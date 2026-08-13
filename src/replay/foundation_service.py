"""WP-05A/WP-05D orchestration service for benchmark, ETF and stock historical curve foundations."""

from __future__ import annotations

import csv
import json
import os
import shutil
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from src.history.analytical_universe_manager import (
    build_analytical_universe_rows_from_current,
    write_analytical_universe_rows,
)
from src.history.market_data_manager import (
    persist_benchmark_returns,
    persist_investable_vehicle_returns,
    persist_security_prices,
)
from src.models.analytical_models import AnalyticalUniverseRow
from src.replay.history_providers import (
    BenchmarkHistoryProvider,
    BenchmarkReturnProvider,
    HistoricalPriceProvider,
    InvestableVehicleHistoryProvider,
    InvestableVehicleReturnProvider,
    NullSecurityPriceHistoryProvider,
    SecurityPriceHistoryProvider,
    YahooBenchmarkProvider,
    YahooHistoricalPriceProvider,
    YahooInvestableVehicleProvider,
)
from src.replay.registry_loader import (
    load_benchmark_category_registry,
    load_investable_vehicle_registry,
    resolve_category_mapping,
)
from src.replay.replay_engine import (
    PERFORMANCE_SERIES_HEADERS,
    REPLAY_SELECTION_HEADERS,
    build_performance_series,
    build_replay_evidence_summary,
    persist_replay_outputs,
    select_top_n_replay,
    write_replay_evidence_summary,
)
from src.replay.stock_replay_service import (
    FULL_UNIVERSE_COVERAGE_THRESHOLD,
    TOP_N_COVERAGE_THRESHOLD,
    build_full_universe_curve,
    build_top_n_curve,
)
from src.validation.replay_validator import (
    validate_analytical_universe_required_fields,
    validate_benchmark_mapping_completeness,
    validate_empty_replay_outputs,
    validate_investable_vehicle_mapping_completeness,
    validate_orphaned_replay_metadata,
    validate_performance_series_shape,
    validate_replay_availability_consistency,
    validate_replay_ui_mismatch,
    validate_replay_no_lookahead,
    validate_top_n_selection_reproducibility,
    validate_unsupported_category_exposure,
)
from src.validation.market_data_validator import (
    validate_benchmark_history_presence,
    validate_benchmark_return_rows,
    validate_curve_depth,
    validate_historical_replay_window,
    validate_historical_price_rows,
    validate_investable_vehicle_return_rows,
    validate_no_lookahead_series_dates,
    validate_price_coverage,
    validate_vehicle_history_presence,
)

REPLAY_AVAILABILITY_HEADERS = [
    "geography",
    "market_cap_bucket",
    "industry",
    "benchmark_available",
    "vehicle_available",
    "stock_replay_available",
    "top_n_available",
    "replay_generated",
    "replay_status",
    "missing_dependencies",
    "generated_at_utc",
]

REPLAY_MATRIX_HEADERS = [
    "replay_id",
    "geography",
    "market_cap_bucket",
    "industry",
    "replay_status",
    "benchmark_id",
    "vehicle_id",
    "performance_row_count",
    "replay_selection_path",
    "replay_series_path",
    "replay_metadata_path",
    "replay_availability_path",
    "replay_evidence_summary_path",
    "generated_at_utc",
]

WP05B_UI_CATEGORY_SCOPE: tuple[Tuple[str, str, str], ...] = (
    ("US", "MEGA", "ALL"),
    ("US", "LARGE", "ALL"),
    ("US", "MID", "ALL"),
    ("US", "SMALL", "ALL"),
    ("US", "MICRO", "ALL"),
    ("INTERNATIONAL", "MEGA", "ALL"),
    ("INTERNATIONAL", "LARGE", "ALL"),
    ("INTERNATIONAL", "MID", "ALL"),
    ("INTERNATIONAL", "SMALL", "ALL"),
    ("INTERNATIONAL", "MICRO", "ALL"),
)

WP05B_REPLAY_GENERATION_SCOPE: tuple[Tuple[str, str, str], ...] = (
    ("US", "MEGA", "ALL"),
    ("US", "LARGE", "ALL"),
    ("US", "MID", "ALL"),
    ("US", "SMALL", "ALL"),
    ("US", "MICRO", "ALL"),
    ("INTERNATIONAL", "MEGA", "ALL"),
    ("INTERNATIONAL", "LARGE", "ALL"),
    ("INTERNATIONAL", "MID", "ALL"),
    ("INTERNATIONAL", "SMALL", "ALL"),
    ("INTERNATIONAL", "MICRO", "ALL"),
)

# Phase C: only these files are atomically published to data/current/
_CURRENT_ATOMIC_OUTPUT_FILES = [
    "analytical_universe.csv",
    "replay_availability.csv",
    "replay_matrix.csv",
    "replay_inputs.csv",
    "replay_performance_series.csv",
    "security_prices.csv",
]

# Phase B: snapshot registry headers
ANALYTICAL_SNAPSHOT_REGISTRY_HEADERS = [
    "snapshot_date",
    "run_id",
    "created_at_utc",
    "analytical_universe_rows",
    "replay_count",
    "replay_coverage_status",
    "benchmark_count",
    "vehicle_count",
    "generation_status",
]

REPLAY_SNAPSHOT_REGISTRY_HEADERS = [
    "replay_id",
    "snapshot_date",
    "start_date",
    "end_date",
    "geography",
    "market_cap_bucket",
    "industry",
    "benchmark_available",
    "vehicle_available",
    "stock_replay_available",
    "top_n_available",
    "replay_status",
    "replay_mode",
    "generated_at_utc",
]


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, headers: Sequence[str], rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def _as_bool_text(value: bool) -> str:
    return "true" if value else "false"


def _classify_replay_failure(message: str) -> str:
    lowered = message.lower()
    if "mapping" in lowered or "undefined" in lowered:
        return "MISSING_MAPPING"
    if "historical" in lowered or "curve depth" in lowered or "provider" in lowered:
        return "MISSING_MARKET_DATA"
    return "BLOCKED"


def _derive_default_end_date(start_date: str) -> str:
    start = date.fromisoformat(start_date)
    return min(start + timedelta(days=365), date.today()).isoformat()


def _derive_default_history_start(snapshot_date: str) -> str:
    snapshot = date.fromisoformat(snapshot_date)
    return (snapshot - timedelta(days=365)).isoformat()


def _resolve_history_window(
    *,
    snapshot_date: str,
    start_date: str | None,
    end_date: str | None,
) -> tuple[str, str]:
    """Resolve replay history window while preserving explicit caller overrides.

    Default behavior is a trailing 365-day window ending at snapshot_date.
    Explicit start/end overrides keep their historical behavior for backward
    compatibility with existing callers.
    """
    if start_date is None and end_date is None:
        return _derive_default_history_start(snapshot_date), snapshot_date
    if start_date is not None and end_date is None:
        return start_date, _derive_default_end_date(start_date)
    if start_date is None and end_date is not None:
        return snapshot_date, end_date
    return str(start_date), str(end_date)


def _atomic_publish_current_outputs(
    tmp_root: Path,
    current_root: Path,
    output_files: Sequence[str] = _CURRENT_ATOMIC_OUTPUT_FILES,
) -> None:
    """Atomically move specific output files from tmp_root to current_root.

    Phase C guarantee: each os.replace() call is atomic on POSIX. If any move
    fails the partially-moved files will be in current/ but the remainder in
    .tmp/. The caller wraps this in try/except to clean up .tmp/ on failure.
    """
    current_root.mkdir(parents=True, exist_ok=True)
    for filename in output_files:
        src = tmp_root / filename
        if src.exists():
            os.replace(src, current_root / filename)


def _append_to_registry(
    *,
    path: Path,
    headers: Sequence[str],
    row: Dict[str, object],
) -> None:
    """Append one row to an append-oriented registry CSV (Phase B)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        if not file_exists:
            writer.writeheader()
        writer.writerow({h: row.get(h, "") for h in headers})


def _write_current_snapshot_metadata(
    current_root: Path,
    *,
    snapshot_date: str,
    run_id: str,
    generated_at_utc: str,
    source_snapshot_date: str,
    freshness_status: str,
) -> None:
    """Write Phase H freshness metadata to data/current/current_snapshot_metadata.json."""
    metadata = {
        "snapshot_date": snapshot_date,
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "source_snapshot_date": source_snapshot_date,
        "freshness_status": freshness_status,
    }
    current_root.mkdir(parents=True, exist_ok=True)
    (current_root / "current_snapshot_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )


def build_wp04_foundation(
    *,
    run_id: str,
    snapshot_date: str,
    filter_market_cap_bucket: str = "LARGE",
    filter_geography: str = "US",
    filter_industry: str = "ALL",
    filter_analytical_subtier: str | None = None,
    top_n: int = 20,
    current_root: str | Path = "data/current",
    analytical_history_root: str | Path = "data/history/analytical_universe",
    replay_history_root: str | Path = "data/history/replays",
    benchmark_registry_path: str | Path = "config/benchmark_category_registry.yaml",
    vehicle_registry_path: str | Path = "config/investable_vehicle_registry.yaml",
    start_date: str | None = None,
    end_date: str | None = None,
    security_price_provider: SecurityPriceHistoryProvider | None = None,
    benchmark_provider: BenchmarkHistoryProvider | None = None,
    vehicle_provider: InvestableVehicleHistoryProvider | None = None,
    historical_price_provider: HistoricalPriceProvider | None = None,
    benchmark_return_provider: BenchmarkReturnProvider | None = None,
    investable_vehicle_return_provider: InvestableVehicleReturnProvider | None = None,
    include_stock_curves: bool = False,
) -> Dict[str, Any]:
    """Build analytical universe plus WP-05A benchmark/ETF historical outputs."""

    benchmark_registry = load_benchmark_category_registry(path=benchmark_registry_path)
    vehicle_registry = load_investable_vehicle_registry(path=vehicle_registry_path)

    mapping_errors = []
    mapping_errors.extend(validate_benchmark_mapping_completeness(benchmark_registry))
    mapping_errors.extend(validate_investable_vehicle_mapping_completeness(vehicle_registry))
    if mapping_errors:
        raise ValueError("WP-04 foundation blocked by registry mapping errors: " + "; ".join(mapping_errors))

    rows: Sequence[AnalyticalUniverseRow] = build_analytical_universe_rows_from_current(
        run_id=run_id,
        snapshot_date=snapshot_date,
        benchmark_registry=benchmark_registry,
        vehicle_registry=vehicle_registry,
        current_root=current_root,
    )
    universe_errors = validate_analytical_universe_required_fields(rows)
    if universe_errors:
        raise ValueError("WP-04 foundation blocked by analytical universe errors: " + "; ".join(universe_errors))

    written_rows = write_analytical_universe_rows(
        rows=rows,
        snapshot_date=snapshot_date,
        run_id=run_id,
        current_root=current_root,
        history_root=analytical_history_root,
    )

    replay_start, replay_end = _resolve_history_window(
        snapshot_date=snapshot_date,
        start_date=start_date,
        end_date=end_date,
    )
    window_errors = validate_historical_replay_window(start_date=replay_start, end_date=replay_end)
    if window_errors:
        raise ValueError("Replay window invalid: " + "; ".join(window_errors))

    selection, filtered_rows = select_top_n_replay(
        analytical_rows=rows,
        start_date=replay_start,
        end_date=replay_end,
        analytical_snapshot_date=snapshot_date,
        market_cap_bucket=filter_market_cap_bucket,
        geography=filter_geography,
        industry=filter_industry,
        top_n=top_n,
        replay_id_suffix=run_id,
        filter_analytical_subtier=filter_analytical_subtier,
    )

    lookahead_errors = validate_replay_no_lookahead(selection, filtered_rows)
    reproducibility_errors = validate_top_n_selection_reproducibility(selection, filtered_rows)
    if lookahead_errors or reproducibility_errors:
        raise ValueError(
            "WP-04 foundation blocked by replay validation errors: "
            + "; ".join(lookahead_errors + reproducibility_errors)
        )

    benchmark, vehicle = resolve_category_mapping(
        geography=selection.filter_geography,
        market_cap_bucket=selection.filter_market_cap_bucket,
        industry_scope="ALL",  # Benchmark/vehicle assignments are market-cap based, not sector-specific.
        benchmark_registry=benchmark_registry,
        vehicle_registry=vehicle_registry,
    )

    # Build a single shared provider stack so replay series and persisted contracts use
    # the same deterministic source rows.
    shared_historical_provider = historical_price_provider
    if shared_historical_provider is None:
        shared_historical_provider = YahooHistoricalPriceProvider()

    if include_stock_curves:
        resolved_security_provider = security_price_provider or shared_historical_provider
    else:
        resolved_security_provider = security_price_provider or NullSecurityPriceHistoryProvider()

    resolved_benchmark_return_provider = benchmark_return_provider
    if resolved_benchmark_return_provider is None:
        resolved_benchmark_return_provider = YahooBenchmarkProvider(shared_historical_provider)

    resolved_vehicle_return_provider = investable_vehicle_return_provider
    if resolved_vehicle_return_provider is None:
        resolved_vehicle_return_provider = YahooInvestableVehicleProvider(shared_historical_provider)

    resolved_benchmark_provider = benchmark_provider or resolved_benchmark_return_provider
    resolved_vehicle_provider = vehicle_provider or resolved_vehicle_return_provider

    required_symbols = sorted({row.symbol for row in filtered_rows}) if include_stock_curves else []
    symbol_metadata = {row.symbol: row for row in filtered_rows}

    historical_price_rows = []
    for symbol in required_symbols:
        template = symbol_metadata[symbol]
        historical_price_rows.extend(
            shared_historical_provider.get_historical_prices(
                security_id=template.security_id,
                symbol=template.symbol,
                security_type=template.security_type,
                start_date=replay_start,
                end_date=replay_end,
            )
        )

    if include_stock_curves:
        price_errors = validate_historical_price_rows(historical_price_rows)
        if price_errors:
            raise ValueError("WP-05 foundation blocked by historical price errors: " + "; ".join(price_errors))

        coverage_warnings = validate_price_coverage(required_symbols, historical_price_rows)
        security_price_persistence = persist_security_prices(rows=historical_price_rows)
    else:
        coverage_warnings = [
            "Stock/full-universe historical curves are unavailable in WP-05A; benchmark and ETF curves only."
        ]
        security_price_persistence = {
            "status": "unavailable",
            "reason": "WP-05A only supports benchmark and investable vehicle curves.",
        }

    benchmark_return_rows = list(
        resolved_benchmark_return_provider.get_benchmark_returns(
            benchmark_id=benchmark.benchmark_id,
            symbol_or_index=benchmark.symbol_or_index,
            start_date=replay_start,
            end_date=replay_end,
        )
    )
    benchmark_errors = validate_benchmark_return_rows(benchmark_return_rows)
    benchmark_errors.extend(validate_benchmark_history_presence(benchmark.benchmark_id, benchmark_return_rows))
    benchmark_errors.extend(
        validate_curve_depth(
            curve_name=f"benchmark:{benchmark.benchmark_id}",
            point_count=len(benchmark_return_rows),
            minimum_points=2,
        )
    )
    if benchmark_errors:
        raise ValueError("WP-05 foundation blocked by benchmark return errors: " + "; ".join(benchmark_errors))
    benchmark_return_persistence = persist_benchmark_returns(rows=benchmark_return_rows)

    vehicle_return_rows = list(
        resolved_vehicle_return_provider.get_investable_vehicle_returns(
            vehicle_id=vehicle.vehicle_id,
            symbol=vehicle.symbol,
            start_date=replay_start,
            end_date=replay_end,
        )
    )
    vehicle_errors = validate_investable_vehicle_return_rows(vehicle_return_rows)
    vehicle_errors.extend(validate_vehicle_history_presence(vehicle.vehicle_id, vehicle_return_rows))
    vehicle_errors.extend(
        validate_curve_depth(
            curve_name=f"investable_vehicle:{vehicle.vehicle_id}",
            point_count=len(vehicle_return_rows),
            minimum_points=2,
        )
    )
    if vehicle_errors:
        raise ValueError("WP-05 foundation blocked by vehicle return errors: " + "; ".join(vehicle_errors))
    vehicle_return_persistence = persist_investable_vehicle_returns(rows=vehicle_return_rows)

    # Phase D/E: Build stock curves (WP-05D)
    # Wrapped in try/except: stock curve failures must NOT prevent BENCHMARK and
    # INVESTABLE_VEHICLE series from being written.  Any exception degrades the
    # stock curve to None (null-provider fallback) and records a warning.
    full_universe_curve_result = None
    top_n_curve_result = None
    if include_stock_curves:
        try:
            full_universe_curve_result = build_full_universe_curve(
                universe_rows=filtered_rows,
                start_date=replay_start,
                end_date=replay_end,
                provider=shared_historical_provider,
                filter_geography=selection.filter_geography,
                filter_market_cap_bucket=selection.filter_market_cap_bucket,
                filter_industry=selection.filter_industry,
                coverage_threshold=FULL_UNIVERSE_COVERAGE_THRESHOLD,
                max_symbols=500,
            )
        except Exception as _fu_exc:
            coverage_warnings.append(f"FULL_UNIVERSE curve build failed (degraded to null): {_fu_exc}")
        try:
            top_n_curve_result = build_top_n_curve(
                selection=selection,
                provider=shared_historical_provider,
                coverage_threshold=TOP_N_COVERAGE_THRESHOLD,
            )
        except Exception as _tn_exc:
            coverage_warnings.append(f"TOP_N_STRATEGY curve build failed (degraded to null): {_tn_exc}")

    performance_rows = build_performance_series(
        selection=selection,
        full_universe_rows=filtered_rows,
        benchmark_symbol_or_index=benchmark.symbol_or_index,
        investable_vehicle_symbol=vehicle.symbol,
        security_price_provider=resolved_security_provider,
        benchmark_provider=resolved_benchmark_provider,
        vehicle_provider=resolved_vehicle_provider,
        full_universe_curve_result=full_universe_curve_result if include_stock_curves else None,
        top_n_curve_result=top_n_curve_result if include_stock_curves else None,
    )

    performance_errors = validate_performance_series_shape(
        [asdict(row) for row in performance_rows],
        replay_id=selection.replay_id,
    )
    if performance_errors:
        raise ValueError("WP-05 foundation blocked by performance series errors: " + "; ".join(performance_errors))

    no_lookahead_errors = validate_no_lookahead_series_dates(
        start_date=replay_start,
        end_date=replay_end,
        series_dates=[row.date for row in performance_rows],
    )
    if no_lookahead_errors:
        raise ValueError("WP-05 foundation blocked by no-lookahead violations: " + "; ".join(no_lookahead_errors))

    output_paths = persist_replay_outputs(
        selection=selection,
        performance_series=performance_rows,
        current_root=current_root,
        history_root=replay_history_root,
        benchmark_symbol_or_index=benchmark.symbol_or_index,
        investable_vehicle_symbol=vehicle.symbol,
    )

    # Phase G: write evidence summary into the replay partition directory
    evidence_summary = build_replay_evidence_summary(
        selection=selection,
        benchmark_symbol=benchmark.symbol_or_index,
        investable_vehicle_symbol=vehicle.symbol,
        full_universe_symbol_count=len({row.symbol for row in filtered_rows}),
        full_universe_curve_result=full_universe_curve_result if include_stock_curves else None,
        top_n_curve_result=top_n_curve_result if include_stock_curves else None,
        performance_series=performance_rows,
    )
    replay_dir = Path(str(output_paths["replay_metadata_path"])).parent
    evidence_path = write_replay_evidence_summary(replay_dir=replay_dir, summary=evidence_summary)
    output_paths["replay_evidence_summary_path"] = str(evidence_path)

    return {
        "written_analytical_universe_rows": written_rows,
        "selection": asdict(selection),
        "performance_row_count": len(performance_rows),
        "benchmark_id": benchmark.benchmark_id,
        "vehicle_id": vehicle.vehicle_id,
        "coverage_warnings": coverage_warnings,
        "stock_curves": {
            "full_universe_status": full_universe_curve_result.coverage_status if include_stock_curves and full_universe_curve_result else "NOT_REQUESTED",
            "top_n_status": top_n_curve_result.coverage_status if include_stock_curves and top_n_curve_result else "NOT_REQUESTED",
        },
        "market_data_persistence": {
            "security_prices": security_price_persistence,
            "benchmark_returns": benchmark_return_persistence,
            "investable_vehicle_returns": vehicle_return_persistence,
        },
        "output_paths": output_paths,
    }


def build_wp05b_replay_matrix(
    *,
    run_id: str,
    snapshot_date: str,
    start_date: str | None = None,
    end_date: str | None = None,
    top_n: int = 20,
    filter_analytical_subtier: str | None = None,
    filter_industry: str = "ALL",
    current_root: str | Path = "data/current",
    analytical_history_root: str | Path = "data/history/analytical_universe",
    replay_history_root: str | Path = "data/history/replays",
    snapshot_registry_root: str | Path = "data/history",
    benchmark_registry_path: str | Path = "config/benchmark_category_registry.yaml",
    vehicle_registry_path: str | Path = "config/investable_vehicle_registry.yaml",
    historical_price_provider: HistoricalPriceProvider | None = None,
    benchmark_return_provider: BenchmarkReturnProvider | None = None,
    investable_vehicle_return_provider: InvestableVehicleReturnProvider | None = None,
) -> Dict[str, Any]:
    """Generate WP-05B/C replay coverage matrix with atomic current publication.

    Phase C: all writes to current/ are staged in current/.tmp/ first, validated,
    then atomically swapped to current/ using os.replace(). On failure current/
    is left unchanged and .tmp/ is cleaned up.

    Phase B: after successful publication, one row is appended to each snapshot
    registry file in data/history/.

    Phase D: symbol validation uses only the YAML registries as the single source
    of truth — no WP05B_REQUIRED_* constants.
    """
    benchmark_registry = load_benchmark_category_registry(path=benchmark_registry_path)
    vehicle_registry = load_investable_vehicle_registry(path=vehicle_registry_path)

    mapping_errors: List[str] = []
    mapping_errors.extend(validate_benchmark_mapping_completeness(benchmark_registry))
    mapping_errors.extend(validate_investable_vehicle_mapping_completeness(vehicle_registry))
    if mapping_errors:
        raise ValueError("WP-05B replay matrix blocked by mapping validation errors: " + "; ".join(mapping_errors))

    generated_at = datetime.now(timezone.utc).isoformat()

    # When a specific industry is requested, replace "ALL" in the scope with that industry.
    industry_filter = filter_industry.upper() if filter_industry else "ALL"
    if industry_filter == "ALL":
        active_scope = WP05B_UI_CATEGORY_SCOPE
        active_gen_scope = WP05B_REPLAY_GENERATION_SCOPE
    else:
        active_scope = tuple(
            (geo, bucket, industry_filter)
            for geo, bucket, _industry in WP05B_UI_CATEGORY_SCOPE
        )
        active_gen_scope = tuple(
            (geo, bucket, industry_filter)
            for geo, bucket, _industry in WP05B_REPLAY_GENERATION_SCOPE
        )

    scope_set = {(geo, bucket, industry) for geo, bucket, industry in active_gen_scope}

    availability_rows: List[Dict[str, object]] = []
    matrix_rows: List[Dict[str, object]] = []
    combined_inputs_rows: List[Dict[str, str]] = []
    combined_series_rows: List[Dict[str, str]] = []
    replay_snapshot_registry_rows: List[Dict[str, object]] = []

    current_root_path = Path(current_root)
    tmp_root = current_root_path / ".tmp"

    # Merge strategy: preserve rows for other industries from an existing current build.
    # When industry_filter == "ALL" this preserves nothing (full rebuild).
    # When industry_filter == "TECHNOLOGY" it keeps ALL + other sector rows intact.
    _existing_inputs_path = current_root_path / "replay_inputs.csv"
    _existing_series_path = current_root_path / "replay_performance_series.csv"
    _existing_availability_path = current_root_path / "replay_availability.csv"
    _existing_matrix_path = current_root_path / "replay_matrix.csv"
    preserved_inputs_rows: List[Dict[str, str]] = []
    preserved_series_rows: List[Dict[str, str]] = []
    preserved_availability_rows: List[Dict[str, str]] = []
    preserved_matrix_rows: List[Dict[str, str]] = []
    if _existing_inputs_path.exists():
        _all_existing_inputs = _read_csv_rows(_existing_inputs_path)
        preserved_inputs_rows = [
            r for r in _all_existing_inputs
            if str(r.get("filter_industry", "")).upper() != industry_filter
        ]
        _surviving_replay_ids = {str(r.get("replay_id", "")) for r in preserved_inputs_rows}
        if _existing_series_path.exists():
            preserved_series_rows = [
                r for r in _read_csv_rows(_existing_series_path)
                if str(r.get("replay_id", "")) in _surviving_replay_ids
            ]
    if _existing_availability_path.exists():
        preserved_availability_rows = [
            r for r in _read_csv_rows(_existing_availability_path)
            if str(r.get("industry", "")).upper() != industry_filter
        ]
    if _existing_matrix_path.exists():
        preserved_matrix_rows = [
            r for r in _read_csv_rows(_existing_matrix_path)
            if str(r.get("industry", "")).upper() != industry_filter
        ]

    # Phase C: clear any stale .tmp from a prior interrupted run before starting
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)

    # Shared provider instances: benchmark and vehicle data are cached in-memory
    # across all categories so each benchmark/ETF symbol is fetched only once,
    # preventing Yahoo Finance rate-limiting on large all-universe builds.
    _shared_historical = historical_price_provider or YahooHistoricalPriceProvider()
    _shared_benchmark_return = benchmark_return_provider or YahooBenchmarkProvider(_shared_historical)
    _shared_vehicle_return = investable_vehicle_return_provider or YahooInvestableVehicleProvider(_shared_historical)

    try:
        for geography, market_cap_bucket, industry in active_scope:
            benchmark_mapped = False
            vehicle_mapped = False
            resolved_benchmark_id = ""
            resolved_vehicle_id = ""
            missing_deps: List[str] = []
            cat_status = "NOT_GENERATED"
            replay_generated = False
            cat_replay_id = ""
            cat_replay_mode = "HISTORICAL_VALIDATION"
            stock_replay_available_flag = False
            top_n_available_flag = False

            try:
                benchmark, vehicle = resolve_category_mapping(
                    geography=geography,
                    market_cap_bucket=market_cap_bucket,
                    industry_scope="ALL",  # Benchmark/vehicle assignments are market-cap based.
                    benchmark_registry=benchmark_registry,
                    vehicle_registry=vehicle_registry,
                )
                benchmark_mapped = bool(benchmark.benchmark_id)
                vehicle_mapped = bool(vehicle.vehicle_id)
                resolved_benchmark_id = benchmark.benchmark_id
                resolved_vehicle_id = vehicle.vehicle_id
            except ValueError as exc:
                cat_status = "MISSING_MAPPING"
                missing_deps.append(str(exc))

            key = (geography, market_cap_bucket, industry)
            if cat_status != "MISSING_MAPPING" and key not in scope_set:
                cat_status = "NOT_GENERATED"
                missing_deps.append("Out of WP-05B replay generation scope.")
            elif cat_status != "MISSING_MAPPING":
                category_run_id = f"{run_id}-{geography}-{market_cap_bucket}-{industry}".replace(" ", "_")
                try:
                    result = build_wp04_foundation(
                        run_id=category_run_id,
                        snapshot_date=snapshot_date,
                        filter_market_cap_bucket=market_cap_bucket,
                        filter_geography=geography,
                        filter_industry=industry,
                        filter_analytical_subtier=filter_analytical_subtier,
                        top_n=top_n,
                        current_root=current_root_path,
                        analytical_history_root=analytical_history_root,
                        replay_history_root=replay_history_root,
                        benchmark_registry_path=benchmark_registry_path,
                        vehicle_registry_path=vehicle_registry_path,
                        start_date=start_date,
                        end_date=end_date,
                        historical_price_provider=_shared_historical,
                        benchmark_return_provider=_shared_benchmark_return,
                        investable_vehicle_return_provider=_shared_vehicle_return,
                        include_stock_curves=True,
                    )

                    output_paths = result["output_paths"]
                    cat_replay_id = str(result["selection"]["replay_id"])
                    cat_replay_mode = str(result["selection"].get("replay_mode", "HISTORICAL_VALIDATION"))
                    replay_selection_rows = _read_csv_rows(Path(str(output_paths["replay_selection_path"])))
                    replay_series_rows = _read_csv_rows(Path(str(output_paths["replay_series_path"])))
                    combined_inputs_rows.extend(replay_selection_rows)
                    combined_series_rows.extend(replay_series_rows)

                    series_types = {str(row.get("series_type", "")).upper() for row in replay_series_rows}
                    benchmark_available = "BENCHMARK" in series_types
                    vehicle_available = "INVESTABLE_VEHICLE" in series_types
                    stock_replay_available_flag = "FULL_UNIVERSE" in series_types
                    top_n_available_flag = "TOP_N_STRATEGY" in series_types
                    replay_generated = bool(replay_series_rows)

                    if replay_generated and benchmark_available and vehicle_available:
                        cat_status = "AVAILABLE"
                    elif replay_generated and (benchmark_available or vehicle_available):
                        cat_status = "PARTIAL"
                    else:
                        cat_status = "MISSING_MARKET_DATA"

                    if not benchmark_available:
                        missing_deps.append("Benchmark curve unavailable.")
                    if not vehicle_available:
                        missing_deps.append("ETF/fund curve unavailable.")
                    if not stock_replay_available_flag:
                        missing_deps.append("Full-universe stock curve unavailable.")
                    if not top_n_available_flag:
                        missing_deps.append("Top-N strategy curve unavailable.")

                    evidence_summary_path_str = output_paths.get("replay_evidence_summary_path", "")
                    replay_dir = Path(str(output_paths["replay_metadata_path"])).parent
                    replay_availability_payload = {
                        "replay_id": cat_replay_id,
                        "geography": geography,
                        "market_cap_bucket": market_cap_bucket,
                        "industry": industry,
                        "benchmark_available": benchmark_available,
                        "vehicle_available": vehicle_available,
                        "stock_replay_available": stock_replay_available_flag,
                        "top_n_available": top_n_available_flag,
                        "replay_generated": replay_generated,
                        "replay_status": cat_status,
                        "missing_dependencies": " | ".join(missing_deps),
                        "generated_at_utc": generated_at,
                    }
                    replay_availability_path = replay_dir / "replay_availability.json"
                    replay_availability_path.write_text(
                        json.dumps(replay_availability_payload, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )

                    matrix_rows.append(
                        {
                            "replay_id": cat_replay_id,
                            "geography": geography,
                            "market_cap_bucket": market_cap_bucket,
                            "industry": industry,
                            "replay_status": cat_status,
                            "benchmark_id": resolved_benchmark_id,
                            "vehicle_id": resolved_vehicle_id,
                            "performance_row_count": len(replay_series_rows),
                            "replay_selection_path": output_paths["replay_selection_path"],
                            "replay_series_path": output_paths["replay_series_path"],
                            "replay_metadata_path": output_paths["replay_metadata_path"],
                            "replay_availability_path": str(replay_availability_path),
                            "replay_evidence_summary_path": evidence_summary_path_str,
                            "generated_at_utc": generated_at,
                        }
                    )
                except Exception as exc:
                    cat_status = _classify_replay_failure(str(exc))
                    missing_deps.append(str(exc))
                    evidence_summary_path_str = ""

            availability_rows.append(
                {
                    "geography": geography,
                    "market_cap_bucket": market_cap_bucket,
                    "industry": industry,
                    "benchmark_available": _as_bool_text(
                        benchmark_mapped and cat_status in {"AVAILABLE", "PARTIAL"}
                    ),
                    "vehicle_available": _as_bool_text(
                        vehicle_mapped and cat_status in {"AVAILABLE", "PARTIAL"}
                    ),
                    "stock_replay_available": _as_bool_text(stock_replay_available_flag if replay_generated else False),
                    "top_n_available": _as_bool_text(top_n_available_flag if replay_generated else False),
                    "replay_generated": _as_bool_text(replay_generated),
                    "replay_status": cat_status,
                    "missing_dependencies": " | ".join(missing_deps),
                    "generated_at_utc": generated_at,
                }
            )

            # Phase B: collect replay snapshot registry row for generated categories
            if replay_generated and cat_replay_id:
                replay_snapshot_registry_rows.append(
                    {
                        "replay_id": cat_replay_id,
                        "snapshot_date": snapshot_date,
                        "start_date": start_date or "",
                        "end_date": end_date or "",
                        "geography": geography,
                        "market_cap_bucket": market_cap_bucket,
                        "industry": industry,
                        "benchmark_available": _as_bool_text(
                            benchmark_mapped and cat_status in {"AVAILABLE", "PARTIAL"}
                        ),
                        "vehicle_available": _as_bool_text(
                            vehicle_mapped and cat_status in {"AVAILABLE", "PARTIAL"}
                        ),
                        "stock_replay_available": _as_bool_text(stock_replay_available_flag if replay_generated else False),
                        "top_n_available": _as_bool_text(top_n_available_flag if replay_generated else False),
                        "replay_status": cat_status,
                        "replay_mode": cat_replay_mode,
                        "generated_at_utc": generated_at,
                    }
                )

        # --- post-loop validation ---
        availability_errors = validate_replay_availability_consistency(availability_rows)
        availability_errors.extend(
            validate_unsupported_category_exposure(
                availability_rows,
                supported_categories=active_gen_scope,
            )
        )
        matrix_errors = validate_empty_replay_outputs(matrix_rows)
        matrix_errors.extend(
            validate_orphaned_replay_metadata(
                matrix_rows,
                history_root=replay_history_root,
                replay_id_prefix=run_id,
            )
        )
        matrix_errors.extend(validate_replay_ui_mismatch(matrix_rows, combined_inputs_rows))

        if availability_errors or matrix_errors:
            raise ValueError(
                "WP-05B replay matrix validation failed: "
                + "; ".join(availability_errors + matrix_errors)
            )

        # Phase C: write all combined outputs to .tmp/ then atomic swap to current/
        _write_csv(tmp_root / "replay_availability.csv", REPLAY_AVAILABILITY_HEADERS,
                   preserved_availability_rows + availability_rows)
        _write_csv(tmp_root / "replay_matrix.csv", REPLAY_MATRIX_HEADERS,
                   preserved_matrix_rows + matrix_rows)
        _write_csv(tmp_root / "replay_inputs.csv", REPLAY_SELECTION_HEADERS,
                   preserved_inputs_rows + combined_inputs_rows)
        _write_csv(
            tmp_root / "replay_performance_series.csv", PERFORMANCE_SERIES_HEADERS,
            preserved_series_rows + combined_series_rows
        )

        _atomic_publish_current_outputs(tmp_root, current_root_path)

        # Phase H: write freshness metadata directly to current/ (small JSON, safe post-swap)
        freshness_status = "FRESH"
        _write_current_snapshot_metadata(
            current_root_path,
            snapshot_date=snapshot_date,
            run_id=run_id,
            generated_at_utc=generated_at,
            source_snapshot_date=snapshot_date,
            freshness_status=freshness_status,
        )

        # Phase B: compute summary counts, then append to snapshot registries
        status_counts: Dict[str, int] = {}
        for avail_row in availability_rows:
            k = str(avail_row.get("replay_status", ""))
            status_counts[k] = status_counts.get(k, 0) + 1

        available_count = status_counts.get("AVAILABLE", 0)
        total_categories = len(WP05B_UI_CATEGORY_SCOPE)
        if available_count == total_categories:
            coverage_status = "FULL"
        elif available_count > 0:
            coverage_status = "PARTIAL"
        else:
            coverage_status = "NONE"

        snapshot_registry_root_path = Path(snapshot_registry_root)
        analytical_registry_row: Dict[str, object] = {
            "snapshot_date": snapshot_date,
            "run_id": run_id,
            "created_at_utc": generated_at,
            "analytical_universe_rows": len(combined_inputs_rows),
            "replay_count": len(matrix_rows),
            "replay_coverage_status": coverage_status,
            "benchmark_count": len(
                {str(r.get("benchmark_id", "")) for r in matrix_rows if r.get("benchmark_id")}
            ),
            "vehicle_count": len(
                {str(r.get("vehicle_id", "")) for r in matrix_rows if r.get("vehicle_id")}
            ),
            "generation_status": "COMPLETE",
        }
        _append_to_registry(
            path=snapshot_registry_root_path / "analytical_snapshot_registry.csv",
            headers=ANALYTICAL_SNAPSHOT_REGISTRY_HEADERS,
            row=analytical_registry_row,
        )
        for registry_row in replay_snapshot_registry_rows:
            _append_to_registry(
                path=snapshot_registry_root_path / "replay_snapshot_registry.csv",
                headers=REPLAY_SNAPSHOT_REGISTRY_HEADERS,
                row=registry_row,
            )

        return {
            "matrix_row_count": len(matrix_rows),
            "availability_row_count": len(availability_rows),
            "generated_category_scope": [f"{geo}/{bucket}/{ind}" for geo, bucket, ind in active_gen_scope],
            "status_counts": status_counts,
            "snapshot_date": snapshot_date,
            "run_id": run_id,
            "freshness_status": freshness_status,
            "current_outputs": {
                "replay_matrix": str(current_root_path / "replay_matrix.csv"),
                "replay_availability": str(current_root_path / "replay_availability.csv"),
                "replay_inputs": str(current_root_path / "replay_inputs.csv"),
                "replay_performance_series": str(current_root_path / "replay_performance_series.csv"),
                "current_snapshot_metadata": str(
                    current_root_path / "current_snapshot_metadata.json"
                ),
            },
        }

    finally:
        # Phase C: always clean up .tmp/ whether the build succeeded or failed
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)

