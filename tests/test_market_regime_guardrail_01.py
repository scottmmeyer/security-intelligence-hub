from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.portfolio.regime.market_regime_contract import validate_guardrail_payload
from src.portfolio.regime.market_regime_guardrail import (
    build_market_regime_guardrail_from_rotation_summary,
    market_regime_guardrail_latest,
)


_REAL_REPO_ROOT = Path("/Users/scottmmeyer/Projects/security-intelligence-hub").resolve()
_REAL_CURRENT_ROOT = (_REAL_REPO_ROOT / "data" / "current").resolve()
_DEDICATED_FILES = (
    "market_regime_proxy_summary.json",
    "market_regime_proxy_inputs.csv",
    "market_regime_proxy_price_history.csv",
)
_REPLAY_FILES = ("replay_inputs.csv", "replay_performance_series.csv")


def _optional_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _current_hashes() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for name in (*_DEDICATED_FILES, *_REPLAY_FILES):
        out[name] = _optional_sha256(_REAL_CURRENT_ROOT / name)
    return out


@pytest.fixture(scope="module", autouse=True)
def _protect_real_current_artifacts() -> None:
    before = _current_hashes()
    yield
    after = _current_hashes()
    assert after == before, (
        "Guardrail test isolation violation: live data/current artifacts changed. "
        f"before={before} after={after}"
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
    assert "unavailable or stale" in payload["operator_summary"].lower()


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
    assert "unavailable or stale" in payload["operator_summary"].lower()
    assert validate_guardrail_payload(payload) == []


def test_market_regime_guardrail_fresh_unknown_does_not_claim_stale_inputs() -> None:
    summary = {
        "status": "OK",
        "signal": "NO_CLEAR_SIGNAL",
        "risk_score": 18,
        "as_of_date": "2026-07-10",
        "confirmation": {"confirmation_passed": False},
        "proxy_returns": {
            "latest_proxy_date": "2026-07-09",
            "tech_returns": {"5d": 0.1, "20d": -0.1, "60d": 0.0},
            "rotation_spread_pct": {"5d": 0.1, "20d": 0.1, "60d": -0.1},
        },
        "portfolio_exposure": {"tech_pct": 31.0},
        "data_quality": {"missing_inputs": []},
    }

    payload = build_market_regime_guardrail_from_rotation_summary(summary)

    assert payload["regime"] == "UNKNOWN"
    assert payload["data_freshness"]["freshness_status"] == "FRESH"
    assert payload["data_freshness"]["operator_action"] == "NONE"
    assert "unavailable or stale" not in payload["operator_summary"].lower()
    assert "unavailable or stale" not in payload["evidence"][0].lower()
    assert "inconclusive" in payload["operator_summary"].lower()
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


def test_market_regime_guardrail_latest_is_fail_closed_unknown(tmp_path: Path) -> None:
    repo_root = tmp_path
    resolved = repo_root.resolve()
    assert resolved != _REAL_CURRENT_ROOT
    assert _REAL_CURRENT_ROOT not in resolved.parents

    with (
        patch(
            "src.portfolio.regime.market_regime_guardrail.load_market_regime_rotation_summary",
            return_value=(None, "legacy_replay_fallback", []),
        ),
        patch("src.portfolio.regime.market_regime_guardrail.rotation_risk_summary", side_effect=RuntimeError("boom")),
    ):
        payload = market_regime_guardrail_latest(repo_root)

    assert payload["regime"] == "UNKNOWN"
    assert payload["confidence"] == "LOW"
    assert payload["scoring_impact"] == "none"
    assert payload["input_source"] == "legacy_replay_fallback"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _rotation_summary_fixture(proxy_date: str, as_of_date: str) -> dict:
    return {
        "status": "OK",
        "diagnostic_id": "ROTATION-RISK-01",
        "diagnostic_name": "Tech-to-hard-assets rotation monitor",
        "as_of_date": as_of_date,
        "run_id": "PAR-20260827-TEST",
        "signal": "NO_CLEAR_SIGNAL",
        "headline": "fixture",
        "risk_score": 10,
        "portfolio_exposure": {"tech_pct": 25.0},
        "proxy_returns": {
            "selected_cap_bucket": "DEDICATED_PROXY",
            "latest_proxy_date": proxy_date,
            "tech_returns": {"5d": 0.1, "20d": 0.1, "60d": 0.1},
            "hard_assets_returns": {"5d": 0.1, "20d": 0.1, "60d": 0.1},
            "rotation_spread_pct": {"5d": 0.0, "20d": 0.0, "60d": 0.0},
            "hard_asset_industry_caps": {
                "ENERGY": "DEDICATED_PROXY",
                "BASIC MATERIALS": "DEDICATED_PROXY",
                "INDUSTRIALS": "DEDICATED_PROXY",
            },
        },
        "confirmation": {"confirmation_passed": False},
        "data_quality": {"missing_inputs": []},
        "provenance": {
            "provider": "YAHOO_FINANCE",
            "generated_at_utc": "2026-09-01T00:00:00+00:00",
            "input_source": "dedicated_market_regime_price_history",
        },
    }


def _write_dedicated_summary(repo_root: Path, rotation_summary: dict) -> None:
    payload = {
        "status": "completed",
        "source": "dedicated_market_regime_proxy_artifact",
        "generated_at_utc": "2026-09-01T00:00:00+00:00",
        "latest_proxy_date": str((rotation_summary.get("proxy_returns") or {}).get("latest_proxy_date") or ""),
        "required_inputs": [],
        "missing_inputs": [],
        "technology_proxy": {"5d": 0.1, "20d": 0.1, "60d": 0.1},
        "hard_asset_proxy": {"5d": 0.1, "20d": 0.1, "60d": 0.1},
        "freshness": {
            "status": "FRESH",
            "portfolio_date": str(rotation_summary.get("as_of_date") or ""),
            "proxy_date": str((rotation_summary.get("proxy_returns") or {}).get("latest_proxy_date") or ""),
            "lag_days": 0,
            "threshold_days": 2,
        },
        "provenance": {
            "provider": "YAHOO_FINANCE",
            "transaction_id": "MRG-DEDICATED-test",
            "input_source": "dedicated_market_regime_price_history",
            "proxy_symbol_map": {},
        },
        "warnings": [],
        "rotation_summary": rotation_summary,
        "input_source": "dedicated_market_regime_price_history",
        "transaction_id": "MRG-DEDICATED-test",
    }
    _write_json(repo_root / "data" / "current" / "market_regime_proxy_summary.json", payload)


def _write_manifest(repo_root: Path, runs: list[dict[str, str]]) -> None:
    _write_json(repo_root / "data" / "portfolio_ingestion" / "manifest.json", {"portfolios": runs})


def _write_run_metadata(repo_root: Path, run_id: str, snapshot_date: str) -> None:
    _write_json(
        repo_root / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "run_metadata.json",
        {"run_id": run_id, "snapshot_date": snapshot_date, "status": "COMPLETE"},
    )


def test_stale_proxy_not_labeled_fresh_for_current_par_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir)
        current_run = "PAR-20260901-E6CE9722"
        _write_manifest(
            repo_root,
            [
                {"run_id": "PAR-20260827-OLD", "snapshot_date": "2026-08-27", "status": "COMPLETE"},
                {"run_id": current_run, "snapshot_date": "2026-09-01", "status": "COMPLETE"},
            ],
        )
        _write_run_metadata(repo_root, current_run, "2026-09-01")
        _write_dedicated_summary(
            repo_root,
            _rotation_summary_fixture(proxy_date="2026-08-25", as_of_date="2026-08-27"),
        )

        payload = market_regime_guardrail_latest(repo_root, run_id=current_run)

        assert payload["data_freshness"]["portfolio_snapshot_ts"] == "2026-09-01"
        assert payload["data_freshness"]["freshness_status"] == "STALE"


def test_current_proxy_within_threshold_remains_fresh() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir)
        current_run = "PAR-20260901-E6CE9722"
        _write_manifest(
            repo_root,
            [{"run_id": current_run, "snapshot_date": "2026-09-01", "status": "COMPLETE"}],
        )
        _write_run_metadata(repo_root, current_run, "2026-09-01")
        _write_dedicated_summary(
            repo_root,
            _rotation_summary_fixture(proxy_date="2026-08-31", as_of_date="2026-08-27"),
        )

        payload = market_regime_guardrail_latest(repo_root, run_id=current_run)

        assert payload["data_freshness"]["portfolio_snapshot_ts"] == "2026-09-01"
        assert payload["data_freshness"]["freshness_status"] == "FRESH"
        assert payload["data_freshness"]["freshness_threshold_days"] == 2


def test_historical_guardrail_binding_uses_historical_run_date_no_lookahead() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir)
        historical_run = "PAR-20260827-OLD"
        current_run = "PAR-20260901-E6CE9722"
        _write_manifest(
            repo_root,
            [
                {"run_id": historical_run, "snapshot_date": "2026-08-27", "status": "COMPLETE"},
                {"run_id": current_run, "snapshot_date": "2026-09-01", "status": "COMPLETE"},
            ],
        )
        _write_run_metadata(repo_root, historical_run, "2026-08-27")
        _write_run_metadata(repo_root, current_run, "2026-09-01")
        _write_dedicated_summary(
            repo_root,
            _rotation_summary_fixture(proxy_date="2026-08-25", as_of_date="2026-08-27"),
        )

        historical_payload = market_regime_guardrail_latest(repo_root, run_id=historical_run)
        current_payload = market_regime_guardrail_latest(repo_root, run_id=current_run)

        assert historical_payload["data_freshness"]["portfolio_snapshot_ts"] == "2026-08-27"
        assert historical_payload["data_freshness"]["freshness_status"] == "FRESH"
        assert current_payload["data_freshness"]["portfolio_snapshot_ts"] == "2026-09-01"
        assert current_payload["data_freshness"]["freshness_status"] == "STALE"
