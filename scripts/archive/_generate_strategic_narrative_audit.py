"""
Phase 7.0 Report 3: Strategic Narrative Audit
Explains why SANM/PSX/SNX are selected as strategic retain anchors,
why VRT/LRCX/DELL/MU/CVE/ASML are not, and what's absent from narratives.
Output: strategic_narrative_audit.md
"""
from __future__ import annotations
import json, re
from pathlib import Path

DATA = json.loads(Path("data/derived/phase7_audit_data.json").read_text())
rows = DATA["audit_rows"]
recs = DATA.get("recommendations", [])
rows_by_sym = {r["symbol"]: r for r in rows}

# ── Parse out retain-narrative recommendations ────────────────────────────────
retain_recs = [r for r in recs if r.get("recommendation_type") == "STRATEGIC_RETAIN_NARRATIVE"]
construction_recs = [r for r in recs if r.get("recommendation_type") in
                     ("PORTFOLIO_CONSTRUCTION_NARRATIVE", "STRATEGIC_PORTFOLIO_NARRATIVE")]

# ── HCR holdings sorted the way phase_e_synthesis does it ────────────────────
# sort by (class_priority=0 for HCR, trim_score) → top-3 get narratives
hcr_rows = [r for r in rows if r["strategic_classification"] == "HIGH_CONVICTION_RETAIN"]
hcr_sorted = sorted(hcr_rows, key=lambda r: r.get("trim_priority_score") or 999)

# The top-3 (selected) vs the rest (just missed)
selected   = hcr_sorted[:3]
just_missed = hcr_sorted[3:8]  # next 5
further    = hcr_sorted[8:]

# ── Non-HCR high-composite holdings ──────────────────────────────────────────
high_comp_tg = [r for r in rows
                if r["strategic_classification"] != "HIGH_CONVICTION_RETAIN"
                and r["composite_score"] >= 4.0]
high_comp_tg.sort(key=lambda x: -x["composite_score"])

lines: list[str] = []
A = lines.append

A("# Phase 7.0 — Strategic Narrative Audit")
A("")
A(f"**Run ID**: {DATA['run_id']}  ")
A(f"**Snapshot Date**: {DATA['snapshot_date']}  ")
A("")
A("---")
A("")
A("## Section 1: How Strategic Retain Narratives Are Selected")
A("")
A("The `_generate_retain_narratives()` function in `src/portfolio/phase_e_synthesis.py`")
A("selects at most **3 holdings** to receive a named strategic retain recommendation:")
A("")
A("```python")
A("retain_candidates = sorted(")
A("    [p for p in profiles if p.strategic_classification in")
A("     {\"HIGH_CONVICTION_RETAIN\", \"CORE_COMPOUNDER\", \"STRATEGIC_CORE\"}],")
A("    key=lambda p: (")
A("        0 if p.strategic_classification == \"HIGH_CONVICTION_RETAIN\" else")
A("        1 if p.strategic_classification == \"CORE_COMPOUNDER\" else")
A("        2 if p.strategic_classification == \"STRATEGIC_CORE\" else 3,")
A("        p.trim_priority_score,")
A("    ),")
A(")[:3]  # hard cap: 3 retain narratives")
A("```")
A("")
A("### Selection Logic")
A("")
A("1. Only **HIGH_CONVICTION_RETAIN**, CORE_COMPOUNDER, and STRATEGIC_CORE holdings are eligible.")
A("2. Among eligible holdings, sort by **(classification priority, trim_score ascending)**.")
A("3. Take the **top 3** — i.e., the 3 highest-priority holdings with the **lowest trim scores**.")
A("")
A("Since all classified holdings in this run are either HIGH_CONVICTION_RETAIN or TACTICAL_GROWTH,")
A("only HIGH_CONVICTION_RETAIN holdings compete, and **the 3 with the lowest trim scores win**.")
A("")

A("---")
A("")
A("## Section 2: Selected Holdings — Why They Won")
A("")
A("| Rank | Symbol | Trim Score | Composite | Signal | % Portfolio | Why Selected |")
A("|---|---|---|---|---|---|---|")
for i, r in enumerate(selected, 1):
    trim = f"{r['trim_priority_score']:.2f}" if r.get("trim_priority_score") is not None else "N/A"
    pct  = f"{r['percent_of_portfolio']:.2f}%"
    A(f"| {i} | **{r['symbol']}** | **{trim}** | {r['composite_score']:.3f} | "
      f"{r['signal_direction']} | {pct} | Lowest trim score among all HCR holdings |")
A("")
A("### Why These Holdings Have Near-Zero Trim Scores")
A("")
A("The `_compute_trim_priority_score()` additive model produces near-zero scores when:")
A("")
A("- **concentration_pressure** ≈ 0: The holding's allocation node is NOT overweight relative to CONCENTRATED_ALPHA mandate targets")
A("- **thematic_overlap** ≈ 0: The holding has no thematic redundancy with other portfolio holdings (unique exposure)")
A("- **signal_weakness** = 0: BULLISH signal with composite ≥ 3.5 → full signal strength discount applied")
A("- **replay_weakness** = 0: Replay-supported with adequate percentile tier")
A("- **strategic_role_importance**: Retain credit applied (−5 to −25 pts)")
A("")
A("These three holdings are small positions (< 1% each) that sit in allocation nodes")
A("that are at or below CONCENTRATED_ALPHA mandate targets, giving them effectively")
A("zero concentration pressure — the dominant trim driver for larger positions.")
A("")
for r in selected:
    tf = r.get("trim_factors") or []
    if tf:
        A(f"**{r['symbol']}** (trim={r.get('trim_priority_score'):.2f}) trim factor breakdown:")
        A("")
        A("| Factor | Contribution | Rationale |")
        A("|---|---|---|")
        for f in tf:
            if isinstance(f, dict):
                A(f"| {f.get('factor','—')} | {f.get('contribution', '—')} | {f.get('rationale','—')} |")
        A("")

A("---")
A("")
A("## Section 3: Holdings That Just Missed the Narrative")
A("")
A("These HIGH_CONVICTION_RETAIN holdings ranked 4th–8th in the selection order.")
A("They share the same classification tier but have higher trim scores.")
A("")
A("| Rank | Symbol | Trim Score | Composite | % Portfolio | Why Not Selected |")
A("|---|---|---|---|---|---|")
for i, r in enumerate(just_missed, 4):
    trim = f"{r['trim_priority_score']:.2f}" if r.get("trim_priority_score") is not None else "N/A"
    A(f"| {i} | {r['symbol']} | {trim} | {r['composite_score']:.3f} | "
      f"{r['percent_of_portfolio']:.2f}% | Trim score > top-3 threshold ({selected[2].get('trim_priority_score', 0):.2f}) |")
A("")
A("### Trim Score Drivers for 4th–8th Place")
A("")
for r in just_missed:
    trim = r.get("trim_priority_score")
    trace = r.get("classification_trace", "")
    trim_disp = f"{trim:.1f}" if trim is not None else "N/A"
    A(f"**{r['symbol']}** (trim={trim_disp}):")
    tf = r.get("trim_factors") or []
    if tf:
        A("")
        A("| Factor | Contribution | Rationale |")
        A("|---|---|---|")
        for f in tf:
            if isinstance(f, dict):
                A(f"| {f.get('factor','—')} | {f.get('contribution', '—')} | {f.get('rationale','—')} |")
    elif trace:
        A(f"> {trace}")
    A("")

A("---")
A("")
A("## Section 4: High-Composite Holdings NOT in Any Narrative")
A("")
A("Holdings with composite ≥ 4.0 not classified HIGH_CONVICTION_RETAIN — they appear")
A("nowhere in strategic retain narratives.")
A("")
A("| Symbol | Composite | STI Class | Signal | Replay | Trim | % Portfolio | Primary Blocker |")
A("|---|---|---|---|---|---|---|---|")
for r in high_comp_tg[:15]:
    trim = f"{r.get('trim_priority_score', 0):.1f}" if r.get("trim_priority_score") is not None else "—"
    # Primary blocker logic
    if not r["replay_supported"]:
        blocker = "No replay support (fails HCR gate)"
    elif r.get("trim_priority_score") is not None and r["trim_priority_score"] >= 30:
        blocker = f"Trim score ≥ 30 (trim={trim})"
    elif r.get("thematic_redundancy_score") is not None and r["thematic_redundancy_score"] >= 35:
        blocker = f"Thematic redundancy ≥ 35 ({r['thematic_redundancy_score']:.0f})"
    else:
        blocker = "See classification trace"
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['strategic_classification']} | "
      f"{r['signal_direction']} | {'✓' if r['replay_supported'] else '✗'} | {trim} | "
      f"{r['percent_of_portfolio']:.2f}% | {blocker} |")
A("")

A("---")
A("")
A("## Section 5: Strategic Narrative Text from Run")
A("")
if retain_recs:
    A(f"**{len(retain_recs)} STRATEGIC_RETAIN_NARRATIVE recommendations generated:**")
    A("")
    for rec in retain_recs:
        A(f"### {rec.get('title', 'Untitled')}")
        A("")
        A(f"**Priority**: {rec.get('priority', '—')}  ")
        A(f"**Confidence**: {rec.get('confidence', '—')}  ")
        A("")
        A(rec.get("narrative", "") or rec.get("rationale", "") or "_No narrative text_")
        A("")
else:
    A("_No STRATEGIC_RETAIN_NARRATIVE recommendations found in this run's output._")
    A("")
    A("Check if retain narratives are stored under a different recommendation type:")
    A("")
    rec_types = list({r.get("recommendation_type", "") for r in recs})
    for rt in sorted(rec_types):
        cnt = sum(1 for r in recs if r.get("recommendation_type") == rt)
        A(f"- `{rt}`: {cnt} recommendations")
A("")

A("---")
A("")
A("## Section 6: What Is Missing From the Narrative")
A("")
A("The strategic narrative generator is constrained to 3 retain signals. Given 19")
A(f"HIGH_CONVICTION_RETAIN holdings and {len(rows)} total holdings, this means **16 HCR**")
A("holdings receive no named retain narrative. Among the most notable omissions:")
A("")
A("| Symbol | Composite | Trim Score | Why Absent From Narrative |")
A("|---|---|---|---|")
all_hcr_not_selected = [r for r in hcr_rows if r["symbol"] not in [s["symbol"] for s in selected]]
all_hcr_not_selected.sort(key=lambda x: x.get("trim_priority_score") or 999)
for r in all_hcr_not_selected[:10]:
    trim = f"{r.get('trim_priority_score', 0):.2f}" if r.get("trim_priority_score") is not None else "—"
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {trim} | Trim score exceeds top-3 threshold; ranked #{hcr_sorted.index(r)+1} of {len(hcr_sorted)} HCR |")
A("")
A("> **Note**: Absent from narrative ≠ absent from portfolio action.")
A("> All HIGH_CONVICTION_RETAIN holdings still receive an ACCUMULATE flag in security_overlays.")
A("> The narrative is an explanatory layer on top of the classification, not the classification itself.")
A("")

out = Path("strategic_narrative_audit.md")
out.write_text("\n".join(lines))
print(f"Written: {out}  ({out.stat().st_size:,} bytes)")
