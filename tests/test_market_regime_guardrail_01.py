from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.portfolio.regime.market_regime_contract import validate_guardrail_payload
from src.portfolio.regime.market_regime_guardrail import (
    build_market_regime_guardrail_from_rotation_summary,
    market_regime_guardrail_latest,
)


def _base_rotation_summary() -> dict:
    return {
        "status": "OK",
        "signal": "WATCHLIST_ROTATION",
        "risk_score": 42,
        "as_of_date": "2026-06-25",
        "confirmation": {"confirmation_passed": False},
        "proxy_returns": {
            "latest_proxy_date": "2026-06-24",
            "tech_returns": {"5d": -2.2, "20d": -4.1, "60d": 1.0},
            "rotation_spread_pct": {"5d": 1.4, "20d": 2.2, "60d": 0.8},
        },
        "portfolio_exposure": {"tech_pct": 34.0},
        "data_quality": {"missing_inputs": []},
    }


def test_market_regime_guardrail_unknown_when_data_unavailable() -> None:
    payload = build_market_regime_guardrail_from_rotation_summary(
        {
            "status": "DATA_UNAVAILABLE",
            "signal": "DATA_UNAVAILABLE",
            "as_of_date": "2026-06-25",
            "data_quality": {"signal_snapshot_date": "2026-06-24", "missing_inputs": ["replay_inputs.csv"]},
            "proxy_returns": {"latest_proxy_date": "2026-06-24"},
        }
    )

    assert payload["regime"] == "UNKNOWN"
    assert payload["deployment_posture"] == "CAUTION_DEPLOY"
    assert payload["scoring_impact"] == "none"
    assert payload["safe_to_deploy"] is False


def test_market_regime_guardrail_maps_semi_ai_pullback() -> None:
    summary = _base_rotation_summary()
    summary["market_proxies"] = {
        "soxx_vs_spy": -1.2,
        "qqq_vs_spy": -0.6,
        "soxx_drawdown_pct": -6.1,
        "soxx_below_20d": True,
        "soxx_below_50d": True,
    }

    payload = build_market_regime_guardrail_from_rotation_summary(summary)

    assert payload["regime"] == "SEMI_AI_PULLBACK"
    assert payload["severity"] == "MODERATE"
    assert payload["deployment_posture"] == "PAUSE_NEW_BUYS"
    assert payload["trim_posture"] == "TRIM_WEAK_SIGNALS_ONLY"
    assert payload["cash_posture"] == "HOLD_EXCESS"
    assert payload["scoring_impact"] == "none"
    assert payload["data_freshness"]["freshness_status"] == "FRESH"
    assert payload["data_freshness"]["proxy_lag_days"] == 1
    assert validate_guardrail_payload(payload) == []


def test_market_regime_guardrail_unknown_when_market_proxy_stale() -> None:
    summary = _base_rotation_summary()
    summary["as_of_date"] = "2026-07-10"
    summary["proxy_returns"] = {
        "latest_proxy_date": "2026-05-14",
        "tech_returns": {"5d": 3.0, "20d": 5.0, "60d": 8.0},
        "rotation_spread_pct": {"5d": -0.2, "20d": -0.5, "60d": -1.1},
    }

    payload = build_market_regime_guardrail_from_rotation_summary(summary)

    assert payload["regime"] == "UNKNOWN"
    assert payload["safe_to_deploy"] is False
    assert payload["data_freshness"]["freshness_status"] == "STALE"
    assert payload["data_freshness"]["operator_action"] == "REFRESH_MARKET_PROXIES"
    assert payload["data_freshness"]["market_proxy_age_days"] == 57
    assert "proxy date 2026-05-14 is 57 day(s) behind portfolio date 2026-07-10" in payload["evidence"][0]
    assert validate_guardrail_payload(payload) == []


def test_market_regime_guardrail_unknown_when_proxy_timestamp_missing() -> None:
    summary = _base_rotation_summary()
    summary["proxy_returns"] = {
        "latest_proxy_date": None,
        "tech_returns": {"5d": 3.0, "20d": 5.0, "60d": 8.0},
        "rotation_spread_pct": {"5d": -0.2, "20d": -0.5, "60d": -1.1},
    }

    payload = build_market_regime_guardrail_from_rotation_summary(summary)

    assert payload["regime"] == "UNKNOWN"
    assert payload["data_freshness"]["freshness_status"] == "MISSING"
    assert payload["data_freshness"]["operator_action"] == "REFRESH_MARKET_PROXIES"
    assert validate_guardrail_payload(payload) == []


def test_market_regime_guardrail_latest_is_fail_closed_unknown() -> None:
    with patch("src.portfolio.regime.market_regime_guardrail.rotation_risk_summary", side_effect=RuntimeError("boom")):
        payload = market_regime_guardrail_latest(Path("."))

    assert payload["regime"] == "UNKNOWN"
    assert payload["confidence"] == "LOW"
    assert payload["scoring_impact"] == "none"
