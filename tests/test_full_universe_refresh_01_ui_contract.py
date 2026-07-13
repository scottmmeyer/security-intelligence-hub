from __future__ import annotations

from pathlib import Path


def test_outcome_visualization_refresh_labels_and_payload_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "ui" / "outcome_visualization" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")

    assert "Refresh Current Holdings Only" in index_html
    assert "Refresh Current Holdings + Buy Candidates" in index_html
    assert "Refresh Full Research Universe (~2,473 symbols)" in index_html

    assert 'intent: mode' in app_js
    assert 'requested_by: "operator"' in app_js
    assert 'source: "outcome_visualization"' in app_js
    assert "window.confirm(\"This will refresh approximately 2,473 research-universe symbols. Historical snapshots and trend history will be retained." in app_js
    assert "_refreshModeLabel(mode)" in app_js
    assert "completed_count ?? info.with_data_count" in app_js
    assert "planned_total_count" in app_js
    assert "rows processed" in app_js
    assert "Today written rows:" in app_js
    assert "holdings_plus_buy_candidates" in app_js
    assert "plus mandatory dependencies and market-regime proxies" in app_js
    assert "plus mandatory provider dependencies and market-regime proxy symbols" in app_js
    assert "stale provider rows +" in app_js
    assert "Planned refresh scope:" in app_js
