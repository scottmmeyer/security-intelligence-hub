from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from src.portfolio.regime.market_regime_guardrail import build_market_regime_guardrail_from_rotation_summary
from src.portfolio.regime.market_regime_inputs import evaluate_market_proxy_freshness


_NY = ZoneInfo("America/New_York")
_MARKET_CLOSE = time(16, 0)

# Contract fixture for this acceptance pass only.
# Repository currently has no shared U.S. trading-session calendar utility.
_US_MARKET_HOLIDAYS_2026 = {
    date(2026, 11, 26),  # Thanksgiving (NYSE/Nasdaq closed)
}


def _ny_dt(y: int, m: int, d: int, hh: int, mm: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=_NY)


def _is_session_day(d: date) -> bool:
    return d.weekday() < 5 and d not in _US_MARKET_HOLIDAYS_2026


def _previous_session_day(d: date) -> date:
    cur = d - timedelta(days=1)
    while not _is_session_day(cur):
        cur -= timedelta(days=1)
    return cur


def _latest_completed_session(evaluation_time: datetime) -> date:
    local = evaluation_time.astimezone(_NY)
    d = local.date()
    t = local.time()

    if _is_session_day(d) and t >= _MARKET_CLOSE:
        return d

    if _is_session_day(d):
        return _previous_session_day(d)

    cur = d
    while not _is_session_day(cur):
        cur -= timedelta(days=1)
    return cur


def _trading_session_lag(proxy_session: date, expected_session: date) -> int:
    if proxy_session > expected_session:
        return -1

    lag = 0
    cur = proxy_session + timedelta(days=1)
    while cur <= expected_session:
        if _is_session_day(cur):
            lag += 1
        cur += timedelta(days=1)
    return lag


def _freshness_from_contract_lag(lag: int) -> str:
    if lag <= 1:
        return "FRESH"
    if lag == 2:
        return "DEGRADED"
    return "STALE"


_CASES = [
    {
        "name": "case_1_fri_after_close",
        "evaluation": _ny_dt(2026, 10, 2, 16, 30),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 2),
        "expected_trading_lag": 0,
        "expected_missed": False,
        "expected_freshness": "FRESH",
        "expected_calendar_lag_days": 0,
    },
    {
        "name": "case_2_sat",
        "evaluation": _ny_dt(2026, 10, 3, 12, 0),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 2),
        "expected_trading_lag": 0,
        "expected_missed": False,
        "expected_freshness": "FRESH",
        "expected_calendar_lag_days": 1,
    },
    {
        "name": "case_3_sun",
        "evaluation": _ny_dt(2026, 10, 4, 12, 0),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 2),
        "expected_trading_lag": 0,
        "expected_missed": False,
        "expected_freshness": "FRESH",
        "expected_calendar_lag_days": 2,
    },
    {
        "name": "case_4_mon_before_close",
        "evaluation": _ny_dt(2026, 10, 5, 10, 0),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 2),
        "expected_trading_lag": 0,
        "expected_missed": False,
        "expected_freshness": "FRESH",
        "expected_calendar_lag_days": 3,
    },
    {
        "name": "case_5_mon_after_close",
        "evaluation": _ny_dt(2026, 10, 5, 16, 30),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 5),
        "expected_trading_lag": 1,
        "expected_missed": True,
        "expected_freshness": "FRESH",
        "expected_calendar_lag_days": 3,
    },
    {
        "name": "case_6_tue_before_close",
        "evaluation": _ny_dt(2026, 10, 6, 10, 0),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 5),
        "expected_trading_lag": 1,
        "expected_missed": True,
        "expected_freshness": "FRESH",
        "expected_calendar_lag_days": 4,
    },
    {
        "name": "case_7_tue_after_close",
        "evaluation": _ny_dt(2026, 10, 6, 16, 30),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 6),
        "expected_trading_lag": 2,
        "expected_missed": True,
        "expected_freshness": "DEGRADED",
        "expected_calendar_lag_days": 4,
    },
    {
        "name": "case_8_wed_after_close",
        "evaluation": _ny_dt(2026, 10, 7, 16, 30),
        "proxy_session": date(2026, 10, 2),
        "expected_session": date(2026, 10, 7),
        "expected_trading_lag": 3,
        "expected_missed": True,
        "expected_freshness": "STALE",
        "expected_calendar_lag_days": 5,
    },
]


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_trading_session_acceptance_matrix(case: dict) -> None:
    expected_session = _latest_completed_session(case["evaluation"])
    expected_lag = _trading_session_lag(case["proxy_session"], expected_session)
    expected_missed = expected_lag >= 1

    assert expected_session == case["expected_session"]
    assert expected_lag == case["expected_trading_lag"]
    assert expected_missed == case["expected_missed"]
    assert _freshness_from_contract_lag(expected_lag) == case["expected_freshness"]

    # Current implementation behavior (calendar-day lag) captured side-by-side.
    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts=case["proxy_session"].isoformat(),
        portfolio_snapshot_ts=case["evaluation"].isoformat(),
    )

    assert freshness["market_proxy_age_days"] == case["expected_calendar_lag_days"]
    assert freshness["freshness_status"] == case["expected_freshness"]


def test_holiday_does_not_count_as_session() -> None:
    pre_holiday_proxy = date(2026, 11, 25)  # Wednesday close
    holiday_eval = _ny_dt(2026, 11, 26, 12, 0)  # Thanksgiving holiday
    next_day_before_close = _ny_dt(2026, 11, 27, 10, 0)  # Friday before close

    holiday_expected_session = _latest_completed_session(holiday_eval)
    friday_am_expected_session = _latest_completed_session(next_day_before_close)

    assert holiday_expected_session == date(2026, 11, 25)
    assert friday_am_expected_session == date(2026, 11, 25)
    assert _trading_session_lag(pre_holiday_proxy, holiday_expected_session) == 0
    assert _trading_session_lag(pre_holiday_proxy, friday_am_expected_session) == 0


@pytest.mark.parametrize(
    "evaluation,proxy_session,expected_lag,expected_missed,expected_freshness",
    [
        (_ny_dt(2026, 10, 5, 16, 30), date(2026, 10, 5), 0, False, "FRESH"),
        (_ny_dt(2026, 10, 6, 16, 30), date(2026, 10, 5), 1, True, "FRESH"),
    ],
    ids=["proxy_advances_same_day", "proxy_advances_then_next_close"],
)
def test_proxy_advancement_contract(
    evaluation: datetime,
    proxy_session: date,
    expected_lag: int,
    expected_missed: bool,
    expected_freshness: str,
) -> None:
    expected_session = _latest_completed_session(evaluation)
    lag = _trading_session_lag(proxy_session, expected_session)

    assert lag == expected_lag
    assert (lag >= 1) == expected_missed
    assert _freshness_from_contract_lag(lag) == expected_freshness

    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts=proxy_session.isoformat(),
        portfolio_snapshot_ts=evaluation.isoformat(),
    )
    assert freshness["freshness_status"] == expected_freshness


@pytest.mark.parametrize(
    "market_ts,snapshot_ts,expected_status",
    [
        ("2026-10-08", "2026-10-07T16:30:00-04:00", "UNKNOWN"),
        ("10/02/2026", "2026-10-07", "UNKNOWN"),
        (None, "2026-10-07", "MISSING"),
        ("2026-10-02", None, "PARTIAL"),
    ],
    ids=["future_proxy_fail_closed", "unparseable_proxy", "missing_proxy", "missing_eval_context"],
)
def test_invalid_or_incomplete_inputs_fail_closed(
    market_ts: str | None,
    snapshot_ts: str | None,
    expected_status: str,
) -> None:
    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts=market_ts,
        portfolio_snapshot_ts=snapshot_ts,
    )
    assert freshness["freshness_status"] == expected_status


def test_calendar_vs_trading_session_provenance_distinction() -> None:
    proxy_session = date(2026, 10, 2)

    sunday_eval = _ny_dt(2026, 10, 4, 12, 0)
    sunday_expected_session = _latest_completed_session(sunday_eval)
    sunday_trading_lag = _trading_session_lag(proxy_session, sunday_expected_session)
    sunday_current = evaluate_market_proxy_freshness(
        market_proxies_ts=proxy_session.isoformat(),
        portfolio_snapshot_ts=sunday_eval.isoformat(),
    )

    assert sunday_current["market_proxy_age_days"] == 2
    assert sunday_trading_lag == 0

    monday_pm_eval = _ny_dt(2026, 10, 5, 16, 30)
    monday_pm_expected_session = _latest_completed_session(monday_pm_eval)
    monday_pm_trading_lag = _trading_session_lag(proxy_session, monday_pm_expected_session)
    monday_pm_current = evaluate_market_proxy_freshness(
        market_proxies_ts=proxy_session.isoformat(),
        portfolio_snapshot_ts=monday_pm_eval.isoformat(),
    )

    assert monday_pm_current["market_proxy_age_days"] == 3
    assert monday_pm_trading_lag == 1


def test_current_date_live_evaluation_uses_runtime_clock() -> None:
    with patch(
        "src.portfolio.regime.market_regime_inputs._utc_now",
        return_value=datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc),
    ):
        freshness = evaluate_market_proxy_freshness(
            market_proxies_ts="2026-10-02",
            portfolio_snapshot_ts="2026-10-05",
        )

    assert freshness["expected_session"] == "2026-10-02"
    assert freshness["trading_session_lag"] == 0
    assert freshness["missed_session"] is False
    assert freshness["freshness_status"] == "FRESH"
    assert freshness["freshness_evaluation_ts"] == "2026-10-05T12:30:00+00:00"


def test_historical_date_only_behavior_is_preserved() -> None:
    with patch(
        "src.portfolio.regime.market_regime_inputs._utc_now",
        return_value=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
    ):
        freshness = evaluate_market_proxy_freshness(
            market_proxies_ts="2026-09-03",
            portfolio_snapshot_ts="2026-09-04",
        )

    assert freshness["freshness_status"] == "FRESH"
    assert freshness["freshness_evaluation_source"] == "historical_snapshot_date"


def test_future_portfolio_snapshot_fails_closed() -> None:
    with patch(
        "src.portfolio.regime.market_regime_inputs._utc_now",
        return_value=datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc),
    ):
        freshness = evaluate_market_proxy_freshness(
            market_proxies_ts="2026-10-02",
            portfolio_snapshot_ts="2026-10-06",
        )

    assert freshness["freshness_status"] == "UNKNOWN"
    assert freshness["expected_session"] is None
    assert freshness["operator_action"] == "VALIDATE_PROXY_AND_SNAPSHOT_TIMESTAMPS"


def test_regime_classification_contract_unchanged_for_mixed_fresh_inputs() -> None:
    payload = build_market_regime_guardrail_from_rotation_summary(
        {
            "status": "OK",
            "signal": "NO_CLEAR_SIGNAL",
            "risk_score": 18,
            "as_of_date": "2026-10-05",
            "freshness_evaluation_ts": "2026-10-05T12:30:00+00:00",
            "confirmation": {"confirmation_passed": False},
            "proxy_returns": {
                "latest_proxy_date": "2026-10-02",
                "tech_returns": {"5d": 0.1, "20d": -0.1, "60d": 0.0},
                "rotation_spread_pct": {"5d": 0.1, "20d": 0.1, "60d": -0.1},
            },
            "portfolio_exposure": {"tech_pct": 31.0},
            "data_quality": {"missing_inputs": []},
        }
    )

    assert payload["regime"] == "UNKNOWN"
    assert payload["data_freshness"]["freshness_status"] == "FRESH"
