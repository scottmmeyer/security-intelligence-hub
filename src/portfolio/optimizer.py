"""Phase 7.3A — Parallel Portfolio Optimizer.

Computes Portfolio Improvement Score (PIS) for all candidate actions
in PARALLEL with the existing legacy recommendation engine.

Governance:
  - NEVER modifies existing recommendation content, order, or structure.
  - All optimizer output is metadata attached to existing recommendations.
  - The recommendation list returned by generate_recommendations() is UNCHANGED.
  - optimizer_metadata is additive only; it carries no UI authority until Phase 7.3D.

Public API:
  run_parallel_optimizer(...)           → dict[rec_id, OptimizerResult]
  score_security_candidate(...)         → OptimizerCandidate
  score_etf_candidate(...)              → OptimizerCandidate
  detect_conflicts(...)                 → list[dict]
"""

from __future__ import annotations

import dataclasses
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Result data structures (plain dicts for JSON-safe output — no frozen dataclass
# to keep the optimizer additions zero-breaking-change to existing models.py)
# ─────────────────────────────────────────────────────────────────────────────

def _make_candidate(
    *,
    symbol: str,
    candidate_type: str,                  # SECURITY | ETF
    target_node: str,
    composite_component: float,
    replay_component: float,
    node_gap_component: float,
    conviction_component: float,
    ess_component: float,
    trim_penalty: float,
    concentration_penalty: float,
    conflict_penalty: float,
    pis: float,
    mandate_gate: str,                    # PASS | SOFT_PASS | FAIL
    etf_gate: str,                        # PASS | FAIL | NA
    optimizer_status: str,                # ACTIONABLE | MANDATE_BLOCKED | ETF_GATED | SUPPRESSED
    ncs: float,
    suitability_tier: str,
    worsens_overweight: bool,
    conflict_nodes: list,
    composite_score: Optional[float],
    ess_score: Optional[str],
    replay_supported: bool,
    sti_tier: str,                        # CCL | HCA | TGC | WTC | NA
    percent_of_portfolio: float,
) -> dict:
    return {
        "symbol": symbol,
        "candidate_type": candidate_type,
        "target_node": target_node,
        "components": {
            "composite_component": round(composite_component, 2),
            "replay_component": round(replay_component, 2),
            "node_gap_component": round(node_gap_component, 2),
            "conviction_component": round(conviction_component, 2),
            "ess_component": round(ess_component, 2),
            "trim_penalty": round(trim_penalty, 2),
            "concentration_penalty": round(concentration_penalty, 2),
            "conflict_penalty": round(conflict_penalty, 2),
        },
        "pis": round(pis, 2),
        "mandate_gate": mandate_gate,
        "etf_gate": etf_gate,
        "optimizer_status": optimizer_status,
        "ncs": round(ncs, 2),
        "suitability_tier": suitability_tier,
        "worsens_overweight": worsens_overweight,
        "conflict_nodes": list(conflict_nodes),
        "composite_score": composite_score,
        "ess_score": ess_score,
        "replay_supported": replay_supported,
        "sti_tier": sti_tier,
        "percent_of_portfolio": round(percent_of_portfolio, 4),
    }


def _make_result(
    *,
    rec_id: str,
    rec_type: str,
    target_node: Optional[str],
    legacy_vehicles: list,
    candidates: list,
    preferred_candidate: Optional[dict],
    optimizer_decision: str,             # SECURITY_SUPERIOR | ETF_ADEQUATE | MANDATE_BLOCKED |
                                         # NO_CANDIDATES | REDUCE_COHERENT | NOT_APPLICABLE
    conflicts_detected: list,
    mandate_blocked: bool,
    optimizer_version: str = "7.3A",
) -> dict:
    return {
        "rec_id": rec_id,
        "rec_type": rec_type,
        "target_node": target_node,
        "legacy_vehicles": list(legacy_vehicles),
        "candidates": list(candidates),
        "preferred_candidate": preferred_candidate,
        "optimizer_decision": optimizer_decision,
        "conflicts_detected": list(conflicts_detected),
        "mandate_blocked": mandate_blocked,
        "optimizer_version": optimizer_version,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STI tier extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sti_tier_from_profiles(symbol: str, profiles: list) -> str:
    """Extract narrative tier from HoldingStrategicProfile list (any format)."""
    sym = symbol.upper()
    for p in profiles:
        if dataclasses.is_dataclass(p) and not isinstance(p, type):
            psym = getattr(p, "symbol", "") or ""
            if psym.upper() == sym:
                return str(getattr(p, "narrative_tier", "") or "TGC")
        elif isinstance(p, dict):
            psym = p.get("symbol") or ""
            if psym.upper() == sym:
                return str(p.get("narrative_tier") or "TGC")
    return "TGC"


def _trim_score_from_profiles(symbol: str, profiles: list) -> float:
    """Extract trim_priority_score from HoldingStrategicProfile list (any format)."""
    sym = symbol.upper()
    for p in profiles:
        if dataclasses.is_dataclass(p) and not isinstance(p, type):
            psym = getattr(p, "symbol", "") or ""
            if psym.upper() == sym:
                val = getattr(p, "trim_priority_score", None)
                return float(val) if val is not None else 0.0
        elif isinstance(p, dict):
            psym = p.get("symbol") or ""
            if psym.upper() == sym:
                val = p.get("trim_priority_score")
                return float(val) if val is not None else 0.0
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Mandate gate evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _mandate_gate_for_node(
    node_key: Optional[str],
    mandate_interpretations: list,
) -> tuple[str, bool]:
    """Return (gate_result, mandate_blocked) for a given target node.

    gate_result: PASS | SOFT_PASS | FAIL
    mandate_blocked: True if INFORMATIONAL or INTENTIONAL drift label

    For REDUCE_OVERWEIGHT nodes, mandate never blocks (reducing OW is always valid).
    For INCREASE_UNDERWEIGHT nodes, INTENTIONAL_UNDERWEIGHT mandate label → FAIL.
    """
    if not node_key:
        return "PASS", False

    for mi in mandate_interpretations:
        mi_node = (mi.node_key if dataclasses.is_dataclass(mi) else mi.get("node_key", ""))
        if mi_node != node_key:
            continue

        if dataclasses.is_dataclass(mi):
            urgency = str(mi.mandate_urgency or "")
            label = str(mi.mandate_drift_label or "")
            suppress = bool(mi.suppress_recommendation)
        else:
            urgency = str(mi.get("mandate_urgency", "") or "")
            label = str(mi.get("mandate_drift_label", "") or "")
            suppress = bool(mi.get("suppress_recommendation", False))

        if urgency == "INFORMATIONAL" or suppress or "INTENTIONAL" in label:
            return "FAIL", True
        return "PASS", False

    return "PASS", False


# ─────────────────────────────────────────────────────────────────────────────
# Overweight node lookup helpers
# ─────────────────────────────────────────────────────────────────────────────

def _overweight_nodes_from_alignment(alignment_results: list) -> dict:
    """Return {node_key: drift_pct} for all OVERWEIGHT nodes with MODERATE+ severity."""
    result = {}
    for ar in alignment_results:
        if dataclasses.is_dataclass(ar):
            direction = ar.drift_direction
            severity = ar.severity
            node = ar.node_key
            drift = ar.drift_pct
        else:
            direction = ar.get("drift_direction", "")
            severity = ar.get("severity", "")
            node = ar.get("node_key", "")
            drift = float(ar.get("drift_pct", 0) or 0)
        if direction == "OVERWEIGHT" and severity in ("HIGH", "MODERATE"):
            result[node] = drift
    return result


def _node_gap_from_alignment(node_key: str, alignment_results: list) -> float:
    """Return drift_pct for a specific node. Negative = underweight."""
    for ar in alignment_results:
        if dataclasses.is_dataclass(ar):
            if ar.node_key == node_key:
                return ar.drift_pct
        else:
            if ar.get("node_key") == node_key:
                return float(ar.get("drift_pct", 0) or 0)
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Holdings node matching
# ─────────────────────────────────────────────────────────────────────────────

def _holding_in_target_node(holding, node_key: str) -> bool:
    """Return True if a PortfolioHolding (dataclass or dict) is in target_node_key.

    Uses the same hierarchy logic as runner._holding_matches_node():
      EQUITIES                  → asset_class=EQUITIES
      EQUITIES.US               → + geography=US
      EQUITIES.US.LARGE         → + market_cap_bucket=LARGE
      EQUITIES.US.MEGA.HYPER    → + mega_subtier=HYPER_MEGA
    """
    if dataclasses.is_dataclass(holding):
        ac = str(getattr(holding, "asset_class", "") or "").upper()
        geo = str(getattr(holding, "geography", "") or "").upper()
        mcb = str(getattr(holding, "market_cap_bucket", "") or "").upper()
        mst = str(getattr(holding, "mega_subtier", "") or "").upper()
        pct = float(getattr(holding, "percent_of_portfolio", 0) or 0)
        sym = str(getattr(holding, "symbol", "") or "").upper()
        op_state = str(getattr(holding, "operational_state", "ACTIVE_POSITION") or "ACTIVE_POSITION")
        is_cash_eq = bool(getattr(holding, "is_cash_equivalent", False))
    else:
        ac = str(holding.get("asset_class", "") or "").upper()
        geo = str(holding.get("geography", "") or "").upper()
        mcb = str(holding.get("market_cap_bucket", "") or "").upper()
        mst = str(holding.get("mega_subtier", "") or "").upper()
        pct = float(holding.get("percent_of_portfolio", 0) or 0)
        sym = str(holding.get("symbol", "") or "").upper()
        op_state = str(holding.get("operational_state", "ACTIVE_POSITION") or "ACTIVE_POSITION")
        is_cash_eq = bool(holding.get("is_cash_equivalent", False))

    # Skip cash/non-equity for equity node matching
    if is_cash_eq or ac in ("CASH", "FIXED_INCOME"):
        return False

    parts = node_key.upper().split(".")
    if not parts or parts[0] != ac:
        return False
    if len(parts) == 1:
        return True
    if len(parts) >= 2 and parts[1] != geo:
        return False
    if len(parts) == 2:
        return True
    if len(parts) >= 3 and parts[2] not in (mcb, "MEGA"):
        return False
    if len(parts) == 3 and parts[2] == "MEGA":
        return mcb == "MEGA"
    if len(parts) == 3:
        return True
    # 4-part: EQUITIES.US.MEGA.HYPER_MEGA etc.
    if len(parts) >= 4 and mcb == "MEGA":
        return parts[3] == mst
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Overlay signal extraction
# ─────────────────────────────────────────────────────────────────────────────

def _overlay_for_symbol(symbol: str, overlays: list) -> Optional[dict]:
    """Return overlay dict for a symbol, regardless of dataclass vs dict form."""
    sym = symbol.upper()
    for o in overlays:
        if dataclasses.is_dataclass(o):
            if str(getattr(o, "symbol", "") or "").upper() == sym:
                return dataclasses.asdict(o)
        elif isinstance(o, dict):
            if str(o.get("symbol", "") or "").upper() == sym:
                return o
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PIS computation for security candidates
# ─────────────────────────────────────────────────────────────────────────────

# T1 conflict penalty (applied when candidate worsens an overweight node)
_T1_CONFLICT_PENALTY = 20.0

# Security is a direct position in target node → 100% NCS
_SECURITY_NCS = 100.0

# ETF minimum NCS to pass the ETF gate
_ETF_MIN_NCS_PCT = 10.0

# Mandate blocked floor: PIS cannot be positive when mandate blocks action
_MANDATE_BLOCKED_PIS = 0.0


def score_security_candidate(
    symbol: str,
    target_node: str,
    node_gap: float,                    # drift_pct for the target node (negative = UW)
    composite_score: Optional[float],
    ess_score: Optional[str],
    replay_supported: bool,
    sti_tier: str,
    trim_priority_score: float,
    percent_of_portfolio: float,
    overweight_nodes: dict,             # {node_key: drift_pct} for all MODERATE+ OW nodes
    mandate_gate: str,
    mandate_blocked: bool,
) -> dict:
    """Score a portfolio security as a candidate for an underweight node deployment.

    Returns an OptimizerCandidate dict.
    """
    # A direct holding in the target node has perfect NCS.
    # Securities never create cross-node leakage.
    conflict_nodes: list[str] = []
    conflict_penalty = 0.0

    # ── Conviction quality (composite signal; 0–30) ──────────────────────────
    composite_component = min(float(composite_score or 0) * 6.0, 30.0)

    # ── Replay support (0 or 20) ─────────────────────────────────────────────
    replay_component = 20.0 if replay_supported else 0.0

    # ── Node gap alignment (deploying into UW node earns up to 20 pts) ───────
    if node_gap < 0:  # underweight
        node_gap_component = min(abs(node_gap) * 2.0, 20.0)
    else:
        node_gap_component = 0.0

    # ── Conviction / STI tier (0–10) ─────────────────────────────────────────
    conviction_component = {
        "CORE_CONVICTION_LEADER": 10.0,
        "HIGH_CONVICTION_ANCHOR": 7.0,
        "CCL": 10.0,
        "HCA": 7.0,
        "TGC": 3.0,
        "WTC": 0.0,
    }.get(sti_tier, 3.0)

    # ── ESS bonus (0–5) ──────────────────────────────────────────────────────
    ess = (ess_score or "").upper()
    if "VERY_BULLISH" in ess:
        ess_component = 5.0
    elif "BULLISH" in ess:
        ess_component = 3.0
    else:
        ess_component = 0.0

    # ── Trim penalty — a high trim score means STI flags exit risk ───────────
    trim_penalty = min(float(trim_priority_score or 0) * 0.2, 20.0)

    # ── Concentration penalty (positions >5% already concentrated) ───────────
    concentration_penalty = 0.0
    if percent_of_portfolio > 5.0:
        concentration_penalty = min((percent_of_portfolio - 5.0) * 3.0, 15.0)

    # ── Assemble PIS ─────────────────────────────────────────────────────────
    raw_pis = (
        composite_component
        + replay_component
        + node_gap_component
        + conviction_component
        + ess_component
        - trim_penalty
        - concentration_penalty
        - conflict_penalty
    )

    # Mandate gate overrides PIS to 0 for blocked actions
    if mandate_blocked:
        final_pis = _MANDATE_BLOCKED_PIS
        optimizer_status = "MANDATE_BLOCKED"
    else:
        final_pis = max(0.0, raw_pis)
        optimizer_status = "ACTIONABLE" if final_pis > 0 else "SUPPRESSED"

    return _make_candidate(
        symbol=symbol,
        candidate_type="SECURITY",
        target_node=target_node,
        composite_component=composite_component,
        replay_component=replay_component,
        node_gap_component=node_gap_component,
        conviction_component=conviction_component,
        ess_component=ess_component,
        trim_penalty=trim_penalty,
        concentration_penalty=concentration_penalty,
        conflict_penalty=conflict_penalty,
        pis=round(final_pis, 2),
        mandate_gate=mandate_gate,
        etf_gate="NA",
        optimizer_status=optimizer_status,
        ncs=_SECURITY_NCS,
        suitability_tier="NA",
        worsens_overweight=False,
        conflict_nodes=conflict_nodes,
        composite_score=composite_score,
        ess_score=ess_score,
        replay_supported=replay_supported,
        sti_tier=sti_tier,
        percent_of_portfolio=percent_of_portfolio,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PIS computation for ETF candidates
# ─────────────────────────────────────────────────────────────────────────────

def score_etf_candidate(
    symbol: str,
    target_node: str,
    node_gap: float,
    suitability_note: dict,             # VehicleSuitabilityNote as dict
    overweight_nodes: dict,             # {node_key: drift_pct}
    mandate_gate: str,
    mandate_blocked: bool,
) -> dict:
    """Score an ETF vehicle as a candidate for an underweight node deployment.

    ETF candidates receive zero conviction/replay/ESS/STI components.
    They are scored on: node gap coverage, NCS quality, and conflict penalties.
    """
    # Extract suitability fields
    target_coverage = float(suitability_note.get("target_node_coverage_pct", 0) or 0)
    off_target = float(suitability_note.get("off_target_exposure_pct", 0) or 0)
    overlap_ow = float(suitability_note.get("overlap_with_existing_pct", 0) or 0)
    worsens = bool(suitability_note.get("worsens_existing_overweight", False))
    suit_score = float(suitability_note.get("suitability_score", 0) or 0)
    suit_tier = str(suitability_note.get("suitability_tier", "LOW") or "LOW")

    # Node Coverage Score (NCS): target_coverage penalized by OW worsening
    # Overweight severity weight: MODERATE = 0.6 (any OW node we have is MODERATE)
    ow_leakage_penalty = overlap_ow * 0.6 if worsens else 0.0
    ncs = max(0.0, target_coverage - ow_leakage_penalty)

    # ── ETF gate ─────────────────────────────────────────────────────────────
    # ETF must pass: suitability >= MEDIUM, NCS >= 10%, no worsening OW
    etf_gate_fails = []
    if suit_tier == "LOW":
        etf_gate_fails.append(f"suitability={suit_tier}")
    if ncs < _ETF_MIN_NCS_PCT:
        etf_gate_fails.append(f"NCS={ncs:.1f}%<{_ETF_MIN_NCS_PCT}%")
    if worsens:
        etf_gate_fails.append("worsens_overweight=True")

    etf_gate = "PASS" if not etf_gate_fails else "FAIL"
    etf_gate_reason = "; ".join(etf_gate_fails) if etf_gate_fails else ""

    # ── Components (ETF has no conviction/replay/ESS/STI signals) ────────────
    composite_component = 0.0
    replay_component = 0.0
    conviction_component = 0.0
    ess_component = 0.0
    trim_penalty = 0.0

    # Node gap component — same logic as security, but scaled by NCS/100
    # (deploying $10K into a 15% NCS ETF delivers only 15% of node benefit)
    if node_gap < 0:
        raw_gap_component = min(abs(node_gap) * 2.0, 20.0)
        node_gap_component = raw_gap_component * (ncs / 100.0)
    else:
        node_gap_component = 0.0

    # Conflict penalty for T1 (ETF worsens existing overweight)
    conflict_nodes = []
    conflict_penalty = 0.0
    if worsens:
        conflict_nodes.append("OVERWEIGHT_NODE_WORSENED")
        conflict_penalty = _T1_CONFLICT_PENALTY

    # Concentration penalty — ETFs don't create position-level concentration
    concentration_penalty = 0.0

    # ── Assemble PIS ─────────────────────────────────────────────────────────
    raw_pis = (
        composite_component
        + replay_component
        + node_gap_component
        + conviction_component
        + ess_component
        - trim_penalty
        - concentration_penalty
        - conflict_penalty
    )

    # Mandate gate
    if mandate_blocked:
        final_pis = _MANDATE_BLOCKED_PIS
        optimizer_status = "MANDATE_BLOCKED"
    elif etf_gate == "FAIL":
        # ETF gate failure — PIS still computed but status reflects the block
        final_pis = max(0.0, raw_pis * 0.3)  # heavy discount, not full zero
        optimizer_status = "ETF_GATED"
    else:
        final_pis = max(0.0, raw_pis)
        optimizer_status = "ACTIONABLE" if final_pis > 0 else "SUPPRESSED"

    return _make_candidate(
        symbol=symbol,
        candidate_type="ETF",
        target_node=target_node,
        composite_component=composite_component,
        replay_component=replay_component,
        node_gap_component=node_gap_component,
        conviction_component=conviction_component,
        ess_component=ess_component,
        trim_penalty=trim_penalty,
        concentration_penalty=concentration_penalty,
        conflict_penalty=conflict_penalty,
        pis=round(final_pis, 2),
        mandate_gate=mandate_gate,
        etf_gate=etf_gate + (f" [{etf_gate_reason}]" if etf_gate_reason else ""),
        optimizer_status=optimizer_status,
        ncs=round(ncs, 2),
        suitability_tier=suit_tier,
        worsens_overweight=worsens,
        conflict_nodes=conflict_nodes,
        composite_score=None,
        ess_score=None,
        replay_supported=False,
        sti_tier="NA",
        percent_of_portfolio=0.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Conflict detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_conflicts(recs_with_overlay: list) -> list:
    """Detect T1/T2/T3 conflicts across the full recommendation set.

    recs_with_overlay: list of rec dicts (from recs_with_drilldown, already have
    mandate_label, mandate_urgency fields from build_mandate_recommendation_overlay).

    Returns list of conflict dicts: {conflict_type, rec_a_id, rec_b_id, description, severity}
    """
    conflicts = []
    build_recs = [
        r for r in recs_with_overlay
        if r.get("recommendation_type") == "INCREASE_UNDERWEIGHT"
        and r.get("severity") in ("HIGH", "MODERATE")
    ]
    reduce_recs = [
        r for r in recs_with_overlay
        if r.get("recommendation_type") == "REDUCE_OVERWEIGHT"
        and r.get("severity") in ("HIGH", "MODERATE")
    ]

    # T1: Build rec uses a vehicle that worsens an OW node being Reduced
    for br in build_recs:
        veh_notes = br.get("vehicle_suitability_notes") or []
        for note in veh_notes:
            if isinstance(note, dict) and note.get("worsens_existing_overweight"):
                # Find which Reduce rec is affected
                for rr in reduce_recs:
                    rr_node = rr.get("affected_node_key", "")
                    conflicts.append({
                        "conflict_type": "T1",
                        "rec_a_id": br.get("recommendation_id", ""),
                        "rec_b_id": rr.get("recommendation_id", ""),
                        "description": (
                            f"Build {br.get('affected_node_key')} using {note.get('symbol')} "
                            f"worsens existing overweight at {rr_node}"
                        ),
                        "severity": "HIGH",
                        "vehicle": note.get("symbol"),
                    })
                    break  # one conflict per vehicle is enough

    # T2: Two build recs share the same vehicle
    vehicle_to_recs: dict = {}
    for br in build_recs:
        symbols = br.get("affected_symbols") or []
        for sym in symbols:
            if sym not in vehicle_to_recs:
                vehicle_to_recs[sym] = []
            vehicle_to_recs[sym].append(br)
    for sym, recs_for_sym in vehicle_to_recs.items():
        if len(recs_for_sym) >= 2:
            for i in range(len(recs_for_sym)):
                for j in range(i + 1, len(recs_for_sym)):
                    conflicts.append({
                        "conflict_type": "T2",
                        "rec_a_id": recs_for_sym[i].get("recommendation_id", ""),
                        "rec_b_id": recs_for_sym[j].get("recommendation_id", ""),
                        "description": (
                            f"Vehicle {sym} appears in both "
                            f"'{recs_for_sym[i].get('affected_node_key')}' and "
                            f"'{recs_for_sym[j].get('affected_node_key')}' Build recs"
                        ),
                        "severity": "LOW",
                        "vehicle": sym,
                    })

    # T3: Engine severity != NONE but mandate urgency = INFORMATIONAL
    for r in recs_with_overlay:
        engine_sev = r.get("severity", "")
        mandate_urgency = r.get("mandate_urgency", "")
        if engine_sev in ("MODERATE", "HIGH") and mandate_urgency == "INFORMATIONAL":
            conflicts.append({
                "conflict_type": "T3",
                "rec_a_id": r.get("recommendation_id", ""),
                "rec_b_id": None,
                "description": (
                    f"Rec '{r.get('affected_node_key')}' has engine severity={engine_sev} "
                    f"but mandate urgency=INFORMATIONAL — contradictory output"
                ),
                "severity": "HIGH",
                "vehicle": None,
            })

    return conflicts


# ─────────────────────────────────────────────────────────────────────────────
# Main parallel optimizer entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_parallel_optimizer(
    recs_with_overlay: list,
    holdings: list,
    overlays: list,
    profiles: list,
    alignment_results: list,
    mandate_interpretations: list,
    total_mv: float = 0.0,
) -> dict:
    """Run the parallel optimizer across all recommendations.

    Returns a dict keyed by recommendation_id:
      {rec_id: OptimizerResult dict}

    IMPORTANT: This function is purely additive. It reads from:
      - recs_with_overlay: the already-completed recommendation list (with mandate overlay)
      - holdings, overlays, profiles, alignment_results, mandate_interpretations

    It does NOT modify any of these inputs.
    """
    overweight_nodes = _overweight_nodes_from_alignment(alignment_results)
    results: dict = {}

    # Index overlays and profiles for fast lookup
    overlay_index: dict = {}
    for o in overlays:
        if dataclasses.is_dataclass(o):
            sym = str(getattr(o, "symbol", "") or "").upper()
        else:
            sym = str(o.get("symbol", "") or "").upper()
        if sym:
            overlay_index[sym] = o

    profile_index: dict = {}
    for p in profiles:
        if dataclasses.is_dataclass(p):
            sym = str(getattr(p, "symbol", "") or "").upper()
        else:
            sym = str(p.get("symbol", "") or "").upper()
        if sym:
            profile_index[sym] = p

    # Run conflict detection across all recs (uses already-computed mandate overlay)
    all_conflicts = detect_conflicts(recs_with_overlay)

    # Build a set of T1-conflicted rec_ids for quick lookup
    t1_conflicted_build_recs = {
        c["rec_a_id"] for c in all_conflicts if c["conflict_type"] == "T1"
    }

    for rec_rd in recs_with_overlay:
        rec_id = rec_rd.get("recommendation_id", "")
        rec_type = rec_rd.get("recommendation_type", "")
        target_node = rec_rd.get("affected_node_key")

        # ── INCREASE_UNDERWEIGHT recs: score all candidates ───────────────────
        if rec_type == "INCREASE_UNDERWEIGHT" and target_node:
            mandate_gate, mandate_blocked = _mandate_gate_for_node(
                target_node, mandate_interpretations
            )
            node_gap = _node_gap_from_alignment(target_node, alignment_results)

            candidates = []
            legacy_vehicles = list(rec_rd.get("affected_symbols") or [])

            # ── Security candidates: holdings in the target node ──────────────
            for h in holdings:
                if not _holding_in_target_node(h, target_node):
                    continue

                sym = (
                    str(getattr(h, "symbol", "") or "").upper()
                    if dataclasses.is_dataclass(h)
                    else str(h.get("symbol", "") or "").upper()
                )
                pct = (
                    float(getattr(h, "percent_of_portfolio", 0) or 0)
                    if dataclasses.is_dataclass(h)
                    else float(h.get("percent_of_portfolio", 0) or 0)
                )

                ov = overlay_index.get(sym)
                if ov:
                    if dataclasses.is_dataclass(ov):
                        composite = getattr(ov, "composite_score", None)
                        ess = getattr(ov, "ess_score_text", None)
                        replay = bool(getattr(ov, "replay_supported", False))
                    else:
                        composite = ov.get("composite_score")
                        ess = ov.get("ess_score_text")
                        replay = bool(ov.get("replay_supported", False))
                else:
                    # Try to get from holding itself
                    if dataclasses.is_dataclass(h):
                        composite = getattr(h, "composite_score", None)
                        ess = getattr(h, "ess_score_text", None)
                    else:
                        composite = h.get("composite_score")
                        ess = h.get("ess_score_text")
                    replay = False

                sti_tier = _sti_tier_from_profiles(sym, profiles)
                trim_score = _trim_score_from_profiles(sym, profiles)

                candidate = score_security_candidate(
                    symbol=sym,
                    target_node=target_node,
                    node_gap=node_gap,
                    composite_score=float(composite) if composite is not None else None,
                    ess_score=str(ess) if ess else None,
                    replay_supported=replay,
                    sti_tier=sti_tier,
                    trim_priority_score=trim_score,
                    percent_of_portfolio=pct,
                    overweight_nodes=overweight_nodes,
                    mandate_gate=mandate_gate,
                    mandate_blocked=mandate_blocked,
                )
                candidates.append(candidate)

            # ── ETF candidates: from vehicle suitability notes on the rec ─────
            veh_notes = rec_rd.get("vehicle_suitability_notes") or []
            for note in veh_notes:
                if not isinstance(note, dict):
                    continue
                etf_sym = note.get("symbol", "")
                if not etf_sym:
                    continue
                candidate = score_etf_candidate(
                    symbol=etf_sym,
                    target_node=target_node,
                    node_gap=node_gap,
                    suitability_note=note,
                    overweight_nodes=overweight_nodes,
                    mandate_gate=mandate_gate,
                    mandate_blocked=mandate_blocked,
                )
                candidates.append(candidate)

            # Sort by PIS descending
            candidates.sort(key=lambda c: -c["pis"])

            preferred = candidates[0] if candidates else None

            # Determine optimizer_decision
            if mandate_blocked:
                optimizer_decision = "MANDATE_BLOCKED"
            elif not candidates:
                optimizer_decision = "NO_CANDIDATES"
            else:
                top = candidates[0]
                if top["candidate_type"] == "SECURITY" and top["pis"] > 0:
                    # Check if highest-PIS ETF is a competitor
                    top_etf = next(
                        (c for c in candidates if c["candidate_type"] == "ETF"),
                        None,
                    )
                    if top_etf is None or top["pis"] > top_etf["pis"]:
                        optimizer_decision = "SECURITY_SUPERIOR"
                    else:
                        optimizer_decision = "ETF_ADEQUATE"
                elif top["candidate_type"] == "ETF" and top["optimizer_status"] == "ACTIONABLE":
                    optimizer_decision = "ETF_ADEQUATE"
                else:
                    optimizer_decision = "NO_CANDIDATES"

            rec_conflicts = [
                c for c in all_conflicts
                if c["rec_a_id"] == rec_id or c["rec_b_id"] == rec_id
            ]

            results[rec_id] = _make_result(
                rec_id=rec_id,
                rec_type=rec_type,
                target_node=target_node,
                legacy_vehicles=legacy_vehicles,
                candidates=candidates,
                preferred_candidate=preferred,
                optimizer_decision=optimizer_decision,
                conflicts_detected=rec_conflicts,
                mandate_blocked=mandate_blocked,
            )

        # ── REDUCE_OVERWEIGHT recs: these are generally coherent ─────────────
        elif rec_type == "REDUCE_OVERWEIGHT":
            # REDUCE recs are not scored against alternatives — they are confirmed
            # as coherent unless there's a T1 or T3 conflict involving them.
            rec_conflicts = [
                c for c in all_conflicts
                if c.get("rec_a_id") == rec_id or c.get("rec_b_id") == rec_id
            ]
            results[rec_id] = _make_result(
                rec_id=rec_id,
                rec_type=rec_type,
                target_node=target_node,
                legacy_vehicles=list(rec_rd.get("affected_symbols") or []),
                candidates=[],
                preferred_candidate=None,
                optimizer_decision="REDUCE_COHERENT",
                conflicts_detected=rec_conflicts,
                mandate_blocked=False,
            )

        # ── All other rec types (narrative, STI, thematic) ──────────────────
        else:
            results[rec_id] = _make_result(
                rec_id=rec_id,
                rec_type=rec_type,
                target_node=target_node,
                legacy_vehicles=[],
                candidates=[],
                preferred_candidate=None,
                optimizer_decision="NOT_APPLICABLE",
                conflicts_detected=[],
                mandate_blocked=False,
            )

    # Attach global conflict summary to every result for audit completeness
    for rec_id, result in results.items():
        result["all_conflicts"] = all_conflicts
        result["total_t1_conflicts"] = sum(
            1 for c in all_conflicts if c["conflict_type"] == "T1"
        )
        result["total_t2_conflicts"] = sum(
            1 for c in all_conflicts if c["conflict_type"] == "T2"
        )
        result["total_t3_conflicts"] = sum(
            1 for c in all_conflicts if c["conflict_type"] == "T3"
        )

    return results
