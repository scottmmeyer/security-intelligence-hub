"""Benchmark assignment engine: computes benchmark_id, benchmark_confidence,
classification_method, and sector_benchmark_id for analytical universe rows.

Phase 1: Primary cap-tier benchmark assignment only.
Phase 2 (future): Sector benchmark overlay (SOXX, VNQ, XBI, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.classification.geography_resolver import (
    GEOGRAPHY_US,
    GEOGRAPHY_INTERNATIONAL,
    GEOGRAPHY_UNKNOWN,
    GeographyResolution,
)
from src.classification.security_type_policy import (
    CANONICAL_EQUITY,
    CANONICAL_ETF,
    CANONICAL_MUTUAL_FUND,
    CANONICAL_BOND,
    CANONICAL_DIGITAL_ASSET,
    SecurityTypeInfo,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Benchmark confidence levels (ordered HIGH → UNRESOLVABLE)
CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_UNRESOLVABLE = "UNRESOLVABLE"

# Classification method codes
METHOD_EQUITY_CAP_TIER = "EQUITY_CAP_TIER"
METHOD_ADR_DOMICILE = "ADR_DOMICILE"
METHOD_FUND_REGISTRY = "FUND_REGISTRY"
METHOD_INTERNATIONAL_CAP_TIER = "INTERNATIONAL_CAP_TIER"
METHOD_UNKNOWN = "UNKNOWN"
METHOD_NOT_APPLICABLE = "NOT_APPLICABLE"

# Valid market cap buckets for benchmark lookup
VALID_CAP_BUCKETS = {"MEGA", "LARGE", "MID", "SMALL", "MICRO"}


@dataclass(frozen=True)
class BenchmarkAssignment:
    """Result of benchmark assignment for a single universe row."""

    primary_benchmark_id: str
    """Assigned primary benchmark ID (or UNMAPPED if resolution failed)."""

    sector_benchmark_id: str
    """Sector-specific benchmark ID. Empty in Phase 1; populated in Phase 2."""

    benchmark_confidence: str
    """HIGH | MEDIUM | LOW | UNRESOLVABLE."""

    classification_method: str
    """How the benchmark was assigned."""

    geography_resolved: str
    """The geography value used for benchmark lookup."""


def assign_benchmarks(
    *,
    symbol: str,
    security_type_info: SecurityTypeInfo,
    geography_resolution: GeographyResolution,
    market_cap_bucket: str,
    benchmark_registry: Dict,
    vehicle_registry: Dict,
) -> BenchmarkAssignment:
    """Assign primary benchmark and classification metadata for a universe row.

    For ETFs, mutual funds, bonds, and digital assets: returns NOT_APPLICABLE
    with the appropriate non-scoring confidence.

    For equities: resolves benchmark from (geography, market_cap_bucket, ALL)
    using the benchmark_category_registry.

    Args:
        symbol:                Ticker (informational).
        security_type_info:    Resolved canonical class + eligibility.
        geography_resolution:  Resolved geography with method and confidence.
        market_cap_bucket:     Cap tier (MEGA | LARGE | MID | SMALL | MICRO).
        benchmark_registry:    Loaded benchmark_category_registry data.
        vehicle_registry:      Loaded investable_vehicle_registry data.

    Returns:
        BenchmarkAssignment with primary_benchmark_id, confidence, method.
    """
    canonical = security_type_info.canonical_class

    # Non-equity types: not applicable for cap-tier equity benchmarks
    if canonical in (CANONICAL_ETF, CANONICAL_MUTUAL_FUND, CANONICAL_BOND, CANONICAL_DIGITAL_ASSET):
        return BenchmarkAssignment(
            primary_benchmark_id="NOT_APPLICABLE",
            sector_benchmark_id="",
            benchmark_confidence=CONFIDENCE_HIGH,  # High because the N/A is certain
            classification_method=METHOD_NOT_APPLICABLE,
            geography_resolved=geography_resolution.geography,
        )

    # UNKNOWN canonical type: use the geography/cap-tier lookup but flag LOW confidence
    geography = geography_resolution.geography
    if geography == GEOGRAPHY_UNKNOWN:
        return BenchmarkAssignment(
            primary_benchmark_id="UNMAPPED",
            sector_benchmark_id="",
            benchmark_confidence=CONFIDENCE_UNRESOLVABLE,
            classification_method=METHOD_UNKNOWN,
            geography_resolved=GEOGRAPHY_UNKNOWN,
        )

    cap_bucket = str(market_cap_bucket or "").strip().upper()
    if cap_bucket not in VALID_CAP_BUCKETS:
        return BenchmarkAssignment(
            primary_benchmark_id="UNMAPPED",
            sector_benchmark_id="",
            benchmark_confidence=CONFIDENCE_LOW,
            classification_method=METHOD_UNKNOWN,
            geography_resolved=geography,
        )

    # Equity: look up benchmark from registry
    try:
        from src.replay.registry_loader import resolve_category_mapping  # lazy import
        benchmark, _vehicle = resolve_category_mapping(
            geography=geography,
            market_cap_bucket=cap_bucket,
            industry_scope="ALL",
            benchmark_registry=benchmark_registry,
            vehicle_registry=vehicle_registry,
        )
        benchmark_id = benchmark.benchmark_id
    except (ValueError, Exception):
        return BenchmarkAssignment(
            primary_benchmark_id="UNMAPPED",
            sector_benchmark_id="",
            benchmark_confidence=CONFIDENCE_LOW,
            classification_method=METHOD_UNKNOWN,
            geography_resolved=geography,
        )

    # Determine classification method and confidence based on resolution quality
    geo_method = geography_resolution.resolution_method
    geo_confidence = geography_resolution.confidence

    if canonical == CANONICAL_EQUITY:
        if geography == GEOGRAPHY_US:
            if geo_confidence == CONFIDENCE_HIGH:
                method = METHOD_EQUITY_CAP_TIER
                confidence = CONFIDENCE_HIGH
            else:
                method = METHOD_EQUITY_CAP_TIER
                confidence = CONFIDENCE_MEDIUM
        else:  # INTERNATIONAL
            if geo_method == "ADR_DOMICILE":
                method = METHOD_ADR_DOMICILE
                confidence = geo_confidence
            elif geo_method in ("COUNTRY_LOOKUP", "MANUAL_OVERRIDE"):
                method = METHOD_INTERNATIONAL_CAP_TIER
                confidence = CONFIDENCE_HIGH
            else:
                method = METHOD_INTERNATIONAL_CAP_TIER
                confidence = CONFIDENCE_LOW
    else:
        # CANONICAL_UNKNOWN treated as equity with LOW confidence
        method = METHOD_UNKNOWN
        confidence = CONFIDENCE_LOW

    return BenchmarkAssignment(
        primary_benchmark_id=benchmark_id,
        sector_benchmark_id="",
        benchmark_confidence=confidence,
        classification_method=method,
        geography_resolved=geography,
    )
