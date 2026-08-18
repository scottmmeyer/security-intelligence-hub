from __future__ import annotations

import json
import re
import socket
import threading
import urllib.error
import urllib.request
from contextlib import ExitStack, closing
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from playwright.sync_api import sync_playwright

from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer


REPO_ROOT = Path(__file__).resolve().parents[1]
CHROME_EXECUTABLE = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _request(path: str, method: str = "GET", patchers: list | None = None) -> tuple[int, dict[str, str], bytes]:
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with ExitStack() as stack:
            for p in patchers or []:
                stack.enter_context(p)
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return int(resp.status), dict(resp.headers.items()), resp.read()
            except urllib.error.HTTPError as exc:
                return int(exc.code), dict(exc.headers.items()), exc.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _write_manifest(repo: Path, portfolios: list[dict]) -> None:
    manifest_path = repo / "data" / "portfolio_ingestion" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"portfolios": portfolios}), encoding="utf-8")


@contextmanager
def _serve_allocation_page(
    route_specs: list[tuple[str, object, int]],
    *,
    path: str = "/ui/allocation_intelligence/?validation=allocation-readpath-final",
    wait_script: str = "() => document.body && document.body.innerText.includes('NOT EVALUATED')",
):
    if not CHROME_EXECUTABLE.exists():
        pytest.skip("Google Chrome is not installed at the expected path for browser validation")

    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), partial(_Handler, directory=str(REPO_ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    request_urls: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=str(CHROME_EXECUTABLE),
                args=["--disable-dev-shm-usage"],
            )
            context = browser.new_context()
            try:
                page = context.new_page()
                page.on("request", lambda request: request_urls.append(request.url))

                for pattern, payload, status in route_specs:
                    def _handler(route, request, _payload=payload, _status=status):
                        route.fulfill(
                            status=_status,
                            content_type="application/json",
                            body=json.dumps(_payload),
                        )

                    page.route(re.compile(pattern), _handler)

                page.goto(f"http://127.0.0.1:{port}{path}", wait_until="domcontentloaded")
                page.wait_for_function(wait_script, timeout=15000)
                yield page, request_urls
            finally:
                context.close()
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_cpv_latest_get_returns_persisted_compliance_payload() -> None:
    with TemporaryDirectory() as tmp:
        repo = Path(tmp)
        run_id = "PAR-TEST-0001"
        _write_manifest(
            repo,
            [{"run_id": run_id, "status": "COMPLETE", "snapshot_date": "2026-08-17"}],
        )
        compliance_path = repo / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "compliance.json"
        compliance_path.parent.mkdir(parents=True, exist_ok=True)
        expected = {
            "run_id": run_id,
            "snapshot_date": "2026-08-17",
            "overall_status": "WARN",
            "current_compliance_score": 75,
            "rules": [{"rule_id": "CPV-01", "status": "WARN"}],
        }
        compliance_path.write_text(json.dumps(expected), encoding="utf-8")

        status, headers, body = _request(
            "/api/cpv/latest",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", repo)],
        )

    assert status == 200
    assert headers.get("Content-Type") == "application/json"
    assert json.loads(body.decode("utf-8")) == expected


def test_cpv_latest_head_succeeds_without_body() -> None:
    with TemporaryDirectory() as tmp:
        repo = Path(tmp)
        run_id = "PAR-TEST-0002"
        _write_manifest(repo, [{"run_id": run_id, "status": "COMPLETE"}])
        compliance_path = repo / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "compliance.json"
        compliance_path.parent.mkdir(parents=True, exist_ok=True)
        compliance_path.write_text(json.dumps({"run_id": run_id, "rules": []}), encoding="utf-8")

        status, headers, body = _request(
            "/api/cpv/latest",
            method="HEAD",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", repo)],
        )

    assert status == 200
    assert headers.get("Content-Type") == "application/json"
    assert body == b""


def test_cpv_latest_missing_run_is_truthful_unavailable() -> None:
    with TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _write_manifest(repo, [])

        status, _headers, body = _request(
            "/api/cpv/latest",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", repo)],
        )

    payload = json.loads(body.decode("utf-8"))
    assert status == 404
    assert payload.get("reason") == "latest_run_missing"


def test_cpv_latest_missing_artifact_is_truthful_unavailable() -> None:
    with TemporaryDirectory() as tmp:
        repo = Path(tmp)
        run_id = "PAR-TEST-0003"
        _write_manifest(repo, [{"run_id": run_id, "status": "COMPLETE"}])

        status, _headers, body = _request(
            "/api/cpv/latest",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", repo)],
        )

    payload = json.loads(body.decode("utf-8"))
    assert status == 404
    assert payload.get("reason") == "compliance_artifact_missing"
    assert payload.get("run_id") == run_id


def test_drift_summary_get_uses_pa006a_provider_contract() -> None:
    expected = {
        "generated_at": "2026-08-17T00:00:00Z",
        "current_date": "2026-08-17",
        "prior_date": "2026-08-16",
        "dates_available": 2,
        "current_overall_status": "WARN",
        "current_compliance_score": 80,
        "cpv_trend": [{"rule_id": "CPV-01"}],
    }
    status, headers, body = _request(
        "/api/drift/summary",
        patchers=[patch("src.portfolio.drift_analyzer.compute_drift_summary", return_value=expected)],
    )

    assert status == 200
    assert headers.get("Content-Type") == "application/json"
    assert json.loads(body.decode("utf-8")) == expected


def test_drift_summary_head_succeeds_without_body() -> None:
    status, headers, body = _request("/api/drift/summary", method="HEAD")
    assert status == 200
    assert headers.get("Content-Type") == "application/json"
    assert body == b""


def test_drift_intelligence_summary_remains_separate_contract() -> None:
    status, headers, body = _request("/api/drift/intelligence-summary")
    payload = json.loads(body.decode("utf-8"))

    assert status == 200
    assert headers.get("Content-Type") == "application/json"
    assert "trend_counts" in payload
    assert "cpv_trend" not in payload


def test_allocation_frontend_supports_runs_envelope_and_legacy_array_path() -> None:
    app_js = Path("ui/allocation_intelligence/app.js").read_text(encoding="utf-8")
    assert "function normalizePortfolioRuns(payload)" in app_js
    assert "Array.isArray(payload.portfolios)" in app_js
    assert "const runsPayload = await fetchJson(\"/api/portfolio/runs\")" in app_js
    assert "const runs = normalizePortfolioRuns(runsPayload)" in app_js


def test_allocation_frontend_recalc_panel_never_infers_pass_without_validator_evidence() -> None:
    app_js = Path("ui/allocation_intelligence/app.js").read_text(encoding="utf-8")
    assert "const isValid = snapshots.length === 0" not in app_js
    assert "NOT_EVALUATED" in app_js
    assert "Validator evidence unavailable in snapshot artifact." in app_js
    assert "validatorStatuses[v].status === \"PASS\"" in app_js


def test_allocation_frontend_strategic_micro_combined_check_is_preserved() -> None:
    app_js = Path("ui/allocation_intelligence/app.js").read_text(encoding="utf-8")
    assert "Micro Cap combined — strategic target" in app_js
    assert "targets.filter(t => t.node_key.includes(\"MICRO\"))" in app_js
    assert "ceiling: sp.max_micro_cap_pct ?? 5" in app_js


def test_allocation_page_renders_current_portfolio_when_run_detail_and_cpv_exist() -> None:
    current_run_id = "PAR-20260817-40E00509"
    run_list = {
        "portfolios": [
            {
                "run_id": current_run_id,
                "status": "COMPLETE",
                "snapshot_date": "2026-08-17",
                "holding_count": 77,
                "total_market_value": 482570.32999999984,
            }
        ]
    }
    run_detail = {
        "run_id": current_run_id,
        "alignment": [
            {"node_key": f"NODE.{idx}", "actual_pct": 1.0}
            for idx in range(39)
        ],
    }
    manifest = {"latest_recalculation_id": "RECALC-20260817-01", "history": []}
    cpv_payload = {
        "run_id": current_run_id,
        "overall_status": "FAIL",
        "compliance_score": 65,
        "violation_count": 2,
        "advisory_count": 0,
        "warn_count": 1,
        "fail_count": 1,
        "generated_at_utc": "2026-08-17T00:00:00Z",
        "rules": [],
    }

    with _serve_allocation_page([
        (r".*/api/portfolio/runs$", run_list, 200),
        (rf".*/api/portfolio/runs/{re.escape(current_run_id)}$", run_detail, 200),
        (r".*/api/cpv/latest$", cpv_payload, 200),
        (r".*/data/allocation/manifest\.json$", manifest, 200),
        (r".*/api/drift/summary$", {"cpv_trend": [], "current_date": "2026-08-17", "current_compliance_score": 65}, 200),
    ], wait_script="() => document.body && document.body.innerText.includes('Current Portfolio Allocation')") as (page, requests):
        body_text = page.locator("body").inner_text()
        assert any(url.endswith(f"/api/portfolio/runs/{current_run_id}") for url in requests)
        assert page.locator("#section-portfolio-compliance").is_visible()
        assert "No portfolio analysis available. Upload a portfolio to see current allocation compliance." not in body_text
        assert "Current Portfolio Allocation" in body_text
        assert "Current Portfolio Compliance" in body_text


def test_allocation_page_keeps_current_portfolio_visible_when_cpv_is_unavailable() -> None:
    current_run_id = "PAR-20260817-40E00509"
    run_list = {
        "portfolios": [
            {
                "run_id": current_run_id,
                "status": "COMPLETE",
                "snapshot_date": "2026-08-17",
                "holding_count": 77,
                "total_market_value": 482570.32999999984,
            }
        ]
    }
    run_detail = {
        "run_id": current_run_id,
        "alignment": [
            {"node_key": f"NODE.{idx}", "actual_pct": 1.0}
            for idx in range(39)
        ],
    }
    unavailable_cpv = {
        "status": "unavailable",
        "reason": "compliance_artifact_missing",
        "message": "Compliance artifact is unavailable for the latest completed run.",
        "run_id": current_run_id,
    }
    manifest = {"latest_recalculation_id": "RECALC-20260817-01", "history": []}

    with _serve_allocation_page([
        (r".*/api/portfolio/runs$", run_list, 200),
        (rf".*/api/portfolio/runs/{re.escape(current_run_id)}$", run_detail, 200),
        (r".*/api/cpv/latest$", unavailable_cpv, 404),
        (r".*/data/allocation/manifest\.json$", manifest, 200),
        (r".*/api/drift/summary$", {"cpv_trend": [], "current_date": "2026-08-17", "current_compliance_score": 65}, 200),
    ], wait_script="() => document.body && document.body.innerText.includes('Current Portfolio Allocation')") as (page, _requests):
        body_text = page.locator("body").inner_text()
        assert "No portfolio analysis available. Upload a portfolio to see current allocation compliance." not in body_text
        assert "Current Portfolio Allocation" in body_text
        assert "Current Portfolio Compliance" in body_text


def test_allocation_page_renders_validator_evidence_and_unavailable_states() -> None:
    manifest = {
        "latest_recalculation_id": "RECALC-20260817-01",
        "latest_recalculation_date": "2026-08-17",
        "total_snapshots": 1,
        "updated_at_utc": "2026-08-17T00:00:00Z",
        "history": [{"recalculation_id": "RECALC-20260817-01"}],
    }
    snapshot_without_evidence = {
        "recalculation_id": "RECALC-20260817-01",
        "change_summary": ["No validator payload present in snapshot artifact."],
    }
    snapshot_with_evidence = {
        "recalculation_id": "RECALC-20260817-01",
        "change_summary": ["Validator payload present."],
        "validator_results": {
            "hierarchy_sums": {"status": "PASS"},
            "policy_bounds": {"status": "PASS"},
            "tactical_overflow": {"status": "PASS"},
            "overlay_staleness": {"status": "PASS"},
            "recalculation_churn": {"status": "PASS"},
            "evidence_alignment": {"status": "PASS"},
            "concentration_ceilings": {"status": "FAIL", "message": "Combined MICRO cap exposure breaches policy."},
            "lineage_completeness": {"status": "PASS"},
        },
    }

    with _serve_allocation_page([
        (r".*/data/allocation/manifest\.json$", manifest, 200),
        (r".*/data/allocation/recalculation_snapshots/RECALC-20260817-01\.json$", snapshot_without_evidence, 200),
    ], path="/ui/allocation_intelligence/?validation=allocation-readpath-validator-none", wait_script="() => document.body && document.body.innerText.includes('NOT EVALUATED')") as (page, _requests):
        body_text = page.locator("body").inner_text()
        assert "NOT EVALUATED" in body_text
        assert "policy bounds" in body_text
        assert "concentration ceilings" in body_text
        assert "Validator evidence unavailable in snapshot artifact." in body_text

    with _serve_allocation_page([
        (r".*/data/allocation/manifest\.json$", manifest, 200),
        (r".*/data/allocation/recalculation_snapshots/RECALC-20260817-01\.json$", snapshot_with_evidence, 200),
    ], path="/ui/allocation_intelligence/?validation=allocation-readpath-validator-evidence", wait_script="() => document.body && document.body.innerText.includes('PASS') && document.body.innerText.includes('FAIL')") as (page, _requests):
        body_text = page.locator("body").inner_text()
        assert "PASS" in body_text
        assert "FAIL" in body_text
        assert "concentration ceilings" in body_text
        assert "Combined MICRO cap exposure breaches policy." in body_text
