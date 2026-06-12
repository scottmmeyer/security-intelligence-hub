#!/usr/bin/env python3
"""Daily signal freshness check and auto-fetch for Zacks, Danelfin, and Yahoo.

Checks whether each signal cache (latest_zacks.csv, latest_danelfin.csv,
latest_yahoo_supplemental.csv) was fetched today.  Any stale cache triggers a
fresh fetch against the current base equity universe.

Usage (standalone):
    PYTHONPATH=. .venv/bin/python scripts/refresh_signals.py
    PYTHONPATH=. .venv/bin/python scripts/refresh_signals.py --dry-run
    PYTHONPATH=. .venv/bin/python scripts/refresh_signals.py --providers zacks danelfin

Called programmatically (e.g. from foundation_service.py):
    from scripts.refresh_signals import ensure_signals_fresh
    ensure_signals_fresh()
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.scoring.fetch_zacks_scores import (
    build_smart_refresh_list,
    fetch_zacks_scores_for_symbols,
)
from src.scoring.fetch_danelfin_scores import fetch_danelfin_scores_for_symbols
from src.scoring.fetch_yahoo_supplemental import fetch_yahoo_supplemental_for_symbols
from src.scoring.fetch_fmp_signals import (
    _get_api_key as _fmp_api_key,
    is_fmp_daily_stale,
    is_fmp_quarterly_stale,
    fetch_fmp_daily_signals,
    fetch_fmp_quarterly_signals,
    get_fmp_freshness_report,
)

_ZACKS_DIR = _REPO_ROOT / "data" / "signals" / "zacks"
_DANELFIN_DIR = _REPO_ROOT / "data" / "signals" / "danelfin"
_YAHOO_DIR = _REPO_ROOT / "data" / "signals" / "yahoo"
_FMP_DIR = _REPO_ROOT / "data" / "signals" / "fmp"
_BASE_UNIVERSE = _REPO_ROOT / "data" / "current" / "base_equity_universe.csv"
_PAR_ROOT = _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs"

_ALL_PROVIDERS = ("zacks", "danelfin", "yahoo", "fmp")


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------

def _latest_sourced_date(latest_csv: Path) -> str | None:
    """Return the first ``sourced_date`` value found in *latest_csv*, or None."""
    if not latest_csv.exists():
        return None
    with latest_csv.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            val = str(row.get("sourced_date", "")).strip()
            if val:
                return val
    return None


def _is_stale(latest_csv: Path) -> bool:
    """Return True when *latest_csv* is missing or its sourced_date ≠ today."""
    today = date.today().isoformat()
    return _latest_sourced_date(latest_csv) != today


# ---------------------------------------------------------------------------
# Symbol list helpers
# ---------------------------------------------------------------------------

_BULLISH_ESS_TEXTS = frozenset({"BULLISH", "VERY_BULLISH"})

# Raw ESS score threshold for including NEUTRAL-labelled stocks in smart refresh.
# A stock with text=NEUTRAL but raw_score >= this threshold is near the Bullish
# boundary (7.1) and warrants fresh provider scores. The official boundary is 7.1;
# we use 6.5 to catch stocks that may cross over before the next export.
_NEAR_BULLISH_RAW_SCORE_THRESHOLD = 6.5


def _all_universe_symbols(universe_csv: Path = _BASE_UNIVERSE) -> list[str]:
    """Return every unique symbol from *universe_csv*, in encounter order."""
    if not universe_csv.exists():
        return []
    symbols: list[str] = []
    seen: set[str] = set()
    with universe_csv.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym and sym not in seen:
                seen.add(sym)
                symbols.append(sym)
    return symbols


def _smart_universe_symbols(universe_csv: Path = _BASE_UNIVERSE) -> list[str]:
    """Return only BULLISH/VERY_BULLISH symbols — the high-priority smart-refresh set.

    Also includes NEUTRAL symbols whose raw ESS score (0.1–10.0) is at or above
    _NEAR_BULLISH_RAW_SCORE_THRESHOLD (6.5), since such stocks sit close to the
    7.1 Bullish boundary and their provider scores may not reflect the latest data.
    """
    if not universe_csv.exists():
        return []
    symbols: list[str] = []
    seen: set[str] = set()
    with universe_csv.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            ess = str(row.get("starmine_ess_text", "")).strip().upper()
            if not sym or sym in seen:
                continue
            if ess in _BULLISH_ESS_TEXTS:
                seen.add(sym)
                symbols.append(sym)
                continue
            # Include near-bullish neutrals when raw score is available
            raw_score_str = str(row.get("starmine_ess_raw_score", "")).strip()
            if ess == "NEUTRAL" and raw_score_str:
                try:
                    if float(raw_score_str) >= _NEAR_BULLISH_RAW_SCORE_THRESHOLD:
                        seen.add(sym)
                        symbols.append(sym)
                except ValueError:
                    pass
    return symbols


def _load_portfolio_equity_holdings() -> set[str]:
    """Return equity holding symbols from the most recent date-stamped PAR run.

    Loads the latest PAR-YYYYMMDD-* holdings.csv and returns the set of symbols
    whose ``asset_class`` is ``EQUITIES``.  These are passed to
    ``build_smart_refresh_list()`` as ``forced_symbols`` to guarantee that all
    currently held equity positions receive a Zacks refresh regardless of ESS
    category or cache status.
    """
    if not _PAR_ROOT.exists():
        return set()
    date_pars = sorted(
        [d for d in _PAR_ROOT.iterdir() if d.name.startswith("PAR-2")],
        key=lambda p: p.name,
        reverse=True,
    )
    if not date_pars:
        return set()
    holdings_path = date_pars[0] / "holdings.csv"
    if not holdings_path.exists():
        return set()
    syms: set[str] = set()
    with holdings_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = (row.get("symbol") or "").strip().upper()
            asset = (row.get("asset_class") or "").strip().upper()
            if sym and asset == "EQUITIES":
                syms.add(sym)
    return syms


# ---------------------------------------------------------------------------
# Per-provider refresh
# ---------------------------------------------------------------------------

def _refresh_zacks(*, dry_run: bool, verbose: bool, smart: bool = False) -> bool:
    """Fetch fresh Zacks scores.  Returns True when a fetch was triggered."""
    latest = _ZACKS_DIR / "latest_zacks.csv"
    if not _is_stale(latest):
        if verbose:
            print(f"[refresh_signals] Zacks: up-to-date ({_latest_sourced_date(latest)}), skipping.")
        return False

    # Zacks always uses smart-refresh (bullish first + uncached); full universe is never needed.
    # Portfolio equity holdings are force-included regardless of ESS/cache status to guarantee
    # all held positions receive a daily Zacks update (ZACKS-REFRESH-UNIVERSE-01 fix).
    forced = _load_portfolio_equity_holdings()
    symbols = build_smart_refresh_list(
        universe_csv=_BASE_UNIVERSE,
        zacks_cache_csv=latest,
        forced_symbols=forced or None,
    )
    if not symbols:
        if verbose:
            print("[refresh_signals] Zacks: stale but no symbols found in universe, skipping.")
        return False

    if verbose:
        if forced:
            print(f"[refresh_signals] Zacks: stale — fetching {len(symbols)} symbols "
                  f"({len(forced)} forced portfolio holdings + smart refresh).")
        else:
            print(f"[refresh_signals] Zacks: stale — fetching {len(symbols)} symbols.")
    if not dry_run:
        fetch_zacks_scores_for_symbols(symbols, output_dir=_ZACKS_DIR, verbose=verbose)
    return True


def _refresh_danelfin(*, dry_run: bool, verbose: bool, smart: bool = False) -> bool:
    """Fetch fresh Danelfin scores.  Returns True when a fetch was triggered."""
    latest = _DANELFIN_DIR / "latest_danelfin.csv"
    if not _is_stale(latest):
        if verbose:
            print(f"[refresh_signals] Danelfin: up-to-date ({_latest_sourced_date(latest)}), skipping.")
        return False

    symbols = _smart_universe_symbols() if smart else _all_universe_symbols()
    if not symbols:
        if verbose:
            print("[refresh_signals] Danelfin: stale but no symbols found in universe, skipping.")
        return False

    mode_label = "smart (bullish only)" if smart else "full universe"
    if verbose:
        print(f"[refresh_signals] Danelfin: stale — fetching {len(symbols)} symbols ({mode_label}).")
    if not dry_run:
        fetch_danelfin_scores_for_symbols(symbols, output_dir=_DANELFIN_DIR, verbose=verbose)
    return True


def _refresh_yahoo(*, dry_run: bool, verbose: bool, smart: bool = False) -> bool:
    """Fetch fresh Yahoo supplemental signals.  Returns True when a fetch was triggered."""
    latest = _YAHOO_DIR / "latest_yahoo_supplemental.csv"
    if not _is_stale(latest):
        if verbose:
            print(f"[refresh_signals] Yahoo: up-to-date ({_latest_sourced_date(latest)}), skipping.")
        return False

    symbols = _smart_universe_symbols() if smart else _all_universe_symbols()
    if not symbols:
        if verbose:
            print("[refresh_signals] Yahoo: stale but no symbols found in universe, skipping.")
        return False

    mode_label = "smart (bullish only)" if smart else "full universe"
    if verbose:
        print(f"[refresh_signals] Yahoo: stale — fetching {len(symbols)} symbols ({mode_label}).")
    if not dry_run:
        fetch_yahoo_supplemental_for_symbols(symbols, output_dir=_YAHOO_DIR, verbose=verbose)
    return True


def _refresh_fmp(*, dry_run: bool, verbose: bool, mode: str = "daily") -> bool:
    """Fetch fresh FMP fundamental signals.  Returns True when a fetch was triggered.

    Args:
        mode: "daily" (key_metrics + grades) or "quarterly" (earnings + income_growth)
              or "all" (both).
    """
    api_key = _fmp_api_key()
    if not api_key:
        if verbose:
            print("[refresh_signals] FMP: no API key found (FMP_API_KEY not set), skipping.")
        return False

    symbols = _all_universe_symbols()
    if not symbols:
        if verbose:
            print("[refresh_signals] FMP: stale but no symbols found in universe, skipping.")
        return False

    triggered = False

    # Daily datasets
    if mode in ("daily", "all"):
        daily_stale = is_fmp_daily_stale("key_metrics", _FMP_DIR / "latest") or \
                      is_fmp_daily_stale("grades_consensus", _FMP_DIR / "latest")
        if daily_stale:
            if verbose:
                print(f"[refresh_signals] FMP (daily): stale — fetching {len(symbols)} symbols.")
            if not dry_run:
                try:
                    fetch_fmp_daily_signals(symbols, api_key=api_key, output_dir=_FMP_DIR,
                                            verbose=verbose)
                    triggered = True
                except RuntimeError as exc:
                    print(f"[refresh_signals] FMP (daily): FAILED — {exc}")
                    # Fail-open: log but don't crash the full refresh
        else:
            freshness = get_fmp_freshness_report(_FMP_DIR)
            km_date = freshness.get("key_metrics", "MISSING")
            if verbose:
                print(f"[refresh_signals] FMP (daily): up-to-date ({km_date}), skipping.")

    # Quarterly datasets
    if mode in ("quarterly", "all"):
        quarterly_stale = is_fmp_quarterly_stale("earnings", _FMP_DIR / "latest") or \
                          is_fmp_quarterly_stale("income_growth", _FMP_DIR / "latest")
        if quarterly_stale:
            if verbose:
                print(f"[refresh_signals] FMP (quarterly): stale — fetching {len(symbols)} symbols.")
            if not dry_run:
                try:
                    fetch_fmp_quarterly_signals(symbols, api_key=api_key, output_dir=_FMP_DIR,
                                                verbose=verbose)
                    triggered = True
                except RuntimeError as exc:
                    print(f"[refresh_signals] FMP (quarterly): FAILED — {exc}")
        else:
            freshness = get_fmp_freshness_report(_FMP_DIR)
            es_date = freshness.get("earnings", "MISSING")
            if verbose:
                print(f"[refresh_signals] FMP (quarterly): up-to-date ({es_date}), skipping.")

    return triggered


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_signals_fresh(
    providers: Sequence[str] = _ALL_PROVIDERS,
    *,
    dry_run: bool = False,
    verbose: bool = True,
    smart: bool = False,
) -> dict[str, bool]:
    """Check freshness and fetch stale signal caches.

    Parameters
    ----------
    providers:
        Subset of ("zacks", "danelfin", "yahoo") to check.  Defaults to all.
    dry_run:
        When True, report staleness without making any API calls.
    verbose:
        When True, print one-line status per provider.
    smart:
        When True, Danelfin and Yahoo fetch only BULLISH/VERY_BULLISH symbols
        (~300) instead of the full universe (~2800).  Zacks always uses its own
        smart-refresh logic regardless of this flag.

    Returns
    -------
    dict mapping provider name → True if a refresh was triggered (or would be
    triggered in dry-run mode), False if already up-to-date.
    """
    triggered: dict[str, bool] = {}
    provider_set = {p.lower() for p in providers}

    if "zacks" in provider_set:
        triggered["zacks"] = _refresh_zacks(dry_run=dry_run, verbose=verbose, smart=smart)
    if "yahoo" in provider_set:
        triggered["yahoo"] = _refresh_yahoo(dry_run=dry_run, verbose=verbose, smart=smart)
    if "danelfin" in provider_set:
        triggered["danelfin"] = _refresh_danelfin(dry_run=dry_run, verbose=verbose, smart=smart)
    if "fmp" in provider_set:
        triggered["fmp"] = _refresh_fmp(dry_run=dry_run, verbose=verbose, mode="daily")

    return triggered


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check and refresh stale signal caches (Zacks, Danelfin, Yahoo)."
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=list(_ALL_PROVIDERS),
        default=list(_ALL_PROVIDERS),
        help="Which providers to check (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report staleness without making API calls.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-provider status messages.",
    )
    parser.add_argument(
        "--smart",
        action="store_true",
        help="Fetch only BULLISH/VERY_BULLISH symbols for Danelfin and Yahoo (~300 vs ~2800).",
    )
    parser.add_argument(
        "--fmp-mode",
        choices=["daily", "quarterly", "all"],
        default="daily",
        help="FMP refresh mode: daily (key_metrics+grades) or quarterly (earnings+growth) or all.",
    )
    args = parser.parse_args()

    results = ensure_signals_fresh(
        providers=args.providers,
        dry_run=args.dry_run,
        verbose=not args.quiet,
        smart=args.smart,
    )

    triggered = [p for p, v in results.items() if v]
    if triggered:
        status = "would fetch" if args.dry_run else "refreshed"
        print(f"\n[refresh_signals] {status}: {', '.join(triggered)}")
    else:
        print("\n[refresh_signals] All signal caches are current.")
