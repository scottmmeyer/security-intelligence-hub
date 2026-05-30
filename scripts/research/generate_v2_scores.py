#!/usr/bin/env python3
"""Research script: populate v2 experimental fields in analytical_universe.csv.

Adds or refreshes the following columns WITHOUT touching composite_score (v1):

    yahoo_abr_normalized   — 6 - abr, clipped [1.0, 5.0], blank if no ABR
    composite_v2_yahoo     — experimental score using _V2_YAHOO_WEIGHTS
    composite_version      — "v1" (production lineage tag, immutable)
    score_generation_timestamp — ISO UTC timestamp of this run

This script is SAFE to run repeatedly (idempotent).
It never rewrites composite_score or any other v1 production field.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/research/generate_v2_scores.py
    PYTHONPATH=. .venv/bin/python scripts/research/generate_v2_scores.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from src.history.analytical_universe_manager import (  # type: ignore[attr-defined]
    normalize_yahoo_abr,
    score_composite_v2_yahoo,
    _COMPOSITE_V2_VERSION_TAG,
)

UNIVERSE_PATH   = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
YAHOO_PATH      = _REPO_ROOT / "data" / "signals" / "yahoo" / "latest_yahoo_supplemental.csv"

# New columns that this script manages — never touches other columns.
_V2_COLUMNS = ["yahoo_abr_normalized", "composite_v2_yahoo", "composite_version", "score_generation_timestamp"]


def _load_yahoo_abr(path: Path) -> dict[str, str]:
    """Return symbol → raw ABR string (empty string if no ABR)."""
    abr_map: dict[str, str] = {}
    if not path.exists():
        print(f"[WARN] Yahoo supplemental not found at {path} — all ABR will be blank.", file=sys.stderr)
        return abr_map
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            abr = str(row.get("abr", "")).strip()
            if sym:
                abr_map[sym] = abr
    return abr_map


def main(dry_run: bool = False) -> None:
    # --- load Yahoo ABR ---
    abr_map = _load_yahoo_abr(YAHOO_PATH)
    abr_covered = sum(1 for v in abr_map.values() if v)
    print(f"Yahoo ABR loaded: {len(abr_map)} symbols, {abr_covered} with ABR value")

    # --- read universe ---
    with UNIVERSE_PATH.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        existing_headers = list(reader.fieldnames or [])
        rows = list(reader)
    print(f"Universe: {len(rows)} rows, {len(existing_headers)} existing columns")

    # Extend headers with v2 columns that aren't already present.
    headers = list(existing_headers)
    for col in _V2_COLUMNS:
        if col not in headers:
            headers.append(col)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- populate v2 fields ---
    abr_hits = 0
    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        raw_abr = abr_map.get(sym, "")
        normalized = normalize_yahoo_abr(raw_abr)

        yahoo_abr_str = str(normalized) if normalized > 0.0 else ""
        if normalized > 0.0:
            abr_hits += 1

        v2_score = score_composite_v2_yahoo(
            ess_score_text=str(row.get("ess_score_text", "") or ""),
            zacks_rating=str(row.get("zacks_rating", "") or ""),
            ess_zacks_rating="",
            yahoo_abr_normalized=yahoo_abr_str,
            danelfin_score=str(row.get("danelfin_score", "") or ""),
        )

        # --- governance: composite_version is immutable once set ---
        existing_cv = str(row.get("composite_version", "")).strip()
        composite_version = existing_cv if existing_cv else "v1"

        row["yahoo_abr_normalized"]        = yahoo_abr_str
        row["composite_v2_yahoo"]          = str(v2_score)
        row["composite_version"]           = composite_version
        row["score_generation_timestamp"]  = ts

    print(f"Yahoo ABR coverage: {abr_hits} / {len(rows)} rows have ABR → yahoo_abr_normalized populated")

    # Spot-check
    spot_symbols = ["MCB", "AAPL", "NVDA", "SBS", "A", "KGC"]
    spot_map = {str(r.get("symbol", "")).strip().upper(): r for r in rows}
    print("\nSpot check (v1 vs v2_yahoo):")
    print(f"  {'SYM':<8} {'ESS':<16} {'Zacks':<6} {'ABR':>5} {'ABR_norm':>9} {'Danelfin':>9} {'v1':>8} {'v2':>8}")
    for sym in spot_symbols:
        r = spot_map.get(sym)
        if not r:
            continue
        print(
            f"  {sym:<8} {str(r.get('ess_score_text','')):<16} "
            f"{str(r.get('zacks_rating','')):<6} "
            f"{abr_map.get(sym,''):>5} "
            f"{str(r.get('yahoo_abr_normalized','')):>9} "
            f"{str(r.get('danelfin_score','')):>9} "
            f"{float(r.get('composite_score',0)):>8.4f} "
            f"{float(r.get('composite_v2_yahoo',0)):>8.4f}"
        )

    if dry_run:
        print("\n[DRY RUN] No files written.")
        return

    with UNIVERSE_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows → {UNIVERSE_PATH}")
    print(f"Columns: {len(headers)} (added {len(headers) - len(existing_headers)} new)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate composite v2 experimental scores.")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write.")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
