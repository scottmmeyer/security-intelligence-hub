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
) -> Path:
    """Fetch Danelfin scores for all *symbols*, write dated + latest CSVs.

    Returns the path of the dated output CSV.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}_danelfin.csv"
    latest_path = output_dir / "latest_danelfin.csv"

    symbol_list = [str(s).strip().upper() for s in symbols if str(s).strip()]

    rows: list[dict[str, str]] = []
    for i, sym in enumerate(symbol_list, start=1):
        if verbose:
            print(f"[{i}/{len(symbol_list)}] {sym}...", end=" ", flush=True)

        danelfin_raw, danelfin_score = fetch_danelfin_score(sym)

        row = {
            "symbol": sym,
            "danelfin_raw": str(danelfin_raw) if danelfin_raw is not None else "",
            "danelfin_score": f"{danelfin_score:.4f}" if danelfin_score is not None else "",
            "sourced_date": today,
        }
        rows.append(row)

        if verbose:
            if danelfin_raw is not None:
                print(f"AI={danelfin_raw}/10  →  score={danelfin_score:.2f}")
            else:
                print("no data")

        if i < len(symbol_list):
            time.sleep(random.uniform(delay_min, delay_max))

    _write_csv(output_path, rows)
    _write_csv(latest_path, rows)

    if verbose:
        with_score = sum(1 for r in rows if r["danelfin_score"])
        print(
            f"\nDanelfin fetch complete: {with_score}/{len(rows)} with score"
            f" → {output_path}"
        )

    return output_path


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
