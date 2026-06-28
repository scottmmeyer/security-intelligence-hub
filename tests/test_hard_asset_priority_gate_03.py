from __future__ import annotations

from pathlib import Path

from src.sih.rotation_risk_monitor import rotation_risk_summary
from tests.test_commodity_fill_guard import _seed_alignment, _seed_common, _seed_deployment_queue


def _build_result(
    tmp_path: Path,
    *,
    commodities_actual: float = 0.0,
    commodities_target: float = 2.0,
    deployable_cash: float = 4702.65,
    equity_symbols: list[str] | None = None,
    commodity_symbols: list[str] | None = None,
):
    run_id, dq_path = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=commodities_actual,
        commodities_target=commodities_target,
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
        equity_symbols=equity_symbols or ["AAPL", "MSFT"],
        commodity_symbols=commodity_symbols or [],
    )
    result = rotation_risk_summary(tmp_path)
    return result, dq_path.read_text(encoding="utf-8")


def test_priority_gate_payload_present_and_display_only(tmp_path: Path):
    result, _ = _build_result(tmp_path)
    gate = result["hard_asset_priority_gate"]

    assert gate["display_only"] is True
    assert gate["operator_review_required"] is True
    assert gate["status"] == "ACTIVE_REVIEW"
    assert gate["verdict"] in {"PARTIAL_HARD_ASSET_FILL", "OPERATOR_REVIEW_REQUIRED"}
    assert gate["priority_verdict"] == gate["verdict"]
    assert gate["priority_score"] == gate["score"]
    assert gate["score_label"] == "Review pressure score"
    assert "trade-confidence score" in gate["score_note"]
    assert gate["recommended_operator_action"].startswith("OPERATOR REVIEW REQUIRED")
    assert any("hard-asset" in str(item).lower() for item in gate["rationale"])
    assert any("equity" in str(item).lower() for item in gate["rationale"])
    assert gate["capital_options"]
    assert gate["decision_factors"]
    assert [opt["label"] for opt in gate["capital_options"]] == [
        "Continue equity deployment",
        "Deployable-cash-only hard-asset fill",
        "Split approach",
        "Reserve cash",
        "Waive commodity target",
    ]


def test_priority_gate_prefers_hard_assets_when_cash_and_equity_pressure_exist(tmp_path: Path):
    result, _ = _build_result(tmp_path, deployable_cash=5000.0)
    gate = result["hard_asset_priority_gate"]

    assert gate["verdict"] == "PARTIAL_HARD_ASSET_FILL"
    assert gate["priority_bias"] == "HARD_ASSET_REVIEW_FIRST"
    assert gate["score"] >= 70
    assert gate["recommended_action"].startswith("OPERATOR REVIEW REQUIRED")
    assert gate["recommended_operator_action"] == gate["recommended_action"]
    assert gate["capital_options"][1]["label"] == "Deployable-cash-only hard-asset fill"
    assert gate["capital_options"][2]["label"] == "Split approach"
    assert gate["summary"]["direct_completion_candidate_count"] == 9
    assert gate["summary"]["equity_adjacent_proxy_count"] == 8


def test_priority_gate_alias_matches_primary_payload(tmp_path: Path):
    result, _ = _build_result(tmp_path)

    assert result["commodity_vs_equity_priority_gate"]["verdict"] == result["hard_asset_priority_gate"]["verdict"]
    assert result["commodity_vs_equity_priority_gate"]["score"] == result["hard_asset_priority_gate"]["score"]
    assert result["commodity_vs_equity_priority_gate"]["priority_verdict"] == result["hard_asset_priority_gate"]["priority_verdict"]
    assert result["commodity_vs_equity_priority_gate"]["priority_score"] == result["hard_asset_priority_gate"]["priority_score"]


def test_priority_gate_is_not_applicable_when_commodity_target_is_zero(tmp_path: Path):
    result, _ = _build_result(
        tmp_path,
        commodities_actual=0.0,
        commodities_target=0.0,
        deployable_cash=2500.0,
    )
    gate = result["hard_asset_priority_gate"]

    assert gate["verdict"] == "HARD_ASSET_NOT_APPLICABLE"
    assert gate["summary"]["commodities_target_pct"] == 0.0


def test_priority_gate_does_not_mutate_deployment_queue(tmp_path: Path):
    result, dq_before = _build_result(tmp_path, commodity_symbols=["PDBC"])
    dq_after = (tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / result["guardrail_run_id"] / "deployment_queue.json").read_text(encoding="utf-8")

    assert dq_before == dq_after
    assert result["hard_asset_priority_gate"]["guardrail_notes"]
