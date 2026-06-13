from __future__ import annotations

import csv
from pathlib import Path

from src.pis.change_detection import CHANGE_HEADERS, SUMMARY_HEADERS
from src.pis.recommendation_lineage import (
    LINEAGE_HEADERS,
    LINEAGE_SUMMARY_HEADERS,
    compute_recommendation_lineage,
    pis_lineage_for_snapshot,
    pis_lineage_latest,
    pis_lineage_summary,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _build_change_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    changes_root = tmp_path / "data" / "history" / "pis" / "changes"
    change_records = changes_root / "change_records.csv"
    change_summary = changes_root / "change_summary.csv"
    lineage_root = tmp_path / "data" / "history" / "pis" / "lineage"

    snapshot_id = "S2"
    prior_snapshot_id = "S1"
    snapshot_date = "2026-06-11"
    prior_snapshot_date = "2026-06-10"

    _write_csv(
        change_records,
        CHANGE_HEADERS,
        [
            {
                "change_id": "CHG-1",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": prior_snapshot_date,
                "change_type": "INCREASED",
                "symbol": "VRT",
                "old_quantity": "10",
                "new_quantity": "12",
                "old_market_value": "1000",
                "new_market_value": "1240",
                "delta_quantity": "2",
                "delta_market_value": "240",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "change_id": "CHG-2",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": prior_snapshot_date,
                "change_type": "EXITED_POSITION",
                "symbol": "MSFT",
                "old_quantity": "8",
                "new_quantity": "0",
                "old_market_value": "900",
                "new_market_value": "0",
                "delta_quantity": "-8",
                "delta_market_value": "-900",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "change_id": "CHG-3",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": prior_snapshot_date,
                "change_type": "NEW_POSITION",
                "symbol": "NVDA",
                "old_quantity": "0",
                "new_quantity": "3",
                "old_market_value": "0",
                "new_market_value": "990",
                "delta_quantity": "3",
                "delta_market_value": "990",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "change_id": "CHG-4",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": prior_snapshot_date,
                "change_type": "REDUCED",
                "symbol": "XYZ",
                "old_quantity": "15",
                "new_quantity": "10",
                "old_market_value": "1500",
                "new_market_value": "1000",
                "delta_quantity": "-5",
                "delta_market_value": "-500",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
        ],
    )

    _write_csv(
        change_summary,
        SUMMARY_HEADERS,
        [
            {
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": prior_snapshot_date,
                "portfolio_value_change": "-170",
                "cash_change": "100",
                "position_count_change": "0",
                "new_holdings_count": "1",
                "exited_holdings_count": "1",
                "increased_holdings_count": "1",
                "reduced_holdings_count": "1",
                "unchanged_holdings_count": "0",
                "created_at": "2026-06-11T12:00:00+00:00",
            }
        ],
    )

    return change_records, change_summary, lineage_root


def _base_candidates() -> list[dict[str, object]]:
    return [
        {
            "recommendation_id": "REC-HIGH-VRT",
            "source": "PAP",
            "recommendation_date": "2026-06-08",
            "symbol": "VRT",
            "direction": "BUY",
            "matched_recommendation": "BUY VRT",
            "theme_symbols": [],
        },
        {
            "recommendation_id": "REC-MEDIUM-MSFT",
            "source": "CRA",
            "recommendation_date": "2026-05-25",
            "symbol": "MSFT",
            "direction": "REDUCE",
            "matched_recommendation": "REDUCE MSFT",
            "theme_symbols": [],
        },
        {
            "recommendation_id": "REC-LOW-THEME",
            "source": "RECOMMENDATION_HISTORY",
            "recommendation_date": "2026-06-10",
            "symbol": "",
            "direction": "",
            "matched_recommendation": "Semiconductor concentration context",
            "theme_symbols": ["NVDA", "AMD"],
        },
    ]


def test_lineage_confidence_levels_and_unmatched(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root = _build_change_fixture(tmp_path)

    compute_recommendation_lineage(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=_base_candidates(),
    )

    detail = pis_lineage_for_snapshot(
        "S2",
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=_base_candidates(),
    )

    by_symbol = {row["symbol"]: row for row in detail["matches"]}
    assert by_symbol["VRT"]["confidence"] == "HIGH"
    assert by_symbol["MSFT"]["confidence"] == "MEDIUM"
    assert by_symbol["NVDA"]["confidence"] == "LOW"

    unmatched_symbols = [row["symbol"] for row in detail["unmatched"]]
    assert unmatched_symbols == ["XYZ"]


def test_multiple_candidates_and_ranking(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root = _build_change_fixture(tmp_path)

    candidates = _base_candidates() + [
        {
            "recommendation_id": "REC-VRT-OLDER",
            "source": "CRA",
            "recommendation_date": "2026-05-20",
            "symbol": "VRT",
            "direction": "BUY",
            "matched_recommendation": "BUY VRT (old)",
            "theme_symbols": [],
        }
    ]

    compute_recommendation_lineage(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=candidates,
    )

    detail = pis_lineage_for_snapshot(
        "S2",
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=candidates,
    )

    vrt = next(row for row in detail["matches"] if row["symbol"] == "VRT")
    assert vrt["matched_recommendation_id"] == "REC-HIGH-VRT"
    assert vrt["confidence"] == "HIGH"


def test_high_confidence_demotes_when_competing_recommendations(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root = _build_change_fixture(tmp_path)

    candidates = _base_candidates() + [
        {
            "recommendation_id": "REC-HIGH-VRT-COMPETE",
            "source": "DEPLOYMENT_QUEUE",
            "recommendation_date": "2026-06-09",
            "symbol": "VRT",
            "direction": "BUY",
            "matched_recommendation": "DEPLOY VRT",
            "theme_symbols": [],
        }
    ]

    compute_recommendation_lineage(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=candidates,
    )

    detail = pis_lineage_for_snapshot(
        "S2",
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=candidates,
    )

    vrt = next(row for row in detail["matches"] if row["symbol"] == "VRT")
    assert vrt["confidence"] == "MEDIUM"


def test_api_payload_shapes(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root = _build_change_fixture(tmp_path)
    compute_recommendation_lineage(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=_base_candidates(),
    )

    latest = pis_lineage_latest(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=_base_candidates(),
    )
    summary = pis_lineage_summary(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=_base_candidates(),
    )

    assert "summary" in latest
    assert "matches" in latest
    assert "unmatched" in latest
    assert "source_breakdown" in latest
    assert len(summary["summary"]) == 1


def test_empty_history_behavior(tmp_path: Path) -> None:
    changes_root = tmp_path / "data" / "history" / "pis" / "changes"
    change_records = changes_root / "change_records.csv"
    change_summary = changes_root / "change_summary.csv"
    lineage_root = tmp_path / "data" / "history" / "pis" / "lineage"

    _write_csv(change_records, CHANGE_HEADERS, [])
    _write_csv(change_summary, SUMMARY_HEADERS, [])

    compute_recommendation_lineage(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=[],
    )

    # persisted files exist with headers
    assert (lineage_root / "lineage_records.csv").exists()
    assert (lineage_root / "lineage_summary.csv").exists()
    assert list(csv.DictReader((lineage_root / "lineage_records.csv").open("r", encoding="utf-8", newline=""))) == []
    assert list(csv.DictReader((lineage_root / "lineage_summary.csv").open("r", encoding="utf-8", newline=""))) == []

    latest = pis_lineage_latest(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=[],
    )

    assert latest["summary"] is None
    assert latest["matches"] == []
    assert latest["unmatched"] == []


def test_lineage_csv_contract_headers(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root = _build_change_fixture(tmp_path)
    compute_recommendation_lineage(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        repo_root=tmp_path,
        candidates_override=_base_candidates(),
    )

    with (lineage_root / "lineage_records.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == LINEAGE_HEADERS
    with (lineage_root / "lineage_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == LINEAGE_SUMMARY_HEADERS


def test_run_outcome_ui_contains_lineage_api_routes() -> None:
    root = Path(__file__).resolve().parents[1]
    server_py = (root / "scripts" / "run_outcome_ui.py").read_text(encoding="utf-8")

    assert "/api/pis/lineage/latest" in server_py
    assert "/api/pis/lineage-summary" in server_py
    assert "/api/pis/lineage/" in server_py
