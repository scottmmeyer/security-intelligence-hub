# Final Threshold Recommendation — Phase 7.5R
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Question:** Should the CCL weight threshold be changed from 1.50%?

---

## Recommendation

### KEEP_THRESHOLD

**The current 1.50% CCL promotion threshold should not be changed.**

---

## 1. What Was Tested

Four threshold scenarios were evaluated:

| Scenario | Threshold | CCL Count | Promoted | Demoted |
|----------|-----------|-----------|----------|---------|
| A | 1.00% | 8 | CAH, CIEN, DELL | — |
| **B** | **1.25%** | **6** | **DELL** | **—** |
| **C (current)** | **1.50%** | **5** | **—** | **—** |
| D | 2.00% | 4 | — | GTX |

Across all scenarios, the same 5 base CCL conditions apply: signal=BULLISH AND replay=True AND composite ≥ 4.0 AND weight ≥ threshold AND trim_score < 30.0.

---

## 2. Why Not Lower the Threshold

### 2A. Lowering to 1.25% (Scenario B) makes things worse

Promoting DELL (1.32% weight) to CCL pushes DELL to rank 1 with a CW-DAS score of 97.91 (vs 90.91 as HCA). DELL then receives **$7,973** — slightly less in absolute terms than VRT's current $8,822, but the concentration character changes adversely:

- DELL is not a position the operator necessarily wants to build aggressively — its weight of 1.32% suggests it is not a deeply established core position
- r(composite, alloc) actually **decreases** to 0.3847 vs 0.4080 current — signal alignment worsens
- VRT drops to rank 2 but is still the largest real established position

The operator would have replaced one concentration problem (VRT dominant at 26.6%) with a different, harder-to-explain one (DELL dominant at 24.0% despite lower weight and lower conviction history).

### 2B. Lowering to 1.00% (Scenario A) transfers concentration, doesn't remove it

Under Scenario A (1.00%), CAH becomes rank 1 with a score of 98.59 (composite 4.50, low headroom pressure, strong signals) and receives **$6,806 (20.5%)**.

While Top-1 drops from 26.6% to 20.5%, Top-5 **increases** from 46.0% to 59.4%:

```
C_150: VRT 26.6%, ARW 6.2%, SNX 5.0%, ATLC 4.3%, PSX 3.9% = 46.0%
A_100: CAH 20.5%, DELL 14.4%, CIEN 11.7%, VRT 9.9%, ARW 2.9% = 59.4%
```

The deployment pool becomes dominated by 3 newly-promoted CCL candidates (CAH, DELL, CIEN) who collectively receive $15,455 — 46.6% of the total — while all HCA candidates are squeezed.

**The outcome is a 3-name concentration rather than a 1-name concentration. It is not an improvement.**

Additionally, CAH (1.06%), CIEN (1.17%), and DELL (1.32%) are borderline holdings that barely clear the 1.00% threshold. Promoting them to CCL is operationally counterintuitive — a portfolio manager would not regard a 1.06% holding as a "Core Conviction Leader."

### 2C. Signal alignment does not improve with threshold changes

```
Threshold 1.5% → 1.0%:   r(composite, alloc) moves 0.408 → 0.401  (−0.007, worsens)
Multiplier 3.0 → 1.75:   r(composite, alloc) moves 0.408 → 0.629  (+0.221, improves)
```

The threshold lever does not address the root problem. Deployment capital is disconnected from signal quality because the multiplier amplifies any CCL candidate by 3×. Changing who is CCL does not fix the amplification itself.

---

## 3. Why Not Raise the Threshold

### 3A. Raising to 2.00% (Scenario D) has zero effect

Scenario D is identical to Scenario C. The only demoted holding is GTX (1.94%), which is already blocked from deployment (ranked 34th, due to OW-node penalties) and receives $0 in the current run.

Changing the threshold to 2.00% changes no output whatsoever. The operation would be cosmetic administrative change with no analytical or capital justification.

### 3B. No other threshold in the 1.5–2.0% range materially changes outcomes

Between 1.50% and VRT's weight of 3.60%, no additional holdings would be demoted. CVE (2.47%), TSM (2.33%), GTX (1.94%) all remain CCL until their specific thresholds are crossed. Since all three are currently blocked from deployment anyway, any demotions in this range are output-neutral.

---

## 4. Why Keep 1.50%

### 4A. The threshold is semantically correct

A 1.50% weight threshold for "Core Conviction Leader" status is operationally reasonable:
- It represents a meaningful established position (in this portfolio: ~$7,000–$10,000 market value)
- It excludes borderline, speculative, or early-stage positions
- It requires the portfolio manager to have already committed meaningful capital, signaling prior conviction

Lowering to 1.00% would admit holdings the manager may regard as "test positions" rather than established convictions.

### 4B. The threshold's current CCL population is correct

At 1.50%, the CCL population includes VRT, CVE, TSM, GTX, MU — all holdings where the portfolio manager has made a meaningful commitment (all ≥ 1.94%). This is the right set to receive elevated deployment consideration.

The non-CCL HCA candidates (ARW 0.92%, ATLC 0.89%, SNX 0.86%, AVT 0.93%) have not yet earned CCL status — they are smaller positions that are being grown. This is coherent portfolio construction.

### 4C. The correct remediation is the multiplier, not the threshold

Phase 7.5Q established that the planner multiplier (CCL=3.0, HCA=1.0) is responsible for 94% of the combined concentration reduction achievable, and exclusively drives signal alignment improvement.

The threshold change addresses the wrong part of the system. It is analogous to changing the patient list for a procedure rather than reducing the procedure's dosage.

---

## 5. Comparison Table: Threshold vs Multiplier

| Action | Top-1 Reduction | Signal Gain | Incumbency Fix | Creates New Risk | Recommended |
|--------|----------------|-------------|----------------|-----------------|-------------|
| Lower threshold (1.0%) | −6.1 pp | None | Partial (transfers) | New dominant CCL | No |
| Lower threshold (1.25%) | −2.6 pp | None | Partial | DELL dominates | No |
| Raise threshold (2.0%) | 0 pp | None | None | None | No (pointless) |
| **Reduce multiplier (1.75/1.25)** | **−12.1 pp** | **+0.221** | **Yes** | **No** | **Yes (Phase 7.5Q)** |
| Both threshold+multiplier | −12.9 pp | +0.112 | Yes | New CCL risk | No |

---

## 6. Decision Rationale

```
THRESHOLD CHANGE VERDICT: KEEP_THRESHOLD (1.50%)

Reason A: Raising to 2.00% has zero operational effect.
Reason B: Lowering to 1.25% makes concentration worse (DELL problem).
Reason C: Lowering to 1.00% transfers concentration without improving signal alignment.
Reason D: The 1.50% threshold correctly identifies established conviction positions.
Reason E: The correct remediation for concentration is multiplier reduction (Phase 7.5Q).
```

The 1.50% threshold is calibrated to the portfolio's actual commitment profile. The concentration distortion is not caused by who qualifies for CCL — it is caused by how much amplification CCL designation delivers in the planner. That is a multiplier problem, not a threshold problem.

---

## 7. Interaction Advisory

If Phase 7.5Q's multiplier recommendation (CCL=1.75, HCA=1.25) is adopted, the threshold should still remain at 1.50%. The factorial analysis shows:

- Multiplier-only (1.5% threshold + 1.75/1.25): Top-1=14.5%, r(comp)=0.629
- Both (1.0% threshold + 1.75/1.25): Top-1=13.7%, r(comp)=0.520

Applying the lower threshold along with the multiplier reduction actually **worsens signal alignment** (0.629 → 0.520) because DELL, CAH, CIEN would enter the CCL tier and receive disproportionate allocation despite not being the highest-composite candidates. The combined change undermines the multiplier improvement.

**Do not lower the threshold when adopting the multiplier change.** Adopt the multiplier change alone.

---

## 8. Summary

| Question | Answer |
|----------|--------|
| Is the 1.50% threshold the primary driver of concentration? | **No.** |
| Would lowering the threshold to 1.00% solve the concentration problem? | **No — it transfers it.** |
| Would raising the threshold to 2.00% solve anything? | **No — it has zero effect.** |
| What is the correct action? | **Reduce the planner multiplier (Phase 7.5Q).** |
| Should the threshold change as part of the Phase 7.5Q adoption? | **No — keep at 1.50%.** |

**KEEP_THRESHOLD: 1.50%**
