# Decision Intelligence Layer — Governance Assessment

**Date:** 2026-06-10

---

## Core Governance Questions

### Q: Should DIL influence scoring?

**NO — unconditionally.**

The CW-DAS, RPS, composite score, and all other quantitative scores are computed by deterministic algorithms from well-defined inputs. DIL outputs must never feed back into any of these. The governance principle is one-way data flow:

```
Scores + Signals → DIL Interpretation
                    (never the reverse)
```

Changing this would introduce circular dependencies and make audit trails impossible.

### Q: Should DIL influence ranking?

**NO — unconditionally.**

The Deployment Queue is ranked by CW-DAS. The Reduction Queue is ranked by CRA priority. DIL cannot reorder these lists. DIL can annotate rows within existing ranked lists but cannot change their order.

An operator reading a `HIGH_CONFIDENCE_REDUCTION` posture on rank #5 does not change the rank — the operator may choose to act on #5 before #3, but that is operator judgment, not system ranking.

### Q: Should DIL be display-only?

**YES — unconditionally.**

DIL outputs (posture labels, commentary, conflict classifications) must:
- Appear only in the UI as advisory text
- Not be persisted to the PAR (recommendations.json, run_metadata.json, etc.)
- Not appear in exported artifacts (CRA CSV/MD exports, deployment plan exports)
- Not be used in reconciliation checks

The only exception: a future audit log could record which posture was shown at the time an operator acted — this is traceability, not influence.

### Q: Should DIL require evidence traceability?

**YES — every conclusion must be auditable.**

Each DIL posture output must cite the specific signals driving it. The UI should show:

```
Posture: INVESTIGATE_BEFORE_ACTING
Drivers:
  • ESS BEARISH [Fidelity, 2026-06-09]
  • Zacks STRONG_BUY (1.0) [Zacks, 2026-06-09]
  • EPS Q1 miss: -30.6% [FMP, 2026-06-04]
  • Beat rate 8Q: 85.7% [FMP, 2026-06-04]
  • Signal alignment: PARTIAL_ALIGNMENT [Computed]
```

This allows the operator to verify the reasoning and identify if any driver is stale.

---

## Operator Authority Preservation

A critical governance constraint: **DIL must never substitute for operator judgment.**

The posture labels are guides, not commands:

- `HIGH_CONFIDENCE_REDUCTION` does NOT mean "execute immediately"
- `INVESTIGATE_BEFORE_ACTING` does NOT mean "never reduce"
- `CONFLICTING_EVIDENCE` does NOT mean the recommendation is wrong

The UI must include a persistent disclosure: *"Decision Intelligence provides interpretive context only. All postures are advisory. The operator remains the final decision maker."*

---

## Data Source Governance

| Source | Governance Requirement |
|---|---|
| StarMine ESS (Fidelity) | Already approved; same as current signal pipeline |
| Yahoo supplemental | Already approved; same as current pipeline |
| Zacks | Already approved; same as current pipeline |
| FMP fundamentals | Already approved; already in FMP enrichment pipeline |
| Company profiles | Already in SIH data signals |
| yfinance price data (Phase 2) | Same terms as current yfinance usage in SIH; no additional approval needed |
| News headlines (Phase 3) | Requires new governance review: API terms, content policy, cost, rate limits |

---

## Audit Trail Requirements

### Minimum (Phase 1)

- DIL posture label is computed at render time from PAR-time signals
- Every displayed posture cites its signal drivers with source and date
- No DIL output stored in PAR artifacts

### Enhanced (Phase 2+)

- DIL posture could be logged in `operator_alignment_state.json` as "displayed posture at time of action" for post-hoc analysis
- Posture history: "last 5 runs showed INVESTIGATE_BEFORE_ACTING for PRIM" — this creates temporal context without influencing current scoring

---

## Failure Mode Analysis

| Failure | Risk | Mitigation |
|---|---|---|
| Stale signals cause wrong posture | Moderate | Always show signal dates; flag if > 14 days stale |
| Posture guides operator to wrong action | Low-Moderate | Persistent advisory disclosure; posture is never a command |
| DIL output confused for score by future developer | Low | Code must keep DIL functions clearly separated from scoring pipeline |
| False confidence from `HIGH_CONFIDENCE` posture | Low | Require 3+ signal sources to reach HIGH_CONFIDENCE; never from single-source |
| FMP data stale (weekly refresh) | Low | Show FMP sourced_date; flag if > 10 days |

---

## Governance Summary

| Dimension | Decision |
|---|---|
| Scoring influence | PROHIBITED |
| Ranking influence | PROHIBITED |
| Persistence in PAR artifacts | PROHIBITED (Phase 1) |
| Evidence traceability | REQUIRED |
| Operator authority override | PROHIBITED |
| Advisory disclosure | REQUIRED in UI |
| External data (Phase 1) | NONE (existing sources only) |
| External data (Phase 2+) | yfinance (same terms); news API requires review |
