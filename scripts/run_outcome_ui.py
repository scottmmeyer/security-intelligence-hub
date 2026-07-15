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
import concurrent.futures
import csv
import http.server
import io
import json
import math
import os
import re
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


def _refresh_status_payload(running: bool) -> dict:
    global _refresh_last_report, _refresh_last_exit_code, _refresh_completed_at_utc

    if not running and _refresh_proc is not None:
        exit_code = _refresh_proc.poll()
        if exit_code is not None:
            _refresh_last_exit_code = int(exit_code)
            _refresh_completed_at_utc = datetime.now(timezone.utc).isoformat()
            if _REFRESH_REPORT_PATH.exists():
                try:
                    _refresh_last_report = json.loads(_REFRESH_REPORT_PATH.read_text(encoding="utf-8"))
                except Exception:
                    _refresh_last_report = None

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

    scope_formula = _refresh_scope_formula(_refresh_scope_summary if isinstance(_refresh_scope_summary, dict) else {}, _refresh_resolved_intent)
    replay_publish = None
    dedicated_proxy_history = None
    dedicated_proxy_build = None
    if isinstance(_refresh_last_report, dict):
        replay_publish = _refresh_last_report.get("market_proxy_replay_publish")
        dedicated_proxy_history = _refresh_last_report.get("market_regime_proxy_history_fetch")
        dedicated_proxy_build = _refresh_last_report.get("market_regime_proxy_artifact_build")
    return {
        "running": running,
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
        "started_at_utc": _refresh_started_at_utc,
        "completed_at_utc": _refresh_completed_at_utc,
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
    result: dict[str, dict] = {}
    for name, path in _SIGNAL_FILES.items():
        sd = _sourced_date(path)
        entry: dict = {
            "sourced_date": sd,
            "stale": sd != today,
            "exists": path.exists(),
        }

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

        if path.exists() and sd == today:
            try:
                today_rows: list[dict] = []
                with path.open("r", encoding="utf-8", newline="") as fh:
                    for row in csv.DictReader(fh):
                        if str(row.get("sourced_date", "")).strip() == today:
                            today_rows.append(row)
                attempted = len(today_rows)
                with_data = sum(
                    1 for r in today_rows if any(r.get(f, "").strip() for f in primary_fields)
                ) if primary_fields else attempted
                coverage_pct = round(with_data / attempted * 100, 1) if attempted else 0.0
                field_coverage: dict[str, float] = {}
                for field in all_fields:
                    n = sum(1 for r in today_rows if r.get(field, "").strip())
                    field_coverage[field] = round(n / attempted * 100, 1) if attempted else 0.0
                degraded = [f for f in primary_fields if field_coverage.get(f, 100) == 0.0]
                zero_fields = [f for f in all_fields if field_coverage.get(f, 100) == 0.0]

                entry["attempted_count"] = attempted
                entry["with_data_count"] = with_data
                entry["coverage_pct"] = coverage_pct
                entry["primary_field_coverage"] = {f: field_coverage[f] for f in primary_fields}
                entry["degraded_fields"] = degraded
                entry["zero_coverage_fields"] = zero_fields
                entry["badge_state"] = "FRESH_PARTIAL" if coverage_pct < 95.0 or degraded else "FRESH"
            except Exception:
                entry["badge_state"] = "FRESH"
        elif sd == today:
            entry["badge_state"] = "FRESH"
        else:
            entry["badge_state"] = "STALE"

        result[name] = entry

    try:
        if str(_REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(_REPO_ROOT))
        from src.portfolio.holdings_coverage import summarize_holdings_coverage

        holdings_providers: dict[str, dict] = {}
        holdings_run_id: str | None = None
        holdings_baseline = 0
        for provider_name in ("zacks", "danelfin", "yahoo"):
            summary = summarize_holdings_coverage(
                provider=provider_name,
                latest_csv=_SIGNAL_FILES[provider_name],
                analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
                base_universe_csv=_REPO_ROOT / "data" / "current" / "base_equity_universe.csv",
                threshold_days=2,
            )
            holdings_run_id = holdings_run_id or str(summary.get("run_id") or "") or None
            holdings_baseline = max(holdings_baseline, int(summary.get("active_holdings_baseline") or 0))
            holdings_providers[provider_name] = summary
            if provider_name in result:
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
            "ess": _provider_cell(signal_data.get("ess") if isinstance(signal_data.get("ess"), dict) else {}, "ess"),
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


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Static file handler extended with /api/* JSON endpoints."""

    def do_GET(self) -> None:  # type: ignore[override]
        global _refresh_proc
        path = self.path.split("?")[0]
        if path == "/api/signal-status":
            running = _refresh_proc is not None and _refresh_proc.poll() is None
            data = _signal_status()
            data["_running"] = running
            self._json_response(data)
        elif path == "/api/refresh-transparency":
            self._json_response(_refresh_transparency_payload())
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
        else:
            self.send_error(404)

    def _json_response(self, data: dict, status: int = 200) -> None:
        clean_data = _sanitize_for_json(data)
        body = json.dumps(clean_data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
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
