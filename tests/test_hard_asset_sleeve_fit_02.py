from __future__ import annotations

import json
from pathlib import Path

from src.sih.rotation_risk_monitor import rotation_risk_summary
from tests.test_commodity_fill_guard import _seed_alignment, _seed_common, _seed_deployment_queue


def _build_result(tmp_path: Path, *, deployable_cash: float = 4702.65):
    run_id, dq_path = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=0.0,
        commodities_target=2.0,
        gold_actual=0.0,
        gold_target=1.0,
        energy_actual=0.0,
        energy_target=0.7,
        broad_actual=0.0,
        broad_target=0.3,
        ultra_mega_drift=4.0,
    )
    _seed_deployment_queue(
        tmp_path,
        run_id,
        deployable_cash=deployable_cash,
        equity_symbols=["AAPL", "MSFT"],
        commodity_symbols=[],
    )
    result = rotation_risk_summary(tmp_path)
    return result, dq_path.read_text(encoding="utf-8")


def test_full_target_gap_uses_total_portfolio_value(tmp_path: Path):
    result, _ = _build_result(tmp_path)
    summary = result["hard_asset_candidate_queue"]["summary"]

    assert summary["portfolio_value"] == 100000.0
    assert summary["gap_amount_full_portfolio"] == 2000.0


def test_deployable_cash_only_uses_cash_and_proportional_sleeve_weights(tmp_path: Path):
    result, _ = _build_result(tmp_path, deployable_cash=4700.0)
    nodes = result["hard_asset_candidate_queue"]["sleeve_nodes"]
    gold = next(n for n in nodes if n["node_key"] == "COMMODITIES.GOLD")
    energy = next(n for n in nodes if n["node_key"] == "COMMODITIES.ENERGY")
    broad = next(n for n in nodes if n["node_key"] == "COMMODITIES.BROAD_BASKET")

    assert gold["deployable_cash_fill_amount"] == 2350.0
    assert energy["deployable_cash_fill_amount"] == 1645.0
    assert broad["deployable_cash_fill_amount"] == 705.0


def test_direct_candidates_receive_direct_filler_classification(tmp_path: Path):
    result, _ = _build_result(tmp_path)
    rows = result["hard_asset_candidate_queue"]["sleeve_fit"]["candidate_fit_scores"]
    gld = next(r for r in rows if r["candidate"] == "GLD")

    assert gld["direct_filler"] is True
    assert gld["sleeve_fit_score"] >= 90


def test_kgc_is_gold_proxy_not_direct_gold_filler(tmp_path: Path):
    result, _ = _build_result(tmp_path)
    rows = result["hard_asset_candidate_queue"]["sleeve_fit"]["candidate_fit_scores"]
    kgc = next(r for r in rows if r["candidate"] == "KGC")

    assert kgc["candidate_type"] == "Gold miner equity proxy"
    assert kgc["direct_filler"] is False
    assert kgc["not_direct_filler_reason"] == "Not a direct COMMODITIES.GOLD filler"


def test_kgc_direct_sleeve_amount_is_zero(tmp_path: Path):
    result, _ = _build_result(tmp_path)
    rows = result["hard_asset_candidate_queue"]["sleeve_fit"]["candidate_fit_scores"]
    kgc = next(r for r in rows if r["candidate"] == "KGC")

    assert kgc["full_gap_amount"] == 0.0
    assert kgc["deployable_cash_only_amount"] == 0.0


def test_sleeve_fit_score_is_display_only(tmp_path: Path):
    result, dq_before = _build_result(tmp_path)
    dq_after = (tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / result["guardrail_run_id"] / "deployment_queue.json").read_text(encoding="utf-8")

    assert result["hard_asset_candidate_queue"]["sleeve_fit"]["display_only"] is True
    assert dq_before == dq_after


def test_existing_deployment_queue_order_unchanged(tmp_path: Path):
    result, dq_before = _build_result(tmp_path)
    dq_after = (tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / result["guardrail_run_id"] / "deployment_queue.json").read_text(encoding="utf-8")

    assert json.loads(dq_before)["queue"] == json.loads(dq_after)["queue"]


def test_rotation_risk_payload_alias_unchanged(tmp_path: Path):
    result, _ = _build_result(tmp_path)

    assert result["commodity_sleeve_completion_candidates"]["status"] == result["hard_asset_candidate_queue"]["status"]
