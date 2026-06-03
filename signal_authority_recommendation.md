# Signal Authority Recommendation
**Phase 7.6C — Signal Authority and Confidence Framework**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## The Question

> *"When ESS, Fidelity, Zacks, Danelfin, Yahoo, and Replay disagree, which signal should the portfolio manager trust most?"*

---

## The Answer

**Trust ESS (StarMine via Fidelity) for signal direction and momentum. Trust Replay for deployment confidence.**

When these two signals agree: deploy with full confidence.
When they disagree with each other: investigate before deploying.
When either disagrees with Zacks/Danelfin/Yahoo: ESS and Replay take precedence.

---

## Rationale

### Why ESS is the primary directional authority

**1. It is architecturally dominant by design.**
ESS contributes 61.1% of the composite score (vs Zacks 27.8%, Danelfin 11.1%). It also controls the full 10-point momentum component in CW-DAS — which is triggered by ESS direction alone, not by any other signal. No combination of Zacks + Danelfin + Yahoo can overcome ESS in the scoring system. The architects of this system made an explicit, informed choice to give ESS this authority.

**2. It is the most forward-looking signal in the composite.**
StarMine's earnings surprise model captures analyst estimate revisions and actual earnings surprise momentum — a factor with decades of documented predictive validity in academic finance (Post-Earnings Announcement Drift). ESS is updated daily, making it the freshest signal in the system.

**3. It correctly identifies the AEIS case as a warning.**
AEIS is the canonical signal disagreement case in this portfolio: ESS=BEARISH while Zacks=5.0 (Strong Buy), Danelfin=4.0 (Bullish), Yahoo=Buy. The system correctly raises `COMPOSITE_ESS_DIVERGE`. The ESS bearish signal means StarMine's earnings model sees negative earnings surprise momentum — regardless of what analysts' ratings say. Analyst ratings are a lagging indicator; earnings surprise momentum is a leading indicator.

**4. Fidelity Opinion = ESS (same data, different label).**
Operators should not treat "Fidelity analyst opinion" as a separate confirming signal. It is ESS mapped to directional labels (BULLISH/NEUTRAL/BEARISH). There is one source — StarMine via Fidelity — contributing to both the ESS text field and the Fidelity direction field.

---

### Why Replay is the co-authority for deployment decisions

**1. It is the only forward-validated signal in the system.**
Replay is the only signal backed by actual 1-year historical performance evidence within this system. It answers the question: "Did holdings in this sector/cap bucket selected by this system perform acceptably over the past 365 days?" ESS, Zacks, Danelfin, and Yahoo have no internal backtest results in this system — their authority is based on external reputation and institutional pedigree.

**2. It acts as a deployment gate that no momentum signal can override.**
The 20-point binary replay gate in CW-DAS is designed to enforce deployment discipline. A stock with VERY_BULLISH ESS and Zacks=5.0 loses 20 CW-DAS points if it lacks replay support — a penalty so significant that it drops the position from the primary deployment queue. This is correct behavior: historical evidence of sector/bucket performance is a necessary condition for high-confidence deployment.

**3. Replay absence signals elevated uncertainty, not a veto.**
When `replay_supported = False`, it does not mean "do not ever own this position" — it means "this holding is not backed by the same evidence base as replay-supported positions." Tactical sizing is appropriate; primary deployment is not.

---

### Why Zacks, Danelfin, and Yahoo are secondary

| Signal | Why Secondary |
|---|---|
| Zacks | High coverage, legitimate signal, but 27.8% composite weight means it cannot override ESS (61.1%) alone. Zacks=5.0 Strong Buy reduces the ESS bearish penalty but does not eliminate it. Example: AEIS composite = 3.06 despite Zacks=5.0. |
| Danelfin | Lowest composite weight (11.1%), narrowest coverage (33.7%), monthly updates. Useful corroboration when aligned; cannot override ESS as sole dissenter. |
| Yahoo ABR + Upside | Not in the scoring path (v1 composite). Zero influence on UCF labels or CW-DAS. Useful for valuation risk noting (e.g., CIEN, DELL negative upside) but cannot approve or block deployment. |

---

## When to Consider Overriding ESS Authority

ESS authority should be treated as near-absolute **except** when:

1. **ESS is BEARISH (not VERY_BEARISH)** AND all three other signals (Zacks, Danelfin, Yahoo) are strongly bullish AND replay_supported = True AND yahoo upside > +15%.
   - This pattern suggests ESS may be reacting to a recent short-term earnings miss in an otherwise fundamentally sound name.
   - Action: escalate for senior PM review; do not auto-approve; document reasoning.

2. **ESS data is stale** (freshness > 5 days due to data ingestion failure).
   - In this case, composite score is based on stale information; promote Zacks to temporary primary authority.
   - Action: flag as DATA_QUALITY issue; defer deployment until ESS is refreshed.

3. **ESS is missing** for a symbol (coverage gap, new ticker, etc.).
   - Action: use Zacks as directional primary; Danelfin as corroboration; replay as deployment gate.

No other conditions justify treating Zacks, Danelfin, or Yahoo as higher authority than ESS.

---

## When ESS and Replay Conflict

**Case: ESS=VERY_BULLISH, replay_supported=False**
ESS says deploy; Replay says insufficient historical evidence for this bucket. Follow Replay as the deployment constraint: size tactically (≤50% of normal). Do not deploy at full conviction size without replay support. Replay validates the deployment context; ESS validates the signal direction.

**Case: ESS=BEARISH, replay_supported=True**
Replay says this bucket historically performed well; ESS says this specific stock has negative earnings momentum. The conflict is meaningful: the bucket was valid historically, but this particular name within the bucket may be deteriorating. Follow ESS for the individual position decision: trim or avoid despite good bucket-level history.

---

## Signal Trust Ranking (Summary)

| Rank | Signal | Trust Authority | Basis |
|---|---|---|---|
| 1A | ESS (StarMine/Fidelity) | Primary — direction + momentum | Dominant in composite (61.1%), daily freshness, academically validated factor |
| 1B | Replay Support | Primary — deployment confidence | Only forward-validated evidence in system; 365-day backtest; 20-pt binary gate |
| 2 | Zacks | Secondary — earnings estimate corroboration | High coverage (91.9%), legitimate signal, insufficient weight to override ESS alone |
| 3 | Composite Score (aggregate) | Derived — multi-signal synthesis | Useful summary but ESS-dominated; treat as strong only when ESS is the bullish driver |
| 4 | Danelfin | Tertiary — AI model corroboration | Low weight (11.1%), narrow coverage; useful when aligned, weak when dissenting |
| 5 | Yahoo ABR + Upside % | Informational — valuation risk note | Not in scoring path; useful for price target sanity check only |
| — | Fidelity Analyst Opinion | = ESS (same source) | Not an independent signal; treat identically to ESS |

---

## Decision Rule (One Sentence)

**When signals disagree, follow ESS direction and Replay confidence — then note what Zacks says, ignore Danelfin and Yahoo as tiebreakers, and document your reasoning before deploying against any Tier 1 signal.**

---

## Verdict

**Phase 7.6C Verdict: FRAMEWORK_ESTABLISHED**

The signal authority hierarchy is now formally documented. ESS is the primary directional authority. Replay is the primary deployment confidence gate. The system's existing architecture reflects this hierarchy correctly. Operator governance rules are now defined for all major disagreement scenarios. The SCS model provides a path to quantified confidence scoring in a future system update.

**Framework status:** Active — applies to all runs from PAR-20260601-9CFD7C63 forward until superseded by a revised version.
