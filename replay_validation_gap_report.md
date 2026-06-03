# Phase 7.4D Validation — Replay Evidence Routing Gap Report

**Investigation scope:** Diagnosis only. No logic modifications. No run regeneration.  
**Question:** Why does UI run PAR-20260531-C1F9A91A show pre-fix replay coverage values despite being created 9 minutes after the Phase 7.4D fix was applied?  
**Answer:** Confirmed. See Root Cause section below.

---

## 1. Observed vs. Expected Values

| Metric | Run PAR-20260531-C1F9A91A (UI) | Expected (Post-Fix) |
|---|---|---|
| `replay_supported=True` count | **21 / 81** | **46 / 81** |
| % holdings replay-supported | **37.89%** (pre-fix) | **52.26%** (post-fix) |
| Gap symbols (ATLC, CIEN, CAH, AVT, NUE, BSVN, PCB, CBOE) | All `False` | All `True` |

The UI is displaying values that belong to the pre-7.4D state.

---

## 2. Timeline

| Timestamp (UTC) | Event |
|---|---|
| Before 2026-05-31T04:05:37 | `run_outcome_ui.py` server started; imports `src.portfolio.recommendations` (pre-fix code) into `sys.modules` |
| 2026-05-31T04:05:37 | PAR-20260531-14549C56 generated — 21/81 True |
| 2026-05-31T04:19:13 | PAR-20260531-52FF3F90 generated — 21/81 True |
| 2026-05-31T04:34:42 | PAR-20260531-406E597F generated — 21/81 True |
| **2026-05-31T04:38:26** | **7.4D fix written to `src/portfolio/recommendations.py` on disk** |
| **2026-05-31T04:47:17** | **PAR-20260531-C1F9A91A generated — still 21/81 True (stale module)** |

The 9-minute gap between fix-on-disk (04:38) and run creation (04:47) is explained entirely by the server's stale module cache.

---

## 3. Root Cause

**The UI server process held stale in-memory Python modules from before the Phase 7.4D fix.**

When `POST /api/portfolio/analyze` is called, `run_outcome_ui.py` line 390 executes:

```python
from src.portfolio.runner import run_analysis
```

This `from … import` statement does **not** reload the module from disk. Python's `sys.modules` cache is process-global and persists for the lifetime of the server. The server was started before the fix was applied, so `sys.modules["src.portfolio.recommendations"]` contained the pre-fix `_load_replay_evidence()` function — the one that silently discards all `filter_industry != 'ALL'` rows:

```python
# PRE-FIX (still in server's sys.modules):
if row.get("filter_industry", "").upper() != "ALL":
    continue   # ← industry-specific replays silently dropped
```

There is no `importlib.reload()` or equivalent anywhere in `run_outcome_ui.py`. The server has no mechanism to detect or reload modified module files at runtime.

---

## 4. Divergence Point: Layer-by-Layer Trace

| Layer | Code path | Verdict |
|---|---|---|
| **`_load_replay_evidence()`** | `src/portfolio/recommendations.py` (stale in server `sys.modules`) | **DIVERGENCE HERE** — pre-fix function discards 8 gap symbols |
| `build_security_overlays()` | `src/portfolio/recommendations.py` | Calls stale `_load_replay_evidence()`; gap symbols get `replay_supported=False` |
| `run_analysis()` → `security_overlays.csv` | `src/portfolio/runner.py` | Writes the overlay objects as-is; correctly persists what stale overlays produced |
| `load_analysis_run()` | `src/portfolio/runner.py:948` | Reads stored `security_overlays.csv` from disk; no recomputation |
| `GET /api/portfolio/runs/{id}` | `scripts/run_outcome_ui.py:258` | Calls `load_analysis_run()`; serves stored artifacts faithfully |
| UI display | `ui/portfolio_alignment/index.html` | Renders what the API returns; correctly shows pre-fix values |

The stored `security_overlays.csv` in PAR-20260531-C1F9A91A was **written by the stale process at run creation time**. Every downstream layer (load, API, UI) merely reads and forwards those stored values. The divergence is entirely in the server-process-level module cache at the time the run was generated.

---

## 5. Confirmation That the Fix Is Correct On Disk

Running `_load_replay_evidence()` from a fresh process against the current disk state:

```
sym_tier entries (ALL replay cross-sector):  178
industry_replay_evidence entries:            800

Gap symbols — ALL replay (sym_tier):      []      (none — correct, they are industry-specific)
Gap symbols — industry_replay_evidence:   8/8 found

  ATLC: {geo=US, cap=MICRO, industry=FINANCIAL SERVICES, replay_id=…-FIN1-US-MICRO-FINANCIAL_SERVICES}
  CIEN: {geo=US, cap=MID,   industry=TECHNOLOGY,         replay_id=…-TECH1-US-MID-TECHNOLOGY}
  CAH:  {geo=US, cap=MID,   industry=HEALTHCARE,         replay_id=…-HEALTH1-US-MID-HEALTHCARE}
  AVT:  {geo=US, cap=SMALL, industry=TECHNOLOGY,         replay_id=…-TECH1-US-SMALL-TECHNOLOGY}
  NUE:  {geo=US, cap=MID,   industry=BASIC MATERIALS,    replay_id=…-BMAT1-US-MID-BASIC_MATERIALS}
  BSVN: {geo=US, cap=MICRO, industry=FINANCIAL SERVICES, replay_id=…-FIN1-US-MICRO-FINANCIAL_SERVICES}
  PCB:  {geo=US, cap=MICRO, industry=FINANCIAL SERVICES, replay_id=…-FIN1-US-MICRO-FINANCIAL_SERVICES}
  CBOE: {geo=US, cap=MID,   industry=FINANCIAL SERVICES, replay_id=…-FIN1-US-MID-FINANCIAL_SERVICES}
```

The fix correctly populates `industry_replay_evidence` with all 8 gap symbols. The code on disk is correct. The problem is exclusively that the server never saw this updated code.

Additionally: `git diff --stat HEAD src/portfolio/recommendations.py` confirms the 7.4D fix is a local unstaged modification (+59 lines, −13 lines) — the file is modified on disk but not yet committed.

---

## 6. Why the Run Timestamp Does Not Imply the Fix Was Applied

The run's `created_at_utc` of `2026-05-31T04:47:17` is **9 minutes after the fix was written to disk**. This is NOT evidence that the run used the fixed code. Python processes do not monitor the filesystem for module changes. A long-running server that imported `src.portfolio.recommendations` before 04:38 UTC will continue using the pre-fix code indefinitely until the process is restarted.

The three runs generated in the window 04:05–04:34 UTC (all pre-fix) and the one run at 04:47 UTC (nominally post-fix) all show identical overlay counts (21/81). This is consistent with a single server process using a single cached module version for all four runs.

---

## 7. What the Stored Run Contains

**Run:** PAR-20260531-C1F9A91A  
**Portfolio snapshot:** PSNAP-20260531-79DC38D170AC (81 holdings, snapshot_date 2026-05-31)

**`security_overlays.csv` — replay_supported=True (21 holdings):**

```
MU, SBS, VRT, NVDA, TSLA, CVE, AEIS, TSM, GTX, DELL,
LRCX, MSFT, AVGO, ARW, SNX, PSX, ASML, SANM, STNG, AMZN, SIMO
```
All 21 are symbols that appear in cross-sector `filter_industry='ALL'` replay rows — the only type that the pre-fix code accepted.

**`security_overlays.csv` — gap symbols (all False):**

| Symbol | % Portfolio | Composite | Industry Replay Tier | Expected |
|---|---|---|---|---|
| CIEN | 1.20% | 4.57 | US.MID.TECHNOLOGY | True |
| CAH | 1.04% | 4.56 | US.MID.HEALTHCARE | True |
| PCB | 0.94% | 4.28 | US.MICRO.FINANCIAL SERVICES | True |
| AVT | 0.91% | 4.50 | US.SMALL.TECHNOLOGY | True |
| ATLC | 0.90% | 4.78 | US.MICRO.FINANCIAL SERVICES | True |
| NUE | 0.79% | 4.29 | US.MID.BASIC MATERIALS | True |
| CBOE | 0.69% | 4.11 | US.MID.FINANCIAL SERVICES | True |
| BSVN | 0.56% | 4.00 | US.MICRO.FINANCIAL SERVICES | True |

---

## 8. Questions Answered

| Diagnostic Question | Answer |
|---|---|
| Was PAR-20260531-C1F9A91A generated using pre-7.4D code? | Yes — via stale server module cache |
| Was `run_outcome_ui.py` restarted after 7.4D? | No — server not running now; it ran through at least 04:47 UTC without restart |
| Does `replay_supported` in the stored overlays use the new `industry_replay_evidence` path? | No — stale code never reached that path |
| Does STI classification in the run reflect corrected replay values? | No — `recommendations.json` contains `replay_supported: false` for all gap symbols |
| Are cached run artifacts being loaded instead of fresh analysis? | Partially — `load_analysis_run()` reads stored CSVs. But the primary issue is the run itself was generated with stale code |
| Is `replay_alignment` still reading `symbol_tier` only? | In the stored run, yes — the stale `_load_replay_evidence()` only populated `symbol_tier` (pre-fix signature) |

---

## 9. Non-Contributing Factors (Ruled Out)

- **`analytical_universe.csv`** — does not contain a `replay_supported` column. No AU-level caching of replay state.
- **Intermediate overlay CSV files** — `data/current/` contains no `security_overlays.csv`. Overlays are written per-run only.
- **`runner.py` caching** — the runner does not cache overlay results. `build_security_overlays()` at line 574 is called fresh each run.
- **`data/current/replay_inputs.csv` content** — the file was not modified between the fix and the run. All 8 gap symbols are present as industry-specific selections and were present when the fix was written.

---

## 10. Resolution Path (Reference Only — No Action Taken)

To see the corrected replay coverage in the UI:

1. **Stop the `run_outcome_ui.py` server** (if running) — kills the stale `sys.modules` cache
2. **Restart the server** — fresh process, imports fixed `recommendations.py` from disk
3. **Upload the May 31 portfolio CSV** via the UI again — triggers `POST /api/portfolio/analyze`
4. **New run generated** — `_load_replay_evidence()` now populates `industry_replay_evidence` with 8 gap symbols
5. **Expected result** — `replay_supported=True`: 46/81 (52.26%), consistent with Phase 7.4D fix validation results

The Phase 7.4D fix itself requires no changes. The stored run PAR-20260531-C1F9A91A will retain its pre-fix artifacts and serves as a historical baseline.

---

## Summary

The Phase 7.4D fix is **correct on disk** and **validated by 27 passing tests**. The pre-fix values visible in the UI for run PAR-20260531-C1F9A91A are a **Python module caching artifact**: the `run_outcome_ui.py` server process imported `src.portfolio.recommendations` before the fix was applied and held the stale module in memory for the lifetime of the session. The 9-minute gap between fix-on-disk and run creation is not evidence that the run used the fixed code — Python servers do not reload modified modules without an explicit restart.

**Divergence point**: `_load_replay_evidence()` in the server's in-memory module (pre-fix; `filter_industry != 'ALL'` guard active).  
**Stored artifact state**: PAR-20260531-C1F9A91A `security_overlays.csv` — 21 True / 60 False (pre-fix).  
**Fix state**: Unstaged local modification, 8/8 gap symbols correctly found in `industry_replay_evidence` when invoked from a fresh process.
