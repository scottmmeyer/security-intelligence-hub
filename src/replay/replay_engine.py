"""Deterministic replay selection and performance-series scaffolding for WP-04/WP-05A/WP-05D."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.models.analytical_models import (
    AnalyticalUniverseRow,
    PerformanceSeries,
    PerformanceSeriesType,
    ReplayMode,
    ReplaySelection,
)
from src.replay.history_providers import (
    BenchmarkHistoryProvider,
    InvestableVehicleHistoryProvider,
    NullBenchmarkHistoryProvider,
    NullInvestableVehicleHistoryProvider,
    NullSecurityPriceHistoryProvider,
    PricePoint,
    SecurityPriceHistoryProvider,
    ensure_chronological,
    equal_weighted_mean_series,
)

REPLAY_SELECTION_HEADERS = [
    "replay_id",
    "start_date",
    "end_date",
    "filter_market_cap_bucket",
    "filter_geography",
    "filter_industry",
    "filter_analytical_subtier",
    "selection_method",
    "top_n",
    "selected_symbols",
    "composite_score_snapshot_date",
    "replay_mode",
]

PERFORMANCE_SERIES_HEADERS = [
    "series_id",
    "replay_id",
    "series_type",
    "date",
    "value",
    "cumulative_return",
    "source",
    "coverage_status",
]


def _write_csv(path: Path, headers: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)


def _to_replay_id(
    *,
    start_date: str,
    end_date: str,
    geography: str,
    market_cap_bucket: str,
    industry: str,
    top_n: int,
    replay_id_suffix: str | None,
    analytical_subtier: str | None = None,
) -> str:
    clean_industry = industry.replace(" ", "_").upper()
    base = (
        f"REPLAY-{start_date}-TO-{end_date}-{geography.upper()}-"
        f"{market_cap_bucket.upper()}-{clean_industry}-TOP{top_n}"
    )
    if analytical_subtier:
        base = f"{base}-{analytical_subtier.upper()}"
    if replay_id_suffix:
        return f"{base}-{replay_id_suffix}"
    return base


def detect_replay_mode(start_date: str, end_date: str) -> str:
    """Classify a replay window into a ReplayMode value. Phase F temporal semantics.

    FORWARD_SIMULATION     — end_date is strictly in the future.
    CURRENT_RECOMMENDATION — end_date is today (captures live market level).
    HISTORICAL_VALIDATION  — both start and end are in the past.
    """
    today = date.today()
    end = date.fromisoformat(end_date)
    if end > today:
        return ReplayMode.FORWARD_SIMULATION.value
    if end == today:
        return ReplayMode.CURRENT_RECOMMENDATION.value
    return ReplayMode.HISTORICAL_VALIDATION.value


def select_top_n_replay(
    *,
    analytical_rows: Iterable[AnalyticalUniverseRow],
    start_date: str,
    end_date: str,
    market_cap_bucket: str,
    geography: str,
    industry: str,
    top_n: int,
    selection_method: str = "TOP_N_COMPOSITE_AT_START",
    replay_id_suffix: str | None = None,
    filter_analytical_subtier: str | None = None,
) -> tuple[ReplaySelection, List[AnalyticalUniverseRow]]:
    """Apply point-in-time filters and deterministic top-N selection without lookahead.

    When ``filter_analytical_subtier`` is provided, an additional filter is applied
    after the standard bucket/geography/industry filters.  When omitted (default),
    existing behaviour is preserved — full backward compatibility.
    """

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("Replay selection blocked: end_date must be >= start_date.")

    market_cap_filter = market_cap_bucket.upper()
    geography_filter = geography.upper()
    industry_filter = industry.upper()
    subtier_filter = filter_analytical_subtier.upper() if filter_analytical_subtier else None

    start_rows = [row for row in analytical_rows if row.snapshot_date == start_date]
    if not start_rows:
        raise ValueError(
            "Replay selection blocked: no analytical universe rows found for start_date="
            f"{start_date}."
        )

    filtered_rows = [
        row
        for row in start_rows
        if row.market_cap_bucket.upper() == market_cap_filter
        and row.geography.upper() == geography_filter
        and (industry_filter == "ALL" or row.industry.upper() == industry_filter)
        and (subtier_filter is None or row.analytical_market_cap_subtier.upper() == subtier_filter)
        and getattr(row, "replay_eligible", True) is not False
        and str(getattr(row, "replay_eligible", True)).lower() != "false"
    ]

    # Deterministic ranking: highest composite first, symbol as tie-breaker.
    # Some snapshots can contain duplicate symbol rows; preserve only the
    # first occurrence after ranking so Top-N membership is unique by symbol.
    sorted_rows = sorted(filtered_rows, key=lambda item: (-float(item.composite_score), item.symbol))
    sorted_unique_rows: List[AnalyticalUniverseRow] = []
    seen_symbols: set[str] = set()
    for row in sorted_rows:
        symbol = str(row.symbol or "").upper()
        if not symbol or symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        sorted_unique_rows.append(row)

    selected_rows = sorted_unique_rows[: max(top_n, 0)]

    replay_id = _to_replay_id(
        start_date=start_date,
        end_date=end_date,
        geography=geography,
        market_cap_bucket=market_cap_bucket,
        industry=industry,
        top_n=top_n,
        replay_id_suffix=replay_id_suffix,
        analytical_subtier=filter_analytical_subtier,
    )
    selection = ReplaySelection(
        replay_id=replay_id,
        start_date=start_date,
        end_date=end_date,
        filter_market_cap_bucket=market_cap_filter,
        filter_geography=geography_filter,
        filter_industry=industry_filter,
        filter_analytical_subtier=filter_analytical_subtier or "",
        selection_method=selection_method,
        top_n=top_n,
        selected_symbols=tuple(row.symbol for row in selected_rows),
        composite_score_snapshot_date=start_date,
        replay_mode=detect_replay_mode(start_date, end_date),
    )

    return selection, sorted_unique_rows


def _series_from_points(
    *,
    series_id: str,
    replay_id: str,
    series_type: PerformanceSeriesType,
    points: Sequence[PricePoint],
    source: str,
    coverage_status: str = "AVAILABLE",
) -> List[PerformanceSeries]:
    if not points:
        return []

    ordered = ensure_chronological(points)
    base = ordered[0].value
    if base == 0:
        return []

    output: List[PerformanceSeries] = []
    for point in ordered:
        cumulative = (point.value / base) - 1.0
        output.append(
            PerformanceSeries(
                series_id=series_id,
                replay_id=replay_id,
                series_type=series_type.value,
                date=point.date,
                value=round(float(point.value), 8),
                cumulative_return=round(float(cumulative), 8),
                source=source,
                coverage_status=coverage_status,
            )
        )
    return output


def build_performance_series(
    *,
    selection: ReplaySelection,
    full_universe_rows: Sequence[AnalyticalUniverseRow],
    benchmark_symbol_or_index: str,
    investable_vehicle_symbol: str,
    security_price_provider: SecurityPriceHistoryProvider | None = None,
    benchmark_provider: BenchmarkHistoryProvider | None = None,
    vehicle_provider: InvestableVehicleHistoryProvider | None = None,
    full_universe_curve_result: Any | None = None,
    top_n_curve_result: Any | None = None,
) -> List[PerformanceSeries]:
    """Build replay performance series lines using provider interfaces or null stubs.

    WP-05D: If ``full_universe_curve_result`` or ``top_n_curve_result`` are
    provided (StockCurveResult instances from stock_replay_service), their
    pre-built points are used directly and the security_price_provider is not
    called for those series.
    """

    security_provider = security_price_provider or NullSecurityPriceHistoryProvider()
    benchmark_history = benchmark_provider or NullBenchmarkHistoryProvider()
    vehicle_history = vehicle_provider or NullInvestableVehicleHistoryProvider()

    benchmark_points = benchmark_history.get_benchmark_series(
        benchmark_symbol_or_index, selection.start_date, selection.end_date
    )
    vehicle_points = vehicle_history.get_vehicle_series(
        investable_vehicle_symbol, selection.start_date, selection.end_date
    )

    series: List[PerformanceSeries] = []
    series.extend(
        _series_from_points(
            series_id=f"{selection.replay_id}:BENCHMARK",
            replay_id=selection.replay_id,
            series_type=PerformanceSeriesType.BENCHMARK,
            points=benchmark_points,
            source="benchmark_history_provider",
            coverage_status="AVAILABLE",
        )
    )
    series.extend(
        _series_from_points(
            series_id=f"{selection.replay_id}:INVESTABLE_VEHICLE",
            replay_id=selection.replay_id,
            series_type=PerformanceSeriesType.INVESTABLE_VEHICLE,
            points=vehicle_points,
            source="investable_vehicle_history_provider",
            coverage_status="AVAILABLE",
        )
    )

    # FULL_UNIVERSE — prefer pre-built stock curve result
    if full_universe_curve_result is not None and full_universe_curve_result.points:
        series.extend(
            _series_from_points(
                series_id=f"{selection.replay_id}:FULL_UNIVERSE",
                replay_id=selection.replay_id,
                series_type=PerformanceSeriesType.FULL_UNIVERSE,
                points=list(full_universe_curve_result.points),
                source="stock_replay_service:equal_weighted",
                coverage_status=full_universe_curve_result.coverage_status,
            )
        )
    else:
        universe_symbols = sorted({row.symbol for row in full_universe_rows})
        universe_symbol_series: Dict[str, Sequence[PricePoint]] = {
            symbol: security_provider.get_symbol_series(symbol, selection.start_date, selection.end_date)
            for symbol in universe_symbols
        }
        full_universe_points = equal_weighted_mean_series(universe_symbol_series)
        series.extend(
            _series_from_points(
                series_id=f"{selection.replay_id}:FULL_UNIVERSE",
                replay_id=selection.replay_id,
                series_type=PerformanceSeriesType.FULL_UNIVERSE,
                points=full_universe_points,
                source="security_price_history_provider:equal_weighted",
                coverage_status="AVAILABLE",
            )
        )

    # TOP_N_STRATEGY — prefer pre-built stock curve result
    top_n_symbols = list(selection.selected_symbols)
    if top_n_curve_result is not None and top_n_curve_result.points:
        series.extend(
            _series_from_points(
                series_id=f"{selection.replay_id}:TOP_N_STRATEGY",
                replay_id=selection.replay_id,
                series_type=PerformanceSeriesType.TOP_N_STRATEGY,
                points=list(top_n_curve_result.points),
                source="stock_replay_service:equal_weighted_hold",
                coverage_status=top_n_curve_result.coverage_status,
            )
        )
    else:
        top_n_symbol_series: Dict[str, Sequence[PricePoint]] = {
            symbol: security_provider.get_symbol_series(symbol, selection.start_date, selection.end_date)
            for symbol in top_n_symbols
        }
        top_n_points = equal_weighted_mean_series(top_n_symbol_series)
        series.extend(
            _series_from_points(
                series_id=f"{selection.replay_id}:TOP_N_STRATEGY",
                replay_id=selection.replay_id,
                series_type=PerformanceSeriesType.TOP_N_STRATEGY,
                points=top_n_points,
                source="security_price_history_provider:equal_weighted_hold",
                coverage_status="AVAILABLE",
            )
        )

    return sorted(series, key=lambda item: (item.series_type, item.date, item.series_id))


def persist_replay_outputs(
    *,
    selection: ReplaySelection,
    performance_series: Sequence[PerformanceSeries],
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/replays",
    benchmark_symbol_or_index: str,
    investable_vehicle_symbol: str,
) -> Dict[str, str]:
    """Persist replay contracts to current and immutable replay history outputs.

    Phase A: history partition uses snapshot_date subdirectory derived from
    ``selection.composite_score_snapshot_date`` so replay history is grouped by
    the analytical universe snapshot that produced the selection.
    """

    current_root_path = Path(current_root)
    history_root_path = Path(history_root)

    # Phase A — snapshot_date-partitioned replay history directory
    snapshot_date_partition = selection.composite_score_snapshot_date or "unknown"
    replay_dir = (
        history_root_path
        / f"snapshot_date={snapshot_date_partition}"
        / f"replay_id={selection.replay_id}"
    )
    if replay_dir.exists():
        raise ValueError(
            "Immutable replay partition protection triggered: replay directory already exists at "
            f"{replay_dir}."
        )

    selection_row = {
        "replay_id": selection.replay_id,
        "start_date": selection.start_date,
        "end_date": selection.end_date,
        "filter_market_cap_bucket": selection.filter_market_cap_bucket,
        "filter_geography": selection.filter_geography,
        "filter_industry": selection.filter_industry,
        "filter_analytical_subtier": selection.filter_analytical_subtier,
        "selection_method": selection.selection_method,
        "top_n": str(selection.top_n),
        "selected_symbols": "|".join(selection.selected_symbols),
        "composite_score_snapshot_date": selection.composite_score_snapshot_date,
        "replay_mode": selection.replay_mode,
    }

    series_rows = [asdict(item) for item in performance_series]

    replay_dir.mkdir(parents=True, exist_ok=False)
    current_root_path.mkdir(parents=True, exist_ok=True)

    current_inputs_path = current_root_path / "replay_inputs.csv"
    current_series_path = current_root_path / "replay_performance_series.csv"

    replay_selection_path = replay_dir / "replay_selection.csv"
    replay_series_path = replay_dir / "replay_performance_series.csv"
    replay_metadata_path = replay_dir / "replay_metadata.json"
    replay_report_path = replay_dir / "replay_report.md"

    # Note: current/ is NOT written here — the matrix builder (build_wp05b_replay_matrix)
    # owns current/ via atomic publish and handles merge across sectors.
    _write_csv(replay_selection_path, REPLAY_SELECTION_HEADERS, [selection_row])
    _write_csv(replay_series_path, PERFORMANCE_SERIES_HEADERS, series_rows)

    metadata = {
        "replay_id": selection.replay_id,
        "replay_mode": selection.replay_mode,
        "start_date": selection.start_date,
        "end_date": selection.end_date,
        "series_count": len(series_rows),
        "benchmark_symbol_or_index": benchmark_symbol_or_index,
        "investable_vehicle_symbol": investable_vehicle_symbol,
        "snapshot_date": snapshot_date_partition,
        "no_lookahead": "Selection uses analytical universe rows at start_date only.",
    }
    replay_metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    replay_report_path.write_text(
        "\n".join(
            [
                "# Replay Foundation Report",
                "",
                f"Replay ID: {selection.replay_id}",
                f"Replay Mode: {selection.replay_mode}",
                f"Window: {selection.start_date} -> {selection.end_date}",
                f"Filters: geography={selection.filter_geography}, market_cap_bucket={selection.filter_market_cap_bucket}, industry={selection.filter_industry}",
                f"Selection method: {selection.selection_method}",
                f"Top N: {selection.top_n}",
                f"Selected symbols: {', '.join(selection.selected_symbols) if selection.selected_symbols else 'NONE'}",
                f"Performance rows written: {len(series_rows)}",
                "",
                "WP-05D: stock-derived FULL_UNIVERSE and TOP_N_STRATEGY curves enabled.",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "current_inputs_path": str(current_inputs_path),
        "current_series_path": str(current_series_path),
        "replay_selection_path": str(replay_selection_path),
        "replay_series_path": str(replay_series_path),
        "replay_metadata_path": str(replay_metadata_path),
        "replay_report_path": str(replay_report_path),
    }


# ---------------------------------------------------------------------------
# Phase G — Replay evidence summary (WP-05D)
# ---------------------------------------------------------------------------

def build_replay_evidence_summary(
    *,
    selection: ReplaySelection,
    benchmark_symbol: str,
    investable_vehicle_symbol: str,
    full_universe_symbol_count: int,
    full_universe_curve_result: Any | None,
    top_n_curve_result: Any | None,
    performance_series: Sequence[PerformanceSeries],
) -> Dict[str, Any]:
    """Build the replay_evidence_summary.json payload.

    Captures all quantitative outcomes and coverage metadata in one artifact so
    downstream consumers can understand strategy vs benchmark/vehicle performance
    without parsing the full performance series CSV.

    Returns a dict suitable for json.dumps().
    """

    def _last_cumulative_return(series_type: str) -> float | None:
        rows = [r for r in performance_series if r.series_type == series_type]
        if not rows:
            return None
        ordered = sorted(rows, key=lambda r: r.date)
        return round(float(ordered[-1].cumulative_return), 8)

    benchmark_final = _last_cumulative_return("BENCHMARK")
    vehicle_final = _last_cumulative_return("INVESTABLE_VEHICLE")
    universe_final = _last_cumulative_return("FULL_UNIVERSE")
    top_n_final = _last_cumulative_return("TOP_N_STRATEGY")

    def _delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return round(a - b, 8)

    # Aggregate coverage status across both stock curves
    fu_status = full_universe_curve_result.coverage_status if full_universe_curve_result else "FAILED"
    tn_status = top_n_curve_result.coverage_status if top_n_curve_result else "FAILED"

    statuses = {fu_status, tn_status}
    if "FAILED" in statuses or "MISSING_MARKET_DATA" in statuses:
        overall_coverage = "FAILED"
    elif "PARTIAL" in statuses or "INSUFFICIENT_HISTORY" in statuses:
        overall_coverage = "PARTIAL"
    else:
        overall_coverage = "AVAILABLE"

    summary: Dict[str, Any] = {
        "replay_id": selection.replay_id,
        "replay_mode": selection.replay_mode,
        "start_date": selection.start_date,
        "end_date": selection.end_date,
        "geography": selection.filter_geography,
        "market_cap_bucket": selection.filter_market_cap_bucket,
        "industry": selection.filter_industry,
        "benchmark_symbol": benchmark_symbol,
        "investable_vehicle_symbol": investable_vehicle_symbol,
        "full_universe_symbol_count": full_universe_symbol_count,
        "top_n": selection.top_n,
        "selected_symbols": list(selection.selected_symbols),
        "missing_price_symbols": list(
            (full_universe_curve_result.symbols_missing if full_universe_curve_result else [])
        ),
        "partial_price_symbols": list(
            (full_universe_curve_result.symbols_insufficient if full_universe_curve_result else [])
        ),
        "benchmark_final_return": benchmark_final,
        "investable_vehicle_final_return": vehicle_final,
        "full_universe_final_return": universe_final,
        "top_n_strategy_final_return": top_n_final,
        "strategy_vs_benchmark_delta": _delta(top_n_final, benchmark_final),
        "strategy_vs_vehicle_delta": _delta(top_n_final, vehicle_final),
        "full_universe_coverage_status": fu_status,
        "top_n_coverage_status": tn_status,
        "coverage_status": overall_coverage,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return summary


def write_replay_evidence_summary(
    *,
    replay_dir: Path,
    summary: Dict[str, Any],
) -> Path:
    """Write replay_evidence_summary.json into the replay partition directory."""
    evidence_path = replay_dir / "replay_evidence_summary.json"
    evidence_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return evidence_path
