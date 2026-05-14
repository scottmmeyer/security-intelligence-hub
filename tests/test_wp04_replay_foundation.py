from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from src.history.analytical_universe_manager import (
    ANALYTICAL_UNIVERSE_HEADERS,
    build_analytical_universe_rows_from_current,
    write_analytical_universe_rows,
)
from src.history.base_universe_manager import BASE_UNIVERSE_HEADERS
from src.history.signal_snapshot_manager import SNAPSHOT_HEADERS
from src.models.analytical_models import AnalyticalUniverseRow
from src.replay.history_providers import PricePoint
from src.replay.registry_loader import (
    load_benchmark_category_registry,
    load_investable_vehicle_registry,
    resolve_category_mapping,
)
from src.replay.replay_engine import (
    build_performance_series,
    persist_replay_outputs,
    select_top_n_replay,
)
from src.validation.replay_validator import (
    validate_analytical_universe_required_fields,
    validate_benchmark_mapping_completeness,
    validate_investable_vehicle_mapping_completeness,
    validate_performance_series_shape,
    validate_replay_no_lookahead,
    validate_top_n_selection_reproducibility,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class _FakeSecurityProvider:
    def get_symbol_series(self, symbol: str, start_date: str, end_date: str):
        return [
            PricePoint(date="2026-05-13", value=100.0),
            PricePoint(date="2026-05-14", value=101.0 if symbol == "AAA" else 99.0),
        ]


class _FakeBenchmarkProvider:
    def get_benchmark_series(self, benchmark_symbol_or_index: str, start_date: str, end_date: str):
        return [
            PricePoint(date="2026-05-13", value=200.0),
            PricePoint(date="2026-05-14", value=202.0),
        ]


class _FakeVehicleProvider:
    def get_vehicle_series(self, symbol: str, start_date: str, end_date: str):
        return [
            PricePoint(date="2026-05-13", value=300.0),
            PricePoint(date="2026-05-14", value=303.0),
        ]


def _row(symbol: str, score: float, *, snapshot_date: str = "2026-05-13") -> AnalyticalUniverseRow:
    return AnalyticalUniverseRow(
        security_id=f"FIDELITY:{symbol}",
        symbol=symbol,
        security_type="Common Stock",
        snapshot_date=snapshot_date,
        run_id="RUN-REPLAY-001",
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
        provider_lineage="provider=FIDELITY;source_file=test.csv",
    )


def test_registry_loading_and_completeness_validation() -> None:
    benchmark_registry = load_benchmark_category_registry()
    vehicle_registry = load_investable_vehicle_registry()

    assert validate_benchmark_mapping_completeness(benchmark_registry) == []
    assert validate_investable_vehicle_mapping_completeness(vehicle_registry) == []


def test_category_to_benchmark_mapping_resolution() -> None:
    benchmark_registry = load_benchmark_category_registry()
    vehicle_registry = load_investable_vehicle_registry()

    benchmark, _ = resolve_category_mapping(
        geography="US",
        market_cap_bucket="LARGE",
        industry_scope="ALL",
        benchmark_registry=benchmark_registry,
        vehicle_registry=vehicle_registry,
    )

    assert benchmark.benchmark_id == "BM_US_LARGE_SP500"
    assert benchmark.symbol_or_index == "^GSPC"


def test_category_to_investable_vehicle_mapping_resolution() -> None:
    benchmark_registry = load_benchmark_category_registry()
    vehicle_registry = load_investable_vehicle_registry()

    _, vehicle = resolve_category_mapping(
        geography="US",
        market_cap_bucket="MID",
        industry_scope="ALL",
        benchmark_registry=benchmark_registry,
        vehicle_registry=vehicle_registry,
    )

    assert vehicle.vehicle_id == "VEH_US_MID_MDY"
    assert vehicle.symbol == "MDY"


def test_analytical_universe_row_creation_and_write(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    history_root = tmp_path / "data" / "history" / "analytical_universe"

    _write_csv(
        current_root / "base_equity_universe.csv",
        BASE_UNIVERSE_HEADERS,
        [
            {
                "symbol": "AAA",
                "company_name": "AAA Corp",
                "security_type": "Common Stock",
                "geography": "US",
                "market_cap_raw_usd": "12000000000",
                "market_cap_bucket": "LARGE",
                "coverage_domain": "STARMINE_COVERED",
                "starmine_ess_text": "BULLISH",
                "provider": "FIDELITY",
                "source_file": "fixture.csv",
                "snapshot_date": "2026-05-13",
                "created_at_utc": "2026-05-13T00:00:00+00:00",
                "run_id": "RUN-REPLAY-001",
            }
        ],
    )

    _write_csv(
        current_root / "signal_snapshot.csv",
        SNAPSHOT_HEADERS,
        [
            {
                "snapshot_date": "2026-05-13",
                "created_at_utc": "2026-05-13T00:00:00+00:00",
                "run_id": "RUN-REPLAY-001",
                "provider": "FIDELITY",
                "source_file": "fixture.csv",
                "symbol": "AAA",
                "coverage_domain": "STARMINE_COVERED",
                "signal_coverage_status": "COVERED",
                "starmine_ess_text": "BULLISH",
                "starmine_ess_numeric": "4.0",
                "starmine_ess_numeric_estimated": "True",
                "starmine_ess_source_type": "TEXT_MAPPED",
            }
        ],
    )

    benchmark_registry = load_benchmark_category_registry()
    vehicle_registry = load_investable_vehicle_registry()

    rows = build_analytical_universe_rows_from_current(
        run_id="RUN-REPLAY-001",
        snapshot_date="2026-05-13",
        benchmark_registry=benchmark_registry,
        vehicle_registry=vehicle_registry,
        current_root=current_root,
        watchlist_path=tmp_path / "no_watchlist.csv",  # isolate test from real watchlist
    )

    assert len(rows) == 1
    assert validate_analytical_universe_required_fields(rows) == []

    written_count = write_analytical_universe_rows(
        rows=rows,
        snapshot_date="2026-05-13",
        run_id="RUN-REPLAY-001",
        current_root=current_root,
        history_root=history_root,
    )
    assert written_count == 1

    output_path = current_root / "analytical_universe.csv"
    assert output_path.exists()
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        output_rows = list(reader)
    assert reader.fieldnames == ANALYTICAL_UNIVERSE_HEADERS
    assert output_rows[0]["benchmark_id"] == "BM_US_LARGE_SP500"


def test_top_n_replay_selection_is_reproducible() -> None:
    rows = [_row("AAA", 3.4), _row("BBB", 4.2), _row("CCC", 4.2)]

    selection, filtered_rows = select_top_n_replay(
        analytical_rows=rows,
        start_date="2026-05-13",
        end_date="2027-05-13",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=2,
    )

    assert list(selection.selected_symbols) == ["BBB", "CCC"]
    assert validate_top_n_selection_reproducibility(selection, filtered_rows) == []


def test_replay_no_lookahead_enforcement() -> None:
    rows = [_row("AAA", 3.4, snapshot_date="2026-05-14")]
    selection = select_top_n_replay(
        analytical_rows=[_row("AAA", 3.4)],
        start_date="2026-05-13",
        end_date="2027-05-13",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=1,
    )[0]

    errors = validate_replay_no_lookahead(selection, rows)
    assert any("no-lookahead" in message.lower() for message in errors)


def test_performance_series_contract_generation_and_persistence(tmp_path: Path) -> None:
    rows = [_row("AAA", 4.0), _row("BBB", 3.8)]
    selection, filtered_rows = select_top_n_replay(
        analytical_rows=rows,
        start_date="2026-05-13",
        end_date="2026-05-14",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=2,
    )

    series = build_performance_series(
        selection=selection,
        full_universe_rows=filtered_rows,
        benchmark_symbol_or_index="^GSPC",
        investable_vehicle_symbol="SPY",
        security_price_provider=_FakeSecurityProvider(),
        benchmark_provider=_FakeBenchmarkProvider(),
        vehicle_provider=_FakeVehicleProvider(),
    )

    series_rows = [asdict(item) for item in series]
    assert validate_performance_series_shape(series_rows, replay_id=selection.replay_id) == []

    paths = persist_replay_outputs(
        selection=selection,
        performance_series=series,
        current_root=tmp_path / "data" / "current",
        history_root=tmp_path / "data" / "history" / "replays",
        benchmark_symbol_or_index="^GSPC",
        investable_vehicle_symbol="SPY",
    )

    assert Path(paths["current_inputs_path"]).exists()
    assert Path(paths["current_series_path"]).exists()
    assert Path(paths["replay_metadata_path"]).exists()
