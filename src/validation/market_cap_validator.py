"""Deterministic validation for market-cap bucket configuration."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

REQUIRED_BUCKETS = ("MEGA", "LARGE", "MID", "SMALL", "MICRO")


class MarketCapValidationError(ValueError):
    """Raised when market-cap configuration fails deterministic validation."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("Market-cap validation failed: " + "; ".join(errors))


def _extract_bounds(bucket_name: str, payload: Dict[str, Any], errors: List[str]) -> Tuple[int | None, int | None]:
    min_value = payload.get("min_usd_inclusive")
    max_value = payload.get("max_usd_exclusive")

    if not isinstance(min_value, int):
        errors.append(f"Malformed bucket definition {bucket_name}: min_usd_inclusive must be integer.")
        min_value = None

    if max_value is not None and not isinstance(max_value, int):
        errors.append(f"Malformed bucket definition {bucket_name}: max_usd_exclusive must be integer or null.")
        max_value = None

    if isinstance(min_value, int) and min_value < 0:
        errors.append(f"Invalid boundaries for {bucket_name}: min_usd_inclusive cannot be negative.")

    if isinstance(min_value, int) and isinstance(max_value, int) and min_value >= max_value:
        errors.append(
            f"Invalid boundaries for {bucket_name}: min_usd_inclusive must be less than max_usd_exclusive."
        )

    return min_value, max_value


def validate_market_cap_config(config: Dict[str, Any]) -> List[str]:
    """Validate market-cap bucket configuration and return explicit errors."""

    errors: List[str] = []
    if not isinstance(config, dict):
        return ["Malformed bucket definitions: config root must be a mapping."]

    provider = config.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        errors.append("Invalid provider metadata: provider must be a non-empty string.")

    effective_date = config.get("effective_date")
    if not isinstance(effective_date, str) or not effective_date.strip():
        errors.append("Invalid provider metadata: effective_date must be a non-empty string placeholder or date.")

    if config.get("currency") != "USD":
        errors.append("Invalid provider metadata: currency must be USD for canonical market-cap normalization.")

    buckets = config.get("buckets")
    if not isinstance(buckets, dict):
        errors.append("Malformed bucket definitions: buckets must be a mapping.")
        return errors

    missing = [bucket for bucket in REQUIRED_BUCKETS if bucket not in buckets]
    if missing:
        errors.append(f"Missing buckets: {', '.join(missing)}")

    parsed_ranges: List[Tuple[str, int, int | None]] = []
    for bucket_name in REQUIRED_BUCKETS:
        payload = buckets.get(bucket_name)
        if payload is None:
            continue
        if not isinstance(payload, dict):
            errors.append(f"Malformed bucket definitions: {bucket_name} must be a mapping.")
            continue

        min_value, max_value = _extract_bounds(bucket_name, payload, errors)
        if min_value is None:
            continue
        parsed_ranges.append((bucket_name, min_value, max_value))

    # Detect overlapping ranges deterministically.
    # Convention: [min_inclusive, max_exclusive); null max means open-ended upper bound.
    for i, (name_a, min_a, max_a) in enumerate(parsed_ranges):
        for name_b, min_b, max_b in parsed_ranges[i + 1 :]:
            upper_a = float("inf") if max_a is None else float(max_a)
            upper_b = float("inf") if max_b is None else float(max_b)
            overlaps = (min_a < upper_b) and (min_b < upper_a)
            if overlaps:
                # Adjacent ranges are not overlap in exclusive upper-bound scheme.
                if not (max_a == min_b or max_b == min_a):
                    errors.append(f"Overlapping ranges detected: {name_a} conflicts with {name_b}.")

    return errors


def assert_valid_market_cap_config(config: Dict[str, Any]) -> None:
    """Raise deterministic validation exception on any config errors."""

    errors = validate_market_cap_config(config)
    if errors:
        raise MarketCapValidationError(errors)
