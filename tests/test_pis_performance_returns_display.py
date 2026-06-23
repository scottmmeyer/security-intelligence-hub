from __future__ import annotations

from pathlib import Path


def test_pis_dashboard_performance_returns_card_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    pis_html = (root / "ui" / "pis_dashboard" / "index.html").read_text(encoding="utf-8")
    pis_app = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "Performance Returns (Snapshot-Based)" in pis_html
    assert "performanceReturnsCard" in pis_html

    assert "function renderPerformanceReturnsCard()" in pis_app
    assert "Latest Portfolio Value" in pis_app
    assert "Start Value (first snapshot)" in pis_app
    assert "Absolute Gain/Loss" in pis_app
    assert "Total Return" in pis_app
    assert "1D Return" in pis_app
    assert "5D Return" in pis_app
    assert "1M Return" in pis_app
    assert "Since Inception Return" in pis_app
    assert "Benchmark Comparison (excess)" in pis_app
    assert "Snapshot-based estimate (cash-flow-unadjusted)" in pis_app
    assert "Unavailable / validation pending" in pis_app
    assert "external cash flows have not yet been fully reconciled" in pis_app
