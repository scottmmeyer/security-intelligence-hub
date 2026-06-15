from __future__ import annotations

import csv
import inspect
from pathlib import Path


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_dynamic_holdings_match_latest_par_holdings_csv(tmp_path, monkeypatch) -> None:
    from scripts import refresh_signals as rs

    par_root = tmp_path / "analysis_runs"

    _write_csv(
        par_root / "PAR-20260610-OLDER" / "holdings.csv",
        ["symbol", "asset_class"],
        [
            {"symbol": "OLD1", "asset_class": "EQUITIES"},
            {"symbol": "ETF1", "asset_class": "ETF"},
        ],
    )
    _write_csv(
        par_root / "PAR-20260612-LATEST" / "holdings.csv",
        ["symbol", "asset_class"],
        [
            {"symbol": "NEW1", "asset_class": "EQUITIES"},
            {"symbol": "KEEP", "asset_class": "EQUITIES"},
            {"symbol": "CASH1", "asset_class": "CASH_EQUIVALENT"},
        ],
    )

    monkeypatch.setattr(rs, "_PAR_ROOT", par_root)

    assert rs._load_portfolio_equity_holdings() == {"NEW1", "KEEP"}


def test_new_holding_automatically_included_in_refresh(tmp_path, monkeypatch) -> None:
    from scripts import refresh_portfolio_signals as rps

    captured: dict[str, list[str]] = {}

    _write_csv(tmp_path / "danelfin.csv", ["symbol"], [{"symbol": "KEEP"}])
    _write_csv(tmp_path / "yahoo.csv", ["symbol"], [{"symbol": "KEEP"}])
    _write_csv(
        tmp_path / "universe.csv",
        ["symbol", "composite_score", "zacks_rating", "danelfin_score", "ess_score_text", "yahoo_score"],
        [{"symbol": "KEEP", "composite_score": "", "zacks_rating": "", "danelfin_score": "", "ess_score_text": "", "yahoo_score": ""}],
    )

    monkeypatch.setattr(rps, "_DANELFIN_LATEST", tmp_path / "danelfin.csv")
    monkeypatch.setattr(rps, "_YAHOO_LATEST", tmp_path / "yahoo.csv")
    monkeypatch.setattr(rps, "_UNIVERSE", tmp_path / "universe.csv")
    monkeypatch.setattr(rps, "_load_portfolio_equity_holdings", lambda: {"KEEP", "NEW1"})
    monkeypatch.setattr(rps, "patch_universe_danelfin", lambda: None)
    monkeypatch.setattr(
        rps,
        "fetch_danelfin_scores_for_symbols",
        lambda symbols, **kwargs: captured.setdefault("danelfin", list(symbols)),
    )
    monkeypatch.setattr(
        rps,
        "fetch_yahoo_supplemental_for_symbols",
        lambda symbols, **kwargs: captured.setdefault("yahoo", list(symbols)),
    )

    rps.main(skip_danelfin=False, skip_yahoo=False)

    assert captured["danelfin"] == ["NEW1"]
    assert captured["yahoo"] == ["NEW1"]


def test_removed_holding_automatically_excluded_from_refresh(tmp_path, monkeypatch) -> None:
    from scripts import refresh_portfolio_signals as rps

    captured: dict[str, list[str]] = {}

    _write_csv(tmp_path / "danelfin.csv", ["symbol"], [])
    _write_csv(tmp_path / "yahoo.csv", ["symbol"], [])
    _write_csv(
        tmp_path / "universe.csv",
        ["symbol", "composite_score", "zacks_rating", "danelfin_score", "ess_score_text", "yahoo_score"],
        [{"symbol": "KEEP", "composite_score": "", "zacks_rating": "", "danelfin_score": "", "ess_score_text": "", "yahoo_score": ""}],
    )

    monkeypatch.setattr(rps, "_DANELFIN_LATEST", tmp_path / "danelfin.csv")
    monkeypatch.setattr(rps, "_YAHOO_LATEST", tmp_path / "yahoo.csv")
    monkeypatch.setattr(rps, "_UNIVERSE", tmp_path / "universe.csv")
    monkeypatch.setattr(rps, "_load_portfolio_equity_holdings", lambda: {"KEEP"})
    monkeypatch.setattr(rps, "patch_universe_danelfin", lambda: None)
    monkeypatch.setattr(
        rps,
        "fetch_danelfin_scores_for_symbols",
        lambda symbols, **kwargs: captured.setdefault("danelfin", list(symbols)),
    )
    monkeypatch.setattr(
        rps,
        "fetch_yahoo_supplemental_for_symbols",
        lambda symbols, **kwargs: captured.setdefault("yahoo", list(symbols)),
    )

    rps.main(skip_danelfin=False, skip_yahoo=False)

    assert captured["danelfin"] == ["KEEP"]
    assert captured["yahoo"] == ["KEEP"]
    assert "SOLD" not in captured["danelfin"]
    assert "SOLD" not in captured["yahoo"]


def test_no_hardcoded_portfolio_symbol_dependency_remains() -> None:
    from scripts import refresh_portfolio_signals as rps

    source = inspect.getsource(rps)

    assert "_PORTFOLIO_SYMBOLS" not in source
    assert not hasattr(rps, "_PORTFOLIO_SYMBOLS")
    assert "_load_portfolio_equity_holdings" in source
