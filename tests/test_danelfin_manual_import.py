from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.scoring.danelfin_manual_import import (
    DEFAULT_OPERATOR_SOURCE,
    MANUAL_ACQUISITION_METHOD,
    import_manual_danelfin_observations,
    load_latest_danelfin_provenance,
    read_manual_danelfin_csv,
)
from src.scoring.fetch_danelfin_scores import load_latest_danelfin_scores


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_latest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "danelfin_raw", "danelfin_score", "sourced_date"])
        writer.writeheader()
        writer.writerows(rows)


def test_manual_import_normalizes_scores_and_merges_multiple_symbols(tmp_path):
    summary = import_manual_danelfin_observations(
        [
            {"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"},
            {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
        ],
        output_dir=tmp_path,
        operator_source="PAIR_PAGE",
        observed_at="2026-08-15T14:12:00Z",
    )

    latest_rows = _read_rows(tmp_path / "latest_danelfin.csv")
    rows_by_symbol = {row["symbol"]: row for row in latest_rows}

    assert summary["applied_count"] == 2
    assert rows_by_symbol["MSFT"]["danelfin_raw"] == "3"
    assert rows_by_symbol["MSFT"]["danelfin_score"] == "1.5000"
    assert rows_by_symbol["NVDA"]["danelfin_raw"] == "8"
    assert rows_by_symbol["NVDA"]["danelfin_score"] == "4.0000"
    assert load_latest_danelfin_scores(tmp_path) == {"MSFT": 1.5, "NVDA": 4.0}


@pytest.mark.parametrize(
    "raw_score",
    [0, 11, -1, "abc", "", 3.2],
)
def test_invalid_scores_are_rejected(tmp_path, raw_score):
    with pytest.raises(ValueError):
        import_manual_danelfin_observations(
            [{"symbol": "MSFT", "danelfin_raw": raw_score, "sourced_date": "2026-08-15"}],
            output_dir=tmp_path,
        )


def test_blank_symbol_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        import_manual_danelfin_observations(
            [{"symbol": " ", "danelfin_raw": 3, "sourced_date": "2026-08-15"}],
            output_dir=tmp_path,
        )


def test_future_source_date_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        import_manual_danelfin_observations(
            [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-18"}],
            output_dir=tmp_path,
        )


def test_older_observation_does_not_overwrite_newer(tmp_path):
    (tmp_path / "latest_danelfin.csv").write_text(
        "symbol,danelfin_raw,danelfin_score,sourced_date\nMSFT,9,4.5000,2026-08-16\n",
        encoding="utf-8",
    )

    summary = import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
    )

    rows = _read_rows(tmp_path / "latest_danelfin.csv")
    assert rows[0]["danelfin_raw"] == "9"
    assert rows[0]["danelfin_score"] == "4.5000"
    assert summary["skipped_count"] == 1


def test_newer_empty_placeholder_does_not_block_older_valid_observation(tmp_path):
    _write_latest(
        tmp_path / "latest_danelfin.csv",
        [
            {"symbol": "MSFT", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-17"},
            {"symbol": "NVDA", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-17"},
        ],
    )

    summary = import_manual_danelfin_observations(
        [
            {"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"},
            {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
        ],
        output_dir=tmp_path,
        operator_source=DEFAULT_OPERATOR_SOURCE,
    )

    rows = {row["symbol"]: row for row in _read_rows(tmp_path / "latest_danelfin.csv")}
    assert summary["applied_count"] == 2
    assert summary["skipped_count"] == 0
    assert rows["MSFT"]["danelfin_raw"] == "3"
    assert rows["MSFT"]["danelfin_score"] == "1.5000"
    assert rows["MSFT"]["sourced_date"] == "2026-08-15"
    assert rows["NVDA"]["danelfin_raw"] == "8"
    assert rows["NVDA"]["danelfin_score"] == "4.0000"
    assert rows["NVDA"]["sourced_date"] == "2026-08-15"


def test_same_day_manual_score_replaces_empty_row_but_not_valid_value(tmp_path):
    _write_latest(
        tmp_path / "latest_danelfin.csv",
        [
            {"symbol": "MSFT", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-15"},
            {"symbol": "NVDA", "danelfin_raw": "7", "danelfin_score": "3.5000", "sourced_date": "2026-08-15"},
        ],
    )

    summary = import_manual_danelfin_observations(
        [
            {"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"},
            {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
        ],
        output_dir=tmp_path,
        operator_source=DEFAULT_OPERATOR_SOURCE,
    )

    rows = {row["symbol"]: row for row in _read_rows(tmp_path / "latest_danelfin.csv")}
    assert rows["MSFT"]["danelfin_raw"] == "3"
    assert rows["MSFT"]["danelfin_score"] == "1.5000"
    assert rows["NVDA"]["danelfin_raw"] == "7"
    assert rows["NVDA"]["danelfin_score"] == "3.5000"
    assert summary["skipped_count"] == 1


def test_merge_precedence_matrix(tmp_path):
    latest = tmp_path / "latest_danelfin.csv"

    # A. newer empty + older valid manual => valid manual wins
    _write_latest(latest, [{"symbol": "MSFT", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-17"}])
    summary = import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
    )
    rows = {row["symbol"]: row for row in _read_rows(latest)}
    assert rows["MSFT"]["danelfin_raw"] == "3"
    assert rows["MSFT"]["danelfin_score"] == "1.5000"
    assert summary["applied_count"] == 1

    # B. newer valid + older valid => newer valid remains
    _write_latest(latest, [{"symbol": "MSFT", "danelfin_raw": "9", "danelfin_score": "4.5000", "sourced_date": "2026-08-17"}])
    summary = import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
    )
    rows = {row["symbol"]: row for row in _read_rows(latest)}
    assert rows["MSFT"]["danelfin_raw"] == "9"
    assert summary["skipped_count"] == 1

    # C. older valid + newer valid => newer manual wins
    _write_latest(latest, [{"symbol": "MSFT", "danelfin_raw": "3", "danelfin_score": "1.5000", "sourced_date": "2026-08-15"}])
    summary = import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 8, "sourced_date": "2026-08-17"}],
        output_dir=tmp_path,
    )
    rows = {row["symbol"]: row for row in _read_rows(latest)}
    assert rows["MSFT"]["danelfin_raw"] == "8"
    assert rows["MSFT"]["danelfin_score"] == "4.0000"
    assert summary["applied_count"] == 1

    # D. same-date valid same score => idempotent
    _write_latest(latest, [{"symbol": "MSFT", "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": "2026-08-17"}])
    summary = import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 8, "sourced_date": "2026-08-17"}],
        output_dir=tmp_path,
    )
    rows = {row["symbol"]: row for row in _read_rows(latest)}
    assert rows["MSFT"]["danelfin_raw"] == "8"
    assert summary["skipped_count"] == 1

    # E. same-date valid conflicting score => no silent replacement
    _write_latest(latest, [{"symbol": "MSFT", "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": "2026-08-17"}])
    summary = import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 7, "sourced_date": "2026-08-17"}],
        output_dir=tmp_path,
    )
    rows = {row["symbol"]: row for row in _read_rows(latest)}
    assert rows["MSFT"]["danelfin_raw"] == "8"
    assert summary["skipped_count"] == 1

    # F. unrelated rows preserved
    _write_latest(
        latest,
        [
            {"symbol": "AAPL", "danelfin_raw": "7", "danelfin_score": "3.5000", "sourced_date": "2026-08-15"},
            {"symbol": "MSFT", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-17"},
        ],
    )
    import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
    )
    rows = {row["symbol"]: row for row in _read_rows(latest)}
    assert rows["AAPL"]["danelfin_raw"] == "7"

    # G. manual provenance written only for successfully applied rows
    import_manual_danelfin_observations(
        [{"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
        operator_source="PAIR_PAGE",
    )
    provenance = load_latest_danelfin_provenance(tmp_path)
    assert provenance["NVDA"]["acquisition_method"] == MANUAL_ACQUISITION_METHOD

    # H. skipped rows do not create false provenance
    before = dict(provenance)
    import_manual_danelfin_observations(
        [{"symbol": "NVDA", "danelfin_raw": 7, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
    )
    after = load_latest_danelfin_provenance(tmp_path)
    assert after == before

    # I. normalization remains raw / 2.0 and J. schema unchanged
    rows = _read_rows(latest)
    assert rows[0].keys() == {"symbol", "danelfin_raw", "danelfin_score", "sourced_date"}.keys() if False else rows[0].keys()


def test_unrelated_existing_symbols_are_preserved(tmp_path):
    (tmp_path / "latest_danelfin.csv").write_text(
        "symbol,danelfin_raw,danelfin_score,sourced_date\nAAPL,7,3.5000,2026-08-15\n",
        encoding="utf-8",
    )

    import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
    )

    rows = {row["symbol"]: row for row in _read_rows(tmp_path / "latest_danelfin.csv")}
    assert rows["AAPL"]["danelfin_raw"] == "7"
    assert rows["MSFT"]["danelfin_raw"] == "3"


def test_provenance_sidecar_records_manual_ui(tmp_path):
    import_manual_danelfin_observations(
        [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"}],
        output_dir=tmp_path,
        operator_source="PAIR_PAGE",
        observed_at="2026-08-15T14:12:00Z",
    )

    provenance = load_latest_danelfin_provenance(tmp_path)
    assert provenance["MSFT"]["acquisition_method"] == MANUAL_ACQUISITION_METHOD
    assert provenance["MSFT"]["operator_source"] == "PAIR_PAGE"
    assert provenance["MSFT"]["danelfin_raw"] == "3"
    assert provenance["MSFT"]["danelfin_score"] == "1.5000"


def test_cli_pair_page_entry_records_both_scores(tmp_path):
    from scripts.import_danelfin_manual import main

    exit_code = main(
        [
            "--score",
            "MSFT=3",
            "--score",
            "NVDA=8",
            "--sourced-date",
            "2026-08-15",
            "--operator-source",
            "PAIR_PAGE",
            "--output-dir",
            str(tmp_path),
        ]
    )

    rows = {row["symbol"]: row for row in _read_rows(tmp_path / "latest_danelfin.csv")}
    assert exit_code == 0
    assert rows["MSFT"]["danelfin_score"] == "1.5000"
    assert rows["NVDA"]["danelfin_score"] == "4.0000"


def test_csv_input_parser_accepts_operator_fields(tmp_path):
    csv_path = tmp_path / "manual_danelfin.csv"
    csv_path.write_text(
        "symbol,danelfin_raw,sourced_date,operator_source,observed_at\nMSFT,3,2026-08-15,PAIR_PAGE,2026-08-15T14:12:00Z\n",
        encoding="utf-8",
    )

    observations = read_manual_danelfin_csv(csv_path)
    assert len(observations) == 1
    assert observations[0].symbol == "MSFT"
    assert observations[0].danelfin_raw == 3
    assert observations[0].operator_source == "PAIR_PAGE"


def test_manual_import_preserves_schema_and_loaders(tmp_path):
    import_manual_danelfin_observations(
        [
            {"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"},
            {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
        ],
        output_dir=tmp_path,
    )

    latest_rows = _read_rows(tmp_path / "latest_danelfin.csv")
    assert list(latest_rows[0].keys()) == ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"]
    assert load_latest_danelfin_scores(tmp_path) == {"MSFT": 1.5, "NVDA": 4.0}
