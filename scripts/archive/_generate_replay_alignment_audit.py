"""
Phase 7.0 Report 2: Replay Alignment Audit
Explains why replay_alignment_score = 22.9 and audits the 21 replay-supported holdings.
Output: replay_alignment_audit.md
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter

DATA = json.loads(Path("data/derived/phase7_audit_data.json").read_text())
rows = DATA["audit_rows"]
mds  = DATA.get("multi_dimensional_score", {})

replay_rows    = [r for r in rows if r["replay_supported"]]
non_replay_rows = [r for r in rows if not r["replay_supported"]]

total_pct    = sum(r["percent_of_portfolio"] for r in rows)
replay_pct   = sum(r["percent_of_portfolio"] for r in replay_rows)
coverage_frac = replay_pct / total_pct if total_pct else 0

# Formula components (from scoring.py)
coverage_component = coverage_frac * 60
# Quality component = mean replay percentile × 40; percentile data unavailable → 0
percentile_rows = [r for r in replay_rows if r.get("replay_percentile")]
if percentile_rows:
    mean_pct = sum(r["replay_percentile"] for r in percentile_rows) / len(percentile_rows)
    quality_component = mean_pct / 100 * 40
else:
    mean_pct = None
    quality_component = 0.0
total_score = coverage_component + quality_component

# High-composite non-replay holdings
high_comp_no_replay = [r for r in non_replay_rows if r["composite_score"] >= 4.0]
high_comp_no_replay.sort(key=lambda x: -x["composite_score"])

lines: list[str] = []
A = lines.append

A("# Phase 7.0 — Replay Alignment Audit")
A("")
A(f"**Run ID**: {DATA['run_id']}  ")
A(f"**Snapshot Date**: {DATA['snapshot_date']}  ")
A("")

A("## Section 1: Score Formula Decomposition")
A("")
A("The `replay_alignment_score` is computed in `src/portfolio/scoring.py` via")
A("`_compute_replay_alignment()`. It combines two independent components:")
A("")
A("```")
A("replay_alignment_score = Coverage Component (0–60) + Quality Component (0–40)")
A("")
A("Coverage Component = (replay_portfolio_pct / total_portfolio_pct) × 60")
A("Quality Component  = mean_replay_percentile × 40")
A("```")
A("")
A("### Component 1: Coverage (0–60)")
A("")
A(f"- Total portfolio weight tracked: **{total_pct:.2f}%**")
A(f"- Replay-supported weight: **{replay_pct:.2f}%**")
A(f"- Coverage fraction: **{coverage_frac:.4f}** ({coverage_frac*100:.1f}%)")
A(f"- Coverage component: {coverage_frac*100:.1f}% × 60 = **{coverage_component:.1f} pts**")
A("")
A("### Component 2: Quality (0–40)")
A("")
if percentile_rows:
    A(f"- Replay percentile available for {len(percentile_rows)} holdings")
    A(f"- Mean replay percentile: **{mean_pct:.1f}**")
    A(f"- Quality component: {mean_pct:.1f} / 100 × 40 = **{quality_component:.1f} pts**")
else:
    A("- Replay percentile data: **not available** for any holding in this run")
    A("- Quality component: **0.0 pts** (no percentile data to score)")
    A("")
    A("> **Why no percentile data?** The replay engine returns a percentile only when")
    A("> a historical replay simulation has been completed and percentile benchmarking")
    A("> computed. In this snapshot, replay support is binary (supported/not-supported)")
    A("> with no percentile ranking available — so the quality sub-score is zero.")
A("")
A("### Total")
A("")
A(f"```")
A(f"replay_alignment_score = {coverage_component:.1f} + {quality_component:.1f} = {total_score:.1f}")
A(f"Displayed as: {round(total_score)} (rounded to nearest integer)")
A(f"```")
A("")
A(f"> The reported score of **{round(total_score)}** is driven entirely by coverage breadth.")
A(f"> With {len(replay_rows)} of {len(rows)} holdings replay-supported ({len(replay_rows)/len(rows)*100:.1f}% by count,")
A(f"> {coverage_frac*100:.1f}% by portfolio weight), the system has moderate replay evidence")
A(f"> across the portfolio but zero quality-adjusted signal because percentile data")
A(f"> is unavailable.")
A("")

A("---")
A("")
A("## Section 2: Replay-Supported Holdings")
A("")
A(f"**{len(replay_rows)} holdings** are replay-supported, covering **{replay_pct:.1f}%** of portfolio value.")
A("")
A("| Symbol | % Portfolio | Composite | ESS | Signal | STI Class | Trim Score | Flag |")
A("|---|---|---|---|---|---|---|---|")
for r in sorted(replay_rows, key=lambda x: -x["percent_of_portfolio"]):
    trim = f"{r['trim_priority_score']:.1f}" if r.get("trim_priority_score") is not None else "—"
    A(f"| {r['symbol']} | {r['percent_of_portfolio']:.2f}% | {r['composite_score']:.3f} | "
      f"{r.get('ess_score_text') or '—'} | {r['signal_direction']} | "
      f"{r['strategic_classification']} | {trim} | {r.get('opportunity_flag') or '—'} |")
A("")
A(f"**Replay-supported portfolio weight breakdown**: {replay_pct:.2f}% of total tracked weight")
A("")

A("---")
A("")
A("## Section 3: High-Conviction Holdings WITHOUT Replay Support")
A("")
A("These holdings have strong signals (composite ≥ 4.0) but no replay evidence.")
A("Their absence from replay reduces the alignment score and limits STI classification.")
A("")
A("| Symbol | Composite | ESS | Signal | STI Class | Trim Score | % Portfolio | Flag | Impact |")
A("|---|---|---|---|---|---|---|---|---|")
for r in high_comp_no_replay:
    trim = f"{r['trim_priority_score']:.1f}" if r.get("trim_priority_score") is not None else "—"
    # Determine impact: would they qualify for HCR if replay were available?
    trim_val = r.get("trim_priority_score") or 99
    redund   = r.get("thematic_redundancy_score") or 0
    if r["signal_direction"] == "BULLISH" and trim_val < 30 and redund < 35:
        impact = "Would qualify HCR if replay added"
    elif r["signal_direction"] == "BULLISH":
        impact = "BULLISH but other blockers remain"
    else:
        impact = "Non-BULLISH signal"
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r.get('ess_score_text') or '—'} | "
      f"{r['signal_direction']} | {r['strategic_classification']} | {trim} | "
      f"{r['percent_of_portfolio']:.2f}% | {r.get('opportunity_flag') or '—'} | {impact} |")
A("")

A("### Replay Coverage Gap: Would-Be HIGH_CONVICTION_RETAIN")
A("")
would_hcr = [r for r in non_replay_rows
             if r["signal_direction"] == "BULLISH"
             and (r.get("trim_priority_score") or 99) < 30
             and (r.get("thematic_redundancy_score") or 0) < 35]
would_hcr.sort(key=lambda x: -x["composite_score"])
if would_hcr:
    A(f"{len(would_hcr)} holdings currently classified TACTICAL_GROWTH would meet all")
    A(f"HIGH_CONVICTION_RETAIN criteria if replay support were added:")
    A("")
    A("| Symbol | Composite | Signal | Trim Score | Redundancy |")
    A("|---|---|---|---|---|")
    for r in would_hcr:
        trim = f"{r['trim_priority_score']:.1f}" if r.get("trim_priority_score") is not None else "—"
        redund = f"{r.get('thematic_redundancy_score', 0):.0f}" if r.get("thematic_redundancy_score") is not None else "0"
        A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['signal_direction']} | {trim} | {redund} |")
else:
    A("No TACTICAL_GROWTH holdings would immediately qualify for HIGH_CONVICTION_RETAIN")
    A("if replay support were added (other blockers exist).")
A("")

A("---")
A("")
A("## Section 4: What the Score Means")
A("")
A(f"The replay alignment score of **{round(total_score)}/100** reflects:")
A("")
A("1. **Moderate coverage breadth**: {:.0f}% of portfolio value has some replay history,".format(coverage_frac*100))
A("   but the system rewards deeper coverage. Moving from {:.0f}% to 80% coverage".format(coverage_frac*100))
A("   would increase coverage component from {:.1f} to 48.0 pts (+{:.1f} pts).".format(
    coverage_component, 48.0 - coverage_component))
A("")
A("2. **Zero quality signal**: Without replay percentile rankings, the 40-pt quality")
A("   component is completely untapped. If percentile data became available with mean")
A("   percentile of 50, quality would add 20 pts, raising total score by ~20 pts.")
A("")
A("3. **Score interpretation**: The score is not a grade — it measures how well")
A("   the replay evidence aligns with the current portfolio composition.")
A("   A score of 23 means replay evidence exists for a moderate share of holdings")
A("   but no quality benchmarking has been performed.")
A("")

out = Path("replay_alignment_audit.md")
out.write_text("\n".join(lines))
print(f"Written: {out}  ({out.stat().st_size:,} bytes)")
