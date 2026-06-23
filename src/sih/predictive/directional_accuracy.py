"""DISLOCATION-07 — Directional Accuracy Analysis.

Determines whether conflict patterns provide useful directional intelligence
even when return magnitude forecasts are unreliable (DISLOCATION-06 finding:
MAE 7.94pp, all patterns LOW confidence).

Key distinction:
  DISLOCATION-06 asked: "How accurate is the magnitude forecast?"
  DISLOCATION-07 asks:  "Is the direction forecast correct?"

A model can fail at predicting "+2.26% excess return" while still reliably
predicting "likely positive outcome" — the latter is what directional accuracy
measures.

Directional thresholds:
  - POSITIVE: predicted or realized excess return > +0.5pp
  - NEGATIVE: predicted or realized excess return < -0.5pp
  - NEUTRAL:  within ±0.5pp (near-median result)

Pattern reliability classification (by hit rate):
  - VERY_STRONG:       hit_rate >= 70%
  - STRONG:            hit_rate >= 60%
  - MODERATE:          hit_rate >= 55%
  - WEAK:              hit_rate < 55%
  - INSUFFICIENT_DATA: n < 20

Governance:
  - Read-only relative to ALL scoring and recommendation engines.
  - No ESS, CW-DAS, UCF, CRA, PAP, or governance logic is modified.
  - Directional accuracy findings are informational only.

Public API
----------
  directional_summary(repo_root)               → dict  (GET /api/predictive/directional-summary)
  pattern_directional(pattern, repo_root)      → dict  (GET /api/predictive/directional-accuracy/<pat>)
  directional_accuracy(repo_root)              → dict  (GET /api/predictive/directional-accuracy)
  refresh_directional(repo_root)               → dict  (POST /api/predictive/directional-refresh)
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Optional

_DIRECTIONAL_FILE = "data/analysis/dislocation/conflict_directional_accuracy.json"
_ALPHA_FILE       = "data/analysis/dislocation/conflict_alpha_report.json"
_DISLOC07_VERSION = "1.0"

# Direction thresholds (percentage points of excess return)
_DIR_POSITIVE_THRESHOLD =  0.5
_DIR_NEGATIVE_THRESHOLD = -0.5

# Minimum observations for reliability classification
_MIN_RELIABLE = 20

# Hit rate thresholds
_HR_VERY_STRONG = 70.0
_HR_STRONG      = 60.0
_HR_MODERATE    = 55.0

_GOVERNANCE_NOTE = (
    "DISLOCATION-07 is research-only. "
    "Directional accuracy metrics are derived from historical observations and do not "
    "guarantee future accuracy. No ESS, CW-DAS, UCF, CRA, Replay, PAP, or "
    "governance logic is modified. "
    "Reliability classifications are informational — operator judgment is required."
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

_CONFLICT_PATTERNS = {
    "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
    "ESS_BULLISH_ANALYST_SKEPTICAL",
    "ESS_BULLISH_ANALYST_MIXED",
    "ESS_BEARISH_ANALYST_MAJORITY_BULLISH",
    "ESS_BEARISH_ANALYST_MIXED",
    "ESS_NEUTRAL_ANALYST_MIXED",
    "ESS_BULLISH_ANALYST_FULL_AGREE",
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


# ── Part A: Direction classification ─────────────────────────────────────────

def _classify_direction(excess_return_pct: float) -> str:
    """Classify a return as POSITIVE, NEGATIVE, or NEUTRAL."""
    if excess_return_pct > _DIR_POSITIVE_THRESHOLD:
        return "POSITIVE"
    if excess_return_pct < _DIR_NEGATIVE_THRESHOLD:
        return "NEGATIVE"
    return "NEUTRAL"


def _predicted_direction(alpha_data: Dict) -> str:
    """
    Reconstruct predicted direction from DISLOCATION-02 alpha data.

    Uses the pattern's excess_return_pct (vs universe median) as the basis.
    A pattern predicting excess_return_pct > +0.5pp predicts POSITIVE outcome.
    """
    excess = _safe_float(alpha_data.get("excess_return_pct"))
    if excess is None:
        return "NEUTRAL"
    return _classify_direction(excess)


# ── Part B: Build prediction + outcome pairs ──────────────────────────────────

def _build_directional_pairs(
    inventory: List[Dict],
    alpha_index: Dict[str, Dict],
    universe_median: float,
) -> List[Dict]:
    """
    For each inventory entry with a realized return, attach:
      - predicted_direction (from alpha pattern's excess return)
      - actual_direction    (from realized excess return vs universe median)
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
        predicted_excess = _safe_float(alpha.get("excess_return_pct"))
        if predicted_excess is None:
            continue

        realized_pct    = round(ret_30_raw * 100, 4)
        realized_excess = round(realized_pct - universe_median, 4)

        pred_dir   = _classify_direction(predicted_excess)
        actual_dir = _classify_direction(realized_excess)
        is_hit     = pred_dir == actual_dir

        pairs.append({
            "symbol":               entry.get("symbol", ""),
            "prediction_date":      entry.get("snapshot_date", ""),
            "pattern":              pattern,
            "predicted_excess_pct": predicted_excess,
            "predicted_direction":  pred_dir,
            "realized_excess_pct":  realized_excess,
            "actual_direction":     actual_dir,
            "is_hit":               is_hit,
        })

    return pairs


# ── Part C: Directional accuracy metrics ──────────────────────────────────────

def _compute_directional_metrics(pairs: List[Dict]) -> Dict:
    """
    Compute hit rate, precision, recall, FPR, FNR, balanced accuracy for a
    set of prediction/outcome pairs.

    Metrics are computed with POSITIVE as the 'positive class'.
    """
    n = len(pairs)
    if n == 0:
        return {"n": 0, "hit_rate": None}

    hits = sum(1 for p in pairs if p["is_hit"])
    hit_rate = round(hits / n * 100, 1)

    # Confusion matrix (POSITIVE = positive class)
    tp = sum(1 for p in pairs if p["predicted_direction"] == "POSITIVE" and p["actual_direction"] == "POSITIVE")
    fp = sum(1 for p in pairs if p["predicted_direction"] == "POSITIVE" and p["actual_direction"] != "POSITIVE")
    tn = sum(1 for p in pairs if p["predicted_direction"] != "POSITIVE" and p["actual_direction"] != "POSITIVE")
    fn = sum(1 for p in pairs if p["predicted_direction"] != "POSITIVE" and p["actual_direction"] == "POSITIVE")

    precision       = round(tp / (tp + fp) * 100, 1) if (tp + fp) > 0 else None
    recall          = round(tp / (tp + fn) * 100, 1) if (tp + fn) > 0 else None
    fpr             = round(fp / (fp + tn) * 100, 1) if (fp + tn) > 0 else None
    fnr             = round(fn / (fn + tp) * 100, 1) if (fn + tp) > 0 else None

    # Balanced accuracy = (TPR + TNR) / 2
    tpr = recall  # same as recall
    tnr = round(tn / (tn + fp) * 100, 1) if (tn + fp) > 0 else None
    if tpr is not None and tnr is not None:
        balanced_accuracy = round((tpr + tnr) / 2, 1)
    else:
        balanced_accuracy = None

    # Direction distribution
    pred_dist = {
        "POSITIVE": sum(1 for p in pairs if p["predicted_direction"] == "POSITIVE"),
        "NEGATIVE": sum(1 for p in pairs if p["predicted_direction"] == "NEGATIVE"),
        "NEUTRAL":  sum(1 for p in pairs if p["predicted_direction"] == "NEUTRAL"),
    }
    actual_dist = {
        "POSITIVE": sum(1 for p in pairs if p["actual_direction"] == "POSITIVE"),
        "NEGATIVE": sum(1 for p in pairs if p["actual_direction"] == "NEGATIVE"),
        "NEUTRAL":  sum(1 for p in pairs if p["actual_direction"] == "NEUTRAL"),
    }

    return {
        "n":                  n,
        "hits":               hits,
        "hit_rate":           hit_rate,
        "precision":          precision,
        "recall":             recall,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "balanced_accuracy":  balanced_accuracy,
        "confusion_matrix":   {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "predicted_distribution":  pred_dist,
        "actual_distribution":     actual_dist,
    }


# ── Part D: Pattern reliability ranking ───────────────────────────────────────

def _reliability_class(n: int, hit_rate: Optional[float]) -> str:
    if n < _MIN_RELIABLE or hit_rate is None:
        return "INSUFFICIENT_DATA"
    if hit_rate >= _HR_VERY_STRONG:
        return "VERY_STRONG"
    if hit_rate >= _HR_STRONG:
        return "STRONG"
    if hit_rate >= _HR_MODERATE:
        return "MODERATE"
    return "WEAK"


def _reliability_label(cls: str) -> str:
    return {
        "VERY_STRONG":       "Highly reliable — directionally correct ≥70% of the time",
        "STRONG":            "Reliable — directionally correct ≥60% of the time",
        "MODERATE":          "Moderately reliable — directionally correct ≥55% of the time",
        "WEAK":              "Low reliability — directional accuracy below chance threshold",
        "INSUFFICIENT_DATA": "Insufficient data for directional reliability classification",
    }.get(cls, cls)


# ── Core computation ───────────────────────────────────────────────────────────

def _compute_pattern_directional(
    pattern: str,
    pairs: List[Dict],
    alpha_data: Dict,
) -> Dict:
    """Compute full directional accuracy stats for one pattern."""
    pattern_pairs = [p for p in pairs if p["pattern"] == pattern]
    metrics = _compute_directional_metrics(pattern_pairs)
    n = metrics["n"]

    rel_class = _reliability_class(n, metrics.get("hit_rate"))

    # Predicted direction for this pattern (single value — all pairs share the same prediction)
    pred_dir = _predicted_direction(alpha_data)

    return {
        "pattern":              pattern,
        "pattern_label":        _PATTERN_LABELS.get(pattern, pattern.replace("_", " ")),
        "n":                    n,
        # DISLOCATION-02 alpha context
        "predicted_excess_pct": alpha_data.get("excess_return_pct"),
        "predicted_direction":  pred_dir,
        "alpha_class":          alpha_data.get("alpha_class"),
        "win_rate_pct":         alpha_data.get("win_rate_pct"),
        # Directional accuracy
        **{k: v for k, v in metrics.items() if k != "n"},
        # Reliability
        "reliability":          rel_class,
        "reliability_label":    _reliability_label(rel_class),
    }


# ── Part G: Comparative analysis ──────────────────────────────────────────────

def _comparative_analysis(
    directional_patterns: List[Dict],
    calibration_data: Optional[Dict],
) -> Dict:
    """
    Compare directional accuracy vs magnitude accuracy (from DISLOCATION-06).
    Goal: determine whether conflict intelligence is better suited for
    direction forecasting or magnitude forecasting.
    """
    # Collect comparable patterns
    comparable = []
    cal_index = {}
    if calibration_data:
        cal_index = {p["pattern"]: p for p in calibration_data.get("patterns", [])}

    for dp in directional_patterns:
        pat = dp["pattern"]
        cal = cal_index.get(pat, {})
        if dp["n"] == 0:
            continue
        comparable.append({
            "pattern":            pat,
            "pattern_label":      dp["pattern_label"],
            "n":                  dp["n"],
            "directional_hit_rate": dp.get("hit_rate"),
            "directional_reliability": dp.get("reliability"),
            "magnitude_mae_pp":   cal.get("mae_pp"),
            "magnitude_confidence": cal.get("confidence"),
        })

    # Aggregate verdict
    dir_hit_rates  = [c["directional_hit_rate"] for c in comparable if c["directional_hit_rate"] is not None]
    mag_maes       = [c["magnitude_mae_pp"] for c in comparable if c["magnitude_mae_pp"] is not None]

    avg_hit_rate   = round(mean(dir_hit_rates), 1)  if dir_hit_rates else None
    avg_mae        = round(mean(mag_maes), 3)        if mag_maes      else None

    # Interpretation
    if avg_hit_rate is not None and avg_hit_rate >= _HR_STRONG:
        verdict = "DIRECTIONAL"
        verdict_label = (
            "Conflict patterns are better suited for directional guidance than "
            "magnitude forecasting. The average directional hit rate exceeds 60%, "
            "while magnitude forecasts have high MAE."
        )
    elif avg_hit_rate is not None and avg_hit_rate >= _HR_MODERATE:
        verdict = "DIRECTIONAL_MARGINAL"
        verdict_label = (
            "Conflict patterns show modest directional predictive value (hit rate ≥55%), "
            "but directional reliability is limited. Magnitude forecasting remains unreliable."
        )
    else:
        verdict = "NEITHER"
        verdict_label = (
            "Conflict patterns do not demonstrate reliable directional or magnitude "
            "predictive accuracy at the individual security level."
        )

    return {
        "patterns":           comparable,
        "avg_directional_hit_rate": avg_hit_rate,
        "avg_magnitude_mae_pp":     avg_mae,
        "verdict":            verdict,
        "verdict_label":      verdict_label,
    }


# ── Core builder ──────────────────────────────────────────────────────────────

def _build_directional_analysis(repo_root: Path) -> Dict:
    inventory   = _load_inventory(repo_root)
    alpha_index = _load_alpha_index(repo_root)

    if not inventory or not alpha_index:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version":      _DISLOC07_VERSION,
            "status":       "NO_DATA",
            "patterns":     [],
            "governance_note": _GOVERNANCE_NOTE,
        }

    # Universe median
    rets = [
        float(e["forward_return_30d"]) * 100
        for e in inventory
        if e.get("forward_return_30d") is not None
    ]
    universe_median = round(median(rets), 4) if rets else 0.0

    # Build directional pairs
    pairs = _build_directional_pairs(inventory, alpha_index, universe_median)

    # Per-pattern analysis
    pattern_results = []
    for pattern in sorted(_CONFLICT_PATTERNS):
        alpha_data = alpha_index.get(pattern, {})
        result = _compute_pattern_directional(pattern, pairs, alpha_data)
        pattern_results.append(result)

    # Sort by hit_rate desc, then n desc
    pattern_results.sort(
        key=lambda r: (-(r.get("hit_rate") or 0), -r.get("n", 0))
    )

    # Overall metrics
    overall_metrics = _compute_directional_metrics(pairs)

    # Reliability distribution
    rel_dist: Dict[str, int] = defaultdict(int)
    for r in pattern_results:
        rel_dist[r["reliability"]] += 1

    # Most/least reliable (by hit rate, min n)
    ranked = [r for r in pattern_results if r["n"] >= _MIN_RELIABLE and r.get("hit_rate") is not None]
    most_reliable  = sorted(ranked, key=lambda r: -(r.get("hit_rate") or 0))[:3]
    least_reliable = sorted(ranked, key=lambda r:  (r.get("hit_rate") or 100))[:3]

    # Load DISLOCATION-06 for comparative analysis
    calibration_data = None
    try:
        from src.sih.predictive.conflict_alpha_calibration import calibration_summary
        calibration_data = calibration_summary(repo_root)
    except Exception:
        pass

    comparison = _comparative_analysis(pattern_results, calibration_data)

    return {
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "version":            _DISLOC07_VERSION,
        "status":             "OK",
        "total_pairs":        len(pairs),
        "universe_median_pct": universe_median,
        "direction_thresholds": {
            "positive_above_pp": _DIR_POSITIVE_THRESHOLD,
            "negative_below_pp": _DIR_NEGATIVE_THRESHOLD,
        },
        "overall":            overall_metrics,
        "reliability_distribution": dict(rel_dist),
        "patterns":           pattern_results,
        "most_reliable":      most_reliable,
        "least_reliable":     least_reliable,
        "comparative":        comparison,
        "governance_note":    _GOVERNANCE_NOTE,
    }


# ── Cache ──────────────────────────────────────────────────────────────────────

def _cache_path(repo_root: Path) -> Path:
    return repo_root / _DIRECTIONAL_FILE


def _get_analysis(repo_root: Path, force: bool = False) -> Dict:
    cache = _cache_path(repo_root)
    inv   = repo_root / "data" / "analysis" / "dislocation" / "dislocation_inventory.csv"
    if not force and cache.exists() and inv.exists():
        try:
            if cache.stat().st_mtime >= inv.stat().st_mtime:
                return json.loads(cache.read_text(encoding="utf-8"))
        except OSError:
            pass
    payload = _build_directional_analysis(repo_root)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    return payload


# ── Part E: Extend DISLOCATION-03/05 output ───────────────────────────────────

def enrich_with_directional(estimate: Dict, repo_root: Path) -> Dict:
    """
    Attach DISLOCATION-07 directional accuracy data to a DISLOCATION-05 forward
    estimate (or DISLOCATION-03 security card).

    Adds: directional_hit_rate, directional_reliability, predicted_direction
    """
    pattern = estimate.get("current_pattern")
    if not pattern or estimate.get("status") != "OK":
        return estimate

    data = _get_analysis(repo_root)
    pat  = next((p for p in data.get("patterns", []) if p["pattern"] == pattern), None)
    if not pat:
        return {**estimate, "directional_reliability": "INSUFFICIENT_DATA",
                "directional_hit_rate": None, "predicted_direction": None}

    return {
        **estimate,
        "predicted_direction":     pat.get("predicted_direction"),
        "directional_hit_rate":    pat.get("hit_rate"),
        "directional_reliability": pat.get("reliability"),
        "directional_reliability_label": pat.get("reliability_label"),
        "balanced_accuracy":       pat.get("balanced_accuracy"),
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def directional_accuracy(repo_root: str | Path = ".") -> Dict:
    """Full directional accuracy analysis for all conflict patterns.

    GET /api/predictive/directional-accuracy
    """
    return _get_analysis(Path(repo_root))


def pattern_directional(pattern: str, repo_root: str | Path = ".") -> Dict:
    """Directional accuracy for a specific conflict pattern.

    GET /api/predictive/directional-accuracy/<pattern>
    """
    root = Path(repo_root)
    data = _get_analysis(root)
    pat  = pattern.strip().upper()
    for p in data.get("patterns", []):
        if p.get("pattern") == pat:
            return p
    return {"pattern": pat, "error": "Pattern not found.", "reliability": "INSUFFICIENT_DATA"}


def directional_summary(repo_root: str | Path = ".") -> Dict:
    """Summary view: overall hit rate, verdict, most/least reliable patterns.

    GET /api/predictive/directional-summary
    """
    data   = _get_analysis(Path(repo_root))
    overall = data.get("overall", {})
    comp    = data.get("comparative", {})
    return {
        "generated_at":              data.get("generated_at"),
        "total_pairs":               data.get("total_pairs"),
        "overall_hit_rate":          overall.get("hit_rate"),
        "overall_balanced_accuracy": overall.get("balanced_accuracy"),
        "overall_precision":         overall.get("precision"),
        "overall_recall":            overall.get("recall"),
        "reliability_distribution":  data.get("reliability_distribution", {}),
        "most_reliable":             data.get("most_reliable", []),
        "least_reliable":            data.get("least_reliable", []),
        "verdict":                   comp.get("verdict"),
        "verdict_label":             comp.get("verdict_label"),
        "avg_directional_hit_rate":  comp.get("avg_directional_hit_rate"),
        "avg_magnitude_mae_pp":      comp.get("avg_magnitude_mae_pp"),
        "patterns":                  data.get("patterns", []),
        "governance_note":           _GOVERNANCE_NOTE,
    }


def refresh_directional(repo_root: str | Path = ".") -> Dict:
    """Force-rebuild and re-cache the directional accuracy analysis.

    POST /api/predictive/directional-refresh
    """
    root    = Path(repo_root)
    payload = _get_analysis(root, force=True)
    return {
        "ok":           payload.get("status") == "OK",
        "total_pairs":  payload.get("total_pairs"),
        "overall_hit_rate": payload.get("overall", {}).get("hit_rate"),
        "verdict":      payload.get("comparative", {}).get("verdict"),
        "generated_at": payload.get("generated_at"),
        "version":      payload.get("version"),
    }
