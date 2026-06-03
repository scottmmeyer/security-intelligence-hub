# Phase 22D.8A — Final Verdict: Deployable Cash vs. Pending Activity

**Phase:** 22D.8A — Deployable Cash vs. Pending Activity Forensic Audit  
**Run Audited:** PAR-20260602-8CF1CB84  
**Date:** 2026-06-02

---

## Q1: Cash Calculation Path Trace

### Holdings included in `cash_mv`:
- **SPAXX** (`is_cash_equivalent=True`) — $41,279.15
  - Brokerage account sub-total: $69.51
  - Individual account sub-total: $41,209.64

### Holdings excluded from `cash_mv`:
- **PENDING ACTIVITY** (`operational_state=ACCOUNTING_ADJUSTMENT`, `is_cash_equivalent=False`) — -$3,566.55
  - Excluded by `investable` filter at `runner.py:559`: `_INVESTABLE_STATES = {"ACTIVE_POSITION", "CASH_EQUIVALENT"}`
  - `ACCOUNTING_ADJUSTMENT` is not in `_INVESTABLE_STATES`
  - Therefore never reaches `compute_deployable_cash()`

### Treatment of PENDING ACTIVITY:
- Classified as `ACCOUNTING_ADJUSTMENT` (not `PENDING_SETTLEMENT`) because the row's parsed `symbol` and `description` are both blank; classification falls through to the `mv < 0` check
- `is_cash_equivalent=False` — correct; PENDING ACTIVITY is not a cash position
- Excluded from `investable` list — excluded from all downstream analytics
- **But:** its -$3,566.55 is included in `snapshot.total_market_value` (ingestion computes total_mv as unconditioned sum of all raw rows)

---

## Q2: Cash MV Computation

| Metric | Value | Derivation |
|--------|-------|-----------|
| `reported_cash_mv` | **$41,279.15** | `sum(SPAXX)` — pre-settlement balance |
| `pending_activity_mv` | -$3,566.55 | ACCOUNTING_ADJUSTMENT row, excluded from cash_mv |
| `adjusted_cash_mv` | **$37,712.60** | `$41,279.15 + (-$3,566.55)` — post-settlement estimate |

---

## Q3: Deployable Cash Computation

All using `effective_floor_pct = 7.0%`, `total_market_value = $480,298.55`.

| Metric | Reported | Adjusted |
|--------|----------|----------|
| `cash_mv` | $41,279.15 | $37,712.60 |
| `floor_mv` (7% × $480,298.55) | $33,620.90 | $33,620.90 |
| `deployable_mv` | **$7,658.25** | **$4,091.70** |
| Overstatement | — | **$3,566.55** |

The overstatement is exactly equal to the absolute value of PENDING ACTIVITY.

---

## Q4: System Treatment of Pending Activity

**A. IGNORES pending activity**

The system does not subtract PENDING ACTIVITY from `cash_mv`. The exclusion occurs at
two layers:
1. `operational_state=ACCOUNTING_ADJUSTMENT` → excluded from `investable` list
2. `is_cash_equivalent=False` → even if it reached `compute_deployable_cash()`, it would be excluded by the inner filter

PENDING ACTIVITY's -$3,566.55 does reduce `total_market_value` (the denominator), which slightly
raises the floor. But it does not reduce `cash_mv` (the numerator). The net effect is an
overstatement of `deployable_mv` by $3,566.55.

---

## Q5: Fidelity Settlement Artifact Assessment

**This is a known Fidelity export settlement artifact. It is transient.**

Fidelity's T+1 settlement export pattern:
- Purchased shares appear immediately at current market value
- SPAXX balance is NOT reduced on execution day
- PENDING ACTIVITY row = negative value equal to the purchase cost
- Pattern self-corrects after settlement (T+1): PENDING disappears, SPAXX is reduced

**Duration:** 1–2 business days from purchase execution
**Frequency:** Every time the operator ingests a Fidelity export on the same day as an equity purchase
**Mechanism:** Broker export lag, not a system bug

**The system is not malfunctioning.** It correctly processes the Fidelity data it receives.
The issue is that the Fidelity data itself is in a transitional state during the settlement window.

---

## Q6: Recommendation (Evidence Only — No Implementation)

Three response options with no code changes specified:

---

### Option A: No Action

**Rationale:**  
The overstatement is transient (1–2 days). The operator recently purchased PRG,
the position is already held, and the SPAXX balance will correct automatically after
settlement. An experienced operator reviewing the holdings would see PENDING ACTIVITY
alongside the new PRG position and understand the cash balance will settle.

**Risk:** Operator could deploy the full $7,658 today, leaving the portfolio below the 7%
mandate floor after T+1 settlement. This is a governance exposure.

**Appropriate if:** The operator consistently waits for T+1 settlement before deploying
additional capital, and the overstatement window is understood as a limitation.

---

### Option B: Warning Banner (Recommended)

**Rationale:**  
Surface a UI warning when any `ACCOUNTING_ADJUSTMENT` or `PENDING_SETTLEMENT` holding
with negative market value is present. Display the adjusted deployable cash alongside
the reported figure.

Proposed banner text:
> **Settlement Notice:** Pending activity totaling $3,567 is earmarked for settlement.
> Adjusted deployable cash may be $4,092 (vs. $7,658 shown). Confirm available cash
> before deploying additional capital.

**Risk:** None. Adds transparency without changing any calculation.

**Appropriate for:** All operator risk tolerances. Does not require code changes to
the cash calculation itself — only to the UI rendering layer.

---

### Option C: Adjust Deployable Cash

**Rationale:**  
Compute `adjusted_cash_mv = cash_mv + sum(ACCOUNTING_ADJUSTMENT rows with negative mv)`
and use this as the basis for `deployable_mv`.

This would change:
- `cash_mv`: $41,279.15 → $37,712.60
- `deployable_mv`: $7,658.25 → $4,091.70
- `cash_pct`: 8.59% → 7.85%

**Risk:** Could overcorrect if `ACCOUNTING_ADJUSTMENT` rows contain items other than
settlement debits. Would require validating the accounting adjustment classification
to ensure only settlement-related rows are subtracted.

**Appropriate for:** Mandates where strict cash governance is enforced and the operator
routinely purchases equities on the same day as running analysis.

---

## Overall Verdict

| Finding | Value |
|---------|-------|
| Overstatement present? | **YES — $3,566.55** |
| Root cause | Fidelity T+1 settlement export pattern: SPAXX not yet reduced |
| System defect? | **NO — system correctly processes the data it receives** |
| Duration | Transient (T+1 settlement, self-corrects Jun 3, 2026) |
| Current `deployable_mv` | $7,658.25 (overstated) |
| Pending-adjusted `deployable_mv` | $4,091.70 |
| Operator risk | Deploying full $7,658 may breach 7% mandate floor post-settlement |
| Recommended action | Option B: warning banner — no code changes required |

**Phase 22D.8A Classification: EVIDENCE COMPLETE**  
No implementation. No fixes. Forensic audit only.
