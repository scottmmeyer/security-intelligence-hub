# ESS Coverage Validation

**Date:** 2026-06-15  
**Scope:** Verify coverage warning for MU, VRT, NVDA and the full 55-gap claim

---

## Symbol Verification: MU, VRT, NVDA

### MU — MICRON TECHNOLOGY INC

| Dimension | Status |
|-----------|--------|
| In current portfolio | YES |
| In Jun 15 signal_snapshot.csv | YES (NON_STARMINE_ANALYST domain, no ESS score) |
| In Jun 12 StarMine (latest) | **YES** — `VERY_BULLISH`, score 5.0 |
| Actually absent from ESS | NO — absent from **today's StarMine intake** only |
| Days stale | 3 |
| Coverage gap classification | STALE (not absent) |

### VRT — VERTIV HOLDINGS CO COM CL A

| Dimension | Status |
|-----------|--------|
| In current portfolio | YES |
| In Jun 15 signal_snapshot.csv | YES (NON_STARMINE_ANALYST domain, no ESS score) |
| In Jun 12 StarMine (latest) | **YES** — `VERY_BULLISH`, score 5.0 |
| Actually absent from ESS | NO — absent from **today's StarMine intake** only |
| Days stale | 3 |
| Coverage gap classification | STALE (not absent) |

### NVDA — NVIDIA CORPORATION

| Dimension | Status |
|-----------|--------|
| In current portfolio | YES |
| In Jun 15 signal_snapshot.csv | ABSENT (not in Zacks non-ESS file either) |
| In Jun 12 StarMine (latest) | **YES** — `BULLISH`, score 4.0 |
| Actually absent from ESS | NO — absent from today's intake only |
| Days stale | 3 |
| Coverage gap classification | STALE (not absent) |

---

## Q5. Are MU, VRT, and NVDA actually missing from ESS?

**NO.** All three symbols are present in the Jun 12 StarMine dataset with known postures:
- MU: VERY_BULLISH (5.0)
- VRT: VERY_BULLISH (5.0)
- NVDA: BULLISH (4.0)

They are missing only from **today's intake batch** because today's ESS intake processed `non-ess.csv` (the Zacks non-StarMine file), which covers different symbols than the StarMine ESS file. The StarMine ESS data was processed earlier today and is in the historical store, but the `signal_snapshot.csv` was last overwritten by the non-StarMine run.

---

## Q6. If missing, why?

The 55 gaps all have `days_stale = 3` (all dated Jun 12) and all have known prior ESS postures. The coverage calculation in `build_ess_coverage_gap_warning()` works as follows:

1. Takes `incoming_ess_symbols` from today's intake (non-StarMine only → 0 StarMine symbols)
2. Iterates portfolio holdings
3. For each holding NOT in `incoming_ess_symbols` that has a prior signal, creates a gap entry

Because no StarMine symbols are in today's `incoming_ess_symbols`, **all 55 portfolio holdings that previously had StarMine coverage are flagged as gaps**.

---

## Full 55-Gap Analysis

| Metric | Value |
|--------|-------|
| Total gaps | 55 |
| All days_stale | 3 (all from Jun 12) |
| VERY_BULLISH posture | 18 |
| BULLISH posture | 16 |
| NEUTRAL posture | 15 |
| BEARISH posture | 5 |
| VERY_BEARISH posture | 1 |

**All 55 symbols have known prior ESS postures.** None are truly uncovered — they simply weren't in the most recent intake batch.

---

## Coverage Calculation Verdict

The warning is **technically correct** but **contextually misleading**: it correctly identifies that 55 holdings are absent from today's incoming ESS batch, but the underlying data is only 3 days old and the symbols' postures are known. The warning code `ESS_COVERAGE_GAP` with `days_stale=3` accurately captures the situation.

**Classification: Option A** — Legitimate coverage staleness warning (not a defect, not an artifact-selection error, not a calculation bug). The StarMine data needs to be available in `signal_snapshot.csv` for today's run.
