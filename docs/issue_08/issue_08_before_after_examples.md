# ISSUE-08 — Before / After Examples

**Date:** June 5, 2026

---

## The Problem It Solved

Analyst consensus had a two-tier quality gap:

| Display | Before ISSUE-08 | After ISSUE-08 |
|---------|----------------|----------------|
| ABR value | 1.78 | 1.78 (unchanged) |
| Consensus label | BUY | BUY (unchanged) |
| Price target | $483.83 | $483.83 (unchanged) |
| Upside | +20.6% | +22.7% (updated with fresh fetch) |
| **Analyst count** | **— (always null)** | **23 analysts** ✅ |
| Sourced date | 2026-06-05 | 2026-06-05 (unchanged) |

The analyst count gap meant operators could not distinguish thin consensus (2–3 analysts) from broad consensus (35–58 analysts). Without this context, all BUY ratings looked equivalent regardless of how many independent analysts contributed to them.

---

## Key Examples

### DELL — High coverage, meaningful consensus

```
BUY  |  ABR 1.78  |  Target $483.83  |  Upside +22.7%  |  23 analysts
```
23 analysts is a meaningful sample. The BUY consensus is well-grounded.

### NVDA — Very high coverage

```
STRONG BUY  |  ABR 1.38  |  Target $298.07  |  Upside +45.3%  |  58 analysts
```
58 analysts is exceptional coverage. The STRONG BUY consensus from this many independent models carries substantial weight.

### PCB — Thin coverage

```
(no ABR)  |  Target $26.00  |  Upside (positive)  |  2 analysts
```
2 analysts. This "consensus" is essentially irrelevant for conviction purposes. Before ISSUE-08, there was no way to distinguish PCB from DELL in the analyst count display — both showed nothing.

### SANM — Moderate coverage, no ABR

```
(no ABR)  |  Target $212.25  |  4 analysts
```
4 analysts. Some coverage, but ABR is unavailable (not enough participating brokers).

---

## Why Analyst Count Matters for CII

CII Layer 1 uses analyst consensus as a primary signal (55% weight via ESS, plus ABR direction). The ESS aggregates thousands of model inputs. The ABR aggregates analyst recommendations.

Displaying analyst count alongside ABR completes the context:
- High count → consensus is stable, institutionally visible, harder to revise
- Low count → consensus is fragile, one analyst flip can move the mean
- This is not a scoring input — it is interpretive intelligence for the operator

---

## CSV Comparison

`latest_yahoo_supplemental.csv` header:

**Before:**
```
symbol,price_target,abr,eps_growth_5yr,current_price,upside_pct,sourced_date
```

**After:**
```
symbol,price_target,abr,analyst_count,eps_growth_5yr,current_price,upside_pct,sourced_date
```

New column `analyst_count` is in position 4 (after `abr`). The column is an integer string or blank (not "None").
