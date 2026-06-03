# ESS Projection Consistency Report
**Generated:** 2026-06-01  
**Scope:** All surfaces that display or use `ess_score_text`, cross-system consistency, and known divergence points

---

## Background

ESS (Equity Summary Score) is the StarMine analyst consensus signal sourced from Fidelity. It is the **primary signal in the composite score** (55% weight per UI tooltip). It surfaces in six distinct locations across the portfolio analysis pipeline. This report audits whether those six locations show the same value for the same symbol and identifies where intentional or accidental divergence can occur.

---

## The Six ESS Surfaces

| # | Surface | Source field | Code location |
|---|---|---|---|
| 1 | Security Overlays table (overlay tab) | `security_overlays[].ess_score_text` | `renderSecurityOverlays()` app.js L1682 |
| 2 | Holdings table ESS column | `recommendations[].drilldown.holdings[].ess_score_text` | `renderHoldingsTable()` app.js L1256 |
| 3 | Signal Agreement panel (ESS row) | `security_overlays[].ess_score_text` via `_computeSignalAgreement()` | app.js L960 |
| 4 | Fidelity signal panel (in holdings drilldown) | `fidelity_signals_by_symbol[sym].ess_text` | `_fidelityPanelHtml()` app.js |
| 5 | Deployment Queue signal profile (ESS card) | `ov.ess_score_text` (overlay lookup) with fallback `c.ess_score_text` | app.js L2368 |
| 6 | Score tooltip explanation | `ov.ess_score_text` | app.js L1162 |

---

## Data Source for Each Surface

### Surfaces 1, 2, 3, 5, 6 — Overlay-sourced ESS

All read from `SecurityIntelligenceOverlay.ess_score_text`, which is built by this chain:

```
signal_snapshot.csv (ess_category col)
  └─► enrich_holdings() → PortfolioHolding.ess_score_text
        └─► build_security_overlays() recommendations.py ~L196
              ├─ Primary: h.ess_score_text (from signal_snapshot at enrichment time)
              └─ Fallback (if empty): ess_history_master.csv (most recent row per symbol)
```

The fallback fires when:
- The symbol is absent from `signal_snapshot.csv` (universe gap)
- The symbol is present but classified `NON_STARMINE_ANALYST` (suppressed)
- `ess_category` field is blank for the row

The resulting value is stored in `security_overlays.csv` per run and returned in the live API response.

### Surface 4 — Fidelity panel ESS

Read from `_build_fidelity_payload()` in `runner.py`, which loads `data/current/signal_snapshot.csv` directly (via `load_fidelity_signals()`). **No archive fallback is applied.** If the symbol is not in `signal_snapshot.csv`, this surface shows `—`.

---

## Divergence Scenarios

### Scenario A: Symbol absent from `signal_snapshot.csv` but present in archive

**What you see:**
- Surfaces 1/2/3/5/6 show the archived ESS value (e.g. `BULLISH`)
- Surface 4 (Fidelity panel) shows `—`

**Risk:** The archived ESS may be weeks or months old. The overlay will silently present it as if it were current. No staleness indicator is shown on any of the six surfaces.

**Frequency:** Affects symbols classified `NON_STARMINE_ANALYST` (typically non-US-listed stocks where StarMine has no analyst coverage) and any symbol that was recently added to the universe before the next ESS harvest.

**Where in code:** [src/portfolio/recommendations.py](src/portfolio/recommendations.py#L172-L184) — `_ess_archive` loading; [L196-L200](src/portfolio/recommendations.py#L196-L200) — fallback assignment.

---

### Scenario B: `signal_snapshot.csv` and `analytical_universe.csv` are out of sync

`enrich_holdings()` reads ESS from `analytical_universe.csv` (which itself is built from `signal_snapshot.csv` during a universe rebuild). If a signal refresh has updated `signal_snapshot.csv` but the analytical universe has **not** been rebuilt, then:

- `build_security_overlays()` uses the stale ESS from the un-rebuilt universe
- `_build_fidelity_payload()` uses the fresh `signal_snapshot.csv`
- Surface 4 will show newer ESS; surfaces 1/2/3/5/6 will show older ESS

**Detection:** None. There is no version/date cross-check between `analytical_universe.csv` and `signal_snapshot.csv` in the overlay builder or the runner.

---

### Scenario C: Loaded run vs live run mismatch for Yahoo/Fidelity data

For a loaded run (`load_analysis_run()`):
- `security_overlays` (and thus surfaces 1/2/3/5/6) reflect ESS **at the time the run was originally computed** — they are read from the static `security_overlays.csv` file.
- Surface 4 (`fidelity_signals_by_symbol`) is **always live** — it re-reads `signal_snapshot.csv` at load time.

If a symbol's ESS changed between the original run and now (e.g. `BULLISH` → `NEUTRAL`), the two panels will show conflicting values. The Signal Agreement panel (Surface 3) will compute agreement using the old ESS from the overlay, but the Fidelity panel will show the new value — creating a visible contradiction on screen without any explanation.

---

### Scenario D: `ess_score_text=None` vs `ess_score_text="UNKNOWN"` rendering gap

In `build_security_overlays()`:
```python
ess_score_text=ess if ess != "UNKNOWN" else None,   # L272
```

`None` is stored in the overlay and CSV. The UI renders `None` as `—` via `o.ess_score_text || "—"`. The signal agreement function applies `?? 2` as a neutral fallback for unknown ESS rank. This is consistent.

However, the Deployment Queue signal card (Surface 5) has:
```javascript
const essText = ov.ess_score_text || c.ess_score_text || "—";
```
Where `c` is the deployment queue candidate row. If the candidate row has its own `ess_score_text` from the deployment_queue payload and the overlay row has `null`, the fallback to `c.ess_score_text` could surface a value from a different time-of-computation source. Verify that `deployment_queue.json` candidates also inherit ESS from overlays at overlay-build time.

---

## ESS Influence on Direction and Flags

ESS is the primary signal in `signal_direction` synthesis:

```python
if ess.upper() == "BULLISH":          direction = "BULLISH"
elif ess.upper() == "BEARISH":
    if score is not None and score >= 2.5:
        direction = "NEUTRAL"          # floor-lifted by composite
    else:
        direction = "BEARISH"
elif score is not None:
    if score >= 3.5:   direction = "BULLISH"
    elif score >= 2.0: direction = "NEUTRAL"
    else:              direction = "BEARISH"
else:
    direction = "UNKNOWN"
```

The `opportunity_flag` (TRIM/WATCH/ACCUMULATE/HOLD) and `flag_rationale` flow directly from `direction`, meaning a stale or incorrect ESS (Scenarios A/B/C above) will produce incorrect TRIM and ACCUMULATE flags — the highest-impact UI outputs.

---

## Recommendations

### P1 — Archive fallback staleness indicator
When `build_security_overlays()` uses the archive fallback for a symbol, set a flag or field (e.g. `ess_source = "ARCHIVE"` vs `"LIVE"`) in the overlay and propagate it to the API response. The overlay table should show a small age/source indicator next to the ESS value.

### P2 — Universe / signal_snapshot sync guard
Add an assertion or warning in `run_analysis()` that compares the `build_date` in `analytical_universe.csv` header (or file mtime) against the `sourced_date` in `signal_snapshot.csv`. If the universe is more than N hours older than the signal snapshot, emit a `sti_warnings` entry.

### P3 — Loaded run ESS consistency note
In `load_analysis_run()`, when `security_overlays` are loaded from CSV (static), add a metadata field `"security_overlays_source": "persisted_csv"` and `"fidelity_signals_source": "live"` so the UI can show a temporal mismatch notice in the Fidelity panel.

### P4 — Deployment Queue ESS fallback audit
Confirm that `deployment_queue.json` candidate rows do **not** carry their own `ess_score_text` from a second independent source. If they do, the `ov.ess_score_text || c.ess_score_text` pattern in the UI (app.js L2368) may silently surface an inconsistent value.

---

## Summary Table

| Divergence scenario | Surfaces affected | Silent? | Existing protection | Priority |
|---|---|---|---|---|
| Symbol absent from signal_snapshot; archive used | 1, 2, 3, 5, 6 show archive value; 4 shows `—` | Yes | None | P1 |
| Universe/signal_snapshot rebuild lag | 1–3, 5–6 stale; 4 fresh | Yes | None | P2 |
| Loaded run vs live run ESS version | 4 shows new; 1–3, 5–6 show old | Yes (visible contradiction) | None | P3 |
| `None` vs `"UNKNOWN"` rendering | All surfaces consistent | No | Consistent handling | — |
| DQ candidate ESS fallback source | Surface 5 may use DQ row value | Potentially | Code audit needed | P4 |
