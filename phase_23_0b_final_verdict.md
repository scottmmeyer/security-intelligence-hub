# Phase 23.0B — Final Verdict: Multi-Dimensional Sell Candidate Framework

**Phase:** 23.0B  
**Verdict Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Scope:** Replace bearish-signal-only sell candidate framework with 7-category Portfolio Action Pipeline

---

## Executive Summary

Phase 23.0A produced a functional but architecturally limited tax-aware actions system. Its core flaw: it enters at the wrong point in operator workflow. The operator does not begin by asking "what signals are bearish?" — they begin by asking "what portfolio actions are warranted right now?" Signal deterioration is one input to that question, not the organizing principle.

Phase 23.0B defines the architecture, category taxonomy, and UI design for a replacement framework. All findings are based on verified analysis of run PAR-20260603-AC8FD5F0 with 81 portfolio holdings.

---

## Q1 Answer: Does the Current Framework Match Operator Workflow?

**No.**

The current framework detects only `signal_direction === "BEARISH"` holdings. In the current 81-position portfolio:

- TSLA and PRIM appear (BEARISH signal)
- FIS does not appear — despite −$14,344 unrealized loss (largest in portfolio), 4.81% allocation, former employer designation
- DODFX, VXUS, VEA, FIGFX do not appear — despite all four being in the EQUITIES.INTERNATIONAL node, which is overweight by +6.63% (MODERATE)
- VOO and FXAIX do not appear — index funds with UNKNOWN signal, no ESS coverage

The framework produces 2 of the ~10 candidates a complete analysis would surface. It is not wrong — TSLA and PRIM are legitimate candidates. The problem is completeness: the framework misses 80% of what the operator needs to act on.

**Verdict:** Current framework does NOT match operator workflow.

---

## Q2 Answer: Should Bearish Detection Remain the Primary Mechanism?

**No.**

Bearish signal detection should become **Category 1 (Signal Deterioration)** — one of seven entry points for action candidates. It should not be removed. It should be demoted from the sole mechanism to one input in a multi-dimensional framework.

The current implementation also has a latent defect: `opportunity_flag = "TRIM"` from the overlay is not being read correctly. The JS reads `ov.recommended_action` but the overlay field is `opportunity_flag`. This means even the bearish detection mechanism is incomplete — TRIM-flagged holdings do not appear.

**Verdict:** Bearish detection should be Category 1 of 7. Field name defect should be corrected when implementing Phase 23.0B.

---

## Q3 Answer: Should FIS Appear in Tax-Aware Actions?

**Yes — highest priority.**

FIS profile:
- Signal: NEUTRAL (not bearish — but not a hold signal on a −38.1% position with no forward intent)
- Unrealized loss: −$14,344.30 (largest unrealized loss in the portfolio)
- Strategic profile: Former employer stock, no purchase intent, no allocation dependency
- Tax impact: Harvesting absorbs 58% of the $24,730 available gain capacity

FIS should appear under:
- **Category 2: Strategic Exit** (HIGH priority)
- **Category 5: Loss Harvest** (HIGH priority)
- **Category 4: Funding Source** (as the best available funding vehicle for new deployments)

FIS is the most important action candidate in the current portfolio. Its complete absence from the current framework is the clearest evidence of the architectural gap.

**Verdict:** FIS MUST appear. It is the highest-priority candidate in the portfolio.

---

## Q4 Answer: Should Overweight Allocations Generate Sell Candidates?

**Yes, automatically for MODERATE and HIGH severity nodes.**

`recommendations.json` already contains `REDUCE_OVERWEIGHT` entries for:
- EQUITIES.INTERNATIONAL (+6.63%, MODERATE)
- EQUITIES.INTERNATIONAL.LARGE (+4.10%, MODERATE)
- EQUITIES.US.MEGA.HYPER_MEGA (+3.58%, MODERATE)

These recommendations exist but are not connected to any action candidate generation. The missing pipeline:

```
REDUCE_OVERWEIGHT recommendation → constituent holdings → Category 3 candidates
```

No new computation is needed. The data is already in `recommendations.json` and `alignment.csv`.

**Current gap impact:** DODFX, VXUS, VEA, FIGFX (total exposure: ~$24,000) are all legitimate reduction candidates for the international overweight. None appear in the current framework because none have ESS signals.

**Verdict:** Overweight allocations SHOULD generate Category 3 candidates. This is a pipeline connection problem, not a data problem.

---

## Q5 Answer: Should Funding Source Intelligence Be Added?

**Yes.**

The deployment queue identifies what to buy. Without funding source intelligence, the operator cannot answer "what do I sell to fund this purchase?" These are two halves of the same decision.

Funding source candidates rank by:
1. Low conviction (or no conviction anchor)
2. Poor replay alignment
3. Neutral/Unknown signal
4. Overweight allocation (reduction already recommended)
5. Favorable tax profile (loss > gain-within-capacity > gain-beyond-capacity)

Top funding source in current portfolio: **FIS** (strategic exit + loss harvest + no forward conviction). It frees $23,287 of capital while simultaneously harvesting $14,344 of loss benefit.

**Guardrail required:** High-conviction holdings (ARW, CVE, SNX, ATLC, MU, PSX) must be explicitly excluded from auto-generated funding source suggestions.

**Verdict:** Category 4 (Funding Source) should be added. Required guardrail: conviction anchors cannot be surfaced as funding sources.

---

## Q6 Answer: How Should Tax Context Integrate?

**Tax context is a ranking modifier within categories, not a candidate generator.**

Design rules:
- T1: Tax context cannot create a candidate — only signal/allocation/strategic logic does that
- T2: Tax context cannot exclude a candidate — holdings with adverse tax profiles still appear
- T3: Within a category, sort by tax profile: `HARVEST: ADDS CAPACITY` > `HARVEST: TAX-FREE` > `SELL: LT GAIN` > `SELL: ST GAIN`
- T4: When cost basis is unavailable, label as `NO COST BASIS` — do not suppress the candidate
- T5: Available gain capacity ($24,730 in current state) informs whether gains are tax-free — tracked cumulatively across all candidates

**This is a reversal of Phase 23.0A's architecture.** Phase 23.0A generates candidates from tax profile. Phase 23.0B generates candidates from portfolio logic and applies tax context as a modifier.

**Verdict:** Tax context integration as described in Q6 is correct. Phase 23.0A's approach was architecturally inverted.

---

## Q7 Answer: What Should the New UI Look Like?

The "Tax-Aware Actions" section should be replaced with "Portfolio Action Pipeline" — a grouped, categorized view with 7 collapsible sections.

Key design decisions:
- **Category sections auto-hide when empty** — clean when no candidates exist
- **Category sections auto-expand for HIGH priority** — FIS would auto-expand Cat 2 and Cat 5
- **Context line per section** explains why the category is active (e.g., "EQUITIES.INTERNATIONAL: 18.63% vs 12.0% target (+6.63% drift)")
- **Cross-category holdings** appear primarily in one category with secondary references in others
- **Tax Context column** shows HARVEST: ADDS CAPACITY / TAX-FREE / LT GAIN / ST GAIN / NO COST BASIS
- **Timing column** shows SELL NOW / CONSIDER / WAIT / DEFER

Projected action pipeline for current portfolio (PAR-20260603-AC8FD5F0):

| Category | Candidates |
|---|---|
| Cat 1: Signal Deterioration | TSLA, PRIM |
| Cat 2: Strategic Exit | FIS |
| Cat 3: Allocation Reduction | DODFX, VXUS, VEA, FIGFX (TSLA cross-ref) |
| Cat 4: Funding Source | FIS (cross-ref), DODFX (cross-ref), VXUS (cross-ref), VOO, FXAIX |
| Cat 5: Loss Harvest | FIS (cross-ref) |
| Cat 6: Gain Harvest | (optional — informational only) |
| Cat 7: Deferral Watch | Empty until holding_days available |

**Verdict:** Phase 23.0B UI design approved as described.

---

## Implementation Dependency Note

Phase 23.0B is a design phase. The following implementation dependencies are deferred to Phase 23.0C:

1. **Cost basis in overlay** — `SecurityIntelligenceOverlay` needs `cost_basis`, `market_value`, `holding_days` from `holdings.csv`. Without this, Categories 5, 6, and 7 cannot compute tax context (though candidates can still appear with `NO COST BASIS` label).

2. **`opportunity_flag` field name fix** — JS reads `ov.recommended_action`; should read `ov.opportunity_flag`. This is a one-line fix that un-breaks existing TRIM detection.

3. **Overweight node → holding mapping** — `alignment.csv` has node assignments. Runner needs to expose per-holding node membership in the API response so JS can identify which holdings are in overweight nodes.

4. **Strategic exit operator flag** — Category 2 requires an operator-curated flag (e.g., `strategic_exit: true` in `portfolio_alignment_state.json`). New UI input field needed.

---

## Phase 23.0B Classification

**APPROVED FOR IMPLEMENTATION**

The 7-category Portfolio Action Pipeline is architecturally correct for the operator workflow. It surfaces all relevant action intelligence, applies tax context as a modifier (not a gatekeeper), and maps cleanly to the analytical data already produced by the pipeline.

Phase 23.0A remains in place and functional. Phase 23.0B replaces its front-end presentation layer and extends the candidate generation logic. Phase 23.0A's tax capacity calculation, state persistence, and tax context labels remain valid and are reused in Phase 23.0B.

| Deliverable | Status |
|---|---|
| Q1: Current Framework Audit | Complete — `phase_23_0b_current_framework_audit.md` |
| Q2: Sell Category Design | Complete — `phase_23_0b_sell_category_design.md` |
| Q3: FIS Case Study | Complete — `phase_23_0b_fis_case_study.md` |
| Q4: Overweight Rebalancing Pipeline | Complete — `phase_23_0b_rebalancing_pipeline.md` |
| Q5: Funding Source Framework | Complete — `phase_23_0b_funding_source_framework.md` |
| Q6: Tax Ranking Integration | Complete — `phase_23_0b_tax_ranking_integration.md` |
| Q7: UI Design | Complete — `phase_23_0b_ui_design.md` |
| Final Verdict | **APPROVED FOR IMPLEMENTATION** — this document |
