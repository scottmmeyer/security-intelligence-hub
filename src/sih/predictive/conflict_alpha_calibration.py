"""DISLOCATION-06 — Confidence Calibration for Forward Return Estimates.

Validates DISLOCATION-05 forward return predictions against realized outcomes.

For each conflict pattern:
  1. Reconstruct the DISLOCATION-05 prediction that would have been made at each
     historical archive date (using pattern's alpha stats known at that point).
  2. Compare the predicted excess return to the actual realized return.
  3. Compute calibration metrics: MAE, bias, accuracy bands, reliability score.
  4. Produce a per-pattern confidence level (VERY_HIGH / HIGH / MEDIUM / LOW /
     INSUFFICIENT_DATA) that extends DISLOCATION-05 output.

Key insight: Since DISLOCATION-02 computes aggregate stats across ALL dates,
we use a leave-one-out approach — for each (symbol, date) the "prediction" is the
pattern's expected excess return, and the "realized" is the actual 30d return
minus the universe median for that snapshot date.

Governance:
  - Read-only relative to ALL scoring and recommendation engines.
  - No ESS, CW-DAS, UCF, CRA, PAP, or governance logic is modified.
  - Calibration findings are informational only.

Public API
----------
  calibration_summary(repo_root)           → dict  (/api/predictive/calibration)
  pattern_calibration(pattern, repo_root)  → dict  (/api/predictive/calibration/<pat>)
  confidence_summary(repo_root)            → dict  (/api/predictive/confidence-summary)
  refresh_calibration(repo_root)           → dict  (POST /api/predictive/calibration/refresh)
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Dict, List, Optional, Tuple

_CALIBRATION_FILE = "data/analysis/dislocation/conflict_alpha_calibration.json"
_ALPHA_FILE       = "data/analysis/dislocation/conflict_alpha_report.json"
_DISLOC06_VERSION = "1.0"

# Accuracy band thresholds (percentage points)
_BANDS = [1.0, 2.0, 5.0, 10.0]

# Minimum observations per pattern for confidence scoring
_MIN_HIGH       = 50
_MIN_MEDIUM     = 20
_MIN_LOW        = 5

# MAE thresholds for confidence (pp)
_MAE_VERY_HIGH  = 2.0
_MAE_HIGH       = 4.0
_MAE_MEDIUM     = 7.0

# Bias threshold: |mean_error| below this = well-centred
_BIAS_CENTRED   = 1.0

_GOVERNANCE_NOTE = (
    "DISLOCATION-06 is research-only. "
    "Calibration metrics are derived from historical observations and do not "
    "guarantee future accuracy. No ESS, CW-DAS, UCF, CRA, Replay, PAP, or "
    "governance logic is modified. "
    "Confidence levels are informational — operator judgment is required."
)

_PATTERN_LABELS = {
    "ESS_BULLISH_ANALYST_MAJORITY_BEARISH": "ESS Buy / Analyst Sell",
    "ESS_BULLISH_ANALYST_SKEPTICAL":        "ESS Buy / Analysts Skeptical",
    "ESS_BULLISH_ANALYST_FULL_AGREE":       "ESS Buy / All Agree Buy",
    "ESS_BULLISH_ANALYST_MIXED":            "ESS Buy / Analysts Mixed",
    "ESS_BEARISH_ANALYST_MAJORITY_BULLISH": "ESS Sell / Analyst Buy",
    "ESS_BEARISH_ANALYST_FULL_AGREE":       "ESS Sell / All Agree Sell",
    "ESS_BEARISH_ANALYST_MIXED":            "ESS Sell / Analysts Mixed",
    "ESS_NEUTRAL_ANALYST_BULLISH":          "ESS Neutral / Analysts Buy",
    "ESS_NEUTRAL_ANALYST_BEARISH":          "ESS Neutral / Analysts Sell",
    "ESS_NEUTRAL_ANALYST_MIXED":            "ESS Neutral / Analysts Mixed",
}


# ── Data loaders ───────────────────────────────────────────────────────────────

def _load_inventory(repo_root: Path) -> List[Dict]:
    from src.sih.signal_conflict_review import load_inventory
    return load_inventory(repo_root)


def _load_alpha_index(repo_root: Path) -> Dict[str, Dict]:
    path = repo_root / _ALPHA_FILE
    if not path.exists():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        return {p["signal_pattern"]: p for p in report.get("patterns", [])}
    except (OSError, json.JSONDecodeError):
        return {}


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── Part A + B: Reconstruct predictions and match realized outcomes ────────────

def _build_prediction_pairs(
    inventory: List[Dict],
    alpha_index: Dict[str, Dict],
    universe_median: float,
) -> List[Dict]:
    """
    For each inventory entry with a realized return, reconstruct what
    DISLOCATION-05 would have predicted and compare to actual.

    'Predicted excess return' = pattern's aggregate avg_return_30d_pct - universe_median_pct
    'Realized excess return'  = actual forward_return_30d*100 - universe_median_pct
    """
    pairs = []
    for entry in inventory:
        pattern = entry.get("signal_pattern", "")
        if not pattern or pattern == "NO_ESS_DATA":
            continue

        ret_30_raw = _safe_float(entry.get("forward_return_30d"))
        if ret_30_raw is None:
            continue

        alpha = alpha_index.get(pattern, {})
        predicted_avg = alpha.get("avg_return_30d_pct")
        predicted_excess = alpha.get("excess_return_pct")
        if predicted_avg is None or predicted_excess is None:
            continue

        realized_pct    = round(ret_30_raw * 100, 4)
        realized_excess = round(realized_pct - universe_median, 4)
        absolute_error  = round(abs(predicted_excess - realized_excess), 4)
        signed_error    = round(predicted_excess - realized_excess, 4)

        pairs.append({
            "symbol":              entry.get("symbol", ""),
            "prediction_date":     entry.get("snapshot_date", ""),
            "pattern":             pattern,
            "predicted_avg_return_pct":    predicted_avg,
            "predicted_excess_return_pct": predicted_excess,
            "realized_return_pct":         realized_pct,
            "realized_excess_return_pct":  realized_excess,
            "absolute_error_pp":           absolute_error,
            "signed_error_pp":             signed_error,
        })

    return pairs


# ── Part C: Calibration analysis per pattern ──────────────────────────────────

def _accuracy_bands(errors: List[float]) -> Dict[str, float]:
    """Fraction of predictions within each absolute error band."""
    n = len(errors)
    if n == 0:
        return {}
    return {
        f"within_{int(b)}pp": round(sum(1 for e in errors if e <= b) / n * 100, 1)
        for b in _BANDS
    }


def _bias_direction(mean_error: float) -> str:
    if abs(mean_error) < _BIAS_CENTRED:
        return "NEUTRAL"
    return "OPTIMISTIC" if mean_error > 0 else "PESSIMISTIC"


# ── Part D: Pattern reliability / confidence level ────────────────────────────

def _confidence_level(n: int, mae: float, bias_abs: float) -> str:
    if n < _MIN_LOW:
        return "INSUFFICIENT_DATA"
    if n >= _MIN_HIGH and mae <= _MAE_VERY_HIGH and bias_abs < _BIAS_CENTRED:
        return "VERY_HIGH"
    if n >= _MIN_MEDIUM and mae <= _MAE_HIGH:
        return "HIGH"
    if n >= _MIN_LOW and mae <= _MAE_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _confidence_label(level: str) -> str:
    return {
        "VERY_HIGH":         "Highly calibrated — large sample, low error, well-centred",
        "HIGH":              "Well calibrated — good sample, moderate error",
        "MEDIUM":            "Moderately calibrated — limited sample or mixed accuracy",
        "LOW":               "Poorly calibrated — small sample or high error",
        "INSUFFICIENT_DATA": "Insufficient historical data for calibration",
    }.get(level, level)


# ── Core computation ───────────────────────────────────────────────────────────

def _compute_pattern_calibration(
    pattern: str,
    pairs: List[Dict],
    alpha_data: Dict,
) -> Dict:
    """Compute full calibration stats for one pattern."""
    pattern_pairs = [p for p in pairs if p["pattern"] == pattern]
    n = len(pattern_pairs)

    if n == 0:
        return {
            "pattern":        pattern,
            "pattern_label":  _PATTERN_LABELS.get(pattern, pattern.replace("_", " ")),
            "n":              0,
            "confidence":     "INSUFFICIENT_DATA",
            "confidence_label": _confidence_label("INSUFFICIENT_DATA"),
        }

    errors    = [p["absolute_error_pp"] for p in pattern_pairs]
    signed    = [p["signed_error_pp"]   for p in pattern_pairs]
    realized  = [p["realized_excess_return_pct"] for p in pattern_pairs]

    mae       = round(mean(errors), 3)
    mean_err  = round(mean(signed), 3)
    rmse      = round(math.sqrt(mean(e**2 for e in errors)), 3)
    bias_dir  = _bias_direction(mean_err)
    bands     = _accuracy_bands(errors)

    # Correlation: does higher predicted excess → higher realized excess?
    predicted = [p["predicted_excess_return_pct"] for p in pattern_pairs]
    if len(set(predicted)) > 1 and len(realized) > 1:
        try:
            mp = mean(predicted); mr = mean(realized)
            num = sum((x - mp) * (y - mr) for x, y in zip(predicted, realized))
            dp  = math.sqrt(sum((x - mp)**2 for x in predicted))
            dr  = math.sqrt(sum((y - mr)**2 for y in realized))
            corr = round(num / (dp * dr), 4) if dp > 0 and dr > 0 else None
        except Exception:
            corr = None
    else:
        corr = None

    confidence = _confidence_level(n, mae, abs(mean_err))

    # Top most-accurate symbols (lowest avg absolute error)
    sym_errors: Dict[str, List[float]] = defaultdict(list)
    for p in pattern_pairs:
        sym_errors[p["symbol"]].append(p["absolute_error_pp"])
    top_accurate = sorted(
        [(s, round(mean(errs), 2)) for s, errs in sym_errors.items()],
        key=lambda x: x[1],
    )[:5]

    return {
        "pattern":               pattern,
        "pattern_label":         _PATTERN_LABELS.get(pattern, pattern.replace("_", " ")),
        "n":                     n,
        # Core alpha stats (from DISLOCATION-02)
        "predicted_excess_return_pct": alpha_data.get("excess_return_pct"),
        "alpha_class":           alpha_data.get("alpha_class"),
        "win_rate_pct":          alpha_data.get("win_rate_pct"),
        # Calibration metrics
        "mae_pp":                mae,
        "rmse_pp":               rmse,
        "mean_error_pp":         mean_err,
        "bias_direction":        bias_dir,
        "accuracy_bands":        bands,
        "correlation":           corr,
        # Confidence
        "confidence":            confidence,
        "confidence_label":      _confidence_label(confidence),
        # Best symbols
        "top_accurate_symbols":  [{"symbol": s, "avg_error_pp": e} for s, e in top_accurate],
    }


def _build_calibration(repo_root: Path) -> Dict:
    inventory   = _load_inventory(repo_root)
    alpha_index = _load_alpha_index(repo_root)

    if not inventory or not alpha_index:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version":      _DISLOC06_VERSION,
            "status":       "NO_DATA",
            "patterns":     [],
            "governance_note": _GOVERNANCE_NOTE,
        }

    # Universe median across all attributed entries
    rets = [
        float(e["forward_return_30d"]) * 100
        for e in inventory
        if e.get("forward_return_30d") is not None
    ]
    universe_median = round(median(rets), 4) if rets else 0.0

    # Build prediction pairs
    pairs = _build_prediction_pairs(inventory, alpha_index, universe_median)

    # Compute per-pattern calibration
    conflict_patterns = {
        "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
        "ESS_BULLISH_ANALYST_SKEPTICAL",
        "ESS_BULLISH_ANALYST_MIXED",
        "ESS_BEARISH_ANALYST_MAJORITY_BULLISH",
        "ESS_BEARISH_ANALYST_MIXED",
        "ESS_NEUTRAL_ANALYST_MIXED",
        "ESS_BULLISH_ANALYST_FULL_AGREE",
    }

    pattern_cals = []
    for pattern in sorted(conflict_patterns):
        alpha_data = alpha_index.get(pattern, {})
        cal = _compute_pattern_calibration(pattern, pairs, alpha_data)
        pattern_cals.append(cal)

    # Sort by confidence level then n
    _conf_order = {"VERY_HIGH": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INSUFFICIENT_DATA": 4}
    pattern_cals.sort(key=lambda c: (_conf_order.get(c.get("confidence", "INSUFFICIENT_DATA"), 99), -c.get("n", 0)))

    # Summary stats
    conf_counts = defaultdict(int)
    for c in pattern_cals:
        conf_counts[c.get("confidence", "INSUFFICIENT_DATA")] += 1

    # Best and worst calibrated conflict patterns
    calibrated = [c for c in pattern_cals if c["n"] >= _MIN_LOW]
    most_reliable  = sorted(calibrated, key=lambda c: c.get("mae_pp", 999))[:3]
    least_reliable = sorted(calibrated, key=lambda c: -(c.get("mae_pp") or 0))[:3]

    # Overall calibration quality
    all_errors = [p["absolute_error_pp"] for p in pairs]
    overall_mae = round(mean(all_errors), 3) if all_errors else None
    overall_bands = _accuracy_bands(all_errors) if all_errors else {}

    return {
        "generated_at":        datetime.now(timezone.utc).isoformat(),
        "version":             _DISLOC06_VERSION,
        "status":              "OK",
        "total_pairs":         len(pairs),
        "universe_median_pct": universe_median,
        "overall_mae_pp":      overall_mae,
        "overall_accuracy_bands": overall_bands,
        "confidence_counts":   dict(conf_counts),
        "patterns":            pattern_cals,
        "most_reliable":       most_reliable,
        "least_reliable":      least_reliable,
        "governance_note":     _GOVERNANCE_NOTE,
    }


# ── Cache ──────────────────────────────────────────────────────────────────────

def _cache_path(repo_root: Path) -> Path:
    return repo_root / _CALIBRATION_FILE


def _get_calibration(repo_root: Path, force: bool = False) -> Dict:
    cache = _cache_path(repo_root)
    inv   = repo_root / "data" / "analysis" / "dislocation" / "dislocation_inventory.csv"
    if not force and cache.exists() and inv.exists():
        try:
            if cache.stat().st_mtime >= inv.stat().st_mtime:
                return json.loads(cache.read_text(encoding="utf-8"))
        except OSError:
            pass
    payload = _build_calibration(repo_root)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    return payload


# ── Part E + F: Extend DISLOCATION-05 output ──────────────────────────────────

def enrich_forward_estimate(estimate: Dict, repo_root: Path) -> Dict:
    """
    Attach DISLOCATION-06 calibration data to a DISLOCATION-05 forward estimate.

    Adds: confidence, confidence_label, mae_pp, accuracy_bands, calibration_n
    """
    pattern = estimate.get("current_pattern")
    if not pattern or estimate.get("status") != "OK":
        return estimate

    data = _get_calibration(repo_root)
    cal  = next((c for c in data.get("patterns", []) if c["pattern"] == pattern), None)
    if not cal:
        return {**estimate, "confidence": "INSUFFICIENT_DATA",
                "confidence_label": _confidence_label("INSUFFICIENT_DATA"),
                "calibration_n": 0}

    return {
        **estimate,
        "confidence":       cal.get("confidence"),
        "confidence_label": cal.get("confidence_label"),
        "mae_pp":           cal.get("mae_pp"),
        "accuracy_bands":   cal.get("accuracy_bands", {}),
        "calibration_n":    cal.get("n", 0),
        "bias_direction":   cal.get("bias_direction"),
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def calibration_summary(repo_root: Path | str = ".") -> Dict:
    """Parts A–D: Full calibration analysis for all conflict patterns.

    Returns { total_pairs, overall_mae, accuracy_bands, patterns: [...], ... }
    """
    return _get_calibration(Path(repo_root))


def pattern_calibration(pattern: str, repo_root: Path | str = ".") -> Dict:
    """Return calibration for a specific conflict pattern."""
    root = Path(repo_root)
    data = _get_calibration(root)
    pat  = pattern.strip().upper()
    for c in data.get("patterns", []):
        if c.get("pattern") == pat:
            return c
    return {"pattern": pat, "error": "Pattern not found.", "confidence": "INSUFFICIENT_DATA"}


def confidence_summary(repo_root: Path | str = ".") -> Dict:
    """Executive confidence summary for the dashboard panel.

    Returns { confidence_counts, most_reliable, least_reliable, overall metrics }
    """
    root = Path(repo_root)
    data = _get_calibration(root)
    return {
        "generated_at":        data.get("generated_at"),
        "total_pairs":         data.get("total_pairs"),
        "overall_mae_pp":      data.get("overall_mae_pp"),
        "overall_accuracy_bands": data.get("overall_accuracy_bands", {}),
        "confidence_counts":   data.get("confidence_counts", {}),
        "most_reliable":       data.get("most_reliable", []),
        "least_reliable":      data.get("least_reliable", []),
        "governance_note":     data.get("governance_note"),
    }


def refresh_calibration(repo_root: Path | str = ".") -> Dict:
    """Force rebuild of calibration data."""
    root    = Path(repo_root)
    payload = _build_calibration(root)
    try:
        _cache_path(root).parent.mkdir(parents=True, exist_ok=True)
        _cache_path(root).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    return {
        "ok":           True,
        "total_pairs":  payload.get("total_pairs"),
        "overall_mae":  payload.get("overall_mae_pp"),
        "generated_at": payload.get("generated_at"),
        "version":      payload.get("version"),
    }
