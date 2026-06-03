# Operator Signal Governance
**Phase 7.6C — Signal Authority and Confidence Framework**
**Run Reference:** PAR-20260601-9CFD7C63
**Version:** 1.0
**Date:** 2026-06-01

---

## Purpose

This document defines the operator decision rules for handling signal disagreements in the Security Intelligence Hub. It translates the Signal Authority Framework (signal_authority_framework_v1.md) into concrete, actionable procedures for portfolio managers reviewing UCF verdicts and CW-DAS deployment queues.

These rules govern when to accept system recommendations, when to investigate further, and when to override. All overrides must be documented.

---

## Governance Principles

1. **Default to the system.** The UCF label and CW-DAS rank reflect the intended signal hierarchy. Operators should accept system recommendations unless a specific governance rule applies.

2. **Conflict flags require acknowledgment.** Any holding with a non-empty `conflict_flags` field must be reviewed before deployment. Deploying into a flagged position without documented acknowledgment is a governance violation.

3. **ESS is the primary signal authority.** When ESS disagrees with other signals, ESS is presumed correct unless a documented override case applies. The burden of proof is on the operator to justify deploying against ESS direction.

4. **Replay absence is a deployment gate.** Positions without `replay_supported = True` should not receive primary deployment capital. Tactical sizing only.

5. **Yahoo ABR is informational.** Yahoo upside_pct and ABR are not in the scoring path and cannot block or approve deployment. They are consulted as valuation risk notes only.

6. **Fidelity Opinion = ESS.** Operators must not treat Fidelity analyst direction and ESS as independent confirmations. They are derived from the same source.

---

## Decision Procedures by Scenario

### Scenario A — Clean Full-Alignment Deployment
**Condition:** All available signals agree (ess=BULLISH, zacks≥4.0, danelfin≥4.0, yahoo=Buy), replay_supported=True, no conflict_flags
**Action:** Deploy per CW-DAS recommendation. No additional review required.
**Examples:** ARW, SNX, ATLC, PSX, CAH, LRCX (PAR-20260601-9CFD7C63)

---

### Scenario B — COMPOSITE_ESS_DIVERGE Flag
**Condition:** `conflict_flags` contains `COMPOSITE_ESS_DIVERGE`; ESS direction contradicts the composite/signal direction
**Current instance:** AEIS (ESS=BEARISH vs composite=3.06, signal_direction=BULLISH per Zacks+Danelfin)

**Required operator actions:**
1. **Acknowledge the flag explicitly.** Record in run notes: "COMPOSITE_ESS_DIVERGE acknowledged for [SYMBOL]: ESS=[text], Zacks=[value], Danelfin=[value]."
2. **Do not deploy to a NEW position.** A COMPOSITE_ESS_DIVERGE flag on a holding not currently owned means do not open. ESS bearish is the governing signal.
3. **For existing positions:** Do not increase. Hold if within normal position bounds. Add to monitoring watch.
4. **Downgrade trigger:** If ESS drops to VERY_BEARISH, initiate trim regardless of Zacks/Danelfin.

**Override case (exceptional):** If the operator has specific non-public or industry information contradicting ESS, they may approve a limited tactical position (maximum 50% of normal sizing). This requires written justification with ticker, date, justification text, and approver initials.

---

### Scenario C — CONVICTION_OW_TENSION Flag
**Condition:** `conflict_flags` contains `CONVICTION_OW_TENSION`; position is at or near overweight threshold
**Current instances:** TSM, NVDA (PAR-20260601-9CFD7C63)

**Required operator actions:**
1. Do not deploy additional capital to this position regardless of signal direction.
2. Review position size relative to portfolio policy thresholds (see config/allocation_policy.yaml).
3. If conviction remains high and position is acceptable at current size, clear the tension by adjusting the threshold OR trimming to below the tension trigger.
4. Signal direction (bullish) does NOT override position size policy.

---

### Scenario D — ESS Bullish, Yahoo Analyst Upside Negative
**Condition:** ESS direction = BULLISH/VERY_BULLISH; yahoo_upside_pct is negative (analysts' price targets below current price)
**Current instances:** CIEN (-20.1%), DELL (-17.4%), CBOE (-8.7%)

**Required operator actions:**
1. No block, no flag change. These holdings remain deployment-eligible.
2. Add "Yahoo analyst upside negative: [value]% — analysts' consensus price target is below current price" to operator notes.
3. Adjust position sizing: for upside_pct < -15%, consider reducing to 75% of normal sized allocation. For -10% to -15%, note only.
4. This is a valuation risk note, not a signal override. ESS momentum authority is intact.

**Note:** CIEN and DELL are both BULLISH per all composite signals (ESS+Zacks+Danelfin) despite negative Yahoo upside. The negative upside indicates analyst price targets have not kept pace with current price appreciation — a common condition for momentum-driven positions.

---

### Scenario E — Danelfin Strongly Disagrees with ESS (No UCF Flag)
**Condition:** Danelfin score ≥ 4.0 (BULLISH) while ESS = BEARISH or VERY_BEARISH — with NO UCF conflict flag raised (this gap is not currently detected by the system)
**Current instance:** KGC (Danelfin=5.0, ESS=BEARISH)

**Required operator actions:**
1. Treat as a manual investigation trigger. The system does not raise a flag; operator must recognize the pattern by reviewing both fields.
2. Do not increase position based on Danelfin=5.0 alone. ESS authority applies.
3. Consider: Is Danelfin measuring a different time horizon (e.g., 3-month technical momentum) vs ESS (earnings surprise, shorter-term fundamental)?
4. If the operator determines Danelfin signal reflects a distinct thesis (e.g., technical breakout, gold price momentum for KGC), they may note it but should not override ESS-governed composite scoring.

**System improvement recommendation:** Add DANELFIN_ESS_DIVERGE conflict flag to UCF (see signal_authority_framework_v1.md Known Gaps §1).

---

### Scenario F — Replay Absent (replay_supported = False)
**Condition:** `replay_supported = False` for a holding regardless of ESS/composite direction
**Current instances:** KGC, PRIM, TSLA (replay_supported = False based on session data)

**Required operator actions:**
1. Do not include in primary deployment queue. These are tactical-only positions.
2. Maximum sizing: 50% of normal allocation for any position without replay support.
3. If ESS is BULLISH and all signals agree, operator may approve at reduced sizing with documented justification.
4. Replay absence is particularly significant for positions with low conviction scores — double constraint.

---

### Scenario G — ESS Very Bearish (VERY_BEARISH)
**Condition:** ESS = VERY_BEARISH regardless of other signals
**Current instance:** TSLA (ESS=VERY_BEARISH, Danelfin=1.5 confirms, Zacks=2.0 confirms)

**Required operator actions:**
1. Place on TRIM_WATCH immediately (system likely already assigns this label).
2. Do not deploy any capital.
3. Initiate trim schedule per trim_priority_score if position exists.
4. Requires ESS improvement to NEUTRAL minimum before any new capital consideration.

---

### Scenario H — Zacks Strong Buy + ESS Neutral (Momentum Gap)
**Condition:** Zacks = 4.0 or 5.0 (Buy/Strong Buy) while ESS = NEUTRAL
**Current instance:** PLTR (ESS=NEUTRAL, Zacks=4.0, Danelfin=1.5)

**Required operator actions:**
1. Note that ESS NEUTRAL = momentum_c = 0 in CW-DAS (full 10-pt momentum component lost).
2. System labels this TACTICAL_GROWTH or DEPLOYMENT_CANDIDATE depending on other factors.
3. Do not promote to HCA consideration without ESS improvement.
4. Zacks Buy alone is insufficient to overcome the momentum penalty. PLTR composite=3.11 due to ESS neutral dragging below midpoint.

---

## Conflict Flag Quick Reference

| Flag | Meaning | Required Action |
|---|---|---|
| `COMPOSITE_ESS_DIVERGE` | ESS direction opposes composite/signal direction | Acknowledge; do not deploy to new position; hold existing |
| `CONVICTION_OW_TENSION` | Position at/near overweight threshold | Do not add capital; review sizing policy |
| `REPLAY_LOSS` | replay_supported=False despite high conviction score | Tactical sizing only (≤50% normal) |
| `SIGNAL_TIER_MISMATCH` | Signal strength doesn't match conviction tier | Review tier assignment; check conviction model |
| (none) | No conflicts detected | Deploy per system recommendation |

---

## Documentation Requirements

For any deployment decision that deviates from the system recommendation (override, block, size adjustment), the operator must record:

```
Date: [YYYY-MM-DD]
Run: [PAR-...]
Symbol: [TICKER]
System recommendation: [deploy / hold / trim]
Operator decision: [different from above]
Conflict flags: [list or 'none']
Justification: [text]
Approver: [initials]
```

This documentation should be stored in the run's `operator_notes` field (future system capability) or in a running notes file until system support is available.

---

## Escalation Thresholds

| Condition | Escalation Level |
|---|---|
| COMPOSITE_ESS_DIVERGE + proposed deployment > $5,000 | Senior PM review required |
| CONVICTION_OW_TENSION + proposed additional deployment | Senior PM review required |
| Replay absent + proposed deployment > $3,000 | Senior PM review required |
| Override of TRIM_WATCH for VERY_BEARISH ESS | Senior PM review required |
| Any override without documentation | Policy violation |
