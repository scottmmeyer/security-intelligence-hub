"""PA-006 — Allocation Compliance Engine — Validation Test Suite.

All tests deterministic, filesystem-isolated via pytest tmp_path.
No network calls. No modifications to existing project data.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.pis.allocation_compliance import (
    ComplianceEntry,
    NodeComplianceResult,
    _severity_to_compliance,
    _compliance_severity_label,
    _compute_streaks,
    _compute_node_compliance,
    _build_node_results,
    _collect_compliance_entries,
    _generate_observations,
    pis_compliance_summary,
    pis_compliance_latest,
    pis_compliance_history,
)


# ─── Fixture helpers ──────────────────────────────────────────────────────────

_ALIGNMENT_HEADERS = [
    "analysis_run_id", "portfolio_snapshot_id", "node_key", "node_label",
    "dimension_type", "actual_pct", "target_pct", "tactical_target_pct",
    "drift_pct", "drift_direction", "severity", "concentration_risk",
    "alignment_score", "recommendation_priority", "created_at_utc",
    "direct_actual_pct", "etf_derived_actual_pct", "effective_actual_pct",
    "decomposition_method", "decomposition_version", "decomposition_confidence",
    "decomposition_source", "decomposition_confidence_tier",
]


def _par_dir(root: Path) -> Path:
    d = root / "data" / "portfolio_ingestion" / "analysis_runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_par(
    root: Path,
    par_id: str,
    snap_date: str,
    nodes: list[dict],
    created_at: str = "2026-06-15T10:00:00+00:00",
) -> Path:
    par = _par_dir(root) / par_id
    par.mkdir(parents=True, exist_ok=True)
    meta = {"run_id": par_id, "snapshot_date": snap_date, "created_at_utc": created_at}
    (par / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    with (par / "alignment.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_ALIGNMENT_HEADERS, extrasaction="ignore")
        w.writeheader()
        for node in nodes:
            row = {h: "" for h in _ALIGNMENT_HEADERS}
            row["node_key"] = node["node_key"]
            row["node_label"] = node.get("node_label", node["node_key"])
            row["dimension_type"] = node.get("dimension_type", "ASSET_CLASS")
            row["severity"] = node.get("severity", "NONE")
            row["drift_pct"] = str(node.get("drift_pct", 0.0))
            row["actual_pct"] = str(node.get("actual_pct", 0.0))
            row["target_pct"] = str(node.get("target_pct", 0.0))
            row["tactical_target_pct"] = str(node.get("target_pct", 0.0))
            row["drift_direction"] = node.get("drift_direction", "ON_TARGET")
            w.writerow(row)
    return par


def _simple_node(key: str, severity: str, drift: float = 0.0) -> dict:
    return {"node_key": key, "severity": severity, "drift_pct": drift,
            "actual_pct": 20.0 + drift, "target_pct": 20.0}


def _make_entry(node_key: str, snap_date: str, compliance_status: str,
                severity: str = "NONE", drift_pct: float = 0.0) -> ComplianceEntry:
    return ComplianceEntry(
        snapshot_date=snap_date,
        node_key=node_key,
        node_label=node_key,
        dimension_type="ASSET_CLASS",
        compliance_status=compliance_status,
        severity=severity,
        drift_pct=drift_pct,
        actual_pct=20.0 + drift_pct,
        target_pct=20.0,
        drift_direction="ON_TARGET" if drift_pct == 0 else ("OVERWEIGHT" if drift_pct > 0 else "UNDERWEIGHT"),
    )


# ─── Domain 1: Compliance Classification ─────────────────────────────────────

def test_T01_none_severity_compliant():
    assert _severity_to_compliance("NONE") == "COMPLIANT"


def test_T02_low_severity_compliant():
    assert _severity_to_compliance("LOW") == "COMPLIANT"


def test_T03_moderate_severity_warning():
    assert _severity_to_compliance("MODERATE") == "WARNING"


def test_T04_high_severity_non_compliant():
    assert _severity_to_compliance("HIGH") == "NON_COMPLIANT"


def test_T05_empty_unknown_severity_compliant():
    assert _severity_to_compliance("") == "COMPLIANT"
    assert _severity_to_compliance("UNKNOWN") == "COMPLIANT"


# ─── Domain 2: Historical Reconstruction ─────────────────────────────────────

def test_T06_empty_par_directory(tmp_path):
    _par_dir(tmp_path)
    entries = _collect_compliance_entries(tmp_path)
    assert entries == []


def test_T07_single_par_entries_created(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01",
              [_simple_node("EQUITIES", "NONE"), _simple_node("CASH", "LOW")])
    entries = _collect_compliance_entries(tmp_path)
    assert len(entries) == 2
    symbols = {e.node_key for e in entries}
    assert symbols == {"EQUITIES", "CASH"}


def test_T08_canonical_selection_latest_wins(tmp_path):
    _make_par(tmp_path, "PAR-EARLY", "2026-06-01",
              [_simple_node("EQUITIES", "HIGH")],
              created_at="2026-06-01T08:00:00+00:00")
    _make_par(tmp_path, "PAR-LATE", "2026-06-01",
              [_simple_node("EQUITIES", "NONE")],  # latest → COMPLIANT
              created_at="2026-06-01T12:00:00+00:00")
    entries = _collect_compliance_entries(tmp_path)
    eq = next(e for e in entries if e.node_key == "EQUITIES")
    assert eq.compliance_status == "COMPLIANT"


def test_T09_missing_alignment_csv_skipped(tmp_path):
    par = _par_dir(tmp_path) / "PAR-NO-ALIGN"
    par.mkdir(parents=True, exist_ok=True)
    (par / "run_metadata.json").write_text(json.dumps({
        "snapshot_date": "2026-06-01", "created_at_utc": "2026-06-01T10:00:00+00:00"
    }))
    _make_par(tmp_path, "PAR-OK", "2026-06-08", [_simple_node("EQUITIES", "NONE")])
    entries = _collect_compliance_entries(tmp_path)
    dates = {e.snapshot_date for e in entries}
    assert "2026-06-08" in dates
    assert "2026-06-01" not in dates


def test_T10_malformed_snapshot_date_skipped(tmp_path):
    par = _par_dir(tmp_path) / "PAR-BAD"
    par.mkdir(parents=True, exist_ok=True)
    (par / "run_metadata.json").write_text(json.dumps({
        "snapshot_date": "NOT-DATE", "created_at_utc": "2026-06-01T10:00:00+00:00"
    }))
    with (par / "alignment.csv").open("w") as f:
        f.write("node_key,severity\nEQUITIES,NONE\n")
    _make_par(tmp_path, "PAR-OK", "2026-06-08", [_simple_node("EQUITIES", "NONE")])
    entries = _collect_compliance_entries(tmp_path)
    dates = {e.snapshot_date for e in entries}
    assert "NOT-DATE" not in dates
    assert "2026-06-08" in dates


# ─── Domain 3: Streak Computation ────────────────────────────────────────────

def _entry_seq(statuses: list[str]) -> list[ComplianceEntry]:
    from datetime import date, timedelta
    base = date(2026, 6, 1)
    return [
        _make_entry("NODE", (base + timedelta(days=i)).isoformat(), s)
        for i, s in enumerate(statuses)
    ]


def test_T11_all_compliant_streak_equals_total():
    entries = _entry_seq(["COMPLIANT"] * 5)
    current, lc, lnc = _compute_streaks(entries)
    assert current == 5
    assert lc == 5
    assert lnc == 0


def test_T12_mixed_streaks():
    # C/C/W/W/NC
    entries = _entry_seq(["COMPLIANT", "COMPLIANT", "WARNING", "WARNING", "NON_COMPLIANT"])
    current, lc, lnc = _compute_streaks(entries)
    assert current == 1  # last is NON_COMPLIANT, streak = 1
    assert lc == 2       # longest compliant run = 2
    assert lnc == 1      # longest non-compliant run = 1


def test_T13_all_non_compliant():
    entries = _entry_seq(["NON_COMPLIANT"] * 7)
    current, lc, lnc = _compute_streaks(entries)
    assert current == 7
    assert lnc == 7
    assert lc == 0


def test_T14_single_entry_streak_1():
    entries = [_make_entry("NODE", "2026-06-01", "COMPLIANT")]
    current, lc, lnc = _compute_streaks(entries)
    assert current == 1
    assert lc == 1


def test_T15_alternating_longest_streak_1():
    entries = _entry_seq(["COMPLIANT", "NON_COMPLIANT", "COMPLIANT", "NON_COMPLIANT"])
    current, lc, lnc = _compute_streaks(entries)
    assert lc == 1
    assert lnc == 1


def test_T16_streak_counts_from_end():
    # Ends with 3 COMPLIANT
    entries = _entry_seq(["NON_COMPLIANT", "NON_COMPLIANT", "COMPLIANT", "COMPLIANT", "COMPLIANT"])
    current, lc, lnc = _compute_streaks(entries)
    assert current == 3
    assert lnc == 2


# ─── Domain 4: Compliance Rates ──────────────────────────────────────────────

def test_T17_fifty_percent_rate():
    entries = _entry_seq(["COMPLIANT"] * 10 + ["NON_COMPLIANT"] * 10)
    result = _compute_node_compliance("NODE", "Node", "ASSET_CLASS", entries)
    assert abs(result.compliance_rate_pct - 50.0) < 0.1


def test_T18_all_compliant_100_pct():
    entries = _entry_seq(["COMPLIANT"] * 5)
    result = _compute_node_compliance("NODE", "Node", "ASSET_CLASS", entries)
    assert result.compliance_rate_pct == 100.0


def test_T19_all_non_compliant_0_pct():
    entries = _entry_seq(["NON_COMPLIANT"] * 5)
    result = _compute_node_compliance("NODE", "Node", "ASSET_CLASS", entries)
    assert result.compliance_rate_pct == 0.0


def test_T20_warning_not_counted_in_compliant_rate():
    entries = _entry_seq(["COMPLIANT", "WARNING", "WARNING", "WARNING"])
    result = _compute_node_compliance("NODE", "Node", "ASSET_CLASS", entries)
    # 1 compliant / 4 total = 25%
    assert abs(result.compliance_rate_pct - 25.0) < 0.1
    assert result.warning_count == 3


# ─── Domain 5: Compliance Severity Labels ────────────────────────────────────

def test_T21_80_pct_highly_compliant():
    assert _compliance_severity_label(80.0) == "HIGHLY_COMPLIANT"
    assert _compliance_severity_label(95.0) == "HIGHLY_COMPLIANT"


def test_T22_60_to_79_mostly_compliant():
    assert _compliance_severity_label(60.0) == "MOSTLY_COMPLIANT"
    assert _compliance_severity_label(75.0) == "MOSTLY_COMPLIANT"
    assert _compliance_severity_label(79.9) == "MOSTLY_COMPLIANT"


def test_T23_40_to_59_mixed():
    assert _compliance_severity_label(40.0) == "MIXED"
    assert _compliance_severity_label(55.0) == "MIXED"
    assert _compliance_severity_label(59.9) == "MIXED"


def test_T24_below_40_persistently_non_compliant():
    assert _compliance_severity_label(39.9) == "PERSISTENTLY_NON_COMPLIANT"
    assert _compliance_severity_label(0.0) == "PERSISTENTLY_NON_COMPLIANT"


def test_T25_exactly_80_highly_compliant():
    assert _compliance_severity_label(80.0) == "HIGHLY_COMPLIANT"


def test_T26_exactly_40_mixed():
    assert _compliance_severity_label(40.0) == "MIXED"


# ─── Domain 6: Governance Observations ──────────────────────────────────────

def _make_node_result(node_key: str, compliance_rate: float, current_status: str = "COMPLIANT",
                      warning_count: int = 0, non_compliant_count: int = 0,
                      dates: int = 19, lnc_streak: int = 0) -> NodeComplianceResult:
    compliant = round(compliance_rate / 100 * dates)
    return NodeComplianceResult(
        node_key=node_key,
        node_label=node_key,
        dimension_type="ASSET_CLASS",
        dates_available=dates,
        compliant_count=compliant,
        warning_count=warning_count,
        non_compliant_count=non_compliant_count or (dates - compliant - warning_count),
        compliance_rate_pct=compliance_rate,
        non_compliance_rate_pct=round(non_compliant_count / dates * 100, 1) if dates else 0.0,
        compliance_severity=_compliance_severity_label(compliance_rate),
        current_status=current_status,
        current_streak=1,
        longest_compliant_streak=compliant,
        longest_non_compliant_streak=lnc_streak,
        current_drift_pct=5.0,
        current_actual_pct=25.0,
        current_target_pct=20.0,
    )


def test_T27_persistent_violation_in_observations():
    results = [
        _make_node_result("EQUITIES.INTERNATIONAL", 10.0, "WARNING", warning_count=17, non_compliant_count=1, lnc_streak=15),
    ]
    obs = _generate_observations(results, 19)
    obs_text = " ".join(obs)
    assert "EQUITIES.INTERNATIONAL" in obs_text or "non-compliant" in obs_text.lower()


def test_T28_highly_compliant_in_observations():
    results = [
        _make_node_result("CASH", 95.0, "COMPLIANT"),
    ]
    obs = _generate_observations(results, 19)
    obs_text = " ".join(obs)
    assert "CASH" in obs_text or "compliance" in obs_text.lower()


def test_T29_long_streak_in_observations():
    results = [
        _make_node_result("EQUITIES.US.MID", 10.0, "NON_COMPLIANT",
                          non_compliant_count=17, lnc_streak=17),
    ]
    obs = _generate_observations(results, 19)
    obs_text = " ".join(obs)
    assert "17" in obs_text or "non-compliant" in obs_text.lower()


def test_T30_observations_capped_at_6():
    results = [
        _make_node_result(f"NODE_{i}", 10.0, "NON_COMPLIANT",
                          non_compliant_count=15, lnc_streak=15)
        for i in range(20)
    ]
    obs = _generate_observations(results, 19)
    assert len(obs) <= 6


# ─── Domain 7: API Payload Integrity ─────────────────────────────────────────

def _minimal_setup(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", [
        _simple_node("EQUITIES", "NONE"),
        _simple_node("CASH", "LOW"),
        _simple_node("EQUITIES.US.LARGE", "MODERATE", drift=-5.0),
    ])
    _make_par(tmp_path, "PAR-002", "2026-06-08", [
        _simple_node("EQUITIES", "NONE"),
        _simple_node("CASH", "LOW"),
        _simple_node("EQUITIES.US.LARGE", "HIGH", drift=-8.0),
    ])


def test_T31_summary_required_fields(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_compliance_summary(tmp_path)
    required = {
        "generated_at", "total_nodes", "currently_compliant", "currently_warning",
        "currently_non_compliant", "dates_covered", "highly_compliant_count",
        "persistently_non_compliant_count", "top_violations", "observations",
    }
    assert required.issubset(result.keys())


def test_T32_latest_node_fields(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_compliance_latest(tmp_path)
    assert "nodes" in result
    assert len(result["nodes"]) > 0
    node = result["nodes"][0]
    required = {
        "node_key", "compliance_rate_pct", "compliance_severity",
        "current_status", "current_streak", "longest_compliant_streak",
        "longest_non_compliant_streak", "current_drift_pct",
    }
    assert required.issubset(node.keys())


def test_T33_history_entries_ascending_by_date(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_compliance_history(tmp_path)
    assert "nodes" in result
    for node in result["nodes"]:
        dates = [e["snapshot_date"] for e in node["entries"]]
        assert dates == sorted(dates)


def test_T34_counts_sum_to_total(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_compliance_summary(tmp_path)
    total = result["total_nodes"]
    current_sum = (result["currently_compliant"] +
                   result["currently_warning"] +
                   result["currently_non_compliant"])
    assert current_sum == total


def test_T35_consistent_node_keys_across_endpoints(tmp_path):
    _minimal_setup(tmp_path)
    latest_keys = {n["node_key"] for n in pis_compliance_latest(tmp_path)["nodes"]}
    history_keys = {n["node_key"] for n in pis_compliance_history(tmp_path)["nodes"]}
    assert latest_keys == history_keys


# ─── Domain 8: Edge Cases ─────────────────────────────────────────────────────

def test_T36_no_par_runs_empty_payload(tmp_path):
    _par_dir(tmp_path)
    result = pis_compliance_summary(tmp_path)
    assert result["total_nodes"] == 0
    assert result["observations"] is not None


def test_T37_all_compliant_no_persistent_violations(tmp_path):
    # All nodes NONE severity across both dates
    for i, d in enumerate(["2026-06-01", "2026-06-08"]):
        _make_par(tmp_path, f"PAR-{i:03}", d, [
            _simple_node("EQUITIES", "NONE"),
            _simple_node("CASH", "NONE"),
        ])
    result = pis_compliance_summary(tmp_path)
    assert result["persistently_non_compliant_count"] == 0
    assert result["currently_non_compliant"] == 0


def test_T38_single_date_streak_equals_1(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", [_simple_node("EQUITIES", "HIGH")])
    result = pis_compliance_latest(tmp_path)
    node = next(n for n in result["nodes"] if n["node_key"] == "EQUITIES")
    assert node["current_streak"] == 1
    assert node["longest_non_compliant_streak"] == 1


def test_T39_node_in_subset_of_dates_correct_count(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01",
              [_simple_node("EQUITIES", "NONE"), _simple_node("CASH", "LOW")])
    _make_par(tmp_path, "PAR-002", "2026-06-08",
              [_simple_node("EQUITIES", "NONE")])  # CASH absent
    result = pis_compliance_latest(tmp_path)
    cash = next((n for n in result["nodes"] if n["node_key"] == "CASH"), None)
    eq = next((n for n in result["nodes"] if n["node_key"] == "EQUITIES"), None)
    assert eq is not None and eq["dates_available"] == 2
    if cash is not None:
        assert cash["dates_available"] == 1
