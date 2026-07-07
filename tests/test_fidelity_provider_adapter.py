from __future__ import annotations

import csv
import json
import shutil
from datetime import date
from pathlib import Path

import yaml

from src.normalize.provider_normalizer import normalize_fidelity_ess_file
from src.pipeline.stage_registry import StageContext
from src.pipeline.stages.ess_intake_stage import execute_ess_intake_stage
from src.providers.fidelity.fidelity_ess_adapter import adapt_fidelity_ess_file
from src.validation.provider_mapping_validator import validate_fidelity_provider_mappings


def _fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "fixtures" / name


def _coverage_contract() -> dict:
    path = Path(__file__).resolve().parents[1] / "config" / "coverage_domains.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_fidelity_adapter_parses_provider_native_schema_and_surfaces_unmapped_columns() -> None:
    result = adapt_fidelity_ess_file(
        file_path=_fixture_path("fidelity_starmine_native_fixture.csv"),
        universe="starmine",
        snapshot_date=date(2026, 5, 13),
    )

    assert result.schema_evaluation.missing_required_columns == ()
    assert "Custom Fidelity Flag" in result.unmapped_columns
    assert len(result.adapted_rows) == 2
    assert result.adapted_rows[0]["snapshot_date"] == "2026-05-13"
    assert result.adapted_rows[0]["provider"] == "FIDELITY"
    assert result.adapted_rows[0]["source_file"] == "fidelity_starmine_native_fixture.csv"


def test_fidelity_adapter_filters_duplicate_and_non_data_rows(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fidelity_native_with_footer.csv"
    with fixture_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Symbol",
                "Company Name",
                "Security Type",
                "Security Price",
                "Equity Summary Score (ESS) from LSEG StarMine",
                "Forward EPS Long Term Growth (3-5 Yrs)",
                "Market Capitalization",
                "Jefferson Research",
                "Zacks Investment Research",
                "McLean Capital Management",
            ]
        )
        writer.writerow(
            [
                "AAPL",
                "Apple Inc",
                "Common Stock",
                "190.10",
                "Very Bullish",
                "12.0",
                "$3.00T",
                "Hold",
                "NEUTRAL",
                "Neutral",
            ]
        )
        writer.writerow(
            [
                "AAPL",
                "Apple Inc",
                "Common Stock",
                "190.10",
                "Bullish",
                "12.0",
                "$3.00T",
                "Hold",
                "NEUTRAL",
                "Neutral",
            ]
        )
        writer.writerow(["AS OF 09:09 AM ET 05/13/2026", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["", "", "", "", "", "", "", "", "", ""])

    adapter_result = adapt_fidelity_ess_file(
        file_path=fixture_path,
        universe="starmine",
        snapshot_date=date(2026, 5, 13),
    )

    assert adapter_result.raw_rows_discovered == 4
    assert adapter_result.duplicate_symbol_rows == 1
    assert adapter_result.dropped_non_data_rows == 2
    assert len(adapter_result.adapted_rows) == 1

    mapping_result = validate_fidelity_provider_mappings(adapter_result)
    assert mapping_result.errors == []
    assert any("Skipped 1 duplicate symbol rows" in warning for warning in mapping_result.warnings)
    assert any("Skipped 2 non-data provider rows" in warning for warning in mapping_result.warnings)


def test_provider_mapping_validation_fails_closed_on_malformed_values() -> None:
    adapter_result = adapt_fidelity_ess_file(
        file_path=_fixture_path("fidelity_malformed_native_fixture.csv"),
        universe="starmine",
        snapshot_date=date(2026, 5, 13),
    )

    result = validate_fidelity_provider_mappings(adapter_result)
    assert result.rows_validated == 0
    assert result.rows_rejected == 1
    assert any("Invalid ESS category parsing" in err for err in result.errors)
    assert any("Invalid market-cap parsing" in err for err in result.errors)


def test_provider_normalizer_generates_canonical_signal_and_base_universe_rows() -> None:
    coverage = _coverage_contract()
    result = normalize_fidelity_ess_file(
        file_path=_fixture_path("fidelity_starmine_native_fixture.csv"),
        universe="starmine",
        snapshot_date=date(2026, 5, 13),
        run_id="RUN-WP032-UNIT-001",
        coverage_mapping=coverage["universe_to_domain"],
    )

    assert result.errors == []
    assert result.rows_normalized == 2
    assert result.rows_rejected == 0
    assert "Custom Fidelity Flag" in result.unmapped_columns

    signal_row = result.normalized_signal_rows[0]
    assert signal_row["starmine_ess_text"] == "VERY_BULLISH"
    assert signal_row["starmine_ess_numeric"] == 5.0
    assert signal_row["signal_coverage_status"] == "COVERED"

    universe_row = result.base_universe_rows[0]
    assert universe_row["market_cap_raw_usd"] == 1740000000
    assert universe_row["market_cap_bucket"] == "MICRO"
    assert universe_row["run_id"] == "RUN-WP032-UNIT-001"


def test_ess_stage_generates_snapshots_and_base_universe_outputs(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "config" / "coverage_domains.yaml", tmp_path / "config" / "coverage_domains.yaml")
    shutil.copy2(repo_root / "config" / "market_cap_buckets.yaml", tmp_path / "config" / "market_cap_buckets.yaml")

    (tmp_path / "incoming" / "ess" / "starmine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "incoming" / "ess" / "non_starmine_zacks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        _fixture_path("fidelity_starmine_native_fixture.csv"),
        tmp_path / "incoming" / "ess" / "starmine" / "fidelity_starmine_native_fixture.csv",
    )
    shutil.copy2(
        _fixture_path("fidelity_non_starmine_native_fixture.csv"),
        tmp_path
        / "incoming"
        / "ess"
        / "non_starmine_zacks"
        / "fidelity_non_starmine_native_fixture.csv",
    )

    output = execute_ess_intake_stage(
        StageContext(run_id="RUN-WP032-INT-001", snapshot_date=date(2026, 5, 13))
    )

    assert output.status == "COMPLETE"
    assert output.validation_summary["ess_files_discovered"] == "2"
    assert output.validation_summary["raw_rows_discovered"] == "4"
    assert output.validation_summary["rows_rejected"] == "0"
    assert output.validation_summary["rows_appended"] == "4"
    assert output.validation_summary["base_universe_rows_appended"] == "4"
    assert output.validation_summary["persistence_verification"] == "PASSED"
    assert output.validation_summary["persisted_signal_rows"] == "4"
    assert output.validation_summary["persisted_base_universe_rows"] == "4"
    assert int(output.validation_summary["unmapped_columns"]) >= 1

    current_signal_path = tmp_path / "data" / "current" / "signal_snapshot.csv"
    with current_signal_path.open("r", encoding="utf-8", newline="") as handle:
        snapshot_rows = list(csv.DictReader(handle))
    assert len(snapshot_rows) == 4
    assert all(row.get("created_at_utc", "") for row in snapshot_rows)

    signal_partition_path = (
        tmp_path
        / "data"
        / "history"
        / "signals"
        / "snapshot_date=2026-05-13"
        / "run_id=RUN-WP032-INT-001"
        / "signal_snapshots.csv"
    )
    with signal_partition_path.open("r", encoding="utf-8", newline="") as handle:
        signal_partition_rows = list(csv.DictReader(handle))
    assert len(signal_partition_rows) == 4

    signal_lineage_path = (
        tmp_path
        / "data"
        / "history"
        / "signals"
        / "snapshot_date=2026-05-13"
        / "run_id=RUN-WP032-INT-001"
        / "signal_lineage_registry.csv"
    )
    with signal_lineage_path.open("r", encoding="utf-8", newline="") as handle:
        signal_lineage_rows = list(csv.DictReader(handle))
    assert len(signal_lineage_rows) == 4
    assert all(row.get("created_at_utc", "") for row in signal_lineage_rows)

    base_universe_path = tmp_path / "data" / "current" / "base_equity_universe.csv"
    with base_universe_path.open("r", encoding="utf-8", newline="") as handle:
        universe_rows = list(csv.DictReader(handle))
    assert len(universe_rows) == 4
    assert all(row.get("created_at_utc", "") for row in universe_rows)

    base_partition_path = (
        tmp_path
        / "data"
        / "history"
        / "universe"
        / "snapshot_date=2026-05-13"
        / "run_id=RUN-WP032-INT-001"
        / "base_equity_universe.csv"
    )
    with base_partition_path.open("r", encoding="utf-8", newline="") as handle:
        base_partition_rows = list(csv.DictReader(handle))
    assert len(base_partition_rows) == 4

    base_lineage_path = (
        tmp_path
        / "data"
        / "history"
        / "universe"
        / "snapshot_date=2026-05-13"
        / "run_id=RUN-WP032-INT-001"
        / "universe_lineage_registry.csv"
    )
    with base_lineage_path.open("r", encoding="utf-8", newline="") as handle:
        base_lineage_rows = list(csv.DictReader(handle))
    assert len(base_lineage_rows) == 4
    assert all(row.get("created_at_utc", "") for row in base_lineage_rows)

    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"
    with signal_index_path.open("r", encoding="utf-8", newline="") as handle:
        signal_index_rows = list(csv.DictReader(handle))
    assert len(signal_index_rows) == 1
    assert signal_index_rows[0]["run_id"] == "RUN-WP032-INT-001"
    assert signal_index_rows[0]["row_count"] == "4"

    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"
    with universe_index_path.open("r", encoding="utf-8", newline="") as handle:
        universe_index_rows = list(csv.DictReader(handle))
    assert len(universe_index_rows) == 1
    assert universe_index_rows[0]["run_id"] == "RUN-WP032-INT-001"
    assert universe_index_rows[0]["row_count"] == "4"


def test_ess_stage_blocks_when_intake_has_no_eligible_files(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "config" / "coverage_domains.yaml", tmp_path / "config" / "coverage_domains.yaml")
    shutil.copy2(repo_root / "config" / "market_cap_buckets.yaml", tmp_path / "config" / "market_cap_buckets.yaml")

    (tmp_path / "incoming" / "ess" / "starmine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "incoming" / "ess" / "non_starmine_zacks").mkdir(parents=True, exist_ok=True)

    output = execute_ess_intake_stage(
        StageContext(run_id="RUN-WP032-BLOCK-001", snapshot_date=date(2026, 5, 13))
    )

    assert output.status == "BLOCKED"
    assert any("Intake readiness gate blocked" in error for error in output.errors)
    assert any("No eligible ESS intake files were discovered" in error for error in output.errors)
    assert output.validation_summary["intake_directories_checked"] == (
        "incoming/ess/starmine|incoming/ess/non_starmine_zacks"
    )
    assert output.validation_summary["eligible_file_count"] == "0"
    assert output.validation_summary["blocked_reason"] == "NO_ELIGIBLE_ESS_INTAKE_FILES"
    assert output.validation_summary["operator_guidance"].startswith(
        "No eligible ESS intake files were discovered"
    )


def test_ess_stage_present_holding_generates_no_coverage_gap_warning(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "config" / "coverage_domains.yaml", tmp_path / "config" / "coverage_domains.yaml")
    shutil.copy2(repo_root / "config" / "market_cap_buckets.yaml", tmp_path / "config" / "market_cap_buckets.yaml")

    (tmp_path / "incoming" / "ess" / "starmine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "incoming" / "ess" / "non_starmine_zacks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        _fixture_path("fidelity_starmine_native_fixture.csv"),
        tmp_path / "incoming" / "ess" / "starmine" / "fidelity_starmine_native_fixture.csv",
    )

    analysis_run = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "PAR-20260514-TEST0001"
    analysis_run.mkdir(parents=True, exist_ok=True)
    with (analysis_run / "holdings.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["symbol", "asset_class", "description", "percent_of_portfolio"])
        writer.writeheader()
        writer.writerow({"symbol": "ABC", "asset_class": "EQUITIES", "description": "Alpha Brands Corp", "percent_of_portfolio": "4.0"})

    output = execute_ess_intake_stage(
        StageContext(run_id="RUN-WP032-INT-ESSOK", snapshot_date=date(2026, 5, 13))
    )

    assert output.status == "COMPLETE"
    assert output.validation_summary["ess_coverage_gap_count"] == "0"
    payload = json.loads((tmp_path / "data" / "current" / "ess_coverage_warning.json").read_text(encoding="utf-8"))
    assert payload["warning_count"] == 0


def test_ess_stage_absent_holding_generates_coverage_gap_warning(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "config" / "coverage_domains.yaml", tmp_path / "config" / "coverage_domains.yaml")
    shutil.copy2(repo_root / "config" / "market_cap_buckets.yaml", tmp_path / "config" / "market_cap_buckets.yaml")

    (tmp_path / "incoming" / "ess" / "starmine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "incoming" / "ess" / "non_starmine_zacks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        _fixture_path("fidelity_starmine_native_fixture.csv"),
        tmp_path / "incoming" / "ess" / "starmine" / "fidelity_starmine_native_fixture.csv",
    )

    current_root = tmp_path / "data" / "current"
    current_root.mkdir(parents=True, exist_ok=True)
    with (current_root / "signal_snapshot.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "snapshot_date", "created_at_utc", "run_id", "provider", "source_file", "symbol",
                "coverage_domain", "signal_coverage_status", "starmine_ess_text", "starmine_ess_numeric",
                "starmine_ess_numeric_estimated", "starmine_ess_source_type",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "snapshot_date": "2026-05-10", "created_at_utc": "2026-05-10T12:00:00+00:00",
            "run_id": "OLDRUN", "provider": "FIDELITY", "source_file": "old.csv", "symbol": "TSLA",
            "coverage_domain": "STARMINE_COVERED", "signal_coverage_status": "COVERED",
            "starmine_ess_text": "BEARISH", "starmine_ess_numeric": "2.0",
            "starmine_ess_numeric_estimated": "False", "starmine_ess_source_type": "TEXT_MAPPED",
        })

    analysis_run = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "PAR-20260514-TEST0002"
    analysis_run.mkdir(parents=True, exist_ok=True)
    with (analysis_run / "holdings.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["symbol", "asset_class", "description", "percent_of_portfolio"])
        writer.writeheader()
        writer.writerow({"symbol": "TSLA", "asset_class": "EQUITIES", "description": "Tesla", "percent_of_portfolio": "5.0"})

    output = execute_ess_intake_stage(
        StageContext(run_id="RUN-WP032-INT-ESSMISS", snapshot_date=date(2026, 5, 13))
    )

    assert output.status == "COMPLETE"
    assert output.validation_summary["ess_coverage_gap_count"] == "1"
    assert any("ESS Coverage Warning" in warning for warning in output.warnings)
    payload = json.loads((tmp_path / "data" / "current" / "ess_coverage_warning.json").read_text(encoding="utf-8"))
    assert payload["warning_count"] == 1
    assert payload["gaps"][0]["symbol"] == "TSLA"
    assert payload["gaps"][0]["current_ess_posture"] == "BEARISH"
    assert payload["gaps"][0]["days_stale"] == 3


def test_ess_stage_multiple_absent_holdings_grouped_warning(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "config" / "coverage_domains.yaml", tmp_path / "config" / "coverage_domains.yaml")
    shutil.copy2(repo_root / "config" / "market_cap_buckets.yaml", tmp_path / "config" / "market_cap_buckets.yaml")

    (tmp_path / "incoming" / "ess" / "starmine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "incoming" / "ess" / "non_starmine_zacks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        _fixture_path("fidelity_starmine_native_fixture.csv"),
        tmp_path / "incoming" / "ess" / "starmine" / "fidelity_starmine_native_fixture.csv",
    )

    current_root = tmp_path / "data" / "current"
    current_root.mkdir(parents=True, exist_ok=True)
    with (current_root / "signal_snapshot.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "snapshot_date", "created_at_utc", "run_id", "provider", "source_file", "symbol",
                "coverage_domain", "signal_coverage_status", "starmine_ess_text", "starmine_ess_numeric",
                "starmine_ess_numeric_estimated", "starmine_ess_source_type",
            ],
        )
        writer.writeheader()
        for sym, posture in [("TSLA", "BEARISH"), ("STNG", "NEUTRAL")]:
            writer.writerow({
                "snapshot_date": "2026-05-10", "created_at_utc": "2026-05-10T12:00:00+00:00",
                "run_id": "OLDRUN", "provider": "FIDELITY", "source_file": "old.csv", "symbol": sym,
                "coverage_domain": "STARMINE_COVERED", "signal_coverage_status": "COVERED",
                "starmine_ess_text": posture, "starmine_ess_numeric": "2.0",
                "starmine_ess_numeric_estimated": "False", "starmine_ess_source_type": "TEXT_MAPPED",
            })

    analysis_run = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "PAR-20260514-TEST0003"
    analysis_run.mkdir(parents=True, exist_ok=True)
    with (analysis_run / "holdings.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["symbol", "asset_class", "description", "percent_of_portfolio"])
        writer.writeheader()
        writer.writerow({"symbol": "TSLA", "asset_class": "EQUITIES", "description": "Tesla", "percent_of_portfolio": "5.0"})
        writer.writerow({"symbol": "STNG", "asset_class": "EQUITIES", "description": "Scorpio Tankers", "percent_of_portfolio": "3.0"})

    output = execute_ess_intake_stage(
        StageContext(run_id="RUN-WP032-INT-ESSMULTI", snapshot_date=date(2026, 5, 13))
    )

    assert output.status == "COMPLETE"
    assert output.validation_summary["ess_coverage_gap_count"] == "2"
    assert output.validation_summary["ess_coverage_gap_examples"] == "TSLA|STNG"
    payload = json.loads((tmp_path / "data" / "current" / "ess_coverage_warning.json").read_text(encoding="utf-8"))
    assert payload["warning_count"] == 2
    assert payload["example_symbols"] == ["TSLA", "STNG"]


def test_ess_stage_repeated_runs_preserve_history_and_regenerate_current(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "config" / "coverage_domains.yaml", tmp_path / "config" / "coverage_domains.yaml")
    shutil.copy2(repo_root / "config" / "market_cap_buckets.yaml", tmp_path / "config" / "market_cap_buckets.yaml")

    starmine_dir = tmp_path / "incoming" / "ess" / "starmine"
    non_starmine_dir = tmp_path / "incoming" / "ess" / "non_starmine_zacks"
    starmine_dir.mkdir(parents=True, exist_ok=True)
    non_starmine_dir.mkdir(parents=True, exist_ok=True)

    run1_file = starmine_dir / "fidelity_starmine_run1.csv"
    shutil.copy2(_fixture_path("fidelity_starmine_native_fixture.csv"), run1_file)

    output1 = execute_ess_intake_stage(
        StageContext(run_id="RUN-WP032-INT-RGEN-001", snapshot_date=date(2026, 5, 13))
    )
    assert output1.status == "COMPLETE"

    run2_file = starmine_dir / "fidelity_starmine_run2.csv"
    shutil.copy2(_fixture_path("fidelity_starmine_native_fixture.csv"), run2_file)

    output2 = execute_ess_intake_stage(
        StageContext(run_id="RUN-WP032-INT-RGEN-002", snapshot_date=date(2026, 5, 13))
    )
    assert output2.status == "COMPLETE"

    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"
    with signal_index_path.open("r", encoding="utf-8", newline="") as handle:
        signal_index_rows = list(csv.DictReader(handle))
    assert len(signal_index_rows) == 2
    assert signal_index_rows[0]["run_id"] == "RUN-WP032-INT-RGEN-001"
    assert signal_index_rows[1]["run_id"] == "RUN-WP032-INT-RGEN-002"

    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"
    with universe_index_path.open("r", encoding="utf-8", newline="") as handle:
        universe_index_rows = list(csv.DictReader(handle))
    assert len(universe_index_rows) == 2
    assert universe_index_rows[0]["run_id"] == "RUN-WP032-INT-RGEN-001"
    assert universe_index_rows[1]["run_id"] == "RUN-WP032-INT-RGEN-002"

    current_signal_path = tmp_path / "data" / "current" / "signal_snapshot.csv"
    with current_signal_path.open("r", encoding="utf-8", newline="") as handle:
        current_signal_rows = list(csv.DictReader(handle))
    assert len(current_signal_rows) == 2
    assert {row["run_id"] for row in current_signal_rows} == {"RUN-WP032-INT-RGEN-002"}
