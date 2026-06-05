# Phase 23.2 — Policy Persistence Design

**Date:** 2026-06-03
**Status:** APPROVED

---

## 1. Storage Strategy

### File: `data/operator/portfolio_alignment_state.json`

The existing operator state file is extended with an `operator_policies` top-level key. No new files are required.

**Rationale:**
- `portfolio_alignment_state.json` is already the canonical operator state container
- It already holds `strategic_exit_symbols` — a per-symbol operator override
- Single file simplifies backup, restore, and version control tracking
- `.gitignore` treatment: this file should be excluded from version control (contains operator-specific runtime state)

---

## 2. Schema Versioning

A `schema_version` key is added to `portfolio_alignment_state.json`:

```json
{
  "schema_version": "23.2",
  "tax_year": 2026,
  "net_realized_ytd": null,
  "potential_additional_losses": null,
  "capital_loss_carryforward": null,
  "strategic_exit_symbols": ["FIS"],
  "operator_policies": {
    "TSLA": { ... },
    "DODFX": { ... }
  }
}
```

The `OperatorPolicyRegistry.load()` method is forward-compatible: unknown fields in each policy record are silently ignored. Old files without `operator_policies` return an empty registry.

---

## 3. Read-Merge-Write Pattern

All writes use the read-merge-write pattern (consistent with existing tax-state handler):

```python
def _write_policy(state_path: Path, symbol: str, policy_record: dict) -> None:
    """Atomic read-merge-write for policy persistence."""
    # Read current state
    if state_path.exists():
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
    else:
        state = {}

    # Merge
    policies = state.get("operator_policies", {})
    policies[symbol.upper()] = policy_record
    state["operator_policies"] = policies
    state["schema_version"] = "23.2"

    # Write (Python json.dump is atomic enough for single-user local file)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
```

For a single-user local application, Python's `json.dump` to a local file is sufficient. No file locking is required.

---

## 4. Policy Lifecycle Transitions

```
[Not Set]
    │
    ▼ POST /api/operator/policies
[ACTIVE]
    │
    ├─▶ POST /api/operator/policies/revoke  ──▶ [REVOKED]
    │
    ├─▶ expires_at reached at runtime       ──▶ [EXPIRED] (auto, no write needed — is_active() returns False)
    │
    └─▶ symbol removed from portfolio       ──▶ [DORMANT — still ACTIVE in file, no effect until symbol returns]
```

### Status Values
- `ACTIVE`: Policy is in effect
- `REVOKED`: Operator explicitly revoked; persisted with `revoked_at` timestamp
- `EXPIRED`: `expires_at` has passed; detected in `is_active()` at read time; no file write required

Policies are **never hard-deleted** from the JSON file. This provides a complete audit trail.

---

## 5. Policy Survival Rules

| Event | Policy Behavior |
|-------|----------------|
| New portfolio CSV upload | Policies survive — symbol-keyed, upload-independent |
| Symbol absent from new portfolio | Policy dormant — preserved in registry, no effect |
| Symbol re-enters portfolio | Policy immediately active again (ACTIVE status still set) |
| Server restart | Policies survive — read from file on each API request |
| Analysis run | Policies loaded at run time; snapshot captured in `run_metadata.json` |
| Manual file edit | Supported — file is human-readable JSON |

---

## 6. API Endpoints

### GET `/api/operator/policies`
Returns all policy records (all statuses).

**Response:**
```json
{
  "operator_policies": {
    "TSLA": {
      "symbol": "TSLA",
      "policy_type": "DO_NOT_SELL",
      "status": "ACTIVE",
      "rationale": "Long-term strategic position",
      "created_at": "2026-06-03T15:30:00+00:00",
      "expires_at": null,
      "revoked_at": null
    }
  }
}
```

---

### GET `/api/operator/policies/{symbol}`
Returns the policy record for a specific symbol, or `{"policy": null}` if none exists.

---

### POST `/api/operator/policies`
Add or update a policy for a symbol.

**Request body:**
```json
{
  "symbol": "TSLA",
  "policy_type": "DO_NOT_SELL",
  "rationale": "Long-term strategic position",
  "expires_at": null
}
```

**Validation:**
- `symbol`: required, string, will be uppercased
- `policy_type`: required, must be in `POLICY_TYPES` frozenset
- `rationale`: required, min 3 characters
- `expires_at`: optional, ISO datetime string or null
- Conflict check: if symbol already has an active policy of conflicting type → 409

**Response (success):**
```json
{
  "ok": true,
  "symbol": "TSLA",
  "policy_type": "DO_NOT_SELL",
  "status": "ACTIVE",
  "warning": null
}
```

**Response (conflict):**
```json
{
  "ok": false,
  "error": "Policy conflict: SELL_LAST and DO_NOT_SELL cannot coexist on TSLA",
  "error_code": "POLICY_CONFLICT"
}
```
HTTP 409

**Response (semantic warning):**
```json
{
  "ok": true,
  "symbol": "DODFX",
  "policy_type": "PREFERRED_ACCUMULATION",
  "status": "ACTIVE",
  "warning": "SELL_LAST and PREFERRED_ACCUMULATION on same symbol — unusual combination"
}
```

---

### POST `/api/operator/policies/revoke`
Revoke an active policy.

**Request body:**
```json
{
  "symbol": "TSLA"
}
```

**Response:**
```json
{
  "ok": true,
  "symbol": "TSLA",
  "revoked_at": "2026-06-03T16:00:00+00:00"
}
```

If symbol has no active policy: `{"ok": false, "error": "No active policy for TSLA"}` HTTP 404.

---

## 7. PAR Policy Snapshot

Every PAR captures the policy state at analysis run time. Written to `run_metadata.json`:

```json
{
  "run_id": "PAR-20260603-XXXXXXXX",
  "snapshot_date": "2026-06-03",
  "mandate_type": "CONCENTRATED_ALPHA",
  "policy_snapshot": {
    "TSLA": {
      "policy_type": "DO_NOT_SELL",
      "status": "ACTIVE",
      "created_at": "2026-06-03T15:30:00+00:00"
    },
    "DODFX": {
      "policy_type": "SELL_LAST",
      "status": "ACTIVE",
      "created_at": "2026-06-03T15:31:00+00:00"
    }
  },
  "policy_suppressed_count": 1,
  "policy_rank_adjusted_count": 2
}
```

This makes every historical PAR auditable: "which policies were active when this analysis was run?"

---

## 8. File Structure After Phase 23.2

```
data/operator/
  portfolio_alignment_state.json     ← extended with operator_policies
  
data/portfolio_ingestion/
  analysis_runs/
    PAR-XXXXXXXXX/
      run_metadata.json              ← extended with policy_snapshot
      deployment_queue.json          ← extended with policy_suppressed
      security_overlays.csv          ← extended with policy_type, policy_annotation
```

---

## 9. Backward Compatibility

Old PARs (pre-Phase 23.2):
- `run_metadata.json` lacks `policy_snapshot` key → treated as "no policies active at run time"
- `deployment_queue.json` lacks `policy_suppressed` key → treated as empty list
- `security_overlays.csv` lacks policy columns → UI renders without policy badges

`OperatorPolicyRegistry.load()` returns empty registry if `operator_policies` key is absent from state file — no error.

---

## 10. Security Considerations

- Policy file is local to the operator machine (`data/operator/`) — no network exposure
- No authentication required (single-user local application)
- Policies cannot modify intelligence data (enforced architecturally, not by access control)
- `rationale` field is free text — no HTML/script injection risk as it is JSON-escaped on write and text-rendered on UI display
- `expires_at` is validated as ISO datetime string; invalid values rejected at write time
