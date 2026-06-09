# SI-REFRESH-02 Certification

Repository: security-intelligence-hub  
Issue: SI-REFRESH-02 Provider Freshness Coverage & Partial Failure Badge  
Date: 2026-06-09  
Status: CERTIFIED

## Q1: Was SI-REFRESH-02 Implemented Successfully?

Yes. All phases implemented:
- `_signal_status()` extended with coverage metrics and `badge_state`
- `_renderSignalPills()` updated to show coverage detail and FRESH_PARTIAL state
- CSS added for new badge states (dot-partial, pill-status-partial, pill-coverage, pill-degraded)
- 13 new tests; full regression 1174 passed, 0 failed

## Q2: What Is the New Status for Yahoo Given eps_growth_5yr 0% Coverage?

Yahoo today:
- `badge_state`: FRESH (eps_growth_5yr is non-primary — does not trigger FRESH_PARTIAL)
- `zero_coverage_fields`: ["eps_growth_5yr"] — visible as advisory in the UI
- `zero_coverage_fields` advisory: "0% today: eps_growth_5yr" displayed in orange pill detail row

The operator can now see the gap. Before SI-REFRESH-02, it was completely invisible.

## Q3: What Provider Fields Are Treated as Primary Coverage Fields?

| Provider | Primary Fields |
|---|---|
| Zacks | zacks_rank, zacks_score |
| Danelfin | danelfin_raw, danelfin_score |
| Yahoo | price_target, analyst_count, current_price |

## Q4: Can a Null-Field Provider Write Still Produce FRESH?

After SI-REFRESH-02:
- If ALL rows today have empty primary fields → `badge_state = FRESH_PARTIAL`
- If a non-primary field (e.g., eps_growth_5yr) is 0% but primary fields are populated → `badge_state = FRESH` with advisory note in `zero_coverage_fields`
- If row coverage < 95% → `badge_state = FRESH_PARTIAL`
- If row coverage ≥ 95% and all primary fields populated → `badge_state = FRESH`

So the answer is: yes, FRESH is still possible if row coverage is high and primary fields are populated, even if supplemental fields are empty. This is intentional — supplemental field gaps are advisory, not blocking.

## Q5: Remaining Refresh Trust Issues

| Issue | Status |
|---|---|
| Silent null writes producing FRESH | RESOLVED — coverage metrics now visible |
| Yahoo eps_growth_5yr 0% invisible | RESOLVED — visible as advisory in badge detail |
| No per-symbol result codes | OPEN — future enhancement: log success/null/error per symbol |
| abr, price_target, eps_growth empty for Zacks bulk refresh | ADVISORY — these fields only populated via on-demand fetch, not bulk |
| `_is_stale()` vs `_sourced_date()` inconsistency (first vs max) | OPEN — low priority; no operational impact identified |
| REFRESHING badge state not implemented in server | OPEN — the `_running` flag exists; badge_state="REFRESHING" can be added when running=True |

## Files Changed

| File | Change |
|---|---|
| scripts/run_outcome_ui.py | `_signal_status()` extended with coverage metrics and badge_state |
| ui/outcome_visualization/app.js | `_renderSignalPills()` updated with coverage detail and new badge states |
| ui/outcome_visualization/index.html | New CSS for FRESH_PARTIAL, dot-partial, pill-coverage, pill-degraded |
| tests/test_si_refresh_02_coverage.py | 13 new tests |

## Test Results

New tests: 13 passed, 0 failed  
Full regression: 1174 passed, 1 skipped, 0 failed
