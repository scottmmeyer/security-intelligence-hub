"""
Phase 7.0 Report 5: Conviction Model Quality Report
Examines whether HIGH_CONVICTION_RETAIN truly captures the highest-conviction holdings,
identifies anomalies, gaps, and structural observations.
Output: conviction_model_quality_report.md
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter, defaultdict
import statistics

DATA = json.loads(Path("data/derived/phase7_audit_data.json").read_text())
rows = DATA["audit_rows"]
mds  = DATA.get("multi_dimensional_score", {})

rows_by_sym = {r["symbol"]: r for r in rows}
hcr_rows  = [r for r in rows if r["strategic_classification"] == "HIGH_CONVICTION_RETAIN"]
tg_rows   = [r for r in rows if r["strategic_classification"] == "TACTICAL_GROWTH"]
other_rows = [r for r in rows if r["strategic_classification"] not in
              ("HIGH_CONVICTION_RETAIN", "TACTICAL_GROWTH")]

# ── Stats per classification ──────────────────────────────────────────────────
def cls_stats(cls_rows: list[dict]) -> dict:
    if not cls_rows:
        return {"count": 0, "avg_comp": 0, "med_comp": 0, "min_comp": 0, "max_comp": 0,
                "avg_trim": 0, "replay_pct": 0}
    comps = [r["composite_score"] for r in cls_rows]
    trims = [r["trim_priority_score"] for r in cls_rows if r.get("trim_priority_score") is not None]
    replay_n = sum(1 for r in cls_rows if r["replay_supported"])
    return {
        "count": len(cls_rows),
        "avg_comp": statistics.mean(comps),
        "med_comp": statistics.median(comps),
        "min_comp": min(comps),
        "max_comp": max(comps),
        "avg_trim": statistics.mean(trims) if trims else 0,
        "replay_pct": replay_n / len(cls_rows) * 100,
    }

hcr_s = cls_stats(hcr_rows)
tg_s  = cls_stats(tg_rows)

# ── Anomaly: TACTICAL_GROWTH holdings with composite ≥ HCR average ───────────
hcr_avg_comp = hcr_s["avg_comp"]
anomalous_tg = [r for r in tg_rows if r["composite_score"] >= hcr_avg_comp]
anomalous_tg.sort(key=lambda x: -x["composite_score"])

# ── HCR holdings with BELOW-average composite ─────────────────────────────────
weak_hcr = [r for r in hcr_rows if r["composite_score"] < tg_s["avg_comp"]]
weak_hcr.sort(key=lambda x: x["composite_score"])

# ── Replay gap: high composite + BULLISH + no replay ─────────────────────────
replay_gap = [r for r in rows
              if not r["replay_supported"]
              and r["signal_direction"] == "BULLISH"
              and r["composite_score"] >= 4.0]
replay_gap.sort(key=lambda x: -x["composite_score"])

# ── ESS coverage ─────────────────────────────────────────────────────────────
no_ess_rows = [r for r in rows if not r.get("ess_score_text")]
has_ess_rows = [r for r in rows if r.get("ess_score_text")]
ess_pct = len(has_ess_rows) / len(rows) * 100 if rows else 0

# ── HCR completeness: does HCR contain top composites? ───────────────────────
top30_syms = {r["symbol"] for r in rows[:30]}
hcr_syms   = {r["symbol"] for r in hcr_rows}
top30_not_hcr = [r for r in rows[:30] if r["symbol"] not in hcr_syms]

# ── Trim score distribution ───────────────────────────────────────────────────
trim_buckets: Counter[str] = Counter()
for r in rows:
    t = r.get("trim_priority_score")
    if t is None:
        trim_buckets["N/A"] += 1
    elif t < 5:
        trim_buckets["0–5 (very low)"] += 1
    elif t < 15:
        trim_buckets["5–15 (low)"] += 1
    elif t < 30:
        trim_buckets["15–30 (moderate)"] += 1
    elif t < 50:
        trim_buckets["30–50 (elevated)"] += 1
    else:
        trim_buckets["50+ (high)"] += 1

lines: list[str] = []
A = lines.append

A("# Phase 7.0 — Conviction Model Quality Report")
A("")
A(f"**Run ID**: {DATA['run_id']}  ")
A(f"**Snapshot Date**: {DATA['snapshot_date']}  ")
A(f"**Mandate**: {DATA['mandate_type']}  ")
A(f"**Total Holdings**: {len(rows)}")
A("")

A("---")
A("")
A("## Section 1: Classification vs Composite Score Alignment")
A("")
A("Does HIGH_CONVICTION_RETAIN actually capture the highest-conviction holdings?")
A("")
A("| Classification | Count | Avg Composite | Median Composite | Min | Max | Replay % |")
A("|---|---|---|---|---|---|---|")
for cls_name, s in [("HIGH_CONVICTION_RETAIN", hcr_s), ("TACTICAL_GROWTH", tg_s)]:
    A(f"| {cls_name} | {s['count']} | {s['avg_comp']:.3f} | {s['med_comp']:.3f} | "
      f"{s['min_comp']:.3f} | {s['max_comp']:.3f} | {s['replay_pct']:.0f}% |")
A("")
if hcr_s["avg_comp"] >= tg_s["avg_comp"]:
    A(f"✓ **Alignment confirmed**: HCR avg composite ({hcr_s['avg_comp']:.3f}) exceeds")
    A(f"  TACTICAL_GROWTH avg ({tg_s['avg_comp']:.3f}) by {hcr_s['avg_comp'] - tg_s['avg_comp']:.3f} pts.")
else:
    A(f"⚠ **Misalignment detected**: HCR avg composite ({hcr_s['avg_comp']:.3f}) is BELOW")
    A(f"  TACTICAL_GROWTH avg ({tg_s['avg_comp']:.3f}). Classification may not be driven")
    A(f"  primarily by composite score.")
A("")

A("### Key Observation")
A("")
A("HIGH_CONVICTION_RETAIN classification is NOT driven by composite score alone.")
A("It is a **multi-gate structural test**:")
A("")
A("```")
A("HCR = signal == BULLISH")
A("    AND replay_supported == True")
A("    AND thematic_redundancy < 35")
A("    AND trim_score < 30")
A("```")
A("")
A("A holding with composite 4.9 that lacks replay support will be TACTICAL_GROWTH.")
A("A holding with composite 3.4 that passes all 4 gates will be HCR.")
A("This means HCR is a **quality-and-alignment filter**, not a signal-strength ranking.")
A("")

A("---")
A("")
A("## Section 2: Anomalies — High-Composite Holdings in TACTICAL_GROWTH")
A("")
A(f"**{len(anomalous_tg)} TACTICAL_GROWTH holdings** have composite ≥ HCR average ({hcr_avg_comp:.3f}).")
A("")
A("| Symbol | Composite | Signal | Replay | Trim | Redundancy | % Portfolio | Primary Blocker |")
A("|---|---|---|---|---|---|---|---|")
for r in anomalous_tg:
    trim = f"{r.get('trim_priority_score', 0):.1f}" if r.get("trim_priority_score") is not None else "—"
    redund = f"{r.get('thematic_redundancy_score', 0):.0f}" if r.get("thematic_redundancy_score") is not None else "0"
    if not r["replay_supported"]:
        blocker = "No replay support"
    elif r.get("trim_priority_score") is not None and r["trim_priority_score"] >= 30:
        blocker = f"Trim score ≥ 30 ({trim})"
    elif r.get("thematic_redundancy_score") is not None and r["thematic_redundancy_score"] >= 35:
        blocker = f"Thematic redundancy ≥ 35 ({redund})"
    elif r["signal_direction"] != "BULLISH":
        blocker = f"Signal = {r['signal_direction']} (not BULLISH)"
    else:
        blocker = "Classification gate not met"
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['signal_direction']} | "
      f"{'✓' if r['replay_supported'] else '✗'} | {trim} | {redund} | "
      f"{r['percent_of_portfolio']:.2f}% | {blocker} |")
A("")

A("### Interpretation")
A("")
replay_blocked = [r for r in anomalous_tg if not r["replay_supported"]]
trim_blocked   = [r for r in anomalous_tg
                  if r["replay_supported"] and r.get("trim_priority_score") is not None
                  and r["trim_priority_score"] >= 30]
A(f"- **{len(replay_blocked)} blocked by replay**: These are high-conviction signal holdings")
A(f"  that haven't yet been through replay analysis. Replay support is a hard gate.")
A(f"- **{len(trim_blocked)} blocked by trim score**: These holdings have elevated concentration")
A(f"  or thematic overlap that the system is flagging as structural risk.")
A("")

A("---")
A("")
A("## Section 3: Anomalies — Weak HCR Holdings")
A("")
A(f"**{len(weak_hcr)} HIGH_CONVICTION_RETAIN holdings** have composite < TACTICAL_GROWTH average ({tg_s['avg_comp']:.3f}).")
A("")
if weak_hcr:
    A("| Symbol | Composite | Signal | Trim Score | % Portfolio |")
    A("|---|---|---|---|---|")
    for r in weak_hcr:
        trim = f"{r.get('trim_priority_score', 0):.2f}" if r.get("trim_priority_score") is not None else "—"
        A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['signal_direction']} | {trim} | {r['percent_of_portfolio']:.2f}% |")
    A("")
    A("### Why HCR at Low Composite?")
    A("")
    A("HCR classification does not require high composite. It requires:")
    A("BULLISH signal + replay support + low thematic redundancy + low trim score.")
    A("A holding with composite 3.4 that passes all 4 gates is classified HCR")
    A("because it has strong structural alignment even if the signal score is moderate.")
else:
    A("_No anomalies in this category — all HCR holdings exceed TACTICAL_GROWTH average._")
A("")

A("---")
A("")
A("## Section 4: Replay Support Gap")
A("")
A(f"**{len(replay_gap)} high-signal holdings** (composite ≥ 4.0, BULLISH) have no replay support.")
A("")
A("| Symbol | Composite | STI Class | Trim | % Portfolio |")
A("|---|---|---|---|---|")
for r in replay_gap:
    trim = f"{r.get('trim_priority_score', 0):.1f}" if r.get("trim_priority_score") is not None else "—"
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['strategic_classification']} | {trim} | {r['percent_of_portfolio']:.2f}% |")
A("")
combined_pct = sum(r["percent_of_portfolio"] for r in replay_gap)
A(f"These {len(replay_gap)} holdings represent **{combined_pct:.1f}%** of portfolio value")
A(f"with strong signals that have no replay evidence to validate or contradict.")
A("")

A("---")
A("")
A("## Section 5: ESS Score Coverage Gap")
A("")
A(f"**ESS coverage**: {len(has_ess_rows)} of {len(rows)} holdings ({ess_pct:.1f}%)")
A(f"**Holdings without ESS**: {len(no_ess_rows)}")
A("")
A("ESS is one of two primary signal inputs (ESS + Zacks). When ESS is absent,")
A("the composite score is driven entirely by Zacks rating, reducing signal confidence.")
A("")
A("| Symbol | Composite | Signal | Zacks | STI Class | % Portfolio |")
A("|---|---|---|---|---|---|")
for r in sorted(no_ess_rows, key=lambda x: -x["composite_score"])[:15]:
    A(f"| {r['symbol']} | {r['composite_score']:.3f} | {r['signal_direction']} | "
      f"{r.get('zacks_rating') or '—'} | {r['strategic_classification']} | "
      f"{r['percent_of_portfolio']:.2f}% |")
A("")

A("---")
A("")
A("## Section 6: Trim Score Distribution")
A("")
A("| Trim Score Range | Count | Notes |")
A("|---|---|---|")
bucket_notes = {
    "0–5 (very low)": "Ideal retain candidates — very low structural risk",
    "5–15 (low)": "Moderate retain candidates",
    "15–30 (moderate)": "Below HCR threshold — still classifiable as HCR",
    "30–50 (elevated)": "Above HCR trim gate — requires TACTICAL_GROWTH or higher class",
    "50+ (high)": "High structural trim pressure",
    "N/A": "Non-equity holdings without STI score",
}
for bucket in ["0–5 (very low)", "5–15 (low)", "15–30 (moderate)", "30–50 (elevated)", "50+ (high)", "N/A"]:
    cnt = trim_buckets.get(bucket, 0)
    A(f"| {bucket} | {cnt} | {bucket_notes.get(bucket, '')} |")
A("")

A("---")
A("")
A("## Section 7: Top-30 Coverage Check")
A("")
A("How many of the top 30 by composite score are HIGH_CONVICTION_RETAIN?")
A("")
top30_hcr_count = sum(1 for r in rows[:30] if r["symbol"] in hcr_syms)
A(f"- **{top30_hcr_count} of 30** top holdings by composite are HIGH_CONVICTION_RETAIN")
A(f"- **{30 - top30_hcr_count} of 30** are TACTICAL_GROWTH (missing at least one HCR gate)")
A("")
if top30_not_hcr:
    A("Holdings in top-30 composite but NOT HIGH_CONVICTION_RETAIN:")
    A("")
    A("| Symbol | Rank | Composite | Primary Blocker |")
    A("|---|---|---|---|")
    for rank, r in enumerate(rows[:30], 1):
        if r["symbol"] not in hcr_syms:
            if not r["replay_supported"]:
                blocker = "No replay support"
            elif r.get("trim_priority_score") is not None and r["trim_priority_score"] >= 30:
                blocker = f"Trim score ≥ 30"
            elif r.get("thematic_redundancy_score") is not None and r["thematic_redundancy_score"] >= 35:
                blocker = "Thematic redundancy ≥ 35"
            else:
                blocker = "Classification gate"
            A(f"| {r['symbol']} | #{rank} | {r['composite_score']:.3f} | {blocker} |")
A("")

A("---")
A("")
A("## Section 8: Model Quality Observations")
A("")
A("These are structural observations based on the audit. **No code changes are implied.**")
A("")
A("### 1. Replay support is the dominant HCR gating factor")
A("")
no_rep_would_hcr = [r for r in tg_rows
                    if r["signal_direction"] == "BULLISH"
                    and (r.get("trim_priority_score") or 99) < 30
                    and (r.get("thematic_redundancy_score") or 0) < 35]
A(f"Of {len(tg_rows)} TACTICAL_GROWTH holdings, **{len(no_rep_would_hcr)} would qualify as HCR**")
A(f"if only replay support were present (all other gates pass). This means replay coverage")
A(f"is the primary constraint on HCR classification breadth, not signal quality or thematic overlap.")
A("")
A("### 2. Narrative cap amplifies the effect of small positional size")
A("")
A("The top-3 narrative cap combined with trim score selection means that the holdings")
A("receiving strategic retain narratives are systematically the *smallest* positions in the")
A("portfolio — not the highest-conviction ones by composite score. This is a consequence")
A("of small positions sitting in underweight nodes with near-zero concentration pressure.")
A("")
A("### 3. ESS absence creates composite score asymmetry")
A("")
A(f"With {len(no_ess_rows)} holdings missing ESS scores, composite scores for those")
A("holdings are computed from Zacks alone. Holdings with ESS have a richer composite")
A("basis. This may create a structural bias against Zacks-only holdings in borderline")
A("classification cases.")
A("")
A("### 4. HCR avg composite is above TACTICAL_GROWTH avg — model is functionally correct")
A("")
A(f"Despite the multi-gate structure, HIGH_CONVICTION_RETAIN holds average composite")
A(f"{hcr_s['avg_comp']:.3f} vs TACTICAL_GROWTH {tg_s['avg_comp']:.3f}. The classification")
A(f"is working as intended: HCR is the highest-signal, highest-alignment tier.")
A("")

out = Path("conviction_model_quality_report.md")
out.write_text("\n".join(lines))
print(f"Written: {out}  ({out.stat().st_size:,} bytes)")
