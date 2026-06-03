# Replay Alignment Staleness Report
**Generated:** 2026-06-01  
**Scope:** All code paths that produce or display `replay_supported`, `replay_percentile`, and `replay_alignment_score`

---

## Executive Summary

The replay alignment subsystem has **two independent staleness vectors** that can silently diverge from reality without any error surfacing to the UI:

1. **Replay evidence staleness** — `replay_inputs.csv` and `replay_performance_series.csv` describe which symbols appeared in which historical replay runs. These are never automatically refreshed. If new replays have been run but `rebuild_analytical_universe.py` or an equivalent step has not propagated results to `data/current/`, overlay `replay_supported` flags will be stale.

2. **Percentile staleness** — `replay_percentile` is computed live at overlay-build time by ranking symbols within their replay cohort by `composite_score` from `analytical_universe.csv`. If the universe is rebuilt (e.g. after a signal refresh), percentiles shift silently for all persisted runs because the computation is not deterministic across rebuilds.

---

## Staleness Vector 1: Replay Evidence Files

### Source files
| File | Path | Updated by |
|---|---|---|
| `replay_inputs.csv` | `data/current/replay_inputs.csv` | Manual replay run / `rebuild_analytical_universe.py` |
| `replay_performance_series.csv` | `data/current/replay_performance_series.csv` | Same |

### Code path
`_load_replay_evidence()` in [src/portfolio/recommendations.py](src/portfolio/recommendations.py#L50) reads both files unconditionally at overlay-build time. There is **no freshness check, no date guard, and no staleness warning** emitted.

### Risk
If `replay_inputs.csv` is outdated:
- Symbols that have entered a new top-N replay since the last universe rebuild will show `replay_supported=False` even though they are legitimately replay-backed.
- Symbols that fell out of the latest replay (replaced by better-scoring alternatives) will still show `replay_supported=True` and earn ACCUMULATE flags.
- The `replay_alignment_score` (multi-dim dimension 4) will be systematically wrong — its Coverage component (0–60 pts) counts replay-supported holdings by portfolio weight.

### Detection
No existing check. The UI `renderReplayAlignment()` shows counts but no indication of evidence file age.

### Recommended fix
Add a `_replay_evidence_age_warning()` check in `_load_replay_evidence()`:

```python
_REPLAY_INPUTS_STALE_DAYS = 14   # configurable
inputs_path = Path("data/current/replay_inputs.csv")
if inputs_path.exists():
    age_days = (datetime.now() - datetime.fromtimestamp(inputs_path.stat().st_mtime)).days
    if age_days > _REPLAY_INPUTS_STALE_DAYS:
        import warnings
        warnings.warn(f"replay_inputs.csv is {age_days} days old — replay evidence may be stale", stacklevel=2)
```

Alternatively, surface `replay_evidence_age_days` in the API response and render a staleness chip in the Replay Alignment section of the UI.

---

## Staleness Vector 2: Percentile Drift Across Universe Rebuilds

### Mechanism
`_compute_replay_alignment()` ([src/portfolio/scoring.py](src/portfolio/scoring.py#L340)) reads `replay_percentile` off the overlay objects. Those percentiles are computed in `_load_replay_evidence()` by sorting a replay cohort by `composite_score` values from `analytical_universe.csv` at overlay-build time.

If `analytical_universe.csv` is rebuilt between two portfolio analysis runs (e.g. after a signal refresh), the rank ordering of the same set of symbols within the same cohort can change, producing different percentiles for the same run_id replay cohort — **the underlying replay result has not changed, only the current composite score snapshot has.**

### Example
Suppose NVDA is in a 20-symbol cohort. Today its composite_score = 4.8, giving it the 20th rank (100th percentile). After a signal refresh its Danelfin score drops, pulling composite_score to 3.9, dropping it to rank 15 (75th percentile). A new portfolio run now shows NVDA replay_percentile=75, while a prior run on disk still shows replay_percentile=100 — both against the same historical replay event.

### Code location
[src/portfolio/recommendations.py](src/portfolio/recommendations.py#L115-L140) — `symbol_percentile` computation loop.

### Risk level
**Medium.** The percentile only feeds into two surfaces:
1. `MultiDimensionalScore.replay_alignment_score` Quality component (0–40 pts)
2. The "Replay Pctile" column in the Deployment Queue signal profile (display only)

The `replay_alignment_score` from a fresh run will differ from a loaded run's value whenever the universe has been rebuilt in between. Since `multi_dimensional_score` is **not persisted** by `load_analysis_run()` (see ui_data_path_trace.md), the loaded run displays no scorecard at all — masking the inconsistency rather than exposing it.

### Recommended fix (option A — snapshot percentile at run time)
Store `replay_evidence_snapshot_date` and `universe_build_date` in `run_metadata.json` so comparisons are possible. No code change required for correctness, only for auditability.

### Recommended fix (option B — decouple percentile from current universe)
Store the per-symbol composite scores used for percentile computation at overlay-build time in `security_overlays.csv`. When loading a historical run, re-derive percentile from the stored scores rather than the current universe. This makes loaded-run percentiles deterministic.

---

## Staleness Vector 3: `multi_dimensional_score` Not Persisted

`run_analysis()` computes and returns `multi_dimensional_score` in the live response (including `replay_alignment_score`). However, `load_analysis_run()` does **not** read this from disk — it is not written to a standalone JSON file.

### Consequence
- The four multi-dim scorecards (Allocation Alignment, Portfolio Quality, Implementation Quality, Replay Alignment) display on freshly-analyzed runs via `localStorage` cache.
- After cache eviction, a re-loaded run from the manifest will have no `multi_dimensional_score` in its API response, causing `renderMultiDimScores()` to silently produce an empty container.

### Fix
Write `multi_dimensional_score` to `run_dir/multi_dim_score.json` in `run_analysis()` and read it back in `load_analysis_run()`:

```python
# In run_analysis(), after computing multi_dim_score:
with open(out_dir / "multi_dim_score.json", "w") as fh:
    json.dump(dataclasses.asdict(multi_dim_score), fh, indent=2)

# In load_analysis_run():
mds_path = run_dir / "multi_dim_score.json"
if mds_path.exists():
    with open(mds_path) as fh:
        result["multi_dimensional_score"] = json.load(fh)
```

---

## Summary Table

| Staleness Vector | Severity | Silent failure? | Currently detected? | Recommended action |
|---|---|---|---|---|
| `replay_inputs.csv` age | HIGH | Yes | No | Add age warning in `_load_replay_evidence()` |
| Percentile drift across universe rebuilds | MEDIUM | Yes | No | Store `universe_build_date` in metadata; Option B for full fix |
| `multi_dimensional_score` not persisted | MEDIUM | Yes (silently empty) | No | Persist to `multi_dim_score.json` |
| Loaded runs show live Yahoo/Fidelity data | LOW | Yes (temporal mismatch) | No | Document as known design trade-off; add staleness indicator |
