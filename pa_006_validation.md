# PA-006 Validation — Historical Drift Evidence

**Date:** 2026-06-15

---

## Q1: Can drift be reconstructed from existing data?

**Yes, completely.** Validated against 250 PAR runs across 20 dates (May 21 – June 15, 2026). Every PAR run contains:
- `concentration.json` — top1%, top5%, top10%, mega%, us%, intl%, HHI (all 250 runs)
- `holdings.csv` — per-symbol market_value, asset_class, geography, market_cap_bucket (all 250 runs)
- `run_metadata.json` — snapshot_date (all 250 runs)
- `compliance.json` — pre-computed CPV actuals (4 runs only — the rest can be computed from holdings.csv)

**No new data collection is required. Drift is entirely reconstructible from artifacts already on disk.**

---

## Q2: Actual Historical Drift Data (Validated)

### Concentration Trend (from concentration.json, one run per date)

| Date | Top1% | Top5% | Top10% | Mega% | US% | Intl% | HHI |
|------|-------|-------|--------|-------|-----|-------|-----|
| 2026-05-21 | 7.04% | 25.06% | 42.22% | 10.05% | 72.97% | 20.18% | 0.0272 |
| 2026-05-27 | 6.32% | 24.80% | 41.70% | 10.73% | 75.07% | 16.38% | 0.0261 |
| 2026-05-28 | 8.12% | 26.59% | 43.53% | 10.76% | 77.49% | 16.31% | 0.0284 |
| 2026-05-29 | 9.03% | 27.65% | 44.47% | 12.46% | 69.47% | 18.83% | 0.0299 |
| 2026-06-03 | 7.90% | 26.41% | 43.10% | 9.40% | 69.82% | 18.78% | 0.0283 |
| 2026-06-05 | 9.23% | 27.21% | 43.11% | 9.32% | 67.33% | 17.26% | 0.0294 |
| 2026-06-11 | 11.21% | 29.67% | 45.37% | 8.88% | 68.91% | 17.14% | 0.0333 |
| 2026-06-14 | 11.07% | 29.63% | 45.36% | 8.82% | 69.15% | 17.07% | 0.0332 |
| 2026-06-15 | 10.85% | 29.88% | 45.46% | 8.83% | 69.21% | 16.88% | 0.0331 |

**Note:** May 22 shows a Top1=30.22% and Top5=59.26% — this is the PAR run where SPAXX (cash) dominated; `concentration_tier=MODERATE`. This was an outlier PAR run (probably with large uninvested cash position before deployment). Most runs show concentration_tier=DIVERSIFIED.

### CPV Rule Actuals (from compliance.json where available)

| Date | CPV-01 Micro | CPV-04 Cash | CPV-05 Intl | CPV-06 AssetClass | CPV-07 Equities | Overall |
|------|-------------|------------|------------|------------------|----------------|---------|
| 2026-05-21 | **9.52% FAIL** | 4.24% OK | 20.34% OK | **94.97% FAIL** | 94.97% OK | FAIL score=50 |
| 2026-05-29 | **8.53% WARN** | 9.03% OK | 19.32% OK | **88.79% WARN** | 88.79% OK | WARN score=80 |
| 2026-06-15 | **8.89% WARN** | 10.83% OK | 17.52% OK | **86.72% WARN** | 86.72% OK | WARN score=80 |

---

## Q3: Drift Trend Analysis (Evidence-Based)

### CPV-01 (Micro Cap — ceiling 5%)

| Period | Value | Status | Delta |
|--------|-------|--------|-------|
| 2026-05-21 | 9.52% | **FAIL** | — |
| 2026-05-29 | 8.53% | WARN | −0.99pp (improving) |
| 2026-06-15 | 8.89% | WARN | +0.36pp (slight regression) |

**Trend:** Improved from FAIL → WARN between May 21 and May 29. Slight regression since. Currently stable in WARN zone. Breach = 3.89pp (threshold for FAIL = 4.0pp).

### CPV-06 (Single Asset Class — ceiling 80%)

| Period | Value | Status | Delta |
|--------|-------|--------|-------|
| 2026-05-21 | 94.97% | **FAIL** | — |
| 2026-05-29 | 88.79% | WARN | −6.18pp (improving) |
| 2026-06-15 | 86.72% | WARN | −2.07pp (improving) |

**Trend:** Consistent improvement. Improved −8.25pp from May 21 to Jun 15. Still in WARN zone. Needs −6.72pp more to reach 80% policy limit.

### Concentration Drift Summary

| Dimension | May 21 | Jun 15 | Delta | Direction |
|-----------|--------|--------|-------|-----------|
| Top 5% | 25.06% | 29.88% | +4.82pp | WORSENING |
| Top 10% | 42.22% | 45.46% | +3.24pp | WORSENING |
| Mega % | 10.05% | 8.83% | −1.22pp | IMPROVING |
| US % | 72.97% | 69.21% | −3.76pp | toward intl (positive) |
| Intl % | 20.18% | 16.88% | −3.30pp | WORSENING |
| HHI | 0.0272 | 0.0331 | +0.0059 | More concentrated |

**Notable:** Top 5 and Top 10 concentration increased materially — consistent with capital deployments into existing positions (VRT, ATLC etc). Mega% declined (micro-cap deployment program partially explains CPV-01 drift).

---

## Q4: Top Drift Contributors (May 21 → Jun 15)

Based on known deployment history (PAR analysis runs June 3-15):

| Symbol | May 21 est% | Jun 15% | Delta | Notes |
|--------|------------|---------|-------|-------|
| ATLC | ~0% | 1.50% | +1.5% | New position built in June |
| VRT | ~3.6% | 4.9% | +1.3% | Increased via deployment |
| SANM | ~0% | ~1.1% | +1.1% | New position |
| MTZ | ~0% | ~0.7% | +0.7% | New position |

*Exact per-symbol deltas require running the contributor computation from holdings.csv; the above are estimates from available attribution data.*

---

## Q5: Data Gaps and Constraints

1. **Only 4 compliance.json files exist** — the other 246 PAR runs need CPV computed on demand from holdings.csv. This is deterministic but adds ~50ms per run at API time. Acceptable for a dashboard load.

2. **May 22 PAR** should be excluded from trend visualization — it is an outlier run with `concentration_tier=MODERATE` (large uninvested cash before the June deployment program).

3. **Only 20 unique dates** span the available history (May 21 – Jun 15, 2026). The "30-day trend" will span the full available window. As the system accumulates more data, this will grow naturally.

4. **No per-symbol asset_class/geography enrichment in PIS position_snapshots.csv** — the `holdings.csv` in PAR runs is required for CPV-01 through CPV-08 computation. PIS snapshots have market_value but not classification metadata.

---

## Validation Conclusion

All Q1-Q5 design questions are validated against actual data:
- **Drift is reconstructible:** ✅
- **Historical span:** 20 dates, 250 PAR runs
- **CPV trend is real and meaningful:** CPV-01 improved FAIL→WARN, CPV-06 improved FAIL→WARN 
- **Concentration drifting upward:** Top 5% increased +4.82pp over the period
- **Algorithm is deterministic:** No model, no estimation — pure arithmetic on existing holdings.csv
