"""Deterministic validation contracts for benchmark intelligence artifacts."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml

from src.models.canonical_models import BenchmarkSnapshot
from src.models.run_metadata import RunMetadata

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9_.-]+$")
_ALLOWED_RUN_STATUSES = {"STARTED", "COMPLETED", "FAILED", "PARTIAL"}


class BenchmarkValidationError(ValueError):
    """Raised when benchmark artifacts fail deterministic validation."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("Benchmark validation failed: " + "; ".join(errors))


def load_registry_file(file_path: str | Path) -> Dict[str, Any]:
    """Load a benchmark registry YAML document as a dictionary."""

    payload = yaml.safe_load(Path(file_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BenchmarkValidationError(["Registry root must be a mapping object."])
    return payload


def validate_benchmark_registry(registry: Dict[str, Any]) -> List[str]:
    """Validate benchmark registry contracts and return explicit error messages."""

    errors: List[str] = []
    required_top_keys = {
        "dimensions",
        "required_market_cap_by_geography",
        "benchmark_definitions",
        "benchmark_assignments",
    }
    missing_top = sorted(required_top_keys.difference(registry.keys()))
    if missing_top:
        errors.append(f"Missing top-level keys: {', '.join(missing_top)}")
        return errors

    dimensions = registry.get("dimensions")
    if not isinstance(dimensions, dict):
        errors.append("Malformed registry entry: dimensions must be a mapping.")
        return errors

    geographies = dimensions.get("geography")
    market_cap_buckets = dimensions.get("market_cap_bucket")
    if not isinstance(geographies, list) or not geographies:
        errors.append("Malformed registry entry: dimensions.geography must be a non-empty list.")
    if not isinstance(market_cap_buckets, list) or not market_cap_buckets:
        errors.append("Malformed registry entry: dimensions.market_cap_bucket must be a non-empty list.")
    if errors:
        return errors

    geographies_set = set(geographies)
    core_buckets_set = set(market_cap_buckets)

    required_map = registry.get("required_market_cap_by_geography")
    if not isinstance(required_map, dict):
        errors.append("Malformed registry entry: required_market_cap_by_geography must be a mapping.")
        return errors

    optional_map = registry.get("optional_categories_by_geography", {})
    if optional_map is None:
        optional_map = {}
    if not isinstance(optional_map, dict):
        errors.append("Malformed registry entry: optional_categories_by_geography must be a mapping.")
        return errors

    definitions = registry.get("benchmark_definitions")
    assignments = registry.get("benchmark_assignments")
    if not isinstance(definitions, list):
        errors.append("Malformed registry entry: benchmark_definitions must be a list.")
        return errors
    if not isinstance(assignments, list):
        errors.append("Malformed registry entry: benchmark_assignments must be a list.")
        return errors

    required_definition_fields = {
        "benchmark_symbol",
        "benchmark_name",
        "geography",
        "market_cap_bucket",
        "benchmark_type",
        "provider",
        "active_status",
        "created_at",
    }
    symbol_to_definition: Dict[str, Dict[str, Any]] = {}
    for index, entry in enumerate(definitions):
        location = f"benchmark_definitions[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"Malformed registry entry at {location}: expected mapping object.")
            continue

        missing_fields = sorted(required_definition_fields.difference(entry.keys()))
        if missing_fields:
            errors.append(
                f"Malformed registry entry at {location}: missing fields {', '.join(missing_fields)}"
            )
            continue

        symbol = entry.get("benchmark_symbol")
        if not isinstance(symbol, str) or not _SYMBOL_PATTERN.match(symbol):
            errors.append(f"Invalid benchmark symbol at {location}: {symbol!r}")
            continue

        if symbol in symbol_to_definition:
            errors.append(f"Duplicate benchmark detection: symbol {symbol} appears multiple times.")
            continue

        geography = entry.get("geography")
        if geography not in geographies_set:
            errors.append(f"Malformed registry entry at {location}: unknown geography {geography!r}")

        allowed_optional = set(optional_map.get(geography, []))
        bucket = entry.get("market_cap_bucket")
        if bucket not in core_buckets_set and bucket not in allowed_optional:
            errors.append(
                f"Malformed registry entry at {location}: market_cap_bucket {bucket!r} is not allowed"
            )

        if not isinstance(entry.get("active_status"), bool):
            errors.append(f"Malformed registry entry at {location}: active_status must be boolean.")

        created_at = entry.get("created_at")
        if not isinstance(created_at, str):
            errors.append(f"Malformed registry entry at {location}: created_at must be ISO timestamp string.")
        else:
            try:
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    f"Malformed registry entry at {location}: created_at is not valid ISO-8601 timestamp."
                )

        symbol_to_definition[symbol] = entry

    required_assignment_fields = {
        "geography",
        "market_cap_bucket",
        "benchmark_symbol",
        "assignment_status",
    }
    seen_active_categories: Set[Tuple[str, str]] = set()
    active_assignments_by_geo: Dict[str, Set[str]] = {}

    for index, assignment in enumerate(assignments):
        location = f"benchmark_assignments[{index}]"
        if not isinstance(assignment, dict):
            errors.append(f"Malformed registry entry at {location}: expected mapping object.")
            continue

        missing_fields = sorted(required_assignment_fields.difference(assignment.keys()))
        if missing_fields:
            errors.append(
                f"Malformed registry entry at {location}: missing fields {', '.join(missing_fields)}"
            )
            continue

        geography = assignment.get("geography")
        bucket = assignment.get("market_cap_bucket")
        symbol = assignment.get("benchmark_symbol")
        status = assignment.get("assignment_status")

        if geography not in geographies_set:
            errors.append(f"Missing geography mappings: unknown assignment geography {geography!r}")

        if not isinstance(symbol, str) or not _SYMBOL_PATTERN.match(symbol):
            errors.append(f"Invalid benchmark symbols: assignment uses invalid symbol {symbol!r}")

        if symbol not in symbol_to_definition:
            errors.append(
                f"Malformed registry entry at {location}: benchmark_symbol {symbol!r} has no definition"
            )

        if status == "ACTIVE":
            category_key = (str(geography), str(bucket))
            if category_key in seen_active_categories:
                errors.append(
                    f"Duplicate category assignment: ACTIVE assignment already exists for {geography}/{bucket}"
                )
            seen_active_categories.add(category_key)
            active_assignments_by_geo.setdefault(str(geography), set()).add(str(bucket))

            referenced_definition = symbol_to_definition.get(str(symbol))
            if referenced_definition and not referenced_definition.get("active_status", False):
                errors.append(
                    f"Inactive benchmark conflicts: ACTIVE assignment points to inactive symbol {symbol}"
                )

    for geography in geographies:
        if geography not in active_assignments_by_geo:
            errors.append(f"Missing geography mappings: no ACTIVE assignments found for geography {geography}")

        required_buckets = required_map.get(geography)
        if not isinstance(required_buckets, list):
            errors.append(
                f"Missing market-cap mappings: required_market_cap_by_geography must define list for {geography}"
            )
            continue

        missing_buckets = sorted(set(required_buckets).difference(active_assignments_by_geo.get(geography, set())))
        if missing_buckets:
            errors.append(
                f"Missing market-cap mappings: geography {geography} missing ACTIVE assignments for {', '.join(missing_buckets)}"
            )

    return errors


def assert_valid_benchmark_registry(registry: Dict[str, Any]) -> None:
    """Raise a deterministic exception if registry validation fails."""

    errors = validate_benchmark_registry(registry)
    if errors:
        raise BenchmarkValidationError(errors)


def validate_run_metadata(record: RunMetadata) -> List[str]:
    """Validate run metadata contract for deterministic snapshot lineage."""

    errors: List[str] = []
    if not record.run_id:
        errors.append("Run metadata error: run_id must be non-empty.")
    if not record.source_provider:
        errors.append("Run metadata error: source_provider must be non-empty.")
    if not record.source_file:
        errors.append("Run metadata error: source_file must be non-empty.")
    if record.processing_status not in _ALLOWED_RUN_STATUSES:
        errors.append(
            "Run metadata error: processing_status must be one of STARTED, COMPLETED, FAILED, PARTIAL."
        )
    return errors


def validate_snapshot_lineage(snapshot: BenchmarkSnapshot, run_metadata: RunMetadata) -> List[str]:
    """Validate that snapshot references deterministic run lineage metadata."""

    errors: List[str] = []
    errors.extend(validate_run_metadata(run_metadata))

    if snapshot.run_id != run_metadata.run_id:
        errors.append("Snapshot lineage error: snapshot.run_id must match run_metadata.run_id.")
    if snapshot.snapshot_date != run_metadata.snapshot_date:
        errors.append("Snapshot lineage error: snapshot_date must match run metadata snapshot_date.")
    if snapshot.source_provider != run_metadata.source_provider:
        errors.append("Snapshot lineage error: source_provider must match run metadata source_provider.")
    if run_metadata.processing_status != "COMPLETED":
        errors.append("Snapshot lineage error: run metadata must be COMPLETED before snapshot publication.")
    return errors


def assert_valid_snapshot_lineage(snapshot: BenchmarkSnapshot, run_metadata: RunMetadata) -> None:
    """Raise a deterministic exception if snapshot lineage validation fails."""

    errors = validate_snapshot_lineage(snapshot, run_metadata)
    if errors:
        raise BenchmarkValidationError(errors)
