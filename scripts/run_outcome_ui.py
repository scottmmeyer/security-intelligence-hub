#!/usr/bin/env python3
"""Run a local static + API server for the WP-04.1 outcome visualization prototype.

Static files are served from the repository root.

API endpoints:
  GET  /api/signal-status          → JSON: last sourced_date and staleness per provider
  POST /api/signal-refresh         → launch scripts/refresh_signals.py as background process
  GET  /api/signal-refresh/status  → JSON: {"running": true/false}
    GET  /api/market-regime-guardrail/latest → display-only market regime posture
  POST /api/portfolio/analyze      → ingest + enrich + align portfolio CSV; returns full analysis
  GET  /api/portfolio/runs         → list all completed portfolio analysis runs
  GET  /api/portfolio/runs/{id}    → load a specific analysis run by run_id
"""

from __future__ import annotations

import argparse
import copy
import concurrent.futures
import csv
import http.server
import io
import json
import math
import os
import re
import secrets
import socketserver
import subprocess
import sys
import threading
from urllib.parse import parse_qs
from datetime import date, datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_SIGNAL_FILES = {
    "zacks":    _REPO_ROOT / "data/signals/zacks/latest_zacks.csv",
    "danelfin": _REPO_ROOT / "data/signals/danelfin/latest_danelfin.csv",
    "yahoo":    _REPO_ROOT / "data/signals/yahoo/latest_yahoo_supplemental.csv",
}
_ESS_SIGNAL_SNAPSHOT = _REPO_ROOT / "data" / "current" / "signal_snapshot.csv"
_ESS_COVERAGE_WARNING = _REPO_ROOT / "data" / "current" / "ess_coverage_warning.json"
_REFRESH_REPORT_PATH = _REPO_ROOT / "data" / "current" / "last_signal_refresh_report.json"

# Background refresh process handle (module-level so Handler instances share it)
_refresh_proc: subprocess.Popen | None = None
_refresh_last_report: dict | None = None
_refresh_last_exit_code: int | None = None
_refresh_requested_intent: str | None = None
_refresh_resolved_intent: str | None = None
_refresh_scope_summary: dict | None = None
_refresh_scope_samples: dict | None = None
_refresh_provider_planned_totals: dict[str, int | None] = {}
_refresh_started_at_utc: str | None = None
_refresh_completed_at_utc: str | None = None

# On-demand score fetch jobs keyed by symbol (uppercase)
_fetch_jobs: dict[str, dict] = {}
_fetch_lock = threading.Lock()

_SYMBOL_RE = re.compile(r"^[A-Z0-9./\-]{1,12}$")
_DANELFIN_CAPTURE_ALLOWED_OPERATOR_SOURCES = {"PAIR_PAGE", "STOCK_PAGE"}
_DANELFIN_CAPTURE_ALLOWED_METHODS = {
    "BROWSER_CAPTURE_DANELFIN_UI",
    "MANUAL_DANELFIN_UI",
}
_DANELFIN_DIAGNOSTIC_DEFAULT_SYMBOL = "NVDA"
_DANELFIN_DIAGNOSTIC_DEFAULT_PAIR_SYMBOL = "ANIP"
_DANELFIN_CAPTURE_STATUS_FIELDS = {
    "worker_started",
    "worker_claimed",
    "navigation_started",
    "navigation_completed",
    "capture_started",
    "capture_completed",
    "result_received",
    "normalized",
    "validation_passed",
}

_danelfin_diag_lock = threading.Lock()
_danelfin_diag_runs: dict[str, dict[str, object]] = {}
_danelfin_prod_lock = threading.Lock()
_danelfin_prod_runs: dict[str, dict[str, object]] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_danelfin_diag_event(
    run_id: str,
    event: str,
    *,
    error: str | None = None,
    url: str | None = None,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    with _danelfin_diag_lock:
        state = _danelfin_diag_runs.get(run_id)
        if not isinstance(state, dict):
            state = {
                "diagnostic_run_id": run_id,
                "created": None,
                "worker_started": None,
                "worker_claimed": None,
                "navigation_started": None,
                "navigation_completed": None,
                "capture_started": None,
                "capture_completed": None,
                "result_received": None,
                "normalized": None,
                "validation_passed": None,
                "error": None,
                "mode": "diagnostic",
                "state": "PREPARED",
                "claimed_at": None,
                "event_log": [],
            }
            _danelfin_diag_runs[run_id] = state

        timestamp = _utc_now_iso()
        if event == "created":
            state["created"] = timestamp
            state["state"] = "PREPARED"
        elif event in _DANELFIN_CAPTURE_STATUS_FIELDS:
            state[event] = timestamp
            if event == "worker_started":
                state["state"] = "RUNNING"
        elif event == "error":
            state["error"] = {
                "timestamp": timestamp,
                "message": str(error or "unknown_error"),
            }
            state["state"] = "ERROR"

        if event == "validation_passed":
            state["state"] = "COMPLETED"

        if url:
            state["url"] = str(url)
        event_log = state.get("event_log")
        if not isinstance(event_log, list):
            event_log = []
            state["event_log"] = event_log
        event_log.append(
            {
                "event": str(event),
                "timestamp": timestamp,
                "payload": copy.deepcopy(payload) if isinstance(payload, dict) else {},
            }
        )
        state["updated_at"] = timestamp
        return copy.deepcopy(state)


def _build_danelfin_diagnostic_queue_payload(symbol: str, pair_symbol: str) -> dict[str, object]:
    primary_symbol = str(symbol or "").strip().upper() or _DANELFIN_DIAGNOSTIC_DEFAULT_SYMBOL
    if not _SYMBOL_RE.match(primary_symbol):
        raise ValueError(f"invalid diagnostic symbol: {primary_symbol!r}")

    secondary_symbol = str(pair_symbol or "").strip().upper() or _DANELFIN_DIAGNOSTIC_DEFAULT_PAIR_SYMBOL
    if not _SYMBOL_RE.match(secondary_symbol):
        raise ValueError(f"invalid diagnostic pair symbol: {secondary_symbol!r}")
    if secondary_symbol == primary_symbol:
        secondary_symbol = "MSFT" if primary_symbol != "MSFT" else "AAPL"

    run_id = f"diag-{_utc_now_iso().replace(':', '').replace('-', '').replace('.', '')}-{secrets.token_hex(4)}"
    symbols = [primary_symbol, secondary_symbol]
    job = {
        "job_id": run_id,
        "mode": "diagnostic",
        "kind": "pair",
        "symbols": symbols,
        "url": _danelfin_capture_pair_url(symbols),
        "operator_source": "PAIR_PAGE",
        "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
        "diagnostic": True,
        "dry_run": True,
        "diagnostic_run_id": run_id,
    }

    with _danelfin_diag_lock:
        _danelfin_diag_runs[run_id] = {
            "diagnostic_run_id": run_id,
            "diagnostic": True,
            "mode": "diagnostic",
            "dry_run": True,
            "symbol": primary_symbol,
            "symbols": symbols,
            "job_id": run_id,
            "url": str(job["url"]),
            "created": _utc_now_iso(),
            "state": "PREPARED",
            "claimed_at": None,
            "worker_started": None,
            "worker_claimed": None,
            "navigation_started": None,
            "navigation_completed": None,
            "capture_started": None,
            "capture_completed": None,
            "result_received": None,
            "normalized": None,
            "validation_passed": None,
            "error": None,
            "event_log": [],
            "updated_at": _utc_now_iso(),
        }

    return {
        "status": "ok",
        "provider": "danelfin",
        "diagnostic": True,
        "dry_run": True,
        "diagnostic_run_id": run_id,
        "symbols": [primary_symbol],
        "jobs": [job],
        "job_count": 1,
        "generated_at_utc": _utc_now_iso(),
    }


def _danelfin_diagnostic_status(run_id: str) -> dict[str, object]:
    requested = str(run_id or "").strip()
    if not requested:
        raise ValueError("diagnostic run id is required")
    with _danelfin_diag_lock:
        state = _danelfin_diag_runs.get(requested)
        if not isinstance(state, dict):
            raise KeyError(requested)
        return copy.deepcopy(state)


def _build_danelfin_diagnostic_queue_payload_from_state(state: dict[str, object]) -> dict[str, object]:
    run_id = str(state.get("diagnostic_run_id") or "").strip()
    symbols_raw = state.get("symbols")
    symbols = [str(item).strip().upper() for item in symbols_raw] if isinstance(symbols_raw, list) else []
    symbols = [item for item in symbols if item]
    if not run_id or not symbols:
        raise ValueError("diagnostic run state is incomplete")

    url = str(state.get("url") or "").strip() or _danelfin_capture_pair_url(symbols)
    job = {
        "job_id": str(state.get("job_id") or run_id),
        "mode": str(state.get("mode") or "diagnostic"),
        "kind": "pair",
        "symbols": symbols,
        "url": url,
        "operator_source": "PAIR_PAGE",
        "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
        "diagnostic": True,
        "dry_run": True,
        "diagnostic_run_id": run_id,
    }

    return {
        "status": "ok",
        "provider": "danelfin",
        "diagnostic": True,
        "dry_run": True,
        "diagnostic_run_id": run_id,
        "symbols": [symbols[0]],
        "jobs": [job],
        "job_count": 1,
        "generated_at_utc": _utc_now_iso(),
    }


def _find_prepared_danelfin_diagnostic_run(symbol: str = "", run_id: str = "") -> dict[str, object] | None:
    requested_run_id = str(run_id or "").strip()
    requested_symbol = str(symbol or "").strip().upper()

    with _danelfin_diag_lock:
        if requested_run_id:
            state = _danelfin_diag_runs.get(requested_run_id)
            if isinstance(state, dict):
                if state.get("claimed_at") is not None:
                    return None
                if state.get("state") in {"COMPLETED", "ERROR"}:
                    return None
                return copy.deepcopy(state)
            return None

        if requested_symbol and not _SYMBOL_RE.match(requested_symbol):
            return None

        candidates: list[dict[str, object]] = []
        for state in _danelfin_diag_runs.values():
            if not isinstance(state, dict):
                continue
            if state.get("claimed_at") is not None:
                continue
            if state.get("state") in {"COMPLETED", "ERROR"}:
                continue
            symbols_raw = state.get("symbols")
            symbols = [str(item).strip().upper() for item in symbols_raw] if isinstance(symbols_raw, list) else []
            symbols = [item for item in symbols if item]
            if requested_symbol and (not symbols or symbols[0] != requested_symbol):
                continue
            candidates.append(copy.deepcopy(state))

    if not candidates:
        return None

    candidates.sort(key=lambda item: str(item.get("created") or ""), reverse=True)
    return candidates[0]


def _claim_prepared_danelfin_diagnostic_run(run_id: str, worker_id: str = "") -> dict[str, object] | None:
    requested_run_id = str(run_id or "").strip()
    worker = str(worker_id or "").strip() or "local_worker"
    if not requested_run_id:
        raise ValueError("diagnostic run id is required for claim")

    with _danelfin_diag_lock:
        state = _danelfin_diag_runs.get(requested_run_id)
        if not isinstance(state, dict):
            return None
        if state.get("claimed_at") is not None:
            return None
        if state.get("state") in {"COMPLETED", "ERROR"}:
            return None

        claim_ts = _utc_now_iso()
        state["claimed_at"] = claim_ts
        state["worker_id"] = worker
        state["state"] = "RUNNING"
        state["worker_claimed"] = claim_ts
        state["updated_at"] = claim_ts

        event_log = state.get("event_log")
        if not isinstance(event_log, list):
            event_log = []
            state["event_log"] = event_log
        event_log.append(
            {
                "event": "worker_claimed",
                "timestamp": claim_ts,
                "payload": {"worker_id": worker, "claim_source": "claim_endpoint"},
            }
        )

        claimed = copy.deepcopy(state)

    return _build_danelfin_diagnostic_queue_payload_from_state(claimed)


def _build_danelfin_production_jobs(symbols: list[str], run_id: str) -> list[dict[str, object]]:
    jobs: list[dict[str, object]] = []
    for idx in range(0, len(symbols), 2):
        chunk = symbols[idx:idx + 2]
        kind = "single" if len(chunk) == 1 else "pair"
        operator_source = "STOCK_PAGE" if kind == "single" else "PAIR_PAGE"
        jobs.append(
            {
                "job_id": f"{run_id}:{idx // 2}",
                "run_id": run_id,
                "mode": "production",
                "kind": kind,
                "symbols": chunk,
                "url": _danelfin_capture_pair_url(chunk),
                "operator_source": operator_source,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "diagnostic": False,
                "dry_run": False,
            }
        )
    return jobs


def _build_danelfin_production_queue_payload_from_state(state: dict[str, object]) -> dict[str, object]:
    run_id = str(state.get("run_id") or "").strip()
    symbols = [
        str(item).strip().upper()
        for item in (state.get("symbols") if isinstance(state.get("symbols"), list) else [])
        if str(item).strip()
    ]
    if not run_id or not symbols:
        raise ValueError("production run state is incomplete")

    jobs = state.get("jobs") if isinstance(state.get("jobs"), list) else []
    if not jobs:
        jobs = _build_danelfin_production_jobs(symbols, run_id)

    return {
        "status": "ok",
        "provider": "danelfin",
        "diagnostic": False,
        "dry_run": False,
        "mode": "production",
        "run_id": run_id,
        "symbols": symbols,
        "jobs": jobs,
        "job_count": len(jobs),
        "generated_at_utc": _utc_now_iso(),
    }


def _prepare_danelfin_production_run(symbols: list[str], *, source: str = "") -> dict[str, object]:
    normalized_symbols: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        sym = str(raw or "").strip().upper()
        if not sym or not _SYMBOL_RE.match(sym) or sym in seen:
            continue
        seen.add(sym)
        normalized_symbols.append(sym)
    if not normalized_symbols:
        raise ValueError("at least one valid symbol is required")

    run_id = f"prod-{_utc_now_iso().replace(':', '').replace('-', '').replace('.', '')}-{secrets.token_hex(4)}"
    jobs = _build_danelfin_production_jobs(normalized_symbols, run_id)
    created_at = _utc_now_iso()
    with _danelfin_prod_lock:
        state = {
            "run_id": run_id,
            "mode": "production",
            "diagnostic": False,
            "dry_run": False,
            "symbols": normalized_symbols,
            "jobs": jobs,
            "source": str(source or "").strip() or None,
            "created": created_at,
            "state": "PREPARED",
            "claimed_at": None,
            "worker_started": None,
            "worker_claimed": None,
            "navigation_started": None,
            "navigation_completed": None,
            "capture_started": None,
            "capture_completed": None,
            "result_received": None,
            "normalized": None,
            "validation_passed": None,
            "error": None,
            "event_log": [],
            "updated_at": created_at,
        }
        _danelfin_prod_runs[run_id] = state
        prepared_state = copy.deepcopy(state)
    return _build_danelfin_production_queue_payload_from_state(prepared_state)


def _find_prepared_danelfin_production_run(run_id: str = "") -> dict[str, object] | None:
    requested_run_id = str(run_id or "").strip()
    with _danelfin_prod_lock:
        if requested_run_id:
            state = _danelfin_prod_runs.get(requested_run_id)
            if not isinstance(state, dict):
                return None
            if state.get("claimed_at") is not None:
                return None
            if state.get("state") in {"COMPLETED", "ERROR"}:
                return None
            return copy.deepcopy(state)

        candidates: list[dict[str, object]] = []
        for state in _danelfin_prod_runs.values():
            if not isinstance(state, dict):
                continue
            if state.get("claimed_at") is not None:
                continue
            if state.get("state") in {"COMPLETED", "ERROR"}:
                continue
            candidates.append(copy.deepcopy(state))
    if not candidates:
        return None
    candidates.sort(key=lambda item: str(item.get("created") or ""))
    return candidates[0]


def _claim_prepared_danelfin_production_run(run_id: str, worker_id: str = "") -> dict[str, object] | None:
    requested_run_id = str(run_id or "").strip()
    worker = str(worker_id or "").strip() or "local_worker"
    if not requested_run_id:
        raise ValueError("run id is required for production claim")

    with _danelfin_prod_lock:
        state = _danelfin_prod_runs.get(requested_run_id)
        if not isinstance(state, dict):
            return None
        if state.get("claimed_at") is not None:
            return None
        if state.get("state") in {"COMPLETED", "ERROR"}:
            return None

        claim_ts = _utc_now_iso()
        state["claimed_at"] = claim_ts
        state["worker_id"] = worker
        state["state"] = "RUNNING"
        state["worker_claimed"] = claim_ts
        state["updated_at"] = claim_ts
        event_log = state.get("event_log")
        if not isinstance(event_log, list):
            event_log = []
            state["event_log"] = event_log
        event_log.append(
            {
                "event": "worker_claimed",
                "timestamp": claim_ts,
                "payload": {"worker_id": worker, "claim_source": "claim_endpoint"},
            }
        )
        claimed = copy.deepcopy(state)

    return _build_danelfin_production_queue_payload_from_state(claimed)


def _record_danelfin_production_event(
    run_id: str,
    event: str,
    *,
    error: str | None = None,
    url: str | None = None,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    requested_run_id = str(run_id or "").strip()
    if not requested_run_id:
        raise ValueError("run id is required")

    with _danelfin_prod_lock:
        state = _danelfin_prod_runs.get(requested_run_id)
        if not isinstance(state, dict):
            raise KeyError(requested_run_id)

        timestamp = _utc_now_iso()
        if event in _DANELFIN_CAPTURE_STATUS_FIELDS:
            state[event] = timestamp
            if event == "worker_started":
                state["state"] = "RUNNING"
        elif event == "error":
            state["error"] = {
                "timestamp": timestamp,
                "message": str(error or "unknown_error"),
            }
            state["state"] = "ERROR"

        if event == "validation_passed":
            state["state"] = "COMPLETED"
        if url:
            state["url"] = str(url)

        event_log = state.get("event_log")
        if not isinstance(event_log, list):
            event_log = []
            state["event_log"] = event_log
        event_log.append(
            {
                "event": str(event),
                "timestamp": timestamp,
                "payload": copy.deepcopy(payload) if isinstance(payload, dict) else {},
            }
        )
        state["updated_at"] = timestamp
        return copy.deepcopy(state)


def _danelfin_production_status(run_id: str) -> dict[str, object]:
    requested = str(run_id or "").strip()
    if not requested:
        raise ValueError("run id is required")
    with _danelfin_prod_lock:
        state = _danelfin_prod_runs.get(requested)
        if not isinstance(state, dict):
            raise KeyError(requested)
        return copy.deepcopy(state)


def _resolve_provider_signal_file(provider_name: str) -> Path:
    configured = _SIGNAL_FILES.get(provider_name)
    if configured is None:
        return _REPO_ROOT / "data" / "signals" / provider_name / f"latest_{provider_name}.csv"
    if provider_name != "yahoo" or configured.exists():
        return configured

    candidates = [
        configured.parent / "latest_yahoo_supplemental.csv",
        configured.parent / "latest_yahoo.csv",
        configured.parent / "yahoo_supplemental.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    dated_candidates = sorted(
        configured.parent.glob("*_yahoo_supplemental.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if dated_candidates:
        return dated_candidates[0]

    return configured


def _danelfin_capture_pair_url(symbols: list[str]) -> str:
    if len(symbols) < 2:
        symbol = symbols[0].lower()
        return f"https://danelfin.com/stock/{symbol}"
    left = symbols[0].lower()
    right = symbols[1].lower()
    return f"https://danelfin.com/stocks/{left}-vs-{right}"


def _danelfin_capture_queue_payload() -> dict[str, object]:
    import sys as _sys

    if str(_REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_REPO_ROOT))

    from src.portfolio.holdings_coverage import summarize_holdings_coverage

    coverage = summarize_holdings_coverage(
        provider="danelfin",
        latest_csv=_SIGNAL_FILES["danelfin"],
        analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
        base_universe_csv=_REPO_ROOT / "data" / "current" / "base_equity_universe.csv",
        threshold_days=2,
    )
    symbols_info = coverage.get("symbols") if isinstance(coverage, dict) else {}
    if not isinstance(symbols_info, dict):
        symbols_info = {}

    baseline = None
    try:
        from src.portfolio.holdings_coverage import load_active_holdings_baseline

        baseline = load_active_holdings_baseline(_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs")
    except Exception:
        baseline = None

    capture_symbols: list[str] = []
    seen: set[str] = set()
    if baseline is not None:
        for row in baseline.holdings:
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol or symbol in seen:
                continue
            info = symbols_info.get(symbol)
            if not isinstance(info, dict):
                continue
            if not bool(info.get("applicable")):
                continue
            if str(info.get("classification") or "").strip().upper() not in {"STALE", "MISSING", "FAILED"}:
                continue
            seen.add(symbol)
            capture_symbols.append(symbol)

    jobs: list[dict[str, object]] = []
    run_id = str(coverage.get("run_id") or "").strip() or f"coverage-{_utc_now_iso().replace(':', '').replace('-', '').replace('.', '')}"
    for idx in range(0, len(capture_symbols), 2):
        chunk = capture_symbols[idx:idx + 2]
        kind = "single" if len(chunk) == 1 else "pair"
        operator_source = "STOCK_PAGE" if kind == "single" else "PAIR_PAGE"
        jobs.append(
            {
                "job_id": f"{run_id}:{idx // 2}",
                "run_id": run_id,
                "mode": "production",
                "kind": kind,
                "symbols": chunk,
                "url": _danelfin_capture_pair_url(chunk),
                "operator_source": operator_source,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "dry_run": False,
                "diagnostic": False,
            }
        )

    return {
        "status": "ok",
        "provider": "danelfin",
        "run_id": run_id,
        "mode": "production",
        "dry_run": False,
        "coverage": coverage,
        "symbols": capture_symbols,
        "jobs": jobs,
        "pair_count": sum(1 for job in jobs if job.get("kind") == "pair"),
        "single_count": sum(1 for job in jobs if job.get("kind") == "single"),
        "symbol_count": len(capture_symbols),
        "job_count": len(jobs),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _capture_cors_origin(handler: http.server.BaseHTTPRequestHandler) -> str | None:
    origin = str(handler.headers.get("Origin") or "").strip()
    if not origin:
        return None
    if origin.startswith("chrome-extension://"):
        return origin
    if origin in {"http://127.0.0.1:8765", "http://localhost:8765"}:
        return origin
    return None


def _normalize_browser_capture_payload(payload: dict[str, object]) -> dict[str, object]:
    observations = payload.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("observations must be a non-empty array")

    dry_run_raw = payload.get("dry_run", True)
    if isinstance(dry_run_raw, bool):
        dry_run = dry_run_raw
    else:
        raise ValueError("dry_run must be boolean")

    operator_source = str(payload.get("operator_source") or "PAIR_PAGE").strip().upper()
    if operator_source not in _DANELFIN_CAPTURE_ALLOWED_OPERATOR_SOURCES:
        raise ValueError("operator_source must be PAIR_PAGE or STOCK_PAGE")

    acquisition_method = str(payload.get("acquisition_method") or "BROWSER_CAPTURE_DANELFIN_UI").strip().upper()
    if acquisition_method not in _DANELFIN_CAPTURE_ALLOWED_METHODS:
        raise ValueError("unsupported acquisition_method")

    normalized_observations: list[dict[str, object]] = []
    seen_symbols: set[str] = set()
    for raw_obs in observations:
        if not isinstance(raw_obs, dict):
            raise ValueError("each observation must be an object")
        symbol = str(raw_obs.get("symbol") or "").strip().upper()
        if not symbol or not _SYMBOL_RE.match(symbol):
            raise ValueError(f"invalid symbol: {symbol!r}")
        if symbol in seen_symbols:
            raise ValueError(f"duplicate symbol in request: {symbol}")
        seen_symbols.add(symbol)
        normalized_observations.append(
            {
                "symbol": symbol,
                "danelfin_raw": raw_obs.get("danelfin_raw"),
                "sourced_date": raw_obs.get("sourced_date"),
                "operator_source": operator_source,
                "acquisition_method": acquisition_method,
            }
        )

    return {
        "dry_run": dry_run,
        "mode": "diagnostic" if dry_run else "production",
        "operator_source": operator_source,
        "acquisition_method": acquisition_method,
        "run_id": str(payload.get("run_id") or payload.get("diagnostic_run_id") or "").strip() or None,
        "diagnostic_run_id": str(payload.get("diagnostic_run_id") or "").strip() or None,
        "observations": normalized_observations,
    }


def _run_browser_capture(payload: dict[str, object]) -> dict[str, object]:
    import sys as _sys

    if str(_REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_REPO_ROOT))

    from src.scoring.danelfin_manual_import import import_manual_danelfin_observations, _normalize_observation

    normalized_payload = _normalize_browser_capture_payload(payload)
    run_mode = str(normalized_payload.get("mode") or "diagnostic").strip().lower()
    run_id = normalized_payload.get("run_id")

    if isinstance(run_id, str) and run_id:
        if run_mode == "production":
            _record_danelfin_production_event(run_id, "result_received")
        else:
            _record_danelfin_diag_event(run_id, "result_received")

    if bool(normalized_payload["dry_run"]):
        normalized_rows: list[dict[str, str]] = []
        requested_symbols = [str(obs["symbol"]).upper() for obs in normalized_payload["observations"]]
        for obs in normalized_payload["observations"]:
            normalized = _normalize_observation(obs)
            normalized_rows.append(
                {
                    "symbol": normalized.symbol,
                    "danelfin_raw": str(normalized.danelfin_raw),
                    "danelfin_score": f"{normalized.danelfin_raw / 2.0:.4f}",
                    "sourced_date": normalized.sourced_date,
                }
            )

        if isinstance(run_id, str) and run_id:
            if run_mode == "production":
                _record_danelfin_production_event(run_id, "normalized")
                _record_danelfin_production_event(run_id, "validation_passed")
            else:
                _record_danelfin_diag_event(run_id, "normalized")
                _record_danelfin_diag_event(run_id, "validation_passed")

        return {
            "status": "ok",
            "dry_run": True,
            "run_id": run_id,
            "diagnostic_run_id": run_id,
            "output_dir": None,
            "operator_source": normalized_payload["operator_source"],
            "acquisition_method": normalized_payload["acquisition_method"],
            "applied_count": len(normalized_rows),
            "skipped_count": 0,
            "applied_symbols": requested_symbols,
            "skipped": [],
            "captured_rows": normalized_rows,
            "latest_path": None,
            "provenance_path": None,
            "canonical_persistence_called": False,
        }

    # Production mode writes through the canonical Danelfin signal cache path.
    output_dir = _REPO_ROOT / "data" / "signals" / "danelfin"

    if isinstance(run_id, str) and run_id:
        if run_mode == "production":
            _record_danelfin_production_event(run_id, "normalized")
            _record_danelfin_production_event(run_id, "validation_passed")
        else:
            _record_danelfin_diag_event(run_id, "normalized")
            _record_danelfin_diag_event(run_id, "validation_passed")

    summary = import_manual_danelfin_observations(
        normalized_payload["observations"],
        output_dir=output_dir,
        operator_source=str(normalized_payload["operator_source"]),
        acquisition_method=str(normalized_payload["acquisition_method"]),
    )

    rows_by_symbol: dict[str, dict[str, str]] = {}
    latest_path = Path(summary["latest_path"])
    if latest_path.exists():
        with latest_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                sym = str(row.get("symbol") or "").strip().upper()
                if sym:
                    rows_by_symbol[sym] = row

    requested_symbols = [str(obs["symbol"]) for obs in normalized_payload["observations"]]
    captured_rows = [
        {
            "symbol": sym,
            "danelfin_raw": rows_by_symbol.get(sym, {}).get("danelfin_raw", ""),
            "danelfin_score": rows_by_symbol.get(sym, {}).get("danelfin_score", ""),
            "sourced_date": rows_by_symbol.get(sym, {}).get("sourced_date", ""),
        }
        for sym in requested_symbols
    ]

    return {
        "status": "ok",
        "dry_run": False,
        "run_id": run_id,
        "diagnostic_run_id": run_id,
        "output_dir": str(output_dir),
        "operator_source": normalized_payload["operator_source"],
        "acquisition_method": normalized_payload["acquisition_method"],
        "applied_count": int(summary.get("applied_count") or 0),
        "skipped_count": int(summary.get("skipped_count") or 0),
        "applied_symbols": summary.get("applied_symbols", []),
        "skipped": summary.get("skipped", []),
        "captured_rows": captured_rows,
        "latest_path": summary.get("latest_path"),
        "provenance_path": summary.get("provenance_path"),
        "canonical_persistence_called": True,
    }


def _resolve_refresh_intent(intent: str | None) -> str:
    raw = str(intent or "portfolio_signals").strip().lower()
    aliases = {
        "portfolio_signals": "portfolio_signals",
        "current_holdings": "portfolio_signals",
        "stale_only": "stale_only",
        "holdings_plus_buy_candidates": "holdings_plus_buy_candidates",
        "portfolio_plus_candidates": "holdings_plus_buy_candidates",
        "rebuild_research_universe": "rebuild_research_universe",
        "prepare_portfolio_review": "prepare_portfolio_review",
        "market_regime_proxy_only": "market_regime_proxy_only",
        "market_regime_proxy": "market_regime_proxy_only",
    }
    return aliases.get(raw, "")


def _allowed_refresh_intents() -> list[str]:
    return [
        "stale_only",
        "portfolio_signals",
        "holdings_plus_buy_candidates",
        "rebuild_research_universe",
        "prepare_portfolio_review",
        "market_regime_proxy_only",
    ]


def _refresh_scope_plan(intent: str) -> dict:
    if intent == "prepare_portfolio_review":
        return {
            "refresh_intent": intent,
            "scope_summary": {
                "portfolio_holdings_count": 0,
                "buy_candidate_count": 0,
                "mandatory_dependency_count": 0,
                "market_proxy_count": 0,
                "deduped_symbol_count": 0,
                "full_universe_count": int(_count_research_universe_rows() or 0),
            },
            "planned_symbol_samples": {
                "portfolio_holdings": [],
                "buy_candidates": [],
                "mandatory_dependencies": [],
                "market_proxies": [],
            },
            "planned_symbols": {
                "market_proxies": [],
                "provider_symbols": {"zacks": [], "danelfin": [], "yahoo": []},
            },
        }
    try:
        import sys as _sys

        if str(_REPO_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_REPO_ROOT))
        from scripts.refresh_signals import _build_refresh_scope

        return _build_refresh_scope(refresh_mode=intent)
    except Exception:
        return {
            "refresh_intent": intent,
            "scope_summary": {
                "portfolio_holdings_count": 0,
                "buy_candidate_count": 0,
                "mandatory_dependency_count": 0,
                "deduped_symbol_count": 0,
                "full_universe_count": int(_count_research_universe_rows() or 0),
            },
            "planned_symbol_samples": {
                "portfolio_holdings": [],
                "buy_candidates": [],
                "mandatory_dependencies": [],
            },
            "planned_symbols": {"provider_symbols": {"zacks": [], "danelfin": [], "yahoo": []}},
        }


def _refresh_scope_formula(scope_summary: dict | None, intent: str | None) -> str:
    summary = scope_summary or {}
    holdings = int(summary.get("portfolio_holdings_count") or 0)
    buy = int(summary.get("buy_candidate_count") or 0)
    deps = int(summary.get("mandatory_dependency_count") or 0)
    proxies = int(summary.get("market_proxy_count") or 0)
    deduped = int(summary.get("deduped_symbol_count") or 0)
    full_count = int(summary.get("full_universe_count") or 0)

    if intent == "rebuild_research_universe":
        if full_count > 0:
            return f"Planned refresh scope: ~{full_count:,} research universe symbols"
        return "Planned refresh scope: full research universe"
    if intent == "holdings_plus_buy_candidates":
        return (
            f"Planned refresh scope: {holdings} holdings + {buy} buy candidates + "
            f"{deps} required dependencies + {proxies} market proxies = {deduped} symbols"
        )
    if intent == "portfolio_signals":
        return (
            f"Planned refresh scope: {holdings} holdings + "
            f"{deps} required dependencies + {proxies} market proxies = {deduped} symbols"
        )
    if intent == "stale_only":
        return f"Planned refresh scope: stale provider rows + {proxies} stale market proxies"
    if intent == "market_regime_proxy_only":
        return f"Planned refresh scope: {proxies} market-regime proxy symbols only"
    return "Planned refresh scope: based on selected refresh intent"


def _pid_is_alive(pid_value: object) -> bool:
    try:
        pid = int(pid_value)
    except Exception:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _load_refresh_report_artifact() -> dict[str, object] | None:
    if not _REFRESH_REPORT_PATH.exists():
        return None
    try:
        raw = json.loads(_REFRESH_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _shared_runtime_state() -> dict[str, object] | None:
    artifact = _load_refresh_report_artifact()
    if not isinstance(artifact, dict):
        return None
    runtime = artifact.get("runtime_status")
    if not isinstance(runtime, dict):
        return None
    snapshot = copy.deepcopy(runtime)
    running = bool(snapshot.get("running"))
    if running and not _pid_is_alive(snapshot.get("pid")):
        snapshot["running"] = False
        if not snapshot.get("completed_at"):
            snapshot["completed_at"] = datetime.now(timezone.utc).isoformat()
        providers = snapshot.get("providers")
        if isinstance(providers, dict):
            for provider_info in providers.values():
                if not isinstance(provider_info, dict):
                    continue
                state = str(provider_info.get("state") or "").upper()
                if state in {"RUNNING", "QUEUED"}:
                    provider_info["state"] = "STALE"
                    if not provider_info.get("completed_at"):
                        provider_info["completed_at"] = snapshot.get("completed_at")
        snapshot["stale_pid"] = True
    return snapshot


def _refresh_status_payload(running: bool) -> dict:
    global _refresh_last_report, _refresh_last_exit_code, _refresh_completed_at_utc
    global _refresh_started_at_utc

    shared_artifact = _load_refresh_report_artifact() or {}
    shared_runtime = _shared_runtime_state()
    effective_running = bool(running)
    status_source = "process_local_state"
    if isinstance(shared_runtime, dict):
        effective_running = bool(shared_runtime.get("running"))
        status_source = "shared_runtime_artifact"

    if not effective_running and _refresh_proc is not None:
        exit_code = _refresh_proc.poll()
        if exit_code is not None:
            _refresh_last_exit_code = int(exit_code)
            _refresh_completed_at_utc = datetime.now(timezone.utc).isoformat()
            if _REFRESH_REPORT_PATH.exists():
                try:
                    _refresh_last_report = json.loads(_REFRESH_REPORT_PATH.read_text(encoding="utf-8"))
                except Exception:
                    _refresh_last_report = None

    if _refresh_last_report is None and isinstance(shared_artifact, dict):
        _refresh_last_report = {
            k: v for k, v in shared_artifact.items() if k != "runtime_status"
        }

    signal_data = _signal_status()
    provider_progress: dict[str, dict] = {}
    for provider in ("zacks", "danelfin", "yahoo"):
        info = signal_data.get(provider)
        if not isinstance(info, dict):
            continue
        completed = int(info.get("completed_count") or info.get("with_data_count") or 0)
        planned = _refresh_provider_planned_totals.get(provider)
        if planned is None and isinstance(info.get("planned_total_count"), int):
            planned = int(info.get("planned_total_count"))

        progress_pct = None
        progress_label = f"{completed} rows processed"
        is_complete = False
        if planned is not None:
            display_completed = min(completed, planned)
            progress_pct = round((display_completed / planned * 100.0), 1) if planned > 0 else 100.0
            progress_label = f"{display_completed}/{planned}"
            is_complete = completed >= planned

        provider_progress[provider] = {
            "completed_count": completed,
            "planned_total_count": planned,
            "progress_pct": progress_pct,
            "progress_label": progress_label,
            "is_complete": is_complete,
        }

    provider_order = ["zacks", "yahoo", "danelfin", "fmp"]
    provider_execution: dict[str, dict] = {}
    last_report_providers = {}
    if isinstance(_refresh_last_report, dict):
        maybe_providers = _refresh_last_report.get("providers")
        if isinstance(maybe_providers, dict):
            last_report_providers = maybe_providers

    for provider in provider_order:
        planned = _refresh_provider_planned_totals.get(provider)
        if planned is None and provider in provider_progress:
            planned = provider_progress[provider].get("planned_total_count")

        attempted_count = None
        success_count = None
        failed_count = None
        report_state = None

        info = signal_data.get(provider)
        if isinstance(info, dict):
            if info.get("attempted_count") is not None:
                attempted_count = int(info.get("attempted_count") or 0)
            if info.get("with_data_count") is not None:
                success_count = int(info.get("with_data_count") or 0)

        report = last_report_providers.get(provider)
        if isinstance(report, dict):
            if report.get("attempted_count") is not None:
                attempted_count = int(report.get("attempted_count") or 0)
            elif report.get("submitted_count") is not None:
                attempted_count = int(report.get("submitted_count") or 0)

            if report.get("primary_data_count") is not None:
                success_count = int(report.get("primary_data_count") or 0)

            if report.get("failed") is not None:
                failed_count = int(report.get("failed") or 0)

            report_state = str(report.get("state") or "").strip().upper() or None

        if provider in ("zacks", "danelfin", "yahoo") and attempted_count is not None and success_count is not None and failed_count is None:
            # Execution attempts can terminate without primary data; keep that separate from holdings coverage.
            failed_count = max(attempted_count - success_count, 0)

        provider_execution[provider] = {
            "provider": provider,
            "planned_count": planned,
            "attempted_count": attempted_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "state": "UNKNOWN",
            "started_at": _refresh_started_at_utc if effective_running else None,
            "completed_at": _refresh_completed_at_utc if not effective_running else None,
            "report_state": report_state,
        }

    for provider in provider_order:
        item = provider_execution[provider]
        report = last_report_providers.get(provider)
        report_triggered = isinstance(report, dict) and bool(report.get("triggered"))

        if not effective_running:
            if isinstance(report, dict):
                attempted = item.get("attempted_count")
                success = item.get("success_count")
                failed = item.get("failed_count")
                if failed is not None and failed > 0:
                    item["state"] = "FAILED"
                elif attempted is not None and attempted > 0 and success is not None and success < attempted:
                    item["state"] = "COMPLETE_WITH_ERRORS"
                elif attempted is not None and attempted > 0:
                    item["state"] = "COMPLETE"
                elif report_triggered:
                    item["state"] = "COMPLETE"
                else:
                    item["state"] = "SKIPPED"
            else:
                item["state"] = "UNKNOWN"
            continue

        # Running states: determine terminal by attempted/planned, not success-only progress.
        planned = item.get("planned_count")
        attempted = item.get("attempted_count")
        success = item.get("success_count")
        failed = item.get("failed_count")
        if planned is not None and attempted is not None and attempted >= int(planned):
            if failed is not None and failed > 0:
                item["state"] = "COMPLETE_WITH_ERRORS"
            elif success is not None and int(planned) > 0 and success < int(planned):
                item["state"] = "COMPLETE_WITH_ERRORS"
            else:
                item["state"] = "COMPLETE"
        else:
            item["state"] = "QUEUED"

    current_stage_provider = None
    if effective_running:
        for provider in ("zacks", "yahoo", "danelfin"):
            if provider_execution[provider].get("state") in {"COMPLETE", "COMPLETE_WITH_ERRORS", "FAILED", "SKIPPED"}:
                continue
            current_stage_provider = provider
            provider_execution[provider]["state"] = "RUNNING"
            break

        if current_stage_provider is None:
            # Core providers are terminal; while process is still alive, the tail stage is FMP.
            current_stage_provider = "fmp"
            provider_execution["fmp"]["state"] = "RUNNING"

        for provider in provider_order:
            if provider == current_stage_provider:
                continue
            if provider_execution[provider].get("state") == "QUEUED":
                continue
            # Keep terminal states intact.

    current_stage = f"provider_refresh_{current_stage_provider}" if current_stage_provider else ""
    current_stage_started_at = _refresh_started_at_utc if current_stage_provider else None

    if isinstance(shared_runtime, dict):
        providers = shared_runtime.get("providers")
        if isinstance(providers, dict):
            for provider in provider_order:
                shared_provider = providers.get(provider)
                if not isinstance(shared_provider, dict):
                    continue
                target = provider_execution.get(provider)
                if not isinstance(target, dict):
                    continue
                target["state"] = str(shared_provider.get("state") or target.get("state") or "UNKNOWN").upper()
                target["planned_count"] = shared_provider.get("planned", target.get("planned_count"))
                target["attempted_count"] = shared_provider.get("attempted", target.get("attempted_count"))
                target["success_count"] = shared_provider.get("success", target.get("success_count"))
                target["failed_count"] = shared_provider.get("failed", target.get("failed_count"))
                target["started_at"] = shared_provider.get("started_at", target.get("started_at"))
                target["completed_at"] = shared_provider.get("completed_at", target.get("completed_at"))

        shared_stage_provider = str(shared_runtime.get("current_stage_provider") or "").strip().lower()
        if shared_stage_provider in provider_order:
            current_stage_provider = shared_stage_provider
            current_stage = f"provider_refresh_{shared_stage_provider}"
            current_stage_started_at = str((providers.get(shared_stage_provider) or {}).get("started_at") or "") if isinstance(providers, dict) else None
        elif not bool(shared_runtime.get("running")):
            current_stage_provider = None
            current_stage = ""
            current_stage_started_at = None

        if _refresh_started_at_utc is None:
            _refresh_started_at_utc = str(shared_runtime.get("started_at") or "") or None
        if not effective_running and _refresh_completed_at_utc is None:
            _refresh_completed_at_utc = str(shared_runtime.get("completed_at") or "") or None

    scope_formula = _refresh_scope_formula(_refresh_scope_summary if isinstance(_refresh_scope_summary, dict) else {}, _refresh_resolved_intent)
    replay_publish = None
    dedicated_proxy_history = None
    dedicated_proxy_build = None
    if isinstance(_refresh_last_report, dict):
        replay_publish = _refresh_last_report.get("market_proxy_replay_publish")
        dedicated_proxy_history = _refresh_last_report.get("market_regime_proxy_history_fetch")
        dedicated_proxy_build = _refresh_last_report.get("market_regime_proxy_artifact_build")
    return {
        "running": effective_running,
        "last_report": _refresh_last_report,
        "market_proxy_replay_publish": replay_publish,
        "market_regime_proxy_history_fetch": dedicated_proxy_history,
        "market_regime_proxy_artifact_build": dedicated_proxy_build,
        "last_exit_code": _refresh_last_exit_code,
        "requested_intent": _refresh_requested_intent,
        "resolved_intent": _refresh_resolved_intent,
        "scope_summary": _refresh_scope_summary or {},
        "planned_symbol_samples": _refresh_scope_samples or {},
        "scope_formula": scope_formula,
        "provider_progress": provider_progress,
        "provider_execution": provider_execution,
        "current_stage": current_stage,
        "current_stage_provider": current_stage_provider,
        "current_stage_started_at": current_stage_started_at,
        "started_at_utc": _refresh_started_at_utc,
        "completed_at_utc": _refresh_completed_at_utc,
        "status_source": status_source,
        "stale_pid_detected": bool(shared_runtime.get("stale_pid")) if isinstance(shared_runtime, dict) else False,
    }


def _sourced_date(csv_path: Path) -> str | None:
    """Return the maximum sourced_date value found in csv_path, or None.

    Reads all rows and returns the latest date rather than the first to guard
    against unsorted files where an older row appears before newer data.
    """
    if not csv_path.exists():
        return None
    try:
        latest: str | None = None
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                val = str(row.get("sourced_date", "")).strip()
                if val and (latest is None or val > latest):
                    latest = val
        return latest
    except Exception:
        pass
    return None


def _iso_age_days(value: str | None, *, today: date | None = None) -> int | None:
    if not value:
        return None
    today = today or date.today()
    try:
        sourced = datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None
    return (today - sourced).days


def _count_research_universe_rows() -> int | None:
    csv_path = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
    if not csv_path.exists():
        return None
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            return sum(1 for _ in csv.DictReader(fh))
    except Exception:
        return None


def _latest_snapshot_date(csv_path: Path) -> str | None:
    """Return the maximum snapshot_date value found in csv_path, or None."""
    if not csv_path.exists():
        return None
    try:
        latest: str | None = None
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                val = str(row.get("snapshot_date", "")).strip()
                if val and (latest is None or val > latest):
                    latest = val
        return latest
    except Exception:
        return None


def _load_ess_coverage_warning() -> dict:
    if not _ESS_COVERAGE_WARNING.exists():
        return {"warning_count": 0, "example_symbols": [], "summary_message": "", "status": "UNKNOWN"}
    try:
        return json.loads(_ESS_COVERAGE_WARNING.read_text(encoding="utf-8"))
    except Exception:
        return {"warning_count": 0, "example_symbols": [], "summary_message": "", "status": "ERROR"}


def _latest_ess_symbol_semantics() -> tuple[str | None, dict[str, dict[str, object]]]:
    """Return latest ESS snapshot date and per-symbol row/score availability."""
    latest_date = _latest_snapshot_date(_ESS_SIGNAL_SNAPSHOT)
    if not latest_date or not _ESS_SIGNAL_SNAPSHOT.exists():
        return None, {}

    symbol_map: dict[str, dict[str, object]] = {}
    try:
        with _ESS_SIGNAL_SNAPSHOT.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                row_date = str(row.get("snapshot_date") or "").strip()
                if row_date != latest_date:
                    continue
                symbol = str(row.get("symbol") or "").strip().upper()
                if not symbol:
                    continue

                coverage_domain = str(row.get("coverage_domain") or "").strip().upper()
                ess_text = str(row.get("starmine_ess_text") or "").strip()
                ess_numeric = str(row.get("starmine_ess_numeric") or "").strip()
                score_present = coverage_domain == "STARMINE_COVERED" and bool(ess_text or ess_numeric)

                prior = symbol_map.get(symbol)
                symbol_map[symbol] = {
                    "row_present": True,
                    "score_present": bool(score_present or (prior and prior.get("score_present"))),
                    "source_date": latest_date,
                }
    except Exception:
        return latest_date, {}

    return latest_date, symbol_map


def _statement_gain_loss_latest_payload() -> tuple[dict, int]:
    """Return latest statement gain/loss artifact payload with graceful fallback."""
    artifacts_dir = _REPO_ROOT / "artifacts" / "statement_gain_loss"
    latest_pointer = artifacts_dir / "latest.json"
    history_index = artifacts_dir / "history" / "statement_gain_loss_index.json"

    def _unavailable(reason: str, message: str, warnings: list[str]) -> tuple[dict, int]:
        return {
            "status": "unavailable",
            "reason": reason,
            "message": message,
            "statement_date": None,
            "statement_period": {"start": None, "end": None},
            "portfolio_ytd_change_in_investment_value": None,
            "accounts": [],
            "combined_realized_net_gain_loss_ytd": None,
            "warnings": warnings,
            "scoring_impact": "none",
        }, 200

    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_available(payload: dict) -> tuple[dict, int]:
        statement_period = payload.get("statement_period") or {}
        portfolio_summary = payload.get("portfolio_summary") or {}
        accounts = payload.get("accounts") or []
        derived_totals = payload.get("derived_totals") or {}
        source_provenance = payload.get("source_provenance") or []
        provenance_kinds = sorted(
            {
                str(item.get("source_provenance", "")).strip()
                for item in source_provenance
                if str(item.get("source_provenance", "")).strip()
            }
        )

        response_accounts = []
        for item in accounts:
            response_accounts.append(
                {
                    "account_number": item.get("account_number"),
                    "realized_net_gain_loss_ytd": item.get("realized_net_gain_loss_ytd"),
                    "change_in_investment_value_ytd": item.get("change_in_investment_value_ytd"),
                    "ending_value": item.get("ending_value"),
                }
            )

        return {
            "status": "available",
            "statement_date": payload.get("statement_date"),
            "statement_period": {
                "start": statement_period.get("start"),
                "end": statement_period.get("end"),
            },
            "portfolio_ytd_change_in_investment_value": portfolio_summary.get("change_in_investment_value_ytd"),
            "accounts": response_accounts,
            "combined_realized_net_gain_loss_ytd": derived_totals.get(
                "combined_realized_net_gain_loss_ytd_all_accounts"
            ),
            "source_provenance": source_provenance,
            "source_provenance_summary": {
                "source_count": len(source_provenance),
                "provenance_types": provenance_kinds,
            },
            "warnings": payload.get("warnings") or [
                "Main portfolio statement aggregates X20 and Z35. Joint account Z26 is separate and must not be double counted unless explicitly included.",
            ],
            "scoring_impact": "none",
        }, 200

    if not artifacts_dir.exists():
        return _unavailable(
            "artifact_directory_missing",
            "Statement gain/loss artifact directory does not exist.",
            [
                "No statement artifact found.",
                "Main portfolio statement aggregates X20 and Z35. Joint account Z26 is separate and must not be double counted unless explicitly included.",
            ],
        )

    candidate_path: Path | None = None
    payload_from_pointer: dict | None = None

    if latest_pointer.exists():
        try:
            payload_from_pointer = _read_json(latest_pointer)
        except Exception as exc:
            return _unavailable(
                "artifact_invalid",
                f"Failed to parse latest pointer artifact: {exc}",
                [
                    "Statement latest pointer exists but is unreadable.",
                    "Main portfolio statement aggregates X20 and Z35. Joint account Z26 is separate and must not be double counted unless explicitly included.",
                ],
            )

    if payload_from_pointer is None and history_index.exists():
        try:
            history_payload = _read_json(history_index)
        except Exception as exc:
            return _unavailable(
                "history_index_invalid",
                f"Failed to parse statement history index: {exc}",
                [
                    "Statement history index exists but is unreadable.",
                    "Main portfolio statement aggregates X20 and Z35. Joint account Z26 is separate and must not be double counted unless explicitly included.",
                ],
            )
        entries = history_payload.get("entries") or []
        if entries:
            latest_entry = sorted(entries, key=lambda e: str(e.get("statement_date") or ""))[-1]
            resolved = Path(str(latest_entry.get("json_artifact_path") or ""))
            if not resolved.is_absolute():
                resolved = _REPO_ROOT / resolved
            candidate_path = resolved

    if payload_from_pointer is None and candidate_path is None:
        dated_candidates = sorted(artifacts_dir.glob("*/STATEMENT_GAIN_LOSS_*.json"), reverse=True)
        if dated_candidates:
            candidate_path = dated_candidates[0]
        else:
            flat_candidates = sorted(artifacts_dir.glob("STATEMENT_GAIN_LOSS_*.json"), reverse=True)
            if flat_candidates:
                candidate_path = flat_candidates[0]

    if payload_from_pointer is None:
        if candidate_path is None:
            return _unavailable(
                "artifact_missing",
                "No statement gain/loss JSON artifacts found.",
                [
                    "No statement artifact found.",
                    "Main portfolio statement aggregates X20 and Z35. Joint account Z26 is separate and must not be double counted unless explicitly included.",
                ],
            )
        if not candidate_path.exists():
            return _unavailable(
                "artifact_missing",
                f"Statement artifact referenced by history was not found: {candidate_path}",
                [
                    "History index referenced a missing statement artifact.",
                    "Main portfolio statement aggregates X20 and Z35. Joint account Z26 is separate and must not be double counted unless explicitly included.",
                ],
            )
        try:
            payload_from_pointer = _read_json(candidate_path)
        except Exception as exc:
            return _unavailable(
                "artifact_invalid",
                f"Failed to parse statement artifact: {exc}",
                [
                    "Statement artifact exists but is unreadable.",
                    "Main portfolio statement aggregates X20 and Z35. Joint account Z26 is separate and must not be double counted unless explicitly included.",
                ],
            )

    return _build_available(payload_from_pointer)


def _market_regime_guardrail_payload(run_id: str | None = None) -> tuple[dict, int]:
    """Return display-only market regime guardrail payload with safe fallback."""
    try:
        import sys as _sys

        if str(_REPO_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_REPO_ROOT))
        from src.portfolio.regime.market_regime_guardrail import market_regime_guardrail_latest

        payload = market_regime_guardrail_latest(_REPO_ROOT, run_id=run_id or "")
        if not isinstance(payload, dict):
            raise ValueError("invalid market regime payload")
        payload["scoring_impact"] = "none"
        return payload, 200
    except Exception as exc:
        return {
            "regime": "UNKNOWN",
            "severity": "LOW",
            "deployment_posture": "CAUTION_DEPLOY",
            "trim_posture": "REVIEW_OVERWEIGHTS",
            "cash_posture": "HOLD_EXCESS",
            "operator_summary": "Market regime guardrail unavailable. Use conservative display-only posture.",
            "evidence": [f"guardrail_endpoint_error: {exc}"],
            "affected_symbols": [],
            "stressed_sectors": [],
            "safe_to_deploy": False,
            "confidence": "LOW",
            "data_freshness": {
                "market_proxies_ts": None,
                "portfolio_snapshot_ts": None,
                "freshness_status": "UNKNOWN",
                "market_proxy_age_days": None,
                "proxy_lag_days": None,
                "freshness_threshold_days": 2,
                "operator_action": "VERIFY_TIMESTAMP_FORMATS",
            },
            "guardrail_version": "MRG-1.0",
            "recommended_operator_checks": [
                "Confirm proxy freshness before changing posture.",
                "Use conservative deployment discipline until data recovers.",
            ],
            "scoring_impact": "none",
        }, 200


def _persist_fetched_scores(symbol: str, zacks_result: dict, danelfin_result: dict) -> None:
    """Persist freshly-fetched scores into the signal files and analytical_universe.csv.

    Updates latest_zacks.csv (upsert by symbol) and patches the matching row(s)
    in analytical_universe.csv so that subsequent portfolio analyses see the new data
    without requiring a full universe rebuild.
    """
    today = date.today().isoformat()
    zacks_score = zacks_result.get("score") if not zacks_result.get("error") else None
    danelfin_score_val = danelfin_result.get("score") if not danelfin_result.get("error") else None

    # --- 1. Upsert latest_zacks.csv ---
    if zacks_score is not None:
        zacks_path = _SIGNAL_FILES["zacks"]
        zacks_path.parent.mkdir(parents=True, exist_ok=True)
        _OUTPUT_HEADERS = ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"]
        existing_rows: list[dict] = []
        if zacks_path.exists():
            with zacks_path.open("r", encoding="utf-8", newline="") as fh:
                existing_rows = list(csv.DictReader(fh))
        # Remove any existing row for this symbol, add fresh row at top
        existing_rows = [r for r in existing_rows if str(r.get("symbol", "")).strip().upper() != symbol]
        rank = zacks_result.get("rank")
        new_row = {
            "symbol": symbol,
            "zacks_rank": str(rank) if rank is not None else "",
            "zacks_score": str(zacks_score),
            "abr": str(zacks_result.get("abr") or ""),
            "price_target": str(zacks_result.get("price_target") or ""),
            "eps_growth": str(zacks_result.get("eps_growth") or ""),
            "sourced_date": today,
        }
        with zacks_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_OUTPUT_HEADERS)
            writer.writeheader()
            writer.writerow(new_row)
            writer.writerows(existing_rows)

    # --- 2. Patch analytical_universe.csv ---
    sys.path.insert(0, str(_REPO_ROOT))
    try:
        from src.history.analytical_universe_manager import _score_from_inputs  # type: ignore[attr-defined]
    except Exception:
        return  # best-effort only

    universe_path = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
    if not universe_path.exists():
        return

    with universe_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []
        rows = list(reader)

    changed = False
    for row in rows:
        if str(row.get("symbol", "")).strip().upper() != symbol:
            continue
        if zacks_score is not None:
            row["zacks_rating"] = str(zacks_score)
        if danelfin_score_val is not None:
            row["danelfin_score"] = str(danelfin_score_val)
        # Recalculate composite_score with updated inputs
        row["composite_score"] = str(_score_from_inputs(
            ess_score_text=row.get("ess_score_text", ""),
            zacks_rating=row.get("zacks_rating", ""),
            ess_zacks_rating="",
            yahoo_score=row.get("yahoo_score", ""),
            danelfin_score=row.get("danelfin_score", ""),
        ))
        changed = True

    if changed:
        with universe_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)


def _do_fetch_scores(symbol: str) -> None:
    """Fetch live scores for *symbol* from all three providers concurrently.

    Results are stored in _fetch_jobs[symbol] and status transitions from
    'pending' → 'done' (or 'error').  Fetched scores are also persisted to
    the signal files and analytical_universe.csv so portfolio analysis sees them.
    """
    sys.path.insert(0, str(_REPO_ROOT))
    from src.scoring.fetch_zacks_scores import fetch_zacks_data
    from src.scoring.fetch_danelfin_scores import fetch_danelfin_score
    from src.scoring.fetch_yahoo_supplemental import fetch_yahoo_supplemental

    def _zacks():
        try:
            rank, score, abr, price_target, eps_growth = fetch_zacks_data(
                symbol, delay_min=0, delay_max=0
            )
            return {"rank": rank, "score": score, "abr": abr,
                    "price_target": price_target, "eps_growth": eps_growth}
        except Exception as exc:
            return {"error": str(exc)}

    def _danelfin():
        try:
            raw, score = fetch_danelfin_score(symbol)
            return {"raw": raw, "score": score}
        except Exception as exc:
            return {"error": str(exc)}

    def _yahoo():
        try:
            return fetch_yahoo_supplemental(symbol)
        except Exception as exc:
            return {"error": str(exc)}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            fz = ex.submit(_zacks)
            fd = ex.submit(_danelfin)
            fy = ex.submit(_yahoo)
            zacks_result    = fz.result(timeout=60)
            danelfin_result = fd.result(timeout=60)
            yahoo_result    = fy.result(timeout=60)

        _persist_fetched_scores(symbol, zacks_result, danelfin_result)

        with _fetch_lock:
            _fetch_jobs[symbol] = {
                "status": "done",
                "symbol": symbol,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "zacks": zacks_result,
                "danelfin": danelfin_result,
                "yahoo": yahoo_result,
            }
    except Exception as exc:
        with _fetch_lock:
            _fetch_jobs[symbol] = {
                "status": "error",
                "symbol": symbol,
                "error": str(exc),
            }


def _signal_status() -> dict:
    today = date.today().isoformat()
    freshness_threshold_days = 2
    result: dict[str, dict] = {}
    resolved_signal_files: dict[str, Path] = {}
    for name in _SIGNAL_FILES.keys():
        resolved_signal_files[name] = _resolve_provider_signal_file(name)

    for name, path in resolved_signal_files.items():
        sd = _sourced_date(path)
        entry: dict = {
            "sourced_date": sd,
            "stale": True,
            "exists": path.exists(),
            "source_path": str(path),
        }
        age_days = _iso_age_days(sd)
        entry["age_days"] = age_days
        entry["threshold_days"] = freshness_threshold_days

        # Provider row-level coverage metrics for current sourced_date.
        _PRIMARY_FIELDS: dict[str, list[str]] = {
            "zacks": ["zacks_rank", "zacks_score"],
            "danelfin": ["danelfin_raw", "danelfin_score"],
            "yahoo": ["price_target", "analyst_count", "current_price"],
        }
        _ALL_SCORE_FIELDS: dict[str, list[str]] = {
            "zacks": ["zacks_rank", "zacks_score", "abr", "price_target", "eps_growth"],
            "danelfin": ["danelfin_raw", "danelfin_score"],
            "yahoo": ["price_target", "abr", "analyst_count", "current_price", "upside_pct", "eps_growth_5yr"],
        }
        primary_fields = _PRIMARY_FIELDS.get(name, [])
        all_fields = _ALL_SCORE_FIELDS.get(name, [])

        if path.exists() and sd:
            try:
                source_rows: list[dict] = []
                with path.open("r", encoding="utf-8", newline="") as fh:
                    for row in csv.DictReader(fh):
                        if str(row.get("sourced_date", "")).strip() == sd:
                            source_rows.append(row)
                attempted = len(source_rows)
                with_data = sum(
                    1 for r in source_rows if any(r.get(f, "").strip() for f in primary_fields)
                ) if primary_fields else attempted
                coverage_pct = round(with_data / attempted * 100, 1) if attempted else 0.0
                field_coverage: dict[str, float] = {}
                for field in all_fields:
                    n = sum(1 for r in source_rows if r.get(field, "").strip())
                    field_coverage[field] = round(n / attempted * 100, 1) if attempted else 0.0
                degraded = [f for f in primary_fields if field_coverage.get(f, 100) == 0.0]
                zero_fields = [f for f in all_fields if field_coverage.get(f, 100) == 0.0]

                entry["attempted_count"] = attempted
                entry["with_data_count"] = with_data
                entry["coverage_pct"] = coverage_pct
                entry["primary_field_coverage"] = {f: field_coverage[f] for f in primary_fields}
                entry["degraded_fields"] = degraded
                entry["zero_coverage_fields"] = zero_fields
                is_within_threshold = age_days is not None and age_days <= freshness_threshold_days
                entry["stale"] = not is_within_threshold
                if is_within_threshold:
                    entry["badge_state"] = "FRESH_PARTIAL" if coverage_pct < 95.0 or degraded else "FRESH"
                else:
                    entry["badge_state"] = "STALE"
            except Exception:
                entry["stale"] = False if age_days is not None and age_days <= freshness_threshold_days else True
                entry["badge_state"] = "FRESH" if entry["stale"] is False else "STALE"
        elif sd:
            entry["stale"] = False if age_days is not None and age_days <= freshness_threshold_days else True
            entry["badge_state"] = "FRESH" if entry["stale"] is False else "STALE"
        else:
            entry["stale"] = True
            entry["badge_state"] = "STALE"

        result[name] = entry

    try:
        if str(_REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(_REPO_ROOT))
        from src.portfolio.holdings_coverage import load_active_holdings_baseline, summarize_holdings_coverage

        # Evaluate provider coverage relative to the active portfolio run snapshot date,
        # so current-holdings freshness reflects canonical run context, not wall-clock drift.
        holdings_reference_date = date.today()
        analysis_runs_root = _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs"
        baseline = load_active_holdings_baseline(analysis_runs_root)
        if baseline is not None:
            run_metadata_path = analysis_runs_root / baseline.run_id / "run_metadata.json"
            if run_metadata_path.exists():
                try:
                    run_metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
                    snapshot_date_raw = str(run_metadata.get("snapshot_date") or "").strip()
                    snapshot_date = datetime.strptime(snapshot_date_raw, "%Y-%m-%d").date() if snapshot_date_raw else None
                    if snapshot_date is not None:
                        holdings_reference_date = snapshot_date
                except Exception:
                    pass

        holdings_providers: dict[str, dict] = {}
        holdings_run_id: str | None = None
        holdings_baseline = 0
        for provider_name in ("zacks", "danelfin", "yahoo"):
            summary = summarize_holdings_coverage(
                provider=provider_name,
                latest_csv=resolved_signal_files[provider_name],
                analysis_runs_root=analysis_runs_root,
                base_universe_csv=_REPO_ROOT / "data" / "current" / "base_equity_universe.csv",
                threshold_days=2,
                today=holdings_reference_date,
            )
            holdings_run_id = holdings_run_id or str(summary.get("run_id") or "") or None
            holdings_baseline = max(holdings_baseline, int(summary.get("active_holdings_baseline") or 0))
            holdings_providers[provider_name] = summary
            if provider_name in result:
                result[provider_name]["source_path"] = str(resolved_signal_files[provider_name])
                result[provider_name]["holdings_status"] = summary.get("status")
                result[provider_name]["holdings_applicable"] = summary.get("applicable_holdings")
                result[provider_name]["holdings_covered_today"] = summary.get("covered_today")
                result[provider_name]["holdings_stale"] = summary.get("stale")
                result[provider_name]["holdings_missing"] = summary.get("missing")
                result[provider_name]["holdings_failed"] = summary.get("failed")

                completed_count = int(result[provider_name].get("with_data_count") or 0)
                applicable_holdings = summary.get("applicable_holdings")
                planned_total_count = (
                    int(applicable_holdings)
                    if applicable_holdings is not None and int(applicable_holdings) >= 0
                    else None
                )
                progress_pct = None
                progress_label = f"{completed_count} rows processed"
                is_complete = False
                if planned_total_count is not None:
                    progress_completed = min(completed_count, planned_total_count)
                    if planned_total_count > 0:
                        progress_pct = round(progress_completed / planned_total_count * 100.0, 1)
                    else:
                        progress_pct = 100.0
                    progress_label = f"{progress_completed}/{planned_total_count}"
                    is_complete = completed_count >= planned_total_count

                result[provider_name]["completed_count"] = completed_count
                result[provider_name]["planned_total_count"] = planned_total_count
                result[provider_name]["progress_pct"] = progress_pct
                result[provider_name]["progress_label"] = progress_label
                result[provider_name]["is_complete"] = is_complete

        result["portfolio_holdings_coverage"] = {
            "run_id": holdings_run_id,
            "active_holdings_baseline": holdings_baseline,
            "threshold_days": 2,
            "providers": holdings_providers,
        }
    except Exception:
        result["portfolio_holdings_coverage"] = {
            "run_id": None,
            "active_holdings_baseline": 0,
            "threshold_days": 2,
            "providers": {},
        }

    for provider_name in ("zacks", "danelfin", "yahoo"):
        provider_entry = result.get(provider_name)
        if not isinstance(provider_entry, dict):
            continue
        if "completed_count" in provider_entry:
            continue
        completed_count = int(provider_entry.get("with_data_count") or 0)
        provider_entry["completed_count"] = completed_count
        provider_entry["planned_total_count"] = None
        provider_entry["progress_pct"] = None
        provider_entry["progress_label"] = f"{completed_count} rows processed"
        provider_entry["is_complete"] = False

    ess_sd = _latest_snapshot_date(_ESS_SIGNAL_SNAPSHOT)
    ess_gap = _load_ess_coverage_warning()
    ess_count = int(ess_gap.get("warning_count") or 0)
    ess_entry: dict = {
        "sourced_date": ess_sd,
        "stale": ess_sd != today,
        "exists": _ESS_SIGNAL_SNAPSHOT.exists(),
        "coverage_warning_count": ess_count,
        "coverage_warning_examples": list(ess_gap.get("example_symbols") or []),
        "coverage_true_missing_count": int(ess_gap.get("true_missing_count") or 0),
        "coverage_stale_count": int(ess_gap.get("stale_coverage_count") or 0),
        "coverage_no_fresh_starmine_count": int(ess_gap.get("no_fresh_starmine_count") or 0),
        "coverage_warning_message": str(ess_gap.get("summary_message") or ""),
    }
    if ess_sd == today and ess_count > 0:
        ess_entry["badge_state"] = "FRESH_PARTIAL"
    elif ess_sd == today:
        ess_entry["badge_state"] = "FRESH"
    elif ess_sd:
        ess_entry["badge_state"] = "STALE"
    else:
        ess_entry["badge_state"] = "UNKNOWN"
    result["ess"] = ess_entry
    return result

def _readiness_status_from_pct(core_fresh_pct: float) -> str:
    if core_fresh_pct >= 95.0:
        return "HIGH"
    if core_fresh_pct >= 80.0:
        return "MEDIUM"
    return "LOW"

def _provider_cell(provider_data: dict[str, object], provider_name: str) -> dict[str, str]:
    sourced_date = str(provider_data.get("sourced_date") or "")
    badge_state = str(provider_data.get("badge_state") or "")
    holdings_status = str(provider_data.get("holdings_status") or "")
    state = "missing"
    if provider_name == "ess":
        if badge_state in {"FRESH", "FRESH_PARTIAL"}:
            state = "fresh"
        elif badge_state == "STALE" or sourced_date:
            state = "stale"
    elif badge_state in {"FRESH", "FRESH_PARTIAL"} and holdings_status == "COMPLIANT":
        state = "fresh"
    elif sourced_date:
        state = "stale"
    return {
        "provider": provider_name,
        "state": state,
        "date": sourced_date or "NA",
    }


def _ess_cell_for_symbol(
    *,
    symbol: str,
    ess_provider_data: dict[str, object],
    ess_latest_snapshot_date: str | None,
    ess_symbol_semantics: dict[str, dict[str, object]],
    true_missing_symbols: set[str],
) -> dict[str, str]:
    """Return symbol-level ESS cell semantics independent from provider freshness badge."""
    default_cell = _provider_cell(ess_provider_data, "ess")

    if not ess_symbol_semantics and not true_missing_symbols:
        return default_cell

    snapshot_date = ess_latest_snapshot_date or str(default_cell.get("date") or "")
    today = date.today().isoformat()
    sem = ess_symbol_semantics.get(symbol)

    if sem and bool(sem.get("row_present")):
        if bool(sem.get("score_present")):
            state = "fresh" if snapshot_date == today else "stale"
            return {
                "provider": "ess",
                "state": state,
                "date": snapshot_date or "NA",
            }
        return {
            "provider": "ess",
            "state": "no_starmine_score",
            "date": snapshot_date or "NA",
        }

    if symbol in true_missing_symbols:
        return {
            "provider": "ess",
            "state": "missing",
            "date": snapshot_date or "NA",
        }

    return default_cell

def _refresh_transparency_payload() -> dict[str, object]:
    signal_data = _signal_status()

    report = _refresh_last_report if isinstance(_refresh_last_report, dict) else None
    if report is None and _REFRESH_REPORT_PATH.exists():
        try:
            report = json.loads(_REFRESH_REPORT_PATH.read_text(encoding="utf-8"))
        except Exception:
            report = None

    providers = report.get("providers") if isinstance(report, dict) else None
    if not isinstance(providers, dict):
        providers = {}

    provider_metrics: dict[str, dict[str, int]] = {}
    warnings: list[str] = []
    for provider in ("zacks", "danelfin", "yahoo"):
        info = providers.get(provider)
        if not isinstance(info, dict):
            provider_metrics[provider] = {
                "submitted": 0,
                "written": 0,
                "written_refresh_date": 0,
                "primary_data": 0,
                "no_coverage": 0,
                "no_score": 0,
                "stale_carryover": 0,
                "true_error": 0,
                "missing_written": 0,
                "failed": 0,
            }
            continue
        provider_metrics[provider] = {
            "submitted": int(info.get("submitted_count") or info.get("submitted") or 0),
            "written": int(info.get("written_count") or 0),
            "written_refresh_date": int(info.get("written_refresh_date_count") or info.get("refreshed") or 0),
            "primary_data": int(info.get("primary_data_count") or 0),
            "no_coverage": int(info.get("no_coverage_count") or 0),
            "no_score": int(info.get("no_score_count") or 0),
            "stale_carryover": int(info.get("stale_carryover_count") or 0),
            "true_error": int(info.get("true_error_count") or info.get("failed") or 0),
            "missing_written": int(info.get("missing_written_count") or 0),
            "failed": int(info.get("failed") or 0),
        }
        if provider_metrics[provider]["stale_carryover"] > 0:
            warnings.append(f"{provider}: stale carryover rows detected")
        if provider_metrics[provider]["missing_written"] > 0:
            warnings.append(f"{provider}: missing writes detected")

    research_total = _count_research_universe_rows()
    if research_total is None or research_total <= 0:
        research_total = max(
            int((signal_data.get("zacks") or {}).get("attempted_count") or 0),
            int((signal_data.get("danelfin") or {}).get("attempted_count") or 0),
            int((signal_data.get("yahoo") or {}).get("attempted_count") or 0),
            0,
        )

    zacks_fresh = int((signal_data.get("zacks") or {}).get("with_data_count") or 0)
    danelfin_fresh = int((signal_data.get("danelfin") or {}).get("with_data_count") or 0)
    yahoo_fresh = int((signal_data.get("yahoo") or {}).get("with_data_count") or 0)
    provider_fresh_counts = [n for n in (zacks_fresh, danelfin_fresh, yahoo_fresh) if n > 0]
    core_fresh = min(provider_fresh_counts) if provider_fresh_counts else 0
    stale_or_missing = max(research_total - core_fresh, 0)
    core_fresh_pct = round((core_fresh / research_total * 100.0), 1) if research_total > 0 else 0.0
    readiness_status = _readiness_status_from_pct(core_fresh_pct)

    readiness_block = {
        "core_fresh_pct": core_fresh_pct,
        "core_fresh": core_fresh,
        "total": research_total,
        "stale_or_missing": stale_or_missing,
        "status": readiness_status,
    }
    readiness = {
        "research_universe": dict(readiness_block),
        "cw_das": dict(readiness_block),
        "ucf": dict(readiness_block),
        "recommendations": dict(readiness_block),
        "cra": dict(readiness_block),
    }

    holdings_providers = ((signal_data.get("portfolio_holdings_coverage") or {}).get("providers") or {})
    ess_provider_data = signal_data.get("ess") if isinstance(signal_data.get("ess"), dict) else {}
    ess_gap = _load_ess_coverage_warning()
    true_missing_symbols = {
        str(s).strip().upper()
        for s in (ess_gap.get("true_missing_symbols") or [])
        if str(s).strip()
    }
    ess_latest_snapshot_date, ess_symbol_semantics = _latest_ess_symbol_semantics()

    symbols: set[str] = set()
    provider_symbol_maps: dict[str, dict[str, object]] = {}
    for provider in ("zacks", "danelfin", "yahoo"):
        p_summary = holdings_providers.get(provider) if isinstance(holdings_providers, dict) else {}
        p_symbols = p_summary.get("symbols") if isinstance(p_summary, dict) else {}
        if not isinstance(p_symbols, dict):
            p_symbols = {}
        provider_symbol_maps[provider] = p_symbols
        for symbol, info in p_symbols.items():
            if isinstance(info, dict) and info.get("applicable"):
                symbols.add(str(symbol).strip().upper())

    rows: list[dict[str, object]] = []
    for symbol in sorted(s for s in symbols if s):
        row = {
            "symbol": symbol,
            "zacks": _provider_cell(signal_data.get("zacks") if isinstance(signal_data.get("zacks"), dict) else {}, "zacks"),
            "danelfin": _provider_cell(signal_data.get("danelfin") if isinstance(signal_data.get("danelfin"), dict) else {}, "danelfin"),
            "yahoo": _provider_cell(signal_data.get("yahoo") if isinstance(signal_data.get("yahoo"), dict) else {}, "yahoo"),
            "ess": _ess_cell_for_symbol(
                symbol=symbol,
                ess_provider_data=ess_provider_data,
                ess_latest_snapshot_date=ess_latest_snapshot_date,
                ess_symbol_semantics=ess_symbol_semantics,
                true_missing_symbols=true_missing_symbols,
            ),
            "fmp": {"provider": "fmp", "state": "missing", "date": "NA"},
            "sources": {
                "cw_das": True,
                "ucf": True,
                "recommendations": True,
                "cra": True,
            },
            "freshness": "FRESH",
        }
        for provider in ("zacks", "danelfin", "yahoo"):
            info = provider_symbol_maps[provider].get(symbol)
            if not isinstance(info, dict):
                continue
            cls = str(info.get("classification") or "").upper()
            if cls in {"STALE", "MISSING", "FAILED"}:
                row["freshness"] = "STALE"
                break
        rows.append(row)

    total_failed = sum(int(v.get("failed") or 0) for v in provider_metrics.values())
    decision_readiness = {
        "classification": readiness_status,
        "core_fresh_pct": core_fresh_pct,
        "stale_or_missing": stale_or_missing,
        "has_provider_failures": total_failed > 0,
    }

    latest_refresh_date = ""
    if isinstance(report, dict):
        latest_refresh_date = str(report.get("refresh_date") or report.get("report_date") or "")
    if not latest_refresh_date:
        latest_refresh_date = str(
            max(
                str((signal_data.get("zacks") or {}).get("sourced_date") or ""),
                str((signal_data.get("danelfin") or {}).get("sourced_date") or ""),
                str((signal_data.get("yahoo") or {}).get("sourced_date") or ""),
            )
        )

    overall_status = "READY" if readiness_status == "HIGH" and total_failed == 0 else "WARNINGS"
    if total_failed > 0 and readiness_status == "LOW":
        overall_status = "DEGRADED"

    ess_info = signal_data.get("ess") if isinstance(signal_data.get("ess"), dict) else {}
    manual_sources = {
        "ess_lseg": {
            "label": "ESS / LSEG Equity Summary Score",
            "sourced_date": str(ess_info.get("sourced_date") or ""),
            "badge_state": str(ess_info.get("badge_state") or "UNKNOWN"),
            "coverage_warning_count": int(ess_info.get("coverage_warning_count") or 0),
            "status": "GOOD" if str(ess_info.get("badge_state") or "") in {"FRESH", "FRESH_PARTIAL"} else "STALE",
            "manual_source": True,
        }
    }

    return {
        "status": overall_status,
        "latest_refresh_date": latest_refresh_date,
        "provider_counts": provider_metrics,
        "decision_readiness": decision_readiness,
        "warnings": warnings,
        "artifacts": {
            "refresh_report_path": str(_REFRESH_REPORT_PATH),
            "refresh_report_exists": _REFRESH_REPORT_PATH.exists(),
            "refresh_report_mtime_utc": datetime.fromtimestamp(_REFRESH_REPORT_PATH.stat().st_mtime, tz=timezone.utc).isoformat()
            if _REFRESH_REPORT_PATH.exists()
            else None,
        },
        "readiness": readiness,
        "rows": rows,
        "manual_sources": manual_sources,
        "compatibility": {
            "endpoint": "/api/refresh-transparency",
            "note": "Compatibility payload synthesized from /api/signal-status and refresh report artifacts.",
        },
    }


def _sanitize_for_json(obj):
    """Recursively convert NaN/Infinity to null for valid JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    return obj


def _latest_completed_run_id() -> str | None:
    manifest_path = _REPO_ROOT / "data" / "portfolio_ingestion" / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        portfolios = manifest.get("portfolios", [])
        completed = [p for p in portfolios if p.get("status") == "COMPLETE" and p.get("run_id")]
        if not completed:
            return None
        return str(completed[-1].get("run_id"))
    except Exception:
        return None


def _operator_priorities_unavailable_payload(*, reason: str, message: str, run_id: str | None = None) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "message": message,
        "run_id": run_id,
        "today_operator_action_plan": {},
        "warnings": [
            "Operator action plan unavailable; do not execute sell-funded rotation from this panel.",
        ],
        "updated_at_utc": None,
    }


def _cra_unavailable_payload(*, reason: str, message: str, run_id: str | None = None) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "message": message,
        "run_id": run_id,
        "actions": [],
        "capital_sources": [],
        "sources": [],
        "deployments": [],
        "warnings": [
            "CRA unavailable; do not execute sell-funded rotation from this panel.",
        ],
        "updated_at_utc": None,
    }


def _cra_draft_path() -> Path:
    return _REPO_ROOT / "data" / "operator" / "cra_draft.json"


def _build_cra_payload() -> dict:
    import sys as _sys

    if str(_REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_REPO_ROOT))

    from src.portfolio.cra.rotation_proposal_builder import (
        build_proposal_from_manifest,
        build_rotation_proposal,
    )

    manifest_path = _REPO_ROOT / "data" / "portfolio_ingestion" / "manifest.json"
    runs_root = _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs"
    tax_state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"

    proposal = build_proposal_from_manifest(
        manifest_path=manifest_path,
        runs_root=runs_root,
        tax_state_path=tax_state_path,
    )
    if proposal is not None:
        return proposal.to_dict()

    run_id = _latest_completed_run_id()
    if not run_id:
        return _cra_unavailable_payload(
            reason="latest_run_missing",
            message="Capital Rotation Advisor data is unavailable for the latest run.",
        )

    run_dir = runs_root / run_id
    if not run_dir.exists():
        return _cra_unavailable_payload(
            reason="run_artifact_missing",
            message="Capital Rotation Advisor artifacts are missing for the latest run.",
            run_id=run_id,
        )

    tax_state = None
    if tax_state_path.exists():
        try:
            tax_state = json.loads(tax_state_path.read_text(encoding="utf-8"))
        except Exception:
            tax_state = None

    strategic_profiles = None
    sp_path = run_dir / "strategic_profiles.json"
    if sp_path.exists():
        try:
            _sp = json.loads(sp_path.read_text(encoding="utf-8"))
            if isinstance(_sp, list):
                strategic_profiles = _sp
            elif isinstance(_sp, dict):
                strategic_profiles = _sp.get("profiles")
        except Exception:
            strategic_profiles = None

    try:
        proposal = build_rotation_proposal(
            run_dir=run_dir,
            tax_state=tax_state,
            strategic_profiles=strategic_profiles,
        )
        return proposal.to_dict()
    except Exception:
        return _cra_unavailable_payload(
            reason="capital_rotation_artifact_missing",
            message="Capital Rotation Advisor data is unavailable for the latest run.",
            run_id=run_id,
        )


def _build_operator_priorities_payload(run_id: str | None = None) -> dict:
    import sys as _sys

    if str(_REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_REPO_ROOT))
    from src.portfolio.runner import load_analysis_run

    resolved_run_id = run_id or _latest_completed_run_id()
    if not resolved_run_id:
        return _operator_priorities_unavailable_payload(
            reason="latest_run_missing",
            message="No completed portfolio analysis run is available.",
        )

    result = load_analysis_run(resolved_run_id)
    if not isinstance(result, dict):
        return _operator_priorities_unavailable_payload(
            reason="run_not_found",
            message="Portfolio operator priorities are unavailable for the requested run.",
            run_id=resolved_run_id,
        )

    plan = result.get("today_operator_action_plan") or result.get("daily_operator_action_plan")
    if not isinstance(plan, dict) or not plan:
        return _operator_priorities_unavailable_payload(
            reason="operator_action_plan_missing",
            message="Operator action plan unavailable — backend returned degraded state.",
            run_id=resolved_run_id,
        )

    return {
        "status": "ok",
        "run_id": resolved_run_id,
        "snapshot_date": (result.get("run_metadata") or {}).get("snapshot_date"),
        "today_operator_action_plan": plan,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


PIS_DASHBOARD_API_ROUTES = {
    "/api/pis/snapshots",
    "/api/pis/summary",
    "/api/pis/latest",
    "/api/pis/health",
    "/api/pis/governance/latest",
    "/api/pis/governance-summary",
    "/api/pis/canonical/latest",
    "/api/pis/canonical/history",
    "/api/pis/canonical-summary",
    "/api/pis/changes/latest",
    "/api/pis/change-summary",
    "/api/pis/lineage/latest",
    "/api/pis/lineage-summary",
    "/api/pis/attribution/latest",
    "/api/pis/attribution/history",
    "/api/pis/attribution-summary",
    "/api/pis/benchmark-attribution/latest",
    "/api/pis/benchmark-attribution/returns",
    "/api/pis/benchmark-attribution/sources",
    "/api/pis/allocation-drift/latest",
    "/api/pis/allocation-drift/summary",
    "/api/pis/action-attribution/summary",
    "/api/pis/action-attribution/recommendations",
    "/api/pis/action-attribution/sources",
    "/api/pis/dor/summary",
    "/api/pis/dor/cohorts",
    "/api/pis/dor/recommendations",
    "/api/pis/policy/current",
    "/api/pis/policy/history",
    "/api/pis/policy/diff",
    "/api/pis/policy/summary",
    "/api/pis/policy/impact",
    "/api/pis/policy/timeline",
    "/api/pis/compliance/latest",
    "/api/pis/compliance/summary",
}


MEI_DASHBOARD_API_ROUTES = {
    "/api/mei/events",
    "/api/mei/events/summary",
    "/api/mei/exposures",
    "/api/mei/exposures/summary",
    "/api/mei/recommendation-context",
    "/api/mei/recommendation-context/summary",
    "/api/mei/event-history/summary",
    "/api/mei/outcomes",
    "/api/mei/outcome-summary",
    "/api/mei/event-impact",
}


def _resolve_pis_dashboard_payload(path: str) -> object | None:
    import sys as _sys

    if str(_REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_REPO_ROOT))

    from src.pis.action_attribution import (
        pis_action_attribution_recommendations,
        pis_action_attribution_sources,
        pis_action_attribution_summary,
    )
    from src.pis.allocation_compliance import pis_compliance_latest, pis_compliance_summary
    from src.pis.allocation_drift import pis_allocation_drift_latest, pis_allocation_drift_summary
    from src.pis.benchmark_attribution import (
        pis_benchmark_latest,
        pis_benchmark_returns,
        pis_benchmark_sources,
    )
    from src.pis.canonical_daily import pis_canonical_history, pis_canonical_latest, pis_canonical_summary
    from src.pis.change_detection import pis_change_summary, pis_changes_latest
    from src.pis.dislocation_outcome_review import (
        pis_dor_cohorts,
        pis_dor_recommendations,
        pis_dor_summary,
    )
    from src.pis.governance import pis_governance_latest, pis_governance_summary
    from src.pis.performance_attribution import (
        pis_attribution_history,
        pis_attribution_latest,
        pis_attribution_summary,
    )
    from src.pis.policy_change_summary import policy_impact, policy_summary, policy_timeline
    from src.pis.policy_version_diff import pis_policy_current, pis_policy_diff, pis_policy_history
    from src.pis.recommendation_lineage import pis_lineage_latest, pis_lineage_summary
    from src.pis.storage import (
        pis_latest_snapshot_summary,
        pis_sih_lineage_summary,
        pis_snapshot_history_health,
        pis_snapshot_inventory,
        pis_value_timeline,
    )

    if path == "/api/pis/snapshots":
        return pis_snapshot_inventory()
    if path == "/api/pis/summary":
        return {
            "timeline": pis_value_timeline(),
            "lineage": pis_sih_lineage_summary(repo_root=_REPO_ROOT),
            "health": pis_snapshot_history_health(),
        }
    if path == "/api/pis/latest":
        return pis_latest_snapshot_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/health":
        return pis_snapshot_history_health()
    if path == "/api/pis/governance/latest":
        return pis_governance_latest()
    if path == "/api/pis/governance-summary":
        return pis_governance_summary()
    if path == "/api/pis/canonical/latest":
        return pis_canonical_latest()
    if path == "/api/pis/canonical/history":
        return pis_canonical_history()
    if path == "/api/pis/canonical-summary":
        return pis_canonical_summary()
    if path == "/api/pis/changes/latest":
        return pis_changes_latest(repo_root=_REPO_ROOT)
    if path == "/api/pis/change-summary":
        return pis_change_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/lineage/latest":
        return pis_lineage_latest(repo_root=_REPO_ROOT)
    if path == "/api/pis/lineage-summary":
        return pis_lineage_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/attribution/latest":
        return pis_attribution_latest(repo_root=_REPO_ROOT)
    if path == "/api/pis/attribution/history":
        return pis_attribution_history(repo_root=_REPO_ROOT)
    if path == "/api/pis/attribution-summary":
        return pis_attribution_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/benchmark-attribution/latest":
        return pis_benchmark_latest(repo_root=_REPO_ROOT)
    if path == "/api/pis/benchmark-attribution/returns":
        return pis_benchmark_returns(repo_root=_REPO_ROOT)
    if path == "/api/pis/benchmark-attribution/sources":
        return pis_benchmark_sources(repo_root=_REPO_ROOT)
    if path == "/api/pis/allocation-drift/latest":
        return pis_allocation_drift_latest(repo_root=_REPO_ROOT)
    if path == "/api/pis/allocation-drift/summary":
        return pis_allocation_drift_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/action-attribution/summary":
        return pis_action_attribution_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/action-attribution/recommendations":
        return pis_action_attribution_recommendations(repo_root=_REPO_ROOT)
    if path == "/api/pis/action-attribution/sources":
        return pis_action_attribution_sources(repo_root=_REPO_ROOT)
    if path == "/api/pis/dor/summary":
        return pis_dor_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/dor/cohorts":
        return pis_dor_cohorts(repo_root=_REPO_ROOT)
    if path == "/api/pis/dor/recommendations":
        return pis_dor_recommendations(repo_root=_REPO_ROOT)
    if path == "/api/pis/policy/current":
        return pis_policy_current(repo_root=_REPO_ROOT)
    if path == "/api/pis/policy/history":
        return pis_policy_history(repo_root=_REPO_ROOT)
    if path == "/api/pis/policy/diff":
        return pis_policy_diff(repo_root=_REPO_ROOT)
    if path == "/api/pis/policy/summary":
        return policy_summary(repo_root=_REPO_ROOT)
    if path == "/api/pis/policy/impact":
        return policy_impact(repo_root=_REPO_ROOT)
    if path == "/api/pis/policy/timeline":
        return policy_timeline(repo_root=_REPO_ROOT)
    if path == "/api/pis/compliance/latest":
        return pis_compliance_latest(repo_root=_REPO_ROOT)
    if path == "/api/pis/compliance/summary":
        return pis_compliance_summary(repo_root=_REPO_ROOT)
    return None


def _resolve_mei_dashboard_payload(path: str, query: str) -> object | None:
    import sys as _sys

    if str(_REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_REPO_ROOT))

    from src.mei.event_history import mei_event_history_summary
    from src.mei.event_outcome_tracker import (
        mei_event_impact,
        mei_outcome_by_event,
        mei_outcome_summary,
        mei_outcomes,
    )
    from src.mei.events import mei_events, mei_events_summary
    from src.mei.exposures import mei_exposures, mei_exposures_summary
    from src.mei.recommendation_context import (
        mei_recommendation_context,
        mei_recommendation_context_summary,
    )

    if path == "/api/mei/events":
        return mei_events(_REPO_ROOT)
    if path == "/api/mei/events/summary":
        return mei_events_summary(_REPO_ROOT)
    if path == "/api/mei/exposures":
        return mei_exposures(_REPO_ROOT)
    if path == "/api/mei/exposures/summary":
        return mei_exposures_summary(_REPO_ROOT)
    if path == "/api/mei/recommendation-context":
        return mei_recommendation_context(_REPO_ROOT)
    if path == "/api/mei/recommendation-context/summary":
        return mei_recommendation_context_summary(_REPO_ROOT)
    if path == "/api/mei/event-history/summary":
        return mei_event_history_summary(_REPO_ROOT)
    if path == "/api/mei/outcome-summary":
        return mei_outcome_summary(_REPO_ROOT)
    if path == "/api/mei/event-impact":
        return mei_event_impact(_REPO_ROOT)
    if path == "/api/mei/outcomes":
        event_id = (parse_qs(query).get("event_id", [""])[0] or "").strip()
        if event_id:
            return mei_outcome_by_event(event_id, _REPO_ROOT)
        return mei_outcomes(_REPO_ROOT)
    return None


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Static file handler extended with /api/* JSON endpoints."""

    def do_OPTIONS(self) -> None:  # type: ignore[override]
        path = self.path.split("?")[0]
        if path in {
            "/api/danelfin/browser-capture",
            "/api/danelfin/browser-capture/diagnostic-status",
            "/api/danelfin/browser-capture/diagnostic-queue/claim",
            "/api/danelfin/browser-capture/production-status",
            "/api/danelfin/browser-capture/production-queue/prepare",
            "/api/danelfin/browser-capture/production-queue/claim",
        }:
            self.send_response(204)
            origin = _capture_cors_origin(self)
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            if str(self.headers.get("Access-Control-Request-Private-Network") or "").strip().lower() == "true":
                self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()
            return
        self.send_error(404)

    def do_HEAD(self) -> None:  # type: ignore[override]
        if self.path.startswith("/api/"):
            self.command = "HEAD"
            try:
                self.do_GET()
            finally:
                self.command = "HEAD"
            return
        super().do_HEAD()

    def do_GET(self) -> None:  # type: ignore[override]
        global _refresh_proc
        path = self.path.split("?")[0]
        if path == "/api/signal-status":
            running = _refresh_proc is not None and _refresh_proc.poll() is None
            data = _signal_status()
            data["_running"] = running
            self._json_response(data)
        elif path == "/api/danelfin/browser-capture/queue":
            try:
                self._json_response(_danelfin_capture_queue_payload())
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/danelfin/browser-capture/diagnostic-queue":
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            symbol = str((qs.get("symbol") or [""])[0] or "").strip() or _DANELFIN_DIAGNOSTIC_DEFAULT_SYMBOL
            pair_symbol = str((qs.get("pair_symbol") or [""])[0] or "").strip() or _DANELFIN_DIAGNOSTIC_DEFAULT_PAIR_SYMBOL
            try:
                self._json_response(_build_danelfin_diagnostic_queue_payload(symbol, pair_symbol))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, 422)
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/danelfin/browser-capture/diagnostic-queue/pending":
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            symbol = str((qs.get("symbol") or [""])[0] or "").strip() or ""
            run_id = str((qs.get("id") or [""])[0] or "").strip() or ""
            try:
                state = _find_prepared_danelfin_diagnostic_run(symbol=symbol, run_id=run_id)
                if state is None:
                    self._json_response(
                        {
                            "status": "ok",
                            "provider": "danelfin",
                            "diagnostic": True,
                            "dry_run": True,
                            "diagnostic_run_id": run_id or None,
                            "symbols": [symbol.upper()] if symbol else [],
                            "jobs": [],
                            "job_count": 0,
                            "generated_at_utc": _utc_now_iso(),
                        }
                    )
                else:
                    self._json_response(_build_danelfin_diagnostic_queue_payload_from_state(state))
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/danelfin/browser-capture/diagnostic-status":
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            run_id = str((qs.get("id") or [""])[0] or "").strip()
            try:
                self._json_response({"status": "ok", "diagnostic": _danelfin_diagnostic_status(run_id)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, 422)
            except KeyError:
                self._json_response({"error": "diagnostic run not found"}, 404)
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/danelfin/browser-capture/production-queue/pending":
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            run_id = str((qs.get("id") or [""])[0] or "").strip()
            try:
                state = _find_prepared_danelfin_production_run(run_id=run_id)
                if state is None:
                    self._json_response(
                        {
                            "status": "ok",
                            "provider": "danelfin",
                            "diagnostic": False,
                            "mode": "production",
                            "dry_run": False,
                            "run_id": run_id or None,
                            "symbols": [],
                            "jobs": [],
                            "job_count": 0,
                            "generated_at_utc": _utc_now_iso(),
                        }
                    )
                else:
                    self._json_response(_build_danelfin_production_queue_payload_from_state(state))
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/danelfin/browser-capture/production-status":
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            run_id = str((qs.get("id") or [""])[0] or "").strip()
            try:
                self._json_response({"status": "ok", "run": _danelfin_production_status(run_id)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, 422)
            except KeyError:
                self._json_response({"error": "production run not found"}, 404)
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/refresh-transparency":
            self._json_response(_refresh_transparency_payload())
        elif path == "/api/portfolio/preflight":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.validation.analysis_preflight import run_analysis_preflight

                payload = run_analysis_preflight(
                    repo_root=_REPO_ROOT,
                    require_active_ess=True,
                ).to_dict()
                self._json_response(payload)
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/signal-refresh/status":
            running = _refresh_proc is not None and _refresh_proc.poll() is None
            self._json_response(_refresh_status_payload(running=running))
        elif path == "/api/score-fetch/status":
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = {k: v for k, v in (p.split("=", 1) for p in qs.split("&") if "=" in p)}
            sym = params.get("symbol", "").strip().upper()
            if not sym:
                self._json_response({"error": "symbol required"}, 400)
                return
            with _fetch_lock:
                job = _fetch_jobs.get(sym)
            if job is None:
                self._json_response({"status": "not_found", "symbol": sym})
            else:
                self._json_response(job)
        elif path == "/api/portfolio/runs":
            try:
                manifest_path = _REPO_ROOT / "data/portfolio_ingestion/manifest.json"
                if manifest_path.exists():
                    with open(manifest_path) as _fh:
                        manifest = json.load(_fh)
                else:
                    manifest = {"portfolios": []}
                self._json_response({"portfolios": manifest.get("portfolios", [])})
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path.startswith("/api/portfolio/runs/"):
            run_id = path.split("/")[-1].strip()
            if not run_id:
                self._json_response({"error": "run_id required"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.runner import load_analysis_run
                result = load_analysis_run(run_id)
                if result is None:
                    self._json_response({"error": "run not found"}, 404)
                else:
                    self._json_response(result)
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/cpv/latest":
            run_id = _latest_completed_run_id()
            if not run_id:
                self._json_response({
                    "status": "unavailable",
                    "reason": "latest_run_missing",
                    "message": "No completed portfolio analysis run is available.",
                    "run_id": None,
                }, 404)
                return

            compliance_path = (
                _REPO_ROOT
                / "data"
                / "portfolio_ingestion"
                / "analysis_runs"
                / run_id
                / "compliance.json"
            )
            if not compliance_path.exists():
                self._json_response({
                    "status": "unavailable",
                    "reason": "compliance_artifact_missing",
                    "message": "Compliance artifact is unavailable for the latest completed run.",
                    "run_id": run_id,
                }, 404)
                return

            try:
                payload = json.loads(compliance_path.read_text(encoding="utf-8"))
                self._json_response(payload)
            except Exception as exc:
                self._json_response({
                    "status": "unavailable",
                    "reason": "compliance_artifact_invalid",
                    "message": f"Compliance artifact could not be loaded: {exc}",
                    "run_id": run_id,
                }, 500)
        elif path == "/api/drift/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.drift_analyzer import compute_drift_summary

                self._json_response(compute_drift_summary(_REPO_ROOT))
            except Exception:
                self._json_response({
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "current_date": None,
                    "prior_date": None,
                    "dates_available": 0,
                    "current_overall_status": "UNKNOWN",
                    "current_compliance_score": None,
                    "cpv_trend": [],
                })
        elif path == "/api/operator/tax-state":
            state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
            if state_path.exists():
                try:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    self._json_response(state)
                except Exception as exc:
                    self._json_response({"error": str(exc)}, 500)
            else:
                self._json_response({})
        elif path == "/api/operator/strategic-exits":
            state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
            existing: dict = {}
            if state_path.exists():
                try:
                    existing = json.loads(state_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            syms = existing.get("strategic_exit_symbols", [])
            if not isinstance(syms, list):
                syms = []
            self._json_response({"strategic_exit_symbols": syms})
        elif path == "/api/statement-gain-loss/latest":
            payload, status = _statement_gain_loss_latest_payload()
            self._json_response(payload, status)
        elif path == "/api/market-regime-guardrail/latest":
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            run_id = (parse_qs(query).get("run_id", [""])[0] or "").strip()
            payload, status = _market_regime_guardrail_payload(run_id=run_id or None)
            self._json_response(payload, status)
        elif path == "/api/operator/policies" or path.startswith("/api/operator/policies/"):
            # GET /api/operator/policies         → all active policies
            # GET /api/operator/policies/{sym}   → single symbol policy
            import sys as _sys
            if str(_REPO_ROOT) not in _sys.path:
                _sys.path.insert(0, str(_REPO_ROOT))
            from src.portfolio.operator_policy import OperatorPolicyRegistry
            state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
            registry = OperatorPolicyRegistry.load(str(state_path))
            sym_seg = path[len("/api/operator/policies/"):].strip().upper() if path != "/api/operator/policies" else ""
            if sym_seg:
                if not _SYMBOL_RE.match(sym_seg):
                    self._json_response({"error": "invalid symbol"}, 400)
                    return
                policy = registry.get(sym_seg)
                if policy is None:
                    self._json_response({"symbol": sym_seg, "policy": None})
                else:
                    import dataclasses as _dc
                    self._json_response({"symbol": sym_seg, "policy": _dc.asdict(policy)})
            else:
                import dataclasses as _dc
                all_active = registry.all_active()
                self._json_response({
                    "policies": [_dc.asdict(p) for p in all_active.values()],
                    "snapshot": registry.policy_snapshot(),
                })
        elif path == "/api/cra/proposal":
            try:
                self._json_response(_build_cra_payload())
            except Exception as exc:
                self._json_response(_cra_unavailable_payload(
                    reason="cra_endpoint_error",
                    message=f"Capital Rotation Advisor data is unavailable: {exc}",
                ))
        elif path == "/api/cra/draft":
            draft_path = _cra_draft_path()
            if not draft_path.exists():
                self._json_response({"error": "draft not found"}, 404)
                return
            try:
                draft = json.loads(draft_path.read_text(encoding="utf-8"))
                self._json_response(draft)
            except Exception as exc:
                self._json_response({"error": f"invalid draft payload: {exc}"}, 500)
        elif path == "/api/cra/draft/export":
            draft_path = _cra_draft_path()
            if not draft_path.exists():
                self._json_response({"error": "draft not found"}, 404)
                return
            try:
                draft = json.loads(draft_path.read_text(encoding="utf-8"))
            except Exception as exc:
                self._json_response({"error": f"invalid draft payload: {exc}"}, 500)
                return

            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            fmt = (parse_qs(query).get("format", ["csv"])[0] or "csv").lower()

            if fmt == "md":
                lines = [
                    f"# CRA Draft ({draft.get('run_id', 'N/A')})",
                    "",
                    f"Status: {draft.get('proposal_status', 'N/A')}",
                    f"As of: {draft.get('as_of_date', 'N/A')}",
                    "",
                    "## Capital Sources",
                ]
                for s in draft.get("sources", []) or []:
                    lines.append(f"- {s.get('symbol', 'N/A')}: {s.get('category', 'N/A')} · {s.get('priority', 'N/A')}")
                lines.append("")
                lines.append("## Deployments")
                for d in draft.get("deployments", []) or []:
                    lines.append(f"- #{d.get('rank', '?')} {d.get('symbol', 'N/A')}: ${float(d.get('suggested_amount') or 0):,.0f}")
                body = "\n".join(lines).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=cra_draft.md")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["section", "rank", "symbol", "category", "priority", "estimated_proceeds", "suggested_amount"])
                for s in draft.get("sources", []) or []:
                    writer.writerow([
                        "source", "", s.get("symbol", ""), s.get("category", ""), s.get("priority", ""),
                        s.get("estimated_proceeds", ""), "",
                    ])
                for d in draft.get("deployments", []) or []:
                    writer.writerow([
                        "deployment", d.get("rank", ""), d.get("symbol", ""), "", "", "", d.get("suggested_amount", ""),
                    ])
                body = buf.getvalue().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=cra_draft.csv")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        elif path in {"/api/operator-priorities", "/api/portfolio-operator-priorities"}:
            try:
                query = self.path.split("?", 1)[1] if "?" in self.path else ""
                run_id = (parse_qs(query).get("run_id", [""])[0] or "").strip()
                payload = _build_operator_priorities_payload(run_id=run_id or None)
                self._json_response(payload)
            except Exception as exc:
                self._json_response(_operator_priorities_unavailable_payload(
                    reason="operator_priorities_endpoint_error",
                    message=f"Operator action plan unavailable — backend returned degraded state: {exc}",
                ))
        elif path == "/api/portfolio-alignment/latest":
            try:
                run_id = _latest_completed_run_id()
                if not run_id:
                    self._json_response(_operator_priorities_unavailable_payload(
                        reason="latest_run_missing",
                        message="No completed portfolio analysis run is available.",
                    ))
                    return
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.runner import load_analysis_run
                result = load_analysis_run(run_id)
                if not isinstance(result, dict):
                    self._json_response(_operator_priorities_unavailable_payload(
                        reason="run_not_found",
                        message="Portfolio alignment payload unavailable for latest run.",
                        run_id=run_id,
                    ))
                else:
                    self._json_response(result)
            except Exception as exc:
                self._json_response(_operator_priorities_unavailable_payload(
                    reason="portfolio_alignment_latest_error",
                    message=f"Portfolio alignment payload unavailable: {exc}",
                ))
        elif path == "/api/portfolio/archetype-targets":
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = {k: v for k, v in (p.split("=", 1) for p in qs.split("&") if "=" in p)}
            mandate = params.get("mandate", "CONCENTRATED_ALPHA").strip().upper()
            try:
                import sys as _sys
                import yaml as _yaml
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.archetype import load_archetype_targets, _PROFILE_FILES
                targets_map = load_archetype_targets(mandate)
                # Load dimension metadata for node labels / depth / parent
                dim_path = _REPO_ROOT / "config" / "allocation_dimensions.yaml"
                dims: dict = {}
                if dim_path.exists():
                    _ddata = _yaml.safe_load(dim_path.read_text(encoding="utf-8"))
                    for _n in (_ddata.get("nodes") or []):
                        dims[_n["key"]] = _n
                # Load profile metadata
                _pfile = _PROFILE_FILES.get(mandate, "balanced_allocation_profile.yaml")
                _ppath = _REPO_ROOT / "config" / "allocation_models" / _pfile
                display_name = mandate
                philosophy = ""
                if _ppath.exists():
                    _pd = _yaml.safe_load(_ppath.read_text(encoding="utf-8"))
                    display_name = _pd.get("display_name", mandate)
                    philosophy = (_pd.get("philosophy") or "").strip()
                # Build structured target rows compatible with allocation_intelligence UI
                rows = []
                for node_key, tgt_pct in sorted(targets_map.items()):
                    dim = dims.get(node_key, {})
                    parent_key = dim.get("parent_key") or ""
                    depth = node_key.count(".") + 1
                    asset_class = node_key.split(".")[0]
                    raw_label = dim.get("label") or node_key.split(".")[-1].replace("_", " ").title()
                    if parent_key and parent_key in targets_map:
                        parent_pct = targets_map[parent_key]
                        pct_of_parent = round((tgt_pct / parent_pct * 100.0), 4) if parent_pct > 0 else 0.0
                    else:
                        pct_of_parent = round(tgt_pct, 4)
                    rows.append({
                        "node_key":            node_key,
                        "node_label":          raw_label,
                        "parent_key":          parent_key,
                        "asset_class":         asset_class,
                        "hierarchy_depth":     str(depth),
                        "target_pct_of_total": str(round(tgt_pct, 4)),
                        "target_pct_of_parent": str(round(pct_of_parent, 4)),
                        "delta_pct":           "",
                        "confidence_score":    "1.0",
                    })
                self._json_response({
                    "mandate_type": mandate,
                    "display_name": display_name,
                    "philosophy":   philosophy,
                    "targets":      rows,
                })
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/drift/intelligence-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_intelligence_summary

                self._json_response(drift_intelligence_summary(_REPO_ROOT))
            except Exception:
                self._json_response({
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "trend_counts": {},
                    "top_priority": None,
                    "most_chronic": None,
                    "most_improving": None,
                    "most_deteriorating": None,
                    "total_nodes": 0,
                    "violation_nodes": 0,
                    "structural_count": 0,
                    "chronic_count": 0,
                    "governance_note": "Display-only intelligence unavailable.",
                })
        elif path == "/api/drift/priorities":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_priorities

                self._json_response(drift_priorities(_REPO_ROOT))
            except Exception:
                self._json_response({"generated_at": datetime.now(timezone.utc).isoformat(), "top10": []})
        elif path == "/api/drift/chronic":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_chronic

                self._json_response(drift_chronic(_REPO_ROOT))
            except Exception:
                self._json_response({"generated_at": datetime.now(timezone.utc).isoformat(), "chronic": []})
        elif path == "/api/drift/momentum":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_momentum

                self._json_response(drift_momentum(_REPO_ROOT))
            except Exception:
                self._json_response({"generated_at": datetime.now(timezone.utc).isoformat(), "nodes": []})
        elif path == "/api/conflict-review/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh

                payload = load_or_refresh(_REPO_ROOT)
                self._json_response({
                    "meta": payload.get("meta", {}),
                    "learning": payload.get("learning", {}),
                })
            except Exception:
                self._json_response({"meta": {}, "learning": {}})
        elif path == "/api/conflict-review/outcomes":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh

                payload = load_or_refresh(_REPO_ROOT)
                self._json_response(payload.get("outcomes", {"patterns": []}))
            except Exception:
                self._json_response({"patterns": []})
        elif path == "/api/conflict-review/scorecard":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh

                payload = load_or_refresh(_REPO_ROOT)
                self._json_response(payload.get("scorecard", {"scorecard": []}))
            except Exception:
                self._json_response({"scorecard": []})
        elif path == "/api/conflict-review/alpha":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.conflict_alpha_analysis import conflict_alpha_report

                self._json_response(conflict_alpha_report(_REPO_ROOT))
            except Exception:
                self._json_response({"status": "NO_DATA", "patterns": []})
        elif path.startswith("/api/conflict-review/symbol/"):
            symbol = path.split("/")[-1].strip().upper()
            if not symbol or not _SYMBOL_RE.match(symbol):
                self._json_response({"error": "invalid symbol"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh, symbol_deep_dive

                payload = load_or_refresh(_REPO_ROOT)
                inventory = payload.get("inventory", [])
                self._json_response(symbol_deep_dive(symbol, inventory))
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/conflict-review/security-alpha-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.security_conflict_alpha import security_alpha_summary

                self._json_response(security_alpha_summary(_REPO_ROOT))
            except Exception:
                self._json_response({"status": "NO_PAR_DATA", "securities": {}})
        elif path == "/api/predictive/calibration":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.conflict_alpha_calibration import calibration_summary

                self._json_response(calibration_summary(_REPO_ROOT))
            except Exception:
                self._json_response({"patterns": []})
        elif path == "/api/predictive/directional-accuracy":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.directional_accuracy import directional_accuracy

                self._json_response(directional_accuracy(_REPO_ROOT))
            except Exception:
                self._json_response({"patterns": [], "overall": {}, "comparative": {}})
        elif path == "/api/signal-conflicts":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.signal_conflict_classifier import get_conflicts_for_symbols

                query = self.path.split("?", 1)[1] if "?" in self.path else ""
                qs = parse_qs(query)
                symbols_raw = ",".join(qs.get("symbols", []))
                symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
                if not symbols:
                    self._json_response({})
                else:
                    self._json_response(get_conflicts_for_symbols(symbols, _REPO_ROOT))
            except Exception:
                self._json_response({})
        elif path == "/api/security-metadata":
            # Optional enrichment endpoint; fail-open to an empty mapping.
            self._json_response({})
        elif path.startswith("/api/pis/"):
            try:
                payload = _resolve_pis_dashboard_payload(path)
            except Exception as exc:
                self._json_response(
                    {
                        "status": "degraded",
                        "endpoint": path,
                        "error": str(exc),
                    }
                )
                return
            if payload is None:
                self._json_response({"error": "not found", "endpoint": path}, 404)
                return
            self._json_response(payload)
        elif path.startswith("/api/mei/"):
            try:
                query = self.path.split("?", 1)[1] if "?" in self.path else ""
                payload = _resolve_mei_dashboard_payload(path, query)
            except Exception as exc:
                self._json_response(
                    {
                        "status": "degraded",
                        "endpoint": path,
                        "error": str(exc),
                    }
                )
                return
            if payload is None:
                self._json_response({"error": "not found", "endpoint": path}, 404)
                return
            self._json_response(payload)
        elif path in {"/ui/allocation_intelligence", "/ui/allocation_intelligence/", "/ui/allocation_intelligence/index.html"}:
            index_path = _REPO_ROOT / "ui" / "allocation_intelligence" / "index.html"
            if not index_path.exists():
                self._json_response({"error": "allocation intelligence index not found"}, 404)
                return
            body = index_path.read_text(encoding="utf-8").replace(
                '<script src="app.js"></script>',
                '<script src="app.js?v=allocation-readpath-20260817b"></script>',
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self) -> None:  # type: ignore[override]
        path = self.path.split("?")[0]
        if path == "/api/signal-refresh":
            global _refresh_proc
            global _refresh_last_report
            global _refresh_last_exit_code
            global _refresh_requested_intent
            global _refresh_resolved_intent
            global _refresh_scope_summary
            global _refresh_scope_samples
            global _refresh_provider_planned_totals
            global _refresh_started_at_utc
            global _refresh_completed_at_utc
            if _refresh_proc is not None and _refresh_proc.poll() is None:
                self._json_response({"started": False, "reason": "already running", **_refresh_status_payload(running=True)})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                payload = {}

            requested_intent = str(payload.get("intent") or "portfolio_signals").strip().lower()
            resolved_intent = _resolve_refresh_intent(requested_intent)
            if not resolved_intent:
                self._json_response(
                    {
                        "accepted": False,
                        "started": False,
                        "error": "unknown refresh intent",
                        "requested_intent": requested_intent,
                        "allowed_intents": _allowed_refresh_intents(),
                    },
                    400,
                )
                return

            scope_plan = _refresh_scope_plan(resolved_intent)
            scope_summary = scope_plan.get("scope_summary") if isinstance(scope_plan, dict) else {}
            scope_samples = scope_plan.get("planned_symbol_samples") if isinstance(scope_plan, dict) else {}
            provider_symbols = ((scope_plan.get("planned_symbols") or {}).get("provider_symbols") or {}) if isinstance(scope_plan, dict) else {}

            _refresh_requested_intent = requested_intent
            _refresh_resolved_intent = resolved_intent
            _refresh_scope_summary = scope_summary if isinstance(scope_summary, dict) else {}
            _refresh_scope_samples = scope_samples if isinstance(scope_samples, dict) else {}
            _refresh_provider_planned_totals = {
                provider: (len(symbols) if isinstance(symbols, list) else None)
                for provider, symbols in (provider_symbols.items() if isinstance(provider_symbols, dict) else [])
            }
            _refresh_last_report = None
            _refresh_last_exit_code = None
            _refresh_started_at_utc = datetime.now(timezone.utc).isoformat()
            _refresh_completed_at_utc = None

            if resolved_intent == "prepare_portfolio_review":
                cmd = [sys.executable, str(_REPO_ROOT / "scripts/prepare_portfolio_review.py")]
            else:
                cmd = [
                    sys.executable,
                    str(_REPO_ROOT / "scripts/refresh_signals.py"),
                    "--refresh-mode",
                    resolved_intent,
                    "--report-path",
                    str(_REFRESH_REPORT_PATH),
                ]
                if resolved_intent == "stale_only":
                    cmd.append("--smart")

            _refresh_proc = subprocess.Popen(
                cmd,
                cwd=str(_REPO_ROOT),
                env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
            )

            self._json_response(
                {
                    "accepted": True,
                    "started": True,
                    "requested_intent": requested_intent,
                    "resolved_intent": resolved_intent,
                    "mode": resolved_intent,
                    "scope_summary": _refresh_scope_summary,
                    "planned_symbol_samples": _refresh_scope_samples,
                    "scope_formula": _refresh_scope_formula(_refresh_scope_summary, resolved_intent),
                    "provider_planned_totals": _refresh_provider_planned_totals,
                }
            )
        elif path == "/api/score-fetch":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            sym = str(payload.get("symbol", "")).strip().upper()
            if not sym or not _SYMBOL_RE.match(sym):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            with _fetch_lock:
                existing = _fetch_jobs.get(sym)
                if existing and existing.get("status") == "pending":
                    self._json_response({"status": "pending", "symbol": sym})
                    return
                _fetch_jobs[sym] = {"status": "pending", "symbol": sym}
            t = threading.Thread(target=_do_fetch_scores, args=(sym,), daemon=True)
            t.start()
            self._json_response({"status": "pending", "symbol": sym})
        elif path == "/api/portfolio/analyze":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            portfolio_csv = payload.get("portfolio_csv", "")
            source_filename = str(payload.get("source_filename", "upload.csv"))
            snapshot_date = str(payload.get("snapshot_date", date.today().isoformat()))
            mandate_type = str(payload.get("mandate_type", "CONCENTRATED_ALPHA"))
            if not portfolio_csv:
                self._json_response({"error": "portfolio_csv is required"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.runner import run_analysis
                result = run_analysis(portfolio_csv, source_filename, snapshot_date, mandate_type)
                self._json_response(result)
            except Exception as exc:
                self._json_response({"status": "REJECTED", "error": str(exc)}, 422)
        elif path == "/api/portfolio/deployment-plan":
            # On-demand deployment plan computation for existing runs.
            # Accepts: {"run_id": "...", "deployable_cash": float (optional)}
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            run_id = str(payload.get("run_id", "")).strip()
            if not run_id:
                self._json_response({"error": "run_id required"}, 400)
                return
            cash_override = payload.get("deployable_cash")
            try:
                import sys as _sys
                import dataclasses as _dc
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                run_dir = _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs" / run_id
                dq_path = run_dir / "deployment_queue.json"
                if not dq_path.exists():
                    self._json_response({"error": "deployment_queue not found for run"}, 404)
                    return
                with open(dq_path) as fh:
                    dq_data = json.load(fh)
                # Phase 22D.10 (D4): when no manual override, use adjusted_deployable_mv
                # from the stored cash_context if present (settlement-aware sizing).
                # Falls back to deployable_mv for pre-22D.10 runs that lack the field.
                if cash_override is not None:
                    cash_arg = float(cash_override)
                else:
                    _cc = dq_data.get("cash_context") or {}
                    if "adjusted_deployable_mv" in _cc:
                        cash_arg = float(_cc["adjusted_deployable_mv"])
                    else:
                        cash_arg = None  # deployment_planner reads deployable_mv itself
                from src.portfolio.deployment_planner import build_deployment_plan, PLANNER_VERSION
                plan = build_deployment_plan(dq_data, deployable_cash=cash_arg)
                result = {
                    "run_id": plan.run_id,
                    "planner_version": f"DP-{PLANNER_VERSION}",
                    "generated_at": plan.generated_at,
                    "deployable_cash": plan.deployable_cash,
                    "total_market_value": plan.total_market_value,
                    "total_allocated": plan.total_allocated,
                    "plan_advisory": plan.plan_advisory,
                    "tier_summaries": [_dc.asdict(t) for t in plan.tier_summaries],
                    "portfolio_impact": _dc.asdict(plan.portfolio_impact),
                    "recommendations": [_dc.asdict(r) for r in plan.recommendations],
                }
                self._json_response(result)
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/predictive/directional-refresh":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.directional_accuracy import refresh_directional

                self._json_response(refresh_directional(_REPO_ROOT))
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/cra/draft":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise ValueError("draft payload must be a JSON object")
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return

            draft_path = _cra_draft_path()
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            payload["_saved_at_utc"] = datetime.now(timezone.utc).isoformat()
            draft_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._json_response({"ok": True, "path": str(draft_path)})
        elif path == "/api/operator/tax-state":
            # POST: save operator tax context to persistent file
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            # Validate and sanitize numeric fields
            _TAX_FIELDS = ("net_realized_ytd", "potential_additional_losses",
                           "capital_loss_carryforward", "tax_year")
            state: dict = {}
            for f in _TAX_FIELDS:
                if f in payload:
                    state[f] = payload[f]
            state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Merge with existing state
            existing: dict = {}
            if state_path.exists():
                try:
                    existing = json.loads(state_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            existing.update(state)
            existing["_updated"] = datetime.now(timezone.utc).isoformat()
            state_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            self._json_response({"ok": True, "state": existing})
        elif path == "/api/operator/strategic-exits":
            # POST: add or remove a strategic exit symbol
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            action = str(payload.get("action", "add")).strip().lower()  # "add" or "remove"
            symbol = str(payload.get("symbol", "")).strip().upper()
            if not symbol or not _SYMBOL_RE.match(symbol):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            existing: dict = {}
            if state_path.exists():
                try:
                    existing = json.loads(state_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            syms = existing.get("strategic_exit_symbols", [])
            if not isinstance(syms, list):
                syms = []
            if action == "add" and symbol not in syms:
                syms.append(symbol)
            elif action == "remove":
                syms = [s for s in syms if s != symbol]
            existing["strategic_exit_symbols"] = sorted(syms)
            existing["_updated"] = datetime.now(timezone.utc).isoformat()
            state_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            self._json_response({"ok": True, "strategic_exit_symbols": sorted(syms)})
        elif path == "/api/operator/policies":
            # POST /api/operator/policies — add or update a policy entry
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            symbol = str(payload.get("symbol", "")).strip().upper()
            if not symbol or not _SYMBOL_RE.match(symbol):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            import sys as _sys
            if str(_REPO_ROOT) not in _sys.path:
                _sys.path.insert(0, str(_REPO_ROOT))
            from src.portfolio.operator_policy import (
                POLICY_TYPES, check_policy_conflict, OperatorPolicyRegistry,
            )
            policy_type = str(payload.get("policy_type", "")).strip().upper()
            if policy_type not in POLICY_TYPES:
                self._json_response({"error": f"unknown policy_type: {policy_type}; valid: {sorted(POLICY_TYPES)}"}, 400)
                return
            rationale = str(payload.get("rationale", "")).strip()
            expires_at = payload.get("expires_at", None)
            state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            existing: dict = {}
            if state_path.exists():
                try:
                    existing = json.loads(state_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            registry = OperatorPolicyRegistry.load(str(state_path))
            # Check conflict with existing active policy for this symbol
            existing_type = registry.active_policy_type(symbol)
            if existing_type and existing_type != policy_type:
                conflict, conflict_msg = check_policy_conflict(existing_type, policy_type)
                if conflict:
                    self._json_response({"error": conflict_msg, "conflict": True}, 409)
                    return
            now_str = datetime.now(timezone.utc).isoformat()
            policies_list = existing.get("operator_policies", [])
            if not isinstance(policies_list, list):
                policies_list = []
            # Mark any existing entry for this symbol as SUPERSEDED
            for i, entry in enumerate(policies_list):
                if entry.get("symbol") == symbol and entry.get("status") == "ACTIVE":
                    policies_list[i] = {**entry, "status": "SUPERSEDED", "revoked_at": now_str}
            new_entry = {
                "symbol": symbol,
                "policy_type": policy_type,
                "status": "ACTIVE",
                "rationale": rationale,
                "created_at": now_str,
                "expires_at": expires_at,
                "revoked_at": None,
            }
            policies_list.append(new_entry)
            existing["operator_policies"] = policies_list
            existing["_updated"] = now_str
            state_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            self._json_response({"ok": True, "policy": new_entry})
        elif path == "/api/operator/policies/revoke":
            # POST /api/operator/policies/revoke — revoke a policy by symbol
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            symbol = str(payload.get("symbol", "")).strip().upper()
            if not symbol or not _SYMBOL_RE.match(symbol):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
            existing: dict = {}
            if state_path.exists():
                try:
                    existing = json.loads(state_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            policies_list = existing.get("operator_policies", [])
            if not isinstance(policies_list, list):
                policies_list = []
            now_str = datetime.now(timezone.utc).isoformat()
            revoked_count = 0
            for i, entry in enumerate(policies_list):
                if entry.get("symbol") == symbol and entry.get("status") == "ACTIVE":
                    policies_list[i] = {**entry, "status": "REVOKED", "revoked_at": now_str}
                    revoked_count += 1
            existing["operator_policies"] = policies_list
            existing["_updated"] = now_str
            state_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            self._json_response({"ok": True, "revoked_count": revoked_count, "symbol": symbol})
        elif path == "/api/danelfin/browser-capture":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            if not isinstance(payload, dict):
                self._json_response({"error": "payload must be a JSON object"}, 400)
                return
            try:
                result = _run_browser_capture(payload)
                self._json_response(result, extra_headers=self._cors_headers())
            except ValueError as exc:
                self._json_response({"error": str(exc)}, 422, extra_headers=self._cors_headers())
            except Exception as exc:
                self._json_response({"error": f"capture_failed: {exc}"}, 500, extra_headers=self._cors_headers())
        elif path == "/api/danelfin/browser-capture/diagnostic-status":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400, extra_headers=self._cors_headers())
                return
            if not isinstance(payload, dict):
                self._json_response({"error": "payload must be a JSON object"}, 400, extra_headers=self._cors_headers())
                return

            run_id = str(payload.get("diagnostic_run_id") or "").strip()
            event = str(payload.get("event") or "").strip()
            if not run_id or not event:
                self._json_response({"error": "diagnostic_run_id and event are required"}, 422, extra_headers=self._cors_headers())
                return

            try:
                state = _record_danelfin_diag_event(
                    run_id,
                    event,
                    error=str(payload.get("error") or "").strip() or None,
                    url=str(payload.get("url") or "").strip() or None,
                    payload={
                        key: value
                        for key, value in payload.items()
                        if key not in {"diagnostic_run_id", "event", "error", "url"}
                    },
                )
                self._json_response({"status": "ok", "diagnostic": state}, extra_headers=self._cors_headers())
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500, extra_headers=self._cors_headers())
        elif path == "/api/danelfin/browser-capture/production-status":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400, extra_headers=self._cors_headers())
                return
            if not isinstance(payload, dict):
                self._json_response({"error": "payload must be a JSON object"}, 400, extra_headers=self._cors_headers())
                return

            run_id = str(payload.get("run_id") or payload.get("diagnostic_run_id") or "").strip()
            event = str(payload.get("event") or "").strip()
            if not run_id or not event:
                self._json_response({"error": "run_id and event are required"}, 422, extra_headers=self._cors_headers())
                return

            try:
                state = _record_danelfin_production_event(
                    run_id,
                    event,
                    error=str(payload.get("error") or "").strip() or None,
                    url=str(payload.get("url") or "").strip() or None,
                    payload={
                        key: value
                        for key, value in payload.items()
                        if key not in {"run_id", "diagnostic_run_id", "event", "error", "url"}
                    },
                )
                self._json_response({"status": "ok", "run": state}, extra_headers=self._cors_headers())
            except KeyError:
                self._json_response({"error": "production run not found"}, 404, extra_headers=self._cors_headers())
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500, extra_headers=self._cors_headers())
        elif path == "/api/danelfin/browser-capture/production-queue/prepare":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400, extra_headers=self._cors_headers())
                return
            if not isinstance(payload, dict):
                self._json_response({"error": "payload must be a JSON object"}, 400, extra_headers=self._cors_headers())
                return
            symbols = payload.get("symbols")
            if not isinstance(symbols, list):
                self._json_response({"error": "symbols must be an array"}, 422, extra_headers=self._cors_headers())
                return

            try:
                prepared = _prepare_danelfin_production_run(
                    [str(item) for item in symbols],
                    source=str(payload.get("source") or "").strip(),
                )
                self._json_response(prepared, extra_headers=self._cors_headers())
            except ValueError as exc:
                self._json_response({"error": str(exc)}, 422, extra_headers=self._cors_headers())
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500, extra_headers=self._cors_headers())
        elif path == "/api/danelfin/browser-capture/production-queue/claim":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400, extra_headers=self._cors_headers())
                return
            if not isinstance(payload, dict):
                self._json_response({"error": "payload must be a JSON object"}, 400, extra_headers=self._cors_headers())
                return

            run_id = str(payload.get("run_id") or "").strip()
            worker_id = str(payload.get("worker_id") or "").strip()
            if not run_id:
                self._json_response({"error": "run_id is required"}, 422, extra_headers=self._cors_headers())
                return

            try:
                claimed_payload = _claim_prepared_danelfin_production_run(run_id, worker_id=worker_id)
                if claimed_payload is None:
                    self._json_response(
                        {
                            "status": "ok",
                            "provider": "danelfin",
                            "diagnostic": False,
                            "mode": "production",
                            "dry_run": False,
                            "jobs": [],
                            "job_count": 0,
                            "run_id": run_id,
                            "generated_at_utc": _utc_now_iso(),
                        },
                        extra_headers=self._cors_headers(),
                    )
                    return
                self._json_response(claimed_payload, extra_headers=self._cors_headers())
            except ValueError as exc:
                self._json_response({"error": str(exc)}, 422, extra_headers=self._cors_headers())
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500, extra_headers=self._cors_headers())
        elif path == "/api/danelfin/browser-capture/diagnostic-queue/claim":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400, extra_headers=self._cors_headers())
                return
            if not isinstance(payload, dict):
                self._json_response({"error": "payload must be a JSON object"}, 400, extra_headers=self._cors_headers())
                return

            run_id = str(payload.get("diagnostic_run_id") or "").strip()
            worker_id = str(payload.get("worker_id") or "").strip()
            if not run_id:
                self._json_response({"error": "diagnostic_run_id is required"}, 422, extra_headers=self._cors_headers())
                return

            try:
                claimed_payload = _claim_prepared_danelfin_diagnostic_run(run_id, worker_id=worker_id)
                if claimed_payload is None:
                    self._json_response(
                        {
                            "status": "ok",
                            "provider": "danelfin",
                            "diagnostic": True,
                            "jobs": [],
                            "job_count": 0,
                            "diagnostic_run_id": run_id,
                            "generated_at_utc": _utc_now_iso(),
                        },
                        extra_headers=self._cors_headers(),
                    )
                    return
                self._json_response(claimed_payload, extra_headers=self._cors_headers())
            except ValueError as exc:
                self._json_response({"error": str(exc)}, 422, extra_headers=self._cors_headers())
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500, extra_headers=self._cors_headers())
        else:
            self.send_error(404)

    def _cors_headers(self) -> dict[str, str]:
        origin = _capture_cors_origin(self)
        if not origin:
            return {}
        return {
            "Access-Control-Allow-Origin": origin,
            "Vary": "Origin",
        }

    def _json_response(self, data: dict, status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
        clean_data = _sanitize_for_json(data)
        body = json.dumps(clean_data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # type: ignore[override]
        # Suppress noisy polling requests from the UI
        if args and "/api/signal-refresh/status" in str(args[0]):
            return
        super().log_message(fmt, *args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local server for outcome visualization prototype UI.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local HTTP server.")
    return parser.parse_args()


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    args = parse_args()

    with _ThreadingTCPServer(("127.0.0.1", args.port), _Handler) as httpd:
        print("Outcome UI server started")
        print(f"Repository root: {_REPO_ROOT}")
        print(f"Open: http://127.0.0.1:{args.port}/ui/outcome_visualization/index.html")
        try:
            os.chdir(_REPO_ROOT)
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
