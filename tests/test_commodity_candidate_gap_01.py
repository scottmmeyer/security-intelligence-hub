"""COMMODITY-CANDIDATE-GAP-01 tests for display-only hard-asset candidate queue."""

from __future__ import annotations

from pathlib import Path

from src.sih.rotation_risk_monitor import rotation_risk_summary
from tests.test_commodity_fill_guard import (
    _seed_alignment,
    _seed_common,
    _seed_deployment_queue,
)


def _build_result(
    tmp_path: Path,
    *,
    commodities_actual: float = 0.0,
    commodities_target: float = 2.0,
    gold_actual: float = 0.0,
    gold_target: float = 1.0,
    energy_actual: float = 0.0,
    energy_target: float = 0.7,
    broad_actual: float = 0.0,
    broad_target: float = 0.3,
    deployable_cash: float = 4702.65,
    equity_symbols: list[str] | None = None,
    commodity_symbols: list[str] | None = None,
):
    run_id, _ = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=commodities_actual,
        commodities_target=commodities_target,
        gold_actual=gold_actual,
        gold_target=gold_target,
        energy_actual=energy_actual,
        energy_target=energy_target,
        broad_actual=broad_actual,
        broad_target=broad_target,
        ultra_mega_drift=4.0,
    )
    _seed_deployment_queue(
        tmp_path,
        run_id,
        deployable_cash=deployable_cash,
        equity_symbols=equity_symbols or ["AAPL", "MSFT"],
        commodity_symbols=commodity_symbols or [],
    )
    return rotation_risk_summary(tmp_path)


def test_candidate_queue_payload_present_and_display_only(tmp_path: Path):
    result = _build_result(tmp_path)
    payload = result["hard_asset_candidate_queue"]

    assert payload["display_only"] is True
    assert payload["operator_review_required"] is True
    assert payload["queue_scope"] == "COMMODITY_SLEEVE_COMPLETION_CANDIDATES"
    assert payload["status"] == "ACTIVE_REVIEW"


def test_candidate_queue_has_required_groups(tmp_path: Path):
    result = _build_result(tmp_path)
    groups = result["hard_asset_candidate_queue"]["candidate_groups"]

    by_node = {g["node"]: g for g in groups}
    assert set(by_node.keys()) == {
        "COMMODITIES.GOLD",
        "COMMODITIES.ENERGY",
        "COMMODITIES.BROAD_BASKET",
    }
    assert by_node["COMMODITIES.GOLD"]["candidates"]
    assert by_node["COMMODITIES.ENERGY"]["candidates"]
    assert by_node["COMMODITIES.BROAD_BASKET"]["candidates"]


def test_candidate_queue_summary_counts_direct_completion_and_proxies(tmp_path: Path):
    result = _build_result(tmp_path)
    summary = result["hard_asset_candidate_queue"]["summary"]

    assert summary["node_count"] == 3
    assert summary["total_gap_pp"] == 2.0
    assert summary["direct_completion_candidate_count"] == 9
    assert summary["equity_adjacent_proxy_count"] == 8


def test_candidate_queue_alias_payload_present(tmp_path: Path):
    result = _build_result(tmp_path)

    assert result["commodity_sleeve_completion_candidates"]["status"] == result["hard_asset_candidate_queue"]["status"]


def test_candidate_queue_status_is_not_applicable_when_target_zero(tmp_path: Path):
    result = _build_result(
        tmp_path,
        commodities_actual=0.0,
        commodities_target=0.0,
        gold_actual=0.0,
        gold_target=0.0,
        energy_actual=0.0,
        energy_target=0.0,
        broad_actual=0.0,
        broad_target=0.0,
    )
    payload = result["hard_asset_candidate_queue"]

    assert payload["status"] == "NOT_APPLICABLE"


def test_candidate_queue_status_is_no_gap_when_sleeve_filled(tmp_path: Path):
    result = _build_result(
        tmp_path,
        commodities_actual=2.0,
        commodities_target=2.0,
        gold_actual=1.0,
        gold_target=1.0,
        energy_actual=0.7,
        energy_target=0.7,
        broad_actual=0.3,
        broad_target=0.3,
    )
    payload = result["hard_asset_candidate_queue"]

    assert payload["status"] == "NO_GAP"
    assert payload["summary"]["total_gap_pp"] == 0.0


def test_candidate_queue_reports_direct_gold_candidates(tmp_path: Path):
    result = _build_result(tmp_path)
    nodes = result["hard_asset_candidate_queue"]["sleeve_nodes"]
    gold = next(n for n in nodes if n["node_key"] == "COMMODITIES.GOLD")

    symbols = {c["symbol"] for c in gold["direct_completion_candidates"]}
    assert {"GLD", "IAU", "SGOL"}.issubset(symbols)


def test_candidate_queue_reports_energy_direct_candidates(tmp_path: Path):
    result = _build_result(tmp_path)
    nodes = result["hard_asset_candidate_queue"]["sleeve_nodes"]
    energy = next(n for n in nodes if n["node_key"] == "COMMODITIES.ENERGY")

    symbols = {c["symbol"] for c in energy["direct_completion_candidates"]}
    assert {"USO", "BNO", "UNG"}.issubset(symbols)


def test_candidate_queue_reports_broad_basket_direct_candidates(tmp_path: Path):
    result = _build_result(tmp_path)
    nodes = result["hard_asset_candidate_queue"]["sleeve_nodes"]
    broad = next(n for n in nodes if n["node_key"] == "COMMODITIES.BROAD_BASKET")

    symbols = {c["symbol"] for c in broad["direct_completion_candidates"]}
    assert {"DBC", "PDBC", "GSG"}.issubset(symbols)


def test_candidate_queue_keeps_equity_adjacent_separate_from_direct(tmp_path: Path):
    result = _build_result(tmp_path)
    payload = result["hard_asset_candidate_queue"]
    nodes = payload["sleeve_nodes"]
    energy = next(n for n in nodes if n["node_key"] == "COMMODITIES.ENERGY")

    direct_symbols = {c["symbol"] for c in energy["direct_completion_candidates"]}
    proxy_symbols = {c["symbol"] for c in energy["equity_adjacent_proxies"]}

    assert "USO" in direct_symbols
    assert "XLE" in proxy_symbols
    assert not (direct_symbols & proxy_symbols)
    assert "XLE" in payload["equity_adjacent_substitutes"]


def test_candidate_queue_estimates_gap_dollars_from_deployable_cash(tmp_path: Path):
    result = _build_result(tmp_path, deployable_cash=5000.0)
    summary = result["hard_asset_candidate_queue"]["summary"]

    assert summary["total_gap_pp"] == 2.0
    assert summary["portfolio_value"] == 100000.0
    assert summary["approx_gap_dollars"] == 2000.0
    assert summary["deployable_cash_only_amount"] == 5000.0


def test_candidate_queue_reports_both_amount_bases_by_sleeve(tmp_path: Path):
    result = _build_result(tmp_path, deployable_cash=5000.0)
    nodes = result["hard_asset_candidate_queue"]["sleeve_nodes"]
    gold = next(n for n in nodes if n["node_key"] == "COMMODITIES.GOLD")
    energy = next(n for n in nodes if n["node_key"] == "COMMODITIES.ENERGY")
    broad = next(n for n in nodes if n["node_key"] == "COMMODITIES.BROAD_BASKET")

    assert gold["gap_amount_full_portfolio"] == 1000.0
    assert gold["deployable_cash_fill_amount"] == 2500.0
    assert energy["gap_amount_full_portfolio"] == 700.0
    assert energy["deployable_cash_fill_amount"] == 1750.0
    assert broad["gap_amount_full_portfolio"] == 300.0
    assert broad["deployable_cash_fill_amount"] == 750.0


def test_candidate_queue_includes_sleeve_fit_payload(tmp_path: Path):
    result = _build_result(tmp_path)
    payload = result["hard_asset_candidate_queue"]

    assert payload["sleeve_fit"]["display_only"] is True
    assert payload["sleeve_fit"]["operator_review_required"] is True
    assert payload["sleeve_fit"]["scoring_basis"] == "SLEEVE_COMPLETION_FIT_NOT_EQUITY_RANKING"


def test_candidate_queue_classifies_kgc_as_gold_proxy_not_direct_filler(tmp_path: Path):
    result = _build_result(tmp_path)
    rows = result["hard_asset_candidate_queue"]["sleeve_fit"]["candidate_fit_scores"]
    kgc = next(r for r in rows if r["candidate"] == "KGC")

    assert kgc["candidate_type"] == "Gold miner equity proxy"
    assert kgc["direct_filler"] is False
    assert kgc["full_gap_amount"] == 0.0
    assert kgc["deployable_cash_only_amount"] == 0.0
    assert kgc["not_direct_filler_reason"] == "Not a direct COMMODITIES.GOLD filler"


def test_candidate_queue_kgc_shows_live_context_when_present(tmp_path: Path):
    result = _build_result(tmp_path)
    rows = result["hard_asset_candidate_queue"]["sleeve_fit"]["candidate_fit_scores"]
    kgc = next(r for r in rows if r["candidate"] == "KGC")

    assert kgc["current_holding"] is False
    assert "gold-mining equity" in kgc["classification_note"]


def test_candidate_queue_lists_equity_adjacent_proxy_with_disclaimer(tmp_path: Path):
    result = _build_result(tmp_path)
    payload = result["hard_asset_candidate_queue"]
    nodes = payload["sleeve_nodes"]
    energy = next(n for n in nodes if n["node_key"] == "COMMODITIES.ENERGY")

    proxy_symbols = {c["symbol"] for c in energy["equity_adjacent_proxies"]}
    assert "XLE" in proxy_symbols
    assert "do not directly fill" in payload["equity_proxy_disclaimer"]


def test_candidate_queue_passes_operator_choices_from_guard(tmp_path: Path):
    result = _build_result(tmp_path)
    payload = result["hard_asset_candidate_queue"]

    assert "fill_hard_asset_sleeve" in payload["operator_choices"]


def test_candidate_queue_reports_existing_queue_candidates(tmp_path: Path):
    result = _build_result(tmp_path, commodity_symbols=["PDBC"])
    nodes = result["hard_asset_candidate_queue"]["sleeve_nodes"]
    energy = next(n for n in nodes if n["node_key"] == "COMMODITIES.ENERGY")

    existing_symbols = {c["symbol"] for c in energy["existing_queue_candidates"]}
    assert "PDBC" in existing_symbols
