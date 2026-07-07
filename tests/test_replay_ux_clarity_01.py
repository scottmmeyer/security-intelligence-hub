from __future__ import annotations

from pathlib import Path


def test_forward_backtest_panel_uses_historical_validation_labels() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")

    assert "Historical replay validation" in app_js
    assert "Historical score date" in app_js
    assert "Historical measurement window" in app_js
    assert "Replay freshness:" in app_js
    assert "replay_age_days" in app_js
    assert "replay_freshness_label" in app_js
    assert "replay_freshness_warning" in app_js


def test_status_label_no_longer_uses_current_badge() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")

    assert "[CURRENT]" not in app_js
    assert "[SELECTED REPLAY]" in app_js
    assert "[FORWARD BACKTEST HISTORICAL]" in app_js
    assert "Selected replay artifact render" in app_js


def test_replay_context_heading_clarifies_historical_artifact() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "ui" / "outcome_visualization" / "index.html").read_text(encoding="utf-8")

    assert "Replay Context (Historical Validation Artifact)" in index_html
    assert "selected historical replay window used for model validation" in index_html
    assert "not the current portfolio evaluation date" in index_html
