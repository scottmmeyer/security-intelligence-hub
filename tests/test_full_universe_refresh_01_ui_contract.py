from __future__ import annotations

from pathlib import Path


def test_outcome_visualization_refresh_labels_and_payload_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "ui" / "outcome_visualization" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")

    assert "Refresh Current Holdings Only" in index_html
    assert "Refresh Full Research Universe (~2,473 symbols)" in index_html

    assert 'intent: mode' in app_js
    assert 'requested_by: "operator"' in app_js
    assert 'source: "outcome_visualization"' in app_js
    assert "window.confirm(\"This will refresh approximately 2,473 research-universe symbols. Historical snapshots and trend history will be retained." in app_js
    assert "_refreshModeLabel(mode)" in app_js
