from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

from src.models.canonical_models import (
    BenchmarkDefinition,
    BenchmarkOutcomeWindow,
    BenchmarkSnapshot,
)
from src.models.run_metadata import RunMetadata
from src.validation.benchmark_validator import (
    validate_benchmark_registry,
    validate_snapshot_lineage,
)


def _load_registry_text() -> dict:
    root = Path(__file__).resolve().parents[1]
    registry_path = root / "config" / "benchmark_registry.yaml"
    import yaml

    return yaml.safe_load(registry_path.read_text(encoding="utf-8"))


def test_benchmark_registry_validation_passes_for_baseline_config() -> None:
    registry = _load_registry_text()
    errors = validate_benchmark_registry(registry)
    assert errors == []


def test_duplicate_mapping_detection_fails_closed() -> None:
    registry = _load_registry_text()
    duplicate_assignment = {
        "geography": "US",
        "market_cap_bucket": "MEGA",
        "benchmark_symbol": "US_MEGA_CORE_IDX",
        "assignment_status": "ACTIVE",
    }
    registry["benchmark_assignments"].append(duplicate_assignment)

    errors = validate_benchmark_registry(registry)
    assert any("Duplicate category assignment" in err for err in errors)


def test_malformed_benchmark_definition_is_reported() -> None:
    registry = _load_registry_text()
    malformed = deepcopy(registry["benchmark_definitions"][0])
    malformed["benchmark_symbol"] = "bad symbol"
    registry["benchmark_definitions"].append(malformed)

    errors = validate_benchmark_registry(registry)
    assert any("Invalid benchmark symbol" in err for err in errors)


def test_benchmark_model_initialization() -> None:
    created_at = datetime(2026, 5, 13, tzinfo=timezone.utc)
    definition = BenchmarkDefinition(
        benchmark_symbol="US_MEGA_CORE_IDX",
        benchmark_name="US Mega Cap Core Placeholder Index",
        geography="US",
        market_cap_bucket="MEGA",
        benchmark_type="EQUITY_CORE",
        provider="INTERNAL_PLACEHOLDER",
        active_status=True,
        created_at=created_at,
    )

    snapshot = BenchmarkSnapshot(
        benchmark_symbol="US_MEGA_CORE_IDX",
        snapshot_date=date(2026, 5, 13),
        adjusted_close=1000.0,
        daily_return=0.01,
        return_30d=0.04,
        return_90d=0.08,
        return_180d=0.12,
        source_provider="INTERNAL_PLACEHOLDER",
        run_id="RUN-20260513-001",
    )

    outcome = BenchmarkOutcomeWindow(
        benchmark_symbol="US_MEGA_CORE_IDX",
        snapshot_date=date(2026, 5, 13),
        horizon_days=30,
        total_return=0.04,
        annualized_return=0.48,
        volatility=0.16,
        relative_strength=0.2,
    )

    assert definition.benchmark_symbol == "US_MEGA_CORE_IDX"
    assert snapshot.adjusted_close == 1000.0
    assert outcome.horizon_days == 30


def test_snapshot_lineage_validation_detects_mismatches() -> None:
    snapshot = BenchmarkSnapshot(
        benchmark_symbol="US_LARGE_CORE_IDX",
        snapshot_date=date(2026, 5, 13),
        adjusted_close=900.0,
        daily_return=0.005,
        return_30d=0.02,
        return_90d=0.05,
        return_180d=0.09,
        source_provider="INTERNAL_PLACEHOLDER",
        run_id="RUN-20260513-ABC",
    )

    valid_run = RunMetadata(
        run_id="RUN-20260513-ABC",
        snapshot_date=date(2026, 5, 13),
        source_provider="INTERNAL_PLACEHOLDER",
        source_file="incoming/manual/benchmark_seed.csv",
        created_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
        processing_status="COMPLETED",
    )
    assert validate_snapshot_lineage(snapshot, valid_run) == []

    invalid_run = RunMetadata(
        run_id="RUN-20260513-XYZ",
        snapshot_date=date(2026, 5, 12),
        source_provider="INTERNAL_PLACEHOLDER",
        source_file="incoming/manual/benchmark_seed.csv",
        created_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
        processing_status="STARTED",
    )
    errors = validate_snapshot_lineage(snapshot, invalid_run)
    assert any("snapshot.run_id" in err for err in errors)
    assert any("snapshot_date" in err for err in errors)
    assert any("must be COMPLETED" in err for err in errors)