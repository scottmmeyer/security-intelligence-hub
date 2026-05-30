"""
Phase 7.2 — Recommendation Conflicts & Security-Level Optimization
Audit-only script. Does not modify recommendation logic.

Generates:
  recommendation_conflict_report.md
  security_vs_etf_report.md
  cash_deployment_report.md
  overlap_analysis_report.md
  conviction_deployment_report.md
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.portfolio.runner import run_analysis

# ─── Run pipeline ────────────────────────────────────────────────────────────
CSV_PATH = Path("incoming/portfolio/Portfolio_Positions_May-29-2026.csv")
csv_text = CSV_PATH.read_text()

print("Running pipeline…")
result = run_analysis(
    csv_text,
    CSV_PATH.name,
    snapshot_date="2026-05-29",
    mandate_type="CONCENTRATED_ALPHA",
)
print(f"  {len(result.get('recommendations', []))} recs, "
      f"{len(result.get('security_overlays', []))} overlays, "
      f"{len(result.get('alignment', []))} alignment rows")

recs       = result.get("recommendations", [])
overlays   = result.get("security_overlays", [])
alignment  = result.get("alignment", [])
profiles   = result.get("strategic_profiles", [])
total_mv   = float(result.get("total_market_value") or 0)

# ─── Load holdings CSV for node classification ───────────────────────────────
par_dirs = sorted(Path("data/portfolio_ingestion/analysis_runs").glob("PAR-20260529*"))
if not par_dirs:
    par_dirs = sorted(Path("data/portfolio_ingestion/analysis_runs").glob("PAR-*"))
holdings_csv_path = par_dirs[-1] / "holdings.csv" if par_dirs else None

holdings_by_sym: dict[str, dict] = {}
if holdings_csv_path and holdings_csv_path.exists():
    for row in csv.DictReader(open(holdings_csv_path)):
        sym = str(row.get("symbol", "") or "").upper()
        if sym:
            holdings_by_sym[sym] = row

# ─── Build lookup maps ───────────────────────────────────────────────────────
overlay_by_sym: dict[str, dict] = {
    str(o.get("symbol", "") or "").upper(): o for o in overlays
}
profile_by_sym: dict[str, dict] = {
    str(p.get("symbol", "") or "").upper(): p for p in profiles
    if str(p.get("symbol", "") or "").upper()
}

alignment_by_node: dict[str, dict] = {
    str(a.get("node_key", "") or ""): a for a in alignment
}

# Action recommendations only
action_recs = [
    r for r in recs
    if r.get("recommendation_type") in (
        "INCREASE_UNDERWEIGHT", "REDUCE_OVERWEIGHT", "REPLAY_SUPPORTED_OPPORTUNITY"
    )
]

# ─── ETF node coverage model ─────────────────────────────────────────────────
# Based on known ETF compositions (heuristic, consistent with vehicle_suitability_notes)
# node_key → {vehicle: coverage_pct}
ETF_NODE_COVERAGE: dict[str, dict[str, float]] = {
    # VOO (S&P 500): ~15% US Large, ~85% US Mega
    #   Of Mega: ~29% Extended (~24.7% total), ~35% Hyper (~29.8% total), ~36% Ultra (~30.6% total)
    "VOO": {
        "EQUITIES.US":                      100.0,
        "EQUITIES.US.LARGE":                15.0,
        "EQUITIES.US.MEGA":                 85.0,
        "EQUITIES.US.MEGA.EXTENDED_MEGA":   25.0,   # 85% * 29.4%
        "EQUITIES.US.MEGA.HYPER_MEGA":      30.0,   # 85% * 35.3%
        "EQUITIES.US.MEGA.ULTRA_MEGA":      30.0,   # 85% * 35.3%
    },
    # IVV (S&P 500): same as VOO
    "IVV": {
        "EQUITIES.US":                      100.0,
        "EQUITIES.US.LARGE":                15.0,
        "EQUITIES.US.MEGA":                 85.0,
        "EQUITIES.US.MEGA.EXTENDED_MEGA":   25.0,
        "EQUITIES.US.MEGA.HYPER_MEGA":      30.0,
        "EQUITIES.US.MEGA.ULTRA_MEGA":      30.0,
    },
    # SPY (S&P 500): same as VOO/IVV
    "SPY": {
        "EQUITIES.US":                      100.0,
        "EQUITIES.US.LARGE":                15.0,
        "EQUITIES.US.MEGA":                 85.0,
        "EQUITIES.US.MEGA.EXTENDED_MEGA":   25.0,
        "EQUITIES.US.MEGA.HYPER_MEGA":      30.0,
        "EQUITIES.US.MEGA.ULTRA_MEGA":      30.0,
    },
    # VTI (Total Market): 55% Mega, 28% Large, 14% Mid, 2% Small, 1% Micro
    #   Of Mega: ~45% Extended (~24.8% total), ~30% Hyper (~16.5%), ~25% Ultra (~13.8%)
    "VTI": {
        "EQUITIES.US":                      100.0,
        "EQUITIES.US.MEGA":                 55.0,
        "EQUITIES.US.LARGE":                28.0,
        "EQUITIES.US.MID":                  14.0,
        "EQUITIES.US.SMALL":                 2.0,
        "EQUITIES.US.MICRO":                 1.0,
        "EQUITIES.US.MEGA.EXTENDED_MEGA":   25.0,   # 55% * 45.5%
        "EQUITIES.US.MEGA.HYPER_MEGA":      16.5,   # 55% * 30.0%
        "EQUITIES.US.MEGA.ULTRA_MEGA":      13.5,   # 55% * 24.5%
    },
    # SCHB (Schwab US Broad): similar to VTI
    "SCHB": {
        "EQUITIES.US":                      100.0,
        "EQUITIES.US.MEGA":                 55.0,
        "EQUITIES.US.LARGE":                28.0,
        "EQUITIES.US.MID":                  14.0,
        "EQUITIES.US.SMALL":                 2.0,
        "EQUITIES.US.MICRO":                 1.0,
        "EQUITIES.US.MEGA.EXTENDED_MEGA":   25.0,
        "EQUITIES.US.MEGA.HYPER_MEGA":      16.5,
        "EQUITIES.US.MEGA.ULTRA_MEGA":      13.5,
    },
    # FXAIX (Fidelity S&P 500): same as VOO/SPY
    "FXAIX": {
        "EQUITIES.US":                      100.0,
        "EQUITIES.US.LARGE":                15.0,
        "EQUITIES.US.MEGA":                 85.0,
        "EQUITIES.US.MEGA.EXTENDED_MEGA":   25.0,
        "EQUITIES.US.MEGA.HYPER_MEGA":      30.0,
        "EQUITIES.US.MEGA.ULTRA_MEGA":      30.0,
    },
}

# Overweight nodes (actual > target, MODERATE+ severity)
OVERWEIGHT_NODES = {
    a["node_key"]: a for a in alignment
    if a.get("drift_direction") == "OVERWEIGHT"
    and a.get("severity") in ("MODERATE", "HIGH")
}

# Underweight nodes (actual < target, MODERATE+ severity)
UNDERWEIGHT_NODES = {
    a["node_key"]: a for a in alignment
    if a.get("drift_direction") == "UNDERWEIGHT"
    and a.get("severity") in ("MODERATE", "HIGH")
}


def _node_impact(vehicle: str, amount_deployed_pct: float = 1.0) -> dict[str, float]:
    """Return {node_key: delta_pct} for deploying `amount_deployed_pct`% into vehicle."""
    coverage = ETF_NODE_COVERAGE.get(vehicle, {})
    return {node: amount_deployed_pct * (cov / 100.0) for node, cov in coverage.items()}


def _classify_impact(node_key: str, delta: float) -> str:
    """HELPS / HURTS / NEUTRAL for a given node and delta."""
    al = alignment_by_node.get(node_key)
    if not al:
        return "NEUTRAL"
    direction = al.get("drift_direction", "")
    if direction == "UNDERWEIGHT" and delta > 0:
        return "HELPS"
    if direction == "OVERWEIGHT" and delta > 0:
        return "HURTS"
    if direction == "OVERWEIGHT" and delta < 0:
        return "HELPS"
    return "NEUTRAL"


def _get_pct(sym: str, field: str, default: float = 0.0) -> float:
    o = overlay_by_sym.get(sym, {})
    return float(o.get(field) or default)


def _holding_node(sym: str) -> str:
    """Return the primary allocation node for a holding symbol."""
    h = holdings_by_sym.get(sym, {})
    ac = str(h.get("asset_class", "") or "").upper()
    geo = str(h.get("geography", "") or "").upper()
    mc = str(h.get("market_cap_bucket", "") or "").upper()
    ms = str(h.get("mega_subtier", "") or "").upper()

    if ac == "CASH":
        return "CASH"
    if ac != "EQUITIES":
        return ac

    parts = ["EQUITIES"]
    if geo == "US":
        parts.append("US")
    elif geo == "INTERNATIONAL":
        parts.append("INTERNATIONAL")
    else:
        return "EQUITIES"

    if mc in ("MEGA", "LARGE", "MID", "SMALL", "MICRO"):
        parts.append(mc)
        if mc == "MEGA" and ms:
            clean_ms = ms.replace("MEGA_", "").replace("_MEGA", "")
            if clean_ms in ("HYPER", "EXTENDED", "ULTRA"):
                parts.append(f"{clean_ms}_MEGA")
    return ".".join(parts)


def _format_pct(v: float) -> str:
    return f"{v:+.2f}%" if v != 0 else "0.00%"


# ─── Section 1 — Conflict Analysis ───────────────────────────────────────────

def build_conflict_matrix() -> list[dict]:
    """For each action rec / vehicle, compute node impact."""
    rows = []
    for rec in action_recs:
        node = rec.get("affected_node_key", "")
        title = rec.get("title", "")
        rt = rec.get("recommendation_type", "")
        drift = float(rec.get("drift_pct") or 0)
        sev = rec.get("severity", "")
        vehicles = rec.get("affected_symbols", [])
        vsn = {v.get("symbol", ""): v for v in (rec.get("vehicle_suitability_notes") or [])}

        rows.append({
            "node": node, "title": title, "type": rt, "drift": drift,
            "severity": sev, "vehicles": vehicles, "vsn": vsn,
        })
    return rows


def conflict_report_text(matrix: list[dict]) -> str:
    lines: list[str] = []
    lines += [
        "# Recommendation Conflict Report",
        "",
        f"**Phase 7.2 — Recommendation Conflicts & Security-Level Optimization**",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        f"**Portfolio:** Portfolio_Positions_May-29-2026.csv",
        f"**Total Market Value:** ${total_mv:,.2f}",
        f"**Mandate:** CONCENTRATED_ALPHA",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "The current recommendation engine identifies valid allocation drift but proposes",
        "ETF vehicles that create structural conflicts: the same instruments recommended to",
        "repair one underweight simultaneously worsen existing overweights.",
        "",
        "**Primary conflict:** VOO, IVV, SPY — recommended for US Large repair — each",
        "carry ~30% Hyper/Ultra Mega exposure, worsening the existing HYPER_MEGA overweight.",
        "VTI and SCHB — recommended for Extended Mega repair — also add Hyper/Ultra Mega.",
        "No vehicle recommended for any 'Build' rec has HIGH suitability.",
        "",
        "---",
        "",
        "## Section 1 — Allocation Node State",
        "",
        "### Overweight Nodes (MODERATE+ severity)",
        "",
        "| Node | Actual | Target | Drift | Severity |",
        "|------|--------|--------|-------|----------|",
    ]
    for node_key, a in sorted(OVERWEIGHT_NODES.items(), key=lambda x: -abs(x[1]["drift_pct"])):
        actual = float(a.get("actual_pct") or 0)
        target = float(a.get("target_pct") or 0)
        drift = float(a.get("drift_pct") or 0)
        sev = a.get("severity", "")
        lines.append(f"| {node_key} | {actual:.2f}% | {target:.2f}% | +{drift:.2f}% | {sev} |")

    lines += [
        "",
        "### Underweight Nodes (MODERATE+ severity)",
        "",
        "| Node | Actual | Target | Gap | Severity |",
        "|------|--------|--------|-----|----------|",
    ]
    for node_key, a in sorted(UNDERWEIGHT_NODES.items(), key=lambda x: x[1]["drift_pct"]):
        actual = float(a.get("actual_pct") or 0)
        target = float(a.get("target_pct") or 0)
        drift = float(a.get("drift_pct") or 0)
        sev = a.get("severity", "")
        lines.append(f"| {node_key} | {actual:.2f}% | {target:.2f}% | {drift:.2f}% | {sev} |")

    lines += [
        "",
        "---",
        "",
        "## Section 2 — Per-Recommendation Vehicle Impact",
        "",
    ]

    # Build recs (INCREASE_UNDERWEIGHT)
    build_recs = [r for r in matrix if r["type"] == "INCREASE_UNDERWEIGHT"]
    reduce_recs = [r for r in matrix if r["type"] == "REDUCE_OVERWEIGHT"]
    replay_recs = [r for r in matrix if r["type"] == "REPLAY_SUPPORTED_OPPORTUNITY"]

    lines += ["### 2A — Build Recommendations (INCREASE_UNDERWEIGHT)", ""]

    for rec in build_recs:
        node = rec["node"]
        title = rec["title"]
        drift = rec["drift"]
        sev = rec["severity"]

        lines += [
            f"#### {node}  (drift={drift:.2f}%, severity={sev})",
            "",
            f"**Rec:** {title}",
            "",
            "**Vehicle Analysis:**",
            "",
            "| Vehicle | Target Node Coverage | Off-Target Exposure | Worsens Overweight | Suitability | Overlap w/Existing |",
            "|---------|---------------------|--------------------|--------------------|-------------|-------------------|",
        ]
        for vsym in rec["vehicles"]:
            v = rec["vsn"].get(vsym, {})
            t_cov = float(v.get("target_node_coverage_pct") or 0)
            off = float(v.get("off_target_exposure_pct") or 0)
            worsens = v.get("worsens_existing_overweight", False)
            tier = v.get("suitability_tier", "N/A")
            score = float(v.get("suitability_score") or 0)
            overlap = float(v.get("overlap_with_existing_pct") or 0)
            warn = " ⚠" if worsens else ""
            lines.append(
                f"| {vsym} | {t_cov:.1f}% | {off:.1f}% | {'YES ⚠' if worsens else 'No'} | {tier} ({score:.0f}/100) | {overlap:.1f}% |"
            )

        lines += [""]

        # Node impact table for each vehicle
        lines += [
            "**Node Impact (per 1% deployment):**",
            "",
            "| Vehicle | Helps Nodes | Hurts Nodes | Net Effect |",
            "|---------|-------------|-------------|------------|",
        ]
        for vsym in rec["vehicles"]:
            impacts = _node_impact(vsym, 1.0)
            helps = [k for k, v in impacts.items() if _classify_impact(k, v) == "HELPS"]
            hurts = [k for k, v in impacts.items() if _classify_impact(k, v) == "HURTS"]
            net = len(helps) - len(hurts)
            net_str = f"+{net}" if net > 0 else str(net)
            helps_str = ", ".join([k.split(".")[-1] for k in helps]) if helps else "—"
            hurts_str = ", ".join([k.split(".")[-1] for k in hurts]) if hurts else "—"
            lines.append(f"| {vsym} | {helps_str} | {hurts_str} | {net_str} |")

        lines += [""]

    lines += ["", "### 2B — Reduce Recommendations (REDUCE_OVERWEIGHT)", ""]

    for rec in reduce_recs:
        node = rec["node"]
        drift = rec["drift"]
        sev = rec["severity"]
        symbols = rec["vehicles"]
        lines += [
            f"#### {node}  (drift=+{drift:.2f}%, severity={sev})",
            "",
            f"**Affected symbols (contributors to overweight):** {', '.join(symbols)}",
            "",
        ]

    if replay_recs:
        lines += ["### 2C — Replay-Supported Opportunities", ""]
        for rec in replay_recs:
            lines += [f"- **{rec['title']}** (drift={rec['drift']:.2f}%, sev={rec['severity']})", ""]

    lines += [
        "---",
        "",
        "## Section 3 — Structural Conflict Matrix",
        "",
        "This table shows which vehicles appear in BOTH a Build recommendation AND worsen",
        "an existing REDUCE recommendation node.",
        "",
        "| Vehicle | Appears In (Build) | Worsens (Reduce) | Conflict? |",
        "|---------|-------------------|-----------------|-----------|",
    ]

    # Collect which vehicles appear in build recs and what overweight nodes they worsen
    veh_in_build: dict[str, list[str]] = {}
    for rec in build_recs:
        for vsym in rec["vehicles"]:
            veh_in_build.setdefault(vsym, []).append(rec["node"])

    for vsym, build_nodes in sorted(veh_in_build.items()):
        impacts = _node_impact(vsym, 1.0)
        hurt_ow_nodes = [
            k for k, v in impacts.items()
            if _classify_impact(k, v) == "HURTS" and k in OVERWEIGHT_NODES
        ]
        conflict = "🔴 YES" if hurt_ow_nodes else "✅ No"
        build_str = ", ".join([n.split(".")[-1] for n in build_nodes])
        hurt_str = ", ".join([n.split(".")[-1] for n in hurt_ow_nodes]) if hurt_ow_nodes else "—"
        lines.append(f"| {vsym} | {build_str} | {hurt_str} | {conflict} |")

    lines += [
        "",
        "### Key Finding",
        "",
        "> **VOO, IVV, SPY**: Recommended to build US Large (-7.3% gap), but each carries",
        "> ~30% Hyper/Ultra Mega content. Buying 1% of portfolio in VOO adds ~0.30% to",
        "> Hyper Mega (already +3.7% overweight) and ~0.30% to Ultra Mega.",
        ">",
        "> **VTI, SCHB**: Recommended for Extended Mega (-4.1% gap), but adds ~16.5% to",
        "> Hyper Mega and ~13.5% to Ultra Mega. Both already overweight.",
        ">",
        "> **VOO also conflicts with itself**: It is listed in both the US Large build rec",
        "> AND the Extended Mega build rec — yet its suitability for Extended Mega is LOW",
        "> (score=17.4/100) vs VTI's MEDIUM (33.5/100).",
        ">",
        "> **Under Concentrated Alpha mandate**: Both underweight nodes are flagged as",
        "> INTENTIONAL_UNDERWEIGHT — meaning no corrective action is actually required.",
        "> This further undermines the case for ETF deployment.",
        "",
        "---",
        "",
        "## Section 4 — Suitability Summary",
        "",
        "All vehicles currently recommended for Build positions are LOW or MEDIUM suitability.",
        "No HIGH-suitability ETF vehicle exists for either underweight node given current",
        "portfolio composition.",
        "",
        "| Vehicle | Best Suitability Score | Best Tier | Conflicts With |",
        "|---------|----------------------|-----------|----------------|",
    ]

    veh_best_score: dict[str, tuple[float, str, list[str]]] = {}
    for rec in build_recs:
        for v in (rec.get("vsn") or {}).values():
            vsym = v.get("symbol", "")
            score = float(v.get("suitability_score") or 0)
            tier = v.get("suitability_tier", "")
            if vsym not in veh_best_score or score > veh_best_score[vsym][0]:
                impacts = _node_impact(vsym, 1.0)
                hurts = [
                    k.split(".")[-1] for k, delta in impacts.items()
                    if _classify_impact(k, delta) == "HURTS" and k in OVERWEIGHT_NODES
                ]
                veh_best_score[vsym] = (score, tier, hurts)

    for vsym, (score, tier, hurts) in sorted(veh_best_score.items(), key=lambda x: -x[1][0]):
        hurts_str = ", ".join(hurts) if hurts else "None"
        lines.append(f"| {vsym} | {score:.1f}/100 | {tier} | {hurts_str} |")

    lines += [""]
    return "\n".join(lines)


# ─── Section 2/3 — Security vs ETF + Net Improvement Model ───────────────────

def build_security_candidates() -> list[dict]:
    """Build scored candidate list for each underweight node."""
    candidates = []
    for sym, h in holdings_by_sym.items():
        node = _holding_node(sym)
        o = overlay_by_sym.get(sym, {})
        p = profile_by_sym.get(sym, {})

        composite = float(o.get("composite_score") or 0)
        replay = bool(o.get("replay_supported", False))
        pct = float(o.get("percent_of_portfolio") or 0)
        signal = str(o.get("signal_direction", "") or "")
        ess = str(o.get("ess_score_text", "") or "")
        trim_score = float(p.get("trim_priority_score") or 0)
        sti_class = str(p.get("strategic_classification", "") or "")
        nar_tier = str(p.get("narrative_tier", "") or "")

        # Node gap this holding covers
        al = alignment_by_node.get(node, {})
        node_gap = float(al.get("drift_pct") or 0)  # negative = underweight

        # Contribution to covered nodes
        mc = str(h.get("market_cap_bucket", "") or "").upper()
        geo_raw = str(h.get("geography", "") or "").upper()

        candidates.append({
            "symbol": sym,
            "node": node,
            "geo": geo_raw,
            "mc": mc,
            "composite": composite,
            "replay": replay,
            "pct": pct,
            "signal": signal,
            "ess": ess,
            "trim_score": trim_score,
            "sti_class": sti_class,
            "narrative_tier": nar_tier,
            "node_gap": node_gap,
        })
    return candidates


def _portfolio_improvement_score(c: dict) -> float:
    """
    Audit-only Portfolio Improvement Score (PIS).
    Components:
      +0..30  composite signal quality (max 30)
      +0..20  replay support           (0 or 20)
      +0..20  node gap alignment       (max 20 — only for underweight nodes)
      +0..10  conviction / STI class   (max 10)
      +0..5   ESS bonus                (max 5)
      -0..20  trim penalty             (max -20)
      -0..15  concentration penalty    (max -15 for >5% weight)
    """
    score = 0.0

    # Composite signal (0-5 scale → 0-30 pts)
    score += min(float(c.get("composite") or 0) * 6.0, 30.0)

    # Replay support
    if c.get("replay"):
        score += 20.0

    # Node gap alignment (deploying INTO an underweight node is good)
    gap = float(c.get("node_gap") or 0)
    if gap < 0:  # underweight node
        score += min(abs(gap) * 2.0, 20.0)

    # Conviction tier
    nar = c.get("narrative_tier", "")
    sti = c.get("sti_class", "")
    if nar == "CORE_CONVICTION_LEADER":
        score += 10.0
    elif nar == "HIGH_CONVICTION_ANCHOR":
        score += 7.0
    elif "HIGH_CONVICTION" in sti or "CORE_COMPOUNDER" in sti:
        score += 5.0

    # ESS bonus
    ess = c.get("ess", "")
    if "VERY_BULLISH" in ess:
        score += 5.0
    elif "BULLISH" in ess:
        score += 3.0

    # Trim penalty (high trim score = elevated exit risk)
    score -= min(float(c.get("trim_score") or 0) * 0.2, 20.0)

    # Concentration penalty (positions >5% already carry concentration risk)
    pct = float(c.get("pct") or 0)
    if pct > 5.0:
        score -= min((pct - 5.0) * 3.0, 15.0)

    return round(score, 2)


def security_vs_etf_report(candidates: list[dict]) -> str:
    lines: list[str] = []
    lines += [
        "# Security vs ETF Comparison Report",
        "",
        "**Phase 7.2 — Audit Only**",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## Overview",
        "",
        "For each underweight allocation node, this report compares the engine's current",
        "ETF recommendation against the top replay-supported, high-conviction securities",
        "already in (or available for) that node.",
        "",
        "**Key question:** Do existing high-composite securities in the target node",
        "provide better risk-adjusted targeting than broad ETFs?",
        "",
        "---",
    ]

    for node_key, al in sorted(UNDERWEIGHT_NODES.items(), key=lambda x: x[1]["drift_pct"]):
        actual = float(al.get("actual_pct") or 0)
        target = float(al.get("target_pct") or 0)
        drift = float(al.get("drift_pct") or 0)
        gap_mv = abs(drift) / 100.0 * total_mv

        lines += [
            "",
            f"## Node: {node_key}",
            f"**Actual:** {actual:.2f}%  **Target:** {target:.2f}%  **Gap:** {drift:.2f}%  (~${gap_mv:,.0f})",
            "",
        ]

        # ETF candidates for this node
        etf_recs_for_node = [
            r for r in action_recs
            if r.get("affected_node_key") == node_key
        ]
        if etf_recs_for_node:
            rec = etf_recs_for_node[0]
            lines += [
                "### Current ETF Recommendation",
                "",
                f"Vehicles: **{', '.join(rec.get('affected_symbols', []))}**",
                "",
                "| Vehicle | Target Coverage | Off-Target | Worsens OW | Suitability |",
                "|---------|----------------|------------|------------|-------------|",
            ]
            for v in (rec.get("vehicle_suitability_notes") or []):
                vsym = v.get("symbol", "")
                t_cov = float(v.get("target_node_coverage_pct") or 0)
                off = float(v.get("off_target_exposure_pct") or 0)
                worsens = v.get("worsens_existing_overweight", False)
                tier = v.get("suitability_tier", "")
                score = float(v.get("suitability_score") or 0)
                lines.append(f"| {vsym} | {t_cov:.1f}% | {off:.1f}% | {'⚠ YES' if worsens else 'No'} | {tier} ({score:.0f}/100) |")
            lines += [""]

        # Securities in this node
        node_secs = [
            c for c in candidates
            if c["node"] == node_key
            and str(holdings_by_sym.get(c["symbol"], {}).get("asset_class", "")).upper() == "EQUITIES"
        ]
        node_secs_sorted = sorted(node_secs, key=lambda c: -float(c.get("composite") or 0))

        if node_secs_sorted:
            lines += [
                "### Securities Currently in This Node",
                "",
                "| Symbol | Weight% | Composite | Replay | Signal | ESS | STI Class | Narrative Tier |",
                "|--------|---------|-----------|--------|--------|-----|-----------|----------------|",
            ]
            for c in node_secs_sorted:
                rep_icon = "✓" if c.get("replay") else "—"
                lines.append(
                    f"| {c['symbol']} | {c['pct']:.2f}% | {c['composite']:.3f} | {rep_icon} | "
                    f"{c['signal']} | {c['ess'] or '—'} | {c['sti_class']} | {c['narrative_tier'] or '—'} |"
                )
            lines += [""]
        else:
            lines += ["> *No direct-held securities currently classified in this node.*", ""]

        # Conclusion
        if node_secs_sorted:
            top_sec = node_secs_sorted[0]
            lines += [
                "### Node Assessment",
                "",
                f"The portfolio has {len(node_secs_sorted)} direct holding(s) in {node_key}.",
            ]
            if top_sec["composite"] > 4.0 and top_sec["replay"]:
                lines += [
                    f"Top security: **{top_sec['symbol']}** (composite={top_sec['composite']:.3f}, "
                    f"replay=✓, signal={top_sec['signal']}) already contributes {top_sec['pct']:.2f}% "
                    f"of portfolio to this node.",
                    "",
                    "> **Audit finding:** Adding to an existing high-conviction security in this node",
                    "> provides full 100% node coverage with no Mega/off-target side effects,",
                    f"> vs ETF solutions (15-28% node coverage, 30-60% off-target exposure).",
                ]
            lines += [""]

    return "\n".join(lines)


# ─── Section 3 — Net Portfolio Improvement Score (Top 25) ────────────────────

def net_improvement_model(candidates: list[dict]) -> str:
    # Score all equity holdings (not cash, not ETF-like vehicles)
    equity_candidates = [
        c for c in candidates
        if str(holdings_by_sym.get(c["symbol"], {}).get("asset_class", "")).upper() == "EQUITIES"
        and c.get("composite", 0) > 0
    ]

    for c in equity_candidates:
        c["pis"] = _portfolio_improvement_score(c)

    equity_candidates.sort(key=lambda c: -c["pis"])
    top25 = equity_candidates[:25]

    lines: list[str] = [
        "# Net Portfolio Improvement Model — Top 25 Deployment Opportunities",
        "",
        "**Phase 7.2 — Audit Only**",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## Methodology",
        "",
        "**Portfolio Improvement Score (PIS)** — audit-only, does not affect engine output.",
        "",
        "| Component | Points | Rationale |",
        "|-----------|--------|-----------|",
        "| Composite signal (0–5) × 6 | 0–30 | Signal quality is the strongest predictor |",
        "| Replay supported | +20 | Historical context adds conviction |",
        "| Node gap alignment | 0–20 | Deploying into underweight nodes is better |",
        "| Conviction tier (CCL/HCA) | 0–10 | Engine's narrative tier as quality filter |",
        "| ESS VERY_BULLISH / BULLISH | +3..5 | External signal corroboration |",
        "| Trim penalty (-trim × 0.2) | 0..−20 | High trim = elevated exit risk |",
        "| Concentration penalty (>5%) | 0..−15 | Already heavy positions get discounted |",
        "",
        "---",
        "",
        "## Top 25 Deployment Opportunities",
        "",
        "| Rank | Symbol | PIS | Weight% | Composite | Replay | Node | Narrative Tier | Trim |",
        "|------|--------|-----|---------|-----------|--------|------|----------------|------|",
    ]

    for i, c in enumerate(top25, 1):
        rep = "✓" if c.get("replay") else "—"
        node_short = c["node"].replace("EQUITIES.", "")
        tier = c.get("narrative_tier", "—") or "—"
        tier_short = tier.replace("_CONVICTION_", "_").replace("CORE_LEADER", "CCL").replace("HIGH_ANCHOR", "HCA").replace("TACTICAL_GROWTH_CANDIDATE", "TGC").replace("WATCH_TRIM_CANDIDATE", "WTC")
        lines.append(
            f"| {i} | {c['symbol']} | {c['pis']:.1f} | {c['pct']:.2f}% | "
            f"{c['composite']:.3f} | {rep} | {node_short} | {tier_short} | {c['trim_score']:.0f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Key Observations",
        "",
    ]

    # Top by node
    node_counts: dict[str, list] = {}
    for c in top25:
        node_counts.setdefault(c["node"], []).append(c["symbol"])

    lines += ["### Distribution by Node", ""]
    for node, syms in sorted(node_counts.items()):
        lines.append(f"- **{node}**: {', '.join(syms)}")

    replay_in_top25 = [c for c in top25 if c.get("replay")]
    ccl = [c for c in top25 if c.get("narrative_tier") == "CORE_CONVICTION_LEADER"]
    hca = [c for c in top25 if c.get("narrative_tier") == "HIGH_CONVICTION_ANCHOR"]

    lines += [
        "",
        "### Signal Summary",
        "",
        f"- Replay-supported in top 25: **{len(replay_in_top25)}** / 25",
        f"- Core Conviction Leaders: **{len(ccl)}**",
        f"- High Conviction Anchors: **{len(hca)}**",
        f"- Mean composite (top 25): **{sum(c['composite'] for c in top25)/len(top25):.3f}**",
        f"- Mean PIS (top 25): **{sum(c['pis'] for c in top25)/len(top25):.1f}**",
        "",
    ]

    return "\n".join(lines)


# ─── Section 4 — Cash Deployment Analysis ────────────────────────────────────

def cash_deployment_report(candidates: list[dict]) -> str:
    # Cash analysis
    cash_node = alignment_by_node.get("CASH", {})
    cash_actual = float(cash_node.get("actual_pct") or 0)
    cash_target = float(cash_node.get("target_pct") or 0)
    cash_excess = max(cash_actual - cash_target, 0)
    deployable_mv = cash_excess / 100.0 * total_mv

    # Score all equity candidates for deployment
    equity_candidates = [
        c for c in candidates
        if str(holdings_by_sym.get(c["symbol"], {}).get("asset_class", "")).upper() == "EQUITIES"
        and c.get("composite", 0) > 0
    ]
    for c in equity_candidates:
        c["pis"] = _portfolio_improvement_score(c)

    equity_candidates.sort(key=lambda c: -c["pis"])
    top10 = equity_candidates[:10]

    # ETF deployment analysis
    etf_options = [
        {
            "symbol": "SPY", "type": "ETF",
            "target_coverage": 15.0, "off_target": 60.0, "conflicts": "HYPER_MEGA, ULTRA_MEGA",
            "composite": "N/A", "replay": "N/A", "note": "S&P 500 — worsens Mega overweights"
        },
        {
            "symbol": "VTI", "type": "ETF",
            "target_coverage": 28.0, "off_target": 38.5, "conflicts": "HYPER_MEGA, ULTRA_MEGA",
            "composite": "N/A", "replay": "N/A", "note": "Total Market — partially worsens Mega"
        },
        {
            "symbol": "IEFA", "type": "ETF",
            "target_coverage": 100.0, "off_target": 0.0, "conflicts": "INTERNATIONAL.LARGE (overweight)",
            "composite": "N/A", "replay": "N/A", "note": "Intl Developed — worsens Intl overweight"
        },
    ]

    lines: list[str] = [
        "# Cash Deployment Analysis Report",
        "",
        "**Phase 7.2 — Audit Only**",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## Cash Position",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Current cash (SPAXX) | {cash_actual:.2f}% |",
        f"| Mandate target cash | {cash_target:.2f}% |",
        f"| Excess cash | {cash_excess:.2f}% |",
        f"| Deployable amount (~) | ${deployable_mv:,.0f} |",
        f"| Total portfolio MV | ${total_mv:,.2f} |",
        "",
        "> Under the Concentrated Alpha mandate, cash target is 7.0%. Current cash is",
        f"> {cash_actual:.2f}%, leaving ~{cash_excess:.2f}% (${deployable_mv:,.0f}) deployable without",
        "> violating the archetype target.",
        "",
        "---",
        "",
        "## ETF Deployment Path",
        "",
        "| Vehicle | Node Target | Target Coverage | Off-Target Exposure | Key Conflict |",
        "|---------|------------|----------------|--------------------|-|",
    ]
    for e in etf_options:
        lines.append(
            f"| {e['symbol']} | US Large/Mega | {e['target_coverage']:.0f}% | {e['off_target']:.1f}% | {e['conflicts']} |"
        )

    lines += [
        "",
        "> **ETF path conclusion:** All available ETF vehicles for underweight nodes either",
        "> worsen existing Mega overweights or worsen the International overweight.",
        "> No ETF provides clean single-node targeting for cash deployment.",
        "",
        "---",
        "",
        "## Security Deployment Path — Top 10 Opportunities",
        "",
        "Ranked by Portfolio Improvement Score (composite + replay + node alignment + conviction − penalties).",
        "",
        "| Rank | Symbol | PIS | Weight% | Composite | Replay | Node | Conviction | Trim |",
        "|------|--------|-----|---------|-----------|--------|------|------------|------|",
    ]

    for i, c in enumerate(top10, 1):
        rep = "✓" if c.get("replay") else "—"
        node_short = c["node"].replace("EQUITIES.", "")
        tier = c.get("narrative_tier", "—") or "—"
        tier_short = {
            "CORE_CONVICTION_LEADER": "CCL",
            "HIGH_CONVICTION_ANCHOR": "HCA",
            "TACTICAL_GROWTH_CANDIDATE": "TGC",
            "WATCH_TRIM_CANDIDATE": "WTC",
        }.get(tier, tier)
        pis = c.get("pis", 0)
        lines.append(
            f"| {i} | **{c['symbol']}** | {pis:.1f} | {c['pct']:.2f}% | "
            f"{c['composite']:.3f} | {rep} | {node_short} | {tier_short} | {c['trim_score']:.0f} |"
        )

    top_pick = top10[0] if top10 else {}
    top10_replay = [c for c in top10 if c.get("replay")]

    lines += [
        "",
        "---",
        "",
        "## Cash Deployment Findings",
        "",
        "### If $10,000 were deployed today:",
        "",
        "**ETF path (SPY/VOO):**",
        f"- Adds ~{10000/total_mv*100*0.15:.2f}% to US Large (partially helps -7.3% gap)",
        f"- Adds ~{10000/total_mv*100*0.30:.2f}% to Hyper Mega (worsens +3.7% overweight)",
        f"- Net: mixed improvement — repairs one node, worsens another",
        "",
        "**Security path (top PIS candidates):**",
        f"- ${10000:,.0f} into **{top_pick.get('symbol','')}** adds ~{10000/total_mv*100:.2f}% to",
        f"  {top_pick.get('node','').replace('EQUITIES.','')} with full node coverage and no off-target leakage",
        f"- Composite: {top_pick.get('composite',0):.3f} | Replay: {'✓' if top_pick.get('replay') else '—'} | "
        f"Conviction: {top_pick.get('narrative_tier','—')}",
        "",
        f"**Replay-supported securities in top 10:** {len(top10_replay)}/10",
        "",
        "### Recommendation (audit only — does not change engine output)",
        "",
        "> The security deployment path dominates the ETF path on a per-dollar basis:",
        "> higher composite scores, full node coverage, no off-target leakage,",
        "> and no conflict with existing overweight nodes.",
        "> This suggests the engine should evolve toward conviction-weighted security",
        "> selection for cash deployment, rather than broad ETF allocation repair.",
        "",
    ]

    return "\n".join(lines)


# ─── Section 5 — Overlap / Redundancy Analysis ───────────────────────────────

def overlap_analysis_report() -> str:
    lines: list[str] = [
        "# Overlap Analysis Report — Recommendation Redundancy",
        "",
        "**Phase 7.2 — Audit Only**",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## Section 1 — Vehicle Overlap Between Recommendations",
        "",
        "| Recommendation A | Recommendation B | Shared Vehicles | Overlap % |",
        "|-----------------|-----------------|----------------|-----------|",
    ]

    build_recs = [
        {"node": r.get("affected_node_key", ""),
         "type": r.get("recommendation_type", ""),
         "vehicles": r.get("affected_symbols", []),
         "vsn": {v.get("symbol",""): v for v in (r.get("vehicle_suitability_notes") or [])}}
        for r in action_recs if r.get("recommendation_type") == "INCREASE_UNDERWEIGHT"
    ]

    for i, rec_a in enumerate(build_recs):
        for j, rec_b in enumerate(build_recs):
            if j <= i:
                continue
            a_veh = set(rec_a.get("vehicles", []))
            b_veh = set(rec_b.get("vehicles", []))
            shared = a_veh & b_veh
            if shared:
                total_veh = len(a_veh | b_veh)
                overlap_pct = len(shared) / total_veh * 100
                a_node = rec_a["node"].replace("EQUITIES.", "")
                b_node = rec_b["node"].replace("EQUITIES.", "")
                lines.append(
                    f"| Build {a_node} | Build {b_node} | {', '.join(sorted(shared))} | {overlap_pct:.0f}% |"
                )

    lines += [
        "",
        "### Finding",
        "",
        "> **VOO** appears in both 'Build US Large' and 'Build Extended Mega' recommendations.",
        "> Executing both recommendations with VOO is counterproductive:",
        "> - For US Large: VOO is 15% effective (LOW suitability, score=15.0)",
        "> - For Extended Mega: VOO is 25% effective (LOW suitability, score=17.4)",
        "> The vehicle solves neither problem cleanly and appears in both because it is",
        "> the default broad-US vehicle in the engine's vehicle registry.",
        "",
        "---",
        "",
        "## Section 2 — Node Hierarchy Redundancy",
        "",
        "Build recommendations targeting sub-nodes of the same parent can be partially",
        "redundant if the same vehicle is prescribed for both.",
        "",
        "| Parent Node | Child Recs | Same Vehicle? | Redundancy? |",
        "|-------------|-----------|--------------|-------------|",
    ]

    # US MEGA subtier analysis
    mega_recs = [r for r in build_recs if "MEGA" in r["node"]]
    parent_mega = alignment_by_node.get("EQUITIES.US.MEGA", {})
    parent_drift = float(parent_mega.get("drift_pct") or 0)
    parent_dir = parent_mega.get("drift_direction", "")

    if mega_recs:
        nodes_str = " + ".join([r["node"].replace("EQUITIES.", "") for r in mega_recs])
        # Check if parent node itself is under/overweight
        parent_note = f"Parent EQUITIES.US.MEGA is {parent_dir} (drift={parent_drift:.2f}%)"
        lines += [
            f"| EQUITIES.US.MEGA | {nodes_str} | Yes (VOO in both) | PARTIAL |",
            "",
            f"> {parent_note}.",
            "> Repairing Extended Mega subtier via VOO also adds Hyper/Ultra Mega,",
            "> which are themselves overweight. Subtier repair requires subtier-specific vehicles.",
        ]

    lines += [
        "",
        "---",
        "",
        "## Section 3 — Mandate Override Impact",
        "",
        "Under the Concentrated Alpha mandate, several 'Build' recommendations are",
        "reclassified as INTENTIONAL_UNDERWEIGHT — no action required.",
        "",
        "| Recommendation | Raw Severity | Mandate Severity | Mandate Label |",
        "|---------------|-------------|-----------------|---------------|",
    ]

    for rec in action_recs:
        raw_sev = rec.get("severity", "")
        mandate_sev = rec.get("mandate_severity", "")
        mandate_label = rec.get("mandate_drift_label", "")
        node = (rec.get("affected_node_key") or "").replace("EQUITIES.", "")
        if mandate_sev in ("NONE", "INFORMATIONAL"):
            lines.append(f"| Build/Reduce {node} | {raw_sev} | {mandate_sev} | {mandate_label} |")

    lines += [
        "",
        "> **Finding:** Both underweight 'Build' recommendations (US Large, Extended Mega)",
        "> are downgraded to INFORMATIONAL under Concentrated Alpha — meaning they are",
        "> already considered intentional positioning. The engine is generating MODERATE-",
        "> severity build recs that the PMI layer immediately demotes. This suggests the",
        "> allocation engine and the PMI layer are partially in conflict.",
        "",
        "---",
        "",
        "## Section 4 — Reduce Recommendation Overlap",
        "",
        "| Recommendation A | Recommendation B | Shared Symbols | Note |",
        "|-----------------|-----------------|---------------|------|",
    ]

    reduce_recs = [
        {"node": r.get("affected_node_key", ""),
         "type": r.get("recommendation_type", ""),
         "vehicles": r.get("affected_symbols", [])}
        for r in action_recs if r.get("recommendation_type") == "REDUCE_OVERWEIGHT"
    ]
    for i, ra in enumerate(reduce_recs):
        for j, rb in enumerate(reduce_recs):
            if j <= i:
                continue
            a_syms = set(ra.get("vehicles", []))
            b_syms = set(rb.get("vehicles", []))
            shared = a_syms & b_syms
            if shared:
                a_node = ra["node"].replace("EQUITIES.", "")
                b_node = rb["node"].replace("EQUITIES.", "")
                lines.append(
                    f"| Reduce {a_node} | Reduce {b_node} | {', '.join(sorted(shared))} | ETFs contribute to both |"
                )

    lines += [""]
    return "\n".join(lines)


# ─── Section 6 — Conviction Deployment Report ────────────────────────────────

def conviction_deployment_report(candidates: list[dict]) -> str:
    # Score all equity candidates
    equity_candidates = [
        c for c in candidates
        if str(holdings_by_sym.get(c["symbol"], {}).get("asset_class", "")).upper() == "EQUITIES"
        and c.get("composite", 0) > 0
    ]
    for c in equity_candidates:
        c["pis"] = _portfolio_improvement_score(c)

    # Top conviction securities (CCL + HCA with replay)
    conviction = sorted(
        [c for c in equity_candidates if c.get("narrative_tier") in (
            "CORE_CONVICTION_LEADER", "HIGH_CONVICTION_ANCHOR"
        )],
        key=lambda c: c.get("strategic_anchor_rank", 999) or 999,
    )

    # Fill in anchor rank from profiles
    for c in conviction:
        p = profile_by_sym.get(c["symbol"], {})
        c["anchor_rank"] = int(p.get("strategic_anchor_rank") or 0)

    conviction.sort(key=lambda c: (c.get("anchor_rank") or 999))

    # VOO representative stats for comparison
    voo_etf = {
        "symbol": "VOO", "composite": "N/A",
        "target_cov": 15.0,  # for US Large
        "off_target": 60.0,
        "worsens_ow": True,
        "suitability": "LOW (15.0/100)",
        "replay": "N/A",
        "note": "S&P 500; worsens Hyper/Ultra Mega overweights"
    }

    lines: list[str] = [
        "# Conviction Deployment Report",
        "",
        "**Phase 7.2 — Audit Only**",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## Overview",
        "",
        "This report evaluates the portfolio's top conviction securities as potential",
        "deployment candidates versus the engine's current ETF recommendations.",
        "",
        "The core question: **Are broad-market ETFs (VOO, VTI, SCHB) the best use of",
        "excess cash when the portfolio already holds replay-supported, high-composite",
        "securities in the same or nearby nodes?**",
        "",
        "---",
        "",
        "## Section 1 — Why VOO Is Currently Recommended",
        "",
        "1. **Vehicle registry default**: The engine's `investable_vehicle_registry.yaml`",
        "   maps `US.LARGE` → `VEH_US_LARGE_SPY` (SPY). VOO/IVV appear as alternatives.",
        "2. **Gap-first logic**: The alignment engine detects a -7.3% US Large gap and",
        "   retrieves the registered vehicle. No conviction filter is applied.",
        "3. **ETF decomposition**: The engine correctly identifies that VOO/IVV/SPY provide",
        "   ~15% coverage for US Large — but does not penalize the 85% Mega leakage heavily",
        "   enough to prevent the recommendation.",
        "",
        "---",
        "",
        "## Section 2 — Is VOO Actually Optimal?",
        "",
        "| Criterion | VOO | Best Security Alternative |",
        "|-----------|-----|--------------------------|",
        "| US Large node coverage | ~15% effective | 100% (direct holding) |",
        "| Off-target (Mega) exposure | ~60% | 0% |",
        "| Worsens Hyper Mega OW | ⚠ YES | No |",
        "| Composite score | N/A (index) | 4.0–4.9 (individual) |",
        "| Replay support | N/A | Available for top names |",
        "| Conviction filter | None | CCL / HCA tier |",
        "| Mandate suitability | INTENTIONAL_UNDERWEIGHT | No mandate conflict |",
        "",
        "> **Audit finding: VOO is NOT optimal for this portfolio.**",
        "> It provides partial node coverage (15%), creates multi-node conflicts,",
        "> carries no composite signal or replay support, and the mandate layer",
        "> demotes the recommendation to INFORMATIONAL anyway.",
        "",
        "---",
        "",
        "## Section 3 — Top Conviction Securities",
        "",
        "Securities ranked by strategic anchor rank (Phase 7.1 narrative tier assignment).",
        "These are the highest-conviction names in the portfolio as identified by the engine.",
        "",
        "| Rank | Symbol | Tier | Weight% | Composite | Replay | Node | ESS | Trim | PIS |",
        "|------|--------|------|---------|-----------|--------|------|-----|------|-----|",
    ]

    for c in conviction[:20]:
        rep = "✓" if c.get("replay") else "—"
        tier_short = {
            "CORE_CONVICTION_LEADER": "CCL",
            "HIGH_CONVICTION_ANCHOR": "HCA",
        }.get(c.get("narrative_tier", ""), c.get("narrative_tier", "—"))
        node_short = c["node"].replace("EQUITIES.", "")
        rank = c.get("anchor_rank") or "—"
        lines.append(
            f"| {rank} | **{c['symbol']}** | {tier_short} | {c['pct']:.2f}% | "
            f"{c['composite']:.3f} | {rep} | {node_short} | {c['ess'] or '—'} | "
            f"{c['trim_score']:.0f} | {c.get('pis',0):.1f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Section 4 — Security vs VOO: Per-Name Analysis",
        "",
        "For each Core Conviction Leader, why it is or is not preferred over VOO for cash deployment.",
        "",
    ]

    ccl = [c for c in conviction if c.get("narrative_tier") == "CORE_CONVICTION_LEADER"]
    hca = [c for c in conviction if c.get("narrative_tier") == "HIGH_CONVICTION_ANCHOR"]

    for c in ccl:
        sym = c["symbol"]
        comp = c["composite"]
        rep = c.get("replay", False)
        pct = c["pct"]
        node = c["node"].replace("EQUITIES.", "")
        trim = c["trim_score"]
        ess = c.get("ess", "") or "—"
        pis = c.get("pis", 0)

        is_heavy = pct > 5.0
        conc_note = f"Already {pct:.1f}% of portfolio — concentration risk if enlarged further." if is_heavy else f"At {pct:.1f}%, has room to grow."
        replay_note = "Replay-supported — historical return context available." if rep else "No replay data — limited historical context."

        lines += [
            f"### {sym} (CCL — Core Conviction Leader)",
            "",
            f"- **Node:** {node}  **Weight:** {pct:.2f}%  **Composite:** {comp:.3f}  **Trim:** {trim:.0f}/100",
            f"- **ESS:** {ess}  **Replay:** {'Yes' if rep else 'No'}  **PIS:** {pis:.1f}",
            "",
            "**Preferred over VOO?**",
            "",
        ]
        if comp > 4.0 and rep and not is_heavy and trim < 30:
            lines += [
                f"> **YES** — {sym} provides 100% node coverage for {node} with composite={comp:.3f}",
                f"> (vs VOO's 15% node coverage and ~60% off-target Mega leakage).",
                f"> {replay_note} {conc_note}",
            ]
        elif is_heavy:
            lines += [
                f"> **QUALIFIED YES** — High conviction signal, but {conc_note}",
                f"> Trimming may be triggered before adding. ETF alternative may be appropriate",
                f"> for incremental deployment if concentration risk is a concern.",
            ]
        else:
            lines += [
                f"> **YES** — {sym} provides cleaner node coverage with stronger signal quality.",
                f"> {conc_note} {replay_note}",
            ]
        lines += [""]

    lines += [
        "---",
        "",
        "## Section 5 — Superior Security Alternatives by Node",
        "",
    ]

    for node_key, al in sorted(UNDERWEIGHT_NODES.items(), key=lambda x: x[1]["drift_pct"]):
        node_secs = sorted(
            [c for c in equity_candidates if c["node"] == node_key and c.get("replay") and c.get("composite", 0) > 3.0],
            key=lambda c: -(c.get("pis") or 0),
        )
        if not node_secs:
            # Widen to non-replay too
            node_secs = sorted(
                [c for c in equity_candidates if c["node"] == node_key and c.get("composite", 0) > 3.0],
                key=lambda c: -(c.get("pis") or 0),
            )

        gap = float(al.get("drift_pct") or 0)
        lines += [
            f"### {node_key}  (gap={gap:.2f}%)",
            "",
        ]
        if node_secs:
            lines += [
                "| Symbol | Composite | Replay | PIS | vs VOO advantage |",
                "|--------|-----------|--------|-----|-----------------|",
            ]
            for c in node_secs[:5]:
                rep = "✓" if c.get("replay") else "—"
                adv = f"100% node coverage vs VOO {ETF_NODE_COVERAGE.get('VOO', {}).get(node_key, 0):.0f}%; no off-target Mega"
                lines.append(f"| {c['symbol']} | {c['composite']:.3f} | {rep} | {c.get('pis',0):.1f} | {adv} |")
        else:
            lines += [
                "> No direct-held securities currently in this node.",
                "> ETF may be required if node representation is desired.",
                "> Consider securities being added to the portfolio that would classify here.",
            ]
        lines += [""]

    lines += [
        "---",
        "",
        "## Section 6 — Final Findings",
        "",
        "### 1. Why is VOO recommended?",
        "",
        "> VOO is the default broad-US vehicle registered for the US Large and US Mega nodes.",
        "> The engine applies a gap-first vehicle lookup without a conviction quality gate.",
        "> Any registered broad-US ETF with partial US Large exposure triggers the recommendation.",
        "",
        "### 2. Is VOO actually optimal?",
        "",
        "> **No.** VOO suitability for US Large is LOW (15.0/100). It provides only 15%",
        "> effective US Large coverage while adding ~60% off-target Mega exposure.",
        "> The mandate layer immediately demotes both 'Build' recs to INFORMATIONAL,",
        "> recognizing these as intentional positioning.",
        "",
        "### 3. Are there superior security-level alternatives?",
        "",
        "> **Yes.** Portfolio already holds high-conviction, replay-supported securities",
        "> with composite scores 4.0–4.9 in the target nodes. Adding to DELL, VRT,",
        "> or LRCX for US Large provides 100% node coverage and zero off-target leakage,",
        "> with materially stronger signal quality than any ETF.",
        "",
        "### 4. Which recommendations conflict with each other?",
        "",
        "> - **Build US Large (VOO)** ↔ **Reduce Hyper Mega**: VOO adds ~30% to Hyper Mega",
        "> - **Build Extended Mega (VTI/SCHB)** ↔ **Reduce Hyper Mega**: Both VTI/SCHB add ~16.5% Hyper Mega",
        "> - **Build US Large (VOO)** ↔ **Build Extended Mega (VOO)**: Same vehicle in both; redundant",
        "> - **Both Build recs** vs PMI layer: Mandate reclassifies both as INTENTIONAL (no action needed)",
        "",
        "### 5. Highest expected-value deployment of excess cash",
        "",
        "> Ranked by Portfolio Improvement Score:",
    ]

    top3 = sorted(equity_candidates, key=lambda c: -(c.get("pis") or 0))[:3]
    for i, c in enumerate(top3, 1):
        node_s = c["node"].replace("EQUITIES.", "")
        lines.append(
            f"> {i}. **{c['symbol']}** — PIS={c.get('pis',0):.1f}, composite={c['composite']:.3f}, "
            f"replay={'Yes' if c.get('replay') else 'No'}, node={node_s}"
        )

    lines += [
        ">",
        "> Security-level deployment into existing high-conviction holdings provides better",
        "> targeted node repair, eliminates cross-node conflicts, and captures the portfolio's",
        "> existing intelligence advantage over generic ETF indices.",
        "",
    ]

    return "\n".join(lines)


# ─── Main execution ───────────────────────────────────────────────────────────

def main():
    candidates = build_security_candidates()
    conflict_matrix = build_conflict_matrix()

    print("Generating reports…")

    # 1. Conflict report
    text = conflict_report_text(conflict_matrix)
    Path("recommendation_conflict_report.md").write_text(text)
    print(f"  ✓ recommendation_conflict_report.md ({len(text):,} chars)")

    # 2. Security vs ETF
    text = security_vs_etf_report(candidates)
    Path("security_vs_etf_report.md").write_text(text)
    print(f"  ✓ security_vs_etf_report.md ({len(text):,} chars)")

    # 3. Cash deployment
    text = cash_deployment_report(candidates)
    Path("cash_deployment_report.md").write_text(text)
    print(f"  ✓ cash_deployment_report.md ({len(text):,} chars)")

    # 4. Overlap analysis
    text = overlap_analysis_report()
    Path("overlap_analysis_report.md").write_text(text)
    print(f"  ✓ overlap_analysis_report.md ({len(text):,} chars)")

    # 5. Conviction deployment (includes net improvement model appendix)
    text = conviction_deployment_report(candidates)
    text += "\n\n---\n\n## Appendix — Full Net Portfolio Improvement Model (Top 25)\n\n"
    text += net_improvement_model(candidates)
    Path("conviction_deployment_report.md").write_text(text)
    print(f"  ✓ conviction_deployment_report.md ({len(text):,} chars)")

    print("\nAll Phase 7.2 audit reports generated.")


if __name__ == "__main__":
    main()
