# ISSUE-08 — Data Flow Validation Report

**Date:** June 5, 2026

---

## Pipeline: Source → Storage → Model → API → UI

```
yfinance ticker.info["numberOfAnalystOpinions"]
  └── fetch_yahoo_supplemental() → result["analyst_count"]
        └── fetch_yahoo_supplemental_for_symbols() → row["analyst_count"]
              └── _write_csv() → latest_yahoo_supplemental.csv (column: analyst_count)
                    └── load_analyst_consensus() → AnalystConsensus.analyst_count
                          └── runner._build_consensus_payload() → analyst_count in dict
                                └── analyst_consensus_by_symbol[sym]["analyst_count"]
                                      ├── _dqAnalystTargetHtml(ac) → "Coverage: N analysts"
                                      └── _consensusPanelHtml(ac) → analyst count field
```

---

## Step-by-Step Validation

### Step 1: yfinance Source

**Test:** `yf.Ticker('DELL').info["numberOfAnalystOpinions"]`  
**Result:** `23`  
**Status:** ✅ Field exists in yfinance for large-cap equities

### Step 2: fetch_yahoo_supplemental() Returns Field

**Test:** `fetch_yahoo_supplemental("DELL")["analyst_count"]`  
**Expected:** `23` (int or None)  
**Status:** ✅ Field populated via `int(info.get("numberOfAnalystOpinions"))`

### Step 3: CSV Storage

**File:** `data/signals/yahoo/latest_yahoo_supplemental.csv`  
**Header:** `symbol,price_target,abr,analyst_count,eps_growth_5yr,current_price,upside_pct,sourced_date`

| Symbol | analyst_count | price_target | upside_pct |
|--------|--------------|--------------|------------|
| DELL | 23 | 483.83 | 22.7 |
| NVDA | 58 | 298.07 | 45.3 |
| MSFT | 55 | 560.95 | 34.6 |
| TSLA | 41 | 411.89 | 5.3 |
| VRT | 25 | 376.80 | 25.4 |
| LRCX | 32 | 316.19 | 4.3 |
| PSX | 19 | 190.58 | 4.1 |
| AEIS | 9 | 393.89 | 33.6 |

**Status:** ✅ Column present and populated for all 53 portfolio symbols

### Step 4: Model Loading

**Test:** `load_analyst_consensus(path)["DELL"].analyst_count`  
**Expected:** `23`  
**Result:** `23`  
**Status:** ✅ `_int("analyst_count")` correctly parses the string "23" to int

### Step 5: API Payload

**Endpoint:** `GET /api/portfolio/runs/PAR-20260605-BC438F9E`  
**Key:** `analyst_consensus_by_symbol["DELL"]["analyst_count"]`  
**Result:** `23`  
**Status:** ✅ `runner._build_consensus_payload()` already emits `analyst_count`

### Step 6: ATI Block (ISSUE-10)

**ATI block items after row expand:**
```
[Target: $483.83]  [Upside: +22.7%]  [Coverage: 23 analysts]  [Sourced: 2026-06-05]
```

**Coverage row visible:** ✅  
**Status:** ✅ No ISSUE-10 code changes needed — field was pre-wired

### Step 7: Recommendation Panel

`_consensusPanelHtml(ac)` references `ac.analyst_count`. The field is populated in the `ac` dict from the API response.

**Status:** ✅ Will render when recommendation cards are expanded

---

## Graceful Degradation Verified

Symbols without Yahoo coverage (e.g., international ADRs with limited analyst coverage, small-caps) will have `analyst_count = null`. The ATI block hides the Coverage row cleanly. Verified with synthetic test case in ISSUE-10 validation.

---

## Coverage Counts (Portfolio Sample)

| Symbol | Count | Coverage level |
|--------|-------|----------------|
| NVDA | 58 | Very high |
| MSFT | 55 | Very high |
| TSLA | 41 | Very high |
| MU | 37 | High |
| AVGO | 36 | High |
| LRCX | 32 | High |
| PLTR | 27 | High |
| VRT | 25 | Moderate-high |
| DELL | 23 | Moderate-high |
| AEIS | 9 | Moderate |
| PCB | 2 | Low — thin coverage |

PCB (Pacific Continental Corp) shows 2 analysts — this is exactly the case where analyst_count provides critical context: a STRONG BUY from 2 analysts is very different from 23.
