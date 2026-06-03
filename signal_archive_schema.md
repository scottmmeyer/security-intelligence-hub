# Signal Archive Schema
**Phase 7.7B — Deliverable Q2**
**Generated:** 2026-06-01

---

## 1. Purpose

Define the canonical archive schema for Zacks and Danelfin signal history files. All capture, ingestion, and normalization tooling must conform to these schemas. This document is the authoritative schema reference for Phase 7.7B governance.

---

## 2. Source File Naming Convention

All dated capture files must follow this naming convention:

```
YYYY-MM-DD_<provider>.csv
```

Examples:
- `2026-06-07_zacks.csv`
- `2026-06-07_danelfin.csv`

Files named `latest_<provider>.csv` are alias convenience files only. They must not be used as the source for any history master or analysis.

---

## 3. Zacks Canonical Archive Schema

### 3.1 Source Schema (as captured)

These fields come directly from the Zacks export file. The `source_schema` defines the raw format before normalization.

| Field | Type | Required | Valid Values | Notes |
|-------|------|----------|-------------|-------|
| `capture_date` | `YYYY-MM-DD` | YES | Valid ISO date | Date the file was captured. Must match the filename date. |
| `symbol` | string | YES | Non-empty ticker | US equity ticker symbol. |
| `zacks_rank` | float or blank | CONDITIONAL | 1.0, 2.0, 3.0, 4.0, 5.0, or blank | 1=Strong Buy (best); 5=Strong Sell (worst). Blank = no rank assigned by Zacks. |
| `zacks_score` | float or blank | OPTIONAL | Any float | Underlying numeric score. Not required for normalization. |
| `zacks_label` | string | DERIVED | See label table | Human-readable label derived from `zacks_rank`. Not present in source file; added during ingestion. |
| `source_file` | string | YES | Filename | Basename of the source file (e.g., `2026-06-07_zacks.csv`). |
| `sourced_date` | `YYYY-MM-DD` | YES | Valid ISO date | Date embedded in the source file's `sourced_date` column. Must match `capture_date`. |
| `coverage_status` | string | DERIVED | See status codes | Classification of this row's data quality. Derived during ingestion. |

**Scaffold fields from source (not used in normalization):**

| Field | Current Status | Action |
|-------|---------------|--------|
| `abr` | Always blank in all files | Retain in source; exclude from master |
| `price_target` | Always blank in all files | Retain in source; exclude from master |
| `eps_growth` | Always blank in all files | Retain in source; exclude from master |

### 3.2 Zacks Rank-to-Label Mapping

| zacks_rank | Label | 5pt Equivalent |
|------------|-------|----------------|
| 1.0 | `STRONG_BUY` | 5 |
| 2.0 | `BUY` | 4 |
| 3.0 | `HOLD` | 3 |
| 4.0 | `SELL` | 2 |
| 5.0 | `STRONG_SELL` | 1 |
| blank | `UNRANKED` | null |

**Normalization rule:** 5pt score = `6 - zacks_rank` (inverted because Zacks rank 1 is best).

### 3.3 Zacks Coverage Status Codes

| coverage_status | Meaning | 5pt Score |
|----------------|---------|-----------|
| `COVERED` | Symbol has a valid, parseable rank | Set |
| `COVERED_BLANK_RANK` | Symbol present in file but rank field is blank | null |
| `OUT_OF_RANGE` | Rank value outside 1–5 range | null |
| `PARSE_ERROR` | Rank field present but not parseable as float | null |

---

## 4. Danelfin Canonical Archive Schema

### 4.1 Source Schema (as captured)

| Field | Type | Required | Valid Values | Notes |
|-------|------|----------|-------------|-------|
| `capture_date` | `YYYY-MM-DD` | YES | Valid ISO date | Date the file was captured. Must match the filename date. |
| `symbol` | string | YES | Non-empty ticker | US equity ticker symbol. |
| `danelfin_raw` | integer | CONDITIONAL | 1–10 | Raw 10-point score from Danelfin AI. |
| `danelfin_score` | float | CONDITIONAL | 1.0–5.0 | Danelfin-provided 5-point score with half-point increments. This is the primary normalization input. |
| `danelfin_label` | string | DERIVED | See label table | Human-readable label derived from `danelfin_score`. Not present in source file; added during ingestion. |
| `source_file` | string | YES | Filename | Basename of the source file. |
| `sourced_date` | `YYYY-MM-DD` | YES | Valid ISO date | Date embedded in source file. Must match `capture_date`. |
| `coverage_status` | string | DERIVED | See status codes | Classification of this row's data quality. |

### 4.2 Danelfin Score-to-Label Mapping

| danelfin_score range | Rounded 5pt | Label |
|---------------------|-------------|-------|
| 1.0–1.4 | 1 | `VERY_BEARISH` |
| 1.5–2.4 | 2 | `BEARISH` |
| 2.5–3.4 | 3 | `NEUTRAL` |
| 3.5–4.4 | 4 | `BULLISH` |
| 4.5–5.0 | 5 | `VERY_BULLISH` |
| blank | null | `UNSCORED` |

**Normalization rule:** 5pt score = `round(danelfin_score)` clamped to [1, 5]. The standard Python `round()` function is used (banker's rounding). For safety, an explicit `int(score + 0.5)` implementation is preferred to ensure 0.5 always rounds up.

### 4.3 Danelfin Coverage Status Codes

| coverage_status | Meaning | 5pt Score |
|----------------|---------|-----------|
| `COVERED` | Symbol has a valid, parseable score in range 1.0–5.0 | Set |
| `COVERED_BLANK_SCORE` | Symbol present but score field is blank | null |
| `OUT_OF_RANGE` | Score present but outside 1.0–5.0 (e.g., 0.5 as seen in 2026-05-21) | null |
| `PARSE_ERROR` | Score field present but not parseable as float | null |

---

## 5. Normalized History Master Schema

Both `zacks_history_master.csv` and `danelfin_history_master.csv` must conform to this canonical schema:

| Field | Type | Description |
|-------|------|-------------|
| `capture_date` | `YYYY-MM-DD` | Date of the source capture file |
| `symbol` | string | Ticker symbol |
| `normalized_5pt_score` | integer (1–5) or blank | 5pt normalized score; blank if coverage_status is not COVERED |
| `raw_value` | string | Original raw value from source (zacks_rank or danelfin_score) |
| `source_file` | string | Source file basename |
| `provider` | string | `ZACKS` or `DANELFIN` |
| `coverage_status` | string | See coverage status codes above |

**Constraints:**
- One row per (capture_date, symbol) combination
- No duplicate (capture_date, symbol) pairs permitted
- `capture_date` must match the filename date in `source_file`
- `normalized_5pt_score` must be null/blank if `coverage_status != COVERED`
- `normalized_5pt_score` must be an integer in [1, 5] if `coverage_status == COVERED`

---

## 6. File Placement and Directory Structure

```
data/
  signals/
    zacks/
      YYYY-MM-DD_zacks.csv       ← dated source files (raw, as captured)
      latest_zacks.csv           ← alias only; not for analysis
    danelfin/
      YYYY-MM-DD_danelfin.csv    ← dated source files (raw, as captured)
      latest_danelfin.csv        ← alias only; not for analysis
  history/
    signals/
      zacks_history_master.csv   ← normalized master (rebuilt from source files)
      danelfin_history_master.csv ← normalized master (rebuilt from source files)
```

**Master file rebuild rule:** History masters are rebuilt from scratch by re-processing all dated source files. They are derivative, not primary. The dated source files under `data/signals/` are the primary archive.

---

## 7. Schema Versioning

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-06-01 | Initial schema definition (Phase 7.7B) |

Future schema changes must:
1. Increment the version
2. Update this document
3. Trigger a full master rebuild
4. Log the change in the governance report
