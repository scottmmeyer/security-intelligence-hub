"""Manage supplemental watchlist symbols that are not in the daily ESS files.

Usage:
    # List all watchlist symbols
    PYTHONPATH=. .venv/bin/python scripts/watchlist.py list

    # Add a symbol interactively
    PYTHONPATH=. .venv/bin/python scripts/watchlist.py add NVDA

    # Add a symbol with all fields specified
    PYTHONPATH=. .venv/bin/python scripts/watchlist.py add NVDA \\
        --name "NVIDIA Corporation" \\
        --security-type "Common Stock" \\
        --geography US \\
        --market-cap-bucket MEGA \\
        --market-cap-raw 3200000000000 \\
        --note "GPU/AI chipmaker"

    # Remove a symbol
    PYTHONPATH=. .venv/bin/python scripts/watchlist.py remove NVDA
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WATCHLIST_PATH = _REPO_ROOT / "data" / "supplemental" / "watchlist.csv"

_WATCHLIST_HEADERS = [
    "symbol",
    "company_name",
    "security_type",
    "geography",
    "market_cap_raw_usd",
    "market_cap_bucket",
    "coverage_domain",
    "starmine_ess_text",
    "ess_zacks_rating",
    "note",
]

_VALID_GEOGRAPHIES = {"US", "INTERNATIONAL"}
_VALID_BUCKETS = {"MEGA", "LARGE", "MID", "SMALL", "MICRO"}


def _load() -> list[dict]:
    if not _WATCHLIST_PATH.exists():
        return []
    with _WATCHLIST_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _save(rows: list[dict]) -> None:
    _WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _WATCHLIST_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_WATCHLIST_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _prompt(label: str, default: str = "", valid: set[str] | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    if valid:
        suffix += f" ({'/'.join(sorted(valid))})"
    while True:
        answer = input(f"  {label}{suffix}: ").strip()
        if not answer:
            answer = default
        if valid and answer.upper() not in valid:
            print(f"    Must be one of: {', '.join(sorted(valid))}")
            continue
        return answer.upper() if valid else answer


def cmd_list(args: argparse.Namespace) -> None:
    rows = _load()
    if not rows:
        print("Watchlist is empty.")
        return
    col = max(len(r.get("symbol", "")) for r in rows) + 2
    print(f"\n{'Symbol':<{col}} {'Geography':<14} {'Bucket':<8} {'Company'}")
    print("-" * 70)
    for r in sorted(rows, key=lambda x: x.get("symbol", "")):
        print(
            f"{r.get('symbol', ''):<{col}}"
            f" {r.get('geography', ''):<14}"
            f" {r.get('market_cap_bucket', ''):<8}"
            f" {r.get('company_name', '')}"
        )
    print(f"\n{len(rows)} symbol(s) in watchlist.\n")


def cmd_add(args: argparse.Namespace) -> None:
    symbol = args.symbol.strip().upper()
    rows = _load()
    existing = {r.get("symbol", "").upper() for r in rows}

    if symbol in existing:
        print(f"{symbol} is already in the watchlist. Use 'remove' then 're-add' to update.")
        sys.exit(1)

    # If all required args are provided, skip interactive prompts
    if args.name and args.geography and args.market_cap_bucket:
        row = {
            "symbol": symbol,
            "company_name": args.name,
            "security_type": args.security_type or "Common Stock",
            "geography": args.geography.upper(),
            "market_cap_raw_usd": str(args.market_cap_raw or ""),
            "market_cap_bucket": args.market_cap_bucket.upper(),
            "coverage_domain": "WATCHLIST",
            "starmine_ess_text": "",
            "ess_zacks_rating": "",
            "note": args.note or "",
        }
    else:
        print(f"\nAdding {symbol} to watchlist. Press Enter to accept defaults.\n")
        row = {
            "symbol": symbol,
            "company_name": _prompt("Company name", args.name or ""),
            "security_type": _prompt("Security type", args.security_type or "Common Stock"),
            "geography": _prompt("Geography", args.geography or "US", _VALID_GEOGRAPHIES),
            "market_cap_raw_usd": _prompt("Market cap USD (raw integer, optional)", str(args.market_cap_raw or "")),
            "market_cap_bucket": _prompt("Market cap bucket", args.market_cap_bucket or "LARGE", _VALID_BUCKETS),
            "coverage_domain": "WATCHLIST",
            "starmine_ess_text": "",
            "ess_zacks_rating": "",
            "note": _prompt("Note (optional)", args.note or ""),
        }

    rows.append(row)
    _save(rows)
    print(f"\nAdded {symbol} ({row['company_name']}) to watchlist.")
    print(f"Run the pipeline or score_lookup to see its composite score.\n")


def cmd_remove(args: argparse.Namespace) -> None:
    symbol = args.symbol.strip().upper()
    rows = _load()
    before = len(rows)
    rows = [r for r in rows if r.get("symbol", "").upper() != symbol]
    if len(rows) == before:
        print(f"{symbol} not found in watchlist.")
        sys.exit(1)
    _save(rows)
    print(f"Removed {symbol} from watchlist.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage supplemental watchlist symbols.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all watchlist symbols")

    add_p = sub.add_parser("add", help="Add a symbol to the watchlist")
    add_p.add_argument("symbol", help="Ticker symbol")
    add_p.add_argument("--name", help="Company name")
    add_p.add_argument("--security-type", default="Common Stock")
    add_p.add_argument("--geography", choices=["US", "INTERNATIONAL"])
    add_p.add_argument("--market-cap-raw", type=int, help="Raw market cap in USD")
    add_p.add_argument("--market-cap-bucket", choices=list(_VALID_BUCKETS))
    add_p.add_argument("--note", help="Free-text note")

    rem_p = sub.add_parser("remove", help="Remove a symbol from the watchlist")
    rem_p.add_argument("symbol", help="Ticker symbol")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    {"list": cmd_list, "add": cmd_add, "remove": cmd_remove}[args.command](args)
