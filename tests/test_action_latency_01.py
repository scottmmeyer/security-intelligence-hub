from __future__ import annotations

from src.portfolio.action_latency import ActionLatencyInput, evaluate_action_latency_state


def test_prim_like_case_escalates_to_missed_action_review() -> None:
    out = evaluate_action_latency_state(
        ActionLatencyInput(
            symbol="PRIM",
            snapshot_date="2026-06-24",
            active_reduction_intent=True,
            conviction_protected=False,
            first_trim_signal_date="2026-06-10",
            last_action_status="IGNORED",
            acted_after_signal=False,
            return_1d=-21.59,
            return_5d=-16.17,
            return_1m=-34.33,
            action_window_days=7,
        )
    )
    assert out["status"] == "MISSED_ACTION_REVIEW"
    assert out["adverse_move_triggered"] is True
    assert len(out["adverse_move_triggers"]) >= 2


def test_mu_like_case_not_escalated_when_not_trim_candidate() -> None:
    out = evaluate_action_latency_state(
        ActionLatencyInput(
            symbol="MU",
            snapshot_date="2026-06-24",
            active_reduction_intent=False,
            conviction_protected=True,
            first_trim_signal_date=None,
            last_action_status="",
            acted_after_signal=False,
            return_1d=-9.10,
            return_5d=-8.40,
            return_1m=-12.20,
            action_window_days=7,
        )
    )
    assert out["status"] == "NONE"


def test_fresh_trim_signal_is_action_due_not_missed() -> None:
    out = evaluate_action_latency_state(
        ActionLatencyInput(
            symbol="ABC",
            snapshot_date="2026-06-24",
            active_reduction_intent=True,
            conviction_protected=False,
            first_trim_signal_date="2026-06-23",
            last_action_status="IGNORED",
            acted_after_signal=False,
            return_1d=-1.2,
            return_5d=-2.4,
            return_1m=-3.3,
            action_window_days=7,
        )
    )
    assert out["status"] == "ACTION_DUE"


def test_stale_trim_without_large_drawdown_is_aging() -> None:
    out = evaluate_action_latency_state(
        ActionLatencyInput(
            symbol="XYZ",
            snapshot_date="2026-06-24",
            active_reduction_intent=True,
            conviction_protected=False,
            first_trim_signal_date="2026-06-10",
            last_action_status="IGNORED",
            acted_after_signal=False,
            return_1d=-1.0,
            return_5d=-2.0,
            return_1m=-4.0,
            action_window_days=7,
        )
    )
    assert out["status"] == "TRIM_SIGNAL_AGING"


def test_fully_acted_recommendation_suppresses_escalation() -> None:
    out = evaluate_action_latency_state(
        ActionLatencyInput(
            symbol="DEF",
            snapshot_date="2026-06-24",
            active_reduction_intent=True,
            conviction_protected=False,
            first_trim_signal_date="2026-06-12",
            last_action_status="FOLLOWED",
            acted_after_signal=True,
            return_1d=-18.0,
            return_5d=-20.0,
            return_1m=-25.0,
            action_window_days=7,
        )
    )
    assert out["status"] == "NONE"
    assert "already observed" in out["message"].lower()


def test_partial_follow_through_surfaces_partial_review_state() -> None:
    out = evaluate_action_latency_state(
        ActionLatencyInput(
            symbol="PRIM",
            snapshot_date="2026-06-24",
            active_reduction_intent=True,
            conviction_protected=False,
            first_trim_signal_date="2026-06-10",
            last_action_status="PARTIALLY_FOLLOWED",
            acted_after_signal=False,
            return_1d=-12.0,
            return_5d=-10.5,
            return_1m=-21.0,
            action_window_days=7,
        )
    )
    assert out["status"] == "PARTIAL_ACTION_REVIEW"
    assert "partial trim action" in out["message"].lower()
