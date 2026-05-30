"""WP-04 analytical universe and replay contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, Sequence


class PerformanceSeriesType(str, Enum):
    """Canonical series types for outcome visualization lines."""

    BENCHMARK = "BENCHMARK"
    INVESTABLE_VEHICLE = "INVESTABLE_VEHICLE"
    FULL_UNIVERSE = "FULL_UNIVERSE"
    TOP_N_STRATEGY = "TOP_N_STRATEGY"


class ReplayMode(str, Enum):
    """Temporal classification of a replay window. Phase F — replay temporal semantics.

    HISTORICAL_VALIDATION  — both start and end are strictly in the past; all
                             market data must be historically available.
    CURRENT_RECOMMENDATION — end date is today; captures current market level.
    FORWARD_SIMULATION     — end date is in the future; must be explicitly labelled
                             as hypothetical / simulation output.
    """

    HISTORICAL_VALIDATION = "HISTORICAL_VALIDATION"
    CURRENT_RECOMMENDATION = "CURRENT_RECOMMENDATION"
    FORWARD_SIMULATION = "FORWARD_SIMULATION"


@dataclass(frozen=True)
class AnalyticalUniverseRow:
    """Point-in-time analytical universe row for replay and visualization."""

    security_id: str
    symbol: str
    security_type: str
    snapshot_date: str
    run_id: str
    market_cap_bucket: str
    geography: str
    country: str
    industry: str
    sector: str
    composite_score: float
    ess_score_text: str
    zacks_rating: str
    yahoo_score: str
    danelfin_score: str
    benchmark_id: str
    investable_vehicle_id: str
    price_at_snapshot: str
    provider_lineage: str
    # Analytical market-structure fields — computed at snapshot time, then frozen.
    analytical_market_cap_subtier: str = ""
    classification_policy_id: str = ""
    classification_snapshot_date: str = ""
    # Eligibility flags — set by security type policy at universe build time.
    replay_eligible: bool = True
    scoring_eligible: bool = True
    allocation_eligible: bool = True
    # Benchmark integrity fields — set by benchmark assignment engine.
    benchmark_confidence: str = ""
    """Confidence in primary_benchmark assignment: HIGH | MEDIUM | LOW | UNRESOLVABLE."""
    sector_benchmark_id: str = ""
    """Sector-specific benchmark overlay (Phase 2). Empty in Phase 1."""
    classification_method: str = ""
    """How benchmark was assigned: EQUITY_CAP_TIER | ADR_DOMICILE | FUND_REGISTRY | etc."""
    # ---------------------------------------------------------------------------
    # Factor research and governance fields — Phase 2+: composite versioning.
    # These are additive and NEVER overwrite composite_score (v1 production).
    # ---------------------------------------------------------------------------
    yahoo_abr_normalized: str = ""
    """Normalized Yahoo ABR score: 6 - abr, clipped to [1.0, 5.0]. Empty if no ABR data."""
    composite_v2_yahoo: str = ""
    """Experimental composite score v2: includes Yahoo ABR at ~10% weight. Empty until generate_v2_scores runs."""
    composite_version: str = "v1"
    """Version tag for the production composite_score formula. Immutable per row once written."""
    score_generation_timestamp: str = ""
    """ISO 8601 UTC timestamp when composite scores were last computed for this row."""


@dataclass(frozen=True)
class ConcentrationScaffold:
    """Scaffold for future portfolio concentration analytics.

    All fields default to None — computation logic is NOT yet implemented.
    This dataclass exists purely to reserve the contract shape.
    """

    portfolio_weight_percent: Optional[float] = None
    concentration_rank: Optional[int] = None
    concentration_tier: Optional[str] = None  # DOMINANT | HIGH | MODERATE | LOW


@dataclass(frozen=True)
class BenchmarkDefinition:
    """Benchmark definition used by analytical category mappings."""

    benchmark_id: str
    name: str
    category: str
    geography: str
    market_cap_bucket: str
    industry_scope: str
    symbol_or_index: str
    benchmark_type: str


@dataclass(frozen=True)
class InvestableVehicle:
    """Investable vehicle that tracks or approximates benchmark exposure."""

    vehicle_id: str
    symbol: str
    name: str
    vehicle_type: str
    tracks_benchmark_id: str
    geography: str
    market_cap_bucket: str
    industry_scope: str


@dataclass(frozen=True)
class ReplaySelection:
    """Deterministic replay basket selection contract."""

    replay_id: str
    start_date: str
    end_date: str
    filter_market_cap_bucket: str
    filter_geography: str
    filter_industry: str
    selection_method: str
    top_n: int
    selected_symbols: Sequence[str] = field(default_factory=tuple)
    composite_score_snapshot_date: str = ""
    replay_mode: str = ReplayMode.HISTORICAL_VALIDATION.value
    filter_analytical_subtier: str = ""


@dataclass(frozen=True)
class PerformanceSeries:
    """One visualization datapoint for a replay series line."""

    series_id: str
    replay_id: str
    series_type: str
    date: str
    value: float
    cumulative_return: float
    source: str
    coverage_status: str = "AVAILABLE"


def validate_series_type(series_type: str) -> str:
    """Validate performance series type against canonical values."""

    allowed = {item.value for item in PerformanceSeriesType}
    if series_type not in allowed:
        raise ValueError(
            f"Invalid series_type {series_type!r}. Allowed values: {', '.join(sorted(allowed))}."
        )
    return series_type


def parse_iso_date(value: str) -> date:
    """Parse an ISO date and raise deterministic errors on invalid input."""

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date {value!r}.") from exc
