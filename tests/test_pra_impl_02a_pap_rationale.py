"""PRA-IMPL-02A end-to-end PAP rationale generation validation.

Ensures recommendation generator output (not parser-only logic) contains the
required policy-aware funding clauses.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.portfolio.models import (
    AllocationAlignmentResult,
    ConcentrationRiskSummary,
    PortfolioHolding,
    SecurityIntelligenceOverlay,
)
from src.portfolio.recommendations import generate_recommendations


_NOW = datetime.now(timezone.utc).isoformat()


def _holding(symbol: str, pct: float, mv: float, *, cash: bool = False, geo: str = "US", cap: str = "LARGE") -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id="PSNAP-RAT",
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
        composite_score=3.5,
        ess_score_text=None,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        operational_state="CASH_EQUIVALENT" if cash else "ACTIVE_POSITION",
        is_cash_equivalent=cash,
    )


def _overlay(symbol: str, *, opp: str = "HOLD", ess: str = "NEUTRAL", signal: str = "NEUTRAL") -> SecurityIntelligenceOverlay:
    return SecurityIntelligenceOverlay(
        portfolio_snapshot_id="PSNAP-RAT",
        symbol=symbol,
        composite_score=3.5,
        ess_score_text=ess,
        zacks_rating=None,
        signal_direction=signal,
        opportunity_flag=opp,
        flag_rationale="",
        replay_supported=False,
        best_replay_return=None,
        replay_percentile=None,
        percent_of_portfolio=0.0,
        is_overweight_vs_target=False,
        created_at_utc=_NOW,
    )


def _alignment_underweight() -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id="RUN-RAT",
        portfolio_snapshot_id="PSNAP-RAT",
        node_key="EQUITIES.US.LARGE",
        node_label="EQUITIES.US.LARGE",
        dimension_type="MARKET_CAP",
        actual_pct=8.0,
        target_pct=12.0,
        tactical_target_pct=12.0,
        drift_pct=-4.0,
        drift_direction="UNDERWEIGHT",
        severity="HIGH",
        concentration_risk="LOW",
        alignment_score=0.7,
        recommendation_priority=1,
        created_at_utc=_NOW,
    )


def _concentration() -> ConcentrationRiskSummary:
    return ConcentrationRiskSummary(
        analysis_run_id="RUN-RAT",
        portfolio_snapshot_id="PSNAP-RAT",
        top1_symbol="NVDA",
        top1_pct=10.0,
        top3_pct=20.0,
        top5_pct=30.0,
        top10_pct=50.0,
        mega_subtier_pct=15.0,
        single_sector_max_pct=20.0,
        single_sector_max_label="TECH",
        us_pct=80.0,
        international_pct=20.0,
        emerging_pct=0.0,
        herfindahl_index=0.08,
        concentration_tier="MODERATE",
        created_at_utc=_NOW,
    )


def test_generate_recommendations_includes_all_funding_clauses_e2e():
    holdings = [
        _holding("SPAXX", 12.0, 12000.0, cash=True),
        _holding("NVDA", 58.0, 58000.0),
        _holding("AAPL", 30.0, 30000.0),
    ]
    overlays = [
        _overlay("NVDA", opp="TRIM", ess="BEARISH", signal="BEARISH"),
        _overlay("AAPL"),
        _overlay("SPAXX"),
    ]

    recs = generate_recommendations(
        analysis_run_id="RUN-RAT",
        portfolio_snapshot_id="PSNAP-RAT",
        holdings=holdings,
        alignment_results=[_alignment_underweight()],
        concentration=_concentration(),
        overlays=overlays,
        strategic_profiles=None,
    )

    underweight_recs = [r for r in recs if r.recommendation_type == "INCREASE_UNDERWEIGHT"]
    assert underweight_recs, "Expected at least one INCREASE_UNDERWEIGHT recommendation"

    rationale = underweight_recs[0].rationale
    assert "Funding source:" in rationale
    assert "Why this source:" in rationale
    assert "Alternatives considered:" in rationale
    assert "Policy alignment:" in rationale
