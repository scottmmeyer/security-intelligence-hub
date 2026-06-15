# Root Cause Verdict — PIS-LINEAGE-ATTR-REFRESH-07

**Investigation Date:** 2026-06-14  
**Scope:** Evaluate hypotheses and rank root causes

---

## Summary

**Root Cause:** Missing refresh trigger mechanism between canonical snapshot governance approval and lineage/attribution recomputation.

**Priority 1 - CONFIRMED CAUSE:** Canonical refresh not triggered after June 14 ingestion  
**Priority 2 - CONFIRMED DEPENDENCY:** Lineage depends on canonical advancement  
**Priority 3 - CONFIRMED CONSEQUENCE:** Attribution depends on lineage advancement

---

## Hypothesis Evaluation

### Hypothesis 1: Dashboard Bug — "No PARs after 2026-05-29"

**Claim:** Dashboard is incorrectly reporting June 14 PAR exists

**Evidence Test:**
- Dashboard source: [src/pis/storage.py:pis_sih_lineage_summary()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/storage.py#L298)
- Data source: [data/portfolio_ingestion/manifest.json](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/manifest.json)
- Manifest state: 236 PARs, latest PAR-20260614-3A8B91DB
- Directory verification: PAR-20260614-3A8B91DB exists with all required files
- PAR file verification: 34 recommendations, 32 deployment items, all valid JSON

**Verdict:** ✗ REJECTED - Dashboard is correct

**Reasoning:** Manifest is authoritative PAR source; it contains 236 PARs; June 14 PAR is real and verified.

---

### Hypothesis 2: Manifest Corrupted

**Claim:** Manifest has invalid or duplicate entries; can't be trusted as source

**Evidence Test:**
- Manifest structure: Valid JSON with 236 portfolio objects
- PAR-20260614-3A8B91DB entry:
  ```json
  {
    "run_id": "PAR-20260614-3A8B91DB",
    "snapshot_date": "2026-06-14",
    "created_at_utc": "2026-06-14T15:17:36.911282+00:00",
    "portfolio_snapshot_id": "PSNAP-20260614-A10360707326",
    "status": "COMPLETE",
    ...
  }
  ```
- Timestamp parsing: Valid ISO 8601 format
- Cross-reference: Snapshot PSNAP-20260614-A10360707326 exists in pis_snapshot_index.csv
- Cross-reference: Directory /data/portfolio_ingestion/analysis_runs/PAR-20260614-3A8B91DB/ exists
- Cross-reference: Inside PAR directory: recommendations.json (34 recs), deployment_queue.json (32 items), all valid

**Verdict:** ✗ REJECTED - Manifest is valid and consistent

**Reasoning:** All 236 entries are well-formed; June 14 entry is verified against physical files.

---

### Hypothesis 3: Lineage Extraction Broken After June 9

**Claim:** build_recommendation_candidates() stops working or filtering out June dates

**Evidence Test:**
- Function: [src/pis/recommendation_lineage.py:build_recommendation_candidates()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/recommendation_lineage.py#L272)
- Manual execution result:
  ```
  Total candidates: 18,872
  June 14 candidates: 230
  Breakdown: CRA=46, DEPLOYMENT_QUEUE=36, DIL=78, PAP=30, RECOMMENDATION_HISTORY=40
  ```
- Code path: Iterates `/data/portfolio_ingestion/analysis_runs/` for all directories
- No date filtering in extraction logic
- All 230 June 14 candidates returned in single list

**Verdict:** ✗ REJECTED - Candidate extraction works correctly

**Reasoning:** Function successfully extracts 230 candidates from June 14 PAR; no filtering at extraction stage.

---

### Hypothesis 4: Governance Failed to Evaluate June 14

**Claim:** June 14 snapshot was never evaluated; not approved as PASS

**Evidence Test:**
- Governance CSV: [data/history/pis/governance/snapshot_governance.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/governance/snapshot_governance.csv)
- June 14 record:
  ```
  PSNAP-20260614-A10360707326,2026-06-14,PASS,true,true,true
  ```
- Governance thresholds: value_pass_max=600,000, value_reject_gt=750,000
- June 14 portfolio_value: 473,874.84 (< 600,000)
- Account scope: Contains valid patterns (General Brokerage, Joint WROS - TOD, Individual - TOD)
- Source file: Portfolio_Positions_Jun-14-2026.csv (not test artifact)
- All checks: scope_valid=true, value_valid=true, source_valid=true

**Verdict:** ✗ REJECTED - Governance evaluation succeeded

**Reasoning:** June 14 snapshot was evaluated and approved with PASS status; all governance checks passed.

---

### Hypothesis 5: Canonical Selection Logic Broken

**Claim:** select_canonical_daily_rows() has a bug preventing June 14 inclusion

**Evidence Test:**
- Manual execution: [src/pis/canonical_daily.py:select_canonical_daily_rows()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/canonical_daily.py#L79)
- Result: 18 daily snapshots INCLUDING 2026-06-14
  ```python
  {
    'snapshot_date': '2026-06-14',
    'canonical_snapshot_id': 'PSNAP-20260614-A10360707326',
    'governance_status': 'PASS',
    'portfolio_value': 473874.84
  }
  ```
- Code path verified:
  - PASS_THEN_LATEST_INGESTION policy implemented correctly
  - No hard-coded date cutoffs
  - No conditional filtering for June dates
  - June 14 is PASS → included in pass_candidates
  - Latest by creation_at_utc → selected correctly

**Verdict:** ✗ REJECTED - Canonical selection logic works correctly

**Reasoning:** When executed, function returns 18 daily snapshots including June 14; logic is sound.

---

### Hypothesis 6: Canonical CSV Not Refreshed After June 14 Ingestion

**Claim:** select_canonical_daily_rows() was never executed after June 14 snapshot was approved

**Evidence Test:**
- Current canonical_daily_snapshots.csv: Last modified 2026-06-14 10:21
- June 14 snapshot ingestion time: 2026-06-14 15:10:36
- June 14 governance approval: After ingestion (based on governance CSV having entry)
- Timeline: CSV modified BEFORE ingestion, governance approval AFTER ingestion, no refresh after approval
- Call sites of select_canonical_daily_rows(): [src/pis/canonical_daily.py](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/canonical_daily.py) exports function but no automatic caller identified
- Trigger mechanisms: Attribution recompute checks if lineage files exist, but doesn't trigger canonical refresh first

**Verdict:** ✓ CONFIRMED - Canonical not refreshed after June 14 ingestion

**Reasoning:** 
1. select_canonical_daily_rows() works correctly when executed
2. But it's never called after June 14 ingestion
3. Therefore canonical_daily_snapshots.csv never gets updated with June 14
4. This is the blocking issue

---

### Hypothesis 7: Canonical Refresh Intentionally Stopped at June 11

**Claim:** Code or operator intentionally froze canonical at June 11 for operational reasons

**Evidence Test:**
- Code review: No hard-coded date constraint
- No conditional `if date > 2026-06-11: skip`
- No administrative lock or pause flag
- No comments indicating intentional freeze
- Governance file shows June 14 as PASS (not REJECT/WARNING)
- No deployment notes or runbooks indicating pause

**Verdict:** ✗ REJECTED - No evidence of intentional freeze

**Reasoning:** No code, data, or documentation suggests this was intentional.

---

### Hypothesis 8: Lineage Matching Filters Out June 14 by Design

**Claim:** Even if canonical were refreshed, matching logic wouldn't accept June 14 recommendations

**Evidence Test:**
- Matching rules: [src/pis/recommendation_lineage.py:_match_confidence()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/recommendation_lineage.py#L325)
- Matching criteria:
  - `days_between`: Must be ≤ 90 days (June 14 recs to June 14 changes would be 0 days) ✓
  - `symbol_match`: Symbol must be in portfolio (June 14 portfolio has 81 positions) ✓
  - `direction_match`: Direction must match (BUY/REDUCE in portfolio) ✓
  - `confidence`: Must be HIGH/MEDIUM/LOW (all June 14 candidates have confidence level) ✓
- No date-based filtering that would reject June 14

**Verdict:** ✗ REJECTED - No matching filter would exclude June 14

**Reasoning:** Matching logic accepts recommendations within 90 days; June 14 recs to June 14 changes would match perfectly (0 days).

---

### Hypothesis 9: Attribution Refresh Already Triggered Automatically

**Claim:** Refresh trigger exists but just hasn't fired yet; will eventually catch up

**Evidence Test:**
- Current time: 2026-06-14T15:30+ (30+ minutes after June 14 ingestion)
- Artifact freshness: All computed artifacts still frozen at 2026-06-11
- No indication of background refresh in progress
- Code review: No timer-based triggers, no event listeners, no async workers
- Refresh logic: Only fires if someone manually deletes lineage files or calls API with override
- Manifest modified but attributes not: Suggests no automatic recomputation

**Verdict:** ✗ REJECTED - No automatic trigger exists to catch up

**Reasoning:** 30+ minutes have passed; if automatic trigger existed, it would have fired by now. It hasn't.

---

### Hypothesis 10: Missing Automatic Refresh Trigger (ROOT CAUSE)

**Claim:** Architecture lacks a trigger mechanism connecting canonical approval → lineage → attribution recomputation

**Evidence Test:**
- Trigger requirement: When new canonical snapshot is approved (PASS), lineage should recompute
- Current implementation: Attribution only recomputes on file deletion or manual override
- Missing piece: No `canonical_refreshed()` or `governance_approved()` event handler
- Missing piece: No scheduler calling canonical refresh after ingestion
- Missing piece: No API endpoint to trigger the chain
- Chain works when manually initiated: Yes (verified by manual canonical selection)
- Chain doesn't work automatically: Yes (canonical not updated in 30+ minutes)

**Verdict:** ✓ CONFIRMED - Root cause is missing trigger

**Reasoning:** All pieces work individually, but orchestration is missing. The refresh chain (canonical → change → lineage → attribution) has no trigger connecting governance approval to recomputation initiation.

---

## Priority-Ordered Root Causes

### Priority 1: CONFIRMED
**Missing Automatic Refresh Trigger**

- No mechanism exists to invoke `select_canonical_daily_rows()` after governance approval
- No mechanism exists to trigger `compute_performance_attribution()` after canonical refresh
- Result: June 14 snapshot is approved but never integrated into computed artifacts

**Impact:** HIGH - Blocks all downstream systems (lineage, attribution, benchmark)

**Fix Complexity:** MEDIUM - Requires adding trigger call, not fixing broken logic

---

### Priority 2: CONFIRMED (Dependency)
**Canonical CSV Not Persisted After Selection**

- select_canonical_daily_rows() returns correct data but return value is never written to CSV
- Without automatic call, CSV never gets updated
- CSV remains frozen at last manual write or initialization

**Impact:** HIGH - But only blocks because trigger doesn't call it

**Fix Complexity:** LOW - CSV write logic exists; just needs to be called by trigger

---

### Priority 3: CONFIRMED (Dependency)
**Attribution Trigger Logic Only Checks File Existence**

- compute_performance_attribution() only triggers if lineage files missing
- Doesn't check: "Is lineage data older than manifest?"
- Doesn't check: "Is canonical data updated since last run?"
- Doesn't check: "Is there new data available?"

**Impact:** MEDIUM - Means manual file deletion required to force refresh

**Fix Complexity:** MEDIUM - Requires adding freshness checks

---

## What Is NOT a Root Cause

- ✗ Dashboard code (it's correct and reporting from manifest)
- ✗ Manifest state (it's valid with 236 PARs)
- ✗ Candidate extraction (it successfully finds 230 June 14 candidates)
- ✗ Governance evaluation (June 14 correctly marked as PASS)
- ✗ Canonical selection logic (it works and returns June 14 when run)
- ✗ Lineage matching logic (would accept June 14 if canonical were available)
- ✗ Attribution scoring logic (would compute June 14 if lineage data existed)

---

## Unified Root Cause Statement

**ROOT CAUSE:** The PIS refresh architecture lacks an orchestration trigger connecting governance approval of new canonical snapshots to automatic recomputation of downstream artifacts (change detection, lineage, attribution, benchmark).

**Technical Details:**
1. When new snapshot is ingested (e.g., June 14), governance evaluation runs and marks it PASS
2. Canonical selection logic CAN include it in canonical_daily_snapshots.csv
3. But nothing calls canonical refresh after governance approval
4. Therefore canonical CSV is never updated with June 14
5. Therefore change detection has no new canonical pairs to process
6. Therefore lineage has no new changes to match
7. Therefore attribution has no new lineage data
8. Entire downstream pipeline is blocked at canonical layer

**Proof of Mechanism:** Manual execution of select_canonical_daily_rows() shows that June 14 WOULD be included if the function were called. The issue is NOT in the logic; it's in the orchestration.

---

## Conclusion

**Primary Root Cause: Missing Refresh Trigger**

No automatic mechanism connects governance approval → canonical refresh → lineage recomputation.

**Severity:** HIGH (Blocks all computed insights)  
**Fix Complexity:** MEDIUM (Add orchestration trigger)  
**Data Integrity:** NOT compromised (all data exists, just not processed)

All forensic hypotheses point to the same conclusion: The system is not broken; it's incomplete. The refresh trigger was never implemented.
