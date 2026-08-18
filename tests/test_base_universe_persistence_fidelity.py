from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import yaml

from src.history.base_universe_manager import append_base_universe_rows
from src.normalize.provider_normalizer import normalize_fidelity_ess_file
from src.providers.fidelity.fidelity_ess_adapter import adapt_fidelity_ess_file
from src.validation.provider_mapping_validator import validate_fidelity_provider_mappings


def _fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "fixtures" / name


def _coverage_contract() -> dict:
    path = Path(__file__).resolve().parents[1] / "config" / "coverage_domains.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_non_starmine_rating_survives_adapter_to_persistence(tmp_path: Path) -> None:
    coverage = _coverage_contract()
    source_path = _fixture_path("fidelity_non_starmine_native_fixture.csv")

    adapter_result = adapt_fidelity_ess_file(
        file_path=source_path,
        universe="non_starmine_zacks",
        snapshot_date=date(2026, 5, 13),
    )
    adapter_row = next(row for row in adapter_result.adapted_rows if row["symbol"] == "QRS")
    assert adapter_row.get("analyst_rating") == "OUTPERFORM"

    mapping_result = validate_fidelity_provider_mappings(adapter_result)
    validated_row = next(row for row in mapping_result.validated_rows if row["symbol"] == "QRS")
    assert validated_row.get("analyst_rating") == "OUTPERFORM"

    normalized = normalize_fidelity_ess_file(
        file_path=source_path,
        universe="non_starmine_zacks",
        snapshot_date=date(2026, 5, 13),
        run_id="RUN-UNIT-NONST-001",
        coverage_mapping=coverage["universe_to_domain"],
    )

    before_persist = next(row for row in normalized.base_universe_rows if row["symbol"] == "QRS")
    assert before_persist.get("starmine_ess_text") == ""
    assert before_persist.get("starmine_ess_raw_score") == ""
    assert before_persist.get("zacks_rating") == ""
    assert before_persist.get("ess_zacks_rating") == "OUTPERFORM"

    current_root = tmp_path / "data" / "current"
    history_root = tmp_path / "data" / "history" / "universe"
    index_path = tmp_path / "data" / "history" / "universe_index.csv"

    appended = append_base_universe_rows(
        base_rows=normalized.base_universe_rows,
        run_id="RUN-UNIT-NONST-001",
        current_root=current_root,
        history_root=history_root,
        index_path=index_path,
    )
    assert appended == len(normalized.base_universe_rows)

    persisted_rows = _read_csv_rows(
        history_root
        / "snapshot_date=2026-05-13"
        / "run_id=RUN-UNIT-NONST-001"
        / "base_equity_universe.csv"
    )
    persisted = next(row for row in persisted_rows if row["symbol"] == "QRS")
    assert persisted["coverage_domain"] == "NON_STARMINE_ANALYST"
    assert persisted["starmine_ess_text"] == ""
    assert persisted["starmine_ess_raw_score"] == ""
    assert persisted["zacks_rating"] == ""
    assert persisted["ess_zacks_rating"] == "OUTPERFORM"


def test_starmine_row_fields_remain_intact_after_persistence(tmp_path: Path) -> None:
    base_row = {
        "symbol": "TEST",
        "company_name": "Test Corp",
        "security_type": "Common Stock",
        "geography": "US",
        "market_cap_raw_usd": 1000000000,
        "market_cap_bucket": "MID",
        "coverage_domain": "STARMINE_COVERED",
        "starmine_ess_text": "BULLISH",
        "starmine_ess_raw_score": "7.0",
        "zacks_rating": "OUTPERFORM",
        "ess_zacks_rating": "",
        "provider": "FIDELITY",
        "source_file": "synthetic_starmine.csv",
        "snapshot_date": "2026-05-13",
        "provider_schema_version": "FIDELITY_ESS_EXPORT_V1",
        "provider_column_lineage": {"symbol": "Symbol"},
        "unmapped_provider_columns": [],
    }

    current_root = tmp_path / "data" / "current"
    history_root = tmp_path / "data" / "history" / "universe"
    index_path = tmp_path / "data" / "history" / "universe_index.csv"

    append_base_universe_rows(
        base_rows=[base_row],
        run_id="RUN-UNIT-STARMINE-001",
        current_root=current_root,
        history_root=history_root,
        index_path=index_path,
    )

    persisted_rows = _read_csv_rows(
        history_root
        / "snapshot_date=2026-05-13"
        / "run_id=RUN-UNIT-STARMINE-001"
        / "base_equity_universe.csv"
    )
    persisted = persisted_rows[0]
    assert persisted["symbol"] == "TEST"
    assert persisted["coverage_domain"] == "STARMINE_COVERED"
    assert persisted["starmine_ess_text"] == "BULLISH"
    assert persisted["starmine_ess_raw_score"] == "7.0"
    assert persisted["zacks_rating"] == "OUTPERFORM"
    assert persisted["ess_zacks_rating"] == ""


def test_synthetic_non_starmine_test_symbol_persists_outperform_rating(tmp_path: Path) -> None:
    base_row = {
        "symbol": "TEST",
        "company_name": "Synthetic Non StarMine",
        "security_type": "Common Stock",
        "geography": "US",
        "market_cap_raw_usd": 2500000000,
        "market_cap_bucket": "MID",
        "coverage_domain": "NON_STARMINE_ANALYST",
        "starmine_ess_text": "",
        "starmine_ess_raw_score": "",
        "zacks_rating": "",
        "ess_zacks_rating": "OUTPERFORM",
        "provider": "FIDELITY",
        "source_file": "synthetic_non_starmine.csv",
        "snapshot_date": "2026-05-13",
        "provider_schema_version": "FIDELITY_ESS_EXPORT_V1",
        "provider_column_lineage": {"analyst_rating": "Zacks Investment Research"},
        "unmapped_provider_columns": [],
    }

    current_root = tmp_path / "data" / "current"
    history_root = tmp_path / "data" / "history" / "universe"
    index_path = tmp_path / "data" / "history" / "universe_index.csv"

    append_base_universe_rows(
        base_rows=[base_row],
        run_id="RUN-UNIT-NONST-TEST-001",
        current_root=current_root,
        history_root=history_root,
        index_path=index_path,
    )

    persisted_rows = _read_csv_rows(
        history_root
        / "snapshot_date=2026-05-13"
        / "run_id=RUN-UNIT-NONST-TEST-001"
        / "base_equity_universe.csv"
    )
    persisted = persisted_rows[0]
    assert persisted["symbol"] == "TEST"
    assert persisted["coverage_domain"] == "NON_STARMINE_ANALYST"
    assert persisted["starmine_ess_text"] == ""
    assert persisted["starmine_ess_raw_score"] == ""
    assert persisted["zacks_rating"] == ""
    assert persisted["ess_zacks_rating"] == "OUTPERFORM"
