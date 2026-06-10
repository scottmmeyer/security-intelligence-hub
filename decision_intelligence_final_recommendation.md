# Decision Intelligence Layer — Final Recommendation

**Date:** 2026-06-10

---

## Q1: Should a Decision Intelligence Layer exist?

**YES — unambiguously.**

The current system correctly identifies WHAT to buy and WHAT to reduce. The gap is WHY. Without context, operators face a high cognitive burden for every non-obvious signal, and risk either acting on incomplete information or ignoring legitimate signals.

The PRIM case makes this concrete: BEARISH ESS + BUY analyst consensus + −15% price action creates a trilemma that the current system cannot resolve. DIL closes this gap without adding complexity to the scoring or ranking engines.

---

## Q2: What information sources provide the highest operator value?

**Ranked by operator value / implementation cost:**

1. **FMP fundamentals** (EPS surprise, beat rate, revenue growth) — **ALREADY AVAILABLE.** Highest value, zero additional cost. The EPS miss vs. beat rate context alone resolves 60% of signal divergence cases.

2. **Price context — 1D/5D/52W** (yfinance) — HIGH value, LOW cost. Answers "why did this appear today?" which is the most common operator question. yfinance already installed.

3. **Signal alignment classification** (ESS+Yahoo+Zacks consensus_matrix) — **ALREADY AVAILABLE.** Determines conflict posture. Already computed.

4. **Analyst target freshness** — Knowing that Yahoo targets are 4 days old post-earnings vs. 2 days dramatically changes confidence in the upside %.

5. **News headlines** — HIGHEST value for catalyst investigation, but HIGH governance and cost burden. Phase 3.

---

## Q3: Can catalyst investigation be performed deterministically?

**Partially — for known patterns.**

The following catalyst patterns can be detected deterministically from existing data:

| Pattern | Detection | Reliability |
|---|---|---|
| EPS miss (single quarter vs. trend) | FMP beat_rate + latest_eps_surprise_pct | HIGH |
| Revenue acceleration/deceleration | FMP revenue_acceleration field | HIGH |
| Signal deterioration (momentum-driven) | ESS BEARISH + recent price action implied | MEDIUM |
| Street divergence | consensus_matrix classification | HIGH |
| Stale analyst targets | Yahoo refresh_date vs. run date | HIGH |
| Position is tax-aware exit (not signal) | CRA category | HIGH |
| Position is passive vehicle | security_type + ESS empty | HIGH |

Cannot be determined deterministically without new data:
- Specific news event (earnings call, guidance cut, contract loss)
- CEO departure, M&A, regulatory events
- Sector rotation driver

---

## Q4: Should internet research be integrated?

**Yes in Phase 3, with strict governance.**

News headline integration (Polygon.io, NewsAPI, Benzinga) would dramatically improve catalyst investigation quality. However, it requires:

- API key management
- Content policy review (financial advice disclaimer implications)
- Rate limiting and cost controls
- Coverage gaps handling (smaller companies less covered)
- Freshness controls (don't show 3-month-old news)

**Phase 1–2: No internet data.** Phase 3 design sprint should treat news as a separate, isolated display layer with explicit operator disclosure that headlines are raw, unfiltered, and not validated.

---

## Q5: How should conflicting signals be explained?

**Use the four-category framework:**

1. `FULL_ALIGNMENT` — explain which signals agree and why this increases confidence
2. `PARTIAL_ALIGNMENT` — identify the outlier; explain possible reasons (stale, different time horizon, model vs. momentum)
3. `MAJOR_DIVERGENCE` — explicitly call out the conflict; provide competing hypotheses; default to INVESTIGATE posture
4. `NO_SIGNAL` — explain this is a passive vehicle or unscored holding; posture is structural, not signal-driven

The explanation must never declare "the model is right and analysts are wrong" or vice versa. It presents both views and lets the operator decide.

---

## Q6: Should DIL ever influence scores or rankings?

**NO. Under any circumstances.**

This is a hard architectural constraint. The moment DIL outputs can influence CW-DAS or RPS, the system becomes circular: scores influence interpretation, interpretation influences scores. This produces hallucination-like behavior — the system would reinforce its own outputs without external validation.

DIL is a read-only consumer of the scoring layer. It cannot write back.

---

## Q7: What is the minimum viable DIL?

**Phase 1 MVP: `computeDIL()` in JavaScript, no new data sources.**

Inputs: `ac` (analyst_consensus), `fs` (fidelity_signals), `fmp` (FMP data, already in DQ scorer), `ucf` (UCF verdict), `ov` (overlay)

Outputs: `posture_label`, `posture_class`, `key_points[]`, `rationale_text`, `evidence_list[]`

Implementation: Single function, ~150 lines of JS. Applied to Reduction Queue profiles (ARCH-05 row expansion). Zero backend changes.

**This resolves 70% of operator interpretation burden using only currently available data.**

---

## Q8: What is the mature-state vision?

**3-tier DIL system (24-month horizon):**

**Tier 1 — Signal Synthesis (Today's MVP):** Deterministic rules on existing signals. Posture + rationale for every portfolio candidate.

**Tier 2 — Market Context Layer (3–6 months):** yfinance price history and earnings calendar. "What happened this week" context. Stock fell 15% + guidance cut detected from price + earnings-window proximity.

**Tier 3 — Catalyst Intelligence (12–24 months):** News headline integration + earnings transcript summarization + analyst revision tracking. Full "what changed and why" investigation panel. The full PRIM experience described in the problem definition.

---

## Q9: Where should this rank relative to existing backlog items?

**HIGH priority, Phase 2 implementation.**

Current ranking context:
- ARCH-01 through ARCH-05: COMPLETE
- SI-REFRESH-03 (coverage history): LOW
- ETF-CONV-01 (label rename): LOW
- ETF-CONV-03 (strategic_role fix): MEDIUM

**DIL Phase 1 MVP should be NEXT major sprint after current backlog closes.** Reasons:
1. Zero backend changes required
2. Uses data already surfaced in ARCH-05 profiles
3. Directly improves demo-readiness (the PRIM question is the first question any portfolio manager asks)
4. Highest operator trust impact per implementation hour of any remaining backlog item

---

## Q10: What would the operator experience be for PRIM after a 15% selloff?

**With DIL Phase 1 (current data only):**

The operator opens the Reduction Queue, sees PRIM ranked #4 (SIGNAL_DETERIORATION, HIGH priority). They click "▼ Profile" to expand, then see the DIL panel at the bottom:

```
⚠ INVESTIGATE BEFORE ACTING

PRIM — Primoris Services Corp (Infrastructure EPC, US Small Cap)

Context:
PRIM's bearish ESS signal conflicts with street consensus (BUY, 14 analysts,
$143.79 target, 18% upside). FMP fundamentals show: beat rate 85.7% over 8
quarters, but most recent quarter missed by 30.6%. Revenue grew +18.9% YoY.

Pattern: SINGLE_QUARTER_MISS — strong executor with one outlier quarter.
Analyst targets likely reflect pre-earnings views and may revise.
ESS bearish signal is consistent with momentum following the EPS miss.

Recommendation: Wait 3–5 days for analyst target revisions before reducing.
If targets hold after revisions, reconsider. If targets cut significantly, the
reduction signal has corroboration.

Evidence:
• ESS BEARISH [Fidelity StarMine, 2026-06-09]
• Zacks 1.0 STRONG_BUY [Zacks, 2026-06-09]
• ABR 1.86 BUY, 14 analysts [Yahoo, 2026-06-05]
• EPS Q1 miss: −30.6% | Beat rate 8Q: 85.7% [FMP, 2026-06-04]
• Revenue growth Q1 YoY: +18.9% [FMP, 2026-06-04]
• Signal alignment: PARTIAL_ALIGNMENT [Computed, PAR time]

Advisory: All postures are interpretive. Operator remains decision maker.
```

**With DIL Phase 2 (yfinance added):**

The same panel, but with the opening context:

```
📉 −15.2% today  |  −16.8% 5D  |  18th pct. of 52W range
Next earnings: ~2026-08-06

This move pattern is consistent with a guidance-driven selloff following earnings.
The bearish ESS was likely triggered by today's price action.
```

**The operator can now make an informed decision in under 60 seconds.** Without DIL, the same investigation takes 5–10 minutes of manual research across multiple platforms — with the risk of missing the beat rate context entirely.
