"""ZERO-NAN-AUDIT-01 API contract test for /api/portfolio/analyze."""

from __future__ import annotations

import json
import socket
import threading
import urllib.request
from contextlib import closing
from unittest.mock import patch

from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _fake_analysis_payload() -> dict:
    return {
        "status": "COMPLETE",
        "run_id": "PAR-TEST-ZERO-NAN",
        "recommendations": [
            {"recommendation_id": "R1", "ranking": 1, "score": 91.2, "affected_node_key": "EQUITIES.US"},
            {"recommendation_id": "R2", "ranking": 2, "score": 88.4, "affected_node_key": "COMMODITIES"},
        ],
        "alignment": [
            {"node_key": "EQUITIES.US", "target_pct": 40.0, "effective_actual_pct": 40.0, "drift_pct": 0.0}
        ],
        "portfolio_compliance": {"overall_status": "PASS"},
        "deployment_queue": {
            "queue": [
                {"rank": 1, "symbol": "MSFT", "deployment_score": 95.0},
                {"rank": 2, "symbol": "ARW", "deployment_score": 90.0},
            ]
        },
        "dislocation_by_symbol": {"MSFT": {"status": "NONE"}},
        "zero_nan_audit": {
            "status": "REVIEW",
            "suspicious_zero_count": 3,
            "nan_count": 2,
            "null_rendered_as_zero_count": 0,
            "divide_by_zero_count": 0,
            "tiny_rounded_to_zero_count": 1,
            "examples": [
                {"surface": "alignment", "field": "target_pct", "classification": "missing"}
            ],
        },
    }


def _post_analyze(*, payload: dict, mocked_result: dict) -> dict:
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/portfolio/analyze",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch("src.portfolio.runner.run_analysis", return_value=mocked_result):
            with patch("scripts.run_outcome_ui._attach_explanations", side_effect=lambda r: r):
                with urllib.request.urlopen(req, timeout=30) as resp:
                    assert resp.status == 200
                    return json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_portfolio_analyze_includes_zero_nan_audit_and_preserves_core_outputs() -> None:
    request_payload = {
        "portfolio_csv": "symbol,quantity,market_value\nMSFT,10,4500\n",
        "source_filename": "contract.csv",
        "snapshot_date": "2026-06-27",
        "mandate_type": "CONCENTRATED_ALPHA",
    }
    baseline = _fake_analysis_payload()
    result = _post_analyze(payload=request_payload, mocked_result=baseline)

    # zero_nan_audit required contract keys
    audit = result.get("zero_nan_audit")
    assert isinstance(audit, dict)
    for key in (
        "status",
        "suspicious_zero_count",
        "nan_count",
        "null_rendered_as_zero_count",
        "divide_by_zero_count",
        "tiny_rounded_to_zero_count",
        "examples",
    ):
        assert key in audit, f"missing zero_nan_audit field: {key}"

    # additive-only guard: existing core outputs are preserved
    assert result["recommendations"] == baseline["recommendations"]
    assert result["alignment"] == baseline["alignment"]
    assert result["portfolio_compliance"] == baseline["portfolio_compliance"]
    assert result["deployment_queue"] == baseline["deployment_queue"]
    assert result["dislocation_by_symbol"] == baseline["dislocation_by_symbol"]
