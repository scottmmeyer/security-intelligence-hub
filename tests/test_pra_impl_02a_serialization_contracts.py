"""PRA-IMPL-02A serialization contract hardening tests.

These tests lock the JSON contract fields added in PRA-IMPL-02 so regressions
(surface removal/rename/incorrect serialization) fail deterministically.
"""

from __future__ import annotations

from src.portfolio.cra.models import (
    CapitalSourceRecord,
    PortfolioImpactEstimate,
    RotationDeploymentTarget,
    RotationProposal,
)


def _proposal_with_fields(*, populated: bool) -> RotationProposal:
    source = CapitalSourceRecord(
        symbol="MSFT",
        current_value_usd=20000.0,
        estimated_proceeds=10000.0,
        sizing_pct=0.5,
        category="OVERWEIGHT_REDUCTION",
        priority="HIGH",
        evidence_summary="overweight",
        tax_bucket="C",
        tax_annotation="test",
        policy_type=None,
        blocked_by_policy=False,
        operator_review_required=False,
        reduction_score=87.2 if populated else 0.0,
        reduction_reason="Reduce overweight first" if populated else "",
        policy_alignment_reason="Rotate from over-allocated exposure" if populated else "",
    )

    target = RotationDeploymentTarget(
        rank=1,
        symbol="VRT",
        deployment_score=92.5,
        allocation_node="EQUITIES.US.LARGE",
        narrative_tier="HIGH_CONVICTION_ANCHOR",
        current_weight_pct=2.0,
        market_value=12000.0,
        suggested_amount=5000.0,
        suggested_pct_add=1.0,
        projected_weight_pct=3.0,
        score_breakdown={"signal": 25.0},
        headroom_pct=12.0,
        allocation_note="test",
        funding_source_symbol="MSFT" if populated else "",
        funding_source_category="OVERWEIGHT_REDUCTION" if populated else "",
        funding_source_score=87.2 if populated else 0.0,
        funding_source_reason="Higher reduction score" if populated else "",
        funding_source_alternatives=["AAPL (TRIM CANDIDATE, score 80.0)"] if populated else [],
        funding_policy_alignment_reason="Supports concentrated-alpha rotation" if populated else "",
    )

    impact = PortfolioImpactEstimate(
        alignment_score_before=0.4,
        alignment_score_after=0.45,
        alignment_delta=0.05,
        concentration_before=35.0,
        concentration_after=34.0,
        concentration_delta=-1.0,
        overweight_nodes_before=["EQUITIES.US.LARGE"],
        overweight_nodes_after=[],
        newly_underweight_nodes=[],
        impact_narrative="test",
    )

    return RotationProposal(
        proposal_id="CRA-TEST",
        run_id="PAR-TEST",
        as_of_date="2026-06-14",
        portfolio_mv=100000.0,
        total_capital_pool=10000.0,
        sources=[source],
        deployments=[target],
        impact=impact,
        proposal_status="READY",
        review_flags=[],
        created_at_utc="2026-06-14T00:00:00+00:00",
    )


def test_capital_source_record_contract_populated_values():
    payload = _proposal_with_fields(populated=True).to_dict()
    source = payload["sources"][0]

    assert source["reduction_score"] == 87.2
    assert source["reduction_reason"] == "Reduce overweight first"
    assert source["policy_alignment_reason"] == "Rotate from over-allocated exposure"


def test_capital_source_record_contract_empty_values_present():
    payload = _proposal_with_fields(populated=False).to_dict()
    source = payload["sources"][0]

    assert "reduction_score" in source
    assert "reduction_reason" in source
    assert "policy_alignment_reason" in source
    assert source["reduction_score"] == 0.0
    assert source["reduction_reason"] == ""
    assert source["policy_alignment_reason"] == ""


def test_rotation_deployment_target_contract_populated_values():
    payload = _proposal_with_fields(populated=True).to_dict()
    target = payload["deployments"][0]

    assert target["funding_source_symbol"] == "MSFT"
    assert target["funding_source_category"] == "OVERWEIGHT_REDUCTION"
    assert target["funding_source_score"] == 87.2
    assert target["funding_source_reason"] == "Higher reduction score"
    assert target["funding_source_alternatives"] == ["AAPL (TRIM CANDIDATE, score 80.0)"]
    assert target["funding_policy_alignment_reason"] == "Supports concentrated-alpha rotation"


def test_rotation_deployment_target_contract_empty_values_present():
    payload = _proposal_with_fields(populated=False).to_dict()
    target = payload["deployments"][0]

    assert "funding_source_symbol" in target
    assert "funding_source_category" in target
    assert "funding_source_score" in target
    assert "funding_source_reason" in target
    assert "funding_source_alternatives" in target
    assert "funding_policy_alignment_reason" in target

    assert target["funding_source_symbol"] == ""
    assert target["funding_source_category"] == ""
    assert target["funding_source_score"] == 0.0
    assert target["funding_source_reason"] == ""
    assert target["funding_source_alternatives"] == []
    assert target["funding_policy_alignment_reason"] == ""
