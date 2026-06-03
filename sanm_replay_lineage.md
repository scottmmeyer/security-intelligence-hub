# SANM Replay Lineage
**Phase 7.6D.1 — SANM Replay Forensics**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q1: Full SANM Lineage — Raw Artifacts to Deployment Queue

### Step 1: Raw Replay Artifacts on Disk

**File:** `data/history/replays/snapshot_date=2025-05-14/replay_id=REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-ALL-TOP20-WP05D-20260521-ALL-US-SMALL-ALL/`

SANM is selected in the **365-day HISTORICAL_VALIDATION** SMALL-ALL replay (snapshot_date=2025-05-14):

| Field | Value |
|---|---|
| replay_id | REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-ALL-TOP20-WP05D-20260521-ALL-US-SMALL-ALL |
| start_date | 2025-05-14 |
| end_date | 2026-05-14 |
| coverage_days | 365 |
| replay_mode | HISTORICAL_VALIDATION |
| basket_size | 20 |
| SANM position | 10 of 20 |
| basket strategy return | +104.6% |
| benchmark return (^RUT) | +37.4% |
| strategy vs benchmark delta | +67.2% |
| generated_at_utc | 2026-05-22T17:19:05Z |

This replay was generated on **2026-05-22** — seven days after the industry-specific 365-day replays were generated (2026-05-15). The replay evidence is complete and the file exists on disk.

SANM also appears in three CURRENT_RECOMMENDATION short-window replays (1-day, 4-day, and 6-day). See `sanm_historical_replay_inventory.csv` for full listing.

---

### Step 2: Replay Matrix Construction

**File:** `data/current/replay_matrix.csv` (120 rows + header)

The replay matrix is built by `build_wp05b_replay_matrix()` in `src/replay/foundation_service.py`. It registers which replays are available for the deployment routing system.

The 365-day SMALL-ALL replay is **not in `data/current/replay_matrix.csv`**.

What IS in the matrix for US-SMALL:

| Industry | Coverage Days | Mode | In Matrix |
|---|---|---|---|
| TECHNOLOGY | 365 | HISTORICAL_VALIDATION | YES |
| HEALTHCARE | 365 | HISTORICAL_VALIDATION | YES |
| INDUSTRIALS | 365 | HISTORICAL_VALIDATION | YES |
| ENERGY | 365 | HISTORICAL_VALIDATION | YES |
| CONSUMER_CYCLICAL | 365 | HISTORICAL_VALIDATION | YES |
| CONSUMER_DEFENSIVE | 365 | HISTORICAL_VALIDATION | YES |
| FINANCIAL_SERVICES | 365 | HISTORICAL_VALIDATION | YES |
| BASIC_MATERIALS | 365 | HISTORICAL_VALIDATION | YES |
| COMMUNICATION_SERVICES | 365 | HISTORICAL_VALIDATION | YES |
| REAL_ESTATE | 365 | HISTORICAL_VALIDATION | YES |
| UTILITIES | 365 | HISTORICAL_VALIDATION | YES |
| ALL | 6 | CURRENT_RECOMMENDATION | YES |

**The ALL-industry 365-day historical replay was generated after the matrix was finalized and was never registered.**

---

### Step 3: Replay Assignment — `_load_replay_evidence()`

**File:** `src/portfolio/recommendations.py`, function `_load_replay_evidence()`

**Source:** `data/current/replay_inputs.csv`

The function reads `replay_inputs.csv` row by row. For each row, it iterates `selected_symbols`:
- If `filter_industry == "ALL"`: assign `symbol_tier[sym] = f"{geo}.{cap}"` (first-seen wins)
- If `filter_industry` is specific: store in `industry_replay_evidence[sym]` (lower priority)

Since the 365-day SMALL-ALL replay is absent from `replay_inputs.csv`, the function finds SANM only in the 6-day CURRENT_RECOMMENDATION SMALL-ALL row:

```
replay_id: REPLAY-2026-05-20-TO-2026-05-26-US-SMALL-ALL-TOP20-WP05D-20260526-ALL2-US-SMALL-ALL
filter_industry: ALL
start_date: 2026-05-20
end_date: 2026-05-26
selected_symbols: ECG|IESC|INSW|LQDA|POWL|ARW|ENS|AGX|CRGY|MYRG|PAGP|VMI|AEIS|SANM|CHRD|CRC|DVA|LFUS|MUSA|OTTR
```

Result: `symbol_tier["SANM"] = "US.SMALL"`, replay_id = 6-day replay.

---

### Step 4: Security Overlay Creation

**File:** `src/portfolio/recommendations.py`, function `build_security_overlays()`

SANM's overlay is written with:
- `replay_supported = True` (derived from `in_replay = "SANM" in symbol_tier`)
- `replay_tier = "US.SMALL"`
- `flag_rationale = "SANM is replay-supported (tier: US.SMALL) with a strong score (4.277778)."`

This overlay is written to `data/portfolio_ingestion/analysis_runs/PAR-20260601-9CFD7C63/security_overlays.csv`.

```
PSNAP-20260601-8765A09ECC06,SANM,4.277778,BULLISH,5.0,,,True,...
```

The overlay does not record the replay window dates, coverage days, or mode — only the boolean `replay_supported=True`.

---

### Step 5: CW-DAS Scoring

**File:** `src/portfolio/deployment_queue.py`

```python
replay_c = 20.0 if replay_supported else 0.0
CW-DAS = signal_pts + replay_c + conviction_pts + sizing_pts + momentum_pts
```

SANM's replay component: **20 pts** (binary gate, `replay_supported=True`)

SANM's CW-DAS = 90.78:
- Signal + scoring component: ~70.78 pts
- Replay component: 20.00 pts

---

### Step 6: Deployment Queue

**File:** `data/portfolio_ingestion/analysis_runs/PAR-20260601-9CFD7C63/deployment_queue.json` and `ucf_verdicts.json`

| Field | Value |
|---|---|
| symbol | SANM |
| ucf_label | HIGH_CONVICTION_ANCHOR |
| ucf_score | 89.53 |
| cw_das_score | 90.78 |
| cw_das_rank | 11 |
| replay_supported | True |
| replay_percentile | null |

SANM ranks **11th** in the deployment queue. The 20-pt replay bonus is earned from a 6-day evidence window, sourced from an unregistered routing path.

---

## Lineage Summary

```
365-day SMALL-ALL HISTORICAL_VALIDATION replay (on disk, generated 2026-05-22)
    ↓
NOT registered in replay_matrix.csv (matrix built 2026-05-15, ALL-industry 365-day replays excluded)
    ↓
NOT in replay_inputs.csv
    ↓
_load_replay_evidence() scans replay_inputs.csv → finds SANM only in 6-day CURRENT_REC replay
    ↓
symbol_tier["SANM"] = "US.SMALL" with 6-day replay_id
    ↓
in_replay = True → replay_supported = True in security overlay
    ↓
CW-DAS replay_c = 20 pts (binary gate: True → 20)
    ↓
CW-DAS total = 90.78 → rank 11
```

The routing gap is at Step 2 (matrix construction) — not at the scoring layer. The 365-day evidence exists on disk, was never surfaced.

---

## Q6: Root Cause Classification

**Classification: `B. ROUTING_ARTIFACT`**

SANM's THIN evidence designation is not a signal quality problem and not a genuine data gap. The 365-day HISTORICAL_VALIDATION SMALL-ALL replay exists on disk with SANM legitimately selected at position 10 of 20 (basket return +104.6%). It was generated 7 days after the matrix was finalized and was never registered.

The root cause is a matrix construction sequencing gap:
1. `build_wp05b_replay_matrix()` was run on 2026-05-15 and registered industry-specific 365-day replays (which were available at that date)
2. The 365-day ALL-industry replays were generated as a post-hoc supplemental run on 2026-05-21/22
3. The matrix was not updated after the ALL-industry 365-day replays were generated
4. `_load_replay_evidence()` reads only `replay_inputs.csv` — it cannot discover replays on disk that are not registered

This is a process sequencing gap, not a code defect. The code (`_load_replay_evidence()`, `build_security_overlays()`) is working correctly. The replay_inputs.csv contents are incomplete.

**Eliminated alternative root causes:**
- `A. GENUINE_THIN_EVIDENCE` — ruled out. 365-day evidence exists on disk. SANM made the top-20 SMALL-ALL basket at the May 2025 snapshot.
- `C. WRONG_BUCKET_CLASSIFICATION` — ruled out. SANM is correctly classified as TECHNOLOGY, SMALL, US. The issue is not the bucket; it is the missing ALL-industry 365-day replay registration.

---

## Q7: Final Recommendation

**Recommendation: `B. FIX_REPLAY_ROUTING_FIRST`**

Before implementing depth-aware scoring (Phase 7.6D recommendation C), register the 365-day HISTORICAL_VALIDATION ALL-industry replays in `replay_matrix.csv` and `replay_inputs.csv`.

**Immediate action (SANM fix):**
Register `REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-ALL-TOP20-WP05D-20260521-ALL-US-SMALL-ALL` in the matrix. Re-run the PAR. SANM will be classified as STRONG (365-day HISTORICAL_VALIDATION), retain rank 11, and the HIGH_CONVICTION_ANCHOR label is properly earned.

**Systemic action (ALL-industry gap):**
Register all 365-day ALL-industry replays from `data/history/replays/snapshot_date=2025-05-14/` across all cap buckets (US-MEGA-ALL, US-LARGE-ALL, US-MID-ALL, US-SMALL-ALL, US-MICRO-ALL, and INTERNATIONAL equivalents). Update the matrix build process to incorporate supplemental replay runs after the initial build.

**Effect on Phase 7.6D conclusions:**
- Phase 7.6D concluded `C. ADD_DEPTH_AWARE_REPLAY_SCORING` based on SANM's apparent THIN evidence
- After routing fix, SANM has STRONG evidence — Model B rank impact (11→33) disappears entirely
- Only remaining depth calibration cases: AEIS (genuine THIN, not in ranked queue), GTX/SIMO/SBS (BUCKET_ONLY, ranks 34–42, minor impact)
- Phase 7.6D's depth-aware scoring reform is conceptually sound but its urgency drops materially once SANM is correctly classified
- Recommend: fix routing first, re-evaluate depth-aware scoring priority against clean data
