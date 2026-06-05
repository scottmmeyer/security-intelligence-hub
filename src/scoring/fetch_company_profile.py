"""Fetch company profile data from Yahoo Finance for display enrichment.

Fetches per-symbol: long_name, city, state, country, business_summary
for use in the Company Snapshot UI panel. Display-only — no scoring impact.

Output CSV: data/signals/company_profile/YYYY-MM-DD_company_profile.csv
            data/signals/company_profile/latest_company_profile.csv

Columns: symbol, long_name, city, state, country, business_summary, sourced_date

Usage:
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_company_profile.py \\
        --symbols VRT DELL TSM [--delay 1.0] [--output-dir data/signals/company_profile]
"""

from __future__ import annotations

import csv
import re
import random
import time
from datetime import date
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "signals" / "company_profile"
_DEFAULT_DELAY_MIN = 0.4
_DEFAULT_DELAY_MAX = 1.5
_MAX_SUMMARY_CHARS = 250

_OUTPUT_HEADERS = [
    "symbol",
    "long_name",
    "city",
    "state",
    "country",
    "business_summary",
    "sourced_date",
]

# Boilerplate patterns to strip from the beginning of summaries
_BOILERPLATE_RE = re.compile(
    r"^(?:Together,?\s+)?(?:the company|it)\s+(?:also\s+)?",
    re.IGNORECASE,
)


def _truncate_summary(raw: str, max_chars: int = _MAX_SUMMARY_CHARS) -> str:
    """Return a concise business description from a raw Yahoo longBusinessSummary.

    Strategy:
    - Take the first complete sentence that fits within max_chars.
    - If the first sentence alone exceeds max_chars, truncate at the last space.
    - Append '…' if truncated.
    """
    if not raw:
        return ""

    # Clean up whitespace
    text = " ".join(raw.split())

    # Split on sentence boundaries (period + space + uppercase, or period + end)
    sentences = re.split(r"(?<=\.)\s+(?=[A-Z])", text)

    result = ""
    for sentence in sentences:
        candidate = (result + " " + sentence).strip() if result else sentence.strip()
        if len(candidate) <= max_chars:
            result = candidate
        else:
            break

    # If even the first sentence is too long, hard-truncate
    if not result:
        result = text[:max_chars].rsplit(" ", 1)[0]
        return result.rstrip(".,;") + "…"

    # Add ellipsis if we didn't take all sentences
    full_text = " ".join(s.strip() for s in sentences)
    if len(result) < len(full_text) - 5:
        result = result.rstrip(".,;") + "…"

    return result


def _compose_hq(city: str, state: str, country: str) -> str:
    """Compose a human-readable HQ location string."""
    parts = [p.strip() for p in [city, state, country] if p.strip()]
    return ", ".join(parts) if parts else ""


def fetch_company_profile(symbol: str) -> dict[str, str]:
    """Fetch company profile for one symbol from Yahoo Finance.

    Returns a dict with keys: long_name, city, state, country, business_summary.
    All values are strings; empty string if unavailable.
    """
    import yfinance as yf  # type: ignore

    sym = str(symbol).strip().upper()
    result: dict[str, str] = {
        "long_name": "",
        "city": "",
        "state": "",
        "country": "",
        "business_summary": "",
    }

    try:
        ticker = yf.Ticker(sym)
        info = ticker.info or {}
    except Exception:
        return result

    result["long_name"] = str(info.get("longName") or info.get("shortName") or "").strip()
    result["city"] = str(info.get("city") or "").strip()
    result["state"] = str(info.get("state") or "").strip()
    result["country"] = str(info.get("country") or "").strip()

    raw_summary = str(info.get("longBusinessSummary") or "").strip()
    result["business_summary"] = _truncate_summary(raw_summary)

    return result


def load_latest_company_profile(
    signals_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> dict[str, dict[str, str]]:
    """Load latest company profile cache into a symbol → field dict."""
    signals_dir = Path(signals_dir)
    latest_path = signals_dir / "latest_company_profile.csv"
    result: dict[str, dict[str, str]] = {}
    if not latest_path.exists():
        return result
    with latest_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


def fetch_company_profile_for_symbols(
    symbols: Iterable[str],
    *,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
    verbose: bool = True,
) -> Path:
    """Fetch company profiles for all symbols, write CSV, return latest path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}_company_profile.csv"
    latest_path = output_dir / "latest_company_profile.csv"

    symbol_list = [str(s).strip().upper() for s in symbols if str(s).strip()]
    archived_rows = _load_rows_by_symbol(output_path)
    latest_rows = _load_rows_by_symbol(latest_path)
    pending_symbols = [sym for sym in symbol_list if sym not in archived_rows]

    if verbose and len(symbol_list) > len(pending_symbols):
        print(
            f"[resume] Company profile: skipping {len(symbol_list) - len(pending_symbols)} "
            f"already cached symbols."
        )

    for i, sym in enumerate(pending_symbols, start=1):
        if verbose:
            print(f"[{i}/{len(pending_symbols)}] {sym}...", end=" ", flush=True)
        data = fetch_company_profile(sym)
        time.sleep(random.uniform(delay_min, delay_max))

        row = {
            "symbol": sym,
            "long_name": data["long_name"],
            "city": data["city"],
            "state": data["state"],
            "country": data["country"],
            "business_summary": data["business_summary"],
            "sourced_date": today,
        }
        archived_rows[sym] = row
        latest_rows[sym] = row
        _write_csv(output_path, list(archived_rows.values()))
        _write_csv(latest_path, list(latest_rows.values()))

        if verbose:
            parts = []
            if data["long_name"]:
                parts.append(data["long_name"][:40])
            hq = _compose_hq(data["city"], data["state"], data["country"])
            if hq:
                parts.append(hq)
            print("  |  ".join(parts) if parts else "no data")

    if verbose:
        rows = list(archived_rows.values())
        with_name = sum(1 for r in rows if r.get("long_name"))
        with_desc = sum(1 for r in rows if r.get("business_summary"))
        print(
            f"\nCompany profile fetch complete: "
            f"{with_name}/{len(rows)} with name, "
            f"{with_desc}/{len(rows)} with description → {latest_path}"
        )

    return latest_path


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
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_OUTPUT_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch company profile data from Yahoo Finance.")
    parser.add_argument("--symbols", nargs="+", help="Symbols to fetch")
    parser.add_argument(
        "--from-universe",
        metavar="CSV",
        help="CSV file with a 'symbol' column to fetch in bulk",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Output directory (default: data/signals/company_profile)",
    )
    parser.add_argument("--delay", type=float, default=None, help="Fixed delay between requests")
    args = parser.parse_args()

    symbols: list[str] = []
    if args.symbols:
        symbols.extend(args.symbols)
    if args.from_universe:
        with open(args.from_universe, "r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    symbols.append(sym)

    if not symbols:
        parser.error("Provide --symbols or --from-universe")

    delay_min = args.delay if args.delay is not None else _DEFAULT_DELAY_MIN
    delay_max = args.delay if args.delay is not None else _DEFAULT_DELAY_MAX

    fetch_company_profile_for_symbols(
        symbols,
        output_dir=Path(args.output_dir),
        delay_min=delay_min,
        delay_max=delay_max,
    )
