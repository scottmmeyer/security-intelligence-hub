# Phase 23.6 — Capital Rotation Advisor
## Deliverable 4: Tax Integration Analysis

**Date:** 2026-06-04
**Status:** Design Phase

---

## 4.1 Existing Tax Infrastructure (Phase 23.0A)

Phase 23.0A delivered a Tax-Aware Action Framework that is already present in the system. The CRA does not rebuild this — it integrates with it.

**Existing capabilities:**

| Asset | Location | What it provides |
|-------|----------|-----------------|
| Tax state persistence | `data/operator/portfolio_alignment_state.json` | Per-portfolio tax position configuration |
| Tax action buckets (A–E) | `renderTaxActionTable()` in app.js | 5-bucket classification of holdings by tax situation |
| API | `GET/POST /api/operator/tax-state` | Reads/writes operator-configured tax state |
| `PortfolioHolding.cost_basis` | `src/portfolio/models.py:52` | Optional cost basis field |
| `PortfolioHolding.holding_days` | Inferred from tax state | Days held (for ST/LT classification) |

**What is NOT present:**
- No holding-level tax lot granularity
- No automatic gain/loss calculation (cost_basis is optional; not always populated)
- No wash-sale tracking
- No realized gain/loss budget for the account

---

## 4.2 How Tax Context Modifies Capital Source Priority

The CRA uses tax context as a **modifier to priority**, not a standalone driver. The underlying signal/conviction reason must exist first.

### Rule Set

```
Tax Modifier Rules (applied to CapitalSourceRecord after category assignment):

R1. Bucket A (loss harvest candidate):
    → priority UPGRADE: MODERATE → HIGH, LOW → MODERATE
    → annotation: "Tax loss harvest opportunity available"

R2. Bucket E (approaching LT threshold, < 30 days from 1-year mark):
    → priority DOWNGRADE to "DEFER" status
    → blocked from capital pool unless operator explicitly overrides
    → annotation: "Within 30 days of long-term threshold — defer unless thesis broken"

R3. Bucket D (significant long-term gain, > $5,000 estimated):
    → priority DOWNGRADE: HIGH → MODERATE
    → operator_review_required = True
    → annotation: "Significant LT gain — confirm tax strategy before executing"

R4. Bucket B or C:
    → no priority modification
    → annotation surfaced for transparency only

R5. No tax data (cost_basis = None):
    → no modification
    → annotation: "No cost basis data — tax impact unknown"
```

---

## 4.3 Tax-Aware Source Ordering

Within the same capital source category and priority tier, tax context governs ordering:

```
1. Bucket A (loss harvest) — prefer first
2. Bucket B (short-term gain) — neutral
3. Bucket C (long-term gain, small) — neutral
4. Bucket D (long-term gain, large) — deprioritize; operator review
5. Bucket E (approaching threshold) — defer unless URGENT signal
```

This ordering ensures the CRA surfaces loss harvest opportunities at the top of the sell stack whenever the underlying signal supports a sell.

---

## 4.4 Tax Transparency in the UI

Every capital source card in the CRA panel (see Deliverable 5) displays:

- Tax bucket badge (A / B / C / D / E / Unknown)
- Tax annotation text
- Cost basis and estimated gain/loss (if available)
- Operator review flag (if applicable)

The operator sees:

```
FIS
Category: Signal Deterioration (BEARISH)
Priority: HIGH
Est. Proceeds: $12,400
Tax Bucket: C — Long-term gain (~$2,100 estimated gain)
Cost Basis: $10,300 | Days Held: ~480
Tax Note: Long-term gain. No deferral concern; confirm gain fits tax strategy.
[Include in Rotation] [Skip]
```

---

## 4.5 What CRA Does Not Provide

The CRA is not a tax planning tool. It explicitly does not:

- Compute exact tax liability (requires tax lot detail and jurisdiction)
- Replace the operator's tax advisor or tax lot optimization workflow
- Track wash-sale windows across related securities
- Optimize lot selection (HIFO, FIFO, specific lot) — that remains operator responsibility
- Account for state tax or AMT considerations

**Design boundary:** The CRA surface says "tax context is X" — not "here is your optimized tax strategy."

---

## 4.6 Integration Points

```
Phase 23.0A Tax Infrastructure
        │
        ▼ reads
CapitalSourceRecord.tax_bucket   (from overlay / tax_state)
CapitalSourceRecord.tax_context  (annotation string)
        │
        ▼ informs
CapitalSourceRecord.priority     (modifier applied per rules above)
CapitalSourceRecord.blocked_from_pool  (bucket E logic)
        │
        ▼ displayed on
CRA Panel Source Card
RotationProposal.proposal_status  (OPERATOR_REVIEW_REQUIRED if bucket D present)
```

No new API endpoints are required. The existing `/api/operator/tax-state` endpoint provides the tax configuration that informs bucket assignment.
