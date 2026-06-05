# Phase 23.0A.1 — Q5: Persistence Review

**Validation Question**: Is the operator tax state persistence implementation correct, appropriate, and safe? What advisories apply?

---

## What Is Persisted

**Location:** `data/operator/portfolio_alignment_state.json` (relative to repo root)

**Schema:**
```json
{
  "net_realized_ytd":              -24730.0,
  "potential_additional_losses":   14236.0,
  "capital_loss_carryforward":     0.0,
  "tax_year":                      2025,
  "_updated":                      "2025-01-15T18:42:11.342+00:00"
}
```

| Field | Type | Purpose |
|---|---|---|
| `net_realized_ytd` | float (signed) | YTD realized gain/loss |
| `potential_additional_losses` | float (unsigned) | Expected additional losses before year-end |
| `capital_loss_carryforward` | float (unsigned) | Prior-year carryforward losses |
| `tax_year` | int | Tax year for context |
| `_updated` | ISO-8601 UTC datetime | Audit trail — last save timestamp |

---

## Persistence Lifecycle

### On Save (POST /api/operator/tax-state)

```python
_TAX_FIELDS = ("net_realized_ytd", "potential_additional_losses",
               "capital_loss_carryforward", "tax_year")
state: dict = {}
for f in _TAX_FIELDS:
    if f in payload:
        state[f] = payload[f]

state_path.parent.mkdir(parents=True, exist_ok=True)  # auto-creates data/operator/

existing = json.loads(state_path.read_text()) if state_path.exists() else {}
existing.update(state)
existing["_updated"] = datetime.now(timezone.utc).isoformat()
state_path.write_text(json.dumps(existing, indent=2))
```

- Directory is auto-created on first save. ✓
- Uses additive merge (`existing.update(state)`) — preserves extra fields from future schema versions. ✓
- Only the 4 defined field names are accepted from the request payload (whitelist enforcement). ✓
- `_updated` timestamp is always set on every save. ✓

### On Load (GET /api/operator/tax-state)

```python
if state_path.exists():
    state = json.loads(state_path.read_text(encoding="utf-8"))
    self._json_response(state)
else:
    self._json_response({})   # no error — returns empty object
```

- Missing file returns `{}` (not 404 or error). Client handles `{}` as "no saved state." ✓
- Parse error on malformed JSON returns 500 with error message. Client `loadTaxState()` catches this via `!resp.ok` guard. ✓

---

## Persistence Behavior Across Lifecycle Events

| Event | Behavior | Correct? |
|---|---|---|
| First save (no file) | Directory + file created | ✓ |
| Subsequent save | Merged, not replaced | ✓ |
| Page refresh | State reloads on `DOMContentLoaded` | ✓ |
| Server restart | State reloads from disk on next page visit | ✓ |
| Browser restart | State reloads from disk on next page visit | ✓ |
| `clearAll()` called | Tax panel NOT cleared (state persists) | ✓ (intentional) |
| No state saved yet | GET returns `{}`, panel shows empty | ✓ |
| State file corrupted | GET returns 500, client silently continues | ✓ |

---

## Advisories

### Advisory 1: No Reset / Clear Button in UI

There is no UI mechanism to clear persisted tax state without manually deleting values and saving. An operator who changes tax year or whose YTD situation changes mid-year cannot easily zero out the panel.

**Recommendation:** Add a "Reset" button to the Tax Context Panel that:
1. Clears all four input fields to empty/blank
2. Calls `saveTaxState()` to persist the cleared state
3. Triggers `renderTaxActionTable()` to re-evaluate with zero context

Implementation is ~10 lines of JS + 1 button element. Not blocking for Phase 23.0A acceptance, but should be addressed in a subsequent pass.

### Advisory 2: `_updated` Timestamp Not Visible to Operator

The `_updated` field is persisted but not displayed anywhere in the UI. An operator cannot tell from the panel whether their state was saved today or six months ago.

**Recommendation:** Display `_updated` as a "Last saved: [date]" label near the Save button. The GET response already includes this field — the client only needs to render it.

### Advisory 3: No Server-Side Numeric Validation

The POST handler uses a field whitelist (`_TAX_FIELDS`) but does not validate that values are numeric:

```python
# Current implementation — no type check
for f in _TAX_FIELDS:
    if f in payload:
        state[f] = payload[f]  # stores whatever type was sent
```

A non-numeric value (e.g., `{"net_realized_ytd": "abc"}` or `{"net_realized_ytd": null}`) would be stored and persisted. On the next `loadTaxState()`, the value would be populated into the DOM input; `parseFloat("abc")` → `NaN` → `|| 0` fallback in `_readTaxInputs()`.

The client-side fallback handles this gracefully, but the state file ends up with invalid data. Since this is a local-only server (bound to `127.0.0.1`), risk is limited to operator entry error.

**Recommendation:** Add `isinstance(payload[f], (int, float))` type check server-side before storing. Block strings and dicts.

### Advisory 4: No Year-to-Year State Rollover

The stored `tax_year` is not used to auto-expire or reset the state on a new tax year. An operator who runs SIH in January 2026 would see stale 2025 YTD values pre-populated.

**Recommendation:** On `loadTaxState()`, if `tax_year !== currentYear`, show a warning prompt: "Your saved tax context is from [year]. Would you like to reset it?" Not required for MVP — operator can manually update the year field.

---

## Security Considerations

The persistence implementation is local-only (server binds to `127.0.0.1`, not `0.0.0.0`). The state file contains no credentials, PII, or account-identifying data — only dollar amounts and year. Risk profile is low. The whitelist on accepted field names (`_TAX_FIELDS`) prevents injection of arbitrary keys into the state file. ✓

The `_updated` field uses UTC ISO-8601 from `datetime.now(timezone.utc)` — no local timezone leakage. ✓

---

## Recommendation

**Retain the persistence architecture as-is.** It is correct, appropriately scoped, and provides genuine operator value (state survives page refreshes and server restarts without requiring re-entry).

Address Advisories 1–4 in a future hardening pass.

---

## Verdict: Q5

| Check | Result |
|---|---|
| File created automatically on first save | ✓ PASS |
| Merge (not replace) on update | ✓ PASS |
| State survives page refresh | ✓ PASS |
| State survives server restart | ✓ PASS |
| Missing file returns `{}` gracefully | ✓ PASS |
| Client silently degrades on load failure | ✓ PASS |
| No UI Reset / Clear button | ⚠ ADVISORY 1 |
| `_updated` not displayed to operator | ⚠ ADVISORY 2 |
| No server-side numeric type validation | ⚠ ADVISORY 3 |
| No year-to-year rollover handling | ⚠ ADVISORY 4 |

**Q5 Status: PASS — 4 advisories documented. No blocking defects.**
