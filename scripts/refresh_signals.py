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
import shutil
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

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

REFRESH_MODE_STALE_ONLY = "stale_only"
REFRESH_MODE_PORTFOLIO_SIGNALS = "portfolio_signals"
REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES = "holdings_plus_buy_candidates"
REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE = "rebuild_research_universe"
REFRESH_MODE_PREPARE_PORTFOLIO_REVIEW = "prepare_portfolio_review"
REFRESH_MODE_MARKET_REGIME_PROXY_ONLY = "market_regime_proxy_only"

_REFRESH_MODES = {
    REFRESH_MODE_STALE_ONLY,
    REFRESH_MODE_PORTFOLIO_SIGNALS,
    REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES,
    REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE,
    REFRESH_MODE_PREPARE_PORTFOLIO_REVIEW,
    REFRESH_MODE_MARKET_REGIME_PROXY_ONLY,
}

_MARKET_PROXY_BASE = ("SPY", "QQQ", "XLK", "XLF", "XLI", "XLV")
_SEMI_PROXY_CANDIDATES = ("SOXX", "SMH")
_MARKET_PROXY_REQUIRED_SYMBOLS = ("XLK", "XLE", "XLB", "XLI")
_MARKET_PROXY_REPLAY_INDUSTRIES = ("TECHNOLOGY", "ENERGY", "BASIC MATERIALS", "INDUSTRIALS")
_MARKET_PROXY_REPLAY_ARTIFACTS = [
    "data/current/replay_inputs.csv",
    "data/current/replay_performance_series.csv",
]
_MARKET_PROXY_REPLAY_OUTPUT_FILES = (
    "replay_availability.csv",
    "replay_matrix.csv",
    "replay_inputs.csv",
    "replay_performance_series.csv",
    "current_snapshot_metadata.json",
)
_MARKET_PROXY_REQUIRED_OUTPUT_FILES = (
    "replay_inputs.csv",
    "replay_performance_series.csv",
)
_MARKET_PROXY_REPLAY_INPUTS_REQUIRED_COLUMNS = {
    "replay_id",
    "filter_geography",
    "filter_market_cap_bucket",
    "filter_industry",
    "selected_symbols",
}
_MARKET_PROXY_REPLAY_PERF_REQUIRED_COLUMNS = {
    "replay_id",
    "series_type",
    "date",
    "value",
}
_MARKET_PROXY_REQUIRED_MISSING_INPUTS = {
    "TECHNOLOGY benchmark proxy",
    "hard-asset benchmark proxies",
}

_PROVIDER_PRIMARY_FIELDS: dict[str, tuple[str, ...]] = {
    "zacks": ("zacks_rank", "zacks_score"),
    "danelfin": ("danelfin_raw", "danelfin_score"),
    "yahoo": ("price_target", "analyst_count", "current_price"),
}

_PROVIDER_STATUS_FIELDS: tuple[str, ...] = (
    "status",
    "coverage_status",
    "signal_coverage_status",
    "provider_status",
    "fetch_status",
    "error_code",
    "reason",
)


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


def _normalize_refresh_mode(refresh_mode: str | None) -> str:
    mode = str(refresh_mode or REFRESH_MODE_STALE_ONLY).strip().lower()
    return mode if mode in _REFRESH_MODES else REFRESH_MODE_STALE_ONLY


def _refresh_mode_label(refresh_mode: str) -> str:
    return {
        REFRESH_MODE_STALE_ONLY: "stale_only",
        REFRESH_MODE_PORTFOLIO_SIGNALS: "portfolio_signals",
        REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES: "holdings_plus_buy_candidates",
        REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE: "rebuild_research_universe",
        REFRESH_MODE_PREPARE_PORTFOLIO_REVIEW: "prepare_portfolio_review",
        REFRESH_MODE_MARKET_REGIME_PROXY_ONLY: "market_regime_proxy_only",
    }.get(refresh_mode, REFRESH_MODE_STALE_ONLY)


def _symbols_in_latest_cache(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()
    out: set[str] = set()
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol") or "").strip().upper()
                if sym:
                    out.add(sym)
    except Exception:
        return set()
    return out


def _select_semiconductor_proxy() -> str:
    # Prefer whichever semiconductor proxy already has local provider coverage.
    covered = set()
    covered |= _symbols_in_latest_cache(_YAHOO_DIR / "latest_yahoo_supplemental.csv")
    covered |= _symbols_in_latest_cache(_ZACKS_DIR / "latest_zacks.csv")
    covered |= _symbols_in_latest_cache(_DANELFIN_DIR / "latest_danelfin.csv")
    for candidate in _SEMI_PROXY_CANDIDATES:
        if candidate in covered:
            return candidate

    # Fall back to whichever exists in the configured base universe.
    universe = set(_all_universe_symbols(_BASE_UNIVERSE))
    for candidate in _SEMI_PROXY_CANDIDATES:
        if candidate in universe:
            return candidate
    return "SOXX"


def _market_proxy_symbols() -> list[str]:
    semi = _select_semiconductor_proxy()
    merged: list[str] = []
    seen: set[str] = set()
    for sym in [*_MARKET_PROXY_BASE, *_MARKET_PROXY_REQUIRED_SYMBOLS, semi]:
        s = str(sym or "").strip().upper()
        if s and s not in seen:
            seen.add(s)
            merged.append(s)
    return merged


def _market_proxy_refresh_needed(threshold_days: int = 2) -> bool:
    try:
        from src.sih.rotation_risk_monitor import rotation_risk_summary
        from src.portfolio.regime.market_regime_inputs import evaluate_market_proxy_freshness

        summary = rotation_risk_summary(repo_root=_REPO_ROOT)
        proxy_ts = ((summary.get("proxy_returns") or {}).get("latest_proxy_date") if isinstance(summary, dict) else "")
        as_of = str((summary.get("as_of_date") if isinstance(summary, dict) else "") or date.today().isoformat())
        freshness = evaluate_market_proxy_freshness(
            market_proxies_ts=proxy_ts,
            portfolio_snapshot_ts=as_of,
            threshold_days=threshold_days,
        )
        status = str(freshness.get("freshness_status") or "UNKNOWN").upper()
        return status != "FRESH"
    except Exception:
        # Fail closed: if freshness cannot be determined, include proxy refresh targets.
        return True


def _load_buy_candidate_symbols(*, cap: int = 50) -> list[str]:
    """Return ordered buy/deployment candidates from latest completed analysis run."""
    manifest_path = _REPO_ROOT / "data" / "portfolio_ingestion" / "manifest.json"
    if not manifest_path.exists():
        return []

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        portfolios = manifest.get("portfolios") or []
        completed = [p for p in portfolios if isinstance(p, dict) and p.get("status") == "COMPLETE" and p.get("run_id")]
        if not completed:
            return []
        run_id = str(completed[-1].get("run_id") or "").strip()
        if not run_id:
            return []

        from src.portfolio.runner import load_analysis_run

        run = load_analysis_run(run_id)
        if not isinstance(run, dict):
            return []

        ordered: list[str] = []
        seen: set[str] = set()

        def _add(sym: str) -> None:
            s = str(sym or "").strip().upper()
            if s and s not in seen:
                seen.add(s)
                ordered.append(s)

        for row in list((run.get("deployment_queue") or {}).get("queue") or []):
            if isinstance(row, dict):
                _add(str(row.get("symbol") or ""))

        for row in list((run.get("deployment_plan") or {}).get("recommendations") or []):
            if isinstance(row, dict):
                _add(str(row.get("symbol") or ""))

        for row in list(run.get("recommendations") or []):
            if not isinstance(row, dict):
                continue
            action_text = " ".join(
                [
                    str(row.get("action") or ""),
                    str(row.get("recommended_action") or ""),
                    str(row.get("action_type") or ""),
                ]
            ).upper()
            if any(tok in action_text for tok in ("BUY", "ADD", "ACCUMULATE", "DEPLOY", "INITIATE")):
                _add(str(row.get("symbol") or ""))

        if cap > 0:
            return ordered[:cap]
        return ordered
    except Exception:
        return []


def _latest_completed_portfolio_context() -> dict[str, str]:
    manifest_path = _REPO_ROOT / "data" / "portfolio_ingestion" / "manifest.json"
    if not manifest_path.exists():
        return {}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        portfolios = manifest.get("portfolios") or []
        completed = [
            p
            for p in portfolios
            if isinstance(p, dict) and p.get("status") == "COMPLETE" and p.get("run_id")
        ]
        if not completed:
            return {}
        latest = completed[-1]
        run_id = str(latest.get("run_id") or "").strip()
        snapshot_date = str(latest.get("snapshot_date") or latest.get("as_of_date") or "").strip()
        return {
            "run_id": run_id,
            "snapshot_date": snapshot_date,
        }
    except Exception:
        return {}


def _evaluate_market_proxy_replay_freshness(*, threshold_days: int = 2) -> dict[str, Any]:
    status: dict[str, Any] = {
        "freshness_status": "UNKNOWN",
        "latest_proxy_date": None,
        "portfolio_snapshot_date": None,
        "should_publish": True,
        "reason": "market_regime_replay_artifacts_unknown",
        "warnings": [],
    }
    try:
        from src.sih.rotation_risk_monitor import rotation_risk_summary
        from src.portfolio.regime.market_regime_inputs import evaluate_market_proxy_freshness

        summary = rotation_risk_summary(repo_root=_REPO_ROOT)
        proxy_ts = ((summary.get("proxy_returns") or {}).get("latest_proxy_date") if isinstance(summary, dict) else "")
        context = _latest_completed_portfolio_context()
        snapshot_ts = str(
            context.get("snapshot_date")
            or (summary.get("as_of_date") if isinstance(summary, dict) else "")
            or date.today().isoformat()
        )
        freshness = evaluate_market_proxy_freshness(
            market_proxies_ts=proxy_ts,
            portfolio_snapshot_ts=snapshot_ts,
            threshold_days=threshold_days,
        )
        freshness_status = str((freshness or {}).get("freshness_status") or "UNKNOWN").upper()
        status["freshness_status"] = freshness_status
        status["latest_proxy_date"] = str(proxy_ts or "").strip() or None
        status["portfolio_snapshot_date"] = snapshot_ts
        status["should_publish"] = freshness_status != "FRESH"
        status["reason"] = (
            "market_regime_replay_artifacts_fresh"
            if freshness_status == "FRESH"
            else "market_regime_replay_artifacts_stale"
        )
    except Exception as exc:
        status["warnings"].append(f"Unable to evaluate market proxy replay freshness: {exc}")
    return status


def _market_proxy_bridge_run_id(snapshot_date: str) -> str:
    date_token = str(snapshot_date or date.today().isoformat()).replace("-", "")
    time_token = datetime.now(timezone.utc).strftime("%H%M%S")
    return f"MRG-PROXY-BRIDGE-{date_token}-{time_token}"


def _seed_market_proxy_replay_staging_root(staged_repo_root: Path) -> Path:
    staged_current_root = staged_repo_root / "data" / "current"
    source_current_root = _REPO_ROOT / "data" / "current"
    staged_current_root.mkdir(parents=True, exist_ok=True)
    if source_current_root.exists():
        for entry in source_current_root.iterdir():
            if not entry.is_file():
                continue
            shutil.copy2(entry, staged_current_root / entry.name)
    return staged_current_root


def _publish_market_proxy_replay_staging_outputs(staged_repo_root: Path) -> None:
    staged_current_root = staged_repo_root / "data" / "current"
    target_current_root = _REPO_ROOT / "data" / "current"
    target_current_root.mkdir(parents=True, exist_ok=True)
    for name in _MARKET_PROXY_REPLAY_OUTPUT_FILES:
        source = staged_current_root / name
        if source.exists():
            shutil.copy2(source, target_current_root / name)


def _csv_header_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
        return {str(item).strip() for item in header if str(item).strip()}
    except Exception:
        return set()


def _industry_membership_in_replay_inputs(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                industry = str(row.get("filter_industry") or "").strip().upper()
                if industry:
                    out.add(industry)
    except Exception:
        return set()
    return out


def _validate_market_proxy_replay_publish_candidate(
    *,
    staged_current_root: Path,
    industry_results: list[dict[str, Any]],
    latest_proxy_date_after: str | None,
    missing_inputs: list[str],
) -> dict[str, Any]:
    target_industries = sorted(list(_MARKET_PROXY_REPLAY_INDUSTRIES))
    present_industries = {
        str(item.get("industry") or "").strip().upper()
        for item in industry_results
        if str(item.get("industry") or "").strip()
    }
    missing_target_industries = sorted(
        list(set(target_industries).difference(present_industries))
    )
    failed_industries = sorted(
        {
            str(item.get("industry") or "")
            for item in industry_results
            if str(item.get("status") or "").strip().lower() in {"failed", "error"}
            or bool(item.get("error"))
        }
    )
    invalid_status_industries = sorted(
        {
            str(item.get("industry") or "")
            for item in industry_results
            if int(((item.get("status_counts") or {}).get("FAILED") or 0)) > 0
            or int(((item.get("status_counts") or {}).get("ERROR") or 0)) > 0
        }
    )
    blocked_industries = sorted(
        {
            str(item.get("industry") or "")
            for item in industry_results
            if int(((item.get("status_counts") or {}).get("BLOCKED") or 0)) > 0
        }
    )
    zero_row_industries = sorted(
        {
            str(item.get("industry") or "")
            for item in industry_results
            if int(item.get("matrix_row_count") or 0) == 0
        }
    )
    missing_required_cohorts = [
        item for item in missing_inputs if item in _MARKET_PROXY_REQUIRED_MISSING_INPUTS
    ]

    missing_output_files = sorted(
        [
            name
            for name in _MARKET_PROXY_REQUIRED_OUTPUT_FILES
            if not (staged_current_root / name).exists()
        ]
    )

    schema_missing: list[dict[str, Any]] = []
    replay_inputs_headers = _csv_header_set(staged_current_root / "replay_inputs.csv")
    missing_replay_inputs_cols = sorted(
        list(_MARKET_PROXY_REPLAY_INPUTS_REQUIRED_COLUMNS.difference(replay_inputs_headers))
    )
    if missing_replay_inputs_cols:
        schema_missing.append(
            {
                "file": "replay_inputs.csv",
                "missing_columns": missing_replay_inputs_cols,
            }
        )

    replay_perf_headers = _csv_header_set(staged_current_root / "replay_performance_series.csv")
    missing_replay_perf_cols = sorted(
        list(_MARKET_PROXY_REPLAY_PERF_REQUIRED_COLUMNS.difference(replay_perf_headers))
    )
    if missing_replay_perf_cols:
        schema_missing.append(
            {
                "file": "replay_performance_series.csv",
                "missing_columns": missing_replay_perf_cols,
            }
        )

    replay_inputs_industries = _industry_membership_in_replay_inputs(
        staged_current_root / "replay_inputs.csv"
    )
    missing_target_cohorts = sorted(
        list(set(target_industries).difference(replay_inputs_industries))
    )

    warnings: list[str] = []
    reason = ""
    if missing_output_files:
        reason = "required_output_file_missing"
    elif schema_missing:
        reason = "required_schema_missing"
    elif failed_industries or invalid_status_industries:
        reason = "industry_generation_failed"
    elif blocked_industries or zero_row_industries:
        reason = "blocked_or_zero_row_generation"
    elif missing_target_industries or missing_target_cohorts or missing_required_cohorts:
        reason = "required_cohorts_missing_after_generation"
    elif not latest_proxy_date_after:
        reason = "latest_proxy_date_missing_after_generation"

    for name in missing_output_files:
        warnings.append(
            f"Replay bridge did not publish because required staged output file is missing: {name}."
        )
    for item in schema_missing:
        missing_cols = ", ".join([str(col) for col in item.get("missing_columns") or []])
        warnings.append(
            "Replay bridge did not publish because required schema columns are missing from "
            f"{item.get('file')}: {missing_cols}."
        )
    for industry in missing_target_industries:
        warnings.append(
            f"Replay bridge did not publish because target industry result is missing: {industry}."
        )
    for industry in sorted(set(failed_industries) | set(invalid_status_industries)):
        warnings.append(
            f"Replay bridge did not publish because {industry} generation failed or reported error status."
        )

    for industry in zero_row_industries:
        warnings.append(
            f"Replay bridge did not publish because {industry} generation returned zero rows."
        )
    for item in industry_results:
        industry = str(item.get("industry") or "")
        blocked_count = int(((item.get("status_counts") or {}).get("BLOCKED") or 0))
        if blocked_count > 0:
            warnings.append(
                f"Replay bridge did not publish because {industry} replay generation was BLOCKED by immutable partition protection."
            )
    if missing_target_cohorts:
        warnings.append(
            "Replay bridge did not publish because required target industry cohorts are absent "
            f"from replay_inputs.csv: {', '.join(missing_target_cohorts)}."
        )
    if missing_required_cohorts:
        warnings.append(
            "Replay bridge did not publish because required market-regime cohorts are still missing after staged generation."
        )
    if not latest_proxy_date_after:
        warnings.append(
            "Replay bridge did not publish because staged replay artifacts still produced an empty latest_proxy_date."
        )

    return {
        "published": not warnings,
        "reason": reason,
        "warnings": warnings,
        "target_industries": target_industries,
        "blocked_industries": blocked_industries,
        "zero_row_industries": zero_row_industries,
        "failed_industries": sorted(set(failed_industries) | set(invalid_status_industries)),
        "missing_required_cohorts": sorted(
            set(missing_required_cohorts) | set(missing_target_cohorts) | set(missing_target_industries)
        ),
        "missing_output_files": missing_output_files,
        "schema_missing": schema_missing,
    }


def _publish_market_proxy_replay_artifacts(
    *,
    verbose: bool,
    reason: str = "market_regime_replay_artifacts_stale",
    latest_proxy_date_before: str | None = None,
) -> dict[str, Any]:
    status: dict[str, Any] = {
        "attempted": True,
        "status": "warning",
        "reason": reason,
        "published": False,
        "artifacts": list(_MARKET_PROXY_REPLAY_ARTIFACTS),
        "latest_proxy_date_before": latest_proxy_date_before,
        "latest_proxy_date_after": None,
        "latest_proxy_date": None,
        "industries": list(_MARKET_PROXY_REPLAY_INDUSTRIES),
        "warnings": [],
        "details": {
            "industry_results": [],
            "blocked_industries": [],
            "zero_row_industries": [],
            "failed_industries": [],
            "missing_required_cohorts": [],
            "target_industries": list(_MARKET_PROXY_REPLAY_INDUSTRIES),
            "history_side_effects_possible": True,
        },
    }

    context = _latest_completed_portfolio_context()
    run_id = str(context.get("run_id") or "").strip()
    snapshot_date = str(context.get("snapshot_date") or date.today().isoformat()).strip()
    if not run_id:
        status["warnings"].append(
            "Market proxy replay publish could not resolve latest completed portfolio context; Market Regime Guardrail may remain stale."
        )
        status["warnings"].append("Latest completed portfolio run_id was not found.")
        return status

    try:
        end_date = date.fromisoformat(snapshot_date)
    except ValueError:
        end_date = date.today()
        snapshot_date = end_date.isoformat()
    start_date = (end_date - timedelta(days=365)).isoformat()
    end_date_iso = end_date.isoformat()
    bridge_run_id = _market_proxy_bridge_run_id(snapshot_date)

    try:
        from src.replay.foundation_service import build_wp05b_replay_matrix
        from src.sih.rotation_risk_monitor import rotation_risk_summary
    except Exception as exc:
        status["status"] = "failed"
        status["warnings"].append(
            "Market proxy replay publish failed; Market Regime Guardrail may remain stale."
        )
        status["warnings"].append(f"Replay publish path unavailable: {exc}")
        return status

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="market-proxy-bridge-") as tmp_dir:
        staged_repo_root = Path(tmp_dir) / "repo"
        staged_current_root = _seed_market_proxy_replay_staging_root(staged_repo_root)

        for industry in _MARKET_PROXY_REPLAY_INDUSTRIES:
            try:
                result = build_wp05b_replay_matrix(
                    run_id=bridge_run_id,
                    snapshot_date=snapshot_date,
                    start_date=start_date,
                    end_date=end_date_iso,
                    filter_industry=industry,
                    current_root=staged_current_root,
                    analytical_history_root=_REPO_ROOT / "data" / "history" / "analytical_universe",
                    replay_history_root=_REPO_ROOT / "data" / "history" / "replays",
                    snapshot_registry_root=_REPO_ROOT / "data" / "history",
                )
                status["details"]["industry_results"].append(
                    {
                        "industry": industry,
                        "status": "completed",
                        "run_id": str(result.get("run_id") or bridge_run_id),
                        "matrix_row_count": int(result.get("matrix_row_count") or 0),
                        "availability_row_count": int(result.get("availability_row_count") or 0),
                        "status_counts": dict(result.get("status_counts") or {}),
                    }
                )
            except Exception as exc:
                failures.append(f"{industry}: {exc}")
                status["details"]["industry_results"].append(
                    {"industry": industry, "status": "failed", "run_id": bridge_run_id, "error": str(exc)}
                )

        latest_proxy_date_after: str | None = None
        missing_inputs_after: list[str] = []
        try:
            summary = rotation_risk_summary(repo_root=staged_repo_root)
            latest_proxy_date_after = str(((summary.get("proxy_returns") or {}).get("latest_proxy_date") or "")).strip() or None
            status["latest_proxy_date_after"] = latest_proxy_date_after
            status["latest_proxy_date"] = latest_proxy_date_after
            missing_inputs_after = [str(item) for item in list((summary.get("data_quality") or {}).get("missing_inputs") or [])]
            status["details"]["missing_inputs_after"] = missing_inputs_after
        except Exception as exc:
            failures.append(f"latest_proxy_date: {exc}")

        validation = _validate_market_proxy_replay_publish_candidate(
            staged_current_root=staged_current_root,
            industry_results=list(status["details"]["industry_results"]),
            latest_proxy_date_after=latest_proxy_date_after,
            missing_inputs=missing_inputs_after,
        )
        status["details"]["target_industries"] = validation["target_industries"]
        status["details"]["blocked_industries"] = validation["blocked_industries"]
        status["details"]["zero_row_industries"] = validation["zero_row_industries"]
        status["details"]["failed_industries"] = validation["failed_industries"]
        status["details"]["missing_required_cohorts"] = validation["missing_required_cohorts"]
        status["details"]["missing_output_files"] = validation["missing_output_files"]
        status["details"]["schema_missing"] = validation["schema_missing"]

        if not failures and validation["published"]:
            try:
                _publish_market_proxy_replay_staging_outputs(staged_repo_root)
                status["published"] = True
            except Exception as exc:
                failures.append(f"publish: {exc}")
                status["warnings"].append(
                    "Replay bridge failed while publishing validated staged artifacts; current replay artifacts were preserved."
                )

    if failures:
        status["status"] = "warning"
        status["reason"] = "industry_generation_failed"
        status["warnings"].append(
            "Market proxy replay publish completed with warnings; Market Regime Guardrail may remain stale."
        )
        status["warnings"].extend(failures)
    elif not status["published"]:
        status["status"] = "warning"
        status["reason"] = str(validation.get("reason") or reason)
        status["warnings"].extend(list(validation.get("warnings") or []))
        status["warnings"].append(
            "Replay artifacts were preserved; current replay artifacts need safe regeneration or restoration before the Market Regime Guardrail can become decision-ready."
        )
        status["warnings"].append(
            "Bridge validation blocked current replay publication, but replay history partitions and snapshot registries may have been written during staged generation."
        )
    else:
        status["status"] = "completed"

    if verbose:
        if status["status"] == "completed":
            print(
                "[refresh_signals] market-proxy replay publish: completed "
                f"(latest_proxy_date={status.get('latest_proxy_date') or 'unknown'})"
            )
        else:
            print(
                "[refresh_signals] market-proxy replay publish: "
                f"{status.get('status')} ({status.get('reason') or 'warning'})"
            )
            for warning in status["warnings"]:
                print(f"[refresh_signals]   {warning}")

    return status


def _build_refresh_scope(
    *,
    refresh_mode: str,
    buy_candidate_cap: int = 50,
) -> dict[str, object]:
    """Build refresh scope summary and per-provider symbol plans."""
    mode = _normalize_refresh_mode(refresh_mode)

    holdings = sorted(_load_portfolio_equity_holdings())
    holdings_set = set(holdings)
    buy_candidates = _load_buy_candidate_symbols(cap=buy_candidate_cap) if mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES else []
    buy_set = set(buy_candidates)

    if mode == REFRESH_MODE_MARKET_REGIME_PROXY_ONLY:
        holdings = []
        holdings_set = set()
        buy_candidates = []
        buy_set = set()

    include_market_proxies = mode in {
        REFRESH_MODE_PORTFOLIO_SIGNALS,
        REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES,
        REFRESH_MODE_PREPARE_PORTFOLIO_REVIEW,
        REFRESH_MODE_MARKET_REGIME_PROXY_ONLY,
    } or (mode == REFRESH_MODE_STALE_ONLY and _market_proxy_refresh_needed())
    market_proxies = _market_proxy_symbols() if include_market_proxies else []
    market_proxy_set = set(market_proxies)

    provider_holdings: dict[str, set[str]] = {
        "zacks": _load_portfolio_provider_holdings("zacks"),
        "danelfin": _load_portfolio_provider_holdings("danelfin"),
        "yahoo": _load_portfolio_provider_holdings("yahoo"),
    }

    mandatory_dependencies: set[str] = set()
    for symbols in provider_holdings.values():
        mandatory_dependencies |= set(symbols)
    mandatory_dependencies -= holdings_set
    mandatory_dependencies -= buy_set
    mandatory_dependencies -= market_proxy_set

    if mode == REFRESH_MODE_MARKET_REGIME_PROXY_ONLY:
        mandatory_dependencies = set()

    if mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
        deduped_all = _all_universe_symbols(_BASE_UNIVERSE)
    elif mode == REFRESH_MODE_MARKET_REGIME_PROXY_ONLY:
        deduped_all = sorted(market_proxy_set)
    else:
        deduped_all = sorted(holdings_set | buy_set | mandatory_dependencies | market_proxy_set)

    provider_symbols: dict[str, list[str]] = {}
    for provider in ("zacks", "danelfin", "yahoo"):
        if mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
            provider_symbols[provider] = list(deduped_all)
            continue
        if mode == REFRESH_MODE_MARKET_REGIME_PROXY_ONLY:
            provider_symbols[provider] = list(market_proxies)
            continue
        if mode == REFRESH_MODE_PORTFOLIO_SIGNALS:
            merged: list[str] = []
            seen: set[str] = set()
            for sym in sorted(provider_holdings.get(provider, set())) + sorted(mandatory_dependencies) + market_proxies:
                s = str(sym or "").strip().upper()
                if s and s not in seen:
                    seen.add(s)
                    merged.append(s)
            provider_symbols[provider] = merged
            continue
        if mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES:
            merged: list[str] = []
            seen: set[str] = set()
            for sym in sorted(provider_holdings.get(provider, set())) + buy_candidates + sorted(mandatory_dependencies) + market_proxies:
                s = str(sym or "").strip().upper()
                if s and s not in seen:
                    seen.add(s)
                    merged.append(s)
            provider_symbols[provider] = merged
            continue
        if mode == REFRESH_MODE_PREPARE_PORTFOLIO_REVIEW:
            merged: list[str] = []
            seen: set[str] = set()
            for sym in sorted(provider_holdings.get(provider, set())) + sorted(mandatory_dependencies) + market_proxies:
                s = str(sym or "").strip().upper()
                if s and s not in seen:
                    seen.add(s)
                    merged.append(s)
            provider_symbols[provider] = merged
            continue
        if mode == REFRESH_MODE_STALE_ONLY and market_proxies:
            provider_symbols[provider] = list(market_proxies)
            continue
        provider_symbols[provider] = []

    full_universe_count = len(_all_universe_symbols(_BASE_UNIVERSE))
    planned_symbol_samples = {
        "portfolio_holdings": holdings[:10],
        "buy_candidates": buy_candidates[:10],
        "mandatory_dependencies": sorted(mandatory_dependencies)[:10],
        "market_proxies": market_proxies[:10],
    }

    return {
        "refresh_intent": mode,
        "scope_summary": {
            "portfolio_holdings_count": len(holdings),
            "buy_candidate_count": len(buy_candidates),
            "mandatory_dependency_count": len(mandatory_dependencies),
            "market_proxy_count": len(market_proxies),
            "deduped_symbol_count": len(deduped_all),
            "full_universe_count": full_universe_count,
        },
        "planned_symbols": {
            "portfolio_holdings": holdings,
            "buy_candidates": buy_candidates,
            "mandatory_dependencies": sorted(mandatory_dependencies),
            "market_proxies": market_proxies,
            "deduped_all": deduped_all,
            "provider_symbols": provider_symbols,
        },
        "planned_symbol_samples": planned_symbol_samples,
        "buy_candidate_cap": int(buy_candidate_cap),
    }


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
    submitted = len(submitted_symbols)
    refresh_date = date.today().isoformat()

    latest_csv_by_provider = {
        "zacks": _ZACKS_DIR / "latest_zacks.csv",
        "danelfin": _DANELFIN_DIR / "latest_danelfin.csv",
        "yahoo": _YAHOO_DIR / "latest_yahoo_supplemental.csv",
    }
    latest_csv = latest_csv_by_provider.get(provider)
    primary_fields = _PROVIDER_PRIMARY_FIELDS.get(provider, ())

    rows_by_symbol: dict[str, list[dict[str, str]]] = {}
    if latest_csv is not None and latest_csv.exists():
        with latest_csv.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                symbol = str(row.get("symbol", "")).strip().upper()
                if not symbol:
                    continue
                rows_by_symbol.setdefault(symbol, []).append(dict(row))

    def _pick_row(symbol_rows: list[dict[str, str]]) -> dict[str, str] | None:
        if not symbol_rows:
            return None
        today_rows = [r for r in symbol_rows if str(r.get("sourced_date", "")).strip() == refresh_date]
        if today_rows:
            # Prefer row with primary data when multiple same-day rows exist.
            for row in today_rows:
                if any(str(row.get(field, "")).strip() for field in primary_fields):
                    return row
            return today_rows[0]
        # Fall back to most recent sourced_date row.
        return max(symbol_rows, key=lambda r: str(r.get("sourced_date", "")).strip())

    def _status_tokens(row: dict[str, str]) -> set[str]:
        tokens: set[str] = set()
        for field in _PROVIDER_STATUS_FIELDS:
            raw = str(row.get(field, "")).strip().upper()
            if raw:
                tokens.add(raw)
        return tokens

    written_count = 0
    written_refresh_date_count = 0
    primary_data_count = 0
    no_coverage_count = 0
    no_score_count = 0
    stale_carryover_count = 0
    explicit_error_count = 0
    duplicate_count = 0

    for symbol in submitted_symbols:
        symbol_rows = rows_by_symbol.get(symbol, [])
        if not symbol_rows:
            continue
        written_count += 1
        if len(symbol_rows) > 1:
            duplicate_count += 1

        row = _pick_row(symbol_rows)
        if row is None:
            continue

        sourced_date = str(row.get("sourced_date", "")).strip()
        has_primary_data = any(str(row.get(field, "")).strip() for field in primary_fields)
        tokens = _status_tokens(row)

        if sourced_date == refresh_date:
            written_refresh_date_count += 1
        elif sourced_date:
            stale_carryover_count += 1

        if has_primary_data:
            primary_data_count += 1

        if "NO_COVERAGE_AVAILABLE" in tokens:
            no_coverage_count += 1
        elif "NO_SCORE_AVAILABLE" in tokens:
            no_score_count += 1
        elif not has_primary_data:
            # Current provider files encode terminal no-coverage as empty primary fields.
            no_coverage_count += 1

        if tokens & {
            "FAILED",
            "ERROR",
            "PARSE_ERROR",
            "RATE_LIMIT",
            "TIMEOUT",
            "BLOCKED",
            "CAPTCHA",
        }:
            explicit_error_count += 1

    empty_primary_data_count = max(written_count - primary_data_count, 0)
    missing_written_count = max(submitted - written_count, 0)
    true_error_count = explicit_error_count + missing_written_count
    failed = true_error_count
    refreshed = written_refresh_date_count
    applicable_before = int(coverage_before.get("applicable_holdings") or 0)
    skipped = max(applicable_before - submitted, 0)
    skipped_checkpoint = int((fetch_stats or {}).get("skipped_checkpoint", 0))
    skipped_already_covered = int((fetch_stats or {}).get("skipped_already_covered", 0))
    retried_failed_checkpoint = int((fetch_stats or {}).get("retried_failed_checkpoint", 0))
    requested_count = int((fetch_stats or {}).get("requested", submitted) or submitted)
    attempted_count = int((fetch_stats or {}).get("attempted", submitted) or submitted)
    return {
        "provider": provider,
        "mode": mode,
        "refresh_date": refresh_date,
        "submitted_count": submitted,
        "written_count": written_count,
        "written_refresh_date_count": written_refresh_date_count,
        "primary_data_count": primary_data_count,
        "empty_primary_data_count": empty_primary_data_count,
        "no_coverage_count": no_coverage_count,
        "no_score_count": no_score_count,
        "stale_carryover_count": stale_carryover_count,
        "true_error_count": true_error_count,
        "missing_written_count": missing_written_count,
        "duplicate_count": duplicate_count,
        "pending_count": 0,
        "requested_count": requested_count,
        "attempted_count": attempted_count,
        "submitted": submitted,
        "skipped_checkpoint": skipped_checkpoint,
        "skipped_already_covered": skipped_already_covered,
        "retried_failed_checkpoint": retried_failed_checkpoint,
        "refreshed": refreshed,
        "skipped": skipped,
        "failed": failed,
        "coverage_before": _coverage_snapshot(coverage_before),
        "coverage_after": _coverage_snapshot(coverage_after),
        "runtime_sec": round(runtime_sec, 4),
    }


def _provider_report_research_fresh(metrics: dict[str, object], fallback: bool) -> bool:
    submitted = int(metrics.get("submitted_count") or metrics.get("submitted") or 0)
    if submitted <= 0:
        return fallback
    missing = int(metrics.get("missing_written_count") or 0)
    stale = int(metrics.get("stale_carryover_count") or 0)
    return missing == 0 and stale == 0


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
    refresh_mode: str = REFRESH_MODE_STALE_ONLY,
    smart: bool = False,
    collect_report: bool = False,
) -> bool | tuple[bool, dict[str, object]]:
    """Fetch fresh Zacks scores.  Returns True when a fetch was triggered."""
    latest = _ZACKS_DIR / "latest_zacks.csv"
    t0 = time.perf_counter()
    coverage_before = _holdings_coverage("zacks", latest)
    repair_targets = _coverage_refresh_targets(coverage_before)
    research_stale = _is_stale(latest)
    refresh_mode = _normalize_refresh_mode(refresh_mode)
    scope = _build_refresh_scope(refresh_mode=refresh_mode)
    proxy_targets = list((((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("zacks") or []))
    if refresh_mode == REFRESH_MODE_STALE_ONLY and not research_stale and not repair_targets and not proxy_targets:
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
                  research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    active_holdings = _load_portfolio_equity_holdings()
    forced = _load_portfolio_provider_holdings("zacks")
    mode = "research_refresh"
    if refresh_mode == REFRESH_MODE_PORTFOLIO_SIGNALS:
        symbols = list((((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("zacks") or []))
        mode = REFRESH_MODE_PORTFOLIO_SIGNALS
    elif refresh_mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES:
        symbols = list(((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("zacks") or [])
        mode = REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES
    elif refresh_mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
        symbols = _all_universe_symbols(_BASE_UNIVERSE)
        mode = REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE
    elif refresh_mode == REFRESH_MODE_STALE_ONLY and proxy_targets and not research_stale and not repair_targets:
        symbols = proxy_targets
        mode = "market_proxy_refresh"
    elif research_stale:
        symbols = build_smart_refresh_list(
            universe_csv=_BASE_UNIVERSE,
            zacks_cache_csv=latest,
            forced_symbols=forced or None,
        )
        symbols = _merge_forced_symbols(symbols, set(proxy_targets) if proxy_targets else None)
    else:
        mode = "coverage_repair"
        symbols = sorted({*repair_targets, *proxy_targets})
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
                  research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
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
        elif mode == REFRESH_MODE_PORTFOLIO_SIGNALS:
            print(
                f"[refresh_signals] Zacks: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} portfolio symbols."
            )
        elif mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES:
            print(
                f"[refresh_signals] Zacks: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} holdings + buy-candidate symbols."
            )
        elif mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
            print(
                f"[refresh_signals] Zacks: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} universe symbols."
            )
        elif mode == "market_proxy_refresh":
            print(
                f"[refresh_signals] Zacks: stale_only — refreshing {len(symbols)} market-regime proxy symbols."
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
              research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
            holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
        )
        return True, metrics
    return True


def _refresh_danelfin(
    *,
    dry_run: bool,
    verbose: bool,
    refresh_mode: str = REFRESH_MODE_STALE_ONLY,
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
    refresh_mode = _normalize_refresh_mode(refresh_mode)
    scope = _build_refresh_scope(refresh_mode=refresh_mode)
    proxy_targets = list((((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("danelfin") or []))
    if refresh_mode == REFRESH_MODE_STALE_ONLY and not research_stale and not repair_targets and not proxy_targets:
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
                  research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    active_holdings = _load_portfolio_equity_holdings()
    forced = forced_symbols if forced_symbols is not None else _load_portfolio_provider_holdings("danelfin")
    mode = "research_refresh"
    if refresh_mode == REFRESH_MODE_PORTFOLIO_SIGNALS:
        symbols = list((((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("danelfin") or []))
        mode = REFRESH_MODE_PORTFOLIO_SIGNALS
    elif refresh_mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES:
        symbols = list(((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("danelfin") or [])
        mode = REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES
    elif refresh_mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
        symbols = _all_universe_symbols(_BASE_UNIVERSE)
        mode = REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE
    elif refresh_mode == REFRESH_MODE_STALE_ONLY and proxy_targets and not research_stale and not repair_targets:
        symbols = proxy_targets
        mode = "market_proxy_refresh"
    elif research_stale:
        base_symbols = _smart_universe_symbols(_BASE_UNIVERSE) if smart else _all_universe_symbols(_BASE_UNIVERSE)
        symbols = _merge_forced_symbols(base_symbols, forced if smart else None)
        symbols = _merge_forced_symbols(symbols, set(proxy_targets) if proxy_targets else None)
    else:
        mode = "coverage_repair"
        symbols = sorted({*repair_targets, *proxy_targets})
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
                  research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
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
        elif mode == REFRESH_MODE_PORTFOLIO_SIGNALS:
            print(
                f"[refresh_signals] Danelfin: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} portfolio symbols."
            )
        elif mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES:
            print(
                f"[refresh_signals] Danelfin: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} holdings + buy-candidate symbols."
            )
        elif mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
            print(
                f"[refresh_signals] Danelfin: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} symbols ({mode_label})."
            )
        elif mode == "market_proxy_refresh":
            print(
                f"[refresh_signals] Danelfin: stale_only — refreshing {len(symbols)} market-regime proxy symbols."
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
              research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
            holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
        )
        return True, metrics
    return True


def _refresh_yahoo(
    *,
    dry_run: bool,
    verbose: bool,
    refresh_mode: str = REFRESH_MODE_STALE_ONLY,
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
    refresh_mode = _normalize_refresh_mode(refresh_mode)
    scope = _build_refresh_scope(refresh_mode=refresh_mode)
    proxy_targets = list((((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("yahoo") or []))
    if refresh_mode == REFRESH_MODE_STALE_ONLY and not research_stale and not repair_targets and not proxy_targets:
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
                  research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
                holdings_status=str(coverage_before.get("status") or "UNKNOWN"),
            )
            return False, metrics
        return False

    active_holdings = _load_portfolio_equity_holdings()
    forced = forced_symbols if forced_symbols is not None else _load_portfolio_provider_holdings("yahoo")
    mode = "research_refresh"
    if refresh_mode == REFRESH_MODE_PORTFOLIO_SIGNALS:
        symbols = list((((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("yahoo") or []))
        mode = REFRESH_MODE_PORTFOLIO_SIGNALS
    elif refresh_mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES:
        symbols = list(((scope.get("planned_symbols") or {}).get("provider_symbols") or {}).get("yahoo") or [])
        mode = REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES
    elif refresh_mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
        symbols = _all_universe_symbols(_BASE_UNIVERSE)
        mode = REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE
    elif refresh_mode == REFRESH_MODE_STALE_ONLY and proxy_targets and not research_stale and not repair_targets:
        symbols = proxy_targets
        mode = "market_proxy_refresh"
    elif research_stale:
        base_symbols = _smart_universe_symbols(_BASE_UNIVERSE) if smart else _all_universe_symbols(_BASE_UNIVERSE)
        symbols = _merge_forced_symbols(base_symbols, forced if smart else None)
        symbols = _merge_forced_symbols(symbols, set(proxy_targets) if proxy_targets else None)
    else:
        mode = "coverage_repair"
        symbols = sorted({*repair_targets, *proxy_targets})
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
                  research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
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
        elif mode == REFRESH_MODE_PORTFOLIO_SIGNALS:
            print(
                f"[refresh_signals] Yahoo: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} portfolio symbols."
            )
        elif mode == REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES:
            print(
                f"[refresh_signals] Yahoo: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} holdings + buy-candidate symbols."
            )
        elif mode == REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE:
            print(
                f"[refresh_signals] Yahoo: {_refresh_mode_label(refresh_mode)} — fetching {len(symbols)} symbols ({mode_label})."
            )
        elif mode == "market_proxy_refresh":
            print(
                f"[refresh_signals] Yahoo: stale_only — refreshing {len(symbols)} market-regime proxy symbols."
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
              research_fresh=_provider_report_research_fresh(metrics, fallback=not research_stale),
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
    refresh_mode: str = REFRESH_MODE_STALE_ONLY,
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
        refresh_mode=refresh_mode,
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
    refresh_mode: str = REFRESH_MODE_STALE_ONLY,
    smart: bool = False,
) -> dict[str, object]:
    """Check freshness and fetch stale/coverage-degraded providers with report."""
    resolved_mode = _normalize_refresh_mode(refresh_mode)
    scope_plan = _build_refresh_scope(refresh_mode=resolved_mode)
    triggered: dict[str, bool] = {}
    provider_report: dict[str, dict[str, object]] = {}
    t0 = time.perf_counter()
    provider_set = {p.lower() for p in providers}
    scope_summary = scope_plan.get("scope_summary") or {}

    replay_publish_status: dict[str, Any] = {
        "attempted": False,
        "status": "disabled",
        "reason": "dedicated_proxy_artifact_architecture",
        "artifacts": [
            "data/current/replay_inputs.csv",
            "data/current/replay_performance_series.csv",
        ],
        "latest_proxy_date_before": None,
        "latest_proxy_date_after": None,
        "latest_proxy_date": None,
        "warnings": [
            "Replay bridge publication is disabled for market regime proxy freshness; dedicated artifacts are used instead."
        ],
        "details": {},
    }
    dedicated_history_status: dict[str, Any] = {
        "attempted": False,
        "status": "skipped_not_in_scope",
        "reason": "market_proxies_not_in_scope",
        "published": False,
        "symbols": [],
        "observations_by_symbol": {},
        "earliest_date": None,
        "latest_common_date": None,
        "missing_symbols": [],
        "insufficient_symbols": [],
        "warnings": [],
        "transaction_id": None,
    }
    dedicated_proxy_build_status: dict[str, Any] = {
        "attempted": False,
        "status": "skipped_not_in_scope",
        "reason": "market_proxies_not_in_scope",
        "published": False,
        "input_source": None,
        "latest_proxy_date_before": None,
        "latest_proxy_date_after": None,
        "missing_inputs": [],
        "warnings": [],
        "transaction_id": None,
    }

    if resolved_mode == REFRESH_MODE_MARKET_REGIME_PROXY_ONLY:
        # Targeted path only: fetch four proxy symbols + build dedicated artifacts.
        if dry_run:
            dedicated_history_status["status"] = "skipped_dry_run"
            dedicated_history_status["reason"] = "dry_run"
            dedicated_proxy_build_status["status"] = "skipped_dry_run"
            dedicated_proxy_build_status["reason"] = "dry_run"
        else:
            from src.portfolio.regime.market_regime_proxy_artifacts import (
                build_market_regime_proxy_artifacts,
                fetch_market_regime_proxy_history,
            )

            dedicated_history_status = fetch_market_regime_proxy_history(repo_root=_REPO_ROOT)
            if bool(dedicated_history_status.get("published")):
                dedicated_proxy_build_status = build_market_regime_proxy_artifacts(repo_root=_REPO_ROOT)
            else:
                dedicated_proxy_build_status["attempted"] = True
                dedicated_proxy_build_status["status"] = "failed"
                dedicated_proxy_build_status["reason"] = "history_fetch_failed"
                dedicated_proxy_build_status["warnings"] = [
                    "Dedicated proxy artifact build skipped because dedicated history fetch failed validation."
                ]

        return {
            "triggered": triggered,
            "providers": provider_report,
            "refresh_intent": resolved_mode,
            "scope_summary": scope_summary,
            "planned_symbol_samples": scope_plan.get("planned_symbol_samples") or {},
            "market_proxy_replay_publish": replay_publish_status,
            "market_regime_proxy_history_fetch": dedicated_history_status,
            "market_regime_proxy_artifact_build": dedicated_proxy_build_status,
            "buy_candidate_cap": int(scope_plan.get("buy_candidate_cap") or 50),
            "smart": bool(smart),
            "dry_run": bool(dry_run),
            "runtime_sec": round(time.perf_counter() - t0, 4),
        }

    if "zacks" in provider_set:
        z = _refresh_zacks(
            dry_run=dry_run,
            verbose=verbose,
            refresh_mode=refresh_mode,
            smart=smart,
            collect_report=True,
        )
        z_triggered, z_metrics = z
        triggered["zacks"] = bool(z_triggered)
        provider_report["zacks"] = {"triggered": bool(z_triggered), **z_metrics}
    if "yahoo" in provider_set:
        y = _refresh_yahoo(
            dry_run=dry_run,
            verbose=verbose,
            refresh_mode=refresh_mode,
            smart=smart,
            collect_report=True,
        )
        y_triggered, y_metrics = y
        triggered["yahoo"] = bool(y_triggered)
        provider_report["yahoo"] = {"triggered": bool(y_triggered), **y_metrics}
    if "danelfin" in provider_set:
        d = _refresh_danelfin(
            dry_run=dry_run,
            verbose=verbose,
            refresh_mode=refresh_mode,
            smart=smart,
            collect_report=True,
        )
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

    market_proxy_count = int(scope_summary.get("market_proxy_count") or 0)
    if market_proxy_count > 0:
        should_publish = True
        if dry_run:
            dedicated_proxy_build_status["status"] = "skipped_dry_run"
            dedicated_proxy_build_status["reason"] = "dry_run"
        elif should_publish:
            from src.portfolio.regime.market_regime_proxy_artifacts import build_market_regime_proxy_artifacts

            dedicated_proxy_build_status = build_market_regime_proxy_artifacts(repo_root=_REPO_ROOT)
        else:
            dedicated_proxy_build_status["status"] = "skipped_fresh"
            dedicated_proxy_build_status["reason"] = "market_regime_proxy_artifacts_fresh"

    return {
        "triggered": triggered,
        "providers": provider_report,
        "refresh_intent": resolved_mode,
        "scope_summary": scope_summary,
        "planned_symbol_samples": scope_plan.get("planned_symbol_samples") or {},
        "market_proxy_replay_publish": replay_publish_status,
        "market_regime_proxy_history_fetch": dedicated_history_status,
        "market_regime_proxy_artifact_build": dedicated_proxy_build_status,
        "buy_candidate_cap": int(scope_plan.get("buy_candidate_cap") or 50),
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
        "--refresh-mode",
        choices=sorted(_REFRESH_MODES),
        default=REFRESH_MODE_STALE_ONLY,
        help="Refresh mode compatibility switch.",
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
        refresh_mode=args.refresh_mode,
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
