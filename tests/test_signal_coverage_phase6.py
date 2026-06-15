from __future__ import annotations

import csv
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
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-12"},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-09"},
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
                "sourced_date": "2026-06-12",
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
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-12"},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-12"},
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
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-12"},
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
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-11"},
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
    analysis_runs, universe, zdir = _setup_holdings_and_universe(tmp_path)
    latest = zdir / "latest_zacks.csv"
    _write_csv(
        latest,
        _zacks_headers(),
        [
            {"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-12"},
            {"symbol": "TSM", "zacks_rank": "1", "zacks_score": "5", "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-10"},
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