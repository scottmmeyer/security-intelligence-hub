#!/usr/bin/env python3
"""Run a local static + API server for the WP-04.1 outcome visualization prototype.

Static files are served from the repository root.

API endpoints:
  GET  /api/signal-status          → JSON: last sourced_date and staleness per provider
  POST /api/signal-refresh         → launch scripts/refresh_signals.py as background process
  GET  /api/signal-refresh/status  → JSON: {"running": true/false}
  POST /api/portfolio/analyze      → ingest + enrich + align portfolio CSV; returns full analysis
  GET  /api/portfolio/runs         → list all completed portfolio analysis runs
  GET  /api/portfolio/runs/{id}    → load a specific analysis run by run_id
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
_ESS_SIGNAL_SNAPSHOT = _REPO_ROOT / "data" / "current" / "signal_snapshot.csv"
_ESS_COVERAGE_WARNING = _REPO_ROOT / "data" / "current" / "ess_coverage_warning.json"
_REFRESH_REPORT_PATH = _REPO_ROOT / "data" / "current" / "last_signal_refresh_report.json"

# Background refresh process handle (module-level so Handler instances share it)
_refresh_proc: subprocess.Popen | None = None
_refresh_last_report: dict | None = None
_refresh_last_exit_code: int | None = None

# On-demand score fetch jobs keyed by symbol (uppercase)
_fetch_jobs: dict[str, dict] = {}
_fetch_lock = threading.Lock()

_SYMBOL_RE = re.compile(r"^[A-Z0-9./\-]{1,12}$")


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
            self._json_response({"running": running})
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
        if path == "/api/signal-refresh":
            global _refresh_proc
            if _refresh_proc is not None and _refresh_proc.poll() is None:
                self._json_response({"started": False, "reason": "already running"})
                return
            _refresh_proc = subprocess.Popen(
                [sys.executable, str(_REPO_ROOT / "scripts/refresh_signals.py"), "--smart"],
                cwd=str(_REPO_ROOT),
                env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
            )
            self._json_response({"started": True})
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
        body = json.dumps(data).encode()
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


def main() -> int:
    args = parse_args()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), _Handler) as httpd:
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
