"""PA-006A: Allocation Drift Analyzer — Phase 1 MVP.

Reads existing PAR artifacts (compliance.json + run_metadata.json) to construct
allocation drift trends across available history.

Phase 1 scope:
- compute_drift_summary()  → current + prior CPV values, 7d/30d deltas, trend directions
- compute_drift_timeline() → per-rule time series from all available compliance.json files

Phase 1 constraints:
- NO holdings.csv parsing
- NO per-symbol contributor analysis
- Read-only; no writes to any artifact

All computation is deterministic: same inputs → same outputs.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# CPV policy constants (mirrors allocation_policy.yaml compliance_tolerance)
# ---------------------------------------------------------------------------

_CPV_POLICY: dict[str, dict[str, Any]] = {
    "CPV-01": {"name": "Combined Micro Cap",       "rule_type": "ceiling", "limit": 5.0,  "advisory_pp": 2.0,  "warn_pp": 4.0},
    "CPV-02": {"name": "Mega Cap Concentration",   "rule_type": "ceiling", "limit": 50.0, "advisory_pp": 5.0,  "warn_pp": 10.0},
    "CPV-03": {"name": "Digital Assets",           "rule_type": "ceiling", "limit": 8.0,  "advisory_pp": 1.0,  "warn_pp": 2.0},
    "CPV-04": {"name": "Cash Floor",               "rule_type": "floor",   "limit": 2.0,  "advisory_pp": 1.0,  "warn_pp": 2.0},
    "CPV-05": {"name": "International Allocation", "rule_type": "floor",   "limit": 10.0, "advisory_pp": 2.0,  "warn_pp": 4.0},
    "CPV-06": {"name": "Single Asset Class Max",   "rule_type": "ceiling", "limit": 80.0, "advisory_pp": 5.0,  "warn_pp": 10.0},
    "CPV-07": {"name": "Equities Minimum",         "rule_type": "floor",   "limit": 40.0, "advisory_pp": 5.0,  "warn_pp": 10.0},
    "CPV-08": {"name": "Fixed Income Maximum",     "rule_type": "ceiling", "limit": 40.0, "advisory_pp": 5.0,  "warn_pp": 10.0},
}

_ALL_RULE_IDS = list(_CPV_POLICY.keys())

# Trend stability threshold: changes below this are classified STABLE
_STABLE_THRESHOLD_PP = 0.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cpv_status(rule_id: str, actual_pct: float) -> tuple[str, float]:
    """Return (status, breach_pp) for a CPV rule given actual_pct.

    breach_pp is always non-negative; it measures the magnitude of the
    policy breach regardless of direction.
    """
    p = _CPV_POLICY[rule_id]
    if p["rule_type"] == "ceiling":
        breach = actual_pct - p["limit"]
    else:  # floor
        breach = p["limit"] - actual_pct

    breach = round(breach, 4)
    if breach <= 0:
        return "OK", max(breach, 0.0)
    elif breach <= p["advisory_pp"]:
        return "ADVISORY", breach
    elif breach <= p["warn_pp"]:
        return "WARN", breach
    else:
        return "FAIL", breach


def _trend_direction(rule_id: str, delta_pp: float | None) -> str:
    """Return trend direction label for a CPV rule given the signed delta.

    delta_pp = current_pct - reference_pct (positive means the metric rose).

    For ceiling rules: rising metric = WORSENING (gets closer to / further past ceiling)
    For floor rules:   falling metric = WORSENING (gets farther below floor)
    """
    if delta_pp is None:
        return "UNKNOWN"
    if abs(delta_pp) < _STABLE_THRESHOLD_PP:
        return "STABLE"
    p = _CPV_POLICY[rule_id]
    if p["rule_type"] == "ceiling":
        return "WORSENING" if delta_pp > 0 else "IMPROVING"
    else:  # floor
        return "IMPROVING" if delta_pp > 0 else "WORSENING"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _par_runs_dir(repo_root: Path) -> Path:
    return repo_root / "data" / "portfolio_ingestion" / "analysis_runs"


def _load_all_compliance_records(repo_root: Path) -> list[dict[str, Any]]:
    """Return all CPV compliance records found on disk, one entry per PAR run.

    Only PAR runs that have both run_metadata.json and compliance.json are
    included. Entries are sorted ascending by (snapshot_date, created_at_utc).
    """
    par_dir = _par_runs_dir(repo_root)
    if not par_dir.exists():
        return []

    records: list[dict[str, Any]] = []

    for par_path in par_dir.iterdir():
        if not par_path.is_dir():
            continue
        meta_file = par_path / "run_metadata.json"
        cpv_file = par_path / "compliance.json"

        if not meta_file.exists() or not cpv_file.exists():
            continue

        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            cpv = json.loads(cpv_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        snapshot_date = str(meta.get("snapshot_date", ""))[:10]
        created_at = str(meta.get("created_at_utc", ""))

        if len(snapshot_date) != 10:
            continue

        cpv_rules: dict[str, dict[str, Any]] = {}
        for rule in cpv.get("rules", []):
            rid = rule.get("rule_id", "")
            if rid in _CPV_POLICY:
                cpv_rules[rid] = {
                    "actual_pct": float(rule.get("actual_pct", 0)),
                    "status": str(rule.get("status", "OK")),
                    "breach_pp": float(rule.get("breach_pp", 0)),
                }

        records.append({
            "par_id": par_path.name,
            "snapshot_date": snapshot_date,
            "created_at_utc": created_at,
            "overall_status": str(cpv.get("overall_status", "OK")),
            "compliance_score": int(cpv.get("compliance_score", 100)),
            "rules": cpv_rules,
        })

    # Sort by (snapshot_date, created_at_utc) ascending
    records.sort(key=lambda r: (r["snapshot_date"], r["created_at_utc"]))
    return records


def _canonical_by_date(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return latest PAR record per snapshot_date (last in sorted order)."""
    by_date: dict[str, dict[str, Any]] = {}
    for r in records:
        by_date[r["snapshot_date"]] = r  # later entries overwrite earlier ones
    return by_date


def _find_reference_record(
    by_date: dict[str, dict[str, Any]],
    current_date_str: str,
    days_back: int,
) -> dict[str, Any] | None:
    """Find the nearest available record at or before (current_date - days_back)."""
    try:
        current_dt = date.fromisoformat(current_date_str)
    except ValueError:
        return None

    target_dt = current_dt - timedelta(days=days_back)
    target_str = target_dt.isoformat()

    # Find the latest date that is ≤ target
    candidates = [d for d in by_date if d <= target_str]
    if not candidates:
        return None
    return by_date[max(candidates)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_drift_summary(repo_root: Path | str = ".") -> dict[str, Any]:
    """Compute the drift summary payload for GET /api/drift/summary.

    Returns:
        {
          "generated_at": ISO timestamp,
          "current_date": "YYYY-MM-DD",
          "prior_date": "YYYY-MM-DD" | null,
          "dates_available": int,
          "current_overall_status": str,
          "current_compliance_score": int,
          "cpv_trend": [ { rule_id, name, rule_type, policy_limit_pct,
                            current_pct, prior_pct, delta_7d_pp, delta_30d_pp,
                            current_status, prior_status, trend_direction,
                            breach_pp } ],
        }
    """
    repo_root = Path(repo_root)
    records = _load_all_compliance_records(repo_root)
    by_date = _canonical_by_date(records)
    sorted_dates = sorted(by_date.keys())

    generated_at = datetime.now().isoformat()

    if not sorted_dates:
        return {
            "generated_at": generated_at,
            "current_date": None,
            "prior_date": None,
            "dates_available": 0,
            "current_overall_status": "UNKNOWN",
            "current_compliance_score": None,
            "cpv_trend": [],
        }

    current_date = sorted_dates[-1]
    current_rec = by_date[current_date]

    # Prior = most recent date before current
    prior_date: str | None = sorted_dates[-2] if len(sorted_dates) >= 2 else None
    prior_rec: dict[str, Any] | None = by_date[prior_date] if prior_date else None

    ref_7d = _find_reference_record(by_date, current_date, 7)
    ref_30d = _find_reference_record(by_date, current_date, 30)

    cpv_trend: list[dict[str, Any]] = []
    for rule_id, policy in _CPV_POLICY.items():
        curr_rule = current_rec["rules"].get(rule_id)
        if curr_rule is None:
            continue

        current_pct = round(curr_rule["actual_pct"], 4)
        current_status, breach_pp = _cpv_status(rule_id, current_pct)

        prior_pct: float | None = None
        prior_status: str | None = None
        if prior_rec and rule_id in prior_rec["rules"]:
            prior_pct = round(prior_rec["rules"][rule_id]["actual_pct"], 4)
            prior_status, _ = _cpv_status(rule_id, prior_pct)

        delta_7d: float | None = None
        if ref_7d and rule_id in ref_7d["rules"] and ref_7d["snapshot_date"] != current_date:
            delta_7d = round(current_pct - ref_7d["rules"][rule_id]["actual_pct"], 4)

        delta_30d: float | None = None
        if ref_30d and rule_id in ref_30d["rules"] and ref_30d["snapshot_date"] != current_date:
            delta_30d = round(current_pct - ref_30d["rules"][rule_id]["actual_pct"], 4)

        # Use 7d delta for trend; fall back to prior delta
        trend_delta = delta_7d if delta_7d is not None else (
            round(current_pct - prior_pct, 4) if prior_pct is not None else None
        )
        trend_direction = _trend_direction(rule_id, trend_delta)

        cpv_trend.append({
            "rule_id": rule_id,
            "name": policy["name"],
            "rule_type": policy["rule_type"],
            "policy_limit_pct": policy["limit"],
            "current_pct": current_pct,
            "prior_pct": prior_pct,
            "delta_7d_pp": delta_7d,
            "delta_30d_pp": delta_30d,
            "current_status": current_status,
            "prior_status": prior_status,
            "trend_direction": trend_direction,
            "breach_pp": round(breach_pp, 4),
        })

    return {
        "generated_at": generated_at,
        "current_date": current_date,
        "prior_date": prior_date,
        "dates_available": len(sorted_dates),
        "current_overall_status": current_rec["overall_status"],
        "current_compliance_score": current_rec["compliance_score"],
        "cpv_trend": cpv_trend,
    }


def compute_drift_timeline(
    rule_id: str,
    repo_root: Path | str = ".",
) -> dict[str, Any]:
    """Compute the time series for a single CPV rule.

    Returns:
        {
          "rule_id": str,
          "name": str,
          "rule_type": str,
          "policy_limit_pct": float,
          "timeline": [ { "date", "actual_pct", "status", "breach_pp" } ],
        }
    """
    repo_root = Path(repo_root)

    if rule_id not in _CPV_POLICY:
        return {
            "error": f"Unknown rule_id '{rule_id}'. Valid: {_ALL_RULE_IDS}",
        }

    policy = _CPV_POLICY[rule_id]
    records = _load_all_compliance_records(repo_root)
    by_date = _canonical_by_date(records)

    timeline: list[dict[str, Any]] = []
    for dt in sorted(by_date.keys()):
        rec = by_date[dt]
        rule_data = rec["rules"].get(rule_id)
        if rule_data is None:
            continue
        actual_pct = round(rule_data["actual_pct"], 4)
        status, breach_pp = _cpv_status(rule_id, actual_pct)
        timeline.append({
            "date": dt,
            "actual_pct": actual_pct,
            "status": status,
            "breach_pp": round(breach_pp, 4),
            "par_id": rec["par_id"],
        })

    return {
        "rule_id": rule_id,
        "name": policy["name"],
        "rule_type": policy["rule_type"],
        "policy_limit_pct": policy["limit"],
        "advisory_threshold_pct": policy["limit"] + policy["advisory_pp"] if policy["rule_type"] == "ceiling" else policy["limit"] - policy["advisory_pp"],
        "warn_threshold_pct": policy["limit"] + policy["warn_pp"] if policy["rule_type"] == "ceiling" else policy["limit"] - policy["warn_pp"],
        "timeline": timeline,
    }
