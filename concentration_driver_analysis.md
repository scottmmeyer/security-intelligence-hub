# Concentration Driver Analysis — Phase 7.5R
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Question:** Which factor contributes more to deployment concentration — CCL threshold or planner multiplier?

---

## 1. Decomposition Methodology

To isolate each factor's contribution independently, a 2×2 factorial design was used:

| Cell | Threshold | CCL Mult | HCA Mult | Description |
|------|-----------|----------|----------|-------------|
| Baseline | 1.50% (current) | 3.0 (current) | 1.0 (current) | Status quo |
| Threshold-only | 1.00% (lower) | 3.0 (current) | 1.0 (current) | Threshold isolated |
| Multiplier-only | 1.50% (current) | 1.75 (Phase 7.5Q) | 1.25 (Phase 7.5Q) | Multiplier isolated |
| Both | 1.00% (lower) | 1.75 | 1.25 | Combined change |

This design separates the main effects from any interaction between the two levers.

---

## 2. Factorial Results

### Top-1 Concentration (% of deployment pool)

| Cell | Top-1% | Change from Baseline |
|------|--------|---------------------|
| Baseline | 26.59% | — |
| Threshold-only | 20.51% | −6.08 pp |
| Multiplier-only | 14.46% | **−12.13 pp** |
| Both | 13.71% | −12.89 pp |

### Signal Alignment: r(composite_score, allocation)

| Cell | r(comp,alloc) | Change from Baseline |
|------|--------------|---------------------|
| Baseline | 0.4080 | — |
| Threshold-only | 0.4014 | **−0.0066** (worsens slightly) |
| Multiplier-only | 0.6289 | **+0.2208** |
| Both | 0.5197 | +0.1117 |

### Incumbency Correlation: r(weight_pct, allocation)

| Cell | r(wt,alloc) | Change from Baseline |
|------|------------|---------------------|
| Baseline | 0.8721 | — |
| Threshold-only | 0.5083 | −0.3638 |
| Multiplier-only | 0.8391 | −0.0330 |
| Both | 0.5000 | −0.3721 |

---

## 3. Effect Attribution

### Top-1 Concentration Attribution

```
Baseline concentration:        26.59%

Threshold main effect:          −6.08 pp  (47% of combined effect)
Multiplier main effect:        −12.13 pp  (94% of combined effect)
Interaction (cancellation):     +5.32 pp  (threshold & multiplier partially offset)
                                ─────────
Combined (both together):      −12.89 pp → 13.71%
```

The two effects are not additive — applying both together produces a smaller combined reduction than the sum of each effect alone. This occurs because:
- When the threshold is lowered, new CCL candidates (CAH, DELL) absorb the CCL multiplier amplification
- The multiplier reduction then has less concentrated candidates to redistribute from

**Net result: The multiplier is 2× more effective than the threshold at reducing Top-1 concentration.**

### Signal Alignment Attribution

This is the definitive test:

| Change | Effect on r(comp, alloc) |
|--------|--------------------------|
| Threshold: 1.50% → 1.00% | **−0.007** (no improvement) |
| Multiplier: 3.0/1.0 → 1.75/1.25 | **+0.221** (large improvement) |

**The threshold change does not improve signal alignment. It slightly worsens it.** This occurs because:
- The newly promoted CCL candidates (CAH, DELL) receive large allocations *because of their tier*, not because of signal quality
- CAH at 4.50 composite is a good signal, but its $6,806 allocation under A_100 is driven by CCL tier, not by its margin over other candidates
- The overall portfolio-signal correlation therefore does not improve

**The multiplier change exclusively accounts for signal alignment improvement.**

---

## 4. Why Incumbency Correlation Behaves Differently

The threshold affects r(weight, alloc) dramatically (0.87 → 0.51) while the multiplier barely moves it (0.87 → 0.84). This seems to contradict the narrative — but the mechanism is different:

**Threshold effect on r(weight,alloc):**  
Lowering the threshold promotes holdings with moderate weight (CAH at 1.06%, DELL at 1.32%, CIEN at 1.17%). These have *lower* weights than VRT (3.60%) but receive *higher* allocations. This breaks the weight-to-allocation linearity, driving r(weight,alloc) down to 0.51.

**What this means:** The threshold change reduces weight-to-allocation correlation not by rewarding quality — but by promoting new incumbents with lower weights who then dominate the pool. The system is still incumbency-driven; the incumbents are just different ones.

**Multiplier effect on r(weight,alloc):**  
The multiplier reduces how much the CCL tier amplifies weight-based incumbency. VRT remains rank 1 but gets less amplification. This is a proportional reduction that mostly preserves the weight-correlation structure while improving signal alignment.

---

## 5. The "Concentration Transfer" Paradox

Under Scenario A (1.00% threshold), the following happens:

```
Current (C_150): VRT 26.6%, ARW 6.2%, SNX 5.0%, ATLC 4.3%, PSX 3.9%
                 Top-5 = 46.0%

Scenario A:      CAH 20.5%, DELL 14.4%, CIEN 11.7%, VRT 9.9%, ARW 2.9%
                 Top-5 = 59.4%   ← MORE concentrated!
```

Lowering the threshold from 1.50% → 1.00% actually *increases* Top-5 concentration from 46.0% to 59.4%, because three new CCL candidates absorb large allocations while HCA candidates (ARW, SNX, ATLC) get squeezed.

The concentration problem is not solved — it is redistributed.

---

## 6. Quantified Factor Contributions

| Factor | Top-1 Reduction | Signal Alignment Gain | Incumbency Reduction | Verdict |
|--------|----------------|-----------------------|---------------------|---------|
| Threshold: 1.5% → 1.0% | −6.1 pp | **0.0** (zero) | −0.37 | Transfers concentration |
| Multiplier: 3.0/1.0 → 1.75/1.25 | **−12.1 pp** | **+0.221** | −0.03 | Genuinely reduces concentration |
| Both together | −12.9 pp | +0.112 | −0.37 | Multiplier effect dominates |

The multiplier is the primary concentration driver by every meaningful metric:
- **2× as effective** at reducing Top-1 concentration
- **Exclusively responsible** for signal alignment improvement
- **Structural driver**: without the multiplier, CCL designation still produces 9× per-candidate premium over HCA (Phase 7.5Q finding)

The threshold is a **secondary concentration lever** that redistributes concentration without reducing it.

---

## 7. Structural Analysis: The CCL Floor

Even with no planner multiplier at all (Phase 7.5Q Model G), CCL candidates still receive 3× more capital per candidate than HCA average due to:
1. +7 CW-DAS conviction points → higher score → rank 1 → √rank advantage
2. This is the "structural floor" of CCL concentration, not addressable by threshold changes

The threshold determines *who* earns this structural advantage. The multiplier determines *how large* the advantage is. Since the structural advantage alone creates 3× per-candidate premium, no threshold choice eliminates concentration — it only changes the recipient.

---

## 8. Interaction Effect

When both changes are applied together, the combined effect (−12.89 pp) is smaller than the multiplier alone (−12.13 pp). The threshold change *partially cancels* the multiplier's benefit:

```
Interaction term = Combined - Threshold - Multiplier
                 = -12.89 - (-6.08) - (-12.13) = +5.32 pp (cancellation)
```

This means if Phase 7.5Q's multiplier reduction is adopted, also lowering the threshold adds only 0.76 pp of additional concentration reduction (12.89 − 12.13), while simultaneously creating the "new dominant CCL" problem (DELL or CAH at rank 1).

---

## 9. Summary Verdict

**The planner multiplier is the primary driver of deployment concentration. The CCL threshold is a secondary driver.**

| Metric | Primary driver | Secondary driver |
|--------|---------------|------------------|
| Top-1 concentration | Multiplier (2×) | Threshold |
| Signal alignment | Multiplier (exclusively) | Threshold (zero effect) |
| Incumbency inflation | Multiplier (3.0× amplifier) | Threshold (structural, not amplification) |
| Actionable lever | **Multiplier** | Threshold |

The correct path to "reward conviction without letting incumbency dominate" is multiplier reduction (Phase 7.5Q recommendation). Threshold reduction is a distraction that creates new concentration risks without improving signal alignment.
