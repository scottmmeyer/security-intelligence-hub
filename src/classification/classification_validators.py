"""Classification validators: audit-time checks for benchmark and geography integrity.

These validators run against a list of AnalyticalUniverseRow objects and emit
ClassificationFinding records at EXCEPTION or WARNING level.

Exit-code semantics (for run_classification_audit.py):
  - Any EXCEPTION-level finding → exit code 1
  - WARNING-level findings → exit code 0 but logged

Validators implemented:
  V01 — UNKNOWN geography on equity security
  V02 — ADR or international company benchmarked against a US benchmark
  V03 — ETF or mutual fund with replay_eligible=True
  V04 — ETF or mutual fund with scoring_eligible=True
  V05 — UNMAPPED or NOT_APPLICABLE benchmark on an equity
  V06 — UNRESOLVABLE benchmark_confidence on an equity
  V07 — Composite score on a non-scoring-eligible security
  V08 — Security type not in canonical class map (UNKNOWN canonical)
  V09 — Market cap bucket invalid or empty
  V10 — geography=US with an INTERNATIONAL benchmark
  V11 — benchmark_confidence=LOW on a large portion of equities (aggregate check)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from src.models.analytical_models import AnalyticalUniverseRow
from src.classification.security_type_policy import (
    SecurityTypePolicy,
    load_security_type_policy,
)

# Known US benchmark IDs (caps at the prefix)
_US_BENCHMARK_PREFIXES = {"BM_US_"}
_INTL_BENCHMARK_PREFIXES = {"BM_INTL_"}

# Valid values
_VALID_GEOGRAPHIES = {"US", "INTERNATIONAL", "UNKNOWN"}
_VALID_CAP_BUCKETS = {"MEGA", "LARGE", "MID", "SMALL", "MICRO"}
_NON_EQUITY_TYPES = {"ETF", "MUTUAL_FUND", "BOND", "DIGITAL_ASSET"}

# Aggregate threshold for V11
_LOW_CONFIDENCE_THRESHOLD = 0.10  # flag if >10% of equities have LOW confidence


class FindingLevel(str, Enum):
    EXCEPTION = "EXCEPTION"
    WARNING = "WARNING"


@dataclass(frozen=True)
class ClassificationFinding:
    """A single classification integrity finding."""

    validator_id: str
    """E.g., V01, V03."""

    level: FindingLevel
    """EXCEPTION or WARNING."""

    symbol: str
    security_type: str
    geography: str
    benchmark_id: str
    message: str


def _is_us_benchmark(benchmark_id: str) -> bool:
    return any(benchmark_id.startswith(p) for p in _US_BENCHMARK_PREFIXES)


def _is_intl_benchmark(benchmark_id: str) -> bool:
    return any(benchmark_id.startswith(p) for p in _INTL_BENCHMARK_PREFIXES)


def validate_universe_classifications(
    rows: Sequence[AnalyticalUniverseRow],
    type_policy: Optional[SecurityTypePolicy] = None,
) -> List[ClassificationFinding]:
    """Run all classification validators against the universe rows.

    Args:
        rows:        Universe rows to validate.
        type_policy: Optional pre-loaded SecurityTypePolicy. Loads default if None.

    Returns a list of ClassificationFinding objects (may be empty).
    """
    if type_policy is None:
        type_policy = load_security_type_policy()

    findings: List[ClassificationFinding] = []

    equity_count = 0
    low_confidence_equity_count = 0

    for row in rows:
        type_info = type_policy.get_type_info(row.security_type)
        canonical = type_info.canonical_class
        geo = str(row.geography or "").strip().upper()
        bm = str(row.benchmark_id or "").strip()
        sym = str(row.symbol or "").strip()
        st = str(row.security_type or "").strip()

        is_equity_like = canonical in ("EQUITY", "UNKNOWN")
        is_fund_like = canonical in ("ETF", "MUTUAL_FUND")

        # V01 — UNKNOWN geography on equity
        if is_equity_like and geo == "UNKNOWN":
            findings.append(ClassificationFinding(
                validator_id="V01",
                level=FindingLevel.EXCEPTION,
                symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                message=f"Equity {sym} has geography=UNKNOWN. Cannot assign correct benchmark.",
            ))

        # V02 — International/ADR company benchmarked against US benchmark
        if is_equity_like and geo == "INTERNATIONAL" and _is_us_benchmark(bm):
            findings.append(ClassificationFinding(
                validator_id="V02",
                level=FindingLevel.EXCEPTION,
                symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                message=f"International/ADR equity {sym} uses US benchmark {bm}.",
            ))

        # V03 — ETF/fund with replay_eligible=True
        if is_fund_like:
            if getattr(row, "replay_eligible", True) is True:
                findings.append(ClassificationFinding(
                    validator_id="V03",
                    level=FindingLevel.EXCEPTION,
                    symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                    message=f"Fund/ETF {sym} has replay_eligible=True. Funds must be excluded from replay.",
                ))

        # V04 — ETF/fund with scoring_eligible=True (composite score should not apply)
        if is_fund_like:
            if getattr(row, "scoring_eligible", True) is True:
                findings.append(ClassificationFinding(
                    validator_id="V04",
                    level=FindingLevel.WARNING,
                    symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                    message=f"Fund/ETF {sym} has scoring_eligible=True. Funds should not receive composite scores.",
                ))

        # V05 — UNMAPPED benchmark on an equity
        if is_equity_like and bm in ("UNMAPPED", ""):
            findings.append(ClassificationFinding(
                validator_id="V05",
                level=FindingLevel.EXCEPTION,
                symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                message=f"Equity {sym} has benchmark_id=UNMAPPED. Benchmark resolution failed.",
            ))

        # V06 — UNRESOLVABLE benchmark_confidence on equity
        confidence = str(getattr(row, "benchmark_confidence", "") or "").strip().upper()
        if is_equity_like and confidence == "UNRESOLVABLE":
            findings.append(ClassificationFinding(
                validator_id="V06",
                level=FindingLevel.WARNING,
                symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                message=f"Equity {sym} has benchmark_confidence=UNRESOLVABLE.",
            ))

        # V07 — Composite score on non-scoring-eligible security
        if canonical in ("ETF", "MUTUAL_FUND", "BOND", "DIGITAL_ASSET"):
            try:
                score = float(row.composite_score or 0)
            except (ValueError, TypeError):
                score = 0.0
            if score > 0.0 and getattr(row, "scoring_eligible", True) is False:
                findings.append(ClassificationFinding(
                    validator_id="V07",
                    level=FindingLevel.WARNING,
                    symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                    message=(
                        f"Non-equity {sym} (canonical={canonical}) has composite_score={score:.2f} "
                        f"but scoring_eligible=False."
                    ),
                ))

        # V08 — Security type maps to UNKNOWN canonical class (unrecognized type string)
        if canonical == "UNKNOWN" and st not in ("UNKNOWN", ""):
            findings.append(ClassificationFinding(
                validator_id="V08",
                level=FindingLevel.WARNING,
                symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                message=f"Symbol {sym} has unrecognized security_type='{st}' (canonical=UNKNOWN).",
            ))

        # V09 — Invalid market cap bucket
        cap = str(row.market_cap_bucket or "").strip().upper()
        if cap not in _VALID_CAP_BUCKETS:
            findings.append(ClassificationFinding(
                validator_id="V09",
                level=FindingLevel.WARNING,
                symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                message=f"Symbol {sym} has invalid market_cap_bucket='{cap}'.",
            ))

        # V10 — geography=US with INTERNATIONAL benchmark (miscategorized as international)
        if is_equity_like and geo == "US" and _is_intl_benchmark(bm):
            findings.append(ClassificationFinding(
                validator_id="V10",
                level=FindingLevel.EXCEPTION,
                symbol=sym, security_type=st, geography=geo, benchmark_id=bm,
                message=f"US equity {sym} uses international benchmark {bm}.",
            ))

        # Accumulate data for V11 aggregate check
        if is_equity_like:
            equity_count += 1
            if confidence == "LOW":
                low_confidence_equity_count += 1

    # V11 — Aggregate: too many equities with LOW confidence
    if equity_count > 0:
        fraction = low_confidence_equity_count / equity_count
        if fraction > _LOW_CONFIDENCE_THRESHOLD:
            findings.append(ClassificationFinding(
                validator_id="V11",
                level=FindingLevel.WARNING,
                symbol="(aggregate)",
                security_type="(equities)",
                geography="(mixed)",
                benchmark_id="(mixed)",
                message=(
                    f"{low_confidence_equity_count}/{equity_count} equities "
                    f"({fraction:.1%}) have benchmark_confidence=LOW. "
                    f"Threshold is {_LOW_CONFIDENCE_THRESHOLD:.0%}."
                ),
            ))

    return findings

