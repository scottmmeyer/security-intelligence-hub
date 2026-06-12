# Governance Standard Assessment
**Audit Date**: 2026-06-12  
**Scope**: SIGNAL-COVERAGE-01 — Mandatory Holdings Coverage Rule evaluation

---

## 1. Proposed Governance Standard

> **Mandatory Holdings Coverage Rule**  
> If a symbol is currently held in the portfolio, that symbol must receive 
> refresh coverage for every provider whose data contributes to:
> - CW-DAS (Conviction-Weighted Decision Architecture System)
> - DIL (Decision Intelligence Layer)
> - PAP (Portfolio Alignment Panel)
> - CRA (Conviction Ranking Analysis)
> - Portfolio Alignment UI
>
> Research-universe optimization may reduce coverage for non-held symbols.  
> It may **never** reduce coverage for held symbols.

---

## 2. Provider Applicability

Which providers' data feeds the four covered systems?

| Provider | CW-DAS | DIL | PAP | CRA | Mandatory Coverage Required? |
|----------|--------|-----|-----|-----|------------------------------|
| ESS | ✅ Primary signal | ✅ | ✅ | ✅ | YES |
| Zacks | ✅ Primary signal | ✅ | ✅ | ✅ | YES |
| Danelfin | ✅ Composite component | ✅ | ✅ | ✅ | YES |
| Yahoo (ABR) | ⚠️ Secondary | ✅ | ✅ | No | YES (DIL display) |
| FMP key_metrics | No | ✅ | ✅ | No | YES (DIL display) |
| FMP grades | No | ✅ | ✅ | No | YES (DIL display) |
| FMP earnings | No | ✅ | No | No | YES (DIL display) |
| Price Targets | No | ✅ | ✅ | No | YES (DIL display) |
| Analyst Consensus | No | ✅ | ✅ | No | YES (DIL display) |
| Security Metadata | No | No | No | No | NO (classification only) |
| Earnings Calendar | No | ✅ | No | No | YES (DIL display) |

---

## 3. Current Compliance Assessment

| Provider | Mandatory Coverage Met? | Gap | Fix Exists? |
|----------|------------------------|-----|-------------|
| Zacks | ✅ YES (post-fix) | 0 holdings | Implemented |
| Danelfin (default path) | ✅ YES | 0 holdings | Compliant |
| **Danelfin (UI smart path)** | **❌ NO** | **37 of 71 equity holdings** | **Needed** |
| Yahoo (default path) | ✅ YES | 0 holdings | Compliant |
| **Yahoo (UI smart path)** | **❌ NO** | **37 of 71 equity holdings** | **Needed** |
| FMP | ✅ YES | 0 holdings | Compliant |
| ESS | ⚠️ PASSIVE | Unknown (externally limited) | Not feasible to fully fix |
| Analyst Consensus | ⚠️ Via Yahoo | Same as Yahoo | Same fix as Yahoo |
| Price Targets | ⚠️ Via Yahoo | Same as Yahoo | Same fix as Yahoo |

---

## 4. Feasibility Assessment

### 4a. Zacks — Already Implemented ✅

`build_smart_refresh_list(forced_symbols=...)` + `_load_portfolio_equity_holdings()` in 
`refresh_signals.py`. Pattern proven. Runtime cost: negligible.

### 4b. Danelfin — Feasible, Medium Effort

**Option A**: Extend `_refresh_danelfin()` to accept `forced_symbols` and add them 
to the fetch list before calling `fetch_danelfin_scores_for_symbols()`.

**Option B**: Remove the `--smart` flag from the UI endpoint (`/api/signal-refresh` 
in `run_outcome_ui.py`). Change `--smart` to no-flag (full universe). This is 
simpler but runs ~2,523 symbols instead of ~500+37.

**Option C** (recommended): Extend `_smart_universe_symbols()` to accept a 
`forced_symbols` parameter, or add a separate `forced_holdings` parameter to 
`_refresh_danelfin()`. This mirrors the Zacks fix exactly.

Runtime cost (Option C): +37 symbols to ~500 smart symbols = +37/~500 = +7% 
fetch time. At 5 seconds/symbol (Danelfin scrape): ~3 minutes additional. Acceptable.

### 4c. Yahoo — Feasible, Low Effort

Same structure as Danelfin. `_refresh_yahoo()` can accept `forced_symbols` 
and prepend them to the symbol list before calling `fetch_yahoo_supplemental_for_symbols()`.

Yahoo fetch is faster (~0.5–2s/symbol). +37 symbols ≈ +18–74 seconds.

### 4d. ESS — Partially Feasible

ESS coverage is externally determined by Fidelity/StarMine. SIH cannot force 
ESS data for symbols that Fidelity does not publish.

However, a detection mechanism is feasible: during intake, compare the incoming 
file's symbol set against the current portfolio holdings. If a holding is absent 
from the new ESS file, emit a WARNING that the holding's ESS data is unrefreshed.

This does not fix the coverage gap, but it eliminates the silent-staleness problem.

### 4e. `refresh_portfolio_signals.py` — Trivial Fix

Replace the hardcoded `_PORTFOLIO_SYMBOLS` list with a dynamic load from 
the latest PAR `holdings.csv`. One-line change using the existing 
`_load_portfolio_equity_holdings()` function from `refresh_signals.py`.

---

## 5. Implementation Roadmap

| Fix | Priority | Effort | Impact |
|-----|----------|--------|--------|
| Danelfin: `forced_symbols` in `_refresh_danelfin()` + fix UI endpoint | P1 | 1 hour | HIGH — closes CW-DAS staleness |
| Yahoo: `forced_symbols` in `_refresh_yahoo()` | P1 | 30 min | MEDIUM — closes DIL staleness |
| `refresh_portfolio_signals.py`: dynamic holdings load | P2 | 15 min | MEDIUM — closes on-demand script drift |
| ESS: drop-detection alert in intake stage | P2 | 2 hours | MEDIUM — silent staleness detection |
| All: staleness alert mechanism (email/log) | P3 | 4 hours | LOW — operational visibility |

---

## 6. Standard Adoption Verdict

**Verdict**: ADOPT as SIH platform-wide governance standard.

Rationale:
1. ZACKS-REFRESH-UNIVERSE-01 demonstrated that research-universe optimization creates
   portfolio-governance blind spots at architecture level
2. The same defect pattern was confirmed in Danelfin and Yahoo
3. The fix is proven (Zacks), low-risk (additive parameter), and backward-compatible
4. The cost is negligible (~30–200 seconds/day additional fetch time)
5. The alternative — trusting that the UI "smart refresh" covers all held positions — 
   is demonstrably false

The standard should be encoded as a pipeline test: after every refresh run, verify 
that all current equity holdings appear in the latest cache for each scoring provider.

---

## 7. Proposed Test

```python
def test_mandatory_holdings_coverage(provider_cache_path, holdings):
    """Verify every equity holding appears in provider cache after refresh."""
    cached = set(load_cache_symbols(provider_cache_path))
    equity_holdings = {h["symbol"] for h in holdings if h["asset_class"] == "EQUITIES"}
    missing = equity_holdings - cached
    assert not missing, f"Holdings missing from {provider_cache_path.name}: {sorted(missing)}"
```

This test should be added to the test suite and run as part of CI after each signal refresh.
