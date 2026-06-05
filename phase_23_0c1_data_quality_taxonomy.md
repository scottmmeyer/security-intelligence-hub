# Phase 23.0C.1 — Data Quality Taxonomy

**PAR Run**: PAR-20260603-B66B00E3  
**Date**: 2026-06-03  
**Status**: COMPLETE

---

## 1. Purpose

The current reconciliation system treats all FAILs as equivalent — implying every FAIL carries the same urgency and the same risk to analytical integrity. This is incorrect. A miscalculated portfolio value and a missing narrative card label require fundamentally different responses.

This taxonomy provides a structured three-level framework for classifying data quality conditions, calibrated to their analytical impact.

---

## 2. Three-Level Framework

### LEVEL 1 — ANALYTICAL DEFECT

**Definition**: The condition directly corrupts financial calculations, allocation decisions, or recommendation outputs. Operator action is required before PAR outputs can be trusted.

**Characteristics**:
- Wrong numbers reach the UI
- Allocation percentages are incorrect
- Cash calculations are wrong
- Recommendations are based on bad underlying data
- Deployment plans cannot be trusted

**Reconciliation outcome**: FAIL — block output delivery if possible; alert operator.

**Examples**:

| Condition | Why LEVEL 1 |
|-----------|-------------|
| Cash total mismatch > 1% | Wrong deployable cash, wrong sizing |
| Allocation sum ≠ 100% by material amount | All allocation-dependent outputs wrong |
| Missing holding rows (incomplete ingestion) | Analysis on wrong universe |
| Conviction score corruption | CONCENTRATED_ALPHA mandate calculations invalid |
| Security type wrong on large position | Allocation bucketing, ESS, mandate rules all wrong |

---

### LEVEL 2 — DATA QUALITY WARNING

**Definition**: The condition reflects a metadata gap, classification inconsistency, or rule sensitivity — but does not corrupt financial calculations or allocation outputs. Operator can use PAR outputs but should be aware of the condition.

**Characteristics**:
- Numbers reaching the UI are correct
- Root cause is a missing label, incorrect tag, or rule scope issue
- No immediate portfolio action is blocked
- Condition warrants monitoring and eventual resolution

**Reconciliation outcome**: WARN — note in audit, continue output delivery.

**Examples**:

| Condition | Why LEVEL 2 |
|-----------|-------------|
| `mandate_drift_label` missing on narrative card recommendations | Label absent; allocation calculations unaffected |
| SPAXX in ETF decomposition registry (RC-06) | Cash calculation correct (RC-05 PASS); registry entry intentional |
| M26CNT069 misclassified as ETF (source says Cash) | Zero-value position; no allocation impact |
| `HEURISTIC_FALLBACK` decomposition at low confidence | Decomposition estimate less precise; position too small to matter |
| Unknown taxonomy nodes (RC-12) | Node unrecognized; no financial consequence |
| Near-zero rounding residue in allocation sum | ≤ 0.001% difference; audit annotation sufficient |

---

### LEVEL 3 — INFORMATIONAL

**Definition**: The condition is expected, benign, or requires no action. It is noted for completeness but imposes no obligation on the operator or system.

**Characteristics**:
- Condition is normal for the portfolio/broker type
- No analytical concern
- No financial impact
- No labeling correction needed
- Historical or structural artifact

**Reconciliation outcome**: PASS with annotation or INFO — no operator action.

**Examples**:

| Condition | Why LEVEL 3 |
|-----------|-------------|
| Zero-value fractional contra position (M26CNT069) | Expected Fidelity corporate action artifact; $0 economic impact |
| Multi-account SPAXX rows in source (correctly merged) | Normal Fidelity export behavior for multi-account portfolios |
| Dormant holding with no ESS coverage | Position may be out of coverage universe; no active signal needed |
| Pending corporate action instrument with unpriced status | Transient; will self-resolve on settlement |
| SPAXX held in 2 accounts | Normal cash sweep behavior |

---

## 3. Classification of Active Conditions (PAR-20260603-B66B00E3)

| Condition | Level | Rationale |
|-----------|-------|-----------|
| RC-06 FAIL: SPAXX in ETF registry | **LEVEL 2** | Rule false positive; cash correct per RC-05 PASS |
| RC-10 FAIL: mandate_drift_label missing (27 recs) | **LEVEL 2** | Missing field on non-allocation recommendation types; no calculation impact |
| M26CNT069 misclassified as ETF | **LEVEL 2** | Metadata error; zero-value position with no allocation impact |
| M26CNT069 zero-value existence | **LEVEL 3** | Expected Fidelity contra entry; transient by nature |
| SPAXX multi-account source rows | **LEVEL 3** | Normal multi-account export; correctly merged |
| RC-12 WARN: unknown taxonomy nodes | **LEVEL 2** | Taxonomy gap; no financial impact confirmed |

**No LEVEL 1 — ANALYTICAL DEFECT conditions identified in this PAR run.**

---

## 4. Reconciliation Outcome Map

| Taxonomy Level | Reconciliation Outcome | Operator Action |
|----------------|----------------------|-----------------|
| LEVEL 1 — Analytical Defect | FAIL | Review before using PAR outputs; correct source data |
| LEVEL 2 — Data Quality Warning | WARN | Note and monitor; PAR outputs usable |
| LEVEL 3 — Informational | PASS (annotated) or INFO | No action required |

---

## 5. Adoption Path

1. Update `reconciliation.json` schema to include `data_quality_level` on each check result
2. Update RC-06 and RC-10 rule scope as defined in the Reconciliation Rule Review
3. Introduce RC-ZV01 (zero-value governance check) at LEVEL 3/WARN level
4. Carry this taxonomy forward into all future PAR runs
