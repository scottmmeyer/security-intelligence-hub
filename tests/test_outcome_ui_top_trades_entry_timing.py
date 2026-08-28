from __future__ import annotations

import copy

from scripts import run_outcome_ui as outcome_ui


def test_enrich_top_trades_entry_timing_context_adds_per_symbol_fields_without_mutating_semantics(monkeypatch):
    run_payload = {
        "snapshot_date": "2026-08-27",
        "deployment_queue": {
            "queue": [
                {
                    "rank": 1,
                    "symbol": "DELL",
                    "deployment_score": 100.25,
                    "status": "DEPLOYABLE",
                    "eligibility": "ELIGIBLE",
                    "suggested_add": 1200.0,
                },
                {
                    "rank": 2,
                    "symbol": "SBS",
                    "deployment_score": 94.52,
                    "status": "DEPLOYABLE",
                    "eligibility": "ELIGIBLE",
                    "suggested_add": 800.0,
                },
            ]
        },
    }

    momentum_summary = {
        "snapshot_date": "2026-08-27",
        "entry_timing_context": {
            "holdings": [
                {
                    "symbol": "DELL",
                    "trend_structure_context": {
                        "latest_price_date": "2026-08-27",
                        "latest_price": 126.42,
                        "sma50": 121.7,
                        "price_vs_sma50_pct": 3.878389,
                        "sma200": 110.3,
                        "price_vs_sma200_pct": 14.614688,
                        "sma50_change_20d_pct": 1.2321,
                        "sma200_change_20d_pct": 0.4123,
                        "history_status": "AVAILABLE",
                        "currentness_state": "CURRENT",
                        "provenance": "src/pis/momentum_intelligence.py::build_trend_structure_context",
                    },
                },
                {
                    "symbol": "SBS",
                    "trend_structure_context": {
                        "latest_price_date": "2026-08-27",
                        "latest_price": 61.22,
                        "sma50": None,
                        "price_vs_sma50_pct": None,
                        "sma200": None,
                        "price_vs_sma200_pct": None,
                        "sma50_change_20d_pct": None,
                        "sma200_change_20d_pct": None,
                        "history_status": "INSUFFICIENT_50",
                        "currentness_state": "CURRENT",
                        "provenance": "src/pis/momentum_intelligence.py::build_trend_structure_context",
                    },
                },
            ]
        },
    }

    monkeypatch.setattr(outcome_ui, "_pis_momentum_summary_cached", lambda: momentum_summary)

    before = copy.deepcopy(run_payload)
    enriched = outcome_ui._enrich_top_trades_entry_timing_context(run_payload)

    assert run_payload == before
    assert enriched is not run_payload

    queue_before = before["deployment_queue"]["queue"]
    queue_after = enriched["deployment_queue"]["queue"]

    assert len(queue_after) == len(queue_before)
    for b, a in zip(queue_before, queue_after):
        assert a["rank"] == b["rank"]
        assert a["symbol"] == b["symbol"]
        assert a["deployment_score"] == b["deployment_score"]
        assert a["status"] == b["status"]
        assert a["eligibility"] == b["eligibility"]
        assert a["suggested_add"] == b["suggested_add"]

        ctx = a.get("entry_timing_context")
        assert isinstance(ctx, dict)
        assert ctx.get("reporting_only") is True
        assert "history_status" in ctx
        assert "currentness_state" in ctx
        assert "source" in ctx

    first_ctx = queue_after[0]["entry_timing_context"]
    assert first_ctx["history_status"] == "AVAILABLE"
    assert first_ctx["currentness_state"] == "CURRENT"
    assert first_ctx["latest_price_date"] == "2026-08-27"

    second_ctx = queue_after[1]["entry_timing_context"]
    assert second_ctx["history_status"] == "INSUFFICIENT_50"
    assert second_ctx["currentness_state"] == "CURRENT"


def test_enrich_top_trades_entry_timing_context_marks_unavailable_when_snapshot_mismatch(monkeypatch):
    run_payload = {
        "snapshot_date": "2026-08-26",
        "deployment_queue": {
            "queue": [
                {"rank": 1, "symbol": "DELL", "deployment_score": 100.25, "status": "DEPLOYABLE", "eligibility": "ELIGIBLE", "suggested_add": 1200.0}
            ]
        },
    }

    momentum_summary = {
        "snapshot_date": "2026-08-27",
        "entry_timing_context": {
            "holdings": [
                {
                    "symbol": "DELL",
                    "trend_structure_context": {
                        "history_status": "AVAILABLE",
                        "currentness_state": "CURRENT",
                    },
                }
            ]
        },
    }

    monkeypatch.setattr(outcome_ui, "_pis_momentum_summary_cached", lambda: momentum_summary)

    enriched = outcome_ui._enrich_top_trades_entry_timing_context(run_payload)
    ctx = enriched["deployment_queue"]["queue"][0]["entry_timing_context"]

    assert ctx["history_status"] == "UNAVAILABLE"
    assert ctx["currentness_state"] == "MISSING"
    assert "snapshot_mismatch" in ctx["source"]
    assert enriched["deployment_queue"]["entry_timing_context_meta"]["compatible"] is False
