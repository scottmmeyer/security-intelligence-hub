# PIS-007 — Algorithm Specification: Allocation Drift Trend Engine

**Status:** IMPLEMENTATION READY  
**Date:** 2026-06-15

---

## 1. Module Entry Point

**File:** `src/pis/allocation_drift.py`

**Public API:**

```python
def pis_allocation_drift_summary(repo_root: Path | str = ".") -> dict
def pis_allocation_drift_latest(repo_root: Path | str = ".") -> dict
def pis_allocation_drift_history(repo_root: Path | str = ".") -> dict
```

All three functions are read-only. No writes to existing files.

---

## 2. Data Loading Algorithm

### Step 1 — Enumerate PAR Runs

```
par_dir = {repo_root}/data/portfolio_ingestion/analysis_runs/
for each subdirectory par_path in par_dir:
    meta_file = par_path / run_metadata.json
    align_file = par_path / alignment.csv
    if both exist:
        parse snapshot_date (first 10 chars of metadata["snapshot_date"])
        parse created_at_utc (metadata["created_at_utc"])
        if snapshot_date is valid YYYY-MM-DD (len==10):
            add to candidates
```

### Step 2 — Canonical Selection (latest PAR per date)

```
by_date = {}
for each candidate:
    if snapshot_date not in by_date
        OR candidate.created_at_utc > by_date[snapshot_date].created_at_utc:
            by_date[snapshot_date] = candidate
canonical_dates = sorted(by_date.keys())  # ascending
```

### Step 3 — Node History Matrix

```
node_history: dict[str, list[HistoryEntry]] = {}

for snapshot_date in canonical_dates:
    candidate = by_date[snapshot_date]
    rows = read_csv(candidate.align_file)
    for row in rows:
        node_key = row["node_key"].strip()
        if not node_key or "." not in node_key and node_key not in LEVEL1_NODES:
            continue  # skip malformed rows
        
        actual_pct = _safe_float(row["effective_actual_pct"])
            if None: _safe_float(row["actual_pct"])
        target_pct = _safe_float(row["tactical_target_pct"])
            if None: _safe_float(row["target_pct"])
        
        if actual_pct is None or target_pct is None:
            continue  # insufficient data for this row
        
        drift_pct = round(actual_pct - target_pct, 4)
        
        node_history.setdefault(node_key, []).append(HistoryEntry(
            snapshot_date=snapshot_date,
            actual_pct=actual_pct,
            target_pct=target_pct,
            drift_pct=drift_pct,
            node_label=row["node_label"],
            dimension_type=row["dimension_type"],
        ))
```

Each node_history list is guaranteed to be in ascending snapshot_date order (inherited from canonical_dates ordering).

---

## 3. Trend Computation Algorithm

### Input
`entries: list[HistoryEntry]` — ordered ascending by snapshot_date, len ≥ 1

### Constants

```python
STABLE_THRESHOLD_PP = 0.5
SEVERITY_MINOR_PP    = 0.5
SEVERITY_MODERATE_PP = 2.0
SEVERITY_SIGNIFICANT_PP = 5.0
```

### Algorithm

```python
def compute_node_trend(node_key, node_label, dimension_type, entries):
    if not entries:
        return null

    current = entries[-1]
    prior   = entries[-2] if len(entries) >= 2 else None
    oldest  = entries[0]

    # ─── Current / Prior Drift ────────────────────────────────────────────
    current_drift = current.drift_pct
    prior_drift   = prior.drift_pct if prior else None

    # ─── Drift Delta (signed) ─────────────────────────────────────────────
    # Negative delta means drift moved toward zero (magnitude decreased)
    # Positive delta means drift moved away from zero (magnitude increased)
    if prior_drift is not None:
        raw_delta = current_drift - prior_drift  # signed
        abs_current = abs(current_drift)
        abs_prior   = abs(prior_drift)
        magnitude_delta = abs_current - abs_prior  # positive = worsening
    else:
        raw_delta = None
        magnitude_delta = None

    # ─── Trend Direction ─────────────────────────────────────────────────
    if magnitude_delta is None:
        trend_direction = "STABLE"
    elif abs(magnitude_delta) < STABLE_THRESHOLD_PP:
        trend_direction = "STABLE"
    elif magnitude_delta > 0:
        trend_direction = "WORSENING"
    else:
        trend_direction = "IMPROVING"

    # ─── Trend Severity ──────────────────────────────────────────────────
    abs_mag = abs(magnitude_delta) if magnitude_delta is not None else 0.0
    if abs_mag < SEVERITY_MINOR_PP:
        severity = "NONE"
    elif abs_mag < SEVERITY_MODERATE_PP:
        severity = "MINOR"
    elif abs_mag < SEVERITY_SIGNIFICANT_PP:
        severity = "MODERATE"
    else:
        severity = "SIGNIFICANT"

    # ─── Drift Velocity (pp per day across full window) ───────────────────
    if len(entries) >= 2:
        oldest_drift = oldest.drift_pct
        try:
            oldest_dt  = date.fromisoformat(oldest.snapshot_date)
            current_dt = date.fromisoformat(current.snapshot_date)
            days_span = max((current_dt - oldest_dt).days, 1)
            velocity = round((current_drift - oldest_drift) / days_span, 4)
        except ValueError:
            velocity = 0.0
    else:
        velocity = 0.0

    # ─── Drift Direction ─────────────────────────────────────────────────
    if abs(current_drift) < 0.05:
        drift_direction = "ON_TARGET"
    elif current_drift > 0:
        drift_direction = "OVERWEIGHT"
    else:
        drift_direction = "UNDERWEIGHT"

    # ─── Persistence Score ───────────────────────────────────────────────
    # Fraction of entries where drift direction matches current direction
    if drift_direction == "ON_TARGET":
        same_dir_count = sum(1 for e in entries if abs(e.drift_pct) < 0.05)
    elif drift_direction == "OVERWEIGHT":
        same_dir_count = sum(1 for e in entries if e.drift_pct > 0)
    else:  # UNDERWEIGHT
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
        drift_delta_pp=raw_delta,
        magnitude_delta_pp=magnitude_delta,
        trend_direction=trend_direction,
        trend_severity=severity,
        drift_velocity_pp_per_day=velocity,
        drift_direction=drift_direction,
        persistence_score=persistence_score,
    )
```

---

## 4. Summary Computation Algorithm

```python
def compute_summary(trends: list[NodeTrendResult], canonical_dates: list[str]) -> dict:

    improving  = [t for t in trends if t.trend_direction == "IMPROVING"]
    worsening  = [t for t in trends if t.trend_direction == "WORSENING"]
    stable     = [t for t in trends if t.trend_direction == "STABLE"]

    # Most improved = largest reduction in drift magnitude
    # magnitude_delta is most negative for most improved
    most_improved = min(trends, key=lambda t: t.magnitude_delta_pp or 0.0, default=None)
    if most_improved and (most_improved.magnitude_delta_pp or 0.0) >= 0:
        most_improved = None  # no improvement at all

    # Most deteriorated = largest increase in drift magnitude
    # magnitude_delta is most positive for most deteriorated
    most_deteriorated = max(trends, key=lambda t: t.magnitude_delta_pp or 0.0, default=None)
    if most_deteriorated and (most_deteriorated.magnitude_delta_pp or 0.0) <= 0:
        most_deteriorated = None  # no deterioration at all

    observations = _generate_observations(trends, len(canonical_dates))

    return {
        "generated_at": ...,
        "dates_available": len(canonical_dates),
        "current_date": canonical_dates[-1] if canonical_dates else None,
        "prior_date": canonical_dates[-2] if len(canonical_dates) >= 2 else None,
        "improving_count": len(improving),
        "worsening_count": len(worsening),
        "stable_count": len(stable),
        "most_improved_node": _node_summary(most_improved),
        "most_deteriorated_node": _node_summary(most_deteriorated),
        "observations": observations,
    }
```

---

## 5. Observations Generation Algorithm

```python
def _generate_observations(
    trends: list[NodeTrendResult],
    total_dates: int,
) -> list[str]:
    obs: list[str] = []

    # Rule 1: WORSENING nodes with MODERATE or SIGNIFICANT severity
    for t in sorted(trends, key=lambda x: abs(x.magnitude_delta_pp or 0), reverse=True):
        if t.trend_direction == "WORSENING" and t.trend_severity in ("MODERATE", "SIGNIFICANT"):
            if t.prior_drift_pct is not None:
                obs.append(
                    f"{t.node_label} has deteriorated from {t.prior_drift_pct:+.1f}pp to "
                    f"{t.current_drift_pct:+.1f}pp since the prior period."
                )

    # Rule 2: IMPROVING nodes with MODERATE or SIGNIFICANT severity
    for t in sorted(trends, key=lambda x: abs(x.magnitude_delta_pp or 0), reverse=True):
        if t.trend_direction == "IMPROVING" and t.trend_severity in ("MODERATE", "SIGNIFICANT"):
            if t.prior_drift_pct is not None:
                direction = "overweight" if t.prior_drift_pct > 0 else "underweight"
                obs.append(
                    f"{t.node_label} drift improved from {t.prior_drift_pct:+.1f}pp to "
                    f"{t.current_drift_pct:+.1f}pp since the prior period."
                )

    # Rule 3: Persistent misalignment (all dates same direction, ≥ 5 dates)
    for t in trends:
        if t.persistence_score == 1.0 and t.dates_available >= 5:
            direction = "overweight" if t.current_drift_pct > 0 else "underweight"
            obs.append(
                f"{t.node_label} remains persistently {direction} across all "
                f"{t.dates_available} observed dates."
            )

    # Rule 4: Nearly on-target (drift within ±0.5pp)
    for t in trends:
        if abs(t.current_drift_pct) < 0.5:
            obs.append(f"{t.node_label} is on-target (drift: {t.current_drift_pct:+.2f}pp).")

    return obs[:8]  # cap at 8 to keep dashboard concise
```

---

## 6. Cache Strategy

### Cache File
`data/history/pis/allocation_drift_cache.json`

### Invalidation
Cache is stale when any PAR run directory `mtime` is newer than the cache file `mtime`. Implementation:

```python
def _cache_is_valid(cache_path: Path, par_dir: Path) -> bool:
    if not cache_path.exists():
        return False
    cache_mtime = cache_path.stat().st_mtime
    for par_path in par_dir.iterdir():
        if par_path.is_dir():
            meta = par_path / "run_metadata.json"
            if meta.exists() and meta.stat().st_mtime > cache_mtime:
                return False
    return True
```

### Cache Content
The cache stores the full `history` payload (all nodes × all dates) since it is the most expensive to compute. `latest` and `summary` payloads are derived from it in-memory and are not separately cached.

---

## 7. Edge Cases

| Case | Handling |
|------|---------|
| Zero PAR runs with alignment.csv | Return empty payload with `dates_available: 0` |
| Only one canonical date | `prior_drift`, `drift_delta`, `magnitude_delta` all `null`; `trend_direction = "STABLE"` |
| Node present in some dates but not others | Only dates where node appears contribute to history; `dates_available` reflects actual count |
| `effective_actual_pct` is empty/missing | Fall back to `actual_pct` |
| `tactical_target_pct` is empty/missing | Fall back to `target_pct` |
| `drift_pct` from CSV vs recomputed mismatch | Use recomputed value (actual_pct − target_pct) for internal consistency |
| All nodes STABLE | Summary returns `most_improved_node: null`, `most_deteriorated_node: null` |
| malformed snapshot_date in metadata | Skip that PAR run entirely |
| duplicate snapshot_dates | Latest `created_at_utc` wins (canonical selection) |

---

## 8. Data Model

```python
@dataclass(frozen=True)
class HistoryEntry:
    snapshot_date: str      # YYYY-MM-DD
    actual_pct: float       # effective actual allocation %
    target_pct: float       # tactical target %
    drift_pct: float        # actual - target (recomputed)
    node_label: str
    dimension_type: str

@dataclass(frozen=True)
class NodeTrendResult:
    node_key: str
    node_label: str
    dimension_type: str
    dates_available: int
    current_actual_pct: float
    current_target_pct: float
    current_drift_pct: float
    prior_drift_pct: Optional[float]
    drift_delta_pp: Optional[float]         # signed: current - prior
    magnitude_delta_pp: Optional[float]     # abs(current) - abs(prior); positive = worsening
    trend_direction: str        # IMPROVING | WORSENING | STABLE
    trend_severity: str         # NONE | MINOR | MODERATE | SIGNIFICANT
    drift_velocity_pp_per_day: float
    drift_direction: str        # OVERWEIGHT | UNDERWEIGHT | ON_TARGET
    persistence_score: float    # 0.0–1.0; fraction of entries in same direction
```

---

## 9. Sorting / Ordering in Payloads

### `/api/pis/allocation-drift/latest` node list
Primary sort: `trend_direction` (WORSENING first, then IMPROVING, then STABLE)
Secondary sort: `abs(magnitude_delta_pp)` descending

### `/api/pis/allocation-drift/history` node list
Sorted by `dimension_type` then `node_key` alphabetically — consistent with allocation hierarchy depth-first.

### Top worsening / top improving (dashboard panels)
Top 5 by `abs(magnitude_delta_pp)` within WORSENING / IMPROVING groups.
