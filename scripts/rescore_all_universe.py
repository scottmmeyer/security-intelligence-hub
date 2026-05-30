#!/usr/bin/env python3
"""One-shot script: recompute composite_score for ALL rows in analytical_universe.csv.

Uses the current _score_from_inputs() formula (renormalized over available signals).
Safe to run repeatedly — idempotent.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/rescore_all_universe.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.history.analytical_universe_manager import _score_from_inputs  # type: ignore[attr-defined]

UNIVERSE_PATH = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"


def main() -> None:
    with UNIVERSE_PATH.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    print(f"Loaded {len(rows)} rows from {UNIVERSE_PATH.name}")

    updated = 0
    for row in rows:
        correct = _score_from_inputs(
            ess_score_text=str(row.get("ess_score_text", "") or ""),
            zacks_rating=str(row.get("zacks_rating", "") or ""),
            ess_zacks_rating="",
            yahoo_score=str(row.get("yahoo_score", "") or ""),
            danelfin_score=str(row.get("danelfin_score", "") or ""),
        )
        stored = str(row.get("composite_score", "")).strip()
        try:
            stored_float = float(stored)
        except (ValueError, TypeError):
            stored_float = 0.0

        if abs(correct - stored_float) > 0.0001:
            row["composite_score"] = str(correct)
            updated += 1

    with UNIVERSE_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {updated} / {len(rows)} rows in {UNIVERSE_PATH.name}")

    # Spot-check key symbols
    spot = {str(r.get("symbol", "")).strip().upper(): r for r in rows}
    for sym in ("MCB", "A", "AAPL", "SBS", "KGC", "NVDA"):
        if sym in spot:
            r = spot[sym]
            print(
                f"  {sym}: ess={r.get('ess_score_text')!r:20s}  "
                f"zacks={r.get('zacks_rating')!r:6s}  "
                f"yahoo={r.get('yahoo_score')!r:6s}  "
                f"danelfin={r.get('danelfin_score')!r:6s}  "
                f"composite={r.get('composite_score')}"
            )


if __name__ == "__main__":
    main()
