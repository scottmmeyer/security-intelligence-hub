"""FMP full-universe batch fetcher — ISSUE-01.

Fetches all 4 FMP signal datasets for every eligible symbol in the
analytical universe using per-symbol calls with smart-resume support.

Strategy:
- Priority 1: deployment queue candidates (highest operator value)
- Priority 2: full analytical universe (equities only)
- Skips already-cached symbols (smart-resume)
- Uses 0.25s inter-call delay (4 calls/symbol = 1 call/s average)
- Checkpoints after every symbol: safe to interrupt and restart
- Estimated time for full universe: ~40–50 min uninterrupted

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/fmp_bulk_fetch_universe.py
    PYTHONPATH=. .venv/bin/python3 scripts/fmp_bulk_fetch_universe.py --queue-only
    PYTHONPATH=. .venv/bin/python3 scripts/fmp_bulk_fetch_universe.py --limit 200
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.scoring.fetch_fmp_signals import (
    fetch_key_metrics_ttm,
    fetch_grades_consensus,
    fetch_earnings_surprises,
    fetch_income_growth,
    _get_api_key,
    _write_csv,
    _load_csv_by_symbol,
    _FMP_LATEST_DIR,
    KEY_METRICS_HEADERS,
    GRADES_CONSENSUS_HEADERS,
    EARNINGS_SURPRISES_HEADERS,
    INCOME_GROWTH_HEADERS,
)
from src.scoring.fmp_universe_enrichment import build_fmp_enriched_universe, coverage_stats

_ETF_LIKE = frozenset({"Unit Trust Fund", "ETF", "FUND", "MUTUAL FUND"})
_DELAY = 0.22   # seconds between calls; 4 calls/symbol → ~0.9s/symbol → ~2,465 symbols in ~37 min

_FETCH_STATUS_PATH = _FMP_LATEST_DIR / "latest_fmp_fetch_status.csv"
_FETCH_STATUS_HEADERS = [
    "symbol",
    "product",
    "status",
    "attempted_at_utc",
    "source_date",
    "failure_type",
    "failure_reason",
]
_PRODUCTS = ("key_metrics", "grades_consensus", "earnings", "income_growth")
_COMPLETE_STATUSES = frozenset({"SUCCESS", "PROVIDER_NO_DATA"})

UNIVERSE_CSV = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
MANIFEST_JSON = _REPO_ROOT / "data" / "portfolio_ingestion" / "manifest.json"


def _load_universe_symbols() -> list[str]:
    """Return all eligible symbols from the analytical universe (no ETFs/funds)."""
    syms: list[str] = []
    if not UNIVERSE_CSV.exists():
        return syms
    with UNIVERSE_CSV.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sec_type = str(row.get("security_type", "")).strip()
            sym = str(row.get("symbol", "")).strip().upper()
            if sym and sec_type not in _ETF_LIKE:
                syms.append(sym)
    return syms


def _load_queue_symbols() -> list[str]:
    """Return deployment queue candidate symbols from the latest completed PAR run."""
    if not MANIFEST_JSON.exists():
        return []
    manifest = json.loads(MANIFEST_JSON.read_text())
    completed = [
        p for p in manifest.get("portfolios", [])
        if p.get("status") == "COMPLETE" and "CONCENTRATED" not in p.get("run_id", "")
    ]
    if not completed:
        return []
    run_id = sorted(completed, key=lambda x: x.get("run_id", ""))[-1]["run_id"]
    dq_path = _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "deployment_queue.json"
    if not dq_path.exists():
        return []
    dq = json.loads(dq_path.read_text())
    return [c["symbol"] for c in dq.get("queue", []) if c.get("symbol")]


def _status_key(symbol: str, product: str) -> tuple[str, str]:
    return symbol.strip().upper(), product.strip().lower()


def _load_fetch_status_rows() -> dict[tuple[str, str], dict[str, str]]:
    if not _FETCH_STATUS_PATH.exists():
        return {}
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with _FETCH_STATUS_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            product = str(row.get("product", "")).strip().lower()
            if sym and product:
                rows[_status_key(sym, product)] = dict(row)
    return rows


def _save_fetch_status_rows(rows: dict[tuple[str, str], dict[str, str]]) -> None:
    _write_csv(_FETCH_STATUS_PATH, list(rows.values()), _FETCH_STATUS_HEADERS)


def _row_fetch_status(row: dict[str, str] | None) -> str:
    if not row:
        return ""
    explicit = str(row.get("fetch_status", "")).strip().upper()
    if explicit:
        return explicit
    # Back-compat for older rows created before fetch_status existed.
    return "SUCCESS"


def _product_status(
    *,
    symbol: str,
    product: str,
    status_rows: dict[tuple[str, str], dict[str, str]],
    product_row: dict[str, str] | None,
) -> str:
    ledger = status_rows.get(_status_key(symbol, product))
    if ledger:
        return str(ledger.get("status", "")).strip().upper()
    return _row_fetch_status(product_row)


def _symbol_completed(
    *,
    symbol: str,
    status_rows: dict[tuple[str, str], dict[str, str]],
    km_rows: dict[str, dict],
    gr_rows: dict[str, dict],
    es_rows: dict[str, dict],
    ig_rows: dict[str, dict],
) -> bool:
    row_map = {
        "key_metrics": km_rows.get(symbol),
        "grades_consensus": gr_rows.get(symbol),
        "earnings": es_rows.get(symbol),
        "income_growth": ig_rows.get(symbol),
    }
    for product in _PRODUCTS:
        status = _product_status(
            symbol=symbol,
            product=product,
            status_rows=status_rows,
            product_row=row_map[product],
        )
        if status not in _COMPLETE_STATUSES:
            return False
    return True


def _set_status_row(
    *,
    status_rows: dict[tuple[str, str], dict[str, str]],
    symbol: str,
    product: str,
    source_date: str,
    status: str,
    failure_type: str,
    failure_reason: str,
) -> None:
    status_rows[_status_key(symbol, product)] = {
        "symbol": symbol,
        "product": product,
        "status": status,
        "attempted_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_date": source_date,
        "failure_type": failure_type,
        "failure_reason": failure_reason,
    }


def fetch_and_checkpoint(
    symbols: list[str],
    api_key: str,
    today: str,
    km_rows: dict,
    gr_rows: dict,
    es_rows: dict,
    ig_rows: dict,
    status_rows: dict[tuple[str, str], dict[str, str]],
    verbose: bool = True,
) -> tuple[int, int]:
    """Fetch all 4 datasets for each symbol, checkpointing after every symbol.

    Returns (fetched_count, skipped_count).
    """
    fetched = 0

    for i, sym in enumerate(symbols, start=1):
        sym = sym.upper()
        if verbose:
            print(f"[{i}/{len(symbols)}] {sym}...", end=" ", flush=True)

        km_current = _product_status(
            symbol=sym,
            product="key_metrics",
            status_rows=status_rows,
            product_row=km_rows.get(sym),
        )
        if km_current not in _COMPLETE_STATUSES:
            km = fetch_key_metrics_ttm(sym, api_key, today)
            km["sourced_date"] = today
            km_rows[sym] = km
            _set_status_row(
                status_rows=status_rows,
                symbol=sym,
                product="key_metrics",
                source_date=today,
                status=str(km.get("fetch_status", "")).strip().upper() or "FETCH_FAILED",
                failure_type=str(km.get("failure_type", "")),
                failure_reason=str(km.get("failure_reason", "")),
            )
            time.sleep(_DELAY)

        gr_current = _product_status(
            symbol=sym,
            product="grades_consensus",
            status_rows=status_rows,
            product_row=gr_rows.get(sym),
        )
        if gr_current not in _COMPLETE_STATUSES:
            gr = fetch_grades_consensus(sym, api_key, today)
            gr["sourced_date"] = today
            gr_rows[sym] = gr
            _set_status_row(
                status_rows=status_rows,
                symbol=sym,
                product="grades_consensus",
                source_date=today,
                status=str(gr.get("fetch_status", "")).strip().upper() or "FETCH_FAILED",
                failure_type=str(gr.get("failure_type", "")),
                failure_reason=str(gr.get("failure_reason", "")),
            )
            time.sleep(_DELAY)

        es_current = _product_status(
            symbol=sym,
            product="earnings",
            status_rows=status_rows,
            product_row=es_rows.get(sym),
        )
        if es_current not in _COMPLETE_STATUSES:
            es = fetch_earnings_surprises(sym, api_key, today)
            es["sourced_date"] = today
            es_rows[sym] = es
            _set_status_row(
                status_rows=status_rows,
                symbol=sym,
                product="earnings",
                source_date=today,
                status=str(es.get("fetch_status", "")).strip().upper() or "FETCH_FAILED",
                failure_type=str(es.get("failure_type", "")),
                failure_reason=str(es.get("failure_reason", "")),
            )
            time.sleep(_DELAY)

        ig_current = _product_status(
            symbol=sym,
            product="income_growth",
            status_rows=status_rows,
            product_row=ig_rows.get(sym),
        )
        if ig_current not in _COMPLETE_STATUSES:
            ig = fetch_income_growth(sym, api_key, today)
            ig["sourced_date"] = today
            ig_rows[sym] = ig
            _set_status_row(
                status_rows=status_rows,
                symbol=sym,
                product="income_growth",
                source_date=today,
                status=str(ig.get("fetch_status", "")).strip().upper() or "FETCH_FAILED",
                failure_type=str(ig.get("failure_type", "")),
                failure_reason=str(ig.get("failure_reason", "")),
            )
            time.sleep(_DELAY)

        # Checkpoint: write all 4 latest files after every symbol
        _FMP_LATEST_DIR.mkdir(parents=True, exist_ok=True)
        _write_csv(_FMP_LATEST_DIR / "latest_fmp_key_metrics.csv",        list(km_rows.values()), KEY_METRICS_HEADERS)
        _write_csv(_FMP_LATEST_DIR / "latest_fmp_grades_consensus.csv",   list(gr_rows.values()), GRADES_CONSENSUS_HEADERS)
        _write_csv(_FMP_LATEST_DIR / "latest_fmp_earnings_surprises.csv", list(es_rows.values()), EARNINGS_SURPRISES_HEADERS)
        _write_csv(_FMP_LATEST_DIR / "latest_fmp_income_growth.csv",      list(ig_rows.values()), INCOME_GROWTH_HEADERS)
        _save_fetch_status_rows(status_rows)

        if verbose:
            km = km_rows.get(sym, {})
            gr = gr_rows.get(sym, {})
            es = es_rows.get(sym, {})
            ev  = km.get("ev_ebitda_ttm", "")
            roe = km.get("roe_ttm", "")
            br  = es.get("beat_rate_8q", "")
            cons = gr.get("consensus_label", "")
            print(f"ev={ev[:6] if ev else '—'}  roe={roe[:5] if roe else '—'}  beat={br or '—'}  cons={cons or '—'}")

        fetched += 1

    return fetched, 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch FMP data for the full analytical universe.")
    parser.add_argument("--queue-only", action="store_true", help="Only fetch deployment queue symbols")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of symbols to fetch")
    parser.add_argument("--force-refresh", action="store_true", help="Re-fetch even cached symbols")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-symbol output")
    args = parser.parse_args()

    api_key = _get_api_key()
    today = date.today().isoformat()
    verbose = not args.quiet

    # Load existing cache (all 4 datasets)
    km_rows  = {r["symbol"]: r for r in _load_csv_by_symbol(_FMP_LATEST_DIR / "latest_fmp_key_metrics.csv").values()}
    gr_rows  = {r["symbol"]: r for r in _load_csv_by_symbol(_FMP_LATEST_DIR / "latest_fmp_grades_consensus.csv").values()}
    es_rows  = {r["symbol"]: r for r in _load_csv_by_symbol(_FMP_LATEST_DIR / "latest_fmp_earnings_surprises.csv").values()}
    ig_rows  = {r["symbol"]: r for r in _load_csv_by_symbol(_FMP_LATEST_DIR / "latest_fmp_income_growth.csv").values()}
    status_rows = _load_fetch_status_rows()

    already = set()
    if not args.force_refresh:
        symbols = set(km_rows) | set(gr_rows) | set(es_rows) | set(ig_rows)
        already = {
            sym for sym in symbols
            if _symbol_completed(
                symbol=sym,
                status_rows=status_rows,
                km_rows=km_rows,
                gr_rows=gr_rows,
                es_rows=es_rows,
                ig_rows=ig_rows,
            )
        }

    # Build prioritized symbol list
    queue_syms  = _load_queue_symbols()
    all_syms    = _load_universe_symbols()

    if args.queue_only:
        priority_list = queue_syms
    else:
        # Priority 1: deployment queue, then rest of universe alphabetically
        queue_set = set(queue_syms)
        priority_list = queue_syms + [s for s in all_syms if s not in queue_set]

    # Remove already-cached
    pending = [s for s in priority_list if s not in already]

    if args.limit:
        pending = pending[:args.limit]

    print(f"FMP Universe Bulk Fetch — {today}")
    print(f"  Universe eligible symbols:  {len(all_syms)}")
    print(f"  Deployment queue symbols:   {len(queue_syms)}")
    print(f"  Already cached:             {len(already)}")
    print(f"  To fetch:                   {len(pending)}")
    est_min = len(pending) * 4 * _DELAY / 60
    print(f"  Estimated time:             {est_min:.0f}–{est_min*1.3:.0f} min")
    print()

    if not pending:
        print("Nothing to fetch — all symbols already cached.")
    else:
        fetched, _ = fetch_and_checkpoint(
            pending, api_key, today,
            km_rows, gr_rows, es_rows, ig_rows,
            status_rows,
            verbose=verbose,
        )
        print(f"\nFetch complete: {fetched} symbols processed.")

    # Rebuild enriched universe
    print("\nRebuilding enriched universe...")
    records = build_fmp_enriched_universe()
    stats = coverage_stats(records)

    print(f"\nCoverage summary ({stats['total']} total symbols):")
    for status, count in stats["coverage_counts"].items():
        pct = stats["coverage_pcts"][status]
        print(f"  {status:25}: {count:5}  ({pct:5.1f}%)")

    print(f"\nNull rates (top fields, among {stats['eligible_count']} FULL/PARTIAL):")
    top_nulls = sorted(stats["null_rates_pct"].items(), key=lambda x: -x[1])[:8]
    for field, rate in top_nulls:
        if rate > 0:
            print(f"  {field:35}: {rate:5.1f}%")


if __name__ == "__main__":
    main()
