from __future__ import annotations

import csv
from pathlib import Path


TODAY = "2026-06-12"


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _build_temp_holdings(par_root: Path) -> set[str]:
    run_dir = par_root / "PAR-20260612-TEST1234"
    _write_csv(
        run_dir / "holdings.csv",
        ["symbol", "asset_class"],
        [
            {"symbol": "BULL", "asset_class": "EQUITIES"},
            {"symbol": "BEAR", "asset_class": "EQUITIES"},
            {"symbol": "ETF1", "asset_class": "ETF"},
        ],
    )
    return {"BULL", "BEAR"}


def _build_temp_universe(universe_csv: Path) -> None:
    _write_csv(
        universe_csv,
        ["symbol", "starmine_ess_text", "starmine_ess_raw_score"],
        [
            {"symbol": "BULL", "starmine_ess_text": "BULLISH", "starmine_ess_raw_score": "8.2"},
            {"symbol": "BEAR", "starmine_ess_text": "BEARISH", "starmine_ess_raw_score": "3.1"},
            {"symbol": "NEAR", "starmine_ess_text": "NEUTRAL", "starmine_ess_raw_score": "6.8"},
            {"symbol": "DROP", "starmine_ess_text": "NEUTRAL", "starmine_ess_raw_score": "4.2"},
        ],
    )


class TestMandatoryHoldingsCoveragePhase1:

    def test_danelfin_smart_refresh_force_includes_current_equity_holdings(self, tmp_path, monkeypatch):
        from scripts import refresh_signals as rs

        expected_holdings = _build_temp_holdings(tmp_path / "analysis_runs")
        universe_csv = tmp_path / "base_equity_universe.csv"
        _build_temp_universe(universe_csv)

        captured: dict[str, list[str]] = {}

        monkeypatch.setattr(rs, "_PAR_ROOT", tmp_path / "analysis_runs")
        monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe_csv)
        monkeypatch.setattr(rs, "_DANELFIN_DIR", tmp_path / "signals" / "danelfin")
        monkeypatch.setattr(
            rs,
            "fetch_danelfin_scores_for_symbols",
            lambda symbols, **kwargs: captured.setdefault("symbols", list(symbols)),
        )

        result = rs._refresh_danelfin(dry_run=False, verbose=False, smart=True)

        assert result is True
        assert expected_holdings.issubset(set(captured["symbols"]))
        assert "NEAR" in captured["symbols"]
        assert "DROP" not in captured["symbols"]

    def test_yahoo_smart_refresh_force_includes_current_equity_holdings(self, tmp_path, monkeypatch):
        from scripts import refresh_signals as rs

        expected_holdings = _build_temp_holdings(tmp_path / "analysis_runs")
        universe_csv = tmp_path / "base_equity_universe.csv"
        _build_temp_universe(universe_csv)

        captured: dict[str, list[str]] = {}

        monkeypatch.setattr(rs, "_PAR_ROOT", tmp_path / "analysis_runs")
        monkeypatch.setattr(rs, "_BASE_UNIVERSE", universe_csv)
        monkeypatch.setattr(rs, "_YAHOO_DIR", tmp_path / "signals" / "yahoo")
        monkeypatch.setattr(
            rs,
            "fetch_yahoo_supplemental_for_symbols",
            lambda symbols, **kwargs: captured.setdefault("symbols", list(symbols)),
        )

        result = rs._refresh_yahoo(dry_run=False, verbose=False, smart=True)

        assert result is True
        assert expected_holdings.issubset(set(captured["symbols"]))
        assert "NEAR" in captured["symbols"]
        assert "DROP" not in captured["symbols"]
