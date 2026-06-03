# Freshness Governance Validation
**Phase 22D.1 — Audit Objective #4**  
**Reference Date:** 2026-06-01  
**Snapshot Date:** 2026-05-31 (analytical_universe.csv)

---

## Signal Provider Freshness Findings

### Measured Dates (as of 2026-06-01)

| Provider | Latest sourced_date | Age vs Ref (2026-06-01) | File | Rows |
|----------|--------------------|-----------------------|------|------|
| ESS (StarMine) | 2026-06-01 | 0 days | `data/current/signal_snapshot.csv` | 2,831 |
| Zacks | 2026-06-01 | 0 days | `data/signals/zacks/latest_zacks.csv` | 2,601 |
| Danelfin | 2026-05-29 | 3 days | `data/signals/danelfin/latest_danelfin.csv` | 954 |
| Yahoo / Analyst Consensus | 2026-05-29 | 3 days | `data/signals/yahoo/latest_yahoo_supplemental.csv` | 954 |

---

## Server-Side Staleness Check (API: `/api/signal-status`)

**File:** `scripts/run_outcome_ui.py`, `_signal_status()` function, lines 207–218  
**Logic:** `stale = sourced_date != today` where `today = date.today().isoformat()`  
**Note:** Server reads only the **first** `sourced_date` value in each CSV (not the latest).

| Provider | Server-reported `sourced_date` | Stale flag |
|----------|-------------------------------|------------|
| Zacks | 2026-06-01 | `False` (current) |
| Danelfin | 2026-05-29 | `True` (stale) |
| Yahoo | 2026-05-29 | `True` (stale) |

**Issue:** ESS is not tracked in `_SIGNAL_FILES` — the server staleness endpoint covers only Zacks, Danelfin, and Yahoo. ESS freshness is embedded per-symbol in the `fidelity_signals_by_symbol` payload and not surfaced as a standalone source timestamp in the signal-status API.

---

## UI Freshness Classification

**File:** `ui/portfolio_alignment/app.js`, `_freshnessStatus()` function, lines 1029–1041  
**Thresholds:** ≤2 days FRESH | ≤5 days WARNING | ≤10 days STALE | >10 days CRITICAL  
**Reference:** `snapshot_date` from the analysis run (2026-06-01)

| Provider | Date | Age | UI Status |
|----------|------|-----|-----------|
| ESS | 2026-06-01 | 0d | **FRESH** |
| Zacks | 2026-06-01 | 0d | **FRESH** |
| Danelfin | 2026-05-29 | 3d | **WARNING** |
| Yahoo | 2026-05-29 | 3d | **WARNING** |

---

## Freshness Data Routing

The UI obtains freshness dates through two separate channels:

### Channel A — Per-symbol signal objects (ESS and Yahoo)
- ESS refresh date: populated as `fs.refresh_date` in `fidelity_signals_by_symbol` entries
- Yahoo refresh date: populated as `ac.refresh_date` in `analyst_consensus_by_symbol` entries
- These are per-symbol values, so the freshness panel shows the date of the specific signal for the symbol being viewed

### Channel B — Analysis run metadata (Zacks and Danelfin)
- Populated by `_build_signal_source_metadata()` in `src/portfolio/runner.py` lines 1061–1089
- Reads `sourced_date` column, returns the **maximum** date across the full file
- Attached to the run payload as `signal_source_metadata.zacks_refresh_date` and `signal_source_metadata.danelfin_refresh_date`
- A single date for the entire provider — not per-symbol

This dual-channel approach creates an inconsistency: ESS and Yahoo freshness reflect the individual symbol's data date, while Zacks and Danelfin show a file-level date that may not reflect whether a specific symbol was actually captured in the latest refresh.

---

## Issues Identified

### Issue A: Server `_sourced_date()` reads first row, not latest

**File:** `scripts/run_outcome_ui.py`, lines 50–61

```python
def _sourced_date(csv_path: Path) -> str | None:
    ...
    for row in csv.DictReader(fh):
        v = (row.get("sourced_date") or "").strip()
        if v:
            return v   # ← returns FIRST non-empty value, not the latest
```

If rows are not sorted by date (or if historical rows are mixed into the file), the server may report a stale sourced_date to the `/api/signal-status` endpoint even when fresh data is present in later rows. The `_build_signal_source_metadata()` function in `runner.py` correctly uses `max(dates)` — the server endpoint does not.

**Severity:** LOW — In practice, latest_zacks.csv and latest_danelfin.csv are written as snapshots with consistent dates per file, so first-row = typical date. But it is a latent correctness risk.

### Issue B: Danelfin and Yahoo are 3 days stale (WARNING state)

Danelfin and Yahoo `sourced_date` = 2026-05-29 vs reference 2026-06-01 (3 days gap).  
UI will render these as **WARNING** in the Signal Freshness panel.  
The server `/api/signal-status` will report both as `stale: true`.  

This is an operational state, not a code bug. The signal files need to be refreshed.

### Issue C: Yahoo file is not tracked as an independent freshness source

Yahoo supplemental (`latest_yahoo_supplemental.csv`) is included in `_SIGNAL_FILES` for the server's staleness endpoint, but the signal-status response object key is `"yahoo"` while the UI reads Yahoo freshness from `ac.refresh_date` (per-symbol from `analyst_consensus_by_symbol`). The server's Yahoo stale flag and the UI's Yahoo freshness date are computed from different sources and may diverge if the per-symbol refresh dates differ from the file's `sourced_date`.

**Severity:** LOW — Unlikely to cause visible inconsistency in normal operation.

### Issue D: ESS not tracked in `/api/signal-status`

ESS freshness is not included in the server's signal-status endpoint. If a user checks the signal status panel independent of a loaded analysis run, ESS freshness is not reported. The UI must load a full portfolio analysis run to see ESS freshness.

**Severity:** LOW — ESS freshness is accessible per-symbol in the Signal Agreement panel during normal analysis workflow.

---

## Freshness Panel Rendering Confirmation

**File:** `ui/portfolio_alignment/app.js`, `_signalAgreementPanelHtml()`, lines 1082–1214

The freshness panel renders only rows where `r.date` is truthy. Given current data:
- ESS: date = `fs.refresh_date` → renders as FRESH
- Zacks: date = `meta.zacks_refresh_date` → renders as FRESH
- Danelfin: date = `meta.danelfin_refresh_date` → renders as WARNING
- Yahoo: date = `ac.refresh_date` → renders as WARNING

Both WARNING rows will be visible in the per-symbol Signal Freshness table. The panel is working correctly for the available data; the WARNING status accurately reflects the 3-day gap.

---

## Classification

| Issue | Severity |
|-------|----------|
| Danelfin + Yahoo 3-day staleness (operational) | **MEDIUM** — Signals need refresh; WARNING status is correctly shown |
| Server `_sourced_date()` reads first row not latest | **LOW** — Latent correctness risk, not currently causing observable errors |
| Yahoo freshness reported from two different sources | **LOW** — Currently consistent; fragile if file format changes |
| ESS absent from `/api/signal-status` endpoint | **LOW** — ESS freshness accessible through analysis run; not a blocking issue |
