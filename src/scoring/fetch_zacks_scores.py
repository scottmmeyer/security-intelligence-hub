"""Fetch Zacks Rank scores for a list of symbols via the quote-feed.zacks.com API.

Zacks Rank scale: 1=Strong Buy (best) → 5=Strong Sell (worst).
This module converts rank to a normalized score on the same 1-5 ascending scale
used by the composite engine: score = 6 - zacks_rank  (1→5.0, 5→1.0).

Output CSV: data/signals/zacks/YYYY-MM-DD_zacks.csv
           data/signals/zacks/latest_zacks.csv  (always overwritten with today)

Usage (standalone):
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_zacks_scores.py \
        --symbols AAPL MSFT GOOG [--delay 4] [--output-dir data/signals/zacks]
"""

from __future__ import annotations

import csv
import json
import random
import re
import time
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

_QUOTE_FEED_PATHS = [
    "index",
    "quote",
    "quotes",
    "company",
    "profile",
    "estimates",
    "analyst",
    "earnings",
    "fundamentals",
    "recommendation",
    "ratings",
]

_OUTPUT_HEADERS = ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"]
_DEFAULT_DELAY_MIN = 3.0
_DEFAULT_DELAY_MAX = 7.0
_DEFAULT_TIMEOUT = 15.0
_DEFAULT_MAX_RETRIES = 2
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "signals" / "zacks"


def _http_get_json(url: str, timeout: float = _DEFAULT_TIMEOUT, retries: int = _DEFAULT_MAX_RETRIES) -> tuple[dict | None, str]:
    """Fetch URL and return (parsed_json, raw_text). raw_text is always the response body on success."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    for attempt in range(1, retries + 1):
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=timeout) as response:
                if int(getattr(response, "status", 200) or 200) == 429:
                    time.sleep(2 ** attempt)
                    continue
                payload = response.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(payload), payload
                except json.JSONDecodeError:
                    return None, payload
        except HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return None, ""
        except (URLError, OSError, TimeoutError):
            if attempt < retries:
                time.sleep(1.5 * attempt)
                continue
            return None, ""
    return None, ""


def _deep_merge(base: dict, update: dict) -> dict:
    """Merge update into base, skipping blank/None values."""
    result = dict(base)
    for key, value in update.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if key not in result or result[key] is None or (isinstance(result[key], str) and not result[key].strip()):
            result[key] = value
    return result


def _fetch_merged_entry(symbol: str) -> tuple[dict | None, str]:
    """Try each quote-feed path and merge non-blank fields across responses.

    Returns (merged_entry_dict, accumulated_raw_text). The raw text is the
    concatenation of all response bodies and is used as a fallback for
    supplemental field extraction via regex.
    """
    merged: dict = {}
    raw_texts: list[str] = []
    sym_upper = symbol.strip().upper()
    any_response = False

    for path in _QUOTE_FEED_PATHS:
        url = f"https://quote-feed.zacks.com/{path}?t={quote_plus(sym_upper)}"
        data, raw_text = _http_get_json(url)
        if raw_text:
            raw_texts.append(raw_text)
        if not isinstance(data, dict) or not data:
            continue

        entry = data.get(sym_upper)
        if not isinstance(entry, dict):
            entry = next((v for v in data.values() if isinstance(v, dict)), None)
        if not isinstance(entry, dict):
            continue

        any_response = True
        merged = _deep_merge(merged, entry)
        # Stop early if we already have what we need
        if merged.get("zacks_rank") or merged.get("rank"):
            break

    combined_text = "\n".join(raw_texts)
    return (merged if any_response else None), combined_text


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _extract_first_number(text: str, pattern: str) -> float | None:
    """Return the first number captured by *pattern* in *text*, or None."""
    try:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
        raw = str(match.group(1) or "").strip().lstrip("$").strip()
        if raw in {"", "-", "--", "N/A", "NA"}:
            return None
        return _to_float(raw)
    except (re.error, AttributeError, IndexError):
        return None


def _extract_supplemental(
    entry: dict, raw_text: str
) -> tuple[float | None, float | None, float | None]:
    """Extract (abr, price_target, eps_growth) from JSON entry dict and/or raw response text.

    Tries JSON field name variants first (cheap), then falls back to regex on
    the raw response text (same approach used by portfolio_manager).
    """
    # --- ABR ---
    abr: float | None = None
    for key in ("abr", "avg_broker_rating", "average_broker_rating", "rec_rating", "analyst_rating_int"):
        val = _to_float(entry.get(key))
        if val is not None:
            abr = val
            break
    if abr is None:
        abr = _extract_first_number(raw_text, r"Average\s*Broker\s*Rating[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?)")

    # --- Price target ---
    price_target: float | None = None
    for key in ("price_target", "consensus_price_target", "avg_price_target", "analyst_target_price", "target_price"):
        val = _to_float(entry.get(key))
        if val is not None:
            price_target = val
            break
    if price_target is None:
        price_target = _extract_first_number(raw_text, r"Price\s*Target[^0-9$]{0,80}(\$?[0-9]+(?:\.[0-9]+)?)")

    # --- EPS 5-year growth (%) ---
    eps_growth: float | None = None
    for key in ("eps_growth", "eps_long_term_growth", "long_term_growth_rate", "growth_rate_pct", "expected_eps_growth_rate"):
        val = _to_float(entry.get(key))
        if val is not None:
            eps_growth = val
            break
    if eps_growth is None:
        eps_growth = _extract_first_number(raw_text, r"EPS\s*Growth[^0-9\-]{0,80}(-?[0-9]+(?:\.[0-9]+)?)%")

    return abr, price_target, eps_growth


def _extract_rank(entry: dict) -> float | None:
    """Extract zacks_rank integer (1-5) from merged quote-feed entry."""
    for key in ("zacks_rank", "rank", "zacks_rank_text"):
        raw = entry.get(key)
        if raw is None:
            continue
        val = _to_float(raw)
        if val is not None and 1 <= val <= 5:
            return val
    return None


def fetch_zacks_data(
    symbol: str,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
) -> tuple[float | None, float | None, float | None, float | None, float | None]:
    """Fetch all Zacks signals for a single symbol.

    Returns (zacks_rank, zacks_score, abr, price_target, eps_growth) where:
      - zacks_rank:   1–5 integer (1=Strong Buy, 5=Strong Sell), or None
      - zacks_score:  normalized 1–5 ascending score (5=best), or None
      - abr:          Average Broker Rating (1.0=Strong Buy … 5.0=Sell), or None
      - price_target: analyst consensus price target in USD, or None
      - eps_growth:   5-year EPS growth estimate in percent, or None
    """
    entry, raw_text = _fetch_merged_entry(symbol)
    time.sleep(random.uniform(delay_min, delay_max))
    if entry is None:
        return None, None, None, None, None

    rank = _extract_rank(entry)
    score = round(6.0 - rank, 2) if rank is not None else None
    abr, price_target, eps_growth = _extract_supplemental(entry, raw_text)
    return rank, score, abr, price_target, eps_growth


def fetch_zacks_rank(
    symbol: str,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
) -> tuple[float | None, float | None]:
    """Fetch Zacks rank for a single symbol (backward-compatible wrapper).

    Returns (zacks_rank, zacks_score). Use fetch_zacks_data() to also get
    abr, price_target, and eps_growth in the same HTTP call.
    """
    rank, score, _, _, _ = fetch_zacks_data(symbol, delay_min=delay_min, delay_max=delay_max)
    return rank, score


def fetch_zacks_scores_for_symbols(
    symbols: Iterable[str],
    *,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
    verbose: bool = True,
) -> Path:
    """Fetch Zacks ranks for all symbols, write to dated CSV, return path.

    Returns the path to the written CSV file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}_zacks.csv"
    latest_path = output_dir / "latest_zacks.csv"

    symbol_list = [str(s).strip().upper() for s in symbols if str(s).strip()]
    archived_rows = _load_rows_by_symbol(output_path)
    latest_rows = _load_rows_by_symbol(latest_path)
    pending_symbols = [symbol for symbol in symbol_list if symbol not in archived_rows]

    if verbose and archived_rows:
        print(
            f"[resume] Zacks: skipping {len(symbol_list) - len(pending_symbols)} already checkpointed "
            f"symbols from {output_path.name}."
        )

    for i, symbol in enumerate(pending_symbols, start=1):
        if verbose:
            print(f"[{i}/{len(pending_symbols)}] Fetching Zacks data for {symbol}...", end=" ", flush=True)
        rank, score, abr, price_target, eps_growth = fetch_zacks_data(
            symbol, delay_min=delay_min, delay_max=delay_max
        )
        row = {
            "symbol": symbol,
            "zacks_rank": str(rank) if rank is not None else "",
            "zacks_score": str(score) if score is not None else "",
            "abr": str(abr) if abr is not None else "",
            "price_target": str(price_target) if price_target is not None else "",
            "eps_growth": str(eps_growth) if eps_growth is not None else "",
            "sourced_date": today,
        }
        archived_rows[symbol] = row
        latest_rows[symbol] = row
        _write_csv(output_path, list(archived_rows.values()))
        _write_csv(latest_path, list(latest_rows.values()))
        if verbose:
            if rank is not None:
                extras = ""
                if price_target is not None:
                    extras += f"  target=${price_target:.2f}"
                if eps_growth is not None:
                    extras += f"  eps_growth={eps_growth:.1f}%"
                print(f"rank={rank:.0f}  score={score}{extras}")
            else:
                print("no data")

    rows = list(archived_rows.values())

    if verbose:
        found = sum(1 for r in rows if r["zacks_rank"])
        print(f"\nZacks fetch complete: {found}/{len(rows)} symbols with data → {output_path}")

    return output_path


def _merge_into_latest(latest_path: Path, new_rows: list[dict[str, str]]) -> None:
    """Upsert *new_rows* into *latest_path*, preserving all previously-known symbols.

    The dated archive (output_path) is a point-in-time snapshot of just this
    batch, but latest_zacks.csv is the cumulative best-known score per symbol.
    Symbols in *new_rows* overwrite any existing entry; all other symbols are kept.
    """
    existing: dict[str, dict[str, str]] = {}
    if latest_path.exists():
        with latest_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    existing[sym] = dict(row)
    # Upsert — new rows win
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


def load_latest_zacks_scores(
    signals_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> dict[str, float | None]:
    """Load latest Zacks scores into a symbol→zacks_score dict.

    Returns empty dict if no cache file exists.
    Scores are on the 1-5 ascending scale (5=Strong Buy, 1=Strong Sell).
    """
    signals_dir = Path(signals_dir)
    latest_path = signals_dir / "latest_zacks.csv"
    if not latest_path.exists():
        return {}

    result: dict[str, float | None] = {}
    with latest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            raw_score = str(row.get("zacks_score", "")).strip()
            try:
                result[symbol] = float(raw_score)
            except (ValueError, TypeError):
                result[symbol] = None
    return result


_BULLISH_ESS_TEXTS: frozenset[str] = frozenset({"BULLISH", "VERY_BULLISH"})


def build_smart_refresh_list(
    universe_csv: Path | str = _REPO_ROOT / "data" / "current" / "base_equity_universe.csv",
    zacks_cache_csv: Path | str = _DEFAULT_OUTPUT_DIR / "latest_zacks.csv",
    bullish_ess_texts: frozenset[str] | None = None,
    forced_symbols: set[str] | None = None,
) -> list[str]:
    """Return the prioritized list of symbols to fetch in a smart-refresh run.

    Priority 0 (mandatory): symbols in *forced_symbols* (e.g. current portfolio
    holdings).  These are always included regardless of ESS category or cache
    status to guarantee held positions never run on stale Zacks data.

    Priority 1 (always fetch): symbols whose ``starmine_ess_text`` is in
    *bullish_ess_texts* (default: BULLISH and VERY_BULLISH).  These are the
    symbols where accuracy matters most for the composite score.

    Priority 2 (fill gaps): symbols that have no entry in the Zacks cache.

    All other symbols can use the ESS ``ess_zacks_rating`` pass-through as a
    cheap proxy fallback and are excluded from the fetch list.

    Returns a deduplicated, ordered list: forced symbols first, then bullish,
    then uncached.
    """
    if bullish_ess_texts is None:
        bullish_ess_texts = _BULLISH_ESS_TEXTS

    cached_symbols: set[str] = set()
    cache_path = Path(zacks_cache_csv)
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    cached_symbols.add(sym)

    universe_path = Path(universe_csv)
    if not universe_path.exists():
        return []

    forced_list: list[str] = []
    bullish_list: list[str] = []
    uncached_list: list[str] = []
    seen: set[str] = set()

    # Priority 0: forced symbols (portfolio holdings guarantee)
    if forced_symbols:
        for sym in sorted(forced_symbols):
            sym = str(sym).strip().upper()
            if sym and sym not in seen:
                forced_list.append(sym)
                seen.add(sym)

    with universe_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            ess_text = str(row.get("starmine_ess_text", "")).strip().upper()
            if ess_text in bullish_ess_texts:
                bullish_list.append(sym)
            elif sym not in cached_symbols:
                uncached_list.append(sym)

    return forced_list + bullish_list + uncached_list


if __name__ == "__main__":
    import argparse
    import csv as _csv
    from pathlib import Path as _Path

    parser = argparse.ArgumentParser(description="Fetch Zacks Rank scores for a list of symbols.")
    parser.add_argument("--symbols", nargs="+", help="Symbols to fetch (overrides --from-universe)")
    parser.add_argument("--from-universe", metavar="CSV", help="Path to analytical_universe.csv or base_equity_universe.csv to read symbols from")
    parser.add_argument("--smart-refresh", action="store_true", help="Auto-select symbols: bullish ESS first, then symbols absent from cache")
    parser.add_argument("--output-dir", default=str(_DEFAULT_OUTPUT_DIR), help="Output directory for zacks CSV files")
    parser.add_argument("--delay-min", type=float, default=_DEFAULT_DELAY_MIN)
    parser.add_argument("--delay-max", type=float, default=_DEFAULT_DELAY_MAX)
    parser.add_argument("--limit", type=int, default=None, help="Max symbols to fetch (for testing)")
    args = parser.parse_args()

    if args.symbols:
        syms = args.symbols
    elif args.smart_refresh:
        syms = build_smart_refresh_list(
            universe_csv=_REPO_ROOT / "data" / "current" / "base_equity_universe.csv",
            zacks_cache_csv=_Path(args.output_dir) / "latest_zacks.csv",
        )
        print(f"Smart refresh: {len(syms)} symbols selected ({sum(1 for s in syms if True)} total)")
    elif args.from_universe:
        universe_path = _Path(args.from_universe)
        syms = []
        with universe_path.open("r", encoding="utf-8", newline="") as f:
            for row in _csv.DictReader(f):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    syms.append(sym)
        syms = list(dict.fromkeys(syms))  # dedupe, preserve order
    else:
        # Default: read from current base universe
        default_universe = _REPO_ROOT / "data" / "current" / "base_equity_universe.csv"
        syms = []
        if default_universe.exists():
            with default_universe.open("r", encoding="utf-8", newline="") as f:
                for row in _csv.DictReader(f):
                    sym = str(row.get("symbol", "")).strip().upper()
                    if sym:
                        syms.append(sym)
            syms = list(dict.fromkeys(syms))
        else:
            parser.error("No symbols provided and no base_equity_universe.csv found. Use --symbols or --from-universe.")

    if args.limit:
        syms = syms[: args.limit]

    fetch_zacks_scores_for_symbols(
        syms,
        output_dir=args.output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
    )
