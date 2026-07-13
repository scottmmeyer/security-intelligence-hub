from __future__ import annotations

from datetime import date, datetime, timezone

from src.portfolio.regime.market_regime_guardrail import build_market_regime_guardrail_from_rotation_summary
from src.portfolio.regime.market_regime_inputs import evaluate_market_proxy_freshness


def test_market_regime_parses_date_only_proxy_timestamp() -> None:
    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts="2026-05-14",
        portfolio_snapshot_ts="2026-07-13",
    )

    assert freshness["freshness_status"] == "STALE"
    assert isinstance(freshness["market_proxy_age_days"], int)


def test_market_regime_parses_datetime_proxy_timestamp() -> None:
    freshness_utc_z = evaluate_market_proxy_freshness(
        market_proxies_ts="2026-05-14T00:00:00Z",
        portfolio_snapshot_ts="2026-07-13T00:00:00+00:00",
    )
    freshness_utc_offset = evaluate_market_proxy_freshness(
        market_proxies_ts="2026-05-14T14:55:00+00:00",
        portfolio_snapshot_ts=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
    )

    assert freshness_utc_z["freshness_status"] == "STALE"
    assert freshness_utc_offset["freshness_status"] == "STALE"
    assert freshness_utc_z["market_proxy_age_days"] == 60


def test_market_regime_stale_timestamp_gets_numeric_lag() -> None:
    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts=date(2026, 5, 14),
        portfolio_snapshot_ts=date(2026, 7, 13),
    )

    assert freshness["freshness_status"] == "STALE"
    assert freshness["market_proxy_age_days"] == 60
    assert freshness["operator_action"] == "REFRESH_MARKET_PROXIES"


def test_market_regime_unparseable_timestamp_returns_unknown_and_verify_action() -> None:
    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts="05/14/26",
        portfolio_snapshot_ts="2026-07-13",
    )

    assert freshness["freshness_status"] == "UNKNOWN"
    assert freshness["market_proxy_age_days"] is None
    assert freshness["operator_action"] == "VERIFY_TIMESTAMP_FORMATS"
    assert "05/14/26" in " ".join(freshness.get("warnings") or [])


def test_market_regime_missing_timestamp_returns_missing() -> None:
    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts=None,
        portfolio_snapshot_ts="2026-07-13",
    )

    assert freshness["freshness_status"] == "MISSING"
    assert freshness["operator_action"] == "REFRESH_MARKET_PROXIES"


def test_market_regime_scoring_impact_always_none() -> None:
    payload = build_market_regime_guardrail_from_rotation_summary(
        {
            "status": "OK",
            "signal": "WATCHLIST_ROTATION",
            "risk_score": 42,
            "as_of_date": "2026-07-13",
            "confirmation": {"confirmation_passed": False},
            "proxy_returns": {
                "latest_proxy_date": "2026-05-14",
                "tech_returns": {"5d": 3.0, "20d": 5.0, "60d": 8.0},
                "rotation_spread_pct": {"5d": -0.2, "20d": -0.5, "60d": -1.1},
            },
            "portfolio_exposure": {"tech_pct": 34.0},
            "data_quality": {"missing_inputs": []},
        }
    )

    assert payload["scoring_impact"] == "none"
