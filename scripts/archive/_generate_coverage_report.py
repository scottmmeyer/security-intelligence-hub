#!/usr/bin/env python3
"""Phase 6.4C — Generate coverage_reconciliation_report.md for a given run_id.

Usage:
    python scripts/_generate_coverage_report.py [run_id]

If run_id is omitted, uses the most recent analysis run.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.portfolio.reconciliation import _rc13_coverage_reconciliation

_INGESTION_ROOT = _REPO_ROOT / "data" / "portfolio_ingestion"
_COVERAGE_HISTORY = _REPO_ROOT / "data" / "derived" / "coverage_history.csv"
_OUTPUT_PATH = _REPO_ROOT / "coverage_reconciliation_report.md"

_SIGNAL_FIELDS = {
    "ESS": "ess_score_text",
    "Zacks": "zacks_rating",
    "Composite": "composite_score",
}

_GRADE_THRESHOLDS = [(95.0, "A"), (90.0, "B"), (80.0, "C"), (70.0, "D"), (0.0, "F")]


def _grade(pct: float) -> str:
    for threshold, g in _GRADE_THRESHOLDS:
        if pct >= threshold:
            return g
    return "F"


def _grade_badge(g: str) -> str:
    return {"A": "🏆 A", "B": "✅ B", "C": "🟡 C", "D": "🟠 D", "F": "❌ F"}.get(g, g)


def _badge(status: str) -> str:
    return {"PASS": "✅ PASS", "WARN": "⚠️ WARN", "FAIL": "❌ FAIL"}.get(status, status)


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


def _load_coverage_history(current_run_id: str) -> dict[str, dict]:
    """Return previous run coverage by signal, keyed by signal name."""
    if not _COVERAGE_HISTORY.exists():
        return {}
    rows = list(csv.DictReader(open(_COVERAGE_HISTORY)))
    # Find the most recent run that is NOT the current run
    run_ids = []
    for r in rows:
        rid = r["run_id"]
        if rid != current_run_id and rid not in run_ids:
            run_ids.append(rid)
    if not run_ids:
        return {}
    prev_run_id = run_ids[-1]
    prev = {}
    for r in rows:
        if r["run_id"] == prev_run_id:
            prev[r["signal"]] = {
                "pct_holdings": float(r["pct_holdings"]),
                "pct_mv": float(r["pct_mv"]),
                "grade": r["grade"],
            }
    return prev


def _render(run_id: str, holdings: list, run_meta: dict) -> str:
    rc13 = _rc13_coverage_reconciliation(holdings)
    prev_coverage = _load_coverage_history(run_id)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    snap_date = run_meta.get("snapshot_date", "?")
    n_total = len(holdings)
    total_mv = sum(float(h.get("market_value", 0) or 0) for h in holdings)

    lines: list[str] = []
    lines.append(f"# Coverage Reconciliation Report")
    lines.append(f"")
    lines.append(f"**Run ID:** `{run_id}`  ")
    lines.append(f"**Snapshot Date:** {snap_date}  ")
    lines.append(f"**Generated:** {generated_at}  ")
    lines.append(f"**RC-13 Status:** {_badge(rc13.status)}  ")
    lines.append(f"")

    # ── Executive Summary ──────────────────────────────────────────────────────
    lines.append(f"## Executive Summary")
    lines.append(f"")
    sc_by_signal = {sc["signal"]: sc for sc in rc13.sub_checks}

    lines.append(f"| Signal | Holdings Coverage | MV Coverage | Grade | vs Previous |")
    lines.append(f"|--------|------------------|-------------|-------|-------------|")
    for signal in _SIGNAL_FIELDS:
        sc = sc_by_signal.get(signal, {})
        pct_h = sc.get("pct_holdings", 0.0)
        pct_mv = sc.get("pct_mv", 0.0)
        g = sc.get("grade", "?")
        prev = prev_coverage.get(signal, {})
        if prev:
            delta = pct_h - prev["pct_holdings"]
            delta_str = f"{delta:+.1f}pp vs {prev['grade']}"
        else:
            delta_str = "—  (baseline)"
        lines.append(f"| {signal} | {pct_h:.1f}% | {pct_mv:.1f}% | {_grade_badge(g)} | {delta_str} |")

    lines.append(f"")
    lines.append(f"> **Note:** ESS coverage below 70% earns grade F. Zacks and Composite are grade D.")
    lines.append(f"> These are baseline readings. Coverage will improve as signal providers are integrated.")
    lines.append(f"")

    # ── Section 1: Per-Holding Coverage Matrix ─────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 1 — Per-Holding Coverage Matrix")
    lines.append(f"")
    lines.append(f"Holdings sorted by market value descending. Signals: Y=populated, —=missing.")
    lines.append(f"")
    lines.append(f"| Symbol | Asset Class | Market Value | % Portfolio | ESS | Zacks | Composite |")
    lines.append(f"|--------|------------|-------------|-------------|-----|-------|-----------|")

    sorted_holdings = sorted(holdings, key=lambda h: -float(h.get("market_value", 0) or 0))
    for h in sorted_holdings:
        sym = h.get("symbol", "?")
        ac = h.get("asset_class", "?")
        mv = float(h.get("market_value", 0) or 0)
        pct = float(h.get("percent_of_portfolio", 0) or 0)
        ess_val = "Y" if str(h.get("ess_score_text", "") or "").strip() else "—"
        zks_val = "Y" if str(h.get("zacks_rating", "") or "").strip() else "—"
        cmp_val = "Y" if str(h.get("composite_score", "") or "").strip() else "—"
        lines.append(
            f"| `{sym}` | {ac} | ${mv:>10,.0f} | {pct:>6.2f}% | {ess_val} | {zks_val} | {cmp_val} |"
        )

    lines.append(f"")

    # ── Section 2: Coverage Summary ──────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 2 — Coverage Summary by Signal")
    lines.append(f"")
    lines.append(f"| Coverage Type | Holdings Covered | % Holdings | % Portfolio Value | Grade |")
    lines.append(f"|--------------|-----------------|------------|-------------------|-------|")

    for signal, field in _SIGNAL_FIELDS.items():
        covered = [h for h in holdings if str(h.get(field, "") or "").strip()]
        n_cov = len(covered)
        pct_h = n_cov / n_total * 100.0 if n_total else 0.0
        mv_cov = sum(float(h.get("market_value", 0) or 0) for h in covered)
        pct_mv = mv_cov / total_mv * 100.0 if total_mv else 0.0
        g = _grade(pct_h)
        lines.append(f"| {signal} | {n_cov}/{n_total} | {pct_h:.1f}% | {pct_mv:.1f}% | {_grade_badge(g)} |")

    lines.append(f"")

    # ── Section 3: Missing Coverage ───────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 3 — Missing Coverage (Largest Uncovered Positions)")
    lines.append(f"")

    for signal, field in _SIGNAL_FIELDS.items():
        uncovered = sorted(
            [h for h in holdings if not str(h.get(field, "") or "").strip()],
            key=lambda h: -float(h.get("market_value", 0) or 0),
        )
        mv_uncov = sum(float(h.get("market_value", 0) or 0) for h in uncovered)
        pct_uncov = mv_uncov / total_mv * 100.0 if total_mv else 0.0

        lines.append(f"### Missing {signal} Coverage")
        lines.append(f"")
        lines.append(f"**{len(uncovered)} holdings** uncovered ({pct_uncov:.1f}% of portfolio by MV).")
        lines.append(f"")
        if uncovered:
            lines.append(f"| Symbol | Asset Class | Market Value | % Portfolio |")
            lines.append(f"|--------|------------|-------------|-------------|")
            for h in uncovered[:15]:
                sym = h.get("symbol", "?")
                ac = h.get("asset_class", "?")
                mv = float(h.get("market_value", 0) or 0)
                pct = float(h.get("percent_of_portfolio", 0) or 0)
                lines.append(f"| `{sym}` | {ac} | ${mv:>10,.0f} | {pct:.2f}% |")
            if len(uncovered) > 15:
                lines.append(f"| *...{len(uncovered)-15} more* | | | |")
            lines.append(f"")
        else:
            lines.append(f"> ✅ Full {signal} coverage.")
            lines.append(f"")

    # ── Section 4: Coverage Grades ────────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 4 — Coverage Grade Summary")
    lines.append(f"")
    lines.append(f"Grade scale: A ≥ 95% | B ≥ 90% | C ≥ 80% | D ≥ 70% | F < 70%")
    lines.append(f"")
    lines.append(f"| Signal | Holdings % | Grade | Assessment |")
    lines.append(f"|--------|-----------|-------|------------|")

    grade_assessments = {
        "A": "Excellent — full institutional coverage",
        "B": "Good — minor gaps, low risk",
        "C": "Adequate — notable gaps, medium risk",
        "D": "Below threshold — significant gaps, requires attention",
        "F": "Insufficient — critical coverage gap",
    }
    for signal, field in _SIGNAL_FIELDS.items():
        covered = [h for h in holdings if str(h.get(field, "") or "").strip()]
        pct_h = len(covered) / n_total * 100.0 if n_total else 0.0
        g = _grade(pct_h)
        lines.append(f"| {signal} | {pct_h:.1f}% | {_grade_badge(g)} | {grade_assessments[g]} |")

    lines.append(f"")

    # ── Section 5: Trend Baseline ─────────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 5 — Coverage Trend Baseline")
    lines.append(f"")

    if _COVERAGE_HISTORY.exists():
        history = list(csv.DictReader(open(_COVERAGE_HISTORY)))
        run_ids_seen: list[str] = []
        for r in history:
            if r["run_id"] not in run_ids_seen:
                run_ids_seen.append(r["run_id"])

        lines.append(f"Coverage history persisted to `data/derived/coverage_history.csv`.")
        lines.append(f"**{len(run_ids_seen)} run(s) in history.**")
        lines.append(f"")

        if len(run_ids_seen) >= 2:
            lines.append(f"| Signal | Previous % | Current % | Delta |")
            lines.append(f"|--------|-----------|-----------|-------|")
            for signal in _SIGNAL_FIELDS:
                sc = sc_by_signal.get(signal, {})
                curr_pct = sc.get("pct_holdings", 0.0)
                prev = prev_coverage.get(signal, {})
                if prev:
                    prev_pct = prev["pct_holdings"]
                    delta = curr_pct - prev_pct
                    delta_str = f"{delta:+.1f}pp"
                else:
                    prev_pct = float("nan")
                    delta_str = "—"
                prev_str = f"{prev_pct:.1f}%" if prev else "—"
                lines.append(f"| {signal} | {prev_str} | {curr_pct:.1f}% | {delta_str} |")
            lines.append(f"")
        else:
            lines.append(f"> This is the baseline run. Trend comparison will be available on subsequent runs.")
            lines.append(f"")
    else:
        lines.append(f"> Coverage history file not yet created. Run an analysis to establish the baseline.")
        lines.append(f"")

    # ── Section 6: RC-13 Check ─────────────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 6 — RC-13: Coverage Reconciliation Check")
    lines.append(f"")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Check ID | RC-13 |")
    lines.append(f"| Status | {_badge(rc13.status)} |")
    lines.append(f"| Expected | {rc13.expected} |")
    lines.append(f"| Variance | {rc13.variance} |")
    lines.append(f"| Tolerance | {rc13.tolerance} |")
    lines.append(f"| Detail | {rc13.detail[:300]} |")
    lines.append(f"")
    lines.append(f"RC-13 validates that coverage percentages are mathematically consistent")
    lines.append(f"(no signal reports > 100% coverage, counts reconcile with totals).")
    lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*Report generated by `scripts/_generate_coverage_report.py` — Phase 6.4C*")

    return "\n".join(lines)


def main() -> None:
    run_id = sys.argv[1] if len(sys.argv) > 1 else _latest_run_id()
    if not run_id:
        print("No analysis runs found.", file=sys.stderr)
        sys.exit(1)

    run_dir = _INGESTION_ROOT / "analysis_runs" / run_id
    if not run_dir.exists():
        print(f"Run not found: {run_id}", file=sys.stderr)
        sys.exit(1)

    holdings = list(csv.DictReader(open(run_dir / "holdings.csv")))
    run_meta = json.loads((run_dir / "run_metadata.json").read_text()) if (run_dir / "run_metadata.json").exists() else {}

    md = _render(run_id, holdings, run_meta)
    _OUTPUT_PATH.write_text(md)
    print(f"Report written to: {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
