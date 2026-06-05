"""Phase 23.2 — Operator Portfolio Policy Layer.

Implements the Operator Policy Registry and policy application logic.

Architecture:
  Intelligence → [Operator Policy] → Action

Policies modify deployment queue ordering and output annotations.
Intelligence scores (ESS, composite, CW-DAS, replay, conviction) are NEVER
modified by this layer.  Reconciliation inputs are pre-policy data.

Policy types:
  DO_NOT_SELL         — symbol excluded from sell/trim execution queue
  SELL_LAST           — symbol ranked last in sell cohort (within cohort)
  CORE_ANCHOR         — annotation only; UI confirmation gate before trim
  PREFERRED_ACCUMULATION — boosted to top of buy deployment queue

Policy storage: data/operator/portfolio_alignment_state.json (operator_policies key)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


# ─── Policy taxonomy ─────────────────────────────────────────────────────────

POLICY_TYPES: frozenset[str] = frozenset({
    "DO_NOT_SELL",
    "SELL_LAST",
    "CORE_ANCHOR",
    "PREFERRED_ACCUMULATION",
})

# Pairs that cannot coexist on the same symbol
POLICY_CONFLICTS: frozenset[frozenset] = frozenset({
    frozenset({"DO_NOT_SELL", "SELL_LAST"}),
})

# Pairs that are semantically unusual (allowed but warned)
POLICY_WARNINGS: frozenset[frozenset] = frozenset({
    frozenset({"SELL_LAST", "PREFERRED_ACCUMULATION"}),
})

# opportunity_flag values that represent sell/trim intent
_SELL_CONTEXT_FLAGS: frozenset[str] = frozenset({"TRIM", "REDUCE_CANDIDATE"})


# ─── Policy data model ────────────────────────────────────────────────────────

@dataclass
class OperatorPolicy:
    """A single operator policy record for one symbol.

    status lifecycle:
      ACTIVE  — policy is currently in effect (or will be after symbol enters portfolio)
      REVOKED — operator explicitly revoked; preserved for audit trail
      EXPIRED — expires_at has passed; detected at read time by is_active()

    Policies are never hard-deleted; only ACTIVE policies are applied.
    """

    symbol:     str
    policy_type: str       # must be in POLICY_TYPES
    status:     str        # ACTIVE | REVOKED | EXPIRED
    rationale:  str
    created_at: str        # ISO 8601 UTC datetime
    expires_at: Optional[str] = None   # ISO 8601 UTC datetime, None = no expiration
    revoked_at: Optional[str] = None   # set when status → REVOKED

    def is_active(self) -> bool:
        """Return True iff this policy should be applied to the current run.

        Checks:
          1. status must be ACTIVE (not REVOKED)
          2. expires_at, if set, must not have passed
        """
        if self.status != "ACTIVE":
            return False
        if self.expires_at:
            try:
                exp = datetime.fromisoformat(self.expires_at)
                # Make naive datetimes UTC-aware for comparison
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp:
                    return False
            except ValueError:
                pass  # malformed expiry → treat as no expiry
        return True


# ─── Policy registry ──────────────────────────────────────────────────────────

class OperatorPolicyRegistry:
    """In-memory view of operator_policies from portfolio_alignment_state.json.

    Load once per analysis run; immutable after load.
    All lookups are O(1) via symbol-keyed dict.
    Unknown symbols at load time are silently skipped (forward-compat).
    """

    def __init__(self, policies: dict[str, OperatorPolicy]) -> None:
        self._policies: dict[str, OperatorPolicy] = policies

    @classmethod
    def load(cls, state_path: str) -> "OperatorPolicyRegistry":
        """Load from portfolio_alignment_state.json.

        Returns an empty registry if the file does not exist or has no
        operator_policies key (backward-compatible with pre-Phase 23.2 files).
        """
        if not os.path.exists(state_path):
            return cls({})
        try:
            with open(state_path, encoding="utf-8") as fh:
                state = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return cls({})

        raw = state.get("operator_policies", [])
        # Support both list format (written by API) and legacy dict format
        if isinstance(raw, list):
            raw_entries = raw
        elif isinstance(raw, dict):
            # Legacy dict format: {symbol: {policy_fields...}}
            raw_entries = [{"symbol": sym, **rec} for sym, rec in raw.items()]
        else:
            return cls({})

        policies: dict[str, OperatorPolicy] = {}
        for rec in raw_entries:
            if not isinstance(rec, dict):
                continue
            try:
                sym = str(rec.get("symbol", "")).upper()
                if not sym:
                    continue
                # Forward-compat: pull only known fields; ignore extras
                policies[sym] = OperatorPolicy(
                    symbol=sym,
                    policy_type=str(rec.get("policy_type", "")),
                    status=str(rec.get("status", "ACTIVE")),
                    rationale=str(rec.get("rationale", "")),
                    created_at=str(rec.get("created_at", "")),
                    expires_at=rec.get("expires_at"),
                    revoked_at=rec.get("revoked_at"),
                )
            except (TypeError, KeyError):
                continue  # skip malformed records

        return cls(policies)

    def get(self, symbol: str) -> Optional[OperatorPolicy]:
        """Return the policy record for symbol (any status), or None."""
        return self._policies.get(symbol.upper())

    def active_policy_type(self, symbol: str) -> Optional[str]:
        """Return the active policy_type for symbol, or None if no active policy."""
        p = self.get(symbol)
        if p and p.is_active():
            return p.policy_type
        return None

    def is_do_not_sell(self, symbol: str) -> bool:
        """True iff symbol has an active DO_NOT_SELL policy."""
        return self.active_policy_type(symbol) == "DO_NOT_SELL"

    def is_sell_last(self, symbol: str) -> bool:
        """True iff symbol has an active SELL_LAST policy."""
        return self.active_policy_type(symbol) == "SELL_LAST"

    def is_core_anchor(self, symbol: str) -> bool:
        """True iff symbol has an active CORE_ANCHOR policy."""
        return self.active_policy_type(symbol) == "CORE_ANCHOR"

    def is_preferred_accumulation(self, symbol: str) -> bool:
        """True iff symbol has an active PREFERRED_ACCUMULATION policy."""
        return self.active_policy_type(symbol) == "PREFERRED_ACCUMULATION"

    def all_active(self) -> dict[str, OperatorPolicy]:
        """Return a dict of symbol → policy for all currently active policies."""
        return {k: v for k, v in self._policies.items() if v.is_active()}

    def policy_snapshot(self) -> dict[str, dict]:
        """Return a compact snapshot of active policies for PAR audit embedding.

        Only ACTIVE policies are included.  Shape is serializable to JSON.
        """
        return {
            sym: {
                "policy_type": p.policy_type,
                "status":      p.status,
                "created_at":  p.created_at,
            }
            for sym, p in self._policies.items()
            if p.is_active()
        }


# ─── Conflict / warning detection ────────────────────────────────────────────

def check_policy_conflict(
    existing_type: Optional[str],
    new_type: str,
) -> tuple[bool, Optional[str]]:
    """Check whether adding new_type conflicts with existing_type on the same symbol.

    Returns:
        (is_conflict, message)
        is_conflict = True → reject the new policy (409)
        message     = human-readable explanation, or None if no issue
    """
    if existing_type is None or existing_type == new_type:
        return False, None
    pair = frozenset({existing_type, new_type})
    if pair in POLICY_CONFLICTS:
        return True, (
            f"Policy conflict: {existing_type} and {new_type} cannot coexist on the same symbol."
        )
    return False, None


def check_policy_warning(
    existing_type: Optional[str],
    new_type: str,
) -> Optional[str]:
    """Return a warning message if the combination is semantically unusual, else None."""
    if existing_type is None:
        return None
    pair = frozenset({existing_type, new_type})
    if pair in POLICY_WARNINGS:
        return (
            f"{existing_type} and {new_type} on the same symbol — unusual combination."
        )
    return None


# ─── Overlay annotation ───────────────────────────────────────────────────────

def build_policy_annotations(
    symbols: list[str],
    registry: OperatorPolicyRegistry,
) -> dict[str, dict]:
    """Return a symbol-keyed dict of policy annotation fields for each symbol.

    Called by runner.py to annotate security_overlays.csv output rows.

    Returns a dict of:
      {
        "TSLA": {
          "policy_type": "DO_NOT_SELL",
          "policy_annotation": "🔒 Operator Protected",
          "policy_protected": True,
        },
        ...
      }

    Symbols with no active policy return empty annotation fields.
    """
    annotations: dict[str, dict] = {}
    for sym in symbols:
        pt = registry.active_policy_type(sym)
        if pt is None:
            annotations[sym.upper()] = {
                "policy_type":       "",
                "policy_annotation": "",
                "policy_protected":  False,
            }
        else:
            annotations[sym.upper()] = {
                "policy_type":       pt,
                "policy_annotation": _policy_badge_text(pt),
                "policy_protected":  pt == "DO_NOT_SELL",
            }
    return annotations


def build_policy_suppressed_entries(
    overlays: list,
    registry: OperatorPolicyRegistry,
) -> list[dict]:
    """Build the list of policy-suppressed entries for deployment_queue.json.

    A "policy-suppressed" entry is a holding that has:
      - DO_NOT_SELL active policy
      - opportunity_flag in SELL_CONTEXT_FLAGS (TRIM or REDUCE_CANDIDATE)

    These entries would normally be actioned by intelligence but are blocked
    by operator policy.  They are recorded in the deployment queue output for
    governance transparency.

    Args:
        overlays: list of SecurityIntelligenceOverlay objects
        registry: loaded OperatorPolicyRegistry

    Returns:
        list of dicts suitable for JSON serialization
    """
    suppressed: list[dict] = []
    for ov in overlays:
        sym = getattr(ov, "symbol", "").upper()
        if not sym:
            continue
        if not registry.is_do_not_sell(sym):
            continue
        flag = str(getattr(ov, "opportunity_flag", "") or "").upper()
        if flag not in _SELL_CONTEXT_FLAGS:
            continue
        suppressed.append({
            "symbol":             sym,
            "policy_type":        "DO_NOT_SELL",
            "policy_annotation":  "🔒 Operator Protected",
            "intelligence_flag":  flag,
            "composite_score":    getattr(ov, "composite_score", None),
            "ess_score_text":     getattr(ov, "ess_score_text", None),
            "percent_of_portfolio": getattr(ov, "percent_of_portfolio", None),
            "note": "Excluded from trim/reduction execution by operator policy",
        })
    return suppressed


# ─── Badge text ───────────────────────────────────────────────────────────────

_POLICY_BADGE_TEXT: dict[str, str] = {
    "DO_NOT_SELL":          "🔒 Operator Protected",
    "SELL_LAST":            "⏸ Sell Last",
    "CORE_ANCHOR":          "⚓ Core Anchor",
    "PREFERRED_ACCUMULATION": "⭐ Preferred Accumulation",
}


def _policy_badge_text(policy_type: str) -> str:
    """Return the human-readable badge text for a policy type."""
    return _POLICY_BADGE_TEXT.get(policy_type, policy_type)


# ─── Execution State computation ─────────────────────────────────────────────

# opportunity_flag values that constitute a sell/trim/reduce action
_SELL_ACTION_FLAGS: frozenset[str] = frozenset({
    "TRIM",
    "REDUCE_CANDIDATE",
    "SELL",
    "REDUCE",
})


def compute_execution_state(
    symbol: str,
    opportunity_flag: str,
    registry: "OperatorPolicyRegistry",
) -> tuple[str, str]:
    """Compute (execution_state, effective_action) for a symbol.

    execution_state values
    ─────────────────────
    EXECUTABLE          No policy modifies execution; intelligence action proceeds.
    BLOCKED_BY_POLICY   DO_NOT_SELL is active and the intelligence action is a
                        sell/trim — execution is fully suppressed.
    DEFERRED_BY_POLICY  SELL_LAST is active and the action is a sell/trim — the
                        action is deferred to last in the cohort, not eliminated.
    INFORMATIONAL_ONLY  CORE_ANCHOR is active and the action is TRIM — the
                        signal is surfaced for awareness but requires manual
                        operator confirmation before any trim is taken.

    effective_action values
    ───────────────────────
    BLOCKED_BY_POLICY   → MONITOR_ONLY
    DEFERRED_BY_POLICY  → "{original_flag}_SELL_LAST"  (e.g. TRIM_SELL_LAST)
    INFORMATIONAL_ONLY  → MONITOR_ONLY
    EXECUTABLE          → original opportunity_flag (or HOLD if empty)

    Intelligence scores are never modified.  This is a pure output-layer
    annotation added on top of existing overlay data.
    """
    policy_type = registry.active_policy_type(symbol)
    flag = (opportunity_flag or "").upper()
    is_sell_action = flag in _SELL_ACTION_FLAGS

    if policy_type == "DO_NOT_SELL" and is_sell_action:
        return "BLOCKED_BY_POLICY", "MONITOR_ONLY"

    if policy_type == "SELL_LAST" and is_sell_action:
        return "DEFERRED_BY_POLICY", f"{flag}_SELL_LAST"

    if policy_type == "CORE_ANCHOR" and flag == "TRIM":
        return "INFORMATIONAL_ONLY", "MONITOR_ONLY"

    return "EXECUTABLE", flag or "HOLD"
