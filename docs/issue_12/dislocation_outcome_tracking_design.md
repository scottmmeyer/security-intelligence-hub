# Dislocation Outcome Tracking Design
## ISSUE-12 Assessment — June 5, 2026

---

## 1. Background: What Exists Today

SIH currently classifies dislocation at analysis-run time and serves the result
in the `dislocation_by_symbol` payload. Each PAR run already produces:

| Artifact | Path | Contains |
|----------|------|---------|
| `deployment_queue.json` | `analysis_runs/{run_id}/` | CW-DAS rank, score, tier, fundamental modifier |
| `security_overlays.csv` | `analysis_runs/{run_id}/` | ESS, Danelfin, replay_percentile, replay_supported, composite_score |
| `run_metadata.json` | `analysis_runs/{run_id}/` | snapshot_date, run_id, created_at_utc |
| `dislocation_by_symbol` | API response only | tier, active_classes, evidence, version |

**Key gap:** `dislocation_by_symbol` is computed at read time but **not persisted
to disk**. To build a tracking database, dislocation snapshots must be written to
a persistent artifact at run time.

**Historical baseline:** 210 runs across 12 portfolio dates (May 21 – June 5,
2026). This represents 2 weeks of run history. Dislocation tracking begins
from the first date a `dislocation_by_symbol` JSON artifact is written to disk
(ISSUE-04B shipped June 5, 2026). Prior runs cannot be retroactively classified
without replaying through the updated pipeline.

---

## 2. Q1 — What Should Be Tracked?

### Minimum Required Detection Snapshot

Each detection event record should capture the state at the moment dislocation
was first classified. These fields are already available in existing artifacts:

| Field | Source | Required |
|-------|--------|----------|
| `detection_date` | `run_metadata.snapshot_date` | ✅ Required |
| `run_id` | `run_metadata.run_id` | ✅ Required (for lineage) |
| `symbol` | `dislocation_by_symbol` | ✅ Required |
| `tier` | `dislocation_by_symbol` | ✅ Required |
| `dislocation_class` | `dislocation_by_symbol` | ✅ Required |
| `active_classes` | `dislocation_by_symbol` | ✅ Required |
| `evidence` | `dislocation_by_symbol` | ✅ Required |
| `ess_at_detection` | `security_overlays.csv` | ✅ Required |
| `danelfin_at_detection` | `security_overlays.csv` | ✅ Required |
| `replay_percentile_at_detection` | `security_overlays.csv` | ✅ Required |
| `replay_supported_at_detection` | `security_overlays.csv` | ✅ Required |
| `composite_score_at_detection` | `security_overlays.csv` | ✅ Required |
| `cw_das_score_at_detection` | `deployment_queue.json` | Recommended |
| `cw_das_rank_at_detection` | `deployment_queue.json` | Recommended |
| `thesis_integrity_at_detection` | `deployment_queue.json` (score_breakdown) | Recommended |
| `fundamental_modifier_at_detection` | `deployment_queue.json` (score_breakdown) | Recommended |
| `dislocation_version` | `dislocation_by_symbol` | ✅ Required |

### Outcome Fields (added later, when price data is sourced)

| Field | Source | Required |
|-------|--------|----------|
| `outcome_date` | Derived from detection_date + holding_period | ✅ Required |
| `price_at_detection` | `current_price` from Yahoo supplemental | ✅ Required |
| `price_at_outcome` | External price source (future integration) | ✅ Required |
| `absolute_return_pct` | Computed | ✅ Required |
| `benchmark_return_pct` | Benchmark source | ✅ Required |
| `excess_return_pct` | Derived | ✅ Required |

### Fields to NOT Track

- Portfolio weight (changes detection profile; not a signal quality input)
- CRA proposal status (not relevant to outcome measurement)
- Tax position (operator-specific; not generalizable)
- Operator policies (DO_NOT_SELL etc. distort natural signal outcome)

---

## 3. Detection Snapshot Format

Proposed CSV schema for `data/derived/dislocation_detections.csv`:

```
detection_date, run_id, symbol, tier, dislocation_class, active_classes,
ess_at_detection, danelfin_at_detection, replay_percentile_at_detection,
replay_supported_at_detection, composite_score_at_detection,
cw_das_score_at_detection, thesis_integrity_at_detection,
fundamental_modifier_at_detection, dislocation_version
```

Append-only. Each run appends new detections. De-duplicate on
`(detection_date, symbol, tier)` to avoid re-counting when the same
dislocation persists across consecutive run dates.

---

## 4. Detection Continuity Model

A single dislocation can span multiple consecutive analysis dates. The tracking
model must distinguish:

**First Detection:** The first date a symbol appears at a given tier or higher.
This is the entry point for outcome measurement.

**Continued Detection:** The same symbol at the same tier on subsequent dates.
These should NOT re-start the holding period clock.

**Tier Escalation:** Symbol moves from WATCH → MODERATE → HIGH_CONVICTION.
Record as a new detection event at the escalated tier with the escalation_date.

**Resolution:** Symbol returns to NONE. Record the resolution date and final tier.

A symbol that oscillates (detected → resolves → detected again) generates
separate tracking records each time.

---

## 5. Price Data Requirements

SIH currently stores `current_price` in `latest_yahoo_supplemental.csv` at
fetch time. This provides the price-at-detection field.

For outcome measurement, `price_at_outcome` requires either:

1. **Persistent daily price history** — a new data artifact storing adjusted
   close prices per symbol per date (not currently in SIH)
2. **Post-hoc fetch at measurement time** — query Yahoo/yfinance for historical
   prices at T+30, T+60, T+90 dates when generating outcome reports

Option 2 is simpler for initial implementation — no new daily pipeline required.
However, it cannot produce outcome reports in real-time during the holding period.

**Recommendation:** Use Option 2 for initial implementation. Architect for
Option 1 in a future enhancement phase.

---

## 6. Implementation Phases

**ISSUE-12A (assessment — this document):** Define schema, methodology, governance.

**ISSUE-12B (persistence):** Write `dislocation_detections.csv` at run time.
Add detection writer to `runner.py` (additive, ~30 lines). No scoring changes.

**ISSUE-12C (outcome computation):** 90-day outcome fetch script. Reads
`dislocation_detections.csv`, fetches historical prices via yfinance, writes
`dislocation_outcomes.csv`. Batch job, not real-time.

**ISSUE-12D (reporting):** Display outcome statistics in the Dislocation
Watchlist panel or a dedicated research view. Gate: only after 90 days of data.
