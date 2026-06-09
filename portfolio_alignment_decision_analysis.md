# Portfolio Alignment — Decision Analysis

Repository: security-intelligence-hub  
Audit Date: 2026-06-09

## Q1 — Actionable Decisions Available to Operator

The operator can make the following decisions from this page:

### Execution Decisions (Highest Priority)

1. **Deploy cash** — Which symbols to add to from the Deployment Queue, and how much
2. **Accept or skip CRA rotation proposal** — Which positions to liquidate (capital pool) and what to buy (rotation targets)
3. **Execute allocation reductions** — Which overweight positions to trim (PAP Cat 3)
4. **Select funding sources** — Which positions to liquidate first when capital is needed (PAP Cat 4)
5. **Confirm strategic exits** — Which operator-designated exit candidates to proceed with (PAP Cat 2)

### Policy Decisions

6. **Set or revoke DO_NOT_SELL policy** — Protect a position from execution
7. **Set or revoke SELL_LAST policy** — Defer a position to last in liquidation order
8. **Set Strategic Exit** — Mark a position for programmatic exit consideration

### Monitoring Decisions

9. **Accept or dismiss retain signals** — DELL, MSFT retain signals with evidence
10. **Acknowledge or ignore dislocation events** — Review dislocation watchlist
11. **Select mandate archetype** — Switch between CONCENTRATED_ALPHA, BALANCED, etc.

### None — Information Only

12. Multi-dimensional scores (no action tied to them)
13. Replay alignment score (no direct execution path)
14. Concentration tier (no direct action)
15. Reconciliation status FAIL (1/13) — visible but no operator action defined
16. Intentional asymmetry score

---

## Q2 — Metric Classification

### Actionable Metrics

| Metric | Why Actionable |
|---|---|
| Deployable cash ($21,711) | Directly determines deployment budget |
| Drift per node (+6.1pp INTL, +4.4pp ULTRA_MEGA) | Determines reduction urgency |
| CRA capital pool total | Determines rotation capacity |
| DQ candidate rank (VRT #1, ARW #2) | Determines deployment order |
| Policy state (TSLA: DO_NOT_SELL) | Explains blocked recommendations |
| PAP Cat 1 flag + ESS signal | Determines trim urgency |

### Informational Metrics

| Metric | Role |
|---|---|
| Portfolio value ($465K) | Context; no action |
| Concentration tier (DIVERSIFIED) | Context; no action |
| Holding count (81) | Context; no action |
| Mandate display (CONCENTRATED_ALPHA) | Selection context |
| Asymmetry state (HIGH_CONVICTION) | Narrative context |
| Replay alignment (58/100) | Coverage quality; indirect action through rebalancing |
| Tax bucket per holding | Context; modifies urgency of Cat 4 ordering |

### Diagnostic Metrics

| Metric | Role |
|---|---|
| Legacy Alignment 41% | System-internal diagnostic; unclear operator meaning |
| Reconciliation FAIL (1/13) | Data integrity signal; operator cannot fix |
| ESS per symbol | Evidence quality for individual holds |
| Composite score per symbol | Signal confidence |
| Conviction tier per symbol | Classification input to recommendations |

### Redundant or Conflicting

| Metric | Redundancy |
|---|---|
| "Legacy Alignment 41%" (KPI strip) vs "Allocation Alignment 41%" (multi-dim) | Same value, two displays, one labelled "Legacy" |
| Concentration Risk panel vs KPI "Concentration: DIVERSIFIED" | Duplication of concentration tier |
| Recommendation lane count in KPI vs Recommendation section header | Same data in two places |
| Replay alignment in multi-dim vs Replay Alignment section | Same score repeated |

---

## Q3 — Sources of Cognitive Overload

### Duplicate Information

1. **Alignment score**: KPI strip ("Legacy Alignment 41%") + Multi-Dim card ("Allocation Alignment") + recommendation urgency labels — same number in 3 places
2. **Concentration**: KPI card + dedicated Concentration Risk panel
3. **Replay score**: Multi-Dim card + Replay Alignment & Geography section + REPLAY_ALIGNMENT_CONTEXT recommendation card

### Conflicting Signals

1. **INCREASE_UNDERWEIGHT + REDUCE_OVERWEIGHT simultaneously**: Operator sees "Build US Large" and "Reduce International" on the same page. Without explanation that these are independent sleeves, this looks contradictory.
2. **Reconciliation FAIL but analysis completed**: System shows FAIL (1/13) but still produces recommendations. Operator may not know whether to trust output.
3. **EXECUTABLE actions but also BLOCKED actions in same section**: Both visible, but BLOCKED has no "what would unblock this" guidance.

### Unnecessary Cognitive Load

1. **Security Intelligence Overlay (81 rows)**: Placed mid-page before CRA and PAP. Operator must scroll past 81 holding rows to reach execution guidance.
2. **40-node allocation map**: Full hierarchy table when operator needs to see top 3 overweight nodes to act.
3. **21 CONVICTION_EXPLAINABILITY_CARD** items (addressed by PRA-IMPL-06 but not yet fully rationalized): Still 25 collapsed anchors.
4. **Phase labels**: Many internal labels ("Phase C", "Phase 7.3B", "Phase 23.5") visible in code-originated UI text — these have leaked into display strings in some areas.
