"""ZERO-NAN-AUDIT-01 display-only diagnostics tests.

These tests validate additive audit behavior only. They must never exercise or
assert any scoring/recommendation/allocation mutation.
"""

from __future__ import annotations

from src.portfolio.runner import (
    _audit_numeric_surface,
    _build_zero_nan_audit,
    _classify_numeric_display_value,
)


def test_classify_none_as_missing() -> None:
    cls, n = _classify_numeric_display_value(None)
    assert cls == "missing"
    assert n is None


def test_classify_empty_string_as_missing() -> None:
    cls, n = _classify_numeric_display_value("   ")
    assert cls == "missing"
    assert n is None


def test_classify_nan_as_invalid() -> None:
    cls, n = _classify_numeric_display_value(float("nan"))
    assert cls == "invalid"
    assert n is None


def test_classify_inf_as_invalid() -> None:
    cls, n = _classify_numeric_display_value(float("inf"))
    assert cls == "invalid"
    assert n is None


def test_classify_zero_as_zero() -> None:
    cls, n = _classify_numeric_display_value(0)
    assert cls == "zero"
    assert n == 0.0


def test_classify_finite_nonzero_value() -> None:
    cls, n = _classify_numeric_display_value("1.25")
    assert cls == "value"
    assert n == 1.25


def test_audit_surface_counts_tiny_nonzero_and_missing() -> None:
    counts, examples = _audit_numeric_surface(
        surface="alignment",
        rows=[
            {"node_key": "COMMODITIES", "target_pct": None, "actual_pct": 0.05},
            {"node_key": "CASH", "target_pct": 7.0, "actual_pct": 0.0},
        ],
        fields=["target_pct", "actual_pct"],
        id_fields=("node_key",),
    )
    assert counts["inspected_values"] == 4
    assert counts["missing_count"] == 1
    assert counts["tiny_nonzero_count"] == 1
    assert any(e["classification"] == "tiny_nonzero" for e in examples)


def test_audit_payload_status_review_when_invalid_present() -> None:
    payload = _build_zero_nan_audit(
        alignment_rows=[{"node_key": "EQUITIES", "target_pct": "nan", "actual_pct": 12.0}],
        overlays=[{"symbol": "AAPL", "percent_of_portfolio": 3.2}],
        deployment_queue_payload={"queue": [], "cash_context": {}},
    )
    assert payload["audit_id"] == "ZERO-NAN-AUDIT-01"
    assert payload["display_only"] is True
    assert payload["status"] == "REVIEW"
    assert payload["suspicious_counts"]["invalid_numeric_values"] >= 1


def test_audit_payload_status_ok_when_clean() -> None:
    payload = _build_zero_nan_audit(
        alignment_rows=[
            {
                "node_key": "EQUITIES",
                "direct_actual_pct": 5.0,
                "etf_derived_actual_pct": 2.0,
                "effective_actual_pct": 7.0,
                "actual_pct": 7.0,
                "target_pct": 7.0,
                "drift_pct": 0.0,
            }
        ],
        overlays=[
            {
                "symbol": "MSFT",
                "percent_of_portfolio": 2.5,
                "composite_score": 4.1,
                "zacks_rating": 3.0,
                "danelfin_score": 3.5,
            }
        ],
        deployment_queue_payload={
            "queue": [
                {
                    "symbol": "MSFT",
                    "allocation_node": "EQUITIES.US.LARGE",
                    "deployment_score": 88.0,
                        "projected_weight_pct": 0.3,
                    "suggested_add": 1000.0,
                    "trim_score": 0.0,
                }
            ],
            "cash_context": {
                "cash_mv": 10000.0,
                "deployable_mv": 5000.0,
                "adjusted_deployable_mv": 5000.0,
                "adjusted_deployable_pct": 1.1,
            },
        },
    )
    assert payload["status"] == "OK"
    assert payload["suspicious_counts"]["invalid_numeric_values"] == 0
    assert payload["suspicious_counts"]["tiny_nonzero_values_lt_0_1"] == 0


def test_audit_payload_contains_surface_breakdown_and_examples() -> None:
    payload = _build_zero_nan_audit(
        alignment_rows=[{"node_key": "COMMODITIES", "target_pct": None, "actual_pct": 0.01}],
        overlays=[{"symbol": "TSLA", "percent_of_portfolio": float("inf")}],
        deployment_queue_payload={"queue": [], "cash_context": {}},
    )
    assert "alignment" in payload["surfaces"]
    assert "security_overlays" in payload["surfaces"]
    assert "deployment_queue" in payload["surfaces"]
    assert "deployment_cash_context" in payload["surfaces"]
    assert isinstance(payload["examples"], list)
    assert payload["examples"], "expected at least one example for suspicious inputs"
