"""Regression tests for PA-006A — Allocation Drift Analyzer.

Covers:
  1. Canonical date selection (latest PAR per date)
  2. Trend direction — ceiling rule, WORSENING
  3. Trend direction — ceiling rule, IMPROVING
  4. Trend direction — floor rule, WORSENING
  5. Trend direction — floor rule, IMPROVING
  6. Empty history handling
  7. Single-date handling (no prior, no delta)
  8. API payload contract (required keys present)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.portfolio.drift_analyzer import (
    _cpv_status,
    _trend_direction,
    compute_drift_summary,
    compute_drift_timeline,
)


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _make_compliance(
    tmp_par_dir: Path,
    par_name: str,
    snapshot_date: str,
    created_at: str,
    rules: dict[str, float],
    overall: str = "WARN",
    score: int = 80,
) -> None:
    """Write run_metadata.json + compliance.json for a fake PAR run."""
    par_path = tmp_par_dir / par_name
    par_path.mkdir(parents=True, exist_ok=True)

    meta = {
        "run_id": par_name,
        "snapshot_date": snapshot_date,
        "created_at_utc": created_at,
        "status": "COMPLETE",
    }
    (par_path / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    rule_list = []
    for rid, pct in rules.items():
        from src.portfolio.drift_analyzer import _cpv_status
        status, breach = _cpv_status(rid, pct)
        rule_list.append({
            "rule_id": rid,
            "actual_pct": pct,
            "status": status,
            "breach_pp": breach,
        })

    cpv = {
        "run_id": par_name,
        "snapshot_date": snapshot_date,
        "overall_status": overall,
        "compliance_score": score,
        "rules": rule_list,
    }
    (par_path / "compliance.json").write_text(json.dumps(cpv), encoding="utf-8")


def _fake_repo(tmp_path: Path, runs: list[dict]) -> Path:
    """Build a minimal fake repo structure under tmp_path."""
    par_dir = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs"
    par_dir.mkdir(parents=True)
    for r in runs:
        _make_compliance(
            par_dir,
            par_name=r["par"],
            snapshot_date=r["date"],
            created_at=r.get("created_at", r["date"] + "T12:00:00"),
            rules=r["rules"],
            overall=r.get("overall", "OK"),
            score=r.get("score", 100),
        )
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests: _cpv_status
# ---------------------------------------------------------------------------

def test_cpv_status_ceiling_ok():
    status, breach = _cpv_status("CPV-01", 4.0)
    assert status == "OK"
    assert breach == 0.0


def test_cpv_status_ceiling_advisory():
    # CPV-01 advisory_pp=2.0; breach=2.0 is right at advisory → ADVISORY
    status, breach = _cpv_status("CPV-01", 7.0)
    assert status == "ADVISORY"
    assert round(breach, 4) == 2.0


def test_cpv_status_ceiling_warn():
    # CPV-01 warn_pp=4.0; breach=3.5 → WARN
    status, breach = _cpv_status("CPV-01", 8.5)
    assert status == "WARN"
    assert round(breach, 4) == 3.5


def test_cpv_status_ceiling_fail():
    # CPV-01 warn_pp=4.0; breach=4.52 → FAIL
    status, breach = _cpv_status("CPV-01", 9.52)
    assert status == "FAIL"
    assert round(breach, 1) == 4.5


def test_cpv_status_floor_ok():
    status, breach = _cpv_status("CPV-04", 10.0)
    assert status == "OK"
    assert breach == 0.0


def test_cpv_status_floor_fail():
    # CPV-04 cash floor = 2%; actual = 0%, breach = 2.0; warn_pp=2.0
    # breach == warn_pp → WARN (FAIL requires breach > warn_pp)
    status, breach = _cpv_status("CPV-04", 0.0)
    assert status == "WARN"
    assert round(breach, 4) == 2.0


def test_cpv_status_floor_fail_strict():
    # CPV-04: actual = -0.01% (impossible but tests strict FAIL boundary)
    # breach = 2.01 > warn_pp 2.0 → FAIL
    status, breach = _cpv_status("CPV-04", -0.1)
    assert status == "FAIL"


# ---------------------------------------------------------------------------
# Unit tests: _trend_direction
# ---------------------------------------------------------------------------

def test_trend_ceiling_worsening():
    # CPV-01 is ceiling; rising metric = WORSENING
    assert _trend_direction("CPV-01", +1.5) == "WORSENING"


def test_trend_ceiling_improving():
    # CPV-01 is ceiling; falling metric = IMPROVING
    assert _trend_direction("CPV-01", -1.5) == "IMPROVING"


def test_trend_floor_worsening():
    # CPV-04 is floor; falling metric = WORSENING
    assert _trend_direction("CPV-04", -1.5) == "WORSENING"


def test_trend_floor_improving():
    # CPV-04 is floor; rising metric = IMPROVING
    assert _trend_direction("CPV-04", +1.5) == "IMPROVING"


def test_trend_stable_small_delta():
    assert _trend_direction("CPV-01", 0.3) == "STABLE"
    assert _trend_direction("CPV-04", -0.3) == "STABLE"


def test_trend_unknown_no_delta():
    assert _trend_direction("CPV-01", None) == "UNKNOWN"


# ---------------------------------------------------------------------------
# Test 1: Canonical date selection (latest PAR per date chosen)
# ---------------------------------------------------------------------------

def test_canonical_selection_latest_per_date(tmp_path):
    """When two PAR runs share the same snapshot_date, the later one is used."""
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-EARLY",  "date": "2026-05-21", "created_at": "2026-05-21T09:00:00",
         "rules": {"CPV-01": 9.52, "CPV-06": 94.97}, "overall": "FAIL", "score": 50},
        {"par": "PAR-LATER",  "date": "2026-05-21", "created_at": "2026-05-21T15:00:00",
         "rules": {"CPV-01": 8.00, "CPV-06": 90.00}, "overall": "WARN", "score": 80},
    ])
    summary = compute_drift_summary(repo_root=repo)
    assert summary["current_date"] == "2026-05-21"
    # Should use PAR-LATER values
    cpv01 = next(r for r in summary["cpv_trend"] if r["rule_id"] == "CPV-01")
    assert cpv01["current_pct"] == 8.0


# ---------------------------------------------------------------------------
# Test 2: Trend direction computed correctly for ceiling rule worsening
# ---------------------------------------------------------------------------

def test_trend_ceiling_worsening_in_summary(tmp_path):
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-A", "date": "2026-05-21", "created_at": "2026-05-21T12:00:00",
         "rules": {"CPV-01": 7.0}, "overall": "WARN", "score": 80},
        {"par": "PAR-B", "date": "2026-06-15", "created_at": "2026-06-15T12:00:00",
         "rules": {"CPV-01": 9.0}, "overall": "WARN", "score": 80},
    ])
    summary = compute_drift_summary(repo_root=repo)
    cpv01 = next(r for r in summary["cpv_trend"] if r["rule_id"] == "CPV-01")
    assert cpv01["trend_direction"] == "WORSENING"


# ---------------------------------------------------------------------------
# Test 3: Trend direction computed correctly for ceiling rule improving
# ---------------------------------------------------------------------------

def test_trend_ceiling_improving_in_summary(tmp_path):
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-A", "date": "2026-05-21", "created_at": "2026-05-21T12:00:00",
         "rules": {"CPV-01": 9.52}, "overall": "FAIL", "score": 50},
        {"par": "PAR-B", "date": "2026-06-15", "created_at": "2026-06-15T12:00:00",
         "rules": {"CPV-01": 8.89}, "overall": "WARN", "score": 80},
    ])
    summary = compute_drift_summary(repo_root=repo)
    cpv01 = next(r for r in summary["cpv_trend"] if r["rule_id"] == "CPV-01")
    assert cpv01["trend_direction"] == "IMPROVING"


# ---------------------------------------------------------------------------
# Test 4: Trend direction — floor rule worsening
# ---------------------------------------------------------------------------

def test_trend_floor_worsening_in_summary(tmp_path):
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-A", "date": "2026-05-21", "created_at": "2026-05-21T12:00:00",
         "rules": {"CPV-04": 5.0}, "overall": "OK", "score": 100},
        {"par": "PAR-B", "date": "2026-06-15", "created_at": "2026-06-15T12:00:00",
         "rules": {"CPV-04": 3.0}, "overall": "OK", "score": 100},
    ])
    summary = compute_drift_summary(repo_root=repo)
    cpv04 = next(r for r in summary["cpv_trend"] if r["rule_id"] == "CPV-04")
    assert cpv04["trend_direction"] == "WORSENING"


# ---------------------------------------------------------------------------
# Test 5: Trend direction — floor rule improving
# ---------------------------------------------------------------------------

def test_trend_floor_improving_in_summary(tmp_path):
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-A", "date": "2026-05-21", "created_at": "2026-05-21T12:00:00",
         "rules": {"CPV-04": 2.5}, "overall": "OK", "score": 100},
        {"par": "PAR-B", "date": "2026-06-15", "created_at": "2026-06-15T12:00:00",
         "rules": {"CPV-04": 9.0}, "overall": "OK", "score": 100},
    ])
    summary = compute_drift_summary(repo_root=repo)
    cpv04 = next(r for r in summary["cpv_trend"] if r["rule_id"] == "CPV-04")
    assert cpv04["trend_direction"] == "IMPROVING"


# ---------------------------------------------------------------------------
# Test 6: Empty history handling
# ---------------------------------------------------------------------------

def test_empty_history(tmp_path):
    """No PAR runs → graceful empty response, no crash."""
    (tmp_path / "data" / "portfolio_ingestion" / "analysis_runs").mkdir(parents=True)
    summary = compute_drift_summary(repo_root=tmp_path)
    assert summary["dates_available"] == 0
    assert summary["cpv_trend"] == []
    assert summary["current_date"] is None

    timeline = compute_drift_timeline("CPV-01", repo_root=tmp_path)
    assert timeline["timeline"] == []


# ---------------------------------------------------------------------------
# Test 7: Single-date handling — no prior, no delta
# ---------------------------------------------------------------------------

def test_single_date_no_prior(tmp_path):
    """Single date → prior=None, deltas=None, trend=UNKNOWN."""
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-ONLY", "date": "2026-06-15", "created_at": "2026-06-15T12:00:00",
         "rules": {"CPV-01": 8.89, "CPV-06": 86.72}, "overall": "WARN", "score": 80},
    ])
    summary = compute_drift_summary(repo_root=repo)
    assert summary["prior_date"] is None
    for rule in summary["cpv_trend"]:
        assert rule["prior_pct"] is None
        assert rule["delta_7d_pp"] is None
        assert rule["delta_30d_pp"] is None
        assert rule["trend_direction"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# Test 8: API payload contract — required keys present
# ---------------------------------------------------------------------------

def test_drift_summary_payload_contract(tmp_path):
    """compute_drift_summary returns all required keys."""
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-A", "date": "2026-05-21", "created_at": "2026-05-21T12:00:00",
         "rules": {"CPV-01": 9.52, "CPV-06": 94.97}, "overall": "FAIL", "score": 50},
        {"par": "PAR-B", "date": "2026-06-15", "created_at": "2026-06-15T12:00:00",
         "rules": {"CPV-01": 8.89, "CPV-06": 86.72}, "overall": "WARN", "score": 80},
    ])
    summary = compute_drift_summary(repo_root=repo)

    # Top-level keys
    for key in ("generated_at", "current_date", "prior_date", "dates_available",
                "current_overall_status", "current_compliance_score", "cpv_trend"):
        assert key in summary, f"Missing top-level key: {key}"

    # Per-rule keys
    rule = summary["cpv_trend"][0]
    for key in ("rule_id", "name", "rule_type", "policy_limit_pct",
                "current_pct", "prior_pct", "delta_7d_pp", "delta_30d_pp",
                "current_status", "prior_status", "trend_direction", "breach_pp"):
        assert key in rule, f"Missing per-rule key: {key}"


def test_drift_timeline_payload_contract(tmp_path):
    """compute_drift_timeline returns all required keys."""
    repo = _fake_repo(tmp_path, [
        {"par": "PAR-A", "date": "2026-05-21", "created_at": "2026-05-21T12:00:00",
         "rules": {"CPV-01": 9.52}, "overall": "FAIL", "score": 50},
    ])
    timeline = compute_drift_timeline("CPV-01", repo_root=repo)
    for key in ("rule_id", "name", "rule_type", "policy_limit_pct", "timeline"):
        assert key in timeline, f"Missing key: {key}"
    assert len(timeline["timeline"]) == 1
    entry = timeline["timeline"][0]
    for key in ("date", "actual_pct", "status", "breach_pp"):
        assert key in entry, f"Missing timeline entry key: {key}"


def test_drift_timeline_unknown_rule(tmp_path):
    """Unknown rule_id returns error key, no crash."""
    (tmp_path / "data" / "portfolio_ingestion" / "analysis_runs").mkdir(parents=True)
    result = compute_drift_timeline("CPV-99", repo_root=tmp_path)
    assert "error" in result
