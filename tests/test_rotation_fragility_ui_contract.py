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
    assert "Continue with equity deployment" in app_js
    assert "Fill hard-asset sleeve" in app_js


def test_guardrail_payload_fallback_is_graceful() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "if (!commodityGuard && !fragilityWatch)" in app_js
    assert "Guardrail payload unavailable for this run" in app_js


def test_rotation_monitor_rendering_still_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "Rotation Risk Monitor" in app_js
    assert "_renderRotationRiskPanel" in app_js
    assert "loadRotationRiskSummary" in app_js
