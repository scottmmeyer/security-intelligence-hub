from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

from scripts import refresh_signals as rs
from src.scoring import fetch_danelfin_scores as danelfin_module
from src.scoring import fetch_yahoo_supplemental as yahoo_module


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_same_day_successful_row_skipped_in_coverage_repair(tmp_path, monkeypatch):
    today = date.today().isoformat()
    out = tmp_path
    _write_csv(
        out / f"{today}_yahoo_supplemental.csv",
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [{"symbol": "AAA", "price_target": "101.0", "abr": "1.5", "analyst_count": "12", "eps_growth_5yr": "", "current_price": "99.0", "upside_pct": "2.0", "sourced_date": today}],
    )

    calls: list[str] = []

    def _fake_fetch(symbol):
        calls.append(symbol)
        return {"price_target": 101.0, "abr": 1.5, "analyst_count": 10, "eps_growth_5yr": None, "current_price": 99.0}

    monkeypatch.setattr(yahoo_module, "fetch_yahoo_supplemental", _fake_fetch)

    _, stats = yahoo_module.fetch_yahoo_supplemental_for_symbols(
        ["AAA"],
        output_dir=out,
        delay_min=0,
        delay_max=0,
        verbose=False,
        force_retry_symbols={"AAA"},
        collect_stats=True,
    )

    assert calls == []
    assert stats["skipped_already_covered"] == 1
    assert stats["retried_failed_checkpoint"] == 0


def test_same_day_failed_row_retried_in_coverage_repair(tmp_path, monkeypatch):
    today = date.today().isoformat()
    out = tmp_path
    _write_csv(
        out / f"{today}_yahoo_supplemental.csv",
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [{"symbol": "AAA", "price_target": "", "abr": "", "analyst_count": "", "eps_growth_5yr": "", "current_price": "", "upside_pct": "", "sourced_date": today}],
    )

    calls: list[str] = []

    def _fake_fetch(symbol):
        calls.append(symbol)
        return {"price_target": 110.0, "abr": 1.7, "analyst_count": 14, "eps_growth_5yr": 10.0, "current_price": 100.0}

    monkeypatch.setattr(yahoo_module, "fetch_yahoo_supplemental", _fake_fetch)

    _, stats = yahoo_module.fetch_yahoo_supplemental_for_symbols(
        ["AAA"],
        output_dir=out,
        delay_min=0,
        delay_max=0,
        verbose=False,
        force_retry_symbols={"AAA"},
        collect_stats=True,
    )

    assert calls == ["AAA"]
    assert stats["retried_failed_checkpoint"] == 1


def test_stale_row_retried_in_coverage_repair(tmp_path, monkeypatch):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    out = tmp_path
    _write_csv(
        out / f"{today}_yahoo_supplemental.csv",
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [{"symbol": "AAA", "price_target": "101.0", "abr": "1.5", "analyst_count": "12", "eps_growth_5yr": "", "current_price": "99.0", "upside_pct": "2.0", "sourced_date": yesterday}],
    )

    calls: list[str] = []

    def _fake_fetch(symbol):
        calls.append(symbol)
        return {"price_target": 111.0, "abr": 1.8, "analyst_count": 10, "eps_growth_5yr": None, "current_price": 99.0}

    monkeypatch.setattr(yahoo_module, "fetch_yahoo_supplemental", _fake_fetch)

    _, stats = yahoo_module.fetch_yahoo_supplemental_for_symbols(
        ["AAA"],
        output_dir=out,
        delay_min=0,
        delay_max=0,
        verbose=False,
        force_retry_symbols={"AAA"},
        collect_stats=True,
    )

    assert calls == ["AAA"]
    assert stats["retried_failed_checkpoint"] == 1


def test_missing_row_retried_in_coverage_repair(tmp_path, monkeypatch):
    calls: list[str] = []

    def _fake_fetch(symbol):
        calls.append(symbol)
        return {"price_target": 120.0, "abr": 1.9, "analyst_count": 5, "eps_growth_5yr": None, "current_price": 100.0}

    monkeypatch.setattr(yahoo_module, "fetch_yahoo_supplemental", _fake_fetch)

    _, stats = yahoo_module.fetch_yahoo_supplemental_for_symbols(
        ["AAA"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        verbose=False,
        force_retry_symbols={"AAA"},
        collect_stats=True,
    )

    assert calls == ["AAA"]
    assert stats["retried_failed_checkpoint"] == 0
    assert stats["attempted"] == 1


def test_research_refresh_resume_unchanged(tmp_path, monkeypatch):
    today = date.today().isoformat()
    out = tmp_path
    _write_csv(
        out / f"{today}_yahoo_supplemental.csv",
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [{"symbol": "AAA", "price_target": "101.0", "abr": "1.5", "analyst_count": "12", "eps_growth_5yr": "", "current_price": "99.0", "upside_pct": "2.0", "sourced_date": today}],
    )

    calls: list[str] = []

    def _fake_fetch(symbol):
        calls.append(symbol)
        return {"price_target": 120.0, "abr": 1.9, "analyst_count": 5, "eps_growth_5yr": None, "current_price": 100.0}

    monkeypatch.setattr(yahoo_module, "fetch_yahoo_supplemental", _fake_fetch)

    _, stats = yahoo_module.fetch_yahoo_supplemental_for_symbols(
        ["AAA", "BBB"],
        output_dir=out,
        delay_min=0,
        delay_max=0,
        verbose=False,
        collect_stats=True,
    )

    assert calls == ["BBB"]
    assert stats["skipped_checkpoint"] == 1


def test_danelfin_repair_retries_failed_same_day_row(tmp_path, monkeypatch):
    today = date.today().isoformat()
    out = tmp_path
    _write_csv(
        out / f"{today}_danelfin.csv",
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [{"symbol": "AAA", "danelfin_raw": "", "danelfin_score": "", "sourced_date": today}],
    )

    calls: list[str] = []

    def _fake_fetch(symbol):
        calls.append(symbol)
        return 7, 3.5

    monkeypatch.setattr(danelfin_module, "fetch_danelfin_score", _fake_fetch)

    _, stats = danelfin_module.fetch_danelfin_scores_for_symbols(
        ["AAA"],
        output_dir=out,
        delay_min=0,
        delay_max=0,
        verbose=False,
        force_retry_symbols={"AAA"},
        collect_stats=True,
    )

    assert calls == ["AAA"]
    assert stats["retried_failed_checkpoint"] == 1


def test_report_includes_retried_failed_checkpoint(tmp_path, monkeypatch):
    analysis_runs = tmp_path / "analysis_runs"
    holdings_path = analysis_runs / "PAR-20260612-BASE" / "holdings.csv"
    _write_csv(
        holdings_path,
        ["symbol", "asset_class", "security_type", "operational_state"],
        [{"symbol": "AAA", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"}],
    )
    universe = tmp_path / "base_equity_universe.csv"
    _write_csv(
        universe,
        ["symbol", "starmine_ess_text", "starmine_ess_raw_score"],
        [{"symbol": "AAA", "starmine_ess_text": "BULLISH", "starmine_ess_raw_score": "8.0"}],
    )

    ydir = tmp_path / "signals" / "yahoo"
    today = date.today().isoformat()
    _write_csv(
        ydir / "latest_yahoo_supplemental.csv",
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [{"symbol": "AAA", "price_target": "", "abr": "", "analyst_count": "", "eps_growth_5yr": "", "current_price": "", "upside_pct": "", "sourced_date": today}],
    )
    _write_csv(
        ydir / f"{today}_yahoo_supplemental.csv",
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [{"symbol": "AAA", "price_target": "", "abr": "", "analyst_count": "", "eps_growth_5yr": "", "current_price": "", "upside_pct": "", "sourced_date": today}],
    )

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe)
    monkeypatch.setattr(rs, "_YAHOO_DIR", ydir)

    def _fake_fetcher(symbols, **kwargs):
        symbol_list = list(symbols)
        return ydir / f"{today}_yahoo_supplemental.csv", {
            "requested": len(symbol_list),
            "attempted": len(symbol_list),
            "skipped_checkpoint": 0,
            "skipped_already_covered": 0,
            "retried_failed_checkpoint": 1,
        }

    monkeypatch.setattr(rs, "fetch_yahoo_supplemental_for_symbols", _fake_fetcher)

    triggered, metrics = rs._refresh_yahoo(dry_run=False, verbose=False, collect_report=True)

    assert triggered is True
    assert metrics["mode"] == "coverage_repair"
    assert "retried_failed_checkpoint" in metrics
    assert metrics["retried_failed_checkpoint"] == 1
