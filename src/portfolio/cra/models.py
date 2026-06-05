"""CRA data models — Phase 23.6.

All models are frozen dataclasses.  CRA is a read-only composition layer;
no upstream scoring is modified.

Design contract source: docs/phase_23_6/06_data_contract.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Source category vocabulary ────────────────────────────────────────────────

CATEGORY_SIGNAL_DETERIORATION   = "SIGNAL_DETERIORATION"
CATEGORY_STRATEGIC_EXIT         = "STRATEGIC_EXIT"
CATEGORY_OVERWEIGHT_REDUCTION   = "OVERWEIGHT_REDUCTION"
CATEGORY_TAX_AWARE_EXIT         = "TAX_AWARE_EXIT"
CATEGORY_LOW_CONVICTION         = "LOW_CONVICTION_REDUCTION"

# Priority ordering (lower index = higher priority)
PRIORITY_ORDER = ["URGENT", "HIGH", "MODERATE", "LOW", "DEFER"]

# ── Tax bucket vocabulary (from Phase 23.0A) ─────────────────────────────────

TAX_BUCKET_A = "A"   # Loss harvest candidate
TAX_BUCKET_B = "B"   # Short-term gain, no special action
TAX_BUCKET_C = "C"   # Long-term gain, acceptable
TAX_BUCKET_D = "D"   # Long-term gain, significant — operator review
TAX_BUCKET_E = "E"   # Approaching LT threshold — defer

# ── Proposal status ───────────────────────────────────────────────────────────

STATUS_DRAFT     = "DRAFT"
STATUS_READY     = "READY"
STATUS_OP_REVIEW = "OPERATOR_REVIEW_REQUIRED"

# ── CRA schema version ────────────────────────────────────────────────────────

CRA_VERSION = "1.0"


@dataclass(frozen=True)
class CapitalSourceRecord:
    """A single sell-candidate holding identified by the CRA.

    This is a guidance artifact — NOT a sell instruction.  The operator
    uses Include/Skip controls in the UI to build the final capital pool.

    Fields read exclusively from upstream PAR artifacts; no new scoring.
    """

    symbol:               str
    current_value_usd:    float        # current market value
    estimated_proceeds:   float        # current_value_usd × sizing_pct
    sizing_pct:           float        # 0.0–1.0; fraction of position to sell
    category:             str          # see CATEGORY_* constants above
    priority:             str          # URGENT | HIGH | MODERATE | LOW | DEFER
    evidence_summary:     str          # human-readable rationale
    tax_bucket:           Optional[str]  # A | B | C | D | E | None
    tax_annotation:       str          # tax context description
    policy_type:          Optional[str] # active operator policy, if any
    blocked_by_policy:    bool         # True if DO_NOT_SELL blocks pool entry
    operator_review_required: bool     # True if CORE_ANCHOR, Bucket D, etc.

    # Optional extended evidence (for UI drilldown)
    ess_score_text:       Optional[str] = None
    signal_direction:     Optional[str] = None
    is_overweight:        bool = False
    drift_pct:            Optional[float] = None
    cost_basis:           Optional[float] = None
    unrealized_gain_loss: Optional[float] = None


@dataclass(frozen=True)
class RotationDeploymentTarget:
    """A deployment target drawn from the CW-DAS queue for a RotationProposal.

    Rank and deployment_score are IMMUTABLE copies from deployment_queue.json.
    The CRA does not re-rank or re-score.

    suggested_amount and projected_weight_pct are planning guidance only.
    """

    rank:                 int
    symbol:               str
    deployment_score:     float        # CW-DAS; unchanged from queue
    allocation_node:      str          # derived from holdings geography + cap tier
    narrative_tier:       str          # CORE_CONVICTION_LEADER | HIGH_CONVICTION_ANCHOR
    current_weight_pct:   float
    market_value:         float
    suggested_amount:     float        # USD from capital pool
    suggested_pct_add:    float        # percentage point addition (guidance)
    projected_weight_pct: float        # current + suggested_pct_add (guidance)
    score_breakdown:      Dict[str, Any]   # CwDasBreakdown fields; unchanged
    headroom_pct:         float        # from CW-DAS; how far below WARN threshold
    allocation_note:      str


@dataclass(frozen=True)
class PortfolioImpactEstimate:
    """Simplified impact estimate for a RotationProposal.

    IMPORTANT: This is an approximation only (is_estimate=True always).
    A full PAR re-run is required for precise alignment scoring.

    The simplified model uses node-level resolution/creation heuristics;
    it does NOT invoke the alignment engine.

    Design source: docs/phase_23_6/03_rotation_framework.md §3.6
    """

    alignment_score_before:   float       # from run_metadata.overall_alignment_score
    alignment_score_after:    float       # approximation
    alignment_delta:          float       # signed delta
    concentration_before:     float       # top-5 weight sum from concentration.json
    concentration_after:      float       # approximation
    concentration_delta:      float       # signed delta
    overweight_nodes_before:  List[str]   # overweight node keys before rotation
    overweight_nodes_after:   List[str]   # estimated remaining after rotation
    newly_underweight_nodes:  List[str]   # nodes that might go underweight
    impact_narrative:         str         # one-sentence human summary
    is_estimate:              bool = True  # always True; full run required

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alignment_score_before":  self.alignment_score_before,
            "alignment_score_after":   self.alignment_score_after,
            "alignment_delta":         round(self.alignment_delta, 4),
            "concentration_before":    self.concentration_before,
            "concentration_after":     self.concentration_after,
            "concentration_delta":     round(self.concentration_delta, 4),
            "overweight_nodes_before": self.overweight_nodes_before,
            "overweight_nodes_after":  self.overweight_nodes_after,
            "newly_underweight_nodes": self.newly_underweight_nodes,
            "impact_narrative":        self.impact_narrative,
            "is_estimate":             self.is_estimate,
        }


@dataclass(frozen=True)
class RotationProposal:
    """A complete Capital Rotation Advisor proposal.

    Assembles capital sources, deployment targets, and impact estimate into
    a single actionable guidance artifact.

    This is guidance only — NOT a trade instruction.
    Operators use Include/Skip controls to finalize before any execution.
    """

    proposal_id:         str
    run_id:              str
    as_of_date:          str
    portfolio_mv:        float
    total_capital_pool:  float          # sum of included estimated_proceeds
    sources:             List[CapitalSourceRecord]
    deployments:         List[RotationDeploymentTarget]
    impact:              PortfolioImpactEstimate
    proposal_status:     str            # DRAFT | READY | OPERATOR_REVIEW_REQUIRED
    review_flags:        List[str]      # reasons for OPERATOR_REVIEW_REQUIRED
    created_at_utc:      str
    suppressed_sources:  List[CapitalSourceRecord] = field(default_factory=list)  # de minimis (Phase 23.6B.4)
    cra_version:         str = CRA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict for API response."""

        def _source_dict(s: CapitalSourceRecord) -> Dict[str, Any]:
            return {
                "symbol":                  s.symbol,
                "current_value_usd":       s.current_value_usd,
                "estimated_proceeds":      s.estimated_proceeds,
                "sizing_pct":              s.sizing_pct,
                "category":                s.category,
                "priority":                s.priority,
                "evidence_summary":        s.evidence_summary,
                "tax_bucket":              s.tax_bucket,
                "tax_annotation":          s.tax_annotation,
                "policy_type":             s.policy_type,
                "blocked_by_policy":       s.blocked_by_policy,
                "operator_review_required": s.operator_review_required,
                "ess_score_text":          s.ess_score_text,
                "signal_direction":        s.signal_direction,
                "is_overweight":           s.is_overweight,
                "drift_pct":               s.drift_pct,
                "cost_basis":              s.cost_basis,
                "unrealized_gain_loss":    s.unrealized_gain_loss,
            }

        def _target_dict(t: RotationDeploymentTarget) -> Dict[str, Any]:
            return {
                "rank":                t.rank,
                "symbol":              t.symbol,
                "deployment_score":    t.deployment_score,
                "allocation_node":     t.allocation_node,
                "narrative_tier":      t.narrative_tier,
                "current_weight_pct":  t.current_weight_pct,
                "market_value":        t.market_value,
                "suggested_amount":    round(t.suggested_amount, 2),
                "suggested_pct_add":   round(t.suggested_pct_add, 4),
                "projected_weight_pct": round(t.projected_weight_pct, 4),
                "score_breakdown":     t.score_breakdown,
                "headroom_pct":        t.headroom_pct,
                "allocation_note":     t.allocation_note,
            }

        return {
            "proposal_id":              self.proposal_id,
            "run_id":                   self.run_id,
            "as_of_date":               self.as_of_date,
            "portfolio_mv":             self.portfolio_mv,
            "total_capital_pool":       round(self.total_capital_pool, 2),
            "proposal_status":          self.proposal_status,
            "review_flags":             self.review_flags,
            "created_at_utc":           self.created_at_utc,
            "cra_version":              self.cra_version,
            "source_count":             len(self.sources),
            "deployment_count":         len(self.deployments),
            "suppressed_source_count":  len(self.suppressed_sources),
            "sources":                  [_source_dict(s) for s in self.sources],
            "deployments":              [_target_dict(t) for t in self.deployments],
            "suppressed_sources":       [_source_dict(s) for s in self.suppressed_sources],
            "impact":                   self.impact.to_dict(),
        }
