# Replay Integrity Classification
**Phase 7.6D.2 — Replay Historical Signal Integrity Audit**
**Date:** 2026-06-01

---

## Q5: Classification of Every Replay Snapshot by Signal Fidelity

### Classification Framework

| Class | Definition |
|---|---|
| CLASS A — Authentic | All material signals captured contemporaneously. ESS source file date matches snapshot date (within ±1 day). Zacks and/or Danelfin partially available from authentic archives. |
| CLASS B — Mixed | ESS is authentic, but secondary signals (Zacks, Danelfin) are absent or derived from non-contemporaneous sources. Composite_score effectively ESS-only. |
| CLASS C — Mostly Reconstructed | ESS is from a file within 30 days of the snapshot date but not contemporaneous. Secondary signals absent. |
| CLASS D — Current Signals Applied Retrospectively | ESS source file is dated materially after the snapshot date (>30 days forward). Basket selection determined by signals known only in hindsight. |

---

## Snapshot-Level Classification

### Snapshot: 2025-05-14 (HISTORICAL_VALIDATION, 365-day)

**Classification: CLASS D**

| Signal | Status | Source | Provenance |
|---|---|---|---|
| ESS (Fidelity StarMine) | Present (2,560 rows) | `EquitySummarScores_May-15-2026.csv` | **366 days FORWARD** of snapshot date |
| Zacks | 1 row only | ESS file embedded proxy from 2026 | **RECONSTRUCTED** |
| Danelfin | 1 row only | 2026 source | **RECONSTRUCTED** |
| Yahoo | 0 rows | Not integrated | **MISSING** |

**Evidence of CLASS D:** The analytical_universe for snapshot_date=2025-05-14 references `EquitySummarScores_May-15-2026.csv` (note: file name includes "2026") in every row's `provider_lineage`. This file was the current ESS input when the WP05D historical batch was constructed on or around 2026-05-15.

**Framework's lookahead validator result:** PASS — The validator checks `composite_score_snapshot_date == start_date` (both equal "2025-05-14"). The date metadata field is correct. The validator does not inspect the provenance of the actual ESS file used to populate those scores.

**Lookahead gap:** 366 days. Every composite_score ranking for the 2025-05-14 snapshot was computed with ESS signals that reflect analyst opinion from May 2026 — after the full 365-day return period had elapsed.

**Replays affected:** 200 HISTORICAL_VALIDATION replays at snapshot_date=2025-05-14 (110 in replay_matrix, 90 additional on disk not in matrix)

---

### Snapshot: 2025-05-13 (CURRENT_RECOMMENDATION, 365-day window)

**Classification: CLASS D**

| Signal | Status | Source | Provenance |
|---|---|---|---|
| ESS | Present (2,502 rows) | `SecurityExtract_ESS_2026May13.csv` | **365 days FORWARD** |
| Zacks | 0 rows | starmine_zacks.csv present, 0 populated | **RECONSTRUCTED** |
| Danelfin | 0 rows | None | **MISSING** |
| Yahoo | 0 rows | Not integrated | **MISSING** |

**Replays affected:** 10 CURRENT_RECOMMENDATION replays at snapshot_date=2025-05-13 (not in replay_matrix)

---

### Snapshot: 2026-05-13 (not in replay_matrix)

**Classification: CLASS B**

| Signal | Status | Source | Provenance |
|---|---|---|---|
| ESS | Present (2,502 rows) | `SecurityExtract_ESS_2026May13.csv` | Matches snapshot date — **AUTHENTIC** |
| Zacks | 0 rows | ESS Zacks proxy available | **ESS-EMBEDDED PROXY** |
| Danelfin | 0 rows | None | **MISSING** |
| Yahoo | 0 rows | Not integrated | **MISSING** |

ESS is authentic. Secondary signals are absent. Composite_score is ESS-driven with no independent confirmation.

---

### Snapshot: 2026-05-14 (not in replay_matrix)

**Classification: CLASS B**

| Signal | Status | Source | Provenance |
|---|---|---|---|
| ESS | Present (2,559 rows) | `ESS_2026May14.csv` | **AUTHENTIC** |
| Zacks | 0 rows | Proxy only | **ESS-EMBEDDED PROXY** |
| Danelfin | 0 rows | None | **MISSING** |
| Yahoo | 0 rows | Not integrated | **MISSING** |

---

### Snapshot: 2026-05-20 (CURRENT_RECOMMENDATION, 6-day — IN REPLAY_MATRIX)

**Classification: CLASS A**

| Signal | Status | Source | Provenance |
|---|---|---|---|
| ESS | Present (2,802 rows) | `ESS1.csv` | **AUTHENTIC** |
| Zacks | 63 rows | `2026-05-20_zacks.csv` | **AUTHENTIC** (sparse coverage) |
| Danelfin | 800 rows | `2026-05-20_danelfin.csv` | **AUTHENTIC** (partial coverage) |
| Yahoo | 0 rows | Not integrated into AU | **MISSING** |

Minor caveat: Zacks coverage is 63/2802 = 2.2% of universe. Danelfin coverage is 800/2802 = 28.6%. ESS coverage is near-complete. Composite_score is effectively ESS-dominant with partial Zacks/Danelfin augmentation.

---

### Snapshot: 2026-05-22 (CURRENT_RECOMMENDATION, 4-day — not in matrix)

**Classification: CLASS A**

ESS authentic, Zacks sparse, Danelfin partial. Same structure as 2026-05-20.

---

### Snapshot: 2026-05-31 (not in replay_matrix)

**Classification: CLASS A**

Zacks coverage reaches 2,480/2,586 = 95.9%. Most complete multi-signal snapshot in the dataset.

---

## Summary Counts

### Replays in replay_matrix.csv (120 total)

| Class | Count | % | Description |
|---|---|---|---|
| CLASS A | 10 | 8.3% | 2026-05-20 CURRENT_RECOMMENDATION ALL-industry replays |
| CLASS D | 110 | 91.7% | 2025-05-14 HISTORICAL_VALIDATION 365-day industry-specific replays |

**91.7% of replay_matrix entries are CLASS D (current signals applied retrospectively).**

### Replays on Disk (all snapshots, ~247 total)

| Class | Count | % | Description |
|---|---|---|---|
| CLASS A | ~27 | 10.9% | 2026-05-20 (20) + 2026-05-22 (7) |
| CLASS B | 0 | 0% | No replays computed at snapshot_dates=2026-05-13/14 |
| CLASS D | ~220 | 89.1% | 2025-05-14 (200 HV + 20 CR) + 2025-05-13 (10 CR) |

---

## Composite Score Formula Impact

The v1 production composite_score formula (used for all replay basket selections):
```
composite_score = (ESS × 0.55) + (Zacks × 0.25) + (Yahoo × 0.10, unused) + (Danelfin × 0.10)
When Zacks missing: ESS fallback (ess_zacks_rating from ESS file itself)
When Danelfin missing: proportional reweight toward ESS
```

For CLASS D snapshots (2025-05-14):
- ESS provides the dominant component (~55–80% of score)
- Zacks derived from the ESS file's own Zacks column (also from 2026)
- Danelfin: 1 row (effectively absent)
- **~100% of composite_score signal originates from May 2026 data**

---

## Why CLASS D Doesn't Necessarily Invalidate Replays

ESS is a consensus-driven signal. It reflects aggregated analyst opinion and changes slowly (quarters, not days). A company rated BULLISH in May 2026 was likely BULLISH in May 2025 if its fundamental trajectory was consistent. The look-ahead bias is not guaranteed to be severe.

However: any company that was rated NEUTRAL or BEARISH in May 2025 and improved to BULLISH by May 2026 (because it performed well over that period) would have been **incorrectly included** in the basket selection using 2026 signals. This is survivorship bias: selecting winners after the performance is known.

**The magnitude of this bias cannot be quantified without authentic May 2025 ESS data**, which does not exist in any accessible form.
