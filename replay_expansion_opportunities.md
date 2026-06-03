# Replay Expansion Opportunities
## Phase 7.6 — Coverage Review

**Reference Run:** PAR-20260531-F794D952
**Total holdings analyzed:** 81
**Replay-supported:** 46 (56.8%)
**Non-replay:** 35 (43.2%)

---

## 1. Current Coverage Summary

| Category | Count | Portfolio Weight | Notes |
|----------|-------|-----------------|-------|
| Replay-supported | 46 | ~55% (ex-cash) | Full CW-DAS Replay +20 pts |
| Non-replay, individual stocks with signal | 15 | ~14% | Analytically present; ineligible for deployment queue |
| ETF / mutual fund / structural | 16 | ~18% | No replay methodology applicable |
| Crypto / alternative | 4 | ~1% | No replay methodology applicable |
| Cash (SPAXX) | 1 | ~9% | Not applicable |

---

## 2. The Replay Absence Taxonomy

Non-replay holdings fall into three distinct buckets. Each has a different fix path.

### Bucket A — Missing Because of Methodology
These holdings lack replay support not because they have weak signals, but because the replay system methodology (cross-sector and industry replays) does not yet cover their sector, geography, or vehicle type.

**Characteristics:**
- Strong composite or ESS signal
- NOT in any replay strategy (cross-sector ALL or industry-specific)
- Likely explanation: replay inputs file does not include strategies covering their industry bucket

**Holdings in this bucket:**

| Symbol | Signal | Composite | ESS | Weight | Notes |
|--------|--------|-----------|-----|--------|-------|
| PRG | BULLISH | 4.72 | VERY_BULLISH | 0.78% | Strongest signal of any non-replay stock. Rent-A-Center/Prog Holdings. Consumer finance sector. |
| MKSI | BULLISH | 3.94 | BULLISH | 0.69% | MKS Instruments. Semiconductor equipment. Signals match replay peers (AEIS, LRCX are replay). |
| HCI | BULLISH | 3.83 | BULLISH | 0.98% | HCI Group. Property/casualty insurance specialty. No insurance replay strategy apparent. |
| LMAT | BULLISH | 3.78 | BULLISH | 1.49% | LeMaitre Vascular. Medical devices / vascular. No med-device replay visible. |
| IVZ | BULLISH | 3.61 | BULLISH | 1.53% | Invesco. Asset management. Financial sector; no AM replay strategy. |
| JBL | BULLISH | 3.61 | BULLISH | 1.31% | Jabil. Contract manufacturing/EMS. Adjacent to tech but no EMS replay. |
| FHI | BULLISH | 3.56 | BULLISH | 2.84% | Federated Hermes. Asset management. Largest-weight non-replay stock with BULLISH signal. |
| MCB | BULLISH | 3.50 | — | 0.88% | Metropolitan Commercial Bank. Community banking. No banking replay strategy. |

**Finding:** 8 stocks with BULLISH signal and composite ≥ 3.5 lack replay coverage. Their absence is most likely a **replay strategy gap** — the sectors they represent (consumer finance, insurance, asset management, community banking, medical devices, contract manufacturing) are not covered by current cross-sector or industry replay runs.

---

### Bucket B — Missing Because of Ranking
These holdings are in sectors covered by replay methodology, but did not rank in the top-N of their applicable strategy. They are known to the replay system but were outranked.

**Characteristics:**
- Sector is likely covered
- May have appeared in prior replay runs at lower percentiles
- Signal is positive but below the top-N cutoff

**Holdings in this bucket (estimated — requires replay run inspection):**

| Symbol | Signal | Composite | ESS | Weight | Notes |
|--------|--------|-----------|-----|--------|-------|
| SMR | NEUTRAL | 3.43 | — | 0.37% | NuScale Power. Nuclear energy. Energy sector replay exists. Likely ranked but outside top-N. |
| PLTR | NEUTRAL | 3.29 | — | 0.03% | Palantir. AI/data analytics. Software replay exists. Very small position. |
| NVS | NEUTRAL | 3.00 | NEUTRAL | 0.19% | Novartis. Pharma. International pharma replay may exist but NVS ranked below cutoff. |

**Finding:** 3 stocks are NEUTRAL-signal holdings that may be known to replay strategies but placed below the selection threshold. These are **not expansion candidates** under current signal strength — they would need signal upgrade first.

---

### Bucket C — Missing Because Replay Unavailable
These holdings have no replay methodology applicable. ETFs, mutual funds, cryptocurrencies, money market, and alternative vehicles cannot participate in stock-selection replay systems.

| Symbol | Type | Weight | Notes |
|--------|------|--------|-------|
| SPAXX | Money market | 9.03% | Cash — not applicable |
| VB | ETF | 3.71% | Vanguard Small-Cap. ETF aggregate. |
| VOO | ETF | 3.68% | Vanguard S&P 500. ETF aggregate. |
| DODFX | Mutual fund | 3.24% | Dodge & Cox International. Mutual fund. |
| VO | ETF | 1.80% | Vanguard Mid-Cap ETF. |
| FXAIX | Mutual fund | 1.33% | Fidelity 500 Index. |
| VXUS | ETF | 0.83% | Vanguard Total International. |
| BNDX | ETF | 0.77% | Vanguard International Bond. |
| VEA | ETF | 0.76% | Vanguard Developed Markets. |
| BND | ETF | 0.70% | Vanguard Total Bond Market. |
| FBTC | Crypto ETF | 0.44% | Fidelity Bitcoin. |
| VWO | ETF | 0.32% | Vanguard Emerging Markets. |
| FIGFX | Mutual fund | 0.26% | Fidelity International Growth. |
| FETH | Crypto ETF | 0.24% | Fidelity Ethereum. |
| FMCSX | Mutual fund | 0.16% | Fidelity Mid Cap Stock. |
| TTNDY | ADR/Intl | 0.11% | Toto Ltd. International. No replay coverage for Japanese ADR. |
| FCPGX | Mutual fund | 0.04% | Fidelity Capital Appreciation. |
| XRP | Crypto | 0.02% | Ripple. Crypto — not applicable. |
| FSOL | Crypto | 0.02% | Fidelity Solana ETF. |
| M26CNT069 | Unknown | 0.00% | Unclassified vehicle. |

**Finding:** 20 holdings (~18% of portfolio weight) are structurally ineligible for replay. This is expected and not a gap.

---

## 3. Weak-Signal Non-Replay (Active Holdings to Monitor)

These are individual stocks with negative or weak signals that lack replay support. They do not qualify for expansion — they qualify for TRIM_WATCH under the UCF.

| Symbol | Signal | Composite | ESS | Weight | UCF Label |
|--------|--------|-----------|-----|--------|-----------|
| PRIM | BEARISH | 2.06 | BEARISH | ~0.3% | TRIM_WATCH |
| KGC | NEUTRAL | 2.61 | BEARISH | ~0.5% | TRIM_WATCH |
| AMG | NEUTRAL | 2.94 | NEUTRAL | ~0.5% | MAINTAIN or TRIM_WATCH |
| FIS | NEUTRAL | 2.83 | NEUTRAL | ~0.5% | MAINTAIN |

---

## 4. Potential Replay Expansion Candidates

These are the holdings most likely to benefit from an expansion of replay strategies to cover their sectors.

**Priority ranking:**

| Rank | Symbol | Signal | Composite | ESS | Weight | Sector Gap | Rationale |
|------|--------|--------|-----------|-----|--------|------------|-----------|
| 1 | PRG | BULLISH | 4.72 | VERY_BULLISH | 0.78% | Consumer Finance | Strongest non-replay signal in portfolio. Would become CCL if replay added. |
| 2 | FHI | BULLISH | 3.56 | BULLISH | 2.84% | Asset Management | Largest-weight non-replay BULLISH stock. Significant deployment queue impact. |
| 3 | MKSI | BULLISH | 3.94 | BULLISH | 0.69% | Semiconductor Equipment | Same sector as AEIS, LRCX (both replay). Appears to be a ranking gap. |
| 4 | LMAT | BULLISH | 3.78 | BULLISH | 1.49% | Medical Devices | Strong signals across providers. Methodology gap in med-device sector. |
| 5 | IVZ | BULLISH | 3.61 | BULLISH | 1.53% | Asset Management | Same sector as FHI. An asset management replay strategy would capture both. |
| 6 | JBL | BULLISH | 3.61 | BULLISH | 1.31% | Contract Manufacturing | Strong signals. EMS/contract manufacturing replay strategy absent. |
| 7 | HCI | BULLISH | 3.83 | BULLISH | 0.98% | Insurance (Specialty P&C) | Specialty insurance niche; no P&C insurance replay strategy. |
| 8 | MCB | BULLISH | 3.50 | — | 0.88% | Community Banking | ESS absent. Community banking replay strategy would validate signal. |

---

## 5. Impact Modeling

If the 8 Bucket A stocks gained replay support (assuming composite and signals unchanged):

| Stock | Current CW-DAS (approx, no replay) | Projected CW-DAS (with replay) | Change |
|-------|--------------------------------------|----------------------------------|--------|
| PRG | Not in queue (not eligible — tier?) | Would need tier check | Tier upgrade possible |
| FHI | ~55–60 (HCA-eligible, no replay) | ~75–80 | +20 pts Replay component |
| MKSI | ~55–65 | ~75–85 | +20 pts |
| LMAT | ~55–65 | ~75–80 | +20 pts |
| IVZ | ~50–60 | ~70–75 | +20 pts |
| JBL | ~50–60 | ~70–75 | +20 pts |

> Note: Exact scores depend on tier assignment and whether replay addition triggers CCL gates. This is an approximation — actual scores would be computed by the engine.

**Portfolio-level impact:** Replay expansion covering Asset Management + Semiconductor Equipment + Medical Devices + Insurance would increase replay coverage from 56.8% to approximately 65–68% of holdings and 60–65% of portfolio weight.

---

## 6. Replay Methodology Gap Summary

| Sector / Category | Current Coverage | Gap |
|-------------------|-----------------|-----|
| US Large-Cap (S&P 500) | ✅ Covered via cross-sector ALL | — |
| Semiconductor Equipment | ✅ Covered (AEIS, LRCX) | MKSI appears to be a ranking miss — review top-N |
| Asset Management | ❌ Not covered | FHI, IVZ are strong candidates — create AM replay strategy |
| Consumer Finance / Specialty Lending | ❌ Not covered | PRG (VERY_BULLISH) — highest-signal miss |
| Medical Devices / Vascular | ❌ Not covered | LMAT — strong signals, no methodology |
| Insurance (Specialty P&C) | ❌ Not covered | HCI — strong signals, niche sector |
| Community Banking | ❌ Not covered | MCB — weak ESS coverage but BULLISH composite |
| Contract Manufacturing (EMS) | ❌ Not covered | JBL — adjacent to tech; consider adding to tech replay |
| Nuclear / Alternative Energy | ⚠ Partial | SMR — energy sector may exist; ranking issue |
| International ADR (Japan) | ❌ Not covered | TTNDY — ETF/ADR structure complicates replay |

---

## 7. Recommended Actions (Design Only — No Implementation)

> These are observations for future replay strategy work. No code changes in Phase 7.6.

1. **Asset Management replay strategy** — Cover FHI, IVZ and their AM sector peers. Both have BULLISH ESS and composite ≥ 3.5. This is the highest-impact single strategy addition by portfolio weight.

2. **Consumer Finance replay strategy** — PRG (PRG Holdings) has VERY_BULLISH ESS at 4.72 composite. This is the strongest-signal non-replay stock in the portfolio. If a consumer finance replay were added and PRG topped the ranking, it would become a deployment candidate immediately.

3. **Review semiconductor equipment top-N** — MKSI (composite=3.94, BULLISH) exists in the same sector as AEIS and LRCX which are replay-supported. It is possible MKSI ranked just below the top-N cutoff in a semiconductor equipment replay. Reviewing the cutoff threshold for this strategy may surface it.

4. **Medical devices replay strategy** — LMAT (1.49% weight, BULLISH ESS) represents an orphaned position. A medical devices or healthcare equipment replay strategy would provide conviction backing.

5. **Do not expand replay for ETFs/funds** — The 20 holdings in Bucket C are not expansion candidates. Expanding replay methodology to cover ETF aggregates would produce misleading conviction signals.

6. **KGC and PRIM — signal review** — These non-replay stocks have BEARISH ESS signals. Before creating a replay strategy to cover their sectors (gold mining, construction), confirm whether the signal weakness reflects a genuine exit case or a temporary dislocation.
