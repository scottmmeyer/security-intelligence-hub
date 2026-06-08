"""Phase E — Strategic Recommendation Synthesis.

Evolves the recommendation engine from generic allocation drift warnings into
explainable strategic portfolio construction guidance.

The system synthesizes:
  - STI intelligence (trim_priority_score, strategic_classification)
  - Thematic overlap topology
  - Strategic role semantics
  - Replay alignment
  - Concentration topology
  - Effective exposure intelligence

into top-level portfolio recommendations that explain:
  - Which holdings are strategically core and why
  - Which concentrations are intentional vs accidental
  - Which overlap is redundant
  - Which trims preserve portfolio quality best
  - Which holdings are simply duplicated thematic exposure

Phase E sections:
  E.1 — STI-driven recommendation synthesis
  E.2 — Recommendation narrative evolution
  E.3 — Strategic retain intelligence
  E.4 — Thematic saturation narratives
  E.5 — Top trim candidate surfacing
  E.6 — Recommendation prioritization
  E.7 — Recommendation deduplication evolution
  E.8 — Portfolio construction explainability
  E.9 — UI data payloads for rich card rendering
  E.10 — Validators
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from .models import (
    HoldingStrategicProfile,
    PortfolioHolding,
    PortfolioRecommendation,
    SecurityIntelligenceOverlay,
)


# ─────────────────────────────────────────────────────────────────────────────
# E.1 / E.4 — Theme label registry
# ─────────────────────────────────────────────────────────────────────────────

_THEME_LABELS: dict[str, str] = {
    "AI_INFRA":                    "AI Infrastructure",
    "SEMICONDUCTOR_CONCENTRATION": "Semiconductor",
    "MEGA_TECH_CONCENTRATION":     "Mega-Tech",
    "GROWTH_MOMENTUM":             "Growth Momentum",
    "ENERGY_TRANSITION":           "Energy Transition",
    "RATE_SENSITIVITY":            "Rate Sensitivity",
    "GENERAL":                     "General Portfolio",
}

_RETAIN_REASONS: dict[str, str] = {
    "HIGH_CONVICTION_RETAIN": "replay leadership + strong fundamental signal + low thematic redundancy",
    "CORE_COMPOUNDER":        "foundational broad-market exposure; portfolio anchor",
    "STRATEGIC_CORE":         "fills a unique allocation role with no equivalent substitute",
    "THEMATIC_LEADER":        "highest-conviction holding within its thematic cluster",
}

_TRIM_CLASSIFICATIONS = frozenset({
    "REDUCIBLE",
    "REDUNDANT_EXPOSURE",
    "CONCENTRATION_RISK",
})

_RETAIN_CLASSIFICATIONS = frozenset({
    "HIGH_CONVICTION_RETAIN",
    "CORE_COMPOUNDER",
    "STRATEGIC_CORE",
    "THEMATIC_LEADER",
})

_TACTICAL_CLASSIFICATIONS = frozenset({
    "TACTICAL_GROWTH",
})


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _theme_label(key: str) -> str:
    return _THEME_LABELS.get(key, key.replace("_", " ").title())


def _overlay_for(symbol: str, overlays: list[SecurityIntelligenceOverlay]) -> Optional[SecurityIntelligenceOverlay]:
    sym = symbol.upper()
    return next((o for o in overlays if o.symbol.upper() == sym), None)


def _profile_for(symbol: str, profiles: list[HoldingStrategicProfile]) -> Optional[HoldingStrategicProfile]:
    sym = symbol.upper()
    return next((p for p in profiles if p.symbol.upper() == sym), None)


def _holding_for(symbol: str, holdings: list[PortfolioHolding]) -> Optional[PortfolioHolding]:
    sym = symbol.upper()
    return next((h for h in holdings if h.symbol.upper() == sym), None)


def _replay_str(overlay: Optional[SecurityIntelligenceOverlay]) -> str:
    if not overlay or not overlay.replay_supported:
        return "no replay support"
    pct = overlay.replay_percentile
    if pct is not None:
        return f"replay-supported ({pct:.0f}th percentile)"
    return "replay-supported"


def _signal_str(overlay: Optional[SecurityIntelligenceOverlay]) -> str:
    if not overlay:
        return "signal unknown"
    d = (overlay.signal_direction or "UNKNOWN").upper()
    score = overlay.composite_score
    ess = overlay.ess_score_text or ""
    parts = [d.title()]
    if score is not None:
        parts.append(f"score {score:.2f}")
    if ess:
        parts.append(f"ESS: {ess}")
    return " | ".join(parts)


def _severity_from_trim_score(score: float) -> tuple[str, str, int]:
    """Return (severity, confidence, priority) from a trim priority score."""
    if score >= 70:
        return "HIGH", "HIGH", 2
    if score >= 50:
        return "MODERATE", "MEDIUM", 3
    return "LOW", "LOW", 4


# ─────────────────────────────────────────────────────────────────────────────
# E.3 — Strategic retain intelligence
# ─────────────────────────────────────────────────────────────────────────────

def _build_retain_rationale(
    profile: HoldingStrategicProfile,
    overlay: Optional[SecurityIntelligenceOverlay],
    holdings: list[PortfolioHolding],
) -> str:
    """Build an explainable retain rationale for a HIGH_CONVICTION / CORE holding.

    Explains WHY the holding remains strategically important even when
    concentration exists.
    """
    cls = profile.strategic_classification
    sym = profile.symbol.upper()

    reasons: list[str] = []

    # 1. Strategic role
    role_reason = _RETAIN_REASONS.get(cls, "")
    if role_reason:
        reasons.append(role_reason)

    # 2. Replay leadership
    if overlay and overlay.replay_supported:
        pct = overlay.replay_percentile
        if pct and pct >= 75:
            reasons.append(f"replay leadership ({pct:.0f}th percentile in tier)")
        else:
            reasons.append("replay-supported position")

    # 3. Signal strength
    if overlay:
        direction = (overlay.signal_direction or "").upper()
        score = overlay.composite_score
        if direction == "BULLISH":
            score_str = f" (score: {score:.2f})" if score is not None else ""
            reasons.append(f"bullish fundamental signal{score_str}")
        elif direction == "NEUTRAL" and score is not None and score >= 2.8:
            reasons.append(f"constructive neutral signal (score: {score:.2f})")

    # 4. Thematic leadership
    if cls == "THEMATIC_LEADER":
        clusters = profile.thematic_overlap_clusters
        if clusters:
            cluster_names = " + ".join(_theme_label(c) for c in clusters[:2])
            reasons.append(f"leads within {cluster_names} theme cluster")

    # 5. Low thematic redundancy
    if profile.thematic_redundancy_score < 20:
        reasons.append("provides unique, low-redundancy thematic exposure")

    # 6. Diversification contribution
    if profile.diversification_contribution >= 60:
        reasons.append(f"meaningful diversification contribution ({profile.diversification_contribution:.0f}/100)")

    return (
        f"{sym} warrants strategic preservation. "
        + " | ".join(reasons)
        + "."
    )


# ─────────────────────────────────────────────────────────────────────────────
# E.2 / E.5 — Top trim candidate surfacing per cluster
# ─────────────────────────────────────────────────────────────────────────────

def _build_cluster_trim_narrative(
    cluster_key: str,
    profiles_in_cluster: list[HoldingStrategicProfile],
    all_profiles: list[HoldingStrategicProfile],
    overlays: list[SecurityIntelligenceOverlay],
    holdings: list[PortfolioHolding],
) -> tuple[str, str, str, str]:
    """Build title, rationale, evidence_summary, reasoning_trace for a cluster.

    Returns (title, rationale, evidence_summary, reasoning_trace).
    """
    cluster_label = _theme_label(cluster_key)

    # Sort: most expendable first
    sorted_trim = sorted(profiles_in_cluster, key=lambda p: -p.trim_priority_score)
    top = sorted_trim[0]
    top_overlay = _overlay_for(top.symbol, overlays)

    # Find retain anchors in same cluster (any RETAIN classification)
    all_cluster_syms = {p.symbol for p in profiles_in_cluster}
    retain_anchors = [
        p for p in all_profiles
        if p.strategic_classification in _RETAIN_CLASSIFICATIONS
        and any(c in p.thematic_overlap_clusters for c in (top.thematic_overlap_clusters or ()))
    ]

    # ── Title (E.2) ──────────────────────────────────────────────────────────
    title = (
        f"{cluster_label} concentration: {top.symbol} is most expendable"
        f" — score {top.trim_priority_score:.0f}/100"
    )

    # ── Rationale (E.2, E.5, E.8) ────────────────────────────────────────────
    # Paragraph 1: ecosystem context
    all_exposed_syms = sorted(
        {p.symbol for p in all_profiles if any(
            c in (p.thematic_overlap_clusters or ())
            for c in (top.thematic_overlap_clusters or (cluster_key,))
        )},
        key=lambda s: next((p.percent_of_portfolio for p in all_profiles if p.symbol == s), 0),
        reverse=True,
    )
    exposure_list = ", ".join(all_exposed_syms[:6])

    rationale = (
        f"{cluster_label} exposure is currently spread across multiple holdings: "
        f"{exposure_list}. "
    )

    # Paragraph 2: why top candidate is expendable
    trim_reasons: list[str] = []
    if top.thematic_redundancy_score >= 40:
        trim_reasons.append(f"high thematic redundancy ({top.thematic_redundancy_score:.0f}/100)")
    if top_overlay and (top_overlay.signal_direction or "").upper() == "BEARISH":
        trim_reasons.append("bearish fundamental signal")
    elif top_overlay and (top_overlay.signal_direction or "").upper() == "NEUTRAL":
        trim_reasons.append("neutral/non-differentiated signal")
    if not (top_overlay and top_overlay.replay_supported):
        trim_reasons.append("no replay support")
    if top.exposure_origin == "ETF_THEMATIC":
        trim_reasons.append("ETF-derived thematic exposure (indirect)")
    if top.concentration_pressure >= 15:
        trim_reasons.append(f"concentration pressure ({top.concentration_pressure:.0f}pts)")

    reason_str = (
        " | ".join(trim_reasons) if trim_reasons
        else f"{top.strategic_classification.replace('_', ' ').title()} classification"
    )
    rationale += (
        f"{top.symbol} ranks as the most strategically expendable holding in this cluster "
        f"due to: {reason_str}. "
    )

    # Paragraph 3: what is justified (retain anchors)
    if retain_anchors:
        anchor_syms = [p.symbol for p in retain_anchors[:2]]
        anchor_reasons = []
        for ap in retain_anchors[:2]:
            ao = _overlay_for(ap.symbol, overlays)
            r = []
            if ao and ao.replay_supported:
                r.append("replay leadership")
            if ao and (ao.signal_direction or "").upper() == "BULLISH":
                r.append("strong signal")
            if ap.strategic_classification == "HIGH_CONVICTION_RETAIN":
                r.append("high conviction")
            elif ap.strategic_classification == "CORE_COMPOUNDER":
                r.append("core anchor")
            anchor_reasons.append(
                f"{ap.symbol} ({', '.join(r) if r else ap.strategic_classification.replace('_', ' ')})"
            )
        rationale += (
            f"Direct concentration in {' and '.join(anchor_syms)} remains strategically justified due to "
            f"{', '.join(anchor_reasons)}. "
        )

    # Ranked trim list
    ranked_str = ", ".join(
        f"{p.symbol} ({p.trim_priority_score:.0f})"
        for p in sorted_trim[:4]
    )
    rationale += f"Top trim candidates within {cluster_label} overlap: {ranked_str}."

    # ── Evidence summary ──────────────────────────────────────────────────────
    evidence_summary = (
        f"STI trim priority: {top.trim_priority_score:.0f}/100. "
        f"Thematic redundancy: {top.thematic_redundancy_score:.0f}/100. "
        f"Strategic importance: {top.strategic_importance}. "
        f"Signal: {_signal_str(top_overlay)}. "
        f"Replay: {_replay_str(top_overlay)}."
    )

    # ── Reasoning trace ───────────────────────────────────────────────────────
    factor_strs = [
        f"{f[0].replace('_', ' ')} ({f[1]:+.1f}pts)"
        for f in (top.trim_factors or ())
    ] if top.trim_factors else []
    factor_summary = " | ".join(factor_strs[:5]) if factor_strs else "no factor breakdown"

    reasoning_trace = (
        f"Phase E synthesis | cluster: {cluster_key} | "
        f"top trim: {top.symbol} (score={top.trim_priority_score:.0f}) | "
        f"classification: {top.strategic_classification} | "
        f"factors: {factor_summary} | "
        f"{top.classification_trace}"
    )

    return title, rationale, evidence_summary, reasoning_trace


# ─────────────────────────────────────────────────────────────────────────────
# E.4 — Thematic saturation narrative (ecosystem-level)
# ─────────────────────────────────────────────────────────────────────────────

def _build_thematic_saturation_rec(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    cluster_key: str,
    profiles_in_cluster: list[HoldingStrategicProfile],
    all_profiles: list[HoldingStrategicProfile],
    overlays: list[SecurityIntelligenceOverlay],
    now_utc: str,
) -> Optional[PortfolioRecommendation]:
    """Generate a thematic saturation narrative for a high-concentration cluster."""
    cluster_label = _theme_label(cluster_key)
    if len(profiles_in_cluster) < 2:
        return None

    # Compute total portfolio weight in this cluster
    total_pct = sum(p.percent_of_portfolio for p in profiles_in_cluster)
    if total_pct < 10.0:
        return None  # Not significant enough

    # Breakdown by exposure origin
    direct = [p for p in profiles_in_cluster if p.exposure_origin == "DIRECT_INTENTIONAL"]
    etf_thematic = [p for p in profiles_in_cluster if p.exposure_origin == "ETF_THEMATIC"]
    etf_inherited = [p for p in profiles_in_cluster if p.exposure_origin == "ETF_INHERITED"]

    # Build origin breakdown string
    origin_parts: list[str] = []
    if direct:
        pct = sum(p.percent_of_portfolio for p in direct)
        syms = ", ".join(p.symbol for p in sorted(direct, key=lambda p: -p.percent_of_portfolio)[:3])
        origin_parts.append(f"direct intentional: {syms} ({pct:.1f}%)")
    if etf_thematic:
        pct = sum(p.percent_of_portfolio for p in etf_thematic)
        syms = ", ".join(p.symbol for p in sorted(etf_thematic, key=lambda p: -p.percent_of_portfolio)[:3])
        origin_parts.append(f"thematic ETFs: {syms} ({pct:.1f}%)")
    if etf_inherited:
        pct = sum(p.percent_of_portfolio for p in etf_inherited)
        syms = ", ".join(p.symbol for p in sorted(etf_inherited, key=lambda p: -p.percent_of_portfolio)[:2])
        origin_parts.append(f"broad ETF overlap: {syms} ({pct:.1f}%)")

    origin_str = "; ".join(origin_parts)

    # Overlap explanation
    redundant = [p for p in profiles_in_cluster if p.strategic_classification in _TRIM_CLASSIFICATIONS]
    distinct = [p for p in profiles_in_cluster if p.strategic_classification in _RETAIN_CLASSIFICATIONS]

    rationale = (
        f"{cluster_label} concentration is currently {total_pct:.1f}% of portfolio, "
        f"derived from multiple sources: {origin_str}. "
    )

    if distinct:
        distinct_syms = ", ".join(p.symbol for p in distinct[:3])
        rationale += (
            f"Strategically distinct holdings ({distinct_syms}) represent intentional "
            f"concentration with differentiated exposure. "
        )

    if redundant:
        redundant_syms = ", ".join(p.symbol for p in redundant[:4])
        rationale += (
            f"Redundant overlap ({redundant_syms}) adds to {cluster_label} concentration "
            f"without contributing unique strategic value. "
        )

    rationale += (
        f"Total effective {cluster_label} exposure ({total_pct:.1f}%) may exceed "
        f"intended strategic weight."
    )

    evidence_summary = (
        f"Cluster: {cluster_key} | Total exposure: {total_pct:.1f}% | "
        f"Holdings: {len(profiles_in_cluster)} | "
        f"Distinct: {len(distinct)} | Redundant: {len(redundant)} | "
        f"Origins: direct={len(direct)}, ETF-thematic={len(etf_thematic)}, ETF-inherited={len(etf_inherited)}"
    )

    trace = (
        f"Phase E.4 thematic saturation | cluster: {cluster_key} | "
        f"total_pct: {total_pct:.1f}% | syms: {', '.join(p.symbol for p in profiles_in_cluster)}"
    )

    return PortfolioRecommendation(
        recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        recommendation_type="THEMATIC_SATURATION_NARRATIVE",
        priority=3,
        confidence="MEDIUM",
        title=f"{cluster_label} ecosystem: {total_pct:.1f}% total exposure across {len(profiles_in_cluster)} holdings",
        rationale=rationale,
        evidence_summary=evidence_summary,
        affected_node_key=None,
        affected_symbols=tuple(p.symbol for p in profiles_in_cluster),
        drift_pct=None,
        severity="MODERATE" if total_pct >= 20 else "LOW",
        replay_run_ids=(),
        created_at_utc=now_utc,
        rec_state="INFORMATIONAL",
        reasoning_trace=trace,
        card_type="NARRATIVE",
        execution_state="INFORMATIONAL_ONLY",
    )


# ─────────────────────────────────────────────────────────────────────────────
# E.3 — Strategic retain narrative
# ─────────────────────────────────────────────────────────────────────────────

def _generate_retain_narratives(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    profiles: list[HoldingStrategicProfile],
    overlays: list[SecurityIntelligenceOverlay],
    holdings: list[PortfolioHolding],
    now_utc: str,
) -> list[PortfolioRecommendation]:
    """Generate STRATEGIC_RETAIN_NARRATIVE recs for high-conviction holdings.

    E.3: The system communicates strategic preservation logic, not just
    reduction pressure. HIGH_CONVICTION_RETAIN and CORE_COMPOUNDER holdings
    get explicit explanation of WHY they remain critical.
    """
    recs: list[PortfolioRecommendation] = []

    retain = [p for p in profiles if p.strategic_classification in _RETAIN_CLASSIFICATIONS]

    # Phase 7.1 — prefer tier-aware selection when narrative tiers are populated
    ccl = [p for p in retain if p.narrative_tier == "CORE_CONVICTION_LEADER"]
    hca = [p for p in retain if p.narrative_tier == "HIGH_CONVICTION_ANCHOR"]

    if ccl or hca:
        # Core conviction leaders first (by anchor rank), then high-conviction anchors (by trim score)
        ccl_sorted = sorted(ccl, key=lambda p: p.strategic_anchor_rank or 999)
        hca_sorted = sorted(hca, key=lambda p: p.trim_priority_score)
        retain_candidates = (ccl_sorted + hca_sorted)[:3]
    else:
        retain_candidates = sorted(
            retain,
            key=lambda p: (
                # Sort: HIGH_CONVICTION_RETAIN first, then by lowest trim score
                0 if p.strategic_classification == "HIGH_CONVICTION_RETAIN" else
                1 if p.strategic_classification == "CORE_COMPOUNDER" else
                2 if p.strategic_classification == "STRATEGIC_CORE" else 3,
                p.trim_priority_score,
            ),
        )[:3]  # cap to 3 retain narratives

    for p in retain_candidates:
        overlay = _overlay_for(p.symbol, overlays)
        rationale = _build_retain_rationale(p, overlay, holdings)

        # Explain why we tolerate any associated concentration
        concentration_note = ""
        if p.thematic_overlap_clusters:
            cluster_names = " + ".join(_theme_label(c) for c in p.thematic_overlap_clusters[:2])
            concentration_note = (
                f" While {p.symbol} participates in {cluster_names} concentration, "
                f"this position represents intentional, thesis-driven exposure rather than "
                f"incidental overlap — strategic asymmetry is justified by the evidence above."
            )

        full_rationale = rationale + concentration_note

        evidence_summary = (
            f"STI classification: {p.strategic_classification} | "
            f"Trim score: {p.trim_priority_score:.0f}/100 (low = retain) | "
            f"Strategic importance: {p.strategic_importance} | "
            f"Exposure origin: {p.exposure_origin.replace('_', ' ')} | "
            f"Signal: {_signal_str(overlay)} | "
            f"Replay: {_replay_str(overlay)}"
        )

        trace = (
            f"Phase E.3 retain narrative | {p.symbol} | "
            f"classification: {p.strategic_classification} | "
            f"importance: {p.strategic_importance} | "
            f"{p.classification_trace}"
        )

        recs.append(PortfolioRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            recommendation_type="STRATEGIC_RETAIN_NARRATIVE",
            priority=5,
            confidence="HIGH",
            title=f"{p.symbol}: {p.strategic_classification.replace('_', ' ').title()} — retain signal",
            rationale=full_rationale,
            evidence_summary=evidence_summary,
            affected_node_key=None,
            affected_symbols=(p.symbol,),
            drift_pct=None,
            severity="LOW",
            replay_run_ids=(),
            created_at_utc=now_utc,
            rec_state="INFORMATIONAL",
            reasoning_trace=trace,
            card_type="NARRATIVE",
            execution_state="INFORMATIONAL_ONLY",
        ))

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# E.1 / E.5 — Top trim candidate recs (cluster-level)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_top_trim_recs(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    profiles: list[HoldingStrategicProfile],
    overlays: list[SecurityIntelligenceOverlay],
    holdings: list[PortfolioHolding],
    now_utc: str,
) -> list[PortfolioRecommendation]:
    """Generate TOP_TRIM_CANDIDATES recs per thematic cluster (E.5).

    Replaces the Phase D cluster-level STRATEGIC_TRIM_CANDIDATE with
    richer, narrative-first synthesis that explains each candidate.
    """
    recs: list[PortfolioRecommendation] = []

    # Build cluster → trim profiles map
    cluster_profiles: dict[str, list[HoldingStrategicProfile]] = {}
    for p in profiles:
        if p.strategic_classification not in _TRIM_CLASSIFICATIONS:
            continue
        clusters = p.thematic_overlap_clusters if p.thematic_overlap_clusters else ("GENERAL",)
        for c in clusters:
            cluster_profiles.setdefault(c, []).append(p)

    # E.7: deduplicate — a holding already in a cluster doesn't get a duplicate
    seen_primary_symbols: set[str] = set()

    # Sort clusters by top trim score descending (most urgent first)
    sorted_clusters = sorted(
        cluster_profiles.items(),
        key=lambda kv: -max(p.trim_priority_score for p in kv[1]),
    )

    for cluster_key, trim_profiles in sorted_clusters[:4]:
        sorted_trim = sorted(trim_profiles, key=lambda p: -p.trim_priority_score)
        top = sorted_trim[0]

        if top.symbol in seen_primary_symbols:
            continue
        seen_primary_symbols.add(top.symbol)
        for p in sorted_trim[1:3]:
            seen_primary_symbols.add(p.symbol)

        title, rationale, evidence_summary, reasoning_trace = _build_cluster_trim_narrative(
            cluster_key, trim_profiles, profiles, overlays, holdings
        )

        severity, confidence, priority = _severity_from_trim_score(top.trim_priority_score)

        recs.append(PortfolioRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            recommendation_type="TOP_TRIM_CANDIDATES",
            priority=priority,
            confidence=confidence,
            title=title,
            rationale=rationale,
            evidence_summary=evidence_summary,
            affected_node_key=None,
            affected_symbols=tuple(p.symbol for p in sorted_trim[:6]),
            drift_pct=None,
            severity=severity,
            replay_run_ids=(),
            created_at_utc=now_utc,
            rec_state="ACTIVE",
            reasoning_trace=reasoning_trace,
            card_type="ACTION",
            execution_state="EXECUTABLE",
        ))

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# E.1 — Portfolio construction narrative (top-level synthesis)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_portfolio_construction_narrative(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    profiles: list[HoldingStrategicProfile],
    overlays: list[SecurityIntelligenceOverlay],
    holdings: list[PortfolioHolding],
    now_utc: str,
) -> Optional[PortfolioRecommendation]:
    """Generate a single top-level PORTFOLIO_CONSTRUCTION_NARRATIVE rec (E.1, E.2, E.8).

    This is the flagship strategic synthesis — a portfolio-wide readable
    narrative that answers: what does this portfolio look like strategically,
    what are the key tensions, and what are the most actionable opportunities?
    """
    if not profiles:
        return None

    total = len(profiles)
    retain = [p for p in profiles if p.strategic_classification in _RETAIN_CLASSIFICATIONS]
    trim = [p for p in profiles if p.strategic_classification in _TRIM_CLASSIFICATIONS]
    tactical = [p for p in profiles if p.strategic_classification in _TACTICAL_CLASSIFICATIONS]

    top_retain = sorted(retain, key=lambda p: p.trim_priority_score)[:3]
    top_trim = sorted(trim, key=lambda p: -p.trim_priority_score)[:3]

    # Phase 7.1 — tier-aware selections (populated by build_strategic_profiles)
    ccl = sorted(
        [p for p in profiles if p.narrative_tier == "CORE_CONVICTION_LEADER"],
        key=lambda p: p.strategic_anchor_rank or 999,
    )
    hca = sorted(
        [p for p in profiles if p.narrative_tier == "HIGH_CONVICTION_ANCHOR"],
        key=lambda p: p.trim_priority_score,
    )
    watch_trim = sorted(
        [p for p in profiles if p.narrative_tier == "WATCH_TRIM_CANDIDATE"],
        key=lambda p: -p.trim_priority_score,
    )

    # Portfolio quality summary
    retain_pct = sum(p.percent_of_portfolio for p in retain)
    trim_pct = sum(p.percent_of_portfolio for p in trim)
    mean_trim_score = sum(p.trim_priority_score for p in profiles) / total if total > 0 else 0

    # Determine portfolio construction quality tier
    if mean_trim_score < 25 and len(retain) / max(total, 1) >= 0.5:
        quality_tier = "high-conviction, well-constructed"
    elif mean_trim_score < 45:
        quality_tier = "strategically sound with optimization opportunities"
    elif mean_trim_score < 65:
        quality_tier = "moderately concentrated with trim opportunities"
    else:
        quality_tier = "heavily concentrated — strategic review recommended"

    # Build narrative — use tier-aware language when tiers are populated
    if ccl or hca:
        # Phase 7.1 tier-aware narrative
        ccl_names = ", ".join(
            f"{p.symbol} ({p.percent_of_portfolio:.1f}%)" for p in ccl[:4]
        ) if ccl else "none identified"
        hca_names = ", ".join(
            f"{p.symbol} (trim={p.trim_priority_score:.0f})" for p in hca[:4]
        ) if hca else "none identified"
        watch_names = ", ".join(p.symbol for p in watch_trim[:3]) if watch_trim else "none"

        ccl_replay_note = (
            " — all replay-supported with strong composite signals"
            if all(
                bool(getattr(_overlay_for(p.symbol, overlays), "replay_supported", False))
                for p in ccl[:4]
            ) and ccl
            else ""
        )

        rationale = (
            f"Portfolio is {quality_tier}. "
            f"Core conviction leadership: {ccl_names}{ccl_replay_note}. "
            f"Retain anchors (low trim pressure): {hca_names}. "
        )
        if watch_trim:
            rationale += f"Primary watch/trim risks: {watch_names}. "
    else:
        # Fallback: existing logic for profiles without narrative tiers assigned
        retain_names = ", ".join(p.symbol for p in top_retain)
        rationale = (
            f"Portfolio construction analysis across {total} holdings identifies this as a "
            f"{quality_tier} portfolio. "
            f"Strategic anchors ({retain_pct:.1f}% of portfolio): {retain_names}. "
        )

    trim_names = ", ".join(p.symbol for p in top_trim)

    # In the fallback (non-tier-aware) path, append trim and tactical summaries
    if not (ccl or hca):
        if trim:
            rationale += (
                f"Trim candidates ({trim_pct:.1f}% of portfolio): {trim_names}. "
            )

        if tactical:
            tactical_syms = ", ".join(p.symbol for p in tactical[:3])
            rationale += (
                f"Tactical growth positions ({', '.join(str(round(p.percent_of_portfolio, 1)) + '%' for p in tactical[:3])}): "
                f"{tactical_syms}. "
            )

    # Key recommendations summary (both paths)
    if top_trim:
        top_trim_sym = top_trim[0]
        top_trim_overlay = _overlay_for(top_trim_sym.symbol, overlays)
        rationale += (
            f"Most actionable trim opportunity: {top_trim_sym.symbol} "
            f"(trim score: {top_trim_sym.trim_priority_score:.0f}/100, "
            f"{top_trim_sym.strategic_classification.replace('_', ' ').title()}, "
            f"{_signal_str(top_trim_overlay)}). "
        )

    if top_retain:
        strongest_retain = top_retain[0]
        retain_overlay = _overlay_for(strongest_retain.symbol, overlays)
        rationale += (
            f"Strongest retain signal: {strongest_retain.symbol} "
            f"({strongest_retain.strategic_classification.replace('_', ' ').title()}, "
            f"{_replay_str(retain_overlay)})."
        )

    evidence_summary = (
        f"Holdings analyzed: {total} | "
        f"Retain anchors: {len(retain)} ({retain_pct:.1f}%) | "
        f"Trim candidates: {len(trim)} ({trim_pct:.1f}%) | "
        f"Tactical: {len(tactical)} | "
        f"Mean trim score: {mean_trim_score:.0f}/100"
    )

    trace = (
        f"Phase E.1 portfolio construction | "
        f"total={total} | retain={len(retain)} | trim={len(trim)} | "
        f"mean_trim_score={mean_trim_score:.1f} | quality={quality_tier}"
    )

    # Priority: HIGH urgency only if significant trim pressure
    priority = 1 if mean_trim_score >= 50 else 2

    return PortfolioRecommendation(
        recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        recommendation_type="PORTFOLIO_CONSTRUCTION_NARRATIVE",
        priority=priority,
        confidence="HIGH",
        title=f"Strategic portfolio assessment: {quality_tier}",
        rationale=rationale,
        evidence_summary=evidence_summary,
        affected_node_key=None,
        affected_symbols=tuple(
            p.symbol for p in sorted(profiles, key=lambda p: -p.trim_priority_score)[:8]
        ),
        drift_pct=None,
        severity="MODERATE" if mean_trim_score >= 45 else "LOW",
        replay_run_ids=(),
        created_at_utc=now_utc,
        rec_state="ACTIVE",
        reasoning_trace=trace,
        card_type="NARRATIVE",
        execution_state="INFORMATIONAL_ONLY",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7.1 — Part C: Replay alignment explainability rec
# ─────────────────────────────────────────────────────────────────────────────

def _generate_replay_alignment_context(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    multi_dim_score: Optional[object],
    now_utc: str,
) -> Optional[PortfolioRecommendation]:
    """Generate a REPLAY_ALIGNMENT_CONTEXT rec explaining the score components.

    Explicitly surfaces: coverage component (0–60), quality component (0–40),
    and an explanation when quality=0 due to missing percentile data.
    """
    if multi_dim_score is None:
        return None

    total = float(getattr(multi_dim_score, "replay_alignment_score", 0.0) or 0.0)
    components = tuple(getattr(multi_dim_score, "replay_alignment_components", ()) or ())

    # Extract coverage and quality components by name
    cov_score = 0.0
    cov_expl = ""
    qual_score = 0.0
    qual_expl = ""
    for comp in components:
        name = str(getattr(comp, "component_name", "")).lower()
        if "coverage" in name:
            cov_score = float(getattr(comp, "weighted_score", 0.0) or 0.0)
            cov_expl = str(getattr(comp, "explanation", ""))
        elif "quality" in name:
            qual_score = float(getattr(comp, "weighted_score", 0.0) or 0.0)
            qual_expl = str(getattr(comp, "explanation", ""))

    quality_note = (
        "Replay quality component unavailable because replay percentile data is not present."
        if qual_score == 0.0
        else f"Replay quality component: {qual_score:.1f}/40. {qual_expl}"
    )

    rationale = (
        f"Replay alignment score: {total:.1f}/100. "
        f"Coverage component ({cov_score:.1f}/60): {cov_expl} "
        f"{quality_note}"
    )

    return PortfolioRecommendation(
        recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        recommendation_type="REPLAY_ALIGNMENT_CONTEXT",
        priority=6,
        confidence="HIGH",
        title=f"Replay alignment: {total:.1f}/100 (coverage={cov_score:.1f}/60, quality={qual_score:.1f}/40)",
        rationale=rationale,
        evidence_summary=(
            f"Total: {total:.1f} | Coverage: {cov_score:.1f}/60 | Quality: {qual_score:.1f}/40"
        ),
        affected_node_key=None,
        affected_symbols=(),
        drift_pct=None,
        severity="LOW",
        replay_run_ids=(),
        created_at_utc=now_utc,
        rec_state="INFORMATIONAL",
        reasoning_trace="Phase 7.1 Part C replay alignment explainability",
        card_type="EXPLAINABILITY",
        execution_state="INFORMATIONAL_ONLY",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7.1 — Part D: Conviction explainability cards
# ─────────────────────────────────────────────────────────────────────────────

def _generate_conviction_explainability_cards(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    profiles: list[HoldingStrategicProfile],
    overlays: list[SecurityIntelligenceOverlay],
    now_utc: str,
    top_n: int = 20,
) -> list[PortfolioRecommendation]:
    """Generate CONVICTION_EXPLAINABILITY_CARD recs for top N holdings by composite score.

    Each card answers: why classified this way, why not upgraded, what would upgrade
    or downgrade the classification.  This is Part D of Phase 7.1.
    """
    recs: list[PortfolioRecommendation] = []

    # Sort by composite score desc (overlay-based), tie-break by anchor rank
    def _composite(p: HoldingStrategicProfile) -> float:
        overlay = _overlay_for(p.symbol, overlays)
        return float(getattr(overlay, "composite_score", None) or 0.0)

    sorted_profiles = sorted(
        profiles,
        key=lambda p: (-_composite(p), p.strategic_anchor_rank or 999),
    )[:top_n]

    for p in sorted_profiles:
        overlay = _overlay_for(p.symbol, overlays)
        composite = _composite(p)
        signal = str(getattr(overlay, "signal_direction", "UNKNOWN") or "UNKNOWN")
        replay = bool(getattr(overlay, "replay_supported", False))
        ess = str(getattr(overlay, "ess_score_text", "") or "")
        tier = p.narrative_tier or "—"

        # Why classified this way
        why_classified = (
            f"{p.symbol} is {p.strategic_classification.replace('_', ' ').title()} "
            f"because: signal={signal}, replay_supported={replay}, "
            f"trim_score={p.trim_priority_score:.0f}/100, "
            f"thematic_redundancy={p.thematic_redundancy_score:.0f}/100, "
            f"strategic_importance={p.strategic_importance}. "
            f"Classification trace: {p.classification_trace}"
        )

        # Why not upgraded
        if p.strategic_classification == "HIGH_CONVICTION_RETAIN":
            upgrade_path = (
                f"{p.symbol} is already at HIGH_CONVICTION_RETAIN. "
                f"Narrative tier is {tier}. "
                f"To reach CORE_CONVICTION_LEADER tier: requires portfolio weight ≥ 1.5% "
                f"(current: {p.percent_of_portfolio:.2f}%) and trim score < 30 "
                f"(current: {p.trim_priority_score:.0f})."
                if p.narrative_tier != "CORE_CONVICTION_LEADER"
                else f"{p.symbol} is a CORE_CONVICTION_LEADER — highest narrative tier."
            )
        elif p.strategic_classification == "TACTICAL_GROWTH":
            missing_gates = []
            if signal != "BULLISH":
                missing_gates.append(f"signal must be BULLISH (current: {signal})")
            if not replay:
                missing_gates.append("replay support required (no replay data available)")
            if p.thematic_redundancy_score >= 35:
                missing_gates.append(f"thematic redundancy must be < 35 (current: {p.thematic_redundancy_score:.0f})")
            if p.trim_priority_score >= 30:
                missing_gates.append(f"trim score must be < 30 (current: {p.trim_priority_score:.0f})")
            upgrade_path = (
                f"To upgrade {p.symbol} to HIGH_CONVICTION_RETAIN: "
                + (", ".join(missing_gates) if missing_gates else "all gates already met — reclassification may occur next run")
                + "."
            )
        elif p.strategic_classification in _TRIM_CLASSIFICATIONS:
            upgrade_path = (
                f"To remove {p.symbol} from trim consideration: trim_score must fall below 30 "
                f"(current: {p.trim_priority_score:.0f}), signal must be BULLISH (current: {signal}), "
                f"and thematic redundancy must be below threshold (current: {p.thematic_redundancy_score:.0f})."
            )
        else:
            upgrade_path = (
                f"{p.symbol} classification ({p.strategic_classification}) is stable. "
                f"Downgrade risk: trim_score rising above 30, signal weakening, or thematic redundancy increasing."
            )

        # Downgrade risk
        downgrade_risk = (
            f"Downgrade risk for {p.symbol}: "
            f"trim_score rising above 30 would trigger TACTICAL_GROWTH reclassification; "
            f"signal shifting to NEUTRAL/BEARISH would remove BULLISH gate; "
            f"thematic redundancy above 35 would flag overlap-based trim."
            if p.strategic_classification in _RETAIN_CLASSIFICATIONS
            else f"Escalation risk: trim_score above 60 would trigger REDUCIBLE classification."
        )

        evidence = (
            f"Composite: {composite:.3f} | STI: {p.strategic_classification} | "
            f"Tier: {tier} | Anchor rank: {p.strategic_anchor_rank} | "
            f"Trim: {p.trim_priority_score:.0f} | Signal: {signal} | "
            f"Replay: {replay} | ESS: {ess} | Weight: {p.percent_of_portfolio:.2f}%"
        )

        recs.append(PortfolioRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            recommendation_type="CONVICTION_EXPLAINABILITY_CARD",
            priority=7,
            confidence="HIGH",
            title=f"{p.symbol}: {p.strategic_classification.replace('_', ' ').title()} | tier={tier} | composite={composite:.3f}",
            rationale=f"{why_classified}\n\n{upgrade_path}\n\n{downgrade_risk}",
            evidence_summary=evidence,
            affected_node_key=None,
            affected_symbols=(p.symbol,),
            drift_pct=None,
            severity="LOW",
            replay_run_ids=(),
            created_at_utc=now_utc,
            rec_state="INFORMATIONAL",
            reasoning_trace=f"Phase 7.1 Part D | {p.symbol} | {p.strategic_classification}",
            card_type="EXPLAINABILITY",
            execution_state="INFORMATIONAL_ONLY",
        ))

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# E.6 — Recommendation prioritization pass
# ─────────────────────────────────────────────────────────────────────────────

_REC_TYPE_BASE_PRIORITY: dict[str, int] = {
    "PORTFOLIO_CONSTRUCTION_NARRATIVE":  1,
    "TOP_TRIM_CANDIDATES":               2,
    "THEMATIC_SATURATION_NARRATIVE":     3,
    "STRATEGIC_RETAIN_NARRATIVE":        5,
    "CONCENTRATION_ECOSYSTEM":           2,
    "REPLAY_ALIGNMENT_CONTEXT":          6,
    "CONVICTION_EXPLAINABILITY_CARD":    7,
    # Legacy types
    "REDUCE_OVERWEIGHT":                 2,
    "DIVERSIFY_CONCENTRATION":           1,
    "INCREASE_UNDERWEIGHT":              3,
    "IMPROVE_REPLAY_ALIGNMENT":          3,
    "IMPROVE_SECTOR_EXPOSURE":           3,
    "IMPROVE_RISK_PROFILE":              3,
    "STRATEGIC_TRIM_CANDIDATE":          2,
    "STRATEGIC_RETAIN_SIGNAL":           5,
}

_SEV_ORDER = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "NONE": 3}
_STATE_ORDER = {"ACTIVE": 0, "DOWNGRADED": 1, "INFORMATIONAL": 2, "SUPPRESSED": 3}


def _prioritize_recs(
    recs: list[PortfolioRecommendation],
) -> list[PortfolioRecommendation]:
    """E.6 — Prioritize recommendations using a composite sort key.

    Sort key: (state_rank, priority, severity_rank)
    Phase E narrative recs have base priorities that ensure:
      - PORTFOLIO_CONSTRUCTION_NARRATIVE appears near the top
      - TOP_TRIM_CANDIDATES appear before thematic narratives
      - RETAIN_NARRATIVE recs appear last (informational context)
    """
    def _sort_key(r: PortfolioRecommendation) -> tuple:
        state_rank = _STATE_ORDER.get(r.rec_state, 2)
        sev_rank = _SEV_ORDER.get(r.severity, 3)
        base_p = _REC_TYPE_BASE_PRIORITY.get(r.recommendation_type, r.priority)
        return (state_rank, min(r.priority, base_p), sev_rank)

    return sorted(recs, key=_sort_key)


# ─────────────────────────────────────────────────────────────────────────────
# E.7 — Deduplication pass
# ─────────────────────────────────────────────────────────────────────────────

def _deduplicate_recs(
    recs: list[PortfolioRecommendation],
) -> list[PortfolioRecommendation]:
    """E.7 — Suppress legacy Phase C/D recs that are subsumed by Phase E synthesis.

    The hierarchy-collapse in Phase C already handles parent/child allocation
    recs. This pass additionally suppresses:
      - Legacy STRATEGIC_TRIM_CANDIDATE recs when TOP_TRIM_CANDIDATES covers
        the same primary symbol
      - Legacy STRATEGIC_RETAIN_SIGNAL recs when STRATEGIC_RETAIN_NARRATIVE
        covers the same symbol
      - Legacy thematic IMPROVE_SECTOR_EXPOSURE when THEMATIC_SATURATION_NARRATIVE exists
    """
    # Gather what Phase E synthesized
    phase_e_trim_symbols: set[str] = set()
    phase_e_retain_symbols: set[str] = set()
    has_thematic_narrative = False

    for r in recs:
        if r.recommendation_type == "TOP_TRIM_CANDIDATES":
            phase_e_trim_symbols.update(r.affected_symbols)
        elif r.recommendation_type == "STRATEGIC_RETAIN_NARRATIVE":
            phase_e_retain_symbols.update(r.affected_symbols)
        elif r.recommendation_type == "THEMATIC_SATURATION_NARRATIVE":
            has_thematic_narrative = True

    result: list[PortfolioRecommendation] = []
    for r in recs:
        # Suppress legacy Phase D trim rec if Phase E covers its primary symbol
        if r.recommendation_type == "STRATEGIC_TRIM_CANDIDATE":
            primary = r.affected_symbols[0] if r.affected_symbols else None
            if primary and primary in phase_e_trim_symbols:
                result.append(replace(r, rec_state="SUPPRESSED",
                    reasoning_trace=f"Superseded by Phase E TOP_TRIM_CANDIDATES synthesis. " + r.reasoning_trace))
                continue

        # Suppress legacy Phase D retain rec if Phase E covers it
        if r.recommendation_type == "STRATEGIC_RETAIN_SIGNAL":
            sym = r.affected_symbols[0] if r.affected_symbols else None
            if sym and sym in phase_e_retain_symbols:
                result.append(replace(r, rec_state="SUPPRESSED",
                    reasoning_trace=f"Superseded by Phase E STRATEGIC_RETAIN_NARRATIVE. " + r.reasoning_trace))
                continue

        # Suppress legacy thematic IMPROVE_SECTOR_EXPOSURE if Phase E has saturation narrative
        if r.recommendation_type == "IMPROVE_SECTOR_EXPOSURE" and has_thematic_narrative:
            result.append(replace(r, rec_state="SUPPRESSED",
                reasoning_trace="Superseded by Phase E THEMATIC_SATURATION_NARRATIVE. " + r.reasoning_trace))
            continue

        result.append(r)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# E.10 — Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_phase_e_consistency(
    recs: list[PortfolioRecommendation],
    profiles: list[HoldingStrategicProfile],
) -> list[str]:
    """E.10 — Validate Phase E synthesis for contradictions and structural issues.

    WARN-not-fail philosophy. Returns a list of warning strings.
    """
    warnings: list[str] = []

    # 1. Trim/retain conflict: same symbol in both trim and retain recs
    trim_syms: set[str] = set()
    retain_syms: set[str] = set()
    for r in recs:
        if r.rec_state == "SUPPRESSED":
            continue
        if r.recommendation_type in ("TOP_TRIM_CANDIDATES", "STRATEGIC_TRIM_CANDIDATE"):
            trim_syms.update(r.affected_symbols)
        elif r.recommendation_type in ("STRATEGIC_RETAIN_NARRATIVE", "STRATEGIC_RETAIN_SIGNAL"):
            retain_syms.update(r.affected_symbols)

    conflicts = trim_syms & retain_syms
    for sym in conflicts:
        warnings.append(
            f"WARN[phase_e_consistency]: {sym} appears in both trim and retain recommendations."
        )

    # 2. Excessive recommendation count (verbosity guard)
    active_recs = [r for r in recs if r.rec_state in ("ACTIVE", "DOWNGRADED")]
    if len(active_recs) > 12:
        warnings.append(
            f"WARN[phase_e_consistency]: {len(active_recs)} active recommendations generated; "
            f"consider increasing deduplication aggressiveness."
        )

    # 3. Duplicate trim candidate surfacing (same symbol as primary in multiple ACTIVE trim recs)
    trim_primary_symbols: list[str] = []
    for r in recs:
        if r.recommendation_type == "TOP_TRIM_CANDIDATES" and r.rec_state == "ACTIVE":
            if r.affected_symbols:
                trim_primary_symbols.append(r.affected_symbols[0])
    duplicated_primaries = [s for s in trim_primary_symbols if trim_primary_symbols.count(s) > 1]
    for sym in set(duplicated_primaries):
        warnings.append(
            f"WARN[phase_e_consistency]: {sym} is the primary trim candidate in multiple ACTIVE recs."
        )

    # 4. Contradictory narratives: PORTFOLIO_CONSTRUCTION_NARRATIVE quality mismatch
    pcn_recs = [r for r in recs if r.recommendation_type == "PORTFOLIO_CONSTRUCTION_NARRATIVE"]
    if len(pcn_recs) > 1:
        warnings.append(
            "WARN[phase_e_consistency]: Multiple PORTFOLIO_CONSTRUCTION_NARRATIVE recs generated; "
            "only one is expected."
        )

    # 5. CRITICAL holding appears as primary trim candidate
    profile_map = {p.symbol: p for p in profiles}
    for r in recs:
        if r.recommendation_type == "TOP_TRIM_CANDIDATES" and r.rec_state == "ACTIVE":
            if r.affected_symbols:
                primary = r.affected_symbols[0]
                p = profile_map.get(primary)
                if p and p.strategic_importance == "CRITICAL":
                    warnings.append(
                        f"WARN[phase_e_consistency]: CRITICAL holding {primary} is primary "
                        f"trim candidate in TOP_TRIM_CANDIDATES rec."
                    )

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Phase E main entry point
# ─────────────────────────────────────────────────────────────────────────────

def synthesize_phase_e_recommendations(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    profiles: list[HoldingStrategicProfile],
    overlays: list[SecurityIntelligenceOverlay],
    holdings: list[PortfolioHolding],
    existing_recs: list[PortfolioRecommendation],
    now_utc: Optional[str] = None,
    multi_dim_score: Optional[object] = None,
) -> tuple[list[PortfolioRecommendation], list[str]]:
    """Phase E entry point — synthesize strategic recommendations.

    Takes existing recs from Phase C/D and enriches them with Phase E
    strategic narratives. Returns (final_recs, phase_e_warnings).

    Strategy:
      1. Generate Phase E narrative recs
      2. Merge with existing recs
      3. Deduplicate (suppress Phase D recs subsumed by Phase E)
      4. Prioritize
      5. Validate

    Args:
        multi_dim_score: Optional MultiDimensionalScore — when provided, adds a
            REPLAY_ALIGNMENT_CONTEXT rec explaining coverage and quality components.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc).isoformat()

    if not profiles:
        return existing_recs, []

    phase_e_recs: list[PortfolioRecommendation] = []

    # E.1 — Portfolio construction narrative (top-level synthesis)
    pcn = _generate_portfolio_construction_narrative(
        analysis_run_id, portfolio_snapshot_id, profiles, overlays, holdings, now_utc
    )
    if pcn:
        phase_e_recs.append(pcn)

    # E.5 — Top trim candidates per cluster
    phase_e_recs.extend(_generate_top_trim_recs(
        analysis_run_id, portfolio_snapshot_id, profiles, overlays, holdings, now_utc
    ))

    # E.4 — Thematic saturation narratives
    cluster_profiles: dict[str, list[HoldingStrategicProfile]] = {}
    for p in profiles:
        clusters = p.thematic_overlap_clusters if p.thematic_overlap_clusters else ()
        for c in clusters:
            cluster_profiles.setdefault(c, []).append(p)

    for cluster_key, cluster_plist in sorted(
        cluster_profiles.items(),
        key=lambda kv: -sum(p.percent_of_portfolio for p in kv[1]),
    )[:3]:
        sat_rec = _build_thematic_saturation_rec(
            analysis_run_id, portfolio_snapshot_id,
            cluster_key, cluster_plist, profiles, overlays, now_utc
        )
        if sat_rec:
            phase_e_recs.append(sat_rec)

    # E.3 — Strategic retain narratives
    phase_e_recs.extend(_generate_retain_narratives(
        analysis_run_id, portfolio_snapshot_id, profiles, overlays, holdings, now_utc
    ))

    # Phase 7.1 Part C — Replay alignment explainability
    replay_ctx = _generate_replay_alignment_context(
        analysis_run_id, portfolio_snapshot_id, multi_dim_score, now_utc
    )
    if replay_ctx:
        phase_e_recs.append(replay_ctx)

    # Phase 7.1 Part D — Conviction explainability cards (top 20 by composite)
    phase_e_recs.extend(_generate_conviction_explainability_cards(
        analysis_run_id, portfolio_snapshot_id, profiles, overlays, now_utc
    ))

    # Merge with existing recs
    merged = existing_recs + phase_e_recs

    # E.7 — Deduplication (suppress superseded Phase D recs)
    deduped = _deduplicate_recs(merged)

    # E.6 — Prioritization
    prioritized = _prioritize_recs(deduped)

    # E.10 — Validation
    phase_e_warnings = validate_phase_e_consistency(prioritized, profiles)

    return prioritized, phase_e_warnings
