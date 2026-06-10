# ARCH-02: Reduction Queue Design

**Date:** 2026-06-09  
**Status:** IMPLEMENTED

---

## Objective

Create a "Reduction Queue — Top 10" panel as a sibling to the Deployment Queue (CW-DAS), allowing the operator to see both where to deploy capital and where to source capital in the primary surface.

---

## Design Decisions

### 1. Data Source: CRA Capital Sources (not re-ranked)

The Reduction Queue uses `_craProposal.sources` — the existing CRA capital source array returned by `/api/cra/proposal`. No new computation, no new API calls, no new backend logic.

**Why not RPS from recommendations?** RPS (Reduction Priority Score) is embedded in REDUCE_OVERWEIGHT drilldown data and only covers symbols in overweight allocation nodes. The CRA capital sources cover all five reduction categories: SIGNAL_DETERIORATION, STRATEGIC_EXIT, OVERWEIGHT_REDUCTION, TAX_AWARE_EXIT, LOW_CONVICTION_REDUCTION. The CRA pool is the more complete reduction surface.

### 2. Ranking: Native CRA Priority (not CW-DAS normalized)

Sort order:
1. Priority ascending: URGENT → HIGH → MODERATE → LOW → DEFER
2. Estimated proceeds descending as tiebreak within same priority

**Why not cross-normalize with CW-DAS?** The Action Ranking Architecture Audit concluded that merging CW-DAS and RPS/CRA onto a single scale requires a validated weighting model that doesn't exist yet. This is ARCH-03 (future backlog). Option B (separate queues, native metrics) was recommended.

### 3. Timing: Loads with CRA Proposal

The Reduction Queue renders immediately after `loadCRAProposal()` succeeds. During the async load period, a placeholder shows "Waiting for CRA capital sources…". This parallels the existing CRA panel behavior.

### 4. Blocked Assets Are Shown (with state)

TSLA (DO_NOT_SELL) appears in the queue with a "🔒 Blocked" badge and reduced opacity. This is intentional:
- The operator should know that the highest-urgency reduction candidate exists
- They should understand it's blocked by their own policy
- The unblock path ("To unblock: remove DO_NOT_SELL policy") is shown in PAP per UX-PA-06

Hiding blocked assets would obscure the portfolio's real reduction picture.

### 5. Suppressed (De Minimis) Sources Not Shown

Sources below the $500 MINIMUM_ACTIONABLE_PROCEEDS threshold are suppressed by `build_capital_sources()`. They do not appear in the Reduction Queue (consistent with CRA behavior).

---

## Components

### HTML (`ui/portfolio_alignment/index.html`)

New section added immediately after `deploymentQueueContainer`:
```html
<div id="reductionQueueContainer" class="rq-section"></div>
```

New CSS classes added: `.rq-section`, `.rq-panel`, `.rq-header`, `.rq-title`, `.rq-pool-badge`, `.rq-table`, `.rq-row-blocked`, `.rq-rank`, `.rq-sym`, `.rq-cat`, `.rq-pri` (with priority variants), `.rq-proceeds`, `.rq-policy-blocked/deferred/review`, `.rq-fvi`, `.rq-no-data`, `.rq-loading`

### JavaScript (`ui/portfolio_alignment/app.js`)

Three new additions:

**1. `renderReductionQueuePlaceholder()`**  
Called from `renderResults()` — shows loading state immediately when a portfolio is analyzed.

**2. `renderReductionQueue(sources, totalPool, fviData)`**  
Full render function. Parameters:
- `sources` — array from `_craProposal.sources`
- `totalPool` — from `_craProposal.total_capital_pool`
- `fviData` — from `_lastAnalysisData.fvi_data` (optional; shows FVI tier if available)

Displays:
- Pool size badge and blocked count in header
- Top 10 sources (sorted by priority then proceeds)
- Per row: Rank | Symbol + Reason | Priority | Est. Proceeds (with sizing %) | Policy / FVI

**3. Hook in `loadCRAProposal()`**  
After `_renderCRAProposal(_craProposal)`, calls:
```javascript
renderReductionQueue(
    _craProposal.sources || [],
    _craProposal.total_capital_pool,
    fviData
);
```

---

## Column Definitions

| Column | Description | Source Field |
|---|---|---|
| Rank | Position in sorted list | Computed |
| Symbol / Reason | Ticker + category label + ESS badge | `s.symbol`, `s.category`, `s.ess_score_text` |
| Priority | URGENT/HIGH/MODERATE/LOW/DEFER badge | `s.priority` |
| Est. Proceeds | Dollar amount + sizing % | `s.estimated_proceeds`, `s.sizing_pct`, `s.current_value_usd` |
| Policy / FVI | Policy badge (if applicable) + FVI tier | `s.blocked_by_policy`, `s.policy_type`, `fvi_data[symbol].fvi_tier` |

---

## Visual Design

- Red top border (`var(--sev-high)`) distinguishes it from the Deployment Queue (accent color border)
- "Reduction Queue — Top 10" title in red to visually signal sell-side vs. buy-side
- Pool badge shows estimated aggregate proceeds
- Blocked rows have reduced opacity and red background tint
- SELL_LAST rows show amber "⏸ Sell Last" badge
- Advisory note: "Source capital — guidance only, not trade instructions"
