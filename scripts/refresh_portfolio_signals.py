#!/usr/bin/env python3
"""Fetch Danelfin + Yahoo scores for a targeted symbol list and patch analytical_universe.csv.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/refresh_portfolio_signals.py
    PYTHONPATH=. .venv/bin/python scripts/refresh_portfolio_signals.py --skip-danelfin
    PYTHONPATH=. .venv/bin/python scripts/refresh_portfolio_signals.py --skip-yahoo
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.scoring.fetch_danelfin_scores import fetch_danelfin_scores_for_symbols
from src.scoring.fetch_yahoo_supplemental import fetch_yahoo_supplemental_for_symbols
from src.history.analytical_universe_manager import _score_from_inputs  # type: ignore[attr-defined]
from scripts.refresh_signals import _load_portfolio_equity_holdings

_DANELFIN_LATEST = _REPO_ROOT / "data" / "signals" / "danelfin" / "latest_danelfin.csv"
_YAHOO_LATEST    = _REPO_ROOT / "data" / "signals" / "yahoo" / "latest_yahoo_supplemental.csv"
_UNIVERSE        = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"


def _missing_from(latest_csv: Path, symbols: list[str]) -> list[str]:
    """Return symbols from *symbols* not present in *latest_csv*."""
    if not latest_csv.exists():
        return list(symbols)
    have: set[str] = set()
    with latest_csv.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                have.add(sym)
    return [s for s in symbols if s not in have]


def patch_universe_danelfin() -> None:
    """Apply danelfin_score from latest_danelfin.csv into analytical_universe.csv."""
    danelfin: dict[str, str] = {}
    with _DANELFIN_LATEST.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            score = str(row.get("danelfin_score", "")).strip()
            if sym and score:
                danelfin[sym] = score

    with _UNIVERSE.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    patched = 0
    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        if sym not in danelfin:
            continue
        row["danelfin_score"] = danelfin[sym]
        row["composite_score"] = str(_score_from_inputs(
            ess_score_text=str(row.get("ess_score_text", "") or ""),
            zacks_rating=str(row.get("zacks_rating", "") or ""),
            ess_zacks_rating="",
            yahoo_score=str(row.get("yahoo_score", "") or ""),
            danelfin_score=danelfin[sym],
        ))
        patched += 1

    with _UNIVERSE.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Patched danelfin_score in {patched} universe rows")


def main(skip_danelfin: bool = False, skip_yahoo: bool = False) -> None:
    portfolio_symbols = sorted(_load_portfolio_equity_holdings())
    if not portfolio_symbols:
        print("\n[Portfolio] No current equity holdings discovered from latest PAR holdings.csv")

    # --- Danelfin ---
    if not skip_danelfin:
        missing = _missing_from(_DANELFIN_LATEST, portfolio_symbols)
        if missing:
            print(f"\n[Danelfin] Fetching {len(missing)} missing symbols: {missing}")
            fetch_danelfin_scores_for_symbols(missing, delay_min=0.3, delay_max=0.8, verbose=True)
        else:
            print("\n[Danelfin] All portfolio symbols already present in latest_danelfin.csv — skipping fetch")
        print("[Danelfin] Patching analytical_universe.csv...")
        patch_universe_danelfin()

    # --- Yahoo supplemental ---
    if not skip_yahoo:
        missing = _missing_from(_YAHOO_LATEST, portfolio_symbols)
        if missing:
            print(f"\n[Yahoo] Fetching {len(missing)} missing symbols: {missing}")
            fetch_yahoo_supplemental_for_symbols(missing, delay_min=0.3, delay_max=0.8, verbose=True)
        else:
            print("\n[Yahoo] All portfolio symbols already present in latest_yahoo_supplemental.csv — skipping fetch")
        # Yahoo data (price targets, ABR) doesn't feed composite_score — no universe patch needed

    # Spot-check key symbols
    print("\n[Spot-check] Key portfolio symbols in analytical_universe:")
    with _UNIVERSE.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym in ("NVDA", "MSFT", "TSLA", "MU", "AVGO", "KGC", "ASML"):
                print(f"  {sym:6s}  composite={row.get('composite_score',''):6s}  "
                      f"zacks={row.get('zacks_rating',''):4s}  "
                      f"danelfin={row.get('danelfin_score',''):6s}  "
                      f"ess={row.get('ess_score_text','')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-danelfin", action="store_true")
    parser.add_argument("--skip-yahoo", action="store_true")
    args = parser.parse_args()
    main(skip_danelfin=args.skip_danelfin, skip_yahoo=args.skip_yahoo)
