from __future__ import annotations

from pathlib import Path


def test_hard_asset_sleeve_review_ui_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "Hard-Asset Sleeve Review" in app_js
    assert "Hard-Asset Priority Gate" in app_js
    assert "Hard-Asset Candidate Queue" in app_js
    assert "Today’s Operator Action Plan" in app_js
    assert "NO CAPITAL DEPLOYMENT QUEUE CHANGES" in app_js
    assert "NO CRA CHANGES" in app_js
    assert "NO TRADE EXECUTION" in app_js
    assert "Sleeve Fit Drilldown" in app_js
    assert "Equity-Adjacent Proxies" in app_js
    assert "_buildClientTodayOperatorActionPlan" in app_js
    assert "_buildClientPriorityGate" in app_js
    assert "_buildClientCandidateQueueFromGuard" in app_js


def test_guardrail_payload_fallback_is_graceful() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "if (!commodityGuard && !fragilityWatch)" in app_js
    assert "Guardrail payload unavailable" in app_js
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


def test_cra_degraded_state_ui_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "function renderReductionQueueUnavailable(message, reason)" in app_js
    assert "CRA unavailable - capital source data not loaded." in app_js
    assert "renderReductionQueueUnavailable(msg, reason);" in app_js
    assert "renderReductionQueueUnavailable(msg, \"fetch_exception\");" in app_js
    assert "reason: \"non_json_response\"" in app_js
    assert "const err = await resp.json().catch(() => ({ error: \"Network error\" }));" not in app_js


def test_outcome_visualization_hard_asset_priority_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")
    index_html = (root / "ui" / "outcome_visualization" / "index.html").read_text(encoding="utf-8")

    assert "Portfolio Operator Priorities" in index_html
    assert "loadLatestPortfolioActionPanel();" in index_html
    assert "Today’s Operator Action Plan" in app_js
    assert "Hard-Asset Priority Gate" in app_js
    assert "Hard-Asset Sleeve Review" in app_js
    assert "Hard-Asset Candidate Queue" in app_js
    assert "Sleeve Fit Drilldown" in app_js
    assert "Capital Deployment Queue" in app_js
