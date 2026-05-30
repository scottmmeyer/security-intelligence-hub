"""Phase E — Target Alignment Engine.

Compares actual portfolio allocations against SIH strategic targets and
optionally applies tactical overlays.

Mapping logic:
  Each PortfolioHolding maps to zero or more hierarchy nodes based on its
  classification dimensions.  The contribution to each node's actual % is
  the holding's percent_of_portfolio.

Node → holding mapping rules:
  EQUITIES                    ← asset_class == EQUITIES
  FIXED_INCOME                ← asset_class == FIXED_INCOME
  DIGITAL                     ← asset_class == DIGITAL
  COMMODITIES                 ← asset_class == COMMODITIES
  CASH                        ← asset_class == CASH
  EQUITIES.US                 ← EQUITIES + geography == US
  EQUITIES.US.MEGA            ← above + market_cap_bucket == MEGA
  EQUITIES.US.MEGA.HYPER_MEGA ← above + mega_subtier == HYPER_MEGA
  ... etc.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from .exposure_decomposition import build_exposure_maps, build_holding_exposure_contribs
from .models import (
    AllocationAlignmentResult,
    ConcentrationRiskSummary,
    PortfolioHolding,
)


# ─────────────────────────────────────────────────────────────────────────────
# Load SIH targets
# ─────────────────────────────────────────────────────────────────────────────

def load_targets(
    targets_csv: str = "data/current/strategic_allocation_targets.csv",
    overlays_csv: str = "data/current/tactical_overlays.csv",
) -> dict[str, dict]:
    """Return node_key → target row dict from strategic_allocation_targets.csv.

    Applies active tactical overlays by adjusting target_pct_of_total.
    Returns a plain dict for each node with keys:
      target_pct_of_total, tactical_target_pct_of_total, node_label,
      parent_key, hierarchy_depth, recalculation_id
    """
    targets: dict[str, dict] = {}
    if os.path.exists(targets_csv):
        for row in csv.DictReader(open(targets_csv)):
            key = row.get("node_key", "").strip()
            if not key:
                continue
            try:
                tgt = float(row.get("target_pct_of_total") or 0)
            except ValueError:
                tgt = 0.0
            targets[key] = {
                "target_pct_of_total": tgt,
                "tactical_target_pct_of_total": tgt,   # default; overlays applied below
                "node_label": row.get("node_label", key),
                "parent_key": row.get("parent_key") or None,
                "hierarchy_depth": int(row.get("hierarchy_depth") or 1),
                "recalculation_id": row.get("recalculation_id", ""),
                "dimension_type": _infer_dimension_type(key),
            }

    # Apply active tactical overlays
    if os.path.exists(overlays_csv):
        for row in csv.DictReader(open(overlays_csv)):
            if row.get("status", "").upper() != "ACTIVE":
                continue
            dim_type = row.get("dimension_type", "")
            dim_val = row.get("dimension_value", "")
            try:
                overlay_pct = float(row.get("overlay_pct") or 0)
            except ValueError:
                overlay_pct = 0.0
            # Find matching node keys by dimension_value substring
            for key, node in targets.items():
                if dim_val.upper() in key.upper():
                    node["tactical_target_pct_of_total"] = (
                        node["target_pct_of_total"] + overlay_pct
                    )

    return targets


def _infer_dimension_type(node_key: str) -> str:
    depth = node_key.count(".") + 1
    if depth == 1:
        return "ASSET_CLASS"
    if depth == 2:
        return "GEOGRAPHY"
    if depth == 3:
        return "MARKET_CAP"
    if depth == 4:
        return "MEGA_SUBTIER"
    return "OTHER"


# ─────────────────────────────────────────────────────────────────────────────
# Holding → node contribution
# ─────────────────────────────────────────────────────────────────────────────

def _holding_node_keys(h: PortfolioHolding) -> list[str]:
    """Return all hierarchy node keys that this holding contributes to."""
    _, effective, _ = build_holding_exposure_contribs(h)
    return list(effective.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Severity classification
# ─────────────────────────────────────────────────────────────────────────────

def _severity(drift: float, dimension_type: str) -> str:
    """Classify drift severity. Thresholds are dimension-aware."""
    abs_drift = abs(drift)
    # Leaf nodes (mega subtier) — tighter thresholds
    if dimension_type in ("MEGA_SUBTIER",):
        if abs_drift >= 5.0:   return "HIGH"
        if abs_drift >= 2.5:   return "MODERATE"
        if abs_drift >= 1.0:   return "LOW"
    elif dimension_type == "ASSET_CLASS":
        if abs_drift >= 10.0:  return "HIGH"
        if abs_drift >= 5.0:   return "MODERATE"
        if abs_drift >= 2.0:   return "LOW"
    else:
        if abs_drift >= 8.0:   return "HIGH"
        if abs_drift >= 4.0:   return "MODERATE"
        if abs_drift >= 1.5:   return "LOW"
    return "NONE"


def _concentration_risk(actual_pct: float, node_key: str) -> str:
    """Flag concentration risk when actual allocation is very large."""
    # Heuristics per node type
    thresholds = {
        "EQUITIES.US.MEGA.HYPER_MEGA": (20, 35),
        "EQUITIES.US.MEGA":            (30, 45),
        "EQUITIES.US":                 (55, 70),
        "EQUITIES":                    (75, 85),
    }
    lo, hi = thresholds.get(node_key, (40, 60))
    if actual_pct >= hi:   return "HIGH"
    if actual_pct >= lo:   return "MODERATE"
    return "LOW"


def _alignment_score(drift: float, target: float) -> float:
    """0.0–1.0 alignment score.  1.0 = exactly on target."""
    if target <= 0:
        return 1.0 if drift == 0 else 0.0
    normalized_error = min(abs(drift) / max(target, 1.0), 1.0)
    return round(1.0 - normalized_error, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Archetype-override target builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_targets_from_override(
    override: dict[str, float],
    overlays_csv: str = "data/current/tactical_overlays.csv",
) -> dict[str, dict]:
    """Build a targets dict matching the load_targets() format from a flat
    node_key → target_pct_of_total override dict.

    Tactical overlays from overlays_csv are applied on top of the override
    values.  Metadata fields (node_label, parent_key, hierarchy_depth,
    recalculation_id) are inferred from the node key.
    """
    targets: dict[str, dict] = {}
    for key, tgt in override.items():
        depth = key.count(".") + 1
        parent_key: Optional[str] = ".".join(key.split(".")[:-1]) if depth > 1 else None
        targets[key] = {
            "target_pct_of_total": float(tgt),
            "tactical_target_pct_of_total": float(tgt),
            "node_label": key,
            "parent_key": parent_key,
            "hierarchy_depth": depth,
            "recalculation_id": "ARCHETYPE_OVERRIDE",
            "dimension_type": _infer_dimension_type(key),
        }

    # Apply active tactical overlays on top
    if os.path.exists(overlays_csv):
        for row in csv.DictReader(open(overlays_csv)):
            if row.get("status", "").upper() != "ACTIVE":
                continue
            dim_val = row.get("dimension_value", "")
            try:
                overlay_pct = float(row.get("overlay_pct") or 0)
            except ValueError:
                overlay_pct = 0.0
            for key, node in targets.items():
                if dim_val.upper() in key.upper():
                    node["tactical_target_pct_of_total"] = (
                        node["target_pct_of_total"] + overlay_pct
                    )

    return targets


# ─────────────────────────────────────────────────────────────────────────────
# Public alignment engine
# ─────────────────────────────────────────────────────────────────────────────

def compute_alignment(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    targets_csv: str = "data/current/strategic_allocation_targets.csv",
    overlays_csv: str = "data/current/tactical_overlays.csv",
    targets_override: Optional[dict[str, float]] = None,
) -> list[AllocationAlignmentResult]:
    """Compute per-node alignment for the given holdings.

    Returns one AllocationAlignmentResult per node that either has a target or
    has actual holdings.

    When targets_override is provided (a dict of node_key → target_pct_of_total
    from an archetype profile), it replaces the CSV-based targets.  Tactical
    overlays from overlays_csv are still applied on top of the override values.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    if targets_override:
        targets = _build_targets_from_override(targets_override, overlays_csv)
    else:
        targets = load_targets(targets_csv, overlays_csv)

    direct_actual, effective_actual, _effective_sector = build_exposure_maps(holdings)

    # Build results for all nodes that appear in targets OR have actual holdings
    all_keys = set(targets.keys()) | set(direct_actual.keys()) | set(effective_actual.keys())
    results: list[AllocationAlignmentResult] = []

    for key in sorted(all_keys):
        direct_act = direct_actual.get(key, 0.0)
        effective_act = effective_actual.get(key, 0.0)
        node = targets.get(key, {})
        tgt = node.get("target_pct_of_total", 0.0)
        tac = node.get("tactical_target_pct_of_total", tgt)
        label = node.get("node_label", key)
        dim_type = node.get("dimension_type", _infer_dimension_type(key))

        drift = round(effective_act - tac, 4)
        direction = (
            "OVERWEIGHT"  if drift > 0.5  else
            "UNDERWEIGHT" if drift < -0.5 else
            "ON_TARGET"
        )
        sev = _severity(drift, dim_type)
        conc = _concentration_risk(effective_act, key)
        score = _alignment_score(drift, tac)
        etf_act = max(0.0, effective_act - direct_act)
        method = "HEURISTIC_REGISTRY_V1" if etf_act > 0.0 else "DIRECT_CLASSIFICATION"
        confidence = 0.75 if etf_act > 0.0 else 1.0

        # Priority: HIGH severity = 1, MODERATE = 2, LOW = 3, NONE = 4
        priority = {"HIGH": 1, "MODERATE": 2, "LOW": 3, "NONE": 4}.get(sev, 4)

        results.append(AllocationAlignmentResult(
            analysis_run_id=analysis_run_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            node_key=key,
            node_label=label,
            dimension_type=dim_type,
            actual_pct=round(effective_act, 4),
            target_pct=round(tgt, 4),
            tactical_target_pct=round(tac, 4),
            drift_pct=drift,
            drift_direction=direction,
            severity=sev,
            concentration_risk=conc,
            alignment_score=score,
            recommendation_priority=priority,
            created_at_utc=now_utc,
            direct_actual_pct=round(direct_act, 4),
            etf_derived_actual_pct=round(etf_act, 4),
            effective_actual_pct=round(effective_act, 4),
            decomposition_method=method,
            decomposition_version="etf-exposure-decomp-v1",
            decomposition_confidence=confidence,
            decomposition_source="REGISTRY" if etf_act > 0.0 else "DIRECT_CLASSIFICATION",
            decomposition_confidence_tier="HIGH" if confidence >= 0.75 else "MEDIUM",
        ))

    # Sort by priority then absolute drift
    results.sort(key=lambda r: (r.recommendation_priority, -abs(r.drift_pct)))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Concentration risk summary
# ─────────────────────────────────────────────────────────────────────────────

def compute_concentration(
    analysis_run_id: str,
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
) -> ConcentrationRiskSummary:
    """Compute portfolio-level concentration metrics."""
    now_utc = datetime.now(timezone.utc).isoformat()
    by_pct = sorted(holdings, key=lambda h: h.percent_of_portfolio, reverse=True)
    direct_node, effective_node, effective_sector = build_exposure_maps(holdings)

    top1 = by_pct[0] if by_pct else None
    top3_pct = sum(h.percent_of_portfolio for h in by_pct[:3])
    top5_pct = sum(h.percent_of_portfolio for h in by_pct[:5])
    top10_pct = sum(h.percent_of_portfolio for h in by_pct[:10])

    hyper_key_prefix = "EQUITIES."
    hyper_suffix = ".MEGA.HYPER_MEGA"
    hyper_effective = sum(
        pct for key, pct in effective_node.items()
        if key.startswith(hyper_key_prefix) and key.endswith(hyper_suffix)
    )
    hyper_direct = sum(
        pct for key, pct in direct_node.items()
        if key.startswith(hyper_key_prefix) and key.endswith(hyper_suffix)
    )
    hyper_etf = max(0.0, hyper_effective - hyper_direct)

    # Sector concentration
    top_sector = max(effective_sector, key=lambda k: effective_sector[k], default="UNKNOWN")
    top_sector_pct = effective_sector.get(top_sector, 0.0)

    # Geography
    us_pct = sum(pct for key, pct in effective_node.items() if key == "EQUITIES.US")
    intl_pct = sum(pct for key, pct in effective_node.items() if key == "EQUITIES.INTERNATIONAL")
    em_pct = sum(pct for key, pct in effective_node.items() if key == "EQUITIES.EMERGING_MARKETS")

    # Herfindahl–Hirschman Index (position-level)
    total = sum(h.percent_of_portfolio for h in holdings) or 100.0
    hhi = sum((h.percent_of_portfolio / total) ** 2 for h in holdings)

    if hhi >= 0.25:     tier = "CRITICAL"
    elif hhi >= 0.15:   tier = "HIGH"
    elif hhi >= 0.08:   tier = "MODERATE"
    else:               tier = "DIVERSIFIED"

    return ConcentrationRiskSummary(
        analysis_run_id=analysis_run_id,
        portfolio_snapshot_id=portfolio_snapshot_id,
        top1_symbol=top1.symbol if top1 else "",
        top1_pct=round(top1.percent_of_portfolio, 4) if top1 else 0.0,
        top3_pct=round(top3_pct, 4),
        top5_pct=round(top5_pct, 4),
        top10_pct=round(top10_pct, 4),
        mega_subtier_pct=round(hyper_effective, 4),
        mega_subtier_direct_pct=round(hyper_direct, 4),
        mega_subtier_etf_derived_pct=round(hyper_etf, 4),
        mega_subtier_effective_pct=round(hyper_effective, 4),
        single_sector_max_pct=round(top_sector_pct, 4),
        single_sector_max_label=top_sector,
        us_pct=round(us_pct, 4),
        international_pct=round(intl_pct, 4),
        emerging_pct=round(em_pct, 4),
        herfindahl_index=round(hhi, 6),
        concentration_tier=tier,
        created_at_utc=now_utc,
    )
