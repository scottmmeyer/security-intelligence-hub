# Phase 23.2 — Data Model Design

**Date:** 2026-06-03
**Status:** APPROVED

---

## 1. Storage Location

Policies are persisted in the existing operator state file:

```
data/operator/portfolio_alignment_state.json
```

This file already holds `strategic_exit_symbols` and tax context. The policy registry is a new top-level key: `operator_policies`.

### Rationale for Co-location
- Single operator state file simplifies backup and restore
- Consistent with existing `strategic_exit_symbols` persistence pattern
- Avoids proliferating operator data files

---

## 2. Policy Registry Schema (JSON)

### Top-Level Structure

```json
{
  "tax_year": 2026,
  "net_realized_ytd": null,
  "potential_additional_losses": null,
  "capital_loss_carryforward": null,
  "strategic_exit_symbols": ["FIS"],
  "operator_policies": {
    "TSLA": {
      "symbol": "TSLA",
      "policy_type": "DO_NOT_SELL",
      "status": "ACTIVE",
      "rationale": "Long-term strategic position",
      "created_at": "2026-06-03T15:30:00+00:00",
      "expires_at": null,
      "revoked_at": null
    },
    "DODFX": {
      "symbol": "DODFX",
      "policy_type": "SELL_LAST",
      "status": "ACTIVE",
      "rationale": "Legacy intentional holding",
      "created_at": "2026-06-03T15:30:00+00:00",
      "expires_at": null,
      "revoked_at": null
    }
  }
}
```

### Policy Record Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | string | YES | Uppercase ticker symbol |
| `policy_type` | enum | YES | One of: DO_NOT_SELL, SELL_LAST, CORE_ANCHOR, PREFERRED_ACCUMULATION |
| `status` | enum | YES | One of: ACTIVE, REVOKED, EXPIRED |
| `rationale` | string | YES | Operator-provided justification (min 3 chars) |
| `created_at` | ISO datetime | YES | UTC timestamp, set at write time |
| `expires_at` | ISO datetime / null | NO | Optional expiration; null = no expiration |
| `revoked_at` | ISO datetime / null | YES | Set when status → REVOKED; null if ACTIVE |

### Symbol Key Rules
- Always uppercase
- Must match known portfolio holding symbols (warning, not hard rejection, for unknown symbols — operator may be pre-configuring for upcoming entry)
- One policy record per symbol (replacing requires explicit revoke-and-create or update)

---

## 3. In-Memory Policy Registry Model (Python)

### Module: `src/portfolio/operator_policy.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import json
import os
from datetime import datetime, timezone

POLICY_TYPES = frozenset({
    "DO_NOT_SELL",
    "SELL_LAST",
    "CORE_ANCHOR",
    "PREFERRED_ACCUMULATION",
})

# Conflict pairs: (A, B) means A and B cannot coexist on same symbol
POLICY_CONFLICTS: frozenset[frozenset] = frozenset({
    frozenset({"DO_NOT_SELL", "SELL_LAST"}),
})

# Semantic warnings (allow but warn)
POLICY_WARNINGS: frozenset[frozenset] = frozenset({
    frozenset({"SELL_LAST", "PREFERRED_ACCUMULATION"}),
})


@dataclass
class OperatorPolicy:
    symbol: str
    policy_type: str
    status: str               # ACTIVE | REVOKED | EXPIRED
    rationale: str
    created_at: str
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None

    def is_active(self) -> bool:
        if self.status != "ACTIVE":
            return False
        if self.expires_at:
            try:
                exp = datetime.fromisoformat(self.expires_at)
                if datetime.now(timezone.utc) > exp:
                    return False
            except ValueError:
                pass
        return True


class OperatorPolicyRegistry:
    """In-memory view of operator_policies from portfolio_alignment_state.json."""

    def __init__(self, policies: dict[str, OperatorPolicy]):
        self._policies: dict[str, OperatorPolicy] = policies

    @classmethod
    def load(cls, state_path: str) -> "OperatorPolicyRegistry":
        if not os.path.exists(state_path):
            return cls({})
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
        raw = state.get("operator_policies", {})
        policies = {}
        for sym, rec in raw.items():
            try:
                policies[sym.upper()] = OperatorPolicy(**rec)
            except TypeError:
                pass  # forward-compat: ignore unknown fields
        return cls(policies)

    def get(self, symbol: str) -> Optional[OperatorPolicy]:
        return self._policies.get(symbol.upper())

    def active_policy_type(self, symbol: str) -> Optional[str]:
        p = self.get(symbol)
        if p and p.is_active():
            return p.policy_type
        return None

    def is_do_not_sell(self, symbol: str) -> bool:
        return self.active_policy_type(symbol) == "DO_NOT_SELL"

    def is_sell_last(self, symbol: str) -> bool:
        return self.active_policy_type(symbol) == "SELL_LAST"

    def is_core_anchor(self, symbol: str) -> bool:
        return self.active_policy_type(symbol) == "CORE_ANCHOR"

    def is_preferred_accumulation(self, symbol: str) -> bool:
        return self.active_policy_type(symbol) == "PREFERRED_ACCUMULATION"

    def all_active(self) -> dict[str, OperatorPolicy]:
        return {k: v for k, v in self._policies.items() if v.is_active()}
```

---

## 4. Policy-Annotated Output Fields

### Security Overlay Extension

The existing `security_overlays.csv` and overlay dict receive additional read-only policy annotation fields (populated by runner.py after policy registry load):

| Field | Type | Source |
|-------|------|--------|
| `policy_type` | str / "" | OperatorPolicyRegistry.active_policy_type(sym) |
| `policy_annotation` | str / "" | Human label for UI display |
| `policy_protected` | bool | is_do_not_sell(sym) |

These are **annotation-only fields** — they do not feed any score or check.

### Deployment Queue Entry Extension

The `CandidateEntry` dataclass in `deployment_queue.py` receives:

| Field | Type | Description |
|-------|------|-------------|
| `policy_type` | str / None | Active policy type or None |
| `policy_annotation` | str / None | Human badge text |
| `policy_rank_boost` | bool | True if rank adjusted by PREFERRED_ACCUMULATION |
| `original_rank` | int / None | Pre-policy rank (for transparency) |

---

## 5. Policy Application Sequence

```
run_analysis()
  ├── ingest CSV
  ├── enrich holdings
  ├── compute alignment
  ├── compute overlays (intelligence only — no policy)
  ├── compute deployment queue (intelligence scores only)
  │
  ├── [NEW] load OperatorPolicyRegistry
  ├── [NEW] apply_policy_to_queue(queue, registry) → annotated queue
  ├── [NEW] apply_policy_to_overlays(overlays, registry) → annotated overlays
  │
  ├── run_reconciliation() ← receives pre-policy intelligence data
  └── write outputs (annotated queue + overlays)
```

**Key sequencing rule:** Reconciliation always runs on pre-policy intelligence data. Policy annotations are applied to the output layer only, after reconciliation.

---

## 6. `apply_policy_to_queue` Logic

```python
def apply_policy_to_queue(
    queue: list[CandidateEntry],
    registry: OperatorPolicyRegistry,
) -> list[CandidateEntry]:
    """Apply operator policies to deployment queue ordering and annotations.

    Sequence:
      1. Annotate all entries with their policy type
      2. For DO_NOT_SELL: remove entries that are sell/trim candidates
      3. For PREFERRED_ACCUMULATION: boost rank to top of buy cohort
      4. For SELL_LAST: push to tail of sell cohort
      5. Renumber ranks sequentially

    Intelligence scores are never modified.
    """
```

### DO_NOT_SELL Handling
```python
if registry.is_do_not_sell(entry.symbol):
    # If this entry is in a sell/trim context:
    #   - Remove from sell queue
    #   - Optionally retain in a separate "policy-suppressed" list for UI transparency
    entry.policy_type = "DO_NOT_SELL"
    entry.policy_annotation = "🔒 Operator Protected"
    entry.policy_protected = True
    # entry removed from execution queue; retained in overlay
```

### SELL_LAST Handling
```python
if registry.is_sell_last(entry.symbol):
    entry.policy_type = "SELL_LAST"
    entry.policy_annotation = "⏸ Sell Last"
    # Deferred: when sort happens, SELL_LAST entries are always pushed to tail
```

### PREFERRED_ACCUMULATION Handling
```python
if registry.is_preferred_accumulation(entry.symbol):
    entry.policy_type = "PREFERRED_ACCUMULATION"
    entry.policy_annotation = "⭐ Preferred Accumulation"
    entry.policy_rank_boost = True
    entry.original_rank = entry.rank
    # Rank boost applied during sort
```

---

## 7. State File Write Pattern

Consistent with existing `strategic_exit_symbols` POST handler:

```python
# Read → merge → write (atomic pattern)
with open(state_path, encoding="utf-8") as fh:
    state = json.load(fh)

policies = state.get("operator_policies", {})
policies[symbol.upper()] = {
    "symbol": symbol.upper(),
    "policy_type": policy_type,
    "status": "ACTIVE",
    "rationale": rationale,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "expires_at": expires_at,
    "revoked_at": None,
}
state["operator_policies"] = policies

with open(state_path, "w", encoding="utf-8") as fh:
    json.dump(state, fh, indent=2)
```

---

## 8. Governance Record in PAR Output

Each PAR's `run_metadata.json` records the active policy snapshot at run time:

```json
{
  "run_id": "PAR-20260603-XXXXXXXX",
  "policy_snapshot": {
    "TSLA": {"policy_type": "DO_NOT_SELL", "status": "ACTIVE"},
    "DODFX": {"policy_type": "SELL_LAST", "status": "ACTIVE"}
  }
}
```

This provides a point-in-time audit record: for any historical PAR, the operator can see which policies were active when the analysis was run.
