from __future__ import annotations

import csv
from pathlib import Path

from src.pis.change_detection import CHANGE_HEADERS, SUMMARY_HEADERS
from src.pis.performance_attribution import (
    ATTRIBUTION_RECORD_HEADERS,
    ATTRIBUTION_SUMMARY_HEADERS,
    AttributionThresholds,
    classify_outcome,
    compute_performance_attribution,
    pis_attribution_history,
    pis_attribution_latest,
    pis_attribution_summary,
)
from src.pis.recommendation_lineage import LINEAGE_HEADERS, LINEAGE_SUMMARY_HEADERS


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _build_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    changes_root = tmp_path / "data" / "history" / "pis" / "changes"
    lineage_root = tmp_path / "data" / "history" / "pis" / "lineage"
    attribution_root = tmp_path / "data" / "history" / "pis" / "attribution"

    change_records = changes_root / "change_records.csv"
    change_summary = changes_root / "change_summary.csv"

    snapshot_id = "S2"
    prior_snapshot_id = "S1"
    snapshot_date = "2026-06-11"

    _write_csv(
        change_records,
        CHANGE_HEADERS,
        [
            {
                "change_id": "CHG-1",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": "2026-06-10",
                "change_type": "INCREASED",
                "symbol": "AAPL",
                "old_quantity": "10",
                "new_quantity": "12",
                "old_market_value": "1000",
                "new_market_value": "1200",
                "delta_quantity": "2",
                "delta_market_value": "200",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "change_id": "CHG-2",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": "2026-06-10",
                "change_type": "REDUCED",
                "symbol": "MSFT",
                "old_quantity": "8",
                "new_quantity": "6",
                "old_market_value": "800",
                "new_market_value": "680",
                "delta_quantity": "-2",
                "delta_market_value": "-120",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "change_id": "CHG-3",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": "2026-06-10",
                "change_type": "INCREASED",
                "symbol": "NVDA",
                "old_quantity": "5",
                "new_quantity": "6",
                "old_market_value": "700",
                "new_market_value": "500",
                "delta_quantity": "1",
                "delta_market_value": "-200",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "change_id": "CHG-4",
                "snapshot_id": snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": "2026-06-10",
                "change_type": "NEW_POSITION",
                "symbol": "QQQ",
                "old_quantity": "0",
                "new_quantity": "1",
                "old_market_value": "0",
                "new_market_value": "10",
                "delta_quantity": "1",
                "delta_market_value": "10",
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
                "prior_snapshot_date": "2026-06-10",
                "portfolio_value_change": "-110",
                "cash_change": "80",
                "position_count_change": "0",
                "new_holdings_count": "1",
                "exited_holdings_count": "0",
                "increased_holdings_count": "2",
                "reduced_holdings_count": "1",
                "unchanged_holdings_count": "0",
                "created_at": "2026-06-11T12:00:00+00:00",
            }
        ],
    )

    _write_csv(
        lineage_root / "lineage_records.csv",
        LINEAGE_HEADERS,
        [
            {
                "lineage_id": "LIN-1",
                "snapshot_id": snapshot_id,
                "change_id": "CHG-1",
                "symbol": "AAPL",
                "change_type": "INCREASED",
                "matched_recommendation_id": "REC-1",
                "matched_recommendation": "Increase AAPL",
                "recommendation_source": "PAP",
                "recommendation_date": "2026-06-09",
                "confidence": "HIGH",
                "days_between": "2",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "lineage_id": "LIN-2",
                "snapshot_id": snapshot_id,
                "change_id": "CHG-2",
                "symbol": "MSFT",
                "change_type": "REDUCED",
                "matched_recommendation_id": "REC-2",
                "matched_recommendation": "Reduce MSFT",
                "recommendation_source": "CRA",
                "recommendation_date": "2026-06-08",
                "confidence": "MEDIUM",
                "days_between": "3",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "lineage_id": "LIN-3",
                "snapshot_id": snapshot_id,
                "change_id": "CHG-3",
                "symbol": "NVDA",
                "change_type": "INCREASED",
                "matched_recommendation_id": "REC-3",
                "matched_recommendation": "Increase NVDA",
                "recommendation_source": "DEPLOYMENT_QUEUE",
                "recommendation_date": "2026-06-09",
                "confidence": "LOW",
                "days_between": "2",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
            {
                "lineage_id": "LIN-4",
                "snapshot_id": snapshot_id,
                "change_id": "CHG-4",
                "symbol": "QQQ",
                "change_type": "NEW_POSITION",
                "matched_recommendation_id": "REC-4",
                "matched_recommendation": "Probe QQQ",
                "recommendation_source": "PAP",
                "recommendation_date": "2026-06-10",
                "confidence": "LOW",
                "days_between": "1",
                "created_at": "2026-06-11T12:00:00+00:00",
            },
        ],
    )

    _write_csv(
        lineage_root / "lineage_summary.csv",
        LINEAGE_SUMMARY_HEADERS,
        [
            {
                "snapshot_id": snapshot_id,
                "snapshot_date": snapshot_date,
                "total_changes": "4",
                "matched_high": "1",
                "matched_medium": "1",
                "matched_low": "2",
                "unmatched": "0",
                "matched_pap": "2",
                "matched_cra": "1",
                "matched_deployment_queue": "1",
                "matched_reduction_queue": "0",
                "matched_dil": "0",
                "matched_other": "0",
                "created_at": "2026-06-11T12:00:00+00:00",
            }
        ],
    )

    return change_records, change_summary, lineage_root, attribution_root


def test_outcome_classification_is_deterministic() -> None:
    thresholds = AttributionThresholds(winner_min_score=100.0, loser_max_score=-100.0)
    assert classify_outcome(120.0, thresholds=thresholds) == "WINNER"
    assert classify_outcome(-120.0, thresholds=thresholds) == "LOSER"
    assert classify_outcome(15.0, thresholds=thresholds) == "NEUTRAL"


def test_compute_and_latest_payload(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root, attribution_root = _build_fixture(tmp_path)
    thresholds = AttributionThresholds(winner_min_score=100.0, loser_max_score=-100.0)

    compute_performance_attribution(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=tmp_path,
        thresholds=thresholds,
    )

    latest = pis_attribution_latest(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=tmp_path,
        thresholds=thresholds,
    )

    assert latest["summary"] is not None
    assert latest["summary"]["matched_recommendations"] == 4
    assert latest["summary"]["winner_count"] == 2
    assert latest["summary"]["neutral_count"] == 1
    assert latest["summary"]["loser_count"] == 1
    assert latest["summary"]["total_directional_attribution"] == 130.0

    outcomes_by_symbol = {row["symbol"]: row["outcome"] for row in latest["records"]}
    assert outcomes_by_symbol["AAPL"] == "WINNER"
    assert outcomes_by_symbol["MSFT"] == "WINNER"
    assert outcomes_by_symbol["NVDA"] == "LOSER"
    assert outcomes_by_symbol["QQQ"] == "NEUTRAL"

    assert latest["top_winning_recommendations"][0]["matched_recommendation_id"] == "REC-1"
    assert latest["top_losing_recommendations"][0]["matched_recommendation_id"] == "REC-3"


def test_history_and_aggregate_summary_payloads(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root, attribution_root = _build_fixture(tmp_path)
    thresholds = AttributionThresholds(winner_min_score=100.0, loser_max_score=-100.0)

    compute_performance_attribution(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=tmp_path,
        thresholds=thresholds,
    )

    history = pis_attribution_history(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=tmp_path,
        thresholds=thresholds,
    )
    aggregate = pis_attribution_summary(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=tmp_path,
        thresholds=thresholds,
    )

    assert len(history["summary"]) == 1
    assert history["summary"][0]["top_winner_symbol"] == "AAPL"
    assert history["summary"][0]["top_loser_symbol"] == "NVDA"

    assert aggregate["summary"]["snapshot_count"] == 1
    assert aggregate["summary"]["matched_recommendations"] == 4
    assert aggregate["summary"]["winner_count"] == 2
    assert aggregate["summary"]["neutral_count"] == 1
    assert aggregate["summary"]["loser_count"] == 1

    pap = next(row for row in aggregate["source_performance"] if row["source"] == "PAP")
    assert pap["matched_count"] == 2
    assert pap["winner_count"] == 1
    assert pap["neutral_count"] == 1


def test_csv_contract_headers(tmp_path: Path) -> None:
    change_records, change_summary, lineage_root, attribution_root = _build_fixture(tmp_path)

    compute_performance_attribution(
        change_records_path=change_records,
        change_summary_path=change_summary,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=tmp_path,
    )

    with (attribution_root / "attribution_records.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == ATTRIBUTION_RECORD_HEADERS
    with (attribution_root / "attribution_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == ATTRIBUTION_SUMMARY_HEADERS


def test_run_outcome_ui_contains_attribution_routes() -> None:
    root = Path(__file__).resolve().parents[1]
    server_py = (root / "scripts" / "run_outcome_ui.py").read_text(encoding="utf-8")

    assert "/api/pis/attribution/latest" in server_py
    assert "/api/pis/attribution/history" in server_py
    assert "/api/pis/attribution-summary" in server_py
