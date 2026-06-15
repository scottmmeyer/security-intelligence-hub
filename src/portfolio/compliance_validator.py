"""CPV — Portfolio Compliance Validator (AI-001-OPTION-B).

Evaluates actual portfolio allocation against structural policy ceilings and
floors, producing OK / ADVISORY / WARN / FAIL signals per rule.

This module is informational governance only.  It does not mutate targets,
scores, recommendations, attribution, or benchmark math.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STATUS_OK = "OK"
_STATUS_ADVISORY = "ADVISORY"
_STATUS_WARN = "WARN"
_STATUS_FAIL = "FAIL"

_STATUS_RANK = {_STATUS_OK: 0, _STATUS_ADVISORY: 1, _STATUS_WARN: 2, _STATUS_FAIL: 3}

_DEFAULT_POLICY_PATH = Path("config/allocation_policy.yaml")

_FLOAT_TOLERANCE = 0.01  # ignore floating-point deltas below 0.01pp


# ---------------------------------------------------------------------------
# Default tolerance bands (used when compliance_tolerance absent from YAML)
# ---------------------------------------------------------------------------

_DEFAULT_TOLERANCES: dict[str, dict[str, float]] = {
    "CPV-01_micro_cap":    {"advisory_pp": 2.0, "warn_pp": 4.0},
    "CPV-02_mega_cap":     {"advisory_pp": 5.0, "warn_pp": 10.0},
    "CPV-03_digital":      {"advisory_pp": 1.0, "warn_pp": 2.0},
    "CPV-04_cash_floor":   {"advisory_pp": 1.0, "warn_pp": 2.0},
    "CPV-05_international":{"advisory_pp": 2.0, "warn_pp": 4.0},
    "CPV-06_asset_class":  {"advisory_pp": 5.0, "warn_pp": 10.0},
    "CPV-07_equities_min": {"advisory_pp": 5.0, "warn_pp": 10.0},
    "CPV-08_fi_max":       {"advisory_pp": 5.0, "warn_pp": 10.0},
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComplianceTolerance:
    advisory_pp: float
    warn_pp: float

    def __post_init__(self) -> None:
        if self.advisory_pp > self.warn_pp:
            raise ValueError(
                f"advisory_pp ({self.advisory_pp}) must be ≤ warn_pp ({self.warn_pp})"
            )


@dataclass(frozen=True)
class ComplianceRuleResult:
    rule_id: str                   # "CPV-01"
    name: str                      # "Combined Micro Cap"
    rule_type: str                 # "ceiling" | "floor"
    policy_value_pct: float        # 5.0
    actual_pct: float              # 9.0
    breach_pp: float               # 4.0 (positive = magnitude of breach)
    status: str                    # OK | ADVISORY | WARN | FAIL
    advisory_pp: float
    warn_pp: float
    node_keys: list[str]
    node_hint: str                 # e.g. "EQUITIES.US.MICRO=9.0% INTL.MICRO=0.0%"
    explanation: str               # human-readable explanation


@dataclass
class PortfolioComplianceResult:
    run_id: str
    snapshot_date: str
    overall_status: str            # OK | ADVISORY | WARN | FAIL
    compliance_score: int          # 0–100, display-only
    rule_results: list[ComplianceRuleResult]
    violation_count: int
    advisory_count: int
    warn_count: int
    fail_count: int
    generated_at_utc: str


# ---------------------------------------------------------------------------
# Tolerance loading
# ---------------------------------------------------------------------------

def load_compliance_tolerances(
    config_path: str | Path = _DEFAULT_POLICY_PATH,
) -> dict[str, ComplianceTolerance]:
    """Load compliance_tolerance from allocation_policy.yaml.

    Falls back to ``_DEFAULT_TOLERANCES`` if the section is absent.
    """
    path = Path(config_path)
    raw_tols: dict[str, Any] = {}

    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        raw_tols = doc.get("compliance_tolerance", {})
        # Remove metadata keys that are not rule entries
        raw_tols = {
            k: v for k, v in raw_tols.items()
            if isinstance(v, dict) and "advisory_pp" in v and "warn_pp" in v
        }

    result: dict[str, ComplianceTolerance] = {}
    for key, defaults in _DEFAULT_TOLERANCES.items():
        raw = raw_tols.get(key, defaults)
        result[key] = ComplianceTolerance(
            advisory_pp=float(raw.get("advisory_pp", defaults["advisory_pp"])),
            warn_pp=float(raw.get("warn_pp", defaults["warn_pp"])),
        )
    return result


# ---------------------------------------------------------------------------
# Rule evaluation helpers
# ---------------------------------------------------------------------------

def _grade(breach_pp: float, tol: ComplianceTolerance) -> str:
    """Return OK/ADVISORY/WARN/FAIL from a breach magnitude (always ≥ 0)."""
    if breach_pp <= _FLOAT_TOLERANCE:
        return _STATUS_OK
    if breach_pp <= tol.advisory_pp:
        return _STATUS_ADVISORY
    if breach_pp <= tol.warn_pp:
        return _STATUS_WARN
    return _STATUS_FAIL


def evaluate_rule_ceiling(
    *,
    rule_id: str,
    name: str,
    actual_pct: float,
    ceiling_pct: float,
    tol: ComplianceTolerance,
    node_keys: list[str],
    node_hint: str = "",
) -> ComplianceRuleResult:
    """Evaluate a max-ceiling CPV rule."""
    actual_pct = max(0.0, actual_pct)
    breach_pp = max(0.0, actual_pct - ceiling_pct)
    status = _grade(breach_pp, tol)

    if status == _STATUS_OK:
        explanation = (
            f"{name} actual {actual_pct:.2f}% is within {ceiling_pct:.1f}% ceiling. OK."
        )
    elif status == _STATUS_ADVISORY:
        explanation = (
            f"{name} actual {actual_pct:.2f}% exceeds {ceiling_pct:.1f}% ceiling by "
            f"{breach_pp:.2f}pp. Within advisory tolerance (≤{tol.advisory_pp:.1f}pp). "
            "No action required; note for next rebalancing review."
        )
    elif status == _STATUS_WARN:
        explanation = (
            f"{name} actual {actual_pct:.2f}% exceeds {ceiling_pct:.1f}% ceiling by "
            f"{breach_pp:.2f}pp. Exceeds advisory ({tol.advisory_pp:.1f}pp), within warn "
            f"threshold ({tol.warn_pp:.1f}pp). Rebalancing review recommended."
        )
    else:  # FAIL
        explanation = (
            f"{name} actual {actual_pct:.2f}% exceeds {ceiling_pct:.1f}% ceiling by "
            f"{breach_pp:.2f}pp. Exceeds warn threshold ({tol.warn_pp:.1f}pp). "
            "Governance acknowledgment recommended before worsening this position."
        )

    return ComplianceRuleResult(
        rule_id=rule_id,
        name=name,
        rule_type="ceiling",
        policy_value_pct=ceiling_pct,
        actual_pct=round(actual_pct, 4),
        breach_pp=round(breach_pp, 4),
        status=status,
        advisory_pp=tol.advisory_pp,
        warn_pp=tol.warn_pp,
        node_keys=node_keys,
        node_hint=node_hint,
        explanation=explanation,
    )


def evaluate_rule_floor(
    *,
    rule_id: str,
    name: str,
    actual_pct: float,
    floor_pct: float,
    tol: ComplianceTolerance,
    node_keys: list[str],
    node_hint: str = "",
) -> ComplianceRuleResult:
    """Evaluate a min-floor CPV rule."""
    actual_pct = max(0.0, actual_pct)
    shortfall_pp = max(0.0, floor_pct - actual_pct)
    status = _grade(shortfall_pp, tol)

    if status == _STATUS_OK:
        explanation = (
            f"{name} actual {actual_pct:.2f}% meets {floor_pct:.1f}% floor. OK."
        )
    elif status == _STATUS_ADVISORY:
        explanation = (
            f"{name} actual {actual_pct:.2f}% is {shortfall_pp:.2f}pp below the "
            f"{floor_pct:.1f}% floor. Within advisory tolerance (≤{tol.advisory_pp:.1f}pp). "
            "No action required; note for next rebalancing review."
        )
    elif status == _STATUS_WARN:
        explanation = (
            f"{name} actual {actual_pct:.2f}% is {shortfall_pp:.2f}pp below the "
            f"{floor_pct:.1f}% floor. Exceeds advisory ({tol.advisory_pp:.1f}pp), within "
            f"warn threshold ({tol.warn_pp:.1f}pp). Rebalancing review recommended."
        )
    else:  # FAIL
        explanation = (
            f"{name} actual {actual_pct:.2f}% is {shortfall_pp:.2f}pp below the "
            f"{floor_pct:.1f}% floor. Exceeds warn threshold ({tol.warn_pp:.1f}pp). "
            "Governance acknowledgment recommended."
        )

    return ComplianceRuleResult(
        rule_id=rule_id,
        name=name,
        rule_type="floor",
        policy_value_pct=floor_pct,
        actual_pct=round(actual_pct, 4),
        breach_pp=round(shortfall_pp, 4),
        status=status,
        advisory_pp=tol.advisory_pp,
        warn_pp=tol.warn_pp,
        node_keys=node_keys,
        node_hint=node_hint,
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

def validate_portfolio_compliance(
    *,
    alignment_rows: list[dict[str, object]],
    policy: dict[str, Any],
    tolerances: dict[str, ComplianceTolerance] | None = None,
    run_id: str = "",
    snapshot_date: str = "",
) -> PortfolioComplianceResult:
    """Evaluate actual portfolio allocation against structural policy.

    Parameters
    ----------
    alignment_rows:
        List of AllocationAlignmentResult dicts (from runner's 'alignment' key
        or from alignment.csv).  Each row must have 'node_key' and 'actual_pct'.
    policy:
        Structural policy dict (the 'structural_policy' block from
        allocation_policy.yaml as loaded by load_structural_policy).
    tolerances:
        Pre-loaded ComplianceTolerance map.  Loaded from YAML if None.
    run_id, snapshot_date:
        Optional metadata for the result envelope.

    Returns
    -------
    PortfolioComplianceResult
    """
    if tolerances is None:
        tolerances = load_compliance_tolerances()

    # Build node_key → actual_pct lookup
    actual: dict[str, float] = {}
    for row in alignment_rows:
        key = str(row.get("node_key", "")).strip()
        val = row.get("actual_pct", 0)
        try:
            actual[key] = max(0.0, float(val))
        except (TypeError, ValueError):
            actual[key] = 0.0

    sp = policy  # structural_policy block

    def _act(key: str) -> float:
        return actual.get(key, 0.0)

    results: list[ComplianceRuleResult] = []

    # --- CPV-01: Combined Micro Cap (max) ---
    micro_us = _act("EQUITIES.US.MICRO")
    micro_intl = _act("EQUITIES.INTERNATIONAL.MICRO")
    micro_combined = micro_us + micro_intl
    results.append(evaluate_rule_ceiling(
        rule_id="CPV-01",
        name="Combined Micro Cap",
        actual_pct=micro_combined,
        ceiling_pct=float(sp.get("max_micro_cap_pct", 5.0)),
        tol=tolerances["CPV-01_micro_cap"],
        node_keys=["EQUITIES.US.MICRO", "EQUITIES.INTERNATIONAL.MICRO"],
        node_hint=f"EQUITIES.US.MICRO={micro_us:.4f}% EQUITIES.INTERNATIONAL.MICRO={micro_intl:.4f}%",
    ))

    # --- CPV-02: Mega Cap Concentration (max) ---
    mega = _act("EQUITIES.US.MEGA")
    results.append(evaluate_rule_ceiling(
        rule_id="CPV-02",
        name="Mega Cap Concentration",
        actual_pct=mega,
        ceiling_pct=float(sp.get("max_mega_concentration_pct", 50.0)),
        tol=tolerances["CPV-02_mega_cap"],
        node_keys=["EQUITIES.US.MEGA"],
        node_hint=f"EQUITIES.US.MEGA={mega:.4f}%",
    ))

    # --- CPV-03: Digital Assets (max) ---
    digital = _act("DIGITAL")
    results.append(evaluate_rule_ceiling(
        rule_id="CPV-03",
        name="Digital Assets",
        actual_pct=digital,
        ceiling_pct=float(sp.get("max_digital_assets_pct", 8.0)),
        tol=tolerances["CPV-03_digital"],
        node_keys=["DIGITAL"],
        node_hint=f"DIGITAL={digital:.4f}%",
    ))

    # --- CPV-04: Cash Floor (min) ---
    cash = _act("CASH")
    results.append(evaluate_rule_floor(
        rule_id="CPV-04",
        name="Cash Floor",
        actual_pct=cash,
        floor_pct=float(sp.get("cash_floor_pct", 2.0)),
        tol=tolerances["CPV-04_cash_floor"],
        node_keys=["CASH"],
        node_hint=f"CASH={cash:.4f}%",
    ))

    # --- CPV-05: International Minimum (min) ---
    intl = _act("EQUITIES.INTERNATIONAL")
    em = _act("EQUITIES.EMERGING_MARKETS")
    intl_combined = intl + em
    results.append(evaluate_rule_floor(
        rule_id="CPV-05",
        name="International Minimum",
        actual_pct=intl_combined,
        floor_pct=float(sp.get("min_international_pct", 10.0)),
        tol=tolerances["CPV-05_international"],
        node_keys=["EQUITIES.INTERNATIONAL", "EQUITIES.EMERGING_MARKETS"],
        node_hint=(
            f"EQUITIES.INTERNATIONAL={intl:.4f}% "
            f"EQUITIES.EMERGING_MARKETS={em:.4f}%"
        ),
    ))

    # --- CPV-06: Single Asset Class Maximum ---
    # Evaluate all L1 nodes; flag the one with the highest breach
    l1_nodes = ["EQUITIES", "FIXED_INCOME", "DIGITAL", "COMMODITIES", "CASH"]
    l1_actuals = {k: _act(k) for k in l1_nodes}
    max_l1_key = max(l1_actuals, key=lambda k: l1_actuals[k])
    max_l1_pct = l1_actuals[max_l1_key]
    asset_class_ceiling = float(sp.get("max_single_asset_class_pct", 80.0))
    results.append(evaluate_rule_ceiling(
        rule_id="CPV-06",
        name="Single Asset Class Maximum",
        actual_pct=max_l1_pct,
        ceiling_pct=asset_class_ceiling,
        tol=tolerances["CPV-06_asset_class"],
        node_keys=[max_l1_key],
        node_hint=" ".join(f"{k}={v:.2f}%" for k, v in sorted(l1_actuals.items(), key=lambda x: -x[1])),
    ))

    # --- CPV-07: Equities Minimum (min) ---
    equities = _act("EQUITIES")
    equities_min = float(sp.get("asset_class_governance", {}).get("EQUITIES", {}).get("min_pct", 40.0))
    # Fallback: use a hardcoded 40% if governance block absent
    if not equities_min:
        equities_min = 40.0
    results.append(evaluate_rule_floor(
        rule_id="CPV-07",
        name="Equities Minimum",
        actual_pct=equities,
        floor_pct=equities_min,
        tol=tolerances["CPV-07_equities_min"],
        node_keys=["EQUITIES"],
        node_hint=f"EQUITIES={equities:.4f}%",
    ))

    # --- CPV-08: Fixed Income Maximum (max) ---
    fi = _act("FIXED_INCOME")
    fi_max = float(sp.get("asset_class_governance", {}).get("FIXED_INCOME", {}).get("max_pct", 40.0))
    if not fi_max:
        fi_max = 40.0
    results.append(evaluate_rule_ceiling(
        rule_id="CPV-08",
        name="Fixed Income Maximum",
        actual_pct=fi,
        ceiling_pct=fi_max,
        tol=tolerances["CPV-08_fi_max"],
        node_keys=["FIXED_INCOME"],
        node_hint=f"FIXED_INCOME={fi:.4f}%",
    ))

    # --- Aggregate ---
    advisory_count = sum(1 for r in results if r.status == _STATUS_ADVISORY)
    warn_count = sum(1 for r in results if r.status == _STATUS_WARN)
    fail_count = sum(1 for r in results if r.status == _STATUS_FAIL)
    violation_count = advisory_count + warn_count + fail_count

    # Overall status = worst rule status
    overall = _STATUS_OK
    for r in results:
        if _STATUS_RANK[r.status] > _STATUS_RANK[overall]:
            overall = r.status

    # Compliance score (display-only)
    score = max(0, min(100, 100 - fail_count * 25 - warn_count * 10 - advisory_count * 5))

    return PortfolioComplianceResult(
        run_id=run_id,
        snapshot_date=snapshot_date,
        overall_status=overall,
        compliance_score=score,
        rule_results=results,
        violation_count=violation_count,
        advisory_count=advisory_count,
        warn_count=warn_count,
        fail_count=fail_count,
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

def compliance_result_to_dict(result: PortfolioComplianceResult) -> dict[str, object]:
    """Serialize PortfolioComplianceResult to a JSON-serializable dict."""
    return {
        "run_id": result.run_id,
        "snapshot_date": result.snapshot_date,
        "overall_status": result.overall_status,
        "compliance_score": result.compliance_score,
        "violation_count": result.violation_count,
        "advisory_count": result.advisory_count,
        "warn_count": result.warn_count,
        "fail_count": result.fail_count,
        "generated_at_utc": result.generated_at_utc,
        "rules": [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "rule_type": r.rule_type,
                "policy_value_pct": r.policy_value_pct,
                "actual_pct": r.actual_pct,
                "breach_pp": r.breach_pp,
                "status": r.status,
                "advisory_pp": r.advisory_pp,
                "warn_pp": r.warn_pp,
                "node_keys": r.node_keys,
                "node_hint": r.node_hint,
                "explanation": r.explanation,
            }
            for r in result.rule_results
        ],
    }
