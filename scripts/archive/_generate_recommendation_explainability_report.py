"""
Phase 7.0 Report 4: Recommendation Explainability Report
One explanation card per holding for the top 20 by composite score.
Output: recommendation_explainability_report.md
"""
from __future__ import annotations
import json
from pathlib import Path

DATA = json.loads(Path("data/derived/phase7_audit_data.json").read_text())
rows = DATA["audit_rows"]
top20 = rows[:20]

# ── Helper: classify why holding has its opportunity flag ─────────────────────
def explain_flag(r: dict) -> str:
    flag = r.get("opportunity_flag", "") or ""
    sig  = r.get("signal_direction", "")
    rep  = r.get("replay_supported", False)
    ow   = r.get("is_overweight_vs_target", False)
    if flag == "ACCUMULATE":
        return "BULLISH signal + replay support → system recommends adding exposure"
    if flag == "TRIM":
        return "Weak signal + overweight allocation → system recommends reducing exposure"
    if flag == "WATCH":
        return "BULLISH signal but no replay support → system flags for monitoring"
    if flag == "HOLD":
        parts = []
        if not rep:
            parts.append("no replay support")
        if sig not in ("BULLISH", "VERY_BULLISH"):
            parts.append(f"signal is {sig}")
        return "No clear action signal: " + (", ".join(parts) or "signal conditions not met")
    return flag or "No flag"

# ── Helper: explain why this STI classification ───────────────────────────────
def explain_sti(r: dict) -> str:
    cls   = r.get("strategic_classification", "UNKNOWN")
    sig   = r.get("signal_direction", "")
    rep   = r.get("replay_supported", False)
    trim  = r.get("trim_priority_score")
    redund = r.get("thematic_redundancy_score")

    if cls == "HIGH_CONVICTION_RETAIN":
        redund_val = f"{redund:.0f}" if redund else "0"
        trim_val_s = f"{trim:.1f}" if trim else "0"
        return (
            f"Meets all 4 HCR gates: (1) BULLISH signal, "
            f"(2) replay-supported, "
            f"(3) thematic redundancy < 35 ({redund_val}), "
            f"(4) trim score < 30 ({trim_val_s})"
        )
    if cls == "TACTICAL_GROWTH":
        blockers = []
        if sig != "BULLISH":
            blockers.append(f"signal is {sig} (not BULLISH)")
        if not rep:
            blockers.append("no replay support (fails gate 2)")
        if redund is not None and redund >= 35:
            blockers.append(f"thematic redundancy ≥ 35 ({redund:.0f})")
        if trim is not None and trim >= 30:
            blockers.append(f"trim score ≥ 30 ({trim:.1f})")
        if blockers:
            return "Fails HCR gates: " + "; ".join(blockers)
        return "Did not meet HCR threshold conditions"
    return cls

# ── Helper: format trim factors table ─────────────────────────────────────────
def trim_factors_md(r: dict) -> str:
    tf = r.get("trim_factors") or []
    if not tf:
        return "_No trim factor detail available_"
    lines = ["| Factor | Contribution | Rationale |", "|---|---|---|"]
    for f in tf:
        if isinstance(f, dict):
            lines.append(f"| {f.get('factor','—')} | {f.get('contribution','—')} | {f.get('rationale','—')} |")
    return "\n".join(lines)

# ── Signal score summary ───────────────────────────────────────────────────────
def signal_summary(r: dict) -> str:
    parts = []
    ess = r.get("ess_score_text", "")
    zacks = r.get("zacks_rating", "")
    comp = r.get("composite_score", 0)
    if ess:
        parts.append(f"ESS: **{ess}**")
    else:
        parts.append("ESS: _no score_")
    if zacks:
        parts.append(f"Zacks: **{zacks}**")
    else:
        parts.append("Zacks: _no rating_")
    parts.append(f"Composite: **{comp:.3f}**")
    parts.append(f"Direction: **{r.get('signal_direction','?')}**")
    return " | ".join(parts)

# ── Build report ──────────────────────────────────────────────────────────────
lines: list[str] = []
A = lines.append

A("# Phase 7.0 — Recommendation Explainability Report")
A("")
A(f"**Run ID**: {DATA['run_id']}  ")
A(f"**Snapshot Date**: {DATA['snapshot_date']}  ")
A("")
A("Top 20 holdings by composite score, with a full explanation of why each")
A("holding received its recommendation classification.")
A("")
A("---")
A("")

for rank, r in enumerate(top20, 1):
    sym   = r["symbol"]
    desc  = r.get("description", "") or ""
    pct   = r["percent_of_portfolio"]
    cls   = r.get("strategic_classification", "UNKNOWN")
    flag  = r.get("opportunity_flag", "") or "—"
    trim  = r.get("trim_priority_score")
    trim_display = f"{trim:.2f}" if trim is not None else "N/A"

    A(f"## Card {rank}: {sym}")
    if desc:
        A(f"*{desc}*  ")
    A(f"**Portfolio Weight**: {pct:.2f}%  |  "
      f"**Sector**: {r.get('sector','—')}  |  "
      f"**Security Type**: {r.get('security_type','—')}")
    A("")

    A("### Signal Inputs")
    A("")
    A(signal_summary(r))
    A("")

    A("### Strategic Classification")
    A("")
    A(f"**Classification**: `{cls}`  ")
    A(f"**Trim Priority Score**: {trim_display}  ")
    A(f"**Thematic Redundancy**: {r.get('thematic_redundancy_score', 0) or 0:.0f}  ")
    A(f"**Replay Supported**: {'Yes' if r.get('replay_supported') else 'No'}")
    A("")
    A(f"**Why this classification**: {explain_sti(r)}")
    A("")

    if r.get("trim_factors"):
        A("**Trim Score Breakdown:**")
        A("")
        A(trim_factors_md(r))
        A("")

    A("### Opportunity Flag")
    A("")
    A(f"**Flag**: `{flag}`  ")
    A(f"**Why**: {explain_flag(r)}")
    A("")

    if r.get("retain_rationale"):
        A("**Retain Rationale:**")
        A(f"> {r['retain_rationale']}")
        A("")

    if r.get("trim_rationale"):
        A("**Trim Rationale:**")
        A(f"> {r['trim_rationale']}")
        A("")

    if r.get("classification_trace"):
        A("**Classification Trace:**")
        A(f"> {r['classification_trace']}")
        A("")

    if r.get("overlap_peers"):
        A(f"**Thematic Overlap Peers**: {', '.join(r['overlap_peers'])}")
        A("")

    A("---")
    A("")

out = Path("recommendation_explainability_report.md")
out.write_text("\n".join(lines))
print(f"Written: {out}  ({out.stat().st_size:,} bytes)")
