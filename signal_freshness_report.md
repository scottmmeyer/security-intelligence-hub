# Signal Freshness Report
**Phase:** 7.5M — Signal Provenance, Lineage & Freshness Audit  
**Date (Reference):** 2026-05-31  
**Status:** COMPLETE — Audit Only (No Enforcement)

---

## Freshness Classification Thresholds

| Status | Threshold | Meaning |
|--------|-----------|---------|
| **FRESH** | ≤ 2 days | Signal is current; no action needed |
| **WARNING** | > 2 days and ≤ 5 days | Signal approaching staleness; monitor |
| **STALE** | > 5 days and ≤ 10 days | Signal is stale; refresh recommended |
| **CRITICAL** | > 10 days | Signal is critically stale; reliability uncertain |

Note: These thresholds are proposed governance guidelines for this audit. No automated enforcement exists yet.

---

## Signal Freshness Summary

| Signal | Source File | Latest Date | Age (days) | Status |
|--------|------------|-------------|-----------|--------|
| Zacks Rank / Score | `data/signals/zacks/latest_zacks.csv` | 2026-05-29 | 2 | ✅ **FRESH** |
| Danelfin AI Score | `data/signals/danelfin/latest_danelfin.csv` | 2026-05-29 | 2 | ✅ **FRESH** |
| Yahoo ABR / Target / Upside | `data/signals/yahoo/latest_yahoo_supplemental.csv` | 2026-05-29 | 2 | ✅ **FRESH** |
| ESS (StarMine) | `data/current/signal_snapshot.csv` | 2026-05-26 | 5 | ⚠️ **WARNING** |
| Analytical Universe (composite) | `data/current/analytical_universe.csv` | 2026-05-31 (rebuild) | 0 | ✅ **FRESH** |
| Replay Inputs | `data/current/replay_inputs.csv` | (static — not date-stamped) | — | ℹ️ N/A |
| Replay Performance | `data/current/replay_performance_series.csv` | (static — not date-stamped) | — | ℹ️ N/A |

---

## Per-Signal Detailed Freshness

### ESS (StarMine) — ⚠️ WARNING (5 days)

- **Source:** Fidelity EquitySummaryScores-May2026.csv
- **Intake run:** INTAKE-20260526-001 (2026-05-26)
- **Refresh cadence:** Monthly (Fidelity publishes updated ESS monthly)
- **Expected next refresh:** June 2026 ESS file
- **Risk:** At 5 days, ESS is at the WARNING threshold. For a monthly-cadence signal, this is operationally normal. The May 2026 ESS file was the most recent available as of 2026-05-31.
- **Composite impact:** ESS carries 55% of the composite weight. Stale ESS can persist for up to 30 days between monthly refreshes.

### Zacks — ✅ FRESH (2 days)

- **Source:** `quote-feed.zacks.com` API via `fetch_zacks_scores.py`
- **Refresh cadence:** On-demand; run approximately weekly per commit pattern
- **Latest fetch:** 2026-05-29
- **Risk:** Low. Zacks rank changes relatively infrequently. 2-day age is within normal operational range.

### Danelfin — ✅ FRESH (2 days)

- **Source:** `danelfin.com/stock/{TICKER}` scrape
- **Refresh cadence:** On-demand; run approximately weekly
- **Latest fetch:** 2026-05-29
- **Risk:** Low. Danelfin AI Score changes gradually over time. 2-day age is within normal operational range.

### Yahoo ABR / Target — ✅ FRESH (2 days, but target stale at source)

- **Source:** Yahoo Finance consensus page scrape
- **Refresh cadence:** On-demand; run approximately weekly
- **Latest fetch:** 2026-05-29
- **Risk:** The **fetch date** is fresh (2 days), but individual analyst **price targets** embedded in Yahoo's consensus may reflect analyst reports from weeks or months prior. See DELL case (yahoo_lineage_report.md).
- **Special case:** DELL shows `upside = −48.3%` with `ABR = 2.0 (Buy)`. The fetch is current but the underlying analyst targets are stale at the Yahoo source level.

### Replay Data — ℹ️ Not date-stamped

- **Source:** `data/current/replay_inputs.csv` and `replay_performance_series.csv`
- Replay evidence is generated from historical simulation runs. It does not have a `sourced_date` field.
- Freshness applies to **when the replay was last run**, not when the data was last fetched from an external source.
- The replay validation runs are defined by the `start_date` / `end_date` in `replay_inputs.csv` — these are point-in-time historical backtests and are not expected to be refreshed on a regular schedule.

---

## Coverage Gaps (No Signal Available)

Some portfolio holdings have missing signals. Signal absence is classified separately from freshness:

| Symbol | Missing Signal | Impact |
|--------|---------------|--------|
| Multiple (ETFs/funds) | ESS — ETFs/funds not covered by StarMine | Composite defaults to Zacks/Danelfin |
| ~50% of portfolio | Yahoo ABR — not all holdings on Yahoo supplemental | Yahoo weight excluded from composite |
| Some holdings | Danelfin — some names not on danelfin.com | Danelfin weight excluded from composite |

---

## Recommendations (Audit Only — No Changes This Phase)

1. **ESS:** Plan monthly refresh trigger when Fidelity ESS June 2026 file is available. Consider adding a CRITICAL threshold alert after 15 days without ESS refresh.
2. **Yahoo target quality:** Consider adding a flag when `ABR ≤ 2.0` (Buy) but `upside_pct < −10%` — this indicates a target that is stale at the source.
3. **Replay freshness:** Add a `last_validated_date` field to `replay_inputs.csv` to support freshness classification for replay evidence.
4. **Danelfin/Zacks:** Current refresh cadence (approximately weekly) maintains FRESH status. No change recommended.
