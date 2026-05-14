"""Validation contracts for WP-05 market data and replay return engine."""

from __future__ import annotations

from datetime import date
from typing import Iterable, List, Sequence, Tuple

from src.models.market_data_models import (
    BenchmarkReturnRow,
    HistoricalPriceRow,
    InvestableVehicleReturnRow,
)


def validate_replay_window(start_date: str, end_date: str) -> List[str]:
    errors: List[str] = []
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return ["Replay window validation failed: start_date and end_date must be ISO dates."]

    if end < start:
        errors.append("Replay window validation failed: end_date must be >= start_date.")
    return errors


def validate_historical_replay_window(
    *,
    start_date: str,
    end_date: str,
    as_of_date: str | None = None,
) -> List[str]:
    """Validate that replay windows are historical-only and not future-facing."""

    errors = validate_replay_window(start_date, end_date)
    if errors:
        return errors

    end = date.fromisoformat(end_date)
    as_of = date.fromisoformat(as_of_date) if as_of_date else date.today()
    if end > as_of:
        return [
            "Historical replay window validation failed: end_date cannot be in the future "
            f"(end_date={end_date}, as_of_date={as_of.isoformat()})."
        ]
    return []


def validate_historical_price_rows(rows: Sequence[HistoricalPriceRow]) -> List[str]:
    errors: List[str] = []
    seen: set[Tuple[str, str]] = set()

    for index, row in enumerate(rows, start=1):
        if not row.symbol:
            errors.append(f"HistoricalPriceRow[{index}] missing symbol.")
        if not row.security_id:
            errors.append(f"HistoricalPriceRow[{index}] missing security_id.")
        try:
            date.fromisoformat(row.date)
        except ValueError:
            errors.append(f"HistoricalPriceRow[{index}] has invalid date {row.date!r}.")

        key = (row.symbol, row.date)
        if key in seen:
            errors.append(f"HistoricalPriceRow duplicate detected for symbol/date {key!r}.")
        seen.add(key)

        if row.adjusted_close <= 0:
            errors.append(f"HistoricalPriceRow[{index}] adjusted_close must be > 0.")

    return errors


def validate_benchmark_return_rows(rows: Sequence[BenchmarkReturnRow]) -> List[str]:
    errors: List[str] = []
    seen: set[Tuple[str, str]] = set()

    for index, row in enumerate(rows, start=1):
        if not row.benchmark_id:
            errors.append(f"BenchmarkReturnRow[{index}] missing benchmark_id.")
        if not row.symbol_or_index:
            errors.append(f"BenchmarkReturnRow[{index}] missing symbol_or_index.")
        key = (row.benchmark_id, row.date)
        if key in seen:
            errors.append(f"BenchmarkReturnRow duplicate detected for benchmark/date {key!r}.")
        seen.add(key)

        if row.adjusted_close <= 0:
            errors.append(f"BenchmarkReturnRow[{index}] adjusted_close must be > 0.")

    return errors


def validate_investable_vehicle_return_rows(rows: Sequence[InvestableVehicleReturnRow]) -> List[str]:
    errors: List[str] = []
    seen: set[Tuple[str, str]] = set()

    for index, row in enumerate(rows, start=1):
        if not row.vehicle_id:
            errors.append(f"InvestableVehicleReturnRow[{index}] missing vehicle_id.")
        if not row.symbol:
            errors.append(f"InvestableVehicleReturnRow[{index}] missing symbol.")
        key = (row.vehicle_id, row.date)
        if key in seen:
            errors.append(f"InvestableVehicleReturnRow duplicate detected for vehicle/date {key!r}.")
        seen.add(key)

        if row.adjusted_close <= 0:
            errors.append(f"InvestableVehicleReturnRow[{index}] adjusted_close must be > 0.")

    return errors


def validate_benchmark_history_presence(benchmark_id: str, rows: Sequence[BenchmarkReturnRow]) -> List[str]:
    if rows:
        return []
    return [f"Missing benchmark history for benchmark_id={benchmark_id}."]


def validate_vehicle_history_presence(vehicle_id: str, rows: Sequence[InvestableVehicleReturnRow]) -> List[str]:
    if rows:
        return []
    return [f"Missing investable vehicle history for vehicle_id={vehicle_id}."]


def validate_curve_depth(
    *,
    curve_name: str,
    point_count: int,
    minimum_points: int = 2,
) -> List[str]:
    if point_count >= minimum_points:
        return []
    return [
        f"Insufficient curve depth for {curve_name}: required >= {minimum_points} points, observed {point_count}."
    ]


def validate_price_coverage(
    required_symbols: Sequence[str],
    price_rows: Sequence[HistoricalPriceRow],
) -> List[str]:
    errors: List[str] = []
    available_symbols = {row.symbol for row in price_rows}

    missing = sorted(set(required_symbols).difference(available_symbols))
    if missing:
        errors.append(
            "Historical price coverage missing for symbols: " + ", ".join(missing[:50])
        )
    return errors


def validate_no_lookahead_series_dates(
    *,
    start_date: str,
    end_date: str,
    series_dates: Iterable[str],
) -> List[str]:
    errors: List[str] = []
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    for raw in series_dates:
        current = date.fromisoformat(raw)
        if current < start:
            errors.append(f"No-lookahead violation: series contains date before start_date: {raw}")
        if current > end:
            errors.append(f"Replay window violation: series contains date after end_date: {raw}")

    return errors


def validate_timeseries_monotonic_dates(series: Sequence[Tuple[str, float]]) -> List[str]:
    errors: List[str] = []
    seen: set[str] = set()
    previous: date | None = None

    for raw_date, _ in series:
        if raw_date in seen:
            errors.append(f"Malformed time-series: duplicate date detected {raw_date}.")
        seen.add(raw_date)

        current = date.fromisoformat(raw_date)
        if previous and current < previous:
            errors.append("Malformed time-series: dates are not monotonic ascending.")
        previous = current

    return errors


# ---------------------------------------------------------------------------
# Phase C — WP-05D stock price coverage validation
# ---------------------------------------------------------------------------


def validate_stock_coverage_status(
    coverage_status: str,
    series_type: str,
) -> List[str]:
    """Validate that a reported stock coverage status is a known canonical value."""
    from src.replay.stock_replay_service import STOCK_COVERAGE_STATUS_ENUM

    if coverage_status not in STOCK_COVERAGE_STATUS_ENUM:
        return [
            f"Invalid stock coverage_status={coverage_status!r} for series_type={series_type}. "
            f"Allowed: {sorted(STOCK_COVERAGE_STATUS_ENUM)}."
        ]
    return []


def validate_stock_price_completeness(
    *,
    symbols_requested: Sequence[str],
    symbols_available: Sequence[str],
    symbols_missing: Sequence[str],
    series_type: str,
) -> List[str]:
    """Validate coverage accounting: requested = available + missing + insufficient."""
    errors: List[str] = []
    if not symbols_requested:
        errors.append(f"Stock price completeness: no symbols requested for {series_type}.")
        return errors

    available_set = set(symbols_available)
    missing_set = set(symbols_missing)
    overlap = available_set & missing_set
    if overlap:
        errors.append(
            f"Stock coverage contract violation for {series_type}: symbols appear in both "
            f"available and missing sets: {sorted(overlap)}."
        )

    if missing_set:
        errors.append(
            f"Stock price missing for {series_type}: {len(missing_set)} of "
            f"{len(symbols_requested)} symbols have no price data: "
            + ", ".join(sorted(missing_set)[:20])
            + ("..." if len(missing_set) > 20 else "")
        )
    return errors


def validate_stock_start_price_presence(
    *,
    symbol: str,
    start_date: str,
    price_dates: Sequence[str],
) -> List[str]:
    """Validate that a stock has a price observation on or near the replay start_date."""
    if not price_dates:
        return [f"No prices available for symbol={symbol}."]

    sorted_dates = sorted(price_dates)
    first_date = sorted_dates[0]
    try:
        first = date.fromisoformat(first_date)
        start = date.fromisoformat(start_date)
    except ValueError:
        return [f"Invalid date format for symbol={symbol} start price check."]

    # Allow first observation up to 7 calendar days after start (market holidays etc.)
    if (first - start).days > 7:
        return [
            f"Missing start price for symbol={symbol}: first available date {first_date} is "
            f"more than 7 calendar days after start_date={start_date}."
        ]
    return []


def validate_stock_end_price_presence(
    *,
    symbol: str,
    end_date: str,
    price_dates: Sequence[str],
) -> List[str]:
    """Validate that a stock has a price observation on or near the replay end_date."""
    if not price_dates:
        return [f"No prices available for symbol={symbol}."]

    sorted_dates = sorted(price_dates)
    last_date = sorted_dates[-1]
    try:
        last = date.fromisoformat(last_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return [f"Invalid date format for symbol={symbol} end price check."]

    # Allow last observation up to 7 calendar days before end (market holidays etc.)
    if (end - last).days > 7:
        return [
            f"Missing end price for symbol={symbol}: last available date {last_date} is "
            f"more than 7 calendar days before end_date={end_date}."
        ]
    return []


def validate_stock_replay_curve_depth(
    *,
    series_type: str,
    point_count: int,
    minimum_points: int = 2,
) -> List[str]:
    """Validate that a stock-derived replay curve has sufficient date coverage."""
    if point_count >= minimum_points:
        return []
    return [
        f"Insufficient stock replay curve depth for {series_type}: "
        f"required >= {minimum_points} points, observed {point_count}."
    ]
