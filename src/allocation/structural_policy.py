"""Load and validate the structural allocation policy from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import StructuralPolicy

_DEFAULT_POLICY_PATH = Path("config/allocation_policy.yaml")


def load_structural_policy(config_path: Path | str = _DEFAULT_POLICY_PATH) -> StructuralPolicy:
    """Parse config/allocation_policy.yaml into a StructuralPolicy dataclass."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Allocation policy config not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    errors = validate_policy_doc(doc)
    if errors:
        raise ValueError(f"Allocation policy validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    sp = doc["structural_policy"]
    rg = doc["recalculation_governance"]
    acg = doc.get("asset_class_governance", {})

    return StructuralPolicy(
        policy_id=doc.get("policy_id", "UNKNOWN"),
        policy_version=int(doc.get("version", 1)),
        effective_date=str(doc.get("effective_date", "")),
        cash_floor_pct=float(sp["cash_floor_pct"]),
        max_micro_cap_pct=float(sp["max_micro_cap_pct"]),
        max_digital_assets_pct=float(sp["max_digital_assets_pct"]),
        max_single_sector_pct=float(sp["max_single_sector_pct"]),
        max_mega_concentration_pct=float(sp["max_mega_concentration_pct"]),
        max_single_asset_class_pct=float(sp["max_single_asset_class_pct"]),
        min_international_pct=float(sp["min_international_pct"]),
        max_leverage_pct=float(sp["max_leverage_pct"]),
        max_recalculation_delta_pct=float(rg["max_single_recalculation_delta_pct"]),
        min_recalculation_interval_days=int(rg["min_recalculation_interval_days"]),
        min_meaningful_change_pct=float(rg["min_meaningful_change_pct"]),
        confidence_threshold=float(rg["confidence_threshold"]),
        replay_min_periods=int(rg["replay_min_periods"]),
        asset_class_governance={k: dict(v) for k, v in acg.items()},
        governance_notes=tuple(doc.get("governance_notes", [])),
    )


def validate_policy_doc(doc: dict[str, Any]) -> list[str]:
    """Validate the raw YAML policy document. Returns list of error strings (empty = valid)."""
    errors: list[str] = []

    if "structural_policy" not in doc:
        errors.append("Missing 'structural_policy' section")
    if "recalculation_governance" not in doc:
        errors.append("Missing 'recalculation_governance' section")

    sp = doc.get("structural_policy", {})
    required_sp = [
        "cash_floor_pct", "max_micro_cap_pct", "max_digital_assets_pct",
        "max_single_sector_pct", "max_mega_concentration_pct",
        "max_single_asset_class_pct", "min_international_pct", "max_leverage_pct",
    ]
    for field in required_sp:
        if field not in sp:
            errors.append(f"structural_policy missing field: {field}")

    rg = doc.get("recalculation_governance", {})
    required_rg = [
        "max_single_recalculation_delta_pct", "min_recalculation_interval_days",
        "min_meaningful_change_pct", "confidence_threshold", "replay_min_periods",
    ]
    for field in required_rg:
        if field not in rg:
            errors.append(f"recalculation_governance missing field: {field}")

    if not errors:
        cash_floor = float(sp.get("cash_floor_pct", 0))
        max_leverage = float(sp.get("max_leverage_pct", 0))
        if cash_floor < 0:
            errors.append("cash_floor_pct must be >= 0")
        if max_leverage < 0:
            errors.append("max_leverage_pct must be >= 0")
        max_delta = float(rg.get("max_single_recalculation_delta_pct", 0))
        if max_delta <= 0 or max_delta > 20:
            errors.append("max_single_recalculation_delta_pct must be between 0 and 20")

    return errors


def get_asset_class_ceiling(policy: StructuralPolicy, asset_class: str) -> float:
    """Return the governance max_pct for a given asset class, or max_single_asset_class_pct."""
    acg = policy.asset_class_governance.get(asset_class, {})
    return float(acg.get("max_pct", policy.max_single_asset_class_pct))


def get_asset_class_floor(policy: StructuralPolicy, asset_class: str) -> float:
    """Return the governance min_pct for a given asset class, or 0."""
    acg = policy.asset_class_governance.get(asset_class, {})
    return float(acg.get("min_pct", 0.0))
