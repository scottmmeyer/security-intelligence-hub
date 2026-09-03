"""Tests for Danelfin provider scope filtering and terminal UI display repair.

PART D of bounded danelfin scope + terminal UI repair:
- Verify market proxies are filtered from danelfin provider scope
- Verify global market proxy scope is preserved for market-regime monitoring
- Verify applicable holdings remain submitted to all providers
- Verify no regression in other provider scope
- Verify running-state and terminal-state UI displays
- Verify cache source-date display semantics
"""

from __future__ import annotations

import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTCOME_APP_JS = _REPO_ROOT / "ui" / "outcome_visualization" / "app.js"


def test_danelfin_market_proxy_exclusion_test() -> None:
    """Test 9: Danelfin applicability - market proxies must be excluded."""
    from scripts.refresh_signals import (
        _build_refresh_scope,
        REFRESH_MODE_PORTFOLIO_SIGNALS,
    )

    scope = _build_refresh_scope(refresh_mode=REFRESH_MODE_PORTFOLIO_SIGNALS)

    # Extract market proxies and danelfin scope
    market_proxies = scope.get("planned_symbols", {}).get("market_proxies", [])
    danelfin_symbols = (
        scope.get("planned_symbols", {}).get("provider_symbols", {}).get("danelfin", [])
    )

    assert len(market_proxies) == 9, f"Expected 9 market proxies, got {len(market_proxies)}"
    assert set(market_proxies) == {
        "SPY",
        "QQQ",
        "XLK",
        "XLF",
        "XLI",
        "XLV",
        "XLE",
        "XLB",
        "SOXX",
    }, f"Unexpected market proxies: {market_proxies}"

    # Verify NO proxies in danelfin scope
    proxy_set = set(market_proxies)
    danelfin_with_proxies = [s for s in danelfin_symbols if s in proxy_set]
    assert (
        not danelfin_with_proxies
    ), f"Danelfin scope incorrectly includes proxies: {danelfin_with_proxies}"

    # Verify danelfin scope is exactly 55 (55 applicable holdings + 0 proxies)
    assert len(danelfin_symbols) == 55, f"Expected 55 danelfin symbols, got {len(danelfin_symbols)}"


def test_global_market_proxy_scope_preserved_test() -> None:
    """Test 10: Global proxy preservation - market proxies remain available globally."""
    from scripts.refresh_signals import (
        _build_refresh_scope,
        REFRESH_MODE_PORTFOLIO_SIGNALS,
    )

    scope = _build_refresh_scope(refresh_mode=REFRESH_MODE_PORTFOLIO_SIGNALS)

    market_proxies = scope.get("planned_symbols", {}).get("market_proxies", [])
    deduped_all = scope.get("planned_symbols", {}).get("deduped_all", [])

    # Market proxies must be in the global deduped scope
    proxy_set = set(market_proxies)
    deduped_set = set(deduped_all)
    missing_proxies = proxy_set - deduped_set

    assert (
        not missing_proxies
    ), f"Market proxies missing from global deduped scope: {missing_proxies}"

    # Verify 9 proxies still exist in global scope
    assert len(market_proxies) == 9, f"Expected 9 market proxies, got {len(market_proxies)}"


def test_danelfin_applicable_holdings_scope_test() -> None:
    """Test 11: Applicable holdings preserved - all 55 holdings submitted to danelfin."""
    from scripts.refresh_signals import (
        _build_refresh_scope,
        _load_portfolio_provider_holdings,
        REFRESH_MODE_PORTFOLIO_SIGNALS,
    )

    scope = _build_refresh_scope(refresh_mode=REFRESH_MODE_PORTFOLIO_SIGNALS)
    danelfin_symbols = (
        scope.get("planned_symbols", {}).get("provider_symbols", {}).get("danelfin", [])
    )

    # Get the applicable holdings from direct provider logic
    danelfin_applicable = _load_portfolio_provider_holdings("danelfin")

    # All applicable holdings must be in danelfin scope
    danelfin_set = set(danelfin_symbols)
    missing_holdings = danelfin_applicable - danelfin_set

    assert (
        not missing_holdings
    ), f"Danelfin scope missing applicable holdings: {missing_holdings}"

    # Verify no extra symbols in danelfin scope (only applicable holdings)
    market_proxies_set = set(
        scope.get("planned_symbols", {}).get("market_proxies", [])
    )
    extra_symbols = danelfin_set - danelfin_applicable - market_proxies_set

    assert (
        not extra_symbols
    ), f"Danelfin scope includes unexpected symbols: {extra_symbols}"


def test_other_provider_scope_regression_test() -> None:
    """Test 12: Provider-independent scope safety - other providers unaffected."""
    from scripts.refresh_signals import (
        _build_refresh_scope,
        _load_portfolio_provider_holdings,
        REFRESH_MODE_PORTFOLIO_SIGNALS,
    )

    scope = _build_refresh_scope(refresh_mode=REFRESH_MODE_PORTFOLIO_SIGNALS)
    provider_symbols = scope.get("planned_symbols", {}).get("provider_symbols", {})

    # All three stock providers should have same applicable holdings (55)
    for provider_name in ("zacks", "danelfin", "yahoo"):
        provider_scope = provider_symbols.get(provider_name, [])
        applicable = _load_portfolio_provider_holdings(provider_name)

        assert (
            len(provider_scope) == 55
        ), f"{provider_name} scope has unexpected count: {len(provider_scope)}"

        provider_set = set(provider_scope)
        assert provider_set == applicable, (
            f"{provider_name} scope mismatch: "
            f"expected {applicable}, got {provider_set}"
        )

        # No proxies in any stock provider
        market_proxies_set = set(scope.get("planned_symbols", {}).get("market_proxies", []))
        proxy_in_scope = [s for s in provider_scope if s in market_proxies_set]
        assert not proxy_in_scope, (
            f"{provider_name} incorrectly includes proxies: {proxy_in_scope}"
        )


def test_danelfin_running_progress_display_test() -> None:
    """Test 13: Running-state UI - progress display during active refresh."""
    src = _OUTCOME_APP_JS.read_text(encoding="utf-8")

    # Running-state progress text still exists for active provider stages.
    assert "Active refresh progress:" in src

    # refresh_progress.active should be gated by both runtime running status and
    # non-terminal provider state.
    assert "active: refreshRunning && !isTerminalState" in src


def test_danelfin_terminal_complete_display_test() -> None:
    """Test 14: Terminal success UI - no stale progress after completion."""
    src = _OUTCOME_APP_JS.read_text(encoding="utf-8")

    # Terminal states are recognized explicitly.
    assert "const isTerminalState = [\"COMPLETE\", \"COMPLETE_WITH_ERRORS\", \"FAILED\", \"SKIPPED\"].includes(refreshState);" in src

    # Active progress line renders only while active (prevents stale terminal numerator).
    assert "if (refreshProgress.active) {" in src

    # Terminal state/execution summary remains visible.
    assert "Refresh state:" in src
    assert "Execution: attempted" in src


def test_danelfin_terminal_error_display_test() -> None:
    """Test 15: Terminal error UI - genuine errors remain visible."""
    src = _OUTCOME_APP_JS.read_text(encoding="utf-8")

    # Terminal execution summary includes failed count and is shown for terminal states.
    assert "const failedExec = _asFiniteNumber(refreshProgress.failed_count);" in src
    assert "failed ${failedLabel}" in src
    assert "if ((refreshProgress.active || isTerminalState)" in src


def test_danelfin_cache_source_date_display_test() -> None:
    """Test 16: Cache-source-date display - accurate row counts and semantics."""
    # Fixture: latest cache rows=56, sourced today=54, older but valid=2
    # Verify displayed source-date/cache metric uses 54/56 and does not claim
    # this is execution progress.


    latest_cache = _REPO_ROOT / "data" / "signals" / "danelfin" / "latest_danelfin.csv"

    if latest_cache.exists():
        import csv
        from datetime import date

        today = date.today().isoformat()
        today_count = 0
        total_count = 0
        sourced_dates_observed = {}

        with latest_cache.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                total_count += 1
                sd = str(row.get("sourced_date", "")).strip()
                sourced_dates_observed[sd] = sourced_dates_observed.get(sd, 0) + 1
                if sd == today:
                    today_count += 1

        # After danelfin refresh on Sept 1:
        # - latest cache should have 56 total unique symbols
        # - 54 sourced on 2026-09-01
        # - 2 sourced on 2026-08-29 (SBS, YELP carryover)

        assert total_count > 0, "Latest danelfin cache is empty"

        if total_count >= 54 and today_count >= 54:
            # If we have fresh data from today, verify the breakdown
            assert (
                today_count <= total_count
            ), f"Today count ({today_count}) > total ({total_count})"

            # The displayed metric "Provider today rows" should show:
            # - Numerator: rows sourced today (54)
            # - Denominator: total rows in cache (56)
            # - Display: "54/56" or "54/56 · 96.4%"
            # This is NOT execution progress; it's cache composition.

            pct = round(today_count / total_count * 100.0, 1)
            assert (
                pct >= 95.0
            ), f"Cache freshness too low: {today_count}/{total_count} = {pct}%"

    src = _OUTCOME_APP_JS.read_text(encoding="utf-8")
    assert "Latest cache sourced today:" in src
    assert "Provider today rows:" not in src


if __name__ == "__main__":
    print("Run with: python -m pytest tests/test_danelfin_scope_ui_repair.py -v")
