# PERF-VAL-01 Performance Validation Results

Generated at: 2026-06-17T11:43:19.884406Z

## Scope
- Validation target: Fidelity-reported 1-year portfolio and benchmark return
- SIH data window used for direct portfolio reconstruction
  - Start: 2026-05-21
  - End: 2026-06-16
  - Calendar span: 26 days
  - Snapshot count: 20

## Part C - Independent Return Calculation
- Beginning value: $457,264.19
- Ending value: $483,021.29
- Net flows (observed ledger): $0.00
- Income (observed ledger): $0.00
- SIH return (window): 5.63%
- SIH 1-year return: N/A (insufficient 1-year holdings/flow history)

## Part D - Benchmark Validation
### 1-Year Benchmarks
| Benchmark | Fidelity | SIH | Variance |
|---|---:|---:|---:|
| S&P 500 (^GSPC) | 27.95% | 24.50% | -3.45% |
| Dow Jones Total Market (^DWCF) | N/A | 24.82% | N/A |
| MSCI ACWI ex USA (ACWX) | N/A | 30.86% | N/A |
| Bloomberg Aggregate Bond (AGG) | N/A | 5.31% | N/A |
| Bloomberg Municipal Bond (MUB) | N/A | 6.43% | N/A |

### SIH Available-Window Benchmarks
| Benchmark | SIH Window Return |
|---|---:|
| S&P 500 (^GSPC) | 0.88% |
| Dow Jones Total Market (^DWCF) | 1.27% |
| MSCI ACWI ex USA (ACWX) | 2.63% |
| Bloomberg Aggregate Bond (AGG) | 0.98% |
| Bloomberg Municipal Bond (MUB) | 1.29% |

## Part E - Variance Analysis
- Fidelity portfolio 1Y: 48.73%
- SIH portfolio 1Y: N/A
- Portfolio variance vs Fidelity: N/A
- Variance confidence: HIGH
- Root-cause assessment:
  - SIH canonical holdings history is shorter than 1 year (starts 2026-05-21).
  - No explicit transaction ledger for deposits/withdrawals/dividends/distributions is available in current SIH dataset.
  - Cash and pending-activity treatment can differ between Fidelity UI calculations and SIH snapshot-based reconstruction.
  - Benchmark data persisted in repository is placeholder/incomplete; online benchmark fetch is required for practical comparison.

## Part F - Alpha Validation
- Fidelity apparent alpha (portfolio - S&P 500): 20.78%
- SIH apparent alpha (window, portfolio - S&P 500): 4.75%
- SIH 1Y alpha: N/A (depends on unavailable SIH 1Y portfolio return)

## Part G - Dashboard Readiness
- Readiness: NOT READY
- Evidence: SIH can compute short-window portfolio/benchmark returns but cannot independently reproduce Fidelity 1Y performance without full 1-year holdings + flow ledger.

## Required Questions (Q1-Q10)
- Q1: Partially. SIH independently calculates return across available canonical history (not full 1Y).
- Q2: No. SIH cannot credibly reproduce Fidelity 48.73% 1Y yet due insufficient 1Y history and missing flow ledger.
- Q3: Yes. SIH can independently calculate benchmark returns via market data (with ticker proxies/fallbacks).
- Q4: Yes. Variance is explainable by methodology and missing data (flows, timing, cash treatment, incomplete benchmark persistence).
- Q5: Not yet for full attribution quality. Data is sufficient for short-window attribution, insufficient for 1Y-grade attribution.
- Q6: NOT READY for PERF-ATTRIB-03 as a full 1Y alpha decomposition initiative.
- Q7: NOT READY for PERF-VAL-02 benchmark reconciliation as an audited 1Y workflow.
- Q8: NO.
- Q9: NO.
- Q10: No. Next priority should be data foundation hardening (transaction and benchmark history completeness) before PERF-ATTRIB-03.

## Governance
- Recommendation algorithms modified: NO
- Scoring algorithms modified: NO
