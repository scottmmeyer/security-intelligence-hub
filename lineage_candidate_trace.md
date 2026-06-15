# Lineage Candidate Trace — PIS-LINEAGE-ATTR-REFRESH-02

**Investigation Date:** 2026-06-14  
**Scope:** Trace lineage candidate generation path and June PAR visibility

---

## Summary

June PARs ARE visible to lineage. The candidate builder extracts 230 candidates from June 14 alone. **The candidates exist; they are not being filtered.**

---

## Q4: Are June PARs visible to lineage?

**Answer:** YES - 100% visible

**Evidence:**

Candidates extracted by `build_recommendation_candidates()`:

```
Latest candidate date: 2026-06-14 (230 candidates)
2026-06-12: 615 candidates
2026-06-11: 348 candidates
2026-06-10: 591 candidates
2026-06-09: 840 candidates
2026-06-08: 471 candidates
...total: 18,872 candidates
```

**Source:** [src/pis/recommendation_lineage.py:build_recommendation_candidates()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/recommendation_lineage.py#L272)

---

## Q5: Are they being filtered?

**Answer:** NO filtering at extraction stage

**Code Path:**

1. `build_recommendation_candidates()` iterates `/data/portfolio_ingestion/analysis_runs/` directories
2. For each PAR directory (including PAR-20260614-*), it calls:
   - `_extract_recommendation_candidates(run_dir, run_date)` 
   - `_extract_deployment_candidates(run_dir, run_id)`
   - `_extract_dil_candidates(run_dir, run_id)`
3. All extracted candidates are returned in a single list
4. No date-based filtering occurs

**Verification:**

June 14 candidates generated: **230**

```
CRA: 46
DEPLOYMENT_QUEUE: 36
DIL: 78
PAP: 30
RECOMMENDATION_HISTORY: 40
```

All 230 are included in the returned candidate list.

---

## Q6: If filtered, why?

**Answer:** Not filtered during extraction, but filtering MAY occur at matching stage.

See lineage matching confidence logic in [src/pis/recommendation_lineage.py:_match_confidence()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/recommendation_lineage.py#L325)

The matching logic filters by:
- `days_between` (difference between recommendation date and snapshot date)
- `symbol_match` (symbol present in portfolio)
- `direction_match` (BUY/REDUCE direction matches)
- `confidence` threshold (HIGH/MEDIUM/LOW)

**However:** For June 14 candidates to be filtered by `days_between`, there must be a snapshot date to compare against. 

**Critical dependency:** Candidates can only be matched if there is a canonical snapshot date to match them to.

---

## Candidate Extraction Details

### PAR-20260614-3A8B91DB Recommendations

**File:** [data/portfolio_ingestion/analysis_runs/PAR-20260614-3A8B91DB/recommendations.json](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/analysis_runs/PAR-20260614-3A8B91DB/recommendations.json)

**Structure:**
```json
{
  "recommendation_id": "REC-XXXXX",
  "created_at_utc": "2026-06-14T10:15:00+00:00",
  "recommendation_type": "INCREASE_UNDERWEIGHT",
  "effective_action": "BUY",
  "title": "...",
  "symbol": "SYMBOL",
  "drilldown": {
    "holdings": [...theme symbols...]
  }
}
```

**Sample Candidates from 2026-06-14:**

```
Candidate 1:
  recommendation_id: CRA-PAR-20260614-0001
  recommendation_date: 2026-06-14
  source: CRA
  symbol: MU
  direction: BUY

Candidate 2:
  recommendation_id: DEPLOYMENT_QUEUE-PAR-20260614-0032
  recommendation_date: 2026-06-14
  source: DEPLOYMENT_QUEUE
  symbol: VRT
  direction: REDUCE

... 228 more candidates from June 14
```

---

## Complete Candidate Timeline

| Date | Candidates | CRA | DEP_QUEUE | DIL | PAP | OTHER |
|------|-----------|-----|-----------|-----|-----|-------|
| 2026-06-14 | 230 | 46 | 36 | 78 | 30 | 40 |
| 2026-06-12 | 615 | 100 | 115 | 225 | 75 | 100 |
| 2026-06-11 | 348 | 54 | 69 | 120 | 45 | 60 |
| 2026-06-10 | 591 | 102 | 114 | 200 | 75 | 100 |
| 2026-06-09 | 840 | 145 | 160 | 290 | 105 | 140 |
| ... | ... | ... | ... | ... | ... | ... |
| **TOTAL** | **18,872** | **3,456** | **4,201** | **6,485** | **2,108** | **2,622** |

---

## Key Finding

**The lineage candidate builder is working correctly and has extracted all PAR recommendations, including June 14.**

The candidates have been extracted and are available for matching.

**Why then does lineage only extend to June 11?**

Answer: See next report (lineage_refresh_trigger_audit.md). The issue is NOT candidate extraction; it's **matching dependency on canonical snapshots**.

---

## Conclusion

Q4: YES - June PARs are visible to lineage (candidates extracted)  
Q5: NO - No filtering occurs at extraction stage  
Q6: N/A - No filtering at this stage (filtering occurs at matching, which depends on canonical snapshots having June 12-14 dates)

The forensic audit's conclusion that "lineage candidates don't exist after 2026-05-29" is **INCORRECT**. Candidates exist for all dates through 2026-06-14. The blocker is elsewhere.
