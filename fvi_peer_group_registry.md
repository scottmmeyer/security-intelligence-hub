# FVI Peer Group Registry

Repository: security-intelligence-hub  
Date: 2026-06-09  
Reference PAR: PAR-20260609-42A90186

## Purpose

This registry maps every fund vehicle currently held in the portfolio to its canonical peer group for FVI evaluation. Peer group assignment determines which comparable vehicles are used to calculate relative quality percentiles.

---

## Equity Fund Vehicles

### DODFX — Dodge & Cox International Stock

| Field | Value |
|---|---|
| Vehicle type | Mutual Fund (no-load after initial purchase) |
| Asset class | EQUITIES.INTERNATIONAL.LARGE |
| Market cap | LARGE |
| Morningstar category equivalent | Foreign Large Value |
| SIH category | EQUITIES.INTERNATIONAL.LARGE |
| Load status | Front-end load already paid (Dodge & Cox I shares are no-load; Class I) |
| FVI peer universe | Foreign Large Value mutual funds (active and passive) |
| Primary comparator tier | Style-consistent: Foreign Large Value |
| Secondary comparator | International Large Blend (broader reference) |
| Portfolio weight | 3.21% ($14,910) |

### VOO — Vanguard S&P 500 ETF

| Field | Value |
|---|---|
| Vehicle type | ETF |
| Asset class | EQUITIES.US.MEGA |
| Market cap | MEGA |
| Morningstar category equivalent | US Large Blend |
| SIH category | EQUITIES.US.MEGA |
| FVI peer universe | US Large Blend ETFs (index-tracking) |
| Primary comparator | SPY, IVV, SCHB, SPLG |
| Portfolio weight | 3.65% ($16,992) |

### VB — Vanguard Small-Cap ETF

| Field | Value |
|---|---|
| Vehicle type | ETF |
| Asset class | EQUITIES.US.SMALL |
| Morningstar category equivalent | US Small Blend |
| SIH category | EQUITIES.US.SMALL |
| FVI peer universe | US Small Blend ETFs (index-tracking) |
| Primary comparator | IWM, SCHA, VXF |
| Portfolio weight | 3.73% ($17,362) |

### VO — Vanguard Mid-Cap ETF

| Field | Value |
|---|---|
| Vehicle type | ETF |
| Asset class | EQUITIES.US.MID |
| Morningstar category equivalent | US Mid Blend |
| SIH category | EQUITIES.US.MID |
| FVI peer universe | US Mid Blend ETFs |
| Primary comparator | IJH, SCHM, MDY |
| Portfolio weight | 1.82% ($8,478) |

### FXAIX — Fidelity 500 Index Fund

| Field | Value |
|---|---|
| Vehicle type | Mutual Fund (index) |
| Asset class | EQUITIES.US.MEGA |
| Morningstar category equivalent | US Large Blend |
| SIH category | EQUITIES.US.MEGA |
| FVI peer universe | US Large Blend (mutual fund share class comparison) |
| Primary comparator | VOO, VFINX equivalent share classes |
| Portfolio weight | 1.32% ($6,149) |

### VEA — Vanguard Developed Markets ETF

| Field | Value |
|---|---|
| Vehicle type | ETF |
| Asset class | EQUITIES.INTERNATIONAL.LARGE |
| Morningstar category equivalent | Foreign Large Blend |
| SIH category | EQUITIES.INTERNATIONAL.LARGE |
| FVI peer universe | Foreign Large Blend ETFs |
| Primary comparator | EFA, IEFA, SCHF |
| Portfolio weight | 0.75% ($3,493) |

### VWO — Vanguard FTSE Emerging Markets ETF

| Field | Value |
|---|---|
| Vehicle type | ETF |
| Asset class | EQUITIES.EMERGING_MARKETS |
| Morningstar category equivalent | Diversified Emerging Markets |
| SIH category | EQUITIES.EMERGING_MARKETS |
| FVI peer universe | Diversified Emerging Markets ETFs |
| Primary comparator | EEM, IEMG, SCHE |
| Portfolio weight | 0.63% ($2,917) |

### FMCSX — Fidelity Mid Cap Stock Fund

| Field | Value |
|---|---|
| Vehicle type | Mutual Fund (active) |
| Asset class | EQUITIES.US.MID |
| Morningstar category equivalent | US Mid Cap Growth (or Blend) |
| SIH category | EQUITIES.US.MID |
| FVI peer universe | US Mid Blend/Growth mutual funds |
| Portfolio weight | 0.16% ($745) |

### FCPGX — Fidelity Small Cap Growth Fund

| Field | Value |
|---|---|
| Vehicle type | Mutual Fund (active) |
| Asset class | EQUITIES.US.SMALL |
| Morningstar category equivalent | US Small Growth |
| SIH category | EQUITIES.US.SMALL |
| FVI peer universe | US Small Growth mutual funds |
| Portfolio weight | 0.04% ($197) |

### FIGFX — Fidelity International Growth Fund

| Field | Value |
|---|---|
| Vehicle type | Mutual Fund (active) |
| Asset class | EQUITIES.INTERNATIONAL.LARGE |
| Morningstar category equivalent | Foreign Large Growth |
| SIH category | EQUITIES.INTERNATIONAL.LARGE |
| FVI peer universe | Foreign Large Growth mutual funds |
| Portfolio weight | Not in current PAR (may be archived) |

### TTNDY — Techtronic Industries ADR

| Field | Value |
|---|---|
| Vehicle type | ADR / Individual Equity |
| Classification | Not a fund vehicle — excluded from FVI |
| Portfolio weight | 0.11% ($524) |

---

## Fixed Income Fund Vehicles

### BND — Vanguard Total Bond Market ETF

| Field | Value |
|---|---|
| Vehicle type | ETF |
| Asset class | FIXED_INCOME.US |
| Morningstar category equivalent | US Intermediate Core Bond |
| FVI peer universe | US Core Bond ETFs |
| Primary comparator | AGG, IUSB, SCHZ |
| Portfolio weight | 0.70% ($3,276) |

### BNDX — Vanguard Total International Bond ETF

| Field | Value |
|---|---|
| Vehicle type | ETF |
| Asset class | FIXED_INCOME.INTERNATIONAL |
| Morningstar category equivalent | World Bond |
| FVI peer universe | World Bond ETFs (currency-hedged) |
| Primary comparator | IAGG, BWX |
| Portfolio weight | 0.77% ($3,596) |

---

## Digital Asset Fund Vehicles

### FBTC — Fidelity Wise Origin Bitcoin Fund

| Field | Value |
|---|---|
| Vehicle type | Digital Asset ETF |
| Asset class | DIGITAL.BITCOIN |
| Morningstar category equivalent | Cryptocurrency (Bitcoin Spot ETF) |
| FVI peer universe | Bitcoin spot ETFs |
| Primary comparator | IBIT, BITB, ARKB |
| Portfolio weight | 0.39% ($1,795) |

### FETH — Fidelity Ethereum Fund

| Field | Value |
|---|---|
| Vehicle type | Digital Asset ETF |
| Asset class | DIGITAL.ETHEREUM |
| FVI peer universe | Ethereum spot ETFs |
| Primary comparator | ETHA, CETH |
| Portfolio weight | 0.21% ($975) |

### FSOL — Fidelity Solana Fund

| Field | Value |
|---|---|
| Vehicle type | Digital Asset ETF |
| Asset class | DIGITAL.OTHER |
| FVI peer universe | Solana/Altcoin digital asset products |
| Portfolio weight | 0.02% ($80) |

### XRP — Bitwise XRP ETF

| Field | Value |
|---|---|
| Vehicle type | Digital Asset ETF |
| Asset class | DIGITAL.OTHER |
| FVI peer universe | XRP/Altcoin digital asset ETFs |
| Portfolio weight | 0.02% ($92) |

---

## Cash Equivalent

### SPAXX — Fidelity Government Money Market

| Field | Value |
|---|---|
| Vehicle type | Money Market / Cash Equivalent |
| FVI applicable | No — evaluated as cash position, not a fund vehicle |
| Portfolio weight | 11.67% ($54,258) |

---

## Fund Registry Summary

| Symbol | Vehicle Type | FVI Category | Weight |
|---|---|---|---|
| DODFX | Mutual Fund (active) | Foreign Large Value | 3.21% |
| VB | ETF (index) | US Small Blend | 3.73% |
| VOO | ETF (index) | US Large Blend | 3.65% |
| VO | ETF (index) | US Mid Blend | 1.82% |
| FXAIX | Mutual Fund (index) | US Large Blend | 1.32% |
| BNDX | ETF (index) | World Bond | 0.77% |
| VEA | ETF (index) | Foreign Large Blend | 0.75% |
| BND | ETF (index) | US Core Bond | 0.70% |
| VWO | ETF (index) | Diversified EM | 0.63% |
| FBTC | Digital Asset ETF | Bitcoin Spot | 0.39% |
| FETH | Digital Asset ETF | Ethereum Spot | 0.21% |
| FMCSX | Mutual Fund (active) | US Mid Blend | 0.16% |
| FCPGX | Mutual Fund (active) | US Small Growth | 0.04% |
| XRP | Digital Asset ETF | XRP | 0.02% |
| FSOL | Digital Asset ETF | Solana | 0.02% |
| SPAXX | Money Market | Cash (not FVI) | 11.67% |
