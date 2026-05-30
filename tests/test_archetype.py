"""Tests for Phase 6.3 — Mandate-Specific Allocation Archetype Loader."""

import pytest
from src.portfolio.archetype import load_archetype_targets, get_archetype_display_name, DEFAULT_MANDATE


class TestDefaultMandate:
    def test_default_is_concentrated_alpha(self):
        assert DEFAULT_MANDATE == "CONCENTRATED_ALPHA"


class TestLoadArchetypeTargets:
    def test_concentrated_alpha_loads(self):
        targets = load_archetype_targets("CONCENTRATED_ALPHA")
        assert len(targets) > 0

    def test_growth_loads(self):
        targets = load_archetype_targets("GROWTH")
        assert len(targets) > 0

    def test_balanced_loads(self):
        targets = load_archetype_targets("BALANCED")
        assert len(targets) > 0

    def test_case_insensitive(self):
        t1 = load_archetype_targets("concentrated_alpha")
        t2 = load_archetype_targets("CONCENTRATED_ALPHA")
        assert t1 == t2

    def test_unknown_mandate_falls_back_gracefully(self):
        # Unknown mandate falls back to balanced profile, not an empty dict
        targets = load_archetype_targets("UNKNOWN_MANDATE_XYZ")
        assert isinstance(targets, dict)
        # Should have loaded balanced as fallback (non-empty)
        assert len(targets) > 0

    def test_values_are_floats(self):
        targets = load_archetype_targets("CONCENTRATED_ALPHA")
        for k, v in targets.items():
            assert isinstance(v, float), f"{k}: expected float, got {type(v)}"

    def test_all_required_nodes_present(self):
        required = [
            "EQUITIES", "FIXED_INCOME", "CASH",
            "EQUITIES.US", "EQUITIES.US.SMALL", "EQUITIES.US.MICRO",
        ]
        for mandate in ["BALANCED", "GROWTH", "CONCENTRATED_ALPHA"]:
            targets = load_archetype_targets(mandate)
            for node in required:
                assert node in targets, f"{mandate} missing node {node}"


class TestArchetypeDifferentiation:
    """Core validation: each mandate must produce materially different targets."""

    def test_small_cap_target_increases_from_balanced_to_concentrated(self):
        balanced = load_archetype_targets("BALANCED")
        growth = load_archetype_targets("GROWTH")
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert balanced["EQUITIES.US.SMALL"] < growth["EQUITIES.US.SMALL"]
        assert growth["EQUITIES.US.SMALL"] < alpha["EQUITIES.US.SMALL"]

    def test_micro_cap_target_increases_from_balanced_to_concentrated(self):
        balanced = load_archetype_targets("BALANCED")
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert alpha["EQUITIES.US.MICRO"] > balanced["EQUITIES.US.MICRO"]

    def test_fixed_income_target_decreases_from_balanced_to_concentrated(self):
        balanced = load_archetype_targets("BALANCED")
        growth = load_archetype_targets("GROWTH")
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert balanced["FIXED_INCOME"] > growth["FIXED_INCOME"]
        assert growth["FIXED_INCOME"] > alpha["FIXED_INCOME"]

    def test_cash_target_highest_in_concentrated_alpha(self):
        balanced = load_archetype_targets("BALANCED")
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert alpha["CASH"] > balanced["CASH"]

    def test_equities_target_highest_in_concentrated_alpha(self):
        balanced = load_archetype_targets("BALANCED")
        growth = load_archetype_targets("GROWTH")
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert alpha["EQUITIES"] > growth["EQUITIES"]
        assert growth["EQUITIES"] > balanced["EQUITIES"]

    def test_concentrated_alpha_small_cap_target_approx(self):
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert abs(alpha["EQUITIES.US.SMALL"] - 14.0) < 0.1

    def test_concentrated_alpha_cash_target_approx(self):
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert abs(alpha["CASH"] - 7.0) < 0.1

    def test_concentrated_alpha_fi_target_approx(self):
        alpha = load_archetype_targets("CONCENTRATED_ALPHA")
        assert abs(alpha["FIXED_INCOME"] - 2.0) < 0.1

    def test_balanced_fi_target_approx(self):
        balanced = load_archetype_targets("BALANCED")
        assert abs(balanced["FIXED_INCOME"] - 30.0) < 0.1

    def test_growth_equities_target_approx(self):
        growth = load_archetype_targets("GROWTH")
        assert abs(growth["EQUITIES"] - 78.0) < 0.1


class TestFallbackMandates:
    """DEFENSIVE and INCOME fall back to balanced; REPLAY_OPTIMIZED to growth."""

    def test_defensive_uses_balanced_values(self):
        defensive = load_archetype_targets("DEFENSIVE")
        balanced = load_archetype_targets("BALANCED")
        assert defensive == balanced

    def test_income_uses_balanced_values(self):
        income = load_archetype_targets("INCOME")
        balanced = load_archetype_targets("BALANCED")
        assert income == balanced

    def test_replay_optimized_uses_growth_values(self):
        replay = load_archetype_targets("REPLAY_OPTIMIZED")
        growth = load_archetype_targets("GROWTH")
        assert replay == growth


class TestDisplayName:
    def test_concentrated_alpha_display_name(self):
        name = get_archetype_display_name("CONCENTRATED_ALPHA")
        assert name == "Concentrated Alpha"

    def test_growth_display_name(self):
        name = get_archetype_display_name("GROWTH")
        assert name == "Growth"

    def test_balanced_display_name(self):
        name = get_archetype_display_name("BALANCED")
        assert name == "Balanced"

    def test_unknown_returns_none(self):
        # Unknown key not in _PROFILE_FILES → None
        name = get_archetype_display_name("TOTALLY_UNKNOWN_MANDATE_ZZZZZ")
        assert name is None
