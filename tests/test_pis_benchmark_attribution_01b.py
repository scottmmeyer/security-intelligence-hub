from __future__ import annotations

import csv
from pathlib import Path

from src.pis.benchmark_attribution import (
    RECOMMENDATION_BENCHMARK_HEADERS,
    SOURCE_BENCHMARK_SUMMARY_HEADERS,
    compute_benchmark_recommendation_attribution,
    pis_benchmark_latest,
    pis_benchmark_recommendations,
    pis_benchmark_sources,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _benchmark_headers() -> list[str]:
    return [
        "snapshot_date",
        "prior_snapshot_date",
        "benchmark_symbol",
        "benchmark_entry_date",
        "benchmark_exit_date",
        "benchmark_entry_price",
        "benchmark_exit_price",
        "benchmark_return_pct",
        "portfolio_return_pct",
        "excess_return_pct",
        "alignment_policy",
        "data_quality_status",
    ]


def _attribution_headers() -> list[str]:
    return [
        "attribution_id",
        "snapshot_id",
        "snapshot_date",
        "change_id",
        "symbol",
        "change_type",
        "matched_recommendation_id",
        "matched_recommendation",
        "recommendation_source",
        "recommendation_date",
        "confidence",
        "old_market_value",
        "new_market_value",
        "delta_market_value",
        "directional_attribution",
        "directional_return_pct",
        "outcome",
        "created_at",
    ]


def _change_headers() -> list[str]:
    return [
        "change_id",
        "snapshot_id",
        "prior_snapshot_id",
        "snapshot_date",
        "prior_snapshot_date",
        "change_type",
        "symbol",
        "old_quantity",
        "new_quantity",
        "old_market_value",
        "new_market_value",
        "delta_quantity",
        "delta_market_value",
        "created_at",
    ]


def _seed_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    benchmark_path = tmp_path / "benchmark_return_series.csv"
    attribution_path = tmp_path / "attribution_records.csv"
    change_path = tmp_path / "change_records.csv"
    recommendation_output = tmp_path / "recommendation_benchmark_records.csv"
    source_output = tmp_path / "source_benchmark_summary.csv"

    _write_csv(
        benchmark_path,
        _benchmark_headers(),
        [
            {
                "snapshot_date": "2026-06-12",
                "prior_snapshot_date": "2026-06-11",
                "benchmark_symbol": "SPY",
                "benchmark_entry_date": "2026-06-11",
                "benchmark_exit_date": "2026-06-12",
                "benchmark_entry_price": "100",
                "benchmark_exit_price": "102",
                "benchmark_return_pct": "2.0",
                "portfolio_return_pct": "1.5",
                "excess_return_pct": "-0.5",
                "alignment_policy": "NEAREST_PRIOR_TRADING_DAY",
                "data_quality_status": "OK",
            },
            {
                "snapshot_date": "2026-06-11",
                "prior_snapshot_date": "2026-06-10",
                "benchmark_symbol": "SPY",
                "benchmark_entry_date": "2026-06-10",
                "benchmark_exit_date": "",
                "benchmark_entry_price": "99",
                "benchmark_exit_price": "0",
                "benchmark_return_pct": "0.0",
                "portfolio_return_pct": "0.9",
                "excess_return_pct": "0.9",
                "alignment_policy": "NEAREST_PRIOR_TRADING_DAY",
                "data_quality_status": "MISSING_BENCHMARK_EXIT",
            },
        ],
    )

    _write_csv(
        attribution_path,
        _attribution_headers(),
        [
            {
                "attribution_id": "ATTR-1",
                "snapshot_id": "S2",
                "snapshot_date": "2026-06-12",
                "change_id": "CH-1",
                "symbol": "AAA",
                "change_type": "INCREASED",
                "matched_recommendation_id": "REC-1",
                "matched_recommendation": "Increase AAA",
                "recommendation_source": "PAP",
                "recommendation_date": "2026-06-11",
                "confidence": "HIGH",
                "old_market_value": "1000",
                "new_market_value": "1100",
                "delta_market_value": "100",
                "directional_attribution": "200",
                "directional_return_pct": "5.0",
                "outcome": "WINNER",
                "created_at": "2026-06-12T00:00:00+00:00",
            },
            {
                "attribution_id": "ATTR-2",
                "snapshot_id": "S2",
                "snapshot_date": "2026-06-12",
                "change_id": "CH-2",
                "symbol": "BBB",
                "change_type": "REDUCED",
                "matched_recommendation_id": "REC-2",
                "matched_recommendation": "Trim BBB",
                "recommendation_source": "PAP",
                "recommendation_date": "2026-06-11",
                "confidence": "MEDIUM",
                "old_market_value": "800",
                "new_market_value": "760",
                "delta_market_value": "-40",
                "directional_attribution": "-50",
                "directional_return_pct": "-1.0",
                "outcome": "LOSER",
                "created_at": "2026-06-12T00:00:00+00:00",
            },
            {
                "attribution_id": "ATTR-3",
                "snapshot_id": "S1",
                "snapshot_date": "2026-06-11",
                "change_id": "CH-3",
                "symbol": "CCC",
                "change_type": "INCREASED",
                "matched_recommendation_id": "REC-3",
                "matched_recommendation": "Add CCC",
                "recommendation_source": "CRA",
                "recommendation_date": "2026-06-10",
                "confidence": "LOW",
                "old_market_value": "700",
                "new_market_value": "740",
                "delta_market_value": "40",
                "directional_attribution": "80",
                "directional_return_pct": "3.0",
                "outcome": "WINNER",
                "created_at": "2026-06-11T00:00:00+00:00",
            },
        ],
    )

    _write_csv(
        change_path,
        _change_headers(),
        [
            {
                "change_id": "CH-1",
                "snapshot_id": "S2",
                "prior_snapshot_id": "S1",
                "snapshot_date": "2026-06-12",
                "prior_snapshot_date": "2026-06-11",
                "change_type": "INCREASED",
                "symbol": "AAA",
                "old_quantity": "10",
                "new_quantity": "11",
                "old_market_value": "1000",
                "new_market_value": "1100",
                "delta_quantity": "1",
                "delta_market_value": "100",
                "created_at": "2026-06-12T00:00:00+00:00",
            },
            {
                "change_id": "CH-2",
                "snapshot_id": "S2",
                "prior_snapshot_id": "S1",
                "snapshot_date": "2026-06-12",
                "prior_snapshot_date": "2026-06-11",
                "change_type": "REDUCED",
                "symbol": "BBB",
                "old_quantity": "9",
                "new_quantity": "8",
                "old_market_value": "800",
                "new_market_value": "760",
                "delta_quantity": "-1",
                "delta_market_value": "-40",
                "created_at": "2026-06-12T00:00:00+00:00",
            },
            {
                "change_id": "CH-3",
                "snapshot_id": "S1",
                "prior_snapshot_id": "S0",
                "snapshot_date": "2026-06-11",
                "prior_snapshot_date": "2026-06-10",
                "change_type": "INCREASED",
                "symbol": "CCC",
                "old_quantity": "7",
                "new_quantity": "8",
                "old_market_value": "700",
                "new_market_value": "740",
                "delta_quantity": "1",
                "delta_market_value": "40",
                "created_at": "2026-06-11T00:00:00+00:00",
            },
        ],
    )

    return benchmark_path, attribution_path, change_path, recommendation_output, source_output


def test_recommendation_join_and_excess_math(tmp_path: Path) -> None:
    benchmark_path, attribution_path, change_path, recommendation_output, source_output = _seed_fixture(tmp_path)

    payload = compute_benchmark_recommendation_attribution(
        benchmark_series_path=benchmark_path,
        attribution_records_path=attribution_path,
        change_records_path=change_path,
        recommendation_output_path=recommendation_output,
        source_output_path=source_output,
    )

    records = payload["recommendation_records"]
    assert len(records) == 3

    rec1 = next(r for r in records if r["recommendation_id"] == "REC-1")
    assert rec1["prior_snapshot_date"] == "2026-06-11"
    assert rec1["benchmark_return_pct"] == 2.0
    assert rec1["directional_return_pct"] == 5.0
    assert rec1["recommendation_excess_return_pct"] == 3.0
    assert rec1["data_quality_status"] == "OK"


def test_source_aggregation_and_quality_exclusion(tmp_path: Path) -> None:
    benchmark_path, attribution_path, change_path, recommendation_output, source_output = _seed_fixture(tmp_path)

    payload = compute_benchmark_recommendation_attribution(
        benchmark_series_path=benchmark_path,
        attribution_records_path=attribution_path,
        change_records_path=change_path,
        recommendation_output_path=recommendation_output,
        source_output_path=source_output,
    )

    quality = payload["quality"]
    assert quality["included_rows"] == 2
    assert quality["excluded_rows"] == 1
    assert quality["excluded_reason_counts"] == {"MISSING_BENCHMARK_EXIT": 1}

    pap = next(r for r in payload["source_summary"] if r["recommendation_source"] == "PAP")
    assert pap["matched_recommendations"] == 2
    assert pap["included_rows"] == 2
    assert pap["excluded_rows"] == 0
    assert pap["avg_directional_return_pct"] == 2.0
    assert pap["avg_benchmark_return_pct"] == 2.0
    assert pap["avg_excess_return_pct"] == 0.0
    assert pap["positive_alpha_count"] == 1
    assert pap["negative_alpha_count"] == 1
    assert pap["alpha_win_rate"] == 50.0
    assert pap["total_directional_attribution"] == 150.0

    cra = next(r for r in payload["source_summary"] if r["recommendation_source"] == "CRA")
    assert cra["included_rows"] == 0
    assert cra["excluded_rows"] == 1
    assert cra["avg_excess_return_pct"] == 0.0


def test_csv_contracts_and_api_payloads(tmp_path: Path) -> None:
    benchmark_path, attribution_path, change_path, recommendation_output, source_output = _seed_fixture(tmp_path)

    compute_benchmark_recommendation_attribution(
        benchmark_series_path=benchmark_path,
        attribution_records_path=attribution_path,
        change_records_path=change_path,
        recommendation_output_path=recommendation_output,
        source_output_path=source_output,
    )

    with recommendation_output.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == RECOMMENDATION_BENCHMARK_HEADERS

    with source_output.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == SOURCE_BENCHMARK_SUMMARY_HEADERS

    rec_payload = pis_benchmark_recommendations(
        benchmark_series_path=benchmark_path,
        attribution_records_path=attribution_path,
        change_records_path=change_path,
        recommendation_output_path=recommendation_output,
        source_output_path=source_output,
    )
    src_payload = pis_benchmark_sources(
        benchmark_series_path=benchmark_path,
        attribution_records_path=attribution_path,
        change_records_path=change_path,
        recommendation_output_path=recommendation_output,
        source_output_path=source_output,
    )

    assert "records" in rec_payload
    assert rec_payload["quality"]["included_rows"] == 2
    assert "source_summary" in src_payload
    assert src_payload["quality"]["excluded_rows"] == 1


def test_latest_payload_surfaces_rankings_and_quality(tmp_path: Path) -> None:
    benchmark_path, attribution_path, change_path, recommendation_output, source_output = _seed_fixture(tmp_path)

    _write_csv(
        tmp_path / "canonical.csv",
        [
            "snapshot_date",
            "canonical_snapshot_id",
            "governance_status",
            "selection_policy",
            "selection_reason",
            "source_file",
            "portfolio_value",
            "cash",
            "position_count",
        ],
        [
            {
                "snapshot_date": "2026-06-12",
                "canonical_snapshot_id": "S2",
                "governance_status": "PASS",
                "selection_policy": "PASS",
                "selection_reason": "x",
                "source_file": "x",
                "portfolio_value": "1100",
                "cash": "100",
                "position_count": "5",
            },
            {
                "snapshot_date": "2026-06-11",
                "canonical_snapshot_id": "S1",
                "governance_status": "PASS",
                "selection_policy": "PASS",
                "selection_reason": "x",
                "source_file": "x",
                "portfolio_value": "1000",
                "cash": "100",
                "position_count": "5",
            },
        ],
    )

    latest = pis_benchmark_latest(
        canonical_output_path=tmp_path / "canonical.csv",
        output_path=benchmark_path,
        benchmark_series_path=benchmark_path,
        attribution_records_path=attribution_path,
        change_records_path=change_path,
        recommendation_output_path=recommendation_output,
        source_output_path=source_output,
    )

    assert latest["latest_portfolio_excess_return"] is not None
    assert latest["quality"]["included_rows"] == 2
    assert latest["top_positive_alpha_recommendations"][0]["recommendation_id"] == "REC-1"
    assert latest["worst_negative_alpha_recommendations"][0]["recommendation_id"] == "REC-2"
    assert latest["source_alpha_ranking"][0]["recommendation_source"] == "PAP"


def test_api_route_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    server_py = (root / "scripts" / "run_outcome_ui.py").read_text(encoding="utf-8")

    assert "/api/pis/benchmark-attribution/recommendations" in server_py
    assert "/api/pis/benchmark-attribution/sources" in server_py
    assert "/api/pis/benchmark-attribution/latest" in server_py
