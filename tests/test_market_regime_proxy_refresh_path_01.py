from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import refresh_signals as refresh


_REAL_REPO_ROOT = Path("/Users/scottmmeyer/Projects/security-intelligence-hub").resolve()
_REAL_CURRENT_ROOT = (_REAL_REPO_ROOT / "data" / "current").resolve()


def _z(**kwargs):
    return False, {}


def _d(**kwargs):
    return False, {}


def _y(**kwargs):
    return False, {}


_GUARDED_FILES = (
    "replay_inputs.csv",
    "replay_performance_series.csv",
    "market_regime_proxy_summary.json",
    "market_regime_proxy_inputs.csv",
    "market_regime_proxy_price_history.csv",
)


def _optional_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _guarded_hashes() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for name in _GUARDED_FILES:
        out[name] = _optional_sha256(_REAL_CURRENT_ROOT / name)
    return out


@pytest.fixture(scope="module", autouse=True)
def _protect_real_current_artifacts() -> None:
    before = _guarded_hashes()
    yield
    after = _guarded_hashes()
    assert after == before, (
        "Refresh-path test isolation violation: live data/current artifacts changed. "
        f"before={before} after={after}"
    )


@patch("scripts.refresh_signals._load_portfolio_equity_holdings", return_value={"AAPL", "MSFT"})
@patch("scripts.refresh_signals._load_buy_candidate_symbols", return_value=["NVDA"])
@patch("scripts.refresh_signals._load_portfolio_provider_holdings")
@patch("scripts.refresh_signals._all_universe_symbols", return_value=["AAPL", "MSFT", "NVDA", "SPY"]) 
def test_holdings_plus_buy_candidates_scope_includes_market_proxies(
    _mock_universe,
    mock_provider_holdings,
    _mock_buy,
    _mock_holdings,
) -> None:
    mock_provider_holdings.return_value = {"AAPL", "MSFT"}
    with patch("scripts.refresh_signals._market_proxy_symbols", return_value=["SPY", "QQQ", "XLK", "SOXX"]):
        scope = refresh._build_refresh_scope(refresh_mode="holdings_plus_buy_candidates")

    summary = scope["scope_summary"]
    assert summary["market_proxy_count"] == 4

    planned = scope["planned_symbols"]
    assert planned["market_proxies"] == ["SPY", "QQQ", "XLK", "SOXX"]
    for provider in ("zacks", "danelfin", "yahoo"):
        provider_symbols = planned["provider_symbols"][provider]
        for sym in ("SPY", "QQQ", "XLK", "SOXX"):
            assert sym in provider_symbols


@patch("scripts.refresh_signals._load_portfolio_equity_holdings", return_value={"AAPL"})
@patch("scripts.refresh_signals._load_portfolio_provider_holdings", return_value={"AAPL"})
@patch("scripts.refresh_signals._all_universe_symbols", return_value=["AAPL", "SPY"])
def test_portfolio_signals_scope_includes_market_proxies(
    _mock_universe,
    _mock_provider_holdings,
    _mock_holdings,
) -> None:
    with patch("scripts.refresh_signals._market_proxy_symbols", return_value=["SPY", "QQQ", "XLK", "SOXX"]):
        scope = refresh._build_refresh_scope(refresh_mode="portfolio_signals")

    planned = scope["planned_symbols"]
    for provider in ("zacks", "danelfin", "yahoo"):
        provider_symbols = planned["provider_symbols"][provider]
        for sym in ("SPY", "QQQ", "XLK", "SOXX"):
            assert sym in provider_symbols


@patch("scripts.refresh_signals._load_portfolio_equity_holdings", return_value={"AAPL"})
@patch("scripts.refresh_signals._load_portfolio_provider_holdings", return_value={"AAPL"})
@patch("scripts.refresh_signals._all_universe_symbols", return_value=["AAPL", "SPY"])
def test_stale_only_scope_includes_market_proxies_only_when_refresh_needed(
    _mock_universe,
    _mock_provider_holdings,
    _mock_holdings,
) -> None:
    with patch("scripts.refresh_signals._market_proxy_symbols", return_value=["SPY", "QQQ", "XLK", "SOXX"]), patch(
        "scripts.refresh_signals._market_proxy_refresh_needed", return_value=True
    ):
        scope_stale = refresh._build_refresh_scope(refresh_mode="stale_only")

    assert scope_stale["scope_summary"]["market_proxy_count"] == 4
    assert scope_stale["planned_symbols"]["market_proxies"] == ["SPY", "QQQ", "XLK", "SOXX"]

    with patch("scripts.refresh_signals._market_proxy_symbols", return_value=["SPY", "QQQ", "XLK", "SOXX"]), patch(
        "scripts.refresh_signals._market_proxy_refresh_needed", return_value=False
    ):
        scope_fresh = refresh._build_refresh_scope(refresh_mode="stale_only")

    assert scope_fresh["scope_summary"]["market_proxy_count"] == 0
    assert scope_fresh["planned_symbols"]["market_proxies"] == []


@patch("scripts.refresh_signals._load_portfolio_equity_holdings", return_value={"AAPL"})
@patch("scripts.refresh_signals._load_portfolio_provider_holdings", return_value={"AAPL"})
@patch("scripts.refresh_signals._all_universe_symbols", return_value=["AAPL", "SPY"])
def test_market_regime_proxy_only_scope_limits_to_proxy_symbols(
    _mock_universe,
    _mock_provider_holdings,
    _mock_holdings,
) -> None:
    with patch("scripts.refresh_signals._market_proxy_symbols", return_value=["SPY", "QQQ", "XLK", "XLE", "XLB", "XLI", "SOXX"]):
        scope = refresh._build_refresh_scope(refresh_mode="market_regime_proxy_only")

    planned = scope["planned_symbols"]
    assert planned["market_proxies"] == ["SPY", "QQQ", "XLK", "XLE", "XLB", "XLI", "SOXX"]
    for provider in ("zacks", "danelfin", "yahoo"):
        assert planned["provider_symbols"][provider] == ["SPY", "QQQ", "XLK", "XLE", "XLB", "XLI", "SOXX"]


def test_refresh_report_surfaces_dedicated_proxy_build_status(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_build_refresh_scope",
        lambda *, refresh_mode: {
            "scope_summary": {"market_proxy_count": 7},
            "planned_symbol_samples": {"market_proxies": ["SPY", "QQQ", "XLK", "XLE", "XLB", "XLI", "SOXX"]},
            "planned_symbols": {"provider_symbols": {"zacks": [], "danelfin": [], "yahoo": []}},
            "buy_candidate_cap": 50,
        },
    )
    monkeypatch.setattr(refresh, "_refresh_zacks", lambda **kwargs: (False, {"provider": "zacks", "state": "RESEARCH_FRESH_COMPLIANT"}))
    monkeypatch.setattr(refresh, "_refresh_danelfin", lambda **kwargs: (False, {"provider": "danelfin", "state": "RESEARCH_FRESH_COMPLIANT"}))
    monkeypatch.setattr(refresh, "_refresh_yahoo", lambda **kwargs: (False, {"provider": "yahoo", "state": "RESEARCH_FRESH_COMPLIANT"}))

    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.fetch_market_regime_proxy_history",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "published": True,
            "symbols": ["XLK", "XLE", "XLB", "XLI"],
            "observations_by_symbol": {"XLK": 70, "XLE": 70, "XLB": 70, "XLI": 70},
            "earliest_date": "2026-03-01",
            "latest_common_date": "2026-07-15",
            "missing_symbols": [],
            "insufficient_symbols": [],
            "warnings": [],
            "transaction_id": "MRG-HISTORY-test",
        },
    )

    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.build_market_regime_proxy_artifacts",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "reason": "completed",
            "published": True,
            "input_source": "dedicated_market_regime_price_history",
            "latest_proxy_date_before": "2026-07-14",
            "latest_proxy_date_after": "2026-07-15",
            "missing_inputs": [],
            "warnings": [],
            "transaction_id": "MRG-DEDICATED-test",
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks", "danelfin", "yahoo"),
        dry_run=False,
        verbose=False,
        refresh_mode="market_regime_proxy_only",
    )

    dedicated = report.get("market_regime_proxy_artifact_build") or {}
    assert dedicated.get("attempted") is True
    assert dedicated.get("status") == "completed"
    assert dedicated.get("published") is True
    assert dedicated.get("input_source") == "dedicated_market_regime_price_history"
    assert dedicated.get("latest_proxy_date_after") == "2026-07-15"


def test_market_regime_proxy_only_does_not_run_broad_provider_refresh(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_build_refresh_scope",
        lambda *, refresh_mode: {
            "scope_summary": {"market_proxy_count": 4},
            "planned_symbol_samples": {"market_proxies": ["XLK", "XLE", "XLB", "XLI"]},
            "planned_symbols": {"provider_symbols": {"zacks": [], "danelfin": [], "yahoo": []}},
            "buy_candidate_cap": 50,
        },
    )

    called = {"z": False, "d": False, "y": False}

    def _z(**kwargs):
        called["z"] = True
        return False, {}

    def _d(**kwargs):
        called["d"] = True
        return False, {}

    def _y(**kwargs):
        called["y"] = True
        return False, {}


def test_macro_liquidity_refresh_mode_invokes_materializer(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_run_macro_liquidity_refresh",
        lambda **kwargs: {
            "provider": "FRED",
            "overall_status": "completed",
            "series_requested": 14,
            "series_succeeded": 14,
            "series_failed": [],
            "series_latest_dates": {"DGS2": "2026-08-25"},
            "refresh_started_at": "2026-08-27T00:00:00Z",
            "refresh_completed_at": "2026-08-27T00:00:05Z",
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode="macro_liquidity_only",
    )

    macro = report.get("macro_liquidity") or {}
    assert macro.get("overall_status") == "completed"
    assert macro.get("provider") == "FRED"
    assert report.get("triggered", {}).get("macro_liquidity") is True


def test_macro_liquidity_refresh_failure_reports_failed_state(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_run_macro_liquidity_refresh",
        lambda **kwargs: {
            "provider": "FRED",
            "overall_status": "failed",
            "series_requested": 14,
            "series_succeeded": 9,
            "series_failed": ["DGS2"],
            "series_latest_dates": {"DGS2": "2026-08-21"},
            "error": "materializer returned partial failure",
            "refresh_started_at": "2026-08-27T00:00:00Z",
            "refresh_completed_at": "2026-08-27T00:00:05Z",
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode="macro_liquidity_only",
    )

    macro = report.get("macro_liquidity") or {}
    assert macro.get("overall_status") == "failed"
    assert macro.get("series_failed") == ["DGS2"]
    assert report.get("triggered", {}).get("macro_liquidity") is False

    called = {"z": False, "d": False, "y": False}

    def _z(**kwargs):
        called["z"] = True
        return False, {}

    def _d(**kwargs):
        called["d"] = True
        return False, {}

    def _y(**kwargs):
        called["y"] = True
        return False, {}

    monkeypatch.setattr(refresh, "_refresh_zacks", _z)
    monkeypatch.setattr(refresh, "_refresh_danelfin", _d)
    monkeypatch.setattr(refresh, "_refresh_yahoo", _y)
    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.fetch_market_regime_proxy_history",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "published": True,
            "symbols": ["XLK", "XLE", "XLB", "XLI"],
            "observations_by_symbol": {"XLK": 70, "XLE": 70, "XLB": 70, "XLI": 70},
            "earliest_date": "2026-03-01",
            "latest_common_date": "2026-07-15",
            "missing_symbols": [],
            "insufficient_symbols": [],
            "warnings": [],
            "transaction_id": "MRG-HISTORY-test",
        },
    )
    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.build_market_regime_proxy_artifacts",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "reason": "completed",
            "published": True,
            "input_source": "dedicated_market_regime_price_history",
            "latest_proxy_date_before": "2026-07-14",
            "latest_proxy_date_after": "2026-07-15",
            "missing_inputs": [],
            "warnings": [],
            "transaction_id": "MRG-DEDICATED-test",
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks", "danelfin", "yahoo"),
        dry_run=False,
        verbose=False,
        refresh_mode="market_regime_proxy_only",
    )

    assert called == {"z": False, "d": False, "y": False}
    assert (report.get("market_regime_proxy_history_fetch") or {}).get("published") is True
    assert (report.get("market_regime_proxy_artifact_build") or {}).get("published") is True
