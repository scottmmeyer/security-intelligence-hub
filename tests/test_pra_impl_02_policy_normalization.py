"""Tests for PRA-IMPL-02 + ARCH-04: Policy-Aware Recommendation Normalization.

Validates:
- apply_policy_to_recommendations() correctly sets execution_state/effective_action
- DO_NOT_SELL → BLOCKED_BY_POLICY on sell-context recs (single-symbol)
- SELL_LAST → DEFERRED_BY_POLICY on sell-context recs (single-symbol)
- Multi-symbol recs use per-symbol evaluation (ARCH-04):
    at least one EXECUTABLE symbol → rec is EXECUTABLE
    all DEFERRED → rec is DEFERRED_BY_POLICY
    all BLOCKED → rec is BLOCKED_BY_POLICY
- symbol_execution_states dict populated with per-symbol states
- Drilldown holdings annotated with per-symbol policy states
- Non-sell-context recs are unaffected by sell policies
- TSLA (DO_NOT_SELL) validated on REDUCE_OVERWEIGHT single-symbol
- DODFX (SELL_LAST) validated on REDUCE_OVERWEIGHT single-symbol
- KGC no longer inherits DODFX deferral (ARCH-04 fix)
- card_lifecycle_state set to POLICY_ADJUSTED when any symbol has policy
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
    def test_REDUCE_OVERWEIGHT_TSLA_only_blocked(self):
        """Single-symbol rec with DO_NOT_SELL → BLOCKED_BY_POLICY."""
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["TSLA"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["effective_action"] == "MONITOR_ONLY"
        assert rec["card_lifecycle_state"] == "POLICY_ADJUSTED"

    def test_REDUCE_OVERWEIGHT_TSLA_and_NVDA_executable_because_nvda_free(self):
        """ARCH-04: TSLA blocked + NVDA executable → rec EXECUTABLE."""
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["TSLA", "NVDA"])
        apply_policy_to_recommendations([rec], reg)
        # Rec is EXECUTABLE because NVDA is unconstrained
        assert rec["execution_state"] == "EXECUTABLE"
        assert rec["card_lifecycle_state"] == "POLICY_ADJUSTED"
        # But per-symbol states show TSLA blocked
        assert rec["symbol_execution_states"]["TSLA"]["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["symbol_execution_states"]["NVDA"]["execution_state"] == "EXECUTABLE"

    def test_STRATEGIC_TRIM_blocked_single_symbol(self):
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("STRATEGIC_TRIM_CANDIDATE", ["TSLA"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"

    def test_TOP_TRIM_multi_symbol_executable(self):
        """ARCH-04: TOP_TRIM with TSLA blocked + MU free → rec EXECUTABLE."""
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("TOP_TRIM_CANDIDATES", ["TSLA", "MU"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"
        assert rec["symbol_execution_states"]["TSLA"]["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["symbol_execution_states"]["MU"]["execution_state"]   == "EXECUTABLE"

    def test_IMPROVE_RISK_PROFILE_blocked_single_symbol(self):
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
    def test_REDUCE_OVERWEIGHT_DODFX_only_deferred(self):
        """Single-symbol rec with SELL_LAST → DEFERRED_BY_POLICY."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["DODFX"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "DEFERRED_BY_POLICY"
        assert rec["effective_action"] == "REDUCE_SELL_LAST"
        assert rec["card_lifecycle_state"] == "POLICY_ADJUSTED"

    def test_REDUCE_OVERWEIGHT_DODFX_and_SBS_executable_because_sbs_free(self):
        """ARCH-04: DODFX deferred + SBS/VXUS free → rec EXECUTABLE."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["SBS", "DODFX", "VXUS"])
        apply_policy_to_recommendations([rec], reg)
        # Rec is EXECUTABLE because SBS and VXUS are unconstrained (ARCH-04 fix)
        assert rec["execution_state"] == "EXECUTABLE"
        assert rec["card_lifecycle_state"] == "POLICY_ADJUSTED"
        assert rec["symbol_execution_states"]["DODFX"]["execution_state"] == "DEFERRED_BY_POLICY"
        assert rec["symbol_execution_states"]["SBS"]["execution_state"]   == "EXECUTABLE"
        assert rec["symbol_execution_states"]["VXUS"]["execution_state"]  == "EXECUTABLE"

    def test_STRATEGIC_TRIM_deferred_single_symbol(self):
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

# ─────────────────────────────────────────────────────────────────────────────
# ARCH-04: Precedence — per-symbol semantics
# ─────────────────────────────────────────────────────────────────────────────

class TestPrecedence:
    def test_blocked_and_deferred_with_executable_third(self):
        """ARCH-04: TSLA blocked + DODFX deferred + SBS executable → rec EXECUTABLE."""
        reg = _registry(("TSLA", "DO_NOT_SELL"), ("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["DODFX", "TSLA", "SBS"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"
        assert rec["symbol_execution_states"]["TSLA"]["execution_state"]  == "BLOCKED_BY_POLICY"
        assert rec["symbol_execution_states"]["DODFX"]["execution_state"] == "DEFERRED_BY_POLICY"
        assert rec["symbol_execution_states"]["SBS"]["execution_state"]   == "EXECUTABLE"

    def test_all_blocked_stays_blocked(self):
        """All symbols blocked → rec BLOCKED_BY_POLICY."""
        reg = _registry(("TSLA", "DO_NOT_SELL"), ("MU", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["TSLA", "MU"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["effective_action"] == "MONITOR_ONLY"

    def test_all_deferred_stays_deferred(self):
        """All symbols SELL_LAST and no executable → rec DEFERRED_BY_POLICY."""
        reg = _registry(("DODFX", "SELL_LAST"), ("FIGFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["DODFX", "FIGFX"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "DEFERRED_BY_POLICY"

    def test_deferred_with_executable_is_executable(self):
        """SELL_LAST on one symbol when others are EXECUTABLE → rec EXECUTABLE."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["SBS", "DODFX", "VXUS"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["execution_state"] == "EXECUTABLE"

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
        """ARCH-04: Simulates actual portfolio. Per-symbol model."""
        reg = _registry(("TSLA", "DO_NOT_SELL"), ("DODFX", "SELL_LAST"))

        recs = [
            # International overweight: DODFX deferred, KGC/VEA/SBS executable
            _make_rec("REDUCE_OVERWEIGHT", ["SBS", "DODFX", "VEA", "KGC"]),
            # Ultra-mega overweight: TSLA blocked, MU/VOO/FXAIX executable
            _make_rec("REDUCE_OVERWEIGHT", ["MU", "VOO", "TSLA", "FXAIX"]),
            # Build US Large: neither policy applies
            _make_rec("INCREASE_UNDERWEIGHT", ["VOO", "IVV", "SPY"]),
        ]
        apply_policy_to_recommendations(recs, reg)

        intl_rec, mega_rec, build_rec = recs

        # ARCH-04: intl rec is now EXECUTABLE (SBS, VEA, KGC are all free)
        assert intl_rec["execution_state"] == "EXECUTABLE"
        assert intl_rec["card_lifecycle_state"] == "POLICY_ADJUSTED"
        # DODFX is still individually deferred
        assert intl_rec["symbol_execution_states"]["DODFX"]["execution_state"] == "DEFERRED_BY_POLICY"
        # KGC, VEA, SBS are individually EXECUTABLE (ARCH-04 fix)
        assert intl_rec["symbol_execution_states"]["KGC"]["execution_state"]   == "EXECUTABLE"
        assert intl_rec["symbol_execution_states"]["VEA"]["execution_state"]   == "EXECUTABLE"
        assert intl_rec["symbol_execution_states"]["SBS"]["execution_state"]   == "EXECUTABLE"

        # ARCH-04: mega rec is now EXECUTABLE (MU, VOO, FXAIX are free)
        assert mega_rec["execution_state"] == "EXECUTABLE"
        assert mega_rec["card_lifecycle_state"] == "POLICY_ADJUSTED"
        # TSLA is still individually blocked
        assert mega_rec["symbol_execution_states"]["TSLA"]["execution_state"]  == "BLOCKED_BY_POLICY"
        assert mega_rec["symbol_execution_states"]["MU"]["execution_state"]    == "EXECUTABLE"

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


# ─────────────────────────────────────────────────────────────────────────────
# ARCH-04: Per-symbol execution states (symbol_execution_states dict)
# ─────────────────────────────────────────────────────────────────────────────

class TestArch04PerSymbolStates:
    def test_symbol_execution_states_present_on_sell_rec(self):
        """symbol_execution_states dict is populated for every sell-context rec."""
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["TSLA", "MU", "NVDA"])
        apply_policy_to_recommendations([rec], reg)
        states = rec.get("symbol_execution_states", {})
        assert "TSLA" in states
        assert "MU" in states
        assert "NVDA" in states

    def test_symbol_execution_states_absent_on_non_sell_rec(self):
        """symbol_execution_states is not added to non-sell-context recs."""
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("INCREASE_UNDERWEIGHT", ["VOO"])
        apply_policy_to_recommendations([rec], reg)
        # Non-sell recs do not receive symbol_execution_states
        assert "symbol_execution_states" not in rec

    def test_kgc_not_deferred_when_dodfx_is_in_same_rec(self):
        """ARCH-04 core fix: KGC does not inherit DODFX's SELL_LAST deferral."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["DODFX", "KGC", "VEA", "TTNDY"])
        apply_policy_to_recommendations([rec], reg)
        # KGC, VEA, TTNDY have no individual policy — must be EXECUTABLE
        assert rec["symbol_execution_states"]["KGC"]["execution_state"]   == "EXECUTABLE"
        assert rec["symbol_execution_states"]["VEA"]["execution_state"]   == "EXECUTABLE"
        assert rec["symbol_execution_states"]["TTNDY"]["execution_state"] == "EXECUTABLE"
        # DODFX is still individually deferred
        assert rec["symbol_execution_states"]["DODFX"]["execution_state"] == "DEFERRED_BY_POLICY"
        # Rec-level: EXECUTABLE (not deferred) because KGC/VEA/TTNDY are free
        assert rec["execution_state"] == "EXECUTABLE"

    def test_mu_not_blocked_when_tsla_is_in_same_rec(self):
        """ARCH-04: MU does not inherit TSLA's DO_NOT_SELL block."""
        reg = _registry(("TSLA", "DO_NOT_SELL"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["TSLA", "MU"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["symbol_execution_states"]["TSLA"]["execution_state"] == "BLOCKED_BY_POLICY"
        assert rec["symbol_execution_states"]["MU"]["execution_state"]   == "EXECUTABLE"
        assert rec["execution_state"] == "EXECUTABLE"

    def test_drilldown_holdings_annotated_per_symbol(self):
        """Drilldown holdings receive per-symbol execution_state and policy_type."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["DODFX", "KGC"])
        rec["drilldown"] = {
            "holdings": [
                {"symbol": "DODFX", "market_value": 14000},
                {"symbol": "KGC",   "market_value": 6000},
            ]
        }
        apply_policy_to_recommendations([rec], reg)
        holdings = rec["drilldown"]["holdings"]
        dodfx_h = next(h for h in holdings if h["symbol"] == "DODFX")
        kgc_h   = next(h for h in holdings if h["symbol"] == "KGC")
        assert dodfx_h["execution_state"] == "DEFERRED_BY_POLICY"
        assert dodfx_h["policy_type"]     == "SELL_LAST"
        assert kgc_h["execution_state"]   == "EXECUTABLE"
        assert kgc_h["policy_type"]       == ""

    def test_policy_adjusted_set_when_any_symbol_constrained(self):
        """card_lifecycle_state is POLICY_ADJUSTED if any symbol has a policy constraint."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["SBS", "DODFX"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["card_lifecycle_state"] == "POLICY_ADJUSTED"

    def test_policy_not_adjusted_when_all_symbols_free(self):
        """card_lifecycle_state stays OBSERVED if all symbols are policy-free."""
        reg = _registry(("DODFX", "SELL_LAST"))
        rec = _make_rec("REDUCE_OVERWEIGHT", ["SBS", "VXUS"])
        apply_policy_to_recommendations([rec], reg)
        assert rec["card_lifecycle_state"] == "OBSERVED"
        assert rec["execution_state"] == "EXECUTABLE"

