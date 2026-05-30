"""Fetch sector, industry, country, and security type metadata from Yahoo Finance.

Enriches the analytical universe with GICS sector and industry classifications
for use in filtering, grouping, and the Symbol Lookup UI panel.

Output CSV: data/signals/security_metadata/YYYY-MM-DD_security_metadata.csv
            data/signals/security_metadata/latest_security_metadata.csv

Columns: symbol, sector, industry, country, quote_type, sourced_date

Usage:
    # Fetch for all symbols in base_equity_universe:
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_security_metadata.py \
        --from-universe data/current/base_equity_universe.csv

    # Fetch for specific symbols:
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_security_metadata.py \
        --symbols MMM AAPL MSFT

    # Smart refresh: skip symbols already fetched in latest cache
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_security_metadata.py \
        --from-universe data/current/base_equity_universe.csv --smart-refresh
"""

from __future__ import annotations

import csv
import random
import time
from datetime import date
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "signals" / "security_metadata"
_DEFAULT_DELAY_MIN = 0.3
_DEFAULT_DELAY_MAX = 1.2

_OUTPUT_HEADERS = [
    "symbol",
    "sector",
    "industry",
    "country",
    "quote_type",
    "sourced_date",
]


def fetch_security_metadata(symbol: str) -> dict[str, str]:
    """Fetch sector/industry/country metadata for one symbol from Yahoo Finance."""
    import yfinance as yf  # type: ignore

    sym = str(symbol).strip().upper()
    result: dict[str, str] = {
        "sector": "",
        "industry": "",
        "country": "",
        "quote_type": "",
    }

    try:
        ticker = yf.Ticker(sym)
        info = ticker.info or {}
    except Exception:
        return result

    result["sector"] = str(info.get("sector") or "").strip()
    result["industry"] = str(info.get("industry") or "").strip()
    result["country"] = str(info.get("country") or "").strip()
    result["quote_type"] = str(info.get("quoteType") or "").strip()

    return result


def load_latest_security_metadata(
    signals_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> dict[str, dict[str, str]]:
    """Load latest security metadata cache into a symbol → field dict."""
    signals_dir = Path(signals_dir)
    latest_path = signals_dir / "latest_security_metadata.csv"
    if not latest_path.exists():
        return {}
    result: dict[str, dict[str, str]] = {}
    with latest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_OUTPUT_HEADERS, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)


def fetch_security_metadata_for_symbols(
    symbols: Iterable[str],
    *,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
    smart_refresh: bool = False,
    verbose: bool = True,
) -> Path:
    """Fetch metadata for all symbols, merge with existing cache, write CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}_security_metadata.csv"
    latest_path = output_dir / "latest_security_metadata.csv"

    symbol_list = [str(s).strip().upper() for s in symbols if str(s).strip()]

    # Smart refresh: load existing cache and skip already-fetched symbols
    existing: dict[str, dict[str, str]] = {}
    if smart_refresh and latest_path.exists():
        existing = load_latest_security_metadata(output_dir)
        if verbose:
            print(f"Smart refresh: {len(existing)} symbols already cached")

    to_fetch = [s for s in symbol_list if s not in existing] if smart_refresh else symbol_list

    if verbose:
        print(f"Fetching metadata for {len(to_fetch)} symbols (skipping {len(symbol_list) - len(to_fetch)} cached)...")

    new_rows: dict[str, dict[str, str]] = {}
    for i, sym in enumerate(to_fetch, start=1):
        if verbose:
            print(f"[{i}/{len(to_fetch)}] {sym}...", end=" ", flush=True)

        data = fetch_security_metadata(sym)
        time.sleep(random.uniform(delay_min, delay_max))

        row = {
            "symbol": sym,
            "sector": data["sector"],
            "industry": data["industry"],
            "country": data["country"],
            "quote_type": data["quote_type"],
            "sourced_date": today,
        }
        new_rows[sym] = row

        if verbose:
            parts = []
            if data["sector"]:
                parts.append(data["sector"])
            if data["industry"]:
                parts.append(data["industry"])
            if data["country"]:
                parts.append(data["country"])
            if data["quote_type"] and data["quote_type"] != "EQUITY":
                parts.append(data["quote_type"])
            print(" | ".join(parts) if parts else "(no metadata)")

    # Merge: new rows override existing, preserve existing for symbols not re-fetched
    merged: dict[str, dict[str, str]] = {**existing, **new_rows}

    # Output in the order of the requested symbol list (preserving original order)
    ordered_rows = [merged[s] for s in symbol_list if s in merged]
    # Append any symbols from existing that weren't in the request
    seen = set(symbol_list)
    for s, row in existing.items():
        if s not in seen:
            ordered_rows.append(row)

    _write_csv(output_path, ordered_rows)
    _write_csv(latest_path, ordered_rows)

    with_sector = sum(1 for r in ordered_rows if r.get("sector"))
    etf_count = sum(1 for r in ordered_rows if r.get("quote_type") == "ETF")

    if verbose:
        print(
            f"\nSecurity metadata fetch complete: "
            f"{with_sector}/{len(ordered_rows)} with sector, "
            f"{etf_count} ETFs → {output_path}"
        )

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch sector/industry metadata from Yahoo Finance.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", nargs="+", help="Symbols to fetch")
    group.add_argument("--from-universe", help="Path to base_equity_universe.csv or analytical_universe.csv")
    parser.add_argument("--output-dir", default=str(_DEFAULT_OUTPUT_DIR))
    parser.add_argument("--delay-min", type=float, default=_DEFAULT_DELAY_MIN)
    parser.add_argument("--delay-max", type=float, default=_DEFAULT_DELAY_MAX)
    parser.add_argument("--smart-refresh", action="store_true", help="Skip symbols already in latest cache")
    args = parser.parse_args()

    if args.symbols:
        symbols = args.symbols
    else:
        universe_path = Path(args.from_universe)
        with universe_path.open("r", encoding="utf-8", newline="") as f:
            symbols = [row["symbol"] for row in csv.DictReader(f) if row.get("symbol", "").strip()]
        # Deduplicate while preserving order
        seen_set: set[str] = set()
        unique: list[str] = []
        for s in symbols:
            su = s.strip().upper()
            if su not in seen_set:
                seen_set.add(su)
                unique.append(su)
        symbols = unique
        print(f"Loaded {len(symbols)} unique symbols from {universe_path.name}")

    fetch_security_metadata_for_symbols(
        symbols,
        output_dir=args.output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        smart_refresh=args.smart_refresh,
    )
