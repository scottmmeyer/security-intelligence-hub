"""DISLOCATION-05 — Forward Return Estimation.

Applies DISLOCATION-02 historical base rates to a security's current conflict
pattern to produce a probabilistic forward return estimate.

"Given MSFT is currently in ESS_BULLISH_ANALYST_MAJORITY_BEARISH and historically
this pattern produced +2.26pp excess return (48.4% win rate, SUGGESTIVE evidence),
the 30d expected return range is [worst: −26.6%, best: +52.9%, median: +2.0%]."

Governance:
  - Read-only. No scoring, CW-DAS, UCF, CRA, or recommendation changes.
  - Estimates are statistical summaries of past observations, not forecasts.
  - Operators must apply their own judgment.

Public API
----------
  forward_estimate(symbol, repo_root) → dict
  forward_estimates_batch(symbols, repo_root) → dict
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.sih.security_conflict_alpha import _load_alpha_index
from src.sih.predictive.pattern_persistence import symbol_pattern_persistence


_ALPHA_FILE = "data/analysis/dislocation/conflict_alpha_report.json"

_CONFIDENCE_LABELS = {
    "NOTEWORTHY":        "Statistically noteworthy — strong historical evidence",
    "SUGGESTIVE":        "Suggestive — moderate historical evidence",
    "WEAK":              "Weak — limited historical evidence",
    "INSUFFICIENT_DATA": "Insufficient data",
}

_GOVERNANCE_NOTE = (
    "DISLOCATION-05 is research-only. "
    "Forward return estimates are statistical summaries of past observations — "
    "not predictions of future performance. "
    "No scoring, CW-DAS, UCF, CRA, Replay, or governance logic is modified. "
    "Operator judgment is required before acting on any estimate."
)


def _load_pattern_detail(repo_root: Path) -> Dict[str, Dict]:
    """Load full pattern detail including best/worst/median from outcomes file."""
    path = repo_root / _ALPHA_FILE
    if not path.exists():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        return {p["signal_pattern"]: p for p in report.get("patterns", [])}
    except (OSError, json.JSONDecodeError):
        return {}


def forward_estimate(symbol: str, repo_root: Path | str = ".") -> Dict:
    """
    Build a forward return estimate for a symbol based on its current
    conflict pattern and DISLOCATION-02 historical base rates.
    """
    root = Path(repo_root)
    sym  = symbol.strip().upper()

    # Get current pattern from persistence
    pers = symbol_pattern_persistence(sym, root)
    if pers.get("error") or not pers.get("current_pattern"):
        return {
            "symbol": sym,
            "status": "NO_CONFLICT_DATA",
            "message": "Symbol not found in ESS archive or no pattern data available.",
            "governance_note": _GOVERNANCE_NOTE,
        }

    pattern         = pers.get("current_pattern", "")
    pattern_label   = pers.get("current_pattern_label", pattern)
    is_conflict     = pers.get("is_current_conflict", False)
    persistence_pct = pers.get("persistence_pct", 0)
    streak          = pers.get("streak", 0)
    dates_observed  = pers.get("dates_observed", 0)

    # Get alpha data
    alpha_index  = _load_pattern_detail(root)
    pattern_data = alpha_index.get(pattern, {})

    if not pattern_data:
        return {
            "symbol":         sym,
            "current_pattern": pattern,
            "pattern_label":   pattern_label,
            "status": "NO_ALPHA_DATA",
            "message": f"No historical alpha data for pattern {pattern}.",
            "governance_note": _GOVERNANCE_NOTE,
        }

    # Core estimate components
    avg_ret         = pattern_data.get("avg_return_30d_pct")
    excess_ret      = pattern_data.get("excess_return_pct")
    median_ret      = pattern_data.get("median_return_30d_pct")
    best_ret        = pattern_data.get("best_return_30d_pct")
    worst_ret       = pattern_data.get("worst_return_30d_pct")
    win_rate        = pattern_data.get("win_rate_pct")
    alpha_class     = pattern_data.get("alpha_class")
    significance    = pattern_data.get("significance", "INSUFFICIENT_DATA")
    n_obs           = pattern_data.get("observations", 0)

    # Persistence modifier: strong persistence boosts confidence
    persistence_note = ""
    if persistence_pct >= 75 and streak >= 3:
        persistence_note = (
            f"{sym} has been in this pattern for {streak} consecutive archive dates "
            f"({persistence_pct:.0f}% persistence rate). "
            "Extended persistence suggests the signal relationship is stable."
        )
    elif persistence_pct <= 25:
        persistence_note = (
            f"This is a new or transient pattern for {sym} "
            f"(only {persistence_pct:.0f}% of observed dates). "
            "Historical base rates may be less applicable."
        )

    # Build interpretation
    conf_label = _CONFIDENCE_LABELS.get(significance, "Insufficient data")
    if alpha_class == "ALPHA_LEADER" and excess_ret is not None:
        interpretation = (
            f"Based on {n_obs} historical occurrences of {pattern_label}, "
            f"this pattern has produced {excess_ret:+.2f}pp excess return above universe median "
            f"({win_rate:.0f}% above-median rate). "
            f"Evidence level: {conf_label}. "
            "Historical evidence favors the ESS signal direction."
        )
    elif alpha_class == "ALPHA_LAGGARD" and excess_ret is not None:
        interpretation = (
            f"Based on {n_obs} historical occurrences of {pattern_label}, "
            f"this pattern has underperformed by {excess_ret:+.2f}pp vs universe median "
            f"({win_rate:.0f}% above-median rate). "
            f"Evidence level: {conf_label}. "
            "Historical evidence suggests caution — analyst consensus has historically "
            "provided a useful counterweight to ESS in this configuration."
        )
    else:
        interpretation = (
            f"Based on {n_obs} historical occurrences of {pattern_label}, "
            f"this pattern has produced {excess_ret:+.2f}pp excess return. "
            f"Evidence level: {conf_label}. "
            "No material alpha advantage or disadvantage identified."
        ) if excess_ret is not None else (
            f"Insufficient historical data for {pattern_label}. "
            "Cannot derive a meaningful base-rate estimate."
        )

    if persistence_note:
        interpretation += " " + persistence_note

    base_result = {
        "symbol":           sym,
        "current_pattern":  pattern,
        "pattern_label":    pattern_label,
        "is_conflict":      is_conflict,
        "status":           "OK",

        # Historical base rates
        "n_observations":   n_obs,
        "alpha_class":      alpha_class,
        "excess_return_pct": excess_ret,
        "avg_return_30d_pct": avg_ret,
        "median_return_30d_pct": median_ret,
        "best_case_30d_pct":  best_ret,
        "worst_case_30d_pct": worst_ret,
        "win_rate_pct":     win_rate,
        "significance":     significance,

        # Pattern persistence context
        "dates_observed":   dates_observed,
        "pattern_persistence_pct": persistence_pct,
        "consecutive_streak": streak,

        # Narrative
        "interpretation":   interpretation,
        "governance_note":  _GOVERNANCE_NOTE,
    }

    # ── DISLOCATION-06: Attach calibration data (non-blocking) ────────────────
    try:
        from src.sih.predictive.conflict_alpha_calibration import enrich_forward_estimate
        return enrich_forward_estimate(base_result, root)
    except Exception:
        return base_result


def forward_estimates_batch(symbols: List[str], repo_root: Path | str = ".") -> Dict:
    """Return forward estimates for a list of symbols."""
    root     = Path(repo_root)
    results  = {}
    for sym in symbols:
        results[sym.upper()] = forward_estimate(sym, root)
    leaders  = [r for r in results.values() if r.get("alpha_class") == "ALPHA_LEADER"]
    laggards = [r for r in results.values() if r.get("alpha_class") == "ALPHA_LAGGARD"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total":        len(results),
        "leader_count": len(leaders),
        "laggard_count": len(laggards),
        "estimates":    results,
        "governance_note": _GOVERNANCE_NOTE,
    }
