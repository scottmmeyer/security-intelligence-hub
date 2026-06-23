"""DISLOCATION-02 — Conflict Alpha Attribution.

Quantifies excess return generation by signal conflict pattern.

For each conflict pattern, computes:
  - average return vs. universe median (excess return / alpha)
  - win rate and consistency
  - a simple t-statistic for statistical significance (≥5 observations)
  - alpha classification: ALPHA_LEADER / ALPHA_NEUTRAL / ALPHA_LAGGARD

Reads from:
  - data/analysis/dislocation/dislocation_inventory.csv  (written by ISSUE-12D)
  - data/analysis/dislocation/pattern_outcomes.json      (written by ISSUE-12D)

Writes (fully regeneratable):
  - data/analysis/dislocation/conflict_alpha_report.json

Governance:
  - Read-only relative to ALL scoring engines.
  - No changes to ESS, CW-DAS, UCF, CRA, Replay, PAP, or Governance.
  - Research / learning output only.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Dict, List, Optional, Tuple

# ── Constants ──────────────────────────────────────────────────────────────────

_ALPHA_VERSION = "1.0"

# Minimum observations to compute stats meaningfully
_MIN_OBS_FOR_STATS = 5

# Minimum |t-statistic| for "statistically noteworthy" classification
_TSTAT_NOTEWORTHY = 1.5

# Alpha thresholds vs universe median (percentage points)
_ALPHA_LEADER_THRESHOLD  =  1.0   # excess return > +1.0pp → ALPHA_LEADER
_ALPHA_LAGGARD_THRESHOLD = -1.0   # excess return < -1.0pp → ALPHA_LAGGARD

_DISLOCATION_DIR = "data/analysis/dislocation"

# ── Pattern label mapping (mirrors signal_conflict_review.py) ─────────────────

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

# Whether the pattern represents a genuine signal conflict
_CONFLICT_PATTERNS = {
    "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
    "ESS_BULLISH_ANALYST_SKEPTICAL",
    "ESS_BULLISH_ANALYST_MIXED",
    "ESS_BEARISH_ANALYST_MAJORITY_BULLISH",
    "ESS_BEARISH_ANALYST_MIXED",
    "ESS_NEUTRAL_ANALYST_BULLISH",
    "ESS_NEUTRAL_ANALYST_BEARISH",
    "ESS_NEUTRAL_ANALYST_MIXED",
}


# ── Statistical helpers ────────────────────────────────────────────────────────

def _t_statistic(values: List[float], mu: float) -> Optional[float]:
    """One-sample t-statistic: (mean - mu) / (std / sqrt(n)).
    Returns None if insufficient data or zero variance.
    """
    n = len(values)
    if n < 2:
        return None
    sample_mean = mean(values)
    # Population stdev with ddof correction (sample stdev)
    s = pstdev(values) * math.sqrt(n / (n - 1))
    if s == 0:
        return None
    return round((sample_mean - mu) / (s / math.sqrt(n)), 3)


def _consistency_score(returns: List[float], universe_median: float) -> float:
    """Fraction of observations that beat the universe median.
    Range [0, 1]; 0.5 = no edge.
    """
    if not returns:
        return 0.5
    beats = sum(1 for r in returns if r > universe_median)
    return round(beats / len(returns), 4)


def _alpha_class(excess_return_pct: float, t_stat: Optional[float]) -> str:
    """Classify pattern as ALPHA_LEADER / ALPHA_NEUTRAL / ALPHA_LAGGARD."""
    if excess_return_pct > _ALPHA_LEADER_THRESHOLD:
        return "ALPHA_LEADER"
    if excess_return_pct < _ALPHA_LAGGARD_THRESHOLD:
        return "ALPHA_LAGGARD"
    return "ALPHA_NEUTRAL"


def _significance_label(t_stat: Optional[float]) -> str:
    if t_stat is None:
        return "INSUFFICIENT_DATA"
    abs_t = abs(t_stat)
    if abs_t >= 2.0:
        return "NOTEWORTHY"      # p ≈ 0.05 range for moderate n
    if abs_t >= _TSTAT_NOTEWORTHY:
        return "SUGGESTIVE"      # directional but not strong
    return "WEAK"


def _insight_text(pattern: str, alpha_class: str, excess_ret: float,
                  win_rate: float, t_stat: Optional[float],
                  ess_direction: str) -> str:
    """Generate plain-language insight for a conflict pattern."""
    label = _PATTERN_LABELS.get(pattern, pattern.replace("_", " "))
    direction = "outperformed" if alpha_class == "ALPHA_LEADER" else (
        "underperformed" if alpha_class == "ALPHA_LAGGARD" else "performed in-line with"
    )
    ess_verb = "bullish" if ess_direction == "BULLISH" else (
        "bearish" if ess_direction == "BEARISH" else "neutral"
    )
    sig = _significance_label(t_stat)

    text = (
        f"When {label.lower()} conflicts occurred, the position {direction} "
        f"the universe median by {excess_ret:+.1f}pp on average "
        f"(30d forward return), with a {win_rate:.0f}% above-median rate. "
    )
    if sig == "NOTEWORTHY":
        text += "The pattern shows a statistically noteworthy return differential. "
    elif sig == "SUGGESTIVE":
        text += "The pattern is suggestive but based on limited observations. "
    else:
        text += "Insufficient data for strong statistical conclusions. "

    if alpha_class == "ALPHA_LEADER":
        text += (
            f"Historical evidence suggests that when ESS is {ess_verb} and "
            f"analysts disagree, the ESS direction was associated with positive excess returns. "
            f"Operator note: ESS signal may be more informative than analyst consensus "
            f"in this conflict configuration."
        )
    elif alpha_class == "ALPHA_LAGGARD":
        text += (
            f"Historical evidence suggests that when ESS is {ess_verb} and "
            f"analysts conflict, this pattern was associated with negative excess returns. "
            f"Operator note: Analyst consensus may warrant additional weight "
            f"in this conflict configuration."
        )
    else:
        text += "No material alpha advantage identified for this conflict pattern."

    return text


# ── Core computation ───────────────────────────────────────────────────────────

def _load_inventory(repo_root: Path) -> List[Dict]:
    """Load the ISSUE-12D inventory CSV."""
    from src.sih.signal_conflict_review import load_inventory
    return load_inventory(repo_root)


def _universe_median_return(inventory: List[Dict]) -> float:
    """30d median return across the full inventory (all symbols all dates)."""
    rets = [e["forward_return_30d"] for e in inventory
            if e.get("forward_return_30d") is not None]
    if not rets:
        return 0.0
    return median(rets)


def compute_conflict_alpha(repo_root: Path) -> Dict:
    """
    Full alpha attribution computation.

    Returns a dict suitable for JSON serialisation with:
      - universe_median_return_pct
      - patterns:  [per-pattern alpha analysis]
      - leaders:   top 3 alpha leaders (conflict patterns only)
      - laggards:  bottom 3 alpha laggards (conflict patterns only)
      - baseline:  non-conflict patterns for comparison
      - governance_note
    """
    inventory = _load_inventory(repo_root)

    if not inventory:
        return {
            "generated_at":             datetime.now(timezone.utc).isoformat(),
            "version":                  _ALPHA_VERSION,
            "universe_median_return_pct": None,
            "patterns":                 [],
            "leaders":                  [],
            "laggards":                 [],
            "baseline":                 [],
            "governance_note":          _GOVERNANCE_NOTE,
            "status":                   "NO_DATA",
        }

    universe_median = _universe_median_return(inventory)
    universe_median_pct = round(universe_median * 100, 4)

    # Group inventory entries by signal_pattern
    by_pattern: Dict[str, List[float]] = defaultdict(list)
    by_pattern_entries: Dict[str, List[Dict]] = defaultdict(list)

    for entry in inventory:
        pattern = entry.get("signal_pattern", "")
        ret = entry.get("forward_return_30d")
        if not pattern or ret is None:
            continue
        by_pattern[pattern].append(float(ret))
        by_pattern_entries[pattern].append(entry)

    results = []
    for pattern, rets in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
        n = len(rets)
        rets_pct = [r * 100 for r in rets]
        avg_ret = round(mean(rets_pct), 4) if rets else None
        med_ret = round(median(rets_pct), 4) if rets else None
        excess  = round(avg_ret - universe_median_pct, 4) if avg_ret is not None else None
        t_stat  = _t_statistic(rets_pct, universe_median_pct)
        consistency = _consistency_score(rets, universe_median)
        win_rate = round(consistency * 100, 1)

        # Best/worst
        best    = round(max(rets_pct), 4) if rets_pct else None
        worst   = round(min(rets_pct), 4) if rets_pct else None

        alpha_cls  = _alpha_class(excess or 0.0, t_stat) if excess is not None else "ALPHA_NEUTRAL"
        sig_label  = _significance_label(t_stat)

        # ESS direction for this pattern
        ess_dir = "BULLISH" if "ESS_BULLISH" in pattern else (
            "BEARISH" if "ESS_BEARISH" in pattern else "NEUTRAL"
        )

        is_conflict = pattern in _CONFLICT_PATTERNS
        insight = _insight_text(pattern, alpha_cls, excess or 0.0, win_rate, t_stat, ess_dir)

        # Top symbols that beat universe median for this pattern
        winners = [e for e in by_pattern_entries[pattern]
                   if e.get("forward_return_30d") is not None
                   and e["forward_return_30d"] > universe_median]
        sym_freq: Dict[str, int] = defaultdict(int)
        for e in winners:
            sym_freq[e["symbol"]] += 1
        top_symbols = sorted(sym_freq.keys(), key=lambda s: -sym_freq[s])[:5]

        results.append({
            "signal_pattern":           pattern,
            "pattern_label":            _PATTERN_LABELS.get(pattern, pattern.replace("_", " ")),
            "is_conflict_pattern":      is_conflict,
            "ess_direction":            ess_dir,
            "observations":             n,
            "avg_return_30d_pct":       avg_ret,
            "median_return_30d_pct":    med_ret,
            "universe_median_pct":      universe_median_pct,
            "excess_return_pct":        excess,
            "win_rate_pct":             win_rate,
            "consistency_score":        consistency,
            "best_return_30d_pct":      best,
            "worst_return_30d_pct":     worst,
            "t_statistic":              t_stat,
            "significance":             sig_label,
            "alpha_class":              alpha_cls,
            "insight":                  insight,
            "top_symbols":              top_symbols,
        })

    # Separate conflict vs baseline
    conflict_results  = [r for r in results if r["is_conflict_pattern"]]
    baseline_results  = [r for r in results if not r["is_conflict_pattern"]]

    # Leaders (conflict patterns with highest excess return)
    leaders  = sorted(conflict_results, key=lambda r: -(r["excess_return_pct"] or -999))[:3]
    laggards = sorted(conflict_results, key=lambda r:  (r["excess_return_pct"] or 999))[:3]

    # Comparative insight: best conflict vs baseline
    conflict_avg_excess = (
        round(mean(r["excess_return_pct"] for r in conflict_results
                   if r["excess_return_pct"] is not None), 4)
        if conflict_results else None
    )
    baseline_avg = (
        round(mean(r["avg_return_30d_pct"] for r in baseline_results
                   if r["avg_return_30d_pct"] is not None), 4)
        if baseline_results else None
    )

    return {
        "generated_at":               datetime.now(timezone.utc).isoformat(),
        "version":                    _ALPHA_VERSION,
        "universe_median_return_pct": universe_median_pct,
        "conflict_avg_excess_pct":    conflict_avg_excess,
        "baseline_avg_return_pct":    baseline_avg,
        "patterns":                   results,
        "leaders":                    leaders,
        "laggards":                   laggards,
        "baseline":                   baseline_results,
        "governance_note":            _GOVERNANCE_NOTE,
        "status":                     "OK",
    }


_GOVERNANCE_NOTE = (
    "DISLOCATION-02 is research-only. "
    "No ESS, CW-DAS, UCF, CRA, Replay, PAP, or governance logic is modified. "
    "Excess return and alpha classification are derived from historical observations "
    "in the SIH ESS archive and may not be predictive of future outcomes. "
    "Operator judgment is required before acting on any finding."
)


# ── Public API ─────────────────────────────────────────────────────────────────

def conflict_alpha_report(repo_root: Path | str = ".") -> Dict:
    """
    Compute or load conflict alpha analysis.

    Returns the full alpha attribution report dict.
    Caches result at data/analysis/dislocation/conflict_alpha_report.json.
    Cache is invalidated whenever dislocation_inventory.csv changes.
    """
    root = Path(repo_root)
    cache_path    = root / _DISLOCATION_DIR / "conflict_alpha_report.json"
    inventory_csv = root / _DISLOCATION_DIR / "dislocation_inventory.csv"

    # Cache validity: alpha report is newer than inventory
    if cache_path.exists() and inventory_csv.exists():
        try:
            if cache_path.stat().st_mtime >= inventory_csv.stat().st_mtime:
                return json.loads(cache_path.read_text(encoding="utf-8"))
        except OSError:
            pass

    report = compute_conflict_alpha(root)

    # Persist
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        pass

    return report
