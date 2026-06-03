# Conviction Framework Design
## Phase 7.6 — Unified Conviction Framework (UCF)

**Status:** Design only. No code changes.
**Objective:** The system performs signal reconciliation so the operator does not have to.

---

## 1. Problem Statement

The current system computes conviction through five independent frameworks:

| Framework | Output | Operator question answered |
|-----------|--------|---------------------------|
| STI | narrative_tier, strategic_classification, trim_priority_score | "Is this worth keeping?" |
| Deployment Queue | CW-DAS rank | "Should I add to this?" |
| Recommendations | signal_direction, severity | "What observation is warranted?" |
| Replay | replay_supported, percentile | "Is conviction backed by evidence?" |
| Phase E | per-field narratives | "Why does it have these signals?" |

Each framework is computed independently. None of them feeds back into another in a unified way. The operator must mentally reconcile 10 per-holding signals before deciding anything.

**Core problem:** Multiple frameworks describing the same underlying fact.

When AEIS has:
- composite=4.71, ESS=BULLISH, replay_supported=True, trim_score<30, weight=2.4%, drift=0
- ...the system currently surfaces these as 10 separate data points instead of one answer: **"This is your best deployment candidate."**

---

## 2. Design Principles

1. **Single verdict per holding** — the UCF outputs one primary conviction label per holding.
2. **Signal hierarchy preserved** — ESS > composite > replay > allocation in case of conflict.
3. **Backward compatible** — existing fields (narrative_tier, CW-DAS, trim_score) remain. UCF is a new synthesis layer on top of them.
4. **Conflict surfaced, not hidden** — when signals diverge, the UCF flags that divergence explicitly rather than silently choosing.
5. **Operator authority maintained** — UCF gives a recommendation; the operator decides.
6. **Additive only** — UCF reads existing computed fields; it does not recompute them.

---

## 3. UCF Output Model

### 3.1 Primary UCF Conviction Label

Six labels, ordered from highest to lowest conviction:

```
CORE_CONVICTION_LEADER     → Best holdings + best deployment candidates
HIGH_CONVICTION_ANCHOR     → Strong hold, eligible for deployment
DEPLOYMENT_CANDIDATE       → Not full conviction, but addable under right conditions
TACTICAL_GROWTH            → Growth position — hold but do not prioritize for new cash
MAINTAIN                   → No strong signal either direction; hold passively
TRIM_WATCH                 → Weakening signal, concentration pressure, or loss of replay
```

---

### 3.2 Label Definitions

#### CORE_CONVICTION_LEADER
**What it means:** The highest-confidence holdings in the portfolio. Best deployment candidates under current mandate.

**Entry criteria (all must be true):**
- `narrative_tier == CORE_CONVICTION_LEADER` (existing gate: BULLISH + replay + composite ≥ 4.0 + weight ≥ 1.5% + trim_score < 30)
- `cw_das_score` places this holding in top quartile of eligible queue
- No OW node redundancy penalty active

**Operator interpretation:** "These are your best bets. If deploying cash, start here."

**Current example (PAR-20260531):** AEIS, VRT

---

#### HIGH_CONVICTION_ANCHOR
**What it means:** Strong conviction hold. May be deployment-eligible but lacks one CCL gate (e.g., lower weight, missing replay, or slight trim pressure).

**Entry criteria (any path):**
- Path A: `narrative_tier == CORE_CONVICTION_LEADER` + OW penalty active (deployment blocked, but conviction intact)
- Path B: `narrative_tier == HIGH_CONVICTION_ANCHOR` (HCR classification) + `composite_score ≥ 3.5` + `signal_direction ∈ {BULLISH, NEUTRAL}`
- Path C: `cw_das_score` top 50% among eligible, with replay_supported=True

**Operator interpretation:** "Hold with confidence. Add only if CW-DAS rank is strong AND deployment cash available."

**Current example:** ARW, SNX, ATLC, PSX (also CVE, TSM, NVDA — blocked by OW but remain anchors)

---

#### DEPLOYMENT_CANDIDATE
**What it means:** Positive signal, replay-supported, but below full CCL threshold. Worth adding to, with care.

**Entry criteria:**
- `replay_supported == True`
- `composite_score ≥ 3.0`
- `signal_direction ∈ {BULLISH, NEUTRAL}`
- Does NOT meet all CCL gates (e.g., weight < 1.5%, composite < 4.0, or trim_score ≥ 30)
- NOT subject to OW node redundancy penalty

**Operator interpretation:** "Deploy here if top-of-queue candidates have capacity constraints. Not first choice."

---

#### TACTICAL_GROWTH
**What it means:** Active growth position. Signal may be positive but lacks replay backing or full conviction depth. Hold as part of thematic exposure.

**Entry criteria:**
- `narrative_tier == TACTICAL_GROWTH_CANDIDATE`
- `composite_score ≥ 2.5`
- `signal_direction ∈ {BULLISH, NEUTRAL}`
- Not a trim candidate

**Operator interpretation:** "Hold. Do not prioritize for new cash. Monitor for signal upgrade to deploy."

**Current example:** Holdings with BULLISH signal but not replay-supported — FHI, JBL, LMAT, IVZ

---

#### MAINTAIN
**What it means:** Neutral conviction. No strong buy or sell signal. Position has strategic or allocation role but signal is flat.

**Entry criteria:**
- `signal_direction ∈ {NEUTRAL, UNKNOWN}`
- `composite_score` between 2.0 and 3.5
- `strategic_classification ∈ {CORE_COMPOUNDER, STRATEGIC_CORE}` OR ETF/fund (no analytical signal)
- Not a trim candidate

**Operator interpretation:** "Keep as part of structural allocation. Do not add to or reduce without reason."

**Current example:** ETFs (VOO, VB, VXUS), structural fixed income (BND, BNDX), AMG

---

#### TRIM_WATCH
**What it means:** Signal weakening, concentration pressure building, or replay dropped. Not necessarily an immediate sell, but requires active monitoring.

**Entry criteria (any path):**
- Path A: `strategic_classification ∈ {REDUCIBLE, REDUNDANT_EXPOSURE, CONCENTRATION_RISK}`
- Path B: `trim_priority_score ≥ 50`
- Path C: `signal_direction == BEARISH` regardless of tier
- Path D: Previously replay_supported, now replay_supported = False (lap regression — requires history)

**Operator interpretation:** "This position is under pressure. Do not add. Evaluate reduction in the next rebalance."

**Current example:** PRIM (BEARISH, composite=2.06), KGC (BEARISH ESS)

---

### 3.3 UCF Conflict Flag

When signals diverge across frameworks, the UCF should surface a conflict flag rather than silently resolve it.

**Conflict types:**

| Conflict Type | Definition | Flag |
|---------------|------------|------|
| `SIGNAL_TIER_MISMATCH` | ESS BULLISH but narrative_tier is TGC or lower | ⚠ Signal ahead of tier assignment |
| `REPLAY_LOSS` | Was replay_supported; now not (requires run history) | ⚠ Replay support dropped |
| `CONVICTION_OW_TENSION` | CCL/HCA tier but OW node penalty active | ⚠ Good stock, wrong allocation node |
| `TRIM_RETAIN_CONFLICT` | strategic_classification=HIGH_CONVICTION_RETAIN + trim_score ≥ 50 | ⚠ Already flagged in trim_intelligence.py |
| `COMPOSITE_ESS_DIVERGE` | ESS BEARISH but composite ≥ 3.0 (or vice versa) | ⚠ Provider disagreement |

Conflicts are surfaced as advisory flags — they do not change the primary UCF label, but they appear alongside it.

---

## 4. Gap Analysis

### 4.1 Duplicate Signal Paths

| Signal | Computed by | Used in | Duplication |
|--------|-------------|---------|-------------|
| "This is high conviction" | narrative_tier (STI) | deploy queue label, recs | Same fact expressed 3 different ways |
| Replay-backed strength | replay_supported (bool) | CW-DAS +20, trim penalty relief, Phase E narrative | Single boolean drives 4 separate surface outputs |
| "ESS is bullish" | ess_score_text + signal_direction | composite (50%), trim Signal Weakness, CW-DAS Momentum, Phase E text | ESS counted 4× across different frameworks |
| "This is a good deployment target" | CW-DAS rank | Deployment Queue only | No cross-reference to STI anchor rank |
| Portfolio weight too high | percent_of_portfolio | CW-DAS Sizing, CW-DAS Conc Pen, trim Concentration Pressure, OW drift | Weight feeds 4 conviction penalty mechanisms independently |

### 4.2 Conflicting Signals (Current Live)

| Symbol | Conflict | Description |
|--------|----------|-------------|
| CVE | CONVICTION_OW_TENSION | CCL-tier holding blocked from deployment by EQUITIES.INTERNATIONAL OW. Score=84.0 if unblocked. |
| TSM | CONVICTION_OW_TENSION | CCL-tier, blocked, score=81.6 |
| NVDA | CONVICTION_OW_TENSION | CCL-tier, blocked, score=78.4 |
| KGC | COMPOSITE_ESS_DIVERGE | ESS=BEARISH but composite=2.61 (secondary consensus partially rescues). Signal=NEUTRAL via override. |
| FHI | SIGNAL_TIER_MISMATCH | BULLISH signal, composite=3.56, replay not supported → falls to TACTICAL_GROWTH despite strong signals |

### 4.3 Redundant Rankings

The system currently produces **two separate ranking systems** that largely describe the same thing:

| Ranking | Source | Top-3 (May 2026) | Purpose |
|---------|--------|------------------|---------|
| CW-DAS Deployment Rank | deployment_queue.py | AEIS, VRT, ARW | "Deploy here" |
| Strategic Anchor Rank | trim_intelligence.py | (same symbols expected) | "These are anchors" |

These are independent calculations producing correlated outputs. The UCF would unify them into a single `ucf_rank` that serves both deployment prioritization and retention priority.

### 4.4 Narrative Duplication

The system generates narrative text about conviction in:
1. STI retain narratives (`trim_intelligence.py`)
2. Phase E synthesis cards (`phase_e_synthesis.py`)
3. Recommendation rationale (`recommendations.py`)
4. Deployment queue "notes" field (`deployment_queue.py`)

All four may describe the same holding's conviction with different phrasing, from different angles, for the same operator decision. The UCF provides a single canonical conviction statement per holding that all four surfaces can reference.

### 4.5 Overlap Quantification

From reference run PAR-20260531-F794D952 (81 holdings, 43 with signals):

| Overlap Type | Count | Notes |
|-------------|-------|-------|
| Holdings where CW-DAS rank and anchor rank agree (top quartile) | ~11 | AEIS, VRT, ARW + others — estimated, no direct cross-join today |
| Holdings with BULLISH signal but not in deployment queue | 11 | Non-replay BULLISH stocks — FHI, LMAT, JBL, etc. |
| Holdings with deployment queue entry but OW-penalized | 11 | Same 11 blocked candidates |
| Signals where ESS and composite agree | ~38/43 | KGC is primary divergence case |
| Signals where ESS and composite disagree | ~5 | Estimated from BEARISH overrides |

---

## 5. UCF Data Model (Design)

```python
@dataclass(frozen=True)
class UnifiedConvictionVerdict:
    symbol:             str
    ucf_label:          str         # One of 6 primary labels
    ucf_rank:           int         # 1 = highest in portfolio (unified ranking)
    ucf_score:          float       # 0–100 (derived from CW-DAS + anchor score synthesis)
    conflict_flags:     list[str]   # Zero or more CONFLICT_TYPE values
    signal_summary:     str         # One-line canonical narrative
    
    # Source signals (read-only — not recomputed)
    composite_score:    Optional[float]
    signal_direction:   str
    narrative_tier:     str         # existing CCL/HCA/TGC
    replay_supported:   bool
    replay_percentile:  Optional[float]
    trim_priority_score: float
    cw_das_score:       Optional[float]  # None if not in queue
    cw_das_rank:        Optional[int]
    
    # Deployment intent
    deployment_eligible: bool       # True if in CW-DAS queue
    deployment_blocked:  bool       # True if eligible but OW-penalized
    deployment_block_reason: Optional[str]
```

---

## 6. UCF Score Formula (Design)

The `ucf_score` synthesizes across all available conviction signals into a single 0–100 number.

```
ucf_score = (
    signal_component    × 0.30  +   # composite_score / 5 × 100
    replay_component    × 0.20  +   # 100 if replay_supported; percentile if available
    tier_component      × 0.25  +   # CCL=100, HCA=80, TGC=40, MAINTAIN=20, TRIM=0
    momentum_component  × 0.15  +   # ESS BULLISH=100, NEUTRAL=50, BEARISH=0
    sizing_component    × 0.10      # headroom_pct × 100
) - penalty_deductions

penalty_deductions:
    OW_node_penalty    = 10.0       # if redundancy_pen active
    concentration_pen  = pro-rated  # if pct > 6%
    trim_signal_pen    = min(trim_priority_score × 0.1, 15)
```

This produces a UCF score that:
- AEIS: ≈ 90–95 (all signals aligned)
- CVE: ≈ 75–80 (CCL strength, OW penalty deducted)
- FHI: ≈ 55–65 (BULLISH but no replay)
- PRIM: ≈ 10–20 (BEARISH, low composite)
- SPAXX: ≈ 0–5 (cash, no signals)

---

## 7. UCF Ranking Unification

The `ucf_rank` replaces both `strategic_anchor_rank` and `cw_das_rank` as a unified portfolio ranking:

```
Tier 1 (CORE_CONVICTION_LEADER):   Ranked by ucf_score desc
Tier 2 (HIGH_CONVICTION_ANCHOR):   Ranked by ucf_score desc
Tier 3 (DEPLOYMENT_CANDIDATE):     Ranked by ucf_score desc
Tier 4 (TACTICAL_GROWTH):          Ranked by ucf_score desc
Tier 5 (MAINTAIN):                 Not ranked (structural positions)
Tier 6 (TRIM_WATCH):               Ranked by trim_priority_score desc (worst first)
```

The global `ucf_rank` is the cross-tier rank (1 = highest conviction globally). TRIM_WATCH positions appear at the bottom.

---

## 8. Implementation Guidance (When Phase 7.6 is Built)

> **This section is architecture specification only. No code in this document.**

**Recommended layering:**

```
Layer 0: Existing signals (unchanged)
  - composite_score, ess_score_text, signal_direction
  - narrative_tier, strategic_classification, trim_priority_score
  - replay_supported, replay_percentile
  - cw_das_score, cw_das_rank

Layer 1: UCF Synthesis (new — read-only from Layer 0)
  src/portfolio/unified_conviction.py
    build_ucf_verdicts(profiles, overlays, dq_queue) → list[UnifiedConvictionVerdict]

Layer 2: UCF Artifact (new)
  data/portfolio_ingestion/analysis_runs/{run_id}/ucf_verdicts.json

Layer 3: Runner integration (additive)
  runner.py: call build_ucf_verdicts() after deployment queue; persist artifact; include in run result

Layer 4: UI surface
  operator_conviction_dashboard_design.md defines the UI shape
```

**Key constraint:** Layer 1 must be purely a reader of Layer 0 outputs. No re-computation of existing signals. This ensures UCF can never conflict with STI, deployment queue, or recommendations — it only aggregates them.

**Test strategy:** UCF label for AEIS should be CORE_CONVICTION_LEADER. UCF label for PRIM should be TRIM_WATCH. UCF label for SPAXX should be MAINTAIN. These are acceptance criteria.
