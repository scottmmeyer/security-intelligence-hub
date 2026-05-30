"""
Recalculation engine: propose updated targets driven by replay evidence.

Never auto-commits. Returns a PROPOSED AllocationRecalculationSnapshot + updated targets.

Evidence scoring formula:
    evidence_weight = outperformance_persistence × (1 − volatility_penalty)
    proposed_delta  = (evidence_weight − 0.5) × max_delta × 2

Governance caps applied per node. Sibling normalization preserves parent=100%.
LOW/NONE sophistication nodes are skipped (methodology baseline only).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .dimensions_loader import AllocationDimensionNode, get_ancestry_chain
from .models import (
    AllocationEvidence,
    AllocationRecalculationSnapshot,
    StrategicAllocationTarget,
)
from .structural_policy import StructuralPolicy

_MIN_EVIDENCE_WEIGHT_MOVE = 0.52   # must be meaningfully above 0.5 to trigger adjustment


def propose_recalculation(
    current_targets: list[StrategicAllocationTarget],
    evidence_records: list[AllocationEvidence],
    all_nodes: dict[str, AllocationDimensionNode],
    policy: StructuralPolicy,
    prior_recalculation_id: str | None = None,
    snapshot_date: str | None = None,
) -> tuple[AllocationRecalculationSnapshot, list[StrategicAllocationTarget]]:
    """
    Given current targets and fresh evidence, compute proposed deltas.

    Returns (snapshot, proposed_targets).
    snapshot.triggered_by = 'EVIDENCE_THRESHOLD' if any deltas proposed, else 'SCHEDULED'.
    """
    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    recalculation_id = f"PROP_{snapshot_date.replace('-', '')}_{uuid.uuid4().hex[:8].upper()}"

    # Index current targets by node_key
    current_map: dict[str, StrategicAllocationTarget] = {t.node_key: t for t in current_targets}

    # Index evidence by node_key (aggregate across multiple evidence records per node)
    node_evidence: dict[str, list[AllocationEvidence]] = {}
    for ev in evidence_records:
        node_evidence.setdefault(ev.node_key, []).append(ev)

    # Build pct_of_parent map starting from current values
    pct_of_parent_map: dict[str, float] = {
        t.node_key: t.target_pct_of_parent for t in current_targets
    }

    proposed_targets: list[StrategicAllocationTarget] = []
    change_summaries: list[str] = []
    unchanged_count = 0
    used_evidence_ids: list[str] = []

    for node_key, node in all_nodes.items():
        current = current_map.get(node_key)
        if current is None:
            continue

        # Skip LOW/NONE sophistication nodes
        if node.replay_sophistication in ("LOW", "NONE"):
            proposed_targets.append(current)
            unchanged_count += 1
            continue

        evidence_for_node = node_evidence.get(node_key, [])
        if not evidence_for_node:
            proposed_targets.append(current)
            unchanged_count += 1
            continue

        # Aggregate evidence metrics from replay evidence
        outperformance_persistence = _aggregate_persistence(evidence_for_node)
        volatility_penalty = _aggregate_volatility_penalty(evidence_for_node)

        evidence_weight = outperformance_persistence * (1.0 - volatility_penalty)

        # Skip if evidence is not meaningfully above/below neutral
        if abs(evidence_weight - 0.5) < (_MIN_EVIDENCE_WEIGHT_MOVE - 0.5):
            proposed_targets.append(current)
            unchanged_count += 1
            continue

        # Delta formula
        raw_delta = (evidence_weight - 0.5) * policy.max_recalculation_delta_pct * 2.0
        # Governance cap
        capped_delta = max(-policy.max_recalculation_delta_pct, min(policy.max_recalculation_delta_pct, raw_delta))
        # Minimum meaningful change threshold
        if abs(capped_delta) < policy.min_meaningful_change_pct:
            proposed_targets.append(current)
            unchanged_count += 1
            continue

        new_pct_of_parent = round(
            max(0.1, min(99.9, current.target_pct_of_parent + capped_delta)), 4
        )

        if new_pct_of_parent == current.target_pct_of_parent:
            proposed_targets.append(current)
            unchanged_count += 1
            continue

        # Update pct_of_parent_map for this node (sibling normalization done below)
        pct_of_parent_map[node_key] = new_pct_of_parent

        ev_ids_for_node = tuple(ev.evidence_id for ev in evidence_for_node)
        used_evidence_ids.extend(ev_ids_for_node)

        change_summaries.append(
            f"{node_key}: {current.target_pct_of_parent:.2f}% → {new_pct_of_parent:.2f}% "
            f"(Δ{capped_delta:+.2f}%, evidence_weight={evidence_weight:.3f})"
        )

        # Create updated target (pct_of_total recomputed after normalization below)
        proposed_targets.append(
            StrategicAllocationTarget(
                target_id=f"TGT_{recalculation_id}_{node_key.replace('.', '_')}",
                snapshot_date=snapshot_date,
                recalculation_id=recalculation_id,
                node_key=current.node_key,
                node_label=current.node_label,
                parent_key=current.parent_key,
                asset_class=current.asset_class,
                geography=current.geography,
                market_structure=current.market_structure,
                mega_subtier=current.mega_subtier,
                hierarchy_depth=current.hierarchy_depth,
                target_pct_of_parent=new_pct_of_parent,
                target_pct_of_total=0.0,  # placeholder; filled below
                prior_target_pct_of_total=current.target_pct_of_total,
                delta_pct=round(capped_delta, 4),
                confidence_score=_aggregate_confidence(evidence_for_node, policy),
                evidence_summary=f"Evidence-driven delta {capped_delta:+.2f}%. Weight={evidence_weight:.3f}. "
                    + (evidence_for_node[0].human_readable[:80] if evidence_for_node else ""),
                evidence_ids=ev_ids_for_node,
                methodology_basis_ref=current.methodology_basis_ref,
                policy_bounded=False,
            )
        )

    # Sibling normalization: ensure siblings still sum to 100%
    proposed_targets = _normalize_siblings(proposed_targets, all_nodes, pct_of_parent_map)

    # Re-propagate pct_of_total from normalized pct_of_parent values
    final_pct_of_parent = {t.node_key: t.target_pct_of_parent for t in proposed_targets}
    proposed_targets = _recompute_pct_of_total(proposed_targets, all_nodes, final_pct_of_parent)

    triggered_by = "EVIDENCE_THRESHOLD" if change_summaries else "SCHEDULED"

    snapshot = AllocationRecalculationSnapshot(
        recalculation_id=recalculation_id,
        recalculation_date=snapshot_date,
        prior_recalculation_id=prior_recalculation_id,
        triggered_by=triggered_by,
        policy_version=policy.policy_id,
        evidence_ids=tuple(set(used_evidence_ids)),
        change_summary=tuple(change_summaries) if change_summaries else ("No changes proposed.",),
        unchanged_summary=f"{unchanged_count} nodes unchanged (LOW/NONE sophistication or insufficient evidence).",
        confidence_summary={t.node_key: t.confidence_score for t in proposed_targets},
        total_allocation_valid=True,
        notes=f"PROPOSED — not yet committed. Run with --commit to publish.",
    )

    return snapshot, proposed_targets


def _aggregate_persistence(evidence_list: list[AllocationEvidence]) -> float:
    """Extract or estimate outperformance_persistence metric from evidence records."""
    vals = [
        ev.metric_value for ev in evidence_list
        if ev.metric_name in ("outperformance_persistence", "relative_return_90d", "relative_return_60d")
        and ev.evidence_type not in ("METHODOLOGY_BASELINE",)
    ]
    if not vals:
        return 0.5  # neutral
    # Normalize to 0–1 range: persistence is already 0–1; returns need scaling
    # relative returns: e.g. 0.05 = 5% outperformance → weight 0.55
    normalized = []
    for ev in evidence_list:
        if ev.metric_name == "outperformance_persistence":
            normalized.append(max(0.0, min(1.0, ev.metric_value)))
        elif ev.metric_name in ("relative_return_90d", "relative_return_60d"):
            # Map +/−15% return range to 0.0–1.0
            normalized.append(max(0.0, min(1.0, 0.5 + ev.metric_value / 30.0)))
    if not normalized:
        return 0.5
    return sum(normalized) / len(normalized)


def _aggregate_volatility_penalty(evidence_list: list[AllocationEvidence]) -> float:
    """Extract volatility_penalty from evidence records; default to 0.0 if absent."""
    vals = [
        ev.metric_value for ev in evidence_list
        if ev.metric_name == "volatility_penalty"
    ]
    if not vals:
        return 0.0
    return max(0.0, min(0.5, sum(vals) / len(vals)))


def _aggregate_confidence(evidence_list: list[AllocationEvidence], policy: StructuralPolicy) -> float:
    """Compute confidence score from evidence. Uses significance levels."""
    sig_map = {"HIGH": 0.85, "MEDIUM": 0.65, "LOW": 0.45}
    scores = [sig_map.get(ev.significance, 0.5) for ev in evidence_list]
    if not scores:
        return policy.confidence_threshold
    return round(sum(scores) / len(scores), 4)


def _normalize_siblings(
    targets: list[StrategicAllocationTarget],
    all_nodes: dict[str, AllocationDimensionNode],
    pct_of_parent_map: dict[str, float],
) -> list[StrategicAllocationTarget]:
    """
    For every parent that has changed children, proportionally renormalize unchanged
    siblings so that the group still sums to 100%.
    """
    import dataclasses

    # Group targets by parent_key
    by_parent: dict[str | None, list[StrategicAllocationTarget]] = {}
    for t in targets:
        by_parent.setdefault(t.parent_key, []).append(t)

    result_map: dict[str, StrategicAllocationTarget] = {t.node_key: t for t in targets}

    for parent_key, sibling_targets in by_parent.items():
        if parent_key is None:
            continue
        current_sum = sum(t.target_pct_of_parent for t in sibling_targets)
        if abs(current_sum - 100.0) < 0.005:
            continue  # already balanced

        # Find the "changed" nodes vs. "unchanged" nodes in this sibling group
        changed_keys = {
            key for key, pct in pct_of_parent_map.items()
            if any(t.node_key == key and t.target_pct_of_parent != t.prior_target_pct_of_total
                   for t in sibling_targets)
        }
        # Simpler: find which nodes were recently updated (have a delta)
        changed_targets = [t for t in sibling_targets if t.delta_pct is not None and t.delta_pct != 0.0]
        unchanged_targets = [t for t in sibling_targets if not (t.delta_pct is not None and t.delta_pct != 0.0)]

        if not unchanged_targets:
            continue  # can't re-balance if all changed

        changed_sum = sum(t.target_pct_of_parent for t in changed_targets)
        residual = 100.0 - changed_sum
        unchanged_prior_sum = sum(t.target_pct_of_parent for t in unchanged_targets)

        if unchanged_prior_sum <= 0:
            continue

        scale = residual / unchanged_prior_sum
        for t in unchanged_targets:
            new_pct = round(t.target_pct_of_parent * scale, 4)
            result_map[t.node_key] = dataclasses.replace(t, target_pct_of_parent=new_pct)

    return list(result_map.values())


def _recompute_pct_of_total(
    targets: list[StrategicAllocationTarget],
    all_nodes: dict[str, AllocationDimensionNode],
    pct_of_parent_map: dict[str, float],
) -> list[StrategicAllocationTarget]:
    """Recompute target_pct_of_total for all targets using ancestry chain product."""
    import dataclasses

    result: list[StrategicAllocationTarget] = []
    for target in targets:
        chain = get_ancestry_chain(target.node_key, all_nodes)
        pct_of_total = 1.0
        for ancestor in chain:
            p = pct_of_parent_map.get(ancestor.key)
            if p is None:
                pct_of_total = 0.0
                break
            pct_of_total *= p / 100.0
        new_pct = round(pct_of_total * 100.0, 4)
        if new_pct != target.target_pct_of_total:
            result.append(dataclasses.replace(target, target_pct_of_total=new_pct))
        else:
            result.append(target)

    return result
