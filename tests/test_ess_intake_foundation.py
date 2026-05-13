from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from src.history.signal_snapshot_manager import append_signal_snapshots, ensure_signal_history_contracts
from src.normalize.ess_normalizer import normalize_ess_rows
from src.pipeline.stage_registry import default_stage_registry
from src.validation.ess_validator import validate_ess_file


def _fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "fixtures" / name


def _coverage_contract() -> dict:
    path = Path(__file__).resolve().parents[1] / "config" / "coverage_domains.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_schema_validation_passes_for_starmine_fixture() -> None:
    coverage = _coverage_contract()
    result = validate_ess_file(
        file_path=_fixture_path("starmine_fixture.csv"),
        universe="starmine",
        allowed_coverage_domains=coverage["coverage_domains"],
        allowed_source_types=coverage["starmine_ess_source_types"],
    )
    assert result.errors == []
    assert len(result.rows) == 2


def test_malformed_row_detection() -> None:
    coverage = _coverage_contract()
    bad_row = "snapshot_date,symbol,provider,source_file,starmine_ess_text\n2026/05/13,,FIDELITY,file.csv,BULLISH\n"
    temp_path = _fixture_path("_temp_malformed.csv")
    temp_path.write_text(bad_row, encoding="utf-8")
    try:
        result = validate_ess_file(
            file_path=temp_path,
            universe="starmine",
            allowed_coverage_domains=coverage["coverage_domains"],
            allowed_source_types=coverage["starmine_ess_source_types"],
        )
        assert any("Malformed row detection" in err for err in result.errors)
        assert any("Snapshot metadata validation" in err for err in result.errors)
    finally:
        temp_path.unlink(missing_ok=True)


def test_duplicate_symbol_detection() -> None:
    coverage = _coverage_contract()
    duplicate_rows = (
        "snapshot_date,symbol,provider,source_file,starmine_ess_text\n"
        "2026-05-13,ABC,FIDELITY,file.csv,BULLISH\n"
        "2026-05-13,abc,FIDELITY,file.csv,NEUTRAL\n"
    )
    temp_path = _fixture_path("_temp_duplicates.csv")
    temp_path.write_text(duplicate_rows, encoding="utf-8")
    try:
        result = validate_ess_file(
            file_path=temp_path,
            universe="starmine",
            allowed_coverage_domains=coverage["coverage_domains"],
            allowed_source_types=coverage["starmine_ess_source_types"],
        )
        assert any("Duplicate symbol detection" in err for err in result.errors)
    finally:
        temp_path.unlink(missing_ok=True)


def test_coverage_domain_assignment_and_text_preservation() -> None:
    coverage = _coverage_contract()
    rows = [
        {
            "snapshot_date": "2026-05-13",
            "symbol": "abc",
            "provider": "FIDELITY",
            "source_file": "starmine_fixture.csv",
            "starmine_ess_text": "BULLISH",
        }
    ]
    normalized = normalize_ess_rows(
        rows=rows,
        universe="starmine",
        coverage_mapping=coverage["universe_to_domain"],
        derive_numeric=False,
    )

    assert normalized[0]["symbol"] == "ABC"
    assert normalized[0]["coverage_domain"] == "STARMINE_COVERED"
    assert normalized[0]["starmine_ess_text"] == "BULLISH"


def test_provenance_preservation_and_numeric_mapping_lineage() -> None:
    coverage = _coverage_contract()
    rows = [
        {
            "snapshot_date": "2026-05-13",
            "symbol": "xyz",
            "provider": "FIDELITY",
            "source_file": "starmine_fixture.csv",
            "starmine_ess_text": "NEUTRAL",
        }
    ]
    normalized = normalize_ess_rows(
        rows=rows,
        universe="starmine",
        coverage_mapping=coverage["universe_to_domain"],
        derive_numeric=True,
    )

    row = normalized[0]
    assert row["provider"] == "FIDELITY"
    assert row["source_file"] == "starmine_fixture.csv"
    assert row["starmine_ess_numeric"] == 3.0
    assert row["starmine_ess_numeric_estimated"] is True
    assert row["starmine_ess_source_type"] == "TEXT_MAPPED"


def test_snapshot_append_behavior_and_immutable_protection(tmp_path: Path) -> None:
    history_root = tmp_path / "history" / "signals"
    ensure_signal_history_contracts(history_root=history_root)

    normalized_records = [
        {
            "snapshot_date": "2026-05-13",
            "symbol": "ABC",
            "provider": "FIDELITY",
            "source_file": "starmine_fixture.csv",
            "coverage_domain": "STARMINE_COVERED",
            "signal_coverage_status": "COVERED",
            "starmine_ess_text": "BULLISH",
            "starmine_ess_numeric": 4.0,
            "starmine_ess_numeric_estimated": True,
            "starmine_ess_source_type": "TEXT_MAPPED",
        }
    ]

    appended = append_signal_snapshots(
        normalized_records=normalized_records,
        run_id="RUN-ESS-001",
        history_root=history_root,
    )
    assert appended == 1

    with (history_root / "signal_snapshots.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["run_id"] == "RUN-ESS-001"

    with pytest.raises(ValueError, match="Immutable snapshot protection"):
        append_signal_snapshots(
            normalized_records=normalized_records,
            run_id="RUN-ESS-001",
            history_root=history_root,
        )


def test_stage_registry_contains_ess_stage_executor() -> None:
    stage_names = [item.stage_name for item in default_stage_registry()]
    assert "ess_intake" in stage_names
    ess_stage = next(item for item in default_stage_registry() if item.stage_name == "ess_intake")
    assert ess_stage.executor is not None