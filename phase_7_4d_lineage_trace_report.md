# Phase 7.4D Lineage Trace Report

**Generated:** 2026-05-31  
**Scope:** Full lineage trace for symbols ATLC and CIEN across 8 pipeline stages  
**Reference run (affected):** PAR-20260531-231817F7  
**Reference run (correct baseline):** PAR-20260531-14F9621B (CLI-generated)  
**Mandate:** Diagnosis only — no code modifications  

---

## Executive Summary

The Phase 7.4D fix (`_load_replay_evidence()` in `src/portfolio/recommendations.py`) is
**correct and working on disk**. When `run_analysis()` is invoked in a fresh Python
process, all 8 gap symbols receive `replay_supported=True` and the `opportunity_flag`
is correctly promoted to `ACCUMULATE`.

The stored run `PAR-20260531-231817F7` — generated at 05:02 AM local on May 31 through
the UI server — shows pre-fix behavior (21 True / 60 False) because **the UI server process
(PID 9026) was started at May 30, 14:47:33 local, more than 8 hours before the fix was
applied at May 30, 23:38 local**. The server cached the pre-fix module in `sys.modules` on
its first request. No restart of the server process occurred before the run was triggered.

**Root cause location:**  
`scripts/run_outcome_ui.py`, line 390 — `from src.portfolio.runner import run_analysis`  
The import is inside a POST handler method and relies on `sys.modules` cache. Because the
server process loaded `src.portfolio.recommendations` before the fix existed, it continued
executing the pre-fix `_load_replay_evidence()` that skipped all industry-specific replay
rows.

---

## Process Timeline

| Time (local, CDT) | Event |
|---|---|
| May 30, 14:47:33 | UI server (PID 9026) started; `run_outcome_ui.py` begins listening on port 8765 |
| May 30, ~15:xx | First portfolio request arrives; `from src.portfolio.runner import run_analysis` executes; pre-fix `recommendations.py` is loaded into `sys.modules` |
| May 30, 23:38:26 | Phase 7.4D fix applied — `recommendations.py` modified on disk |
| May 30, 23:41 | Python compiles new `.pyc` from fixed source; `__pycache__/recommendations.cpython-314.pyc` updated |
| May 31, 05:02 | User triggers new run through UI; server (PID 9026, still running) uses stale pre-fix module from `sys.modules`; `PAR-20260531-231817F7` written with 21 True |
| May 31, ~10:xx | CLI invocation `PYTHONPATH=. python3 -c "... run_analysis(...)"` uses fresh process; correct fixed code runs; produces 46 True in `PAR-20260531-14F9621B` |

---

## Pre-Fix vs. Post-Fix Code: The Exact Discard Point

**File:** `src/portfolio/recommendations.py`  
**Function:** `_load_replay_evidence()`, lines 49–112  

### Pre-fix code (committed baseline — what PID 9026 has in memory):

```python
if os.path.exists(replay_inputs_csv):
    for row in csv.DictReader(open(replay_inputs_csv)):
        if row.get("filter_industry", "").upper() != "ALL":
            continue   # ← ALL industry-specific rows discarded here
        cap = row.get("filter_market_cap_bucket", "")
        geo = row.get("filter_geography", "")
        syms = row.get("selected_symbols", "").split("|")
        for s in syms:
            sym = s.strip().upper()
            if sym and sym not in symbol_tier:
                symbol_tier[sym] = f"{geo}.{cap}"
                symbol_replay[sym] = row.get("replay_id", "")

return {
    "symbol_tier": symbol_tier,
    "symbol_replay": symbol_replay,
    # ← no industry_replay_evidence key
}
```

The `continue` on the third line unconditionally discards every row where
`filter_industry != "ALL"`. ATLC, CIEN, CAH, AVT, NUE, BSVN, PCB, and CBOE all
appear exclusively in industry-specific rows; they are never added to `symbol_tier`
and never returned.

### Post-fix code (on disk — what fresh processes use):

```python
if os.path.exists(replay_inputs_csv):
    with open(replay_inputs_csv, newline="", encoding="utf-8") as _fh:
        for row in csv.DictReader(_fh):
            ind = row.get("filter_industry", "").strip().upper()
            if ind == "ALL":
                if sym not in symbol_tier:
                    symbol_tier[sym] = f"{geo}.{cap}"
                    symbol_replay[sym] = replay_id
            else:
                if sym not in symbol_tier and sym not in industry_replay_evidence:
                    industry_replay_evidence[sym] = {
                        "geo": geo, "cap": cap, "industry": ind,
                        "replay_id": replay_id,
                    }

return {
    "symbol_tier": symbol_tier,
    "symbol_replay": symbol_replay,
    "industry_replay_evidence": industry_replay_evidence,   # ← new key
}
```

---

## Stage-by-Stage Lineage Trace

### Stage 1 — Replay Source Data (`data/current/replay_inputs.csv`)

| Symbol | replay_id | filter_geography | filter_market_cap_bucket | filter_industry |
|---|---|---|---|---|
| ATLC | `REPLAY-2025-05-14-TO-2026-05-14-US-MICRO-FINANCIAL_SERVICES-TOP20-...` | US | MICRO | FINANCIAL SERVICES |
| CIEN | `REPLAY-2025-05-14-TO-2026-05-14-US-MID-TECHNOLOGY-TOP20-...` | US | MID | TECHNOLOGY |

**Finding:** Both symbols exist in `replay_inputs.csv` as industry-specific replay entries.
Neither is present in any `filter_industry=ALL` row.

---

### Stage 2 — `industry_replay_evidence` Dict Population

**Module:** `src/portfolio/recommendations.py`  
**Function:** `_load_replay_evidence()`, lines 85–100  

| Symbol | Expected entry in `industry_replay_evidence` | Present in pre-fix execution | Present in post-fix execution |
|---|---|---|---|
| ATLC | `{geo=US, cap=MICRO, industry=FINANCIAL SERVICES, replay_id=...}` | **NO** (discarded by `continue`) | YES |
| CIEN | `{geo=US, cap=MID, industry=TECHNOLOGY, replay_id=...}` | **NO** (discarded by `continue`) | YES |

**Finding:** In the pre-fix module loaded by PID 9026, `industry_replay_evidence` is always an
empty dict `{}`. Both symbols are discarded at the `continue` on line 60 (pre-fix numbering).

---

### Stage 3 — Holding Enrichment (`enrich_holdings` → `normalize_and_aggregate_holdings`)

**Module:** `src/portfolio/enrichment.py`  
**Function:** `enrich_holdings()`, line 158; `normalize_and_aggregate_holdings()`, line 361  
**Evidence source:** `data/portfolio_ingestion/analysis_runs/PAR-20260531-231817F7/holdings.csv`

| Symbol | geography | market_cap_bucket | industry | operational_state |
|---|---|---|---|---|
| ATLC | US | MICRO | FINANCIAL SERVICES | ACTIVE_POSITION |
| CIEN | US | MID | TECHNOLOGY | ACTIVE_POSITION |

**Finding:** Both symbols are correctly enriched from `data/current/analytical_universe.csv`.
All three tier-matching fields (`geography`, `market_cap_bucket`, `industry`) carry exact values
that would satisfy the Phase 7.4D condition check — if `industry_replay_evidence` were non-empty.

The condition at `build_security_overlays()` lines 150–157:
```python
ev["geo"] == h.geography           # "US" == "US"      ✓
ev["cap"] == h.market_cap_bucket   # "MICRO"=="MICRO"  ✓  (ATLC)
ev["industry"] == (h.industry or "").strip().upper()
# "FINANCIAL SERVICES" == "FINANCIAL SERVICES"         ✓  (ATLC)
```
This condition evaluates to `True` for both symbols in the post-fix execution path.

---

### Stage 4 — `build_security_overlays()` Execution

**Module:** `src/portfolio/recommendations.py`  
**Function:** `build_security_overlays()`, line 116  

#### 4A: PAR-20260531-231817F7 (server, pre-fix module in memory)

| Symbol | `industry_replay_evidence` dict | `in_replay` result | `replay_supported` | `opportunity_flag` |
|---|---|---|---|---|
| ATLC | `{}` (empty) | False | **False** | HOLD |
| CIEN | `{}` (empty) | False | **False** | HOLD |

The check `if not in_replay and sym in industry_replay_evidence` immediately
short-circuits — `industry_replay_evidence` is an empty dict, so `sym in {}` is always
`False`. No symbols are ever promoted via this path.

#### 4B: PAR-20260531-14F9621B (CLI, fresh process, post-fix module)

| Symbol | `industry_replay_evidence` dict | Condition result | `replay_supported` | `opportunity_flag` |
|---|---|---|---|---|
| ATLC | `{geo=US, cap=MICRO, industry=FINANCIAL SERVICES, ...}` | True | **True** | ACCUMULATE |
| CIEN | `{geo=US, cap=MID, industry=TECHNOLOGY, ...}` | True | **True** | ACCUMULATE |

---

### Stage 5 — Persistence to `security_overlays.csv`

**Module:** `src/portfolio/runner.py`  
**Function:** `run_analysis()`, lines 729–734  

```python
if overlays:
    _write_csv(
        str(out_dir / "security_overlays.csv"),
        overlays,
        list(dataclasses.asdict(overlays[0]).keys()),
    )
```

The CSV is written directly from the `overlays` list returned by `build_security_overlays()`.
No transformation or caching occurs between overlay generation and disk write.

| Run | Stored `replay_supported=True` count | Total |
|---|---|---|
| PAR-20260531-231817F7 (server) | **21** | 81 |
| PAR-20260531-14F9621B (CLI) | **46** | 81 |

---

### Stage 6 — `runner.py` Import Chain

**Module:** `src/portfolio/runner.py`, line 40  
```python
from .recommendations import build_security_overlays, generate_recommendations, ...
```
This is a top-level module import. When `runner.py` is loaded, it binds
`build_security_overlays` to whatever `recommendations.py` was in `sys.modules` at
server startup time.

Because PID 9026 started at **May 30, 14:47:33** (pre-fix), this binding resolved to the
pre-fix `build_security_overlays`. Subsequent calls through the server always invoke the
stale function.

---

### Stage 7 — Alignment Data (No Replay Involvement)

**File:** `data/portfolio_ingestion/analysis_runs/PAR-20260531-231817F7/alignment.csv`

Alignment results have no replay-related columns. The `overweight_nodes` set used in
`build_security_overlays()` comes from alignment but does not affect `replay_supported`.
ATLC and CIEN are not in any overweight node. This stage is not involved in the discard.

---

### Stage 8 — `load_analysis_run()` (Read Path)

**Module:** `src/portfolio/runner.py`  
**Function:** `load_analysis_run()`, lines 948–995  

```python
opath = run_dir / "security_overlays.csv"
if opath.exists():
    result["security_overlays"] = list(csv.DictReader(open(opath)))
```

The UI's `/api/portfolio/runs/{id}` endpoint reads stored artifact files — no
recomputation. The `replay_supported=False` values written at Stage 5 are faithfully
served back to the UI. This stage is not involved in the discard; it only reflects the
already-wrong stored data.

---

## Divergence Table

| Stage | ATLC | CIEN | Expected | Actual (run PAR-20260531-231817F7) |
|---|---|---|---|---|
| 1. `replay_inputs.csv` | Present (MICRO/FINANCIAL SERVICES) | Present (MID/TECHNOLOGY) | Present | Present ✓ |
| 2. `industry_replay_evidence` | Should be `{geo=US, cap=MICRO, industry=FINANCIAL SERVICES}` | Should be `{geo=US, cap=MID, industry=TECHNOLOGY}` | Non-empty | **Empty `{}`** ← DISCARD POINT |
| 3. Holding fields | geo=US, cap=MICRO, industry=FINANCIAL SERVICES | geo=US, cap=MID, industry=TECHNOLOGY | Correct | Correct ✓ |
| 4. `replay_supported` | True | True | True | **False** |
| 5. `security_overlays.csv` | replay_supported=True, flag=ACCUMULATE | replay_supported=True, flag=ACCUMULATE | ACCUMULATE | **False / HOLD** |
| 6. Runner import | Fixed `build_security_overlays` | Fixed `build_security_overlays` | Post-fix | **Pre-fix (stale in-memory)** |
| 7. Alignment | No replay involvement | No replay involvement | N/A | N/A |
| 8. `load_analysis_run()` | Reads stored False | Reads stored False | True | **False (read from disk)** |

**Discard point: Stage 2** — `_load_replay_evidence()` returns `industry_replay_evidence={}` because the pre-fix module in PID 9026's `sys.modules` contains the `continue` guard that discards all `filter_industry != "ALL"` rows.

---

## Exact Module and Field of Discard

| Attribute | Value |
|---|---|
| **File** | `src/portfolio/recommendations.py` |
| **Function** | `_load_replay_evidence()` |
| **Pre-fix line** | Line 60 (committed baseline): `continue` inside `if row.get("filter_industry", "").upper() != "ALL":` |
| **Field affected** | `industry_replay_evidence` — dict is never populated; returned as `{}` |
| **How discard propagates** | `build_security_overlays()` receives empty dict; `sym in industry_replay_evidence` is always `False`; `in_replay` stays `False` for all 25 industry-specific symbols |
| **Root cause** | UI server PID 9026 was started May 30, 14:47:33 (pre-fix); `sys.modules` cache holds stale pre-fix module; server was never restarted after fix was written at 23:38 |

---

## Affected Symbols (Full List)

All 25 symbols with `replay_supported=True` in the CLI run but `False` in the server run are
exclusively in `industry_replay_evidence` (not in `symbol_tier`):

```
AGEN, ALNT, ANGO, ANIP, ATLC, AVT, AZZ, BSVN, CAH, CBOE,
CIEN, CMCO, CRS, DVN, FSLR, GFF, HALO, MTZ, NUE, PCB,
STLD, UHS, UTHR, XYZ, YELP
```

Gap symbols (original Phase 7.4D scope): ATLC, BSVN, PCB, CIEN, CAH, AVT, NUE, CBOE — all 8 confirmed affected.

---

## Required Remediation

**Action:** Kill and restart the UI server process. The fix is already correct on disk. No
code changes are needed.

```bash
kill 9026
PYTHONPATH=. python3 scripts/run_outcome_ui.py --port 8765
```

After restart, the next portfolio analysis triggered through the UI will produce
`replay_supported=True` for all 25 industry-specific replay symbols, matching the CLI
baseline of 46/81.

---

*Report generated by Phase 7.4D diagnostic — diagnosis only, no code modified.*
