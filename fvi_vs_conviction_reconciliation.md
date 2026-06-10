# ETF-CONVICTION-01: FVI vs. Conviction Reconciliation

**Date:** 2026-06-10

---

## The Apparent Contradiction

```
VOO in Reduction Queue:
  Reason:   Low Conviction
  Priority: Moderate
  FVI Tier: ELITE
```

An operator seeing this may conclude:
1. The system recommends selling VOO because VOO is a bad investment → **INCORRECT**
2. The system recommends selling VOO because the portfolio has a better use for the capital → **CORRECT**
3. There's a bug where FVI is inconsistent with conviction → **INCORRECT (no bug)**

---

## Two Independent Measurement Dimensions

The SIH measures two entirely separate concepts that should not be compared directly:

### Dimension 1: Fund Vehicle Intelligence (FVI)

**Source:** `config/fvi_peer_groups.yaml` + `src/portfolio/fvi_loader.py`

**Question answered:** "If you need to gain exposure to this asset class/theme, which vehicle is best?"

**ELITE** means: Best-in-class implementation efficiency — lowest cost, best liquidity, strongest tracking, deepest market depth. VOO is ELITE because it is the Vanguard S&P 500 ETF with $500B+ AUM, near-zero expense ratio, and tight spreads.

**FVI does NOT measure:**
- Whether you should hold this asset class at all
- Whether this vehicle fits your current mandate sizing
- Whether direct stocks outperform passive exposure under a Concentrated Alpha mandate

### Dimension 2: Conviction Level (LOW_CONVICTION_REDUCTION)

**Source:** `src/portfolio/cra/capital_source_builder.py`

**Question answered:** "Does the SIH conviction engine have evidence to retain this specific position with high conviction under the Concentrated Alpha mandate?"

**LOW_CONVICTION_REDUCTION** means: The engine has no individual ESS signal, no replay evidence, and no buy thesis for this specific holding. Under the Concentrated Alpha mandate — which favors direct-ownership alpha over passive exposure — this position has lower strategic priority than a direct-conviction equity holding.

**LOW_CONVICTION does NOT mean:**
- This is a bad fund
- This fund has underperformed
- You should always sell this
- VOO is riskier than alternatives

---

## Reconciliation: Both Are Correct Simultaneously

| Statement | Source | Correct? |
|---|---|---|
| "VOO is an elite fund vehicle" | FVI | ✓ YES |
| "VOO has low individual conviction under the Concentrated Alpha mandate" | CRA Cat 5 | ✓ YES |
| "VOO is a bad investment" | Operator misinterpretation | ✗ NO |
| "VOO should be sold immediately" | CRA rank / priority | ✗ NO (Moderate priority, low sizing 25%) |

The two systems speak to different questions. An operator who understands this will correctly interpret:

> "FVI says VOO is ELITE — so if I do reduce it, I should redeploy into another vehicle of similar quality (or into high-conviction direct positions like VRT/ARW). The reduction isn't because VOO is bad, it's because the capital has higher-conviction uses available."

---

## Where the Semantic Tension Is Created

The current Reduction Queue label "Low Conviction" creates tension because:

1. It sounds like a judgment about the **investment quality** of VOO
2. It appears alongside an FVI badge saying "ELITE" — which sounds like a quality endorsement
3. The operator may not understand that these two signals live in orthogonal dimensions

The tension is a **labeling problem, not a data or logic problem.**

---

## Correct Framing for Each ETF Category

| CRA Category | Current Label | What It Really Means |
|---|---|---|
| LOW_CONVICTION_REDUCTION | "Low Conviction" | "No individual alpha thesis; passive exposure; opportunity cost under Concentrated Alpha mandate" |
| OVERWEIGHT_REDUCTION | "Overweight Reduction" | "Allocation node is overweight vs mandate target; regardless of quality, sizing needs adjustment" |
| TAX_AWARE_EXIT | "Tax-Aware Exit" | "Unrealized loss creates tax harvesting opportunity; reduction may be net-positive after tax" |
| SIGNAL_DETERIORATION | "Signal Deterioration" | "ESS bearish/deteriorating; conviction has weakened; priority reduction candidate" |

---

## Portfolio Construction Philosophy Statement

The SIH is expressing **Statement B**:

> "VOO is a high-quality vehicle but a lower-conviction expression than direct ownership of top-ranked securities under the Concentrated Alpha mandate."

**Evidence:**
1. FVI = ELITE confirms vehicle quality is acknowledged
2. CRA priority = MODERATE (not URGENT/HIGH) — not a distress sell
3. CRA sizing = 25% (not 100%) — partial reduction only; system is not recommending full exit
4. The capital source evidence string reads: "HOLD flag | no replay support | opportunity cost position" — the term "opportunity cost" explicitly frames this as a capital opportunity decision, not a conviction failure
5. DQ ineligibility is a mandate alignment issue (ETFs vs. direct securities under Concentrated Alpha), not a quality judgment

---

## System Design Intent (as documented in code)

From `capital_source_builder.py` docstring:
> "5. LOW_CONVICTION_REDUCTION — HOLD flag, no replay, above de minimis threshold"

From `trim_intelligence.py`:
> "ETF_INHERITED — broad index fund; exposure is incidental, not intentional"

The code correctly distinguishes ETF_INHERITED exposure from DIRECT_INTENTIONAL conviction. The issue is that the operator-facing label fails to communicate this distinction.
