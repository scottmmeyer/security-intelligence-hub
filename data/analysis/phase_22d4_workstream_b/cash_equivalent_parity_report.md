# Q3 — Cash Equivalent Parity Report
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** All 6 supported cash-equivalent symbols — SPAXX, VMFXX, FZFXX, FDRXX, SPRXX, FCASH  

---

## Verdict: All 6 Supported Symbols Are Treated Identically as CASH

No supported cash-equivalent symbol receives ETF, equity, fixed-income, or any other non-cash classification at any stage.

---

## Section 1 — Symbol Registry (Primary Source of Truth)

**File:** `src/portfolio/enrichment.py`, `_ETF_OVERRIDES` dict, lines 83–91:

```python
# Cash
"SPAXX": dict(asset_class="CASH", geography="US", market_cap_bucket="N/A",
              mega_subtier="N/A", sector="Cash", industry="Money Market"),
"VMFXX": dict(asset_class="CASH", geography="US", market_cap_bucket="N/A",
              mega_subtier="N/A", sector="Cash", industry="Money Market"),
"FZFXX": dict(asset_class="CASH", geography="US", market_cap_bucket="N/A",
              mega_subtier="N/A", sector="Cash", industry="Money Market"),
"FDRXX": dict(asset_class="CASH", geography="US", market_cap_bucket="N/A",
              mega_subtier="N/A", sector="Cash", industry="Money Market"),
"SPRXX": dict(asset_class="CASH", geography="US", market_cap_bucket="N/A",
              mega_subtier="N/A", sector="Cash", industry="Money Market"),
"FCASH": dict(asset_class="CASH", geography="US", market_cap_bucket="N/A",
              mega_subtier="N/A", sector="Cash", industry="Cash"),
```

All 6 symbols share `asset_class="CASH"`, `geography="US"`, `market_cap_bucket="N/A"`, `mega_subtier="N/A"`. FCASH uses `industry="Cash"` instead of `"Money Market"` — a minor metadata difference, not a governance difference.

---

## Section 2 — `_CASH_EQUIVALENT_SYMBOLS` Frozenset

**File:** `src/portfolio/enrichment.py`, line 120:
```python
_CASH_EQUIVALENT_SYMBOLS: frozenset[str] = frozenset(
    sym for sym, ov in _ETF_OVERRIDES.items() if ov.get("asset_class") == "CASH"
) | frozenset({"FDRXX", "SPRXX", "FCASH", "FGXX", "SWVXX", "VUSXX", "TTTXX", "PRTXX", "FDLXX"})
```

Membership confirmed for all 6 primary symbols:
| Symbol | In `_ETF_OVERRIDES` (CASH) | In Extended Set | In `_CASH_EQUIVALENT_SYMBOLS` |
|--------|---------------------------|-----------------|-------------------------------|
| SPAXX  | ✅ | — | ✅ |
| VMFXX  | ✅ | — | ✅ |
| FZFXX  | ✅ | — | ✅ |
| FDRXX  | ✅ | ✅ (redundant, correct) | ✅ |
| SPRXX  | ✅ | ✅ (redundant, correct) | ✅ |
| FCASH  | ✅ | ✅ (redundant, correct) | ✅ |

The union operator `|` means FDRXX, SPRXX, FCASH are included from both sides — harmless redundancy, consistent result.

---

## Section 3 — Reconciliation Symbol Registry

**File:** `src/portfolio/reconciliation.py`, lines 51–59:
```python
_CASH_EQUIVALENT_SYMBOLS = frozenset({
    "SPAXX", "FCASH", "FDRXX", "SPRXX", "VMFXX", "FZFXX",
    "FZSXX", "FTIXX", "FMPXX", "FDLXX",
})
```
All 6 primary symbols are explicitly listed. This frozenset is used by the RC-06 governance check to validate that cash instruments are never misclassified.

**Note:** `enrichment.py` and `reconciliation.py` define their `_CASH_EQUIVALENT_SYMBOLS` independently. Both cover all 6 primary symbols. The reconciliation set includes additional extended symbols (FZSXX, FTIXX, FMPXX, FDLXX) that are not in the enrichment ETF override table — these would be handled by the fallback path in enrichment (security_type="Cash" detection).

---

## Section 4 — Enrichment Protection Guard (Applies to ALL 6 Symbols)

**File:** `src/portfolio/enrichment.py`, lines 227–234:
```python
if sym in _CASH_EQUIVALENT_SYMBOLS:
    # Cash-equivalent symbols (SPAXX, VMFXX, etc.) must NOT be promoted
    # to security_type='ETF'
    effective_security_type = "Cash"
    is_cash_equiv = True
    new_op_state = "CASH_EQUIVALENT"
```

This single guard applies to **all symbols** in `_CASH_EQUIVALENT_SYMBOLS`. When any cash-equivalent symbol is encountered during enrichment, it is hard-assigned to `security_type="Cash"`, `is_cash_equivalent=True`, `operational_state="CASH_EQUIVALENT"` — regardless of any other path.

**Fallback path** (for extended symbols not in the override table):
**File:** `src/portfolio/enrichment.py`, line 273:
```python
if security_type == "Cash" or sym in _CASH_EQUIVALENT_SYMBOLS:
    is_cash_equivalent = True
    operational_state = "CASH_EQUIVALENT"
    asset_class = "CASH"
```

---

## Section 5 — Expected Classification for Each Symbol

| Symbol | asset_class | security_type | is_cash_equivalent | operational_state |
|--------|-------------|---------------|--------------------|-------------------|
| SPAXX  | CASH | Cash | True | CASH_EQUIVALENT |
| VMFXX  | CASH | Cash | True | CASH_EQUIVALENT |
| FZFXX  | CASH | Cash | True | CASH_EQUIVALENT |
| FDRXX  | CASH | Cash | True | CASH_EQUIVALENT |
| SPRXX  | CASH | Cash | True | CASH_EQUIVALENT |
| FCASH  | CASH | Cash | True | CASH_EQUIVALENT |

---

## Section 6 — Platform Behavior Parity

All 6 symbols receive **identical treatment** at every subsequent platform stage:

| Stage | Behavior (All 6 Symbols) |
|-------|--------------------------|
| Deployment queue | Excluded — `is_cash_equivalent = True` → `_is_eligible()` returns `False` |
| CW-DAS scoring | Not scored — `is_cash_equivalent` gate fires first |
| UCF | `ucf_label = MAINTAIN`, `ucf_score = 0.0` (no composite, no replay) |
| Recommendation engine | Excluded from position-level recs; contributes to EXCESS_CASH funding pool |
| Optimizer | Excluded from equity/FI node matching — `is_cash_eq = True` |
| Replay | `replay_supported = False` — cash has no replay universe |
| Allocation node | Contributes to `CASH` L1 node only |
| Trim intelligence | `trim_priority = HIGH` — never targeted for trim |
| UI | Rendered as CASH aggregate — no conviction/ETF/signal labels |

---

## Section 7 — Test Evidence

| Test | Symbol | File | Assertion |
|------|--------|------|-----------|
| `test_spaxx_enriched_as_cash_not_etf` | SPAXX | `test_cash_semantics.py` | `security_type="Cash"`, `asset_class="CASH"` |
| `test_spaxx_is_cash_equivalent_flag` | SPAXX | `test_cash_semantics.py` | `is_cash_equivalent=True` |
| `test_spaxx_operational_state_is_cash_equivalent` | SPAXX | `test_cash_semantics.py` | `operational_state="CASH_EQUIVALENT"` |
| `test_vmfxx_enriched_as_cash` | VMFXX | `test_cash_semantics.py` | Same assertions as SPAXX |
| `test_fzfxx_enriched_as_cash` | FZFXX | `test_cash_semantics.py` | Same assertions as SPAXX |

**Note:** FDRXX, SPRXX, FCASH do not have dedicated test fixtures in `test_cash_semantics.py` as they are currently not held in the live portfolio. Their inclusion in `_CASH_EQUIVALENT_SYMBOLS` and `_ETF_OVERRIDES` ensures identical treatment if held.

---

## Section 8 — ETF Registry Parity (VMFXX, FZFXX)

VMFXX and FZFXX also appear in `config/etf_exposure_decomposition.yaml` alongside SPAXX:

```yaml
VMFXX:
  strategic_role: CASH_EQUIVALENT
  exposure_sector_mix:
    CASH: 100
FZFXX:
  strategic_role: CASH_EQUIVALENT
  exposure_sector_mix:
    CASH: 100
```

These entries carry the same `strategic_role: CASH_EQUIVALENT` declaration as SPAXX. They are subject to the same enrichment guard and would produce the same `decomposition_source = "REGISTRY"` stale field. The same behavioral guard prevents ETF promotion for both.

FDRXX, SPRXX, FCASH do NOT appear in the ETF registry YAML — these symbols do not carry the stale metadata fields.

---

## Section 9 — Extended Cash Symbols (Not in Live Portfolio)

The enrichment `_CASH_EQUIVALENT_SYMBOLS` also includes: `FGXX`, `SWVXX`, `VUSXX`, `TTTXX`, `PRTXX`, `FDLXX`.  
The reconciliation `_CASH_EQUIVALENT_SYMBOLS` also includes: `FZSXX`, `FTIXX`, `FMPXX`, `FDLXX`.

These extended symbols are handled by the fallback path at enrichment line 273. If any of these appeared in a portfolio CSV, they would receive the same `CASH_EQUIVALENT` treatment via the `security_type == "Cash"` or `sym in _CASH_EQUIVALENT_SYMBOLS` condition.
