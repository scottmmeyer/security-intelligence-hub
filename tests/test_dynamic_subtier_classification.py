"""Tests for dynamic analytical market-cap subtier classification.

Covers:
  - Thirds partitioning (divisible, non-divisible, edge cases)
  - Deterministic tie-breaking
  - Non-MEGA passthrough
  - Snapshot freeze / idempotency
  - Replay engine subtier filtering
  - Replay backward compatibility (no subtier arg)
  - Policy malformed detection
  - Validator: invalid Fidelity/subtier combo
  - ConcentrationScaffold defaults
"""

from __future__ import annotations

import pytest

from src.scoring.market_cap_subtier_classifier import (
    _compute_mega_thirds,
    classify_analytical_subtiers,
    load_subtier_policy,
)
from src.validation.market_cap_subtier_validator import (
    validate_mega_subtier_coverage,
    validate_no_duplicate_rank_assignment,
    validate_no_invalid_fidelity_subtier_combo,
    validate_subtier_partitioning_completeness,
    validate_subtier_policy_config,
)
from src.models.analytical_models import AnalyticalUniverseRow, ConcentrationScaffold
from src.replay.replay_engine import select_top_n_replay


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mega_rows(caps_and_symbols: list[tuple[int, str]]) -> list[dict]:
    """Build minimal row dicts for MEGA classification tests."""
    return [
        {
            "symbol": sym,
            "market_cap_bucket": "MEGA",
            "market_cap_raw_usd": cap,
        }
        for cap, sym in caps_and_symbols
    ]


def _make_non_mega_row(symbol: str, bucket: str) -> dict:
    return {
        "symbol": symbol,
        "market_cap_bucket": bucket,
        "market_cap_raw_usd": 1_000_000_000,
    }


_VALID_POLICY = {
    "policy_id": "DYNAMIC_MEGA_THIRDS_V1",
    "methodology_type": "DYNAMIC_RANK_BASED",
    "partitioning_strategy": "MEGA_ONLY",
    "ranking_basis": "MARKET_CAP_DESCENDING",
    "tie_break_rule": "SYMBOL_ASCENDING",
    "partition_rules": [
        {"label": "HYPER_MEGA"},
        {"label": "ULTRA_MEGA"},
        {"label": "EXTENDED_MEGA"},
    ],
}


# ---------------------------------------------------------------------------
# Phase 2: _compute_mega_thirds
# ---------------------------------------------------------------------------

class TestThirdsPartitioning:
    def test_divisible_9(self):
        h, u, e = _compute_mega_thirds(9)
        assert (h, u, e) == (3, 3, 3)
        assert h + u + e == 9

    def test_nondivisible_10(self):
        h, u, e = _compute_mega_thirds(10)
        assert (h, u, e) == (4, 3, 3)
        assert h + u + e == 10

    def test_nondivisible_11(self):
        h, u, e = _compute_mega_thirds(11)
        assert (h, u, e) == (4, 4, 3)
        assert h + u + e == 11

    def test_edge_n1(self):
        h, u, e = _compute_mega_thirds(1)
        assert (h, u, e) == (1, 0, 0)
        assert h + u + e == 1

    def test_edge_n2(self):
        h, u, e = _compute_mega_thirds(2)
        assert (h, u, e) == (1, 1, 0)
        assert h + u + e == 2

    def test_edge_n3(self):
        h, u, e = _compute_mega_thirds(3)
        assert (h, u, e) == (1, 1, 1)
        assert h + u + e == 3

    def test_edge_n4(self):
        h, u, e = _compute_mega_thirds(4)
        assert (h, u, e) == (2, 1, 1)
        assert h + u + e == 4

    def test_edge_n0(self):
        h, u, e = _compute_mega_thirds(0)
        assert (h, u, e) == (0, 0, 0)

    def test_large_n(self):
        n = 100
        h, u, e = _compute_mega_thirds(n)
        assert h + u + e == n
        # All thirds roughly equal, hyper slightly larger on remainder
        assert abs(h - e) <= 1
        assert abs(h - u) <= 1


# ---------------------------------------------------------------------------
# Phase 2: classify_analytical_subtiers — correct label assignment
# ---------------------------------------------------------------------------

class TestClassifyAnalyticalSubtiers:
    def test_9_mega_splits_evenly(self):
        rows = _make_mega_rows([
            (3_000_000_000_000, "AAPL"),
            (2_800_000_000_000, "MSFT"),
            (2_600_000_000_000, "NVDA"),
            (2_000_000_000_000, "GOOGL"),
            (1_800_000_000_000, "AMZN"),
            (1_600_000_000_000, "META"),
            (1_000_000_000_000, "BRK"),
            (900_000_000_000,  "TSM"),
            (800_000_000_000,  "LLY"),
        ])
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        by_sym = {r["symbol"]: r["analytical_market_cap_subtier"] for r in enriched}
        assert by_sym["AAPL"] == "HYPER_MEGA"
        assert by_sym["MSFT"] == "HYPER_MEGA"
        assert by_sym["NVDA"] == "HYPER_MEGA"
        assert by_sym["GOOGL"] == "ULTRA_MEGA"
        assert by_sym["AMZN"] == "ULTRA_MEGA"
        assert by_sym["META"] == "ULTRA_MEGA"
        assert by_sym["BRK"] == "EXTENDED_MEGA"
        assert by_sym["TSM"] == "EXTENDED_MEGA"
        assert by_sym["LLY"] == "EXTENDED_MEGA"

    def test_classification_policy_id_propagated(self):
        rows = _make_mega_rows([(1_000_000_000_000, "AAPL")])
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        assert enriched[0]["classification_policy_id"] == "DYNAMIC_MEGA_THIRDS_V1"

    def test_classification_snapshot_date_propagated(self):
        rows = _make_mega_rows([(1_000_000_000_000, "AAPL")])
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        assert enriched[0]["classification_snapshot_date"] == "2026-05-15"

    def test_non_mega_passthrough_large(self):
        rows = [_make_non_mega_row("ORCL", "LARGE")]
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        assert enriched[0]["analytical_market_cap_subtier"] == "LARGE"

    def test_non_mega_passthrough_mid(self):
        rows = [_make_non_mega_row("XYZ", "MID")]
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        assert enriched[0]["analytical_market_cap_subtier"] == "MID"

    def test_non_mega_passthrough_small(self):
        rows = [_make_non_mega_row("ABC", "SMALL")]
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        assert enriched[0]["analytical_market_cap_subtier"] == "SMALL"

    def test_non_mega_passthrough_micro(self):
        rows = [_make_non_mega_row("DEF", "MICRO")]
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        assert enriched[0]["analytical_market_cap_subtier"] == "MICRO"

    def test_original_dicts_not_mutated(self):
        original = _make_mega_rows([(1_000_000_000_000, "AAPL")])
        original_copy = dict(original[0])
        classify_analytical_subtiers(original, _VALID_POLICY, "2026-05-15")
        assert original[0] == original_copy  # no mutation

    def test_snapshot_freeze_idempotent(self):
        rows = _make_mega_rows([
            (3_000_000_000_000, "AAPL"),
            (2_000_000_000_000, "MSFT"),
            (1_000_000_000_000, "NVDA"),
        ])
        result1 = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        result2 = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        labels1 = [(r["symbol"], r["analytical_market_cap_subtier"]) for r in result1]
        labels2 = [(r["symbol"], r["analytical_market_cap_subtier"]) for r in result2]
        assert labels1 == labels2


# ---------------------------------------------------------------------------
# Deterministic tie-breaking
# ---------------------------------------------------------------------------

class TestDeterministicTieBreaking:
    def test_same_cap_sorts_by_symbol_ascending(self):
        """When two symbols have the same cap, they must be ordered alphabetically."""
        rows = _make_mega_rows([
            (1_000_000_000_000, "ZETA"),
            (1_000_000_000_000, "ALPHA"),
            (1_000_000_000_000, "MIDCO"),
        ])
        enriched = classify_analytical_subtiers(rows, _VALID_POLICY, "2026-05-15")
        by_sym = {r["symbol"]: r["analytical_market_cap_subtier"] for r in enriched}
        # With N=3: ALPHA→HYPER, MIDCO→ULTRA, ZETA→EXTENDED (symbol ascending tie-break)
        assert by_sym["ALPHA"] == "HYPER_MEGA"
        assert by_sym["MIDCO"] == "ULTRA_MEGA"
        assert by_sym["ZETA"] == "EXTENDED_MEGA"

    def test_tie_break_is_stable_regardless_of_input_order(self):
        rows_a = _make_mega_rows([
            (1_000_000_000_000, "ZETA"),
            (1_000_000_000_000, "ALPHA"),
        ])
        rows_b = _make_mega_rows([
            (1_000_000_000_000, "ALPHA"),
            (1_000_000_000_000, "ZETA"),
        ])
        result_a = {r["symbol"]: r["analytical_market_cap_subtier"] for r in classify_analytical_subtiers(rows_a, _VALID_POLICY, "2026-01-01")}
        result_b = {r["symbol"]: r["analytical_market_cap_subtier"] for r in classify_analytical_subtiers(rows_b, _VALID_POLICY, "2026-01-01")}
        assert result_a == result_b


# ---------------------------------------------------------------------------
# Phase 8: Validators
# ---------------------------------------------------------------------------

class TestValidateSubtierPolicyConfig:
    def test_valid_policy_returns_no_errors(self):
        assert validate_subtier_policy_config(_VALID_POLICY) == []

    def test_missing_policy_id(self):
        bad = {k: v for k, v in _VALID_POLICY.items() if k != "policy_id"}
        errors = validate_subtier_policy_config(bad)
        assert any("policy_id" in e for e in errors)

    def test_missing_partition_rules(self):
        bad = {k: v for k, v in _VALID_POLICY.items() if k != "partition_rules"}
        errors = validate_subtier_policy_config(bad)
        assert any("partition_rules" in e or "required" in e.lower() for e in errors)

    def test_invalid_methodology_type(self):
        bad = {**_VALID_POLICY, "methodology_type": "STATIC_FIXED_THRESHOLDS"}
        errors = validate_subtier_policy_config(bad)
        assert any("methodology_type" in e for e in errors)

    def test_non_dict_raises_error(self):
        errors = validate_subtier_policy_config("not-a-dict")  # type: ignore[arg-type]
        assert errors  # must return at least one error

    def test_empty_partition_rules_list(self):
        bad = {**_VALID_POLICY, "partition_rules": []}
        errors = validate_subtier_policy_config(bad)
        assert errors


class TestValidateMegaSubtierCoverage:
    def test_valid_mega_rows(self):
        rows = [{"symbol": "AAPL", "market_cap_bucket": "MEGA", "analytical_market_cap_subtier": "HYPER_MEGA"}]
        assert validate_mega_subtier_coverage(rows) == []

    def test_mega_row_missing_subtier(self):
        rows = [{"symbol": "AAPL", "market_cap_bucket": "MEGA", "analytical_market_cap_subtier": ""}]
        errors = validate_mega_subtier_coverage(rows)
        assert errors

    def test_non_mega_rows_ignored(self):
        rows = [{"symbol": "ORCL", "market_cap_bucket": "LARGE", "analytical_market_cap_subtier": "LARGE"}]
        assert validate_mega_subtier_coverage(rows) == []


class TestValidateNoInvalidFidelitySubtierCombo:
    def test_large_with_hyper_mega_is_invalid(self):
        rows = [{"symbol": "ORCL", "market_cap_bucket": "LARGE", "analytical_market_cap_subtier": "HYPER_MEGA"}]
        errors = validate_no_invalid_fidelity_subtier_combo(rows)
        assert errors

    def test_mega_with_hyper_mega_is_valid(self):
        rows = [{"symbol": "AAPL", "market_cap_bucket": "MEGA", "analytical_market_cap_subtier": "HYPER_MEGA"}]
        assert validate_no_invalid_fidelity_subtier_combo(rows) == []

    def test_mid_with_extended_mega_is_invalid(self):
        rows = [{"symbol": "XYZ", "market_cap_bucket": "MID", "analytical_market_cap_subtier": "EXTENDED_MEGA"}]
        errors = validate_no_invalid_fidelity_subtier_combo(rows)
        assert errors


class TestValidateSubtierPartitioningCompleteness:
    def test_empty_subtier_flagged(self):
        rows = [{"symbol": "AAA", "analytical_market_cap_subtier": ""}]
        errors = validate_subtier_partitioning_completeness(rows)
        assert errors

    def test_populated_subtier_passes(self):
        rows = [{"symbol": "AAA", "analytical_market_cap_subtier": "HYPER_MEGA"}]
        assert validate_subtier_partitioning_completeness(rows) == []


class TestValidateNoDuplicateRankAssignment:
    def test_duplicate_mega_symbol(self):
        rows = [
            {"symbol": "AAPL", "market_cap_bucket": "MEGA", "analytical_market_cap_subtier": "HYPER_MEGA"},
            {"symbol": "AAPL", "market_cap_bucket": "MEGA", "analytical_market_cap_subtier": "ULTRA_MEGA"},
        ]
        errors = validate_no_duplicate_rank_assignment(rows)
        assert errors

    def test_unique_mega_symbols_pass(self):
        rows = [
            {"symbol": "AAPL", "market_cap_bucket": "MEGA", "analytical_market_cap_subtier": "HYPER_MEGA"},
            {"symbol": "MSFT", "market_cap_bucket": "MEGA", "analytical_market_cap_subtier": "ULTRA_MEGA"},
        ]
        assert validate_no_duplicate_rank_assignment(rows) == []


# ---------------------------------------------------------------------------
# Phase 5: Replay engine subtier filtering
# ---------------------------------------------------------------------------

def _make_analytical_row(symbol: str, bucket: str, subtier: str, score: float = 3.0) -> AnalyticalUniverseRow:
    return AnalyticalUniverseRow(
        security_id=f"FIDELITY:{symbol}",
        symbol=symbol,
        security_type="Common Stock",
        snapshot_date="2026-05-15",
        run_id="RUN-TEST-001",
        market_cap_bucket=bucket,
        geography="US",
        country="US",
        industry="ALL",
        sector="ALL",
        composite_score=score,
        ess_score_text="BULLISH",
        zacks_rating="",
        yahoo_score="",
        danelfin_score="",
        benchmark_id="SPY",
        investable_vehicle_id="SPY",
        price_at_snapshot="",
        provider_lineage="provider=FIDELITY;source_file=test",
        analytical_market_cap_subtier=subtier,
        classification_policy_id="DYNAMIC_MEGA_THIRDS_V1",
        classification_snapshot_date="2026-05-15",
    )


class TestReplayEngineSubtierFilter:
    def _build_rows(self) -> list[AnalyticalUniverseRow]:
        return [
            _make_analytical_row("AAPL",  "MEGA",  "HYPER_MEGA",    score=5.0),
            _make_analytical_row("MSFT",  "MEGA",  "HYPER_MEGA",    score=4.9),
            _make_analytical_row("NVDA",  "MEGA",  "ULTRA_MEGA",    score=4.5),
            _make_analytical_row("GOOGL", "MEGA",  "ULTRA_MEGA",    score=4.0),
            _make_analytical_row("META",  "MEGA",  "EXTENDED_MEGA", score=3.5),
            _make_analytical_row("BRK",   "MEGA",  "EXTENDED_MEGA", score=3.0),
        ]

    def test_hyper_mega_filter_returns_only_hyper(self):
        rows = self._build_rows()
        selection, _ = select_top_n_replay(
            analytical_rows=rows,
            start_date="2026-05-15",
            end_date="2027-05-15",
            market_cap_bucket="MEGA",
            geography="US",
            industry="ALL",
            top_n=10,
            filter_analytical_subtier="HYPER_MEGA",
        )
        assert set(selection.selected_symbols) == {"AAPL", "MSFT"}

    def test_ultra_mega_filter_returns_only_ultra(self):
        rows = self._build_rows()
        selection, _ = select_top_n_replay(
            analytical_rows=rows,
            start_date="2026-05-15",
            end_date="2027-05-15",
            market_cap_bucket="MEGA",
            geography="US",
            industry="ALL",
            top_n=10,
            filter_analytical_subtier="ULTRA_MEGA",
        )
        assert set(selection.selected_symbols) == {"NVDA", "GOOGL"}

    def test_extended_mega_filter_returns_only_extended(self):
        rows = self._build_rows()
        selection, _ = select_top_n_replay(
            analytical_rows=rows,
            start_date="2026-05-15",
            end_date="2027-05-15",
            market_cap_bucket="MEGA",
            geography="US",
            industry="ALL",
            top_n=10,
            filter_analytical_subtier="EXTENDED_MEGA",
        )
        assert set(selection.selected_symbols) == {"META", "BRK"}

    def test_subtier_filter_is_case_insensitive(self):
        rows = self._build_rows()
        selection, _ = select_top_n_replay(
            analytical_rows=rows,
            start_date="2026-05-15",
            end_date="2027-05-15",
            market_cap_bucket="MEGA",
            geography="US",
            industry="ALL",
            top_n=10,
            filter_analytical_subtier="hyper_mega",
        )
        assert set(selection.selected_symbols) == {"AAPL", "MSFT"}

    def test_replay_id_includes_subtier_suffix(self):
        rows = self._build_rows()
        selection, _ = select_top_n_replay(
            analytical_rows=rows,
            start_date="2026-05-15",
            end_date="2027-05-15",
            market_cap_bucket="MEGA",
            geography="US",
            industry="ALL",
            top_n=5,
            filter_analytical_subtier="HYPER_MEGA",
        )
        assert "HYPER_MEGA" in selection.replay_id

    def test_backward_compatibility_no_subtier_arg(self):
        rows = self._build_rows()
        # Without filter_analytical_subtier all 6 MEGA rows must be candidates
        selection, filtered = select_top_n_replay(
            analytical_rows=rows,
            start_date="2026-05-15",
            end_date="2027-05-15",
            market_cap_bucket="MEGA",
            geography="US",
            industry="ALL",
            top_n=10,
        )
        assert len(selection.selected_symbols) == 6

    def test_replay_id_no_subtier_suffix_when_not_filtered(self):
        rows = self._build_rows()
        selection, _ = select_top_n_replay(
            analytical_rows=rows,
            start_date="2026-05-15",
            end_date="2027-05-15",
            market_cap_bucket="MEGA",
            geography="US",
            industry="ALL",
            top_n=5,
        )
        # replay_id must NOT contain any MEGA subtier token when no filter is provided
        assert "HYPER_MEGA" not in selection.replay_id
        assert "ULTRA_MEGA" not in selection.replay_id
        assert "EXTENDED_MEGA" not in selection.replay_id


# ---------------------------------------------------------------------------
# Phase 3: ConcentrationScaffold defaults
# ---------------------------------------------------------------------------

class TestConcentrationScaffold:
    def test_all_fields_default_to_none(self):
        scaffold = ConcentrationScaffold()
        assert scaffold.portfolio_weight_percent is None
        assert scaffold.concentration_rank is None
        assert scaffold.concentration_tier is None

    def test_can_be_constructed_with_values(self):
        scaffold = ConcentrationScaffold(
            portfolio_weight_percent=7.5,
            concentration_rank=1,
            concentration_tier="DOMINANT",
        )
        assert scaffold.portfolio_weight_percent == 7.5
        assert scaffold.concentration_rank == 1
        assert scaffold.concentration_tier == "DOMINANT"


# ---------------------------------------------------------------------------
# Policy loading from disk
# ---------------------------------------------------------------------------

class TestLoadSubtierPolicyFromDisk:
    def test_default_policy_loads_without_error(self):
        policy = load_subtier_policy()
        assert policy["policy_id"] == "DYNAMIC_MEGA_THIRDS_V1"
        assert policy["methodology_type"] == "DYNAMIC_RANK_BASED"

    def test_default_policy_passes_validator(self):
        policy = load_subtier_policy()
        errors = validate_subtier_policy_config(policy)
        assert errors == []
