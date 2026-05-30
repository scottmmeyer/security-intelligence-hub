"""
Eight validators for the allocation intelligence pipeline.
Each validator returns list[str] — empty list means pass.
"""

from __future__ import annotations

from .dimensions_loader import AllocationDimensionNode
from .models import (
    AllocationEvidence,
    AllocationRecalculationSnapshot,
    StrategicAllocationTarget,
    TacticalMomentumOverlay,
)
from .structural_policy import StructuralPolicy, get_asset_class_ceiling

_SUM_TOLERANCE = 0.01


def validate_hierarchy_sums(
    targets: list[StrategicAllocationTarget],
    all_nodes: dict[str, AllocationDimensionNode],
) -> list[str]:
    """
    Validator 1: Each parent's children must sum to 100.0 ±0.01.
    """
    errors: list[str] = []
    target_map: dict[str, StrategicAllocationTarget] = {t.node_key: t for t in targets}

    checked: set[str] = set()
    for node_key, node in all_nodes.items():
        if not node.children or node_key in checked:
            continue
        checked.add(node_key)

        child_sum = 0.0
        missing = []
        for child_key in node.children:
            child_target = target_map.get(child_key)
            if child_target is None:
                missing.append(child_key)
            else:
                child_sum += child_target.target_pct_of_parent

        if missing:
            errors.append(f"Parent '{node_key}': missing targets for children {missing}")
        elif abs(child_sum - 100.0) > _SUM_TOLERANCE:
            errors.append(
                f"Parent '{node_key}': children sum to {child_sum:.4f}% (expected 100.0 ±{_SUM_TOLERANCE})"
            )

    return errors


def validate_policy_bounds(
    targets: list[StrategicAllocationTarget],
    policy: StructuralPolicy,
) -> list[str]:
    """
    Validator 2: pct_of_total must not exceed asset class ceiling.
    Also checks max_single_asset_class_pct for L1 nodes.
    """
    errors: list[str] = []

    for target in targets:
        ceiling = get_asset_class_ceiling(policy, target.asset_class)
        # L1 nodes: check against max_single_asset_class_pct
        if target.hierarchy_depth == 1:
            effective_ceiling = min(ceiling, policy.max_single_asset_class_pct)
            if target.target_pct_of_total > effective_ceiling + _SUM_TOLERANCE:
                errors.append(
                    f"{target.node_key}: pct_of_total={target.target_pct_of_total:.2f}% "
                    f"exceeds ceiling {effective_ceiling:.1f}%"
                )

        # Cash floor check
        if target.asset_class == "CASH" and target.hierarchy_depth == 1:
            if target.target_pct_of_total < policy.cash_floor_pct - _SUM_TOLERANCE:
                errors.append(
                    f"CASH: {target.target_pct_of_total:.2f}% is below cash_floor_pct={policy.cash_floor_pct:.1f}%"
                )

        # Digital assets ceiling
        if target.asset_class == "DIGITAL" and target.hierarchy_depth == 1:
            if target.target_pct_of_total > policy.max_digital_assets_pct + _SUM_TOLERANCE:
                errors.append(
                    f"DIGITAL: {target.target_pct_of_total:.2f}% exceeds max_digital_assets_pct={policy.max_digital_assets_pct:.1f}%"
                )

        # International minimum (sum of EQUITIES.INTERNATIONAL + EQUITIES.EMERGING_MARKETS)
        # checked at aggregate level in validate_concentration_ceilings

    return errors


def validate_tactical_overflow(
    targets: list[StrategicAllocationTarget],
    overlays: list[TacticalMomentumOverlay],
    policy: StructuralPolicy,
) -> list[str]:
    """
    Validator 3: strategic_target + max_overlay must not exceed asset class ceiling.
    Only applies to equity (HIGH sophistication) nodes.
    """
    errors: list[str] = []
    active_overlays = [ov for ov in overlays if ov.status == "ACTIVE"]

    for target in targets:
        if not target.node_key.startswith("EQUITIES."):
            continue

        # Find max applicable overlay for this node
        max_applicable_overlay = 0.0
        for ov in active_overlays:
            key_parts = target.node_key.split(".")
            dv = ov.dimension_value.upper()
            matched = False
            if ov.dimension_type == "MARKET_CAP" and len(key_parts) >= 3:
                matched = key_parts[2] == dv
            elif ov.dimension_type == "GEOGRAPHY" and len(key_parts) >= 2:
                matched = key_parts[1] == dv
            if matched:
                max_applicable_overlay = max(max_applicable_overlay, abs(ov.max_overlay_pct))

        ceiling = get_asset_class_ceiling(policy, target.asset_class)
        worst_case = target.target_pct_of_total + max_applicable_overlay
        if worst_case > ceiling + _SUM_TOLERANCE:
            errors.append(
                f"{target.node_key}: strategic {target.target_pct_of_total:.2f}% + "
                f"max_overlay {max_applicable_overlay:.2f}% = {worst_case:.2f}% "
                f"exceeds ceiling {ceiling:.1f}%"
            )

    return errors


def validate_overlay_staleness(
    overlays: list[TacticalMomentumOverlay],
    as_of_date: str | None = None,
) -> list[str]:
    """
    Validator 4: No ACTIVE overlay should have a past expiry_date.
    """
    from datetime import datetime, timezone
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    errors: list[str] = []
    for ov in overlays:
        if ov.status == "ACTIVE" and ov.expiry_date and ov.expiry_date < as_of_date:
            errors.append(
                f"Overlay '{ov.overlay_id}' ({ov.dimension_value}) expired on {ov.expiry_date} "
                f"but still ACTIVE"
            )
    return errors


def validate_recalculation_churn(
    proposed_targets: list[StrategicAllocationTarget],
    policy: StructuralPolicy,
) -> list[str]:
    """
    Validator 5: |delta_pct| must not exceed max_recalculation_delta_pct.
    Skip LOW/NONE sophistication nodes (they always have delta_pct=None).
    """
    errors: list[str] = []
    for target in proposed_targets:
        if target.delta_pct is None:
            continue
        if abs(target.delta_pct) > policy.max_recalculation_delta_pct + 0.001:
            errors.append(
                f"{target.node_key}: |delta_pct|={abs(target.delta_pct):.3f}% "
                f"exceeds max_recalculation_delta_pct={policy.max_recalculation_delta_pct:.1f}%"
            )
    return errors


def validate_evidence_alignment(
    proposed_targets: list[StrategicAllocationTarget],
    evidence_records: list[AllocationEvidence],
) -> list[str]:
    """
    Validator 6: Evidence direction must match delta sign.
    Skip METHODOLOGY_BASELINE evidence (no directional signal).
    """
    errors: list[str] = []
    ev_by_node: dict[str, list[AllocationEvidence]] = {}
    for ev in evidence_records:
        if ev.evidence_type != "METHODOLOGY_BASELINE":
            ev_by_node.setdefault(ev.node_key, []).append(ev)

    for target in proposed_targets:
        if target.delta_pct is None or abs(target.delta_pct) < 0.001:
            continue
        node_evidence = ev_by_node.get(target.node_key, [])
        if not node_evidence:
            continue

        # Check dominant direction of evidence
        returns = [ev.metric_value for ev in node_evidence if ev.metric_name == "relative_return_90d"]
        if not returns:
            continue
        mean_return = sum(returns) / len(returns)
        if mean_return > 0 and target.delta_pct < 0:
            errors.append(
                f"{target.node_key}: delta_pct={target.delta_pct:+.3f}% conflicts "
                f"with positive evidence (mean_relative_return={mean_return:+.3f})"
            )
        elif mean_return < 0 and target.delta_pct > 0:
            errors.append(
                f"{target.node_key}: delta_pct={target.delta_pct:+.3f}% conflicts "
                f"with negative evidence (mean_relative_return={mean_return:+.3f})"
            )

    return errors


def validate_concentration_ceilings(
    targets: list[StrategicAllocationTarget],
    policy: StructuralPolicy,
) -> list[str]:
    """
    Validator 7: Specific concentration ceiling checks.
    - Mega concentration: EQUITIES.US.MEGA pct_of_total ≤ max_mega_concentration_pct
    - Micro cap: combined MICRO nodes ≤ max_micro_cap_pct
    - International: INTERNATIONAL + EMERGING ≥ min_international_pct
    """
    errors: list[str] = []
    target_map = {t.node_key: t for t in targets}

    # Mega concentration
    mega_target = target_map.get("EQUITIES.US.MEGA")
    if mega_target and mega_target.target_pct_of_total > policy.max_mega_concentration_pct + _SUM_TOLERANCE:
        errors.append(
            f"EQUITIES.US.MEGA: {mega_target.target_pct_of_total:.2f}% "
            f"exceeds max_mega_concentration_pct={policy.max_mega_concentration_pct:.1f}%"
        )

    # Micro cap
    micro_keys = [k for k in target_map if "MICRO" in k.split(".")]
    micro_sum = sum(target_map[k].target_pct_of_total for k in micro_keys if k in target_map)
    if micro_sum > policy.max_micro_cap_pct + _SUM_TOLERANCE:
        errors.append(
            f"Combined MICRO cap exposure: {micro_sum:.2f}% "
            f"exceeds max_micro_cap_pct={policy.max_micro_cap_pct:.1f}%"
        )

    # International minimum
    intl_target = target_map.get("EQUITIES.INTERNATIONAL")
    em_target = target_map.get("EQUITIES.EMERGING_MARKETS")
    intl_total = (intl_target.target_pct_of_total if intl_target else 0.0) + \
                 (em_target.target_pct_of_total if em_target else 0.0)
    if intl_total < policy.min_international_pct - _SUM_TOLERANCE:
        errors.append(
            f"International + Emerging: {intl_total:.2f}% "
            f"below min_international_pct={policy.min_international_pct:.1f}%"
        )

    return errors


def validate_lineage_completeness(
    targets: list[StrategicAllocationTarget],
    snapshot: AllocationRecalculationSnapshot,
) -> list[str]:
    """
    Validator 8: Required fields must be present on all targets and the snapshot.
    """
    errors: list[str] = []

    required_target_fields = [
        "target_id", "snapshot_date", "recalculation_id", "node_key", "node_label",
        "asset_class", "hierarchy_depth", "target_pct_of_parent", "target_pct_of_total",
        "confidence_score", "methodology_basis_ref",
    ]

    for target in targets:
        for f in required_target_fields:
            val = getattr(target, f, None)
            if val is None or val == "":
                errors.append(f"Target '{target.node_key}' missing required field: {f}")

    if not snapshot.recalculation_id:
        errors.append("Snapshot missing recalculation_id")
    if not snapshot.recalculation_date:
        errors.append("Snapshot missing recalculation_date")
    if not snapshot.evidence_ids:
        errors.append("Snapshot has no evidence_ids — cannot establish lineage")
    if not snapshot.change_summary:
        errors.append("Snapshot has no change_summary")

    return errors


def run_all_validators(
    targets: list[StrategicAllocationTarget],
    snapshot: AllocationRecalculationSnapshot,
    evidence_records: list[AllocationEvidence],
    overlays: list[TacticalMomentumOverlay],
    all_nodes: dict[str, AllocationDimensionNode],
    policy: StructuralPolicy,
) -> dict[str, list[str]]:
    """
    Run all 8 validators. Returns dict of {validator_name: [errors]}.
    Empty list means pass.
    """
    return {
        "hierarchy_sums":         validate_hierarchy_sums(targets, all_nodes),
        "policy_bounds":          validate_policy_bounds(targets, policy),
        "tactical_overflow":      validate_tactical_overflow(targets, overlays, policy),
        "overlay_staleness":      validate_overlay_staleness(overlays),
        "recalculation_churn":    validate_recalculation_churn(targets, policy),
        "evidence_alignment":     validate_evidence_alignment(targets, evidence_records),
        "concentration_ceilings": validate_concentration_ceilings(targets, policy),
        "lineage_completeness":   validate_lineage_completeness(targets, snapshot),
    }
