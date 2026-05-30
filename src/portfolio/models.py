"""Canonical models for the Portfolio Alignment Analysis capability.

Design principles:
- All models are frozen dataclasses — immutable after construction.
- No behavioral logic lives here; only data contracts.
- Every model records lineage: source_file, created_at_utc, snapshot_id.
- Classification fields mirror the SIH analytical_universe contract exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Canonical Portfolio Holding
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PortfolioHolding:
    """A single normalized holding within a portfolio snapshot.

    All monetary values are in USD.  Classification fields (market_cap_bucket,
    geography, sector, industry) use SIH canonical vocabulary and are populated
    by the enrichment step after ingestion.
    """

    # Identity
    portfolio_snapshot_id: str
    snapshot_date: str                       # ISO 8601 YYYY-MM-DD
    account_name: str
    symbol: str
    description: str

    # Position sizing
    quantity: float
    market_value: float
    percent_of_portfolio: float              # 0.0–100.0

    # SIH classification dimensions (enriched from analytical_universe)
    asset_class: str                         # EQUITIES | FIXED_INCOME | DIGITAL | COMMODITIES | CASH | UNKNOWN
    geography: str                           # US | INTERNATIONAL | EMERGING_MARKETS | UNKNOWN
    market_cap_bucket: str                   # MEGA | LARGE | MID | SMALL | MICRO | UNKNOWN
    mega_subtier: str                        # HYPER_MEGA | STANDARD_MEGA | UNKNOWN | N/A
    sector: str
    industry: str
    security_type: str                       # Common Stock | ETF | Bond | Cash | Other

    # Optional enrichment
    cost_basis: Optional[float]
    composite_score: Optional[float]         # from analytical_universe at snapshot
    ess_score_text: Optional[str]
    zacks_rating: Optional[str]
    benchmark_id: Optional[str]
    investable_vehicle_id: Optional[str]

    # Lineage
    source_file: str
    created_at_utc: str                      # ISO 8601 datetime

    # Exposure decomposition (ETF / fund heuristic model; direct rows stay empty or one-hot)
    exposure_geography_mix: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    exposure_market_cap_mix: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    exposure_mega_subtier_mix: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    exposure_sector_mix: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    exposure_style_mix: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    exposure_thematic_mix: tuple[tuple[str, float], ...] = field(default_factory=tuple)  # independent concentration flags
    decomposition_method: str = ""
    decomposition_version: str = ""
    decomposition_timestamp: str = ""
    decomposition_confidence: Optional[float] = None
    decomposition_source: str = ""             # REGISTRY | DIRECT_CLASSIFICATION | HEURISTIC_FALLBACK | UNRESOLVED
    decomposition_confidence_tier: str = ""    # HIGH | MEDIUM | LOW | UNKNOWN
    strategic_role: str = ""                   # e.g. CORE_BROAD_US | AGGRESSIVE_GROWTH_CONCENTRATION

    # Phase 6.1 — Operational state and cash classification
    operational_state: str = "ACTIVE_POSITION"
    # ACTIVE_POSITION       — investable, included in all analytics
    # CASH_EQUIVALENT       — money-market / sweep fund, included in analytics (direct cash exposure)
    # PENDING_SETTLEMENT    — pending activity / unsettled transaction, excluded from analytics
    # ACCOUNTING_ADJUSTMENT — negative market-value correction row, excluded from analytics
    # CLOSED_POSITION       — zero market-value closed position, excluded from analytics
    # NON_ANALYZABLE        — any other non-investment row
    is_cash_equivalent: bool = False           # True for money-market sweep funds and operational cash


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Immutable snapshot of an entire portfolio at a point in time.

    Contains aggregate metadata; individual holdings are stored separately
    and linked via portfolio_snapshot_id.
    """

    portfolio_snapshot_id: str
    snapshot_date: str
    account_name: str
    total_market_value: float
    holding_count: int
    source_file: str
    source_format: str                       # FIDELITY_CSV | GENERIC_CSV
    ingestion_status: str                    # ACCEPTED | REJECTED | PARTIAL
    normalization_warnings: tuple            # tuple[str] — non-fatal issues found
    created_at_utc: str
    run_id: str                              # ties snapshot to analysis run


# ─────────────────────────────────────────────────────────────────────────────
# Phase E — Allocation Alignment Result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AllocationAlignmentResult:
    """Comparison of actual vs target allocation for a single hierarchy node."""

    analysis_run_id: str
    portfolio_snapshot_id: str
    node_key: str                            # e.g. "EQUITIES.US.MEGA.HYPER_MEGA"
    node_label: str
    dimension_type: str                      # ASSET_CLASS | GEOGRAPHY | MARKET_CAP | MEGA_SUBTIER

    # Allocation figures (% of total portfolio)
    actual_pct: float
    target_pct: float
    tactical_target_pct: float               # tactical-adjusted target
    drift_pct: float                         # actual - tactical_target
    drift_direction: str                     # OVERWEIGHT | UNDERWEIGHT | ON_TARGET

    # Risk assessment
    severity: str                            # HIGH | MODERATE | LOW | NONE
    concentration_risk: str                  # HIGH | MODERATE | LOW | NONE
    alignment_score: float                   # 0.0–1.0; 1.0 = perfectly aligned

    # Recommendation metadata
    recommendation_priority: int             # 1 = highest priority
    created_at_utc: str

    # Exposure decomposition breakdown (% of total portfolio)
    direct_actual_pct: float = 0.0
    etf_derived_actual_pct: float = 0.0
    effective_actual_pct: float = 0.0
    decomposition_method: str = ""
    decomposition_version: str = ""
    decomposition_confidence: Optional[float] = None
    decomposition_source: str = ""             # REGISTRY | DIRECT_CLASSIFICATION | HEURISTIC_FALLBACK | UNRESOLVED
    decomposition_confidence_tier: str = ""    # HIGH | MEDIUM | LOW | UNKNOWN


@dataclass(frozen=True)
class ConcentrationRiskSummary:
    """Portfolio-level concentration risk snapshot."""

    analysis_run_id: str
    portfolio_snapshot_id: str

    # Top-position dominance
    top1_symbol: str
    top1_pct: float
    top3_pct: float
    top5_pct: float
    top10_pct: float

    # Dimension concentrations
    mega_subtier_pct: float                  # pct in HYPER_MEGA
    single_sector_max_pct: float
    single_sector_max_label: str
    us_pct: float
    international_pct: float
    emerging_pct: float

    # Scores
    herfindahl_index: float                  # 0.0–1.0; higher = more concentrated
    concentration_tier: str                  # CRITICAL | HIGH | MODERATE | DIVERSIFIED
    created_at_utc: str

    mega_subtier_direct_pct: float = 0.0
    mega_subtier_etf_derived_pct: float = 0.0
    mega_subtier_effective_pct: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Phase F — Recommendation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PortfolioRecommendation:
    """A single explainable advisory recommendation.

    These are guidance outputs — NOT trade instructions.
    """

    recommendation_id: str
    analysis_run_id: str
    portfolio_snapshot_id: str

    # Classification
    recommendation_type: str                 # See RECOMMENDATION_TYPES below
    priority: int                            # 1 = act soonest
    confidence: str                          # HIGH | MEDIUM | LOW

    # What and why
    title: str
    rationale: str                           # plain-English explanation
    evidence_summary: str                    # replay/score evidence reference
    affected_node_key: Optional[str]         # which hierarchy node this targets
    affected_symbols: tuple                  # tuple[str] — specific securities implicated

    # Magnitude
    drift_pct: Optional[float]
    severity: str                            # HIGH | MODERATE | LOW

    # Lineage
    replay_run_ids: tuple                    # tuple[str] — supporting replays
    created_at_utc: str

    # Phase C — Recommendation state + explainability
    rec_state: str = "ACTIVE"              # ACTIVE | DOWNGRADED | INFORMATIONAL | SUPPRESSED
    reasoning_trace: str = ""             # Why was this state assigned? (explainability)

    # Phase C — Direct vs derived exposure breakdown (% of total portfolio)
    direct_exposure_pct: float = 0.0      # Direct holdings exposure for affected_node_key
    etf_derived_exposure_pct: float = 0.0 # ETF-fund-derived exposure for affected_node_key
    effective_exposure_pct: float = 0.0   # Combined effective exposure
    etf_contributors: tuple = ()          # tuple[str] — ETF symbols contributing to this node

    # Phase F-2 — Vehicle suitability scoring (populated for INCREASE_UNDERWEIGHT recs)
    vehicle_suitability_notes: tuple = ()  # tuple[VehicleSuitabilityNote], sorted by suitability_score desc


@dataclass(frozen=True)
class VehicleSuitabilityNote:
    """Suitability assessment for a single suggested investable vehicle.

    Scored relative to the specific underweight allocation node being targeted.
    A vehicle that is HIGH suitability for general Mega may be MEDIUM for
    Extended Mega, where subtier purity and off-target spillover matter more.
    """

    symbol: str
    target_node_coverage_pct: float       # % of vehicle's exposure allocated to the target node
    off_target_exposure_pct: float        # % allocated to adjacent/sibling nodes (not the target)
    overlap_with_existing_pct: float      # % of vehicle exposure in already-overweight nodes
    worsens_existing_overweight: bool     # True if vehicle meaningfully worsens an overweight node
    thematic_concentration_added: str     # worst-case thematic risk label, or ""
    strategic_role: str                   # e.g. CORE_BROAD_US, AGGRESSIVE_GROWTH_CONCENTRATION
    suitability_score: float              # 0.0–100.0 (higher = more suitable for this specific node)
    suitability_tier: str                 # HIGH | MEDIUM | LOW
    suitability_explanation: str          # plain-English reason, suitable for UI display


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6.1D — Funding Source Analysis
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FundingSourceEntry:
    """A single identified source of deployable capital for reallocation."""

    priority: int                    # 1 = highest priority
    source_type: str                 # EXCESS_CASH | TRIM_CANDIDATE | OVERWEIGHT_REDUCTION
    symbols: tuple                   # tuple[str] — symbol(s) contributing this source
    available_pct: float             # estimated % of portfolio value deployable from this source
    rationale: str                   # plain-English explanation for the recommendation UI


@dataclass(frozen=True)
class FundingSourceAnalysis:
    """Funding source intelligence for the current portfolio analysis run.

    Identifies capital that can be redeployed into underweight allocations
    without requiring new external capital contributions.
    """

    analysis_run_id: str
    portfolio_snapshot_id: str
    sources: tuple                   # tuple[FundingSourceEntry], sorted by priority
    total_available_pct: float       # total deployable capital across all sources
    summary: str                     # one-sentence narrative for the UI
    created_at_utc: str


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6.2 — Portfolio Mandate Intelligence (PMI)
# ─────────────────────────────────────────────────────────────────────────────

# Valid mandate type identifiers
MANDATE_TYPES = frozenset({
    "BALANCED",
    "GROWTH",
    "DEFENSIVE",
    "INCOME",
    "REPLAY_OPTIMIZED",
    "CONCENTRATED_ALPHA",
})

# Labels for mandate-adjusted drift interpretation
MANDATE_DRIFT_LABELS = frozenset({
    "ON_TARGET",
    "STANDARD_OVERWEIGHT",
    "TOLERATED_OVERWEIGHT",
    "INTENTIONAL_OVERWEIGHT",
    "STANDARD_UNDERWEIGHT",
    "TOLERATED_UNDERWEIGHT",
    "INTENTIONAL_UNDERWEIGHT",
})

# Intentional asymmetry assessment states
ASYMMETRY_STATES = frozenset({
    "ACCIDENTAL",          # drift appears circumstantial
    "LIKELY_INTENTIONAL",  # pattern suggests deliberate positioning
    "HIGH_CONVICTION",     # strong evidence of intentional asymmetric construction
})


@dataclass(frozen=True)
class PortfolioMandate:
    """Investment philosophy and risk tolerance profile for a portfolio mandate.

    PMI Governance: this model defines HOW to interpret portfolio analytics,
    not the analytics themselves.  No decomposition, suitability, replay, or
    exposure data is modified by mandate application.
    """

    mandate_type: str                         # from MANDATE_TYPES
    display_name: str
    description: str

    # Tolerance levels: 0.0 = zero tolerance (strict), 1.0 = fully tolerated (lenient)
    concentration_tolerance: float            # general equity concentration drift
    cash_tolerance: float                     # excess cash vs target
    fixed_income_tolerance: float             # fixed income shortfall (0=critical, 1=ignored)
    small_cap_tolerance: float                # small/micro-cap overweight
    thematic_concentration_tolerance: float   # single-theme exposure clustering

    # Priority weights: 0.0 = not a priority, 1.0 = highest priority
    replay_alignment_priority: float          # how much replay-backed evidence matters
    turnover_tolerance: float                 # 0 = prefer stability, 1 = churn is fine
    diversification_priority: float           # 0 = concentration OK, 1 = diversify hard
    target_adherence_priority: float          # 0 = ignore target model, 1 = stick to it


@dataclass(frozen=True)
class MandateDriftInterpretation:
    """Mandate-adjusted interpretation of a single allocation node's drift.

    The underlying exposure data (actual_pct, drift_pct, etc.) is UNCHANGED.
    Only the semantic interpretation changes: is this drift a problem, a choice,
    or an intentional feature of the mandate?
    """

    node_key: str
    node_label: str
    mandate_type: str
    raw_drift_pct: float
    raw_severity: str                    # original severity from alignment engine
    mandate_severity: str                # adjusted: HIGH | MODERATE | LOW | NONE
    mandate_drift_label: str             # from MANDATE_DRIFT_LABELS
    mandate_urgency: str                 # URGENT | MODERATE | LOW | INFORMATIONAL
    mandate_rationale: str               # plain-English explanation
    suppress_recommendation: bool        # True when mandate considers drift within policy


@dataclass(frozen=True)
class ScoreComponent:
    """A single component contributing to a multi-dimensional portfolio score."""

    component_name: str
    raw_score: float                     # 0.0–100.0 (pre-weighting)
    weight: float                        # contribution weight (0.0–1.0)
    weighted_score: float                # raw_score * weight
    explanation: str


@dataclass(frozen=True)
class MultiDimensionalScore:
    """Four-dimensional portfolio quality score framework.

    Replaces the single overall_alignment_score with orthogonal dimensions
    that better reflect institutional portfolio assessment:

      Allocation Alignment   — distance from the target model
      Portfolio Quality      — concentration, signal quality, strategic classification
      Implementation Quality — vehicle suitability, operational integrity
      Replay Alignment       — replay-supported exposure coverage and quality
    """

    analysis_run_id: str
    portfolio_snapshot_id: str
    mandate_type: str

    # Top-level scores (0–100, rounded to 1 decimal)
    allocation_alignment_score: float
    portfolio_quality_score: float
    implementation_quality_score: float
    replay_alignment_score: float

    # Component breakdowns (tuple[ScoreComponent])
    allocation_alignment_components: tuple
    portfolio_quality_components: tuple
    implementation_quality_components: tuple
    replay_alignment_components: tuple

    created_at_utc: str


@dataclass(frozen=True)
class IntentionalAsymmetryAssessment:
    """Detects whether portfolio drift is likely accidental or intentional.

    Analyses signal patterns — replay-backed overweights, high-conviction
    retain classifications, thematic clustering — to assess whether the
    portfolio's apparent target-model deviations reflect deliberate positioning.
    """

    analysis_run_id: str
    portfolio_snapshot_id: str
    mandate_type: str

    asymmetry_state: str                 # from ASYMMETRY_STATES
    asymmetry_score: float               # 0.0–1.0 (higher = more evidence of intent)

    evidence_signals: tuple              # tuple[str] — detected patterns
    dominant_theme: str                  # primary detected theme or "UNKNOWN"
    replay_conviction_count: int         # number of replay-supported overweight nodes
    thematic_cluster_count: int          # number of thematic clusters with >10% exposure

    assessment_rationale: str
    created_at_utc: str


# Canonical recommendation type vocabulary
RECOMMENDATION_TYPES = frozenset({
    "REDUCE_OVERWEIGHT",
    "INCREASE_UNDERWEIGHT",
    "DIVERSIFY_CONCENTRATION",
    "IMPROVE_SECTOR_EXPOSURE",
    "IMPROVE_GEOGRAPHY_BALANCE",
    "IMPROVE_MARKET_CAP_BALANCE",
    "IMPROVE_REPLAY_ALIGNMENT",
    "IMPROVE_RISK_PROFILE",
    # Phase D — Strategic Trim Intelligence
    "STRATEGIC_TRIM_CANDIDATE",   # specific holding(s) identified as most expendable
    "STRATEGIC_RETAIN_SIGNAL",    # holding explicitly flagged as portfolio-critical
    # Phase E — Strategic Recommendation Synthesis
    "PORTFOLIO_CONSTRUCTION_NARRATIVE",   # synthesized construction guidance narrative
    "THEMATIC_SATURATION_NARRATIVE",      # ecosystem-level thematic overlap analysis
    "TOP_TRIM_CANDIDATES",                # ranked trim candidate list within overlap cluster
    "STRATEGIC_RETAIN_NARRATIVE",         # retain reasoning for high-conviction holdings
    "CONCENTRATION_ECOSYSTEM",            # concentration topology with justified vs accidental
})


# ─────────────────────────────────────────────────────────────────────────────
# Phase G — Security-level intelligence overlay
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SecurityIntelligenceOverlay:
    """Intelligence overlay for a single held security.

    Links holding data to SIH analytical signals and replay performance.
    """

    portfolio_snapshot_id: str
    symbol: str

    # Current scores from analytical_universe
    composite_score: Optional[float]
    ess_score_text: Optional[str]
    zacks_rating: Optional[str]

    # Replay-derived
    best_replay_return: Optional[float]
    replay_percentile: Optional[float]       # where symbol ranked in its tier replay
    replay_supported: bool                   # True if top-quartile in any replay

    # Position context
    percent_of_portfolio: float
    is_overweight_vs_target: bool

    # Intelligence synthesis
    signal_direction: str                    # BULLISH | NEUTRAL | BEARISH | UNKNOWN
    opportunity_flag: str                    # TRIM | HOLD | ACCUMULATE | WATCH
    flag_rationale: str
    created_at_utc: str


# ─────────────────────────────────────────────────────────────────────────────
# Phase D — Strategic Trim Intelligence Profile
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HoldingStrategicProfile:
    """Strategic Trim Intelligence (STI) profile for a single portfolio holding.

    Phase D — Portfolio Construction Intelligence.

    Captures strategic classification, trim priority score, thematic overlap,
    exposure origin, and full explainability for every holding.  These profiles
    evolve the system from allocation correction into portfolio construction
    intelligence: which holdings are core, which are redundant, which are the
    best trim candidates, and why.
    """

    portfolio_snapshot_id: str
    symbol: str
    security_type: str
    percent_of_portfolio: float

    # D.1 — Strategic classification
    strategic_classification: str
    # Vocabulary:
    #   HIGH_CONVICTION_RETAIN   — strong signal + replay-supported + low thematic overlap
    #   CORE_COMPOUNDER          — foundational broad exposure + healthy signal
    #   STRATEGIC_CORE           — fills unique allocation need; preserve
    #   THEMATIC_LEADER          — highest-conviction holding within its thematic cluster
    #   TACTICAL_GROWTH          — decent signal but participates in shared thematic overlap
    #   REDUNDANT_EXPOSURE       — low unique contribution; better peers exist
    #   CONCENTRATION_RISK       — high portfolio weight + high thematic concentration
    #   REDUCIBLE                — highest trim priority in its cluster

    # D.2 — Trim priority score (0.0–100.0; higher = more expendable)
    trim_priority_score: float
    trim_factors: tuple          # tuple[(factor_name, contribution, rationale)]

    # D.3 — Thematic overlap analysis
    thematic_overlap_clusters: tuple   # tuple[str]: themes where this holding overlaps
    overlap_peers: tuple               # tuple[str]: symbols with significant shared exposure
    thematic_redundancy_score: float   # 0.0–100.0; higher = more redundant vs peers

    # D.4 — Strategic role
    strategic_role: str                # inherited from PortfolioHolding.strategic_role
    strategic_importance: str          # CRITICAL | HIGH | MEDIUM | LOW

    # D.5 — Exposure origin
    exposure_origin: str
    # Vocabulary:
    #   DIRECT_INTENTIONAL  — stock directly held (intentional alpha bet)
    #   ETF_INHERITED       — broad index fund (incidental exposure)
    #   ETF_THEMATIC        — concentrated ETF (deliberate thematic bet)
    #   UNKNOWN

    # D.6/7 — Explainability
    trim_rationale: str           # Why this holding ranks where it does on trim priority
    retain_rationale: str         # Why to keep this holding if retaining
    classification_trace: str     # Step-by-step classification reasoning

    # Individual factor scores (for UI decomposition display)
    concentration_pressure: float       # 0.0–100.0
    diversification_contribution: float # 0.0–100.0; higher = more unique contribution

    created_at_utc: str

    # Phase 7.1 — Narrative tiering (explainability layer only; does not replace STI classification)
    narrative_tier: str = ""
    # Vocabulary: CORE_CONVICTION_LEADER | HIGH_CONVICTION_ANCHOR | TACTICAL_GROWTH_CANDIDATE | WATCH_TRIM_CANDIDATE | ""
    strategic_anchor_rank: int = 0
    # 1 = strongest anchor signal; higher = weaker conviction; 0 = unranked


# ─────────────────────────────────────────────────────────────────────────────
# Analysis Run envelope
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PortfolioAnalysisRun:
    """Envelope for a complete portfolio alignment analysis execution."""

    run_id: str
    portfolio_snapshot_id: str
    snapshot_date: str
    recalculation_id: str                    # ties to the active SIH allocation targets
    analytical_universe_date: str           # which universe snapshot was used for enrichment
    alignment_results_count: int
    recommendation_count: int
    concentration_tier: str
    overall_alignment_score: float           # 0.0–1.0
    status: str                              # COMPLETE | PARTIAL | FAILED
    warnings: tuple
    created_at_utc: str
