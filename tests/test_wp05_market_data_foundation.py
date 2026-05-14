from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.history.market_data_manager import (
    persist_benchmark_returns,
    persist_investable_vehicle_returns,
    persist_security_prices,
)
from src.models.market_data_models import (
    BenchmarkReturnRow,
    HistoricalPriceRow,
    InvestableVehicleReturnRow,
)
from src.validation.market_data_validator import (
    validate_benchmark_history_presence,
    validate_benchmark_return_rows,
    validate_curve_depth,
    validate_historical_replay_window,
    validate_historical_price_rows,
    validate_investable_vehicle_return_rows,
    validate_no_lookahead_series_dates,
    validate_replay_window,
    validate_timeseries_monotonic_dates,
    validate_vehicle_history_presence,
)


def _price(symbol: str, d: str, value: float) -> HistoricalPriceRow:
    return HistoricalPriceRow(
        security_id=f"FIDELITY:{symbol}",
        symbol=symbol,
        security_type="Common Stock",
        date=d,
        open=value,
        high=value,
        low=value,
        close=value,
        adjusted_close=value,
        volume=1000,
        dividend=0.0,
        split_ratio=1.0,
        source_provider="TEST",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def test_market_data_validators_basic_pass() -> None:
    prices = [_price("AAA", "2026-05-13", 100.0), _price("AAA", "2026-05-14", 102.0)]
    bench = [
        BenchmarkReturnRow("BM1", "^GSPC", "2026-05-13", 100.0, 0.0, "TEST"),
        BenchmarkReturnRow("BM1", "^GSPC", "2026-05-14", 102.0, 0.02, "TEST"),
    ]
    veh = [
        InvestableVehicleReturnRow("VEH1", "SPY", "2026-05-13", 100.0, 0.0, "TEST"),
        InvestableVehicleReturnRow("VEH1", "SPY", "2026-05-14", 101.0, 0.01, "TEST"),
    ]

    assert validate_historical_price_rows(prices) == []
    assert validate_benchmark_return_rows(bench) == []
    assert validate_investable_vehicle_return_rows(veh) == []
    assert validate_replay_window("2026-05-13", "2027-05-13") == []
    assert validate_historical_replay_window(start_date="2025-05-13", end_date="2026-05-13", as_of_date="2026-05-13") == []
    assert validate_no_lookahead_series_dates(
        start_date="2026-05-13", end_date="2026-05-14", series_dates=["2026-05-13", "2026-05-14"]
    ) == []
    assert validate_benchmark_history_presence("BM1", bench) == []
    assert validate_vehicle_history_presence("VEH1", veh) == []
    assert validate_curve_depth(curve_name="benchmark:BM1", point_count=len(bench), minimum_points=2) == []


def test_historical_replay_window_blocks_future_end_date() -> None:
    errors = validate_historical_replay_window(
        start_date="2026-05-13",
        end_date="2027-05-13",
        as_of_date="2026-05-13",
    )
    assert any("cannot be in the future" in err.lower() for err in errors)


def test_curve_depth_and_history_presence_fail_closed() -> None:
    assert validate_benchmark_history_presence("BM_MISSING", [])
    assert validate_vehicle_history_presence("VEH_MISSING", [])
    errors = validate_curve_depth(curve_name="benchmark:BM1", point_count=1, minimum_points=2)
    assert any("insufficient curve depth" in err.lower() for err in errors)


def test_timeseries_monotonic_validator_detects_duplicate() -> None:
    errors = validate_timeseries_monotonic_dates(
        [("2026-05-13", 1.0), ("2026-05-13", 2.0)]
    )
    assert any("duplicate" in err.lower() for err in errors)


def test_market_data_storage_partition_append_only(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    history_prices = tmp_path / "data" / "history" / "prices"
    history_bench = tmp_path / "data" / "history" / "benchmarks"
    history_veh = tmp_path / "data" / "history" / "investable_vehicles"

    prices = [_price("AAA", "2026-05-13", 100.0), _price("AAA", "2026-05-14", 102.0)]
    bench = [
        BenchmarkReturnRow("BM1", "^GSPC", "2026-05-13", 100.0, 0.0, "TEST"),
        BenchmarkReturnRow("BM1", "^GSPC", "2026-05-14", 102.0, 0.02, "TEST"),
    ]
    veh = [
        InvestableVehicleReturnRow("VEH1", "SPY", "2026-05-13", 100.0, 0.0, "TEST"),
        InvestableVehicleReturnRow("VEH1", "SPY", "2026-05-14", 101.0, 0.01, "TEST"),
    ]

    result_prices = persist_security_prices(rows=prices, current_root=current_root, history_root=history_prices)
    result_bench = persist_benchmark_returns(rows=bench, current_root=current_root, history_root=history_bench)
    result_veh = persist_investable_vehicle_returns(rows=veh, current_root=current_root, history_root=history_veh)

    assert result_prices["history_rows_appended"] == 2
    assert result_bench["history_rows_appended"] == 2
    assert result_veh["history_rows_appended"] == 2

    bench_current = (current_root / "benchmark_returns.csv").read_text(encoding="utf-8")
    veh_current = (current_root / "investable_vehicle_returns.csv").read_text(encoding="utf-8")
    assert "adjusted_close" in bench_current.splitlines()[0]
    assert "adjusted_close" in veh_current.splitlines()[0]

    # Re-appending identical rows should not create duplicates.
    result_prices_2 = persist_security_prices(rows=prices, current_root=current_root, history_root=history_prices)
    assert result_prices_2["history_rows_appended"] == 0
