#!/usr/bin/env python3
"""Phase 7.3A — Optimizer Report Generator.

Generates two audit-quality markdown reports from the parallel optimizer:

1. optimizer_candidate_report.md   — all scored candidates per recommendation
2. optimizer_vs_legacy_report.md   — optimizer preferred vs legacy vehicle decisions

Usage:
    cd /path/to/security-intelligence-hub
    source .venv/bin/activate
    python scripts/_generate_phase73a_optimizer_reports.py [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

# ── Ensure the src package is on the path ────────────────────────────────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)


def _load_portfolio() -> tuple[str, str]:
    """Return (csv_text, source_filename) for the most recent portfolio file."""
    port_dir = os.path.join(_REPO_ROOT, "incoming", "portfolio")
    if not os.path.isdir(port_dir):
        port_dir = os.path.join(_REPO_ROOT, "incoming")
    files = [f for f in os.listdir(port_dir) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"No CSV files found in {port_dir}")
    files.sort(reverse=True)
    chosen = files[0]
    path = os.path.join(port_dir, chosen)
    with open(path, encoding="utf-8") as fh:
        return fh.read(), chosen


def _run_pipeline(snapshot_date: str | None = None) -> dict:
    """Run the full analysis pipeline and return the result dict."""
    from src.portfolio.runner import run_analysis  # noqa: PLC0415

    portfolio_content, source_filename = _load_portfolio()
    result = run_analysis(
        portfolio_content=portfolio_content,
        source_filename=source_filename,
        snapshot_date=snapshot_date,
        mandate_type="CONCENTRATED_ALPHA",
    )
    if result.get("status") != "COMPLETE":
        raise RuntimeError(f"Pipeline returned non-COMPLETE status: {result.get('status')}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Report 1 — optimizer_candidate_report.md
# ─────────────────────────────────────────────────────────────────────────────

def _build_candidate_report(result: dict, generated_at: str) -> str:
    lines: list[str] = []
    lines.append("# Optimizer Candidate Report")
    lines.append(f"\n**Generated:** {generated_at}")
    lines.append(f"**Mandate:** {result.get('mandate_display_name', result.get('mandate_type', ''))}")
    lines.append(f"**Portfolio:** {result.get('total_market_value', 0):,.0f} | "
                 f"{result.get('holding_count', 0)} holdings | "
                 f"Date: {result.get('snapshot_date', '')}")
    lines.append(f"**Run ID:** {result.get('run_id', '')}")

    optimizer_scores: dict = result.get("optimizer_scores", {})
    recs: list = result.get("recommendations", [])

    # Global conflict summary
    sample_result = next(iter(optimizer_scores.values()), None) if optimizer_scores else None
    if sample_result:
        t1 = sample_result.get("total_t1_conflicts", 0)
        t2 = sample_result.get("total_t2_conflicts", 0)
        t3 = sample_result.get("total_t3_conflicts", 0)
        lines.append(f"\n**Cross-rec conflicts detected:** T1={t1} | T2={t2} | T3={t3}")

        all_conflicts = sample_result.get("all_conflicts", [])
        if all_conflicts:
            lines.append("\n### Conflict Summary")
            for cf in all_conflicts:
                icon = {"T1": "🔴", "T2": "🟡", "T3": "🔴"}.get(cf.get("conflict_type", ""), "⚪")
                lines.append(
                    f"- **{cf.get('conflict_type')}** [{icon}]: {cf.get('description')}  "
                    f"  `severity={cf.get('severity')} | vehicle={cf.get('vehicle')}`"
                )

    lines.append("\n---\n")

    # Per-recommendation candidate tables
    for rec in recs:
        rec_id = rec.get("recommendation_id", "")
        rec_type = rec.get("recommendation_type", "")
        target_node = rec.get("affected_node_key", "")
        severity = rec.get("severity", "")
        title = rec.get("title", "")
        mandate_urgency = rec.get("mandate_urgency", "")
        mandate_label = rec.get("mandate_drift_label", "")

        opt = optimizer_scores.get(rec_id)
        if not opt:
            continue

        optimizer_decision = opt.get("optimizer_decision", "")
        candidates = opt.get("candidates", [])
        conflicts = opt.get("conflicts_detected", [])

        lines.append(f"## {title}")
        lines.append(f"**Rec ID:** `{rec_id}`  **Type:** {rec_type}  **Node:** `{target_node}`  "
                     f"**Severity:** {severity}  **Mandate urgency:** {mandate_urgency}  "
                     f"**Mandate label:** {mandate_label}")
        lines.append(f"**Optimizer decision:** `{optimizer_decision}`")

        if conflicts:
            cf_summary = " | ".join(
                f"{c['conflict_type']}:{c.get('vehicle','?')}" for c in conflicts
            )
            lines.append(f"**Conflicts:** {cf_summary}")

        if not candidates:
            lines.append("\n_No candidates evaluated for this recommendation type._\n")
            lines.append("---\n")
            continue

        lines.append(
            "\n| Candidate | Type | Target Node | PIS | Mandate Status | ETF Gate | "
            "NCS | Suit | Composite | Replay | STI Tier | Trim | Helps/Node | Conflict Flags |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )

        for c in candidates:
            sym = c.get("symbol", "")
            ctype = c.get("candidate_type", "")
            pis = c.get("pis", 0.0)
            ostatus = c.get("optimizer_status", "")
            etf_gate = c.get("etf_gate", "N/A")
            ncs = c.get("ncs", 0.0)
            suit = c.get("suitability_tier", "N/A")
            composite = c.get("composite_score")
            replay = "✓" if c.get("replay_supported") else ""
            sti = c.get("sti_tier", "")
            worsens = "⚠ worsens OW" if c.get("worsens_overweight") else ""
            conflict_flags = "; ".join(c.get("conflict_nodes", []))
            comp_str = f"{composite:.3f}" if composite is not None else "—"
            trim = c.get("components", {}).get("trim_penalty", 0.0)

            # Bold the preferred candidate
            if pis == (candidates[0]["pis"] if candidates else -1):
                sym = f"**{sym}**"
                pis_str = f"**{pis:.1f}**"
            else:
                pis_str = f"{pis:.1f}"

            lines.append(
                f"| {sym} | {ctype} | `{target_node}` | {pis_str} | {ostatus} | "
                f"{etf_gate} | {ncs:.1f}% | {suit} | {comp_str} | {replay} | "
                f"{sti} | {trim:.1f} | {target_node} | {conflict_flags}{worsens} |"
            )

        lines.append("")
        lines.append("---\n")

    # Summary statistics
    build_recs_scored = [
        opt for opt in optimizer_scores.values()
        if opt.get("rec_type") == "INCREASE_UNDERWEIGHT"
    ]
    if build_recs_scored:
        lines.append("## Summary Statistics")
        decisions = {}
        for opt in build_recs_scored:
            d = opt.get("optimizer_decision", "UNKNOWN")
            decisions[d] = decisions.get(d, 0) + 1
        for decision, count in sorted(decisions.items()):
            lines.append(f"- **{decision}**: {count} rec(s)")

        blocked = sum(1 for opt in build_recs_scored if opt.get("mandate_blocked"))
        lines.append(f"- **Mandate blocked**: {blocked} rec(s)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 2 — optimizer_vs_legacy_report.md
# ─────────────────────────────────────────────────────────────────────────────

def _build_vs_legacy_report(result: dict, generated_at: str) -> str:
    lines: list[str] = []
    lines.append("# Optimizer vs Legacy Recommendation Report")
    lines.append(f"\n**Generated:** {generated_at}")
    lines.append(f"**Mandate:** {result.get('mandate_display_name', result.get('mandate_type', ''))}")
    lines.append(f"**Portfolio:** {result.get('total_market_value', 0):,.0f} | "
                 f"{result.get('holding_count', 0)} holdings | "
                 f"Date: {result.get('snapshot_date', '')}")
    lines.append(f"**Run ID:** {result.get('run_id', '')}")

    lines.append("\n## Design Principles")
    lines.append(
        "> This report compares the **legacy recommendation engine output** (existing, unchanged) "
        "against the **Phase 7.3A parallel optimizer** candidate rankings. "
        "The legacy recommendations are **not modified** by this analysis. "
        "This report informs Phase 7.3D migration planning only."
    )

    optimizer_scores: dict = result.get("optimizer_scores", {})
    recs: list = result.get("recommendations", [])

    lines.append("\n## Build Recommendation Comparison\n")
    lines.append(
        "| Legacy Rec | Legacy Vehicles | Legacy Severity | Mandate Urgency | "
        "Optimizer Preferred | PIS | Optimizer Decision | Notes |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")

    for rec in recs:
        rec_id = rec.get("recommendation_id", "")
        rec_type = rec.get("recommendation_type", "")
        if rec_type != "INCREASE_UNDERWEIGHT":
            continue

        opt = optimizer_scores.get(rec_id)
        if not opt:
            continue

        title = rec.get("title", "")
        legacy_vehicles = opt.get("legacy_vehicles", [])
        legacy_vehicles_str = ", ".join(str(v) for v in legacy_vehicles[:3])
        if len(legacy_vehicles) > 3:
            legacy_vehicles_str += ", ..."
        severity = rec.get("severity", "")
        mandate_urgency = rec.get("mandate_urgency", "")
        preferred = opt.get("preferred_candidate")
        optimizer_decision = opt.get("optimizer_decision", "")

        if preferred:
            pref_sym = preferred.get("symbol", "—")
            pref_pis = f"{preferred.get('pis', 0.0):.1f}"
            pref_type = preferred.get("candidate_type", "")
        else:
            pref_sym = "—"
            pref_pis = "0"
            pref_type = ""

        # Compose notes
        notes_parts = []
        if opt.get("mandate_blocked"):
            notes_parts.append("Mandate BLOCKED")
        if preferred and preferred.get("replay_supported"):
            notes_parts.append(f"replay ✓")
        if preferred and preferred.get("composite_score") is not None:
            notes_parts.append(f"composite={preferred['composite_score']:.3f}")
        if preferred and preferred.get("sti_tier") not in (None, "", "NA"):
            notes_parts.append(f"STI={preferred['sti_tier']}")
        conflicts = opt.get("conflicts_detected", [])
        if conflicts:
            notes_parts.append(
                " ".join(f"[{c['conflict_type']}:{c.get('vehicle','?')}]" for c in conflicts)
            )
        notes = "; ".join(notes_parts) if notes_parts else "—"

        # Highlight SECURITY_SUPERIOR in bold
        decision_str = f"**{optimizer_decision}**" if optimizer_decision == "SECURITY_SUPERIOR" else optimizer_decision
        pref_str = f"**{pref_sym}** ({pref_type})" if optimizer_decision == "SECURITY_SUPERIOR" else f"{pref_sym} ({pref_type})"

        lines.append(
            f"| {title} | {legacy_vehicles_str} | {severity} | {mandate_urgency} | "
            f"{pref_str} | {pref_pis} | {decision_str} | {notes} |"
        )

    # Focus: US Large comparison (the archetypal validation case)
    lines.append("\n## Spotlight: US Large Deployment Decision\n")
    lines.append(
        "The Phase 7.3A key validation: for the 'Build US Large' recommendation, does the optimizer "
        "correctly rank individual portfolio securities (VRT, LRCX, DELL) above ETF vehicles "
        "(VOO, IVV, SPY) when the ETFs would worsen the HYPER_MEGA overweight?"
    )

    for rec in recs:
        rec_id = rec.get("recommendation_id", "")
        if rec.get("recommendation_type") != "INCREASE_UNDERWEIGHT":
            continue
        if "EQUITIES.US.LARGE" not in (rec.get("affected_node_key") or ""):
            continue

        opt = optimizer_scores.get(rec_id)
        if not opt:
            continue

        candidates = opt.get("candidates", [])
        securities = [c for c in candidates if c.get("candidate_type") == "SECURITY"]
        etfs = [c for c in candidates if c.get("candidate_type") == "ETF"]

        lines.append(f"\n**Recommendation:** {rec.get('title', '')}")
        lines.append(f"**Mandate urgency:** {rec.get('mandate_urgency', '')} | "
                     f"**Optimizer decision:** {opt.get('optimizer_decision', '')}")

        if securities:
            lines.append("\n**Security candidates:**")
            lines.append("| Symbol | PIS | Composite | Replay | STI | % of Port | Status |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for c in securities[:5]:
                comp_str = f"{c['composite_score']:.3f}" if c['composite_score'] is not None else "—"
                lines.append(
                    f"| **{c['symbol']}** | {c['pis']:.1f} | "
                    f"{comp_str} | "
                    f"{'✓' if c['replay_supported'] else ''} | {c['sti_tier']} | "
                    f"{c['percent_of_portfolio']:.2f}% | {c['optimizer_status']} |"
                )

        if etfs:
            lines.append("\n**ETF candidates:**")
            lines.append("| Symbol | PIS | NCS | ETF Gate | Suitability | Worsens OW | Status |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for c in etfs[:5]:
                lines.append(
                    f"| {c['symbol']} | {c['pis']:.1f} | {c['ncs']:.1f}% | "
                    f"{c['etf_gate']} | {c['suitability_tier']} | "
                    f"{'⚠ YES' if c['worsens_overweight'] else 'No'} | {c['optimizer_status']} |"
                )

    # All rec decisions summary
    lines.append("\n## All Recommendation Optimizer Decisions\n")
    lines.append("| Rec ID | Type | Node | Decision |")
    lines.append("| --- | --- | --- | --- |")
    for rec in recs:
        rec_id = rec.get("recommendation_id", "")
        opt = optimizer_scores.get(rec_id)
        if not opt:
            continue
        lines.append(
            f"| `{rec_id}` | {rec.get('recommendation_type','')} | "
            f"`{rec.get('affected_node_key', '—')}` | {opt.get('optimizer_decision', '')} |"
        )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 7.3A optimizer reports")
    parser.add_argument("--date", default=None, help="Snapshot date (YYYY-MM-DD), default=today")
    parser.add_argument(
        "--outdir", default=None,
        help="Output directory (default: data/exports/)"
    )
    args = parser.parse_args()

    out_dir = args.outdir or os.path.join(_REPO_ROOT, "data", "exports")
    os.makedirs(out_dir, exist_ok=True)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"[7.3A] Running pipeline... (snapshot_date={args.date or 'today'})")
    result = _run_pipeline(snapshot_date=args.date)
    print(f"[7.3A] Pipeline COMPLETE. Run ID: {result.get('run_id')} | "
          f"Recs: {result.get('recommendation_count')} | "
          f"Optimizer scores: {len(result.get('optimizer_scores', {}))}")

    # Report 1
    r1 = _build_candidate_report(result, generated_at)
    r1_path = os.path.join(out_dir, "optimizer_candidate_report.md")
    with open(r1_path, "w", encoding="utf-8") as fh:
        fh.write(r1)
    print(f"[7.3A] Written: {r1_path}")

    # Report 2
    r2 = _build_vs_legacy_report(result, generated_at)
    r2_path = os.path.join(out_dir, "optimizer_vs_legacy_report.md")
    with open(r2_path, "w", encoding="utf-8") as fh:
        fh.write(r2)
    print(f"[7.3A] Written: {r2_path}")

    # Print key spotlight: US Large decision
    opt_scores = result.get("optimizer_scores", {})
    recs = result.get("recommendations", [])
    for rec in recs:
        if rec.get("recommendation_type") == "INCREASE_UNDERWEIGHT" and "EQUITIES.US.LARGE" in (rec.get("affected_node_key") or ""):
            rid = rec.get("recommendation_id", "")
            opt = opt_scores.get(rid, {})
            candidates = opt.get("candidates", [])
            if candidates:
                print(f"\n[7.3A] US Large candidate ranking:")
                for i, c in enumerate(candidates[:6], 1):
                    print(f"  {i}. {c['symbol']:<8} PIS={c['pis']:<6.1f} type={c['candidate_type']:<8} "
                          f"status={c['optimizer_status']}")
            print(f"[7.3A] US Large decision: {opt.get('optimizer_decision', '')}")


if __name__ == "__main__":
    main()
