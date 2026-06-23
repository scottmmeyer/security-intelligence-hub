from __future__ import annotations

from pathlib import Path


def test_pis_dashboard_boot_path_and_build_markers_present() -> None:
    root = Path(__file__).resolve().parents[1]
    pis_html = (root / "ui" / "pis_dashboard" / "index.html").read_text(encoding="utf-8")
    pis_app = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "PIS_BUILD_HTML=2026-06-23-runtime-01" in pis_html
    assert "id=\"pisBuildMarkerHtml\"" in pis_html
    assert 'script src="app.js?v=2026-06-23-runtime-01"' in pis_html

    assert 'const PIS_BUILD_JS = "2026-06-23-runtime-01";' in pis_app
    assert 'window.__PIS_BUILD_JS__ = PIS_BUILD_JS;' in pis_app
    assert 'console.log("[PIS_BOOT] app.js loaded"' in pis_app


def test_pis_dashboard_bootstrap_guard_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]
    pis_app = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "function bootstrapDashboard()" in pis_app
    assert "renderStartupFailure(error);" in pis_app
    assert "Dashboard failed during startup" in pis_app
    assert "Startup Failure Diagnostics" in pis_app
    assert "DOMContentLoaded" in pis_app
    assert "if (document.readyState === \"loading\")" in pis_app
    assert "sectionsPlanned" in pis_app
