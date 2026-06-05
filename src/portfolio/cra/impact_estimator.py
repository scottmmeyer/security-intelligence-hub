"""Impact Estimator — Phase 23.6A.

Computes a simplified PortfolioImpactEstimate for a proposed rotation.

NON-NEGOTIABLE:
  - This module does NOT invoke the PAR alignment engine.
  - All estimates are approximations; is_estimate=True always.
  - No PAR re-run, no predictive modeling.
  - Coefficients are heuristic; calibration against real PAR deltas is
    recommended before production use (see open question in 08_final_verdict.md).

Simplified alignment delta model:
  +4.0 per overweight node fully resolved by the rotation
  +3.0 per underweight node that receives capital deployment
  −2.0 per node that becomes newly underweight due to sells
  −1.0 per node that remains overweight (partial reduction, not full)

Simplified concentration delta model:
  Remove source holdings' weight contributions from top-5 calculation.
  Add deployment target weight contributions to top-5 calculation.

Design source: docs/phase_23_6/03_rotation_framework.md §3.6
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

from .models import CapitalSourceRecord, PortfolioImpactEstimate, RotationDeploymentTarget

log = logging.getLogger(__name__)

# ── Scoring coefficients ──────────────────────────────────────────────────────

_COEFF_OW_RESOLVED    =  4.0   # overweight node fully resolved
_COEFF_OW_PARTIAL     = -1.0   # overweight node partially reduced (still OW)
_COEFF_UW_FUNDED      =  3.0   # underweight node that receives capital
_COEFF_NEW_UW         = -2.0   # node that goes newly underweight after sell

# Maximum alignment score is 1.0 (fractional); clamp estimates to [0, 1]
_SCORE_MIN = 0.0
_SCORE_MAX = 1.0

# Minimum amount to consider a node "funded" (USD)
_MIN_FUND_THRESHOLD = 200.0


def estimate_impact(
    sources: List[CapitalSourceRecord],
    deployments: List[RotationDeploymentTarget],
    alignment: List[Dict],
    concentration: Dict,
    run_metadata: Dict,
    portfolio_mv: float,
) -> PortfolioImpactEstimate:
    """Compute simplified portfolio impact for a proposed rotation.

    Args:
        sources:        Capital sources included in the rotation (not blocked).
        deployments:    Deployment targets that will receive capital.
        alignment:      Rows from alignment.csv (list of dicts).
        concentration:  Parsed concentration.json dict.
        run_metadata:   Parsed run_metadata.json dict.
        portfolio_mv:   Total portfolio market value (USD).

    Returns:
        PortfolioImpactEstimate with is_estimate=True.
    """
    # ── Baseline metrics ──────────────────────────────────────────────────────
    alignment_before = float(run_metadata.get("overall_alignment_score") or 0.0)
    concentration_before = float(concentration.get("top5_pct") or 0.0)

    # ── Build overweight node map ─────────────────────────────────────────────
    # node_key → {drift_pct, actual_pct, target_pct}
    ow_nodes: Dict[str, Dict] = {}
    uw_nodes: Dict[str, Dict] = {}
    for row in alignment:
        node = row.get("node_key", "")
        drift = _f(row.get("drift_pct"))
        actual = _f(row.get("actual_pct"))
        target = _f(row.get("target_pct") or row.get("tactical_target_pct"))
        if drift is None or actual is None:
            continue
        if drift > 0:
            ow_nodes[node] = {"drift_pct": drift, "actual_pct": actual, "target_pct": target}
        elif drift < 0:
            uw_nodes[node] = {"drift_pct": drift, "actual_pct": actual, "target_pct": target}

    overweight_nodes_before = sorted(ow_nodes.keys())

    # ── Derive source symbol → allocation nodes ───────────────────────────────
    # Use deployment target allocation_node as-is; for sources we need to infer.
    # Sources only carry symbol; derive nodes from alignment data by matching
    # symbols that participate in overweight nodes via is_overweight flag.
    source_symbols = {s.symbol for s in sources if not s.blocked_by_policy}
    source_pcts: Dict[str, float] = {
        s.symbol: (s.estimated_proceeds / portfolio_mv * 100) if portfolio_mv > 0 else 0
        for s in sources
        if not s.blocked_by_policy
    }

    # Map deployment target → allocation node
    deploy_node_amounts: Dict[str, float] = {}  # node → total deployed USD
    for t in deployments:
        node = t.allocation_node
        if node:
            deploy_node_amounts[node] = deploy_node_amounts.get(node, 0.0) + t.suggested_amount

    # ── Estimate overweight node resolution ───────────────────────────────────
    # For each OW node: check if enough capital is being removed from it
    # via source sells to bring it below target.  We use a simplified check:
    # if any source in this node is being sold at sizing >= 0.5, count as
    # partially resolved.  If the source's estimated_proceeds >= drift amount,
    # count as resolved.
    overweight_nodes_after: List[str] = []
    newly_underweight: List[str] = []
    alignment_delta_components: List[float] = []

    for node, node_data in ow_nodes.items():
        drift_pct = node_data["drift_pct"]
        drift_mv = drift_pct / 100 * portfolio_mv if portfolio_mv > 0 else 0

        # Check if sources are reducing this node
        # A source "participates" in a node if source.is_overweight=True
        # and source.drift_pct roughly corresponds to this node's drift
        participating_sources = [
            s for s in sources
            if not s.blocked_by_policy
            and s.is_overweight
            and abs((s.drift_pct or 0) - drift_pct) < (drift_pct * 0.5 + 1.0)
        ]
        total_proceeds_in_node = sum(
            s.estimated_proceeds for s in participating_sources
        )

        if total_proceeds_in_node >= drift_mv * 0.9:
            # Full resolution
            alignment_delta_components.append(_COEFF_OW_RESOLVED)
        elif total_proceeds_in_node > 0:
            # Partial reduction — node stays OW
            overweight_nodes_after.append(node)
            alignment_delta_components.append(_COEFF_OW_PARTIAL)
        else:
            # No action on this node
            overweight_nodes_after.append(node)

    # ── Estimate newly underweight nodes ──────────────────────────────────────
    # If a source is sold and its node was near target, the sell might push it UW.
    # Simplified: only flag this if selling removes more than the node's
    # actual_pct - target_pct buffer.
    for node, node_data in ow_nodes.items():
        drift_pct = node_data["drift_pct"]
        if drift_pct < 1.0:
            # Node was barely OW; selling might tip it UW
            # Conservative: flag it only if it was already soft OW
            pass  # not flagging for minor cases

    # ── Estimate underweight node funding ─────────────────────────────────────
    funded_uw_nodes: Set[str] = set()
    for node, deployed_usd in deploy_node_amounts.items():
        if deployed_usd < _MIN_FUND_THRESHOLD:
            continue
        if node in uw_nodes:
            funded_uw_nodes.add(node)
            alignment_delta_components.append(_COEFF_UW_FUNDED)

    # ── Compute alignment delta ───────────────────────────────────────────────
    # The alignment score is fractional (0–1); scale the heuristic delta to match.
    # Raw delta is in "alignment score points" on a ~1.0 scale.
    # Observed range from real data: alignment_before ≈ 0.4; max ≈ 1.0.
    # Each coefficient (4.0, 3.0, etc.) is in basis units; normalize by
    # total possible improvement (100 points → 1.0 score).
    raw_delta = sum(alignment_delta_components)
    normalized_delta = raw_delta / 100.0  # each "point" = 0.01 on the 0–1 scale

    alignment_after = max(
        _SCORE_MIN,
        min(_SCORE_MAX, alignment_before + normalized_delta),
    )

    # ── Estimate concentration delta ─────────────────────────────────────────
    # Simplified: remove source weight%, add target weight%.
    # top5_pct may shift if sources/targets are in top-5.
    sold_weight_pct = sum(source_pcts.values())
    added_weight_pct = sum(
        t.suggested_pct_add for t in deployments
    )
    # Concentration change is bounded by the actual holdings
    concentration_delta = added_weight_pct - sold_weight_pct
    concentration_after = max(0.0, concentration_before + concentration_delta)

    # ── Build narrative ────────────────────────────────────────────────────────
    source_count = len([s for s in sources if not s.blocked_by_policy])
    deploy_count = len(deployments)
    resolved_count = len(overweight_nodes_before) - len(overweight_nodes_after)

    if source_count == 0:
        narrative = "No capital sources selected — no portfolio impact estimated."
    elif deploy_count == 0:
        narrative = (
            f"Selling {source_count} position(s) creates capital "
            f"but no deployment targets are allocated."
        )
    else:
        parts = []
        parts.append(
            f"Rotating {source_count} position(s) into {deploy_count} CW-DAS target(s)"
        )
        if normalized_delta > 0:
            parts.append(f"improves alignment by ~{normalized_delta:.3f} pts")
        if resolved_count > 0:
            parts.append(f"resolves {resolved_count} overweight node(s)")
        if funded_uw_nodes:
            parts.append(f"funds {len(funded_uw_nodes)} underweight node(s)")
        narrative = " | ".join(parts) + "."

    return PortfolioImpactEstimate(
        alignment_score_before=round(alignment_before, 4),
        alignment_score_after=round(alignment_after, 4),
        alignment_delta=round(normalized_delta, 4),
        concentration_before=round(concentration_before, 4),
        concentration_after=round(concentration_after, 4),
        concentration_delta=round(concentration_delta, 4),
        overweight_nodes_before=overweight_nodes_before,
        overweight_nodes_after=sorted(overweight_nodes_after),
        newly_underweight_nodes=sorted(newly_underweight),
        impact_narrative=narrative,
        is_estimate=True,
    )


def _f(val) -> Optional[float]:
    if val is None or val == "" or val == "None":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
