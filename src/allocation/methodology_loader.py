"""Load allocation methodology rationale and extract seed targets from YAML."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .dimensions_loader import (
    AllocationDimensionNode,
    compute_pct_of_total,
    get_ancestry_chain,
)
from .models import (
    AllocationEvidence,
    AllocationMethodologyBasis,
    AllocationRecalculationSnapshot,
    StrategicAllocationTarget,
)
from .structural_policy import StructuralPolicy

_DEFAULT_METHODOLOGY_PATH = Path("config/allocation_methodology.yaml")


def load_methodology(
    config_path: Path | str = _DEFAULT_METHODOLOGY_PATH,
) -> dict[str, AllocationMethodologyBasis]:
    """Parse config/allocation_methodology.yaml. Returns dict keyed by node_key."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Allocation methodology config not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    methodology_id = doc.get("methodology_id", "v1")
    result: dict[str, AllocationMethodologyBasis] = {}

    for raw in doc.get("nodes", []):
        key = raw["key"]
        result[key] = AllocationMethodologyBasis(
            node_key=key,
            methodology_id=methodology_id,
            evidence_basis=tuple(str(e).strip() for e in raw.get("evidence_basis", [])),
            risk_factors=tuple(str(r).strip() for r in raw.get("risk_factors", [])),
            baseline_target_pct_of_parent=float(raw["baseline_target_pct_of_parent"]),
            confidence_level=str(raw.get("confidence_level", "MEDIUM")),
        )

    return result


def _confidence_to_score(level: str) -> float:
    return {"HIGH": 0.85, "MEDIUM": 0.65, "LOW": 0.45}.get(level.upper(), 0.5)


def _derive_dimension_fields(
    node: AllocationDimensionNode,
) -> tuple[str, str | None, str | None, str | None]:
    """Return (asset_class, geography, market_structure, mega_subtier) from node."""
    parts = node.key.split(".")
    asset_class = parts[0]

    geography: str | None = None
    market_structure: str | None = None
    mega_subtier: str | None = None

    if node.hierarchy_level >= 2 and node.allocation_category_type in ("EQUITY", "FIXED_INCOME"):
        if node.dimension_type == "GEOGRAPHY":
            geography = parts[1] if len(parts) > 1 else None
    if node.hierarchy_level >= 3 and node.dimension_type == "MARKET_CAP":
        geography = parts[1] if len(parts) > 1 else None
        market_structure = parts[2] if len(parts) > 2 else None
    if node.hierarchy_level == 4 and node.dimension_type == "MEGA_SUBTIER":
        geography = parts[1] if len(parts) > 1 else None
        market_structure = parts[2] if len(parts) > 2 else None
        mega_subtier = parts[3] if len(parts) > 3 else None

    return asset_class, geography, market_structure, mega_subtier


def extract_seed_targets(
    methodology: dict[str, AllocationMethodologyBasis],
    all_nodes: dict[str, AllocationDimensionNode],
    policy: StructuralPolicy,
    snapshot_date: str | None = None,
) -> tuple[AllocationRecalculationSnapshot, list[StrategicAllocationTarget], list[AllocationEvidence]]:
    """
    Build the initial AllocationRecalculationSnapshot and list of StrategicAllocationTargets
    seeded entirely from the methodology YAML.

    Returns: (snapshot, targets, evidence_records)
    """
    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    recalculation_id = f"SEED_{snapshot_date.replace('-', '')}_{uuid.uuid4().hex[:8].upper()}"

    # Build pct_of_parent map from methodology
    pct_of_parent_map: dict[str, float] = {}
    for key, basis in methodology.items():
        pct_of_parent_map[key] = basis.baseline_target_pct_of_parent

    # Validate sibling sums before committing
    sum_errors = _validate_sibling_sums(all_nodes, pct_of_parent_map)
    if sum_errors:
        raise ValueError(
            "Methodology seed target sibling sums are invalid:\n"
            + "\n".join(f"  - {e}" for e in sum_errors)
        )

    targets: list[StrategicAllocationTarget] = []
    evidence_records: list[AllocationEvidence] = []
    evidence_ids: list[str] = []

    for key, node in sorted(all_nodes.items(), key=lambda x: x[1].hierarchy_level):
        basis = methodology.get(key)
        pct_of_parent = pct_of_parent_map.get(key)
        if pct_of_parent is None:
            continue

        # Compute pct_of_total by multiplying pct_of_parent up the ancestry chain
        chain = get_ancestry_chain(key, all_nodes)
        pct_of_total = 1.0
        for ancestor in chain:
            p = pct_of_parent_map.get(ancestor.key)
            if p is None:
                pct_of_total = 0.0
                break
            pct_of_total *= p / 100.0
        pct_of_total = round(pct_of_total * 100.0, 4)

        confidence_level = basis.confidence_level if basis else "LOW"
        confidence_score = _confidence_to_score(confidence_level)

        # Build evidence record
        evidence_id = f"EV_{recalculation_id}_{key.replace('.', '_')}"
        evidence_summary = (
            basis.evidence_basis[0][:120] if basis and basis.evidence_basis else "Methodology baseline."
        )
        evidence = AllocationEvidence(
            evidence_id=evidence_id,
            evidence_date=snapshot_date,
            evidence_type="METHODOLOGY_BASELINE",
            node_key=key,
            asset_class=key.split(".")[0],
            metric_name="baseline_target_pct_of_parent",
            metric_value=pct_of_parent,
            benchmark_comparison=None,
            significance=confidence_level,
            replay_id=None,
            human_readable=f"{key}: {pct_of_parent:.1f}% of parent. {evidence_summary}",
        )
        evidence_records.append(evidence)
        evidence_ids.append(evidence_id)

        asset_class, geography, market_structure, mega_subtier = _derive_dimension_fields(node)

        target_id = f"TGT_{recalculation_id}_{key.replace('.', '_')}"
        target = StrategicAllocationTarget(
            target_id=target_id,
            snapshot_date=snapshot_date,
            recalculation_id=recalculation_id,
            node_key=key,
            node_label=node.label,
            parent_key=node.parent_key,
            asset_class=asset_class,
            geography=geography,
            market_structure=market_structure,
            mega_subtier=mega_subtier,
            hierarchy_depth=node.hierarchy_level,
            target_pct_of_parent=pct_of_parent,
            target_pct_of_total=pct_of_total,
            prior_target_pct_of_total=None,
            delta_pct=None,
            confidence_score=confidence_score,
            evidence_summary=f"Methodology seed ({confidence_level} confidence). {evidence_summary[:80]}",
            evidence_ids=(evidence_id,),
            methodology_basis_ref=key,
            policy_bounded=False,
        )
        targets.append(target)

    # Build snapshot
    snapshot = AllocationRecalculationSnapshot(
        recalculation_id=recalculation_id,
        recalculation_date=snapshot_date,
        prior_recalculation_id=None,
        triggered_by="MANUAL",
        policy_version=str(policy.policy_version),
        evidence_ids=tuple(evidence_ids),
        change_summary=(
            f"Initial seed from config/allocation_methodology.yaml (methodology_id={methodology.get(list(methodology.keys())[0]).methodology_id if methodology else 'unknown'}). "
            f"{len(targets)} nodes initialized.",
        ),
        unchanged_summary=f"0 nodes unchanged — this is the initial seed recalculation.",
        confidence_summary={t.node_key: t.confidence_score for t in targets},
        total_allocation_valid=True,
        notes="Seed recalculation from investment policy statement rationale.",
    )

    return snapshot, targets, evidence_records


def _validate_sibling_sums(
    all_nodes: dict[str, AllocationDimensionNode],
    pct_of_parent_map: dict[str, float],
    tolerance: float = 0.01,
) -> list[str]:
    """Check that each parent's children sum to 100.0 within tolerance."""
    errors: list[str] = []
    checked: set[str] = set()

    for key, node in all_nodes.items():
        if not node.children or key in checked:
            continue
        checked.add(key)
        sibling_sum = sum(pct_of_parent_map.get(child_key, 0.0) for child_key in node.children)
        if abs(sibling_sum - 100.0) > tolerance:
            errors.append(
                f"Parent '{key}' children sum to {sibling_sum:.4f}% (expected 100.0 ±{tolerance}). "
                f"Children: {list(node.children)}"
            )

    return errors
