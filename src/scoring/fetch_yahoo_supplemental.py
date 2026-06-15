"""Fetch supplemental analyst signals from Yahoo Finance via yfinance.

Fetches per-symbol: price_target, abr (analyst recommendation mean), and
eps_growth_5yr (long-term growth estimate) for use as display/filter signals.

These are supplemental columns and do NOT affect the composite score formula.

Output CSV: data/signals/yahoo/YYYY-MM-DD_yahoo_supplemental.csv
            data/signals/yahoo/latest_yahoo_supplemental.csv

Usage:
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_yahoo_supplemental.py \
        --symbols AGX CHRD CRC [--delay 1.0] [--output-dir data/signals/yahoo]
"""

from __future__ import annotations

import csv
import random
import time
from datetime import date
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "signals" / "yahoo"
_DEFAULT_DELAY_MIN = 0.5
_DEFAULT_DELAY_MAX = 2.0

_OUTPUT_HEADERS = [
    "symbol",
    "price_target",
    "abr",
    "analyst_count",
    "eps_growth_5yr",
    "current_price",
    "upside_pct",
    "sourced_date",
]


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        v = float(str(value).replace(",", "").strip())
        return None if (v != v) else v  # filter NaN
    except (ValueError, TypeError):
        return None


def fetch_yahoo_supplemental(symbol: str) -> dict[str, float | None]:
    """Fetch supplemental signals for one symbol from Yahoo Finance.

    Returns a dict with keys: price_target, abr, eps_growth_5yr, current_price.
    All values are float or None.
    """
    import yfinance as yf  # type: ignore

    sym = str(symbol).strip().upper()
    result: dict[str, float | int | None] = {
        "price_target": None,
        "abr": None,
        "analyst_count": None,
        "eps_growth_5yr": None,
        "current_price": None,
    }

    try:
        ticker = yf.Ticker(sym)
        info = ticker.info or {}
    except Exception:
        return result

    result["price_target"] = _to_float(info.get("targetMeanPrice"))
    result["abr"] = _to_float(info.get("recommendationMean"))
    # Analyst count: numberOfAnalystOpinions → int or None (ISSUE-08)
    _raw_count = info.get("numberOfAnalystOpinions")
    result["analyst_count"] = int(_raw_count) if _raw_count else None

    # Current price: prefer regularMarketPrice, fall back to previousClose
    result["current_price"] = _to_float(
        info.get("regularMarketPrice") or info.get("previousClose")
    )

    # 5-year EPS growth from long-term growth estimate
    try:
        growth = ticker.get_growth_estimates()
        if growth is not None and not growth.empty and "LTG" in growth.index:
            ltg_row = growth.loc["LTG"]
            stock_trend = ltg_row.get("stockTrend") if hasattr(ltg_row, "get") else None
            ltg_value = _to_float(stock_trend)
            if ltg_value is not None:
                # Convert decimal (0.15) → percent (15.0) if needed
                result["eps_growth_5yr"] = ltg_value * 100.0 if abs(ltg_value) <= 1.0 else ltg_value
    except Exception:
        pass

    return result


def fetch_yahoo_supplemental_for_symbols(
    symbols: Iterable[str],
    *,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
    verbose: bool = True,
    force_retry_symbols: set[str] | None = None,
    collect_stats: bool = False,
) -> Path | tuple[Path, dict[str, int]]:
    """Fetch supplemental signals for all symbols, write CSV, return path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}_yahoo_supplemental.csv"
    latest_path = output_dir / "latest_yahoo_supplemental.csv"

    symbol_list = [str(s).strip().upper() for s in symbols if str(s).strip()]
    force_retry = {str(s).strip().upper() for s in (force_retry_symbols or set()) if str(s).strip()}
    archived_rows = _load_rows_by_symbol(output_path)
    latest_rows = _load_rows_by_symbol(latest_path)
    pending_symbols: list[str] = []
    stats = {
        "skipped_checkpoint": 0,
        "skipped_already_covered": 0,
        "retried_failed_checkpoint": 0,
    }

    for symbol in symbol_list:
        row = archived_rows.get(symbol)
        if row is None:
            pending_symbols.append(symbol)
            continue
        if symbol not in force_retry:
            stats["skipped_checkpoint"] += 1
            continue
        if _is_yahoo_row_successful_today(row, today):
            stats["skipped_already_covered"] += 1
            continue
        stats["retried_failed_checkpoint"] += 1
        pending_symbols.append(symbol)

    if verbose and archived_rows:
        print(
            f"[resume] Yahoo: skipping {stats['skipped_checkpoint']} already checkpointed "
            f"symbols from {output_path.name}."
        )

    for i, sym in enumerate(pending_symbols, start=1):
        if verbose:
            print(f"[{i}/{len(pending_symbols)}] {sym}...", end=" ", flush=True)
        data = fetch_yahoo_supplemental(sym)
        time.sleep(random.uniform(delay_min, delay_max))

        price = data["current_price"]
        target = data["price_target"]
        upside: float | None = None
        if price is not None and target is not None and price > 0:
            upside = round((target - price) / price * 100, 2)

        row = {
            "symbol": sym,
            "price_target": f"{target:.2f}" if target is not None else "",
            "abr": f"{data['abr']:.2f}" if data["abr"] is not None else "",
            "analyst_count": str(data.get("analyst_count")) if data.get("analyst_count") is not None else "",
            "eps_growth_5yr": f"{data['eps_growth_5yr']:.1f}" if data["eps_growth_5yr"] is not None else "",
            "current_price": f"{price:.2f}" if price is not None else "",
            "upside_pct": f"{upside:.1f}" if upside is not None else "",
            "sourced_date": today,
        }
        archived_rows[sym] = row
        latest_rows[sym] = row
        _write_csv(output_path, list(archived_rows.values()))
        _write_csv(latest_path, list(latest_rows.values()))

        if verbose:
            parts = []
            if target is not None:
                parts.append(f"target=${target:.2f}")
            if upside is not None:
                parts.append(f"upside={upside:+.1f}%")
            if data["eps_growth_5yr"] is not None:
                parts.append(f"eps_5yr={data['eps_growth_5yr']:.1f}%")
            if data["abr"] is not None:
                parts.append(f"abr={data['abr']:.2f}")
            print("  ".join(parts) if parts else "no supplemental data")

    rows = list(archived_rows.values())

    if verbose:
        with_target = sum(1 for r in rows if r["price_target"])
        print(f"\nYahoo supplemental fetch complete: {with_target}/{len(rows)} with price target → {output_path}")

    if collect_stats:
        stats["requested"] = len(symbol_list)
        stats["attempted"] = len(pending_symbols)
        return output_path, stats
    return output_path


def _is_yahoo_row_successful_today(row: dict[str, str], today: str) -> bool:
    if str(row.get("sourced_date", "")).strip() != today:
        return False
    for key in ("current_price", "abr", "price_target", "analyst_count"):
        if str(row.get(key, "")).strip():
            return True
    return False


def _merge_into_latest(latest_path: Path, new_rows: list[dict[str, str]]) -> None:
    """Upsert *new_rows* into *latest_path*, preserving all previously-known symbols."""
    existing: dict[str, dict[str, str]] = {}
    if latest_path.exists():
        with latest_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    existing[sym] = dict(row)
    for row in new_rows:
        sym = str(row.get("symbol", "")).strip().upper()
        if sym:
            existing[sym] = row
    _write_csv(latest_path, list(existing.values()))


def _load_rows_by_symbol(path: Path) -> dict[str, dict[str, str]]:
    rows_by_symbol: dict[str, dict[str, str]] = {}
    if not path.exists():
        return rows_by_symbol
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                rows_by_symbol[sym] = dict(row)
    return rows_by_symbol


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_OUTPUT_HEADERS, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)


def load_latest_yahoo_supplemental(
    signals_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> dict[str, dict[str, str]]:
    """Load latest Yahoo supplemental cache into a symbol → field dict."""
    signals_dir = Path(signals_dir)
    latest_path = signals_dir / "latest_yahoo_supplemental.csv"
    if not latest_path.exists():
        return {}
    result: dict[str, dict[str, str]] = {}
    with latest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


if __name__ == "__main__":
    import argparse
    import csv as _csv

    parser = argparse.ArgumentParser(description="Fetch Yahoo supplemental signals.")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to fetch")
    parser.add_argument("--output-dir", default=str(_DEFAULT_OUTPUT_DIR))
    parser.add_argument("--delay-min", type=float, default=_DEFAULT_DELAY_MIN)
    parser.add_argument("--delay-max", type=float, default=_DEFAULT_DELAY_MAX)
    args = parser.parse_args()

    fetch_yahoo_supplemental_for_symbols(
        args.symbols,
        output_dir=args.output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
    )
