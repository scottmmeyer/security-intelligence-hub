"""Phase D — Strategic Trim Intelligence (STI).

Evolves SIH from allocation correction into portfolio construction intelligence.

Design principles:
  - DOWNGRADE-FIRST: trim scoring modulates, never blindly overrides strong signals
  - Explainable: every factor has a rationale trace; no black-box scoring
  - Deterministic: config-backed, reproducible, governance-friendly
  - Additive: factors combine transparently; weights are inspectable
  - Growth-oriented: goal is intelligent construction, not simplistic liquidation

Phase D sections:
  D.1 — Strategic holding classification
  D.2 — Trim priority score (additive factor model)
  D.3 — Thematic overlap / cluster analysis
  D.4 — Strategic role preservation
  D.5 — Direct vs derived exposure intelligence
  D.7 — Explainability (trim + retain rationale, classification trace)
  D.9 — Consistency validators
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Optional

from .models import HoldingStrategicProfile, PortfolioHolding


# ─────────────────────────────────────────────────────────────────────────────
# Phase D.4 — Strategic role importance table
# ─────────────────────────────────────────────────────────────────────────────

# Maps strategic_role → structural importance tier.
# Higher importance = harder to trim; a penalty is subtracted from trim score.
_ROLE_IMPORTANCE: dict[str, str] = {
    "CORE_BROAD_US":                   "CRITICAL",   # VOO, IVV — foundational broad market
    "STABILITY_CORE":                  "CRITICAL",   # BND — diversification anchor
    "CASH_EQUIVALENT":                 "HIGH",       # SPAXX — operational liquidity
    "INTERNATIONAL_DIVERSIFICATION":   "HIGH",       # VEA, VXUS — geographic balance
    "AGGRESSIVE_GROWTH_CONCENTRATION": "MEDIUM",     # QQQ — intentional growth bet
    "SECTOR_CONCENTRATION":            "MEDIUM",     # XLK, XLF — deliberate sector tilt
    "SEMICONDUCTOR_CONCENTRATION":     "MEDIUM",     # SMH, SOXX — thematic semiconductor
    "SYSTEMATIC_SMALL_CAP":            "LOW",        # IWM — can trim when overweight
    "SYSTEMATIC_MID_CAP":              "LOW",
    "SYSTEMATIC_MICRO_CAP":            "LOW",
}

# Contribution to trim priority score: negative = penalizes trimming (retain signal)
_ROLE_TRIM_PENALTY: dict[str, float] = {
    "CRITICAL": -25.0,
    "HIGH":     -15.0,
    "MEDIUM":     0.0,
    "LOW":        5.0,   # slightly more trim-eligible when overweight
}


# ─────────────────────────────────────────────────────────────────────────────
# Phase D.5 — Exposure origin classification
# ─────────────────────────────────────────────────────────────────────────────

def _classify_exposure_origin(holding: PortfolioHolding) -> str:
    """Classify whether a holding's exposure is direct/intentional or inherited.

    DIRECT_INTENTIONAL  — stock held directly (thesis-driven alpha bet)
    ETF_THEMATIC        — concentrated ETF with a specific thematic mandate
    ETF_INHERITED       — broad index fund; exposure is incidental, not intentional
    UNKNOWN
    """
    sec = (holding.security_type or "").strip().upper()
    role = (holding.strategic_role or "").strip()

    if sec in ("ETF", "MUTUAL_FUND"):
        if role in {
            "SEMICONDUCTOR_CONCENTRATION",
            "SECTOR_CONCENTRATION",
            "AGGRESSIVE_GROWTH_CONCENTRATION",
        }:
            return "ETF_THEMATIC"
        return "ETF_INHERITED"

    # Common Stock / stock-like holding
    canonical = sec.replace(" ", "_")
    if canonical in ("COMMON_STOCK", "COMMON STOCK") or sec.startswith("COMMON"):
        return "DIRECT_INTENTIONAL"

    # Anything not explicitly a fund — treat as direct
    if sec not in ("ETF", "MUTUAL_FUND", "CASH", "BOND", "FIXED_INCOME"):
        return "DIRECT_INTENTIONAL"

    return "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# Phase D.3 — Thematic overlap / cluster analysis
# ─────────────────────────────────────────────────────────────────────────────

def _build_thematic_cluster_map(
    holdings: list[PortfolioHolding],
) -> dict[str, list[str]]:
    """Return theme → [symbols with nonzero intensity for that theme].

    Used to identify which holdings participate in each thematic cluster.
    """
    clusters: dict[str, list[str]] = {}
    for h in holdings:
        for theme, intensity in h.exposure_thematic_mix:
            if intensity > 0:
                clusters.setdefault(theme, []).append(h.symbol.upper())
    return clusters


def _compute_pairwise_thematic_overlap(
    a: PortfolioHolding,
    b: PortfolioHolding,
) -> float:
    """Weighted Jaccard overlap of thematic exposures between two holdings.

    Returns 0.0–1.0.  Higher = more thematic overlap (more redundant).

    Formula: sum(min(a_intensity, b_intensity)) / sum(max(a_intensity, b_intensity))
    across the union of all themes present in either holding.
    """
    a_map = {theme: intensity for theme, intensity in a.exposure_thematic_mix if intensity > 0}
    b_map = {theme: intensity for theme, intensity in b.exposure_thematic_mix if intensity > 0}

    if not a_map or not b_map:
        return 0.0

    all_themes = set(a_map) | set(b_map)
    numerator = sum(min(a_map.get(t, 0.0), b_map.get(t, 0.0)) for t in all_themes)
    denominator = sum(max(a_map.get(t, 0.0), b_map.get(t, 0.0)) for t in all_themes)
    return round(numerator / denominator, 4) if denominator > 0 else 0.0


def _find_overlap_peers(
    symbol: str,
    holdings: list[PortfolioHolding],
    threshold: float = 0.25,
) -> list[str]:
    """Return symbols sharing significant thematic overlap with `symbol`.

    Sorted by overlap strength descending.
    """
    target = next((h for h in holdings if h.symbol.upper() == symbol.upper()), None)
    if not target or not target.exposure_thematic_mix:
        return []

    scored: list[tuple[str, float]] = []
    for h in holdings:
        if h.symbol.upper() == symbol.upper():
            continue
        overlap = _compute_pairwise_thematic_overlap(target, h)
        if overlap >= threshold:
            scored.append((h.symbol.upper(), overlap))

    scored.sort(key=lambda x: -x[1])
    return [sym for sym, _ in scored]


def _compute_thematic_redundancy_score(
    holding: PortfolioHolding,
    holdings: list[PortfolioHolding],
) -> float:
    """Score 0–100: how redundant is this holding vs. portfolio peers?

    Redundancy = portfolio-weight-adjusted average thematic overlap with all
    other holdings.  Holdings that duplicate exposure in large positions score
    higher than those that overlap only with small positions.

    The raw weighted average (0–1) is amplified × 3.5 to spread the 0–100
    range meaningfully; final result is clamped to 0–100.
    """
    total_weight = 0.0
    weighted_overlap = 0.0

    for h in holdings:
        if h.symbol.upper() == holding.symbol.upper():
            continue
        overlap = _compute_pairwise_thematic_overlap(holding, h)
        peer_weight = max(h.percent_of_portfolio, 0.0) / 100.0
        weighted_overlap += overlap * peer_weight
        total_weight += peer_weight

    if total_weight == 0.0:
        return 0.0

    raw = (weighted_overlap / total_weight) * 100.0
    return round(min(raw * 3.5, 100.0), 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase D.2 — Trim priority score
# ─────────────────────────────────────────────────────────────────────────────

def _compute_trim_priority_score(
    holding: PortfolioHolding,
    overlay,                                 # SecurityIntelligenceOverlay | None
    alignment_map: dict,                     # node_key → AllocationAlignmentResult
    holdings: list[PortfolioHolding],
    thematic_redundancy: float,
    strategic_importance: str,
) -> tuple[float, list[dict], float]:
    """Compute trim priority score + factor breakdown + diversification contribution.

    Returns (trim_score, factors, diversification_contribution).

    Additive factor model (raw sum clamped to 0–100):

      Factor                          Max contribution
      ─────────────────────────────   ────────────────
      concentration_pressure           25 pts
      thematic_overlap                 25 pts
      signal_weakness                  20 pts
      replay_weakness_relative         15 pts
      allocation_pressure              10 pts
      diversification_penalty           5 pts
      strategic_role_importance        -25 pts (penalty / retain signal)
      direct_intentional_ownership      -5 pts (penalty; direct = more intentional)
      ─────────────────────────────   ────────────────
      Raw range                        ~-30 … ~100
      Final (clamped)                    0 … 100

    Higher score = more trim-worthy / more expendable.
    """
    from .alignment import _holding_node_keys  # deferred to avoid circular import

    factors: list[dict] = []
    raw_total = 0.0

    # ── Factor 1: Concentration Pressure (0–25) ────────────────────────────
    # Driven by: number of overweight allocation nodes + absolute portfolio weight
    node_keys = _holding_node_keys(holding)
    overweight_count = sum(
        1
        for nk in node_keys
        if alignment_map.get(nk) is not None
        and getattr(alignment_map[nk], "drift_direction", "") == "OVERWEIGHT"
        and getattr(alignment_map[nk], "severity", "") in ("HIGH", "MODERATE")
    )
    # Weight contribution: each overweight node adds 8pts; large positions add up to 9pts more
    conc_pts = min(25.0, (overweight_count * 8.0) + min(holding.percent_of_portfolio * 0.45, 9.0))
    factors.append({
        "factor": "concentration_pressure",
        "contribution": round(conc_pts, 2),
        "rationale": (
            f"{overweight_count} overweight allocation node(s); "
            f"portfolio weight: {holding.percent_of_portfolio:.1f}%"
        ),
    })
    raw_total += conc_pts

    # ── Factor 2: Thematic Overlap (0–25) ─────────────────────────────────
    # Directly from redundancy score (0–100) scaled to 0–25
    thematic_pts = round(thematic_redundancy * 0.25, 2)
    factors.append({
        "factor": "thematic_overlap",
        "contribution": thematic_pts,
        "rationale": (
            f"Thematic redundancy: {thematic_redundancy:.0f}/100 "
            "(weighted overlap with portfolio peers)"
        ),
    })
    raw_total += thematic_pts

    # ── Factor 3: Signal Weakness (0–20) ──────────────────────────────────
    signal = (
        (getattr(overlay, "signal_direction", None) or "UNKNOWN").upper()
        if overlay else "UNKNOWN"
    )
    score = getattr(overlay, "composite_score", None) if overlay else None

    _SIG_PTS: dict[str, float] = {"BEARISH": 20.0, "UNKNOWN": 12.0, "NEUTRAL": 7.0, "BULLISH": 0.0}
    sig_pts = _SIG_PTS.get(signal, 12.0)

    # Strong score reduces the signal-weakness contribution (high conviction softens neutral)
    if score is not None and score >= 3.5:
        sig_pts = max(0.0, sig_pts - (score - 3.5) / 1.5 * 8.0)

    sig_pts = round(sig_pts, 2)
    score_str = f"{score:.2f}" if score is not None else "N/A"
    factors.append({
        "factor": "signal_weakness",
        "contribution": sig_pts,
        "rationale": f"Signal: {signal}; composite score: {score_str}",
    })
    raw_total += sig_pts

    # ── Factor 4: Replay Weakness Relative to Peers (0–15) ────────────────
    replay_ok = getattr(overlay, "replay_supported", False) if overlay else False
    replay_pctile = getattr(overlay, "replay_percentile", None) if overlay else None

    if not replay_ok:
        replay_pts = 15.0
    elif replay_pctile is not None and replay_pctile < 25:
        replay_pts = 15.0
    elif replay_pctile is not None and replay_pctile >= 75:
        replay_pts = 0.0
    else:
        replay_pts = 5.0

    pctile_str = f"{replay_pctile:.0f}" if replay_pctile is not None else "N/A"
    factors.append({
        "factor": "replay_weakness_relative",
        "contribution": replay_pts,
        "rationale": (
            f"Replay-supported: {replay_ok}; "
            f"replay percentile: {pctile_str}"
        ),
    })
    raw_total += replay_pts

    # ── Factor 5: Allocation Pressure (0–10) ──────────────────────────────
    alloc_pts = round(min(10.0, overweight_count * 3.5), 2)
    factors.append({
        "factor": "allocation_pressure",
        "contribution": alloc_pts,
        "rationale": f"{overweight_count} overweight allocation tier(s)",
    })
    raw_total += alloc_pts

    # ── Factor 6: Diversification Penalty (0–5) ───────────────────────────
    # Holdings with high thematic redundancy and fund structure contribute less
    # unique diversification to the portfolio.
    sec_type = (holding.security_type or "").strip().upper()

    if sec_type in ("ETF", "MUTUAL_FUND") and thematic_redundancy > 60:
        div_penalty = 5.0
        div_contribution = 20.0
    elif thematic_redundancy > 40:
        div_penalty = 2.5
        div_contribution = 50.0
    else:
        div_penalty = 0.0
        div_contribution = max(0.0, 80.0 - thematic_redundancy * 0.5)

    factors.append({
        "factor": "diversification_penalty",
        "contribution": div_penalty,
        "rationale": (
            f"Estimated diversification contribution: {div_contribution:.0f}/100 "
            "(lower = more redundant vs peers)"
        ),
    })
    raw_total += div_penalty

    # ── Strategic Role Importance Adjustment ──────────────────────────────
    role_penalty = _ROLE_TRIM_PENALTY.get(strategic_importance, 0.0)
    if role_penalty != 0.0:
        role_label = holding.strategic_role or "unclassified"
        factors.append({
            "factor": "strategic_role_importance",
            "contribution": role_penalty,  # negative = reduces trim score (retain signal)
            "rationale": (
                f"Strategic importance: {strategic_importance} "
                f"({role_label})"
            ),
        })
        raw_total += role_penalty

    # ── Direct vs Derived Ownership ───────────────────────────────────────
    origin = _classify_exposure_origin(holding)
    if origin == "DIRECT_INTENTIONAL":
        # Direct stock ownership reflects intentional conviction — trim penalty
        factors.append({
            "factor": "direct_intentional_ownership",
            "contribution": -5.0,
            "rationale": (
                "Direct stock ownership represents intentional alpha conviction; "
                "trim priority reduced vs passive ETF-inherited exposure"
            ),
        })
        raw_total -= 5.0

    final_score = round(max(0.0, min(100.0, raw_total)), 2)
    return final_score, factors, round(div_contribution, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase D.1 — Strategic classification
# ─────────────────────────────────────────────────────────────────────────────

def _classify_holding(
    holding: PortfolioHolding,
    overlay,                         # SecurityIntelligenceOverlay | None
    trim_score: float,
    thematic_redundancy: float,
    overlap_peers: list[str],
    strategic_importance: str,
    exposure_origin: str,
) -> str:
    """Assign a strategic classification to a holding.

    Classification vocabulary:
      HIGH_CONVICTION_RETAIN   Strong signal + replay-backed + low overlap
      CORE_COMPOUNDER          Critical role + healthy signal + low trim score
      STRATEGIC_CORE           Important structural role; preserve
      THEMATIC_LEADER          Top signal within a shared thematic cluster
      TACTICAL_GROWTH          Decent signal but high thematic participation/overlap
      REDUNDANT_EXPOSURE       Low unique contribution; better peers exist
      CONCENTRATION_RISK       High portfolio weight + high concentration
      REDUCIBLE                Highest expendability in its cluster
    """
    signal = (
        (getattr(overlay, "signal_direction", None) or "UNKNOWN").upper()
        if overlay else "UNKNOWN"
    )
    replay_ok = getattr(overlay, "replay_supported", False) if overlay else False

    # ── HIGH_CONVICTION_RETAIN ──────────────────────────────────────────────
    # Strongest signal + replay evidence + low overlap + low trim score
    if (
        signal == "BULLISH"
        and replay_ok
        and thematic_redundancy < 35
        and trim_score < 30
    ):
        return "HIGH_CONVICTION_RETAIN"

    # ── CORE_COMPOUNDER ─────────────────────────────────────────────────────
    # Critical structural role + acceptable signal + low trim score
    if (
        strategic_importance == "CRITICAL"
        and signal in ("BULLISH", "NEUTRAL")
        and trim_score < 40
    ):
        return "CORE_COMPOUNDER"

    # ── STRATEGIC_CORE ──────────────────────────────────────────────────────
    # High structural importance; preserve even with moderate overlap
    if strategic_importance in ("CRITICAL", "HIGH") and trim_score < 45:
        return "STRATEGIC_CORE"

    # ── CONCENTRATION_RISK ──────────────────────────────────────────────────
    # Large position + high redundancy + many peers = structural risk
    if (
        holding.percent_of_portfolio >= 5.0
        and thematic_redundancy > 55
        and len(overlap_peers) >= 3
    ):
        return "CONCENTRATION_RISK"

    # ── REDUCIBLE ───────────────────────────────────────────────────────────
    # High trim score + weak/neutral signal
    if trim_score >= 60 and signal in ("BEARISH", "UNKNOWN", "NEUTRAL"):
        return "REDUCIBLE"

    # ── REDUNDANT_EXPOSURE ──────────────────────────────────────────────────
    # Moderate-high overlap + multiple better-positioned peers
    if thematic_redundancy > 50 and len(overlap_peers) >= 2 and signal != "BULLISH":
        return "REDUNDANT_EXPOSURE"

    # ── THEMATIC_LEADER ─────────────────────────────────────────────────────
    # Strong signal within a shared thematic cluster
    # (leads the cluster; represents intentional thematic conviction)
    if signal == "BULLISH" and len(overlap_peers) >= 1 and thematic_redundancy > 20:
        return "THEMATIC_LEADER"

    # ── TACTICAL_GROWTH ─────────────────────────────────────────────────────
    # Decent signal but participates in shared thematic exposure
    if signal in ("BULLISH", "NEUTRAL") and thematic_redundancy > 25:
        return "TACTICAL_GROWTH"

    # ── Fallback by importance ──────────────────────────────────────────────
    if strategic_importance in ("CRITICAL", "HIGH"):
        return "STRATEGIC_CORE"

    return "TACTICAL_GROWTH"


# ─────────────────────────────────────────────────────────────────────────────
# Phase D.7 — Explainability
# ─────────────────────────────────────────────────────────────────────────────

def _build_trim_rationale(
    holding: PortfolioHolding,
    classification: str,
    trim_score: float,
    factors: list[dict],
    overlap_peers: list[str],
    thematic_redundancy: float,
    strategic_importance: str,
    exposure_origin: str,
) -> tuple[str, str, str]:
    """Build (trim_rationale, retain_rationale, classification_trace).

    trim_rationale    — plain-English: WHY this holding ranks where it does
    retain_rationale  — plain-English: WHY to keep it if not trimming
    classification_trace — step-by-step classification reasoning (one line)
    """
    sym = holding.symbol.upper()

    # Top positive-contribution drivers (sorted by pts desc)
    drivers = sorted(
        [
            (f["factor"], f["contribution"])
            for f in factors
            if f["contribution"] > 0
        ],
        key=lambda x: -x[1],
    )
    top_drivers = drivers[:3]
    driver_text = "; ".join(
        f"{f.replace('_', ' ')}: +{c:.1f}pts" for f, c in top_drivers
    ) if top_drivers else "multiple small factors"

    peer_text = (
        f" Overlapping peers: {', '.join(overlap_peers[:4])}." if overlap_peers else ""
    )

    # Trim rationale
    if classification in ("REDUCIBLE", "REDUNDANT_EXPOSURE", "CONCENTRATION_RISK"):
        trim_rationale = (
            f"Trim priority elevated (score: {trim_score:.0f}/100). "
            f"Primary drivers: {driver_text}.{peer_text}"
        )
    elif classification == "TACTICAL_GROWTH":
        trim_rationale = (
            f"Moderate trim priority (score: {trim_score:.0f}/100). "
            f"Participates in shared thematic exposure"
            + (f" with {', '.join(overlap_peers[:3])}" if overlap_peers else "")
            + ". Review if cluster becomes overconcentrated."
        )
    elif classification in ("CORE_COMPOUNDER", "STRATEGIC_CORE", "HIGH_CONVICTION_RETAIN"):
        trim_rationale = (
            f"Low trim priority ({trim_score:.0f}/100). "
            f"Strategic importance ({strategic_importance}) and signal quality favor retention."
        )
    elif classification == "THEMATIC_LEADER":
        trim_rationale = (
            f"Leads its thematic cluster (score: {trim_score:.0f}/100). "
            f"If trimming thematic exposure, trim peers before {sym}."
        )
    else:
        trim_rationale = f"Trim priority score: {trim_score:.0f}/100. {driver_text}."

    # Retain rationale
    retain_signals: list[str] = []
    if strategic_importance in ("CRITICAL", "HIGH"):
        retain_signals.append(f"strategic importance: {strategic_importance}")
    if thematic_redundancy < 30:
        retain_signals.append("low thematic overlap with portfolio peers")
    if exposure_origin == "DIRECT_INTENTIONAL":
        retain_signals.append("direct ownership reflects intentional conviction")
    if classification in ("HIGH_CONVICTION_RETAIN", "CORE_COMPOUNDER", "STRATEGIC_CORE"):
        retain_signals.append(f"classified {classification}")

    if retain_signals:
        retain_rationale = f"Retain signal for {sym}: " + "; ".join(retain_signals) + "."
    else:
        retain_rationale = (
            f"No strong structural retain signal for {sym}. "
            "Evaluate relative to portfolio construction goals."
        )

    # Classification trace (single line; operational explainability)
    classification_trace = (
        f"class={classification} | "
        f"trim={trim_score:.0f}/100 | "
        f"importance={strategic_importance} | "
        f"origin={exposure_origin} | "
        f"redundancy={thematic_redundancy:.0f}/100 | "
        f"peers={len(overlap_peers)}"
    )

    return trim_rationale, retain_rationale, classification_trace


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7.1 — Narrative tier and strategic anchor ranking
# ─────────────────────────────────────────────────────────────────────────────

_RETAIN_CLASSIFICATIONS_FOR_TIER = frozenset({
    "HIGH_CONVICTION_RETAIN",
    "CORE_COMPOUNDER",
    "STRATEGIC_CORE",
    "THEMATIC_LEADER",
})

_TRIM_CLASSIFICATIONS_FOR_TIER = frozenset({
    "REDUCIBLE",
    "REDUNDANT_EXPOSURE",
    "CONCENTRATION_RISK",
})

_ESS_TIER_BONUS: dict[str, float] = {
    "VERY_BULLISH":      10.0,
    "STRONG_BULLISH":    10.0,
    "BULLISH":            6.0,
    "MODERATELY_BULLISH": 6.0,
    "NEUTRAL":            2.0,
}


def _compute_anchor_score(
    profile: HoldingStrategicProfile,
    overlay: Optional[object],
) -> float:
    """Compute a narrative anchor score for ranking conviction strength.

    Higher score = stronger conviction anchor.  Used only for narrative
    tier assignment and strategic_anchor_rank; does not affect STI
    classification or trim_priority_score.

    Components:
      Composite signal  (0–30 pts): composite_score × 6.0
      Replay support    (0–20 pts): +20 if replay_supported
      Portfolio weight  (0–15 pts): min(pct × 2.5, 15)
      ESS strength      (0–10 pts): text-based ESS rating
      Retain bonus      (0–5 pts):  +5 if STI retain classification
      Trim penalty      (0–−20 pts): −trim_score × 0.2
      Diversification   (0–5 pts):  diversification_contribution / 20
    """
    composite = float(getattr(overlay, "composite_score", None) or 0.0)
    replay = bool(getattr(overlay, "replay_supported", False))
    ess_text = str(getattr(overlay, "ess_score_text", "") or "").upper()

    score = min(composite * 6.0, 30.0)
    score += 20.0 if replay else 0.0
    score += min(profile.percent_of_portfolio * 2.5, 15.0)
    score += _ESS_TIER_BONUS.get(ess_text, 0.0)
    if profile.strategic_classification in _RETAIN_CLASSIFICATIONS_FOR_TIER:
        score += 5.0
    score -= min(profile.trim_priority_score * 0.2, 20.0)
    score += min(profile.diversification_contribution / 20.0, 5.0)
    return round(score, 3)


def _assign_narrative_tiers(
    profiles: list[HoldingStrategicProfile],
    overlay_by_sym: dict[str, object],
) -> list[HoldingStrategicProfile]:
    """Assign narrative_tier and strategic_anchor_rank to each profile.

    Tiers (additive to STI classification, not replacing it):
      CORE_CONVICTION_LEADER    — BULLISH + replay + composite ≥ 4.0 + weight ≥ 1.5%
      HIGH_CONVICTION_ANCHOR    — HCR classification, smaller but strong signal
      TACTICAL_GROWTH_CANDIDATE — all other non-trim holdings
      WATCH_TRIM_CANDIDATE      — trim classifications (REDUCIBLE, CONCENTRATION_RISK, etc.)

    strategic_anchor_rank: 1 = highest anchor_score globally; tied by score then symbol.
    """
    # 1. Compute anchor scores for all profiles
    anchor_scores: dict[str, float] = {
        p.symbol: _compute_anchor_score(p, overlay_by_sym.get(p.symbol))
        for p in profiles
    }

    # 2. Determine tier for each profile
    def _tier_for(p: HoldingStrategicProfile) -> str:
        if p.strategic_classification in _TRIM_CLASSIFICATIONS_FOR_TIER:
            return "WATCH_TRIM_CANDIDATE"
        overlay = overlay_by_sym.get(p.symbol)
        signal = str(getattr(overlay, "signal_direction", "") or "").upper()
        replay = bool(getattr(overlay, "replay_supported", False))
        composite = float(getattr(overlay, "composite_score", None) or 0.0)
        is_ccl = (
            signal == "BULLISH"
            and replay
            and composite >= 4.0
            and p.percent_of_portfolio >= 1.5
            and p.trim_priority_score < 30.0
        )
        if is_ccl:
            return "CORE_CONVICTION_LEADER"
        if p.strategic_classification == "HIGH_CONVICTION_RETAIN":
            return "HIGH_CONVICTION_ANCHOR"
        return "TACTICAL_GROWTH_CANDIDATE"

    tier_map: dict[str, str] = {p.symbol: _tier_for(p) for p in profiles}

    # 3. Global rank by anchor_score descending (ties broken by symbol for determinism)
    ranked = sorted(profiles, key=lambda p: (-anchor_scores[p.symbol], p.symbol))
    rank_map: dict[str, int] = {p.symbol: i + 1 for i, p in enumerate(ranked)}

    # 4. Rebuild profiles with new fields (frozen dataclass → use dataclasses.replace)
    return [
        dataclasses.replace(
            p,
            narrative_tier=tier_map[p.symbol],
            strategic_anchor_rank=rank_map[p.symbol],
        )
        for p in profiles
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_strategic_profiles(
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    overlays: list,
    alignment_results: list,
) -> list[HoldingStrategicProfile]:
    """Build Strategic Trim Intelligence profiles for all portfolio holdings.

    Args:
        portfolio_snapshot_id:  snapshot ID for lineage
        holdings:               enriched PortfolioHolding list
        overlays:               SecurityIntelligenceOverlay list
        alignment_results:      AllocationAlignmentResult list

    Returns list of HoldingStrategicProfile, sorted by trim_priority_score
    descending (highest expendability first).
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    # Build fast lookup maps
    overlay_by_sym: dict[str, object] = {
        (getattr(o, "symbol", "") or "").upper(): o
        for o in overlays
    }
    alignment_map: dict[str, object] = {
        (getattr(ar, "node_key", "") or ""): ar
        for ar in alignment_results
    }

    # Phase D.3 — thematic cluster map (theme → [symbols])
    cluster_map = _build_thematic_cluster_map(holdings)

    profiles: list[HoldingStrategicProfile] = []

    for h in holdings:
        sym = h.symbol.upper()
        overlay = overlay_by_sym.get(sym)

        # D.5 — Exposure origin
        exposure_origin = _classify_exposure_origin(h)

        # D.3 — Thematic overlap
        thematic_redundancy = _compute_thematic_redundancy_score(h, holdings)
        overlap_peers = _find_overlap_peers(sym, holdings)
        thematic_overlap_clusters = tuple(
            theme
            for theme, syms in cluster_map.items()
            if sym in syms
        )

        # D.4 — Strategic role importance
        role = h.strategic_role or ""
        strategic_importance = _ROLE_IMPORTANCE.get(role, "MEDIUM")

        # D.2 — Trim priority score + factor breakdown + diversification
        trim_score, factors, div_contribution = _compute_trim_priority_score(
            holding=h,
            overlay=overlay,
            alignment_map=alignment_map,
            holdings=holdings,
            thematic_redundancy=thematic_redundancy,
            strategic_importance=strategic_importance,
        )

        # D.1 — Strategic classification
        classification = _classify_holding(
            holding=h,
            overlay=overlay,
            trim_score=trim_score,
            thematic_redundancy=thematic_redundancy,
            overlap_peers=overlap_peers,
            strategic_importance=strategic_importance,
            exposure_origin=exposure_origin,
        )

        # D.7 — Explainability
        trim_rationale, retain_rationale, classification_trace = _build_trim_rationale(
            holding=h,
            classification=classification,
            trim_score=trim_score,
            factors=factors,
            overlap_peers=overlap_peers,
            thematic_redundancy=thematic_redundancy,
            strategic_importance=strategic_importance,
            exposure_origin=exposure_origin,
        )

        # Extract concentration pressure from factors
        conc_pressure = next(
            (f["contribution"] for f in factors if f["factor"] == "concentration_pressure"),
            0.0,
        )

        profiles.append(
            HoldingStrategicProfile(
                portfolio_snapshot_id=portfolio_snapshot_id,
                symbol=sym,
                security_type=h.security_type or "",
                percent_of_portfolio=h.percent_of_portfolio,
                strategic_classification=classification,
                trim_priority_score=trim_score,
                trim_factors=tuple(
                    (f["factor"], f["contribution"], f["rationale"])
                    for f in factors
                ),
                thematic_overlap_clusters=thematic_overlap_clusters,
                overlap_peers=tuple(overlap_peers[:6]),
                thematic_redundancy_score=thematic_redundancy,
                strategic_role=role,
                strategic_importance=strategic_importance,
                exposure_origin=exposure_origin,
                trim_rationale=trim_rationale,
                retain_rationale=retain_rationale,
                classification_trace=classification_trace,
                concentration_pressure=round(conc_pressure, 2),
                diversification_contribution=round(div_contribution, 2),
                created_at_utc=now_utc,
            )
        )

    profiles.sort(key=lambda p: p.trim_priority_score, reverse=True)

    # Phase 7.1 — Assign narrative tiers and strategic anchor ranks
    profiles = _assign_narrative_tiers(profiles, overlay_by_sym)

    return profiles


# ─────────────────────────────────────────────────────────────────────────────
# Phase D.9 — Consistency validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_trim_intelligence_consistency(
    profiles: list[HoldingStrategicProfile],
) -> list[str]:
    """WARN-not-fail-close validators for STI profile consistency.

    Detects contradictory classifications, impossible score combinations,
    and data quality issues.  Returns list of warning strings (empty = all clear).
    """
    warnings: list[str] = []

    seen_syms: set[str] = set()

    for p in profiles:
        # Duplicate symbol check
        if p.symbol in seen_syms:
            warnings.append(
                f"WARN: Duplicate STI profile for {p.symbol} — check holding deduplication"
            )
        seen_syms.add(p.symbol)

        # CORE_COMPOUNDER with very high trim score is contradictory
        if p.strategic_classification == "CORE_COMPOUNDER" and p.trim_priority_score > 65:
            warnings.append(
                f"WARN: {p.symbol} classified CORE_COMPOUNDER but "
                f"trim_priority_score={p.trim_priority_score:.0f} — "
                "review classification thresholds"
            )

        # REDUCIBLE with CRITICAL importance is contradictory
        if (
            p.strategic_classification == "REDUCIBLE"
            and p.strategic_importance == "CRITICAL"
        ):
            warnings.append(
                f"WARN: {p.symbol} classified REDUCIBLE but strategic_importance=CRITICAL — "
                "review STI classification logic"
            )

        # HIGH_CONVICTION_RETAIN with high trim score is contradictory
        if (
            p.strategic_classification == "HIGH_CONVICTION_RETAIN"
            and p.trim_priority_score > 40
        ):
            warnings.append(
                f"WARN: {p.symbol} classified HIGH_CONVICTION_RETAIN but "
                f"trim_priority_score={p.trim_priority_score:.0f} — "
                "verify signal and replay data"
            )

        # Extreme trim score: flag for operational review
        if p.trim_priority_score > 85:
            warnings.append(
                f"WARN: {p.symbol} has very high trim_priority_score={p.trim_priority_score:.0f}/100 — "
                "verify concentration and overlap factors are correctly computed"
            )

        # Impossible: trim_priority_score outside [0, 100]
        if not (0.0 <= p.trim_priority_score <= 100.0):
            warnings.append(
                f"WARN: {p.symbol} has trim_priority_score={p.trim_priority_score:.2f} "
                "outside valid range [0, 100]"
            )

    return warnings
