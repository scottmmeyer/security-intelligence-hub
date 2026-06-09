# RC-02 Regression Validation

**Date:** 2026-06-09

---

## Regression Outcome

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| Full test suite (pytest) | 1192 | 1 | **0** |

No regressions introduced by the classification fix.

---

## Change Scope Verification

| System Component | Changed? |
|---|---|
| ESS signal generation | No |
| Scoring (composite, zacks, danelfin) | No |
| Recommendation generation logic | No |
| Policy engine | No |
| CW-DAS / deployment queue | No |
| STI (strategic trim intelligence) | No |
| Replay engine | No |
| Reconciliation check logic | No |
| Enrichment pipeline logic (enrich_holdings) | No (table data only) |
| `_ETF_OVERRIDES` table | **Yes** — 3 entries added |

---

## Classification-Specific Tests

The existing test suite includes tests for:
- `test_enrichment.py` — enrichment pipeline (verifies _ETF_OVERRIDES lookup)
- `test_reconciliation.py` — RC-02 and all reconciliation checks

All pass after the fix.

---

## Behavioral Delta

The only behavioral change is classification enrichment for BSVN, STNG, and SIMO:
- These holdings are now enriched with asset_class/geography/market_cap_bucket/sector
- They now contribute to their respective L1 allocation nodes
- Allocation alignment computation now includes these holdings
- RC-02 passes; the reconciliation panel in the UI no longer shows a FAIL

No other observable behavioral differences between pre-fix and post-fix PAR runs.
