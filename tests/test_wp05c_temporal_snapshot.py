"""WP-05C temporal snapshot architecture tests.

Tests covering:
  Phase A — snapshot-date-partitioned history directories
  Phase B — snapshot registry append semantics
  Phase C — atomic current publication and rollback
  Phase D — single-source registry derivation
  Phase E — temporal validation hardening
  Phase F — replay mode detection and consistency
  Phase G — expanded coverage states (FAILED, STALE)
  Phase H — freshness metadata contract
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta, timezone
from pathlib import Path

import pytest

from src.history.base_universe_manager import BASE_UNIVERSE_HEADERS
from src.history.signal_snapshot_manager import SNAPSHOT_HEADERS
from src.models.analytical_models import ReplayMode
from src.models.market_data_models import BenchmarkReturnRow, InvestableVehicleReturnRow
from src.replay.foundation_service import (
    ANALYTICAL_SNAPSHOT_REGISTRY_HEADERS,
    REPLAY_SNAPSHOT_REGISTRY_HEADERS,
    build_wp05b_replay_matrix,
    _atomic_publish_current_outputs,
    _append_to_registry,
    _write_current_snapshot_metadata,
)
from src.replay.history_providers import PricePoint
from src.replay.registry_loader import (
    derive_benchmark_symbols_from_registry,
    derive_vehicle_symbols_from_registry,
    load_benchmark_category_registry,
    load_investable_vehicle_registry,
)
from src.replay.replay_engine import detect_replay_mode
from src.validation.replay_validator import (
    REPLAY_STATUS_ENUM,
    validate_current_history_synchronization,
    validate_current_outputs_freshness,
    validate_no_duplicate_snapshot_registry_entries,
    validate_partial_current_publication,
    validate_replay_mode_consistency,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class _StubBenchmarkProvider:
    def get_benchmark_returns(self, *, benchmark_id, symbol_or_index, start_date, end_date):
        return [
            BenchmarkReturnRow("BM", "IDX", "2025-05-13", 100.0, 0.0, "TEST"),
            BenchmarkReturnRow("BM", "IDX", "2026-05-13", 110.0, 0.10, "TEST"),
        ]

    def get_benchmark_series(self, benchmark_symbol_or_index, start_date, end_date):
        return [
            PricePoint(date="2025-05-13", value=100.0),
            PricePoint(date="2026-05-13", value=110.0),
        ]


class _StubVehicleProvider:
    def get_investable_vehicle_returns(self, *, vehicle_id, symbol, start_date, end_date):
        return [
            InvestableVehicleReturnRow("VEH", "ETF", "2025-05-13", 100.0, 0.0, "TEST"),
            InvestableVehicleReturnRow("VEH", "ETF", "2026-05-13", 108.0, 0.08, "TEST"),
        ]

    def get_vehicle_series(self, symbol, start_date, end_date):
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
    from datetime import datetime
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


# ---------------------------------------------------------------------------
# Phase D — single-source registry symbol derivation
# ---------------------------------------------------------------------------


def test_registry_symbol_derivation_produces_nonempty_sets() -> None:
    """Phase D: derived symbols from registry YAML must be non-empty."""
    benchmark_registry = load_benchmark_category_registry()
    vehicle_registry = load_investable_vehicle_registry()

    benchmark_symbols = derive_benchmark_symbols_from_registry(benchmark_registry)
    vehicle_symbols = derive_vehicle_symbols_from_registry(vehicle_registry)

    assert len(benchmark_symbols) >= 7, "Expected at least 7 benchmark symbols from registry."
    assert len(vehicle_symbols) >= 5, "Expected at least 5 vehicle symbols from registry."


def test_registry_derivation_all_upper() -> None:
    """Phase D: derived symbols must be upper-cased (provider comparison is case-sensitive)."""
    benchmark_registry = load_benchmark_category_registry()
    vehicle_registry = load_investable_vehicle_registry()

    for sym in derive_benchmark_symbols_from_registry(benchmark_registry):
        assert sym == sym.upper(), f"Benchmark symbol {sym!r} not uppercased."
    for sym in derive_vehicle_symbols_from_registry(vehicle_registry):
        assert sym == sym.upper(), f"Vehicle symbol {sym!r} not uppercased."


# ---------------------------------------------------------------------------
# Phase F — replay mode detection
# ---------------------------------------------------------------------------


def test_detect_replay_mode_historical() -> None:
    past = (date.today() - timedelta(days=30)).isoformat()
    past2 = (date.today() - timedelta(days=1)).isoformat()
    assert detect_replay_mode(past, past2) == ReplayMode.HISTORICAL_VALIDATION.value


def test_detect_replay_mode_current_recommendation() -> None:
    past = (date.today() - timedelta(days=30)).isoformat()
    today = date.today().isoformat()
    assert detect_replay_mode(past, today) == ReplayMode.CURRENT_RECOMMENDATION.value


def test_detect_replay_mode_forward_simulation() -> None:
    past = (date.today() - timedelta(days=30)).isoformat()
    future = (date.today() + timedelta(days=30)).isoformat()
    assert detect_replay_mode(past, future) == ReplayMode.FORWARD_SIMULATION.value


def test_replay_mode_consistency_validator_passes_for_historical() -> None:
    past = (date.today() - timedelta(days=30)).isoformat()
    past2 = (date.today() - timedelta(days=1)).isoformat()
    errors = validate_replay_mode_consistency("HISTORICAL_VALIDATION", past, past2)
    assert errors == []


def test_replay_mode_consistency_validator_catches_mismatch() -> None:
    past = (date.today() - timedelta(days=30)).isoformat()
    past2 = (date.today() - timedelta(days=1)).isoformat()
    # Declare FORWARD_SIMULATION but give historical window
    errors = validate_replay_mode_consistency("FORWARD_SIMULATION", past, past2)
    assert len(errors) == 1
    assert "FORWARD_SIMULATION" in errors[0]


# ---------------------------------------------------------------------------
# Phase G — expanded coverage states (FAILED and STALE in enum)
# ---------------------------------------------------------------------------


def test_replay_status_enum_contains_failed_and_stale() -> None:
    """Phase G: FAILED and STALE must be valid replay status values."""
    assert "FAILED" in REPLAY_STATUS_ENUM
    assert "STALE" in REPLAY_STATUS_ENUM


# ---------------------------------------------------------------------------
# Phase E — temporal validation hardening
# ---------------------------------------------------------------------------


def test_no_duplicate_snapshot_registry_entries_passes_for_unique() -> None:
    rows = [
        {"snapshot_date": "2025-05-13", "run_id": "RUN-A"},
        {"snapshot_date": "2025-05-14", "run_id": "RUN-B"},
    ]
    errors = validate_no_duplicate_snapshot_registry_entries(
        rows, key_fields=["snapshot_date", "run_id"]
    )
    assert errors == []


def test_no_duplicate_snapshot_registry_entries_catches_duplicate() -> None:
    rows = [
        {"snapshot_date": "2025-05-13", "run_id": "RUN-A"},
        {"snapshot_date": "2025-05-13", "run_id": "RUN-A"},
    ]
    errors = validate_no_duplicate_snapshot_registry_entries(
        rows, key_fields=["snapshot_date", "run_id"]
    )
    assert len(errors) == 1
    assert "duplicate" in errors[0].lower()


def test_partial_publication_detected_when_tmp_exists(tmp_path: Path) -> None:
    """Phase E: .tmp/ existence signals a prior interrupted atomic publication."""
    current_root = tmp_path / "current"
    (current_root / ".tmp").mkdir(parents=True)
    errors = validate_partial_current_publication(current_root)
    assert len(errors) == 1
    assert ".tmp" in errors[0]


def test_partial_publication_passes_when_no_tmp(tmp_path: Path) -> None:
    current_root = tmp_path / "current"
    current_root.mkdir(parents=True)
    errors = validate_partial_current_publication(current_root)
    assert errors == []


def test_current_outputs_freshness_missing_metadata(tmp_path: Path) -> None:
    """Phase E: missing current_snapshot_metadata.json should be reported."""
    errors = validate_current_outputs_freshness(tmp_path / "current")
    assert len(errors) == 1
    assert "missing" in errors[0].lower()


def test_current_outputs_freshness_fresh(tmp_path: Path) -> None:
    """Phase H+E: fresh metadata should pass freshness check."""
    current_root = tmp_path / "current"
    from datetime import datetime
    _write_current_snapshot_metadata(
        current_root,
        snapshot_date="2025-05-13",
        run_id="RUN-A",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        source_snapshot_date="2025-05-13",
        freshness_status="FRESH",
    )
    errors = validate_current_outputs_freshness(current_root, max_staleness_days=7)
    assert errors == []


# ---------------------------------------------------------------------------
# Phase C — atomic current publication
# ---------------------------------------------------------------------------


def test_atomic_publish_moves_files_to_current(tmp_path: Path) -> None:
    """Phase C: files in .tmp/ must appear in current/ after atomic publish."""
    current_root = tmp_path / "current"
    tmp_root = current_root / ".tmp"
    tmp_root.mkdir(parents=True)
    (tmp_root / "replay_availability.csv").write_text("header\nvalue", encoding="utf-8")

    _atomic_publish_current_outputs(tmp_root, current_root, ["replay_availability.csv"])

    assert (current_root / "replay_availability.csv").exists()
    assert not (tmp_root / "replay_availability.csv").exists()


def test_atomic_publish_does_not_touch_other_current_files(tmp_path: Path) -> None:
    """Phase C: atomic publish only moves listed files; other current/ files untouched."""
    current_root = tmp_path / "current"
    current_root.mkdir(parents=True)
    existing = current_root / "important_existing.csv"
    existing.write_text("should not be deleted", encoding="utf-8")

    tmp_root = current_root / ".tmp"
    tmp_root.mkdir(parents=True)
    (tmp_root / "replay_availability.csv").write_text("data", encoding="utf-8")

    _atomic_publish_current_outputs(tmp_root, current_root, ["replay_availability.csv"])

    assert existing.exists()
    assert existing.read_text() == "should not be deleted"


# ---------------------------------------------------------------------------
# Phase B — snapshot registry append semantics
# ---------------------------------------------------------------------------


def test_snapshot_registry_append_creates_file_with_headers(tmp_path: Path) -> None:
    """Phase B: first _append_to_registry call must write headers then the row."""
    registry_path = tmp_path / "analytical_snapshot_registry.csv"
    row = {h: f"val_{h}" for h in ANALYTICAL_SNAPSHOT_REGISTRY_HEADERS}
    _append_to_registry(path=registry_path, headers=ANALYTICAL_SNAPSHOT_REGISTRY_HEADERS, row=row)

    assert registry_path.exists()
    with registry_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["snapshot_date"] == f"val_snapshot_date"


def test_snapshot_registry_append_adds_rows_without_duplicate_headers(tmp_path: Path) -> None:
    """Phase B: multiple appends must not duplicate headers."""
    registry_path = tmp_path / "registry.csv"
    for i in range(3):
        _append_to_registry(
            path=registry_path,
            headers=ANALYTICAL_SNAPSHOT_REGISTRY_HEADERS,
            row={h: str(i) for h in ANALYTICAL_SNAPSHOT_REGISTRY_HEADERS},
        )

    with registry_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# Phase H — freshness metadata contract
# ---------------------------------------------------------------------------


def test_write_current_snapshot_metadata_produces_valid_json(tmp_path: Path) -> None:
    """Phase H: current_snapshot_metadata.json must be well-formed JSON."""
    from datetime import datetime
    _write_current_snapshot_metadata(
        tmp_path,
        snapshot_date="2025-05-13",
        run_id="RUN-TEST",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        source_snapshot_date="2025-05-13",
        freshness_status="FRESH",
    )
    path = tmp_path / "current_snapshot_metadata.json"
    assert path.exists()
    metadata = json.loads(path.read_text(encoding="utf-8"))
    assert metadata["snapshot_date"] == "2025-05-13"
    assert metadata["freshness_status"] == "FRESH"
    assert "generated_at_utc" in metadata


# ---------------------------------------------------------------------------
# Phase A + Phase B integration: build writes snapshot_date-partitioned history
# ---------------------------------------------------------------------------


def test_wp05c_build_creates_snapshot_date_partitioned_replay_history(tmp_path: Path) -> None:
    """Phase A: replay history partitions must use snapshot_date=.../replay_id=... structure."""
    current_root = tmp_path / "data" / "current"
    replay_history_root = tmp_path / "data" / "history" / "replays"
    analytical_history_root = tmp_path / "data" / "history" / "analytical_universe"
    snapshot_registry_root = tmp_path / "data" / "history"

    _seed_current_inputs(current_root)
    build_wp05b_replay_matrix(
        run_id="RUN-WP05C-UNIT",
        snapshot_date="2025-05-13",
        start_date="2025-05-13",
        end_date="2026-05-13",
        current_root=current_root,
        replay_history_root=replay_history_root,
        analytical_history_root=analytical_history_root,
        snapshot_registry_root=snapshot_registry_root,
        benchmark_return_provider=_StubBenchmarkProvider(),
        investable_vehicle_return_provider=_StubVehicleProvider(),
    )

    # Phase A: verify snapshot_date partition exists in replay history
    snapshot_dirs = list(replay_history_root.glob("snapshot_date=*"))
    assert len(snapshot_dirs) >= 1, "No snapshot_date partition found in replay history."
    snapshot_dir = snapshot_dirs[0]
    assert snapshot_dir.name == "snapshot_date=2025-05-13"
    replay_dirs = list(snapshot_dir.glob("replay_id=*"))
    assert len(replay_dirs) >= 1, "No replay_id partitions inside snapshot_date partition."


def test_wp05c_build_publishes_snapshot_registries(tmp_path: Path) -> None:
    """Phase B: build must append rows to both snapshot registry files."""
    current_root = tmp_path / "data" / "current"
    replay_history_root = tmp_path / "data" / "history" / "replays"
    analytical_history_root = tmp_path / "data" / "history" / "analytical_universe"
    snapshot_registry_root = tmp_path / "data" / "history"

    _seed_current_inputs(current_root)
    build_wp05b_replay_matrix(
        run_id="RUN-WP05C-REG",
        snapshot_date="2025-05-13",
        start_date="2025-05-13",
        end_date="2026-05-13",
        current_root=current_root,
        replay_history_root=replay_history_root,
        analytical_history_root=analytical_history_root,
        snapshot_registry_root=snapshot_registry_root,
        benchmark_return_provider=_StubBenchmarkProvider(),
        investable_vehicle_return_provider=_StubVehicleProvider(),
    )

    analytical_reg = snapshot_registry_root / "analytical_snapshot_registry.csv"
    replay_reg = snapshot_registry_root / "replay_snapshot_registry.csv"

    assert analytical_reg.exists(), "analytical_snapshot_registry.csv not created."
    assert replay_reg.exists(), "replay_snapshot_registry.csv not created."

    with analytical_reg.open("r", encoding="utf-8", newline="") as handle:
        a_rows = list(csv.DictReader(handle))
    assert len(a_rows) == 1
    assert a_rows[0]["snapshot_date"] == "2025-05-13"
    assert a_rows[0]["run_id"] == "RUN-WP05C-REG"


def test_wp05c_build_writes_freshness_metadata(tmp_path: Path) -> None:
    """Phase H: build must create current_snapshot_metadata.json in current/."""
    current_root = tmp_path / "data" / "current"
    replay_history_root = tmp_path / "data" / "history" / "replays"
    analytical_history_root = tmp_path / "data" / "history" / "analytical_universe"
    snapshot_registry_root = tmp_path / "data" / "history"

    _seed_current_inputs(current_root)
    build_wp05b_replay_matrix(
        run_id="RUN-WP05C-FRESH",
        snapshot_date="2025-05-13",
        start_date="2025-05-13",
        end_date="2026-05-13",
        current_root=current_root,
        replay_history_root=replay_history_root,
        analytical_history_root=analytical_history_root,
        snapshot_registry_root=snapshot_registry_root,
        benchmark_return_provider=_StubBenchmarkProvider(),
        investable_vehicle_return_provider=_StubVehicleProvider(),
    )

    metadata_path = current_root / "current_snapshot_metadata.json"
    assert metadata_path.exists(), "current_snapshot_metadata.json not created."
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["snapshot_date"] == "2025-05-13"
    assert metadata["freshness_status"] == "FRESH"
    assert "generated_at_utc" in metadata


def test_wp05c_build_leaves_no_tmp_after_success(tmp_path: Path) -> None:
    """Phase C: .tmp/ directory must be cleaned up after a successful build."""
    current_root = tmp_path / "data" / "current"
    replay_history_root = tmp_path / "data" / "history" / "replays"
    analytical_history_root = tmp_path / "data" / "history" / "analytical_universe"
    snapshot_registry_root = tmp_path / "data" / "history"

    _seed_current_inputs(current_root)
    build_wp05b_replay_matrix(
        run_id="RUN-WP05C-CLEAN",
        snapshot_date="2025-05-13",
        start_date="2025-05-13",
        end_date="2026-05-13",
        current_root=current_root,
        replay_history_root=replay_history_root,
        analytical_history_root=analytical_history_root,
        snapshot_registry_root=snapshot_registry_root,
        benchmark_return_provider=_StubBenchmarkProvider(),
        investable_vehicle_return_provider=_StubVehicleProvider(),
    )

    assert not (current_root / ".tmp").exists(), ".tmp/ still exists after successful build."
