"""Fetch Danelfin AI scores by scraping danelfin.com/stock/{TICKER}.

Danelfin AI Score scale: 1–10 (10 = highest probability of beating the market in 3 months).
This module converts the raw score to a normalized score on the same 1–5 ascending
scale used by the composite engine:

    danelfin_score = danelfin_raw / 2.0   →  raw 10 → 5.0, raw 1 → 0.5

No API key required.  Scores are scraped from the public stock page using the
aria-label pattern established in the sister portfolio_manager project:

    https://danelfin.com/stock/{TICKER}

The first five ``aria-label="N out of 10"`` elements on the page map to:
  [0] AI Score  [1] Fundamental  [2] Technical  [3] Sentiment  [4] Low Risk

Output CSV: data/signals/danelfin/YYYY-MM-DD_danelfin.csv
            data/signals/danelfin/latest_danelfin.csv  (always overwritten with today)

Usage (standalone):
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_danelfin_scores.py \\
        --symbols AGX CHRD CRC [--delay 5.0] [--output-dir data/signals/danelfin]
"""

from __future__ import annotations

import csv
import re
import random
import time
from datetime import date
from pathlib import Path
from typing import Iterable

import requests

_DEFAULT_DELAY_MIN = 4.5
_DEFAULT_DELAY_MAX = 7.0
_REQUEST_TIMEOUT = 20

_OUTPUT_HEADERS = ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "signals" / "danelfin"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://danelfin.com/",
}

# Scores appear as aria-label="N out of 10" — first 5 occurrences in fixed order.
_SCORE_RE = re.compile(r'aria-label="(\d+) out of 10"')

# Ticker URL overrides for path-unsafe symbols (e.g. MOG/A → MOG.A)
_URL_SYMBOL_OVERRIDES = {
    "MOG/A": "MOG.A",
}


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

def _stock_url(symbol: str) -> str:
    s = str(symbol).strip().upper()
    s = _URL_SYMBOL_OVERRIDES.get(s, s.replace("/", "."))
    return f"https://danelfin.com/stock/{s}"


def fetch_danelfin_score(symbol: str) -> tuple[int | None, float | None]:
    """Scrape the Danelfin AI score for *symbol*.

    Returns ``(danelfin_raw, danelfin_score)`` where:
        - ``danelfin_raw`` is the integer 1–10 from the page, or ``None``
        - ``danelfin_score`` is ``danelfin_raw / 2.0`` on the 1–5 composite
          scale, or ``None``
    """
    url = _stock_url(symbol)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            return None, None
        html = resp.text
    except requests.RequestException:
        return None, None

    score_values = _SCORE_RE.findall(html)
    if not score_values:
        return None, None

    try:
        danelfin_raw = int(score_values[0])
        if not (1 <= danelfin_raw <= 10):
            return None, None
        return danelfin_raw, round(danelfin_raw / 2.0, 4)
    except (ValueError, IndexError):
        return None, None


# ---------------------------------------------------------------------------
# Batch fetch + CSV output
# ---------------------------------------------------------------------------

def fetch_danelfin_scores_for_symbols(
    symbols: Iterable[str],
    *,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
    verbose: bool = True,
    force_retry_symbols: set[str] | None = None,
    collect_stats: bool = False,
) -> Path | tuple[Path, dict[str, int]]:
    """Fetch Danelfin scores for all *symbols*, write dated + latest CSVs.

    Returns the path of the dated output CSV.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}_danelfin.csv"
    latest_path = output_dir / "latest_danelfin.csv"

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
        if _is_danelfin_row_successful_today(row, today):
            stats["skipped_already_covered"] += 1
            continue
        stats["retried_failed_checkpoint"] += 1
        pending_symbols.append(symbol)

    if verbose and archived_rows:
        print(
            f"[resume] Danelfin: skipping {stats['skipped_checkpoint']} already checkpointed "
            f"symbols from {output_path.name}."
        )

    for i, sym in enumerate(pending_symbols, start=1):
        if verbose:
            print(f"[{i}/{len(pending_symbols)}] {sym}...", end=" ", flush=True)

        danelfin_raw, danelfin_score = fetch_danelfin_score(sym)

        row = {
            "symbol": sym,
            "danelfin_raw": str(danelfin_raw) if danelfin_raw is not None else "",
            "danelfin_score": f"{danelfin_score:.4f}" if danelfin_score is not None else "",
            "sourced_date": today,
        }
        archived_rows[sym] = row
        latest_rows[sym] = row
        _write_csv(output_path, list(archived_rows.values()))
        _write_csv(latest_path, list(latest_rows.values()))

        if verbose:
            if danelfin_raw is not None:
                print(f"AI={danelfin_raw}/10  →  score={danelfin_score:.2f}")
            else:
                print("no data")

        if i < len(pending_symbols):
            time.sleep(random.uniform(delay_min, delay_max))

    rows = list(archived_rows.values())

    if verbose:
        with_score = sum(1 for r in rows if r["danelfin_score"])
        print(
            f"\nDanelfin fetch complete: {with_score}/{len(rows)} with score"
            f" → {output_path}"
        )

    if collect_stats:
        stats["requested"] = len(symbol_list)
        stats["attempted"] = len(pending_symbols)
        return output_path, stats
    return output_path


def _is_danelfin_row_successful_today(row: dict[str, str], today: str) -> bool:
    if str(row.get("sourced_date", "")).strip() != today:
        return False
    return bool(str(row.get("danelfin_score", "")).strip() or str(row.get("danelfin_raw", "")).strip())


# ---------------------------------------------------------------------------
# Cache loader (consumed by analytical_universe_manager)
# ---------------------------------------------------------------------------

def load_latest_danelfin_scores(
    signals_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> dict[str, float]:
    """Load latest Danelfin cache into a ``{symbol: danelfin_score}`` dict.

    Returns an empty dict if the cache file does not exist.
    """
    signals_dir = Path(signals_dir)
    latest_path = signals_dir / "latest_danelfin.csv"
    if not latest_path.exists():
        return {}
    result: dict[str, float] = {}
    with latest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sym = str(row.get("symbol", "")).strip().upper()
            raw_score = str(row.get("danelfin_score", "")).strip()
            if sym and raw_score:
                try:
                    result[sym] = float(raw_score)
                except ValueError:
                    pass
    return result


# ---------------------------------------------------------------------------
# Internal CSV writer
# ---------------------------------------------------------------------------

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
        writer = csv.DictWriter(
            handle, fieldnames=_OUTPUT_HEADERS, extrasaction="ignore", restval=""
        )
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch Danelfin AI scores by scraping danelfin.com/stock/TICKER."
    )
    parser.add_argument(
        "--symbols", nargs="+", required=True,
        help="Ticker symbols to fetch (e.g. AGX CHRD CRC)",
    )
    parser.add_argument(
        "--output-dir", default=str(_DEFAULT_OUTPUT_DIR),
        help=f"Output directory for CSVs (default: {_DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--delay-min", type=float, default=_DEFAULT_DELAY_MIN,
        help="Minimum inter-request delay in seconds (default: 4.5)",
    )
    parser.add_argument(
        "--delay-max", type=float, default=_DEFAULT_DELAY_MAX,
        help="Maximum inter-request delay in seconds (default: 7.0)",
    )
    args = parser.parse_args()

    fetch_danelfin_scores_for_symbols(
        args.symbols,
        output_dir=args.output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
    )
