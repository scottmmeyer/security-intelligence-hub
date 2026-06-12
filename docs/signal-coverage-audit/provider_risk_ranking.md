# Provider Risk Ranking
**Audit Date**: 2026-06-12  
**Scope**: SIGNAL-COVERAGE-01 — Governance Risk by Provider

---

## Risk Criteria

Providers are ranked by the following criteria:

1. **Exclusion mechanism**: Can the provider's refresh logic permanently exclude a held position?
2. **Scoring impact**: Does stale data from this provider affect CW-DAS composite scoring?
3. **Trigger path**: Is the exclusion pathway triggered by normal operations?
4. **Staleness cap**: Is there a maximum age enforced for held positions?
5. **Alert mechanism**: Does SIH alert when a held position becomes stale?

---

## Rankings

---

### CRITICAL — Danelfin (Smart Path via UI)

**Governance Risk**: CRITICAL  
**Status**: ACTIVE DEFECT  
**GitHub Issue**: Needs creation

| Criterion | Assessment |
|-----------|-----------|
| Can exclude held positions? | YES — 37 of 71 equity holdings excluded in UI smart path |
| Scoring impact | HIGH — Danelfin feeds CW-DAS composite score directly |
| Triggered by normal operations? | YES — operator clicking "Refresh Signals" in UI always uses `--smart` |
| Staleness cap | NONE |
| Alert mechanism | NONE |

**Exclusion Pathway**: `run_outcome_ui.py:724` hardcodes `--smart` → `_smart_universe_symbols()` 
excludes NEUTRAL (ESS < 6.5), BEARISH, VERY_BEARISH, NO_ESS holdings. Every time the operator 
uses the UI to trigger a signal refresh, Danelfin data for 37 held positions is not updated.

**Asymmetric Risk**: Holdings under reduction review (BEARISH/VERY_BEARISH) are the exact 
positions most likely to be reviewed by the operator — and they receive no Danelfin refresh 
via the standard UI path.

**Fix Required**: Add `forced_symbols` (holdings) to `_refresh_danelfin()` OR remove `--smart` 
from the UI endpoint for Danelfin specifically OR fix the UI endpoint to use full-universe mode.

---

### HIGH — Yahoo Supplemental (Smart Path via UI)

**Governance Risk**: HIGH  
**Status**: ACTIVE DEFECT (same structural path as Danelfin)

| Criterion | Assessment |
|-----------|-----------|
| Can exclude held positions? | YES — 37 of 71 equity holdings excluded in UI smart path |
| Scoring impact | MEDIUM — Yahoo ABR is informational; affects DIL analyst consensus display |
| Triggered by normal operations? | YES — same UI endpoint, same `--smart` flag |
| Staleness cap | NONE |
| Alert mechanism | NONE |

**Impact vs. Danelfin**: Lower severity because Yahoo ABR/price_target does not drive 
primary CW-DAS composite scoring. However, stale analyst consensus for a position under 
active reduction review is a decision-context failure.

The `composite_v2_yahoo` column does include Yahoo signals — if this feeds any downstream 
ranking, the scoring impact would be elevated to HIGH.

**Fix Required**: Same as Danelfin — `forced_symbols` parameter in `_refresh_yahoo()`.

---

### HIGH — `refresh_portfolio_signals.py` (Hardcoded List)

**Governance Risk**: HIGH (operational)  
**Status**: GOVERNANCE DEFECT

| Criterion | Assessment |
|-----------|-----------|
| Can exclude held positions? | YES — any position not in `_PORTFOLIO_SYMBOLS` (static code list) |
| Scoring impact | MEDIUM — script updates Danelfin + Yahoo caches for portfolio symbols |
| Triggered by normal operations? | YES — divergence grows silently with each portfolio change |
| Staleness cap | N/A |
| Alert mechanism | NONE |

The script `scripts/refresh_portfolio_signals.py` has a hardcoded list of ~80 portfolio 
symbols committed in source code. New positions (e.g. AGEN, SMR) or removed positions 
are not automatically reflected. The script does not fail — it silently succeeds while 
missing new holdings.

**Fix Required**: Replace `_PORTFOLIO_SYMBOLS` with dynamic load from latest PAR holdings.

---

### MEDIUM — ESS (Passive Coverage Risk)

**Governance Risk**: MEDIUM (passive)  
**Status**: STRUCTURAL RISK (not a pipeline defect)

| Criterion | Assessment |
|-----------|-----------|
| Can exclude held positions? | YES — if Fidelity/StarMine drops a holding from their file |
| Scoring impact | HIGH — ESS is the primary CW-DAS signal |
| Triggered by normal operations? | Passive — SIH has no control |
| Staleness cap | NONE |
| Alert mechanism | NONE |

ESS is the highest-weight signal in CW-DAS, but the coverage risk is externally 
determined (not a pipeline architecture defect). SIH cannot force ESS data. However, 
SIH does not currently detect when a holding is absent from the incoming ESS file, 
which creates silent staleness.

**Fix Available (detection only)**: Add a holdings-absence check during ESS intake. 
If a current equity holding is not present in the incoming ESS file, emit WARNING 
with the missing symbol list.

---

### LOW — Zacks (Post-Fix)

**Governance Risk**: LOW  
**Status**: ✅ FIXED (ZACKS-REFRESH-UNIVERSE-01)

| Criterion | Assessment |
|-----------|-----------|
| Can exclude held positions? | NO (post-fix) |
| Scoring impact | HIGH (but gap is closed) |
| Triggered by normal operations? | NO — forced_symbols prevents exclusion |
| Staleness cap | 1 day (daily refresh) |
| Alert mechanism | None |

Post-fix: all current equity holdings are force-included in the Zacks daily refresh 
via `forced_symbols` parameter. The only remaining gap is if `_load_portfolio_equity_holdings()` 
fails to find the latest PAR run, which defaults to an empty forced set (graceful degradation).

---

### LOW — FMP

**Governance Risk**: LOW  
**Status**: ✅ NO DEFECT

| Criterion | Assessment |
|-----------|-----------|
| Can exclude held positions? | NO — full universe always |
| Scoring impact | LOW (informational) |
| Triggered by normal operations? | N/A |
| Staleness cap | Daily (key_metrics, grades); 90 days (earnings, income_growth) |
| Alert mechanism | `get_fmp_freshness_report()` available |

FMP daily refresh uses `_all_universe_symbols()` with no smart exclusion. No holdings gap.

---

### LOW — Analyst Consensus, Price Targets

**Governance Risk**: LOW (informational)  
**Status**: ⚠️ DEPENDENT ON YAHOO — gap exists but informational only

These are derived signals from Yahoo supplemental. Their governance risk is fully 
inherited from the Yahoo provider. Since ABR/price targets are not CW-DAS composite 
score drivers, the operational impact is limited to DIL display quality.

---

## Summary Risk Table

| Provider | Governance Risk | Defect | Scoring Impact | Fix Priority |
|----------|----------------|--------|----------------|-------------|
| Danelfin (UI smart path) | **CRITICAL** | Active | HIGH | P1 |
| Yahoo (UI smart path) | **HIGH** | Active | MEDIUM | P1 |
| `refresh_portfolio_signals.py` | **HIGH** | Active | MEDIUM | P2 |
| ESS | **MEDIUM** | Passive | HIGH | P2 (detection) |
| Zacks | LOW | Fixed ✅ | — | Done |
| FMP | LOW | None ✅ | — | None needed |
| Analyst Consensus | LOW | Via Yahoo | LOW | P1 (via Yahoo fix) |
| Price Targets | LOW | Via Yahoo | LOW | P1 (via Yahoo fix) |
| Security Metadata | NONE | None | None | None needed |
