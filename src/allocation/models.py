"""Canonical allocation intelligence data models for SIH."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class StructuralPolicy:
    """Governance guardrails loaded from config/allocation_policy.yaml."""

    policy_id: str
    policy_version: int
    effective_date: str
    cash_floor_pct: float
    max_micro_cap_pct: float
    max_digital_assets_pct: float
    max_single_sector_pct: float
    max_mega_concentration_pct: float
    max_single_asset_class_pct: float
    min_international_pct: float
    max_leverage_pct: float
    max_recalculation_delta_pct: float
    min_recalculation_interval_days: int
    min_meaningful_change_pct: float
    confidence_threshold: float
    replay_min_periods: int
    asset_class_governance: dict  # keyed by EQUITIES/FIXED_INCOME/DIGITAL/etc.
    governance_notes: tuple


@dataclass(frozen=True)
class AllocationDimensionNode:
    """A single node in the allocation hierarchy tree."""

    key: str                          # e.g. "EQUITIES.US.MEGA.HYPER_MEGA"
    label: str
    parent_key: Optional[str]
    dimension_type: str               # ASSET_CLASS | GEOGRAPHY | MARKET_CAP | MEGA_SUBTIER | ASSET_SUBTYPE
    allocation_category_type: str     # EQUITY | FIXED_INCOME | DIGITAL | COMMODITY | CASH
    hierarchy_level: int              # 1=asset class, 2=geography, 3=market cap, 4=mega subtier
    children: tuple                   # tuple of child key strings
    replay_filter_mapping: dict       # maps to replay_inputs.csv filter columns
    replay_sophistication: str        # HIGH | LOW | NONE

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def asset_class(self) -> str:
        """Top-level asset class key from this node's key path."""
        return self.key.split(".")[0]


@dataclass(frozen=True)
class AllocationMethodologyBasis:
    """Research rationale and seed target for one hierarchy node."""

    node_key: str
    methodology_id: str
    evidence_basis: tuple             # tuple of str
    risk_factors: tuple               # tuple of str
    baseline_target_pct_of_parent: float
    confidence_level: str             # HIGH | MEDIUM | LOW


@dataclass(frozen=True)
class StrategicAllocationTarget:
    """A target allocation for one hierarchy node at a specific recalculation."""

    target_id: str
    snapshot_date: str
    recalculation_id: str
    node_key: str                     # e.g. "EQUITIES.US.MEGA.HYPER_MEGA"
    node_label: str
    parent_key: Optional[str]
    asset_class: str                  # EQUITIES | FIXED_INCOME | DIGITAL | COMMODITIES | CASH
    geography: Optional[str]          # US | INTERNATIONAL | EMERGING_MARKETS | None
    market_structure: Optional[str]   # MEGA | LARGE | MID | SMALL | MICRO | None
    mega_subtier: Optional[str]       # HYPER_MEGA | ULTRA_MEGA | EXTENDED_MEGA | None
    hierarchy_depth: int              # 1-4
    target_pct_of_parent: float
    target_pct_of_total: float        # = product(pct_of_parent) up ancestry chain
    prior_target_pct_of_total: Optional[float]
    delta_pct: Optional[float]
    confidence_score: float           # 0.0–1.0
    evidence_summary: str             # human-readable "why this target"
    evidence_ids: tuple               # tuple of str
    methodology_basis_ref: str        # references AllocationMethodologyBasis.node_key
    policy_bounded: bool


@dataclass(frozen=True)
class TacticalMomentumOverlay:
    """A temporary tactical adjustment to a dimension (sector, cap tier, geography)."""

    overlay_id: str
    effective_date: str
    expiry_date: Optional[str]
    dimension_type: str               # SECTOR | SUBSECTOR | MARKET_CAP | GEOGRAPHY
    dimension_value: str              # e.g. TECHNOLOGY, SEMICONDUCTORS, MEGA, US
    overlay_pct: float                # signed: +3.0 = overweight, -1.5 = underweight
    max_overlay_pct: float            # governance bound (absolute value)
    persistence_score: float          # 0.0–1.0
    momentum_signal: str              # STRONG | MODERATE | WEAK
    replay_support_ids: tuple         # tuple of replay_id strings
    notes: str
    status: str                       # ACTIVE | EXPIRED | OVERRIDDEN


@dataclass(frozen=True)
class AllocationRecommendation:
    """Effective allocation after applying tactical overlays, bounded by policy."""

    recommendation_id: str
    snapshot_date: str
    policy_id: str
    recalculation_id: str
    node_key: str
    asset_class: str
    strategic_target_pct: float
    tactical_overlay_pct: float       # 0.0 for non-equity or non-overlay nodes
    effective_target_pct: float       # strategic + tactical, bounded by policy
    is_policy_capped: bool
    policy_ceiling: Optional[float]
    drift_from_prior: Optional[float]


@dataclass(frozen=True)
class AllocationEvidence:
    """Evidence record supporting a target — from replay or methodology."""

    evidence_id: str
    evidence_date: str
    evidence_type: str                # REPLAY_OUTPERFORMANCE | VOLATILITY_WARNING | MOMENTUM
                                      # | METHODOLOGY_BASELINE | FACTOR_PERSISTENCE
    node_key: str
    asset_class: str
    metric_name: str                  # e.g. "relative_return_90d", "outperformance_persistence"
    metric_value: float
    benchmark_comparison: Optional[str]
    significance: str                 # HIGH | MEDIUM | LOW
    replay_id: Optional[str]
    human_readable: str               # e.g. "EQUITIES.US.MEGA 90-day +7.4% vs BM_US_MEGA_SP100"


@dataclass(frozen=True)
class AllocationRecalculationSnapshot:
    """Versioned record of one recalculation cycle — append-only lineage."""

    recalculation_id: str
    recalculation_date: str
    prior_recalculation_id: Optional[str]
    triggered_by: str                 # SCHEDULED | EVIDENCE_THRESHOLD | MANUAL
    policy_version: str
    evidence_ids: tuple               # tuple of str
    change_summary: tuple             # tuple of human-readable str, one per changed node
    unchanged_summary: str            # e.g. "14 nodes unchanged (methodology baseline)"
    confidence_summary: dict          # node_key → confidence_score
    total_allocation_valid: bool
    notes: str


@dataclass(frozen=True)
class PortfolioComparisonResult:
    """Future-facing comparison model. All fields Optional — zero logic implemented."""

    comparison_id: str
    comparison_date: Optional[str] = None
    portfolio_source: Optional[str] = None      # "UPLOAD" | "API"
    recommendation_id: Optional[str] = None
    node_key: Optional[str] = None
    portfolio_current_pct: Optional[float] = None
    effective_target_pct: Optional[float] = None
    drift_pct: Optional[float] = None
    drift_direction: Optional[str] = None       # OVERWEIGHT | UNDERWEIGHT | ALIGNED
    rebalance_pressure: Optional[str] = None    # HIGH | MEDIUM | LOW | NONE
