# ISSUE-04C — UI Validation Report

**Date:** June 5, 2026  
**Run:** PAR-20260605-BC438F9E

---

## Validation Matrix

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| v25 loaded | True | True | ✅ |
| Container visible after render | True | True | ✅ |
| Panel HTML renders | True | True | ✅ |
| Title: "Dislocation Watchlist" | Match | Match | ✅ |
| Governance advisory present | "no action implied" | Confirmed | ✅ |
| Default rows (MODERATE only, no WATCH) | 5 | 5 | ✅ |
| Tier summary chips | "5 MODERATE", "17 WATCH" | Both shown | ✅ |
| PSX absent (DETERIORATING thesis → NONE) | True | True (absent) | ✅ |
| DELL absent by default (WATCH tier) | True | True (absent) | ✅ |
| LRCX absent by default (WATCH tier) | True | True (absent) | ✅ |
| Toggle "Include WATCH" exists | True | True | ✅ |
| After toggle: DELL appears | True | True | ✅ |
| After toggle: LRCX appears | True | True | ✅ |
| After toggle: PSX still absent | True | True (still absent) | ✅ |
| After toggle: total rows = 22 | 22 | 22 | ✅ |
| Row click → expansion opens | True | True | ✅ |
| Expansion shows evidence items | ≥ 2 | 4 | ✅ |
| `_disFromBackend()` HC → "HIGH CONVICTION" label | True | True | ✅ |
| `_disFromBackend()` MODERATE → "MODERATE" label | True | True | ✅ |
| `_disFromBackend()` null → "NONE" label | True | True | ✅ |
| Fundamental Snapshot uses backend (no JS recompute) | True | True | ✅ |
| DELL backend tier: WATCH | WATCH | WATCH | ✅ |
| 1,063 tests passing | True | True | ✅ |

---

## Default View (MODERATE only)

Symbols shown: AMG, FIS, ANIP, CBOE, YELP (5 MODERATE)

These 5 names have:
- ≥ 75% beat rate
- INTACT thesis
- ESS BEARISH or NEUTRAL + Danelfin < 3.0

---

## After Toggle (WATCH included)

Total rows: 22 (5 MODERATE + 17 WATCH)

WATCH tier includes: DELL, LRCX, AEIS, MU, GTX, SBS, FHI, and others with:
- ≥ 62.5% beat rate
- INTACT thesis
- Mild Danelfin divergence

---

## Governance Checks

| System | Status |
|--------|--------|
| CW-DAS scores | Unchanged |
| Deployment queue ranking | Unchanged |
| Composite scores | Unchanged |
| CRA | Unchanged |
| Fundamental Modifier | Unchanged |
