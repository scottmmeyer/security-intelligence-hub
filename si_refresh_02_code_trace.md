# SI-REFRESH-02 Code Trace

Repository: security-intelligence-hub  
Audit Date: 2026-06-09  
Purpose: Forensic verification of SI-REFRESH-02 implementation against documentation

## 1. `_signal_status()` — scripts/run_outcome_ui.py

### Primary Field Definitions (actual code)

```python
_PRIMARY_FIELDS = {
    "zacks":    ["zacks_rank", "zacks_score"],
    "danelfin": ["danelfin_raw", "danelfin_score"],
    "yahoo":    ["price_target", "analyst_count", "current_price"],
}
```

`eps_growth_5yr` is **NOT** a primary field. It is included only in `_ALL_SCORE_FIELDS`.

### Badge State Logic (actual code)

```python
# FRESH: today, ≥95% row coverage, no primary field at 0%
# FRESH_PARTIAL: today but coverage <95% OR a primary field at 0%
if coverage_pct < 95.0 or degraded:
    entry["badge_state"] = "FRESH_PARTIAL"
else:
    entry["badge_state"] = "FRESH"
```

- `degraded` = primary fields with 0% coverage today.
- `zero_fields` = ALL score fields with 0% coverage (includes supplemental).
- `badge_state = FRESH_PARTIAL` is triggered ONLY by: row coverage < 95% OR a **primary** field at 0%.
- `eps_growth_5yr` appearing in `zero_coverage_fields` does **NOT** trigger FRESH_PARTIAL.

### Live API Computation (2026-06-09)

| Provider | attempted | with_data | coverage | degraded_fields | zero_coverage_fields | badge_state |
|---|---|---|---|---|---|---|
| Zacks | 702 | 671 | 95.6% | [] | [abr, price_target, eps_growth] | **FRESH** |
| Danelfin | 697 | 697 | 100% | [] | [] | **FRESH** |
| Yahoo | 697 | 696 | 99.9% | [] | [eps_growth_5yr] | **FRESH** |

**Yahoo `badge_state` = FRESH** because:
1. coverage_pct = 99.9% (≥ 95% threshold)
2. degraded_fields = [] (no primary field at 0%)
3. eps_growth_5yr is in zero_coverage_fields but this does NOT trigger FRESH_PARTIAL

## 2. `_renderSignalPills()` — ui/outcome_visualization/app.js

The rendering function correctly reads `badge_state` and maps it to visual classes and labels.

For Yahoo today:
- `badge_state = "FRESH"` → green dot, "(fresh)"
- `zero_coverage_fields = ["eps_growth_5yr"]` → advisory text "0% today: eps_growth_5yr" shown in `pill-degraded-advisory` yellow tag

The advisory IS rendered because `info.zero_coverage_fields.length > 0` and `info.degraded_fields.length == 0` routes to the `else if` branch showing `pill-degraded-advisory`.

## 3. Badge State Rendering Paths

| badge_state | dot class | status class | status label |
|---|---|---|---|
| FRESH | dot-fresh (green) | pill-status-fresh | "fresh" |
| FRESH_PARTIAL | dot-partial (orange) | pill-status-partial | "fresh — partial" |
| STALE | dot-stale (red) | pill-status-stale | "stale" |
| REFRESHING | dot-refreshing (blue pulse) | pill-status-refreshing | "refreshing" |
| UNKNOWN | dot-unknown (gray) | pill-status-unknown | "no data" |

## 4. REFRESHING State

`badge_state = "REFRESHING"` is defined in the rendering table but **never set by the server** in `_signal_status()`. The `_running` flag is added at the top level (`data["_running"]`), and the UI code checks `data._running` separately to disable the button and show the progress message. The badge itself does not show REFRESHING via `badge_state` today. This is a known open item (si_refresh_02_certification.md §Q5).
