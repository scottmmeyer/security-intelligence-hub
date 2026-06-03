# Zacks and Danelfin Archive Inventory
**Phase 7.7B — Deliverable Q1**
**Generated:** 2026-06-01

---

## 1. Purpose

Inventory the existing Zacks and Danelfin signal archives as of 2026-06-01, establishing a baseline for ongoing governance. This report defines the starting condition before systematic archive capture begins.

---

## 2. Zacks Archive Inventory

### 2.1 File Manifest

| File | Capture Date | Rows | Symbols | Blank Rank | Has Score | File Size | MD5 (8) |
|------|-------------|------|---------|-----------|-----------|-----------|---------|
| `2026-05-14_zacks.csv` | 2026-05-14 | 1 | 1 | 0 | 1 | 98 B | 5555c219 |
| `2026-05-20_zacks.csv` | 2026-05-20 | 1 | 1 | 0 | 1 | 99 B | ad28838d |
| `2026-05-21_zacks.csv` | 2026-05-21 | 78 | 78 | 9 | 69 | 2,167 B | 46050a3f |
| `2026-05-26_zacks.csv` | 2026-05-26 | 2,568 | 2,568 | 105 | 2,463 | 70,027 B | f370444b |
| `2026-05-29_zacks.csv` | 2026-05-29 | 725 | 725 | 31 | 694 | 19,808 B | 0af5a2b6 |
| `latest_zacks.csv` | (alias) | 2,601 | 2,601 | — | — | 70,892 B | 297aea9f |

**Note:** `latest_zacks.csv` is an alias file maintained by the upstream export process. It contains the union of the most recent full-universe capture. It is **not** a substitute for dated archive files and must not be used as a primary historical source.

### 2.2 Coverage Summary

| Metric | Value |
|--------|-------|
| Earliest capture date | 2026-05-14 |
| Latest capture date | 2026-05-29 |
| Archive span | 15 calendar days |
| Total dated files | 5 |
| Total observations (all dates) | 3,373 |
| Observations with valid rank | 3,228 (95.7%) |
| Unique symbols (all dates) | 2,601 |
| Full-universe dates | **1** (2026-05-26 only) |

### 2.3 Schema

**Source file schema:** `symbol, zacks_rank, zacks_score, abr, price_target, eps_growth, sourced_date`

| Field | Type | Population | Notes |
|-------|------|------------|-------|
| `symbol` | string | 100% | Ticker symbol |
| `zacks_rank` | float string | 95.7% | 1.0=Strong Buy, 5.0=Strong Sell; blank means no rank assigned |
| `zacks_score` | float string | ~95% | Underlying numeric score; not used for 5pt normalization |
| `abr` | float | 0% | Analyst Buy Rating — **never populated in any file** |
| `price_target` | float | 0% | **Never populated** |
| `eps_growth` | float | 0% | **Never populated** |
| `sourced_date` | date | 100% | Date the data was sourced (same as capture_date for dated files) |

**Known data quality issues:**
- Blank rank rows present in all files with more than 2 rows (4.1% of 2026-05-26 file)
- `abr`, `price_target`, `eps_growth` columns never populated — scaffold columns only
- 2026-05-14 and 2026-05-20 are single-symbol test captures (not full-universe)
- 2026-05-21 is partial capture (78 rows)
- 2026-05-29 is partial capture (725 rows vs. 2,568 on 2026-05-26)

### 2.4 Rank Distribution (2026-05-26, full-universe)

| Zacks Rank | Label | Count | % | 5pt Equivalent |
|------------|-------|-------|---|----------------|
| 1 | Strong Buy | 203 | 7.9% | 5 |
| 2 | Buy | 397 | 15.5% | 4 |
| 3 | Hold | 1,460 | 56.8% | 3 |
| 4 | Sell | 299 | 11.6% | 2 |
| 5 | Strong Sell | 104 | 4.0% | 1 |
| blank | No rank | 105 | 4.1% | — |

### 2.5 Known Gaps

| Gap Type | Description |
|----------|-------------|
| **No full-universe captures before 2026-05-26** | First two files are single-symbol tests. 2026-05-21 is partial (78 rows). |
| **No captures between 2026-05-29 and 2026-06-01** | 3-day gap (weekend); not operationally significant |
| **No historical archive before 2026-05-14** | Zero archive depth prior to May 2026 |
| **Three scaffold columns always empty** | `abr`, `price_target`, `eps_growth` |

---

## 3. Danelfin Archive Inventory

### 3.1 File Manifest

| File | Capture Date | Rows | Symbols | Blank Score | Out of Range | File Size | MD5 (8) |
|------|-------------|------|---------|------------|--------------|-----------|---------|
| `2026-05-14_danelfin.csv` | 2026-05-14 | 1 | 1 | 0 | 0 | 73 B | bee5dfd5 |
| `2026-05-20_danelfin.csv` | 2026-05-20 | 782 | 782 | 0 | 0 | 19,975 B | d2469645 |
| `2026-05-21_danelfin.csv` | 2026-05-21 | 33 | 33 | 6 | 2 | 855 B | dd30d114 |
| `2026-05-26_danelfin.csv` | 2026-05-26 | 725 | 725 | 0 | 0 | 18,533 B | 853c0b48 |
| `2026-05-29_danelfin.csv` | 2026-05-29 | 725 | 725 | 2 | 0 | 18,517 B | 93b778a9 |
| `latest_danelfin.csv` | (alias) | 954 | 954 | — | — | 24,321 B | 8910db49 |

**Note:** Same alias caveat as Zacks — `latest_danelfin.csv` is not a primary historical source.

### 3.2 Coverage Summary

| Metric | Value |
|--------|-------|
| Earliest capture date | 2026-05-14 |
| Latest capture date | 2026-05-29 |
| Archive span | 15 calendar days |
| Total dated files | 5 |
| Total observations (all dates) | 2,266 |
| Observations with valid score | 2,256 (99.6%) |
| Unique symbols (all dates) | 954 |
| Full-universe dates | **0** (no consistently full-universe capture) |

**Note on "full-universe":** Danelfin's maximum single-date count is 782 rows (2026-05-20). The 2026-05-26 and 2026-05-29 files each have 725 rows — 57 fewer symbols than the peak. There is no established baseline for what constitutes Danelfin's "full universe."

### 3.3 Schema

**Source file schema:** `symbol, danelfin_raw, danelfin_score, sourced_date`

| Field | Type | Population | Notes |
|-------|------|------------|-------|
| `symbol` | string | 100% | Ticker symbol |
| `danelfin_raw` | integer (1–10) | ~99% | Raw 10-point score from Danelfin AI |
| `danelfin_score` | float (1.0–5.0) | 99.6% | Normalized 5-point score with half-point increments |
| `sourced_date` | date | 100% | Date the data was sourced |

**Known data quality issues:**
- 2026-05-21: 6 blank scores, 2 records with `danelfin_score=0.5` (below valid floor of 1.0) → classified as OUT_OF_RANGE
- 2026-05-29: 2 blank scores
- 2026-05-14 is a single-symbol test capture
- Coverage drops from 782 (2026-05-20) to 725 (2026-05-26) — unclear whether this is a universe reduction or incomplete export

### 3.4 Score Distribution (2026-05-20, largest capture)

| Danelfin Score | Count | 5pt Bucket |
|---------------|-------|-----------|
| 1.0 | 9 | 1 |
| 1.5 | 61 | 2 |
| 2.0 | 131 | 2 |
| 2.5 | 167 | 3 |
| 3.0 | 177 | 3 |
| 3.5 | 118 | 4 |
| 4.0 | 85 | 4 |
| 4.5 | 26 | 5 |
| 5.0 | 8 | 5 |

Distribution is bell-shaped, concentrated in middle buckets. Bucket 5 (score 4.5–5.0) has only 34 symbols — insufficient for statistical analysis.

### 3.5 Known Gaps

| Gap Type | Description |
|----------|-------------|
| **No full-universe definition** | Maximum single-date count is 782; drops to 725 in later captures |
| **No historical archive before 2026-05-14** | Zero archive depth prior to May 2026 |
| **Out-of-range scores in 2026-05-21** | 2 records with score=0.5 (below 1.0 floor) — export anomaly |
| **Blank score records** | 8 total across all files |
| **Single test capture on 2026-05-14** | Not usable for analysis |

---

## 4. Comparative Archive Summary

| Dimension | Zacks | Danelfin |
|-----------|-------|----------|
| Archive start | 2026-05-14 | 2026-05-14 |
| Archive end | 2026-05-29 | 2026-05-29 |
| Span | 15 days | 15 days |
| Total observations | 3,373 | 2,266 |
| Unique symbols | 2,601 | 954 |
| Full-universe snapshots | 1 | 0 |
| Coverage rate | 95.7% | 99.6% |
| Source schema fields | 7 (3 unused) | 4 (all used) |
| Data quality issues | Blank ranks (4.1%) | Out-of-range (0.09%), blanks (0.35%) |

**ESS comparison benchmark:** ESS has 54,566 observations, 2,918 symbols, 36 dates, 317-day archive. Zacks and Danelfin are at approximately 6% of ESS archive depth.

---

## 5. Recommended Baseline

**Official governance baseline as of 2026-06-01:**
- Zacks first credible full-universe capture: **2026-05-26** (2,568 rows)
- Danelfin first credible large-universe capture: **2026-05-20** (782 rows)
- Single-symbol test files (2026-05-14, 2026-05-20 for Zacks; 2026-05-14 for Danelfin) remain in archive for completeness but are excluded from effectiveness analysis

Future governance will use 2026-06-01 as the **archive governance start date** — the date from which systematic, fail-closed capture begins.
