"""PRA-IMPL-02A CRA API contract validation tests.

These tests exercise the real /api/cra/proposal endpoint path consumed by
Portfolio Alignment UI and assert PRA-IMPL-02 fields in JSON payloads.
"""

from __future__ import annotations

import json
import socket
import threading
import urllib.request
from contextlib import closing
from unittest.mock import patch

from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer
from src.portfolio.cra.models import (
    CapitalSourceRecord,
    PortfolioImpactEstimate,
    RotationDeploymentTarget,
    RotationProposal,
)


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _proposal(*, populated: bool) -> RotationProposal:
    source = CapitalSourceRecord(
        symbol="MSFT",
        current_value_usd=25000.0,
        estimated_proceeds=12500.0,
        sizing_pct=0.5,
        category="OVERWEIGHT_REDUCTION",
        priority="HIGH",
        evidence_summary="test",
        tax_bucket="C",
        tax_annotation="test",
        policy_type=None,
        blocked_by_policy=False,
        operator_review_required=False,
        reduction_score=88.4 if populated else 0.0,
        reduction_reason="Overweight reduction" if populated else "",
        policy_alignment_reason="Concentrated-alpha rotation" if populated else "",
    )

    target = RotationDeploymentTarget(
        rank=1,
        symbol="ARW",
        deployment_score=90.0,
        allocation_node="EQUITIES.US.LARGE",
        narrative_tier="HIGH_CONVICTION_ANCHOR",
        current_weight_pct=2.3,
        market_value=14000.0,
        suggested_amount=12500.0,
        suggested_pct_add=1.2,
        projected_weight_pct=3.5,
        score_breakdown={"signal": 24.0},
        headroom_pct=20.0,
        allocation_note="test",
        funding_source_symbol="MSFT" if populated else "",
        funding_source_category="OVERWEIGHT_REDUCTION" if populated else "",
        funding_source_score=88.4 if populated else 0.0,
        funding_source_reason="Top policy-aware source" if populated else "",
        funding_source_alternatives=["AAPL (TRIM CANDIDATE, score 77.0)"] if populated else [],
        funding_policy_alignment_reason="Policy aligned" if populated else "",
    )

    impact = PortfolioImpactEstimate(
        alignment_score_before=0.40,
        alignment_score_after=0.45,
        alignment_delta=0.05,
        concentration_before=30.0,
        concentration_after=29.2,
        concentration_delta=-0.8,
        overweight_nodes_before=["EQUITIES.US.LARGE"],
        overweight_nodes_after=[],
        newly_underweight_nodes=[],
        impact_narrative="test",
    )

    return RotationProposal(
        proposal_id="CRA-API-TEST",
        run_id="PAR-API-TEST",
        as_of_date="2026-06-14",
        portfolio_mv=150000.0,
        total_capital_pool=12500.0,
        sources=[source],
        deployments=[target],
        impact=impact,
        proposal_status="READY",
        review_flags=[],
        created_at_utc="2026-06-14T00:00:00+00:00",
    )


def _fetch_cra_payload(proposal: RotationProposal) -> dict:
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with patch(
            "src.portfolio.cra.rotation_proposal_builder.build_proposal_from_manifest",
            return_value=proposal,
        ):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/cra/proposal", timeout=5) as resp:
                assert resp.status == 200
                return json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_cra_api_payload_includes_source_contract_fields():
    payload = _fetch_cra_payload(_proposal(populated=True))
    source = payload["sources"][0]

    assert source["symbol"] == "MSFT"
    assert source["reduction_score"] == 88.4
    assert source["reduction_reason"] == "Overweight reduction"
    assert source["policy_alignment_reason"] == "Concentrated-alpha rotation"


def test_cra_api_payload_includes_target_contract_fields():
    payload = _fetch_cra_payload(_proposal(populated=True))
    target = payload["deployments"][0]

    assert target["symbol"] == "ARW"
    assert target["funding_source_symbol"] == "MSFT"
    assert target["funding_source_category"] == "OVERWEIGHT_REDUCTION"
    assert target["funding_source_score"] == 88.4
    assert target["funding_source_reason"] == "Top policy-aware source"
    assert target["funding_source_alternatives"] == ["AAPL (TRIM CANDIDATE, score 77.0)"]
    assert target["funding_policy_alignment_reason"] == "Policy aligned"


def test_cra_api_payload_preserves_empty_field_contracts():
    payload = _fetch_cra_payload(_proposal(populated=False))
    source = payload["sources"][0]
    target = payload["deployments"][0]

    assert source["reduction_score"] == 0.0
    assert source["reduction_reason"] == ""
    assert source["policy_alignment_reason"] == ""

    assert target["funding_source_symbol"] == ""
    assert target["funding_source_category"] == ""
    assert target["funding_source_score"] == 0.0
    assert target["funding_source_reason"] == ""
    assert target["funding_source_alternatives"] == []
    assert target["funding_policy_alignment_reason"] == ""
