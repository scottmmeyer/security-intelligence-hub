# Holdings Coverage Reconciliation

- Audit date: 2026-06-12
- Holdings baseline: PAR-20260529-33B7DB0B (`asset_class = EQUITIES`) = 74 symbols

## Q1. Are all current portfolio holdings being submitted to refresh?

| Provider | Submitted | Skipped | Holdings Denominator |
|---|---:|---:|---:|
| Zacks | 34 | 40 | 74 |
| Danelfin | 34 | 40 | 74 |
| Yahoo | 34 | 40 | 74 |

Verdict: No. All three providers show 34 submitted / 40 skipped for the current holdings baseline.

## Denominator and Set Reconciliation

| Set | Count | Notes |
|---|---:|---|
| UI holdings set (latest PAR by mtime: PAR-20260529-33B7DB0B) | 74 | Used by current portfolio analysis context |
| Refresh forced set (`_load_portfolio_equity_holdings`) | 71 | Uses latest `PAR-2*` by lexicographic date, not mtime |
| Difference (UI holdings not in forced set) | 3 | FIGFX, VEA, VXUS |
| Missing from merged smart set (against forced set) | 0 | Always 0 by construction once merged |
| Missing from merged smart set (against UI holdings) | 3 | FIGFX, VEA, VXUS |

Interpretation:
- The prior “0 missing from merged smart refresh set” claim is true only against the 71-symbol forced set used by refresh list construction.
- The active portfolio analysis context is based on a 74-symbol holdings set from the latest PAR by modification time.
- Three holdings (FIGFX, VEA, VXUS) are not in the forced set, so they cannot be guaranteed by that governance check.
