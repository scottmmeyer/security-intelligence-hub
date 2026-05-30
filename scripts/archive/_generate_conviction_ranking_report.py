"""
Phase 7.0 Report 1: Conviction Ranking Report
All 81 holdings ranked by composite score with signal breakdown and STI classification.
Output: conviction_ranking_report.md
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter, defaultdict

DATA = json.loads(Path("data/derived/phase7_audit_data.json").read_text())
rows = DATA["audit_rows"]
mds  = DATA.get("multi_dimensional_score", {})
recs = DATA.get("recommendations", [])

# ── helpers ───────────────────────────────────────────────────────────────────
def ess_display(t: str) -> str:
    return t if t else "—"

def flag_icon(f: str) -> str:
    return {"ACCUMULATE": "⬆ ACCUMULATE", "TRIM": "⬇ TRIM", "WATCH": "👁 WATCH",
            "HOLD": "◆ HOLD"}.get(f, f or "—")

# ── aggregate stats ───────────────────────────────────────────────────────────
total_holdings = len(rows)
classes = Counter(r["strategic_classification"] for r in rows)
signals = Counter(r["signal_direction"] for r in rows)
replay_count = sum(1 for r in rows if r["replay_supported"])
replay_pct = sum(r["percent_of_portfolio"] for r in rows if r["replay_supported"])

hcr_rows = [r for r in rows if r["strategic_classification"] == "HIGH_CONVICTION_RETAIN"]
tg_rows  = [r for r in rows if r["strategic_classification"] == "TACTICAL_GROWTH"]
other_rows = [r for r in rows if r["strategic_classification"] not in
              ("HIGH_CONVICTION_RETAIN", "TACTICAL_GROWTH")]

hcr_avg = sum(r["composite_score"] for r in hcr_rows) / len(hcr_rows) if hcr_rows else 0
tg_avg  = sum(r["composite_score"] for r in tg_rows)  / len(tg_rows)  if tg_rows  else 0

# Build flag breakdown
flag_by_class: dict[str, Counter] = defaultdict(Counter)
for r in rows:
    flag_by_class[r["strategic_classification"]][r["opportunity_flag"]] += 1

# ── reconstruct retain narrative context from recs ───────────────────────────
retain_recs = [r for r in recs if r.get("recommendation_type") == "STRATEGIC_RETAIN_NARRATIVE"]
retain_symbols = []
for rec in retain_recs:
    title = rec.get("title", "")
    # title format: "Retain Signal: SANM" or "Strategic Retain: SANM"
    parts = title.split(":")
    if len(parts) >= 2:
        retain_symbols.append(parts[-1].strip())

# ── format table rows ─────────────────────────────────────────────────────────
def row_line(r: dict, rank: int) -> str:
    sym   = r["symbol"]
    comp  = f"{r['composite_score']:.3f}"
    ess   = ess_display(r.get("ess_score_text", ""))
    zacks = r.get("zacks_rating") or "—"
    sig   = r.get("signal_direction", "UNKNOWN")
    rep   = "✓" if r["replay_supported"] else "✗"
    sti   = r.get("strategic_classification", "UNKNOWN")
    trim  = f"{r['trim_priority_score']:.1f}" if r.get("trim_priority_score") is not None else "N/A"
    pct   = f"{r['percent_of_portfolio']:.2f}%"
    flag  = r.get("opportunity_flag", "") or "—"
    return f"| {rank} | {sym} | {comp} | {ess} | {zacks} | {sig} | {rep} | {sti} | {trim} | {pct} | {flag} |"

# ── write report ──────────────────────────────────────────────────────────────
lines: list[str] = []
A = lines.append

A("# Phase 7.0 — Conviction Ranking Report")
A("")
A(f"**Run ID**: {DATA['run_id']}  ")
A(f"**Snapshot Date**: {DATA['snapshot_date']}  ")
A(f"**Mandate**: {DATA['mandate_type']}  ")
A(f"**Total Holdings**: {total_holdings}")
A("")

A("## Portfolio Scores")
A("")
A(f"| Dimension | Score |")
A(f"|---|---|")
A(f"| Portfolio Quality | {mds.get('portfolio_quality_score', 'N/A')} |")
A(f"| Implementation Quality | {mds.get('implementation_quality_score', 'N/A')} |")
A(f"| Allocation Alignment | {mds.get('allocation_alignment_score', 'N/A')} |")
A(f"| Replay Alignment | {mds.get('replay_alignment_score', 'N/A')} |")
A("")

A("---")
A("")
A("## Section 1: Top 20 Holdings by Composite Score")
A("")
A("| Rank | Symbol | Composite | ESS | Zacks | Signal | Replay | STI Class | Trim Score | % Portfolio | Flag |")
A("|---|---|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(rows[:20], 1):
    A(row_line(r, i))
A("")

A("---")
A("")
A("## Section 2: All Holdings Ranked (21–81)")
A("")
A("| Rank | Symbol | Composite | ESS | Zacks | Signal | Replay | STI Class | Trim Score | % Portfolio | Flag |")
A("|---|---|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(rows[20:], 21):
    A(row_line(r, i))
A("")

A("---")
A("")
A("## Section 3: Classification Breakdown")
A("")
A(f"**Total Holdings**: {total_holdings}")
A("")
A("| Classification | Count | Avg Composite | Avg Trim Score |")
A("|---|---|---|---|")
for cls_name, cls_rows in [("HIGH_CONVICTION_RETAIN", hcr_rows), ("TACTICAL_GROWTH", tg_rows)]:
    cnt  = len(cls_rows)
    avg  = sum(r["composite_score"] for r in cls_rows) / cnt if cnt else 0
    trims = [r["trim_priority_score"] for r in cls_rows if r.get("trim_priority_score") is not None]
    avg_trim = sum(trims) / len(trims) if trims else 0
    A(f"| {cls_name} | {cnt} | {avg:.3f} | {avg_trim:.1f} |")
for cls_name, cnt in classes.items():
    if cls_name not in ("HIGH_CONVICTION_RETAIN", "TACTICAL_GROWTH"):
        cls_r = [r for r in rows if r["strategic_classification"] == cls_name]
        avg = sum(r["composite_score"] for r in cls_r) / cnt if cnt else 0
        A(f"| {cls_name} | {cnt} | {avg:.3f} | — |")
A("")

A("### HIGH_CONVICTION_RETAIN Holdings")
A("")
A("Sorted by trim score ascending (lowest trim = strongest retain signal).")
A("")
A("| Symbol | Composite | Signal | Trim Score | % Portfolio |")
A("|---|---|---|---|---|")
for r in sorted(hcr_rows, key=lambda x: x.get("trim_priority_score") or 999):
    trim = f"{r['trim_priority_score']:.2f}" if r.get("trim_priority_score") is not None else "N/A"
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['signal_direction']} | {trim} | {r['percent_of_portfolio']:.2f}% |")
A("")

A("### TACTICAL_GROWTH Holdings with Composite ≥ 4.5")
A("")
A("These are high-conviction signal holdings that did not qualify for HIGH_CONVICTION_RETAIN.")
A("")
A("| Symbol | Composite | Signal | Replay | Trim Score | % Portfolio | Key Blocker |")
A("|---|---|---|---|---|---|---|")
for r in [r for r in tg_rows if r["composite_score"] >= 4.5]:
    trim = f"{r['trim_priority_score']:.1f}" if r.get("trim_priority_score") is not None else "N/A"
    # Determine primary blocker
    if not r["replay_supported"]:
        blocker = "No replay support"
    elif r.get("trim_priority_score") and r["trim_priority_score"] >= 30:
        blocker = f"Trim score ≥ 30 ({trim})"
    elif r.get("thematic_redundancy_score") and r["thematic_redundancy_score"] >= 35:
        blocker = f"Thematic redundancy ≥ 35 ({r['thematic_redundancy_score']:.0f})"
    else:
        blocker = "Classification rule not met"
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['signal_direction']} | {'✓' if r['replay_supported'] else '✗'} | {trim} | {r['percent_of_portfolio']:.2f}% | {blocker} |")
A("")

A("---")
A("")
A("## Section 4: Signal Coverage Summary")
A("")
A("| Signal Direction | Count | % of Holdings |")
A("|---|---|---|")
for sig, cnt in sorted(signals.items(), key=lambda x: -x[1]):
    A(f"| {sig} | {cnt} | {cnt/total_holdings*100:.1f}% |")
A("")

A("### Replay Coverage")
A("")
A(f"- **Replay-supported holdings**: {replay_count} of {total_holdings} ({replay_count/total_holdings*100:.1f}%)")
A(f"- **Portfolio value replay-covered**: {replay_pct:.1f}%")
A(f"- **Replay alignment score**: {mds.get('replay_alignment_score', 'N/A')} / 100")
A("")

A("### Opportunity Flag Distribution")
A("")
A("| Flag | Count |")
A("|---|---|")
all_flags = Counter(r.get("opportunity_flag", "") or "NONE" for r in rows)
for flag, cnt in sorted(all_flags.items(), key=lambda x: -x[1]):
    A(f"| {flag} | {cnt} |")
A("")

A("---")
A("")
A("## Section 5: ESS Coverage Gap")
A("")
no_ess = [r for r in rows if not r.get("ess_score_text")]
A(f"**Holdings without ESS score**: {len(no_ess)} of {total_holdings} ({len(no_ess)/total_holdings*100:.1f}%)")
A("")
A("| Symbol | Composite | Signal | Zacks | STI Class |")
A("|---|---|---|---|---|")
for r in sorted(no_ess, key=lambda x: -x["composite_score"])[:20]:
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['signal_direction']} | {r.get('zacks_rating') or '—'} | {r['strategic_classification']} |")
A("")

out = Path("conviction_ranking_report.md")
out.write_text("\n".join(lines))
print(f"Written: {out}  ({out.stat().st_size:,} bytes)")
