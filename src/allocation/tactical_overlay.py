"""Apply tactical momentum overlays to strategic targets → AllocationRecommendations."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from .models import AllocationRecommendation, StrategicAllocationTarget, TacticalMomentumOverlay
from .structural_policy import StructuralPolicy, get_asset_class_ceiling

_DEFAULT_OVERLAY_PATH = Path("data/current/tactical_overlays.csv")

OVERLAY_HEADERS = [
    "overlay_id", "effective_date", "expiry_date", "dimension_type",
    "dimension_value", "overlay_pct", "max_overlay_pct", "persistence_score",
    "momentum_signal", "replay_support_ids", "notes", "status",
]


def load_active_overlays(csv_path: Path | str = _DEFAULT_OVERLAY_PATH) -> list[TacticalMomentumOverlay]:
    """Load ACTIVE overlays from CSV. Returns empty list if file doesn't exist."""
    path = Path(csv_path)
    if not path.exists():
        return []

    overlays: list[TacticalMomentumOverlay] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("status", "").strip().upper() != "ACTIVE":
                continue
            overlays.append(
                TacticalMomentumOverlay(
                    overlay_id=row["overlay_id"],
                    effective_date=row["effective_date"],
                    expiry_date=row.get("expiry_date") or None,
                    dimension_type=row["dimension_type"],
                    dimension_value=row["dimension_value"],
                    overlay_pct=float(row["overlay_pct"]),
                    max_overlay_pct=float(row["max_overlay_pct"]),
                    persistence_score=float(row.get("persistence_score", 0.0)),
                    momentum_signal=row.get("momentum_signal", "WEAK"),
                    replay_support_ids=tuple(
                        s.strip() for s in row.get("replay_support_ids", "").split("|") if s.strip()
                    ),
                    notes=row.get("notes", ""),
                    status="ACTIVE",
                )
            )
    return overlays


def expire_stale_overlays(
    overlays: list[TacticalMomentumOverlay],
    as_of_date: str | None = None,
) -> list[TacticalMomentumOverlay]:
    """Return updated list with past-expiry overlays marked EXPIRED."""
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    result: list[TacticalMomentumOverlay] = []
    for ov in overlays:
        if ov.expiry_date and ov.expiry_date < as_of_date and ov.status == "ACTIVE":
            # Re-create with EXPIRED status (frozen dataclass workaround)
            import dataclasses
            result.append(dataclasses.replace(ov, status="EXPIRED"))
        else:
            result.append(ov)
    return result


def apply_overlay_to_node(
    node_key: str,
    all_node_labels: dict[str, str],
    overlays: list[TacticalMomentumOverlay],
) -> float:
    """
    Compute net tactical overlay pct for a given node key.

    Overlays apply to equity nodes only and are matched by dimension_value against
    the node's label or key components. Non-equity nodes always return 0.0.
    """
    if not node_key.startswith("EQUITIES."):
        return 0.0

    net_overlay = 0.0
    for ov in overlays:
        if ov.status != "ACTIVE":
            continue
        # Match: dimension_value against node key parts or label
        # e.g. TECHNOLOGY sector overlay applies to nodes matching TECHNOLOGY in industry context
        # For market-cap overlays: MEGA matches EQUITIES.*.MEGA nodes
        # For geography: US matches EQUITIES.US.* nodes
        key_parts = node_key.split(".")
        dv = ov.dimension_value.upper()
        matched = False
        if ov.dimension_type in ("MARKET_CAP",) and len(key_parts) >= 3:
            matched = key_parts[2] == dv
        elif ov.dimension_type in ("MEGA_SUBTIER",) and len(key_parts) == 4:
            matched = key_parts[3] == dv
        elif ov.dimension_type in ("GEOGRAPHY",) and len(key_parts) >= 2:
            matched = key_parts[1] == dv
        # Sector overlays are cross-cutting; they don't map to hierarchy nodes directly.
        # They are displayed in the UI but don't alter specific node targets.
        # (Portfolio consumers apply sector tilts within their equity positions.)
        if matched:
            net_overlay += ov.overlay_pct

    return net_overlay


def compute_effective_allocations(
    targets: list[StrategicAllocationTarget],
    overlays: list[TacticalMomentumOverlay],
    policy: StructuralPolicy,
    snapshot_date: str | None = None,
) -> list[AllocationRecommendation]:
    """
    Produce AllocationRecommendation for each target by applying tactical overlays
    and enforcing policy ceilings.
    """
    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    active_overlays = [ov for ov in overlays if ov.status == "ACTIVE"]
    all_node_labels = {t.node_key: t.node_label for t in targets}

    import uuid
    batch_id = uuid.uuid4().hex[:8].upper()
    recommendations: list[AllocationRecommendation] = []

    for target in targets:
        tactical_pct = apply_overlay_to_node(target.node_key, all_node_labels, active_overlays)
        raw_effective = target.target_pct_of_total + tactical_pct

        # Policy ceiling check
        asset_class_ceiling = get_asset_class_ceiling(policy, target.asset_class)
        is_capped = False
        policy_ceiling: float | None = None

        if raw_effective > asset_class_ceiling and target.hierarchy_depth == 1:
            raw_effective = asset_class_ceiling
            is_capped = True
            policy_ceiling = asset_class_ceiling

        # Additional per-dimension ceilings
        if target.mega_subtier is not None:
            # MEGA subtree total ceiling
            pass  # enforced at aggregate level via validators

        effective_pct = round(max(0.0, raw_effective), 4)

        rec_id = f"REC_{batch_id}_{target.node_key.replace('.', '_')}"
        recommendations.append(
            AllocationRecommendation(
                recommendation_id=rec_id,
                snapshot_date=snapshot_date,
                policy_id=policy.policy_id,
                recalculation_id=target.recalculation_id,
                node_key=target.node_key,
                asset_class=target.asset_class,
                strategic_target_pct=target.target_pct_of_total,
                tactical_overlay_pct=tactical_pct,
                effective_target_pct=effective_pct,
                is_policy_capped=is_capped,
                policy_ceiling=policy_ceiling,
                drift_from_prior=target.delta_pct,
            )
        )

    return recommendations
