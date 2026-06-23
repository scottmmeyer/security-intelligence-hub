"""PA-006B — Allocation Drift Intelligence & Persistent Violation Analytics.

Transforms allocation drift from a static compliance report into portfolio-
management intelligence: trend classification, momentum scoring, violation
persistence, priority ranking, and historical learning.

Architectural constraints:
  - READ-ONLY relative to all existing artifacts.
  - No changes to CRA, PAP, ESS, CW-DAS, Replay, UCF, governance rules, or
    allocation targets.
  - Consumes PAR alignment.csv rows (same source as PA-006A allocation_drift.py).
  - Writes only derived cache artifacts under data/history/pis/pa006b/:
      drift_intelligence.json   — fully regeneratable
      allocation_drift_learning.json — fully regeneratable

Public API
----------
  drift_trends(repo_root)         → dict   (trend classification per node)
  drift_priorities(repo_root)     → dict   (top-10 attention ranking)
  drift_chronic(repo_root)        → dict   (chronic / structural violations)
  drift_momentum(repo_root)       → dict   (momentum scores per node)
  drift_intelligence_summary(repo_root) → dict (executive summary)
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Optional, Tuple

# ── Constants ──────────────────────────────────────────────────────────────────

_STABLE_THRESHOLD_PP = 0.5       # abs drift change below this → STABLE

_OSCILLATING_THRESHOLD = 2       # ≥ this many direction reversals → OSCILLATING

# Persistence classifications (observations in violation)
_TEMPORARY_MAX   = 2
_RECURRING_MAX   = 5
_CHRONIC_MAX     = 11            # < CHRONIC_MAX → CHRONIC; ≥ CHRONIC_MAX → STRUCTURAL

# Priority formula weights
_W_SEVERITY = 35.0
_W_PERSISTENCE = 25.0
_W_MOMENTUM = 25.0
_W_MAGNITUDE = 15.0

_CACHE_DIR = "data/history/pis/pa006b"
_INTELLIGENCE_CACHE = "drift_intelligence.json"
_LEARNING_CACHE     = "allocation_drift_learning.json"

# Fraction of history in violation → STRUCTURAL
_STRUCTURAL_FRACTION = 0.75


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HistoryEntry:
    snapshot_date: str
    actual_pct:    float
    target_pct:    float
    drift_pct:     float   # actual - target


@dataclass(frozen=True)
class DriftTrend:
    """Full trend profile for one allocation node."""
    node_key:              str
    node_label:            str
    dimension_type:        str

    # Raw history
    dates_available:       int
    current_drift_pct:     float
    current_actual_pct:    float
    current_target_pct:    float

    # Part A — Trend classification
    trend:                 str       # IMPROVING | DETERIORATING | STABLE | OSCILLATING

    # Part B — Momentum score
    momentum_score:        float     # -100 to +100

    # Part C — Persistence
    violation_count:       int       # observations with |drift| > threshold
    persistence_pct:       float     # violation_count / dates_available
    persistence_class:     str       # TEMPORARY | RECURRING | CHRONIC | STRUCTURAL | NONE

    # Part F — Historical learning
    first_violation_date:  Optional[str]
    worst_drift_pct:       float     # highest abs drift observed
    best_drift_pct:        float     # lowest abs drift observed
    avg_drift_pct:         float
    max_drift_pct:         float     # signed max

    # Derived
    drift_direction:       str       # OVERWEIGHT | UNDERWEIGHT | ON_TARGET
    severity:              str       # NONE | MINOR | MODERATE | SIGNIFICANT | CRITICAL


@dataclass(frozen=True)
class PriorityItem:
    """Single entry in the priority ranking."""
    rank:              int
    node_key:          str
    node_label:        str
    priority_score:    float        # 0–100
    primary_reason:    str
    trend:             str
    persistence_class: str
    severity:          str
    current_drift_pct: float
    momentum_score:    float


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _par_runs_dir(repo_root: Path) -> Path:
    return repo_root / "data" / "portfolio_ingestion" / "analysis_runs"


def _collect_canonical_runs(repo_root: Path) -> List[Tuple[str, Path]]:
    """Return [(snapshot_date, alignment_csv_path), ...] sorted ascending.
    Mirrors allocation_drift._collect_canonical_runs logic.
    """
    par_dir = _par_runs_dir(repo_root)
    if not par_dir.exists():
        return []

    by_date: Dict[str, Tuple[str, Path]] = {}
    for par_path in par_dir.iterdir():
        if not par_path.is_dir():
            continue
        meta_file  = par_path / "run_metadata.json"
        align_file = par_path / "alignment.csv"
        if not meta_file.exists() or not align_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        snapshot_date = str(meta.get("snapshot_date", ""))[:10]
        if len(snapshot_date) != 10:
            continue
        try:
            date.fromisoformat(snapshot_date)
        except ValueError:
            continue
        created_at = str(meta.get("created_at_utc", ""))
        if snapshot_date not in by_date or created_at > by_date[snapshot_date][0]:
            by_date[snapshot_date] = (created_at, align_file)

    return [(d, by_date[d][1]) for d in sorted(by_date.keys())]


def _build_node_history(
    canonical_runs: List[Tuple[str, Path]],
) -> Dict[str, Tuple[str, str, List[HistoryEntry]]]:
    """Return {node_key: (label, dimension_type, [HistoryEntry])}, dates ascending."""
    acc: Dict[str, Tuple[str, str, List[HistoryEntry]]] = {}
    for snapshot_date, align_path in canonical_runs:
        for row in _read_csv_rows(align_path):
            nk = str(row.get("node_key") or "").strip()
            if not nk:
                continue
            actual = _safe_float(row.get("effective_actual_pct")) or _safe_float(row.get("actual_pct"))
            target = _safe_float(row.get("tactical_target_pct")) or _safe_float(row.get("target_pct"))
            if actual is None or target is None:
                continue
            label  = str(row.get("node_label") or nk).strip()
            dim    = str(row.get("dimension_type") or "").strip()
            entry  = HistoryEntry(snapshot_date, actual, target, round(actual - target, 4))
            if nk not in acc:
                acc[nk] = (label, dim, [])
            acc[nk][2].append(entry)
    return acc


# ── Part A — Trend classification ─────────────────────────────────────────────

def _classify_trend(drifts: List[float]) -> str:
    """Classify drift trend from oldest to newest drift values.

    IMPROVING   — signed magnitude moving toward 0 overall
    DETERIORATING — signed magnitude moving away from 0 overall
    OSCILLATING — repeated direction reversals (≥2)
    STABLE      — no meaningful directional change
    """
    if len(drifts) < 2:
        return "STABLE"

    # Count direction reversals in the drift sequence
    reversals = 0
    for i in range(1, len(drifts) - 1):
        prev_sign = drifts[i - 1] >= 0
        curr_sign = drifts[i]     >= 0
        next_sign = drifts[i + 1] >= 0
        if curr_sign != prev_sign and curr_sign != next_sign:
            reversals += 1
    if reversals >= _OSCILLATING_THRESHOLD:
        return "OSCILLATING"

    # Compare first half vs second half absolute magnitude
    mid = len(drifts) // 2
    first_half_avg  = mean(abs(d) for d in drifts[:mid])
    second_half_avg = mean(abs(d) for d in drifts[mid:])
    delta = second_half_avg - first_half_avg

    if delta < -_STABLE_THRESHOLD_PP:
        return "IMPROVING"
    if delta > _STABLE_THRESHOLD_PP:
        return "DETERIORATING"
    return "STABLE"


# ── Part B — Momentum score ────────────────────────────────────────────────────

def _compute_momentum(drifts: List[float]) -> float:
    """Compute momentum score in range [-100, +100].

    Positive = improving (drift magnitude decreasing).
    Negative = deteriorating (drift magnitude increasing).
    Zero     = stable.

    Uses weighted slope of absolute drift values, normalised to [-100, +100].
    """
    if len(drifts) < 2:
        return 0.0

    abs_drifts = [abs(d) for d in drifts]
    n = len(abs_drifts)

    # Weighted linear regression slope (recent observations weighted higher)
    weights = list(range(1, n + 1))
    w_sum  = sum(weights)
    w_xsum = sum(weights[i] * i for i in range(n))
    w_ysum = sum(weights[i] * abs_drifts[i] for i in range(n))
    w_xxsum = sum(weights[i] * i * i for i in range(n))
    w_xysum = sum(weights[i] * i * abs_drifts[i] for i in range(n))

    denom = w_sum * w_xxsum - w_xsum ** 2
    if abs(denom) < 1e-9:
        return 0.0

    slope = (w_sum * w_xysum - w_xsum * w_ysum) / denom

    # Normalise: clamp slope to ±5pp/period → maps to ±100
    raw = -slope / 5.0 * 100.0     # negative slope = improving = positive score
    return round(max(-100.0, min(100.0, raw)), 2)


# ── Part C — Persistence classification ───────────────────────────────────────

_VIOLATION_THRESHOLD_PP = 0.5   # |drift| above this = in violation

def _classify_persistence(violation_count: int, total: int) -> str:
    if violation_count == 0:
        return "NONE"
    fraction = violation_count / total if total > 0 else 0.0
    if fraction >= _STRUCTURAL_FRACTION:
        return "STRUCTURAL"
    if violation_count > _CHRONIC_MAX:
        # > 11 observations in violation (and below structural fraction)
        return "CHRONIC"
    if violation_count > _RECURRING_MAX:
        # 6–11 observations
        return "CHRONIC"
    if violation_count > _TEMPORARY_MAX:
        # 3–5 observations
        return "RECURRING"
    # 1–2 observations
    return "TEMPORARY"


def _severity_label(abs_drift: float) -> str:
    if abs_drift < 0.5:   return "NONE"
    if abs_drift < 2.0:   return "MINOR"
    if abs_drift < 5.0:   return "MODERATE"
    if abs_drift < 10.0:  return "SIGNIFICANT"
    return "CRITICAL"


def _drift_direction(drift: float) -> str:
    if abs(drift) < 0.05:
        return "ON_TARGET"
    return "OVERWEIGHT" if drift > 0 else "UNDERWEIGHT"


# ── Part D — Priority score ────────────────────────────────────────────────────

_SEVERITY_SCORES = {"NONE": 0, "MINOR": 20, "MODERATE": 50, "SIGNIFICANT": 80, "CRITICAL": 100}
_PERSISTENCE_SCORES = {"NONE": 0, "TEMPORARY": 15, "RECURRING": 40, "CHRONIC": 70, "STRUCTURAL": 100}

def _compute_priority_score(dt: DriftTrend) -> float:
    """Compute attention priority score 0–100."""
    sev_score  = _SEVERITY_SCORES.get(dt.severity, 0)
    pers_score = _PERSISTENCE_SCORES.get(dt.persistence_class, 0)
    # Momentum contribution: deteriorating gets bonus, improving gets penalty
    mom_penalty = max(0.0, -dt.momentum_score)  # deteriorating → large positive
    mom_bonus   = max(0.0,  dt.momentum_score)  # improving    → penalty on priority
    mom_contrib = (mom_penalty - mom_bonus * 0.3) / 100.0 * _W_MOMENTUM

    mag_contrib = min(abs(dt.current_drift_pct) / 20.0 * _W_MAGNITUDE, _W_MAGNITUDE)

    raw = (
        sev_score  / 100.0 * _W_SEVERITY +
        pers_score / 100.0 * _W_PERSISTENCE +
        mom_contrib +
        mag_contrib
    )
    return round(min(100.0, max(0.0, raw)), 2)


def _primary_reason(dt: DriftTrend) -> str:
    """Generate a one-line primary reason for priority ranking."""
    parts = []
    if dt.trend == "DETERIORATING":
        parts.append("Deteriorating")
    elif dt.trend == "OSCILLATING":
        parts.append("Oscillating")
    if dt.persistence_class in ("STRUCTURAL", "CHRONIC"):
        parts.append(dt.persistence_class.capitalize())
    if dt.severity == "CRITICAL":
        parts.append("Critical Drift")
    elif dt.severity == "SIGNIFICANT":
        parts.append("Significant Drift")
    if not parts:
        parts.append(f"{dt.severity.capitalize()} violation")
    return " + ".join(parts)


# ── Core analysis engine ───────────────────────────────────────────────────────

def _analyse_node(
    node_key: str,
    label: str,
    dim: str,
    entries: List[HistoryEntry],
) -> DriftTrend:
    """Compute full DriftTrend for one node."""
    drifts   = [e.drift_pct for e in entries]
    abs_drifts = [abs(d) for d in drifts]
    current  = drifts[-1]
    n        = len(entries)

    trend    = _classify_trend(drifts)
    momentum = _compute_momentum(drifts)

    # Violations
    v_count  = sum(1 for d in drifts if abs(d) > _VIOLATION_THRESHOLD_PP)
    v_pct    = round(v_count / n * 100, 1) if n > 0 else 0.0
    pers_cls = _classify_persistence(v_count, n)

    # First violation date
    first_v: Optional[str] = None
    for e in entries:
        if abs(e.drift_pct) > _VIOLATION_THRESHOLD_PP:
            first_v = e.snapshot_date
            break

    worst    = max(drifts, key=abs)
    best_val = min(abs_drifts)
    avg      = round(mean(drifts), 4)
    mx       = max(drifts)

    severity = _severity_label(abs(current))
    dir_lbl  = _drift_direction(current)

    return DriftTrend(
        node_key=node_key,
        node_label=label,
        dimension_type=dim,
        dates_available=n,
        current_drift_pct=round(current, 4),
        current_actual_pct=round(entries[-1].actual_pct, 4),
        current_target_pct=round(entries[-1].target_pct, 4),
        trend=trend,
        momentum_score=momentum,
        violation_count=v_count,
        persistence_pct=v_pct,
        persistence_class=pers_cls,
        first_violation_date=first_v,
        worst_drift_pct=round(worst, 4),
        best_drift_pct=round(best_val, 4),
        avg_drift_pct=avg,
        max_drift_pct=round(mx, 4),
        drift_direction=dir_lbl,
        severity=severity,
    )


def _analyse_all(repo_root: Path) -> Tuple[List[str], List[DriftTrend]]:
    """Return (canonical_dates, [DriftTrend, ...]) for all nodes."""
    runs     = _collect_canonical_runs(repo_root)
    dates    = [d for d, _ in runs]
    history  = _build_node_history(runs)
    results  = [
        _analyse_node(nk, lbl, dim, entries)
        for nk, (lbl, dim, entries) in sorted(history.items())
    ]
    return dates, results


# ── Serialisation helpers ──────────────────────────────────────────────────────

def _trend_dict(dt: DriftTrend) -> Dict:
    return {
        "node_key":              dt.node_key,
        "node_label":            dt.node_label,
        "dimension_type":        dt.dimension_type,
        "dates_available":       dt.dates_available,
        "current_drift_pct":     dt.current_drift_pct,
        "current_actual_pct":    dt.current_actual_pct,
        "current_target_pct":    dt.current_target_pct,
        "trend":                 dt.trend,
        "momentum_score":        dt.momentum_score,
        "violation_count":       dt.violation_count,
        "persistence_pct":       dt.persistence_pct,
        "persistence_class":     dt.persistence_class,
        "first_violation_date":  dt.first_violation_date,
        "worst_drift_pct":       dt.worst_drift_pct,
        "best_drift_pct":        dt.best_drift_pct,
        "avg_drift_pct":         dt.avg_drift_pct,
        "max_drift_pct":         dt.max_drift_pct,
        "drift_direction":       dt.drift_direction,
        "severity":              dt.severity,
    }


# ── Cache ──────────────────────────────────────────────────────────────────────

def _cache_root(repo_root: Path) -> Path:
    return repo_root / _CACHE_DIR


def _invalidate_needed(repo_root: Path) -> bool:
    cache_file = _cache_root(repo_root) / _INTELLIGENCE_CACHE
    if not cache_file.exists():
        return True
    try:
        cache_mtime = cache_file.stat().st_mtime
    except OSError:
        return True
    par_dir = _par_runs_dir(repo_root)
    if not par_dir.exists():
        return False
    for p in par_dir.iterdir():
        if not p.is_dir():
            continue
        meta = p / "run_metadata.json"
        try:
            if meta.exists() and meta.stat().st_mtime > cache_mtime:
                return True
        except OSError:
            continue
    return False


def _load_cache(repo_root: Path) -> Optional[Dict]:
    cache_file = _cache_root(repo_root) / _INTELLIGENCE_CACHE
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(repo_root: Path, payload: Dict) -> None:
    cache_root = _cache_root(repo_root)
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        (cache_root / _INTELLIGENCE_CACHE).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _get_intelligence(repo_root: Path) -> Dict:
    """Return intelligence payload, using cache when valid."""
    if not _invalidate_needed(repo_root):
        cached = _load_cache(repo_root)
        if cached:
            return cached

    dates, trend_list = _analyse_all(repo_root)

    # Priority ranking
    ranked = sorted(
        [dt for dt in trend_list if dt.severity != "NONE"],
        key=_compute_priority_score,
        reverse=True,
    )
    top10 = [
        {
            "rank":              i + 1,
            "node_key":          dt.node_key,
            "node_label":        dt.node_label,
            "priority_score":    _compute_priority_score(dt),
            "primary_reason":    _primary_reason(dt),
            "trend":             dt.trend,
            "persistence_class": dt.persistence_class,
            "severity":          dt.severity,
            "current_drift_pct": dt.current_drift_pct,
            "momentum_score":    dt.momentum_score,
        }
        for i, dt in enumerate(ranked[:10])
    ]

    # Trend summary counts
    trend_counts: Dict[str, int] = {"IMPROVING": 0, "STABLE": 0, "DETERIORATING": 0, "OSCILLATING": 0}
    for dt in trend_list:
        trend_counts[dt.trend] = trend_counts.get(dt.trend, 0) + 1

    # Chronic / structural
    chronic = [
        _trend_dict(dt) for dt in trend_list
        if dt.persistence_class in ("CHRONIC", "STRUCTURAL", "RECURRING")
    ]
    chronic.sort(key=lambda x: (-x["persistence_pct"], x["node_key"]))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dates": dates,
        "trends":    [_trend_dict(dt) for dt in trend_list],
        "top10":     top10,
        "chronic":   chronic,
        "trend_counts": trend_counts,
    }
    _write_cache(repo_root, payload)

    # Also write learning file (Part F)
    _write_learning(repo_root, trend_list)

    return payload


def _write_learning(repo_root: Path, trend_list: List[DriftTrend]) -> None:
    """Write allocation_drift_learning.json (Part F)."""
    records = [
        {
            "node_key":             dt.node_key,
            "node_label":           dt.node_label,
            "first_violation_date": dt.first_violation_date,
            "worst_drift_pct":      dt.worst_drift_pct,
            "best_drift_pct":       dt.best_drift_pct,
            "avg_drift_pct":        dt.avg_drift_pct,
            "max_drift_pct":        dt.max_drift_pct,
            "violation_count":      dt.violation_count,
            "dates_available":      dt.dates_available,
            "persistence_class":    dt.persistence_class,
            "current_severity":     dt.severity,
        }
        for dt in sorted(trend_list, key=lambda x: -abs(x.worst_drift_pct))
    ]
    cache_root = _cache_root(repo_root)
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        (cache_root / _LEARNING_CACHE).write_text(
            json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                        "nodes": records}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


# ── Public API ─────────────────────────────────────────────────────────────────

def drift_trends(repo_root: Path | str = ".") -> Dict:
    """Part A — Trend classification per node.

    Returns:
        {
          "generated_at": ...,
          "trend_counts": {"IMPROVING": N, "STABLE": N, "DETERIORATING": N, "OSCILLATING": N},
          "nodes": [{ node_key, node_label, trend, momentum_score, current_drift_pct, ... }]
        }
    """
    root = Path(repo_root)
    intel = _get_intelligence(root)
    return {
        "generated_at": intel["generated_at"],
        "trend_counts":  intel["trend_counts"],
        "nodes": intel["trends"],
    }


def drift_priorities(repo_root: Path | str = ".") -> Dict:
    """Part D — Top-10 allocation attention ranking.

    Returns:
        {
          "generated_at": ...,
          "top10": [{ rank, node_key, node_label, priority_score, primary_reason, ... }]
        }
    """
    root = Path(repo_root)
    intel = _get_intelligence(root)
    return {
        "generated_at": intel["generated_at"],
        "top10": intel["top10"],
    }


def drift_chronic(repo_root: Path | str = ".") -> Dict:
    """Part C — Chronic and structural violations.

    Returns:
        {
          "generated_at": ...,
          "chronic": [{ node_key, persistence_class, violation_count, persistence_pct, ... }]
        }
    """
    root = Path(repo_root)
    intel = _get_intelligence(root)
    return {
        "generated_at": intel["generated_at"],
        "chronic": intel["chronic"],
    }


def drift_momentum(repo_root: Path | str = ".") -> Dict:
    """Part B — Momentum scores per node.

    Returns:
        {
          "generated_at": ...,
          "nodes": [{ node_key, node_label, momentum_score, trend, current_drift_pct }]
        }
    """
    root = Path(repo_root)
    intel = _get_intelligence(root)
    # Sort: most extreme momentum first
    nodes_sorted = sorted(
        intel["trends"],
        key=lambda x: abs(x.get("momentum_score", 0)),
        reverse=True,
    )
    return {
        "generated_at": intel["generated_at"],
        "nodes": [
            {
                "node_key":          n["node_key"],
                "node_label":        n["node_label"],
                "momentum_score":    n["momentum_score"],
                "trend":             n["trend"],
                "current_drift_pct": n["current_drift_pct"],
                "severity":          n["severity"],
            }
            for n in nodes_sorted
        ],
    }


def drift_intelligence_summary(repo_root: Path | str = ".") -> Dict:
    """Executive summary combining all PA-006B intelligence.

    Returns:
        {
          "generated_at": ...,
          "trend_counts": ...,
          "top_priority": <top-ranked node or null>,
          "most_chronic": <most persistent violator or null>,
          "most_improving": <highest positive momentum or null>,
          "most_deteriorating": <most negative momentum or null>,
          "total_nodes": N,
          "violation_nodes": N,
          "structural_count": N,
          "chronic_count": N,
          "governance_note": str,
        }
    """
    root  = Path(repo_root)
    intel = _get_intelligence(root)
    trends = intel["trends"]

    total   = len(trends)
    in_viol = sum(1 for t in trends if t["severity"] != "NONE")
    struct  = sum(1 for t in trends if t["persistence_class"] == "STRUCTURAL")
    chron   = sum(1 for t in trends if t["persistence_class"] == "CHRONIC")

    top_priority   = intel["top10"][0] if intel["top10"] else None
    most_chronic   = intel["chronic"][0] if intel["chronic"] else None

    improving_list = [t for t in trends if t["trend"] == "IMPROVING" and t["momentum_score"] > 0]
    improving_list.sort(key=lambda x: -x["momentum_score"])
    most_improving = improving_list[0] if improving_list else None

    det_list = [t for t in trends if t["trend"] == "DETERIORATING"]
    det_list.sort(key=lambda x: x["momentum_score"])
    most_deteriorating = det_list[0] if det_list else None

    return {
        "generated_at":     intel["generated_at"],
        "trend_counts":     intel["trend_counts"],
        "top_priority":     top_priority,
        "most_chronic":     most_chronic,
        "most_improving":   most_improving,
        "most_deteriorating": most_deteriorating,
        "total_nodes":      total,
        "violation_nodes":  in_viol,
        "structural_count": struct,
        "chronic_count":    chron,
        "governance_note": (
            "PA-006B is display-only. No allocation targets, recommendation engines, "
            "governance rules, CRA, PAP, ESS, CW-DAS, UCF, or Replay logic is modified. "
            "All findings are informational to support portfolio-manager situational awareness."
        ),
    }
