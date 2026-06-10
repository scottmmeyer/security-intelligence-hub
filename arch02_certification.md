# ARCH-02: Certification

**Date:** 2026-06-09

---

## Certification Checklist

| Criterion | Status |
|---|---|
| ARCH-01: Label renamed from "Recommended Actions" to "Deployment Candidates" | PASS |
| ARCH-02: Reduction Queue section renders in UI | PASS |
| ARCH-02: Data source is CRA capital sources (no new backend) | PASS |
| ARCH-02: Ranking uses native CRA priority (not CW-DAS normalized) | PASS |
| ARCH-02: Blocked assets visible with 🔒 badge (not hidden) | PASS |
| ARCH-02: SELL_LAST assets visible with ⏸ badge | PASS |
| ARCH-02: Pool total shown in header | PASS |
| ARCH-02: FVI tier shown when available | PASS |
| ARCH-02: Placeholder shown while CRA loads async | PASS |
| No CW-DAS scoring changes | PASS |
| No RPS changes | PASS |
| No CRA logic changes | PASS |
| No PAP changes | PASS |
| No policy engine changes | PASS |
| `escHtml()` on all user-facing dynamic content | PASS |
| Full regression suite: 0 failures | PASS |

---

## Final Q&A

### Q1: Was ARCH-01 implemented?

**Yes.** "Recommended Actions — Top 10" → "Deployment Candidates — Top 10" in `app.js`. The label accurately describes the surface (capital deployment buy candidates, CW-DAS ranked).

### Q2: Was ARCH-02 implemented?

**Yes.** `renderReductionQueue()` renders a "Reduction Queue — Top 10" panel as a sibling to the Deployment Queue. It uses `_craProposal.sources` as its data source (no new backend logic), sorted by CRA priority (URGENT → HIGH → MODERATE → LOW → DEFER) and then estimated proceeds.

### Q3: What does the Reduction Queue show today?

| Rank | Symbol | Priority | Category | Est. Proceeds | Policy |
|---|---|---|---|---|---|
| 1 | TSLA | — | Signal Deterioration | $13,904 | 🔒 Blocked |
| 2 | LMAT | MODERATE | Tax-Aware Exit | $7,133 | — |
| 3 | CIEN | MODERATE | Tax-Aware Exit | $4,667 | — |
| 4 | DVN | MODERATE | Tax-Aware Exit | $4,508 | — |
| 5 | SBS | LOW | Overweight Reduction | $4,389 | — |
| 6 | VB | MODERATE | Low Conviction | $4,340 | — |
| 7 | VOO | MODERATE | Low Conviction | $4,248 | — |
| 8 | MSFT | MODERATE | Tax-Aware Exit | $4,117 | — |
| 9 | ANIP | MODERATE | Tax-Aware Exit | $4,006 | — |
| 10 | AVGO | MODERATE | Tax-Aware Exit | $3,966 | — |

Pool header: **$96,633 est. pool · 1 blocked by policy**

### Q4: Are any protected assets visible?

**Yes — TSLA is visible at rank #1 with its blocked state disclosed.** This is correct behavior. TSLA is the highest-urgency reduction candidate (RPS=85, VERY_BEARISH, overweight node) and hiding it would obscure the portfolio's true reduction picture. The 🔒 badge and reduced opacity make the blocked state immediately apparent.

No other DO_NOT_SELL assets appear in the top 10.

### Q5: Should ARCH-04 be created next?

**Yes.** ARCH-04 (KGC DEFERRED policy propagation artifact) is the next most actionable backlog item from the audit. KGC currently shows as DEFERRED because it's in the same REDUCE_OVERWEIGHT rec as DODFX (which carries SELL_LAST). KGC has no individual SELL_LAST policy constraint. The fix requires per-symbol execution state evaluation in multi-symbol sell recs, rather than propagating the most-restrictive state to all affected symbols. This is a behavioral refinement to `apply_policy_to_recommendations()`.

The suggested GitHub issue: "ARCH-04: Fix policy propagation artifact in multi-symbol REDUCE_OVERWEIGHT recs — KGC inherits DODFX SELL_LAST deferral"
