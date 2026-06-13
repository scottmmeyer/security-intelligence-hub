from __future__ import annotations

import csv
import json
from pathlib import Path

from src.sih.allocation_explainability import (
    EXPLANATION_HEADERS,
    SUMMARY_HEADERS,
    build_recommendation_explanation,
    explanation_for_recommendation,
    explanation_summary,
    explanations_for_run,
    explanations_latest,
    refresh_allocation_explanations,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _build_run(tmp_path: Path, run_id: str = "PAR-TEST-01") -> Path:
    run_dir = tmp_path / "analysis_runs" / run_id
    _write_json(
        run_dir / "run_metadata.json",
        {
            "run_id": run_id,
            "snapshot_date": "2026-06-13",
        },
    )
    _write_json(
        run_dir / "recommendations.json",
        [
            {
                "recommendation_id": "REC-1",
                "recommendation_type": "INCREASE_UNDERWEIGHT",
                "title": "Build US Mega allocation",
                "rationale": "Portfolio is underweight US Mega by 4.0pp. Increase exposure to align with target. Funding source: Excess Cash (SPAXX, ~6.5% available).",
                "evidence_summary": "Replay evidence available (2 replay(s) for this tier).",
                "severity": "HIGH",
                "drift_pct": -4.0,
                "replay_run_ids": ["R1", "R2"],
                "execution_state": "EXECUTABLE",
                "affected_symbols": ["VRT"],
                "mandate_urgency": "URGENT",
                "mandate_drift_label": "STANDARD_UNDERWEIGHT",
                "drilldown": {
                    "holdings": [
                        {
                            "symbol": "VRT",
                            "composite_score": 4.3,
                            "ess_score_text": "BULLISH",
                            "zacks_rating": "1",
                            "danelfin_score": "8.4",
                            "cw_das_score": 91.2,
                        }
                    ]
                },
            },
            {
                "recommendation_id": "REC-2",
                "recommendation_type": "TOP_TRIM_CANDIDATES",
                "title": "Trim semis cluster",
                "rationale": "The portfolio has redundant semiconductor overlap. Trimming concentrated names lowers concentration risk.",
                "evidence_summary": "Cluster concentration exceeds intended strategic weight.",
                "severity": "MODERATE",
                "execution_state": "DEFERRED_BY_POLICY",
                "affected_symbols": ["NVDA", "TSM"],
                "symbol_execution_states": {
                    "NVDA": {"execution_state": "DEFERRED_BY_POLICY", "effective_action": "TRIM_SELL_LAST", "policy_type": "SELL_LAST"},
                    "TSM": {"execution_state": "EXECUTABLE", "effective_action": "TRIM", "policy_type": ""},
                },
                "drilldown": {
                    "holdings": [
                        {
                            "symbol": "NVDA",
                            "composite_score": 2.2,
                            "ess_score_text": "BEARISH",
                            "zacks_rating": "4",
                            "danelfin_score": "3.1",
                        }
                    ]
                },
                "reasoning_trace": "Phase E.5 thematic trim cluster reasoning.",
            },
        ],
    )
    _write_json(
        run_dir / "analyst_consensus.json",
        {
            "VRT": {
                "consensus_label": "BUY",
                "price_target": 145.0,
                "abr": 1.8,
            }
        },
    )
    return run_dir


def test_build_recommendation_explanation_maps_policy_signal_and_funding(tmp_path: Path) -> None:
    run_dir = _build_run(tmp_path)
    recommendations = json.loads((run_dir / "recommendations.json").read_text(encoding="utf-8"))

    explanation = build_recommendation_explanation(recommendations[0], run_dir, "2026-06-13", "PAR-TEST-01")

    assert explanation["recommendation_id"] == "REC-1"
    assert explanation["primary_reason"].startswith("Portfolio is underweight US Mega")
    assert explanation["funding_drivers"][0]["source_type"] == "EXCESS_CASH"
    assert explanation["signal_drivers"][0]["source"] == "CW-DAS"
    assert any(row["source"] == "ESS" for row in explanation["signal_drivers"])
    assert any(row["source"] == "Zacks" for row in explanation["signal_drivers"])
    assert any(row["source"] == "Danelfin" for row in explanation["signal_drivers"])
    assert any(row["source"] == "Yahoo" for row in explanation["signal_drivers"])
    assert any(row["value"] == "STANDARD_UNDERWEIGHT" for row in explanation["policy_drivers"])
    assert explanation["philosophy_drivers"][0]["philosophy"] == "Cash Deployment"


def test_multiple_driver_recommendation_and_missing_funding_handled(tmp_path: Path) -> None:
    run_dir = _build_run(tmp_path)
    recommendations = json.loads((run_dir / "recommendations.json").read_text(encoding="utf-8"))

    explanation = build_recommendation_explanation(recommendations[1], run_dir, "2026-06-13", "PAR-TEST-01")

    assert explanation["funding_drivers"] == []
    assert any(row["driver_type"] == "symbol_policy" for row in explanation["policy_drivers"])
    assert len(explanation["philosophy_drivers"]) >= 2
    assert explanation["supporting_reasons"][-1] == "Severity: MODERATE"


def test_refresh_and_api_payloads(tmp_path: Path) -> None:
    _build_run(tmp_path)
    output_root = tmp_path / "history" / "explanations"

    refresh_allocation_explanations(
        analysis_runs_root=tmp_path / "analysis_runs",
        output_root=output_root,
    )

    with (output_root / "recommendation_explanations.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == EXPLANATION_HEADERS
    with (output_root / "explanation_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == SUMMARY_HEADERS

    latest = explanations_latest(
        analysis_runs_root=tmp_path / "analysis_runs",
        output_root=output_root,
    )
    assert latest["analysis_run_id"] == "PAR-TEST-01"
    assert len(latest["explanations"]) == 2

    single = explanation_for_recommendation(
        "REC-2",
        analysis_runs_root=tmp_path / "analysis_runs",
        output_root=output_root,
    )
    assert single["explanation"]["recommendation_type"] == "TOP_TRIM_CANDIDATES"

    summary = explanation_summary(
        analysis_runs_root=tmp_path / "analysis_runs",
        output_root=output_root,
    )
    assert summary["history"][0]["recommendation_count"] == 2
    assert summary["history"][0]["funding_driver_count"] == 1
    assert summary["source_summary"]["PAP"] == 2

    by_run = explanations_for_run(
        "PAR-TEST-01",
        analysis_runs_root=tmp_path / "analysis_runs",
        output_root=output_root,
    )
    assert set(by_run.keys()) == {"REC-1", "REC-2"}
