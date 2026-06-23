from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from src.portfolio.ess_coverage import build_ess_coverage_gap_warning


SIGNAL_HEADERS = [
    "snapshot_date",
    "created_at_utc",
    "run_id",
    "provider",
    "source_file",
    "symbol",
    "coverage_domain",
    "signal_coverage_status",
    "starmine_ess_text",
    "starmine_ess_numeric",
    "starmine_ess_numeric_estimated",
    "starmine_ess_source_type",
]

BASE_UNIVERSE_HEADERS = ["symbol"]


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_present_symbol_with_fresh_starmine_is_not_false_positive(tmp_path: Path) -> None:
    snapshot_date = date(2026, 6, 17)
    base_universe = tmp_path / "data" / "current" / "base_equity_universe.csv"
    _write_csv(base_universe, BASE_UNIVERSE_HEADERS, [{"symbol": "MU"}])

    signal_snapshot = tmp_path / "data" / "current" / "signal_snapshot.csv"
    _write_csv(
        signal_snapshot,
        SIGNAL_HEADERS,
        [
            {
                "snapshot_date": "2026-06-17",
                "created_at_utc": "2026-06-17T11:00:00+00:00",
                "run_id": "intake-sm",
                "provider": "FIDELITY",
                "source_file": "EquitySummaryScores.csv",
                "symbol": "MU",
                "coverage_domain": "STARMINE_COVERED",
                "signal_coverage_status": "COVERED",
                "starmine_ess_text": "VERY_BULLISH",
                "starmine_ess_numeric": "5.0",
                "starmine_ess_numeric_estimated": "True",
                "starmine_ess_source_type": "TEXT_MAPPED",
            }
        ],
    )

    holdings_path = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "PAR-20260617-TEST" / "holdings.csv"
    _write_csv(
        holdings_path,
        ["symbol", "asset_class", "description", "percent_of_portfolio"],
        [
            {
                "symbol": "MU",
                "asset_class": "EQUITIES",
                "description": "Micron",
                "percent_of_portfolio": "6.4",
            }
        ],
    )

    warning = build_ess_coverage_gap_warning(
        snapshot_date=snapshot_date,
        signal_snapshot_path=signal_snapshot,
        analysis_runs_root=tmp_path / "data" / "portfolio_ingestion" / "analysis_runs",
        base_universe_csv=base_universe,
    )

    assert warning is None


def test_classifies_missing_stale_and_no_fresh_starmine(tmp_path: Path) -> None:
    snapshot_date = date(2026, 6, 17)
    base_universe = tmp_path / "data" / "current" / "base_equity_universe.csv"
    _write_csv(
        base_universe,
        BASE_UNIVERSE_HEADERS,
        [{"symbol": "AAA"}, {"symbol": "BBB"}, {"symbol": "CCC"}],
    )

    signal_snapshot = tmp_path / "data" / "current" / "signal_snapshot.csv"
    _write_csv(
        signal_snapshot,
        SIGNAL_HEADERS,
        [
            {
                "snapshot_date": "2026-06-16",
                "created_at_utc": "2026-06-16T11:00:00+00:00",
                "run_id": "prior-sm",
                "provider": "FIDELITY",
                "source_file": "EquitySummaryScores.csv",
                "symbol": "BBB",
                "coverage_domain": "STARMINE_COVERED",
                "signal_coverage_status": "COVERED",
                "starmine_ess_text": "BEARISH",
                "starmine_ess_numeric": "2.0",
                "starmine_ess_numeric_estimated": "True",
                "starmine_ess_source_type": "TEXT_MAPPED",
            },
            {
                "snapshot_date": "2026-06-17",
                "created_at_utc": "2026-06-17T11:00:00+00:00",
                "run_id": "noness",
                "provider": "FIDELITY",
                "source_file": "non-ess.csv",
                "symbol": "CCC",
                "coverage_domain": "NON_STARMINE_ANALYST",
                "signal_coverage_status": "NON_COVERED",
                "starmine_ess_text": "",
                "starmine_ess_numeric": "",
                "starmine_ess_numeric_estimated": "False",
                "starmine_ess_source_type": "UNKNOWN",
            },
        ],
    )

    holdings_path = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "PAR-20260617-TEST" / "holdings.csv"
    _write_csv(
        holdings_path,
        ["symbol", "asset_class", "description", "percent_of_portfolio"],
        [
            {"symbol": "AAA", "asset_class": "EQUITIES", "description": "AAA", "percent_of_portfolio": "5.0"},
            {"symbol": "BBB", "asset_class": "EQUITIES", "description": "BBB", "percent_of_portfolio": "4.0"},
            {"symbol": "CCC", "asset_class": "EQUITIES", "description": "CCC", "percent_of_portfolio": "3.0"},
        ],
    )

    warning = build_ess_coverage_gap_warning(
        snapshot_date=snapshot_date,
        signal_snapshot_path=signal_snapshot,
        analysis_runs_root=tmp_path / "data" / "portfolio_ingestion" / "analysis_runs",
        base_universe_csv=base_universe,
    )

    assert warning is not None
    assert warning.warning_count == 3
    assert warning.true_missing_count == 1
    assert warning.stale_coverage_count == 1
    assert warning.no_fresh_starmine_count == 1
    assert warning.true_missing_symbols == ("AAA",)
    assert warning.stale_coverage_symbols == ("BBB",)
    assert warning.no_fresh_starmine_symbols == ("CCC",)

    by_symbol = {detail.symbol: detail for detail in warning.gaps}
    assert by_symbol["AAA"].gap_type == "TRUE_MISSING"
    assert by_symbol["BBB"].gap_type == "STALE_ESS"
    assert by_symbol["CCC"].gap_type == "NO_FRESH_STARMINE"


def test_excludes_non_applicable_and_keeps_applicable_missing_symbols(tmp_path: Path) -> None:
    snapshot_date = date(2026, 6, 17)

    signal_snapshot = tmp_path / "data" / "current" / "signal_snapshot.csv"
    _write_csv(signal_snapshot, SIGNAL_HEADERS, [])

    base_universe = tmp_path / "data" / "current" / "base_equity_universe.csv"
    _write_csv(base_universe, BASE_UNIVERSE_HEADERS, [{"symbol": "SIMO"}])

    holdings_path = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "PAR-20260617-TEST" / "holdings.csv"
    _write_csv(
        holdings_path,
        ["symbol", "asset_class", "security_type", "description", "percent_of_portfolio"],
        [
            {"symbol": "SBS", "asset_class": "EQUITIES", "security_type": "Common Stock", "description": "SBS ADR", "percent_of_portfolio": "9.0"},
            {"symbol": "VB", "asset_class": "EQUITIES", "security_type": "ETF", "description": "VB ETF", "percent_of_portfolio": "8.0"},
            {"symbol": "VOO", "asset_class": "EQUITIES", "security_type": "ETF", "description": "VOO ETF", "percent_of_portfolio": "7.0"},
            {"symbol": "FXAIX", "asset_class": "EQUITIES", "security_type": "Mutual Fund", "description": "Fidelity 500", "percent_of_portfolio": "6.0"},
            {"symbol": "SIMO", "asset_class": "EQUITIES", "security_type": "Common Stock", "description": "SIMO", "percent_of_portfolio": "5.0"},
        ],
    )

    warning = build_ess_coverage_gap_warning(
        snapshot_date=snapshot_date,
        signal_snapshot_path=signal_snapshot,
        analysis_runs_root=tmp_path / "data" / "portfolio_ingestion" / "analysis_runs",
        base_universe_csv=base_universe,
    )

    assert warning is not None
    assert warning.warning_count == 1
    assert warning.example_symbols == ("SIMO",)
    assert warning.true_missing_count == 1
    assert warning.true_missing_symbols == ("SIMO",)
    assert warning.stale_coverage_count == 0
    assert warning.no_fresh_starmine_count == 0

    symbols = {gap.symbol for gap in warning.gaps}
    assert "SIMO" in symbols
    assert "SBS" not in symbols
    assert "VB" not in symbols
    assert "VOO" not in symbols
    assert "FXAIX" not in symbols
