from __future__ import annotations

from unittest.mock import patch

from scripts import refresh_signals as refresh


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
