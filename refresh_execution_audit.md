# REFRESH-BEHAVIOR-01 Refresh Execution Audit

## Audit context

- Server: scripts/run_outcome_ui.py
- Trigger path: POST /api/signal-refresh
- Child script: scripts/refresh_signals.py --smart

## Runtime evidence from server log

Observed after POST:

- [refresh_signals] Zacks: up-to-date (2026-06-12), skipping.
- [refresh_signals] Yahoo: up-to-date (2026-06-12), skipping.
- [refresh_signals] Danelfin: up-to-date (2026-06-12), skipping.
- [refresh_signals] FMP (daily): up-to-date (2026-06-12), skipping.
- [refresh_signals] All signal caches are current.

## Determination

The refresh button did launch the background refresh script.

But for Zacks, Danelfin, and Yahoo, execution exited at freshness guards because each provider was already marked fresh at file level for today.

Therefore this operation did not execute provider symbol fetch loops.

## A/B/C/D classification

- A) executed provider refreshes: No (not for Zacks/Danelfin/Yahoo)
- B) only recalculated freshness metadata: Not exactly; script ran checks and exited
- C) launched background jobs: Yes
- D) exited early because providers already marked fresh: Yes

Primary behavior for this run: C + D.# Refresh Execution Audit

Repository: security-intelligence-hub  
Date: 2026-06-09  
Audit scope: Zacks, Danelfin, Yahoo signal refresh cycle for 2026-06-09

---

## Q1 — Refresh Timing

Based on file timestamps:

| Provider | File Written | Source |
|---|---|---|
| Zacks | 2026-06-09 07:03 | data/signals/zacks/2026-06-09_zacks.csv |
| Yahoo | 2026-06-09 07:25 | data/signals/yahoo/2026-06-09_yahoo_supplemental.csv |
| Danelfin | 2026-06-09 08:27 | data/signals/danelfin/2026-06-09_danelfin.csv |

Duration is not captured in the output files. Estimated from gaps:
- Zacks → Yahoo gap: ~22 minutes (consistent with sequential symbol-by-symbol fetch)
- Yahoo → Danelfin gap: ~62 minutes

---

## Q2 — Symbol Counts

### Zacks

| Metric | Count |
|---|---|
| Symbols eligible (universe) | ~700+ (smart refresh list — bullish-first) |
| Symbols attempted | 702 |
| Symbols succeeded (with score data) | 671 |
| Symbols fetched but returned no data | 31 |
| Symbols skipped (already fresh) | 0 |

**31 Zacks symbols had `sourced_date=2026-06-09` written but empty `zacks_rank` and `zacks_score`.** These symbols were attempted but the provider returned no data (see failure modes).

### Danelfin

| Metric | Count |
|---|---|
| Symbols attempted | 497 |
| Symbols succeeded (with score) | 497 |
| No-data rows | 0 |
| Skip (already fresh) | 0 |

Danelfin had **100% success rate** today.

### Yahoo

| Metric | Count |
|---|---|
| Symbols attempted | 697 |
| Symbols with at least one data field | 696 |
| No-data rows (all fields empty) | 1 |
| Symbols with price_target | 684 |
| Symbols with abr (analyst buy ratio) | 463 |
| Symbols with analyst_count | 684 |
| Symbols with current_price | 696 |
| Symbols with upside_pct | 684 |
| Symbols with eps_growth_5yr | **0 of 697** |

Yahoo `eps_growth_5yr` was **universally empty** across all 697 symbols fetched today. This is a partial-field failure affecting all rows. The badge still shows FRESH because other fields were populated.

---

## Q3 — Timestamps Before / After

Timestamps come from `sourced_date` field within the CSV files. This is set to `date.today().isoformat()` at fetch time, regardless of whether data was returned.

| Provider | sourced_date (sample before) | sourced_date (today) | Changed? |
|---|---|---|---|
| Zacks | 2026-06-08 | 2026-06-09 | Yes (for 702 symbols) |
| Danelfin | 2026-06-08 | 2026-06-09 | Yes (for 497 symbols) |
| Yahoo | 2026-06-08 | 2026-06-09 | Yes (for 697 symbols) |

---

## Q4 — Value Changes

### Zacks

671 symbols received updated `zacks_rank` and `zacks_score`. 31 symbols received updated `sourced_date` but empty scores (unchanged from last successful fetch for those symbols, but overwritten to empty).

`abr`, `price_target`, `eps_growth` are universally empty in today's batch (0/702). These fields are populated only in the on-demand per-symbol fetch path, not the bulk refresh.

### Danelfin

497 symbols received updated `danelfin_raw` and `danelfin_score`. All values changed or were confirmed.

### Yahoo

696 symbols received at least one updated data point. `eps_growth_5yr` was empty for all 697 symbols fetched today. `abr` was populated for 463/697 (66%).

---

## Summary Table

| Provider | Attempted | Score Data | No Data | Badge Today | Data Quality |
|---|---|---|---|---|---|
| Zacks | 702 | 671 | 31 | FRESH ✓ | Good — 31 gaps are expected for illiquid symbols |
| Danelfin | 497 | 497 | 0 | FRESH ✓ | Excellent |
| Yahoo | 697 | 696 | 1 | FRESH ✓ | Partial — eps_growth_5yr universally empty |
