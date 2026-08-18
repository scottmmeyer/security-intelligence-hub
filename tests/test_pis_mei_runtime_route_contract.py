from __future__ import annotations

import io
import re
from pathlib import Path

import scripts.run_outcome_ui as runtime


_REQUIRED_ENDPOINTS = {
    "/api/pis/snapshots",
    "/api/pis/summary",
    "/api/pis/latest",
    "/api/pis/health",
    "/api/pis/lineage/latest",
    "/api/mei/events",
    "/api/mei/events/summary",
}


def _extract_dashboard_endpoints() -> set[str]:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")
    matches = re.findall(r'"(/api/(?:pis|mei)[^"]+)"', app_js)
    return set(matches)


def test_required_pis_mei_runtime_routes_are_mounted() -> None:
    mounted = runtime.PIS_DASHBOARD_API_ROUTES | runtime.MEI_DASHBOARD_API_ROUTES
    assert _REQUIRED_ENDPOINTS <= mounted


def test_all_literal_dashboard_endpoints_are_declared_in_runtime_contract() -> None:
    expected = _extract_dashboard_endpoints()
    mounted = runtime.PIS_DASHBOARD_API_ROUTES | runtime.MEI_DASHBOARD_API_ROUTES
    missing = sorted(expected - mounted)
    assert not missing, f"Missing runtime route declarations for dashboard endpoints: {missing}"


def test_representative_dispatchers_return_json_payloads() -> None:
    pis_payload = runtime._resolve_pis_dashboard_payload("/api/pis/summary")
    assert isinstance(pis_payload, dict)
    assert "timeline" in pis_payload

    mei_payload = runtime._resolve_mei_dashboard_payload("/api/mei/events/summary", "")
    assert isinstance(mei_payload, dict)
    assert "as_of_date" in mei_payload


def test_head_requests_are_accepted_for_dashboard_routes() -> None:
    handler = runtime._Handler.__new__(runtime._Handler)
    handler.path = "/api/pis/summary"
    handler.headers = {}
    handler.wfile = io.BytesIO()
    handler.command = "HEAD"
    handler.send_response = lambda status: None
    handler.send_header = lambda *args, **kwargs: None
    handler.end_headers = lambda: None

    handler.do_HEAD()

    assert handler.wfile.getvalue() == b""
