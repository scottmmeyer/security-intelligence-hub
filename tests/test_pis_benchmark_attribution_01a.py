from __future__ import annotations

import csv
from pathlib import Path

from src.pis.benchmark_attribution import (
    BENCHMARK_RETURN_SERIES_HEADERS,
    BenchmarkAttributionConfig,
    compute_benchmark_return_series,
    pis_benchmark_latest,
    pis_benchmark_returns,
    pis_benchmark_summary,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _canonical_headers() -> list[str]:
    return [
        "snapshot_date",
        "canonical_snapshot_id",
        "governance_status",
        "selection_policy",
        "selection_reason",
        "source_file",
        "portfolio_value",
        "cash",
        "position_count",
    ]


class _FixtureProvider:
    def __init__(self, prices: dict[str, float]) -> None:
        self._prices = prices

    def get_prices(self, *, symbol: str, start_date: str, end_date: str) -> dict[str, float]:
        _ = symbol
        return {d: p for d, p in self._prices.items() if start_date <= d <= end_date}


def test_same_day_alignment_and_return_math(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.csv"
    output = tmp_path / "benchmark_return_series.csv"
    _write_csv(
        canonical,
        _canonical_headers(),
        [
            {
                "snapshot_date": "2026-06-12",
                "canonical_snapshot_id": "S3",
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
                "canonical_snapshot_id": "S2",
                "governance_status": "PASS",
                "selection_policy": "PASS",
                "selection_reason": "x",
                "source_file": "x",
                "portfolio_value": "1000",
                "cash": "100",
                "position_count": "5",
            },
            {
                "snapshot_date": "2026-06-10",
                "canonical_snapshot_id": "S1",
                "governance_status": "PASS",
                "selection_policy": "PASS",
                "selection_reason": "x",
                "source_file": "x",
                "portfolio_value": "950",
                "cash": "100",
                "position_count": "5",
            },
        ],
    )

    provider = _FixtureProvider(
        {
            "2026-06-10": 190.0,
            "2026-06-11": 200.0,
            "2026-06-12": 220.0,
        }
    )
    result = compute_benchmark_return_series(
        canonical_output_path=canonical,
        output_path=output,
        config=BenchmarkAttributionConfig(benchmark_symbol="SPY"),
        price_provider=provider,
    )

    assert result["summary"]["interval_count"] == 2
    latest = result["series"][0]
    assert latest["snapshot_date"] == "2026-06-12"
    assert latest["benchmark_entry_date"] == "2026-06-11"
    assert latest["benchmark_exit_date"] == "2026-06-12"
    assert latest["benchmark_return_pct"] == 10.0
    assert latest["portfolio_return_pct"] == 10.0
    assert latest["excess_return_pct"] == 0.0
    assert latest["data_quality_status"] == "OK"


def test_weekend_nearest_prior_alignment(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.csv"
    output = tmp_path / "benchmark_return_series.csv"
    _write_csv(
        canonical,
        _canonical_headers(),
        [
            {
                "snapshot_date": "2026-06-15",
                "canonical_snapshot_id": "S2",
                "governance_status": "PASS",
                "selection_policy": "PASS",
                "selection_reason": "x",
                "source_file": "x",
                "portfolio_value": "1010",
                "cash": "100",
                "position_count": "5",
            },
            {
                "snapshot_date": "2026-06-14",
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

    provider = _FixtureProvider(
        {
            "2026-06-13": 300.0,
            "2026-06-15": 303.0,
        }
    )
    result = compute_benchmark_return_series(
        canonical_output_path=canonical,
        output_path=output,
        config=BenchmarkAttributionConfig(benchmark_symbol="SPY"),
        price_provider=provider,
    )

    row = result["series"][0]
    assert row["benchmark_entry_date"] == "2026-06-13"
    assert row["benchmark_exit_date"] == "2026-06-15"
    assert row["benchmark_return_pct"] == 1.0
    assert row["portfolio_return_pct"] == 1.0
    assert row["excess_return_pct"] == 0.0


def test_missing_benchmark_data_behavior(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.csv"
    output = tmp_path / "benchmark_return_series.csv"
    _write_csv(
        canonical,
        _canonical_headers(),
        [
            {
                "snapshot_date": "2026-06-12",
                "canonical_snapshot_id": "S2",
                "governance_status": "PASS",
                "selection_policy": "PASS",
                "selection_reason": "x",
                "source_file": "x",
                "portfolio_value": "1010",
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

    provider = _FixtureProvider({"2026-06-12": 101.0})
    result = compute_benchmark_return_series(
        canonical_output_path=canonical,
        output_path=output,
        config=BenchmarkAttributionConfig(benchmark_symbol="SPY"),
        price_provider=provider,
    )

    row = result["series"][0]
    assert row["data_quality_status"] == "MISSING_BENCHMARK_ENTRY"
    assert row["benchmark_return_pct"] == 0.0
    assert row["portfolio_return_pct"] == 1.0
    assert row["excess_return_pct"] == 1.0


def test_csv_persistence_contract_and_api_payloads(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.csv"
    output = tmp_path / "benchmark_return_series.csv"
    _write_csv(
        canonical,
        _canonical_headers(),
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

    provider = _FixtureProvider({"2026-06-11": 200.0, "2026-06-12": 220.0})
    compute_benchmark_return_series(
        canonical_output_path=canonical,
        output_path=output,
        config=BenchmarkAttributionConfig(benchmark_symbol="SPY"),
        price_provider=provider,
    )

    with output.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == BENCHMARK_RETURN_SERIES_HEADERS

    returns_payload = pis_benchmark_returns(canonical_output_path=canonical, output_path=output)
    latest_payload = pis_benchmark_latest(canonical_output_path=canonical, output_path=output)
    summary_payload = pis_benchmark_summary(canonical_output_path=canonical, output_path=output)

    assert "series" in returns_payload
    assert returns_payload["benchmark_symbol"] == "SPY"
    assert latest_payload["latest_portfolio_excess_return"] is not None
    assert "summary" in summary_payload
    assert "average_excess_return_pct" in summary_payload["summary"]


def test_api_route_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    server_py = (root / "scripts" / "run_outcome_ui.py").read_text(encoding="utf-8")

    assert "/api/pis/benchmark-attribution/returns" in server_py
    assert "/api/pis/benchmark-attribution/latest" in server_py
    assert "/api/pis/benchmark-attribution-summary" in server_py
