#!/usr/bin/env python3
"""Phase 6.4 — Generate portfolio_reconciliation_report.md for a given run_id.

Usage:
    python scripts/_generate_reconciliation_report.py [run_id]

If run_id is omitted, uses the most recent analysis run.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.portfolio.reconciliation import ReconciliationCheck, ReconciliationResult, run_reconciliation

_INGESTION_ROOT = _REPO_ROOT / "data" / "portfolio_ingestion"
_OUTPUT_PATH = _REPO_ROOT / "portfolio_reconciliation_report.md"


# ─────────────────────────────────────────────────────────────────────────────
# Load run data
# ─────────────────────────────────────────────────────────────────────────────

def _latest_run_id() -> str | None:
    runs_dir = _INGESTION_ROOT / "analysis_runs"
    if not runs_dir.exists():
        return None
    dirs = sorted(
        (d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("PAR-")),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return dirs[0].name if dirs else None


def _load_run(run_id: str) -> dict:
    run_dir = _INGESTION_ROOT / "analysis_runs" / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")

    result: dict = {"run_id": run_id}

    for fname in ("run_metadata.json", "snapshot.json"):
        p = run_dir / fname
        if p.exists():
            result[fname.replace(".json", "")] = json.loads(p.read_text())

    p = run_dir / "recommendations.json"
    if p.exists():
        result["recommendations"] = json.loads(p.read_text())

    p = run_dir / "alignment.csv"
    if p.exists():
        result["alignment"] = list(csv.DictReader(p.open()))

    p = run_dir / "holdings.csv"
    if p.exists():
        result["holdings"] = list(csv.DictReader(p.open()))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Markdown rendering
# ─────────────────────────────────────────────────────────────────────────────

def _badge(status: str) -> str:
    return {"PASS": "✅ PASS", "WARN": "⚠️ WARN", "FAIL": "❌ FAIL"}.get(status, status)


def _render_report(result: ReconciliationResult, run_meta: dict, snap_meta: dict) -> str:
    lines: list[str] = []
    w = lines.append

    run_id = result.run_id
    snap_date = run_meta.get("snapshot_date", "—")
    created = run_meta.get("created_at_utc", "—")
    total_mv = snap_meta.get("total_market_value", 0.0)
    mandate = run_meta.get("mandate_type") or "CONCENTRATED_ALPHA"

    w(f"# Portfolio Reconciliation Report")
    w(f"")
    w(f"**Run ID:** {run_id}  ")
    w(f"**Snapshot Date:** {snap_date}  ")
    w(f"**Portfolio Value:** ${float(total_mv):,.2f}  ")
    w(f"**Active Mandate:** {mandate}  ")
    w(f"**Generated:** {result.generated_at}  ")
    w(f"")
    w(f"---")
    w(f"")

    # Executive Summary
    w(f"## Section 1 — Executive Summary")
    w(f"")
    overall_badge = _badge(result.overall_status)
    w(f"**Overall Certification: {overall_badge}**")
    w(f"")
    w(f"| Metric | Value |")
    w(f"|--------|-------|")
    w(f"| Checks Passed | {result.checks_passed}/10 |")
    w(f"| Checks Warned | {result.checks_warned}/10 |")
    w(f"| Checks Failed | {result.checks_failed}/10 |")
    w(f"| Certification | {result.certification} |")
    w(f"")
    w(f"| Check | Name | Status |")
    w(f"|-------|------|--------|")
    for c in result.checks:
        w(f"| {c.check_id} | {c.name} | {_badge(c.status)} |")
    w(f"")
    if result.overall_status != "PASS":
        failed_checks = [c for c in result.checks if c.status != "PASS"]
        w(f"### Failures / Warnings Requiring Attention")
        w(f"")
        for c in failed_checks:
            badge = _badge(c.status)
            w(f"- **{c.check_id} {c.name}** {badge}")
            for d in c.detail[1:4]:
                w(f"  - {d}")
        w(f"")

    w(f"---")
    w(f"")

    # RC-01
    w(f"## Section 2 — Portfolio Value Reconciliation")
    _render_check(lines, result.checks[0])

    # RC-02
    w(f"## Section 3 — Allocation Reconciliation")
    _render_check(lines, result.checks[1])

    # RC-03 + RC-04
    w(f"## Section 4 — ETF Decomposition Validation")
    w(f"")
    w(f"### RC-03 — Decomposition Integrity")
    _render_check(lines, result.checks[2], show_sub=True, max_sub=15)
    w(f"")
    w(f"### RC-04 — ETF Weight Validation")
    _render_check(lines, result.checks[3], show_sub=True, max_sub=20)

    # RC-05
    w(f"## Section 5 — Cash Reconciliation")
    _render_cash_section(lines, result.checks[4])

    # RC-06
    w(f"## Section 6 — Security Classification Audit")
    _render_classification_section(lines, result.checks[5])

    # RC-07
    w(f"## Section 7 — Archetype Target Validation")
    _render_check(lines, result.checks[6], show_sub=True)

    # RC-08
    w(f"## Section 8 — Recommendation Validation")
    _render_check(lines, result.checks[7], show_sub=True, max_sub=10)

    # RC-09 + RC-10
    w(f"## Section 9 — Philosophy Validation")
    w(f"")
    w(f"### RC-09 — Holding Classification Consistency")
    _render_check(lines, result.checks[8], show_sub=True)
    w(f"")
    w(f"### RC-10 — Portfolio Philosophy Consistency")
    _render_check(lines, result.checks[9], show_sub=True, max_sub=10)

    # Certification
    w(f"## Section 10 — Certification")
    w(f"")
    w(f"### Reconciliation Certification Gates")
    w(f"")
    w(f"| Gate | Requirement | Status |")
    w(f"|------|------------|--------|")
    gates = [
        ("RC-01", "Portfolio value reconciles"),
        ("RC-02", "Allocation totals reconcile"),
        ("RC-03", "ETF decomposition valid"),
        ("RC-04", "ETF weight tables valid"),
        ("RC-05", "Cash reconciles"),
        ("RC-06", "Security classifications valid"),
        ("RC-07", "Archetype targets valid"),
        ("RC-08", "Recommendations aligned"),
        ("RC-09", "Holding states consistent"),
        ("RC-10", "Portfolio philosophy aligned"),
    ]
    for (check_id, req), chk in zip(gates, result.checks):
        w(f"| {check_id} | {req} | {_badge(chk.status)} |")
    w(f"")
    w(f"**Overall Result: {_badge(result.overall_status)}**  ")
    w(f"**{result.certification}**")
    w(f"")
    if result.overall_status == "PASS":
        w(f"> All 10 reconciliation checks passed. Portfolio accounting is internally consistent.")
    else:
        failed = [c for c in result.checks if c.status == "FAIL"]
        w(f"> **{len(failed)} reconciliation failure(s) detected. Review sections above before trusting recommendations.**")
    w(f"")

    return "\n".join(lines)


def _render_check(
    lines: list[str],
    c: ReconciliationCheck,
    show_sub: bool = False,
    max_sub: int = 0,
) -> None:
    w = lines.append
    w(f"")
    w(f"**{c.check_id} — {c.name}**: {_badge(c.status)}")
    w(f"")
    w(f"| Field | Value |")
    w(f"|-------|-------|")
    w(f"| Expected | {c.expected} |")
    w(f"| Actual | {c.actual} |")
    w(f"| Variance | {c.variance} |")
    w(f"| Tolerance | {c.tolerance} |")
    w(f"")
    for d in c.detail:
        w(f"> {d}")
    w(f"")
    if show_sub and c.sub_checks:
        display = c.sub_checks[:max_sub] if max_sub else c.sub_checks
        if display:
            keys = list(display[0].keys())
            # omit 'violations' and 'not_in_portfolio' from table header
            table_keys = [k for k in keys if k not in ("violations", "not_in_portfolio")]
            w(f"| {' | '.join(table_keys)} |")
            w(f"|{'|'.join(['---'] * len(table_keys))}|")
            for row in display:
                status_val = row.get("status", "")
                cells = []
                for k in table_keys:
                    v = row.get(k, "")
                    if k == "status":
                        v = _badge(str(v))
                    cells.append(str(v))
                w(f"| {' | '.join(cells)} |")
            if max_sub and len(c.sub_checks) > max_sub:
                w(f"")
                w(f"*... {len(c.sub_checks) - max_sub} more rows omitted*")
            w(f"")


def _render_cash_section(lines: list[str], c: ReconciliationCheck) -> None:
    w = lines.append
    w(f"")
    w(f"**{c.check_id} — {c.name}**: {_badge(c.status)}")
    w(f"")
    w(f"| Field | Value |")
    w(f"|-------|-------|")
    w(f"| Expected (from holdings) | {c.expected} |")
    w(f"| Actual (reported by engine) | {c.actual} |")
    w(f"| Variance | {c.variance} |")
    w(f"| Tolerance | {c.tolerance} |")
    w(f"")
    for d in c.detail:
        prefix = "> ⚠️ " if "DOUBLE-COUNT" in d else "> "
        w(f"{prefix}{d}")
    w(f"")
    # Cash contributors table
    portfolio_subs = [s for s in c.sub_checks if not s.get("not_in_portfolio")]
    absent_subs = [s for s in c.sub_checks if s.get("not_in_portfolio")]
    if portfolio_subs:
        w(f"### Cash Contributors in Portfolio")
        w(f"")
        w(f"| Symbol | Market Value | Security Type | Operational State | Cash Equivalent | Included In CASH |")
        w(f"|--------|-------------|--------------|------------------|-----------------|-----------------|")
        for h in portfolio_subs:
            mv = h.get("market_value", 0)
            pct = h.get("percent_of_portfolio", 0)
            incl = "✅ Yes" if h.get("included_in_cash") else "❌ No"
            is_ce = "✅ True" if h.get("is_cash_equivalent") else "❌ False"
            w(f"| {h.get('symbol', '?')} | ${float(mv):>12,.2f} ({float(pct):.4f}%) | {h.get('security_type', '—')} | {h.get('operational_state', '—')} | {is_ce} | {incl} |")
        w(f"")
    if absent_subs:
        w(f"### Known Cash-Equivalent Symbols Not Present in Portfolio")
        w(f"")
        w(f"| Symbol | Status |")
        w(f"|--------|--------|")
        for h in absent_subs:
            w(f"| {h.get('symbol', '?')} | Not in portfolio |")
        w(f"")


def _render_classification_section(lines: list[str], c: ReconciliationCheck) -> None:
    w = lines.append
    w(f"")
    w(f"**{c.check_id} — {c.name}**: {_badge(c.status)}")
    w(f"")
    for d in c.detail:
        w(f"> {d}")
    w(f"")
    if c.sub_checks:
        w(f"| Symbol | Security Type | Cash Equivalent | In ETF Registry | Status |")
        w(f"|--------|--------------|-----------------|----------------|--------|")
        for row in c.sub_checks:
            is_ce = "✅ Yes" if row.get("is_cash_equivalent") else "❌ No"
            in_reg = "⚠️ Yes" if row.get("in_etf_registry") else "No"
            w(f"| {row.get('symbol', '?')} | {row.get('security_type', '?')} | {is_ce} | {in_reg} | {_badge(row.get('status', ''))} |")
        w(f"")
        for row in c.sub_checks:
            if row.get("violations"):
                for v in row["violations"]:
                    w(f"> ⚠️ **{row.get('symbol')}**: {v}")
        w(f"")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    if run_id is None:
        run_id = _latest_run_id()
    if run_id is None:
        print("ERROR: No analysis runs found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading run: {run_id}")
    run_data = _load_run(run_id)

    run_meta = run_data.get("run_metadata", {})
    snap_meta = run_data.get("snapshot", {})
    holdings = run_data.get("holdings", [])
    alignment = run_data.get("alignment", [])
    recommendations = run_data.get("recommendations", [])
    mandate_type = run_meta.get("mandate_type") or "CONCENTRATED_ALPHA"
    total_mv = float(snap_meta.get("total_market_value", 0.0) or 0.0)

    print(f"Running reconciliation ({len(holdings)} holdings, {len(alignment)} nodes, {len(recommendations)} recs)...")
    result = run_reconciliation(
        holdings=holdings,
        alignment=alignment,
        recommendations=recommendations,
        mandate_type=mandate_type,
        snapshot_total_mv=total_mv,
        run_id=run_id,
    )

    print(f"Result: {result.overall_status} — {result.certification}")

    report_md = _render_report(result, run_meta, snap_meta)
    _OUTPUT_PATH.write_text(report_md, encoding="utf-8")
    print(f"Written: {_OUTPUT_PATH}")
    print(f"Lines: {len(report_md.splitlines())}")

    # Also write reconciliation.json to the run directory
    import dataclasses as dc

    def _ser(obj):
        if dc.is_dataclass(obj) and not isinstance(obj, type):
            return dc.asdict(obj)
        if isinstance(obj, list):
            return [_ser(i) for i in obj]
        return obj

    run_dir = _INGESTION_ROOT / "analysis_runs" / run_id
    rec_json = {
        "run_id": result.run_id,
        "generated_at": result.generated_at,
        "overall_status": result.overall_status,
        "checks_passed": result.checks_passed,
        "checks_warned": result.checks_warned,
        "checks_failed": result.checks_failed,
        "certification": result.certification,
        "checks": [dc.asdict(c) for c in result.checks],
    }
    (run_dir / "reconciliation.json").write_text(json.dumps(rec_json, indent=2))
    print(f"Written: {run_dir / 'reconciliation.json'}")


if __name__ == "__main__":
    main()
