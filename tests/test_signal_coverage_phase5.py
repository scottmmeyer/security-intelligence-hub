from __future__ import annotations

import csv
import os
from datetime import date, timedelta
from pathlib import Path

from scripts import refresh_signals as rs
from scripts import run_outcome_ui as outcome_ui
from src.portfolio.holdings_coverage import (
    classify_provider_applicability,
    load_active_holdings_baseline,
    load_provider_applicable_symbols,
    summarize_holdings_coverage,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_active_holdings_baseline_uses_latest_holdings_mtime(tmp_path) -> None:
    analysis_runs = tmp_path / "analysis_runs"
    older = analysis_runs / "PAR-20260612-OLDER" / "holdings.csv"
    newer_named_but_older_mtime = analysis_runs / "PAR-20260613-NEWERNAME" / "holdings.csv"

    _write_csv(older, ["symbol", "asset_class"], [{"symbol": "RIGHT", "asset_class": "EQUITIES"}])
    _write_csv(
        newer_named_but_older_mtime,
        ["symbol", "asset_class"],
        [{"symbol": "WRONG", "asset_class": "EQUITIES"}],
    )

    now = 1_800_000_000
    os.utime(newer_named_but_older_mtime, (now - 60, now - 60))
    os.utime(older, (now, now))

    baseline = load_active_holdings_baseline(analysis_runs)

    assert baseline is not None
    assert baseline.run_id == "PAR-20260612-OLDER"
    assert {row["symbol"] for row in baseline.holdings} == {"RIGHT"}


def test_provider_applicability_classifies_non_refreshable_holdings(tmp_path) -> None:
    base_universe = tmp_path / "base_equity_universe.csv"
    _write_csv(base_universe, ["symbol"], [{"symbol": "AAPL"}, {"symbol": "TSM"}])
    base_symbols = {"AAPL", "TSM"}

    assert classify_provider_applicability(
        {"symbol": "AAPL", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
        provider="zacks",
        base_universe_symbols=base_symbols,
    ) == (True, "applicable")

    assert classify_provider_applicability(
        {"symbol": "VWO", "asset_class": "EQUITIES", "security_type": "ETF", "operational_state": "ACTIVE_POSITION"},
        provider="zacks",
        base_universe_symbols=base_symbols,
    ) == (False, "not_in_base_equity_universe")

    assert classify_provider_applicability(
        {"symbol": "M26CNT069", "asset_class": "EQUITIES", "security_type": "CONTRA_ENTRY", "operational_state": "ZERO_VALUE_LEGACY_POSITION"},
        provider="zacks",
        base_universe_symbols=base_symbols,
    ) == (False, "zero_value_legacy_position")


def test_provider_applicable_symbols_use_same_baseline_and_filter_non_applicable(tmp_path) -> None:
    analysis_runs = tmp_path / "analysis_runs"
    _write_csv(
        analysis_runs / "PAR-20260612-BASE" / "holdings.csv",
        ["symbol", "asset_class", "security_type", "operational_state"],
        [
            {"symbol": "AAPL", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "TSM", "asset_class": "EQUITIES", "security_type": "Depository Receipt", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "VWO", "asset_class": "EQUITIES", "security_type": "ETF", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "M26CNT069", "asset_class": "EQUITIES", "security_type": "CONTRA_ENTRY", "operational_state": "ZERO_VALUE_LEGACY_POSITION"},
        ],
    )
    base_universe = tmp_path / "base_equity_universe.csv"
    _write_csv(base_universe, ["symbol"], [{"symbol": "AAPL"}, {"symbol": "TSM"}])

    assert load_provider_applicable_symbols(analysis_runs, base_universe, provider="zacks") == {"AAPL", "TSM"}
    assert load_provider_applicable_symbols(analysis_runs, base_universe, provider="danelfin") == {"AAPL", "TSM"}
    assert load_provider_applicable_symbols(analysis_runs, base_universe, provider="yahoo") == {"AAPL", "TSM"}


def test_holdings_coverage_distinguishes_compliance_from_research_health(tmp_path) -> None:
    analysis_runs = tmp_path / "analysis_runs"
    _write_csv(
        analysis_runs / "PAR-20260612-BASE" / "holdings.csv",
        ["symbol", "asset_class", "security_type", "operational_state"],
        [
            {"symbol": "AAPL", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "TSM", "asset_class": "EQUITIES", "security_type": "Depository Receipt", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "VWO", "asset_class": "EQUITIES", "security_type": "ETF", "operational_state": "ACTIVE_POSITION"},
        ],
    )
    base_universe = tmp_path / "base_equity_universe.csv"
    _write_csv(base_universe, ["symbol"], [{"symbol": "AAPL"}, {"symbol": "TSM"}])

    today = date(2026, 6, 12)
    latest = tmp_path / "latest_zacks.csv"
    _write_csv(
        latest,
        ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"],
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": today.isoformat()},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": (today - timedelta(days=5)).isoformat()},
            {"symbol": "EXTRA1", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": today.isoformat()},
            {"symbol": "EXTRA2", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": today.isoformat()},
        ],
    )

    summary = summarize_holdings_coverage(
        provider="zacks",
        latest_csv=latest,
        analysis_runs_root=analysis_runs,
        base_universe_csv=base_universe,
        threshold_days=2,
        today=today,
    )

    assert summary["run_id"] == "PAR-20260612-BASE"
    assert summary["active_holdings_baseline"] == 3
    assert summary["applicable_holdings"] == 2
    assert summary["covered_today"] == 1
    assert summary["covered_within_threshold"] == 1
    assert summary["stale"] == 1
    assert summary["missing"] == 0
    assert summary["not_applicable"] == 1
    assert summary["status"] == "DEGRADED"


def test_refresh_submits_all_applicable_holdings_for_each_provider(tmp_path, monkeypatch) -> None:
    analysis_runs = tmp_path / "analysis_runs"
    _write_csv(
        analysis_runs / "PAR-20260612-BASE" / "holdings.csv",
        ["symbol", "asset_class", "security_type", "operational_state"],
        [
            {"symbol": "AAPL", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "TSM", "asset_class": "EQUITIES", "security_type": "Depository Receipt", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "VWO", "asset_class": "EQUITIES", "security_type": "ETF", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "M26CNT069", "asset_class": "EQUITIES", "security_type": "CONTRA_ENTRY", "operational_state": "ZERO_VALUE_LEGACY_POSITION"},
        ],
    )
    base_universe = tmp_path / "base_equity_universe.csv"
    _write_csv(
        base_universe,
        ["symbol", "starmine_ess_text", "starmine_ess_raw_score"],
        [
            {"symbol": "AAPL", "starmine_ess_text": "BULLISH", "starmine_ess_raw_score": "8.2"},
            {"symbol": "TSM", "starmine_ess_text": "NEUTRAL", "starmine_ess_raw_score": "4.0"},
            {"symbol": "EXTRA", "starmine_ess_text": "BULLISH", "starmine_ess_raw_score": "8.0"},
        ],
    )

    captured: dict[str, list[str]] = {}

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(rs, "_ZACKS_DIR", tmp_path / "signals" / "zacks")
    monkeypatch.setattr(rs, "_DANELFIN_DIR", tmp_path / "signals" / "danelfin")
    monkeypatch.setattr(rs, "_YAHOO_DIR", tmp_path / "signals" / "yahoo")
    monkeypatch.setattr(rs, "fetch_zacks_scores_for_symbols", lambda symbols, **kwargs: captured.setdefault("zacks", list(symbols)))
    monkeypatch.setattr(rs, "fetch_danelfin_scores_for_symbols", lambda symbols, **kwargs: captured.setdefault("danelfin", list(symbols)))
    monkeypatch.setattr(rs, "fetch_yahoo_supplemental_for_symbols", lambda symbols, **kwargs: captured.setdefault("yahoo", list(symbols)))

    assert rs._refresh_zacks(dry_run=False, verbose=False) is True
    assert rs._refresh_danelfin(dry_run=False, verbose=False, smart=True) is True
    assert rs._refresh_yahoo(dry_run=False, verbose=False, smart=True) is True

    for provider in ("zacks", "danelfin", "yahoo"):
        submitted = set(captured[provider])
        assert {"AAPL", "TSM"}.issubset(submitted)
        assert "VWO" not in submitted
        assert "M26CNT069" not in submitted


def test_signal_status_splits_research_health_and_holdings_coverage(tmp_path, monkeypatch) -> None:
    root = tmp_path
    analysis_runs = root / "data" / "portfolio_ingestion" / "analysis_runs"
    _write_csv(
        analysis_runs / "PAR-20260612-BASE" / "holdings.csv",
        ["symbol", "asset_class", "security_type", "operational_state"],
        [
            {"symbol": "AAPL", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "TSM", "asset_class": "EQUITIES", "security_type": "Depository Receipt", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "VWO", "asset_class": "EQUITIES", "security_type": "ETF", "operational_state": "ACTIVE_POSITION"},
        ],
    )
    _write_csv(root / "data" / "current" / "base_equity_universe.csv", ["symbol"], [{"symbol": "AAPL"}, {"symbol": "TSM"}])

    today = date.today().isoformat()
    stale = (date.today() - timedelta(days=5)).isoformat()
    zacks = root / "latest_zacks.csv"
    danelfin = root / "latest_danelfin.csv"
    yahoo = root / "latest_yahoo_supplemental.csv"
    _write_csv(
        zacks,
        ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"],
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": today},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": stale},
            {"symbol": "EXTRA", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": today},
        ],
    )
    _write_csv(
        danelfin,
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [
            {"symbol": "AAPL", "danelfin_raw": "8", "danelfin_score": "4.0", "sourced_date": today},
            {"symbol": "TSM", "danelfin_raw": "7", "danelfin_score": "3.5", "sourced_date": stale},
            {"symbol": "EXTRA", "danelfin_raw": "7", "danelfin_score": "3.5", "sourced_date": today},
        ],
    )
    _write_csv(
        yahoo,
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [
            {"symbol": "AAPL", "price_target": "200", "abr": "1.2", "analyst_count": "30", "eps_growth_5yr": "12", "current_price": "180", "upside_pct": "11", "sourced_date": today},
            {"symbol": "TSM", "price_target": "220", "abr": "1.3", "analyst_count": "20", "eps_growth_5yr": "10", "current_price": "200", "upside_pct": "10", "sourced_date": stale},
            {"symbol": "EXTRA", "price_target": "110", "abr": "1.5", "analyst_count": "10", "eps_growth_5yr": "8", "current_price": "100", "upside_pct": "10", "sourced_date": today},
        ],
    )

    monkeypatch.setattr(outcome_ui, "_REPO_ROOT", root)
    monkeypatch.setattr(outcome_ui, "_SIGNAL_FILES", {"zacks": zacks, "danelfin": danelfin, "yahoo": yahoo})
    monkeypatch.setattr(outcome_ui, "_ESS_SIGNAL_SNAPSHOT", root / "missing_ess.csv")
    monkeypatch.setattr(outcome_ui, "_ESS_COVERAGE_WARNING", root / "missing_ess_warning.json")

    status = outcome_ui._signal_status()

    assert status["zacks"]["badge_state"] == "FRESH"
    assert status["zacks"]["holdings_status"] == "DEGRADED"
    assert status["portfolio_holdings_coverage"]["active_holdings_baseline"] == 3
    assert status["portfolio_holdings_coverage"]["providers"]["zacks"]["status"] == "DEGRADED"
    assert status["portfolio_holdings_coverage"]["providers"]["zacks"]["not_applicable"] == 1


def test_ui_and_refresh_share_same_active_holdings_baseline(tmp_path, monkeypatch) -> None:
    analysis_runs = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs"
    _write_csv(
        analysis_runs / "PAR-20260612-BASE" / "holdings.csv",
        ["symbol", "asset_class", "security_type", "operational_state"],
        [
            {"symbol": "AAPL", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "TSM", "asset_class": "EQUITIES", "security_type": "Depository Receipt", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "VWO", "asset_class": "EQUITIES", "security_type": "ETF", "operational_state": "ACTIVE_POSITION"},
        ],
    )
    _write_csv(tmp_path / "data" / "current" / "base_equity_universe.csv", ["symbol"], [{"symbol": "AAPL"}, {"symbol": "TSM"}])
    signal = tmp_path / "latest_zacks.csv"
    _write_csv(signal, ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"], [{"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": date.today().isoformat()}])

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", tmp_path / "data" / "current" / "base_equity_universe.csv")
    monkeypatch.setattr(outcome_ui, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(outcome_ui, "_SIGNAL_FILES", {"zacks": signal, "danelfin": signal, "yahoo": signal})
    monkeypatch.setattr(outcome_ui, "_ESS_SIGNAL_SNAPSHOT", tmp_path / "missing_ess.csv")
    monkeypatch.setattr(outcome_ui, "_ESS_COVERAGE_WARNING", tmp_path / "missing_ess_warning.json")

    status = outcome_ui._signal_status()

    assert len(rs._load_portfolio_equity_holdings()) == status["portfolio_holdings_coverage"]["active_holdings_baseline"]