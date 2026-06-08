"""Phase F / G / H — Recommendation Engine + Security Intelligence.

Generates prioritized, explainable advisory recommendations by combining:
  - Allocation alignment results (drift, severity)
  - Concentration risk summary
  - Security-level SIH scores (composite, ESS, Zacks)
  - Replay performance evidence

All recommendations are advisory guidance — NOT trade instructions.

Phase C additions:
  - Recommendation state model: ACTIVE / DOWNGRADED / INFORMATIONAL / SUPPRESSED
  - Effective exposure saturation analysis
  - Downgrade-first philosophy: ETF-derived indirect exposure modulates recs,
    never erases intentional direct exposure semantics
  - Hierarchy-aware recommendation collapse (parent/child deduplication)
  - Thematic concentration detection (AI_INFRA, SEMICONDUCTOR, etc.)
  - Reasoning trace: plain-English explainability for every state assignment
  - Recommendation validators
"""

from __future__ import annotations

import csv
import os
import uuid
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from .models import (
    AllocationAlignmentResult,
    ConcentrationRiskSummary,
    FundingSourceAnalysis,
    FundingSourceEntry,
    PortfolioHolding,
    PortfolioRecommendation,
    SecurityIntelligenceOverlay,
)
from .exposure_decomposition import build_holding_exposure_contribs
from .phase_e_synthesis import synthesize_phase_e_recommendations


# ─────────────────────────────────────────────────────────────────────────────
# Replay evidence loader
# ─────────────────────────────────────────────────────────────────────────────

def _load_replay_evidence(
    replay_series_csv: str = "data/current/replay_performance_series.csv",
    replay_inputs_csv: str = "data/current/replay_inputs.csv",
    analytical_universe_csv: str = "data/current/analytical_universe.csv",
) -> dict[str, dict]:
    """Return symbol → {tier, return, replay_id, percentile_approx}.

    We load the final cumulative return for each symbol that appeared in any
    TOP_N_STRATEGY replay to estimate replay-backed performance context.
    This is a lightweight evidence signal — not full scoring.

    Replay evidence routing (Phase 7.4D fix):
    - Cross-sector ALL replays are accepted unconditionally (existing behavior).
    - Industry-specific replays are now also accepted.  The symbol's canonical
      tier (geography / market_cap_bucket / industry) must match the replay's
      filter dimensions; this check is deferred to build_security_overlays()
      where the holding's classification is available.
    - If a symbol appears in both an ALL replay and an industry-specific replay,
      the ALL replay takes priority (first-seen wins).

    Phase 22D.2 — Replay Quality:
    - Computes per-symbol percentile rank within each replay cohort using current
      composite scores from analytical_universe.csv.  Higher composite score =
      higher percentile.  Stored in symbol_percentile and wired to the
      replay_percentile field of SecurityIntelligenceOverlay.
    """
    # Cross-sector ALL replay evidence: symbol → tier key / replay_id
    symbol_tier: dict[str, str] = {}
    symbol_replay: dict[str, str] = {}

    # Industry-specific replay evidence: symbol → {geo, cap, industry, replay_id}
    # Canonical tier compatibility is verified in build_security_overlays().
    industry_replay_evidence: dict[str, dict[str, str]] = {}

    # Per-replay symbol lists (needed for percentile computation below).
    replay_symbols: dict[str, list[str]] = {}

    if os.path.exists(replay_inputs_csv):
        with open(replay_inputs_csv, newline="", encoding="utf-8") as _fh:
            for row in csv.DictReader(_fh):
                cap = row.get("filter_market_cap_bucket", "")
                geo = row.get("filter_geography", "")
                ind = row.get("filter_industry", "").strip().upper()
                replay_id = row.get("replay_id", "")
                syms_raw = row.get("selected_symbols", "").split("|")
                sym_list = [s.strip().upper() for s in syms_raw if s.strip()]
                if replay_id:
                    replay_symbols[replay_id] = sym_list
                for sym in sym_list:
                    if ind == "ALL":
                        # Cross-sector ALL replay — highest priority.
                        if sym not in symbol_tier:
                            symbol_tier[sym] = f"{geo}.{cap}"
                            symbol_replay[sym] = replay_id
                    else:
                        # Industry-specific replay — record dimensions for
                        # downstream tier-compatibility check.  Do not promote
                        # if the symbol is already covered by an ALL replay.
                        if sym not in symbol_tier and sym not in industry_replay_evidence:
                            industry_replay_evidence[sym] = {
                                "geo": geo,
                                "cap": cap,
                                "industry": ind,
                                "replay_id": replay_id,
                            }

    # ── Phase 22D.2: per-symbol percentile within replay cohort ───────────
    # Load current composite scores to rank each symbol within its replay.
    composite_scores: dict[str, float] = {}
    if os.path.exists(analytical_universe_csv):
        with open(analytical_universe_csv, newline="", encoding="utf-8") as _ufh:
            for _urow in csv.DictReader(_ufh):
                _usym = str(_urow.get("symbol", "")).strip().upper()
                _uscr = str(_urow.get("composite_score", "")).strip()
                if _usym and _uscr:
                    try:
                        composite_scores[_usym] = float(_uscr)
                    except ValueError:
                        pass

    symbol_percentile: dict[str, float] = {}
    for rid, sym_list in replay_symbols.items():
        if not sym_list:
            continue
        # Only compute for symbols registered in the primary (ALL) replay path.
        primary_syms = [s for s in sym_list if symbol_replay.get(s) == rid]
        scored = [(s, composite_scores[s]) for s in primary_syms if s in composite_scores]
        if not scored:
            continue
        scored.sort(key=lambda x: x[1])   # ascending → lowest = percentile 0 end
        n = len(scored)
        for rank_idx, (sym, _) in enumerate(scored):
            symbol_percentile[sym] = round((rank_idx + 1) / n * 100.0, 1)

    return {
        "symbol_tier": symbol_tier,
        "symbol_replay": symbol_replay,
        "industry_replay_evidence": industry_replay_evidence,
        "symbol_percentile": symbol_percentile,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Security intelligence overlay (Phase G)
# ─────────────────────────────────────────────────────────────────────────────

def build_security_overlays(
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    alignment_results: list[AllocationAlignmentResult],
) -> list[SecurityIntelligenceOverlay]:
    """Build per-holding intelligence overlays."""
    now_utc = datetime.now(timezone.utc).isoformat()
    replay_ev = _load_replay_evidence()
    symbol_tier = replay_ev["symbol_tier"]
    symbol_replay = replay_ev["symbol_replay"]
    industry_replay_evidence: dict[str, dict[str, str]] = replay_ev.get("industry_replay_evidence", {})
    symbol_percentile: dict[str, float] = replay_ev.get("symbol_percentile", {})

    # ── Phase 22D.2 WS-B: ESS archive fallback ───────────────────────────
    # For symbols whose ESS was absent or suppressed in signal_snapshot.csv
    # (e.g. symbols absent from snapshot or classified NON_STARMINE_ANALYST),
    # fall back to the most recent entry in ess_history_master.csv.
    _ess_archive: dict[str, str] = {}
    _ess_archive_path = "ess_history_master.csv"
    if os.path.exists(_ess_archive_path):
        _ess_latest_dates: dict[str, str] = {}
        with open(_ess_archive_path, newline="", encoding="utf-8") as _efh:
            for _erow in csv.DictReader(_efh):
                _esym = str(_erow.get("symbol", "")).strip().upper()
                _ecat = str(_erow.get("ess_category", "")).strip()
                _edate = str(_erow.get("capture_date", "")).strip()
                if _esym and _ecat and _edate:
                    if _esym not in _ess_latest_dates or _edate > _ess_latest_dates[_esym]:
                        _ess_latest_dates[_esym] = _edate
                        _ess_archive[_esym] = _ecat

    # Build set of overweight node keys for quick lookup
    overweight_nodes = {
        r.node_key for r in alignment_results
        if r.drift_direction == "OVERWEIGHT" and r.severity in ("HIGH", "MODERATE")
    }

    overlays: list[SecurityIntelligenceOverlay] = []
    for h in holdings:
        sym = h.symbol.upper()
        score = h.composite_score
        ess = h.ess_score_text or ""
        # Phase 22D.2 WS-B: if ESS is absent from the holding (signal_snapshot
        # gap or NON_STARMINE_ANALYST suppression), use archive fallback.
        if not ess:
            ess = _ess_archive.get(sym, "")
        ess = ess or "UNKNOWN"
        zacks = h.zacks_rating or "UNKNOWN"

        # Replay support — is this symbol in any top-N replay for its tier?
        # Phase 7.4D: also accept industry-specific replay evidence when
        # geo / market_cap_bucket / industry match the holding's canonical tier.
        in_replay = sym in symbol_tier
        replay_id = symbol_replay.get(sym)
        replay_tier = symbol_tier.get(sym, "?")

        if not in_replay and sym in industry_replay_evidence:
            ev = industry_replay_evidence[sym]
            if (
                ev["geo"] == h.geography
                and ev["cap"] == h.market_cap_bucket
                and ev["industry"] == (h.industry or "").strip().upper()
            ):
                in_replay = True
                replay_id = ev["replay_id"]
                replay_tier = f"{ev['geo']}.{ev['cap']}.{ev['industry']}"

        # Signal direction synthesis
        # ESS takes priority when available and explicit; composite score is
        # tiebreaker only when ESS is absent or NEUTRAL.
        # Score scale: 1–5. ≥3.5 = bullish zone, 2.0–3.49 = neutral zone,
        # <2.0 = weak/bearish zone.  A score of 2.4 is borderline neutral —
        # don't override an explicit ESS=NEUTRAL with BEARISH.
        #
        # ESS=BEARISH floor override: if the composite score (which includes
        # Danelfin, Zacks, and Yahoo) is ≥2.5, strong secondary consensus
        # lifts the direction to NEUTRAL ("cautious hold") rather than BEARISH.
        # ESS still caps the ceiling — BULLISH is never reached this way.
        if ess.upper() == "BULLISH":
            direction = "BULLISH"
        elif ess.upper() == "BEARISH":
            if score is not None and score >= 2.5:
                direction = "NEUTRAL"
            else:
                direction = "BEARISH"
        elif score is not None:
            if score >= 3.5:    direction = "BULLISH"
            elif score >= 2.0:  direction = "NEUTRAL"
            else:               direction = "BEARISH"
        else:
            direction = "UNKNOWN"

        # Determine if this holding is in an overweight node
        holding_nodes = set(_holding_node_keys_for_sym(h))
        is_overweight = bool(holding_nodes & overweight_nodes)

        # Opportunity flag
        if direction == "BEARISH" and is_overweight:
            flag = "TRIM"
            rationale = f"{sym} has a weak signal ({ess}/{zacks}) and sits in an overweight allocation tier."
        elif direction == "BULLISH" and in_replay:
            flag = "ACCUMULATE"
            rationale = f"{sym} is replay-supported (tier: {replay_tier}) with a strong score ({score})."
        elif direction == "BEARISH":
            flag = "WATCH"
            rationale = f"{sym} has a weak signal — monitor for further deterioration."
        elif is_overweight:
            flag = "HOLD"
            rationale = f"{sym} is in an overweight tier; maintain but do not add."
        else:
            flag = "HOLD"
            rationale = f"No specific action signal — hold current position."

        overlays.append(SecurityIntelligenceOverlay(
            portfolio_snapshot_id=portfolio_snapshot_id,
            symbol=sym,
            composite_score=score,
            ess_score_text=ess if ess != "UNKNOWN" else None,
            zacks_rating=zacks if zacks != "UNKNOWN" else None,
            best_replay_return=None,    # enriched if needed in future
            replay_percentile=symbol_percentile.get(sym),
            replay_supported=in_replay,
            percent_of_portfolio=h.percent_of_portfolio,
            is_overweight_vs_target=is_overweight,
            signal_direction=direction,
            opportunity_flag=flag,
            flag_rationale=rationale,
            created_at_utc=now_utc,
            danelfin_score=h.danelfin_score,
        ))

    return sorted(overlays, key=lambda o: o.percent_of_portfolio, reverse=True)


def _holding_node_keys_for_sym(h: PortfolioHolding) -> list[str]:
    """Import-safe thin wrapper — avoids circular dependency."""
    from .alignment import _holding_node_keys
    return _holding_node_keys(h)


# ─────────────────────────────────────────────────────────────────────────────
# Recommendation engine (Phase F / H)
# ─────────────────────────────────────────────────────────────────────────────

def generate_recommendations(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    alignment_results: list[AllocationAlignmentResult],
    concentration: ConcentrationRiskSummary,
    overlays: list[SecurityIntelligenceOverlay],
    strategic_profiles: Optional[list] = None,  # Phase D HoldingStrategicProfile list
) -> list[PortfolioRecommendation]:
    """Generate prioritized advisory recommendations.

    Sources of recommendations:
    1. HIGH/MODERATE drift in alignment results → allocation balance recs
    2. Concentration risk → diversification recs
    3. Security-level TRIM signals → specific position recs
    4. Underweight tiers with replay support → opportunity recs
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    recs: list[PortfolioRecommendation] = []

    replay_ev = _load_replay_evidence()
    symbol_tier = replay_ev["symbol_tier"]

    # Pre-compute funding sources once (used in INCREASE_UNDERWEIGHT rationale)
    funding = identify_funding_sources(
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        holdings=holdings,
        alignment_results=alignment_results,
        overlays=overlays,
    )
    _top_funding_str = ""
    if funding.sources:
        top_src = funding.sources[0]
        sym_preview = ", ".join(top_src.symbols[:2])
        _top_funding_str = (
            f" Funding source: {top_src.source_type.replace('_', ' ').title()}"
            f" ({sym_preview}, ~{top_src.available_pct:.1f}% available)."
        )

    # ── 1. Allocation drift recommendations ──────────────────────────────────
    for ar in alignment_results:
        if ar.severity not in ("HIGH", "MODERATE"):
            continue

        if ar.drift_direction == "OVERWEIGHT":
            rec_type = "REDUCE_OVERWEIGHT"
            # Find implicated symbols in this node (highest value overweight positions)
            implicated = _symbols_in_node(ar.node_key, holdings)
            title = f"Reduce {ar.node_label} allocation ({ar.drift_pct:+.1f}% drift)"
            rationale = (
                f"Portfolio is overweight {ar.node_label} by {ar.drift_pct:+.1f} percentage points "
                f"(actual {ar.actual_pct:.1f}% vs target {ar.tactical_target_pct:.1f}%). "
                f"Severity: {ar.severity}. "
                f"Reducing to target improves diversification and manages concentration risk."
            )
        else:
            rec_type = "INCREASE_UNDERWEIGHT"
            sorted_vehicles, suitability_notes = _sorted_vehicles_with_suitability(
                ar.node_key, alignment_results
            )
            # Use suitability-sorted vehicles if available; fall back to existing holdings
            implicated = sorted_vehicles if sorted_vehicles else _symbols_in_node(ar.node_key, holdings)
            prescriptive = _prescriptive_rationale(ar.node_key, ar.drift_pct, ar.tactical_target_pct)
            title = f"Build {ar.node_label} allocation ({ar.drift_pct:+.1f}% drift)"
            decomposition_note = _decomposition_note(ar.node_key, ar, holdings)
            # Append top vehicle suitability context when available
            suitability_note_str = ""
            if suitability_notes:
                top = suitability_notes[0]
                suitability_note_str = (
                    f" Best match: {top.symbol} ({top.suitability_tier} suitability). "
                    f"{top.suitability_explanation}"
                )
            rationale = (
                f"Portfolio is underweight {ar.node_label} by {abs(ar.drift_pct):.1f}pp "
                f"(actual {ar.actual_pct:.1f}% vs target {ar.tactical_target_pct:.1f}%). "
                + prescriptive
                + decomposition_note
                + suitability_note_str
                + _top_funding_str
            )

        # Find any replay support for this node
        replay_ids = _replay_ids_for_node(ar.node_key)
        evidence = _evidence_summary(ar, replay_ids)

        is_increase = rec_type == "INCREASE_UNDERWEIGHT"
        recs.append(PortfolioRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            recommendation_type=rec_type,
            priority=ar.recommendation_priority,
            confidence=_confidence_from_severity(ar.severity),
            title=title,
            rationale=rationale,
            evidence_summary=evidence,
            affected_node_key=ar.node_key,
            affected_symbols=implicated,
            drift_pct=ar.drift_pct,
            severity=ar.severity,
            replay_run_ids=tuple(replay_ids),
            created_at_utc=now_utc,
            vehicle_suitability_notes=suitability_notes if is_increase else (),
            card_type="ACTION",
            execution_state="EXECUTABLE",
        ))

    # ── 2. Concentration risk recommendations ────────────────────────────────
    if concentration.concentration_tier in ("CRITICAL", "HIGH"):
        recs.append(PortfolioRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            recommendation_type="DIVERSIFY_CONCENTRATION",
            priority=1,
            confidence="HIGH",
            title=f"Portfolio concentration is {concentration.concentration_tier} (HHI={concentration.herfindahl_index:.3f})",
            rationale=(
                f"Top position {concentration.top1_symbol} represents {concentration.top1_pct:.1f}% of portfolio. "
                f"Top 5 positions = {concentration.top5_pct:.1f}%. "
                f"Herfindahl index {concentration.herfindahl_index:.3f} indicates {concentration.concentration_tier.lower()} concentration. "
                f"Broadening exposure reduces idiosyncratic risk."
            ),
            evidence_summary="Concentration risk exceeds SIH structural policy thresholds.",
            affected_node_key=None,
            affected_symbols=(concentration.top1_symbol,),
            drift_pct=None,
            severity="HIGH" if concentration.concentration_tier == "CRITICAL" else "MODERATE",
            replay_run_ids=(),
            created_at_utc=now_utc,
            card_type="ACTION",
            execution_state="EXECUTABLE",
        ))

    # ── 3. Security-level TRIM signals (Phase D: use STI when available) ────
    if strategic_profiles:
        strat_recs = _generate_strategic_trim_recs(
            analysis_run_id, portfolio_snapshot_id, strategic_profiles,
            overlays, alignment_results, now_utc
        )
        recs.extend(strat_recs)
    else:
        # Fallback: legacy TRIM flag path (no STI profiles available)
        trim_targets = [o for o in overlays if o.opportunity_flag == "TRIM"]
        if trim_targets:
            symbols_to_trim = tuple(o.symbol for o in trim_targets[:5])
            recs.append(PortfolioRecommendation(
                recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
                analysis_run_id=analysis_run_id,
                portfolio_snapshot_id=portfolio_snapshot_id,
                recommendation_type="IMPROVE_RISK_PROFILE",
                priority=2,
                confidence="MEDIUM",
                title=f"Review low-signal overweight positions ({len(trim_targets)} flagged)",
                rationale=(
                    f"{len(trim_targets)} holding(s) combine weak SIH signals with overweight tier positioning: "
                    + ", ".join(symbols_to_trim)
                    + ". "
                    "Reducing these positions addresses both signal weakness and allocation drift simultaneously."
                ),
                evidence_summary=(
                    "Holdings flagged where composite_score is low (< 2.0) or ESS is explicitly BEARISH "
                    "AND the position sits in an overweight allocation tier."
                ),
                affected_node_key=None,
                affected_symbols=symbols_to_trim,
                drift_pct=None,
                severity="MODERATE",
                replay_run_ids=(),
                created_at_utc=now_utc,
                card_type="ACTION",
                execution_state="EXECUTABLE",
            ))

    # ── 4. Replay-supported underweight opportunities ─────────────────────────
    replay_underweights = [
        ar for ar in alignment_results
        if ar.drift_direction == "UNDERWEIGHT"
        and ar.severity in ("HIGH", "MODERATE")
        and ar.node_key in {
            "EQUITIES.US.MEGA", "EQUITIES.US.LARGE", "EQUITIES.US.SMALL",
            "EQUITIES.US.MEGA.HYPER_MEGA",
        }
    ]
    for ar in replay_underweights[:3]:
        replay_ids = _replay_ids_for_node(ar.node_key)
        if replay_ids:
            recs.append(PortfolioRecommendation(
                recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
                analysis_run_id=analysis_run_id,
                portfolio_snapshot_id=portfolio_snapshot_id,
                recommendation_type="IMPROVE_REPLAY_ALIGNMENT",
                priority=2,
                confidence="MEDIUM",
                title=f"Replay-supported opportunity in {ar.node_label} (underweight {ar.drift_pct:+.1f}%)",
                rationale=(
                    f"Portfolio is underweight {ar.node_label} by {abs(ar.drift_pct):.1f}pp. "
                    f"SIH replay evidence shows this tier has historically delivered above-benchmark returns "
                    f"when top-ranked composite score stocks were selected. "
                    f"Increasing allocation here aligns with replay-backed intelligence."
                ),
                evidence_summary=f"Replay IDs: {', '.join(replay_ids[:3])}",
                affected_node_key=ar.node_key,
                affected_symbols=(),
                drift_pct=ar.drift_pct,
                severity=ar.severity,
                replay_run_ids=tuple(replay_ids[:3]),
                created_at_utc=now_utc,
                card_type="ACTION",
                execution_state="EXECUTABLE",
            ))

    # ── Phase C: downgrade pass ───────────────────────────────────────────────
    # Build a fast lookup: node_key → AllocationAlignmentResult
    alignment_map: dict[str, AllocationAlignmentResult] = {
        ar.node_key: ar for ar in alignment_results
    }
    recs = _apply_downgrade_pass(recs, alignment_map, holdings)

    # ── Phase C: hierarchy-aware collapse ─────────────────────────────────────
    recs = _apply_hierarchy_collapse(recs)

    # ── Phase C: thematic concentration detection ─────────────────────────────
    thematic_rec = _maybe_thematic_concentration_rec(
        analysis_run_id, portfolio_snapshot_id, holdings, now_utc
    )
    if thematic_rec:
        recs.append(thematic_rec)

    # ── Phase C: consistency validation (log only) ────────────────────────────
    consistency_warnings = validate_recommendation_consistency(recs)

    # ── Phase E: strategic synthesis ─────────────────────────────────────────
    # When STI profiles are available, synthesize Phase E narrative recommendations,
    # deduplicate Phase D recs subsumed by Phase E, and re-prioritize the full set.
    # Phase E warnings are returned alongside recs via the runner; here we absorb them.
    if strategic_profiles:
        recs, _phase_e_warnings = synthesize_phase_e_recommendations(
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            profiles=strategic_profiles,
            overlays=overlays,
            holdings=holdings,
            existing_recs=recs,
            now_utc=now_utc,
        )
    else:
        # Sort by priority + severity when no STI profiles
        sev_order = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "NONE": 3}
        recs.sort(key=lambda r: (r.priority, sev_order.get(r.severity, 3)))

    return recs


def generate_recommendations_with_phase_e_warnings(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    alignment_results: list[AllocationAlignmentResult],
    concentration: ConcentrationRiskSummary,
    overlays: list[SecurityIntelligenceOverlay],
    strategic_profiles: Optional[list] = None,
) -> tuple[list[PortfolioRecommendation], list[str]]:
    """Variant of generate_recommendations that also returns Phase E validation warnings.

    Used by the runner to surface phase_e_warnings in the API response.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    recs = generate_recommendations(
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        holdings=holdings,
        alignment_results=alignment_results,
        concentration=concentration,
        overlays=overlays,
        strategic_profiles=strategic_profiles,
    )

    # Re-run Phase E validation to surface warnings separately
    phase_e_warnings: list[str] = []
    if strategic_profiles:
        from .phase_e_synthesis import validate_phase_e_consistency
        phase_e_warnings = validate_phase_e_consistency(recs, strategic_profiles)

    return recs, phase_e_warnings


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6.1D — Funding source intelligence
# ─────────────────────────────────────────────────────────────────────────────

_CASH_RESERVE_FLOOR_PCT = 2.0  # keep at least this much in cash/sweep as an operational floor


def identify_funding_sources(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    alignment_results: list[AllocationAlignmentResult],
    overlays: list[SecurityIntelligenceOverlay],
) -> FundingSourceAnalysis:
    """Identify deployable capital sources for funding underweight reallocation.

    Returns a FundingSourceAnalysis with prioritized sources:
      1. EXCESS_CASH  — cash-equivalent holdings above the operational floor
      2. TRIM_CANDIDATE — holdings with TRIM opportunity flag from overlays
      3. OVERWEIGHT_REDUCTION — holdings in HIGH/MODERATE overweight nodes

    This function is deterministic: same inputs produce same outputs.
    """
    from .alignment import _holding_node_keys
    now_utc = datetime.now(timezone.utc).isoformat()

    overlay_map: dict[str, SecurityIntelligenceOverlay] = {o.symbol: o for o in overlays}
    sources: list[FundingSourceEntry] = []

    # ── 1. Excess cash ────────────────────────────────────────────────────────
    cash_holdings = [
        h for h in holdings
        if h.is_cash_equivalent or h.asset_class == "CASH"
    ]
    total_cash_pct = sum(h.percent_of_portfolio for h in cash_holdings)
    deployable_cash = max(0.0, total_cash_pct - _CASH_RESERVE_FLOOR_PCT)
    if deployable_cash > 0.1:
        cash_syms = tuple(h.symbol for h in sorted(
            cash_holdings, key=lambda x: x.percent_of_portfolio, reverse=True
        ))
        sources.append(FundingSourceEntry(
            priority=1,
            source_type="EXCESS_CASH",
            symbols=cash_syms,
            available_pct=round(deployable_cash, 2),
            rationale=(
                f"Cash/sweep allocation ({total_cash_pct:.1f}%) exceeds the operational"
                f" reserve floor ({_CASH_RESERVE_FLOOR_PCT:.0f}%). Approximately"
                f" {deployable_cash:.1f}% is deployable without affecting liquidity."
            ),
        ))

    # ── 2. Trim candidates from overlay signals ───────────────────────────────
    trim_holdings = [
        h for h in holdings
        if (ov := overlay_map.get(h.symbol)) is not None
        and getattr(ov, "opportunity_flag", "") == "TRIM"
    ]
    if trim_holdings:
        trim_sorted = sorted(trim_holdings, key=lambda x: x.percent_of_portfolio, reverse=True)
        trim_syms = tuple(h.symbol for h in trim_sorted[:5])
        trim_pct = sum(h.percent_of_portfolio for h in trim_holdings)
        label_list = ", ".join(h.symbol for h in trim_sorted[:3])
        sources.append(FundingSourceEntry(
            priority=2,
            source_type="TRIM_CANDIDATE",
            symbols=trim_syms,
            available_pct=round(trim_pct, 2),
            rationale=(
                f"{len(trim_holdings)} holding(s) flagged for TRIM"
                f" ({label_list}{', ...' if len(trim_holdings) > 3 else ''})."
                f" Combined weight {trim_pct:.1f}%. These have weak signals in"
                " overweight allocation tiers."
            ),
        ))

    # ── 3. Overweight reduction opportunities ─────────────────────────────────
    overweight_nodes = [
        ar for ar in alignment_results
        if ar.drift_direction == "OVERWEIGHT" and ar.severity in ("HIGH", "MODERATE")
    ]
    for ar in sorted(overweight_nodes, key=lambda x: abs(x.drift_pct), reverse=True)[:2]:
        ow_holdings = sorted(
            [h for h in holdings if ar.node_key in _holding_node_keys(h)],
            key=lambda h: h.percent_of_portfolio,
            reverse=True,
        )
        if not ow_holdings:
            continue
        ow_syms = tuple(h.symbol for h in ow_holdings[:3])
        ow_pct = round(abs(ar.drift_pct), 2)
        label_list = ", ".join(ow_syms)
        sources.append(FundingSourceEntry(
            priority=3,
            source_type="OVERWEIGHT_REDUCTION",
            symbols=ow_syms,
            available_pct=ow_pct,
            rationale=(
                f"{ar.node_label} is overweight by {ar.drift_pct:+.1f}pp. Trimming"
                f" exposure ({label_list}) corrects the overweight and frees"
                " capacity for reallocation."
            ),
        ))

    total_available = round(
        sum(s.available_pct for s in sources if s.priority <= 2), 2
    )
    if sources:
        primary = sources[0]
        sym_preview = ", ".join(primary.symbols[:2])
        summary = (
            f"{len(sources)} funding source(s) identified."
            f" Primary: {primary.source_type.replace('_', ' ').title()}"
            f" ({sym_preview}, ~{primary.available_pct:.1f}% available)."
        )
    else:
        summary = "No clear internal funding sources identified. New capital contribution required."

    return FundingSourceAnalysis(
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        sources=tuple(sources),
        total_available_pct=total_available,
        summary=summary,
        created_at_utc=now_utc,
    )




def _symbols_in_node(node_key: str, holdings: list[PortfolioHolding]) -> tuple:
    """Return top-5 symbols by % that map to node_key."""
    from .alignment import _holding_node_keys
    matching = [
        h for h in holdings
        if node_key in _holding_node_keys(h)
    ]
    matching.sort(key=lambda h: h.percent_of_portfolio, reverse=True)
    return tuple(h.symbol for h in matching[:5])


def _decomposition_note(node_key: str, ar: AllocationAlignmentResult, holdings: list[PortfolioHolding]) -> str:
    """Explain how ETF decomposition affected a node-level recommendation."""
    if ar.etf_derived_actual_pct <= 0.0:
        return ""

    contributors: list[tuple[str, float]] = []
    for holding in holdings:
        security_type = str(getattr(holding, "security_type", "") or "").strip().upper()
        if security_type not in {"ETF", "MUTUAL_FUND"}:
            continue
        _, effective, _ = build_holding_exposure_contribs(holding)
        contribution = float(effective.get(node_key, 0.0) or 0.0)
        if contribution > 0:
            contributors.append((holding.symbol.upper(), contribution))

    contributors.sort(key=lambda item: item[1], reverse=True)
    top = ", ".join(f"{symbol} {pct:.1f}%" for symbol, pct in contributors[:3])

    note = (
        f" ETF decomposition contributes {ar.etf_derived_actual_pct:.1f}% of effective exposure"
        f" to {node_key}."
    )
    if top:
        note += f" Top ETF contributors: {top}."
    return note


def _replay_ids_for_node(node_key: str) -> list[str]:
    """Return replay IDs that cover this allocation node."""
    inputs_csv = "data/current/replay_inputs.csv"
    if not os.path.exists(inputs_csv):
        return []
    # Map node_key parts to replay filter fields
    parts = node_key.upper().split(".")
    if len(parts) < 2:
        return []
    geo_map = {"US": "US", "INTERNATIONAL": "INTERNATIONAL", "EMERGING_MARKETS": "INTERNATIONAL"}
    cap_map = {"MEGA": "MEGA", "LARGE": "LARGE", "MID": "MID", "SMALL": "SMALL", "MICRO": "MICRO"}

    target_geo = geo_map.get(parts[1]) if len(parts) > 1 else None
    target_cap = cap_map.get(parts[2]) if len(parts) > 2 else None

    ids: list[str] = []
    for row in csv.DictReader(open(inputs_csv)):
        if target_geo and row.get("filter_geography", "").upper() != target_geo:
            continue
        if target_cap and row.get("filter_market_cap_bucket", "").upper() != target_cap:
            continue
        if row.get("filter_industry", "").upper() != "ALL":
            continue
        replay_id = row.get("replay_id", "")
        if replay_id:
            ids.append(replay_id)
        if len(ids) >= 5:
            break
    return ids


def _evidence_summary(ar: AllocationAlignmentResult, replay_ids: list[str]) -> str:
    base = (
        f"Strategic target: {ar.target_pct:.1f}%. "
        f"Tactical target: {ar.tactical_target_pct:.1f}%. "
        f"Actual: {ar.actual_pct:.1f}%. "
        f"Drift: {ar.drift_pct:+.1f}pp."
    )
    if replay_ids:
        base += f" Replay evidence available ({len(replay_ids)} replay(s) for this tier)."
    return base


def _confidence_from_severity(severity: str) -> str:
    return {"HIGH": "HIGH", "MODERATE": "MEDIUM", "LOW": "LOW"}.get(severity, "LOW")


# ─────────────────────────────────────────────────────────────────────────────
# Suggested investable vehicles by allocation node
# ─────────────────────────────────────────────────────────────────────────────

_SUGGESTED_VEHICLES: dict[str, tuple[str, ...]] = {
    # Fixed income
    "FIXED_INCOME":                       ("BND",  "AGG",  "IEF",  "SCHP"),
    "FIXED_INCOME.US":                    ("BND",  "AGG",  "IEF",  "SCHP", "LQD"),
    "FIXED_INCOME.INTERNATIONAL":         ("BNDX", "IAGG"),
    # International equity
    "EQUITIES.INTERNATIONAL":             ("VEA",  "VXUS", "EFA"),
    "EQUITIES.INTERNATIONAL.MEGA":        ("EFA",  "VEA"),
    "EQUITIES.INTERNATIONAL.LARGE":       ("VEA",  "EFA",  "IEFA"),
    "EQUITIES.INTERNATIONAL.MID":         ("IEFA", "VEA"),
    "EQUITIES.INTERNATIONAL.SMALL":       ("VSS",  "SCHF"),
    "EQUITIES.INTERNATIONAL.MICRO":       ("VSS",),
    # Emerging markets
    "EQUITIES.EMERGING_MARKETS":          ("VWO",  "EEM",  "IEMG"),
    # US equity broad
    "EQUITIES.US":                        ("VOO",  "VTI",  "IVV"),
    "EQUITIES.US.MEGA":                   ("VOO",  "IVV",  "SPY"),
    "EQUITIES.US.MEGA.HYPER_MEGA":        ("QQQ",  "VOO"),
    "EQUITIES.US.MEGA.ULTRA_MEGA":        ("VOO",  "IVV",  "QQQ"),
    "EQUITIES.US.MEGA.EXTENDED_MEGA":     ("VTI",  "SCHB", "VOO"),
    "EQUITIES.US.LARGE":                  ("VOO",  "IVV",  "SPY"),
    "EQUITIES.US.MID":                    ("VO",   "MDY",  "IJH"),
    "EQUITIES.US.SMALL":                  ("VB",   "IWM",  "IJR"),
    "EQUITIES.US.MICRO":                  ("IWC",),
    # Digital assets
    "DIGITAL":                            ("FBTC", "IBIT", "FETH"),
    # Commodities
    "COMMODITIES":                        ("GLD",  "IAU",  "GSG"),
    # Cash / short-term
    "CASH":                               ("SGOV", "BIL"),
}


def _suggested_vehicles_for_node(node_key: str) -> tuple[str, ...]:
    """Return suggested ETF/fund tickers for an underweight allocation node.

    Tries the most-specific key first, falling back to shorter prefixes.
    Returns an empty tuple if no mapping exists.
    """
    key = node_key.upper()
    parts = key.split(".")
    for length in range(len(parts), 0, -1):
        candidate = ".".join(parts[:length])
        if candidate in _SUGGESTED_VEHICLES:
            return _SUGGESTED_VEHICLES[candidate]
    return ()


# Prescriptive, plain-language rationale keyed by allocation node.
# Each string should complete the sentence fragment that precedes it in the
# recommendation text (i.e. it follows the drift/target statement).
_PRESCRIPTIVE_RATIONALE: dict[str, str] = {
    "FIXED_INCOME": (
        "The portfolio holds no bonds. Start with BND (Vanguard Total Bond Market ETF) "
        "for broad, low-cost investment-grade US exposure across government and corporate debt. "
        "Add SCHP to build inflation protection via TIPS. "
        "IEF (7–10yr Treasuries) provides intermediate duration if you want to lock in "
        "current yields. AGG is a direct alternative to BND with nearly identical exposure."
    ),
    "FIXED_INCOME.US": (
        "No US bond exposure exists. BND or AGG cover the full investment-grade spectrum "
        "in a single fund. SCHP hedges inflation risk (TIPS). "
        "LQD adds investment-grade corporate yield above Treasuries. "
        "IEF targets the intermediate Treasury segment specifically."
    ),
    "FIXED_INCOME.INTERNATIONAL": (
        "The strategic target includes a 5% allocation to non-US bonds. "
        "BNDX (Vanguard Total International Bond ETF) is currency-hedged, eliminating "
        "FX volatility while adding diversification across developed-market sovereign and "
        "corporate debt. IAGG (iShares Core International Aggregate Bond ETF) offers a "
        "similar profile. If you prefer to keep all bond exposure domestic, consider "
        "reallocating this target to FIXED_INCOME.US instead."
    ),
    "FIXED_INCOME.INFLATION_PROTECTED": (
        "No TIPS/inflation-protected exposure. SCHP (Schwab US TIPS ETF) is the "
        "lowest-cost option; TIP (iShares TIPS) is the more liquid alternative. "
        "Both track US Treasury inflation-protected securities and help preserve "
        "real purchasing power when CPI rises."
    ),
    "EQUITIES.INTERNATIONAL": (
        "International developed-market equities are underweight. "
        "VEA (Vanguard FTSE Developed Markets) or EFA (iShares MSCI EAFE) provide "
        "broad exposure to Europe, Japan, and Australasia. "
        "VXUS adds emerging markets alongside developed markets in one fund."
    ),
    "EQUITIES.EMERGING_MARKETS": (
        "Emerging markets exposure is below target. "
        "VWO (Vanguard FTSE Emerging Markets) and IEMG (iShares Core EM) are the "
        "two most widely held low-cost options. "
        "EEM offers higher liquidity but carries a higher expense ratio."
    ),
    "EQUITIES.US.MEGA": (
        "US Mega Cap equities are underweight. "
        "VOO (Vanguard S&P 500), IVV (iShares Core S&P 500), and SPY are the preferred "
        "vehicles for balanced mega-cap completion — they distribute exposure across "
        "Hyper, Ultra, and Extended Mega tiers. "
        "Avoid QQQ for general Mega completion: QQQ concentrates 95% in mega-cap but "
        "is tilted 65% toward AI/tech themes and will worsen tech concentration "
        "if that is already elevated."
    ),
    "EQUITIES.US.MEGA.HYPER_MEGA": (
        "Hyper Mega Cap (top-tier mega, e.g. NVDA, AAPL, MSFT) is underweight. "
        "QQQ concentrates in this tier (48% effective Hyper Mega) and is appropriate "
        "when the goal is growth-tilted Hyper Mega exposure. "
        "VOO provides a more balanced Hyper Mega addition (30% effective) if growth "
        "concentration is already elevated."
    ),
    "EQUITIES.US.MEGA.ULTRA_MEGA": (
        "Ultra Mega Cap is underweight. "
        "VOO and IVV provide balanced Ultra Mega exposure (~30% effective) "
        "without adding the AI/tech concentration that QQQ brings."
    ),
    "EQUITIES.US.MEGA.EXTENDED_MEGA": (
        "Extended Mega Cap (the broader, lower-concentration segment of mega-cap) is "
        "underweight. VTI (Vanguard Total Market) provides the highest Extended Mega "
        "weight (~25% effective: 55% MEGA × 45% Extended subtier). "
        "SCHB (Schwab U.S. Broad Market) is a low-cost alternative. "
        "VOO contributes Extended Mega (~25% effective: 85% MEGA × 29% Extended) "
        "but also raises Hyper/Ultra Mega. "
        "Do NOT use QQQ: QQQ allocates only 12% of its MEGA share to Extended, "
        "making it ineffective and counterproductive for Extended Mega completion."
    ),
}


def _prescriptive_rationale(node_key: str, drift_pct: float, target_pct: float) -> str:
    """Return a prescriptive, plain-language recommendation for an underweight node.

    Falls back to a generic message when no specific text is defined.
    """
    key = node_key.upper()
    # Try exact match, then parent prefixes
    parts = key.split(".")
    for length in range(len(parts), 0, -1):
        candidate = ".".join(parts[:length])
        if candidate in _PRESCRIPTIVE_RATIONALE:
            return _PRESCRIPTIVE_RATIONALE[candidate]
    # Generic fallback
    suggested = _suggested_vehicles_for_node(node_key)
    if suggested:
        return (
            f"Increasing to the {target_pct:.1f}% target improves strategic balance. "
            f"Suggested vehicles: {', '.join(suggested[:4])}."
        )
    return f"Increasing to the {target_pct:.1f}% target improves strategic balance."


# ─────────────────────────────────────────────────────────────────────────────
# Phase F-2 — Vehicle suitability scoring
# ─────────────────────────────────────────────────────────────────────────────

# Lazy cache for the ETF decomposition registry (plain YAML dicts, not dataclasses).
_VEHICLE_REGISTRY_CACHE: Optional[dict[str, dict]] = None


def _get_vehicle_registry() -> dict[str, dict]:
    """Return cached ETF decomposition registry (symbol → raw YAML dict)."""
    global _VEHICLE_REGISTRY_CACHE
    if _VEHICLE_REGISTRY_CACHE is None:
        from .exposure_decomposition import load_decomposition_registry
        _VEHICLE_REGISTRY_CACHE = (
            load_decomposition_registry().get("symbols") or {}
        )
    return _VEHICLE_REGISTRY_CACHE


# Subtier purity thresholds for suitability tier classification.
# "purity" = the % within the MEGA subtier_mix that goes to the target subtier.
_SUBTIER_HIGH_THRESHOLD: dict[str, float] = {
    "HYPER_MEGA":    45.0,
    "ULTRA_MEGA":    33.0,
    "EXTENDED_MEGA": 40.0,
}
_SUBTIER_MEDIUM_THRESHOLD: dict[str, float] = {
    "HYPER_MEGA":    30.0,
    "ULTRA_MEGA":    20.0,
    "EXTENDED_MEGA": 26.0,
}


def _compute_overweight_overlap(
    cap_mix: dict,
    geo_mix: dict,
    subtier_mix: dict,
    alignment_map: dict,
) -> tuple[float, bool]:
    """Compute what % of vehicle weight would land in already-overweight nodes.

    Returns (overlap_pct, worsens_bool).  overlap_pct is the sum of the
    vehicle's effective exposure weight going to HIGH/MODERATE OVERWEIGHT nodes.
    """
    overlap = 0.0
    worsens = False
    for node_key, ar in alignment_map.items():
        if ar.drift_direction != "OVERWEIGHT" or ar.severity not in ("HIGH", "MODERATE"):
            continue
        parts = node_key.upper().split(".")
        if len(parts) < 3 or parts[0] != "EQUITIES":
            continue
        geo_pct = float(geo_mix.get(parts[1], 0))
        cap_pct = float(cap_mix.get(parts[2], 0))
        if len(parts) == 3:
            contribution = geo_pct * cap_pct / 100.0
        elif len(parts) == 4:
            sub_pct = float(subtier_mix.get(parts[3], 0))
            contribution = geo_pct * cap_pct * sub_pct / 10000.0
        else:
            contribution = 0.0
        if contribution >= 10.0:
            overlap += contribution
            worsens = True
    return min(overlap, 100.0), worsens


def _score_vehicle_for_subtier(
    symbol: str,
    subtier_name: str,
    cap_mix: dict,
    subtier_mix: dict,
    thematic_mix: dict,
    worsens: bool,
) -> tuple[float, str, str]:
    """Score a vehicle for a specific MEGA subtier target node.

    Primary signal: subtier purity — what % of the vehicle's MEGA share goes
    to the target subtier?  Higher purity = better fit for that subtier.
    Penalties applied for thematic concentration and overweight worsening.

    Returns (score 0–100, tier HIGH|MEDIUM|LOW, explanation).
    """
    mega_pct = float(cap_mix.get("MEGA", 0))

    if mega_pct < 20.0:
        return (
            5.0, "LOW",
            f"{symbol} suitability: LOW; insufficient MEGA exposure ({mega_pct:.0f}%) "
            f"— cannot meaningfully contribute to "
            f"{subtier_name.replace('_', ' ').title()}.",
        )

    if not subtier_mix:
        return (
            10.0, "LOW",
            f"{symbol} suitability: LOW; no subtier decomposition data — "
            f"{subtier_name.replace('_', ' ').title()} contribution cannot be assessed.",
        )

    purity = float(subtier_mix.get(subtier_name, 0))
    effective_pct = mega_pct * purity / 100.0
    subtier_label = subtier_name.replace("_", " ").title()

    # Thematic penalties
    mega_tech = float(thematic_mix.get("MEGA_TECH_CONCENTRATION", 0))
    ai_infra = float(thematic_mix.get("AI_INFRA", 0))
    growth = float(thematic_mix.get("GROWTH_MOMENTUM", 0))
    thematic_penalty = max(mega_tech, ai_infra) * 0.30 + growth * 0.08
    overweight_penalty = 12.0 if worsens else 0.0

    score = max(0.0, min(100.0, purity - thematic_penalty - overweight_penalty))

    high_thresh = _SUBTIER_HIGH_THRESHOLD.get(subtier_name, 40.0)
    med_thresh = _SUBTIER_MEDIUM_THRESHOLD.get(subtier_name, 25.0)
    tier = "HIGH" if score >= high_thresh else ("MEDIUM" if score >= med_thresh else "LOW")

    # Explanation
    parts_list = [
        f"{symbol} suitability: {tier}",
        f"contributes {effective_pct:.1f}% effective {subtier_label} exposure "
        f"({mega_pct:.0f}% MEGA \u00d7 {purity:.1f}% {subtier_label} subtier share)",
    ]
    if subtier_name == "EXTENDED_MEGA":
        off_pct = mega_pct * (100.0 - purity) / 100.0
        parts_list.append(
            f"also adds {off_pct:.1f}% Hyper/Ultra Mega exposure "
            f"(off-target for Extended Mega completion)"
        )
    if mega_tech >= 70.0:
        parts_list.append(
            f"introduces high mega-tech concentration ({mega_tech:.0f}% intensity) "
            f"— unsuitable for non-growth Mega targets"
        )
    elif ai_infra >= 50.0:
        parts_list.append(f"adds AI/infrastructure theme concentration ({ai_infra:.0f}% intensity)")
    if worsens:
        parts_list.append(
            "may worsen existing US Equity overweight "
            "— consider whether adding more Mega exposure is appropriate"
        )

    return score, tier, "; ".join(parts_list) + "."


def _score_vehicle_for_general_mega(
    symbol: str,
    cap_mix: dict,
    subtier_mix: dict,
    thematic_mix: dict,
    strategic_role: str,
    worsens: bool,
) -> tuple[float, str, str]:
    """Score a vehicle for the general EQUITIES.US.MEGA node (all subtiers).

    For general Mega completion, balanced subtier distribution and core
    strategic role are the primary signals.  QQQ-style growth tilt is
    acceptable only if the investor intends a growth-tilted Mega completion.
    """
    mega_pct = float(cap_mix.get("MEGA", 0))
    if mega_pct < 50.0:
        return (
            10.0, "LOW",
            f"{symbol} suitability: LOW; low MEGA exposure ({mega_pct:.0f}%) "
            "— not well suited for general Mega Cap completion.",
        )

    # Balance score: spread across all three subtiers
    balance_penalty = 0.0
    if subtier_mix:
        values = [float(subtier_mix.get(k, 0)) for k in ("HYPER_MEGA", "ULTRA_MEGA", "EXTENDED_MEGA")]
        non_zero = [v for v in values if v > 0]
        if len(non_zero) >= 2:
            balance_penalty = (max(non_zero) - min(non_zero)) * 0.15

    mega_tech = float(thematic_mix.get("MEGA_TECH_CONCENTRATION", 0))
    ai_infra = float(thematic_mix.get("AI_INFRA", 0))
    thematic_penalty = max(mega_tech, ai_infra) * 0.25
    overweight_penalty = 8.0 if worsens else 0.0

    base = (mega_pct / 100.0) * 60.0
    score = max(0.0, min(100.0, base - balance_penalty - thematic_penalty - overweight_penalty))
    tier = "HIGH" if score >= 40.0 else ("MEDIUM" if score >= 25.0 else "LOW")

    parts_list = [f"{symbol} suitability: {tier}"]
    if subtier_mix:
        tilt = max(subtier_mix.items(), key=lambda kv: kv[1])
        if tilt[1] > 45.0:
            parts_list.append(
                f"broad Mega Cap coverage ({mega_pct:.0f}% MEGA, "
                f"tilted toward {tilt[0].replace('_', ' ').title()})"
            )
        else:
            parts_list.append(f"broad balanced Mega Cap coverage ({mega_pct:.0f}% MEGA)")
    else:
        parts_list.append(f"broad Mega Cap coverage ({mega_pct:.0f}% MEGA)")

    if strategic_role == "CORE_BROAD_US":
        parts_list.append("CORE_BROAD_US role — balanced sector and subtier distribution")
    if mega_tech >= 60.0:
        parts_list.append(
            f"introduces significant mega-tech concentration ({mega_tech:.0f}%) "
            "— appropriate only if growth tilt is intentional"
        )
    if worsens:
        parts_list.append("may worsen existing US Mega overweight")

    return score, tier, "; ".join(parts_list) + "."


def _score_vehicle_generic(
    symbol: str,
    target_node_key: str,
    cap_mix: dict,
    geo_mix: dict,
    worsens: bool,
) -> tuple[float, str, str]:
    """Generic fallback scoring for non-MEGA-subtier nodes."""
    parts = target_node_key.upper().split(".")
    if len(parts) >= 3:
        geo_pct = float(geo_mix.get(parts[1], 0))
        cap_pct = float(cap_mix.get(parts[2], 0))
        effective = geo_pct * cap_pct / 100.0
        score = min(effective, 100.0)
        tier = "HIGH" if score >= 50.0 else ("MEDIUM" if score >= 25.0 else "LOW")
        explanation = (
            f"{symbol} suitability: {tier}; "
            f"{geo_pct:.0f}% {parts[1]} geography × {cap_pct:.0f}% {parts[2]} exposure "
            f"= {effective:.1f}% effective coverage for {target_node_key}."
        )
        if worsens:
            explanation = explanation.rstrip(".") + "; may worsen existing overweight."
        return score, tier, explanation

    return (
        50.0, "MEDIUM",
        f"{symbol} suitability: MEDIUM; no fine-grained scoring available for {target_node_key}.",
    )


def _compute_vehicle_suitability(
    symbol: str,
    target_node_key: str,
    alignment_results: list,
) -> "VehicleSuitabilityNote":
    """Score how suitable a vehicle is for a specific underweight allocation node.

    Suitability is node-specific: a vehicle excellent for general Mega Cap may
    be MEDIUM for Extended Mega completion (different subtier purity profile).
    """
    from .models import VehicleSuitabilityNote

    registry = _get_vehicle_registry()
    model = registry.get(symbol.upper())
    alignment_map = {ar.node_key: ar for ar in alignment_results}

    if not model:
        return VehicleSuitabilityNote(
            symbol=symbol.upper(),
            target_node_coverage_pct=0.0,
            off_target_exposure_pct=0.0,
            overlap_with_existing_pct=0.0,
            worsens_existing_overweight=False,
            thematic_concentration_added="",
            strategic_role="UNKNOWN",
            suitability_score=0.0,
            suitability_tier="LOW",
            suitability_explanation=(
                f"{symbol} suitability: LOW; no decomposition registry entry "
                "— cannot assess target-node fit."
            ),
        )

    cap_mix: dict = model.get("exposure_market_cap_mix") or {}
    geo_mix: dict = model.get("exposure_geography_mix") or {}
    subtier_mix: dict = model.get("exposure_mega_subtier_mix") or {}
    thematic_mix: dict = model.get("exposure_thematic_mix") or {}
    strategic_role = str(model.get("strategic_role") or "")

    overlap_pct, worsens = _compute_overweight_overlap(cap_mix, geo_mix, subtier_mix, alignment_map)
    node_parts = target_node_key.upper().split(".")

    if (
        len(node_parts) == 4
        and node_parts[0] == "EQUITIES"
        and node_parts[2] == "MEGA"
    ):
        # e.g. EQUITIES.US.MEGA.EXTENDED_MEGA
        subtier_name = node_parts[3]
        score, tier, explanation = _score_vehicle_for_subtier(
            symbol=symbol.upper(),
            subtier_name=subtier_name,
            cap_mix=cap_mix,
            subtier_mix=subtier_mix,
            thematic_mix=thematic_mix,
            worsens=worsens,
        )
        mega_pct = float(cap_mix.get("MEGA", 0))
        purity = float(subtier_mix.get(subtier_name, 0))
        target_coverage = mega_pct * purity / 100.0
        off_target = mega_pct - target_coverage

    elif (
        len(node_parts) == 3
        and node_parts[0] == "EQUITIES"
        and node_parts[2] == "MEGA"
    ):
        # e.g. EQUITIES.US.MEGA
        score, tier, explanation = _score_vehicle_for_general_mega(
            symbol=symbol.upper(),
            cap_mix=cap_mix,
            subtier_mix=subtier_mix,
            thematic_mix=thematic_mix,
            strategic_role=strategic_role,
            worsens=worsens,
        )
        target_coverage = float(cap_mix.get("MEGA", 0))
        off_target = 100.0 - target_coverage

    else:
        score, tier, explanation = _score_vehicle_generic(
            symbol=symbol.upper(),
            target_node_key=target_node_key,
            cap_mix=cap_mix,
            geo_mix=geo_mix,
            worsens=worsens,
        )
        target_coverage = 0.0
        off_target = 0.0

    # Identify worst thematic concentration (intensity >= 60)
    worst_theme = ""
    worst_intensity = 0.0
    for theme, intensity in thematic_mix.items():
        if float(intensity) > worst_intensity:
            worst_intensity = float(intensity)
            worst_theme = theme
    if worst_intensity < 60.0:
        worst_theme = ""
    else:
        worst_theme = worst_theme.replace("_", " ").title()

    return VehicleSuitabilityNote(
        symbol=symbol.upper(),
        target_node_coverage_pct=round(target_coverage, 2),
        off_target_exposure_pct=round(off_target, 2),
        overlap_with_existing_pct=round(overlap_pct, 2),
        worsens_existing_overweight=worsens,
        thematic_concentration_added=worst_theme,
        strategic_role=strategic_role,
        suitability_score=round(score, 1),
        suitability_tier=tier,
        suitability_explanation=explanation,
    )


def _sorted_vehicles_with_suitability(
    node_key: str,
    alignment_results: list,
) -> tuple[tuple[str, ...], tuple]:
    """Return suggested vehicles sorted by suitability score (highest first).

    Returns (sorted_symbols_tuple, suitability_notes_tuple).
    Vehicles with no registry entry are placed last.
    """
    candidates = list(_suggested_vehicles_for_node(node_key))
    if not candidates:
        return (), ()

    notes = [
        _compute_vehicle_suitability(sym, node_key, alignment_results)
        for sym in candidates
    ]
    paired = sorted(zip(candidates, notes), key=lambda x: x[1].suitability_score, reverse=True)
    sorted_symbols = tuple(sym for sym, _ in paired)
    sorted_notes = tuple(note for _, note in paired)
    return sorted_symbols, sorted_notes


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Effective exposure saturation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _identify_etf_contributors(
    node_key: str,
    holdings: list[PortfolioHolding],
) -> list[tuple[str, float, str]]:
    """Return ETF/fund holdings that contribute exposure to node_key.

    Returns list of (symbol, contribution_pct, strategic_role) sorted by pct desc.
    Only includes holdings whose decomposition_source is registry-backed or whose
    security_type marks them as a fund.
    """
    _FUND_SOURCES = {"REGISTRY", "HEURISTIC_FALLBACK", "SYMBOL_HEURISTIC"}
    _FUND_TYPES = {"ETF", "MUTUAL_FUND"}
    contributors: list[tuple[str, float, str]] = []
    for h in holdings:
        # Cash-equivalent holdings are never ETF exposure containers,
        # even if they appear in the ETF registry (Phase 6.3D fix).
        op_state = str(getattr(h, "operational_state", "") or "").strip().upper()
        is_ce = getattr(h, "is_cash_equivalent", False)
        if op_state == "CASH_EQUIVALENT" or is_ce:
            continue
        src = str(getattr(h, "decomposition_source", "") or "").strip().upper()
        sec = str(getattr(h, "security_type", "") or "").strip().upper()
        if src not in _FUND_SOURCES and sec not in _FUND_TYPES:
            continue
        _, effective, _ = build_holding_exposure_contribs(h)
        contribution = float(effective.get(node_key, 0.0) or 0.0)
        if contribution > 0.0:
            role = str(getattr(h, "strategic_role", "") or "")
            contributors.append((h.symbol.upper(), round(contribution, 3), role))
    contributors.sort(key=lambda x: x[1], reverse=True)
    return contributors


def _compute_node_saturation(ar: AllocationAlignmentResult) -> dict:
    """Compute saturation and indirect exposure ratios for a node."""
    effective = float(ar.effective_actual_pct or 0.0)
    target = float(ar.tactical_target_pct or 0.0)
    etf_derived = float(ar.etf_derived_actual_pct or 0.0)
    direct = float(ar.direct_actual_pct or 0.0)

    saturation_ratio = (effective / target) if target > 0.0 else 1.0
    indirect_ratio = (etf_derived / effective) if effective > 0.001 else 0.0

    return {
        "saturation_ratio": min(saturation_ratio, 2.0),  # cap for display
        "indirect_ratio": min(indirect_ratio, 1.0),
        "effective": effective,
        "direct": direct,
        "etf_derived": etf_derived,
        "target": target,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Recommendation state determination
# ─────────────────────────────────────────────────────────────────────────────

# Strategic roles where indirect ETF exposure is fundamentally broad / core —
# these roles should have higher downgrade sensitivity (broad passive exposure
# is less "intentional" than concentrated sector/theme exposure).
_CORE_PASSIVE_ROLES = frozenset({
    "CORE_BROAD_US",
    "INTERNATIONAL_DIVERSIFICATION",
    "STABILITY_CORE",
    "CASH_EQUIVALENT",
})

# Roles where exposure is concentrated and intentional — downgrade threshold
# is higher (these represent deliberate concentration bets).
_CONCENTRATED_ROLES = frozenset({
    "AGGRESSIVE_GROWTH_CONCENTRATION",
    "SEMICONDUCTOR_CONCENTRATION",
    "SECTOR_CONCENTRATION",
    "SYSTEMATIC_SMALL_CAP",
    "SYSTEMATIC_MID_CAP",
    "SYSTEMATIC_MICRO_CAP",
})


def _determine_rec_state_underweight(
    saturation_ratio: float,
    indirect_ratio: float,
    etf_contributors: list[tuple[str, float, str]],
) -> str:
    """Determine ACTIVE/DOWNGRADED/INFORMATIONAL state for an INCREASE_UNDERWEIGHT rec.

    Philosophy: indirect ETF exposure MODULATES but does not erase intentional
    direct exposure semantics.

    Thresholds:
      INFORMATIONAL: target nearly met and mostly via ETFs (high passive coverage)
      DOWNGRADED:    partial satisfaction via ETFs — still worth acting but context needed
      ACTIVE:        either direct gap is real, or indirect coverage is low
    """
    # Check the strategic character of contributing ETFs
    contributing_roles = {role for _, _, role in etf_contributors if role}
    all_core_passive = bool(contributing_roles) and contributing_roles.issubset(_CORE_PASSIVE_ROLES)
    any_concentrated = bool(contributing_roles & _CONCENTRATED_ROLES)

    # Core-passive ETFs provide true broad exposure — higher downgrade sensitivity
    if all_core_passive:
        if saturation_ratio >= 0.85 and indirect_ratio >= 0.75:
            return "INFORMATIONAL"
        if saturation_ratio >= 0.60 and indirect_ratio >= 0.60:
            return "DOWNGRADED"
    # Concentrated roles (QQQ, SMH etc.) provide intentional thematic exposure
    elif any_concentrated:
        # These are deliberate bets — only downgrade when very heavily covered
        if saturation_ratio >= 0.90 and indirect_ratio >= 0.85:
            return "INFORMATIONAL"
        if saturation_ratio >= 0.75 and indirect_ratio >= 0.80:
            return "DOWNGRADED"
    else:
        # Mixed or unknown — moderate thresholds
        if saturation_ratio >= 0.88 and indirect_ratio >= 0.80:
            return "INFORMATIONAL"
        if saturation_ratio >= 0.65 and indirect_ratio >= 0.70:
            return "DOWNGRADED"

    return "ACTIVE"


def _determine_rec_state_overweight(
    saturation_ratio: float,
    indirect_ratio: float,
    etf_contributors: list[tuple[str, float, str]],
) -> str:
    """Determine state for a REDUCE_OVERWEIGHT rec.

    Overweight conditions remain ACTIVE by default — overweight is overweight
    regardless of whether it arrived via direct or indirect exposure. However:
    - If 100% of the overweight is indirect (no direct holdings at all) we can
      contextualise the rec as DOWNGRADED with a note to trim ETF holdings.
    """
    has_direct = any(True for _ in [1] if (1.0 - indirect_ratio) > 0.01)
    # If almost entirely indirect, annotate as DOWNGRADED (but keep visible)
    if indirect_ratio >= 0.95 and not has_direct:
        return "DOWNGRADED"
    return "ACTIVE"


def _adjust_confidence(
    base_confidence: str,
    state: str,
    etf_contributors: list[tuple[str, float, str]],
) -> str:
    """Adjust recommendation confidence based on state and ETF decomposition quality."""
    if state == "INFORMATIONAL":
        # Downgrade one notch: HIGH→MEDIUM, MEDIUM→LOW, LOW stays LOW
        return {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}.get(base_confidence, base_confidence)
    if state == "DOWNGRADED":
        return {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}.get(base_confidence, base_confidence)
    return base_confidence


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Reasoning trace construction
# ─────────────────────────────────────────────────────────────────────────────

def _build_reasoning_trace(
    state: str,
    node_key: str,
    ar: AllocationAlignmentResult,
    etf_contributors: list[tuple[str, float, str]],
    saturation_ratio: float,
    indirect_ratio: float,
) -> str:
    """Build a plain-English reasoning trace explaining the recommendation state.

    This is the explainability backbone — critical for operator trust and
    governance lineage.
    """
    if not state or state == "ACTIVE":
        # Only add trace when ETF decomposition is meaningful context
        etf_derived = float(ar.etf_derived_actual_pct or 0.0)
        if etf_derived <= 0.0:
            return ""
        top = ", ".join(f"{s} ({p:.1f}%)" for s, p, _ in etf_contributors[:3])
        return (
            f"Effective {node_key} exposure: {ar.effective_actual_pct:.1f}% "
            f"(direct: {ar.direct_actual_pct:.1f}%, ETF-derived: {etf_derived:.1f}%"
            + (f" via {top}" if top else "")
            + f"). Target: {ar.tactical_target_pct:.1f}%. Drift warrants action."
        )

    top = ", ".join(f"{s} ({p:.1f}%)" for s, p, _ in etf_contributors[:3])
    effective = float(ar.effective_actual_pct or 0.0)
    direct = float(ar.direct_actual_pct or 0.0)
    etf_derived = float(ar.etf_derived_actual_pct or 0.0)
    target = float(ar.tactical_target_pct or 0.0)

    if state == "INFORMATIONAL":
        trace = (
            f"Recommendation is informational: {saturation_ratio * 100:.0f}% of the "
            f"{target:.1f}% {node_key} target is already satisfied via effective exposure "
            f"({effective:.1f}% total = {direct:.1f}% direct + {etf_derived:.1f}% ETF-derived)."
        )
        if top:
            trace += f" Primary ETF contributors: {top}."
        trace += (
            " No immediate action required; monitor if composition shifts toward "
            "concentrated or lower-quality vehicles."
        )

    elif state == "DOWNGRADED":
        trace = (
            f"Recommendation downgraded: {indirect_ratio * 100:.0f}% of current "
            f"{node_key} exposure ({effective:.1f}%) arrives indirectly via ETF "
            f"decomposition (direct: {direct:.1f}%, ETF-derived: {etf_derived:.1f}%)."
        )
        if top:
            trace += f" ETF contributors: {top}."
        if ar.drift_direction == "UNDERWEIGHT":
            trace += (
                " Portfolio may already have meaningful indirect exposure through "
                "existing funds. Consider whether the remaining gap ({:.1f}pp) "
                "requires additional direct or ETF exposure, or whether current "
                "indirect coverage is sufficient for strategic intent.".format(
                    abs(float(ar.drift_pct or 0.0))
                )
            )
        else:  # OVERWEIGHT
            trace += (
                " The overweight condition is driven primarily by ETF indirect "
                "exposure. Reducing it requires trimming ETF holdings, which will "
                "also reduce exposure in related allocation buckets."
            )

    else:
        trace = ""

    return trace


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Downgrade pass
# ─────────────────────────────────────────────────────────────────────────────

def _apply_downgrade_pass(
    recs: list[PortfolioRecommendation],
    alignment_map: dict[str, AllocationAlignmentResult],
    holdings: list[PortfolioHolding],
) -> list[PortfolioRecommendation]:
    """Apply DOWNGRADE-FIRST pass to all allocation drift recommendations.

    Only INCREASE_UNDERWEIGHT and REDUCE_OVERWEIGHT are candidates for
    state mutation.  All other recommendation types pass through unchanged.
    """
    result: list[PortfolioRecommendation] = []
    for rec in recs:
        if rec.recommendation_type not in ("INCREASE_UNDERWEIGHT", "REDUCE_OVERWEIGHT"):
            result.append(rec)
            continue

        node_key = rec.affected_node_key
        if not node_key or node_key not in alignment_map:
            result.append(rec)
            continue

        ar = alignment_map[node_key]
        sat = _compute_node_saturation(ar)
        etf_contributors = _identify_etf_contributors(node_key, holdings)

        saturation_ratio = sat["saturation_ratio"]
        indirect_ratio = sat["indirect_ratio"]

        if rec.recommendation_type == "INCREASE_UNDERWEIGHT":
            state = _determine_rec_state_underweight(
                saturation_ratio, indirect_ratio, etf_contributors
            )
        else:
            state = _determine_rec_state_overweight(
                saturation_ratio, indirect_ratio, etf_contributors
            )

        confidence = _adjust_confidence(rec.confidence, state, etf_contributors)
        trace = _build_reasoning_trace(
            state, node_key, ar, etf_contributors, saturation_ratio, indirect_ratio
        )
        etf_syms = tuple(sym for sym, _, _ in etf_contributors[:6])

        result.append(replace(
            rec,
            rec_state=state,
            reasoning_trace=trace,
            confidence=confidence,
            direct_exposure_pct=sat["direct"],
            etf_derived_exposure_pct=sat["etf_derived"],
            effective_exposure_pct=sat["effective"],
            etf_contributors=etf_syms,
        ))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Hierarchy-aware recommendation collapse
# ─────────────────────────────────────────────────────────────────────────────

def _apply_hierarchy_collapse(
    recs: list[PortfolioRecommendation],
) -> list[PortfolioRecommendation]:
    """Downgrade parent-level recs to INFORMATIONAL when a more specific
    descendant recommendation exists for the same direction.

    This prevents spam like:
      ACTIVE: Reduce US Equities (+20% drift)
      ACTIVE: Reduce US Mega (+15% drift)
      ACTIVE: Reduce US Mega Hyper (+8% drift)

    After collapse:
      INFORMATIONAL: Reduce US Equities  ← subsumed by child
      INFORMATIONAL: Reduce US Mega      ← subsumed by child
      ACTIVE:        Reduce US Mega Hyper
    """
    # Only consider allocation drift recs that are ACTIVE or DOWNGRADED
    directional = [
        r for r in recs
        if r.recommendation_type in ("INCREASE_UNDERWEIGHT", "REDUCE_OVERWEIGHT")
        and r.rec_state in ("ACTIVE", "DOWNGRADED")
        and r.affected_node_key
    ]

    # Build set of rec IDs to collapse (parent subsumed by a more specific child)
    to_collapse: dict[str, list[str]] = {}  # rec_id → list of child node_keys
    for parent in directional:
        children = [
            child.affected_node_key
            for child in directional
            if child.recommendation_id != parent.recommendation_id
            and child.recommendation_type == parent.recommendation_type
            and child.affected_node_key.startswith(parent.affected_node_key + ".")
        ]
        if children:
            to_collapse[parent.recommendation_id] = children

    result: list[PortfolioRecommendation] = []
    for rec in recs:
        if rec.recommendation_id in to_collapse:
            child_keys = to_collapse[rec.recommendation_id]
            collapse_note = (
                f"Hierarchy context: more specific recommendation(s) generated for "
                f"{', '.join(child_keys[:2])}. "
                "This parent-level view is retained as informational context only."
            )
            existing = rec.reasoning_trace
            full_trace = (collapse_note + " " + existing).strip() if existing else collapse_note
            result.append(replace(
                rec,
                rec_state="INFORMATIONAL",
                reasoning_trace=full_trace,
            ))
        else:
            result.append(rec)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Thematic concentration detection
# ─────────────────────────────────────────────────────────────────────────────

# Portfolio-weighted thematic exposure thresholds (% of total portfolio).
# Crossing these triggers an INFORMATIONAL thematic concentration rec.
_THEMATIC_CONCENTRATION_THRESHOLDS: dict[str, float] = {
    "AI_INFRA":                   15.0,
    "SEMICONDUCTOR_CONCENTRATION": 10.0,
    "MEGA_TECH_CONCENTRATION":    20.0,
    "GROWTH_MOMENTUM":            30.0,
    "ENERGY_TRANSITION":          12.0,
    "RATE_SENSITIVITY":           20.0,
}

# Human-readable theme labels
_THEME_LABELS: dict[str, str] = {
    "AI_INFRA":                   "AI Infrastructure",
    "SEMICONDUCTOR_CONCENTRATION": "Semiconductor Concentration",
    "MEGA_TECH_CONCENTRATION":    "Mega-Tech Concentration",
    "GROWTH_MOMENTUM":            "Growth Momentum",
    "ENERGY_TRANSITION":          "Energy Transition",
    "RATE_SENSITIVITY":           "Rate Sensitivity",
}


def _aggregate_thematic_exposure(
    holdings: list[PortfolioHolding],
) -> dict[str, float]:
    """Compute portfolio-weighted thematic exposure scores (% of portfolio).

    Each holding's exposure_thematic_mix contains per-theme intensity flags
    (0–100, independent — they do NOT sum to 100). Weighting by portfolio %
    gives a portfolio-level thematic exposure measure.

    Example: NVDA 5% with AI_INFRA=80% → contributes 5 × 0.80 = 4.0%
    """
    totals: dict[str, float] = {}
    for h in holdings:
        weight = h.percent_of_portfolio / 100.0  # 0.0–1.0
        for theme, intensity in h.exposure_thematic_mix:
            contribution = weight * (intensity / 100.0) * 100.0  # back to portfolio %
            totals[theme] = totals.get(theme, 0.0) + contribution
    return totals


def _maybe_thematic_concentration_rec(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    now_utc: str,
) -> Optional[PortfolioRecommendation]:
    """Generate an INFORMATIONAL thematic concentration rec if thresholds are crossed.

    Returns None if no thematic concentration is detected.
    """
    thematic = _aggregate_thematic_exposure(holdings)
    triggered = [
        (theme, thematic[theme])
        for theme, threshold in _THEMATIC_CONCENTRATION_THRESHOLDS.items()
        if thematic.get(theme, 0.0) > threshold
    ]
    if not triggered:
        return None

    triggered.sort(key=lambda x: x[1], reverse=True)
    label_strs = [
        f"{_THEME_LABELS.get(t, t.replace('_', ' ').title())}: {p:.1f}%"
        for t, p in triggered
    ]
    top_themes = [_THEME_LABELS.get(t, t) for t, _ in triggered[:2]]
    title = f"Thematic concentration: {' + '.join(top_themes)}"

    rationale = (
        "Portfolio-weighted thematic exposure analysis detected high concentration "
        "across related themes: "
        + "; ".join(label_strs)
        + ". These themes may overlap significantly even when raw allocation buckets "
        "appear diversified. Example: QQQ + XLK + SMH together create layered "
        "AI/semiconductor/mega-tech exposure that does not show up in a simple "
        "market-cap bucket analysis."
    )

    # Holdings contributing to triggered themes
    triggered_theme_keys = {t for t, _ in triggered}
    contributing = [
        h.symbol.upper()
        for h in holdings
        if any(theme in triggered_theme_keys for theme, _ in h.exposure_thematic_mix)
    ]
    # Sort by portfolio weight
    contributing_by_weight = sorted(
        contributing,
        key=lambda s: next(
            (h.percent_of_portfolio for h in holdings if h.symbol.upper() == s), 0.0
        ),
        reverse=True,
    )

    trace = (
        "Thematic concentration detected via ETF decomposition registry. "
        + " | ".join(label_strs)
        + f". Contributing holdings: {', '.join(contributing_by_weight[:6])}."
    )

    return PortfolioRecommendation(
        recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        recommendation_type="IMPROVE_SECTOR_EXPOSURE",
        priority=2,
        confidence="MEDIUM",
        title=title,
        rationale=rationale,
        evidence_summary="Thematic exposure aggregated via Phase B ETF decomposition registry.",
        affected_node_key=None,
        affected_symbols=tuple(contributing_by_weight[:8]),
        drift_pct=None,
        severity="MODERATE",
        replay_run_ids=(),
        created_at_utc=now_utc,
        rec_state="INFORMATIONAL",
        reasoning_trace=trace,
        card_type="ACTION",
        execution_state="EXECUTABLE",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase D — Strategic trim recommendations (D.8)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_strategic_trim_recs(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    strategic_profiles: list,           # list[HoldingStrategicProfile]
    overlays: list[SecurityIntelligenceOverlay],
    alignment_results: list[AllocationAlignmentResult],
    now_utc: str,
) -> list[PortfolioRecommendation]:
    """Generate STRATEGIC_TRIM_CANDIDATE and STRATEGIC_RETAIN_SIGNAL recommendations.

    D.8 evolution: instead of "Reduce Semiconductor Exposure", the system now
    identifies the most expendable holding within each overweight thematic cluster
    and explains exactly why that holding ranks above peers.

    Strategy:
      1. Group REDUCIBLE / REDUNDANT / CONCENTRATION_RISK profiles by their
         thematic_overlap_clusters to produce cluster-level trim recs.
      2. Identify the top-trim holding per cluster and call it out by name.
      3. Generate one STRATEGIC_RETAIN_SIGNAL rec per CORE_COMPOUNDER /
         HIGH_CONVICTION_RETAIN profile (capped to keep rec count manageable).
    """
    recs: list[PortfolioRecommendation] = []

    # ── Trim candidates by thematic cluster ──────────────────────────────────
    _TRIM_CLASSIFICATIONS = frozenset({
        "REDUCIBLE",
        "REDUNDANT_EXPOSURE",
        "CONCENTRATION_RISK",
    })

    # Build cluster → [profiles] map for trim-worthy holdings
    cluster_profiles: dict[str, list] = {}
    for p in strategic_profiles:
        if p.strategic_classification not in _TRIM_CLASSIFICATIONS:
            continue
        clusters = p.thematic_overlap_clusters if p.thematic_overlap_clusters else ("GENERAL",)
        for cluster in clusters:
            cluster_profiles.setdefault(cluster, []).append(p)

    # One STRATEGIC_TRIM_CANDIDATE rec per cluster (capped at 4 clusters)
    seen_rec_symbols: set[str] = set()
    _THEME_LABELS_LOCAL: dict[str, str] = {
        "AI_INFRA":                    "AI Infrastructure",
        "SEMICONDUCTOR_CONCENTRATION": "Semiconductor",
        "MEGA_TECH_CONCENTRATION":     "Mega-Tech",
        "GROWTH_MOMENTUM":             "Growth Momentum",
        "ENERGY_TRANSITION":           "Energy Transition",
        "RATE_SENSITIVITY":            "Rate Sensitivity",
        "GENERAL":                     "Portfolio",
    }

    for cluster_key, profiles in sorted(
        cluster_profiles.items(),
        key=lambda x: -max(p.trim_priority_score for p in x[1]),
    )[:4]:
        # Sort by trim priority descending — top is most expendable
        profiles_sorted = sorted(profiles, key=lambda p: -p.trim_priority_score)
        top = profiles_sorted[0]

        if top.symbol in seen_rec_symbols:
            continue
        seen_rec_symbols.add(top.symbol)

        cluster_label = _THEME_LABELS_LOCAL.get(cluster_key, cluster_key.replace("_", " ").title())
        peer_syms = [p.symbol for p in profiles_sorted[1:4]]
        peer_str = f" Cluster peers: {', '.join(peer_syms)}." if peer_syms else ""

        title = (
            f"{cluster_label} cluster: {top.symbol} is most expendable"
            f" (trim score: {top.trim_priority_score:.0f}/100)"
        )
        rationale = (
            f"{cluster_label} exposure is shared across multiple holdings. "
            f"{top.symbol} ranks as the most trim-worthy position in this cluster "
            f"({top.strategic_classification}). "
            f"{top.trim_rationale}{peer_str}"
        )

        # Severity based on trim score
        if top.trim_priority_score >= 70:
            severity = "HIGH"
            confidence = "HIGH"
            priority = 2
        elif top.trim_priority_score >= 50:
            severity = "MODERATE"
            confidence = "MEDIUM"
            priority = 3
        else:
            severity = "LOW"
            confidence = "LOW"
            priority = 4

        all_cluster_syms = tuple(p.symbol for p in profiles_sorted[:6])
        trace = (
            f"STI cluster: {cluster_key} | "
            f"Top trim candidate: {top.symbol} (score={top.trim_priority_score:.0f}) | "
            f"{top.classification_trace}"
        )

        recs.append(PortfolioRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            recommendation_type="STRATEGIC_TRIM_CANDIDATE",
            priority=priority,
            confidence=confidence,
            title=title,
            rationale=rationale,
            evidence_summary=(
                f"STI trim priority score: {top.trim_priority_score:.0f}/100. "
                f"Thematic redundancy: {top.thematic_redundancy_score:.0f}/100. "
                f"Strategic importance: {top.strategic_importance}. "
                f"Exposure origin: {top.exposure_origin}."
            ),
            affected_node_key=None,
            affected_symbols=all_cluster_syms,
            drift_pct=None,
            severity=severity,
            replay_run_ids=(),
            created_at_utc=now_utc,
            rec_state="ACTIVE",
            reasoning_trace=trace,
            card_type="ACTION",
            execution_state="EXECUTABLE",
        ))

    # ── Strategic retain signals (cap to 2) ───────────────────────────────────
    _RETAIN_CLASSIFICATIONS = frozenset({"HIGH_CONVICTION_RETAIN", "CORE_COMPOUNDER"})
    retain_candidates = sorted(
        [p for p in strategic_profiles if p.strategic_classification in _RETAIN_CLASSIFICATIONS],
        key=lambda p: p.trim_priority_score,   # lowest trim = strongest retain
    )[:2]

    for p in retain_candidates:
        recs.append(PortfolioRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            recommendation_type="STRATEGIC_RETAIN_SIGNAL",
            priority=5,
            confidence="HIGH",
            title=f"{p.symbol}: {p.strategic_classification.replace('_', ' ').title()}",
            rationale=p.retain_rationale,
            evidence_summary=(
                f"STI classification: {p.strategic_classification}. "
                f"Trim score: {p.trim_priority_score:.0f}/100 (low = retain). "
                f"Strategic importance: {p.strategic_importance}."
            ),
            affected_node_key=None,
            affected_symbols=(p.symbol,),
            drift_pct=None,
            severity="LOW",
            replay_run_ids=(),
            created_at_utc=now_utc,
            rec_state="INFORMATIONAL",
            reasoning_trace=p.classification_trace,
            card_type="OBSERVATION",
            execution_state="INFORMATIONAL_ONLY",
        ))

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Recommendation consistency validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_recommendation_consistency(
    recs: list[PortfolioRecommendation],
) -> list[str]:
    """Validate recommendation set for contradictions and structural problems.

    Returns a list of warning strings (WARN-not-fail-close design).
    Warnings are advisory — they do NOT prevent recommendations from being returned.
    """
    warnings: list[str] = []

    # Group non-suppressed recs by node_key
    by_node: dict[str, list[PortfolioRecommendation]] = defaultdict(list)
    for r in recs:
        if r.affected_node_key and r.rec_state != "SUPPRESSED":
            by_node[r.affected_node_key].append(r)

    for node_key, node_recs in by_node.items():
        active_types = {
            r.recommendation_type
            for r in node_recs
            if r.rec_state in ("ACTIVE", "DOWNGRADED")
        }

        # Contradictory pair: both REDUCE and INCREASE active for same node
        if "REDUCE_OVERWEIGHT" in active_types and "INCREASE_UNDERWEIGHT" in active_types:
            warnings.append(
                f"WARN[rec_consistency]: Contradictory recs for {node_key}: "
                "both REDUCE_OVERWEIGHT and INCREASE_UNDERWEIGHT are active simultaneously."
            )

        # Duplicate active recs of same type for same node
        for rec_type in active_types:
            same_type = [
                r for r in node_recs
                if r.recommendation_type == rec_type
                and r.rec_state in ("ACTIVE", "DOWNGRADED")
            ]
            if len(same_type) > 1:
                warnings.append(
                    f"WARN[rec_consistency]: {len(same_type)} duplicate active "
                    f"{rec_type} recommendations for {node_key}."
                )

    # Check for impossible simultaneous allocation advice
    # (e.g. both INCREASE and REDUCE for parent and child if they conflict)
    all_active = [r for r in recs if r.rec_state in ("ACTIVE", "DOWNGRADED") and r.affected_node_key]
    for r1 in all_active:
        for r2 in all_active:
            if r1.recommendation_id >= r2.recommendation_id:
                continue
            key1, key2 = r1.affected_node_key, r2.affected_node_key
            # Parent-child with opposite directions
            is_hierarchy = key2.startswith(key1 + ".") or key1.startswith(key2 + ".")
            if is_hierarchy:
                if r1.recommendation_type != r2.recommendation_type:
                    warnings.append(
                        f"WARN[rec_consistency]: Conflicting hierarchy recs: "
                        f"{r1.recommendation_type} on {key1} vs "
                        f"{r2.recommendation_type} on {key2}."
                    )

    return warnings
