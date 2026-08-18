"""Portfolio Analysis Runner — orchestrates Phase C→H end-to-end.

Takes raw portfolio CSV content and produces a complete analysis run stored
under data/portfolio_ingestion/analysis_runs/{run_id}/.

Output files per run:
  snapshot.json          — PortfolioSnapshot envelope
  holdings.csv           — enriched PortfolioHolding rows
  alignment.csv          — AllocationAlignmentResult rows
  concentration.json     — ConcentrationRiskSummary
  recommendations.json   — PortfolioRecommendation list
  security_overlays.csv  — SecurityIntelligenceOverlay rows
  run_metadata.json      — PortfolioAnalysisRun envelope
"""

from __future__ import annotations

import csv
import dataclasses
import io
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .alignment import compute_alignment, compute_concentration
from .archetype import load_archetype_targets
from .compliance_validator import (
    compliance_result_to_dict,
    load_compliance_tolerances,
    validate_portfolio_compliance,
)
from .enrichment import enrich_holdings, normalize_and_aggregate_holdings
from .ingestion import IngestionError, ingest_portfolio
from .mandate import (
    build_mandate_recommendation_overlay,
    evaluate_alignment_under_mandate,
    get_cash_interpretation,
    get_mandate,
)
from .analyst_consensus import load_analyst_consensus, compute_conflict_badge
from .fidelity_signal import load_fidelity_signals, compute_consensus_matrix
from .dislocation import build_dislocation_payload  # ISSUE-04B
from .outcome_tracker import persist_dislocation_detections  # ISSUE-12B
from .models import PortfolioAnalysisRun
from .reconciliation import run_reconciliation
from .deployment_queue import build_deployment_queue, compute_deployable_cash, CW_DAS_VERSION, apply_policy_to_queue as _apply_policy_to_queue
from .deployment_planner import build_deployment_plan, PLANNER_VERSION
from .ess_coverage import load_ess_coverage_warning
from .unified_conviction import build_ucf_verdicts, UCF_VERSION
from .operator_policy import (
    OperatorPolicyRegistry,
    apply_policy_to_recommendations as _apply_policy_to_recs,
    build_policy_annotations,
    build_policy_suppressed_entries,
    compute_execution_state,
)
from .recommendations import build_security_overlays, generate_recommendations, generate_recommendations_with_phase_e_warnings, identify_funding_sources
from .scoring import compute_multi_dimensional_score, detect_intentional_asymmetry
from .trim_intelligence import build_strategic_profiles, validate_trim_intelligence_consistency
from .fvi_loader import load_fvi_registry, build_fvi_data_for_holdings
from .action_latency import build_action_latency_by_symbol
from src.validation.analysis_preflight import run_analysis_preflight

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INGESTION_ROOT = _REPO_ROOT / "data" / "portfolio_ingestion"
_CURRENT_UNIVERSE = str(_REPO_ROOT / "data" / "current" / "analytical_universe.csv")
_TARGETS_CSV = str(_REPO_ROOT / "data" / "current" / "strategic_allocation_targets.csv")
_OVERLAYS_CSV = str(_REPO_ROOT / "data" / "current" / "tactical_overlays.csv")
_YAHOO_SUPPLEMENTAL = _REPO_ROOT / "data" / "signals" / "yahoo" / "latest_yahoo_supplemental.csv"
_SIGNAL_SNAPSHOT    = _REPO_ROOT / "data" / "current" / "signal_snapshot.csv"
_ESS_COVERAGE_WARNING = _REPO_ROOT / "data" / "current" / "ess_coverage_warning.json"
_ZACKS_LATEST       = _REPO_ROOT / "data" / "signals" / "zacks" / "latest_zacks.csv"
_DANELFIN_LATEST    = _REPO_ROOT / "data" / "signals" / "danelfin" / "latest_danelfin.csv"
_OPERATOR_STATE     = str(_REPO_ROOT / "data" / "operator" / "portfolio_alignment_state.json")

# ZACKS-SOURCE-02: symbol-level Zacks sourced_date lookup (display-only; no scoring impact)
def _load_zacks_latest_by_symbol() -> dict:
    try:
        rows = {}
        with open(_ZACKS_LATEST, newline="") as f:
            for row in csv.DictReader(f):
                sym = (row.get("symbol") or "").strip().upper()
                if sym:
                    rows[sym] = row
        return rows
    except Exception:
        return {}

_ZACKS_LATEST_BY_SYMBOL: dict = _load_zacks_latest_by_symbol()

# PRA-IMPL-03 — recommendation_type sets for typed lane counting
_CONVICTION_ANCHOR_TYPES: frozenset[str] = frozenset({
    "STRATEGIC_RETAIN_SIGNAL",
    "STRATEGIC_RETAIN_NARRATIVE",
    "CONVICTION_EXPLAINABILITY_CARD",
})
_NARRATIVE_TYPES: frozenset[str] = frozenset({
    "PORTFOLIO_CONSTRUCTION_NARRATIVE",
    "THEMATIC_SATURATION_NARRATIVE",
})
_EXPLAINABILITY_TYPES: frozenset[str] = frozenset({
    "REPLAY_ALIGNMENT_CONTEXT",
})


def _trigger_pis_refresh_background(*, repo_root: Path) -> None:
    """Fire-and-forget PIS derived-artifact refresh after a new snapshot is registered.

    Runs in a daemon thread so it never blocks the analysis response path.
    All exceptions are swallowed — failure here must never affect SIH processing.
    """
    import sys
    import threading

    def _run() -> None:
        print("[PIS] Post-ingestion refresh started.", file=sys.stderr)
        try:
            from src.pis.refresh_orchestrator import trigger_startup_refresh
            trigger_startup_refresh(repo_root=repo_root)
            print("[PIS] Post-ingestion refresh completed.", file=sys.stderr)
        except Exception as exc:
            print(f"[PIS] Post-ingestion refresh failed: {exc}", file=sys.stderr)

    t = threading.Thread(target=_run, daemon=True, name="pis-post-ingestion-refresh")
    t.start()


def _register_pis_snapshot_best_effort(
    *,
    snapshot: PortfolioSnapshot,
    raw_holdings: list[PortfolioHolding],
) -> tuple[dict[str, object], list[str]]:
    """Register a PIS snapshot without ever blocking SIH analysis."""

    pis_registration: dict[str, object] = {
        "status": "SKIPPED",
        "registered": False,
        "duplicate": False,
        "snapshot_id": snapshot.portfolio_snapshot_id,
        "position_count": 0,
    }
    pis_warnings: list[str] = []
    if str(snapshot.ingestion_status).upper() == "REJECTED":
        return pis_registration, pis_warnings

    try:
        from src.pis.service import register_portfolio_snapshot_from_sih

        pis_result = register_portfolio_snapshot_from_sih(
            snapshot=snapshot,
            holdings=raw_holdings,
        )
        pis_registration = dataclasses.asdict(pis_result)
        pis_registration["status"] = "REGISTERED" if pis_result.registered else "DUPLICATE" if pis_result.duplicate else "SKIPPED"
        if pis_result.warning:
            pis_warnings.append(f"PIS_SNAPSHOT_REGISTRATION_WARNING: {pis_result.warning}")
        if pis_result.registered:
            _trigger_pis_refresh_background(repo_root=_REPO_ROOT)
    except Exception as exc:
        pis_registration = {
            "status": "FAILED",
            "registered": False,
            "duplicate": False,
            "snapshot_id": snapshot.portfolio_snapshot_id,
            "position_count": 0,
            "error": str(exc),
        }
        pis_warnings.append(f"PIS_SNAPSHOT_REGISTRATION_FAILED: {exc}")

    return pis_registration, pis_warnings


def _compute_typed_rec_counts(recs: list[dict]) -> dict[str, int]:
    """Return additive typed lane counts for run_metadata (PRA-IMPL-03).

    Keys are additive and backwards-compatible with existing recommendation_count.
    """
    action = blocked = anchor = narrative = explainability = observation = 0
    for rd in recs:
        ct = rd.get("card_type", "DIAGNOSTIC")
        es = rd.get("execution_state", "EXECUTABLE")
        rt = rd.get("recommendation_type", "")
        if rt in _CONVICTION_ANCHOR_TYPES:
            anchor += 1
        elif rt in _NARRATIVE_TYPES:
            narrative += 1
        elif rt in _EXPLAINABILITY_TYPES:
            explainability += 1
        elif ct == "ACTION":
            if es in ("BLOCKED_BY_POLICY", "DEFERRED_BY_POLICY"):
                blocked += 1
            else:
                action += 1
        else:
            observation += 1
    return {
        "action_count": action,
        "blocked_action_count": blocked,
        "conviction_anchor_count": anchor,
        "narrative_count": narrative,
        "explainability_count": explainability,
        "observation_count": observation,
    }


def _run_id(snapshot_date: str) -> str:
    digest = uuid.uuid4().hex[:8].upper()
    clean = snapshot_date.replace("-", "")
    return f"PAR-{clean}-{digest}"


def _as_json(obj) -> str:
    """Serialize dataclass or list of dataclasses to JSON string."""
    def _convert(o):
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
            d = dataclasses.asdict(o)
            # tuples → lists for JSON
            return {k: list(v) if isinstance(v, (tuple, list)) else v
                    for k, v in d.items()}
        if isinstance(o, (list, tuple)):
            return [_convert(i) for i in o]
        return o
    return json.dumps(_convert(obj), indent=2, default=str)


def _write_csv(path: str, rows: list, fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            if dataclasses.is_dataclass(r) and not isinstance(r, type):
                d = dataclasses.asdict(r)
                # flatten tuples to pipe-delimited strings for CSV
                row = {
                    k: "|".join(str(x) for x in v) if isinstance(v, (tuple, list)) else v
                    for k, v in d.items()
                }
                writer.writerow(row)
            else:
                writer.writerow(r)


# ─────────────────────────────────────────────────────────────────────────────
# Drilldown intelligence helpers
# ─────────────────────────────────────────────────────────────────────────────

_DRILLDOWN_VERSION = "1.0"

# Signal → weakness score (0–30).  Higher = higher reduction priority.
_SIGNAL_WEAKNESS = {"BEARISH": 30, "UNKNOWN": 20, "NEUTRAL": 10, "BULLISH": 0}


def _fld(obj, attr: str, default=None):
    """Uniform field access for both dataclass instances and CSV dicts."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _build_zero_nan_audit_compat() -> dict:
    """Backward-compatible display diagnostics payload for legacy consumers."""
    return {
        "audit_id": "ZERO-NAN-AUDIT-01",
        "display_only": True,
        "status": "OK",
        "suspicious_zero_count": 0,
        "nan_count": 0,
        "null_rendered_as_zero_count": 0,
        "divide_by_zero_count": 0,
        "tiny_rounded_to_zero_count": 0,
        "governance_note": (
            "Display diagnostics only. Never used by scoring, recommendation, "
            "allocation, ranking, or trade execution logic."
        ),
        "summary": {
            "inspected_values": 0,
            "missing_count": 0,
            "invalid_count": 0,
            "zero_count": 0,
            "finite_nonzero_count": 0,
            "tiny_nonzero_count": 0,
        },
        "surfaces": {
            "alignment": {},
            "security_overlays": {},
            "deployment_queue": {},
            "deployment_cash_context": {},
        },
        "suspicious_counts": {
            "invalid_numeric_values": 0,
            "tiny_nonzero_values_lt_0_1": 0,
            "missing_numeric_values": 0,
        },
        "examples": [],
    }


def _empty_operator_action_plan() -> dict:
    """Stable degraded payload shape for operator-priority consumers."""
    return {
        "display_only": True,
        "operator_review_required": True,
        "not_trade_instructions": True,
        "primary_decision": {
            "verdict": "UNAVAILABLE",
            "headline": "Operator action plan unavailable for this run.",
            "basis": [],
        },
        "ordered_actions": [],
        "cash_options": [],
        "hard_asset_buy_plan": [],
        "equity_buy_fallback": [],
        "sell_trim_review": [],
        "blocked_actions": [],
        "conflicts": [],
        "warnings": ["Operator action plan unavailable"],
        "controls": [
            "DISPLAY_ONLY",
            "OPERATOR_REVIEW_REQUIRED",
            "NO CAPITAL DEPLOYMENT QUEUE CHANGES",
            "NO CRA CHANGES",
            "NO TRADE EXECUTION",
        ],
        "summary": {},
        "source_refs": {},
        "daily_operator_action_plan": None,
        "kgc_conflict": {},
    }


def _to_float(v, default=None):
    """Safe float conversion; returns default on failure or empty string."""
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_bool(v, default: bool = False) -> bool:
    """Safe bool conversion; handles 'True'/'False' strings from CSV."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return default if v is None else bool(v)


def _holding_matches_node(
    asset_class: str,
    geography: str,
    market_cap_bucket: str,
    mega_subtier: str,
    node_key: str,
) -> bool:
    """Return True if holding classification fields match the allocation node key.

    node_key hierarchy examples:
      EQUITIES                      → asset_class=EQUITIES
      EQUITIES.US                   → + geography=US
      EQUITIES.US.SMALL             → + market_cap_bucket=SMALL
      EQUITIES.US.MEGA.HYPER_MEGA   → + mega_subtier=HYPER_MEGA
      FIXED_INCOME                  → asset_class=FIXED_INCOME
    """
    parts = node_key.split(".")
    if not parts or parts[0] != asset_class:
        return False
    if len(parts) == 1:
        return True
    if parts[1] != geography:
        return False
    if len(parts) == 2:
        return True
    if parts[2] != market_cap_bucket:
        return False
    if len(parts) == 3:
        return True
    return parts[3] == mega_subtier


def _compute_rps(holding, overlay, node_actual_pct: float) -> dict:
    """Compute the Reduction Priority Score (0–100) for one holding.

    Four additive components (max 100):
      signal_component   (0–30)  BEARISH=30 / UNKNOWN=20 / NEUTRAL=10 / BULLISH=0
      score_component    (0–30)  scaled from composite_score; below 3.5 → penalty
      replay_component   (0–25)  absence of replay validation; not supported → 20
      allocation_component (0–15) fractional share of the overweight category

    Category contribution is weighted lower (15 pts max) than signal/score so
    that a high-conviction large holding is not automatically prioritised over a
    small bearish position.
    """
    signal = (_fld(overlay, "signal_direction") or "UNKNOWN").upper()
    score = _to_float(_fld(overlay, "composite_score"))
    replay_ok = _to_bool(_fld(overlay, "replay_supported"))
    replay_pctile = _to_float(_fld(overlay, "replay_percentile"))
    holding_pct = _to_float(_fld(holding, "percent_of_portfolio"), 0.0)

    # 1. Signal weakness (0–30)
    sig_pts = _SIGNAL_WEAKNESS.get(signal, 20)

    # 2. Score weakness (0–30): 3.5 = inflection point; score 1.0 → 30pts, 5.0 → 0pts
    if score is not None:
        score_pts = max(0, min(30, round((3.5 - score) / 2.5 * 30)))
    else:
        score_pts = 15  # no score data = neutral penalty

    # 3. Replay absence (0–25)
    if not replay_ok:
        replay_pts = 25 if (replay_pctile is not None and replay_pctile < 25) else 20
    else:
        if replay_pctile is not None and replay_pctile < 25:
            replay_pts = 25
        elif replay_pctile is not None and replay_pctile >= 75:
            replay_pts = 0
        else:
            replay_pts = 5  # replay-supported but not top-quartile

    # 4. Category contribution (0–15) — intentionally lower weight
    if node_actual_pct and node_actual_pct > 0 and holding_pct is not None:
        cat_pts = min(15, round(holding_pct / node_actual_pct * 15))
    else:
        cat_pts = 0

    total = sig_pts + score_pts + replay_pts + cat_pts

    # Explanation: top 3 drivers by points
    score_display = f"{score:.2f}" if score is not None else "N/A"
    drivers = sorted(
        [
            (sig_pts,   f"signal ({signal}) +{sig_pts}pts"),
            (score_pts, f"score ({score_display}) +{score_pts}pts"),
            (replay_pts, f"replay absence +{replay_pts}pts"),
            (cat_pts,   f"category share +{cat_pts}pts"),
        ],
        key=lambda x: -x[0],
    )
    top = [desc for pts, desc in drivers[:3] if pts > 0]
    explanation = (
        f"RPS {total}/100. Top factors: {'; '.join(top)}."
        if top else f"RPS {total}/100."
    )

    return {
        "total": total,
        "signal_component": sig_pts,
        "score_component": score_pts,
        "replay_component": replay_pts,
        "allocation_component": cat_pts,
        "explanation": explanation,
    }


def _suggested_action(rps_total: int, signal: str) -> str:
    """Map RPS + signal direction to a human-readable suggested action.

    Actions (from most positive to most negative):
      CORE_RETAIN      — high conviction BULLISH, low reduction priority
      HIGH_CONVICTION  — BULLISH, moderate RPS
      STRUCTURAL_HOLD  — neutral signal, low RPS (diversification anchor)
      HOLD             — neutral, no clear action signal
      MONITOR          — emerging weakness; watch before acting
      REDUCE_CANDIDATE — clear reduction candidate
    """
    sig = (signal or "").upper()
    if sig == "BULLISH" and rps_total < 25:
        return "CORE_RETAIN"
    if sig == "BULLISH" and rps_total < 40:
        return "HIGH_CONVICTION"
    if rps_total >= 60:
        return "REDUCE_CANDIDATE"
    if rps_total >= 40:
        return "MONITOR"
    if rps_total < 25:
        return "STRUCTURAL_HOLD"
    return "HOLD"


def _benchmark_relative_state(overlay) -> tuple:
    """Derive relative-strength context from replay percentile (proxy).

    NOTE: This is a replay-universe proxy, not a true price-benchmark comparison.
    Full benchmark integration (SPY / IWM / sector ETFs) is a planned enhancement.
    Returns (benchmark_symbol, relative_strength_state).
    """
    pctile = _to_float(_fld(overlay, "replay_percentile"))
    if pctile is None:
        return ("REPLAY_UNIVERSE", "INSUFFICIENT_DATA")
    if pctile >= 65:
        return ("REPLAY_UNIVERSE", "OUTPERFORMING")
    if pctile <= 35:
        return ("REPLAY_UNIVERSE", "UNDERPERFORMING")
    return ("REPLAY_UNIVERSE", "NEUTRAL")


def _build_sti_summary(profile) -> Optional[dict]:
    """Serialize a HoldingStrategicProfile into a JSON-friendly summary dict."""
    if profile is None:
        return None
    # Convert trim_factors tuple-of-tuples to list-of-dicts for JSON clarity
    raw_factors = _fld(profile, "trim_factors") or []
    factors = []
    for item in raw_factors:
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            factors.append({
                "factor":       item[0],
                "contribution": _to_float(item[1], 0.0),
                "rationale":    item[2],
            })
        elif isinstance(item, dict):
            factors.append(item)

    return {
        "symbol":                     _fld(profile, "symbol", ""),
        "percent_of_portfolio":       _to_float(_fld(profile, "percent_of_portfolio"), 0.0),
        "strategic_classification":   _fld(profile, "strategic_classification", ""),
        "trim_priority_score":        _to_float(_fld(profile, "trim_priority_score"), 0.0),
        "strategic_importance":       _fld(profile, "strategic_importance", ""),
        "exposure_origin":            _fld(profile, "exposure_origin", ""),
        "thematic_redundancy_score":  _to_float(_fld(profile, "thematic_redundancy_score"), 0.0),
        "overlap_peers":              list(_fld(profile, "overlap_peers") or []),
        "thematic_overlap_clusters":  list(_fld(profile, "thematic_overlap_clusters") or []),
        "concentration_pressure":     _to_float(_fld(profile, "concentration_pressure"), 0.0),
        "diversification_contribution": _to_float(_fld(profile, "diversification_contribution"), 0.0),
        "trim_rationale":             _fld(profile, "trim_rationale", ""),
        "retain_rationale":           _fld(profile, "retain_rationale", ""),
        "classification_trace":       _fld(profile, "classification_trace", ""),
        "trim_factors":               factors,
        # Phase 7.1 — narrative tier and anchor rank
        "narrative_tier":             _fld(profile, "narrative_tier", ""),
        "strategic_anchor_rank":      int(_fld(profile, "strategic_anchor_rank") or 0),
    }


def _build_drilldown_data(
    holdings: list,
    alignment_results: list,
    overlays: list,
    recs: list,
    generated_at: str,
    strategic_profiles: Optional[list] = None,
) -> dict:
    """Build per-recommendation drilldown with enriched holdings and RPS.

    Supports two drilldown modes:
      NODE    — holdings filtered by allocation hierarchy node key
      SYMBOLS — holdings filtered by the recommendation's affected_symbols list

    Returns:
        dict mapping recommendation_id → drilldown dict
    """
    overlay_by_sym = {_fld(o, "symbol", ""): o for o in overlays}

    # Phase D — STI profile lookup (symbol → HoldingStrategicProfile)
    sti_by_sym: dict[str, object] = {}
    if strategic_profiles:
        for p in strategic_profiles:
            sym = _fld(p, "symbol", "")
            if sym:
                sti_by_sym[sym] = p

    node_info: dict = {}
    for ar in alignment_results:
        key = _fld(ar, "node_key", "")
        node_info[key] = {
            "actual_pct":      _to_float(_fld(ar, "actual_pct"), 0.0),
            "target_pct":      _to_float(_fld(ar, "target_pct"), 0.0),
            "drift_pct":       _to_float(_fld(ar, "drift_pct"), 0.0),
            "node_label":      _fld(ar, "node_label", key),
            "drift_direction": _fld(ar, "drift_direction", ""),
        }

    result: dict = {}

    for rec in recs:
        rec_id = _fld(rec, "recommendation_id", "")
        affected_node = _fld(rec, "affected_node_key")
        affected_syms_raw = _fld(rec, "affected_symbols") or []

        # Normalize affected_symbols (tuple, list, or pipe-delimited CSV string)
        if isinstance(affected_syms_raw, str):
            affected_syms = [s.strip() for s in affected_syms_raw.split("|") if s.strip()]
        else:
            affected_syms = list(affected_syms_raw)

        # Determine drilldown mode
        if affected_node:
            mode = "NODE"
            ni = node_info.get(affected_node, {})
            node_actual_pct = ni.get("actual_pct", 0.0)
        elif affected_syms:
            mode = "SYMBOLS"
            ni = {}
            # For SYMBOLS mode: node_actual_pct = sum pct of affected symbols
            node_actual_pct = sum(
                _to_float(_fld(h, "percent_of_portfolio"), 0.0)
                for h in holdings
                if _fld(h, "symbol", "") in affected_syms
            ) or 1.0
        else:
            result[rec_id] = {
                "recommendation_id":     rec_id,
                "drilldown_version":     _DRILLDOWN_VERSION,
                "drilldown_generated_at": generated_at,
                "mode":                  "NONE",
                "holdings_count":        0,
                "holdings":              [],
            }
            continue

        # Filter holdings by mode
        matched = []
        for h in holdings:
            sym = _fld(h, "symbol", "")
            if mode == "NODE":
                if _holding_matches_node(
                    _fld(h, "asset_class", ""),
                    _fld(h, "geography", ""),
                    _fld(h, "market_cap_bucket", ""),
                    _fld(h, "mega_subtier", ""),
                    affected_node,
                ):
                    matched.append(h)
            else:
                if sym in affected_syms:
                    matched.append(h)

        # Enrich each matched holding with RPS and intelligence context
        enriched_rows = []
        for h in matched:
            sym = _fld(h, "symbol", "")
            overlay = overlay_by_sym.get(sym)
            rps = _compute_rps(h, overlay, node_actual_pct)
            bm_sym, bm_state = _benchmark_relative_state(overlay)
            signal_dir = (_fld(overlay, "signal_direction") or "UNKNOWN").upper()
            action = _suggested_action(rps["total"], signal_dir)

            h_pct = _to_float(_fld(h, "percent_of_portfolio"), 0.0)
            cat_pct = round(h_pct / node_actual_pct * 100, 2) if node_actual_pct > 0 else 0.0

            enriched_rows.append({
                "symbol":                    sym,
                "description":               _fld(h, "description", ""),
                "market_value":              _to_float(_fld(h, "market_value"), 0.0),
                "percent_of_portfolio":      h_pct,
                "category_contribution_pct": cat_pct,
                "asset_class":               _fld(h, "asset_class", ""),
                "geography":                 _fld(h, "geography", ""),
                "market_cap_bucket":         _fld(h, "market_cap_bucket", ""),
                "mega_subtier":              _fld(h, "mega_subtier", ""),
                "sector":                    _fld(h, "sector", ""),
                "industry":                  _fld(h, "industry", ""),
                "security_type":             _fld(h, "security_type", ""),
                "composite_score":           _to_float(_fld(overlay, "composite_score")),
                "ess_score_text":            _fld(overlay, "ess_score_text", ""),
                "zacks_rating":              _fld(overlay, "zacks_rating", ""),
                "danelfin_score":            _fld(overlay, "danelfin_score", ""),
                "signal_direction":          signal_dir,
                "opportunity_flag":          _fld(overlay, "opportunity_flag", ""),
                "flag_rationale":            _fld(overlay, "flag_rationale", ""),
                "replay_supported":          _to_bool(_fld(overlay, "replay_supported")),
                "best_replay_return":        _to_float(_fld(overlay, "best_replay_return")),
                "replay_percentile":         _to_float(_fld(overlay, "replay_percentile")),
                "benchmark_symbol":          bm_sym,
                "benchmark_relative_state":  bm_state,
                "reduction_priority_score":  rps["total"],
                "rps_breakdown": {
                    "signal_component":      rps["signal_component"],
                    "score_component":       rps["score_component"],
                    "replay_component":      rps["replay_component"],
                    "allocation_component":  rps["allocation_component"],
                    "explanation":           rps["explanation"],
                },
                "suggested_action": action,
                # Phase D — Strategic Trim Intelligence
                "strategic_profile": _build_sti_summary(sti_by_sym.get(sym)),
            })

        # Compute RPS percentile rank within this drilldown group
        # 0th = lowest reduction priority, 100th = highest
        if enriched_rows:
            rps_vals = sorted(r["reduction_priority_score"] for r in enriched_rows)
            n = len(rps_vals)
            for row in enriched_rows:
                rv = row["reduction_priority_score"]
                rank = sum(1 for v in rps_vals if v <= rv)
                row["rps_percentile"] = round(rank / n * 100)

        # Sort by RPS descending (highest reduction priority first)
        enriched_rows.sort(key=lambda r: r["reduction_priority_score"], reverse=True)

        result[rec_id] = {
            "recommendation_id":      rec_id,
            "drilldown_version":      _DRILLDOWN_VERSION,
            "drilldown_generated_at": generated_at,
            "mode":                   mode,
            "affected_node_key":      affected_node,
            "affected_node_label":    ni.get("node_label", ""),
            "node_actual_pct":        ni.get("actual_pct", 0.0),
            "node_target_pct":        ni.get("target_pct", 0.0),
            "node_drift_pct":         ni.get("drift_pct", 0.0),
            "node_drift_direction":   ni.get("drift_direction", ""),
            "holdings_count":         len(enriched_rows),
            "holdings":               enriched_rows,
        }

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_analysis(
    portfolio_content: str,
    source_filename: str,
    snapshot_date: Optional[str] = None,
    mandate_type: str = "CONCENTRATED_ALPHA",
) -> dict:
    """Run a complete portfolio alignment analysis.

    Args:
        portfolio_content: raw CSV text of the portfolio extract
        source_filename:   original filename (for lineage)
        snapshot_date:     ISO date of the portfolio; defaults to today
        mandate_type:      portfolio mandate for PMI interpretation layer
                           (BALANCED|GROWTH|DEFENSIVE|INCOME|
                            REPLAY_OPTIMIZED|CONCENTRATED_ALPHA)

    Returns a dict summary suitable for JSON serialization.

    Phase 6.2 additions (interpretation layer only — all exposure/decomp
    data is UNCHANGED):
        mandate_type, mandate_display_name
        mandate_interpretations  — per-node mandate-adjusted drift interpretation
        multi_dimensional_score  — four-dimensional portfolio quality score
        intentional_asymmetry    — asymmetry detection assessment
        cash_mandate_context     — mandate-specific cash position narrative
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc).date().isoformat()

    # ── Phase B/C — Ingest and normalize ─────────────────────────────────────
    try:
        snapshot, raw_holdings = ingest_portfolio(
            portfolio_content, source_filename, snapshot_date
        )
    except IngestionError as exc:
        # Write to rejected/
        rejected_dir = _INGESTION_ROOT / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        ts = now_utc.replace(":", "-")[:19]
        (rejected_dir / f"{ts}_{source_filename}").write_text(
            portfolio_content, encoding="utf-8"
        )
        return {
            "status": "REJECTED",
            "error": str(exc),
            "source_filename": source_filename,
        }

    pis_registration, pis_warnings = _register_pis_snapshot_best_effort(
        snapshot=snapshot,
        raw_holdings=raw_holdings,
    )

    run_id = _run_id(snapshot_date)

    # ── Phase D — Enrich holdings ─────────────────────────────────────────────
    enriched = enrich_holdings(raw_holdings, universe_csv=_CURRENT_UNIVERSE)
    # ── Phase 6.1C — Aggregate duplicate symbols ───────────────────────────────────
    enriched = normalize_and_aggregate_holdings(enriched)

    # ── Phase 22D.10 — Apply settlement governance attribute ──────────────────
    # safe_to_offset_cash = True for ACCOUNTING_ADJUSTMENT rows with negative MV.
    # These rows represent pending purchase settlements: cash already economically
    # committed at trade placement and not available for redeployment.
    # MV=0 rows (net-zero transfer artifacts) remain False — offsetting $0 is a
    # noop but explicitly excluded to preserve governance intent.
    # Default False is conservative: unrecognized patterns are excluded until reviewed.
    enriched = [
        dataclasses.replace(
            h,
            safe_to_offset_cash=(
                h.operational_state == "ACCOUNTING_ADJUSTMENT" and h.market_value < 0
            ),
        )
        for h in enriched
    ]

    # ── Phase 6.1B — Separate investable from operational/audit-only rows ───────
    _INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
    investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]
    excluded_operational = [
        h for h in enriched if h.operational_state not in _INVESTABLE_STATES
    ]
    operational_warnings = [
        f"Excluded from analytics: {h.symbol!r} ({h.description!r}) — {h.operational_state}"
        for h in excluded_operational
    ]
    # ── Phase E — Alignment + concentration ──────────────────────────────────
    archetype_targets = load_archetype_targets(mandate_type)
    alignment = compute_alignment(
        analysis_run_id=run_id,
        portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
        holdings=investable,
        targets_csv=_TARGETS_CSV,
        overlays_csv=_OVERLAYS_CSV,
        targets_override=archetype_targets if archetype_targets else None,
    )
    concentration = compute_concentration(
        analysis_run_id=run_id,
        portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
        holdings=investable,
    )

    # ── CPV — Current Portfolio Compliance Validator (AI-001-OPTION-B) ─────
    try:
        import dataclasses as _dc_cpv
        import yaml as _yaml_cpv
        _policy_doc = _yaml_cpv.safe_load(
            (_REPO_ROOT / "config" / "allocation_policy.yaml").read_text(encoding="utf-8")
        ) or {}
        _sp_block = dict(_policy_doc.get("structural_policy", {}))
        _sp_block["asset_class_governance"] = _policy_doc.get("asset_class_governance", {})
        _tols = load_compliance_tolerances(_REPO_ROOT / "config" / "allocation_policy.yaml")
        portfolio_compliance = validate_portfolio_compliance(
            alignment_rows=[_dc_cpv.asdict(r) for r in alignment],
            policy=_sp_block,
            tolerances=_tols,
            run_id=run_id,
            snapshot_date=snapshot_date,
        )
    except Exception as _cpv_exc:
        portfolio_compliance = None
        operational_warnings.append(f"CPV_EVALUATION_FAILED: {_cpv_exc}")

    # ── Analysis preflight (read-only readiness governance gate) ─────────────
    preflight = run_analysis_preflight(
        repo_root=_REPO_ROOT,
        require_active_ess=True,
        holdings_rows=[dataclasses.asdict(h) for h in enriched],
    )
    preflight_blocked = preflight.status == "BLOCKED"
    if preflight_blocked:
        operational_warnings.append(
            "PREFLIGHT_BLOCKED: Action-oriented outputs are suppressed; see analysis_preflight reason codes."
        )

    # ── Phase F/G/H — Recommendations + security overlays ────────────────────
    if preflight_blocked:
        overlays = []
        strategic_profiles = []
        sti_warnings = []
        recs = []
        phase_e_warnings = [
            "Preflight BLOCKED: action-oriented recommendations suppressed until blocking prerequisites are resolved."
        ]
    else:
        overlays = build_security_overlays(
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            alignment_results=alignment,
        )

        # ── Phase D — Strategic Trim Intelligence ─────────────────────────────
        strategic_profiles = build_strategic_profiles(
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            overlays=overlays,
            alignment_results=alignment,
        )
        sti_warnings = validate_trim_intelligence_consistency(strategic_profiles)

        recs, phase_e_warnings = generate_recommendations_with_phase_e_warnings(
            analysis_run_id=run_id,
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            alignment_results=alignment,
            concentration=concentration,
            overlays=overlays,
            strategic_profiles=strategic_profiles,
        )

    # Overall alignment score = mean of per-node alignment scores
    if alignment:
        overall_score = round(sum(r.alignment_score for r in alignment) / len(alignment), 4)
    else:
        overall_score = 0.0

    # ── Phase 6.2 — Portfolio Mandate Intelligence (interpretation layer) ─────
    mandate = get_mandate(mandate_type)

    mandate_interpretations = evaluate_alignment_under_mandate(alignment, mandate)
    interp_by_node = {mi.node_key: mi for mi in mandate_interpretations}

    multi_dim_score = compute_multi_dimensional_score(
        analysis_run_id=run_id,
        portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
        mandate_type=mandate_type,
        alignment_results=alignment,
        concentration=concentration,
        overlays=overlays,
        recs=recs,
        strategic_profiles=strategic_profiles,
    )

    # Phase 7.1 Part C — Append replay alignment context rec now that multi_dim_score is available
    if strategic_profiles:
        from .phase_e_synthesis import _generate_replay_alignment_context, _prioritize_recs
        replay_ctx = _generate_replay_alignment_context(
            analysis_run_id=run_id,
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            multi_dim_score=multi_dim_score,
            now_utc=now_utc,
            overlays=overlays,
        )
        if replay_ctx:
            recs = _prioritize_recs(list(recs) + [replay_ctx])

    asymmetry = detect_intentional_asymmetry(
        analysis_run_id=run_id,
        portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
        mandate_type=mandate_type,
        holdings=investable,
        overlays=overlays,
        alignment_results=alignment,
        strategic_profiles=strategic_profiles,
    )

    cash_ar = next((a for a in alignment if a.node_key == "CASH"), None)
    cash_mandate_context = get_cash_interpretation(
        cash_actual_pct=cash_ar.actual_pct if cash_ar else 0.0,
        cash_target_pct=cash_ar.target_pct if cash_ar else 0.0,
        mandate=mandate,
    )

    # ── Compute drilldown intelligence ───────────────────────────────────────
    drilldown_by_rec = _build_drilldown_data(
        holdings=investable,
        alignment_results=alignment,
        overlays=overlays,
        recs=recs,
        generated_at=now_utc,
        strategic_profiles=strategic_profiles,
    )
    # Build recommendation dicts with drilldown + mandate overlay embedded
    recs_with_drilldown = []
    for rec in recs:
        rd = dataclasses.asdict(rec)
        for k, v in rd.items():
            if isinstance(v, tuple):
                rd[k] = list(v)
        dd = drilldown_by_rec.get(rd["recommendation_id"])
        if dd:
            rd["drilldown"] = dd
        # Inject mandate overlay for this recommendation's affected node
        node_key = rd.get("affected_node_key") or ""
        interp = interp_by_node.get(node_key)
        mandate_overlay = build_mandate_recommendation_overlay(rd, interp, mandate)
        rd.update(mandate_overlay)
        recs_with_drilldown.append(rd)

    # ── Phase 7.3A — Parallel Optimizer (metadata only, does NOT change recs) ──
    from .optimizer import run_parallel_optimizer as _run_parallel_optimizer
    if preflight_blocked:
        optimizer_scores = {}
    else:
        optimizer_scores = _run_parallel_optimizer(
            recs_with_overlay=recs_with_drilldown,
            holdings=investable,
            overlays=overlays,
            profiles=strategic_profiles,
            alignment_results=alignment,
            mandate_interpretations=mandate_interpretations,
            total_mv=snapshot.total_market_value,
        )
    # Inject optimizer_metadata into each rec dict (additive; rec content unchanged)
    for rd in recs_with_drilldown:
        rid = rd.get("recommendation_id", "")
        if rid in optimizer_scores:
            rd["optimizer_metadata"] = optimizer_scores[rid]

    # ── Phase 7.5B — Capital Deployment Queue (additive; does not alter any existing data) ──
    if preflight_blocked:
        deployment_queue = []
    else:
        deployment_queue = build_deployment_queue(
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            overlays=overlays,
            strategic_profiles=strategic_profiles,
            alignment_results=alignment,
            total_market_value=snapshot.total_market_value,
        )

    # ── Phase 23.2 — Operator Policy Layer ───────────────────────────────────
    # Load operator policies AFTER deployment queue is built (pre-policy scores preserved).
    # Policy application: annotate queue, boost/suppress as approved.
    # Reconciliation inputs are untouched — policy is an output-layer transform.
    _policy_registry = OperatorPolicyRegistry.load(_OPERATOR_STATE)
    deployment_queue, _policy_suppressed = _apply_policy_to_queue(
        deployment_queue, _policy_registry
    )
    # ── PRA-IMPL-02 — Normalise policy execution state on recommendation dicts ─
    # Mutates execution_state, effective_action, card_lifecycle_state in-place.
    # Scoring, ranking, and generation logic are NOT affected.
    _apply_policy_to_recs(recs_with_drilldown, _policy_registry)
    _policy_suppressed_from_overlays = build_policy_suppressed_entries(
        overlays, _policy_registry
    )
    _policy_suppressed_all = (
        _policy_suppressed_from_overlays
        + [dataclasses.asdict(c) for c in _policy_suppressed]
    )
    _policy_annotations = build_policy_annotations(
        [o.symbol for o in overlays], _policy_registry
    )
    # Resolve mandate cash target for deployable cash computation (fail-closed).
    # archetype_targets is already loaded above; "CASH" key holds the mandate target %.
    _cash_target_pct = archetype_targets.get("CASH") if archetype_targets else None
    if _cash_target_pct is None:
        raise ValueError(
            f"Mandate profile for '{mandate_type}' is missing a CASH node target. "
            "Add 'CASH: <target_pct>' to the mandate's allocation_models YAML before running."
        )
    cash_context = compute_deployable_cash(
        holdings=investable,
        total_market_value=snapshot.total_market_value,
        mandate_cash_target_pct=_cash_target_pct,
    )

    # ── Phase 22D.10 — Settlement adjustment (D2) ────────────────────────────
    # Sum the absolute market values of all excluded holdings that are flagged
    # as safe_to_offset_cash.  These represent pending purchase settlements:
    # cash debited at trade placement but not yet reflected in the SPAXX balance.
    # Original cash_context values are preserved; adjusted_* fields are additive.
    _settlement_adjustment = round(
        sum(abs(h.market_value) for h in excluded_operational if h.safe_to_offset_cash),
        2,
    )
    _adjusted_cash_mv = round(
        max(0.0, cash_context["cash_mv"] - _settlement_adjustment), 2
    )
    _adjusted_deployable_mv = round(
        max(0.0, cash_context["deployable_mv"] - _settlement_adjustment), 2
    )
    _adjusted_deployable_pct = round(
        _adjusted_deployable_mv / snapshot.total_market_value * 100.0
        if snapshot.total_market_value else 0.0,
        4,
    )
    # Extend cash_context with settlement-aware fields (original fields unchanged)
    cash_context = {
        **cash_context,
        "settlement_adjustment":   _settlement_adjustment,
        "adjusted_cash_mv":        _adjusted_cash_mv,
        "adjusted_deployable_mv":  _adjusted_deployable_mv,
        "adjusted_deployable_pct": _adjusted_deployable_pct,
    }

    dq_payload = {
        "run_id": run_id,
        "queue_version": f"CW-DAS-{CW_DAS_VERSION}",
        "generated_at": now_utc,
        "total_market_value": snapshot.total_market_value,
        "cash_context": cash_context,
        "candidate_count": len(deployment_queue),
        "queue": [dataclasses.asdict(c) for c in deployment_queue],
        # Phase 23.2 — policy layer output
        "policy_suppressed": _policy_suppressed_all,
        "policy_active_count": len(_policy_registry.all_active()),
        "suppressed_by_preflight": preflight_blocked,
        "preflight_reason_codes": list(preflight.reason_codes),
    }

    # ── Persist outputs ───────────────────────────────────────────────────────
    out_dir = _INGESTION_ROOT / "analysis_runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # snapshot.json
    snap_dict = dataclasses.asdict(snapshot)
    snap_dict["run_id"] = run_id
    snap_dict["normalization_warnings"] = list(snap_dict["normalization_warnings"])
    # Phase 22D.10 (D4): embed settlement lineage in snapshot for operator audit
    snap_dict["settlement_adjustment"]   = _settlement_adjustment
    snap_dict["adjusted_cash_mv"]        = _adjusted_cash_mv
    snap_dict["adjusted_deployable_mv"]  = _adjusted_deployable_mv
    snap_dict["adjusted_deployable_pct"] = _adjusted_deployable_pct
    with open(out_dir / "snapshot.json", "w") as fh:
        json.dump(snap_dict, fh, indent=2)

    # holdings.csv — write ALL enriched rows for full audit lineage
    if enriched:
        _write_csv(
            str(out_dir / "holdings.csv"),
            enriched,
            list(dataclasses.asdict(enriched[0]).keys()),
        )

    # alignment.csv
    if alignment:
        _write_csv(
            str(out_dir / "alignment.csv"),
            alignment,
            list(dataclasses.asdict(alignment[0]).keys()),
        )

    # concentration.json
    with open(out_dir / "concentration.json", "w") as fh:
        fh.write(_as_json(concentration))

    # recommendations.json  (drilldown intelligence embedded per recommendation)
    with open(out_dir / "recommendations.json", "w") as fh:
        json.dump(recs_with_drilldown, fh, indent=2, default=str)

    # security_overlays.csv — write with additive policy annotation columns
    if overlays:
        base_fields = list(dataclasses.asdict(overlays[0]).keys())
        policy_fields = ["policy_type", "policy_annotation", "policy_protected",
                         "execution_state", "effective_action"]
        overlay_fieldnames = base_fields + policy_fields
        with open(str(out_dir / "security_overlays.csv"), "w", newline="", encoding="utf-8") as _fh:
            _writer = csv.DictWriter(_fh, fieldnames=overlay_fieldnames)
            _writer.writeheader()
            for _ov in overlays:
                _row = dataclasses.asdict(_ov)
                _ann = _policy_annotations.get(_ov.symbol.upper(), {})
                _row["policy_type"]       = _ann.get("policy_type", "")
                _row["policy_annotation"] = _ann.get("policy_annotation", "")
                _row["policy_protected"]  = _ann.get("policy_protected", False)
                _exec_state, _eff_action = compute_execution_state(
                    _ov.symbol,
                    str(_row.get("opportunity_flag") or ""),
                    _policy_registry,
                )
                _row["execution_state"]  = _exec_state
                _row["effective_action"] = _eff_action
                _writer.writerow(_row)

    # deployment_queue.json
    with open(out_dir / "deployment_queue.json", "w") as fh:
        json.dump(dq_payload, fh, indent=2, default=str)

    # ── Phase 7.5D — Capital Deployment Planner (additive; guidance only) ────
    # Phase 22D.10 (D3): CW-DAS uses adjusted_deployable_mv as the budget.
    # If no settlement obligations exist (_settlement_adjustment == 0), this
    # equals deployable_mv and behavior is identical to pre-22D.10.
    if preflight_blocked:
        dp_payload = {
            "run_id": run_id,
            "planner_version": f"DP-{PLANNER_VERSION}",
            "generated_at": now_utc,
            "deployable_cash": _adjusted_deployable_mv,
            "total_market_value": snapshot.total_market_value,
            "total_allocated": 0.0,
            "plan_advisory": "Suppressed by analysis preflight BLOCKED state.",
            "tier_summaries": [],
            "portfolio_impact": {
                "total_market_value": snapshot.total_market_value,
                "cash_before_pct": cash_context.get("cash_pct", 0.0),
                "cash_after_pct": cash_context.get("cash_pct", 0.0),
                "cash_before_mv": cash_context.get("cash_mv", 0.0),
                "cash_after_mv": cash_context.get("cash_mv", 0.0),
                "positions_at_warn_before": 0,
                "positions_at_warn_after": 0,
                "total_deployed": 0.0,
                "unallocated_cash": _adjusted_deployable_mv,
            },
            "recommendations": [],
            "suppressed_by_preflight": True,
            "preflight_reason_codes": list(preflight.reason_codes),
        }
    else:
        deployment_plan = build_deployment_plan(
            deployment_queue_data=dq_payload,
            deployable_cash=_adjusted_deployable_mv,  # Phase 22D.10: settlement-adjusted
        )
        dp_payload = {
            "run_id": run_id,
            "planner_version": f"DP-{PLANNER_VERSION}",
            "generated_at": deployment_plan.generated_at,
            "deployable_cash": deployment_plan.deployable_cash,
            "total_market_value": deployment_plan.total_market_value,
            "total_allocated": deployment_plan.total_allocated,
            "plan_advisory": deployment_plan.plan_advisory,
            "tier_summaries": [dataclasses.asdict(t) for t in deployment_plan.tier_summaries],
            "portfolio_impact": dataclasses.asdict(deployment_plan.portfolio_impact),
            "recommendations": [dataclasses.asdict(r) for r in deployment_plan.recommendations],
            "suppressed_by_preflight": False,
            "preflight_reason_codes": list(preflight.reason_codes),
        }
    with open(out_dir / "deployment_plan.json", "w") as fh:
        json.dump(dp_payload, fh, indent=2, default=str)

    # ── Phase 7.5E — UCF Verdicts (additive signal transparency layer) ───────
    ucf_verdicts = build_ucf_verdicts(
        profiles=strategic_profiles or [],
        overlays=overlays,
        deployment_queue=dq_payload,
    )
    ucf_payload = {
        "run_id": run_id,
        "ucf_version": UCF_VERSION,
        "queue_size": len(dq_payload.get("queue", [])),
        "total_holdings": len(ucf_verdicts),
        "generated_at": now_utc,
        "label_counts": {},
        "verdicts": [],
    }
    # tally label counts and build verdicts list
    _lbl_counts: dict[str, int] = {}
    _verdicts_dicts: list[dict] = []
    for v in ucf_verdicts:
        _lbl_counts[v.ucf_label] = _lbl_counts.get(v.ucf_label, 0) + 1
        _verdicts_dicts.append({
            "symbol": v.symbol,
            "ucf_label": v.ucf_label,
            "ucf_score": round(v.ucf_score, 4),
            "ucf_rank": v.ucf_rank,
            "conflict_flags": v.conflict_flags,
            "source_signals": {
                "narrative_tier": v.narrative_tier,
                "composite_score": v.composite_score,
                "signal_direction": v.signal_direction,
                "replay_supported": v.replay_supported,
                "replay_percentile": v.replay_percentile,
                "trim_priority_score": v.trim_priority_score,
                "cw_das_score": v.cw_das_score,
                "cw_das_rank": v.cw_das_rank,
            },
            "deployment": {
                "deployment_eligible": v.deployment_eligible,
                "deployment_blocked": v.deployment_blocked,
                "deployment_block_reason": v.deployment_block_reason,
            },
            "signal_summary": v.signal_summary,
        })
    ucf_payload["label_counts"] = _lbl_counts
    ucf_payload["verdicts"] = _verdicts_dicts
    with open(out_dir / "ucf_verdicts.json", "w") as fh:
        json.dump(ucf_payload, fh, indent=2, default=str)

    with open(out_dir / "analyst_consensus.json", "w") as fh:
        json.dump(_build_consensus_payload(), fh, indent=2, default=str)

    # ── Phase 6.4 — Reconciliation ────────────────────────────────────────────
    reconciliation = run_reconciliation(
        holdings=investable,
        alignment=alignment,
        recommendations=recs_with_drilldown,
        mandate_type=mandate_type,
        snapshot_total_mv=snapshot.total_market_value,
        run_id=run_id,
        generated_at=now_utc,
    )
    with open(out_dir / "reconciliation.json", "w") as fh:
        json.dump({
            "run_id": reconciliation.run_id,
            "generated_at": reconciliation.generated_at,
            "overall_status": reconciliation.overall_status,
            "checks_passed": reconciliation.checks_passed,
            "checks_warned": reconciliation.checks_warned,
            "checks_failed": reconciliation.checks_failed,
            "certification": reconciliation.certification,
            "checks": [
                dataclasses.asdict(c) for c in reconciliation.checks
            ],
        }, fh, indent=2)

        # ── Write compliance.json ─────────────────────────────────────────────
        if portfolio_compliance is not None:
            compliance_dict = compliance_result_to_dict(portfolio_compliance)
            with open(out_dir / "compliance.json", "w") as fh:
                json.dump(compliance_dict, fh, indent=2)

        # run_metadata.json
    analysis_run = PortfolioAnalysisRun(
        run_id=run_id,
        portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
        snapshot_date=snapshot_date,
        recalculation_id="SEED_20260520_D9E58D7F",   # active SIH recalculation
        analytical_universe_date=snapshot_date,
        alignment_results_count=len(alignment),
        recommendation_count=len(recs),
        concentration_tier=concentration.concentration_tier,
        overall_alignment_score=overall_score,
        status="COMPLETE",
        warnings=tuple(list(snapshot.normalization_warnings) + pis_warnings + operational_warnings),
        created_at_utc=now_utc,
    )
    with open(out_dir / "run_metadata.json", "w") as fh:
        meta = dataclasses.asdict(analysis_run)
        meta["warnings"] = list(meta["warnings"])
        meta["analysis_preflight"] = preflight.to_dict()
        meta["reconciliation_status"] = reconciliation.overall_status
        meta["reconciliation_checks_passed"] = reconciliation.checks_passed
        meta["reconciliation_checks_failed"] = reconciliation.checks_failed
        meta["reconciliation_checks_warned"] = reconciliation.checks_warned
        meta["reconciliation_certification"] = reconciliation.certification
        meta["taxonomy_status"] = next(
            (c.status for c in reconciliation.checks if c.check_id == "RC-12"),
            "N/A",
        )
        meta["coverage_status"] = next(
            (c.status for c in reconciliation.checks if c.check_id == "RC-13"),
            "N/A",
        )
        # Phase 23.2 — Operator Policy Layer
        meta["policy_snapshot"] = _policy_registry.policy_snapshot()
        meta["policy_suppressed_count"] = len(_policy_suppressed_all)
        meta["policy_rank_adjusted_count"] = sum(
            1 for c in deployment_queue if c.policy_rank_boost
        )
        json.dump(meta, fh, indent=2)

    with open(out_dir / "preflight.json", "w") as fh:
        json.dump(preflight.to_dict(), fh, indent=2)

    # ── Coverage history trend baseline ──────────────────────────────────────
    rc13 = next((c for c in reconciliation.checks if c.check_id == "RC-13"), None)
    if rc13 and rc13.sub_checks:
        _append_coverage_history(run_id, now_utc, rc13.sub_checks)

    # ── Update manifest ───────────────────────────────────────────────────────
    _update_manifest(run_id, snapshot, analysis_run, now_utc, reconciliation, preflight)

    # ── Archive incoming file ─────────────────────────────────────────────────
    archive_dir = _INGESTION_ROOT / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = now_utc.replace(":", "-")[:19]
    (archive_dir / f"{ts}_{run_id}_{source_filename}").write_text(
        portfolio_content, encoding="utf-8"
    )

    _held_symbols = [h.symbol for h in investable]
    _consensus_payload = _build_consensus_payload()
    _fidelity_payload = _build_fidelity_payload()
    _fmp_payload = _build_fmp_payload(_held_symbols)
    _price_payload = _build_price_context_payload(_held_symbols)
    _ucf_by_symbol = {v["symbol"]: v for v in ucf_payload["verdicts"]}
    _ov_by_symbol = {o.symbol.upper(): dataclasses.asdict(o) for o in overlays}

    try:
        _action_latency_payload = build_action_latency_by_symbol(
            repo_root=_REPO_ROOT,
            symbols=_held_symbols,
            snapshot_date=snapshot_date,
            overlays_by_symbol=_ov_by_symbol,
            fidelity_by_symbol=_fidelity_payload,
            ucf_by_symbol=_ucf_by_symbol,
            price_context_by_symbol=_price_payload,
        )
    except Exception:
        _action_latency_payload = {}

    _zero_nan_audit_payload = _build_zero_nan_audit_compat()

    rotation_summary: dict = {}
    _operator_plan_payload = _empty_operator_action_plan()
    try:
        from src.sih.rotation_risk_monitor import rotation_risk_summary, _build_today_operator_action_plan

        rotation_summary = rotation_risk_summary(_REPO_ROOT, run_id=run_id)
        if _build_today_operator_action_plan is not None:
            _operator_plan_payload = _build_today_operator_action_plan(
                hard_asset_priority_gate=rotation_summary.get("hard_asset_priority_gate", {}),
                hard_asset_candidate_queue=rotation_summary.get("hard_asset_candidate_queue", {}),
                rotation_fragility_watch=rotation_summary.get("rotation_fragility_watch", {}),
                commodity_guard=rotation_summary.get("commodity_fill_guard", {}),
                deployment_queue=dq_payload,
                security_overlays=[dataclasses.asdict(o) for o in overlays],
                recommendations_payload=recs_with_drilldown,
            ) or _empty_operator_action_plan()
    except Exception:
        pass

    return {
        "status": "COMPLETE",
        "run_id": run_id,
        "portfolio_snapshot_id": snapshot.portfolio_snapshot_id,
        "account_name": snapshot.account_name,
        "snapshot_date": snapshot_date,
        "holding_count": snapshot.holding_count,
        "total_market_value": snapshot.total_market_value,
        "source_format": snapshot.source_format,
        "warnings": list(snapshot.normalization_warnings) + pis_warnings + operational_warnings,
        "analysis_preflight": preflight.to_dict(),
        "pis_snapshot_registration": pis_registration,
        "concentration_tier": concentration.concentration_tier,
        "overall_alignment_score": overall_score,
        "recommendation_count": len(recs),
        # PRA-IMPL-03 — Additive typed lane counts (client can also compute locally)
        **_compute_typed_rec_counts(recs_with_drilldown),
        # PRA-IMPL-05 — FVI advisory data (additive; advisory-only; no scoring impact)
        "fvi_data": _build_fvi_payload(_held_symbols),
        # Full detail arrays — included so the UI renders immediately
        "alignment": [dataclasses.asdict(r) for r in alignment],
        "concentration": dataclasses.asdict(concentration),
        "recommendations": recs_with_drilldown,
        "security_overlays": [dataclasses.asdict(o) for o in overlays],
        # Phase D — Strategic Trim Intelligence profiles (one per holding)
        "strategic_profiles": [_build_sti_summary(p) for p in strategic_profiles],
        "sti_warnings": sti_warnings,
        # Phase E — Strategic Recommendation Synthesis warnings
        "phase_e_warnings": phase_e_warnings,
        # Phase 6.1 — Operational row audit + funding source intelligence
        "operational_exclusions": [
            {"symbol": h.symbol, "description": h.description,
             "operational_state": h.operational_state}
            for h in excluded_operational
        ],
        "operational_exclusion_count": len(excluded_operational),
        # Phase 6.2 — Portfolio Mandate Intelligence (interpretation layer)
        # Governance: all exposure/decomposition/suitability/replay data above
        # is unchanged.  PMI only adjusts interpretation and urgency.
        "mandate_type": mandate_type,
        "mandate_display_name": mandate.display_name,
        "mandate_interpretations": [
            dataclasses.asdict(mi) for mi in mandate_interpretations
        ],
        "multi_dimensional_score": dataclasses.asdict(multi_dim_score),
        # AI-001-OPTION-B — Current Portfolio Compliance (CPV)
        "portfolio_compliance": (
            compliance_result_to_dict(portfolio_compliance)
            if portfolio_compliance is not None else None
        ),
        "intentional_asymmetry": dataclasses.asdict(asymmetry),
        "cash_mandate_context": cash_mandate_context,
        # Phase 6.4 — Reconciliation
        "reconciliation_status": reconciliation.overall_status,
        "reconciliation_checks_passed": reconciliation.checks_passed,
        "reconciliation_checks_failed": reconciliation.checks_failed,
        "reconciliation_checks_warned": reconciliation.checks_warned,
        "reconciliation_certification": reconciliation.certification,
        # UX-PA-02: Full check array for explainability panel
        "reconciliation_checks": [dataclasses.asdict(c) for c in reconciliation.checks],
        "taxonomy_status": next(
            (c.status for c in reconciliation.checks if c.check_id == "RC-12"),
            "N/A",
        ),
        "coverage_status": next(
            (c.status for c in reconciliation.checks if c.check_id == "RC-13"),
            "N/A",
        ),
        # Phase 7.3A — Parallel optimizer scores (metadata only)
        # Governance: does not affect recommendation ordering, content, or UI.
        "optimizer_scores": optimizer_scores,
        # Phase 7.5B — Capital Deployment Queue (additive; guidance artifact only)
        # Governance: does not affect STI, recs, overlays, or optimizer output.
        "deployment_queue": dq_payload,
        # Phase 7.5D — Capital Deployment Planner (additive; guidance only)
        # Governance: read-only. No trade generation, no execution authority.
        "deployment_plan": dp_payload,
        # Operator priorities compatibility payloads (display-only).
        "commodity_fill_guard": rotation_summary.get("commodity_fill_guard", {}),
        "hard_asset_candidate_queue": rotation_summary.get("hard_asset_candidate_queue", {}),
        "commodity_sleeve_completion_candidates": rotation_summary.get("commodity_sleeve_completion_candidates", {}),
        "hard_asset_priority_gate": rotation_summary.get("hard_asset_priority_gate", {}),
        "commodity_vs_equity_priority_gate": rotation_summary.get("commodity_vs_equity_priority_gate", {}),
        "rotation_fragility_watch": rotation_summary.get("rotation_fragility_watch", {}),
        "today_operator_action_plan": _operator_plan_payload,
        "daily_operator_action_plan": _operator_plan_payload,
        # Phase 7.5E — UCF Verdicts (additive signal transparency layer)
        # Governance: read-only synthesis of existing signals.
        "ucf_verdicts_by_symbol": _ucf_by_symbol,
        # Phase 7.5J — Analyst Consensus Transparency (additive; display-only)
        # Governance: no scoring, no ranking, no deployment queue changes.
        "analyst_consensus_by_symbol": _consensus_payload,
        # Phase 7.5K — Fidelity Analyst Transparency (additive; display-only)
        # Governance: ESS reformatted as analyst language + 3-signal consensus matrix.
        "fidelity_signals_by_symbol": _fidelity_payload,
        # Phase 7.5N — Signal Source Metadata (additive; display-only)
        # Governance: refresh dates for Zacks/Danelfin freshness display. No scoring impact.
        "signal_source_metadata": _build_signal_source_metadata(),
        # DIL Phase 1 — FMP fundamental context for Decision Intelligence Layer (display-only)
        # Governance: read-only display fields. Never fed back into any scoring system.
        "fmp_data_by_symbol": _fmp_payload,
        # DIL Phase 2 — recent price context (display-only; no scoring impact)
        "price_context_by_symbol": _price_payload,
        # Compatibility diagnostics surfaces (display-only; additive).
        "action_latency_by_symbol": _action_latency_payload,
        "zero_nan_audit": _zero_nan_audit_payload,
        # ISSUE-04D — pass analyst consensus for Class B2
        "dislocation_by_symbol": _build_dislocation_payload(
            overlays, ac_by_sym=_consensus_payload
        ),
    }

    # MARKET-CONTEXT-01 — Deployment timing & macro event awareness (display-only)
    # Governance: additive display layer; no scoring, ranking, or recommendation impact.
    result["market_context"] = _build_market_context_payload(
        price_context_by_symbol=result.get("price_context_by_symbol", {}),
        deployment_queue=result.get("deployment_queue", {}),
        security_overlays=overlays,
        investable_symbols=[h.symbol for h in investable],
    )

    # ISSUE-12B — Persist dislocation detections for outcome tracking.
    # Governance: append-only, informational only. No scoring impact.
    _disloc_payload = result["dislocation_by_symbol"]
    if _disloc_payload:
        # Load current prices from Yahoo supplemental for price_at_detection
        _yahoo_prices: dict[str, float] = {}
        try:
            from src.portfolio.analyst_consensus import load_analyst_consensus
            _cons = load_analyst_consensus(_YAHOO_SUPPLEMENTAL)
            for _sym, _ac in _cons.items():
                if _ac.current_price is not None:
                    _yahoo_prices[_sym] = _ac.current_price
        except Exception:
            pass
        try:
            persist_dislocation_detections(
                detection_date=snapshot_date,
                run_id=run_id,
                dislocation_payload=_disloc_payload,
                overlays=overlays,
                dq_payload=dq_payload,
                yahoo_prices=_yahoo_prices or None,
            )
        except Exception:
            pass  # never let tracking errors break the analysis run


def _build_fvi_payload(symbols: list[str]) -> dict[str, dict]:
    """Load FVI advisory data for portfolio holdings (PRA-IMPL-05).

    Advisory-only — never mutates scores, rankings, or recommendations.
    Graceful degradation: returns empty dict if config is missing.
    """
    try:
        registry = load_fvi_registry()
        return build_fvi_data_for_holdings(symbols, registry)
    except Exception:
        return {}


def _build_price_context_payload(symbols: list[str]) -> dict[str, dict]:
    """DIL Phase 2 — recent price context for Decision Intelligence Layer (display-only).

    Fetches 1D/5D/1M returns, 52-week range position, and next earnings date via yfinance.
    Governance: additive display layer only. Never injected into CW-DAS, RPS, ESS, or any
    scoring system. Falls back gracefully to empty dict if yfinance unavailable.
    """
    if not symbols:
        return {}
    try:
        import yfinance as yf
        import datetime as dt

        result: dict[str, dict] = {}
        tickers = yf.Tickers(" ".join(symbols))

        for sym in symbols:
            try:
                ticker = tickers.tickers.get(sym.upper())
                if ticker is None:
                    continue
                info = ticker.fast_info
                hist = ticker.history(period="1mo", auto_adjust=True)
                if hist.empty:
                    continue

                current = float(hist["Close"].iloc[-1])
                price_1d_ago = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current
                price_5d_ago = float(hist["Close"].iloc[-6]) if len(hist) >= 6 else float(hist["Close"].iloc[0])
                price_1m_ago = float(hist["Close"].iloc[0])

                high_52w = getattr(info, "year_high", None)
                low_52w  = getattr(info, "year_low", None)
                pct_52w  = None
                if high_52w and low_52w and high_52w > low_52w:
                    pct_52w = round((current - low_52w) / (high_52w - low_52w) * 100, 1)

                entry: dict = {
                    "current_price": round(current, 2),
                    "return_1d":     round((current - price_1d_ago) / price_1d_ago * 100, 2) if price_1d_ago else None,
                    "return_5d":     round((current - price_5d_ago) / price_5d_ago * 100, 2) if price_5d_ago else None,
                    "return_1m":     round((current - price_1m_ago) / price_1m_ago * 100, 2) if price_1m_ago else None,
                    "high_52w":      round(high_52w, 2) if high_52w else None,
                    "low_52w":       round(low_52w, 2) if low_52w else None,
                    "pct_52w_range": pct_52w,
                }

                # Next earnings date (best-effort)
                try:
                    cal = ticker.calendar
                    if cal is not None and not cal.empty:
                        earnings_col = [c for c in cal.columns if "Earnings" in str(c)]
                        if earnings_col:
                            ed = cal[earnings_col[0]].iloc[0]
                            entry["next_earnings_date"] = str(ed)[:10] if ed else None
                except Exception:
                    pass

                result[sym.upper()] = entry
            except Exception:
                continue

        return result
    except Exception:
        return {}

    """Load FMP enriched universe fields for DIL Phase 1 (display-only).

    Exposes fundamental context fields (EPS surprise, beat rate, revenue
    growth) for the Decision Intelligence Layer. These are read-only display
    fields — they are never injected back into CW-DAS, RPS, or any scoring
    system. The FMP fundamental_modifier is already baked into CW-DAS scores;
    this payload is for operator-facing interpretation only.
    """
    _DISPLAY_FIELDS = frozenset({
        "latest_eps_surprise_pct", "beat_rate_8q", "beats_last_8q",
        "q1_surprise_pct", "q2_surprise_pct", "q3_surprise_pct", "q4_surprise_pct",
        "revenue_growth_q1_yoy", "eps_growth_q1_yoy", "revenue_acceleration",
        "fmp_coverage_status", "fmp_sourced_date",
        "buy_count", "hold_count", "sell_count", "net_buy_score",
        "ev_ebitda_ttm", "fcf_yield_ttm", "roe_ttm", "roic_ttm",
    })
    try:
        from src.scoring.fmp_universe_enrichment import load_fmp_enriched_universe
        fmp = load_fmp_enriched_universe()
        return {
            sym.upper(): {k: v for k, v in (fmp.get(sym.upper()) or {}).items() if k in _DISPLAY_FIELDS}
            for sym in symbols
            if fmp.get(sym.upper())
        }
    except Exception:
        return {}


def _build_market_context_payload(
    price_context_by_symbol: dict,
    deployment_queue: dict,
    security_overlays: list,
    investable_symbols: list,
) -> dict:
    """MARKET-CONTEXT-01 — Deployment Timing & Macro Event Awareness (display-only).

    Aggregates three display layers for operator timing awareness:
      1. Macro events   — FOMC meetings, options expiry, index events (static 2026 calendar)
      2. Portfolio events — upcoming earnings for holdings, DQ candidates, reduction candidates
      3. Timing posture — EVENT_DENSE / MODERATE / NORMAL banner

    Governance: additive display layer only. Never injected into CW-DAS, RPS, ESS,
    DIL posture, PAP, CRA, or any scoring system. No recommendation influence.
    """
    import datetime as dt

    today = dt.date.today()
    MACRO_HORIZON_DAYS = 14
    EARNINGS_HORIZON_DAYS = 30

    # ── Static 2026 macro calendar ────────────────────────────────────────────
    _MACRO_STATIC = [
        # FOMC decision dates (pre-announced by Federal Reserve for full calendar year)
        {"event": "FOMC Meeting",          "date": "2026-01-29", "category": "FED"},
        {"event": "FOMC Meeting",          "date": "2026-03-18", "category": "FED"},
        {"event": "FOMC Meeting",          "date": "2026-05-07", "category": "FED"},
        {"event": "FOMC Meeting",          "date": "2026-06-18", "category": "FED"},
        {"event": "FOMC Meeting",          "date": "2026-07-30", "category": "FED"},
        {"event": "FOMC Meeting",          "date": "2026-09-17", "category": "FED"},
        {"event": "FOMC Meeting",          "date": "2026-10-29", "category": "FED"},
        {"event": "FOMC Meeting",          "date": "2026-12-10", "category": "FED"},
        # Quarterly Triple Witching (3rd Friday of March/June/Sep/Dec)
        {"event": "Triple Witching",       "date": "2026-03-20", "category": "OPTIONS"},
        {"event": "Triple Witching",       "date": "2026-06-19", "category": "OPTIONS"},
        {"event": "Triple Witching",       "date": "2026-09-18", "category": "OPTIONS"},
        {"event": "Triple Witching",       "date": "2026-12-18", "category": "OPTIONS"},
        # Russell Index Reconstitution (effective last Friday of June)
        {"event": "Russell Reconstitution","date": "2026-06-26", "category": "INDEX"},
    ]

    macro_events: list[dict] = []
    horizon = today + dt.timedelta(days=MACRO_HORIZON_DAYS)
    for e in _MACRO_STATIC:
        try:
            edate = dt.date.fromisoformat(e["date"])
            days_away = (edate - today).days
            if 0 <= days_away <= MACRO_HORIZON_DAYS:
                macro_events.append({
                    "event":     e["event"],
                    "date":      e["date"],
                    "days_away": days_away,
                    "category":  e["category"],
                })
        except Exception:
            continue

    # Monthly options expiry (3rd Friday of each month, deduped against triple witching)
    def _third_friday(year: int, month: int):
        import calendar as cal_mod
        weeks = cal_mod.monthcalendar(year, month)
        fridays = [w[4] for w in weeks if w[4] != 0]
        return dt.date(year, month, fridays[2]) if len(fridays) >= 3 else None

    existing_dates = {e["date"] for e in macro_events}
    for offset in range(3):
        m = today.month + offset
        y = today.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        opex = _third_friday(y, m)
        if opex and today <= opex <= horizon and opex.isoformat() not in existing_dates:
            macro_events.append({
                "event":     "Monthly Options Expiry",
                "date":      opex.isoformat(),
                "days_away": (opex - today).days,
                "category":  "OPTIONS",
            })
            existing_dates.add(opex.isoformat())

    macro_events.sort(key=lambda x: x["days_away"])

    # ── Portfolio earnings events ─────────────────────────────────────────────
    dq_syms   = {(e.get("symbol") or "").upper() for e in (deployment_queue.get("queue") or [])[:15]}
    held_syms = {(s or "").upper() for s in (investable_symbols or [])}

    red_syms: set = set()
    try:
        ranked = sorted(
            [o for o in (security_overlays or []) if float(o.get("reduction_priority_score") or 0) > 0],
            key=lambda o: -float(o.get("reduction_priority_score") or 0),
        )
        red_syms = {(o.get("symbol") or "").upper() for o in ranked[:15]}
    except Exception:
        pass

    portfolio_events: list[dict] = []
    seen: set = set()
    for sym_upper, pc in (price_context_by_symbol or {}).items():
        edate_str = pc.get("next_earnings_date")
        if not edate_str:
            continue
        try:
            edate = dt.date.fromisoformat(str(edate_str)[:10])
        except Exception:
            continue
        days_away = (edate - today).days
        if not (0 <= days_away <= EARNINGS_HORIZON_DAYS):
            continue
        if sym_upper in seen:
            continue
        seen.add(sym_upper)

        if sym_upper in dq_syms and sym_upper in red_syms:
            context = "DEPLOYMENT_AND_REDUCTION"
        elif sym_upper in dq_syms:
            context = "TOP_DEPLOYMENT_CANDIDATE"
        elif sym_upper in red_syms:
            context = "REDUCTION_CANDIDATE"
        elif sym_upper in held_syms:
            context = "CURRENT_HOLDING"
        else:
            continue  # exclude symbols outside our relevant universe

        portfolio_events.append({
            "symbol":    sym_upper,
            "event":     "Earnings",
            "date":      str(edate_str)[:10],
            "days_away": days_away,
            "context":   context,
        })

    portfolio_events.sort(key=lambda x: x["days_away"])
    portfolio_events = portfolio_events[:20]

    # ── Deployment timing posture ─────────────────────────────────────────────
    events_7d   = sum(1 for e in macro_events    if e["days_away"] <= 7)
    earnings_7d = sum(1 for e in portfolio_events if e["days_away"] <= 7)
    total_7d    = events_7d + earnings_7d

    if total_7d >= 4:
        timing_posture = "EVENT_DENSE"
    elif total_7d >= 2:
        timing_posture = "MODERATE_ACTIVITY"
    else:
        timing_posture = "NORMAL"

    return {
        "as_of_date":       today.isoformat(),
        "macro_events":     macro_events,
        "portfolio_events": portfolio_events,
        "market_events":    [],   # reserved: future IPO / geopolitical events
        "timing_posture":   timing_posture,
        "events_7d":        events_7d,
        "earnings_7d":      earnings_7d,
        "total_events_7d":  total_7d,
    }


def _build_consensus_payload() -> dict:
    """Load Yahoo supplemental and build a serializable analyst_consensus_by_symbol dict.

    Each value is a dict with keys matching AnalystConsensus fields plus
    a pre-computed 'conflict_badge' field (informational only).
    """
    consensus_map = load_analyst_consensus(_YAHOO_SUPPLEMENTAL)
    result: dict[str, dict] = {}
    for sym, ac in consensus_map.items():
        result[sym] = {
            "symbol": ac.symbol,
            "abr": ac.abr,
            "analyst_count": ac.analyst_count,
            "price_target": ac.price_target,
            "current_price": ac.current_price,
            "upside_pct": ac.upside_pct,
            "consensus_label": ac.consensus_label,
            "consensus_strength": ac.consensus_strength,
            "refresh_date": ac.refresh_date,
        }
    return result


def _build_fidelity_payload() -> dict:
    """Load signal_snapshot and build a serializable fidelity_signals_by_symbol dict.

    Each value is a dict with FidelitySignal fields plus a pre-computed
    consensus_matrix entry (informational only).  The Yahoo supplemental is also
    loaded so the consensus_matrix can incorporate the ABR direction.
    """
    if not _SIGNAL_SNAPSHOT.exists():
        return {}

    fidelity_map  = load_fidelity_signals(_SIGNAL_SNAPSHOT)
    consensus_map = load_analyst_consensus(_YAHOO_SUPPLEMENTAL) if _YAHOO_SUPPLEMENTAL.exists() else {}

    # Also load the latest Zacks data for the 3-signal matrix
    _zacks_latest = _REPO_ROOT / "data" / "signals" / "zacks" / "latest_zacks.csv"
    zacks_map: dict[str, float | None] = {}
    if _zacks_latest.exists():
        import csv as _csv
        with open(_zacks_latest, newline="", encoding="utf-8") as fh:
            for row in _csv.DictReader(fh):
                sym = (row.get("symbol") or "").strip().upper()
                try:
                    zacks_map[sym] = float(row.get("zacks_score") or "")
                except (ValueError, TypeError):
                    zacks_map[sym] = None

    result: dict[str, dict] = {}
    for sym, fs in fidelity_map.items():
        ac = consensus_map.get(sym)
        consensus_label = ac.consensus_label if ac else "NO_CONSENSUS"
        zacks_score = zacks_map.get(sym)
        matrix = compute_consensus_matrix(fs.ess_text, consensus_label, zacks_score)
        # ZACKS-SOURCE-02: include symbol-level Zacks sourced_date for DIL provenance
        zacks_row = _ZACKS_LATEST_BY_SYMBOL.get(sym.upper()) if _ZACKS_LATEST_BY_SYMBOL else None
        zacks_symbol_date = zacks_row.get("sourced_date") if zacks_row else None
        result[sym] = {
            "symbol": fs.symbol,
            "ess_text": fs.ess_text,
            "ess_numeric": fs.ess_numeric,
            "fidelity_rating": fs.fidelity_rating,
            "fidelity_direction": fs.fidelity_direction,
            "refresh_date": fs.refresh_date,
            "coverage_domain": fs.coverage_domain,
            "consensus_matrix": matrix,
            "zacks_sourced_date": zacks_symbol_date,   # symbol-level, not universe-level
            "zacks_source_type": "DIRECT_ZACKS" if zacks_symbol_date else "NO_DATA",
        }
    return result


def _build_fmp_payload(symbols: list[str]) -> dict:
    """Load FMP enriched-universe fields for display-only DIL context.

    This helper mirrors the existing UI contract consumed by
    `fmp_data_by_symbol`. It is intentionally read-only and returns only the
    per-symbol fields that the dashboard and dislocation logic already use.
    """
    _DISPLAY_FIELDS = frozenset({
        "latest_eps_surprise_pct", "beat_rate_8q", "beats_last_8q",
        "q1_surprise_pct", "q2_surprise_pct", "q3_surprise_pct", "q4_surprise_pct",
        "revenue_growth_q1_yoy", "eps_growth_q1_yoy", "revenue_acceleration",
        "fmp_coverage_status", "fmp_sourced_date",
        "buy_count", "hold_count", "sell_count", "net_buy_score",
        "ev_ebitda_ttm", "fcf_yield_ttm", "roe_ttm", "roic_ttm",
    })

    try:
        from src.scoring.fmp_universe_enrichment import load_fmp_enriched_universe

        fmp = load_fmp_enriched_universe()
        return {
            sym.upper(): {k: v for k, v in (fmp.get(sym.upper()) or {}).items() if k in _DISPLAY_FIELDS}
            for sym in symbols
            if fmp.get(sym.upper())
        }
    except Exception:
        return {}


def _build_dislocation_payload(overlays: list, ac_by_sym: Optional[dict] = None) -> dict:
    """Build dislocation_by_symbol payload using FMP enriched universe.

    ISSUE-04D: passes analyst consensus for Class B2 support.
    Governance: informational only — no scoring, ranking, or CW-DAS influence.
    """
    try:
        from src.scoring.fmp_universe_enrichment import load_fmp_enriched_universe
        fmp_by_sym = load_fmp_enriched_universe()
    except Exception:
        fmp_by_sym = {}
    return build_dislocation_payload(overlays=overlays, fmp_by_sym=fmp_by_sym,
                                     ac_by_sym=ac_by_sym or {})


def _build_signal_source_metadata() -> dict:
    """Build signal refresh-date metadata for display purposes.

    Phase 7.5N — Signal Provenance, Lineage & Freshness (display-only).
    No scoring or ranking impact. Supplies Zacks and Danelfin refresh dates
    (ESS and Yahoo dates are already embedded per-symbol in their respective
    fidelity_signals_by_symbol and analyst_consensus_by_symbol payloads).
    """

    def _latest_date(path: Path, date_col: str) -> str:
        if not path.exists():
            return ""
        try:
            latest = ""
            with open(path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    d = (row.get(date_col) or "").strip()
                    if d > latest:
                        latest = d
            return latest
        except Exception:
            return ""

    return {
        "ess_refresh_date": _latest_date(_SIGNAL_SNAPSHOT, "snapshot_date"),
        "zacks_refresh_date": _latest_date(_ZACKS_LATEST, "sourced_date"),
        "danelfin_refresh_date": _latest_date(_DANELFIN_LATEST, "sourced_date"),
        "ess_coverage_warning": load_ess_coverage_warning(_ESS_COVERAGE_WARNING),
    }


def _append_coverage_history(run_id: str, run_at: str, signal_sub_checks: list) -> None:
    """Append per-signal coverage metrics to data/derived/coverage_history.csv.

    Creates the file with a header row on first call.  Each run appends one row
    per signal type so future runs can compare Previous/Current/Delta.
    """
    history_path = _INGESTION_ROOT.parent / "derived" / "coverage_history.csv"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "run_id", "run_at_utc", "signal",
        "holdings_covered", "holdings_total",
        "pct_holdings", "pct_mv", "grade",
    ]
    write_header = not history_path.exists()
    with open(history_path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for sc in signal_sub_checks:
            writer.writerow({
                "run_id": run_id,
                "run_at_utc": run_at,
                "signal": sc.get("signal", ""),
                "holdings_covered": sc.get("holdings_covered", 0),
                "holdings_total": sc.get("holdings_total", 0),
                "pct_holdings": sc.get("pct_holdings", 0.0),
                "pct_mv": sc.get("pct_mv", 0.0),
                "grade": sc.get("grade", "?"),
            })


def _update_manifest(run_id, snapshot, analysis_run, now_utc: str, reconciliation=None, preflight=None) -> None:
    manifest_path = _INGESTION_ROOT / "manifest.json"
    try:
        with open(manifest_path) as fh:
            manifest = json.load(fh)
    except Exception:
        manifest = {"version": 1, "portfolios": []}

    manifest["last_updated"] = now_utc
    entry = {
        "run_id": run_id,
        "portfolio_snapshot_id": snapshot.portfolio_snapshot_id,
        "account_name": snapshot.account_name,
        "snapshot_date": snapshot.snapshot_date,
        "holding_count": snapshot.holding_count,
        "total_market_value": snapshot.total_market_value,
        "source_format": snapshot.source_format,
        "status": analysis_run.status,
        "concentration_tier": analysis_run.concentration_tier,
        "overall_alignment_score": analysis_run.overall_alignment_score,
        "recommendation_count": analysis_run.recommendation_count,
        "created_at_utc": now_utc,
    }
    if preflight is not None:
        entry["preflight_status"] = preflight.status
        entry["preflight_reason_codes"] = list(preflight.reason_codes)
    if reconciliation is not None:
        entry["reconciliation_status"] = reconciliation.overall_status
        entry["reconciliation_checks_passed"] = reconciliation.checks_passed
        entry["reconciliation_checks_failed"] = reconciliation.checks_failed
        entry["reconciliation_certification"] = reconciliation.certification
        entry["taxonomy_status"] = next(
            (c.status for c in reconciliation.checks if c.check_id == "RC-12"),
            "N/A",
        )
        entry["coverage_status"] = next(
            (c.status for c in reconciliation.checks if c.check_id == "RC-13"),
            "N/A",
        )
    manifest["portfolios"].append(entry)

    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Load a completed analysis run from disk
# ─────────────────────────────────────────────────────────────────────────────

def load_analysis_run(run_id: str) -> Optional[dict]:
    """Load a complete analysis run from disk by run_id. Returns None if not found."""
    run_dir = _INGESTION_ROOT / "analysis_runs" / run_id
    if not run_dir.exists():
        return None

    result: dict = {"run_id": run_id}
    for fname in ("run_metadata.json", "snapshot.json", "concentration.json"):
        path = run_dir / fname
        if path.exists():
            with open(path) as fh:
                result[fname.replace(".json", "")] = json.load(fh)

    for fname in ("recommendations.json",):
        path = run_dir / fname
        if path.exists():
            with open(path) as fh:
                result[fname.replace(".json", "")] = json.load(fh)

    # alignment.csv
    apath = run_dir / "alignment.csv"
    if apath.exists():
        result["alignment"] = list(csv.DictReader(open(apath)))

    # Holdings — read full rows for backward-compat drilldown computation
    hpath = run_dir / "holdings.csv"
    holdings_for_drilldown = []
    if hpath.exists():
        with open(hpath) as fh:
            holdings_for_drilldown = list(csv.DictReader(fh))
        result["holdings_count"] = len(holdings_for_drilldown)

    # overlays
    opath = run_dir / "security_overlays.csv"
    if opath.exists():
        result["security_overlays"] = list(csv.DictReader(open(opath)))

    # deployment_queue.json (Phase 7.5B — additive, absent for pre-7.5B runs)
    dq_path = run_dir / "deployment_queue.json"
    if dq_path.exists():
        with open(dq_path) as fh:
            result["deployment_queue"] = json.load(fh)

    # deployment_plan.json (Phase 7.5D — additive, absent for pre-7.5D runs)
    dp_path = run_dir / "deployment_plan.json"
    if dp_path.exists():
        with open(dp_path) as fh:
            result["deployment_plan"] = json.load(fh)

    preflight_path = run_dir / "preflight.json"
    if preflight_path.exists():
        with open(preflight_path) as fh:
            result["analysis_preflight"] = json.load(fh)
        result["analysis_preflight_provenance"] = "persisted_preflight_artifact"
    else:
        meta_preflight = ((result.get("run_metadata") or {}).get("analysis_preflight"))
        if isinstance(meta_preflight, dict):
            result["analysis_preflight"] = meta_preflight
            result["analysis_preflight_provenance"] = "persisted_run_metadata"
        else:
            computed = run_analysis_preflight(
                repo_root=_REPO_ROOT,
                require_active_ess=True,
                holdings_rows=holdings_for_drilldown,
            ).to_dict()
            computed["computed_at_load_time"] = True
            computed["historical_provenance_note"] = (
                "Computed during load from current runtime artifacts; not persisted at original run time."
            )
            result["analysis_preflight"] = computed
            result["analysis_preflight_provenance"] = "computed_load_time_fallback"

    # ucf_verdicts.json (Phase 7.5E — additive, absent for pre-7.5E runs)
    ucf_path = run_dir / "ucf_verdicts.json"
    if ucf_path.exists():
        with open(ucf_path) as fh:
            ucf_data = json.load(fh)
        verdicts_list = ucf_data.get("verdicts", [])
        result["ucf_verdicts_by_symbol"] = {v["symbol"]: v for v in verdicts_list}

    # analyst_consensus (Phase 7.5J — always loaded from latest Yahoo supplemental)
    result["analyst_consensus_by_symbol"] = _build_consensus_payload()

    # fidelity_signals (Phase 7.5K — always loaded from latest signal_snapshot)
    result["fidelity_signals_by_symbol"] = _build_fidelity_payload()

    # signal_source_metadata (Phase 7.5N — display-only refresh dates)
    result["signal_source_metadata"] = _build_signal_source_metadata()

    # DIL Phase 1 — FMP fundamental context (display-only; no scoring impact)
    _held_syms = [row.get("symbol", "") for row in holdings_for_drilldown if row.get("symbol")]
    result["fmp_data_by_symbol"] = _build_fmp_payload(_held_syms)
    # DIL Phase 2 — recent price context (display-only; no scoring impact)
    result["price_context_by_symbol"] = _build_price_context_payload(_held_syms)
    _ov_by_symbol = {
        str(row.get("symbol") or "").upper(): row
        for row in result.get("security_overlays", [])
        if str(row.get("symbol") or "").strip()
    }
    try:
        result["action_latency_by_symbol"] = build_action_latency_by_symbol(
            repo_root=_REPO_ROOT,
            symbols=_held_syms,
            snapshot_date=(result.get("run_metadata") or {}).get("snapshot_date", ""),
            overlays_by_symbol=_ov_by_symbol,
            fidelity_by_symbol=result.get("fidelity_signals_by_symbol", {}),
            ucf_by_symbol=result.get("ucf_verdicts_by_symbol", {}),
            price_context_by_symbol=result.get("price_context_by_symbol", {}),
        )
    except Exception:
        result["action_latency_by_symbol"] = {}
    result["zero_nan_audit"] = _build_zero_nan_audit_compat()
    # MARKET-CONTEXT-01 — Deployment timing & macro event awareness (display-only)
    result["market_context"] = _build_market_context_payload(
        price_context_by_symbol=result.get("price_context_by_symbol", {}),
        deployment_queue=result.get("deployment_queue", {}),
        security_overlays=result.get("security_overlays", []),
        investable_symbols=_held_syms,
    )

    try:
        from src.sih.rotation_risk_monitor import rotation_risk_summary, _build_today_operator_action_plan

        rotation_summary = rotation_risk_summary(_REPO_ROOT, run_id=run_id)
    except Exception:
        rotation_summary = {}
        _build_today_operator_action_plan = None

    for key in (
        "commodity_fill_guard",
        "hard_asset_candidate_queue",
        "commodity_sleeve_completion_candidates",
        "hard_asset_priority_gate",
        "commodity_vs_equity_priority_gate",
        "rotation_fragility_watch",
    ):
        if key in rotation_summary:
            result[key] = rotation_summary[key]

    if _build_today_operator_action_plan is not None:
        result["today_operator_action_plan"] = _build_today_operator_action_plan(
            hard_asset_priority_gate=result.get("hard_asset_priority_gate", {}),
            hard_asset_candidate_queue=result.get("hard_asset_candidate_queue", {}),
            rotation_fragility_watch=result.get("rotation_fragility_watch", {}),
            commodity_guard=result.get("commodity_fill_guard", {}),
            deployment_queue=result.get("deployment_queue", {}),
            security_overlays=result.get("security_overlays", []),
            recommendations_payload=result.get("recommendations", []),
        ) or _empty_operator_action_plan()
    else:
        result["today_operator_action_plan"] = _empty_operator_action_plan()
    result["daily_operator_action_plan"] = result["today_operator_action_plan"]

    # dislocation_by_symbol (ISSUE-04D — informational, Classes A1/D1/B2)
    result["dislocation_by_symbol"] = _build_dislocation_payload(
        result.get("security_overlays", []),
        ac_by_sym=_build_consensus_payload(),
    )

    # ── STALE-PAR-01: Policy replay on load ──────────────────────────────────
    # Re-apply current operator policy to recommendation dicts on every load.
    # This ensures that if policies changed after the PAR was generated, the
    # loaded recs reflect current policy — not the stale on-disk state.
    #
    # Governance:
    #   - Only execution_state, effective_action, card_lifecycle_state are
    #     mutated (output-layer annotation only).  Scoring, ranking, and
    #     generation logic are untouched.
    #   - The on-disk recommendations.json is NOT rewritten — this is a
    #     live-view transform, not a re-run.
    #   - Policy staleness is signalled via "policy_replay_applied": True so
    #     the UI can display a staleness advisory if desired.
    recs_list = result.get("recommendations", [])
    _load_registry = OperatorPolicyRegistry.load(_OPERATOR_STATE)
    if recs_list:
        _apply_policy_to_recs(recs_list, _load_registry)
        result["policy_replay_applied"] = True
        result["policy_replay_timestamp"] = datetime.now(timezone.utc).isoformat()
    else:
        result["policy_replay_applied"] = False

    # Expose current policy snapshot so the UI can detect policy drift
    result["current_policy_snapshot"] = _load_registry.policy_snapshot()
    # Compare against PAR-time snapshot to flag staleness
    par_policy_snap = (result.get("run_metadata") or {}).get("policy_snapshot", {})
    result["policy_is_stale"] = (par_policy_snap != result["current_policy_snapshot"])

    # ── Reconciliation checks (for UX-PA-02 explainability) ──────────────────
    recon_path = run_dir / "reconciliation.json"
    if recon_path.exists():
        with open(recon_path) as fh:
            recon_data = json.load(fh)
        result["reconciliation_checks"] = recon_data.get("checks", [])
        result["reconciliation_status"] = recon_data.get("overall_status", "")
        result["reconciliation_checks_passed"] = recon_data.get("checks_passed", 0)
        result["reconciliation_checks_failed"] = recon_data.get("checks_failed", 0)
        result["reconciliation_checks_warned"] = recon_data.get("checks_warned", 0)
        result["reconciliation_certification"] = recon_data.get("certification", "")

    # For pre-upgrade runs that lack embedded drilldown, compute on demand
    if (
        recs_list
        and holdings_for_drilldown
        and not any("drilldown" in r for r in recs_list)
    ):
        dd_map = _build_drilldown_data(
            holdings=holdings_for_drilldown,
            alignment_results=result.get("alignment", []),
            overlays=result.get("security_overlays", []),
            recs=recs_list,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        for rec in recs_list:
            rid = rec.get("recommendation_id", "")
            if rid in dd_map:
                rec["drilldown"] = dd_map[rid]

    return result
