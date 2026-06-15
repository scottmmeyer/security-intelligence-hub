# AI-006 Danelfin Visibility Audit

**Date:** 2026-06-15  
**PAR:** PAR-20260615-FF5E50AF

---

## Q1-Q4: Actual Danelfin Scores

| Symbol | Danelfin Raw (1-10) | Danelfin Score (1-5) | Sourced Date | In Overlays? |
|--------|--------------------|-----------------------|-------------|-------------|
| CAH | **5** | **2.5000** | 2026-06-15 | YES |
| NUE | **7** | **3.5000** | 2026-06-15 | YES |
| SANM | **8** | **4.0000** | 2026-06-15 | YES |
| MTZ | **9** | **4.5000** | 2026-06-15 | YES |
| VRT | 7 | 3.5000 | 2026-06-15 | YES |
| ATLC | 6 | 3.0000 | 2026-06-15 | YES |
| DELL | 5 | 2.5000 | 2026-06-15 | YES |
| LRCX | 6 | 3.0000 | 2026-06-12 | YES |
| PCB | 7 | 3.5000 | 2026-06-12 | YES |
| CRS | 8 | 4.0000 | 2026-06-12 | YES |

---

## Q5: Data Store Presence

| Store | Present | Details |
|-------|---------|---------|
| `data/signals/danelfin/latest_danelfin.csv` | YES | 2,661 rows, sourced 2026-06-15 |
| `security_overlays.csv` (PAR) | YES | `danelfin_score` populated for all holdings |
| Deployment API payload | YES | `security_overlays` array in run response includes `danelfin_score` |
| Recommendation payload | YES | `security_overlays` in run result at `run['security_overlays']` |
| Holdings overlay payload | YES | `security_overlays` keyed by symbol in `_ovBySymbol` in UI |
| `fidelity_signals_by_symbol` | NO | This payload reads only from signal_snapshot.csv (StarMine ESS); Danelfin is NOT in fidelity_signals_by_symbol |
| `danelfin_refresh_date` in metadata | YES | `runner.py:1753` includes `_latest_date(_DANELFIN_LATEST, "sourced_date")` |

**Critical finding:** Danelfin is NOT available in `fidelity_signals_by_symbol`. This payload is loaded by the Signal Agreement panel and holdings table. The Danelfin score for the Signal Agreement panel is sourced from `security_overlays`, not `fidelity_signals_by_symbol`. Any UI code path that depends on `fs.danelfin_score` (from fidelity_signals payload) will fail to find it — it must use `ov.danelfin_score` (from security_overlays).

---

## Q6: UI Rendering Paths

**Danelfin is rendered in the following UI locations** (all in `ui/portfolio_alignment/app.js`):

| Location | Code | Reads From | Status |
|----------|------|-----------|--------|
| Signal Agreement Panel (4-signal table) | L2343-2372 | `ov.danelfin_score` (security_overlays) | ✓ WORKS |
| Signal Freshness row | L2507 | `meta.danelfin_refresh_date` | ✓ WORKS |
| Deployment Queue signal card | L4455-4472 | `ov.danelfin_score` | ✓ WORKS |
| Holdings table signal corroboration | L4750 | `ovObj.danelfin_score` | ✓ WORKS |
| "Why It Is Working" explainability | L4879-4893 | `ovObj.danelfin_score` | ✓ WORKS |
| Reduction Queue profile | L5137, L5211 | `ov.danelfin_score` | ✓ WORKS |
| Holdings overlay scoring | L5841, L5887 | `ov.danelfin_score` | ✓ WORKS |

**The observed "missing Danelfin" in some operator views is likely a display issue, not a data issue.** All eight rendering paths read from `ov.danelfin_score` which is confirmed populated. If an operator sees a blank Danelfin field, it is likely because they are viewing a PAR run that predates today's Danelfin fetch (LRCX, PCB data is from 2026-06-12, not 2026-06-15).

---

## Q7: Root Cause of Any Missing Display

**Not a data gap.** Danelfin is present and populated. However, two conditions can produce a blank display:

1. **Symbol not in latest_danelfin.csv** — international/EM symbols without Danelfin coverage
2. **Stale run** — viewing a PAR generated before Danelfin data was fetched today (LRCX and PCB show 2026-06-12)

**No UI fix required.** The rendering paths are correct.

**One improvement opportunity (not required):** The `fidelity_signals_by_symbol` payload does not include Danelfin. This means if any UI code mistakenly reads `fs.danelfin_score` instead of `ov.danelfin_score`, it will show `undefined`. Current code correctly reads from `ov`, so this is a latent risk rather than an active bug.
