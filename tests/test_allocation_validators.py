from __future__ import annotations

from types import SimpleNamespace

from src.allocation.validators import (
    validate_concentration_ceilings,
    validate_policy_bounds,
)


def _target(node_key: str, pct_total: float, *, depth: int = 3, asset_class: str = "EQUITIES") -> SimpleNamespace:
    return SimpleNamespace(
        node_key=node_key,
        target_pct_of_total=pct_total,
        hierarchy_depth=depth,
        asset_class=asset_class,
    )


def _policy(max_micro: float = 5.0) -> SimpleNamespace:
    return SimpleNamespace(
        max_micro_cap_pct=max_micro,
        max_mega_concentration_pct=50.0,
        min_international_pct=10.0,
        max_single_asset_class_pct=80.0,
        cash_floor_pct=2.0,
        max_digital_assets_pct=8.0,
        asset_class_governance={
            "EQUITIES": {"max_pct": 80.0},
            "FIXED_INCOME": {"max_pct": 40.0},
            "DIGITAL": {"max_pct": 8.0},
            "COMMODITIES": {"max_pct": 20.0},
            "CASH": {"max_pct": 20.0},
        },
    )


def test_policy_bounds_does_not_apply_combined_micro_cap_check() -> None:
    targets = [
        _target("EQUITIES.US.MICRO", 6.0),
        _target("EQUITIES.INTERNATIONAL.MICRO", 0.5),
    ]

    errors = validate_policy_bounds(targets, _policy(max_micro=5.0))

    assert all("micro" not in e.lower() for e in errors)


def test_concentration_ceilings_applies_combined_micro_cap_check() -> None:
    targets = [
        _target("EQUITIES.US.MICRO", 6.0),
        _target("EQUITIES.INTERNATIONAL.MICRO", 0.5),
    ]

    errors = validate_concentration_ceilings(targets, _policy(max_micro=5.0))

    assert any("Combined MICRO cap exposure" in e for e in errors)


def test_concentration_ceilings_passes_when_combined_micro_within_limit() -> None:
    targets = [
        _target("EQUITIES.US.MICRO", 4.0),
        _target("EQUITIES.INTERNATIONAL.MICRO", 0.5),
    ]

    errors = validate_concentration_ceilings(targets, _policy(max_micro=5.0))

    assert not any("Combined MICRO cap exposure" in e for e in errors)
