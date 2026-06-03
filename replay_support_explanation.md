# Replay Support Explanation — Phase 7.5S-A
**Date:** 2026-06-01

---

## Primary Question

> "What historical evidence actually causes a stock to receive replay support?"

---

## The Short Answer

A stock receives `replay_supported = True` if and only if it was selected as one of the **top-N composite scorers** in its peer group (by geography, market cap, and optionally industry) at a prior snapshot date, and that selection is recorded in `data/current/replay_inputs.csv`.

**No price performance data is evaluated. No return threshold must be met. The test is purely: was this symbol in the top-N at the snapshot?**

---

## The Complete Answer

### What "replay" means in this system

A replay is a point-in-time experiment that asks: *"If I had selected the highest-scoring stocks in this peer group at this date, how would that basket have performed over the following year?"* The word "replay" reflects running a selection rule forward from a known past state — replaying the portfolio construction decision with hindsight.

### What causes `replay_supported = True`

The system evaluates a two-stage test:

**Stage 1 — Was the symbol selected?**
The composite score for every universe member was frozen at a snapshot date. The top N symbols (typically 20) in a defined peer group were recorded in `replay_inputs.csv` under `selected_symbols`. If the symbol appears in that list, it advances to Stage 2.

**Stage 2 — Does the symbol's current classification match the replay's scope?**

This depends on which routing path the symbol takes:

| Replay `filter_industry` | Path | Stage 2 check |
|--------------------------|------|---------------|
| `ALL` | `symbol_tier` (unconditional) | None — selection is immediate |
| Any specific industry | `industry_replay_evidence` (conditional) | Must verify: `holding.geo == replay.geo AND holding.cap == replay.cap AND holding.industry == replay.industry` |

If both stages pass, `replay_supported = True`.

### What evidence does NOT cause replay_supported

| Evidence type | Does it affect replay_supported? |
|---------------|----------------------------------|
| Current composite score | No |
| Current ESS rating | No |
| Current Zacks rating | No |
| Historical return of the symbol itself | No |
| TOP_N_STRATEGY basket return | No |
| Being in a benchmark or investable vehicle | No |
| Danelfin, Yahoo, or other signal scores | No |
| Analyst upgrades or news | No |

Replay support is entirely backward-looking at the **selection decision** made at the snapshot date, not the outcome.

---

## Why This Design Was Chosen

Replay support is used as a **selection quality signal**, not a performance guarantee. The question it answers is: *"Was this stock's composite signal strong enough to be top-tier among peers at a prior rigorous scoring date?"*

This avoids survivorship bias: the selection was made before the outcome was known. A stock that was selected but subsequently underperformed still receives `replay_supported = True` because it reflects the quality of the signal at selection time, not the accuracy of the prediction.

The performance series (`replay_performance_series.csv`) tracks what happened to the basket after selection — but this is for reference and visualization, not for the support flag.

---

## What replay_supported Actually Measures

`replay_supported = True` means: **this symbol was ranked in the top composite quintile of its market-cap tier at a prior scoring snapshot.** It is a confirmation that the current signal is not an anomaly — the stock had strong cross-provider consensus (ESS + Zacks + Danelfin + Yahoo) at a real past date and was evaluated against real peers in a controlled peer group.

More precisely, it answers:
> "Did this stock's composite score clear the top-N bar among real-world peer competitors at a known prior date?"

---

## How replay_supported Flows Into Deployment

Once `replay_supported = True` is set on the overlay, it propagates through four downstream systems:

### 1. CW-DAS Score (+20 points)
```python
replay_c = 20.0 if replay_supported else 0.0
```
The "Replay" component of CW-DAS adds 20 points (out of a 103-point scale). This is the direct financial weight of replay evidence.

### 2. CCL Gate (required for Core Conviction Leader promotion)
```python
is_ccl = (
    signal == "BULLISH"
    and replay          # ← replay_supported must be True
    and composite >= 4.0
    and p.percent_of_portfolio >= 1.5
    and p.trim_priority_score < 30.0
)
```
No `replay_supported = True` → no CCL → no `_CCL_CONVICTION_MULT = 3.0` multiplier in the deployment planner. This is the gate that separates CCL holdings (VRT) from HCA holdings (ARW, CIEN, etc.).

### 3. Deployment Planner Weight
```python
planner_weight = cw_das_score × conviction_mult / sqrt(rank)
```
The replay bonus affects both the CW-DAS score (+20) and the conviction multiplier path (CCL vs HCA). Both amplify deployment allocation.

### 4. Conviction Narrative
`replay_supported` drives the conviction profile narrative label:
- `True` → "replay-backed" → STRONG or CORE_CONVICTION tier
- `False` → "no replay" → SIGNAL or WATCH tier

---

## Evidence Quality Spectrum

Not all `replay_supported = True` instances represent equal evidence:

| Symbol | Evidence basis | Evidence depth |
|--------|---------------|----------------|
| CIEN | HISTORICAL_VALIDATION, 252 trading days, MID-TECH basket +124.6% | **Strong** — full-year retrospective |
| VRT | CURRENT_RECOMMENDATION, 4 trading days, LARGE-ALL basket +4.7% | **Thin** — 4-day forward snapshot |
| ARW | CURRENT_RECOMMENDATION, 4 trading days, SMALL-ALL basket +4.0% | **Thin** — 4-day forward snapshot |
| CAH | HISTORICAL_VALIDATION, 252 trading days, MID-HEALTH basket +15.0% | **Strong** — full-year retrospective |
| ATLC | HISTORICAL_VALIDATION, 252 trading days, MICRO-FIN basket +13.8% | **Strong** — full-year retrospective |
| PRG | None | **None** — not selected at any snapshot |

The system treats all `replay_supported = True` as equivalent. There is no quality tier within the flag — 4 days and 252 days produce the same boolean. This is a known design simplification.

---

## The PRG Case: Why Strong Signals Can Produce No Replay Support

PRG has:
- composite score 4.722 (VERY_BULLISH, top decile)
- ESS = VERY_BULLISH
- Classification: US MICRO-cap INDUSTRIALS

Two replays exist and are AVAILABLE for PRG's tier. PRG simply did not rank in the top-20 among US MICRO-cap stocks at either snapshot date (2025-05-14 for HISTORICAL, 2026-05-20 for CURRENT).

**Interpretation:** PRG's current signal is strong but unvalidated by peer-group selection. Its composite score may have improved since the snapshot dates, or the MICRO peer group at those dates was highly competitive. The absence of replay support does not indicate weak signal quality — it indicates the signal strength was not yet historically confirmed through the peer-selection mechanism.

**Consequence:** PRG receives 0 replay points in CW-DAS, cannot qualify for CCL, and receives the "no replay" conviction narrative. This is the same treatment as a stock with a mediocre signal, even though PRG's underlying signals are strong.

---

## Summary: The Replay Evidence Model

| Concept | What it is |
|---------|-----------|
| Replay | A retrospective selection experiment: "what if we'd taken the top-N scorers in this peer group at this date?" |
| replay_supported source | `data/current/replay_inputs.csv` — single file, `selected_symbols` column |
| Selection criterion | Top-N by composite score at composite_score_snapshot_date |
| Peer group | Defined by filter_geography × filter_market_cap_bucket × filter_industry |
| replay_supported = True | Symbol was in the top-N at that date AND (if industry-specific replay) current classification still matches |
| What it measures | Past selection quality — confirmation that signal strength cleared a competitive peer bar at a real prior date |
| What it does NOT measure | Future return prediction, price performance, analyst consensus, fundamentals |
| Downstream effect | +20 CW-DAS points, CCL gate enablement, conviction tier, deployment weight |
| Evidence depth | Varies: 4 trading days (CURRENT_RECOMMENDATION) to 252 trading days (HISTORICAL_VALIDATION) — both treated identically by the boolean |
