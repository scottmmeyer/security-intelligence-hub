# Signal Archive Quality Gates
**Phase 7.7B — Deliverable Q5**
**Generated:** 2026-06-01

---

## 1. Purpose

Define fail-closed quality gates for Zacks and Danelfin archive ingestion. All captures must pass all gates before being appended to the history masters. A failing gate must block the append operation and generate a logged rejection report.

**Philosophy:** Fail closed. A missing capture is always preferable to a corrupt or stale capture in the history master. Operators must explicitly override a failing gate with a documented justification.

---

## 2. Gate Categories

| Category | Description |
|----------|-------------|
| **STRUCTURAL** | File existence, format, encoding |
| **FRESHNESS** | Date validation, staleness detection |
| **COVERAGE** | Symbol count, row count, deduplication |
| **CONTENT** | Field validation, range checks, parse success |
| **INTEGRITY** | Checksum, duplicate file detection |
| **DELTA** | Change detection versus prior capture |

---

## 3. Zacks Quality Gates

### Gate Z-01 — File Exists
- **Category:** STRUCTURAL
- **Test:** File at expected path `data/signals/zacks/YYYY-MM-DD_zacks.csv` exists and is non-empty
- **Fail condition:** File missing or zero bytes
- **Action on fail:** BLOCK — log `GATE_Z01_FILE_MISSING`

### Gate Z-02 — Required Columns Present
- **Category:** STRUCTURAL
- **Test:** File header row contains `symbol`, `zacks_rank`, `sourced_date` (minimum required fields)
- **Fail condition:** Any of the three minimum columns absent from header
- **Action on fail:** BLOCK — log `GATE_Z02_MISSING_COLUMNS`

### Gate Z-03 — Row Count Above Minimum Threshold
- **Category:** COVERAGE
- **Test:** Data rows (excluding header) ≥ 500
- **Rationale:** Full-universe Zacks exports contain ~2,568 rows. A row count below 500 indicates a partial export, a connection failure mid-download, or a malformed file.
- **Fail condition:** Data rows < 500
- **Action on fail:** BLOCK — log `GATE_Z03_ROW_COUNT_LOW` with actual count
- **Override:** Operator may override with `PARTIAL_CAPTURE` justification; file is still archived with `coverage_status=PARTIAL_EXPORT`

### Gate Z-04 — Symbol Count vs. Prior Capture Delta
- **Category:** DELTA
- **Test:** Unique symbol count within ±20% of the most recent prior full-universe capture
- **Rationale:** Sudden symbol count drops or spikes indicate export anomaly, not genuine universe changes. Zacks baseline: ~2,568 symbols.
- **Fail condition:** Symbol count < 2,054 (−20%) or > 3,082 (+20%)
- **Action on fail:** WARN — log `GATE_Z04_SYMBOL_DELTA_EXCEEDED` with delta %; allow append but flag file as `coverage_status=COVERAGE_ANOMALY`

### Gate Z-05 — Sourced Date Matches Capture Date
- **Category:** FRESHNESS
- **Test:** `sourced_date` column values match the filename date within ±1 calendar day
- **Rationale:** A file named `2026-06-07_zacks.csv` must contain `sourced_date=2026-06-07`. A mismatch indicates the file is stale or was copied from a prior capture.
- **Fail condition:** >10% of rows have `sourced_date` differing by more than 1 day from the filename date
- **Action on fail:** BLOCK — log `GATE_Z05_SOURCED_DATE_MISMATCH`

### Gate Z-06 — Sourced Date Not Future-Dated
- **Category:** FRESHNESS
- **Test:** No `sourced_date` values later than the current system date
- **Fail condition:** Any row has `sourced_date` > today
- **Action on fail:** BLOCK — log `GATE_Z06_FUTURE_DATED`

### Gate Z-07 — Rank Parse Success Rate
- **Category:** CONTENT
- **Test:** ≥ 90% of rows with non-blank rank can be parsed as float in [1.0, 5.0]
- **Rationale:** Occasional blank ranks (4.1% in baseline) are normal. A sudden spike in unparseable ranks indicates a format change.
- **Fail condition:** Parse success rate < 90% of non-blank rows
- **Action on fail:** BLOCK — log `GATE_Z07_PARSE_FAILURE_RATE` with failure count

### Gate Z-08 — Duplicate File Detection
- **Category:** INTEGRITY
- **Test:** MD5 checksum of incoming file does not match any previously archived file's checksum
- **Rationale:** Prevents re-archiving the same file under a different date (e.g., if operator re-downloads and re-submits an old export).
- **Fail condition:** MD5 match found in checksum registry
- **Action on fail:** BLOCK — log `GATE_Z08_DUPLICATE_CHECKSUM` with matching prior filename

### Gate Z-09 — No Duplicate Symbol-Date Pairs in Master
- **Category:** INTEGRITY
- **Test:** After append, no (capture_date, symbol) pair appears more than once in `zacks_history_master.csv`
- **Fail condition:** Duplicate pairs detected post-append
- **Action on fail:** ROLLBACK append, log `GATE_Z09_DUPLICATE_PAIRS`

### Gate Z-10 — Blank Rank Rate Within Expected Range
- **Category:** CONTENT
- **Test:** Blank rank rate ≤ 10% of total rows
- **Rationale:** Baseline blank rate is 4.1% (105/2,568). A rate above 10% indicates a data quality problem, not normal variation.
- **Fail condition:** Blank rank rate > 10%
- **Action on fail:** WARN — log `GATE_Z10_HIGH_BLANK_RATE` with actual rate; allow append with flag

---

## 4. Danelfin Quality Gates

### Gate D-01 — File Exists
- **Category:** STRUCTURAL
- **Test:** File at expected path `data/signals/danelfin/YYYY-MM-DD_danelfin.csv` exists and is non-empty
- **Fail condition:** File missing or zero bytes
- **Action on fail:** BLOCK — log `GATE_D01_FILE_MISSING`

### Gate D-02 — Required Columns Present
- **Category:** STRUCTURAL
- **Test:** File header contains `symbol`, `danelfin_score`, `sourced_date`
- **Fail condition:** Any minimum column absent
- **Action on fail:** BLOCK — log `GATE_D02_MISSING_COLUMNS`

### Gate D-03 — Row Count Above Minimum Threshold
- **Category:** COVERAGE
- **Test:** Data rows ≥ 400
- **Rationale:** Danelfin's baseline is ~725–782 rows. A threshold of 400 allows for universe variation while still catching catastrophic failures.
- **Fail condition:** Data rows < 400
- **Action on fail:** BLOCK — log `GATE_D03_ROW_COUNT_LOW`
- **Override:** Operator may override with `PARTIAL_CAPTURE` justification

### Gate D-04 — Symbol Count vs. Prior Capture Delta
- **Category:** DELTA
- **Test:** Unique symbol count within ±25% of the most recent prior capture
- **Rationale:** Danelfin's universe appears less stable than Zacks (782 on 2026-05-20 vs. 725 on 2026-05-26). A ±25% tolerance avoids false alarms.
- **Fail condition:** Symbol count < 544 (−25% from 725 baseline) or > 978 (+25%)
- **Action on fail:** WARN — log `GATE_D04_SYMBOL_DELTA_EXCEEDED`

### Gate D-05 — Sourced Date Matches Capture Date
- **Category:** FRESHNESS
- **Test:** `sourced_date` column values match the filename date within ±1 calendar day
- **Fail condition:** >10% of rows have `sourced_date` differing by more than 1 day from the filename date
- **Action on fail:** BLOCK — log `GATE_D05_SOURCED_DATE_MISMATCH`

### Gate D-06 — Sourced Date Not Future-Dated
- **Category:** FRESHNESS
- **Test:** No `sourced_date` values later than today
- **Fail condition:** Any row has `sourced_date` > today
- **Action on fail:** BLOCK — log `GATE_D06_FUTURE_DATED`

### Gate D-07 — Score In-Range Rate
- **Category:** CONTENT
- **Test:** ≥ 98% of non-blank scores are in range [1.0, 5.0]
- **Rationale:** Baseline shows 2 out-of-range records in 33 rows (6.1%) on 2026-05-21 partial capture. A threshold of 98% on full-universe captures is realistic.
- **Fail condition:** Out-of-range rate > 2% for files with ≥ 400 rows
- **Action on fail:** WARN — log `GATE_D07_OUT_OF_RANGE_RATE` with count; allow append with OUT_OF_RANGE status

### Gate D-08 — Duplicate File Detection
- **Category:** INTEGRITY
- **Test:** MD5 checksum does not match any prior archived file
- **Fail condition:** MD5 match found
- **Action on fail:** BLOCK — log `GATE_D08_DUPLICATE_CHECKSUM`

### Gate D-09 — No Duplicate Symbol-Date Pairs in Master
- **Category:** INTEGRITY
- **Test:** After append, no (capture_date, symbol) pair appears more than once in `danelfin_history_master.csv`
- **Fail condition:** Duplicates detected
- **Action on fail:** ROLLBACK append, log `GATE_D09_DUPLICATE_PAIRS`

### Gate D-10 — Score Format Consistency
- **Category:** CONTENT
- **Test:** All parseable scores follow half-point increment format (1.0, 1.5, 2.0, ..., 5.0)
- **Rationale:** Danelfin uses exactly 9 score values. Scores like 1.3 or 2.7 would indicate a format change that requires schema review.
- **Fail condition:** Any score not in {1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0} found in ≥ 1% of scored rows
- **Action on fail:** WARN — log `GATE_D10_NON_STANDARD_SCORES` with examples; trigger schema review

---

## 5. Gate Summary Table

| Gate | Provider | Category | Fail Type | Applies to Masters? |
|------|----------|----------|-----------|---------------------|
| Z-01 | Zacks | STRUCTURAL | BLOCK | Pre-append |
| Z-02 | Zacks | STRUCTURAL | BLOCK | Pre-append |
| Z-03 | Zacks | COVERAGE | BLOCK* | Pre-append |
| Z-04 | Zacks | DELTA | WARN | Pre-append |
| Z-05 | Zacks | FRESHNESS | BLOCK | Pre-append |
| Z-06 | Zacks | FRESHNESS | BLOCK | Pre-append |
| Z-07 | Zacks | CONTENT | BLOCK | Pre-append |
| Z-08 | Zacks | INTEGRITY | BLOCK | Pre-append |
| Z-09 | Zacks | INTEGRITY | ROLLBACK | Post-append |
| Z-10 | Zacks | CONTENT | WARN | Pre-append |
| D-01 | Danelfin | STRUCTURAL | BLOCK | Pre-append |
| D-02 | Danelfin | STRUCTURAL | BLOCK | Pre-append |
| D-03 | Danelfin | COVERAGE | BLOCK* | Pre-append |
| D-04 | Danelfin | DELTA | WARN | Pre-append |
| D-05 | Danelfin | FRESHNESS | BLOCK | Pre-append |
| D-06 | Danelfin | FRESHNESS | BLOCK | Pre-append |
| D-07 | Danelfin | CONTENT | WARN | Pre-append |
| D-08 | Danelfin | INTEGRITY | BLOCK | Pre-append |
| D-09 | Danelfin | INTEGRITY | ROLLBACK | Post-append |
| D-10 | Danelfin | CONTENT | WARN | Pre-append |

*BLOCK with operator override available.

---

## 6. Gate Log Schema

All gate events must be logged to a capture report file (see Q6 Runbook for format):

| Field | Description |
|-------|-------------|
| `timestamp` | ISO datetime of gate evaluation |
| `provider` | ZACKS or DANELFIN |
| `capture_date` | Target capture date |
| `source_file` | Filename being evaluated |
| `gate_id` | Gate identifier (e.g., Z-03) |
| `gate_result` | PASS, WARN, BLOCK, ROLLBACK |
| `detail` | Human-readable detail (counts, values that triggered the gate) |
| `override_justification` | If operator overrode a BLOCK, required free-text justification |

---

## 7. Gate Threshold Review

Gate thresholds should be reviewed and updated after each of the following milestones:
- 30 days of systematic capture (June 2026 → July 2026)
- 90 days of systematic capture (September 2026)
- 6-month comparative study (December 2026)

If the Danelfin universe stabilizes at a different size, update Gate D-03 and D-04 thresholds accordingly.
