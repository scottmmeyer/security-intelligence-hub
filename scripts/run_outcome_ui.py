#!/usr/bin/env python3
"""Run a local static + API server for the WP-04.1 outcome visualization prototype.

Static files are served from the repository root.

API endpoints:
  GET  /api/signal-status          → JSON: last sourced_date and staleness per provider
  POST /api/signal-refresh         → launch scripts/refresh_signals.py as background process
    GET  /api/signal-refresh/status  → JSON: running + exit_code + last_report
  POST /api/portfolio/analyze      → ingest + enrich + align portfolio CSV; returns full analysis
  GET  /api/portfolio/runs         → list all completed portfolio analysis runs
  GET  /api/portfolio/runs/{id}    → load a specific analysis run by run_id
  GET  /api/cpv/latest             → current portfolio compliance validator results
  GET  /api/drift/summary          → allocation drift summary (CPV trend table + banner data)
  GET  /api/drift/timeline         → time series for a single CPV rule (?rule_id=CPV-01)
  GET  /api/signal-conflicts       → advisory conflict badges for symbols (?symbols=VRT,NUE,...)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
from datetime import date, datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_SIGNAL_FILES = {
    "zacks":    _REPO_ROOT / "data/signals/zacks/latest_zacks.csv",
    "danelfin": _REPO_ROOT / "data/signals/danelfin/latest_danelfin.csv",
    "yahoo":    _REPO_ROOT / "data/signals/yahoo/latest_yahoo_supplemental.csv",
}
_ESS_SIGNAL_SNAPSHOT = _REPO_ROOT / "data/current/signal_snapshot.csv"
_ESS_COVERAGE_WARNING = _REPO_ROOT / "data/current/ess_coverage_warning.json"
_REFRESH_REPORT_PATH = _REPO_ROOT / "data" / "current" / "last_signal_refresh_report.json"

# Background refresh process handle (module-level so Handler instances share it)
_refresh_proc: subprocess.Popen | None = None
_refresh_last_report: dict | None = None
_refresh_last_exit_code: int | None = None
_refresh_started_at_utc: datetime | None = None
_refresh_completed_at_utc: datetime | None = None
_refresh_mode: str | None = None
_refresh_log_lines: list[str] = []
_refresh_log_lock = threading.Lock()

# On-demand score fetch jobs keyed by symbol (uppercase)
_fetch_jobs: dict[str, dict] = {}
_fetch_lock = threading.Lock()

_SYMBOL_RE = re.compile(r"^[A-Z0-9./\-]{1,12}$")
_PROVIDER_PROGRESS_RE = re.compile(
    r"^\[(\d+)\s*/\s*(\d+)\]\s+Fetching\s+([A-Za-z0-9_\- ]+)\s+data\s+for\s+([A-Z0-9./\-]+)",
    re.IGNORECASE,
)
_ANALYTICAL_UNIVERSE_CSV = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
_FMP_UNIVERSE_CSV = _REPO_ROOT / "data" / "signals" / "fmp" / "latest" / "latest_fmp_enriched_universe.csv"
_MANIFEST_PATH = _REPO_ROOT / "data" / "portfolio_ingestion" / "manifest.json"
_RUNS_ROOT = _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs"
_FRESHNESS_THRESHOLD_DAYS = 2


def _capture_refresh_output(proc: subprocess.Popen) -> None:
    """Capture refresh subprocess output for live progress telemetry."""
    stream = proc.stdout
    if stream is None:
        return
    try:
        for raw in stream:
            line = str(raw).rstrip()
            if not line:
                continue
            with _refresh_log_lock:
                _refresh_log_lines.append(line)
                if len(_refresh_log_lines) > 200:
                    del _refresh_log_lines[: len(_refresh_log_lines) - 200]
    except Exception:
        return


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded HTTP server so slow requests do not block unrelated endpoints."""

    daemon_threads = True


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


def _sanitize_nan(obj: object) -> object:
    """Recursively replace NaN/Inf floats with None so JSON serialization succeeds."""
    if isinstance(obj, float):
        import math
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_nan(v) for v in obj]
    return obj


def _attach_explanations(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    run_id = str(result.get("run_id", "")).strip()
    if not run_id:
        return result
    try:
        import sys as _sys
        if str(_REPO_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_REPO_ROOT))
        from src.sih.allocation_explainability import (
            explanations_for_run,
            refresh_allocation_explanations,
        )

        refresh_allocation_explanations(
            analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
            output_root=_REPO_ROOT / "data" / "history" / "explanations",
        )
        result["explanations_by_recommendation"] = explanations_for_run(
            run_id,
            analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
            output_root=_REPO_ROOT / "data" / "history" / "explanations",
        )
    except Exception:
        result["explanations_by_recommendation"] = {}
    return result


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
        # ── SI-REFRESH-02: Add coverage metrics ──────────────────────────────
        # Primary fields define data quality; 0% coverage on any primary field
        # indicates a silent partial failure even when sourced_date == today.
        _PRIMARY_FIELDS: dict[str, list[str]] = {
            "zacks":    ["zacks_rank", "zacks_score"],
            "danelfin": ["danelfin_raw", "danelfin_score"],
            "yahoo":    ["price_target", "analyst_count", "current_price"],
        }
        _ALL_SCORE_FIELDS: dict[str, list[str]] = {
            "zacks":    ["zacks_rank", "zacks_score", "abr", "price_target", "eps_growth"],
            "danelfin": ["danelfin_raw", "danelfin_score"],
            "yahoo":    ["price_target", "abr", "analyst_count", "current_price",
                         "upside_pct", "eps_growth_5yr"],
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
                # "with data" = row has at least one primary field non-empty
                with_data = sum(
                    1 for r in today_rows
                    if any(r.get(f, "").strip() for f in primary_fields)
                ) if primary_fields else attempted
                coverage_pct = round(with_data / attempted * 100, 1) if attempted else 0.0
                # Per-field coverage on score fields
                field_coverage: dict[str, float] = {}
                for f in all_fields:
                    n = sum(1 for r in today_rows if r.get(f, "").strip())
                    field_coverage[f] = round(n / attempted * 100, 1) if attempted else 0.0
                # Degraded fields = primary fields with 0% coverage today
                degraded = [f for f in primary_fields if field_coverage.get(f, 100) == 0.0]
                # All score fields with 0% coverage (for extended reporting)
                zero_fields = [f for f in all_fields if field_coverage.get(f, 100) == 0.0]

                entry["attempted_count"]     = attempted
                entry["with_data_count"]     = with_data
                entry["coverage_pct"]        = coverage_pct
                entry["primary_field_coverage"] = {
                    f: field_coverage[f] for f in primary_fields
                }
                entry["degraded_fields"]     = degraded  # primary fields at 0%
                entry["zero_coverage_fields"] = zero_fields  # all fields at 0%

                # Badge state
                # FRESH: today, ≥95% row coverage, no primary field at 0%
                # FRESH_PARTIAL: today but coverage <95% OR a primary field at 0%
                if coverage_pct < 95.0 or degraded:
                    entry["badge_state"] = "FRESH_PARTIAL"
                else:
                    entry["badge_state"] = "FRESH"
            except Exception:
                entry["badge_state"] = "FRESH"  # degrade gracefully
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


def _parse_iso_date(value: str | None) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except Exception:
        return None


def _load_provider_rows(csv_path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if not csv_path.exists():
        return rows
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    rows[sym] = row
    except Exception:
        return {}
    return rows


def _is_provider_value_present(row: dict[str, str], primary_fields: list[str]) -> bool:
    if not primary_fields:
        return True
    return any(str(row.get(field, "")).strip() for field in primary_fields)


def _classify_provider_freshness(
    symbol: str,
    provider_rows: dict[str, dict[str, str]],
    *,
    date_field: str,
    primary_fields: list[str],
    today: date,
) -> dict[str, object]:
    row = provider_rows.get(symbol)
    if row is None:
        return {"state": "missing", "date": None, "age_days": None}
    if not _is_provider_value_present(row, primary_fields):
        return {"state": "missing", "date": str(row.get(date_field, "") or "") or None, "age_days": None}
    sourced = _parse_iso_date(row.get(date_field))
    if sourced is None:
        return {"state": "missing", "date": str(row.get(date_field, "") or "") or None, "age_days": None}
    age_days = max((today - sourced).days, 0)
    return {
        "state": "fresh" if age_days <= _FRESHNESS_THRESHOLD_DAYS else "stale",
        "date": sourced.isoformat(),
        "age_days": age_days,
    }


def _latest_candidate_run_id() -> str | None:
    if not _MANIFEST_PATH.exists():
        return None
    try:
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    portfolios = manifest.get("portfolios") if isinstance(manifest, dict) else []
    if not isinstance(portfolios, list):
        return None
    candidates: list[tuple[str, str, str]] = []
    for entry in portfolios:
        if not isinstance(entry, dict):
            continue
        run_id = str(entry.get("run_id") or "").strip()
        if not run_id:
            continue
        run_dir = _RUNS_ROOT / run_id
        if not (run_dir / "deployment_queue.json").exists():
            continue
        if not (run_dir / "ucf_verdicts.json").exists():
            continue
        if not (run_dir / "recommendations.json").exists():
            continue
        candidates.append(
            (
                str(entry.get("snapshot_date") or ""),
                str(entry.get("created_at_utc") or ""),
                run_id,
            )
        )
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _candidate_symbols_from_run(run_id: str) -> dict[str, list[str]]:
    run_dir = _RUNS_ROOT / run_id
    queue_json = _load_json(run_dir / "deployment_queue.json") or {}
    ucf_json = _load_json(run_dir / "ucf_verdicts.json") or {}
    rec_json = _load_json(run_dir / "recommendations.json") or []

    queue_rows = []
    if isinstance(queue_json, dict):
        queue_rows = list(queue_json.get("queue") or queue_json.get("deployment_queue") or [])
    queue_symbols = [str(r.get("symbol") or "").strip().upper() for r in queue_rows if isinstance(r, dict)]

    verdict_rows = []
    if isinstance(ucf_json, dict):
        verdict_rows = list(ucf_json.get("verdicts") or [])
    elif isinstance(ucf_json, list):
        verdict_rows = list(ucf_json)
    ucf_symbols = [str(r.get("symbol") or "").strip().upper() for r in verdict_rows if isinstance(r, dict)]

    recommendation_rows = list(rec_json) if isinstance(rec_json, list) else []
    recommendation_primary: list[str] = []
    recommendation_all: list[str] = []
    for row in recommendation_rows:
        if not isinstance(row, dict):
            continue
        affected = row.get("affected_symbols") or []
        if isinstance(affected, list) and affected:
            first = str(affected[0] or "").strip().upper()
            if first:
                recommendation_primary.append(first)
            for sym in affected:
                norm = str(sym or "").strip().upper()
                if norm:
                    recommendation_all.append(norm)

    def _unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for value in values:
            if value and value not in seen:
                out.append(value)
                seen.add(value)
        return out

    return {
        "cw_das": _unique(queue_symbols),
        "ucf": _unique(ucf_symbols),
        "recommendations_primary": _unique(recommendation_primary),
        "recommendations_all": _unique(recommendation_all),
    }


def _load_cra_symbols_from_latest_proposal() -> list[str]:
    try:
        import sys as _sys
        if str(_REPO_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_REPO_ROOT))
        from src.portfolio.cra.rotation_proposal_builder import build_proposal_from_manifest

        if not _MANIFEST_PATH.exists():
            return []
        tax_state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"
        proposal = build_proposal_from_manifest(
            manifest_path=_MANIFEST_PATH,
            runs_root=_RUNS_ROOT,
            tax_state_path=tax_state_path if tax_state_path.exists() else None,
        )
        if proposal is None:
            return []
        deployments = proposal.to_dict().get("deployments") or []
        return [str(row.get("symbol") or "").strip().upper() for row in deployments if isinstance(row, dict)]
    except Exception:
        return []


def _read_research_universe_symbols() -> list[str]:
    if not _ANALYTICAL_UNIVERSE_CSV.exists():
        return []
    symbols: list[str] = []
    try:
        with _ANALYTICAL_UNIVERSE_CSV.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol") or "").strip().upper()
                if sym:
                    symbols.append(sym)
    except Exception:
        return []
    seen: set[str] = set()
    unique: list[str] = []
    for sym in symbols:
        if sym not in seen:
            unique.append(sym)
            seen.add(sym)
    return unique


def _readiness_status(fresh_pct: float, stale_or_missing_count: int) -> str:
    if fresh_pct >= 95.0 and stale_or_missing_count <= 1:
        return "HIGH"
    if fresh_pct >= 80.0:
        return "MEDIUM"
    return "LOW"


def _compute_candidate_transparency_payload() -> dict[str, object]:
    today = date.today()
    provider_maps = {
        "zacks": {
            "rows": _load_provider_rows(_SIGNAL_FILES["zacks"]),
            "date_field": "sourced_date",
            "primary_fields": ["zacks_rank", "zacks_score"],
        },
        "danelfin": {
            "rows": _load_provider_rows(_SIGNAL_FILES["danelfin"]),
            "date_field": "sourced_date",
            "primary_fields": ["danelfin_raw", "danelfin_score"],
        },
        "yahoo": {
            "rows": _load_provider_rows(_SIGNAL_FILES["yahoo"]),
            "date_field": "sourced_date",
            "primary_fields": ["price_target", "analyst_count", "current_price"],
        },
        "ess": {
            "rows": _load_provider_rows(_ESS_SIGNAL_SNAPSHOT),
            "date_field": "snapshot_date",
            "primary_fields": ["signal_coverage_status", "starmine_ess_text"],
        },
        "fmp": {
            "rows": _load_provider_rows(_FMP_UNIVERSE_CSV),
            "date_field": "fmp_sourced_date",
            "primary_fields": ["fmp_coverage_status"],
        },
    }

    run_id = _latest_candidate_run_id()
    symbol_sets = {
        "cw_das": [],
        "ucf": [],
        "recommendations_primary": [],
        "recommendations_all": [],
        "cra": [],
        "research_universe": _read_research_universe_symbols(),
    }
    if run_id:
        symbol_sets.update(_candidate_symbols_from_run(run_id))
    symbol_sets["cra"] = sorted({s for s in _load_cra_symbols_from_latest_proposal() if s})

    def _core_state(symbol: str) -> bool:
        z = _classify_provider_freshness(
            symbol,
            provider_maps["zacks"]["rows"],
            date_field=str(provider_maps["zacks"]["date_field"]),
            primary_fields=list(provider_maps["zacks"]["primary_fields"]),
            today=today,
        )
        d = _classify_provider_freshness(
            symbol,
            provider_maps["danelfin"]["rows"],
            date_field=str(provider_maps["danelfin"]["date_field"]),
            primary_fields=list(provider_maps["danelfin"]["primary_fields"]),
            today=today,
        )
        y = _classify_provider_freshness(
            symbol,
            provider_maps["yahoo"]["rows"],
            date_field=str(provider_maps["yahoo"]["date_field"]),
            primary_fields=list(provider_maps["yahoo"]["primary_fields"]),
            today=today,
        )
        return z.get("state") == "fresh" and d.get("state") == "fresh" and y.get("state") == "fresh"

    def _metric_for_set(label: str, symbols: list[str]) -> dict[str, object]:
        total = len(symbols)
        core_fresh = sum(1 for sym in symbols if _core_state(sym))
        stale_or_missing = max(total - core_fresh, 0)
        pct = round((core_fresh / total * 100.0), 1) if total else 0.0
        return {
            "label": label,
            "total": total,
            "core_fresh": core_fresh,
            "stale_or_missing": stale_or_missing,
            "core_fresh_pct": pct,
            "status": _readiness_status(pct, stale_or_missing),
        }

    readiness = {
        "research_universe": _metric_for_set("Research Universe", symbol_sets["research_universe"]),
        "cw_das": _metric_for_set("CW-DAS Queue", symbol_sets["cw_das"]),
        "ucf": _metric_for_set("UCF Ranked", symbol_sets["ucf"]),
        "recommendations": _metric_for_set("Recommendations", symbol_sets["recommendations_primary"]),
        "cra": _metric_for_set("CRA Deployments", symbol_sets["cra"]),
    }

    rows_by_symbol: dict[str, dict[str, object]] = {}
    source_sets = {
        "cw_das": set(symbol_sets["cw_das"]),
        "ucf": set(symbol_sets["ucf"]),
        "recommendations": set(symbol_sets["recommendations_all"]),
        "cra": set(symbol_sets["cra"]),
    }
    table_symbols = sorted(set().union(*source_sets.values())) if source_sets else []
    for sym in table_symbols:
        z = _classify_provider_freshness(
            sym,
            provider_maps["zacks"]["rows"],
            date_field=str(provider_maps["zacks"]["date_field"]),
            primary_fields=list(provider_maps["zacks"]["primary_fields"]),
            today=today,
        )
        d = _classify_provider_freshness(
            sym,
            provider_maps["danelfin"]["rows"],
            date_field=str(provider_maps["danelfin"]["date_field"]),
            primary_fields=list(provider_maps["danelfin"]["primary_fields"]),
            today=today,
        )
        y = _classify_provider_freshness(
            sym,
            provider_maps["yahoo"]["rows"],
            date_field=str(provider_maps["yahoo"]["date_field"]),
            primary_fields=list(provider_maps["yahoo"]["primary_fields"]),
            today=today,
        )
        e = _classify_provider_freshness(
            sym,
            provider_maps["ess"]["rows"],
            date_field=str(provider_maps["ess"]["date_field"]),
            primary_fields=list(provider_maps["ess"]["primary_fields"]),
            today=today,
        )
        f = _classify_provider_freshness(
            sym,
            provider_maps["fmp"]["rows"],
            date_field=str(provider_maps["fmp"]["date_field"]),
            primary_fields=list(provider_maps["fmp"]["primary_fields"]),
            today=today,
        )
        core_fresh = z.get("state") == "fresh" and d.get("state") == "fresh" and y.get("state") == "fresh"
        full_fresh = core_fresh and e.get("state") == "fresh" and f.get("state") == "fresh"
        freshness = "FULL_FRESH" if full_fresh else ("CORE_FRESH" if core_fresh else "CORE_PARTIAL")
        rows_by_symbol[sym] = {
            "symbol": sym,
            "sources": {
                "cw_das": sym in source_sets["cw_das"],
                "ucf": sym in source_sets["ucf"],
                "recommendations": sym in source_sets["recommendations"],
                "cra": sym in source_sets["cra"],
            },
            "zacks": z,
            "danelfin": d,
            "yahoo": y,
            "ess": e,
            "fmp": f,
            "freshness": freshness,
        }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "threshold_days": _FRESHNESS_THRESHOLD_DAYS,
        "run_id": run_id,
        "readiness": readiness,
        "rows": [rows_by_symbol[k] for k in sorted(rows_by_symbol.keys())],
    }


def _parse_provider_progress_line(line: str) -> dict[str, object]:
    raw = str(line or "").strip()
    if not raw:
        return {
            "provider_stage": None,
            "stage_progress_current": None,
            "stage_progress_total": None,
            "current_symbol": None,
        }
    m = _PROVIDER_PROGRESS_RE.match(raw)
    if not m:
        return {
            "provider_stage": None,
            "stage_progress_current": None,
            "stage_progress_total": None,
            "current_symbol": None,
        }
    provider = str(m.group(3) or "").strip().title()
    current = int(m.group(1))
    total = int(m.group(2))
    symbol = str(m.group(4) or "").strip().upper()
    return {
        "provider_stage": provider,
        "stage_progress_current": current,
        "stage_progress_total": total,
        "current_symbol": symbol,
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
        elif path == "/api/pis/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.storage import pis_dashboard_summary, pis_value_timeline

                payload = pis_dashboard_summary(repo_root=_REPO_ROOT)
                payload["timeline"] = pis_value_timeline()
                self._json_response(payload)
            except Exception as exc:
                self._json_response(
                    {
                        "health": {
                            "first_snapshot_date": "",
                            "latest_snapshot_date": "",
                            "snapshot_count": 0,
                            "missing_days": 0,
                            "duplicate_uploads_prevented": 0,
                        },
                        "lineage": {
                            "total_sih_analyses_captured": 0,
                            "latest_par": "",
                            "latest_mandate": "",
                            "latest_upload_date": "",
                        },
                        "timeline": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/snapshots":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.storage import pis_snapshot_inventory

                self._json_response({"snapshots": pis_snapshot_inventory()})
            except Exception as exc:
                self._json_response({"snapshots": [], "error": str(exc)}, 200)
        elif path == "/api/pis/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.storage import pis_latest_snapshot_summary

                self._json_response(pis_latest_snapshot_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {
                        "snapshot_date": "",
                        "total_value": 0.0,
                        "cash": 0.0,
                        "position_count": 0,
                        "largest_holdings": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/health":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.storage import pis_snapshot_history_health

                self._json_response(pis_snapshot_history_health())
            except Exception as exc:
                self._json_response(
                    {
                        "first_snapshot_date": "",
                        "latest_snapshot_date": "",
                        "snapshot_count": 0,
                        "missing_days": 0,
                        "duplicate_uploads_prevented": 0,
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/governance/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.governance import pis_governance_latest

                self._json_response(pis_governance_latest())
            except Exception as exc:
                self._json_response(
                    {
                        "generated_at_utc": "",
                        "latest_snapshot_date": "",
                        "status_counts": {"PASS": 0, "WARNING": 0, "REJECT": 0},
                        "snapshots": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/governance-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.governance import pis_governance_summary

                self._json_response(pis_governance_summary())
            except Exception as exc:
                self._json_response(
                    {
                        "generated_at_utc": "",
                        "total_snapshots": 0,
                        "status_counts": {"PASS": 0, "WARNING": 0, "REJECT": 0},
                        "daily": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/canonical/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.canonical_daily import pis_canonical_latest

                self._json_response(pis_canonical_latest())
            except Exception as exc:
                self._json_response(
                    {
                        "generated_at_utc": "",
                        "latest": {
                            "snapshot_date": "",
                            "canonical_snapshot_id": "",
                            "governance_status": "",
                            "selection_policy": "",
                            "selection_reason": "",
                            "source_file": "",
                            "portfolio_value": 0.0,
                            "cash": 0.0,
                            "position_count": 0,
                        },
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/canonical/history":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.canonical_daily import pis_canonical_history

                self._json_response(pis_canonical_history())
            except Exception as exc:
                self._json_response(
                    {
                        "generated_at_utc": "",
                        "history": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/canonical-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.canonical_daily import pis_canonical_summary

                self._json_response(pis_canonical_summary())
            except Exception as exc:
                self._json_response(
                    {
                        "generated_at_utc": "",
                        "total_dates": 0,
                        "selected_dates": 0,
                        "unselected_dates": 0,
                        "selected_status_counts": {"PASS": 0, "WARNING": 0, "REJECT": 0},
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/status":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.storage import summarize_portfolio_history

                self._json_response(summarize_portfolio_history())
            except Exception as exc:
                self._json_response({"error": str(exc), "snapshot_count": 0, "position_count": 0, "account_count": 0}, 200)
        elif path == "/api/pis/changes/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.change_detection import pis_changes_latest

                self._json_response(pis_changes_latest(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {
                        "summary": None,
                        "new_positions": [],
                        "exited_positions": [],
                        "increased_positions": [],
                        "reduced_positions": [],
                        "unchanged_positions": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/change-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.change_detection import pis_change_summary

                self._json_response(pis_change_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"summary": [], "error": str(exc)}, 200)
        elif path == "/api/pis/lineage/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.recommendation_lineage import pis_lineage_latest

                self._json_response(pis_lineage_latest(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"summary": None, "matches": [], "unmatched": [], "source_breakdown": [], "error": str(exc)}, 200)
        elif path == "/api/pis/lineage-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.recommendation_lineage import pis_lineage_summary

                self._json_response(pis_lineage_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"summary": [], "error": str(exc)}, 200)
        elif path == "/api/pis/attribution/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.performance_attribution import pis_attribution_latest

                self._json_response(pis_attribution_latest(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {
                        "summary": None,
                        "records": [],
                        "top_winning_recommendations": [],
                        "top_losing_recommendations": [],
                        "source_performance": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/attribution/history":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.performance_attribution import pis_attribution_history

                self._json_response(pis_attribution_history(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"summary": [], "error": str(exc)}, 200)
        elif path == "/api/pis/attribution-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.performance_attribution import pis_attribution_summary

                self._json_response(pis_attribution_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {
                        "summary": {
                            "snapshot_count": 0,
                            "matched_recommendations": 0,
                            "winner_count": 0,
                            "neutral_count": 0,
                            "loser_count": 0,
                            "total_directional_attribution": 0.0,
                            "average_directional_return_pct": 0.0,
                        },
                        "top_winning_recommendations": [],
                        "top_losing_recommendations": [],
                        "source_performance": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/benchmark-attribution/returns":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.benchmark_attribution import pis_benchmark_returns

                self._json_response(pis_benchmark_returns())
            except Exception as exc:
                self._json_response(
                    {
                        "benchmark_symbol": "SPY",
                        "alignment_policy": "NEAREST_PRIOR_TRADING_DAY",
                        "generated_at_utc": "",
                        "series": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/benchmark-attribution/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.benchmark_attribution import pis_benchmark_latest

                self._json_response(pis_benchmark_latest())
            except Exception as exc:
                self._json_response(
                    {
                        "benchmark_symbol": "SPY",
                        "alignment_policy": "NEAREST_PRIOR_TRADING_DAY",
                        "latest_portfolio_excess_return": None,
                        "top_positive_alpha_recommendations": [],
                        "worst_negative_alpha_recommendations": [],
                        "source_alpha_ranking": [],
                        "quality": {
                            "included_rows": 0,
                            "excluded_rows": 0,
                            "excluded_reason_counts": {},
                        },
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/benchmark-attribution/recommendations":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.benchmark_attribution import pis_benchmark_recommendations

                self._json_response(pis_benchmark_recommendations())
            except Exception as exc:
                self._json_response(
                    {
                        "benchmark_symbol": "SPY",
                        "records": [],
                        "quality": {
                            "included_rows": 0,
                            "excluded_rows": 0,
                            "excluded_reason_counts": {},
                        },
                        "generated_at_utc": "",
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/benchmark-attribution/sources":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.benchmark_attribution import pis_benchmark_sources

                self._json_response(pis_benchmark_sources())
            except Exception as exc:
                self._json_response(
                    {
                        "benchmark_symbol": "SPY",
                        "source_summary": [],
                        "quality": {
                            "included_rows": 0,
                            "excluded_rows": 0,
                            "excluded_reason_counts": {},
                        },
                        "generated_at_utc": "",
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/benchmark-attribution-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.benchmark_attribution import pis_benchmark_summary

                self._json_response(pis_benchmark_summary())
            except Exception as exc:
                self._json_response(
                    {
                        "benchmark_symbol": "SPY",
                        "alignment_policy": "NEAREST_PRIOR_TRADING_DAY",
                        "summary": {
                            "interval_count": 0,
                            "ok_interval_count": 0,
                            "missing_interval_count": 0,
                            "latest_snapshot_date": "",
                            "average_benchmark_return_pct": 0.0,
                            "average_portfolio_return_pct": 0.0,
                            "average_excess_return_pct": 0.0,
                        },
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/pis/allocation-drift/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.allocation_drift import pis_allocation_drift_summary

                self._json_response(pis_allocation_drift_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"dates_available": 0, "current_date": None, "prior_date": None,
                     "improving_count": 0, "worsening_count": 0, "stable_count": 0,
                     "most_improved_node": None, "most_deteriorated_node": None,
                     "observations": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/allocation-drift/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.allocation_drift import pis_allocation_drift_latest

                self._json_response(pis_allocation_drift_latest(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"dates_available": 0, "current_date": None, "nodes": [], "error": str(exc)},
                    200,
                )
        elif path == "/api/pis/allocation-drift/history":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.allocation_drift import pis_allocation_drift_history

                self._json_response(pis_allocation_drift_history(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"dates": [], "nodes": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/action-attribution/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.action_attribution import pis_action_attribution_summary

                self._json_response(pis_action_attribution_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"total_attribution_records": 0, "followed_count": 0, "ignored_count": 0,
                     "opposed_count": 0, "expired_count": 0, "partially_followed_count": 0,
                     "follow_rate_pct": 0.0, "ignore_rate_pct": 0.0, "oppose_rate_pct": 0.0,
                     "observations": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/action-attribution/recommendations":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.action_attribution import pis_action_attribution_recommendations

                self._json_response(pis_action_attribution_recommendations(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"total": 0, "records": [], "error": str(exc)}, 200)
        elif path == "/api/pis/action-attribution/sources":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.action_attribution import pis_action_attribution_sources

                self._json_response(pis_action_attribution_sources(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"scorecards": [], "missed_opportunities": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/dor/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.dislocation_outcome_review import pis_dor_summary

                self._json_response(pis_dor_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"total_dil_records": 0, "followed_count": 0, "ignored_count": 0,
                     "winner_count": 0, "loser_count": 0, "follow_rate_pct": 0.0,
                     "win_rate_pct": 0.0, "observations": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/dor/cohorts":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.dislocation_outcome_review import pis_dor_cohorts

                self._json_response(pis_dor_cohorts(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"cohorts": [], "missed_winners": [], "error": str(exc)}, 200)
        elif path == "/api/pis/dor/recommendations":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.dislocation_outcome_review import pis_dor_recommendations

                self._json_response(pis_dor_recommendations(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"total": 0, "records": [], "error": str(exc)}, 200)
        elif path == "/api/pis/policy/current":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.policy_version_diff import pis_policy_current

                self._json_response(pis_policy_current(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"policy_id": "", "node_count": 0, "run_count": 0,
                     "observations": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/policy/history":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.policy_version_diff import pis_policy_history

                self._json_response(pis_policy_history(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"version_count": 0, "versions": [], "observations": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/policy/diff":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.policy_version_diff import pis_policy_diff

                self._json_response(pis_policy_diff(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"versions_compared": 0, "has_changes": False, "diffs": [],
                     "observations": [], "error": str(exc)}, 200,
                )
        # ── AI-004B: Policy Change Intelligence ──────────────────────────────
        elif path == "/api/pis/policy/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.policy_change_summary import policy_summary
                self._json_response(policy_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"change_count": 0, "has_changes": False, "error": str(exc)}, 200)
        elif path == "/api/pis/policy/impact":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.policy_change_summary import policy_impact
                self._json_response(policy_impact(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"rec_impact": {}, "before_after": [], "error": str(exc)}, 200)
        elif path == "/api/pis/policy/timeline":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.policy_change_summary import policy_timeline
                self._json_response(policy_timeline(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"timeline": [], "error": str(exc)}, 200)
        elif path.startswith("/api/pis/policy/version/"):
            raw_vid = path[len("/api/pis/policy/version/"):].strip()
            if not raw_vid:
                self._json_response({"error": "version_id required"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.policy_change_summary import policy_version
                self._json_response(policy_version(raw_vid, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"version_id": raw_vid, "error": str(exc)}, 200)
        elif path == "/api/pis/compliance/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.allocation_compliance import pis_compliance_summary

                self._json_response(pis_compliance_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {"total_nodes": 0, "currently_compliant": 0, "currently_warning": 0,
                     "currently_non_compliant": 0, "observations": [], "error": str(exc)}, 200,
                )
        elif path == "/api/pis/compliance/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.allocation_compliance import pis_compliance_latest

                self._json_response(pis_compliance_latest(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"nodes": [], "observations": [], "error": str(exc)}, 200)
        elif path == "/api/pis/compliance/history":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.allocation_compliance import pis_compliance_history

                self._json_response(pis_compliance_history(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"dates": [], "nodes": [], "error": str(exc)}, 200)
        # ── MEI: Market Event Intelligence ───────────────────────────────────
        elif path == "/api/mei/events":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.events import mei_events

                self._json_response(mei_events(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"events": [], "total_events": 0, "error": str(exc)}, 200)
        elif path == "/api/mei/events/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.events import mei_events_summary

                self._json_response(mei_events_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"events_next_14_days": 0, "error": str(exc)}, 200)
        elif path == "/api/mei/exposures":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.exposures import mei_exposures

                self._json_response(mei_exposures(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"event_exposures": [], "error": str(exc)}, 200)
        elif path == "/api/mei/exposures/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.exposures import mei_exposures_summary

                self._json_response(mei_exposures_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"total_events_analyzed": 0, "error": str(exc)}, 200)
        elif path == "/api/mei/recommendation-context":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.recommendation_context import mei_recommendation_context

                self._json_response(mei_recommendation_context(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"items": [], "total_recommendations": 0, "error": str(exc)}, 200)
        elif path == "/api/mei/recommendation-context/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.recommendation_context import mei_recommendation_context_summary

                self._json_response(mei_recommendation_context_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"total_recommendations": 0, "error": str(exc)}, 200)
        elif path == "/api/mei/event-history":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.event_history import mei_event_history

                self._json_response(mei_event_history(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"events": [], "total_events_tracked": 0, "error": str(exc)}, 200)
        elif path == "/api/mei/event-history/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.event_history import mei_event_history_summary

                self._json_response(mei_event_history_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"total_events_tracked": 0, "error": str(exc)}, 200)
        elif path.startswith("/api/mei/security/"):
            symbol = path[len("/api/mei/security/"):].strip().upper()
            if not symbol or not _SYMBOL_RE.match(symbol):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.security_profiles import mei_security_profile

                self._json_response(mei_security_profile(symbol, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"symbol": symbol, "sensitivities": {}, "error": str(exc)}, 200)
        elif path.startswith("/api/mei/security/"):
            symbol = path[len("/api/mei/security/"):].strip().upper()
            if not symbol or not _SYMBOL_RE.match(symbol):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.security_profiles import mei_security_profile

                self._json_response(mei_security_profile(symbol, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"symbol": symbol, "sensitivities": {}, "error": str(exc)}, 200)
        # ── MEI-002: Event Outcome Attribution ───────────────────────────────
        elif path == "/api/mei/outcomes":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.event_outcome_tracker import mei_outcomes
                self._json_response(mei_outcomes(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"event_count": 0, "outcomes": [], "error": str(exc)}, 200)
        elif path.startswith("/api/mei/outcomes/"):
            raw_eid = path[len("/api/mei/outcomes/"):].strip()
            if not raw_eid:
                self._json_response({"error": "event_id required"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.event_outcome_tracker import mei_outcome_by_event
                self._json_response(mei_outcome_by_event(raw_eid, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"error": str(exc)}, 200)
        elif path == "/api/mei/event-impact":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.event_outcome_tracker import mei_event_impact
                self._json_response(mei_event_impact(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"effectiveness": [], "error": str(exc)}, 200)
        elif path == "/api/mei/outcome-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.event_outcome_tracker import mei_outcome_summary
                self._json_response(mei_outcome_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"event_count": 0, "error": str(exc)}, 200)
        # ── end MEI ──────────────────────────────────────────────────────────
        elif path == "/api/pis/refresh/status":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.artifact_freshness import artifact_freshness_report

                self._json_response(artifact_freshness_report())
            except Exception as exc:
                self._json_response(
                    {
                        "latest_pass_snapshot_date": "",
                        "latest_canonical_date": "",
                        "latest_change_date": "",
                        "latest_lineage_date": "",
                        "latest_attribution_date": "",
                        "latest_benchmark_date": "",
                        "canonical_status": "MISSING",
                        "change_status": "MISSING",
                        "lineage_status": "MISSING",
                        "attribution_status": "MISSING",
                        "benchmark_status": "MISSING",
                        "overall_refresh_status": "MISSING",
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/explanations/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.allocation_explainability import explanations_latest, refresh_allocation_explanations

                refresh_allocation_explanations(
                    analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
                    output_root=_REPO_ROOT / "data" / "history" / "explanations",
                )
                self._json_response(explanations_latest(
                    analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
                    output_root=_REPO_ROOT / "data" / "history" / "explanations",
                ))
            except Exception as exc:
                self._json_response({"analysis_run_id": "", "snapshot_date": "", "explanations": [], "summary": None, "error": str(exc)}, 200)
        elif path == "/api/explanations/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.allocation_explainability import explanation_summary, refresh_allocation_explanations

                refresh_allocation_explanations(
                    analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
                    output_root=_REPO_ROOT / "data" / "history" / "explanations",
                )
                self._json_response(explanation_summary(
                    analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
                    output_root=_REPO_ROOT / "data" / "history" / "explanations",
                ))
            except Exception as exc:
                self._json_response({"history": [], "source_summary": {}, "error": str(exc)}, 200)
        elif path.startswith("/api/explanations/"):
            recommendation_id = path[len("/api/explanations/"):].strip()
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.allocation_explainability import explanation_for_recommendation, refresh_allocation_explanations

                refresh_allocation_explanations(
                    analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
                    output_root=_REPO_ROOT / "data" / "history" / "explanations",
                )
                self._json_response(explanation_for_recommendation(
                    recommendation_id,
                    analysis_runs_root=_REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs",
                    output_root=_REPO_ROOT / "data" / "history" / "explanations",
                ))
            except Exception as exc:
                self._json_response({"explanation": None, "error": str(exc)}, 200)
        elif path.startswith("/api/pis/lineage/"):
            snapshot_id = path[len("/api/pis/lineage/"):].strip()
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.recommendation_lineage import pis_lineage_for_snapshot

                self._json_response(pis_lineage_for_snapshot(snapshot_id, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"summary": None, "matches": [], "unmatched": [], "source_breakdown": [], "error": str(exc)}, 200)
        elif path.startswith("/api/pis/changes/"):
            snapshot_id = path[len("/api/pis/changes/"):].strip()
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.change_detection import pis_changes_for_snapshot

                self._json_response(pis_changes_for_snapshot(snapshot_id, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {
                        "summary": None,
                        "new_positions": [],
                        "exited_positions": [],
                        "increased_positions": [],
                        "reduced_positions": [],
                        "unchanged_positions": [],
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/signal-refresh/status":
            running = _refresh_proc is not None and _refresh_proc.poll() is None
            global _refresh_last_report, _refresh_last_exit_code, _refresh_completed_at_utc
            if _refresh_proc is not None and not running:
                _refresh_last_exit_code = _refresh_proc.poll()
                if _refresh_completed_at_utc is None:
                    _refresh_completed_at_utc = datetime.now(timezone.utc)
                if _refresh_last_report is None and _REFRESH_REPORT_PATH.exists():
                    try:
                        _refresh_last_report = json.loads(_REFRESH_REPORT_PATH.read_text(encoding="utf-8"))
                    except Exception:
                        _refresh_last_report = None
            elapsed_sec: float | None = None
            if _refresh_started_at_utc is not None:
                elapsed_sec = max((datetime.now(timezone.utc) - _refresh_started_at_utc).total_seconds(), 0.0)
            with _refresh_log_lock:
                recent_lines = list(_refresh_log_lines[-8:])
            last_line = recent_lines[-1] if recent_lines else ""
            progress_fields = _parse_provider_progress_line(last_line)
            self._json_response({
                "running": running,
                "exit_code": _refresh_last_exit_code,
                "last_report": _refresh_last_report,
                "mode": _refresh_mode,
                "started_at_utc": _refresh_started_at_utc.isoformat() if _refresh_started_at_utc else None,
                "completed_at_utc": _refresh_completed_at_utc.isoformat() if _refresh_completed_at_utc else None,
                "elapsed_sec": round(elapsed_sec, 1) if elapsed_sec is not None else None,
                "recent_log_lines": recent_lines,
                "last_log_line": last_line,
                "provider_stage_note": "Provider-stage progress, not overall refresh completion.",
                **progress_fields,
            })
        elif path == "/api/refresh-transparency":
            self._json_response(_compute_candidate_transparency_payload())
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
        # ── ISSUE-12D: Signal Conflict Review endpoints ────────────────────────
        elif path == "/api/conflict-review/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh
                data = load_or_refresh(_REPO_ROOT)
                self._json_response({
                    "meta": data["meta"],
                    "learning": data["learning"],
                })
            except Exception as exc:
                self._json_response({"error": str(exc)}, 200)
        elif path == "/api/conflict-review/outcomes":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh
                data = load_or_refresh(_REPO_ROOT)
                self._json_response(data.get("outcomes", {}))
            except Exception as exc:
                self._json_response({"patterns": [], "error": str(exc)}, 200)
        elif path == "/api/conflict-review/scorecard":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh
                data = load_or_refresh(_REPO_ROOT)
                self._json_response(data.get("scorecard", {}))
            except Exception as exc:
                self._json_response({"scorecard": [], "error": str(exc)}, 200)
        elif path.startswith("/api/conflict-review/symbol/"):
            raw_sym = path[len("/api/conflict-review/symbol/"):].strip().upper()
            if not raw_sym or not _SYMBOL_RE.match(raw_sym):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import load_or_refresh, symbol_deep_dive
                data = load_or_refresh(_REPO_ROOT)
                dive = symbol_deep_dive(raw_sym, data["inventory"])
                self._json_response(dive)
            except Exception as exc:
                self._json_response({"symbol": raw_sym, "error": str(exc)}, 200)
        elif path == "/api/conflict-review/refresh":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.signal_conflict_review import refresh_conflict_data
                meta = refresh_conflict_data(_REPO_ROOT)
                self._json_response({"ok": True, **meta})
            except Exception as exc:
                self._json_response({"ok": False, "error": str(exc)}, 200)
        elif path == "/api/conflict-review/alpha":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.conflict_alpha_analysis import conflict_alpha_report
                self._json_response(conflict_alpha_report(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"patterns": [], "leaders": [], "laggards": [],
                                     "error": str(exc)}, 200)
        elif path.startswith("/api/conflict-review/security-alpha/"):
            raw_sym = path[len("/api/conflict-review/security-alpha/"):].strip().upper()
            if not raw_sym or not _SYMBOL_RE.match(raw_sym):
                self._json_response({"error": "invalid or missing symbol"}, 400)
                return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.security_conflict_alpha import get_security_conflict_alpha
                from urllib.parse import parse_qs, urlparse as _urlparse2
                qs3 = parse_qs(_urlparse2(self.path).query)
                sca = get_security_conflict_alpha(
                    raw_sym,
                    repo_root=_REPO_ROOT,
                    ess_text=qs3.get("ess", [None])[0],
                    zacks_score=float(qs3["zacks"][0]) if "zacks" in qs3 else None,
                    yahoo_consensus=qs3.get("yahoo", [None])[0],
                )
                self._json_response(sca)
            except Exception as exc:
                self._json_response({"symbol": raw_sym, "error": str(exc)}, 200)
        elif path == "/api/conflict-review/security-alpha-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.security_conflict_alpha import security_alpha_summary
                self._json_response(security_alpha_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"status": "ERROR", "securities": {},
                                     "error": str(exc)}, 200)
        # ── Predictive Intelligence EPIC endpoints ────────────────────────────
        elif path == "/api/predictive/pattern-persistence":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.pattern_persistence import all_pattern_persistence
                self._json_response(all_pattern_persistence(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"total_symbols": 0, "error": str(exc)}, 200)
        elif path.startswith("/api/predictive/pattern-persistence/"):
            raw_sym = path[len("/api/predictive/pattern-persistence/"):].strip().upper()
            if not raw_sym or not _SYMBOL_RE.match(raw_sym):
                self._json_response({"error": "invalid symbol"}, 400); return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.pattern_persistence import symbol_pattern_persistence
                self._json_response(symbol_pattern_persistence(raw_sym, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"symbol": raw_sym, "error": str(exc)}, 200)
        elif path == "/api/predictive/forward-estimate":
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = {k: v for k, v in (p.split("=", 1) for p in qs.split("&") if "=" in p)}
            sym = params.get("symbol", "").strip().upper()
            if not sym:
                self._json_response({"error": "symbol required"}, 400); return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.forward_return_estimate import forward_estimate
                self._json_response(forward_estimate(sym, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"symbol": sym, "error": str(exc)}, 200)
        elif path == "/api/predictive/event-triggers":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.event_triggered_refresh import check_pending_refresh_triggers
                self._json_response(check_pending_refresh_triggers(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"pending_count": 0, "pending": [], "error": str(exc)}, 200)
        elif path == "/api/predictive/funding-effectiveness":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.funding_source_effectiveness import funding_effectiveness_study
                self._json_response(funding_effectiveness_study(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"category_outcomes": {}, "error": str(exc)}, 200)
        elif path == "/api/predictive/mei-calibration":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.event_sensitivity_calibration import calibrate_sensitivities
                self._json_response(calibrate_sensitivities(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"calibrations": [], "error": str(exc)}, 200)
        elif path == "/api/predictive/scenario":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.portfolio_scenario import scenario_from_cra
                self._json_response(scenario_from_cra(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"status": "ERROR", "error": str(exc)}, 200)
        # ── DISLOCATION-06: Calibration ───────────────────────────────────────
        elif path == "/api/predictive/calibration":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.conflict_alpha_calibration import calibration_summary
                self._json_response(calibration_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"status": "ERROR", "patterns": [], "error": str(exc)}, 200)
        elif path.startswith("/api/predictive/calibration/"):
            raw_pat = path[len("/api/predictive/calibration/"):].strip().upper()
            if not raw_pat:
                self._json_response({"error": "pattern required"}, 400); return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.conflict_alpha_calibration import pattern_calibration
                self._json_response(pattern_calibration(raw_pat, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"pattern": raw_pat, "error": str(exc)}, 200)
        elif path == "/api/predictive/confidence-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.conflict_alpha_calibration import confidence_summary
                self._json_response(confidence_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"confidence_counts": {}, "error": str(exc)}, 200)
        # ── DISLOCATION-07: Directional Accuracy ──────────────────────────────
        elif path == "/api/predictive/directional-accuracy":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.directional_accuracy import directional_accuracy
                self._json_response(directional_accuracy(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"status": "ERROR", "patterns": [], "error": str(exc)}, 200)
        elif path.startswith("/api/predictive/directional-accuracy/"):
            raw_pat = path[len("/api/predictive/directional-accuracy/"):].strip().upper()
            if not raw_pat:
                self._json_response({"error": "pattern required"}, 400); return
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.directional_accuracy import pattern_directional
                self._json_response(pattern_directional(raw_pat, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"pattern": raw_pat, "error": str(exc)}, 200)
        elif path == "/api/predictive/directional-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.directional_accuracy import directional_summary
                self._json_response(directional_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"patterns": [], "error": str(exc)}, 200)
        elif path == "/api/drift/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.drift_analyzer import compute_drift_summary
                self._json_response(compute_drift_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path.startswith("/api/drift/timeline"):
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.drift_analyzer import compute_drift_timeline
                from urllib.parse import parse_qs, urlparse
                qs = parse_qs(urlparse(self.path).query)
                rule_id = qs.get("rule_id", ["CPV-01"])[0]
                self._json_response(compute_drift_timeline(rule_id=rule_id, repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        # ── PA-006B: Allocation Drift Intelligence ────────────────────────────
        elif path == "/api/drift/trends":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_trends
                self._json_response(drift_trends(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"trend_counts": {}, "nodes": [], "error": str(exc)}, 200)
        elif path == "/api/drift/priorities":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_priorities
                self._json_response(drift_priorities(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"top10": [], "error": str(exc)}, 200)
        elif path == "/api/drift/chronic":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_chronic
                self._json_response(drift_chronic(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"chronic": [], "error": str(exc)}, 200)
        elif path == "/api/drift/momentum":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_momentum
                self._json_response(drift_momentum(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"nodes": [], "error": str(exc)}, 200)
        elif path == "/api/drift/intelligence-summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.drift_trend_analyzer import drift_intelligence_summary
                self._json_response(drift_intelligence_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response({"total_nodes": 0, "violation_nodes": 0, "error": str(exc)}, 200)
        elif path.startswith("/api/signal-conflicts"):
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from urllib.parse import parse_qs, urlparse as _urlparse
                from src.portfolio.signal_conflict_classifier import get_conflicts_for_symbols
                import yaml as _yaml
                qs2 = parse_qs(_urlparse(self.path).query)
                raw_syms = qs2.get("symbols", [""])[0]
                symbols = [s.strip().upper() for s in raw_syms.split(",") if s.strip()]
                if not symbols:
                    self._json_response({"error": "symbols query parameter required"}, 400)
                else:
                    _pol_path = _REPO_ROOT / "config" / "allocation_policy.yaml"
                    _config = {}
                    if _pol_path.exists():
                        try:
                            _config = _yaml.safe_load(_pol_path.read_text(encoding="utf-8")) or {}
                        except Exception:
                            pass
                    conflicts = get_conflicts_for_symbols(symbols, repo_root=_REPO_ROOT, config=_config)
                    self._json_response({"conflicts": conflicts})
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
        elif path == "/api/rotation-risk/summary":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.rotation_risk_monitor import rotation_risk_summary

                self._json_response(rotation_risk_summary(repo_root=_REPO_ROOT))
            except Exception as exc:
                self._json_response(
                    {
                        "status": "DATA_UNAVAILABLE",
                        "diagnostic_id": "ROTATION-RISK-01",
                        "diagnostic_name": "Tech-to-hard-assets rotation monitor",
                        "signal": "DATA_UNAVAILABLE",
                        "headline": "Rotation monitor unavailable due to runtime error.",
                        "error": str(exc),
                    },
                    200,
                )
        elif path == "/api/cpv/latest":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                import json as _json
                # Find latest PAR compliance.json
                manifest_path = _REPO_ROOT / "data/portfolio_ingestion/manifest.json"
                compliance_payload = None
                if manifest_path.exists():
                    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
                    portfolios = [
                        p for p in (manifest.get("portfolios") or [])
                        if len(str(p.get("snapshot_date", "")).strip()) == 10
                        and str(p.get("snapshot_date", "")).strip()[4:5] == "-"
                    ]
                    if portfolios:
                        latest_run_id = max(
                            portfolios,
                            key=lambda p: (str(p.get("snapshot_date", "")), str(p.get("created_at_utc", ""))),
                        ).get("run_id", "")
                        compliance_path = (
                            _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs"
                            / latest_run_id / "compliance.json"
                        )
                        if compliance_path.exists():
                            compliance_payload = _json.loads(compliance_path.read_text(encoding="utf-8"))
                if compliance_payload is None:
                    self._json_response({"error": "No compliance data available"}, 404)
                else:
                    self._json_response(compliance_payload)
            except Exception as exc:
                self._json_response({"error": str(exc)}, 500)
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
                    self._json_response(_attach_explanations(result))
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
            # GET /api/cra/proposal
            # Returns a RotationProposal built from the latest COMPLETE PAR run.
            # Reads: deployment_queue.json, security_overlays.csv, holdings.csv,
            #        alignment.csv, run_metadata.json, concentration.json,
            #        snapshot.json, portfolio_alignment_state.json (optional).
            # Does NOT modify any upstream artifacts.
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.portfolio.cra.rotation_proposal_builder import build_proposal_from_manifest
                manifest_path  = _REPO_ROOT / "data" / "portfolio_ingestion" / "manifest.json"
                runs_root      = _REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs"
                tax_state_path = _REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json"

                if not manifest_path.exists():
                    self._json_response(
                        {"error": "No portfolio manifest found. Run a portfolio analysis first."},
                        404,
                    )
                    return

                proposal = build_proposal_from_manifest(
                    manifest_path=manifest_path,
                    runs_root=runs_root,
                    tax_state_path=tax_state_path if tax_state_path.exists() else None,
                )

                if proposal is None:
                    self._json_response(
                        {"error": "No COMPLETE portfolio analysis run found. Run a portfolio analysis first."},
                        404,
                    )
                    return

                self._json_response(proposal.to_dict())
            except FileNotFoundError as exc:
                self._json_response({"error": f"Required PAR files missing: {exc}"}, 404)
            except Exception as exc:
                import traceback as _tb
                log.error("CRA proposal error: %s\n%s", exc, _tb.format_exc())
                self._json_response({"error": f"CRA proposal generation failed: {exc}"}, 500)

        elif path == "/api/security-metadata":
            # GET /api/security-metadata
            # Returns {symbol → {sector, industry, country, quote_type,
            #   market_cap_bucket, long_name, hq, business_summary}}
            # Merges security_metadata + analytical_universe + company_profile.
            # Display-only — no scoring impact.
            try:
                import sys as _sys, csv as _csv
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.scoring.fetch_security_metadata import load_latest_security_metadata
                metadata: dict = load_latest_security_metadata()

                # Enrich with market_cap_bucket from analytical universe
                au_path = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
                if au_path.exists():
                    with au_path.open("r", encoding="utf-8", newline="") as _fh:
                        for _row in _csv.DictReader(_fh):
                            _sym = str(_row.get("symbol", "")).strip().upper()
                            if _sym:
                                if _sym not in metadata:
                                    metadata[_sym] = {"sector": "", "industry": "", "country": "", "quote_type": ""}
                                metadata[_sym]["market_cap_bucket"] = str(_row.get("market_cap_bucket") or "")
                                metadata[_sym]["security_type"]    = str(_row.get("security_type") or "")
                                if not metadata[_sym].get("country"):
                                    metadata[_sym]["country"] = str(_row.get("country") or "")

                # Enrich with company profile (name, HQ, business description)
                from src.scoring.fetch_company_profile import load_latest_company_profile, _compose_hq
                from src.scoring.fmp_universe_enrichment import load_fmp_enriched_universe
                _COUNTRY_ABBREV = {"United States": "USA"}
                company_profiles = load_latest_company_profile()
                for _sym, _prof in company_profiles.items():
                    if _sym not in metadata:
                        metadata[_sym] = {"sector": "", "industry": "", "country": "", "quote_type": ""}
                    metadata[_sym]["long_name"] = str(_prof.get("long_name") or "")
                    _raw_country = str(_prof.get("country") or "")
                    _disp_country = _COUNTRY_ABBREV.get(_raw_country, _raw_country)
                    metadata[_sym]["hq"] = _compose_hq(
                        str(_prof.get("city") or ""),
                        str(_prof.get("state") or ""),
                        _disp_country,
                    )
                    metadata[_sym]["business_summary"] = str(_prof.get("business_summary") or "")

                # Enrich with FMP fundamental data (Phase 8.0B.1B.5 — display only)
                fmp_enriched = load_fmp_enriched_universe()
                for _sym, _frow in fmp_enriched.items():
                    if _sym not in metadata:
                        metadata[_sym] = {"sector": "", "industry": "", "country": "", "quote_type": ""}
                    metadata[_sym]["fmp_coverage"]          = str(_frow.get("fmp_coverage_status") or "")
                    metadata[_sym]["fmp_ev_ebitda"]         = str(_frow.get("ev_ebitda_ttm") or "")
                    metadata[_sym]["fmp_fcf_yield"]         = str(_frow.get("fcf_yield_ttm") or "")
                    metadata[_sym]["fmp_roe"]               = str(_frow.get("roe_ttm") or "")
                    metadata[_sym]["fmp_roic"]              = str(_frow.get("roic_ttm") or "")
                    metadata[_sym]["fmp_revenue_growth"]    = str(_frow.get("revenue_growth_q1_yoy") or "")
                    metadata[_sym]["fmp_eps_growth"]        = str(_frow.get("eps_growth_q1_yoy") or "")
                    metadata[_sym]["fmp_revenue_accel"]     = str(_frow.get("revenue_acceleration") or "")
                    metadata[_sym]["fmp_beat_rate"]         = str(_frow.get("beat_rate_8q") or "")
                    metadata[_sym]["fmp_beats_8q"]          = str(_frow.get("beats_last_8q") or "")
                    metadata[_sym]["fmp_latest_surprise"]   = str(_frow.get("latest_eps_surprise_pct") or "")
                    metadata[_sym]["fmp_net_buy_score"]     = str(_frow.get("net_buy_score") or "")
                    metadata[_sym]["fmp_consensus"]         = str(_frow.get("consensus_label") or "")
                    metadata[_sym]["fmp_buy_count"]         = str(_frow.get("buy_count") or "")
                    metadata[_sym]["fmp_hold_count"]        = str(_frow.get("hold_count") or "")
                    metadata[_sym]["fmp_sell_count"]        = str(_frow.get("sell_count") or "")

                self._json_response(metadata)
            except Exception as exc:
                self._json_response({}, 200)  # fail-open: empty dict on error

        elif path == "/api/cra/draft":
            # GET /api/cra/draft — load saved CRA proposal draft (404 if none)
            draft_path = _REPO_ROOT / "data" / "operator" / "cra_draft.json"
            if not draft_path.exists():
                self._json_response({"error": "No saved draft found"}, 404)
            else:
                try:
                    draft = json.loads(draft_path.read_text(encoding="utf-8"))
                    self._json_response(draft)
                except Exception as exc:
                    self._json_response({"error": f"Failed to load draft: {exc}"}, 500)

        elif path.startswith("/api/cra/draft/export"):
            # GET /api/cra/draft/export?format=csv|md — export saved draft
            draft_path = _REPO_ROOT / "data" / "operator" / "cra_draft.json"
            if not draft_path.exists():
                self._json_response({"error": "No saved draft to export"}, 404)
                return
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = {k: v for k, v in (p.split("=", 1) for p in qs.split("&") if "=" in p)}
            fmt = params.get("format", "csv").lower().strip()
            try:
                draft = json.loads(draft_path.read_text(encoding="utf-8"))
                as_of = draft.get("as_of_date", "draft")
                if fmt == "csv":
                    import csv as _csv, io as _io
                    output = _io.StringIO()
                    w = _csv.writer(output)
                    # Header
                    w.writerow(["CRA Proposal", as_of, draft.get("proposal_id", ""), draft.get("cra_version", "1.0")])
                    w.writerow([])
                    # Sources
                    w.writerow(["section", "symbol", "category", "priority",
                                 "estimated_proceeds", "sizing_pct", "tax_bucket",
                                 "tax_annotation", "evidence_summary"])
                    for s in draft.get("sources", []):
                        w.writerow(["SOURCE", s.get("symbol"), s.get("category"),
                                    s.get("priority"), s.get("estimated_proceeds"),
                                    s.get("sizing_pct"), s.get("tax_bucket"),
                                    s.get("tax_annotation"), s.get("evidence_summary")])
                    w.writerow([])
                    # Targets
                    w.writerow(["section", "rank", "symbol", "narrative_tier",
                                 "deployment_score", "suggested_amount", "projected_weight_pct"])
                    for t in draft.get("deployments", []):
                        w.writerow(["TARGET", t.get("rank"), t.get("symbol"),
                                    t.get("narrative_tier"), t.get("deployment_score"),
                                    t.get("suggested_amount"),
                                    f"{float(t.get('projected_weight_pct', 0))*100:.2f}%"])
                    w.writerow([])
                    # Impact
                    imp = draft.get("impact", {})
                    w.writerow(["section", "alignment_before", "alignment_after",
                                 "alignment_delta", "concentration_before",
                                 "concentration_after", "narrative"])
                    w.writerow(["IMPACT", imp.get("alignment_score_before"),
                                 imp.get("alignment_score_after"), imp.get("alignment_delta"),
                                 imp.get("concentration_before"), imp.get("concentration_after"),
                                 imp.get("impact_narrative")])
                    csv_bytes = output.getvalue().encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="cra_proposal_{as_of}.csv"')
                    self.send_header("Content-Length", str(len(csv_bytes)))
                    self.end_headers()
                    self.wfile.write(csv_bytes)
                elif fmt in ("md", "markdown"):
                    lines = [
                        f"# Capital Rotation Advisor — Proposal",
                        f"",
                        f"**As of:** {as_of}  ·  **Proposal ID:** {draft.get('proposal_id', '—')}",
                        f"**Status:** {draft.get('proposal_status', '—')}  ·  **CRA Version:** {draft.get('cra_version', '1.0')}",
                        f"",
                    ]
                    # Sources by category
                    cat_labels = {
                        "SIGNAL_DETERIORATION": "Signal Deterioration",
                        "STRATEGIC_EXIT": "Strategic Exit",
                        "OVERWEIGHT_REDUCTION": "Exposure Reduction",
                        "TAX_AWARE_EXIT": "Tax-Aware Exit",
                        "LOW_CONVICTION_REDUCTION": "Low Conviction Reduction",
                    }
                    lines += [f"## Capital Sources  (Est. Pool: ${draft.get('total_capital_pool', 0):,.0f})", ""]
                    for cat_key, cat_label in cat_labels.items():
                        cat_src = [s for s in draft.get("sources", []) if s.get("category") == cat_key]
                        if cat_src:
                            lines += [f"### {cat_label}", "| Symbol | Est. Proceeds | Tax | Evidence |", "| --- | --- | --- | --- |"]
                            for s in cat_src:
                                lines.append(f"| {s.get('symbol')} | ${float(s.get('estimated_proceeds', 0)):,.0f} | {s.get('tax_bucket','—')} | {s.get('evidence_summary', '')} |")
                            lines.append("")
                    # Targets
                    lines += ["## Deployment Targets", "", "| Rank | Symbol | Tier | Score | Add | Proj. Weight |", "| --- | --- | --- | --- | --- | --- |"]
                    for t in draft.get("deployments", []):
                        tier_short = "CCL" if "CORE" in t.get("narrative_tier","") else "HCA"
                        lines.append(f"| #{t.get('rank')} | {t.get('symbol')} | {tier_short} | {t.get('deployment_score')} | ${float(t.get('suggested_amount', 0)):,.0f} | {float(t.get('projected_weight_pct', 0))*100:.1f}% |")
                    lines.append("")
                    # Impact
                    imp = draft.get("impact", {})
                    lines += [
                        "## Portfolio Impact Estimate",
                        "",
                        f"- Alignment: {imp.get('alignment_score_before', '—')} → {imp.get('alignment_score_after', '—')} ({'+' if float(imp.get('alignment_delta', 0)) >= 0 else ''}{imp.get('alignment_delta', 0):.1f})",
                        f"- Concentration: {imp.get('concentration_before', '—')} → {imp.get('concentration_after', '—')}",
                        f"- {imp.get('impact_narrative', '')}",
                        "",
                        "---",
                        "*Advisory guidance only — not trade instructions. Generated by Security Intelligence Hub.*",
                    ]
                    md_bytes = "\n".join(lines).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/markdown; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="cra_proposal_{as_of}.md"')
                    self.send_header("Content-Length", str(len(md_bytes)))
                    self.end_headers()
                    self.wfile.write(md_bytes)
                else:
                    self._json_response({"error": f"Unsupported format: {fmt}"}, 400)
            except Exception as exc:
                self._json_response({"error": f"Export failed: {exc}"}, 500)

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
        else:
            super().do_GET()

    def do_POST(self) -> None:  # type: ignore[override]
        path = self.path.split("?")[0]
        if path == "/api/cra/draft":
            # POST /api/cra/draft — save proposal (+ optional operator_include_map) as draft
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body)
            except Exception:
                self._json_response({"error": "invalid JSON body"}, 400)
                return
            if not payload:
                self._json_response({"error": "empty payload"}, 400)
                return
            # Inject saved_at_utc timestamp
            from datetime import datetime as _dt, timezone as _tz
            payload["saved_at_utc"] = _dt.now(_tz.utc).isoformat(timespec="seconds")
            draft_path = _REPO_ROOT / "data" / "operator" / "cra_draft.json"
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = draft_path.with_suffix(".tmp")
            try:
                tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                tmp.replace(draft_path)
                self._json_response({"saved": True, "proposal_id": payload.get("proposal_id")})
            except Exception as exc:
                self._json_response({"error": f"Failed to save draft: {exc}"}, 500)
        elif path == "/api/signal-refresh":
            global _refresh_proc
            if _refresh_proc is not None and _refresh_proc.poll() is None:
                self._json_response({"started": False, "reason": "already running"})
                return
            global _refresh_last_report, _refresh_last_exit_code
            _refresh_last_report = None
            _refresh_last_exit_code = None
            refresh_mode = "stale_only"
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body) if body else {}
                refresh_mode = str(payload.get("mode") or refresh_mode).strip().lower()
                if _REFRESH_REPORT_PATH.exists():
                    _REFRESH_REPORT_PATH.unlink()
            except Exception:
                refresh_mode = "stale_only"

            if refresh_mode == "prepare_portfolio_review":
                command = [
                    sys.executable,
                    str(_REPO_ROOT / "scripts" / "prepare_portfolio_review.py"),
                    "--report-path",
                    str(_REFRESH_REPORT_PATH),
                ]
            else:
                command = [
                    sys.executable,
                    str(_REPO_ROOT / "scripts" / "refresh_signals.py"),
                    "--mode",
                    refresh_mode,
                    "--smart",
                    "--report-path",
                    str(_REFRESH_REPORT_PATH),
                ]

            global _refresh_started_at_utc, _refresh_completed_at_utc, _refresh_mode
            with _refresh_log_lock:
                _refresh_log_lines.clear()
            _refresh_started_at_utc = datetime.now(timezone.utc)
            _refresh_completed_at_utc = None
            _refresh_mode = refresh_mode
            _refresh_proc = subprocess.Popen(
                command,
                cwd=str(_REPO_ROOT),
                env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            threading.Thread(target=_capture_refresh_output, args=(_refresh_proc,), daemon=True).start()
            self._json_response({"started": True, "mode": refresh_mode})
        elif path == "/api/pis/refresh":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.pis.refresh_orchestrator import refresh_derived_artifacts

                result = refresh_derived_artifacts(repo_root=_REPO_ROOT)
                self._json_response(result)
            except Exception as exc:
                self._json_response({"error": str(exc), "refreshed": [], "skipped": []}, 200)
        elif path == "/api/mei/outcomes/refresh":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.mei.event_outcome_tracker import refresh_event_outcomes
                meta = refresh_event_outcomes(repo_root=_REPO_ROOT)
                self._json_response(meta)
            except Exception as exc:
                self._json_response({"ok": False, "error": str(exc)}, 200)
        elif path == "/api/predictive/calibration/refresh":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.conflict_alpha_calibration import refresh_calibration
                meta = refresh_calibration(repo_root=_REPO_ROOT)
                self._json_response(meta)
            except Exception as exc:
                self._json_response({"ok": False, "error": str(exc)}, 200)
        elif path == "/api/predictive/directional-refresh":
            try:
                import sys as _sys
                if str(_REPO_ROOT) not in _sys.path:
                    _sys.path.insert(0, str(_REPO_ROOT))
                from src.sih.predictive.directional_accuracy import refresh_directional
                meta = refresh_directional(repo_root=_REPO_ROOT)
                self._json_response(meta)
            except Exception as exc:
                self._json_response({"ok": False, "error": str(exc)}, 200)
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
                self._json_response(_attach_explanations(result))
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

    def do_DELETE(self) -> None:  # type: ignore[override]
        path = self.path.split("?")[0]
        if path == "/api/cra/draft":
            # DELETE /api/cra/draft — clear saved draft
            draft_path = _REPO_ROOT / "data" / "operator" / "cra_draft.json"
            if draft_path.exists():
                draft_path.unlink()
                self._json_response({"deleted": True})
            else:
                self._json_response({"deleted": False, "reason": "no draft exists"}, 404)
        else:
            self.send_error(404)

    def _json_response(self, data: dict, status: int = 200) -> None:
        try:
            body = json.dumps(_sanitize_nan(data), allow_nan=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            body = json.dumps({"error": f"serialization_error: {exc}"}).encode("utf-8")
            status = 500

        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected before response flush; avoid noisy traceback.
            return

    def log_message(self, fmt: str, *args: object) -> None:  # type: ignore[override]
        # Suppress noisy polling requests from the UI
        if args and "/api/signal-refresh/status" in str(args[0]):
            return
        super().log_message(fmt, *args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local server for outcome visualization prototype UI.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local HTTP server.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    _ThreadingTCPServer.allow_reuse_address = True
    with _ThreadingTCPServer(("127.0.0.1", args.port), _Handler) as httpd:
        print("Outcome UI server started")
        print(f"Repository root: {_REPO_ROOT}")
        print(f"Open: http://127.0.0.1:{args.port}/ui/outcome_visualization/index.html")
        try:
            os.chdir(_REPO_ROOT)
            # Run PIS derived-artifact refresh once at startup without blocking
            # the HTTP listener.  The refresh chain is idempotent — if all
            # artifacts are already current it exits immediately.
            if str(_REPO_ROOT) not in sys.path:
                sys.path.insert(0, str(_REPO_ROOT))
            from src.pis.refresh_orchestrator import trigger_startup_refresh
            _pis_startup_thread = threading.Thread(
                target=trigger_startup_refresh,
                kwargs={"repo_root": _REPO_ROOT},
                daemon=True,
                name="pis-startup-refresh",
            )
            _pis_startup_thread.start()
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
