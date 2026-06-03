# Comparative Signal Authority Recommendation
**Phase 7.7A — Deliverable Q7 (Final)**
**Generated:** 2026-06-01

---

## 1. Study Question

> Is ESS actually stronger than Zacks and Danelfin, or is ESS simply the best-covered signal?

Phase 7.7A was commissioned to determine whether ESS deserves its 55% composite weight, and whether Zacks (25%) and Danelfin (10%) are appropriately weighted given actual signal effectiveness evidence.

---

## 2. Verdict

### E. INSUFFICIENT_COMPARATIVE_EVIDENCE

The archive depth mismatch between ESS (10.5 months) and Zacks/Danelfin (15 days each) makes a rigorous comparative effectiveness analysis impossible at this time.

**The question cannot be answered empirically with current data.** This is not a hedged finding — it is a structural limitation of the data.

---

## 3. What the Evidence Shows

### 3.1 Where ESS Has Confirmed Advantage

| Dimension | ESS | Zacks | Danelfin | Edge |
|-----------|-----|-------|----------|------|
| Archive depth | 10.5 months | 15 days | 15 days | ESS overwhelming |
| 30d forward return testability | 32,805 pairs | 0 pairs | 0 pairs | ESS only |
| Persistence measurement | HIGH confidence | LOW confidence | LOW confidence | ESS only |
| Universe coverage | 2,918 symbols | 2,601 symbols | 954 symbols | ESS and Zacks comparable |
| Monotonicity tested | PARTIAL (confirmed) | UNTESTABLE | UNTESTABLE | ESS only |

**ESS is the only signal for which effectiveness has been empirically demonstrated in this SIH context.** Its 55% composite weight is supported by this advantage — not disproven.

### 3.2 Where ESS Has Potential Vulnerabilities

ESS effectiveness (Phase 7.6G findings) was partially confirmed, not fully:
- **Return prediction:** Average returns show a U-shape (bucket 1 outperforms bucket 2), suggesting regime sensitivity or distressed-asset rebound effects at the extreme bearish end
- **Median and win rate:** These are properly ordered (ρ = 0.7), supporting ESS as a directional orderer
- **Volatility:** Strongly ordered (ρ = 0.9), confirming ESS as a risk-characterization tool
- **Persistence:** 79.0% — operationally sufficient but not tested across a full bear market cycle

**ESS is a partially confirmed signal, not a fully confirmed signal.** The 55% weight is defensible but not locked.

### 3.3 What Is Unknown About Zacks and Danelfin

The persistent assumption that Zacks (25%) and Danelfin (10%) are weaker than ESS is based on:
1. Archive availability (ESS had a multi-month archive first)
2. Institutional convention (ESS is the dominant signal by composite weight)
3. Absence of evidence against ESS dominance

None of this is the same as evidence of signal weakness. Specifically:

- **Zacks:** Covers 2,601 symbols (89% of ESS's universe). It is a professional consensus rank with institutional-grade methodology. Its effectiveness on 30-day returns is **simply unknown** — it has not been tested in this system. Zacks persistence showing 90.1% over 15 days tells us nothing reliable about long-run behavior.
- **Danelfin:** Covers only 954 symbols (33% of ESS). Its 7-day effectiveness appears mixed (ρ = −0.3 average return) but the sample sizes at bucket extremes are 7–8 observations — far below statistical threshold. These numbers should not be used to assess Danelfin's true effectiveness.

---

## 4. Coverage vs. Effectiveness

The original study question distinguishes two possible reasons for ESS dominance:

**Hypothesis A:** ESS is a genuinely stronger signal (better predictive power, better monotonicity, better persistence) that deserves dominant weighting.

**Hypothesis B:** ESS simply has the deepest archive and broadest universe, making it appear dominant when the comparison is actually asymmetric.

**Current data cannot distinguish A from B.** ESS has been tested because it had enough data to test. Zacks and Danelfin have not been tested because they don't have enough data. If Zacks were given a 10-month archive, we do not know whether it would outperform ESS, match it, or underperform it.

This is the core finding of Phase 7.7A.

---

## 5. What IS Known and Actionable

| Finding | Confidence | Implication |
|---------|-----------|-------------|
| ESS effectiveness confirmed on median, win rate, volatility (30d) | HIGH | 55% weight remains defensible |
| ESS effectiveness not confirmed on average return (U-shape) | MEDIUM | 55% weight should not be raised |
| Zacks covers a comparable universe to ESS (2,601 vs 2,918) | HIGH | Zacks warrants ongoing monitoring |
| Danelfin covers only 32% of ESS universe | HIGH | Danelfin has structural breadth limitation regardless of effectiveness |
| Zacks/Danelfin persistence data is a 15-day artifact | HIGH | Do not use these numbers in weight decisions |
| No 30-day or longer return data exists for Zacks or Danelfin | HIGH | No weight adjustment is justified |

---

## 6. Impact on Current Composite Weight

### Current Weights (Production v1)

```
composite_score = ESS×0.55 + Zacks×0.25 + Yahoo×0.10 (unused) + Danelfin×0.10
```

### Recommended Changes

**NONE.** The weights should not change as a result of Phase 7.7A.

Rationale:
- Insufficient evidence to increase ESS (effectiveness only partially confirmed)
- Insufficient evidence to decrease Zacks (effectiveness unknown, not disproven)
- Insufficient evidence to adjust Danelfin (effectiveness unknown due to data)
- The composite formula remains valid as a weighted blend where ESS dominates by archive depth and practical deployment history, not by proven superiority

The verdict **E. INSUFFICIENT_COMPARATIVE_EVIDENCE** means the status quo is maintained by default.

---

## 7. Recommended Actions

### Immediate (Starting 2026-06-01)

| Action | Owner | Priority |
|--------|-------|----------|
| Implement weekly Zacks data capture with full-universe scope | Data Engineering | HIGH |
| Implement weekly Danelfin data capture with full-universe scope | Data Engineering | HIGH |
| Archive format: same schema as current, timestamped in `data/signals/` | Data Engineering | HIGH |
| Capture frequency: minimum weekly; ideally 2x/week | Data Engineering | MEDIUM |

**Target archive milestone:** Zacks and Danelfin each accumulate 200+ weekly observations per symbol across 6+ months, enabling:
- 30d forward return matching (available ~2026-07-01 for first 30d pairs)
- 90d forward return matching (available ~2026-09-01)
- 6-month persistence sample (available ~2026-12-01)

### Phase 8.x Re-evaluation (Target: 2026-12-01)

Re-run the Phase 7.7A comparative study when:
- Zacks archive ≥ 6 months (capturing ≥ 25 weekly snapshots)
- Danelfin archive ≥ 6 months (capturing ≥ 25 weekly snapshots)
- Both include at least one market correction event for cycle testing

**At that point, the question "Is ESS stronger than Zacks and Danelfin?" can be answered empirically.** The composite weights should be revisited at Phase 8.x.

### Danelfin Coverage Gap

Danelfin covers only 954 symbols (32% of ESS's universe). Even if Danelfin proves to be an effective signal, its 10% weight may be appropriate given that it cannot score the majority of the investable universe. This is a structural constraint, not a data artifact. Monitor whether Danelfin expands coverage in future.

---

## 8. Summary

| Question | Answer |
|----------|--------|
| Is ESS stronger than Zacks and Danelfin? | **Unknown — cannot be tested with current archives** |
| Is ESS dominant by coverage rather than quality? | **Partially — ESS has archive advantage, but Zacks has comparable universe** |
| Should composite weights change? | **NO — E. INSUFFICIENT_COMPARATIVE_EVIDENCE** |
| Is ESS's 55% weight defensible? | **YES — by archive depth and partial effectiveness confirmation** |
| What must happen next? | **Begin systematic Zacks/Danelfin archive capture. Re-evaluate Phase 8.x** |

---

## 9. Phase 7.7A Closure

**Verdict: E. INSUFFICIENT_COMPARATIVE_EVIDENCE**

This is not a failure of the analysis — it is the correct finding. Phase 7.7A discovered a structural data gap that prevents the intended comparison. The recommended response is ongoing data collection, not premature weight adjustments.

Phase 7.7A is complete. All 7 deliverables written. No framework changes. No deployment changes. Signal authority remains: ESS 55%, Zacks 25%, Danelfin 10% pending Phase 8.x re-evaluation.
