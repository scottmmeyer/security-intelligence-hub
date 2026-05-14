from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import sys

import pandas as pd
import pytest

from src.models.market_data_models import HistoricalPriceRow
from src.models.analytical_models import AnalyticalUniverseRow
from src.replay.history_providers import (
    YahooBenchmarkProvider,
    YahooHistoricalPriceProvider,
    YahooInvestableVehicleProvider,
)
from src.replay.replay_engine import build_performance_series, select_top_n_replay
from src.replay.history_providers import PricePoint


class _FixedSecurityProvider:
    def get_symbol_series(self, symbol: str, start_date: str, end_date: str):
        if symbol == "AAA":
            return [PricePoint("2026-05-13", 100.0), PricePoint("2026-05-14", 103.0)]
        return [PricePoint("2026-05-13", 100.0), PricePoint("2026-05-14", 101.0)]


class _FixedBenchmarkProvider:
    def get_benchmark_series(self, benchmark_symbol_or_index: str, start_date: str, end_date: str):
        return [PricePoint("2026-05-13", 100.0), PricePoint("2026-05-14", 102.0)]


class _FixedVehicleProvider:
    def get_vehicle_series(self, symbol: str, start_date: str, end_date: str):
        return [PricePoint("2026-05-13", 100.0), PricePoint("2026-05-14", 101.5)]


def _row(symbol: str, score: float) -> AnalyticalUniverseRow:
    return AnalyticalUniverseRow(
        security_id=f"FIDELITY:{symbol}",
        symbol=symbol,
        security_type="Common Stock",
        snapshot_date="2026-05-13",
        run_id="RUN-TEST",
        market_cap_bucket="LARGE",
        geography="US",
        country="US",
        industry="ALL",
        sector="ALL",
        composite_score=score,
        ess_score_text="BULLISH",
        zacks_rating="",
        yahoo_score="",
        danelfin_score="",
        benchmark_id="BM_US_LARGE_SP500",
        investable_vehicle_id="VEH_US_LARGE_SPY",
        price_at_snapshot="",
        provider_lineage="provider=FIDELITY",
    )


def test_top_n_replay_equal_weight_calculations() -> None:
    rows = [_row("AAA", 4.0), _row("BBB", 3.9)]
    selection, filtered = select_top_n_replay(
        analytical_rows=rows,
        start_date="2026-05-13",
        end_date="2026-05-14",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=2,
        replay_id_suffix="UNIT",
    )

    series = build_performance_series(
        selection=selection,
        full_universe_rows=filtered,
        benchmark_symbol_or_index="^GSPC",
        investable_vehicle_symbol="SPY",
        security_price_provider=_FixedSecurityProvider(),
        benchmark_provider=_FixedBenchmarkProvider(),
        vehicle_provider=_FixedVehicleProvider(),
    )

    by_type = {}
    for row in series:
        by_type.setdefault(row.series_type, []).append(row)

    assert len(by_type["BENCHMARK"]) == 2
    assert len(by_type["INVESTABLE_VEHICLE"]) == 2
    assert len(by_type["FULL_UNIVERSE"]) == 2
    assert len(by_type["TOP_N_STRATEGY"]) == 2

    # Equal-weight universe average: day2 value is (103 + 101) / 2 = 102
    assert by_type["FULL_UNIVERSE"][1].value == 102.0
    assert by_type["FULL_UNIVERSE"][1].cumulative_return == 0.02


class _StubHistoricalProvider:
    def get_historical_prices(self, *, security_id: str, symbol: str, security_type: str, start_date: str, end_date: str):
        del security_id, security_type, start_date, end_date
        return [
            HistoricalPriceRow(
                security_id=f"TEST:{symbol}",
                symbol=symbol,
                security_type="ETF",
                date="2026-05-13",
                open=100.0,
                high=100.0,
                low=100.0,
                close=100.0,
                adjusted_close=100.0,
                volume=1,
                dividend=0.0,
                split_ratio=1.0,
                source_provider="TEST",
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            ),
            HistoricalPriceRow(
                security_id=f"TEST:{symbol}",
                symbol=symbol,
                security_type="ETF",
                date="2026-05-14",
                open=102.0,
                high=102.0,
                low=102.0,
                close=102.0,
                adjusted_close=102.0,
                volume=1,
                dividend=0.0,
                split_ratio=1.0,
                source_provider="TEST",
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            ),
        ]


def test_yahoo_historical_provider_normalizes_multiindex_and_uses_auto_adjust(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {}

    columns = pd.MultiIndex.from_tuples(
        [
            ("Open", "SPY"),
            ("High", "SPY"),
            ("Low", "SPY"),
            ("Close", "SPY"),
            ("Volume", "SPY"),
            ("Dividends", "SPY"),
            ("Stock Splits", "SPY"),
        ]
    )
    frame = pd.DataFrame(
        [
            [100.0, 101.0, 99.0, 100.0, 1000.0, 0.0, 0.0],
            [101.0, 103.0, 100.0, 102.0, 1200.0, 0.0, 0.0],
        ],
        columns=columns,
        index=pd.to_datetime(["2026-05-13", "2026-05-14"]),
    )

    def _fake_download(**kwargs):
        calls.update(kwargs)
        return frame

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=_fake_download))

    provider = YahooHistoricalPriceProvider()
    rows = provider.get_historical_prices(
        security_id="TEST:SPY",
        symbol="SPY",
        security_type="ETF",
        start_date="2026-05-13",
        end_date="2026-05-14",
    )

    assert calls["auto_adjust"] is True
    assert len(rows) == 2
    assert rows[0].adjusted_close == rows[0].close
    assert rows[1].adjusted_close == rows[1].close


def test_wp05a_supported_symbol_guards_and_adjusted_close_returns() -> None:
    historical = _StubHistoricalProvider()
    benchmark_provider = YahooBenchmarkProvider(historical)
    vehicle_provider = YahooInvestableVehicleProvider(historical)

    benchmark_rows = benchmark_provider.get_benchmark_returns(
        benchmark_id="BM_US_LARGE_SP500",
        symbol_or_index="^GSPC",
        start_date="2026-05-13",
        end_date="2026-05-14",
    )
    vehicle_rows = vehicle_provider.get_investable_vehicle_returns(
        vehicle_id="VEH_US_LARGE_SPY",
        symbol="SPY",
        start_date="2026-05-13",
        end_date="2026-05-14",
    )

    assert benchmark_rows[0].adjusted_close == 100.0
    assert benchmark_rows[1].cumulative_return == 0.02
    assert vehicle_rows[1].adjusted_close == 102.0
    assert vehicle_rows[1].cumulative_return == 0.02

    with pytest.raises(ValueError, match="Unsupported benchmark symbol"):
        benchmark_provider.get_benchmark_returns(
            benchmark_id="BM_BAD",
            symbol_or_index="ACWX",
            start_date="2026-05-13",
            end_date="2026-05-14",
        )

    with pytest.raises(ValueError, match="Unsupported investable vehicle symbol"):
        vehicle_provider.get_investable_vehicle_returns(
            vehicle_id="VEH_BAD",
            symbol="SCJ",
            start_date="2026-05-13",
            end_date="2026-05-14",
        )
