"""Registry loading and category resolution for WP-04 replay contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from src.models.analytical_models import BenchmarkDefinition, InvestableVehicle


def _load_yaml_mapping(path: str | Path) -> Dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Registry root must be a mapping: {path}")
    return payload


def load_benchmark_category_registry(
    path: str | Path = "config/benchmark_category_registry.yaml",
) -> Dict[str, Any]:
    """Load benchmark category registry config."""

    return _load_yaml_mapping(path)


def load_investable_vehicle_registry(
    path: str | Path = "config/investable_vehicle_registry.yaml",
) -> Dict[str, Any]:
    """Load investable vehicle registry config."""

    return _load_yaml_mapping(path)


def _find_assignment(
    assignments: list[dict[str, Any]],
    *,
    geography: str,
    market_cap_bucket: str,
    industry_scope: str,
    id_key: str,
) -> str:
    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        if (
            str(assignment.get("geography", "")) == geography
            and str(assignment.get("market_cap_bucket", "")) == market_cap_bucket
            and str(assignment.get("industry_scope", "ALL")) == industry_scope
            and str(assignment.get("assignment_status", "")).upper() == "ACTIVE"
        ):
            return str(assignment.get(id_key, ""))
    raise ValueError(
        "No ACTIVE category mapping found for "
        f"geography={geography}, market_cap_bucket={market_cap_bucket}, industry_scope={industry_scope}."
    )


def resolve_category_mapping(
    *,
    geography: str,
    market_cap_bucket: str,
    industry_scope: str,
    benchmark_registry: Dict[str, Any],
    vehicle_registry: Dict[str, Any],
) -> Tuple[BenchmarkDefinition, InvestableVehicle]:
    """Resolve deterministic benchmark and investable vehicle for category filters."""

    benchmark_id = _find_assignment(
        benchmark_registry.get("benchmark_assignments", []),
        geography=geography,
        market_cap_bucket=market_cap_bucket,
        industry_scope=industry_scope,
        id_key="benchmark_id",
    )
    vehicle_id = _find_assignment(
        vehicle_registry.get("vehicle_assignments", []),
        geography=geography,
        market_cap_bucket=market_cap_bucket,
        industry_scope=industry_scope,
        id_key="vehicle_id",
    )

    benchmark_lookup = {
        str(item.get("benchmark_id", "")): item
        for item in benchmark_registry.get("benchmark_definitions", [])
        if isinstance(item, dict)
    }
    vehicle_lookup = {
        str(item.get("vehicle_id", "")): item
        for item in vehicle_registry.get("investable_vehicles", [])
        if isinstance(item, dict)
    }

    benchmark_payload = benchmark_lookup.get(benchmark_id)
    vehicle_payload = vehicle_lookup.get(vehicle_id)
    if benchmark_payload is None:
        raise ValueError(f"Benchmark definition not found for benchmark_id={benchmark_id}")
    if vehicle_payload is None:
        raise ValueError(f"Investable vehicle not found for vehicle_id={vehicle_id}")

    benchmark = BenchmarkDefinition(
        benchmark_id=str(benchmark_payload.get("benchmark_id", "")),
        name=str(benchmark_payload.get("name", "")),
        category=str(benchmark_payload.get("category", "")),
        geography=str(benchmark_payload.get("geography", "")),
        market_cap_bucket=str(benchmark_payload.get("market_cap_bucket", "")),
        industry_scope=str(benchmark_payload.get("industry_scope", "")),
        symbol_or_index=str(benchmark_payload.get("symbol_or_index", "")),
        benchmark_type=str(benchmark_payload.get("benchmark_type", "")),
    )

    vehicle = InvestableVehicle(
        vehicle_id=str(vehicle_payload.get("vehicle_id", "")),
        symbol=str(vehicle_payload.get("symbol", "")),
        name=str(vehicle_payload.get("name", "")),
        vehicle_type=str(vehicle_payload.get("vehicle_type", "")),
        tracks_benchmark_id=str(vehicle_payload.get("tracks_benchmark_id", "")),
        geography=str(vehicle_payload.get("geography", "")),

        market_cap_bucket=str(vehicle_payload.get("market_cap_bucket", "")),
        industry_scope=str(vehicle_payload.get("industry_scope", "")),
    )

    return benchmark, vehicle


def derive_benchmark_symbols_from_registry(registry: Dict[str, Any]) -> frozenset:
    """Derive the set of all active benchmark symbols from registry definitions.

    This is the Phase D single-source mechanism: providers load allowed symbols
    from the YAML registry rather than hardcoded frozensets.
    """
    return frozenset(
        str(item.get("symbol_or_index", "")).upper()
        for item in registry.get("benchmark_definitions", [])
        if isinstance(item, dict) and str(item.get("symbol_or_index", "")).strip()
    )


def derive_vehicle_symbols_from_registry(registry: Dict[str, Any]) -> frozenset:
    """Derive the set of all active investable vehicle symbols from registry definitions.

    This is the Phase D single-source mechanism: providers load allowed symbols
    from the YAML registry rather than hardcoded frozensets.
    """
    return frozenset(
        str(item.get("symbol", "")).upper()
        for item in registry.get("investable_vehicles", [])
        if isinstance(item, dict) and str(item.get("symbol", "")).strip()
    )
