"""Tests for PRA-IMPL-02: Policy-Aware Recommendation Normalization.

Validates:
- apply_policy_to_recommendations() correctly sets execution_state/effective_action
- DO_NOT_SELL → BLOCKED_BY_POLICY on sell-context recs
- SELL_LAST → DEFERRED_BY_POLICY on sell-context recs
- Non-sell-context recs are unaffected by sell policies
- Most-restrictive-wins across multi-symbol recommendations
- TSLA (DO_NOT_SELL) validated on REDUCE_OVERWEIGHT
- DODFX (SELL_LAST) validated on REDUCE_OVERWEIGHT
- card_lifecycle_state set to POLICY_ADJUSTED when policy fires
- Effective actions resolved for EXECUTABLE increase recs
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone

import pytest

from src.portfolio.operator_policy import (
    OperatorPolicyRegistry,
    apply_policy_to_recommendations,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _registry(*policies: tuple[str, str]) -> OperatorPolicyRegistry:
    """Build a registry from [(symbol, policy_type), ...] tuples."""
    data = {
        "operator_policies": [
            {
                "symbol": sym,
                "policy_type": ptype,
                "status": "ACTIVE",
                "rationale": "test",
                "created_at": _now(),
            }
            for sym, ptype in policies
        ]
    }
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return OperatorPolicyRegistry.load(f.name)


def _make_rec(rec_type: str, symbols: list[str], **extra) -> dict:
    """Minimal recommendation dict matching PRA-IMPL-01 schema."""
    return {
        "recommendation_id": "REC-TEST01",
        "recommendation_type": rec_type,
        "affected_symbols": symbols,
        "card_type": "ACTION" if rec_type in (
            "REDUCE_OVERWEIGHT", "STRATEGIC_TRIM_CANDIDATE", "TOP_TRIM_CANDIDATES",
            "IMPROVE_RISK_PROFILE", "INCREASE_UNDERWEIGHT", "IMPROVE_REPLAY_ALIGNMENT",
            "IMPROVE_SECTOR_EXPOSURE",
        ) else "OBSERVATION",
        "execution_state": "EXECUTABLE",
        "effective_action": "",
        "card_lifecycle_state": "OBSERVED",
        **extra,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Core: DO_NOT_SELL
# ─────────────────────────────────────────────────────────────────────────────

class TestDoNotSell:
    def test_REDUCE_OVERWEIGHT_TSLA_blocked(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["TSLA", "NVDA"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["effective_action"] == "MONITOR_ONLY"
        assert rec["card_lifecycle_state"] == "POLICY_ADJUSTED"

    def test_STRATEGIC_TRIM_blocked(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("STRATEGIC_TRIM_CANDIDATE", ["TSLA"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"

    def test_TOP_TRIM_blocked(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("TOP_TRIM_CANDIDATES", ["TSLA", "MU"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["effective_action"] == "MONITOR_ONLY"

    def test_IMPROVE_RISK_PROFILE_blocked(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("IMPROVE_RISK_PROFILE", ["TSLA"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"

    def test_non_sell_type_not_blocked(self):
        """DO_NOT_SELL should not block INCREASE_UNDERWEIGHT."""
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("INCREASE_UNDERWEIGHT", ["VOO", "TSLA"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"
        assert rec["effective_action"] == "BUY"


# ─────────────────────────────────────────────────────────────────────────────
# Core: SELL_LAST
# ─────────────────────────────────────────────────────────────────────────────

class TestSellLast:
    def test_REDUCE_OVERWEIGHT_DODFX_deferred(self):
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["SBS", "DODFX", "VXUS"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "DEFERRED_BY_POLICY"
        assert rec["effective_action"] == "REDUCE_SELL_LAST"
        assert rec["card_lifecycle_state"] == "POLICY_ADJUSTED"

    def test_STRATEGIC_TRIM_deferred(self):
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("STRATEGIC_TRIM_CANDIDATE", ["DODFX"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "DEFERRED_BY_POLICY"
        assert rec["effective_action"] == "TRIM_SELL_LAST"

    def test_non_sell_type_not_deferred(self):
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("INCREASE_UNDERWEIGHT", ["VOO", "DODFX"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"


# ─────────────────────────────────────────────────────────────────────────────
# Precedence: most restrictive wins
# ─────────────────────────────────────────────────────────────────────────────

class TestPrecedence:
    def test_blocked_beats_deferred(self):
        """If one symbol is DO_NOT_SELL and another is SELL_LAST, BLOCKED wins."""
        reg = _registry(("TSLA", "DO_NOT_SELL"), ("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["DODFX", "TSLA", "SBS"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["effective_action"] == "MONITOR_ONLY"

    def test_deferred_beats_executable(self):
        """SELL_LAST on one symbol should trigger deferral even if others are EXECUTABLE."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["SBS", "DODFX", "VXUS"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "DEFERRED_BY_POLICY"

    def test_all_executable_stays_executable(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["SBS", "VXUS"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"


# ─────────────────────────────────────────────────────────────────────────────
# Non-sell recommendations: effective_action resolution
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutableEffectiveAction:
    def test_INCREASE_UNDERWEIGHT_gets_BUY(self):
        reg = _registry()
        rec = _make_rec("INCREASE_UNDERWEIGHT", ["VOO"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"
        assert rec["effective_action"] == "BUY"

    def test_IMPROVE_REPLAY_ALIGNMENT_gets_BUY(self):
        reg = _registry()
        rec = _make_rec("IMPROVE_REPLAY_ALIGNMENT", [])
        apply_policy_to_recommendations([rec], reg)
        assert rec["effective_action"] == "BUY"

    def test_IMPROVE_SECTOR_EXPOSURE_gets_BUY(self):
        reg = _registry()
        rec = _make_rec("IMPROVE_SECTOR_EXPOSURE", [])
        apply_policy_to_recommendations([rec], reg)
        assert rec["effective_action"] == "BUY"

    def test_DIVERSIFY_CONCENTRATION_gets_REDUCE(self):
        reg = _registry()
        rec = _make_rec("DIVERSIFY_CONCENTRATION", ["NVDA"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["effective_action"] == "REDUCE"


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio-level scenarios: TSLA and DODFX side by side
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioScenario:
    def test_tsla_do_not_sell_dodfx_sell_last(self):
        """Simulates PAR-20260529-7482D734 policy state."""
        reg = _registry(("TSLA", "DO_NOT_SELL"), ("DODFX", "SELL_LAST"))

        recs = [
            # International overweight: DODFX is a candidate
            _make_rec("REDUCE_OVERWEIGHT", ["SBS", "DODFX", "VXUS", "VEA"]),
            # Ultra-mega overweight: TSLA is a candidate
            _make_rec("REDUCE_OVERWEIGHT", ["MU", "VOO", "TSLA", "FXAIX"]),
            # Build US Large: neither policy applies
            _make_rec("INCREASE_UNDERWEIGHT", ["VOO", "IVV", "SPY"]),
        ]
        apply_policy_to_recommendations(recs, reg)

        intl_rec, mega_rec, build_rec = recs

        # DODFX → deferred
        assert intl_rec["execution_state"] == "DEFERRED_BY_POLICY"
        assert intl_rec["effective_action"] == "REDUCE_SELL_LAST"
        assert intl_rec["card_lifecycle_state"] == "POLICY_ADJUSTED"

        # TSLA → blocked
        assert mega_rec["execution_state"] == "BLOCKED_BY_POLICY"
        assert mega_rec["effective_action"] == "MONITOR_ONLY"
        assert mega_rec["card_lifecycle_state"] == "POLICY_ADJUSTED"

        # Build rec → unaffected
        assert build_rec["execution_state"] == "EXECUTABLE"
        assert build_rec["effective_action"] == "BUY"
        assert build_rec["card_lifecycle_state"] == "OBSERVED"

    def test_empty_affected_symbols_stays_executable(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", [])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"

    def test_empty_registry(self):
        reg = OperatorPolicyRegistry({})
        rec = _make_rec("REDUCE_OVERWEIGHT", ["TSLA", "DODFX"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"
        assert rec["effective_action"] == "REDUCE"

    def test_narrative_recs_not_mutated(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        recs = [
            {
                "recommendation_id": "REC-NARR01",
                "recommendation_type": "PORTFOLIO_CONSTRUCTION_NARRATIVE",
                "affected_symbols": ["TSLA", "MU"],
                "card_type": "NARRATIVE",
                "execution_state": "INFORMATIONAL_ONLY",
                "effective_action": "",
                "card_lifecycle_state": "OBSERVED",
            }
        ]
        apply_policy_to_recommendations(recs, reg)
        # Narrative recs are not sell-context — only effective_action may be set
        # execution_state is left unchanged since it's INFORMATIONAL_ONLY (not EXECUTABLE)
        assert recs[0]["execution_state"] == "INFORMATIONAL_ONLY"
