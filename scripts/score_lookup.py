"""Composite score lookup for one or more symbols.

Looks up each symbol against:
  - The current analytical universe  (for full ESS-pipeline composite score)
  - The current base universe         (for ESS text and ess_zacks_rating)
  - The Zacks cache                   (for internet-fetched Zacks rank)
  - Optionally fetches fresh Zacks data when --fetch is passed

Usage:
    PYTHONPATH=. .venv/bin/python scripts/score_lookup.py SBS MCB
    PYTHONPATH=. .venv/bin/python scripts/score_lookup.py SBS MCB --fetch
    PYTHONPATH=. .venv/bin/python scripts/score_lookup.py SBS MCB --fetch --show-formula
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_ANALYTICAL_UNIVERSE = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
_BASE_UNIVERSE = _REPO_ROOT / "data" / "current" / "base_equity_universe.csv"
_ZACKS_LATEST = _REPO_ROOT / "data" / "signals" / "zacks" / "latest_zacks.csv"

# Composite formula weights
_W_ESS = 0.55
_W_ZACKS = 0.25
_W_YAHOO = 0.10
_W_DANELFIN = 0.10

_ESS_TEXT_SCORE_MAP = {
    "VERY_BULLISH": 5.0,
    "BULLISH": 4.0,
    "NEUTRAL": 3.0,
    "BEARISH": 2.0,
    "VERY_BEARISH": 1.0,
}

_ZACKS_TEXT_SCORE_MAP = {
    "STRONG BUY": 5.0, "STRONG_BUY": 5.0,
    "BUY": 4.0, "OUTPERFORM": 4.0, "OVERWEIGHT": 4.0,
    "HOLD": 3.0, "NEUTRAL": 3.0, "EQUAL_WEIGHT": 3.0, "MARKET PERFORM": 3.0,
    "UNDERPERFORM": 2.0, "UNDERWEIGHT": 2.0, "SELL": 2.0,
    "STRONG SELL": 1.0, "STRONG_SELL": 1.0,
}


def _load_csv_by_symbol(path: Path, symbol_col: str = "symbol") -> dict[str, dict]:
    if not path.exists():
        return {}
    result: dict[str, dict] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            sym = str(row.get(symbol_col, "")).strip().upper()
            if sym:
                result[sym] = row
    return result


def _to_float(raw: object) -> float | None:
    try:
        v = float(str(raw or "").strip())
        return v if v == v else None  # NaN guard
    except (ValueError, TypeError):
        return None


def _compute_composite(ess_score: float, zacks_score: float, yahoo_score: float, danelfin_score: float) -> float:
    return round(
        ess_score * _W_ESS
        + zacks_score * _W_ZACKS
        + yahoo_score * _W_YAHOO
        + danelfin_score * _W_DANELFIN,
        4,
    )


def _resolve_zacks_score(zacks_cache_row: dict | None, ess_zacks_rating: str) -> tuple[float, str]:
    """Return (zacks_score, source_label). Score is on ascending 1-5 scale."""
    if zacks_cache_row:
        raw = str(zacks_cache_row.get("zacks_score", "")).strip()
        rank_raw = str(zacks_cache_row.get("zacks_rank", "")).strip()
        val = _to_float(raw)
        if val is not None and 1.0 <= val <= 5.0:
            sourced = zacks_cache_row.get("sourced_date", "")
            return val, f"internet cache ({sourced}, rank={rank_raw})"

    # Fall back to ESS ess_zacks_rating (raw rank, must invert)
    ess_rank = _to_float(ess_zacks_rating)
    if ess_rank is not None and 1.0 <= ess_rank <= 5.0:
        return round(6.0 - ess_rank, 2), f"ESS file proxy (rank={ess_rank:.0f})"

    return 3.0, "NEUTRAL default (no data)"


def lookup(symbols: list[str], fetch_fresh: bool = False, show_formula: bool = False) -> None:
    if fetch_fresh:
        print(f"Fetching fresh Zacks data for: {', '.join(symbols)} …\n")
        sys.path.insert(0, str(_REPO_ROOT))
        from src.scoring.fetch_zacks_scores import fetch_zacks_data, _write_csv, _OUTPUT_HEADERS, load_latest_zacks_scores
        import time, random
        from datetime import date

        today = date.today().isoformat()
        existing_rows: list[dict] = []
        if _ZACKS_LATEST.exists():
            with _ZACKS_LATEST.open("r", encoding="utf-8", newline="") as f:
                existing_rows = list(csv.DictReader(f))
        existing_by_sym = {r["symbol"]: r for r in existing_rows if r.get("symbol")}

        for sym in [s.upper() for s in symbols]:
            rank, score, abr, price_target, eps_growth = fetch_zacks_data(sym)
            row = {
                "symbol": sym,
                "zacks_rank": str(rank) if rank is not None else "",
                "zacks_score": str(score) if score is not None else "",
                "abr": str(abr) if abr is not None else "",
                "price_target": str(price_target) if price_target is not None else "",
                "eps_growth": str(eps_growth) if eps_growth is not None else "",
                "sourced_date": today,
            }
            existing_by_sym[sym] = row
            if rank is not None:
                extras = ""
                if price_target is not None:
                    extras += f"  target=${price_target:.2f}"
                if eps_growth is not None:
                    extras += f"  eps_growth={eps_growth:.1f}%"
                print(f"  {sym}: rank={rank:.0f}  score={score}{extras}")
            else:
                print(f"  {sym}: no Zacks data")

        updated_rows = list(existing_by_sym.values())
        _write_csv(_ZACKS_LATEST, updated_rows)
        # Also write dated file without overwriting existing (append new symbols)
        dated_path = _ZACKS_LATEST.parent / f"{today}_zacks.csv"
        if dated_path.exists():
            with dated_path.open("r", encoding="utf-8", newline="") as f:
                dated_rows = {r["symbol"]: r for r in csv.DictReader(f) if r.get("symbol")}
            for sym in [s.upper() for s in symbols]:
                if sym in existing_by_sym:
                    dated_rows[sym] = existing_by_sym[sym]
            _write_csv(dated_path, list(dated_rows.values()))
        else:
            fresh = [existing_by_sym[s.upper()] for s in symbols if s.upper() in existing_by_sym]
            _write_csv(dated_path, fresh)
        print()

    analytical = _load_csv_by_symbol(_ANALYTICAL_UNIVERSE)
    base = _load_csv_by_symbol(_BASE_UNIVERSE)
    zacks_cache = _load_csv_by_symbol(_ZACKS_LATEST)

    col_width = max(len(s) for s in symbols) + 2
    header = (
        f"{'Symbol':<{col_width}} {'Composite':>10} {'ESS':>13} {'Zacks':>7} {'Yahoo':>7} {'Danelfin':>9}  Source"
    )
    print(header)
    print("-" * len(header))

    for sym in [s.strip().upper() for s in symbols]:
        analytical_row = analytical.get(sym)

        if analytical_row:
            # Symbol exists in current pipeline output — use pre-computed composite
            composite = _to_float(analytical_row.get("composite_score")) or 0.0
            ess_text = str(analytical_row.get("ess_score_text", "") or "").strip() or "—"
            ess_score = _ESS_TEXT_SCORE_MAP.get(ess_text.upper(), 0.0)
            zacks_rating = str(analytical_row.get("zacks_rating", "") or "").strip()
            yahoo = _to_float(analytical_row.get("yahoo_score", "")) or 0.0
            danelfin = _to_float(analytical_row.get("danelfin_score", "")) or 0.0
            zacks_val = _to_float(zacks_rating) or 0.0
            source = "analytical_universe (pipeline)"
        else:
            # Not in pipeline — compute on-the-fly from available data
            base_row = base.get(sym, {})
            ess_text = str(base_row.get("starmine_ess_text", "") or "").strip() or "—"
            ess_score = _ESS_TEXT_SCORE_MAP.get(ess_text.upper(), 0.0)
            ess_zacks_rating = str(base_row.get("ess_zacks_rating", "") or "").strip()
            yahoo = _to_float(base_row.get("yahoo_score", "")) or 0.0
            danelfin = _to_float(base_row.get("danelfin_score", "")) or 0.0

            zacks_cache_row = zacks_cache.get(sym)
            zacks_val, zacks_src = _resolve_zacks_score(zacks_cache_row, ess_zacks_rating)

            composite = _compute_composite(ess_score, zacks_val, yahoo, danelfin)
            if base_row:
                source = f"base_universe + {zacks_src}"
            else:
                source = f"not in universe — {zacks_src}"

        ess_label = f"{ess_text}({ess_score:.1f})" if ess_text != "—" else f"—({ess_score:.1f})"
        print(
            f"{sym:<{col_width}} {composite:>10.4f} {ess_label:>13} {zacks_val:>7.2f} {yahoo:>7.2f} {danelfin:>9.2f}  {source}"
        )

        if show_formula:
            print(
                f"  = ESS({ess_score:.2f})×{_W_ESS}"
                f" + Zacks({zacks_val:.2f})×{_W_ZACKS}"
                f" + Yahoo({yahoo:.2f})×{_W_YAHOO}"
                f" + Danelfin({danelfin:.2f})×{_W_DANELFIN}"
            )

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Composite score lookup for one or more symbols.")
    parser.add_argument("symbols", nargs="+", help="Ticker symbols to look up")
    parser.add_argument("--fetch", action="store_true", help="Fetch fresh Zacks data for these symbols before scoring")
    parser.add_argument("--show-formula", action="store_true", help="Show the score breakdown formula line")
    args = parser.parse_args()

    lookup(args.symbols, fetch_fresh=args.fetch, show_formula=args.show_formula)
