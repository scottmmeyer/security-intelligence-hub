# Phase 23.0A.1 — Final Verdict

**Phase:** 23.0A.1 — Tax-Aware Actions Validation & Architecture Hardening  
**Scope:** Validation audit of Phase 23.0A implementation. No new features.  
**Classification:** ACCEPTED WITH ADVISORIES

---

## Executive Summary

Phase 23.0A delivered a tax-aware decision support layer on top of the Portfolio Alignment workflow. The implementation was validated across six dimensions: calculation accuracy, bucket logic, cost basis dependency, optional-context architecture, persistence design, and future data acquisition options.

**One functional defect was found and corrected** (display precision in `_formatTaxDollar`). All core logic is correct. Eleven advisories are documented for future consideration — none are blocking.

---

## Validation Findings by Question

### Q1 — Tax Capacity Calculation

**Result: PASS (1 defect corrected)**

- `available = max(0, -net_realized_ytd + carryforward)` is algebraically correct.
- `projected = available + potential_additional_losses` is correct.
- Verification case: `available = 24,730` ✓, `projected = 38,966` ✓
- Sign convention on `net_realized_ytd` is correct (negative = loss booked, increases capacity).
- Floor at 0 prevents negative display when net gains exceed carryforward.

**Defect corrected:** `_formatTaxDollar()` used K-notation for values ≥ $1,000, causing `$24,730` to display as `$24.7K`. Threshold raised to $100,000 in Phase 23.0A.1. Values below $100K now display with full comma notation (`$24,730`, `$38,966`).

→ Reference: [phase_23_0a1_tax_capacity_validation.md](phase_23_0a1_tax_capacity_validation.md)

---

### Q2 — Action Bucket Validation

**Result: PASS (3 advisories)**

All 5 buckets (A–E) were traced through the `_computeTaxActions()` branch logic and verified against a 9-row test matrix. No incorrect assignments found.

**Advisories:**
1. When `holding_days` is absent, Bucket B (WAIT) is unavailable — poor-outlook gain holdings default conservatively to Bucket A (SELL NOW). This is a safe default but may trigger unnecessary urgency for short-term gains.
2. `flag === "TRIM"` in `isReduceCandidate` is unreachable code (TRIM holdings are always caught by earlier `isPoorOutlook` branches). No incorrect outcomes result.
3. Bucket B rows do not display "days to long-term" — operators must calculate this manually.

→ Reference: [phase_23_0a1_bucket_validation.md](phase_23_0a1_bucket_validation.md)

---

### Q3 — Cost Basis Dependency Audit

**Result: PASS (2 advisories)**

SIH is fully operational as a portfolio intelligence platform without cost basis data. Tax features degrade gracefully:
- **Tier 1 (always available):** Signal-based bucket assignment, Bucket A/C fallbacks, all labels and priority ordering.
- **Tier 2 (partial):** Tax impact, tax category, holding period display as `—` / `N/A`.
- **Tier 3 (unavailable):** Bucket D (harvest loss), Bucket B (wait for LT), precise gain-shielding calculation.

**Advisories:**
1. Bucket C timing label defaults to `HARVEST_LOSS` when cost basis is absent — mildly misleading when it's unknown whether a loss exists.
2. No explicit panel-level notice when cost basis is absent — only a passive footer note.

→ Reference: [phase_23_0a1_cost_basis_dependency_audit.md](phase_23_0a1_cost_basis_dependency_audit.md)

---

### Q4 — Optional Context Governance

**Result: PASS (1 advisory)**

The optional-context architecture is fully preserved. Tax state has zero server-side dependency in the analysis pipeline. Client-side `loadTaxState()` failure is completely silent. Empty tax inputs default to zero without altering bucket logic. The tax action section auto-hides when no actions qualify.

**Advisory:**
1. No upper-bound guard on tax input fields — very large values are accepted and displayed without validation or warning.

→ Reference: [phase_23_0a1_context_governance.md](phase_23_0a1_context_governance.md)

---

### Q5 — Persistence Review

**Result: PASS (4 advisories)**

Persistence architecture is correct. State survives page refresh, server restart, and browser restart. Directory auto-creation works. Merge semantics (not replace) preserve forward compatibility. Field whitelist enforced on POST.

**Advisories:**
1. No Reset / Clear button — operator must manually blank and re-save.
2. `_updated` timestamp is not displayed in the UI.
3. No server-side numeric type validation on incoming field values.
4. No year-to-year state rollover handling.

→ Reference: [phase_23_0a1_persistence_review.md](phase_23_0a1_persistence_review.md)

---

### Q6 — Future Data Acquisition

**Result: DOCUMENTED (research only)**

Four acquisition options ranked by complexity and reliability:

| Tier | Option | Priority |
|---|---|---|
| Current | Manual operator entry | Deployed |
| Near-term | Generic CSV import | HIGH |
| Near-term | Brokerage gain/loss CSV (e.g., Schwab format) | MEDIUM-HIGH |
| Mid-term | Tax software carryforward import | MEDIUM |
| Long-term | Brokerage API (OAuth2) | LOW |

The natural next step is a brokerage gain/loss CSV import (`POST /api/operator/tax-state/import`) — consistent with the existing portfolio CSV workflow and low implementation cost.

→ Reference: [phase_23_0a1_tax_data_acquisition_options.md](phase_23_0a1_tax_data_acquisition_options.md)

---

## Complete Advisory Register

| # | Category | Advisory | Blocking? | File |
|---|---|---|---|---|
| Q1-A1 | Display | K-notation precision defect in `_formatTaxDollar` | **CORRECTED** | Q1 |
| Q2-A1 | Logic | Bucket B unavailable when `holding_days` absent — conservative Bucket A fallback | No | Q2 |
| Q2-A2 | Code | `isReduceCandidate` TRIM branch unreachable (dead code, no error) | No | Q2 |
| Q2-A3 | UX | Bucket B rows lack "days to long-term" derived field | No | Q2 |
| Q3-A1 | UX | Bucket C timing label "HARVEST_LOSS" when cost basis absent | No | Q3 |
| Q3-A2 | UX | No explicit missing-cost-basis notice in Tax Panel | No | Q3 |
| Q4-A1 | Validation | No upper-bound guard on tax input fields | No | Q4 |
| Q5-A1 | UX | No Reset / Clear button in Tax Context Panel | No | Q5 |
| Q5-A2 | UX | `_updated` timestamp not displayed to operator | No | Q5 |
| Q5-A3 | Security | No server-side numeric type validation on POST body | No | Q5 |
| Q5-A4 | UX | No year-to-year state rollover handling | No | Q5 |

---

## Code Changes Made in Phase 23.0A.1

| File | Change | Reason |
|---|---|---|
| `ui/portfolio_alignment/app.js` | `_formatTaxDollar` K threshold raised from $1,000 to $100,000 | Display precision defect — values like $24,730 were showing as $24.7K |

---

## Architecture Assessment

The Phase 23.0A implementation correctly extends the SIH advisory architecture:

1. **Tax is a display layer, not a data layer.** The analysis pipeline (`run_analysis()`) is unchanged and unaware of tax state. Tax signals are computed entirely in the client from existing `security_overlays` data.

2. **Operator authority is preserved.** All bucket outputs are advisory. The operator sees bucket assignments and reasons but retains full control over whether and when to act.

3. **Graceful degradation is real.** Without cost basis, without holding period data, or with empty tax inputs — the feature degrades cleanly at each tier rather than erroring or rendering broken UI.

4. **Persistence is appropriately scoped.** State survives the typical operator workflow (refresh, restart, close/reopen) without requiring re-entry. It does not persist to any external system.

---

## Final Classification

**ACCEPTED WITH ADVISORIES**

Phase 23.0A is accepted as production-ready for the local advisory tool use case. The one functional defect (display precision) has been corrected in Phase 23.0A.1. All 10 remaining advisories are non-blocking UX and code-quality improvements suitable for a future hardening pass.

### Recommended Next Actions (Prioritized)

| Priority | Action |
|---|---|
| 1 (Near-term) | Add Reset / Clear button to Tax Context Panel (Advisory Q5-A1) |
| 2 (Near-term) | Display `_updated` "Last saved" label near Save button (Advisory Q5-A2) |
| 3 (Near-term) | Add numeric type validation on `POST /api/operator/tax-state` (Advisory Q5-A3) |
| 4 (Mid-term) | Add "days to long-term" derived column to Bucket B rows (Advisory Q2-A3) |
| 5 (Mid-term) | Add `holding_period_days` to portfolio ingestion pipeline to enable Bucket B coverage |
| 6 (Mid-term) | Implement CSV import for tax context (Q6 — generic tax context CSV schema) |
| 7 (Future) | Year-to-year state rollover handling (Advisory Q5-A4) |

---

*Phase 23.0A.1 validation completed. No additional work required for Phase 23.0A acceptance.*
