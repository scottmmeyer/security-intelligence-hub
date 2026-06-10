# Zacks Staleness Logic Audit

**Date:** 2026-06-10

---

## 1. `_signal_status()` — Freshness Badge Logic

**File:** `scripts/run_outcome_ui.py` lines 213–285

**What it checks:**
```python
_SIGNAL_FILES = {
    "zacks": _REPO_ROOT / "data/signals/zacks/latest_zacks.csv",
    ...
}

sd = _sourced_date(path)   # → max(sourced_date) across ALL rows in latest_zacks.csv
entry["stale"] = sd != today
if sd == today and coverage >= 95%:
    badge_state = "FRESH"
elif sd == today:
    badge_state = "FRESH_PARTIAL"
else:
    badge_state = "STALE"
```

**Source checked:** Source 1 (direct Zacks, `latest_zacks.csv`) ONLY.  
**Fidelity ESS Zacks involvement:** **NONE.** The Fidelity-embedded `ess_zacks_rating` field does not touch `latest_zacks.csv` and cannot affect this badge.

**Verdict on Q3 (Can Fidelity make Zacks appear FRESH?):**  
**For the freshness badge: NO.** The badge is based solely on `latest_zacks.csv` which only contains directly fetched data.

---

## 2. `_sourced_date()` — Date Determination

**File:** `scripts/run_outcome_ui.py` lines 53–68

```python
def _sourced_date(csv_path: Path) -> str | None:
    latest: str | None = None
    for row in csv.DictReader(fh):
        val = str(row.get("sourced_date", "")).strip()
        if val and (latest is None or val > latest):
            latest = val
    return latest
```

**Problem identified:** Returns the **maximum** sourced_date across ALL rows — not the date for any specific symbol. Today (2026-06-10), 122 of 2,647 symbols have been fetched. The remaining 2,525 symbols have dates ranging from 2026-05-26 to 2026-06-09.

**The badge shows FRESH as soon as ANY symbol has been fetched today** — even if 95% of the portfolio's symbols still have Zacks data from weeks ago. This is a **portfolio coverage gap** in the freshness logic, though it doesn't involve Fidelity ESS data.

---

## 3. `_build_signal_source_metadata()` — Runner Metadata

**File:** `src/portfolio/runner.py` lines 1328–1353

```python
"zacks_refresh_date": _latest_date(_ZACKS_LATEST, "sourced_date"),
```

**Same behavior:** Returns the max date across all rows in `latest_zacks.csv`. Used to populate `signal_source_metadata.zacks_refresh_date` which appears in DIL evidence labels.

**Impact:** DIL shows `Zacks: 1.0 [Zacks, {max_date}]` regardless of whether the specific symbol's Zacks data was fetched on that date or months earlier.

---

## 4. `_score_from_inputs()` — Fallback Logic

**File:** `src/history/analytical_universe_manager.py` lines 344–389

```python
# If direct Zacks is available:
if zacks_score_raw and 1.0 <= zacks_score_raw <= 5.0:
    zacks_score = zacks_score_raw     # from latest_zacks.csv
    zacks_available = True
# Fallback to Fidelity ESS embedded Zacks:
elif ...:
    ess_zacks_raw = float(ess_zacks_rating)
    if ess_zacks_raw and 1.0 <= ess_zacks_raw <= 5.0:
        zacks_score = round(6.0 - ess_zacks_raw, 2)  # inverted scale
        zacks_available = True
# Last resort:
else:
    zacks_score = 3.0    # NEUTRAL default
    zacks_available = False
```

**Impact on scoring:** Fidelity ESS Zacks IS used in composite score calculation when direct Zacks is absent. However, this is scoring (not display freshness). The `zacks_available` flag is used for composite score weighting only — it does not propagate to any display or badge.

**No source tag:** When `ess_zacks_rating` is used, the `zacks_rating` field in `analytical_universe.csv` is set to `""` (empty) — the composite score is computed using the fallback, but the raw field is left blank. This means the fallback is invisible in the data artifacts.

---

## 5. DIL Evidence Date — `computeDIL()` in app.js

**File:** `ui/portfolio_alignment/app.js`

The DIL engine uses:
```javascript
const meta = (_lastAnalysisData && _lastAnalysisData.signal_source_metadata) || {};
// ... later:
evidence.push(`Zacks: ${zacks.toFixed(1)} [Zacks, ${today_str}]`);
```

**Current behavior:** DIL shows the current date as the Zacks evidence date. It does not use `signal_source_metadata.zacks_refresh_date` for per-symbol dating. It uses `today_str` computed from `new Date()`. This is **incorrect** — the date shown is the display date, not the sourced date.

---

## Summary of Audit Findings

| Check | Finding | Severity |
|---|---|---|
| Can Fidelity ESS make Zacks FRESH badge? | No — badge reads `latest_zacks.csv` only | ✓ CLEAN |
| Does `_sourced_date()` use per-symbol dates? | No — uses max date across all rows | ⚠ MISLEADING |
| Is Fidelity ESS fallback used in scoring? | Yes — when direct Zacks absent | ✓ CORRECT (by design) |
| Is Fidelity ESS fallback flagged/labeled? | No — invisible in analytical_universe | ⚠ GOVERNANCE GAP |
| Does DIL show correct per-symbol Zacks date? | No — shows `today_str` not sourced date | ⚠ MISLEADING |
| Does portfolio runner correctly identify Zacks source? | No per-symbol provenance field | ⚠ GOVERNANCE GAP |
| Can PRIM show Zacks from 2026-05-21 labeled as "Zacks, 2026-06-10"? | Yes, currently | ⚠ MISLEADING |
