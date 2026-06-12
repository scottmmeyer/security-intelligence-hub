# Final Verdict: SIGNAL-COVERAGE-01
**Audit Date**: 2026-06-12  
**Scope**: Mandatory Holdings Coverage Audit — All Signal Providers  
**Status**: TWO ACTIVE DEFECTS CONFIRMED + TWO GOVERNANCE RISKS IDENTIFIED

---

## Q1: Which providers already guarantee mandatory holdings coverage?

| Provider | Guaranteed? | Mechanism |
|----------|-------------|-----------|
| **Zacks** | ✅ YES (post-fix) | `forced_symbols` parameter added in ZACKS-REFRESH-UNIVERSE-01 |
| **FMP** | ✅ YES | `_all_universe_symbols()` — no smart mode exists |
| Danelfin (default path) | ✅ YES (default only) | Full universe when `smart=False` |
| Yahoo (default path) | ✅ YES (default only) | Full universe when `smart=False` |
| ESS | ⚠️ PASSIVE | Externally determined by Fidelity/StarMine |

No provider other than Zacks (post-fix) and FMP **unconditionally** guarantees 
mandatory holdings coverage across all invocation paths.

---

## Q2: Which providers can exclude held positions?

### CONFIRMED ACTIVE DEFECTS

**Danelfin** — `run_outcome_ui.py:724` hardcodes `--smart`, which passes `smart=True` 
to `_refresh_danelfin()`, which calls `_smart_universe_symbols()`. This path 
excludes NEUTRAL (ESS < 6.5), BEARISH, VERY_BEARISH, and NO_ESS holdings.

- **Affected**: 37 of 71 equity holdings (52%)  
- **Triggered by**: Standard operator action (clicking "Refresh Signals" in the UI)
- **Scoring impact**: HIGH — Danelfin feeds CW-DAS composite score

**Yahoo** — Same structural defect as Danelfin. Same UI endpoint, same `--smart` flag.

- **Affected**: 37 of 71 equity holdings (52%)  
- **Triggered by**: Standard operator action  
- **Scoring impact**: MEDIUM — ABR/price targets are informational

### Specific Holdings at Risk

The 5 BEARISH/VERY_BEARISH equity holdings are highest-risk (potential reduction candidates 
running on stale Danelfin data):

| Symbol | ESS | Gap Provider |
|--------|-----|-------------|
| TSLA | VERY_BEARISH | Danelfin + Yahoo |
| CMCO | BEARISH | Danelfin + Yahoo |
| DVN | BEARISH | Danelfin + Yahoo |
| KGC | BEARISH | Danelfin + Yahoo |
| PRIM | BEARISH | Danelfin + Yahoo |

The 6 NO_ESS equity holdings have no fallback signal (Danelfin + Yahoo are their only data sources):

| Symbol | ESS | Gap Provider |
|--------|-----|-------------|
| AEIS | NO_ESS | Danelfin + Yahoo |
| BSVN | NO_ESS | Danelfin + Yahoo |
| CBOE | NO_ESS | Danelfin + Yahoo |
| MTZ | NO_ESS | Danelfin + Yahoo |
| SIMO | NO_ESS | Danelfin + Yahoo |
| STNG | NO_ESS | Danelfin + Yahoo |

---

## Q3: Are any additional defects present today?

### ACTIVE DEFECTS

1. **SIGNAL-COVERAGE-01a — Danelfin UI smart-path excludes 37 held equity positions**  
   - Root: `run_outcome_ui.py:724` hardcodes `--smart`  
   - Impact: CW-DAS composite score stale for 37 holdings when refreshed via UI  
   - Priority: **P1**

2. **SIGNAL-COVERAGE-01b — Yahoo UI smart-path excludes 37 held equity positions**  
   - Root: Same `--smart` flag, same path  
   - Impact: Analyst consensus + price targets stale for 37 holdings via UI  
   - Priority: **P1**

### GOVERNANCE RISKS (not active scoring defects today, but will worsen over time)

3. **`refresh_portfolio_signals.py` hardcoded `_PORTFOLIO_SYMBOLS` list**  
   - Any new position is silently missing from this on-demand refresh script  
   - Priority: **P2**

4. **ESS: no detection of holdings absent from incoming file**  
   - If StarMine drops a holding, SIH uses stale ESS indefinitely with no warning  
   - Priority: **P2**

---

## Q4: Should Mandatory Holdings Coverage become an SIH-wide governance standard?

**Yes. Adopt immediately.**

ZACKS-REFRESH-UNIVERSE-01 was not a one-off oversight. This audit confirms the same 
architectural pattern exists in two additional providers (Danelfin and Yahoo) and 
is triggered by the standard operator workflow. The pattern is:

> Research-universe optimization is implemented at the invocation level,  
> not at the provider level.  
> Holdings are not a first-class concept in the refresh pipeline design.  
> Therefore, any research optimization that reduces the fetch set can silently  
> drop held positions.

The governance standard (mandatory holdings coverage as a non-negotiable constraint) 
prevents this class of defect from recurring as new providers are added.

---

## Q5: Recommended Remediation Roadmap

### Phase 1 — P1 Fixes (This Sprint)

**Fix SIGNAL-COVERAGE-01a — Danelfin**

Add `forced_symbols: set[str] | None = None` to `_refresh_danelfin()` in 
`scripts/refresh_signals.py`. Load holdings via `_load_portfolio_equity_holdings()`. 
Pass as forced set. Update UI endpoint to pass forced holdings regardless of `--smart` mode.

```python
# scripts/refresh_signals.py — _refresh_danelfin()
def _refresh_danelfin(*, dry_run, verbose, smart=False):
    ...
    forced = _load_portfolio_equity_holdings()
    base_symbols = _smart_universe_symbols() if smart else _all_universe_symbols()
    # Force-include equity holdings not already in the smart set
    forced_extra = [s for s in sorted(forced) if s not in set(base_symbols)]
    symbols = forced_extra + base_symbols  # Holdings first (priority fetch)
    ...
```

**Fix SIGNAL-COVERAGE-01b — Yahoo**

Identical pattern to Danelfin fix.

**Estimated runtime increase**: +37 symbols × ~1.5s = +55 seconds for Danelfin.  
+37 symbols × ~1s = +37 seconds for Yahoo.  
Total: **< 2 minutes additional per daily refresh**.

### Phase 2 — P2 Fixes (Next Sprint)

**Fix: `refresh_portfolio_signals.py` — Dynamic Holdings Load**

```python
# Replace:
_PORTFOLIO_SYMBOLS = ['AEIS', 'AGEN', ...]  # static list

# With:
_PORTFOLIO_SYMBOLS = sorted(_load_portfolio_equity_holdings())
```

**Fix: ESS Drop Detection in Intake Stage**

During `execute_ess_intake_stage()`, after processing the incoming file, compare 
the set of symbols in the new file against current equity holdings from the latest PAR run. 
Emit a structured WARNING for any holding absent from the new file.

### Phase 3 — P3 Improvements (Backlog)

- Platform-wide staleness alert: after every refresh run, log which equity holdings 
  are absent from each provider's latest cache (via `holdings_coverage_matrix`-style check)
- Add pytest coverage test: `test_mandatory_holdings_coverage()` per provider

---

## Summary Verdict

| Defect ID | Description | Status | Priority |
|-----------|-------------|--------|----------|
| ZACKS-REFRESH-UNIVERSE-01 | Zacks excluded 24 bearish holdings | ✅ FIXED | Done |
| SIGNAL-COVERAGE-01a | Danelfin UI smart-path excludes 37 holdings | ❌ ACTIVE | P1 |
| SIGNAL-COVERAGE-01b | Yahoo UI smart-path excludes 37 holdings | ❌ ACTIVE | P1 |
| SIGNAL-COVERAGE-01c | `refresh_portfolio_signals.py` hardcoded list | ⚠️ RISK | P2 |
| SIGNAL-COVERAGE-01d | ESS drop-detection absent from intake | ⚠️ RISK | P2 |

**Governance Standard**: ADOPT — Mandatory Holdings Coverage Rule applies to all 
providers contributing data to CW-DAS, DIL, PAP, CRA, and Portfolio Alignment.
