# Signal Authority Framework v1
**Phase 7.6C — Signal Authority and Confidence Framework**
**Run Reference:** PAR-20260601-9CFD7C63
**Version:** 1.0
**Date:** 2026-06-01

---

## Overview

This framework establishes a formal hierarchy of signal authority for the Security Intelligence Hub. It governs how signals are weighted during disagreements, which signals have veto power over deployment decisions, and what operators should consult when UCF conflict flags are raised.

The framework is descriptive of the current system's actual signal architecture plus normative guidance for operator behavior. It is not a redesign — it formalizes what the code already does and makes the implicit explicit.

---

## Tier Structure

### Tier 1 — Primary Authority (Forward-Validated)

**Signals: ESS (StarMine/Fidelity), Replay Support**

These signals have primary authority in the system. When they disagree with lower-tier signals, the operator should default to these unless there is a documented reason to override.

| Signal | Authority Basis | System Role |
|---|---|---|
| ESS (StarMine/Fidelity) | Institutional-grade quantitative model; academically validated earnings-surprise momentum factor; daily freshness; 88.2% universe coverage | 61.1% composite weight + full momentum component in CW-DAS (max 40 of 103 pts) |
| Replay Support | Only forward-validated bucket-level signal in the system; 365-day historical evidence window | Binary 20-pt gate in CW-DAS |

**Key rule:** When ESS is BEARISH or VERY_BEARISH, the system is designed to penalize the score significantly even if Zacks and Danelfin are bullish. This is the intended behavior. Operators should treat COMPOSITE_ESS_DIVERGE flags as a genuine warning, not a system error.

---

### Tier 2 — Secondary Authority (High Coverage, Earnings-Grounded)

**Signal: Zacks Rating**

Zacks provides the highest universe coverage of any composite-contributing signal (91.9%) and uses an earnings estimate revision model with documented predictive validity. It is a meaningful independent signal, but its composite weight (27.8%) is insufficient to override ESS alone.

| Signal | Authority Basis | System Role |
|---|---|---|
| Zacks | Earnings estimate revision model; 91.9% coverage; ~weekly updates | 27.8% of composite score; contributes to signal component in CW-DAS |

**Key rule:** Zacks=5.0 (Strong Buy) is a significant positive signal and should be noted by operators when ESS is bearish. However, in the current weighting scheme, Zacks Strong Buy reduces but does not eliminate the ESS bearish penalty in composite scoring. Zacks alone cannot overcome ESS bearish.

---

### Tier 3 — Corroborating Evidence (Useful Confirmation)

**Signals: Danelfin AI Score, Yahoo ABR (analyst upside %)**

These signals are useful when they confirm Tier 1 and Tier 2 signals, but they should not be used to override them in isolation.

| Signal | Authority Basis | Limitation |
|---|---|---|
| Danelfin | AI/ML model, orthogonal methodology, independent of ESS/Zacks design | 33.7% coverage; 11.1% composite weight; monthly updates; cannot overcome ESS bearish |
| Yahoo ABR + Upside | Aggregates analyst consensus; price target upside provides valuation perspective not present in momentum models | Not in scoring path (v1); 10-day stale; analyst consensus is a lagging indicator |

**Key rule:** When Danelfin=5.0 disagrees with ESS=BEARISH (e.g., KGC), treat it as a reason to investigate, not a reason to deploy. When Yahoo upside is negative (e.g., CIEN -20.1%, DELL -17.4%), treat it as a valuation risk note, not a deployment block.

---

## Authority Hierarchy Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 — PRIMARY AUTHORITY                                     │
│  ESS (StarMine/Fidelity)         Replay Support (binary gate)   │
│  Max influence: 40/103 pts CW-DAS  Max influence: 20/103 pts   │
│  Composite weight: 61.1%           Composite weight: N/A        │
├─────────────────────────────────────────────────────────────────┤
│  TIER 2 — SECONDARY AUTHORITY                                   │
│  Zacks (Earnings Estimate Revisions)                            │
│  Max influence: ~8/103 pts (via composite) Composite: 27.8%    │
├─────────────────────────────────────────────────────────────────┤
│  TIER 3 — CORROBORATING EVIDENCE                                │
│  Danelfin AI Score          Yahoo ABR + Analyst Upside %        │
│  Max influence: ~3/103 pts  Max influence: 0 pts (not in path) │
│  Composite weight: 11.1%    Composite weight: 0% (v1)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Signal Disagreement Resolution Rules

### Rule 1 — ESS Bearish vs All Others Bullish
**Example:** AEIS (ESS=BEARISH, Zacks=5.0, Danelfin=4.0, Yahoo=Buy)

**Resolution:** ESS authority applies. Composite will score below midpoint. Do NOT deploy to a new position or increase existing position without explicit operator acknowledgment of the COMPOSITE_ESS_DIVERGE flag. Operator may note "ESS bearish noted; Zacks+Danelfin bullish; monitoring" and defer deployment.

**Threshold for override consideration:** ESS=BEARISH (not VERY_BEARISH) + Zacks=5.0 + Danelfin≥4.0 + Yahoo_upside≥+15% may warrant elevated manual review; but this is NOT an automatic approval path.

---

### Rule 2 — ESS Very Bullish vs Negative Yahoo Upside
**Examples:** CIEN (-20.1%), DELL (-17.4%), CBOE (-8.7%)

**Resolution:** ESS has momentum authority; Yahoo has valuation authority. These are measuring different things. A stock can have strong earnings momentum AND be above analyst consensus price target simultaneously. Yahoo negative upside is a risk note (overvalued per analysts), not a deployment block. Recommend: deploy within normal position bounds but note valuation risk in signal summary.

**Action:** No block, no flag change. Add "Yahoo analyst upside negative: overvalued per consensus price targets" to operator notes.

---

### Rule 3 — Replay Absent + ESS Bullish
**If `replay_supported = False` despite bullish ESS:**

**Resolution:** Replay absence removes 20 CW-DAS pts, which is significant. This is the intended gate: replay validates that historical performance of similar positions in this sector/cap bucket was acceptable. ESS bullishness does not override replay absence. Do NOT deploy above minimal tactical sizing without replay support.

---

### Rule 4 — Danelfin Strongly Disagrees with ESS
**Example:** KGC (Danelfin=5.0, ESS=BEARISH)

**Resolution:** Danelfin is Tier 3 corroboration. It cannot override Tier 1 ESS authority. This case is notable as an investigative trigger (Why is the AI model strongly bullish while ESS is bearish? Different time horizons? Technical vs. fundamental divergence?). However, no COMPOSITE_ESS_DIVERGE flag is currently raised for ESS vs Danelfin mismatches — this is a gap in the current conflict detection system.

**Recommended operator action:** Flag for manual review; do not increase position; do not block current position; note signal disagreement.

---

### Rule 5 — TSM/NVDA — Conviction OW Tension
**Examples:** TSM (CONVICTION_OW_TENSION), NVDA (CONVICTION_OW_TENSION)

**Resolution:** Position is at or near overweight threshold. CONVICTION_OW_TENSION is the correct flag. Regardless of signal direction, these positions should not receive additional deployment until the overweight tension is resolved (trim or threshold adjustment). Signal agreement (all bullish) does not override the position size constraint.

---

## Known Framework Gaps (v1)

1. **No ESS vs Danelfin conflict flag:** Current UCF only flags COMPOSITE_ESS_DIVERGE (ESS vs composite/signal direction). Direct ESS vs Danelfin tension (e.g., KGC) is undetected.

2. **Yahoo ABR not in scoring path:** v1 composite uses only ESS + Zacks + Danelfin. Yahoo ABR is visible in the data but has zero influence on UCF labels or CW-DAS scores. Operators must consult it manually.

3. **Replay depth not distinguished:** All replay_supported=True holdings earn the same 20 pts regardless of whether they appear in 1 or 252 replay runs. Depth gradient would improve signal confidence.

4. **Fidelity Opinion ≠ Independent Signal:** Operators viewing "Fidelity analyst opinion" in the UI may perceive it as separate from ESS. Both are the same StarMine data via Fidelity. The framework explicitly prohibits treating them as independent confirmations.

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-06-01 | Initial framework; formalized existing system architecture; added operator resolution rules |
