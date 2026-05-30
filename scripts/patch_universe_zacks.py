#!/usr/bin/env python3
"""One-shot script: apply all scores from latest_zacks.csv into analytical_universe.csv.

Updates zacks_rating and recalculates composite_score for every matched symbol.
Safe to run repeatedly — idempotent upsert.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/patch_universe_zacks.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.history.analytical_universe_manager import _score_from_inputs  # type: ignore[attr-defined]

ZACKS_PATH = _REPO_ROOT / "data" / "signals" / "zacks" / "latest_zacks.csv"
UNIVERSE_PATH = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"


def main() -> None:
    # --- Load Zacks scores ---
    zacks: dict[str, str] = {}
    with ZACKS_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            score = str(row.get("zacks_score", "")).strip()
            if sym and score:
                zacks[sym] = score
    print(f"Loaded {len(zacks)} Zacks scores from {ZACKS_PATH.name}")

    # --- Patch universe ---
    with UNIVERSE_PATH.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    patched = 0
    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        if sym not in zacks:
            continue
        row["zacks_rating"] = zacks[sym]
        row["composite_score"] = str(_score_from_inputs(
            ess_score_text=str(row.get("ess_score_text", "") or ""),
            zacks_rating=zacks[sym],
            ess_zacks_rating="",
            yahoo_score=str(row.get("yahoo_score", "") or ""),
            danelfin_score=str(row.get("danelfin_score", "") or ""),
        ))
        patched += 1

    with UNIVERSE_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Patched {patched} / {len(rows)} rows in {UNIVERSE_PATH.name}")

    # Spot-check a few key symbols
    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        if sym in ("NVDA", "MSFT", "TSLA", "MU", "AVGO"):
            print(f"  {sym}: zacks_rating={row['zacks_rating']}  composite_score={row['composite_score']}")


if __name__ == "__main__":
    main()
