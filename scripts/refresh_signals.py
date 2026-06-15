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
import json
import sys
import time
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
from src.portfolio.holdings_coverage import (
    load_active_holding_symbols,
    load_provider_applicable_symbols,
    summarize_holdings_coverage,
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
    """Return True when *latest_csv* is missing or its newest sourced_date is more than 2 days old.

    A 2-day tolerance accommodates weekend and overnight gaps: data sourced on
    a Friday or Saturday is still considered research-fresh on Sunday or Monday,
    allowing the refresh engine to focus on coverage-repair mode rather than
    triggering a full research-refresh for the entire universe.
    """
    latest_str = _latest_sourced_date(latest_csv)
    if not latest_str:
        return True
    try:
        days_old = (date.today() - date.fromisoformat(latest_str)).days
        return days_old > 2
    except ValueError:
        return True


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
    """Return equity holding symbols from the canonical active holdings baseline."""
    return load_active_holding_symbols(_PAR_ROOT)


def _load_portfolio_provider_holdings(provider: str) -> set[str]:
    """Return provider-applicable holdings from the canonical active baseline."""
    return load_provider_applicable_symbols(_PAR_ROOT, _BASE_UNIVERSE, provider=provider)


def _holdings_coverage(provider: str, latest_csv: Path) -> dict[str, object]:
    return summarize_holdings_coverage(
        provider=provider,
        latest_csv=latest_csv,
        analysis_runs_root=_PAR_ROOT,
        base_universe_csv=_BASE_UNIVERSE,
        threshold_days=2,
    )


def _coverage_refresh_targets(coverage: dict[str, object]) -> list[str]:
    symbols = coverage.get("symbols") or {}
    if not isinstance(symbols, dict):
        return []
    targets: list[str] = []
    for symbol, info in symbols.items():
        if not isinstance(info, dict):
            continue
        if not info.get("applicable"):
            continue
        if info.get("classification") in {"STALE", "MISSING", "FAILED"}:
            targets.append(str(symbol).strip().upper())
    return sorted({s for s in targets if s})


def _provider_state(*, research_fresh: bool, holdings_status: str) -> str:
    freshness_state = "RESEARCH_FRESH" if research_fresh else "RESEARCH_STALE"
    return f"{freshness_state}_{holdings_status or 'UNKNOWN'}"


def _coverage_snapshot(coverage: dict[str, object]) -> dict[str, object]:
    return {
        "run_id": coverage.get("run_id"),
        "active_holdings_baseline": int(coverage.get("active_holdings_baseline") or 0),
        "applicable_holdings": int(coverage.get("applicable_holdings") or 0),
        "covered_today": int(coverage.get("covered_today") or 0),
        "covered_within_threshold": int(coverage.get("covered_within_threshold") or 0),
        "stale": int(coverage.get("stale") or 0),
        "missing": int(coverage.get("missing") or 0),
        "failed": int(coverage.get("failed") or 0),
        "not_applicable": int(coverage.get("not_applicable") or 0),
        "status": str(coverage.get("status") or "UNKNOWN"),
    }


def _compute_provider_metrics(
    *,
    provider: str,
    mode: str,
    submitted_symbols: list[str],
    coverage_before: dict[str, object],
    coverage_after: dict[str, object],
    runtime_sec: float,
    fetch_stats: dict[str, int] | None = None,
) -> dict[str, object]:
    symbols_after = coverage_after.get("symbols") or {}
    refreshed = 0
    for symbol in submitted_symbols:
        info = symbols_after.get(symbol)
        if isinstance(info, dict) and info.get("classification") == "COVERED_TODAY":
            refreshed += 1
    submitted = len(submitted_symbols)
    failed = max(submitted - refreshed, 0)
    applicable_before = int(coverage_before.get("applicable_holdings") or 0)
    skipped = max(applicable_before - submitted, 0)
    skipped_already_covered = int((fetch_stats or {}).get("skipped_already_covered", 0))
    retried_failed_checkpoint = int((fetch_stats or {}).get("retried_failed_checkpoint", 0))
    return {
        "provider": provider,
        "mode": mode,
        "submitted": submitted,
        "skipped_already_covered": skipped_already_covered,
        "retried_failed_checkpoint": retried_failed_checkpoint,
        "refreshed": refreshed,
        "skipped": skipped,
        "failed": failed,
        "coverage_before": _coverage_snapshot(coverage_before),
        "coverage_after": _coverage_snapshot(coverage_after),
        "runtime_sec": round(runtime_sec, 4),
    }


def _merge_forced_symbols(
    base_symbols: Sequence[str],
    forced_symbols: set[str] | None = None,
) -> list[str]:
    """Return a deduplicated list with forced symbols prepended.

    This preserves smart-refresh efficiency for non-held symbols while ensuring
    current equity holdings are always refreshed regardless of ESS posture.
    """
    merged: list[str] = []
    seen: set[str] = set()

    if forced_symbols:
        for sym in sorted(forced_symbols):
            norm = str(sym).strip().upper()
            if norm and norm not in seen:
                merged.append(norm)
                seen.add(norm)

    for sym in base_symbols:
        norm = str(sym).strip().upper()
        if norm and norm not in seen:
            merged.append(norm)
            seen.add(norm)

    return merged


# ---------------------------------------------------------------------------
# Per-provider refresh
# ---------------------------------------------------------------------------

def _refresh_zacks(
    *,
    dry_run: bool,
    verbose: bool,
    smart: bool = False,
    collect_report: bool = False,
) -> bool | tuple[bool, dict[str, object]]:
    """Fetch fresh Zacks scores.  Returns True when a fetch was triggered."""
    latest = _ZACKS_DIR / "latest_zacks.csv"
    t0 = time.perf_counter()
    coverage_before = _holdings_coverage("zacks", latest)
    repair_targets = _coverage_refresh_targets(coverage_before)
    research_stale = _is_stale(latest)
    if not research_stale and not repair_targets:
        if verbose:
            print(f"[refresh_signals] Zacks: up-to-date ({_latest_sourced_date(latest)}) and holdings compliant, skipping.")
        if collect_report:
            cov_after = _holdings_coverage("zacks", latest)
            metrics = _compute_provider_metrics(
                provider="zacks",
                mode="skip_compliant",
                submitted_symbols=[],
                coverage_before=coverage_before,
                coverage_after=cov_after,
                runtime_sec=time.perf_counter() - t0,
            )
            metrics["state"] = _provider_state(
                research_fresh=not research_stale,
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    active_holdings = _load_portfolio_equity_holdings()
    forced = _load_portfolio_provider_holdings("zacks")
    mode = "research_refresh"
    if research_stale:
        symbols = build_smart_refresh_list(
            universe_csv=_BASE_UNIVERSE,
            zacks_cache_csv=latest,
            forced_symbols=forced or None,
        )
    else:
        mode = "coverage_repair"
        symbols = repair_targets
    if not symbols:
        if verbose:
            print("[refresh_signals] Zacks: no repair targets after eligibility evaluation, skipping.")
        if collect_report:
            cov_after = _holdings_coverage("zacks", latest)
            metrics = _compute_provider_metrics(
                provider="zacks",
                mode="skip_no_targets",
                submitted_symbols=[],
                coverage_before=coverage_before,
                coverage_after=cov_after,
                runtime_sec=time.perf_counter() - t0,
            )
            metrics["state"] = _provider_state(
                research_fresh=not research_stale,
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    if verbose:
        if mode == "coverage_repair":
            print(
                f"[refresh_signals] Zacks: research fresh but holdings {coverage_before.get('status')} "
                f"— refreshing {len(symbols)} stale/missing applicable holdings."
            )
        elif forced:
            print(f"[refresh_signals] Zacks: stale — fetching {len(symbols)} symbols "
                  f"({len(forced)}/{len(active_holdings)} provider-applicable active holdings + smart refresh).")
        else:
            print(f"[refresh_signals] Zacks: stale — fetching {len(symbols)} symbols.")
    if not dry_run:
        fetch_result = fetch_zacks_scores_for_symbols(
            symbols,
            output_dir=_ZACKS_DIR,
            verbose=verbose,
            force_retry_symbols=set(symbols) if mode == "coverage_repair" else None,
            collect_stats=True,
        )
        fetch_stats = fetch_result[1] if isinstance(fetch_result, tuple) else None
    else:
        fetch_stats = None
    if collect_report:
        cov_after = _holdings_coverage("zacks", latest)
        metrics = _compute_provider_metrics(
            provider="zacks",
            mode=mode,
            submitted_symbols=symbols,
            coverage_before=coverage_before,
            coverage_after=cov_after,
            runtime_sec=time.perf_counter() - t0,
            fetch_stats=fetch_stats,
        )
        metrics["state"] = _provider_state(
            research_fresh=not research_stale,
            holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
        )
        return True, metrics
    return True


def _refresh_danelfin(
    *,
    dry_run: bool,
    verbose: bool,
    smart: bool = False,
    forced_symbols: set[str] | None = None,
    collect_report: bool = False,
) -> bool | tuple[bool, dict[str, object]]:
    """Fetch fresh Danelfin scores.  Returns True when a fetch was triggered."""
    latest = _DANELFIN_DIR / "latest_danelfin.csv"
    t0 = time.perf_counter()
    coverage_before = _holdings_coverage("danelfin", latest)
    repair_targets = _coverage_refresh_targets(coverage_before)
    research_stale = _is_stale(latest)
    if not research_stale and not repair_targets:
        if verbose:
            print(f"[refresh_signals] Danelfin: up-to-date ({_latest_sourced_date(latest)}) and holdings compliant, skipping.")
        if collect_report:
            cov_after = _holdings_coverage("danelfin", latest)
            metrics = _compute_provider_metrics(
                provider="danelfin",
                mode="skip_compliant",
                submitted_symbols=[],
                coverage_before=coverage_before,
                coverage_after=cov_after,
                runtime_sec=time.perf_counter() - t0,
            )
            metrics["state"] = _provider_state(
                research_fresh=not research_stale,
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    active_holdings = _load_portfolio_equity_holdings()
    forced = forced_symbols if forced_symbols is not None else _load_portfolio_provider_holdings("danelfin")
    mode = "research_refresh"
    if research_stale:
        base_symbols = _smart_universe_symbols(_BASE_UNIVERSE) if smart else _all_universe_symbols(_BASE_UNIVERSE)
        symbols = _merge_forced_symbols(base_symbols, forced if smart else None)
    else:
        mode = "coverage_repair"
        symbols = repair_targets
    if not symbols:
        if verbose:
            print("[refresh_signals] Danelfin: no repair targets after eligibility evaluation, skipping.")
        if collect_report:
            cov_after = _holdings_coverage("danelfin", latest)
            metrics = _compute_provider_metrics(
                provider="danelfin",
                mode="skip_no_targets",
                submitted_symbols=[],
                coverage_before=coverage_before,
                coverage_after=cov_after,
                runtime_sec=time.perf_counter() - t0,
            )
            metrics["state"] = _provider_state(
                research_fresh=not research_stale,
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    mode_label = "smart (bullish only)" if smart else "full universe"
    if verbose:
        if mode == "coverage_repair":
            print(
                f"[refresh_signals] Danelfin: research fresh but holdings {coverage_before.get('status')} "
                f"— refreshing {len(symbols)} stale/missing applicable holdings."
            )
        elif smart and forced:
            print(
                f"[refresh_signals] Danelfin: stale — fetching {len(symbols)} symbols "
                f"({len(forced)}/{len(active_holdings)} provider-applicable active holdings + {mode_label})."
            )
        else:
            print(f"[refresh_signals] Danelfin: stale — fetching {len(symbols)} symbols ({mode_label}).")
    if not dry_run:
        fetch_result = fetch_danelfin_scores_for_symbols(
            symbols,
            output_dir=_DANELFIN_DIR,
            verbose=verbose,
            force_retry_symbols=set(symbols) if mode == "coverage_repair" else None,
            collect_stats=True,
        )
        fetch_stats = fetch_result[1] if isinstance(fetch_result, tuple) else None
    else:
        fetch_stats = None
    if collect_report:
        cov_after = _holdings_coverage("danelfin", latest)
        metrics = _compute_provider_metrics(
            provider="danelfin",
            mode=mode,
            submitted_symbols=symbols,
            coverage_before=coverage_before,
            coverage_after=cov_after,
            runtime_sec=time.perf_counter() - t0,
            fetch_stats=fetch_stats,
        )
        metrics["state"] = _provider_state(
            research_fresh=not research_stale,
            holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
        )
        return True, metrics
    return True


def _refresh_yahoo(
    *,
    dry_run: bool,
    verbose: bool,
    smart: bool = False,
    forced_symbols: set[str] | None = None,
    collect_report: bool = False,
) -> bool | tuple[bool, dict[str, object]]:
    """Fetch fresh Yahoo supplemental signals.  Returns True when a fetch was triggered."""
    latest = _YAHOO_DIR / "latest_yahoo_supplemental.csv"
    t0 = time.perf_counter()
    coverage_before = _holdings_coverage("yahoo", latest)
    repair_targets = _coverage_refresh_targets(coverage_before)
    research_stale = _is_stale(latest)
    if not research_stale and not repair_targets:
        if verbose:
            print(f"[refresh_signals] Yahoo: up-to-date ({_latest_sourced_date(latest)}) and holdings compliant, skipping.")
        if collect_report:
            cov_after = _holdings_coverage("yahoo", latest)
            metrics = _compute_provider_metrics(
                provider="yahoo",
                mode="skip_compliant",
                submitted_symbols=[],
                coverage_before=coverage_before,
                coverage_after=cov_after,
                runtime_sec=time.perf_counter() - t0,
            )
            metrics["state"] = _provider_state(
                research_fresh=not research_stale,
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    active_holdings = _load_portfolio_equity_holdings()
    forced = forced_symbols if forced_symbols is not None else _load_portfolio_provider_holdings("yahoo")
    mode = "research_refresh"
    if research_stale:
        base_symbols = _smart_universe_symbols(_BASE_UNIVERSE) if smart else _all_universe_symbols(_BASE_UNIVERSE)
        symbols = _merge_forced_symbols(base_symbols, forced if smart else None)
    else:
        mode = "coverage_repair"
        symbols = repair_targets
    if not symbols:
        if verbose:
            print("[refresh_signals] Yahoo: no repair targets after eligibility evaluation, skipping.")
        if collect_report:
            cov_after = _holdings_coverage("yahoo", latest)
            metrics = _compute_provider_metrics(
                provider="yahoo",
                mode="skip_no_targets",
                submitted_symbols=[],
                coverage_before=coverage_before,
                coverage_after=cov_after,
                runtime_sec=time.perf_counter() - t0,
            )
            metrics["state"] = _provider_state(
                research_fresh=not research_stale,
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    mode_label = "smart (bullish only)" if smart else "full universe"
    if verbose:
        if mode == "coverage_repair":
            print(
                f"[refresh_signals] Yahoo: research fresh but holdings {coverage_before.get('status')} "
                f"— refreshing {len(symbols)} stale/missing applicable holdings."
            )
        elif smart and forced:
            print(
                f"[refresh_signals] Yahoo: stale — fetching {len(symbols)} symbols "
                f"({len(forced)}/{len(active_holdings)} provider-applicable active holdings + {mode_label})."
            )
        else:
            print(f"[refresh_signals] Yahoo: stale — fetching {len(symbols)} symbols ({mode_label}).")
    if not dry_run:
        fetch_result = fetch_yahoo_supplemental_for_symbols(
            symbols,
            output_dir=_YAHOO_DIR,
            verbose=verbose,
            force_retry_symbols=set(symbols) if mode == "coverage_repair" else None,
            collect_stats=True,
        )
        fetch_stats = fetch_result[1] if isinstance(fetch_result, tuple) else None
    else:
        fetch_stats = None
    if collect_report:
        cov_after = _holdings_coverage("yahoo", latest)
        metrics = _compute_provider_metrics(
            provider="yahoo",
            mode=mode,
            submitted_symbols=symbols,
            coverage_before=coverage_before,
            coverage_after=cov_after,
            runtime_sec=time.perf_counter() - t0,
            fetch_stats=fetch_stats,
        )
        metrics["state"] = _provider_state(
            research_fresh=not research_stale,
            holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
        )
        return True, metrics
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
    report = ensure_signals_fresh_with_report(
        providers=providers,
        dry_run=dry_run,
        verbose=verbose,
        smart=smart,
    )
    return {
        str(provider): bool(details.get("triggered"))
        for provider, details in (report.get("providers") or {}).items()
    }


def ensure_signals_fresh_with_report(
    providers: Sequence[str] = _ALL_PROVIDERS,
    *,
    dry_run: bool = False,
    verbose: bool = True,
    smart: bool = False,
) -> dict[str, object]:
    """Check freshness and fetch stale/coverage-degraded providers with report."""
    triggered: dict[str, bool] = {}
    provider_report: dict[str, dict[str, object]] = {}
    t0 = time.perf_counter()
    provider_set = {p.lower() for p in providers}

    if "zacks" in provider_set:
        z = _refresh_zacks(dry_run=dry_run, verbose=verbose, smart=smart, collect_report=True)
        z_triggered, z_metrics = z
        triggered["zacks"] = bool(z_triggered)
        provider_report["zacks"] = {"triggered": bool(z_triggered), **z_metrics}
    if "yahoo" in provider_set:
        y = _refresh_yahoo(dry_run=dry_run, verbose=verbose, smart=smart, collect_report=True)
        y_triggered, y_metrics = y
        triggered["yahoo"] = bool(y_triggered)
        provider_report["yahoo"] = {"triggered": bool(y_triggered), **y_metrics}
    if "danelfin" in provider_set:
        d = _refresh_danelfin(dry_run=dry_run, verbose=verbose, smart=smart, collect_report=True)
        d_triggered, d_metrics = d
        triggered["danelfin"] = bool(d_triggered)
        provider_report["danelfin"] = {"triggered": bool(d_triggered), **d_metrics}
    if "fmp" in provider_set:
        f_t0 = time.perf_counter()
        f_triggered = _refresh_fmp(dry_run=dry_run, verbose=verbose, mode="daily")
        triggered["fmp"] = bool(f_triggered)
        provider_report["fmp"] = {
            "triggered": bool(f_triggered),
            "provider": "fmp",
            "mode": "daily",
            "submitted": 0,
            "skipped_already_covered": 0,
            "retried_failed_checkpoint": 0,
            "refreshed": 0,
            "skipped": 0,
            "failed": 0,
            "runtime_sec": round(time.perf_counter() - f_t0, 4),
        }

    return {
        "triggered": triggered,
        "providers": provider_report,
        "smart": bool(smart),
        "dry_run": bool(dry_run),
        "runtime_sec": round(time.perf_counter() - t0, 4),
    }


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
    parser.add_argument(
        "--report-path",
        default="",
        help="Optional file path to write machine-readable refresh report JSON.",
    )
    args = parser.parse_args()

    report = ensure_signals_fresh_with_report(
        providers=args.providers,
        dry_run=args.dry_run,
        verbose=not args.quiet,
        smart=args.smart,
    )

    results = report.get("triggered") or {}

    triggered = [p for p, v in results.items() if v]
    if triggered:
        status = "would fetch" if args.dry_run else "refreshed"
        print(f"\n[refresh_signals] {status}: {', '.join(triggered)}")
    else:
        print("\n[refresh_signals] All signal caches are current.")

    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
