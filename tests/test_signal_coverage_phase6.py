from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path

from scripts import refresh_signals as rs


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _setup_holdings_and_universe(tmp_path: Path) -> tuple[Path, Path, Path]:
    analysis_runs = tmp_path / "analysis_runs"
    holdings_path = analysis_runs / "PAR-20260612-BASE" / "holdings.csv"
    _write_csv(
        holdings_path,
        ["symbol", "asset_class", "security_type", "operational_state"],
        [
            {"symbol": "AAPL", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "TSM", "asset_class": "EQUITIES", "security_type": "Depository Receipt", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "VWO", "asset_class": "EQUITIES", "security_type": "ETF", "operational_state": "ACTIVE_POSITION"},
        ],
    )

    universe = tmp_path / "base_equity_universe.csv"
    _write_csv(
        universe,
        ["symbol", "starmine_ess_text", "starmine_ess_raw_score"],
        [
            {"symbol": "AAPL", "starmine_ess_text": "BULLISH", "starmine_ess_raw_score": "8.0"},
            {"symbol": "TSM", "starmine_ess_text": "BULLISH", "starmine_ess_raw_score": "8.0"},
            {"symbol": "EXTRA", "starmine_ess_text": "BULLISH", "starmine_ess_raw_score": "8.0"},
        ],
    )

    zdir = tmp_path / "signals" / "zacks"
    return analysis_runs, universe, zdir


def _zacks_headers() -> list[str]:
    return ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"]


def test_provider_fresh_but_coverage_degraded_triggers_targeted_refresh(tmp_path, monkeypatch):
    today = rs.date.today()
    fresh = today.isoformat()
    stale = (today - timedelta(days=3)).isoformat()
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": fresh},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": stale},
        ],
    )

    captured: dict[str, list[str]] = {}

    def _fake_fetch(symbols, **kwargs):
        captured["symbols"] = list(symbols)
        rows = list(csv.DictReader(latest.open("r", encoding="utf-8", newline="")))
        by = {r["symbol"]: r for r in rows}
        for sym in symbols:
            by[sym] = {
                "symbol": sym,
                "zacks_rank": "1",
                "zacks_score": "5",
                "abr": "",
                "price_target": "",
                "eps_growth": "",
                    "sourced_date": fresh,
            }
        _write_csv(latest, _zacks_headers(), list(by.values()))

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe)
    monkeypatch.setattr(rs, "_ZACKS_DIR", zdir)
    monkeypatch.setattr(rs, "fetch_zacks_scores_for_symbols", _fake_fetch)

    triggered, metrics = rs._refresh_zacks(dry_run=False, verbose=False, collect_report=True)

    assert triggered is True
    assert metrics["mode"] == "coverage_repair"
    assert captured["symbols"] == ["TSM"]
    assert metrics["submitted"] == 1
    assert metrics["coverage_before"]["status"] == "DEGRADED"
    assert metrics["coverage_after"]["covered_today"] >= metrics["coverage_before"]["covered_today"]


def test_provider_fresh_and_coverage_compliant_skips(tmp_path, monkeypatch):
    fresh = rs.date.today().isoformat()
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": fresh},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": fresh},
        ],
    )

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe)
    monkeypatch.setattr(rs, "_ZACKS_DIR", zdir)
    monkeypatch.setattr(rs, "fetch_zacks_scores_for_symbols", lambda symbols, **kwargs: (_ for _ in ()).throw(AssertionError("fetch should not run")))

    triggered, metrics = rs._refresh_zacks(dry_run=False, verbose=False, collect_report=True)

    assert triggered is False
    assert metrics["mode"] == "skip_compliant"
    assert metrics["submitted"] == 0


def test_provider_fresh_with_missing_applicable_symbol_submits_missing(tmp_path, monkeypatch):
    fresh = rs.date.today().isoformat()
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": fresh},
        ],
    )

    captured: dict[str, list[str]] = {}

    def _fake_fetch(symbols, **kwargs):
        captured["symbols"] = list(symbols)

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe)
    monkeypatch.setattr(rs, "_ZACKS_DIR", zdir)
    monkeypatch.setattr(rs, "fetch_zacks_scores_for_symbols", _fake_fetch)

    triggered, metrics = rs._refresh_zacks(dry_run=False, verbose=False, collect_report=True)

    assert triggered is True
    assert metrics["mode"] == "coverage_repair"
    assert captured["symbols"] == ["TSM"]


def test_research_stale_mode_keeps_research_refresh_behavior(tmp_path, monkeypatch):
    stale = (rs.date.today() - timedelta(days=3)).isoformat()
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": stale},
        ],
    )

    captured: dict[str, list[str]] = {}

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe)
    monkeypatch.setattr(rs, "_ZACKS_DIR", zdir)
    monkeypatch.setattr(rs, "fetch_zacks_scores_for_symbols", lambda symbols, **kwargs: captured.setdefault("symbols", list(symbols)))

    triggered, metrics = rs._refresh_zacks(dry_run=False, verbose=False, collect_report=True)

    assert triggered is True
    assert metrics["mode"] == "research_refresh"
    # Research mode can include applicable holdings plus smart-universe symbols.
    assert set(["AAPL", "TSM"]).issubset(set(captured["symbols"]))


def test_ensure_signals_fresh_with_report_exposes_provider_activity(tmp_path, monkeypatch):
    today = rs.date.today()
    fresh = today.isoformat()
    stale = (today - timedelta(days=3)).isoformat()
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": fresh},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": stale},
        ],
    )

    monkeypatch.setattr(rs, "_PAR_ROOT", analysis_runs)
    monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe)
    monkeypatch.setattr(rs, "_ZACKS_DIR", zdir)
    monkeypatch.setattr(rs, "_DANELFIN_DIR", tmp_path / "signals" / "danelfin")
    monkeypatch.setattr(rs, "_YAHOO_DIR", tmp_path / "signals" / "yahoo")
    monkeypatch.setattr(rs, "fetch_zacks_scores_for_symbols", lambda symbols, **kwargs: None)
    monkeypatch.setattr(rs, "fetch_danelfin_scores_for_symbols", lambda symbols, **kwargs: None)
    monkeypatch.setattr(rs, "fetch_yahoo_supplemental_for_symbols", lambda symbols, **kwargs: None)

    # Keep danelfin/yahoo out of this test by making them look stale with no symbols.
    _write_csv(tmp_path / "signals" / "danelfin" / "latest_danelfin.csv", ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"], [])
    _write_csv(tmp_path / "signals" / "yahoo" / "latest_yahoo_supplemental.csv", ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"], [])

    report = rs.ensure_signals_fresh_with_report(providers=["zacks"], dry_run=False, verbose=False, smart=True)

    assert "providers" in report
    assert "zacks" in report["providers"]
    assert "submitted" in report["providers"]["zacks"]
    assert "coverage_before" in report["providers"]["zacks"]
    assert "coverage_after" in report["providers"]["zacks"]


def test_provider_metrics_separate_no_coverage_from_failed(tmp_path, monkeypatch):
    today = rs.date.today().isoformat()
    ydir = tmp_path / "signals" / "yahoo"
    latest = ydir / "latest_yahoo_supplemental.csv"
    _write_csv(
        latest,
        ["symbol", "price_target", "abr", "analyst_count", "eps_growth_5yr", "current_price", "upside_pct", "sourced_date"],
        [
            {
                "symbol": "AAA",
                "price_target": "",
                "abr": "",
                "analyst_count": "",
                "eps_growth_5yr": "",
                "current_price": "",
                "upside_pct": "",
                "sourced_date": today,
            },
            {
                "symbol": "BBB",
                "price_target": "120.0",
                "abr": "",
                "analyst_count": "10",
                "eps_growth_5yr": "",
                "current_price": "100.0",
                "upside_pct": "",
                "sourced_date": today,
            },
        ],
    )

    monkeypatch.setattr(rs, "_YAHOO_DIR", ydir)
    metrics = rs._compute_provider_metrics(
        provider="yahoo",
        mode="coverage_repair",
        submitted_symbols=["AAA", "BBB"],
        coverage_before={"applicable_holdings": 2},
        coverage_after={"applicable_holdings": 2},
        runtime_sec=0.01,
        fetch_stats={"requested": 2, "attempted": 2},
    )

    assert metrics["submitted"] == 2
    assert metrics["written_count"] == 2
    assert metrics["written_refresh_date_count"] == 2
    assert metrics["primary_data_count"] == 1
    assert metrics["empty_primary_data_count"] == 1
    assert metrics["no_coverage_count"] == 1
    assert metrics["missing_written_count"] == 0
    assert metrics["true_error_count"] == 0
    assert metrics["failed"] == 0


def test_provider_metrics_missing_write_counts_as_true_error(tmp_path, monkeypatch):
    today = rs.date.today().isoformat()
    zdir = tmp_path / "signals" / "zacks"
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"],
        [
            {
                "symbol": "AAA",
                "zacks_rank": "1",
                "zacks_score": "5",
                "abr": "",
                "price_target": "",
                "eps_growth": "",
                "sourced_date": today,
            },
        ],
    )

    monkeypatch.setattr(rs, "_ZACKS_DIR", zdir)
    metrics = rs._compute_provider_metrics(
        provider="zacks",
        mode="research_refresh",
        submitted_symbols=["AAA", "BBB"],
        coverage_before={"applicable_holdings": 2},
        coverage_after={"applicable_holdings": 2},
        runtime_sec=0.01,
        fetch_stats={"requested": 2, "attempted": 2},
    )

    assert metrics["submitted"] == 2
    assert metrics["written_count"] == 1
    assert metrics["missing_written_count"] == 1
    assert metrics["true_error_count"] == 1
    assert metrics["failed"] == 1