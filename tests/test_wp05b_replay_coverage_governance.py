from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.history.base_universe_manager import BASE_UNIVERSE_HEADERS
from src.history.signal_snapshot_manager import SNAPSHOT_HEADERS
from src.models.market_data_models import BenchmarkReturnRow, InvestableVehicleReturnRow
from src.replay.foundation_service import (
    build_wp05b_replay_matrix,
)
from src.replay.history_providers import PricePoint
from src.replay.registry_loader import (
    derive_benchmark_symbols_from_registry,
    derive_vehicle_symbols_from_registry,
    load_benchmark_category_registry,
    load_investable_vehicle_registry,
)
from src.validation.replay_validator import (
    validate_replay_availability_consistency,
    validate_unsupported_category_exposure,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class _StubBenchmarkProvider:
    def get_benchmark_returns(self, *, benchmark_id: str, symbol_or_index: str, start_date: str, end_date: str):
        del benchmark_id, symbol_or_index, start_date, end_date
        return [
            BenchmarkReturnRow("BM", "IDX", "2025-05-13", 100.0, 0.0, "TEST"),
            BenchmarkReturnRow("BM", "IDX", "2026-05-13", 110.0, 0.10, "TEST"),
        ]

    def get_benchmark_series(self, benchmark_symbol_or_index: str, start_date: str, end_date: str):
        del benchmark_symbol_or_index, start_date, end_date
        return [
            PricePoint(date="2025-05-13", value=100.0),
            PricePoint(date="2026-05-13", value=110.0),
        ]


class _StubVehicleProvider:
    def get_investable_vehicle_returns(self, *, vehicle_id: str, symbol: str, start_date: str, end_date: str):
        del vehicle_id, symbol, start_date, end_date
        return [
            InvestableVehicleReturnRow("VEH", "ETF", "2025-05-13", 100.0, 0.0, "TEST"),
            InvestableVehicleReturnRow("VEH", "ETF", "2026-05-13", 108.0, 0.08, "TEST"),
        ]

    def get_vehicle_series(self, symbol: str, start_date: str, end_date: str):
        del symbol, start_date, end_date
        return [
            PricePoint(date="2025-05-13", value=100.0),
            PricePoint(date="2026-05-13", value=108.0),
        ]


def _seed_current_inputs(current_root: Path) -> None:
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
                "snapshot_date": "2025-05-13",
                "created_at_utc": "2025-05-13T00:00:00+00:00",
                "run_id": "RUN-TEST",
            }
        ],
    )

    _write_csv(
        current_root / "signal_snapshot.csv",
        SNAPSHOT_HEADERS,
        [
            {
                "snapshot_date": "2025-05-13",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "run_id": "RUN-TEST",
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


def test_wp05b_matrix_generation_and_availability_contracts(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    replay_history_root = tmp_path / "data" / "history" / "replays"
    analytical_history_root = tmp_path / "data" / "history" / "analytical_universe"
    _seed_current_inputs(current_root)

    result = build_wp05b_replay_matrix(
        run_id="RUN-WP05B-UNIT",
        snapshot_date="2025-05-13",
        start_date="2025-05-13",
        end_date="2026-05-13",
        current_root=current_root,
        replay_history_root=replay_history_root,
        analytical_history_root=analytical_history_root,
        benchmark_return_provider=_StubBenchmarkProvider(),
        investable_vehicle_return_provider=_StubVehicleProvider(),
    )

    assert result["matrix_row_count"] == 10
    assert result["availability_row_count"] == 10
    assert (current_root / "replay_availability.csv").exists()
    assert (current_root / "replay_matrix.csv").exists()

    with (current_root / "replay_availability.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert any(
        row["geography"] == "INTERNATIONAL" and row["market_cap_bucket"] == "MEGA" and row["replay_status"] in {"AVAILABLE", "PARTIAL"}
        for row in rows
    )
    assert any(
        row["geography"] == "US" and row["market_cap_bucket"] == "LARGE" and row["replay_status"] in {"AVAILABLE", "PARTIAL"}
        for row in rows
    )


def test_wp05c_registry_derived_symbols_cover_all_active_categories() -> None:
    """Phase D: verify that benchmark and vehicle symbols derive correctly from registry YAML.

    The YAML registries are now the single source of truth for allowed symbols.
    No hardcoded frozensets in providers — this test confirms the derivation path
    produces a non-empty set that covers all active assigned symbols.
    """
    benchmark_registry = load_benchmark_category_registry()
    vehicle_registry = load_investable_vehicle_registry()

    benchmark_symbols = derive_benchmark_symbols_from_registry(benchmark_registry)
    vehicle_symbols = derive_vehicle_symbols_from_registry(vehicle_registry)

    assert len(benchmark_symbols) > 0, "No benchmark symbols derived from registry."
    assert len(vehicle_symbols) > 0, "No vehicle symbols derived from registry."

    # Every active assignment must resolve to a symbol in the derived set.
    for assignment in benchmark_registry.get("benchmark_assignments", []):
        if str(assignment.get("assignment_status", "")).upper() != "ACTIVE":
            continue
        bm_id = str(assignment.get("benchmark_id", ""))
        defs = {
            str(item.get("benchmark_id", "")): str(item.get("symbol_or_index", "")).upper()
            for item in benchmark_registry.get("benchmark_definitions", [])
            if isinstance(item, dict)
        }
        symbol = defs.get(bm_id, "")
        assert symbol in benchmark_symbols, (
            f"Active benchmark_id={bm_id!r} symbol {symbol!r} not in derived set."
        )

    for assignment in vehicle_registry.get("vehicle_assignments", []):
        if str(assignment.get("assignment_status", "")).upper() != "ACTIVE":
            continue
        veh_id = str(assignment.get("vehicle_id", ""))
        defs = {
            str(item.get("vehicle_id", "")): str(item.get("symbol", "")).upper()
            for item in vehicle_registry.get("investable_vehicles", [])
            if isinstance(item, dict)
        }
        symbol = defs.get(veh_id, "")
        assert symbol in vehicle_symbols, (
            f"Active vehicle_id={veh_id!r} symbol {symbol!r} not in derived set."
        )


def test_wp05b_availability_consistency_and_unsupported_exposure_validator() -> None:
    rows = [
        {
            "geography": "US",
            "market_cap_bucket": "LARGE",
            "industry": "ALL",
            "benchmark_available": "true",
            "vehicle_available": "true",
            "stock_replay_available": "false",
            "top_n_available": "false",
            "replay_generated": "true",
            "replay_status": "AVAILABLE",
            "missing_dependencies": "",
            "generated_at_utc": "2026-05-13T00:00:00+00:00",
        },
        {
            "geography": "INTERNATIONAL",
            "market_cap_bucket": "MEGA",
            "industry": "ALL",
            "benchmark_available": "false",
            "vehicle_available": "false",
            "stock_replay_available": "false",
            "top_n_available": "false",
            "replay_generated": "false",
            "replay_status": "NOT_GENERATED",
            "missing_dependencies": "Out of scope",
            "generated_at_utc": "2026-05-13T00:00:00+00:00",
        },
    ]

    assert validate_replay_availability_consistency(rows) == []
    assert validate_unsupported_category_exposure(
        rows,
        supported_categories=(("US", "LARGE", "ALL"),),
    ) == []
