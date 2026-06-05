# Phase 23.4A — Q1: Operator Workflow Analysis
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip

---

## 1. Current Workflow: Opportunity → Blocked → Diagnostics

### 1.1 As-Built Flow (Phase 23.3 State)

```
Operator opens portfolio alignment UI
        │
        ▼
┌─────────────────────────┐
│  Recommendation Card     │
│  - Symbol / Node         │
│  - Action flag (badge)   │
│  - Opportunity signal    │
└──────────┬──────────────┘
           │
           │ If blocked:
           ▼
┌─────────────────────────────────────┐
│  MANDATE_BLOCKED banner             │  ← Phase 23.3 UI
│  ETF_GATE_FAILED badge              │
│  WORSENS_OVERWEIGHT badge           │
│  CONFLICTS_WITH_MANDATE badge       │
└──────────┬──────────────────────────┘
           │
           │ (No further guidance surfaced)
           ▼
    ❌  DEAD END — Operator must independently:
        - Read mandate logic
        - Consult deployment queue
        - Choose alternative action
        - Determine if any alternative is executable
```

### 1.2 Cognitive Cost at Dead End

When an operator encounters a blocked recommendation today, they face four un-answered questions with no UI support:

| Question | Where the Answer Lives | Manual Steps Required |
|---|---|---|
| Why is this blocked? | optimizer_metadata + mandate logic | 2–3 concepts to synthesize |
| Is there an alternative? | deployment_queue.json | Must mentally cross-reference |
| Which alternative is best? | UCF rank + ESS + headroom | No comparison surface |
| Is the alternative executable? | operator_policy.py | Must remember active policies |

**Assessment:** The current flow terminates at a badge. It tells the operator *that* an action is blocked; it provides no path forward. This places the full interpretive burden on the operator.

---

## 2. Proposed Workflow: Opportunity → Blocked → Next Best Action → Diagnostics

### 2.1 Redesigned Flow

```
Operator opens portfolio alignment UI
        │
        ▼
┌─────────────────────────┐
│  Recommendation Card     │
│  - Symbol / Node         │
│  - Action flag (badge)   │
│  - Opportunity signal    │
└──────────┬──────────────┘
           │
           │ If blocked:
           ▼
┌─────────────────────────────────────┐
│  NEXT BEST ACTION panel             │  ← Phase 23.5 TARGET
│  "Instead of [blocked action]:"     │
│  - Action type (ACCUMULATE / TRIM)  │
│  - Top 3 alternative candidates     │
│  - Deployment scores                │
│  - Expected portfolio effect        │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Suggested Alternatives table       │
│  (ranked list, up to 5)             │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  BLOCK DIAGNOSTICS (collapsible)    │
│  - Why Blocked                      │
│  - Evidence                         │
│  - How To Unblock                   │
└─────────────────────────────────────┘
```

### 2.2 Sequencing Rationale: Next Best Action Before Diagnostics

The operator's primary cognitive need upon encountering a block is **"what do I do instead?"** — not **"why am I blocked?"** Diagnostics are reference material; Next Best Action is actionable guidance.

| Factor | DIAGNOSTICS FIRST | NEXT BEST ACTION FIRST |
|---|---|---|
| Primary operator intent | Understand block | Act on portfolio |
| Time to first actionable step | High (must read + synthesize) | Low (pre-computed, scannable) |
| Expert operator use case | Occasionally reviews | Rarely needs to explain to self |
| New operator use case | Required for understanding | Required for guidance |
| Matches mental model | Forensic/audit | Investment workflow |

**Verdict:** Next Best Action should appear first. Diagnostics collapse by default. An operator who wants the "why" can expand it; an operator who trusts the system skips directly to the alternative.

---

## 3. Evaluating Sequence Against Operator Decision Making

### 3.1 Operator Archetypes

**Archetype A — Execution-Focused Operator**
- Comes to the UI to deploy capital
- Wants to know: "What can I buy/sell right now?"
- Current friction: blocked rec with no forward path forces context switch to deployment queue
- NBA benefit: HIGH — direct path to next executable action

**Archetype B — Research-Oriented Operator**
- Comes to the UI to understand portfolio state
- Wants to know: "Why is this flagged this way?"
- Current friction: Low — MANDATE_BLOCKED badge gives enough signal
- NBA benefit: MEDIUM — still useful to see alternatives but less urgent

**Archetype C — Mandate Oversight Operator**
- Comes to audit alignment vs. mandate
- Wants to know: "Is the system enforcing the right constraints?"
- Current friction: Moderate — no way to verify that alternatives were considered
- NBA benefit: HIGH — validates that the system found valid alternatives before blocking

### 3.2 Frequency Assessment

Based on the PAR-20260604-8DB0393D dataset:
- EQUITIES.US.LARGE: `MANDATE_BLOCKED` — VOO/IVV/SPY all blocked. The recommendation has 5 direct-security candidates (VRT, DELL, LRCX, PLTR, CIEN) all sitting at `pis=0.0` because the mandate gate suppressed the entire rec. The deployment queue has VRT at rank 1 (score 94.97), DELL at rank 4 (92.45), LRCX at rank 8 (91.56). **These are already the answer — the system just doesn't surface them on the blocked card.**
- TSLA: `BLOCKED_BY_POLICY/MONITOR_ONLY`. Deployment queue has no TSLA entry. Next best candidate for capital deployment is VRT rank 1.

In both cases the answer exists in `deployment_queue.json`. It is simply not presented.

### 3.3 Workflow Decision

**RECOMMENDATION: Adopt the revised flow.**

The sequence `Opportunity → Blocked → Next Best Action → Diagnostics` is superior because:
1. It answers the operator's primary question without requiring manual queue lookup
2. It does not change scoring, signals, or mandate logic — purely presentational
3. Diagnostics remain available for operators who need the explanation
4. The data required to generate alternatives already exists in the current pipeline

---

## 4. Scope Boundary

This analysis is **presentation layer only**. The proposed workflow requires:

**ZERO changes to:**
- `src/portfolio/optimizer.py`
- `src/portfolio/mandate.py`
- `src/portfolio/deployment_queue.py` (read-only)
- `src/portfolio/recommendations.py`
- `src/portfolio/unified_conviction.py`
- `src/portfolio/operator_policy.py`
- `src/portfolio/runner.py`
- Any test file

**Required changes (Phase 23.5 implementation scope, not this phase):**
- `ui/portfolio_alignment/app.js`: render `_buildNextBestAction(r)` panel
- `ui/portfolio_alignment/app.js`: reorder BLOCK DIAGNOSTICS sections
- Potentially: expose `deployment_queue` data to UI if not currently available

---

## 5. Summary

| Finding | Result |
|---|---|
| Current workflow terminates at a block badge | TRUE — no forward path exists |
| Next Best Action before Diagnostics improves operator flow | TRUE — reduces cognitive load for all archetypes |
| Alternatives can be generated from existing data | TRUE — deployment queue data already ranked |
| Scoring changes required | NONE |
| Mandate logic changes required | NONE |

**Status: Q1 COMPLETE — DESIGN CERTIFIED**
