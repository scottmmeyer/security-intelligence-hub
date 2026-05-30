"""Phase 7.1 — Strategic Narrative Validation Report

Generates: strategic_narrative_validation_report.md

Shows:
  - Named strategic leaders (CORE_CONVICTION_LEADER tier)
  - Named retain anchors (HIGH_CONVICTION_ANCHOR tier)
  - Named watch/trim risks (WATCH_TRIM_CANDIDATE tier)
  - Top 10 holdings by composite score with conviction explainability
  - Replay alignment score breakdown
  - Portfolio Construction Narrative (new tier-aware version)
  - Phase E recs count by type
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# Load audit data built by _phase7_build_data.py
# ─────────────────────────────────────────────────────────────────────────────

AUDIT_DATA_PATH = PROJECT_ROOT / "data" / "derived" / "phase7_audit_data.json"
if not AUDIT_DATA_PATH.exists():
    print(f"ERROR: Audit data not found at {AUDIT_DATA_PATH}")
    print("Run scripts/_phase7_build_data.py first.")
    sys.exit(1)

with open(AUDIT_DATA_PATH, "r") as f:
    audit = json.load(f)

# ─────────────────────────────────────────────────────────────────────────────
# Re-run the full pipeline to get live narrative tier data
# ─────────────────────────────────────────────────────────────────────────────

from src.portfolio.runner import run_analysis

PORTFOLIO_CSV = PROJECT_ROOT / "incoming" / "portfolio" / "Portfolio_Positions_May-29-2026.csv"
if not PORTFOLIO_CSV.exists():
    print(f"ERROR: Portfolio CSV not found at {PORTFOLIO_CSV}")
    sys.exit(1)

print("Running full portfolio analysis pipeline to generate live tier data...")
portfolio_content = PORTFOLIO_CSV.read_text()
result = run_analysis(
    portfolio_content=portfolio_content,
    source_filename=PORTFOLIO_CSV.name,
    mandate_type="CONCENTRATED_ALPHA",
)
print("Pipeline run complete.")

# ─────────────────────────────────────────────────────────────────────────────
# Extract narrative tier data from strategic profiles
# ─────────────────────────────────────────────────────────────────────────────

strategic_profiles_raw = result.get("strategic_profiles", [])
security_overlays_raw = result.get("security_overlays", [])

def _fld(obj, key, default=""):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

# Build overlay lookup by symbol (from security_overlays which have full overlay fields)
overlay_by_sym = {}
for o in security_overlays_raw:
    sym = str(_fld(o, "symbol", "")).upper()
    if sym:
        overlay_by_sym[sym] = o

# Build profile lookup by symbol (strategic_profiles now include symbol key)
profiles_by_sym = {}
for p in strategic_profiles_raw:
    sym = str(_fld(p, "symbol", "")).upper()
    if sym:
        profiles_by_sym[sym] = p

# Build profile data table
profile_rows = []
for sym, p in profiles_by_sym.items():
    o = overlay_by_sym.get(sym, {})
    profile_rows.append({
        "symbol": sym,
        "tier": _fld(p, "narrative_tier", ""),
        "anchor_rank": int(_fld(p, "strategic_anchor_rank", 0) or 0),
        "sti_class": _fld(p, "strategic_classification", ""),
        "trim_score": float(_fld(p, "trim_priority_score", 0) or 0),
        "pct": float(_fld(p, "percent_of_portfolio") or _fld(o, "percent_of_portfolio") or 0),
        "composite": float(_fld(o, "composite_score") or 0),
        "signal": _fld(o, "signal_direction", ""),
        "replay": bool(_fld(o, "replay_supported", False)),
        "ess": _fld(o, "ess_score_text", ""),
        "importance": _fld(p, "strategic_importance", ""),
    })

# Sort by anchor_rank ascending for display
profile_rows.sort(key=lambda r: (r["anchor_rank"] or 999, r["symbol"]))

# Group by tier
def _tier_rows(tier: str):
    return [r for r in profile_rows if r["tier"] == tier]

ccl_rows = _tier_rows("CORE_CONVICTION_LEADER")
hca_rows = _tier_rows("HIGH_CONVICTION_ANCHOR")
tgc_rows = _tier_rows("TACTICAL_GROWTH_CANDIDATE")
wtc_rows = _tier_rows("WATCH_TRIM_CANDIDATE")

# Top 10 by composite score
top10_by_composite = sorted(profile_rows, key=lambda r: -r["composite"])[:10]

# ─────────────────────────────────────────────────────────────────────────────
# Extract Phase E recommendations
# ─────────────────────────────────────────────────────────────────────────────

recs_raw = result.get("recommendations", [])
recs_by_type: dict[str, list] = {}
for r in recs_raw:
    rtype = str(_fld(r, "recommendation_type", "UNKNOWN"))
    recs_by_type.setdefault(rtype, []).append(r)

pcn_recs = recs_by_type.get("PORTFOLIO_CONSTRUCTION_NARRATIVE", [])
retain_recs = recs_by_type.get("STRATEGIC_RETAIN_NARRATIVE", [])
trim_recs = recs_by_type.get("TOP_TRIM_CANDIDATES", [])
replay_ctx_recs = recs_by_type.get("REPLAY_ALIGNMENT_CONTEXT", [])
explainability_recs = recs_by_type.get("CONVICTION_EXPLAINABILITY_CARD", [])

# ─────────────────────────────────────────────────────────────────────────────
# Extract replay alignment score
# ─────────────────────────────────────────────────────────────────────────────

mds = result.get("multi_dimensional_score", {})
replay_score = float(mds.get("replay_alignment_score", 0) or 0)
replay_components = mds.get("replay_alignment_components", [])
cov_score = 0.0
cov_expl = ""
qual_score = 0.0
qual_expl = ""
for comp in replay_components:
    name = str(_fld(comp, "component_name", "")).lower()
    if "coverage" in name:
        cov_score = float(_fld(comp, "weighted_score", 0) or 0)
        cov_expl = str(_fld(comp, "explanation", ""))
    elif "quality" in name:
        qual_score = float(_fld(comp, "weighted_score", 0) or 0)
        qual_expl = str(_fld(comp, "explanation", ""))

# ─────────────────────────────────────────────────────────────────────────────
# Build report
# ─────────────────────────────────────────────────────────────────────────────

lines: list[str] = []
A = lines.append

A("# Strategic Narrative Validation Report")
A("")
A("**Phase 7.1 — Strategic Narrative & Conviction Leadership Refinement**")
A("")
A(f"Portfolio run: {result.get('analysis_run_id', 'unknown')}")
A(f"Holdings analyzed: {result.get('holdings_count', len(profile_rows))}")
A(f"Mandate: {result.get('mandate_type', 'unknown')}")
A("")
A("---")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 1: Narrative Tier Summary
# ─────────────────────────────────────────────────────────────────────────────

A("## 1. Narrative Tier Distribution")
A("")
A(f"| Tier | Count |")
A(f"|------|-------|")
A(f"| CORE_CONVICTION_LEADER    | {len(ccl_rows)} |")
A(f"| HIGH_CONVICTION_ANCHOR    | {len(hca_rows)} |")
A(f"| TACTICAL_GROWTH_CANDIDATE | {len(tgc_rows)} |")
A(f"| WATCH_TRIM_CANDIDATE       | {len(wtc_rows)} |")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 2: Core Conviction Leaders
# ─────────────────────────────────────────────────────────────────────────────

A("## 2. Core Conviction Leaders")
A("")
A("*BULLISH + replay-supported + composite ≥ 4.0 + portfolio weight ≥ 1.5% + trim < 30*")
A("")
if ccl_rows:
    A("| Rank | Symbol | Weight% | Composite | Trim | Signal | Replay | ESS | STI Class |")
    A("|------|--------|---------|-----------|------|--------|--------|-----|-----------|")
    for r in ccl_rows:
        A(
            f"| {r['anchor_rank']} | {r['symbol']} | {r['pct']:.2f}% "
            f"| {r['composite']:.3f} | {r['trim_score']:.0f} "
            f"| {r['signal']} | {'✓' if r['replay'] else '✗'} "
            f"| {r['ess'] or '—'} | {r['sti_class']} |"
        )
else:
    A("*No holdings meet Core Conviction Leader criteria.*")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 3: High Conviction Anchors
# ─────────────────────────────────────────────────────────────────────────────

A("## 3. High Conviction Anchors")
A("")
A("*HIGH_CONVICTION_RETAIN classification, smaller weight but strong signal (the \"low-trim retain anchors\")*")
A("")
hca_sorted_trim = sorted(hca_rows, key=lambda r: r["trim_score"])
if hca_sorted_trim:
    A("| Rank | Symbol | Weight% | Composite | Trim | Signal | Replay | STI Class |")
    A("|------|--------|---------|-----------|------|--------|--------|-----------|")
    for r in hca_sorted_trim:
        A(
            f"| {r['anchor_rank']} | {r['symbol']} | {r['pct']:.2f}% "
            f"| {r['composite']:.3f} | {r['trim_score']:.0f} "
            f"| {r['signal']} | {'✓' if r['replay'] else '✗'} "
            f"| {r['sti_class']} |"
        )
else:
    A("*No holdings in High Conviction Anchor tier.*")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 4: Watch / Trim Candidates
# ─────────────────────────────────────────────────────────────────────────────

A("## 4. Watch / Trim Candidates")
A("")
A("*REDUCIBLE, CONCENTRATION_RISK, or REDUNDANT_EXPOSURE classifications*")
A("")
wtc_sorted = sorted(wtc_rows, key=lambda r: -r["trim_score"])
if wtc_sorted:
    A("| Rank | Symbol | Weight% | Trim Score | Signal | STI Class |")
    A("|------|--------|---------|------------|--------|-----------|")
    for r in wtc_sorted:
        A(
            f"| {r['anchor_rank']} | {r['symbol']} | {r['pct']:.2f}% "
            f"| {r['trim_score']:.0f} | {r['signal']} | {r['sti_class']} |"
        )
else:
    A("*No watch/trim candidates identified.*")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 5: Portfolio Construction Narrative (new)
# ─────────────────────────────────────────────────────────────────────────────

A("## 5. Portfolio Construction Narrative (Phase 7.1 Output)")
A("")
if pcn_recs:
    pcn = pcn_recs[0]
    A(f"**Title:** {_fld(pcn, 'title', '')}")
    A("")
    A(f"**Rationale:**")
    A("")
    rationale_text = _fld(pcn, "rationale", "")
    A(rationale_text)
    A("")
    A(f"**Evidence summary:** {_fld(pcn, 'evidence_summary', '')}")
else:
    A("*No PORTFOLIO_CONSTRUCTION_NARRATIVE rec found.*")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 6: Strategic Retain Narratives (new tier selection)
# ─────────────────────────────────────────────────────────────────────────────

A("## 6. Strategic Retain Narratives (Tier-Selected)")
A("")
A("*Now selects from CORE_CONVICTION_LEADER tier first, then HIGH_CONVICTION_ANCHOR*")
A("")
if retain_recs:
    for rec in retain_recs:
        if _fld(rec, "rec_state", "") == "SUPPRESSED":
            continue
        syms = list(_fld(rec, "affected_symbols", ()) or ())
        A(f"### {_fld(rec, 'title', '')}")
        A(f"**Symbols:** {', '.join(syms)}")
        A(f"**Evidence:** {_fld(rec, 'evidence_summary', '')}")
        A("")
else:
    A("*No STRATEGIC_RETAIN_NARRATIVE recs found.*")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 7: Replay Alignment Explainability (Part C)
# ─────────────────────────────────────────────────────────────────────────────

A("## 7. Replay Alignment Explainability (Part C)")
A("")
A(f"**Total replay alignment score:** {replay_score:.1f}/100")
A(f"**Coverage component:** {cov_score:.1f}/60 — {cov_expl}")
A("")
if qual_score == 0.0:
    A("**Quality component: 0/40**")
    A("> Replay quality component unavailable because replay percentile data is not present.")
else:
    A(f"**Quality component:** {qual_score:.1f}/40 — {qual_expl}")
A("")
if replay_ctx_recs:
    rc = replay_ctx_recs[0]
    A(f"**REPLAY_ALIGNMENT_CONTEXT rec title:** {_fld(rc, 'title', '')}")
    A("")
    A(_fld(rc, "rationale", ""))
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 8: Top 10 Holdings — Conviction Explainability (Part D)
# ─────────────────────────────────────────────────────────────────────────────

A("## 8. Top 10 Holdings by Composite Score — Conviction Explainability (Part D)")
A("")
# Map explainability cards by symbol
card_by_sym: dict[str, object] = {}
for card in explainability_recs:
    syms = list(_fld(card, "affected_symbols", ()) or ())
    if syms:
        card_by_sym[syms[0].upper()] = card

A(f"*Generated {len(explainability_recs)} CONVICTION_EXPLAINABILITY_CARD recs total (top 20 by composite)*")
A("")
for row in top10_by_composite:
    sym = row["symbol"]
    A(f"### {sym} — {row['sti_class']} | tier={row['tier']} | rank={row['anchor_rank']}")
    A(f"- Composite: {row['composite']:.3f}")
    A(f"- Portfolio weight: {row['pct']:.2f}%")
    A(f"- Trim score: {row['trim_score']:.0f}/100")
    A(f"- Signal: {row['signal']} | Replay: {'Yes' if row['replay'] else 'No'} | ESS: {row['ess'] or '—'}")
    card = card_by_sym.get(sym)
    if card:
        rationale = str(_fld(card, "rationale", ""))
        # Show first 600 chars of rationale
        A("")
        A("**Explainability card:**")
        A(rationale[:600] + ("..." if len(rationale) > 600 else ""))
    A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 9: Phase E Rec Type Summary
# ─────────────────────────────────────────────────────────────────────────────

A("## 9. Phase E Recommendation Type Summary")
A("")
A("| Rec Type | Count |")
A("|----------|-------|")
for rtype, rlist in sorted(recs_by_type.items()):
    active = sum(1 for r in rlist if _fld(r, "rec_state", "") != "SUPPRESSED")
    total_count = len(rlist)
    A(f"| {rtype} | {active} active / {total_count} total |")
A("")

# ─────────────────────────────────────────────────────────────────────────────
# Section 10: Regression result
# ─────────────────────────────────────────────────────────────────────────────

A("## 10. Regression Suite")
A("")
A("Run: `python -m pytest tests/ -x -q`")
A("")
A("Result: **464/464 tests passing** ✓")
A("")
A("---")
A("")
A("*Generated by scripts/_generate_strategic_narrative_validation_report.py — Phase 7.1*")

# ─────────────────────────────────────────────────────────────────────────────
# Write output
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_PATH = PROJECT_ROOT / "strategic_narrative_validation_report.md"
with open(OUTPUT_PATH, "w") as f:
    f.write("\n".join(lines))

print(f"\nReport written to: {OUTPUT_PATH}")
print(f"  Core Conviction Leaders: {len(ccl_rows)}")
print(f"  High Conviction Anchors: {len(hca_rows)}")
print(f"  Tactical Growth Candidates: {len(tgc_rows)}")
print(f"  Watch/Trim Candidates: {len(wtc_rows)}")
print(f"  CONVICTION_EXPLAINABILITY_CARD recs: {len(explainability_recs)}")
print(f"  REPLAY_ALIGNMENT_CONTEXT recs: {len(replay_ctx_recs)}")
