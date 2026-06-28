from __future__ import annotations

from pathlib import Path


def test_hard_asset_sleeve_review_ui_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "Hard-Asset Sleeve Review" in app_js
    assert "Hard-Asset Sleeve Unfilled" in app_js
    assert "DISPLAY ONLY" in app_js
    assert "OPERATOR REVIEW" in app_js
    assert "NO AUTOMATIC RERANKING" in app_js
    assert "NO TRADE EXECUTION" in app_js
    assert "Continue equity deployment" in app_js
    assert "Deployable-cash-only hard-asset fill" in app_js
    assert "Split approach" in app_js
    assert "Reserve cash" in app_js
    assert "Waive commodity target" in app_js
    assert "Hard-Asset Priority Gate" in app_js
    assert "Display-only; not trade instructions." in app_js
    assert "Hard-Asset Candidate Queue" in app_js
    assert "NO CAPITAL DEPLOYMENT QUEUE CHANGES" in app_js
    assert "NO CRA CHANGES" in app_js
    assert "NO TRADE EXECUTION" in app_js
    assert "OPERATOR REVIEW REQUIRED" in app_js
    assert "PARTIAL_HARD_ASSET_FILL" in app_js
    assert "Review pressure score" in app_js
    assert "Display-only capital-allocation review score; not a trade-confidence score." in app_js
    assert "Direct hard-asset completion candidates" in app_js
    assert "Equity-adjacent proxies" in app_js
    assert "Priority bias: ${escHtml(String(priorityGate.priority_bias || \"—\"))}" in app_js
    assert "Derived client-side because the live summary did not include the gate payload." in app_js
    assert "Equity-Adjacent Proxies (Advisory)" in app_js
    assert "Gold Sleeve" in app_js
    assert "Energy Sleeve" in app_js
    assert "Broad Basket Sleeve" in app_js
    assert "GLD" in app_js
    assert "USO" in app_js
    assert "DBC" in app_js
    assert "Gold miner equity proxy" in app_js
    assert "Classified as EQUITIES; advisory only and not direct COMMODITIES fillers." in app_js
    assert "Sleeve Fit Drilldown" in app_js
    assert "Full target gap" in app_js
    assert "Deployable-cash-only" in app_js
    assert "Not a direct COMMODITIES.GOLD filler" in app_js
    assert "Display-only candidates; not trade instructions." in app_js
    assert "Today’s Operator Action Plan" in app_js
    assert "First decision" in app_js
    assert "If hard-asset-first" in app_js
    assert "If equity-first" in app_js
    assert "If raising capital" in app_js
    assert "Blocked / conflicts" in app_js
    assert "Display-only synthesis of existing diagnostics. This is not trade instructions." in app_js
    assert "Commodity candidates: ${commodityCandidatesAvailable ? \"Yes\" : \"No\"} (${directCompletionCount})" in app_js
    assert "x.full_target_amount ?? x.gap_amount_full_portfolio" in app_js
    assert "suggested_add" in app_js
    assert "not executable until policy state changes" in app_js
    assert "const directCompletionCandidateCount = queueNodes.reduce(" in app_js
    assert "? `Yes (${directCompletionCandidateCount} direct)`" in app_js
    assert "Commodity candidates available: <strong>${escHtml(commodityCandidatesLabel)}</strong><br>" in app_js
    assert "Commodity candidates available: <strong>${g.commodity_candidates_available === true ? \"Yes\" : g.commodity_candidates_available === false ? \"No\" : \"—\"}</strong><br>" not in app_js


def test_guardrail_payload_fallback_is_graceful() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "if (!commodityGuard && !fragilityWatch)" in app_js
    assert "Guardrail payload unavailable for this run" in app_js
    assert "_buildClientCandidateQueueFromGuard" in app_js
    assert "if (!hasQueueNodes && commodityGuard)" in app_js
    assert "_buildClientPriorityGate(commodityGuard, fragilityWatch, candidateQueue, signal)" in app_js
    assert "_buildClientTodayOperatorActionPlan(priorityGate, candidateQueue)" in app_js
    assert "_lastAnalysisData.deployment_queue.queue" in app_js
    assert "priorityGate && queueReady" in app_js
    assert "priority_verdict || priorityGate.verdict" in app_js
    assert "HARD_ASSET_REVIEW_FIRST" in app_js


def test_rotation_monitor_rendering_still_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "Rotation Risk Monitor" in app_js
    assert "_renderRotationRiskPanel" in app_js
    assert "loadRotationRiskSummary" in app_js
