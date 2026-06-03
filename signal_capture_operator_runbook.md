# Signal Capture Operator Runbook
**Phase 7.7B — Deliverable Q6**
**Generated:** 2026-06-01

---

## 1. Purpose

Step-by-step workflow for the operator performing a Zacks and Danelfin signal capture. This runbook is the authoritative operational reference. Follow each step in sequence. Do not skip steps.

**Cadence:** Twice weekly — Tuesday and Friday.
**Time estimate:** 15–20 minutes per capture session.
**Scope:** One session captures BOTH Zacks and Danelfin.

---

## 2. Pre-Capture Checklist

Before beginning a capture session, verify:

- [ ] System date is correct (run `date` in terminal)
- [ ] You are in the SIH project directory: `/Users/scottmmeyer/Projects/security-intelligence-hub`
- [ ] Virtual environment is active: `source .venv/bin/activate`
- [ ] Landing directories exist:
  - `data/signals/zacks/`
  - `data/signals/danelfin/`
- [ ] History master files exist:
  - `data/history/signals/zacks_history_master.csv`
  - `data/history/signals/danelfin_history_master.csv`

---

## 3. Step 1 — Download Zacks Export

**Source:** Zacks Investment Research export (web-based, requires Zacks Premium account)

1. Navigate to the Zacks screener or data export page
2. Select the full US equity universe (do not apply ticker filters)
3. Confirm the following fields are included in the export:
   - symbol (ticker)
   - zacks_rank
   - zacks_score (if available)
   - sourced_date (or export date)
4. Download as CSV
5. **Do NOT open the file in Excel** before saving — Excel silently reformats dates and numeric values
6. Save the raw downloaded file as: `YYYY-MM-DD_zacks.csv` where YYYY-MM-DD is today's date
   - Example: `2026-06-07_zacks.csv`

**File naming is critical.** The filename date must match the actual download date.

---

## 4. Step 2 — Download Danelfin Export

**Source:** Danelfin AI platform export (requires Danelfin account)

1. Navigate to the Danelfin export or screener page
2. Select the full coverage universe (do not apply filters)
3. Confirm the following fields are included:
   - symbol (ticker)
   - danelfin_raw (1–10 score)
   - danelfin_score (1.0–5.0 normalized score)
   - sourced_date (or export date)
4. Download as CSV
5. Do NOT open in Excel before saving
6. Save as: `YYYY-MM-DD_danelfin.csv` using today's date
   - Example: `2026-06-07_danelfin.csv`

---

## 5. Step 3 — Place Files in Landing Folders

Move downloaded files to the correct directories:

```bash
mv ~/Downloads/2026-06-07_zacks.csv \
   /Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/zacks/

mv ~/Downloads/2026-06-07_danelfin.csv \
   /Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/danelfin/
```

Verify placement:

```bash
ls -la data/signals/zacks/ | tail -5
ls -la data/signals/danelfin/ | tail -5
```

Confirm the new files appear with today's date and a non-zero file size.

---

## 6. Step 4 — Run Quality Gate Validation

Run the quality gate validation script against both new files:

```bash
PYTHONPATH=. .venv/bin/python3 scripts/validate_signal_capture.py \
  --zacks data/signals/zacks/2026-06-07_zacks.csv \
  --danelfin data/signals/danelfin/2026-06-07_danelfin.csv \
  --capture-date 2026-06-07
```

**Expected output:**

```
Gate Z-01: PASS (file exists, 70,027 bytes)
Gate Z-02: PASS (columns: symbol, zacks_rank, sourced_date)
Gate Z-03: PASS (2,568 data rows >= 500 threshold)
Gate Z-04: PASS (2,568 symbols, delta +0.0% vs prior 2,568)
Gate Z-05: PASS (100% sourced_date matches 2026-06-07 ± 1 day)
Gate Z-06: PASS (no future-dated records)
Gate Z-07: PASS (95.9% parse success rate)
Gate Z-08: PASS (MD5 f370444b not in checksum registry)
Gate Z-10: PASS (blank rank rate 4.1% < 10%)

Gate D-01: PASS (file exists, 18,533 bytes)
Gate D-02: PASS (columns: symbol, danelfin_score, sourced_date)
Gate D-03: PASS (725 data rows >= 400 threshold)
Gate D-04: PASS (725 symbols, delta -7.3% vs prior 782)
Gate D-05: PASS (100% sourced_date matches 2026-06-07 ± 1 day)
Gate D-06: PASS (no future-dated records)
Gate D-07: PASS (0 out-of-range scores)
Gate D-08: PASS (MD5 853c0b48 not in checksum registry)
Gate D-10: PASS (all scores in standard half-point set)

ALL GATES PASSED. Ready to append.
```

**If any gate shows BLOCK:** Do NOT proceed to append. See Section 10 (Error Handling).

**If any gate shows WARN:** Review the detail. If the anomaly is understood and acceptable, proceed. Log the decision in the capture report.

---

## 7. Step 5 — Normalize and Append to History Masters

Run the normalization and append script:

```bash
PYTHONPATH=. .venv/bin/python3 scripts/append_signal_capture.py \
  --zacks data/signals/zacks/2026-06-07_zacks.csv \
  --danelfin data/signals/danelfin/2026-06-07_danelfin.csv \
  --capture-date 2026-06-07
```

**What this script does:**
1. Reads both source files
2. Applies normalization rules (see `signal_archive_schema.md`)
3. Assigns `coverage_status` to each row
4. Appends new rows to `data/history/signals/zacks_history_master.csv`
5. Appends new rows to `data/history/signals/danelfin_history_master.csv`
6. Runs Gate Z-09 and D-09 (post-append duplicate check)
7. Rolls back both appends atomically if any post-append gate fails

**Expected output:**

```
Appending 2026-06-07 Zacks: 2,568 rows (2,463 COVERED, 105 COVERED_BLANK_RANK)
Appending 2026-06-07 Danelfin: 725 rows (725 COVERED)
Gate Z-09: PASS (no duplicate symbol-date pairs)
Gate D-09: PASS (no duplicate symbol-date pairs)
zacks_history_master.csv: 5,941 total rows (was 3,373)
danelfin_history_master.csv: 2,991 total rows (was 2,266)
Append complete. MD5: zacks=<hash>, danelfin=<hash>
```

---

## 8. Step 6 — Generate Capture Report

Run the capture report generator:

```bash
PYTHONPATH=. .venv/bin/python3 scripts/generate_capture_report.py \
  --capture-date 2026-06-07 \
  --output runs/capture_reports/
```

The report is saved to `runs/capture_reports/2026-06-07_capture_report.md`.

**Report contents:**
- Gate results for both providers
- Row counts before and after append
- Symbol coverage comparison vs. prior capture
- Score distribution comparison vs. prior capture
- Any WARN or BLOCK events with details
- Capture timestamp and MD5 checksums

---

## 9. Step 7 — Update latest_*.csv Aliases

After successful append, update the alias files:

```bash
cp data/signals/zacks/2026-06-07_zacks.csv data/signals/zacks/latest_zacks.csv
cp data/signals/danelfin/2026-06-07_danelfin.csv data/signals/danelfin/latest_danelfin.csv
```

These alias files are used by real-time scoring pipelines that need "current" signal values without knowing the exact capture date.

---

## 8. Step 8 — Commit Archive Artifacts

Commit the new files to the repository:

```bash
git add data/signals/zacks/2026-06-07_zacks.csv \
        data/signals/zacks/latest_zacks.csv \
        data/signals/danelfin/2026-06-07_danelfin.csv \
        data/signals/danelfin/latest_danelfin.csv \
        data/history/signals/zacks_history_master.csv \
        data/history/signals/danelfin_history_master.csv \
        runs/capture_reports/2026-06-07_capture_report.md

git commit -m "Signal capture 2026-06-07: Zacks 2568 rows, Danelfin 725 rows"
```

**Commit message format:**
```
Signal capture YYYY-MM-DD: Zacks <N> rows, Danelfin <N> rows
```

---

## 10. Error Handling

### 10.1 BLOCK Gate — File Not Found or Zero Bytes (Z-01, D-01)

The download failed or the file was placed in the wrong location.

1. Verify the download completed (check browser downloads)
2. Verify the file path is correct
3. If download was incomplete, re-download and restart from Step 1
4. Do NOT attempt to use a prior file to "cover" the missing capture — record the gap in the capture report

### 10.2 BLOCK Gate — Row Count Too Low (Z-03, D-03)

The export was a partial or truncated capture.

1. Check if the export tool showed an error or warning
2. If the provider had a known outage, record the date as a known gap
3. If the file is genuinely a partial export (still useful), file an override:
   ```bash
   # Add --override flag to append script with justification
   PYTHONPATH=. .venv/bin/python3 scripts/append_signal_capture.py \
     --zacks data/signals/zacks/2026-06-07_zacks.csv \
     --capture-date 2026-06-07 \
     --override-z03 "Provider export was 1,200 rows; verified partial outage on provider dashboard"
   ```
4. The file is archived with `coverage_status=PARTIAL_EXPORT` for all rows

### 10.3 BLOCK Gate — Sourced Date Mismatch (Z-05, D-05)

The file's `sourced_date` column doesn't match the filename date.

1. Open the file and inspect the `sourced_date` values
2. If the file is genuinely from a different date (e.g., operator downloaded yesterday's file today), rename the file to the correct date before running gates again
3. If the provider's export contains the wrong date, file an override with justification and note the discrepancy

### 10.4 BLOCK Gate — Duplicate Checksum (Z-08, D-08)

The file is an exact copy of a previously archived file.

1. Identify which prior file matches (the gate log will tell you)
2. This usually means the operator downloaded the same file twice, or the provider's export did not update
3. Check the provider's "last updated" indicator
4. If the provider did not update their data (e.g., holiday), record as a known gap — do NOT archive the duplicate
5. If this is a genuine new export that happens to be identical to the prior (very rare), file an override with explicit justification

### 10.5 ROLLBACK — Post-Append Duplicate Pairs (Z-09, D-09)

A (capture_date, symbol) duplicate was detected after append.

1. The script automatically rolls back both masters
2. Inspect the source file for duplicate symbol rows
3. Deduplicate the source file (keep the row with the higher confidence rank/score if they differ, or the first row if identical)
4. Re-run from Step 4

---

## 11. Missed Capture Protocol

If a scheduled capture session is skipped (holiday, system outage, operator unavailability):

1. Record the missed capture in the capture log: `runs/capture_reports/missed_captures.md`
2. Include: date, reason, provider(s) affected
3. Do NOT attempt to backfill by downloading a late-dated export — a missing capture is preferable to a misdated one
4. Continue with the next scheduled capture on schedule

---

## 12. Capture Session Summary Checklist

At the end of each session, verify:

- [ ] Both source files present in `data/signals/zacks/` and `data/signals/danelfin/`
- [ ] All gates PASS (or WARN with documented justification)
- [ ] Master files updated with new rows
- [ ] Capture report written to `runs/capture_reports/`
- [ ] `latest_*.csv` aliases updated
- [ ] Changes committed to git
