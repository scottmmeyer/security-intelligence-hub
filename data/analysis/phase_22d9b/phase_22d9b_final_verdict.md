# Phase 22D.9B — Final Verdict: ACCOUNTING_ADJUSTMENT Taxonomy Audit

**Phase:** 22D.9B — ACCOUNTING_ADJUSTMENT Taxonomy Audit  
**Date:** 2026-06-02  
**Audit scope:** All 173 analysis runs in `data/portfolio_ingestion/analysis_runs/`,
6 raw Fidelity CSV archive files, test fixtures, and codebase classification logic  
**Mandate:** CONCENTRATED_ALPHA  

---

## Purpose

Phase 22D.9A identified a material recommendation engine defect: CW-DAS sizes
suggestions using reported deployable cash ($7,658.25) instead of
settlement-adjusted deployable cash ($4,091.70). The proposed remediation was
Option C — using `adjusted_deployable_mv` as the CW-DAS budget.

Phase 22D.9A assumed that negative ACCOUNTING_ADJUSTMENT rows represent cash
that should reduce deployable capital. Phase 22D.9B was launched to validate
that assumption before approving Option C implementation.

---

## Q1: Inventory Scope

**Result: 42 ACCOUNTING_ADJUSTMENT rows across 9 unique portfolio snapshots**

- Total analysis runs searched: 173
- Runs with at least one ACCOUNTING_ADJUSTMENT row: 42 (all from 9 underlying snapshots)
- Corpus date range: 2026-05-28 to 2026-06-02
- Symbol uniformity: 100% "PENDING ACTIVITY"
- Description uniformity: 100% blank ("")
- Account: all from account "General Brokerage, Joint WROS - TOD, Individual - TOD"

Additional context: Pre-schema runs from May 22, 2026 (23-column holdings.csv
format, no `operational_state` column) also contained "PENDING ACTIVITY" rows.
These are NOT included in the 42-row count. The symmetric offset pattern in those
runs is consistent with Class C transfer artifacts.

**Finding:** The inventory is complete and the corpus is well-defined.

---

## Q2: Classification Results

**Result: 36/42 rows (85.7%) are pending purchase settlements; 6/42 (14.3%) are net-zero transfer artifacts**

| Class | Label | Count | % | Net MV |
|-------|-------|-------|---|--------|
| A | PENDING_PURCHASE | 36 | 85.7% | -$60,199.65 |
| C | CASH_TRANSFER (net zero) | 6 | 14.3% | $0.00 |
| All others (B, D, E, F, G) | Not observed | 0 | 0% | $0.00 |
| **TOTAL** | | **42** | **100%** | **-$60,199.65** |

Class A evidence: All 36 negative rows derive from single-account "Pending
activity" entries in Z35123695 (Individual TOD) with no positive counterpart.
Values (-$1,500.00 and -$3,566.55) represent unsettled equity purchases.

Class C evidence: 6 zero-MV rows arise from `normalize_and_aggregate_holdings()`
summing symmetric +/- "Pending activity" pairs across two sub-accounts (General
Brokerage negative, Individual TOD positive). The `_classify_operational_state()`
function assigns ACCOUNTING_ADJUSTMENT to the first occurrence (negative); the
aggregation sums them to zero.

**Finding: Assumption validated. Negative ACCOUNTING_ADJUSTMENT rows represent
committed, uncommittable cash. They are correctly excluded from deployable capital.**

---

## Q3: Positive Adjustment Assessment

**Result: ZERO positive ACCOUNTING_ADJUSTMENT rows in processed holdings.csv. Ever.**

Positive "Pending activity" entries DO appear in raw Fidelity CSVs, but only as
symmetric counterparts to negative entries. After `normalize_and_aggregate_holdings()`
aggregates by symbol, they net to zero. The classification logic in
`_classify_operational_state()` structurally prevents positive-MV rows from
receiving the ACCOUNTING_ADJUSTMENT state (positive MV → ACTIVE_POSITION).

**Finding: No positive ACCOUNTING_ADJUSTMENT risk in current data or classification logic.**

---

## Q4: Cash Offset Safety Assessment

**Result: Subtracting negative ACCOUNTING_ADJUSTMENT market values from deployable cash is CORRECT for 100% of observed rows**

| Class | mv Polarity | Safe to offset? | Why |
|-------|-------------|-----------------|-----|
| A (36 rows) | NEGATIVE | YES | Cash committed for unsettled purchase; SPAXX balance not yet decremented |
| C (6 rows) | ZERO | NEUTRAL | Offset = $0; harmless regardless |
| B — pending sale (0 rows) | Positive (not ACCOUNTING_ADJUSTMENT) | N/A | Structural impossibility |
| E — corporate action (0 rows) | Unknown | AMBIGUOUS | Not observed; conservative default = do not offset |

**Finding: The offset assumption is empirically validated. Zero incorrect offsets
occurred across 42 rows and 9 portfolio snapshots.**

---

## Q5: Taxonomy Evolution

**Result: The single ACCOUNTING_ADJUSTMENT state is insufficiently granular for production governance. A safe_to_offset_cash attribute should be introduced.**

Current classification treats all negative-MV rows identically, regardless of
whether they represent purchase settlements, transfers, corporate actions, or
bookkeeping artifacts. For current data, this produces correct results. For future
data, it creates unchecked risk.

**Recommended evolution:** Add `safe_to_offset_cash: bool = False` to PortfolioHolding.
Set `True` for ACCOUNTING_ADJUSTMENT rows with `market_value < 0`. Default `False`
protects against new/unclassified patterns.

**Finding: safe_to_offset_cash should be a co-deliverable with Option C in Phase 22D.10.**

---

## Q6: Offset Governance Analysis

**Result: safe_to_offset_cash is the correct governance structure; operational_state alone is acceptable for current data but insufficient for production**

| Governance Approach | Correct for observed data? | Protected against theoretical Classes C'/E/F? |
|--------------------|---------------------------|----------------------------------------------|
| operational_state + mv < 0 (Option A) | YES | NO |
| safe_to_offset_cash attribute (Option B) | YES | YES |

The `safe_to_offset_cash` attribute breaks the implicit coupling between a
classification state (ACCOUNTING_ADJUSTMENT) and a financial decision (reduce
deployable cash). It makes the governance decision explicit, auditable, and
default-conservative.

**Finding: Option B (safe_to_offset_cash) is the correct governance structure.
Implement in Phase 22D.10 alongside Option C.**

---

## Q7: Option C Revalidation

**Result: Option C is CONFIRMED. The remediation assumption is validated. No false positives or false negatives observed.**

| Risk | Observed rate | Assessment |
|------|---------------|------------|
| False positive (incorrectly reduces deployable cash) | 0 / 42 (0%) | None in corpus |
| False negative (fails to reduce when should) | 0 / 36 Class A rows (0%) | None in corpus |
| Mandate compliance benefit | 6.26% → 7.00% post-settlement | Exact; deterministic |
| Implementation complexity | ~20 lines in runner.py | Low |
| Test impact | ~5 assertions across 2–3 test files | Manageable |

**Finding: Option C is correct, safe, and empirically validated. Phase 22D.10
should proceed.**

---

## Final Classification: REMEDIATION VALIDATED WITH GOVERNANCE CONDITIONS

### Verdict: APPROVED FOR IMPLEMENTATION — with conditions

Phase 22D.9B has validated every critical assumption underlying the Phase 22D.9A
Option C recommendation:

**VALIDATED:**
- ✓ Negative ACCOUNTING_ADJUSTMENT rows represent pending purchase settlements
- ✓ Subtracting these from deployable cash is economically correct
- ✓ No positive ACCOUNTING_ADJUSTMENT rows have been produced (structural protection)
- ✓ No false positives in 42-row corpus
- ✓ No false negatives in 36-row Class A corpus
- ✓ Mandate breach is exactly remediable (6.26% → 7.00% on reference run)

**CONDITIONS FOR IMPLEMENTATION:**
- ☐ `safe_to_offset_cash` governance attribute implemented alongside Option C
  (not prerequisite, but co-deliverable in Phase 22D.10)
- ☐ Test assertions updated for runs containing ACCOUNTING_ADJUSTMENT rows
- ☐ `settlement_adjustment` and `adjusted_deployable_mv` added to audit lineage
  (snapshot.json and deployment_queue.json)
- ☐ This verdict document reviewed and accepted by operator before Phase 22D.10 begins

---

## Escalation Path

**Phase 22D.10: Option C Implementation**

Scope:
1. Add `safe_to_offset_cash: bool = False` to PortfolioHolding
2. Set `safe_to_offset_cash = True` for ACCOUNTING_ADJUSTMENT rows with mv < 0
3. Compute `settlement_adjustment` and `adjusted_deployable_mv` in runner.py
4. Route CW-DAS planner to use `adjusted_deployable_mv` as deployment budget
5. Persist `settlement_adjustment` and `adjusted_deployable_mv` to output artifacts
6. Update test assertions for pending-settlement scenarios

**Success criteria for Phase 22D.10:**
- Reference run PAR-20260602-8CF1CB84 with Option C active: all 31 suggested_add
  values resized; post-deployment cash% = 7.00% (not 6.26%)
- All runs without ACCOUNTING_ADJUSTMENT rows: identical behavior to pre-Phase-22D.10
- CI passes

---

*Phase 22D.9B audit complete. All 8 deliverables written.*  
*Audit conducted without any code changes or implementation actions, per mandate.*
