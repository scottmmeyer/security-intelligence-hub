"""MEI-003 — Event Sensitivity Calibration.

Compares the declared event sensitivity for each security
(from security_profiles.py) against observed portfolio reactions
in the MEI-002 event outcome data.

"VRT was declared HIGH for INTEREST_RATE. After FOMC events, VRT averaged
+3.2% 5d return. The declared sensitivity was well-calibrated."

Governance: Read-only. No sensitivity profiles are modified.

Public API
----------
  calibrate_sensitivities(repo_root) → dict
  symbol_calibration(symbol, repo_root) → dict
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

_OUTCOMES_FILE    = "data/mei/event_outcomes.json"
_CALIBRATION_FILE = "data/mei/sensitivity_calibration.json"

_LEVEL_RANK = {"HIGH": 3, "MODERATE": 2, "LOW": 1, "NONE": 0}
_RANK_LEVEL = {3: "HIGH", 2: "MODERATE", 1: "LOW", 0: "NONE"}

_GOVERNANCE_NOTE = (
    "MEI-003 is informational only. "
    "No security sensitivity profiles are modified. "
    "Calibration observations are derived from historical event outcome data "
    "and are intended to help operators assess whether declared sensitivities "
    "appear well-calibrated against observed portfolio behavior."
)


def _load_outcomes(repo_root: Path) -> Dict:
    path = repo_root / _OUTCOMES_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_security_profiles(symbols: List[str], repo_root: Path) -> Dict[str, Dict]:
    """Load sensitivity profiles for a list of symbols."""
    try:
        from src.mei.security_profiles import mei_security_profiles_bulk
        return mei_security_profiles_bulk(symbols, repo_root)
    except Exception:
        return {}


def _calibration_label(declared: str, observed_reaction: float) -> str:
    """Classify how well the declared sensitivity matches observed reaction."""
    rank = _LEVEL_RANK.get(declared, 0)
    abs_r = abs(observed_reaction)
    if rank == 3:   # HIGH declared
        return "CALIBRATED" if abs_r >= 1.5 else "OVER_DECLARED"
    if rank == 2:   # MODERATE declared
        if abs_r >= 2.0: return "UNDER_DECLARED"
        if abs_r >= 0.5: return "CALIBRATED"
        return "OVER_DECLARED"
    if rank == 1:   # LOW declared
        return "UNDER_DECLARED" if abs_r >= 2.0 else "CALIBRATED"
    return "CALIBRATED"  # NONE declared


def calibrate_sensitivities(repo_root: Path | str = ".") -> Dict:
    """Compute sensitivity calibration for all securities in the event outcome data."""
    root     = Path(repo_root)
    outcomes = _load_outcomes(root)
    if not outcomes or not outcomes.get("outcomes"):
        return {"status": "NO_OUTCOME_DATA", "calibrations": [], "governance_note": _GOVERNANCE_NOTE}

    # Collect per-symbol, per-event-type observed returns
    sym_type_rets: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for outcome in outcomes.get("outcomes", []):
        etype = outcome.get("event_type", "")
        tags  = outcome.get("sensitivity_tags", [])
        for sym, sdata in outcome.get("security_returns", {}).items():
            r5 = sdata.get("return_5d")
            if r5 is not None:
                sym_type_rets[sym][etype].append(r5)
                for tag in tags:
                    sym_type_rets[sym][f"TAG:{tag}"].append(r5)

    # Load sensitivity profiles for observed symbols
    observed_syms = list(sym_type_rets.keys())
    profiles = _load_security_profiles(observed_syms, root)

    calibrations = []
    for sym in sorted(observed_syms):
        profile = profiles.get(sym, {})
        senss   = profile.get("sensitivities", {})
        obs     = sym_type_rets[sym]

        sym_calibs = []
        for event_type, rets in sorted(obs.items()):
            if event_type.startswith("TAG:"):
                tag   = event_type[4:]
                level = senss.get(tag, "NONE")
            else:
                level = "UNKNOWN"

            avg_ret = round(mean(rets) * 100, 3) if rets else None
            n       = len(rets)
            label   = _calibration_label(level, avg_ret or 0) if level not in ("NONE", "UNKNOWN") else "NOT_DECLARED"

            sym_calibs.append({
                "event_type_or_tag": event_type,
                "declared_level":    level,
                "observed_avg_5d_pct": avg_ret,
                "n_events":          n,
                "calibration":       label,
            })

        if sym_calibs:
            # Overall: fraction calibrated
            declared = [c for c in sym_calibs if c["calibration"] not in ("NOT_DECLARED",)]
            cal_rate = (
                round(sum(1 for c in declared if c["calibration"] == "CALIBRATED") / len(declared) * 100, 1)
                if declared else None
            )
            calibrations.append({
                "symbol":           sym,
                "calibration_rate": cal_rate,
                "detail":           sym_calibs,
            })

    calibrations.sort(key=lambda c: -(c.get("calibration_rate") or 0))
    payload = {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "total_symbols": len(calibrations),
        "calibrations":  calibrations,
        "governance_note": _GOVERNANCE_NOTE,
    }
    try:
        out = root / _CALIBRATION_FILE
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    return payload


def symbol_calibration(symbol: str, repo_root: Path | str = ".") -> Dict:
    """Return sensitivity calibration for a single symbol."""
    root = Path(repo_root)
    sym  = symbol.strip().upper()
    data = calibrate_sensitivities(root)
    for c in data.get("calibrations", []):
        if c.get("symbol") == sym:
            return c
    return {"symbol": sym, "error": "No event outcome data for this symbol.", "governance_note": _GOVERNANCE_NOTE}
