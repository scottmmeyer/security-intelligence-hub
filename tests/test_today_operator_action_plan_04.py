from __future__ import annotations

import json
from pathlib import Path

from src.sih.rotation_risk_monitor import rotation_risk_summary
from tests.test_commodity_fill_guard import _seed_alignment, _seed_common, _seed_deployment_queue


def test_today_operator_action_plan_display_only_and_ordered_actions(tmp_path: Path) -> None:
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
        ultra_mega_drift=5.0,
    )
    _seed_deployment_queue(
        tmp_path,
        run_id,
        deployable_cash=4702.65,
        equity_symbols=["AAPL", "MSFT", "NUE"],
        commodity_symbols=[],
    )

    before = dq_path.read_text(encoding="utf-8")
    result = rotation_risk_summary(tmp_path)
    after = dq_path.read_text(encoding="utf-8")

    plan = result.get("today_operator_action_plan")
    assert isinstance(plan, dict)
    assert result.get("daily_operator_action_plan") == plan

    # Display-only controls
    assert plan.get("display_only") is True
    assert plan.get("operator_review_required") is True
    assert plan.get("not_trade_instructions") is True
    controls = set(plan.get("controls") or [])
    assert "NO CAPITAL DEPLOYMENT QUEUE CHANGES" in controls
    assert "NO CRA CHANGES" in controls
    assert "NO TRADE EXECUTION" in controls

    # Ordered action contract
    ordered = list(plan.get("ordered_actions") or [])
    assert [row.get("code") for row in ordered] == [
        "FIRST_DECISION",
        "CASH_ACTION_IF_HARD_ASSET_FIRST",
        "EQUITY_FALLBACK_IF_WAIVED_OR_SPLIT",
        "SELL_TRIM_REVIEW_IF_RAISING_CAPITAL",
        "CONFLICT_REVIEW",
    ]

    # Hard-asset plan and queue-preserving fallback
    hard_plan = list(plan.get("hard_asset_buy_plan") or [])
    assert [row.get("node_key") for row in hard_plan] == [
        "COMMODITIES.GOLD",
        "COMMODITIES.ENERGY",
        "COMMODITIES.BROAD_BASKET",
    ]
    assert all(float(row.get("deployable_cash_only_amount") or 0.0) >= 0.0 for row in hard_plan)
    assert all(float(row.get("full_target_amount") or 0.0) > 0.0 for row in hard_plan)

    seeded_queue = json.loads(before).get("queue", [])
    queue_symbols = [row.get("symbol") for row in seeded_queue]
    fallback_symbols = [row.get("symbol") for row in (plan.get("equity_buy_fallback") or [])]
    assert fallback_symbols == queue_symbols[: len(fallback_symbols)]
    if any(float(row.get("suggested_amount") or 0.0) > 0.0 for row in seeded_queue):
        assert any(float(row.get("suggested_amount") or 0.0) > 0.0 for row in (plan.get("equity_buy_fallback") or []))

    # Conflict / blocked path coverage
    sell_trim_symbols = [row.get("symbol") for row in (plan.get("sell_trim_review") or [])]
    blocked_symbols = [row.get("symbol") for row in (plan.get("blocked_actions") or [])]
    assert "KGC" in sell_trim_symbols
    assert "PRIM" in sell_trim_symbols
    assert "TSLA" in blocked_symbols

    ordered = list(plan.get("ordered_actions") or [])
    raising_capital = next((row for row in ordered if row.get("code") == "SELL_TRIM_REVIEW_IF_RAISING_CAPITAL"), {})
    raising_details = " ".join(str(x) for x in (raising_capital.get("details") or []))
    assert "KGC" in raising_details
    assert "PRIM" in raising_details

    kgc_conflict = plan.get("kgc_conflict") or {}
    assert kgc_conflict.get("gold_adjacent_proxy") is True
    assert kgc_conflict.get("direct_gold_sleeve_filler") is False
    assert kgc_conflict.get("thesis_trim_candidate") is True

    # No mutation of queue artifact
    assert before == after
