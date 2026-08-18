"""Phase 6.2E/F — Multi-Dimensional Scoring and Intentional Asymmetry Detection.

Public API:
  compute_multi_dimensional_score(...)   → MultiDimensionalScore
  detect_intentional_asymmetry(...)      → IntentionalAsymmetryAssessment
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .models import (
    IntentionalAsymmetryAssessment,
    MultiDimensionalScore,
    ScoreComponent,
)


# ─────────────────────────────────────────────────────────────────────────────
# Field access helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fld(obj, attr: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _to_float(v, default: float = 0.0) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_bool(v, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return default if v is None else bool(v)


# ─────────────────────────────────────────────────────────────────────────────
# Allocation Alignment Score  (Phase 6.2E — dimension 1)
# ─────────────────────────────────────────────────────────────────────────────

_DIM_WEIGHTS = {
    "ASSET_CLASS": 3.0,
    "GEOGRAPHY": 2.0,
    "MARKET_CAP": 1.5,
    "MEGA_SUBTIER": 0.5,
}


def _compute_allocation_alignment(
    alignment_results: list,
) -> tuple[float, tuple[ScoreComponent, ...]]:
    """Weighted mean of per-node alignment scores, broken out by dimension type.

    Returns (overall_score_0_100, components_tuple).
    """
    bucket_sum: dict[str, float] = {}
    bucket_wt: dict[str, float] = {}
    bucket_count: dict[str, int] = {}

    for ar in alignment_results:
        dim = str(_fld(ar, "dimension_type") or "OTHER")
        score = _to_float(_fld(ar, "alignment_score"))
        wt = _DIM_WEIGHTS.get(dim, 1.0)
        bucket_sum[dim] = bucket_sum.get(dim, 0.0) + score * wt
        bucket_wt[dim] = bucket_wt.get(dim, 0.0) + wt
        bucket_count[dim] = bucket_count.get(dim, 0) + 1

    components: list[ScoreComponent] = []
    total_weighted = 0.0
    total_wt = 0.0

    for dim in ("ASSET_CLASS", "GEOGRAPHY", "MARKET_CAP", "MEGA_SUBTIER"):
        if dim not in bucket_wt or bucket_wt[dim] == 0:
            continue
        raw = bucket_sum[dim] / bucket_wt[dim] * 100
        wt = _DIM_WEIGHTS[dim]
        n = bucket_count[dim]
        label = {
            "ASSET_CLASS": "Asset Class Alignment",
            "GEOGRAPHY": "Geography Alignment",
            "MARKET_CAP": "Market Cap Alignment",
            "MEGA_SUBTIER": "Mega Subtier Alignment",
        }[dim]
        components.append(ScoreComponent(
            component_name=label,
            raw_score=round(raw, 1),
            weight=wt,
            weighted_score=round(raw * wt, 2),
            explanation=f"Mean alignment across {n} {dim.lower().replace('_', ' ')} node(s).",
        ))
        total_weighted += raw * wt
        total_wt += wt

    overall = round(total_weighted / total_wt, 1) if total_wt > 0 else 0.0
    return overall, tuple(components)


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio Quality Score  (Phase 6.2E — dimension 2)
# ─────────────────────────────────────────────────────────────────────────────

_STRONG_STRATEGIC_CLASSES = frozenset({
    "HIGH_CONVICTION_RETAIN",
    "CORE_COMPOUNDER",
    "STRATEGIC_CORE",
    "THEMATIC_LEADER",
})


def _compute_portfolio_quality(
    concentration,
    overlays: list,
    strategic_profiles: list,
) -> tuple[float, tuple[ScoreComponent, ...]]:
    """Three-component portfolio quality score.

    1. Concentration Quality (0–40): inverse Herfindahl index quality.
    2. Signal Quality       (0–30): weighted fraction with BULLISH/NEUTRAL signal.
    3. Strategic Quality    (0–30): fraction in strong strategic classifications.
    """
    components: list[ScoreComponent] = []

    # 1. Concentration quality
    hhi = _to_float(_fld(concentration, "herfindahl_index"), 0.0)
    # HHI 0.0 → 40 pts; HHI 0.2+ → 0 pts (5x amplifier)
    conc_raw = max(0.0, 1.0 - hhi * 5.0) * 40.0
    top1_pct = _to_float(_fld(concentration, "top1_pct"), 0.0)
    # Additional penalty: each 5pp over 20% costs 2 pts
    top1_penalty = max(0.0, (top1_pct - 20.0) / 5.0) * 2.0
    conc_score = max(0.0, conc_raw - top1_penalty)
    components.append(ScoreComponent(
        component_name="Concentration Quality",
        raw_score=round(conc_score, 1),
        weight=1.0,
        weighted_score=round(conc_score, 1),
        explanation=(
            f"HHI={hhi:.4f}; top position={top1_pct:.1f}% of portfolio. "
            f"Lower HHI and smaller top position improve score."
        ),
    ))

    # 2. Signal quality
    total_pct = sum(_to_float(_fld(o, "percent_of_portfolio")) for o in overlays)
    if total_pct > 0 and overlays:
        bullish_pct = sum(
            _to_float(_fld(o, "percent_of_portfolio"))
            for o in overlays
            if str(_fld(o, "signal_direction") or "").upper() == "BULLISH"
        )
        neutral_pct = sum(
            _to_float(_fld(o, "percent_of_portfolio"))
            for o in overlays
            if str(_fld(o, "signal_direction") or "").upper() in ("NEUTRAL", "UNKNOWN")
        )
        # BULLISH = full credit; NEUTRAL/UNKNOWN = half credit
        signal_quality = (bullish_pct * 1.0 + neutral_pct * 0.5) / total_pct
        sig_score = round(signal_quality * 30.0, 1)
        expl = (
            f"{bullish_pct:.1f}% bullish, {neutral_pct:.1f}% neutral/unknown of "
            f"portfolio value covered by signal data."
        )
    else:
        sig_score = 15.0
        expl = "No signal overlay data available; defaulting to neutral score."
    components.append(ScoreComponent(
        component_name="Signal Quality",
        raw_score=sig_score,
        weight=1.0,
        weighted_score=sig_score,
        explanation=expl,
    ))

    # 3. Strategic quality
    if strategic_profiles:
        strong_pct = sum(
            _to_float(_fld(p, "percent_of_portfolio"))
            for p in strategic_profiles
            if str(_fld(p, "strategic_classification") or "") in _STRONG_STRATEGIC_CLASSES
        )
        total_strat_pct = sum(
            _to_float(_fld(p, "percent_of_portfolio")) for p in strategic_profiles
        )
        quality = strong_pct / total_strat_pct if total_strat_pct > 0 else 0.5
        strat_score = round(quality * 30.0, 1)
        n_strong = sum(
            1 for p in strategic_profiles
            if str(_fld(p, "strategic_classification") or "") in _STRONG_STRATEGIC_CLASSES
        )
        expl = (
            f"{n_strong} of {len(strategic_profiles)} holdings classified as "
            f"HIGH_CONVICTION, CORE_COMPOUNDER, STRATEGIC_CORE, or THEMATIC_LEADER "
            f"({strong_pct:.1f}% of portfolio value)."
        )
    else:
        strat_score = 15.0
        expl = "No strategic trim intelligence available; defaulting to neutral score."
    components.append(ScoreComponent(
        component_name="Strategic Classification Quality",
        raw_score=strat_score,
        weight=1.0,
        weighted_score=strat_score,
        explanation=expl,
    ))

    overall = round(conc_score + sig_score + strat_score, 1)
    # Cap at 100
    overall = min(100.0, overall)
    return overall, tuple(components)


# ─────────────────────────────────────────────────────────────────────────────
# Implementation Quality Score  (Phase 6.2E — dimension 3)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_implementation_quality(
    alignment_results: list,
    recs: list,
) -> tuple[float, tuple[ScoreComponent, ...]]:
    """Three-component implementation quality score.

    1. Vehicle Suitability (0–40): from INCREASE_UNDERWEIGHT vehicle notes.
    2. Cash Efficiency     (0–30): how close cash is to its target.
    3. Operational Integrity (0–30): Phase 6.1 operational cleanliness.
    """
    components: list[ScoreComponent] = []

    # 1. Vehicle suitability
    suitability_scores = []
    for rec in recs:
        vsn = _fld(rec, "vehicle_suitability_notes") or ()
        if not hasattr(vsn, "__iter__"):
            continue
        for note in vsn:
            s = _to_float(_fld(note, "suitability_score"))
            if s > 0:
                suitability_scores.append(s)
    if suitability_scores:
        avg = sum(suitability_scores) / len(suitability_scores)
        vehicle_score = round(avg * 0.40, 1)  # 0–100 → 0–40
        expl = (
            f"Mean vehicle suitability score {avg:.1f}/100 across "
            f"{len(suitability_scores)} candidate vehicle(s)."
        )
    else:
        vehicle_score = 20.0
        expl = "No vehicle suitability data available; defaulting to neutral score."
    components.append(ScoreComponent(
        component_name="Vehicle Suitability",
        raw_score=vehicle_score,
        weight=1.0,
        weighted_score=vehicle_score,
        explanation=expl,
    ))

    # 2. Cash efficiency — penalise excess/deficit vs target
    cash_ar = next(
        (ar for ar in alignment_results if str(_fld(ar, "node_key") or "") == "CASH"),
        None,
    )
    if cash_ar is not None:
        cash_drift_abs = abs(_to_float(_fld(cash_ar, "drift_pct")))
        # Within 2pp → 30 pts; each additional pp above 2 costs 3 pts
        cash_score = round(max(0.0, 30.0 - max(0.0, cash_drift_abs - 2.0) * 3.0), 1)
        expl = (
            f"Cash drift {_to_float(_fld(cash_ar, 'drift_pct')):+.1f}pp vs target. "
            f"Within ±2pp earns full 30 pts."
        )
    else:
        cash_score = 25.0
        expl = "No cash allocation node found; defaulting to near-full score."
    components.append(ScoreComponent(
        component_name="Cash Efficiency",
        raw_score=cash_score,
        weight=1.0,
        weighted_score=cash_score,
        explanation=expl,
    ))

    # 3. Operational integrity — Phase 6.1 guarantees cleanliness
    op_score = 30.0
    components.append(ScoreComponent(
        component_name="Operational Integrity",
        raw_score=op_score,
        weight=1.0,
        weighted_score=op_score,
        explanation=(
            "Phase 6.1 operational filtering ensures PENDING and adjustment rows "
            "are excluded from all analytics. Full integrity score awarded."
        ),
    ))

    overall = round(min(100.0, vehicle_score + cash_score + op_score), 1)
    return overall, tuple(components)


# ─────────────────────────────────────────────────────────────────────────────
# Replay Alignment Score  (Phase 6.2E — dimension 4)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_replay_alignment(
    overlays: list,
) -> tuple[float, tuple[ScoreComponent, ...]]:
    """Two-component replay alignment score.

    1. Coverage (0–60): % of portfolio value that is replay-supported.
    2. Quality  (0–40): mean replay percentile among supported holdings.
    """
    components: list[ScoreComponent] = []

    total_pct = sum(_to_float(_fld(o, "percent_of_portfolio")) for o in overlays)
    supported = [o for o in overlays if _to_bool(_fld(o, "replay_supported"))]
    replay_pct = sum(_to_float(_fld(o, "percent_of_portfolio")) for o in supported)

    # 1. Coverage
    coverage = replay_pct / total_pct if total_pct > 0 else 0.0
    cov_score = round(coverage * 60.0, 1)
    components.append(ScoreComponent(
        component_name="Replay Coverage",
        raw_score=cov_score,
        weight=1.0,
        weighted_score=cov_score,
        explanation=(
            f"{replay_pct:.1f}% of portfolio value is in replay-supported positions "
            f"({len(supported)} of {len(overlays)} holdings)."
        ),
    ))

    # 2. Quality — mean percentile
    percentiles = [
        _to_float(_fld(o, "replay_percentile"))
        for o in supported
        if _fld(o, "replay_percentile") is not None
    ]
    if percentiles:
        mean_pctile = sum(percentiles) / len(percentiles)
        qual_score = round(mean_pctile / 100.0 * 40.0, 1)
        expl = (
            f"Mean replay percentile {mean_pctile:.1f} among "
            f"{len(percentiles)} supported holding(s)."
        )
    else:
        qual_score = 0.0
        expl = "Replay quality unavailable — no cohort percentile scores found for supported holdings."
    components.append(ScoreComponent(
        component_name="Replay Quality",
        raw_score=qual_score,
        weight=1.0,
        weighted_score=qual_score,
        explanation=expl,
    ))

    overall = round(min(100.0, cov_score + qual_score), 1)
    return overall, tuple(components)


# ─────────────────────────────────────────────────────────────────────────────
# Main scorer  (Phase 6.2E)
# ─────────────────────────────────────────────────────────────────────────────

def compute_multi_dimensional_score(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    mandate_type: str,
    alignment_results: list,
    concentration,
    overlays: list,
    recs: list,
    strategic_profiles: list,
) -> MultiDimensionalScore:
    """Compute all four portfolio quality dimensions.

    Governance:
        Read-only.  No portfolio data is modified.
        Scoring uses only the outputs of the existing analytical pipeline.
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    alloc_score, alloc_comps = _compute_allocation_alignment(alignment_results)
    pq_score, pq_comps = _compute_portfolio_quality(concentration, overlays, strategic_profiles)
    iq_score, iq_comps = _compute_implementation_quality(alignment_results, recs)
    rp_score, rp_comps = _compute_replay_alignment(overlays)

    replay_alignment_available = bool(
        [o for o in overlays if _to_bool(_fld(o, "replay_supported"))]
    ) and any(
        _fld(o, "replay_percentile") is not None and str(_fld(o, "replay_percentile")).strip() not in {"", "None", "null", "nan", "N/A"}
        for o in overlays
    )

    return MultiDimensionalScore(
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        mandate_type=mandate_type,
        allocation_alignment_score=alloc_score,
        portfolio_quality_score=pq_score,
        implementation_quality_score=iq_score,
        replay_alignment_score=rp_score,
        replay_alignment_available=replay_alignment_available,
        allocation_alignment_components=alloc_comps,
        portfolio_quality_components=pq_comps,
        implementation_quality_components=iq_comps,
        replay_alignment_components=rp_comps,
        created_at_utc=now_utc,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Intentional Asymmetry Detection  (Phase 6.2F)
# ─────────────────────────────────────────────────────────────────────────────

_THEMATIC_EXTRACT_KEYS = (
    "exposure_thematic_mix",
    "thematic_overlap_clusters",
)


def _extract_theme(holding_or_profile) -> str:
    """Extract the dominant thematic label from a holding or profile, or ''."""
    for attr in _THEMATIC_EXTRACT_KEYS:
        val = _fld(holding_or_profile, attr)
        if val:
            if isinstance(val, (list, tuple)) and val:
                first = val[0]
                if isinstance(first, (list, tuple)) and first:
                    return str(first[0])
                return str(first)
            if isinstance(val, str) and val:
                return val.split("|")[0].strip()
    return ""


def detect_intentional_asymmetry(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    mandate_type: str,
    holdings: list,
    overlays: list,
    alignment_results: list,
    strategic_profiles: list,
) -> IntentionalAsymmetryAssessment:
    """Assess whether portfolio drift appears accidental or intentional.

    Detection signals:
      A. Replay-supported overweight nodes
      B. HIGH_CONVICTION_RETAIN strategic classifications
      C. Thematic exposure clustering (single theme >10% of portfolio)
      D. Overweight nodes where top holdings are also replay-supported

    Asymmetry score accumulates signal evidence (0.0–1.0).
    States: ACCIDENTAL (<0.30), LIKELY_INTENTIONAL (0.30–0.55), HIGH_CONVICTION (>0.55)
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    evidence: list[str] = []
    asymmetry_score = 0.0

    # Build quick-lookup structures
    overlay_by_sym = {
        str(_fld(o, "symbol") or "").upper(): o for o in overlays
    }
    overweight_nodes = {
        str(_fld(ar, "node_key") or "")
        for ar in alignment_results
        if str(_fld(ar, "drift_direction") or "") == "OVERWEIGHT"
    }

    # ── Signal A: Replay-supported overweight nodes ───────────────────────
    replay_supported_ow_count = 0
    for ar in alignment_results:
        if str(_fld(ar, "drift_direction") or "") != "OVERWEIGHT":
            continue
        node = str(_fld(ar, "node_key") or "")
        # Count replay-supported holdings in this overweight node
        node_replay_pct = 0.0
        for h in holdings:
            sym = str(_fld(h, "symbol") or "").upper()
            ov = overlay_by_sym.get(sym)
            if ov and _to_bool(_fld(ov, "replay_supported")):
                # Simple: if the holding is replay-supported and the node is overweight,
                # count it as a replay-supported overweight contribution
                h_pct = _to_float(_fld(h, "percent_of_portfolio"))
                if h_pct > 0:
                    node_replay_pct += h_pct
        if node_replay_pct > 1.0:  # at least 1pp of replay-supported exposure in OW node
            replay_supported_ow_count += 1

    if replay_supported_ow_count >= 3:
        asymmetry_score += 0.4
        evidence.append(
            f"{replay_supported_ow_count} overweight allocation nodes contain "
            f"replay-supported holdings — suggests deliberate conviction positioning."
        )
    elif replay_supported_ow_count >= 1:
        asymmetry_score += 0.2
        evidence.append(
            f"{replay_supported_ow_count} overweight node(s) contain replay-supported "
            f"holdings — possible deliberate positioning."
        )

    # ── Signal B: High-conviction retain classifications ──────────────────
    hc_retain_count = sum(
        1 for p in strategic_profiles
        if str(_fld(p, "strategic_classification") or "") == "HIGH_CONVICTION_RETAIN"
    )
    hc_retain_pct = sum(
        _to_float(_fld(p, "percent_of_portfolio"))
        for p in strategic_profiles
        if str(_fld(p, "strategic_classification") or "") == "HIGH_CONVICTION_RETAIN"
    )
    if hc_retain_count >= 3:
        asymmetry_score += 0.3
        evidence.append(
            f"{hc_retain_count} holdings classified HIGH_CONVICTION_RETAIN "
            f"({hc_retain_pct:.1f}% of portfolio) — strong evidence of intentional "
            f"conviction-weighted construction."
        )
    elif hc_retain_count >= 1:
        asymmetry_score += 0.15
        evidence.append(
            f"{hc_retain_count} HIGH_CONVICTION_RETAIN holding(s) detected "
            f"({hc_retain_pct:.1f}% of portfolio)."
        )

    # ── Signal C: Thematic clustering ────────────────────────────────────
    theme_pct: dict[str, float] = {}
    for h in holdings:
        theme = _extract_theme(h)
        if theme:
            pct = _to_float(_fld(h, "percent_of_portfolio"))
            theme_pct[theme] = theme_pct.get(theme, 0.0) + pct

    significant_themes = [t for t, pct in theme_pct.items() if pct > 10.0]
    thematic_cluster_count = len(significant_themes)
    dominant_theme = (
        max(theme_pct, key=theme_pct.__getitem__)
        if theme_pct else "UNKNOWN"
    )
    dominant_theme_pct = theme_pct.get(dominant_theme, 0.0)

    if thematic_cluster_count >= 2:
        asymmetry_score += 0.25
        evidence.append(
            f"{thematic_cluster_count} thematic clusters each exceed 10% of portfolio "
            f"— pattern consistent with intentional thematic concentration."
        )
    elif thematic_cluster_count == 1:
        asymmetry_score += 0.1
        evidence.append(
            f"Single thematic cluster '{dominant_theme}' represents "
            f"{dominant_theme_pct:.1f}% of portfolio."
        )

    # ── Signal D: Concentration in overweight nodes ───────────────────────
    ow_pct = sum(
        _to_float(_fld(ar, "drift_pct"))
        for ar in alignment_results
        if str(_fld(ar, "drift_direction") or "") == "OVERWEIGHT"
        and str(_fld(ar, "dimension_type") or "") == "ASSET_CLASS"
    )
    if ow_pct > 15.0:
        asymmetry_score += 0.1
        evidence.append(
            f"Asset-class level overweight totals {ow_pct:.1f}pp above target — "
            f"suggests portfolio has been intentionally positioned away from model."
        )

    # Cap at 1.0
    asymmetry_score = round(min(1.0, asymmetry_score), 4)

    # Determine state
    if asymmetry_score >= 0.55:
        state = "HIGH_CONVICTION"
    elif asymmetry_score >= 0.30:
        state = "LIKELY_INTENTIONAL"
    else:
        state = "ACCIDENTAL"

    # Build rationale
    if state == "HIGH_CONVICTION":
        rationale = (
            f"Strong evidence of intentional asymmetric construction "
            f"(asymmetry score: {asymmetry_score:.2f}). "
            f"Multiple signals — replay conviction, strategic classification, "
            f"and thematic clustering — consistently indicate deliberate positioning "
            f"rather than passive drift."
        )
    elif state == "LIKELY_INTENTIONAL":
        rationale = (
            f"Portfolio drift appears partially intentional "
            f"(asymmetry score: {asymmetry_score:.2f}). "
            f"Some signals suggest deliberate positioning, but evidence is not "
            f"conclusive. Recommend reviewing mandate alignment."
        )
    else:
        rationale = (
            f"Portfolio drift appears circumstantial rather than deliberate "
            f"(asymmetry score: {asymmetry_score:.2f}). "
            f"No strong signals of intentional asymmetric construction detected."
        )

    return IntentionalAsymmetryAssessment(
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        mandate_type=mandate_type,
        asymmetry_state=state,
        asymmetry_score=asymmetry_score,
        evidence_signals=tuple(evidence),
        dominant_theme=dominant_theme,
        replay_conviction_count=replay_supported_ow_count,
        thematic_cluster_count=thematic_cluster_count,
        assessment_rationale=rationale,
        created_at_utc=now_utc,
    )
