# Phase 23.0A.1 — Q4: Optional Context Governance

**Validation Question**: Does tax context remain strictly optional — i.e., does portfolio analysis work correctly when the Tax Context Panel is empty, removed, or contains invalid values?

---

## Architectural Principle

SIH Phase 23.0A was designed with a hard constraint: **tax is a decision modifier, not a dependency.** The portfolio analysis pipeline must produce correct, complete results whether or not the operator has entered any tax context.

---

## Dependency Audit: Server Side

### `POST /api/portfolio/analyze` → `run_analysis()`

No tax state is read, referenced, or injected at any point in the server-side analysis pipeline. The `run_analysis()` function in `src/portfolio/runner.py` operates entirely on portfolio holdings and SIH signal data. Tax state stored in `data/operator/portfolio_alignment_state.json` is never loaded during analysis.

**Server-side verdict: ZERO tax dependency. ✓**

### `GET /api/operator/tax-state`

This endpoint is called on page load (`loadTaxState()`) as a best-effort operation:

```js
async function loadTaxState() {
  try {
    const resp = await fetch("/api/operator/tax-state");
    if (!resp.ok) return;            // silently exits on error
    const data = await resp.json();
    if (data && typeof data === "object" && !data.error) {
      _taxState = { ..._taxState, ...data };
      _populateTaxFields();
      updateTaxComputed();
    }
  } catch (_) { /* best-effort */ }  // silently exits on network error
}
```

Failure modes handled without interruption:
- Server not running → `catch` swallows network error
- No state file → server returns `{}` → `if (!data.error)` allows empty merge
- State file corrupted → `catch` or `!resp.ok` guard exits silently
- Field contains null → `_populateTaxFields()` checks `_taxState[key] != null` before writing to DOM

**Page load tax error verdict: FULLY SILENT DEGRADATION. ✓**

---

## Dependency Audit: Client Side

### Empty Tax Panel — Calculation Path

When the Tax Context Panel is empty (all inputs blank), `_readTaxInputs()` applies `|| 0` fallbacks:

```js
function _readTaxInputs() {
  return {
    net_realized_ytd:            parseFloat(...) || 0,   // blank → 0
    potential_additional_losses: Math.abs(parseFloat(...) || 0),  // blank → 0
    capital_loss_carryforward:   Math.abs(parseFloat(...) || 0),  // blank → 0
    tax_year:                    parseInt(...) || currentYear,    // blank → current year
  };
}
```

With all zeros:
```
available = max(0, -0 + 0) = 0
projected = 0 + 0 = 0
gainShielded = (available > 0 && ...) = false  [available is 0]
```

Bucket assignments still proceed based on signal/flag alone. The absence of tax capacity simply means `gainShielded` is never true — all poor-outlook gain positions are classified Bucket A or B based on holding period, not shielding. This is correct and expected behavior.

### Invalid Input Handling

| Input Value | `parseFloat()` Result | `|| 0` Fallback | Effect |
|---|---|---|---|
| Empty string `""` | `NaN` | `0` | Treated as zero |
| Non-numeric `"abc"` | `NaN` | `0` | Treated as zero |
| Negative number `-5000` for potential_losses | `-5000` | `Math.abs(-5000) = 5000` | Normalized to positive |
| Very large number | `Infinity` possible | `Math.max(0, ...)` catches | Not handled — see advisory |

**Advisory:** Extremely large values (e.g. operator types `999999999999`) are not bounded. Computed display would show a large M value. No error is thrown. This is acceptable for a local advisory tool but warrants input validation in a future hardening pass.

### `renderTaxActionTable(data)` — Called Unconditionally

`renderTaxActionTable()` is called at the end of `renderResults()` on every analysis completion:

```js
function renderResults(data) {
  // ... renders signals, recommendations, etc.
  renderTaxActionTable(data);  // always called
}
```

Inside `renderTaxActionTable()`:

```js
const actions = _computeTaxActions(data);
if (!actions.length) {
  section.style.display = "none";  // hides section cleanly
  return;
}
section.style.display = "block";
```

If no securities match any bucket (e.g., all holdings are neutral with no signals), the tax action section is hidden entirely. No empty table is rendered.

**Unconditional call verdict: SAFE — section auto-hides when no actions exist. ✓**

### `clearAll()` Reset

```js
function clearAll() {
  // ... clears upload, results, overlays ...
  const taxActionSection = document.getElementById("taxActionSection");
  if (taxActionSection) taxActionSection.style.display = "none";
}
```

The tax action section is explicitly hidden when the operator clears results. Tax panel inputs and computed values are NOT cleared (they represent persistent operator context, not per-analysis results). This is intentional — tax state persists across analysis runs. ✓

---

## Panel Visibility Independence

The Tax Context Panel is collapsible (`toggleTaxPanel()`). When collapsed, the panel body is hidden via CSS (`display: none`), but the form inputs remain in the DOM. `_readTaxInputs()` reads from DOM inputs, not from a JS state object. Even with the panel collapsed, tax context is still read and applied to bucket computations.

**Collapsed panel verdict: INPUTS STILL ACTIVE when collapsed. ✓**

This means operators who collapse the panel to reduce visual clutter do not inadvertently disable the tax feature. The saved values continue to influence bucket assignments.

---

## Summary: Optional Context Architecture Preserved

| Boundary | Independence | Method |
|---|---|---|
| Server analysis pipeline | Fully independent | Tax state never loaded during `run_analysis()` |
| Page load failure | Silent degradation | `try/catch` in `loadTaxState()` |
| Empty tax panel | Graceful zero-fallback | `|| 0` in `_readTaxInputs()` |
| Invalid inputs | Normalized to 0 | `parseFloat() || 0` + `Math.abs()` |
| No bucket matches | Auto-hidden section | `actions.length === 0` guard |
| Panel collapsed | Still active | DOM inputs independent of panel visibility |
| `clearAll()` | Tax panel preserved | Only result section is hidden |

---

## Verdict: Q4

| Check | Result |
|---|---|
| Analysis pipeline has zero tax dependency | ✓ CONFIRMED |
| Page load tax error is silent | ✓ CONFIRMED |
| Empty panel produces valid zero-fallback | ✓ CONFIRMED |
| Invalid inputs normalized | ✓ CONFIRMED |
| Tax section auto-hides with no actions | ✓ CONFIRMED |
| Collapsed panel inputs remain active | ✓ CONFIRMED |
| Input range validation (very large values) | ⚠ ADVISORY — no upper-bound guard |

**Q4 Status: PASS — optional-context architecture fully preserved. 1 minor advisory.**
