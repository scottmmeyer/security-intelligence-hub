from __future__ import annotations

from pathlib import Path


def test_pis_dashboard_has_fail_open_section_diagnostics_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "function runSectionTask(sectionKey, requestFactory, onSuccess)" in app_js
    assert "console.error(`[PIS Dashboard] Section ${sectionKey} failed`" in app_js
    assert "sectionErrors[sectionKey] = error || new Error(\"Unknown section failure.\")" in app_js
    assert "Dashboard load outcome:" in app_js
    assert "Loaded with unavailable sections" in app_js
    assert "Loaded with warnings" in app_js
    assert "Section diagnostics" in app_js
    assert "Endpoint: ${error.requestPath}." in app_js


def test_pis_dashboard_request_timeout_and_error_context_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "const REQUEST_TIMEOUT_MS = 12000;" in app_js
    assert "timeoutError.requestPath = path;" in app_js
    assert "httpError.requestPath = path;" in app_js
    assert "Invalid JSON response from ${path}" in app_js
    assert "Request timed out while waiting for the server." in app_js
