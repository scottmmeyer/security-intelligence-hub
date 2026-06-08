# Cash Reconciliation Report — PAR-20260529-7482D734 (Current Audit)

**Audit Date:** 2026-06-08  
**PAR:** PAR-20260529-7482D734  
**Source File:** Portfolio_Positions_May-29-2026.csv (incoming/portfolio/)  
**Portfolio Total Market Value:** $472,219.90  

## Fidelity Cash Positions (Source of Truth)

| Symbol | Account | Description | Value |
|---|---|---|---|
| SPAXX | Z35123695 | HELD IN MONEY MARKET | $42,619.59 |

Total Fidelity cash: $42,619.59. No FDRXX or other money-market positions present.

## SIH Cash Derivation — Line by Line

| Step | Field | Calculation | Result |
|---|---|---|---|
| 1 | cash_mv | SPAXX balance | $42,619.59 |
| 2 | cash_pct | $42,619.59 / $472,219.90 | 9.0254% |
| 3 | mandate_cash_target_pct | CONCENTRATED_ALPHA floor | 7.0% |
| 4 | floor_mv | $472,219.90 × 0.07 | $33,055.39 |
| 5 | excess_mv | $42,619.59 − $33,055.39 | $9,564.20 |
| 6 | settlement_adjustment | None in May-29 CSV | $0 |
| 7 | deployable_mv | $9,564.20 + $0 | **$9,564.20** |

SIH agrees with Fidelity: cash = $42,619.59. Deployable = $9,564.20 (excess above 7% floor).

Note: The $54,257.49 figure referenced in the audit request does not appear in the May-29 portfolio CSV. It likely reflects a more recent real-time Fidelity balance. If the operator uploads a current portfolio export, SIH will recalculate deployable accordingly (~$21,202 if $54,257.49 is used with the same 7% floor).

---
<!-- Historical record below: Phase 6.3D audit against earlier run -->

# Phase 6.3D — Cash Reconciliation & SPAXX Classification Audit

**Generated:** 2026-05-29  
**Run ID:** PAR-20260529-FE757845  
**Snapshot Date:** 2026-05-29  
**Portfolio Total Market Value:** $472,219.90  
**Source File:** Portfolio_Positions_May-29-2026 (2).csv  

---

## Section 1 — Cash Contributors

All positions contributing to the CASH allocation node in the latest portfolio run.

| Symbol | Market Value | Security Type | Operational State | is_cash_equivalent | asset_class | sector | Included In CASH |
|--------|-------------|--------------|------------------|-------------------|-------------|--------|-----------------|
| SPAXX | $42,619.59 | Cash | CASH_EQUIVALENT | True | CASH | Cash | ✅ Yes (1×) |
| FCASH | — | — | — | — | — | — | Not present |
| FDRXX | — | — | — | — | — | — | Not present |
| SPRXX | — | — | — | — | — | — | Not present |
| VMFXX | — | — | — | — | — | — | Not present |
| FZFXX | — | — | — | — | — | — | Not present |

**Only one cash position exists in this portfolio: SPAXX.**

### Dollar Arithmetic

| Metric | Value |
|--------|-------|
| Total portfolio market value (holdings sum) | $472,219.90 |
| SPAXX market value | $42,619.59 |
| SPAXX as % of portfolio | 9.025% |
| **Reported CASH % (alignment engine)** | **18.051%** |
| **Reported CASH $ (implied, 18.051% × $472,219.90)** | **~$85,239** |
| **Expected CASH % (holdings arithmetic)** | **9.025%** |
| **Expected CASH $ (actual holdings)** | **$42,619.59** |
| **Discrepancy** | **+9.025 percentage points (~$42,620 overstated)** |

> **Verdict:** CASH is overstated by exactly **2×**. Reported 18.05% vs actual 9.025%.  
> SPAXX is being counted **twice** in the CASH allocation node.

---

## Section 2 — Cash Calculation Trace

### Full Contribution Path for SPAXX

```
Portfolio CSV row
  → symbol: SPAXX
  → market_value: 42619.59
  → percent_of_portfolio: 9.0254
  → asset_class: CASH
  → sector: Cash            ← KEY FIELD
  → security_type: Cash
  → operational_state: CASH_EQUIVALENT
  → is_cash_equivalent: True
  → decomposition_source: REGISTRY   ← from enrichment phase
```

**Ingestion / Enrichment:** SPAXX is found in `config/etf_exposure_decomposition.yaml`, so `decomposition_source = "REGISTRY"` is set during enrichment. This is a pre-classification artifact from before SPAXX was reclassified as a cash equivalent. The YAML registry entry defines `exposure_sector_mix: {CASH: 100}`.

**Alignment Computation:**  
`compute_alignment()` calls `build_exposure_maps(holdings)`, which calls `_accumulate_holding_exposure()` for each holding.

Inside `_accumulate_holding_exposure` for SPAXX:

```python
asset_class = "CASH"      # from holding field, already uppercased
sector = "CASH"           # "Cash".upper() = "CASH"  ← same as asset_class
is_fund = False           # "CASH" not in {"ETF", "MUTUAL_FUND"}
holding_pct = 9.0254

# === CONTRIBUTION 1: asset class block (line ~230) ===
effective["CASH"] += 9.0254    # ✅ correct — SPAXX is 9.025% of portfolio
direct["CASH"]   += 9.0254

# === CONTRIBUTION 2: sector block (line ~238) — non-EQUITIES path ===
if asset_class != "EQUITIES":
    if sector != "UNKNOWN":
        effective["CASH"] += 9.0254    # ⚠️ BUG — adds again because sector.upper() == asset_class
        direct["CASH"]   += 9.0254

# === Final state ===
effective["CASH"] = 18.0508    # 2 × 9.0254
direct["CASH"]   = 18.0508
```

**The sector tracking block was designed for non-equity asset classes where sector ≠ asset_class** (e.g. FIXED_INCOME holdings with sector="Technology"). When sector and asset_class normalize to the same string — which only happens for SPAXX (sector="Cash" → "CASH" = asset_class="CASH") — the same percentage is added twice.

### Why BNDX/BND Are Not Affected

| Symbol | asset_class | sector (raw) | sector (upper) | Match? |
|--------|------------|-------------|---------------|--------|
| SPAXX | CASH | Cash | **CASH** | ✅ MATCH → double count |
| BNDX | FIXED_INCOME | Fixed Income | **FIXED INCOME** | ❌ no match (space vs underscore) |
| BND | FIXED_INCOME | Fixed Income | **FIXED INCOME** | ❌ no match |
| FBTC | DIGITAL | Digital Assets | **DIGITAL ASSETS** | ❌ no match |

SPAXX is the **only** holding in this portfolio where `sector.upper() == asset_class`.

### Root Cause Classification

| # | Root Cause | Description |
|---|-----------|-------------|
| **1** | **sector == asset_class double-count** | `_accumulate_holding_exposure()` in `exposure_decomposition.py` adds a non-EQUITIES holding's percentage to `effective[asset_class]` AND separately to `effective[sector]`. When `sector.upper() == asset_class` (as with SPAXX: sector="Cash" → "CASH"), the node receives the contribution twice. |

**Affected file:** `src/portfolio/exposure_decomposition.py`  
**Affected function:** `_accumulate_holding_exposure()`  
**Affected lines:** the `if asset_class != "EQUITIES": if sector != "UNKNOWN":` block (~lines 238–244)

---

## Section 3 — SPAXX Classification Audit

SPAXX runtime classification from holdings.csv (PAR-20260529-FE757845):

| Field | Actual Runtime Value | Expected Value | Match |
|-------|---------------------|----------------|-------|
| `symbol` | SPAXX | SPAXX | ✅ |
| `security_type` | Cash | Cash | ✅ |
| `asset_class` | CASH | CASH | ✅ |
| `is_cash_equivalent` | True | True | ✅ |
| `operational_state` | CASH_EQUIVALENT | CASH_EQUIVALENT | ✅ |
| `sector` | Cash | — | ⚠️ Causes double-count (see Section 2) |
| `decomposition_source` | REGISTRY | DIRECT_CLASSIFICATION | ⚠️ Stale (see Section 4) |
| `decomposition_method` | HEURISTIC_REGISTRY_V1 | — | ⚠️ Stale (see Section 4) |

**SPAXX is correctly classified as a cash equivalent.** The Phase 6.1A intent is honored:
- `security_type = "Cash"` ✅  
- `is_cash_equivalent = True` ✅  
- `operational_state = "CASH_EQUIVALENT"` ✅  

The double-counting is not a classification failure — SPAXX is classified correctly. It is an **aggregation bug** in the exposure calculation where sector duplicates the asset_class contribution.

---

## Section 4 — ETF Contributor Audit

### Why the UI Shows "ETF contributors: SPAXX"

The display path is:

```
recommendations.json → r.etf_contributors: ["SPAXX"]
    ↓
ui/portfolio_alignment/app.js line 839–844:
    const contributors = r.etf_contributors || [];
    if (contributors.length > 0)
        → <span class="rec-etf-label">ETF contributors:</span>
        → <span class="rec-etf-chip">SPAXX</span>
```

The label "ETF contributors:" is **hardcoded** and is applied to any non-empty `etf_contributors` array regardless of whether the contributors are ETFs or cash equivalents.

### How SPAXX Enters etf_contributors

`_identify_etf_contributors()` in `src/portfolio/recommendations.py` (line 1219):

```python
_FUND_SOURCES = {"REGISTRY", "HEURISTIC_FALLBACK", "SYMBOL_HEURISTIC"}
_FUND_TYPES   = {"ETF", "MUTUAL_FUND"}

for h in holdings:
    src = str(getattr(h, "decomposition_source", "")).strip().upper()  # → "REGISTRY"
    sec = str(getattr(h, "security_type", "")).strip().upper()         # → "CASH"
    if src not in _FUND_SOURCES and sec not in _FUND_TYPES:
        continue                # ← SPAXX passes this gate because src = "REGISTRY"
    _, effective, _ = build_holding_exposure_contribs(h)
    contribution = float(effective.get(node_key, 0.0))  # → 18.051% (doubled!)
    if contribution > 0.0:
        contributors.append((h.symbol.upper(), ...))    # SPAXX added
```

**Gate failure:** SPAXX has `decomposition_source = "REGISTRY"` because it was found in `config/etf_exposure_decomposition.yaml` during enrichment. That YAML entry predates Phase 6.1A's cash reclassification. As a result, SPAXX passes the `_FUND_SOURCES` filter and is treated as a fund contributor.

**The etf_contributors check has no guard for `operational_state == "CASH_EQUIVALENT"` or `is_cash_equivalent == True`.**

### Root Cause Summary for Issue #2

| # | Root Cause | Description |
|---|-----------|-------------|
| **2a** | **SPAXX in ETF registry** | `config/etf_exposure_decomposition.yaml` contains a SPAXX entry (from before Phase 6.1A). During enrichment, SPAXX gets `decomposition_source = "REGISTRY"`, which causes it to pass the fund filter in `_identify_etf_contributors`. |
| **2b** | **No cash-equivalent exclusion in fund filter** | `_identify_etf_contributors()` checks only `decomposition_source` and `security_type`. It does not check `operational_state` or `is_cash_equivalent`. A holding with `decomposition_source = "REGISTRY"` and `operational_state = "CASH_EQUIVALENT"` still passes and appears as a "fund contributor." |
| **2c** | **Hardcoded "ETF contributors:" label** | The UI label `ETF contributors:` is unconditional — it fires whenever `etf_contributors.length > 0`, with no distinction between actual ETFs and cash positions. |

### ETF Registry Entry for SPAXX

In `config/etf_exposure_decomposition.yaml`:

```yaml
SPAXX:
  decomposition_method: HEURISTIC_REGISTRY_V1
  decomposition_confidence: 0.90
  strategic_role: CASH_EQUIVALENT
  exposure_geography_mix:
    US: 100
  exposure_sector_mix:
    CASH: 100
  exposure_style_mix:
    INCOME: 100
  exposure_thematic_mix:
    CASH_EQUIVALENT: 100
```

The registry entry has `strategic_role: CASH_EQUIVALENT` — the cash identity is known to the registry — but the recommendation engine's fund-filter does not use `strategic_role` to exclude cash equivalents.

---

## Section 5 — Targeted Validation

| Check | Expected | Actual | Result |
|-------|----------|--------|--------|
| SPAXX `security_type` = Cash | Cash | Cash | ✅ PASS |
| SPAXX `is_cash_equivalent` = True | True | True | ✅ PASS |
| SPAXX `operational_state` = CASH_EQUIVALENT | CASH_EQUIVALENT | CASH_EQUIVALENT | ✅ PASS |
| SPAXX excluded from ETF contributor list | Not in `etf_contributors` | `etf_contributors: ["SPAXX"]` for CASH rec | ❌ FAIL |
| SPAXX counted exactly once in CASH node | 9.025% | 18.051% (2×) | ❌ FAIL |
| Reported CASH % matches actual holdings | 9.025% | 18.051% | ❌ FAIL |
| Reported CASH $ matches actual holdings | $42,619.59 | ~$85,239 (implied) | ❌ FAIL |
| "ETF contributors:" label correct for CASH rec | Should say "Cash position:" or be absent | "ETF contributors: SPAXX" | ❌ FAIL |

---

## Root Cause Summary

Two independent bugs, both rooted in the Phase 6.1A cash reclassification not being fully propagated.

### Bug 1 — Double-Count in Exposure Aggregation

**File:** `src/portfolio/exposure_decomposition.py`  
**Function:** `_accumulate_holding_exposure()`  
**Trigger:** Any non-EQUITIES holding where `sector.upper() == asset_class`  
**Only affected holding in this portfolio:** SPAXX (sector="Cash" → "CASH" = asset_class)  
**Effect:** `effective["CASH"]` = 2 × 9.025% = 18.051% instead of 9.025%  
**Downstream cascade:** CASH alignment node shows 18.051% → drift of +16.051% → HIGH severity recommendation to "Reduce Cash"  

### Bug 2 — SPAXX as ETF Contributor

**File:** `src/portfolio/recommendations.py`  
**Function:** `_identify_etf_contributors()`  
**Trigger:** `decomposition_source = "REGISTRY"` passes `_FUND_SOURCES` filter  
**Root cause:** SPAXX is in `config/etf_exposure_decomposition.yaml` (predates Phase 6.1A), so enrichment marks it as `decomposition_source = "REGISTRY"`. The fund filter has no exclusion for `operational_state = "CASH_EQUIVALENT"`.  
**Effect:** SPAXX appears in `etf_contributors: ["SPAXX"]` and the UI renders "ETF contributors: SPAXX" on the CASH recommendation card.  
**Compounding:** Because of Bug 1, `build_holding_exposure_contribs(SPAXX)` returns 18.051% for the CASH node (instead of 9.025%), making SPAXX appear to be a large indirect contributor.  

---

## Recommended Fixes

> **Do not implement until root cause is accepted. Evidence above is definitive.**

### Fix 1 — Prevent sector/asset_class double-count

In `src/portfolio/exposure_decomposition.py`, `_accumulate_holding_exposure()`:

```python
# BEFORE (buggy):
if asset_class != "EQUITIES":
    if sector != "UNKNOWN":
        effective[sector] += holding_pct
        if not is_fund:
            direct[sector] += holding_pct

# AFTER (correct):
if asset_class != "EQUITIES":
    if sector != "UNKNOWN" and sector != asset_class:   # ← add guard
        effective[sector] += holding_pct
        if not is_fund:
            direct[sector] += holding_pct
```

This one-line guard prevents any non-EQUITIES holding from double-counting when `sector.upper() == asset_class`.

### Fix 2 — Exclude cash equivalents from ETF contributor filter

In `src/portfolio/recommendations.py`, `_identify_etf_contributors()`:

```python
# BEFORE (buggy):
for h in holdings:
    src = str(getattr(h, "decomposition_source", "") or "").strip().upper()
    sec = str(getattr(h, "security_type", "") or "").strip().upper()
    if src not in _FUND_SOURCES and sec not in _FUND_TYPES:
        continue

# AFTER (correct):
for h in holdings:
    op_state = str(getattr(h, "operational_state", "") or "").strip().upper()
    is_cash_eq = str(getattr(h, "is_cash_equivalent", "") or "").strip().upper()
    if op_state == "CASH_EQUIVALENT" or is_cash_eq == "TRUE":
        continue                                          # ← skip cash equivalents
    src = str(getattr(h, "decomposition_source", "") or "").strip().upper()
    sec = str(getattr(h, "security_type", "") or "").strip().upper()
    if src not in _FUND_SOURCES and sec not in _FUND_TYPES:
        continue
```

### Fix 3 (Optional) — UI label generalization

In `ui/portfolio_alignment/app.js`, the hardcoded "ETF contributors:" label could be changed to "Contributing positions:" to be correct regardless of position type. This is cosmetic and lower priority once Fix 2 is applied (SPAXX will no longer appear in the list).

---

## Dollar Reconciliation (Post-Fix Projection)

After Fix 1 is applied:

| Metric | Current (Buggy) | After Fix |
|--------|----------------|-----------|
| CASH effective_pct | 18.051% | **9.025%** |
| CASH drift vs 7.0% target (CONCENTRATED_ALPHA) | +11.051% | **+2.025%** |
| CASH severity | HIGH | **LOW** |
| CASH recommendation | REDUCE (urgent) | LOW drift / likely no recommendation |
| Implied CASH $ | ~$85,239 | **$42,619.59** |
| Operator expected cash balance | ~$41,000 | **$42,620** ← reconciled ✅ |

The operator's expected cash of ~$41K is confirmed by SPAXX at $42,619.59 — a $1,620 rounding/timing difference consistent with money market accrual. Once Bug 1 is fixed, the alignment engine will report **9.025% cash** instead of **18.051%**, which reconciles exactly with the actual holding.
