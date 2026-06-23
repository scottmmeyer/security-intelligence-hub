"""PIS-007 — Allocation Drift Trend Engine.

Reads existing PAR alignment.csv artifacts to reconstruct historical allocation
drift across all canonical portfolio dates.  Computes trend direction, severity,
velocity, and persistence for every allocation node.  Exposes three API functions
for the PIS dashboard.

This module is STRICTLY READ-ONLY with respect to all existing PAR artifacts and
PIS storage.  It writes only an optional cache file at:
  data/history/pis/allocation_drift_cache.json
which is a derived artifact and fully regeneratable.

Public API
----------
  pis_allocation_drift_summary(repo_root)  → dict   (summary cards payload)
  pis_allocation_drift_latest(repo_root)   → dict   (per-node trend snapshot)
  pis_allocation_drift_history(repo_root)  → dict   (full time-series payload)
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STABLE_THRESHOLD_PP = 0.5
_SEVERITY_MINOR_PP = 0.5
_SEVERITY_MODERATE_PP = 2.0
_SEVERITY_SIGNIFICANT_PP = 5.0

_ON_TARGET_BAND_PP = 0.05   # drift < ±0.05pp → ON_TARGET

_MAX_OBSERVATIONS = 8       # cap on generated observation strings

_CACHE_FILENAME = "allocation_drift_cache.json"

# ─── Data models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HistoryEntry:
    """Single-date record for one allocation node."""
    snapshot_date: str      # YYYY-MM-DD
    actual_pct: float       # effective actual allocation %
    target_pct: float       # tactical target %
    drift_pct: float        # actual_pct − target_pct (recomputed)


@dataclass(frozen=True)
class NodeTrendResult:
    """Trend analysis result for one allocation node across all history."""
    node_key: str
    node_label: str
    dimension_type: str
    dates_available: int
    current_actual_pct: float
    current_target_pct: float
    current_drift_pct: float
    prior_drift_pct: Optional[float]
    drift_delta_pp: Optional[float]         # signed: current_drift - prior_drift
    magnitude_delta_pp: Optional[float]     # abs(current) - abs(prior); + = worsening
    trend_direction: str        # IMPROVING | WORSENING | STABLE
    trend_severity: str         # NONE | MINOR | MODERATE | SIGNIFICANT
    drift_velocity_pp_per_day: float
    drift_direction: str        # OVERWEIGHT | UNDERWEIGHT | ON_TARGET
    persistence_score: float    # 0.0–1.0; fraction of entries in same direction


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _safe_float(value: object) -> Optional[float]:
    """Return float or None if value is absent/non-numeric."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _safe_str(row: dict[str, str], key: str) -> str:
    return str(row.get(key) or "").strip()


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ─── Step 1 — PAR run enumeration + canonical selection ───────────────────────


def _par_runs_dir(repo_root: Path) -> Path:
    return repo_root / "data" / "portfolio_ingestion" / "analysis_runs"


def _collect_canonical_runs(repo_root: Path) -> list[tuple[str, Path]]:
    """Return [(snapshot_date, alignment_csv_path), ...] sorted ascending.

    For each snapshot_date, only the PAR run with the latest created_at_utc
    is retained (mirrors drift_analyzer._canonical_by_date logic).
    """
    par_dir = _par_runs_dir(repo_root)
    if not par_dir.exists():
        return []

    # date → (created_at_utc, alignment_path)
    by_date: dict[str, tuple[str, Path]] = {}

    for par_path in par_dir.iterdir():
        if not par_path.is_dir():
            continue
        meta_file = par_path / "run_metadata.json"
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
        # Validate it looks like a date
        try:
            date.fromisoformat(snapshot_date)
        except ValueError:
            continue

        created_at = str(meta.get("created_at_utc", ""))

        if snapshot_date not in by_date or created_at > by_date[snapshot_date][0]:
            by_date[snapshot_date] = (created_at, align_file)

    # Sort ascending by date
    result = [(d, by_date[d][1]) for d in sorted(by_date.keys())]
    return result


# ─── Step 2 — Node history reconstruction ─────────────────────────────────────


def _build_node_history(
    canonical_runs: list[tuple[str, Path]],
) -> dict[str, tuple[str, str, list[HistoryEntry]]]:
    """Return {node_key: (node_label, dimension_type, [HistoryEntry, ...])} ordered by date."""

    # node_key → (label, dimension_type, entries)
    accumulator: dict[str, tuple[str, str, list[HistoryEntry]]] = {}

    for snapshot_date, align_path in canonical_runs:
        rows = _read_csv_rows(align_path)
        for row in rows:
            node_key = _safe_str(row, "node_key")
            if not node_key:
                continue

            # Resolve actual_pct: prefer effective_actual_pct, fall back to actual_pct
            actual_pct = _safe_float(row.get("effective_actual_pct"))
            if actual_pct is None:
                actual_pct = _safe_float(row.get("actual_pct"))
            if actual_pct is None:
                continue  # cannot use this row

            # Resolve target_pct: prefer tactical_target_pct, fall back to target_pct
            target_pct = _safe_float(row.get("tactical_target_pct"))
            if target_pct is None:
                target_pct = _safe_float(row.get("target_pct"))
            if target_pct is None:
                continue

            drift_pct = round(actual_pct - target_pct, 4)

            node_label = _safe_str(row, "node_label") or node_key
            dimension_type = _safe_str(row, "dimension_type") or ""

            entry = HistoryEntry(
                snapshot_date=snapshot_date,
                actual_pct=actual_pct,
                target_pct=target_pct,
                drift_pct=drift_pct,
            )

            if node_key not in accumulator:
                accumulator[node_key] = (node_label, dimension_type, [])
            accumulator[node_key][2].append(entry)

    return accumulator


# ─── Step 3 — Trend computation ───────────────────────────────────────────────


def _drift_direction(drift_pct: float) -> str:
    if abs(drift_pct) < _ON_TARGET_BAND_PP:
        return "ON_TARGET"
    return "OVERWEIGHT" if drift_pct > 0 else "UNDERWEIGHT"


def _compute_trend(
    node_key: str,
    node_label: str,
    dimension_type: str,
    entries: list[HistoryEntry],
) -> NodeTrendResult:
    """Compute all trend metrics for one node from its ordered history entries."""
    assert entries, "entries must not be empty"

    current = entries[-1]
    prior = entries[-2] if len(entries) >= 2 else None
    oldest = entries[0]

    current_drift = current.drift_pct
    prior_drift: Optional[float] = prior.drift_pct if prior else None

    # Drift delta (signed) and magnitude delta
    if prior_drift is not None:
        drift_delta_pp = round(current_drift - prior_drift, 4)
        magnitude_delta_pp = round(abs(current_drift) - abs(prior_drift), 4)
    else:
        drift_delta_pp = None
        magnitude_delta_pp = None

    # Trend direction: based on magnitude (distance from zero), not signed delta
    if magnitude_delta_pp is None or abs(magnitude_delta_pp) < _STABLE_THRESHOLD_PP:
        trend_direction = "STABLE"
    elif magnitude_delta_pp > 0:
        trend_direction = "WORSENING"
    else:
        trend_direction = "IMPROVING"

    # Trend severity
    abs_mag = abs(magnitude_delta_pp) if magnitude_delta_pp is not None else 0.0
    if abs_mag < _SEVERITY_MINOR_PP:
        trend_severity = "NONE"
    elif abs_mag < _SEVERITY_MODERATE_PP:
        trend_severity = "MINOR"
    elif abs_mag < _SEVERITY_SIGNIFICANT_PP:
        trend_severity = "MODERATE"
    else:
        trend_severity = "SIGNIFICANT"

    # Drift velocity (pp per calendar day across full window)
    if len(entries) >= 2:
        try:
            oldest_dt = date.fromisoformat(oldest.snapshot_date)
            current_dt = date.fromisoformat(current.snapshot_date)
            days_span = max((current_dt - oldest_dt).days, 1)
            velocity = round((current_drift - oldest.drift_pct) / days_span, 4)
        except ValueError:
            velocity = 0.0
    else:
        velocity = 0.0

    # Current drift direction
    drift_direction = _drift_direction(current_drift)

    # Persistence score: fraction of entries in same drift direction as current
    if drift_direction == "ON_TARGET":
        same_dir_count = sum(1 for e in entries if abs(e.drift_pct) < _ON_TARGET_BAND_PP)
    elif drift_direction == "OVERWEIGHT":
        same_dir_count = sum(1 for e in entries if e.drift_pct > 0)
    else:
        same_dir_count = sum(1 for e in entries if e.drift_pct < 0)
    persistence_score = round(same_dir_count / len(entries), 3)

    return NodeTrendResult(
        node_key=node_key,
        node_label=node_label,
        dimension_type=dimension_type,
        dates_available=len(entries),
        current_actual_pct=current.actual_pct,
        current_target_pct=current.target_pct,
        current_drift_pct=current_drift,
        prior_drift_pct=prior_drift,
        drift_delta_pp=drift_delta_pp,
        magnitude_delta_pp=magnitude_delta_pp,
        trend_direction=trend_direction,
        trend_severity=trend_severity,
        drift_velocity_pp_per_day=velocity,
        drift_direction=drift_direction,
        persistence_score=persistence_score,
    )


def _compute_all_trends(
    node_history: dict[str, tuple[str, str, list[HistoryEntry]]],
) -> list[NodeTrendResult]:
    results = []
    for node_key, (node_label, dimension_type, entries) in node_history.items():
        if not entries:
            continue
        results.append(_compute_trend(node_key, node_label, dimension_type, entries))
    return results


# ─── Step 4 — Summary + observations ─────────────────────────────────────────


def _node_summary_dict(t: Optional[NodeTrendResult]) -> Optional[dict]:
    if t is None:
        return None
    return {
        "node_key": t.node_key,
        "node_label": t.node_label,
        "current_drift_pct": t.current_drift_pct,
        "prior_drift_pct": t.prior_drift_pct,
        "drift_delta_pp": t.drift_delta_pp,
        "magnitude_delta_pp": t.magnitude_delta_pp,
        "trend_direction": t.trend_direction,
        "trend_severity": t.trend_severity,
    }


def _generate_observations(trends: list[NodeTrendResult], total_dates: int) -> list[str]:
    """Generate up to _MAX_OBSERVATIONS human-readable drift observations."""
    obs: list[str] = []

    # Rule 1: Worsening nodes with MODERATE or SIGNIFICANT severity
    worsening_notable = sorted(
        [t for t in trends if t.trend_direction == "WORSENING"
         and t.trend_severity in ("MODERATE", "SIGNIFICANT")],
        key=lambda x: abs(x.magnitude_delta_pp or 0.0),
        reverse=True,
    )
    for t in worsening_notable:
        if t.prior_drift_pct is not None:
            obs.append(
                f"{t.node_label} has deteriorated from {t.prior_drift_pct:+.1f}pp to "
                f"{t.current_drift_pct:+.1f}pp since the prior period."
            )
        if len(obs) >= _MAX_OBSERVATIONS:
            return obs

    # Rule 2: Improving nodes with MODERATE or SIGNIFICANT severity
    improving_notable = sorted(
        [t for t in trends if t.trend_direction == "IMPROVING"
         and t.trend_severity in ("MODERATE", "SIGNIFICANT")],
        key=lambda x: abs(x.magnitude_delta_pp or 0.0),
        reverse=True,
    )
    for t in improving_notable:
        if t.prior_drift_pct is not None:
            obs.append(
                f"{t.node_label} drift improved from {t.prior_drift_pct:+.1f}pp to "
                f"{t.current_drift_pct:+.1f}pp since the prior period."
            )
        if len(obs) >= _MAX_OBSERVATIONS:
            return obs

    # Rule 3: Persistent misalignment (all observed dates same direction, ≥ 5 dates)
    for t in sorted(trends, key=lambda x: x.dates_available, reverse=True):
        if t.persistence_score == 1.0 and t.dates_available >= 5:
            direction = "overweight" if t.current_drift_pct > 0 else "underweight"
            obs.append(
                f"{t.node_label} remains persistently {direction} across all "
                f"{t.dates_available} observed dates."
            )
        if len(obs) >= _MAX_OBSERVATIONS:
            return obs

    # Rule 4: Nearly on-target (drift within ±0.5pp)
    for t in trends:
        if abs(t.current_drift_pct) < 0.5 and t.drift_direction != "ON_TARGET":
            obs.append(
                f"{t.node_label} is nearly on-target (drift: {t.current_drift_pct:+.2f}pp)."
            )
        if len(obs) >= _MAX_OBSERVATIONS:
            return obs

    return obs


# ─── Cache ────────────────────────────────────────────────────────────────────


def _cache_path(repo_root: Path) -> Path:
    return repo_root / "data" / "history" / "pis" / _CACHE_FILENAME


def _cache_is_valid(cache_path: Path, par_dir: Path) -> bool:
    """Return True iff cache exists and no PAR run metadata is newer than it."""
    if not cache_path.exists():
        return False
    try:
        cache_mtime = cache_path.stat().st_mtime
    except OSError:
        return False
    if not par_dir.exists():
        return True
    for par_path in par_dir.iterdir():
        if not par_path.is_dir():
            continue
        meta = par_path / "run_metadata.json"
        try:
            if meta.exists() and meta.stat().st_mtime > cache_mtime:
                return False
        except OSError:
            continue
    return True


def _load_cache(cache_path: Path) -> Optional[dict]:
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(cache_path: Path, payload: dict) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass  # cache write failure is non-fatal


# ─── Core computation ─────────────────────────────────────────────────────────


def _compute_drift_data(repo_root: Path) -> tuple[
    list[str],                                              # canonical_dates
    dict[str, tuple[str, str, list[HistoryEntry]]],         # node_history
    list[NodeTrendResult],                                  # trends
]:
    """Central computation: gather canonical runs, build history, compute trends."""
    canonical_runs = _collect_canonical_runs(repo_root)
    canonical_dates = [d for d, _ in canonical_runs]
    node_history = _build_node_history(canonical_runs)
    trends = _compute_all_trends(node_history)
    return canonical_dates, node_history, trends


def _get_history_payload(repo_root: Path) -> dict:
    """Return full history payload, using cache when valid."""
    par_dir = _par_runs_dir(repo_root)
    cache = _cache_path(repo_root)

    if _cache_is_valid(cache, par_dir):
        cached = _load_cache(cache)
        if cached is not None:
            return cached

    canonical_runs = _collect_canonical_runs(repo_root)
    canonical_dates = [d for d, _ in canonical_runs]
    node_history = _build_node_history(canonical_runs)

    # Build history payload
    nodes_payload = []
    for node_key in sorted(node_history.keys()):
        node_label, dimension_type, entries = node_history[node_key]
        nodes_payload.append({
            "node_key": node_key,
            "node_label": node_label,
            "dimension_type": dimension_type,
            "entries": [
                {
                    "snapshot_date": e.snapshot_date,
                    "actual_pct": e.actual_pct,
                    "target_pct": e.target_pct,
                    "drift_pct": e.drift_pct,
                }
                for e in entries
            ],
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dates": canonical_dates,
        "nodes": nodes_payload,
    }
    _write_cache(cache, payload)
    return payload


# ─── Public API ───────────────────────────────────────────────────────────────


def pis_allocation_drift_history(repo_root: Path | str = ".") -> dict:
    """Full historical time-series: for every canonical date, every node's allocation.

    Returns:
        {
          "generated_at": ISO timestamp,
          "dates": ["YYYY-MM-DD", ...],   # all canonical dates ascending
          "nodes": [
            {
              "node_key": str,
              "node_label": str,
              "dimension_type": str,
              "entries": [
                {"snapshot_date": str, "actual_pct": float, "target_pct": float, "drift_pct": float},
                ...
              ]
            }
          ]
        }
    """
    return _get_history_payload(Path(repo_root))


def pis_allocation_drift_latest(repo_root: Path | str = ".") -> dict:
    """Latest per-node drift snapshot with trend metrics.

    Returns:
        {
          "generated_at": ISO timestamp,
          "current_date": str | null,
          "dates_available": int,
          "nodes": [NodeTrendResult as dict, ...]   # sorted: WORSENING first, then IMPROVING, then STABLE
        }
    """
    repo_root = Path(repo_root)
    canonical_runs = _collect_canonical_runs(repo_root)
    canonical_dates = [d for d, _ in canonical_runs]
    node_history = _build_node_history(canonical_runs)
    trends = _compute_all_trends(node_history)

    # Sort: WORSENING first, then IMPROVING, then STABLE; within each group by abs(magnitude_delta) desc
    _sort_order = {"WORSENING": 0, "IMPROVING": 1, "STABLE": 2}

    def _sort_key(t: NodeTrendResult) -> tuple:
        return (
            _sort_order.get(t.trend_direction, 3),
            -(abs(t.magnitude_delta_pp) if t.magnitude_delta_pp is not None else 0.0),
        )

    sorted_trends = sorted(trends, key=_sort_key)

    def _trend_dict(t: NodeTrendResult) -> dict:
        return {
            "node_key": t.node_key,
            "node_label": t.node_label,
            "dimension_type": t.dimension_type,
            "dates_available": t.dates_available,
            "current_actual_pct": t.current_actual_pct,
            "current_target_pct": t.current_target_pct,
            "current_drift_pct": t.current_drift_pct,
            "prior_drift_pct": t.prior_drift_pct,
            "drift_delta_pp": t.drift_delta_pp,
            "magnitude_delta_pp": t.magnitude_delta_pp,
            "trend_direction": t.trend_direction,
            "trend_severity": t.trend_severity,
            "drift_velocity_pp_per_day": t.drift_velocity_pp_per_day,
            "drift_direction": t.drift_direction,
            "persistence_score": t.persistence_score,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_date": canonical_dates[-1] if canonical_dates else None,
        "dates_available": len(canonical_dates),
        "nodes": [_trend_dict(t) for t in sorted_trends],
    }


def pis_allocation_drift_summary(repo_root: Path | str = ".") -> dict:
    """Summary cards payload for the Allocation Drift Trends dashboard section.

    Returns:
        {
          "generated_at": ISO timestamp,
          "current_date": str | null,
          "prior_date": str | null,
          "dates_available": int,
          "improving_count": int,
          "worsening_count": int,
          "stable_count": int,
          "most_improved_node": {node_key, node_label, current_drift_pct,
                                  prior_drift_pct, drift_delta_pp,
                                  magnitude_delta_pp, trend_direction} | null,
          "most_deteriorated_node": same shape | null,
          "observations": [str, ...]
        }
    """
    repo_root = Path(repo_root)
    canonical_runs = _collect_canonical_runs(repo_root)
    canonical_dates = [d for d, _ in canonical_runs]
    node_history = _build_node_history(canonical_runs)
    trends = _compute_all_trends(node_history)

    improving = [t for t in trends if t.trend_direction == "IMPROVING"]
    worsening = [t for t in trends if t.trend_direction == "WORSENING"]
    stable = [t for t in trends if t.trend_direction == "STABLE"]

    # Most improved: node with largest magnitude decrease (most negative magnitude_delta)
    improving_candidates = [t for t in trends if (t.magnitude_delta_pp or 0.0) < 0]
    most_improved: Optional[NodeTrendResult] = (
        min(improving_candidates, key=lambda t: t.magnitude_delta_pp or 0.0)
        if improving_candidates else None
    )

    # Most deteriorated: node with largest magnitude increase (most positive magnitude_delta)
    worsening_candidates = [t for t in trends if (t.magnitude_delta_pp or 0.0) > 0]
    most_deteriorated: Optional[NodeTrendResult] = (
        max(worsening_candidates, key=lambda t: t.magnitude_delta_pp or 0.0)
        if worsening_candidates else None
    )

    observations = _generate_observations(trends, len(canonical_dates))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_date": canonical_dates[-1] if canonical_dates else None,
        "prior_date": canonical_dates[-2] if len(canonical_dates) >= 2 else None,
        "dates_available": len(canonical_dates),
        "improving_count": len(improving),
        "worsening_count": len(worsening),
        "stable_count": len(stable),
        "most_improved_node": _node_summary_dict(most_improved),
        "most_deteriorated_node": _node_summary_dict(most_deteriorated),
        "observations": observations,
    }
