# Tax State Persistence — Phase 23.0A

## Mechanism

Operator tax context is stored in a server-side JSON file to provide
durable persistence that survives page refresh, server restart, and
browser restart.

---

## Storage File

```
data/operator/portfolio_alignment_state.json
```

Directory is created automatically on first save.

---

## Schema

```json
{
  "net_realized_ytd": -24730,
  "potential_additional_losses": 14236,
  "capital_loss_carryforward": 0,
  "tax_year": 2026,
  "_updated": "2026-06-02T18:45:00+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `net_realized_ytd` | number | Net realized gain (positive) or loss (negative) YTD |
| `potential_additional_losses` | number | Remaining harvestable losses (positive magnitude) |
| `capital_loss_carryforward` | number | Prior-year carryforward (positive magnitude) |
| `tax_year` | integer | Active tax year |
| `_updated` | ISO datetime | Last save timestamp (server-generated) |

---

## API Endpoints

### `GET /api/operator/tax-state`

Returns persisted tax state JSON.  Returns `{}` when no state has been saved.

### `POST /api/operator/tax-state`

Merges supplied fields into persisted state and writes to disk.

**Request body:** Any subset of the schema fields above.

**Response:** `{ "ok": true, "state": { ...merged state } }`

---

## Client Behavior

1. On `DOMContentLoaded`: `loadTaxState()` calls `GET /api/operator/tax-state`
   and populates input fields from server response.
2. On "Save Tax Position" button: `saveTaxState()` calls `POST /api/operator/tax-state`
   with current field values, then re-renders the tax action table.
3. Live compute: inputs trigger `updateTaxComputed()` on every keystroke to
   show Available and Projected Gain Capacity in real time without a save.

---

## Lifecycle

| Event | Behavior |
|---|---|
| Page load | Tax state loaded from server JSON |
| User edits inputs | Computed values update live; not saved until button clicked |
| Save clicked | Fields merged to disk; tax action table re-renders |
| Server restart | State persists from disk file |
| Browser restart | State persists from disk file (not localStorage) |
| User clears inputs manually | Operator intent; requires explicit save to persist empty values |
