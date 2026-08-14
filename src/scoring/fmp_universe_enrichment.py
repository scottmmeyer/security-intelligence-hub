"""FMP Analytical Universe Enrichment — Phase 8.0B.1B.

Loads all four FMP signal datasets and merges them into a single enriched
view per symbol for diagnostic and display purposes.

This module is DATA VISIBILITY ONLY.

Non-negotiables:
  - NO scoring changes
  - NO CW-DAS changes
  - NO ranking changes
  - NO recommendation changes
  - NO conviction changes

Output:
  data/signals/fmp/latest/latest_fmp_enriched_universe.csv
  (symbol-keyed flat file with all FMP fields + coverage status)

Coverage status per symbol:
  FULL               — all 4 datasets have at least one populated field
  PARTIAL            — at least 1 dataset populated but not all
  ETF_NOT_APPLICABLE — symbol is an ETF/FUND/ETN/MUTUALFUND in the universe
    PROVIDER_NO_DATA   — symbol was attempted but provider returned no usable payload
    FETCH_FAILED       — symbol was attempted and one or more product calls failed
    NOT_FETCHED        — symbol exists in universe but has not been attempted yet

Usage:
    PYTHONPATH=. .venv/bin/python3 src/scoring/fmp_universe_enrichment.py
"""

from __future__ import annotations

import csv
import dataclasses
from pathlib import Path
from typing import Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FMP_LATEST_DIR = _REPO_ROOT / "data" / "signals" / "fmp" / "latest"
_OUTPUT_PATH    = _FMP_LATEST_DIR / "latest_fmp_enriched_universe.csv"
_FETCH_STATUS_PATH = _FMP_LATEST_DIR / "latest_fmp_fetch_status.csv"
_UNIVERSE_PATH  = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"

# Security types considered not applicable for FMP fundamental data
_ETF_LIKE_TYPES = frozenset({
    "ETF", "FUND", "MUTUAL FUND", "UNIT TRUST FUND", "ETN",
    "MUTUALFUND", "EXCHANGE TRADED FUND",
})

# Coverage status values
COVERAGE_FULL       = "FULL"
COVERAGE_PARTIAL    = "PARTIAL"
COVERAGE_ETF_NA     = "ETF_NOT_APPLICABLE"
COVERAGE_PROVIDER_NO_DATA = "PROVIDER_NO_DATA"
COVERAGE_FETCH_FAILED = "FETCH_FAILED"
COVERAGE_NOT_FETCHED = "NOT_FETCHED"

ATTEMPT_PROVENANCE_LEDGER = "LEDGER_CONFIRMED"
ATTEMPT_PROVENANCE_LEGACY = "LEGACY_PAYLOAD_CONFIRMED"
ATTEMPT_PROVENANCE_UNKNOWN = "UNKNOWN"

FETCH_STATUS_SUCCESS = "SUCCESS"
FETCH_STATUS_PROVIDER_NO_DATA = "PROVIDER_NO_DATA"
FETCH_STATUS_FETCH_FAILED = "FETCH_FAILED"

_PRODUCTS = ("key_metrics", "grades_consensus", "earnings", "income_growth")

# ── Output schema ─────────────────────────────────────────────────────────────

ENRICHED_HEADERS = [
    # Identity
    "symbol",
    "fmp_coverage_status",
    "fmp_attempted",
    "fmp_attempt_provenance",
    "fmp_sourced_date",
    # Key Metrics TTM
    "pe_ratio_ttm",
    "ev_ebitda_ttm",
    "price_to_fcf_ttm",
    "fcf_yield_ttm",
    "roe_ttm",
    "roic_ttm",
    "earnings_yield_ttm",
    # Grades / Analyst Consensus
    "strong_buy_count",
    "buy_count",
    "hold_count",
    "sell_count",
    "strong_sell_count",
    "total_analysts",
    "net_buy_score",
    "consensus_label",
    # Earnings Surprises
    "latest_eps_surprise_pct",
    "beats_last_8q",
    "beat_rate_8q",
    "q1_surprise_pct",
    "q2_surprise_pct",
    "q3_surprise_pct",
    "q4_surprise_pct",
    # Income Growth
    "revenue_growth_q1_yoy",
    "eps_growth_q1_yoy",
    "revenue_acceleration",
]


@dataclasses.dataclass
class FmpEnrichedRecord:
    """All FMP fields for one symbol, with coverage status."""

    symbol: str
    fmp_coverage_status: str
    fmp_attempted: str
    fmp_attempt_provenance: str
    fmp_sourced_date: str

    # Key metrics TTM
    pe_ratio_ttm: Optional[str] = None
    ev_ebitda_ttm: Optional[str] = None
    price_to_fcf_ttm: Optional[str] = None
    fcf_yield_ttm: Optional[str] = None
    roe_ttm: Optional[str] = None
    roic_ttm: Optional[str] = None
    earnings_yield_ttm: Optional[str] = None

    # Grades / consensus
    strong_buy_count: Optional[str] = None
    buy_count: Optional[str] = None
    hold_count: Optional[str] = None
    sell_count: Optional[str] = None
    strong_sell_count: Optional[str] = None
    total_analysts: Optional[str] = None
    net_buy_score: Optional[str] = None
    consensus_label: Optional[str] = None

    # Earnings surprises
    latest_eps_surprise_pct: Optional[str] = None
    beats_last_8q: Optional[str] = None
    beat_rate_8q: Optional[str] = None
    q1_surprise_pct: Optional[str] = None
    q2_surprise_pct: Optional[str] = None
    q3_surprise_pct: Optional[str] = None
    q4_surprise_pct: Optional[str] = None

    # Income growth
    revenue_growth_q1_yoy: Optional[str] = None
    eps_growth_q1_yoy: Optional[str] = None
    revenue_acceleration: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        return {k: (v or "") for k, v in dataclasses.asdict(self).items()}


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> Dict[str, Dict[str, str]]:
    """Load a CSV keyed by symbol (upper-case)."""
    result: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return result
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


def _load_fetch_status(path: Path = _FETCH_STATUS_PATH) -> Dict[str, Dict[str, str]]:
    """Load symbol -> product -> fetch status from the status ledger."""
    result: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return result
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            product = str(row.get("product", "")).strip().lower()
            status = str(row.get("status", "")).strip().upper()
            if sym and product and status:
                result.setdefault(sym, {})[product] = status
    return result


def _has_data(row: Optional[Dict[str, str]], *fields: str) -> bool:
    """Return True if at least one of the given fields is non-empty."""
    if not row:
        return False
    return any(str(row.get(f, "")).strip() not in ("", "None", "nan") for f in fields)


def _get(row: Optional[Dict[str, str]], field: str) -> Optional[str]:
    """Get a field value, returning None if empty/missing."""
    if not row:
        return None
    v = str(row.get(field, "")).strip()
    return v if v not in ("", "None", "nan") else None


def _is_explicit_failure(row: Optional[Dict[str, str]]) -> bool:
    """Return True when a row carries explicit technical failure markers."""
    if not row:
        return False
    for field in ("fetch_status", "status", "fetch_error", "error", "error_type", "error_message"):
        value = str(row.get(field, "")).strip().upper()
        if not value:
            continue
        if "FAIL" in value or "ERROR" in value or "TIMEOUT" in value or value.startswith("HTTP "):
            return True
    return False


# ── Coverage classifier ───────────────────────────────────────────────────────

def classify_coverage(
    security_type: str,
    attempted: bool,
    product_statuses: Dict[str, str],
    km: Optional[Dict[str, str]],
    gr: Optional[Dict[str, str]],
    es: Optional[Dict[str, str]],
    ig: Optional[Dict[str, str]],
) -> str:
    """Determine FMP coverage status for a symbol."""
    # ETF / Fund: not applicable for FMP fundamentals
    if security_type.strip().upper() in _ETF_LIKE_TYPES:
        return COVERAGE_ETF_NA

    if not attempted:
        return COVERAGE_NOT_FETCHED

    if any(
        str(product_statuses.get(product, "")).upper() == FETCH_STATUS_FETCH_FAILED
        for product in _PRODUCTS
    ):
        return COVERAGE_FETCH_FAILED

    has_km = _has_data(km, "ev_ebitda_ttm", "roe_ttm", "roic_ttm")
    has_gr = _has_data(gr, "consensus_label", "net_buy_score")
    has_es = _has_data(es, "beat_rate_8q", "latest_eps_surprise_pct")
    has_ig = _has_data(ig, "revenue_growth_q1_yoy", "eps_growth_q1_yoy")

    populated = sum([has_km, has_gr, has_es, has_ig])

    if populated == 4:
        return COVERAGE_FULL
    if populated >= 1:
        return COVERAGE_PARTIAL
    if any(_is_explicit_failure(row) for row in (km, gr, es, ig)):
        return COVERAGE_FETCH_FAILED
    return COVERAGE_PROVIDER_NO_DATA


def _attempt_provenance(
    *,
    security_type: str,
    product_statuses: Dict[str, str],
    km: Optional[Dict[str, str]],
    gr: Optional[Dict[str, str]],
    es: Optional[Dict[str, str]],
    ig: Optional[Dict[str, str]],
) -> str:
    """Return symbol-level attempt provenance.

    Ledger rows are authoritative for modern attempts. For pre-ledger symbols,
    persisted product cache rows are treated as legacy-confirmed evidence.
    """
    if security_type.strip().upper() in _ETF_LIKE_TYPES:
        return ATTEMPT_PROVENANCE_UNKNOWN
    if product_statuses:
        return ATTEMPT_PROVENANCE_LEDGER
    if any(row is not None for row in (km, gr, es, ig)):
        return ATTEMPT_PROVENANCE_LEGACY
    return ATTEMPT_PROVENANCE_UNKNOWN


# ── Main builder ──────────────────────────────────────────────────────────────

def build_fmp_enriched_universe(
    fmp_latest_dir: Path = _FMP_LATEST_DIR,
    universe_path: Path = _UNIVERSE_PATH,
    output_path: Path = _OUTPUT_PATH,
    symbols: Optional[list[str]] = None,
) -> Dict[str, FmpEnrichedRecord]:
    """Build the FMP-enriched universe, writing CSV and returning the dict.

    Args:
        fmp_latest_dir: directory containing the four FMP latest CSVs
        universe_path:  analytical universe CSV (for security_type lookup)
        output_path:    where to write the enriched CSV
        symbols:        optional symbol list to restrict output (default: all)

    Returns:
        Dict mapping upper-case symbol → FmpEnrichedRecord
    """
    # Load FMP datasets
    km_by_sym = _load_csv(fmp_latest_dir / "latest_fmp_key_metrics.csv")
    gr_by_sym = _load_csv(fmp_latest_dir / "latest_fmp_grades_consensus.csv")
    es_by_sym = _load_csv(fmp_latest_dir / "latest_fmp_earnings_surprises.csv")
    ig_by_sym = _load_csv(fmp_latest_dir / "latest_fmp_income_growth.csv")
    status_by_sym = _load_fetch_status(fmp_latest_dir / "latest_fmp_fetch_status.csv")

    # Load universe for security_type lookup
    sec_type_by_sym: Dict[str, str] = {}
    sourced_date_by_sym: Dict[str, str] = {}
    if universe_path.exists():
        with universe_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    sec_type_by_sym[sym] = str(row.get("security_type", "")).strip()
                    sourced_date_by_sym[sym] = str(row.get("snapshot_date", "")).strip()

    # Union of all known symbols
    all_syms = set(km_by_sym) | set(gr_by_sym) | set(es_by_sym) | set(ig_by_sym) | set(sec_type_by_sym)
    if symbols:
        all_syms = {s.upper() for s in symbols} & all_syms

    result: Dict[str, FmpEnrichedRecord] = {}

    for sym in sorted(all_syms):
        sec_type  = sec_type_by_sym.get(sym, "")
        km        = km_by_sym.get(sym)
        gr        = gr_by_sym.get(sym)
        es        = es_by_sym.get(sym)
        ig        = ig_by_sym.get(sym)

        product_statuses = status_by_sym.get(sym, {})
        attempt_provenance = _attempt_provenance(
            security_type=sec_type,
            product_statuses=product_statuses,
            km=km,
            gr=gr,
            es=es,
            ig=ig,
        )
        attempted = attempt_provenance != ATTEMPT_PROVENANCE_UNKNOWN
        coverage = classify_coverage(sec_type, attempted, product_statuses, km, gr, es, ig)

        # Derive sourced_date from any available row
        sourced = (_get(km, "sourced_date") or _get(gr, "sourced_date") or
                   _get(es, "sourced_date") or _get(ig, "sourced_date") or "")

        rec = FmpEnrichedRecord(
            symbol=sym,
            fmp_coverage_status=coverage,
            fmp_attempted="1" if attempted else "0",
            fmp_attempt_provenance=attempt_provenance,
            fmp_sourced_date=sourced,
            # Key metrics
            pe_ratio_ttm=_get(km, "pe_ratio_ttm"),
            ev_ebitda_ttm=_get(km, "ev_ebitda_ttm"),
            price_to_fcf_ttm=_get(km, "price_to_fcf_ttm"),
            fcf_yield_ttm=_get(km, "fcf_yield_ttm"),
            roe_ttm=_get(km, "roe_ttm"),
            roic_ttm=_get(km, "roic_ttm"),
            earnings_yield_ttm=_get(km, "earnings_yield_ttm"),
            # Grades
            strong_buy_count=_get(gr, "strong_buy_count"),
            buy_count=_get(gr, "buy_count"),
            hold_count=_get(gr, "hold_count"),
            sell_count=_get(gr, "sell_count"),
            strong_sell_count=_get(gr, "strong_sell_count"),
            total_analysts=_get(gr, "total_analysts"),
            net_buy_score=_get(gr, "net_buy_score"),
            consensus_label=_get(gr, "consensus_label"),
            # Earnings
            latest_eps_surprise_pct=_get(es, "latest_eps_surprise_pct"),
            beats_last_8q=_get(es, "beats_last_8q"),
            beat_rate_8q=_get(es, "beat_rate_8q"),
            q1_surprise_pct=_get(es, "q1_surprise_pct"),
            q2_surprise_pct=_get(es, "q2_surprise_pct"),
            q3_surprise_pct=_get(es, "q3_surprise_pct"),
            q4_surprise_pct=_get(es, "q4_surprise_pct"),
            # Income growth
            revenue_growth_q1_yoy=_get(ig, "revenue_growth_q1_yoy"),
            eps_growth_q1_yoy=_get(ig, "eps_growth_q1_yoy"),
            revenue_acceleration=_get(ig, "revenue_acceleration"),
        )
        result[sym] = rec

    # Write output CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ENRICHED_HEADERS, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(r.to_dict() for r in result.values())

    return result


def load_fmp_enriched_universe(
    output_path: Path = _OUTPUT_PATH,
) -> Dict[str, Dict[str, str]]:
    """Load the pre-built enriched universe CSV. Returns {} if not yet built."""
    result: Dict[str, Dict[str, str]] = {}
    if not output_path.exists():
        return result
    with output_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


# ── Coverage statistics ───────────────────────────────────────────────────────

def coverage_stats(records: Dict[str, FmpEnrichedRecord]) -> Dict[str, object]:
    """Compute summary coverage statistics."""
    total = len(records)
    counts: Dict[str, int] = {
        COVERAGE_FULL: 0, COVERAGE_PARTIAL: 0,
        COVERAGE_ETF_NA: 0,
        COVERAGE_PROVIDER_NO_DATA: 0,
        COVERAGE_FETCH_FAILED: 0,
        COVERAGE_NOT_FETCHED: 0,
    }
    for rec in records.values():
        counts[rec.fmp_coverage_status] = counts.get(rec.fmp_coverage_status, 0) + 1

    # Field null rates (across FULL + PARTIAL only)
    eligible = [r for r in records.values() if r.fmp_coverage_status in (COVERAGE_FULL, COVERAGE_PARTIAL)]
    n = len(eligible)
    null_rates: Dict[str, float] = {}
    if n > 0:
        for field in ENRICHED_HEADERS[4:]:  # skip symbol, coverage, attempted flag, date
            null_count = sum(1 for r in eligible if not getattr(r, field, None))
            null_rates[field] = round(null_count / n * 100, 1)

    return {
        "total": total,
        "coverage_counts": counts,
        "coverage_pcts": {k: round(v / total * 100, 1) if total else 0 for k, v in counts.items()},
        "null_rates_pct": null_rates,
        "eligible_count": n,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build FMP enriched universe.")
    parser.add_argument("--symbols", nargs="+", help="Restrict to specific symbols")
    parser.add_argument("--stats", action="store_true", help="Print coverage stats")
    args = parser.parse_args()

    records = build_fmp_enriched_universe(symbols=args.symbols)

    if args.stats:
        stats = coverage_stats(records)
        print(f"\nTotal symbols: {stats['total']}")
        print("Coverage breakdown:")
        for status, count in stats["coverage_counts"].items():
            pct = stats["coverage_pcts"][status]
            print(f"  {status:25}: {count:4} ({pct:5.1f}%)")
        print(f"\nNull rates (among {stats['eligible_count']} FULL/PARTIAL symbols):")
        for field, rate in sorted(stats["null_rates_pct"].items(), key=lambda x: -x[1])[:15]:
            print(f"  {field:35}: {rate:5.1f}%")

    print(f"\nOutput written: {_OUTPUT_PATH}")
    print(f"Records: {len(records)}")
