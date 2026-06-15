"""PRA-IMPL-02 deterministic funding/reduction policy tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.portfolio.cra.funding_policy import (
    annotate_deployments_with_funding_plan,
    score_reduction_candidates,
)
from src.portfolio.cra.models import CapitalSourceRecord, RotationDeploymentTarget
from src.portfolio.models import AllocationAlignmentResult, PortfolioHolding, SecurityIntelligenceOverlay
from src.portfolio.recommendations import identify_funding_sources
from src.sih.allocation_explainability import build_recommendation_explanation

_NOW = datetime.now(timezone.utc).isoformat()


def _source(
    symbol: str,
    category: str,
    priority: str,
    estimated_proceeds: float,
    ess: str = "",
    signal: str = "",
    drift_pct: float | None = None,
    tax_bucket: str | None = None,
    blocked: bool = False,
) -> CapitalSourceRecord:
    return CapitalSourceRecord(
        symbol=symbol,
        current_value_usd=estimated_proceeds,
        estimated_proceeds=estimated_proceeds,
        sizing_pct=1.0,
        category=category,
        priority=priority,
        evidence_summary="test",
        tax_bucket=tax_bucket,
        tax_annotation="",
        policy_type=None,
        blocked_by_policy=blocked,
        operator_review_required=False,
        ess_score_text=ess or None,
        signal_direction=signal or None,
        is_overweight=bool(drift_pct and drift_pct > 0),
        drift_pct=drift_pct,
    )


def _target(rank: int, symbol: str) -> RotationDeploymentTarget:
    return RotationDeploymentTarget(
        rank=rank,
        symbol=symbol,
        deployment_score=90.0,
        allocation_node="EQUITIES.US.LARGE",
        narrative_tier="HIGH_CONVICTION_ANCHOR",
        current_weight_pct=3.0,
        market_value=10_000.0,
        suggested_amount=2_000.0,
        suggested_pct_add=0.4,
        projected_weight_pct=3.4,
        score_breakdown={},
        headroom_pct=15.0,
        allocation_note="test",
    )


def _holding(symbol: str, pct: float, mv: float, *, cash: bool = False, geo: str = "US", cap: str = "LARGE") -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id="PSNAP-TEST",
        snapshot_date="2026-01-01",
        account_name="TEST",
        symbol=symbol,
        description=symbol,
        quantity=1.0,
        market_value=mv,
        percent_of_portfolio=pct,
        asset_class="CASH" if cash else "EQUITIES",
        geography=geo,
        market_cap_bucket=cap,
        mega_subtier="N/A",
        sector="UNKNOWN",
        industry="UNKNOWN",
        security_type="Cash" if cash else "Common Stock",
        cost_basis=None,
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        operational_state="CASH_EQUIVALENT" if cash else "ACTIVE_POSITION",
        is_cash_equivalent=cash,
    )


def _overlay(symbol: str, *, opp: str = "HOLD", ess: str = "NEUTRAL", signal: str = "NEUTRAL", overweight: bool = False) -> SecurityIntelligenceOverlay:
    return SecurityIntelligenceOverlay(
        portfolio_snapshot_id="PSNAP-TEST",
        symbol=symbol,
        composite_score=None,
        ess_score_text=ess,
        zacks_rating=None,
        signal_direction=signal,
        opportunity_flag=opp,
        flag_rationale="",
        replay_supported=False,
        best_replay_return=None,
        replay_percentile=None,
        percent_of_portfolio=0.0,
        is_overweight_vs_target=overweight,
        created_at_utc=_NOW,
    )


def _alignment(node_key: str, drift: float, direction: str, severity: str) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id="RUN-TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        node_key=node_key,
        node_label=node_key,
        dimension_type="MARKET_CAP",
        actual_pct=10.0,
        target_pct=8.0,
        tactical_target_pct=8.0,
        drift_pct=drift,
        drift_direction=direction,
        severity=severity,
        concentration_risk="LOW",
        alignment_score=0.7,
        recommendation_priority=2,
        created_at_utc=_NOW,
    )


def test_reduction_candidates_rank_deterministically():
    sources = [
        _source("AAA", "OVERWEIGHT_REDUCTION", "HIGH", 12_000.0, drift_pct=14.0),
        _source("BBB", "SIGNAL_DETERIORATION", "HIGH", 10_000.0, ess="VERY_BEARISH", signal="BEARISH"),
        _source("CCC", "LOW_CONVICTION_REDUCTION", "MODERATE", 14_000.0),
    ]
    queue = [{"symbol": "AAA", "narrative_tier": "CORE_CONVICTION_LEADER", "rank": 1}]
    scored = score_reduction_candidates(sources=sources, deployment_queue=queue)

    assert scored[0].symbol == "BBB"
    assert scored[0].reduction_score >= scored[1].reduction_score >= scored[2].reduction_score
    assert scored[0].reduction_reason
    assert scored[0].policy_alignment_reason


def test_reduction_tie_breaks_by_symbol():
    sources = [
        _source("ZZZ", "LOW_CONVICTION_REDUCTION", "LOW", 2_000.0),
        _source("AAA", "LOW_CONVICTION_REDUCTION", "LOW", 2_000.0),
    ]
    scored = score_reduction_candidates(sources=sources, deployment_queue=[])
    assert scored[0].symbol == "AAA"
    assert scored[1].symbol == "ZZZ"


def test_deployment_annotations_include_primary_and_alternatives():
    scored_sources = score_reduction_candidates(
        sources=[
            _source("SRC1", "SIGNAL_DETERIORATION", "HIGH", 11_000.0, ess="BEARISH", signal="BEARISH"),
            _source("SRC2", "OVERWEIGHT_REDUCTION", "HIGH", 9_000.0, drift_pct=11.0),
            _source("SRC3", "LOW_CONVICTION_REDUCTION", "MODERATE", 8_000.0),
        ],
        deployment_queue=[],
    )
    deployments = annotate_deployments_with_funding_plan(
        deployments=[_target(1, "BUY1"), _target(2, "BUY2")],
        sources=scored_sources,
    )

    assert deployments[0].funding_source_symbol
    assert deployments[0].funding_source_reason
    assert deployments[0].funding_source_alternatives
    assert deployments[1].funding_source_symbol


def test_funding_source_capacity_depletes_across_targets():
    scored_sources = score_reduction_candidates(
        sources=[
            _source("MSFT", "OVERWEIGHT_REDUCTION", "HIGH", 20_000.0, drift_pct=10.0),
            _source("AAPL", "SIGNAL_DETERIORATION", "HIGH", 20_000.0, ess="BEARISH", signal="BEARISH"),
        ],
        deployment_queue=[],
    )

    t1 = _target(1, "VRT")
    t2 = _target(2, "ARW")
    # Require enough capital so target 1 fully consumes the top-ranked source.
    t1 = t1.__class__(**{**t1.__dict__, "suggested_amount": 20_000.0})
    t2 = t2.__class__(**{**t2.__dict__, "suggested_amount": 20_000.0})

    deployments = annotate_deployments_with_funding_plan(
        deployments=[t1, t2],
        sources=scored_sources,
    )

    assert deployments[0].funding_source_symbol == scored_sources[0].symbol
    assert deployments[1].funding_source_symbol == scored_sources[1].symbol


def test_depleted_sources_removed_from_alternatives():
    scored_sources = score_reduction_candidates(
        sources=[
            _source("SRC1", "SIGNAL_DETERIORATION", "HIGH", 5_000.0, ess="BEARISH", signal="BEARISH"),
            _source("SRC2", "OVERWEIGHT_REDUCTION", "HIGH", 15_000.0, drift_pct=12.0),
            _source("SRC3", "LOW_CONVICTION_REDUCTION", "MODERATE", 15_000.0),
        ],
        deployment_queue=[],
    )

    t1 = _target(1, "BUY1")
    t2 = _target(2, "BUY2")
    t1 = t1.__class__(**{**t1.__dict__, "suggested_amount": 5_000.0})
    t2 = t2.__class__(**{**t2.__dict__, "suggested_amount": 10_000.0})

    deployments = annotate_deployments_with_funding_plan(
        deployments=[t1, t2],
        sources=scored_sources,
    )

    assert deployments[0].funding_source_symbol == "SRC1"
    assert deployments[1].funding_source_symbol != "SRC1"
    assert all("SRC1" not in alt for alt in deployments[1].funding_source_alternatives)


def test_cash_first_policy_when_available():
    holdings = [
        _holding("SPAXX", 12.0, 12_000.0, cash=True),
        _holding("NVDA", 70.0, 70_000.0),
        _holding("AAPL", 18.0, 18_000.0),
    ]
    overlays = [_overlay("NVDA", opp="TRIM", ess="BEARISH", signal="BEARISH", overweight=True)]
    alignment = [_alignment("EQUITIES.US.LARGE", 8.0, "OVERWEIGHT", "HIGH")]

    funding = identify_funding_sources("RUN-TEST", "PSNAP-TEST", holdings, alignment, overlays)
    assert funding.sources
    assert funding.sources[0].source_type == "EXCESS_CASH"


def test_no_cash_scenario_uses_non_cash_sources():
    holdings = [
        _holding("SPAXX", 1.0, 1_000.0, cash=True),
        _holding("NVDA", 60.0, 60_000.0),
        _holding("AAPL", 39.0, 39_000.0),
    ]
    overlays = [_overlay("NVDA", opp="TRIM", ess="BEARISH", signal="BEARISH")]
    alignment = [_alignment("EQUITIES.US.LARGE", 9.0, "OVERWEIGHT", "HIGH")]

    funding = identify_funding_sources("RUN-TEST", "PSNAP-TEST", holdings, alignment, overlays)
    assert funding.sources
    assert funding.sources[0].source_type != "EXCESS_CASH"


def test_explainability_extracts_funding_and_alternatives_drivers():
    rec = {
        "recommendation_id": "REC-TEST",
        "recommendation_type": "INCREASE_UNDERWEIGHT",
        "affected_symbols": ["VRT"],
        "rationale": (
            "Portfolio is underweight. Funding source: Excess Cash (SPAXX, ~4.0% available). "
            "Why this source: Uses excess liquidity first. "
            "Alternatives considered: Trim Candidate, Overweight Reduction. "
            "Policy alignment: Rotates from weaker exposures into higher-conviction opportunities."
        ),
        "title": "Build exposure",
        "evidence_summary": "test",
    }
    explanation = build_recommendation_explanation(rec, Path("."), "2026-01-01", "RUN-TEST")
    driver_types = {d.get("driver_type") for d in explanation["funding_drivers"]}
    assert "funding_source" in driver_types
    assert "funding_alternatives" in driver_types
    assert "funding_policy_alignment" in driver_types
