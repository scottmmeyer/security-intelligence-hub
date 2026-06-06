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

# Background refresh process handle (module-level so Handler instances share it)
_refresh_proc: subprocess.Popen | None = None

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
        result[name] = {
            "sourced_date": sd,
            "stale": sd != today,
            "exists": path.exists(),
        }
    return result


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
