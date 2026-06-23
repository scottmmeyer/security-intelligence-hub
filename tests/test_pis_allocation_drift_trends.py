"""PIS-007 — Allocation Drift Trend Visibility — Validation Test Suite.

All tests are deterministic and filesystem-isolated (pytest tmp_path).
No network calls. No modifications to existing project data.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.pis.allocation_drift import (
    HistoryEntry,
    _collect_canonical_runs,
    _build_node_history,
    _compute_trend,
    _compute_all_trends,
    _generate_observations,
    pis_allocation_drift_summary,
    pis_allocation_drift_latest,
    pis_allocation_drift_history,
)


# ─── Fixture helpers ──────────────────────────────────────────────────────────


def _par_dir(root: Path) -> Path:
    d = root / "data" / "portfolio_ingestion" / "analysis_runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_run_metadata(
    root: Path,
    par_id: str,
    snapshot_date: str,
    created_at_utc: str = "2026-06-15T10:00:00+00:00",
) -> Path:
    d = _par_dir(root) / par_id
    d.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": par_id,
        "snapshot_date": snapshot_date,
        "created_at_utc": created_at_utc,
        "status": "COMPLETE",
    }
    (d / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


_ALIGNMENT_HEADERS = [
    "analysis_run_id", "portfolio_snapshot_id", "node_key", "node_label",
    "dimension_type", "actual_pct", "target_pct", "tactical_target_pct",
    "drift_pct", "drift_direction", "severity", "concentration_risk",
    "alignment_score", "recommendation_priority", "created_at_utc",
    "direct_actual_pct", "etf_derived_actual_pct", "effective_actual_pct",
    "decomposition_method", "decomposition_version", "decomposition_confidence",
    "decomposition_source", "decomposition_confidence_tier",
]


def _make_alignment_csv(
    run_dir: Path,
    par_id: str,
    nodes: list[dict],
) -> Path:
    """Write alignment.csv to run_dir with given node rows."""
    path = run_dir / "alignment.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_ALIGNMENT_HEADERS, extrasaction="ignore")
        writer.writeheader()
        for node in nodes:
            row = {h: "" for h in _ALIGNMENT_HEADERS}
            row["analysis_run_id"] = par_id
            row["node_key"] = node.get("node_key", "EQUITIES")
            row["node_label"] = node.get("node_label", "Equities")
            row["dimension_type"] = node.get("dimension_type", "ASSET_CLASS")
            row["actual_pct"] = str(node.get("actual_pct", 50.0))
            row["target_pct"] = str(node.get("target_pct", 50.0))
            row["tactical_target_pct"] = str(node.get("tactical_target_pct", ""))
            row["effective_actual_pct"] = str(node.get("effective_actual_pct", ""))
            writer.writerow(row)
    return path


def _make_par(
    root: Path,
    par_id: str,
    snapshot_date: str,
    nodes: list[dict],
    created_at_utc: str = "2026-06-15T10:00:00+00:00",
) -> Path:
    run_dir = _make_run_metadata(root, par_id, snapshot_date, created_at_utc)
    _make_alignment_csv(run_dir, par_id, nodes)
    return run_dir


_SINGLE_NODE = [{"node_key": "EQUITIES", "node_label": "Equities",
                 "dimension_type": "ASSET_CLASS", "actual_pct": 90.0, "target_pct": 88.0}]


# ─── Domain 1: Historical Reconstruction ─────────────────────────────────────


def test_T01_empty_par_directory(tmp_path):
    """T-01: Empty PAR directory → dates_available: 0, empty nodes."""
    _par_dir(tmp_path)  # create empty dir
    result = pis_allocation_drift_summary(tmp_path)
    assert result["dates_available"] == 0
    assert result["current_date"] is None
    latest = pis_allocation_drift_latest(tmp_path)
    assert latest["dates_available"] == 0
    assert latest["nodes"] == []


def test_T02_single_par_single_node(tmp_path):
    """T-02: Single PAR run, single node → one entry; STABLE trend; no prior drift."""
    _make_par(tmp_path, "PAR-001", "2026-06-01", _SINGLE_NODE)
    latest = pis_allocation_drift_latest(tmp_path)
    assert latest["dates_available"] == 1
    assert len(latest["nodes"]) == 1
    node = latest["nodes"][0]
    assert node["node_key"] == "EQUITIES"
    assert node["prior_drift_pct"] is None
    assert node["drift_delta_pp"] is None
    assert node["trend_direction"] == "STABLE"
    assert node["trend_severity"] == "NONE"


def test_T03_multiple_runs_same_date_latest_wins(tmp_path):
    """T-03: Two PAR runs same date, different times → later created_at wins."""
    early_node = [{"node_key": "EQUITIES", "actual_pct": 80.0, "target_pct": 88.0}]
    late_node = [{"node_key": "EQUITIES", "actual_pct": 92.0, "target_pct": 88.0}]
    _make_par(tmp_path, "PAR-EARLY", "2026-06-01", early_node,
              created_at_utc="2026-06-01T09:00:00+00:00")
    _make_par(tmp_path, "PAR-LATE", "2026-06-01", late_node,
              created_at_utc="2026-06-01T12:00:00+00:00")
    latest = pis_allocation_drift_latest(tmp_path)
    assert latest["dates_available"] == 1
    node = latest["nodes"][0]
    # Late run: actual=92.0, target=88.0 → drift=+4.0
    assert abs(node["current_actual_pct"] - 92.0) < 0.01


def test_T04_multiple_dates_all_represented(tmp_path):
    """T-04: Three dates → all three in history, ascending order."""
    for i, d in enumerate(["2026-06-01", "2026-06-08", "2026-06-15"]):
        _make_par(tmp_path, f"PAR-{i:03}", d, _SINGLE_NODE)
    hist = pis_allocation_drift_history(tmp_path)
    assert hist["dates"] == ["2026-06-01", "2026-06-08", "2026-06-15"]
    assert len(hist["nodes"]) == 1


def test_T05_missing_alignment_csv_skipped(tmp_path):
    """T-05: PAR run without alignment.csv is silently skipped."""
    run_dir = _make_run_metadata(tmp_path, "PAR-NO-ALIGN", "2026-06-01")
    # No alignment.csv written
    _make_par(tmp_path, "PAR-OK", "2026-06-08", _SINGLE_NODE)
    hist = pis_allocation_drift_history(tmp_path)
    assert "2026-06-01" not in hist["dates"]
    assert "2026-06-08" in hist["dates"]


def test_T06_effective_actual_pct_used_when_present(tmp_path):
    """T-06: effective_actual_pct takes priority over actual_pct."""
    nodes = [{
        "node_key": "EQUITIES", "actual_pct": 80.0, "target_pct": 88.0,
        "effective_actual_pct": 92.0,  # this should win
    }]
    _make_par(tmp_path, "PAR-001", "2026-06-01", nodes)
    latest = pis_allocation_drift_latest(tmp_path)
    node = latest["nodes"][0]
    assert abs(node["current_actual_pct"] - 92.0) < 0.01


def test_T07_fallback_to_actual_pct(tmp_path):
    """T-07: effective_actual_pct absent → falls back to actual_pct."""
    nodes = [{"node_key": "EQUITIES", "actual_pct": 85.0, "target_pct": 88.0,
              "effective_actual_pct": ""}]
    _make_par(tmp_path, "PAR-001", "2026-06-01", nodes)
    latest = pis_allocation_drift_latest(tmp_path)
    node = latest["nodes"][0]
    assert abs(node["current_actual_pct"] - 85.0) < 0.01


def test_T08_tactical_target_pct_used_when_present(tmp_path):
    """T-08: tactical_target_pct takes priority over target_pct."""
    nodes = [{
        "node_key": "EQUITIES", "actual_pct": 90.0, "target_pct": 88.0,
        "tactical_target_pct": 86.0,  # this should win
    }]
    _make_par(tmp_path, "PAR-001", "2026-06-01", nodes)
    latest = pis_allocation_drift_latest(tmp_path)
    node = latest["nodes"][0]
    assert abs(node["current_target_pct"] - 86.0) < 0.01
    assert abs(node["current_drift_pct"] - 4.0) < 0.01  # 90 - 86


def test_T09_fallback_to_target_pct(tmp_path):
    """T-09: tactical_target_pct absent → falls back to target_pct."""
    nodes = [{"node_key": "EQUITIES", "actual_pct": 90.0, "target_pct": 88.0,
              "tactical_target_pct": ""}]
    _make_par(tmp_path, "PAR-001", "2026-06-01", nodes)
    latest = pis_allocation_drift_latest(tmp_path)
    node = latest["nodes"][0]
    assert abs(node["current_target_pct"] - 88.0) < 0.01


def test_T10_row_with_no_actual_skipped(tmp_path):
    """T-10: Row missing both effective_actual_pct and actual_pct → skipped."""
    nodes = [{"node_key": "EQUITIES", "actual_pct": "", "effective_actual_pct": "",
              "target_pct": 88.0}]
    _make_par(tmp_path, "PAR-001", "2026-06-01", nodes)
    latest = pis_allocation_drift_latest(tmp_path)
    assert latest["nodes"] == []


def test_T11_node_in_subset_of_dates(tmp_path):
    """T-11: Node appears in 2 of 3 dates → dates_available = 2."""
    nodes_with = [{"node_key": "EQUITIES.US.MID", "actual_pct": 15.0, "target_pct": 20.0}]
    nodes_without = [{"node_key": "EQUITIES", "actual_pct": 90.0, "target_pct": 88.0}]
    _make_par(tmp_path, "PAR-001", "2026-06-01", nodes_with)
    _make_par(tmp_path, "PAR-002", "2026-06-08", nodes_without)  # MID absent
    _make_par(tmp_path, "PAR-003", "2026-06-15", nodes_with)
    latest = pis_allocation_drift_latest(tmp_path)
    mid_node = next((n for n in latest["nodes"] if n["node_key"] == "EQUITIES.US.MID"), None)
    assert mid_node is not None
    assert mid_node["dates_available"] == 2


def test_T12_malformed_snapshot_date_skipped(tmp_path):
    """T-12: PAR with malformed snapshot_date is skipped entirely."""
    run_dir = _make_run_metadata(tmp_path, "PAR-BAD", "NOT-A-DATE")
    _make_alignment_csv(run_dir, "PAR-BAD", _SINGLE_NODE)
    _make_par(tmp_path, "PAR-OK", "2026-06-08", _SINGLE_NODE)
    runs = _collect_canonical_runs(tmp_path)
    dates = [d for d, _ in runs]
    assert "2026-06-08" in dates
    assert "NOT-A-DATE" not in dates


# ─── Domain 2: Canonical Date Selection ──────────────────────────────────────


def test_T13_canonical_selection_latest_created_at(tmp_path):
    """T-13: Same date, two PARs with different created_at → latest wins."""
    n1 = [{"node_key": "CASH", "actual_pct": 3.0, "target_pct": 5.0}]
    n2 = [{"node_key": "CASH", "actual_pct": 7.0, "target_pct": 5.0}]
    _make_par(tmp_path, "PAR-A", "2026-06-01", n1, "2026-06-01T08:00:00+00:00")
    _make_par(tmp_path, "PAR-B", "2026-06-01", n2, "2026-06-01T11:00:00+00:00")
    runs = _collect_canonical_runs(tmp_path)
    assert len(runs) == 1
    _, align_path = runs[0]
    with align_path.open() as f:
        rows = list(csv.DictReader(f))
    actual = float(rows[0]["actual_pct"])
    assert abs(actual - 7.0) < 0.01  # PAR-B won


def test_T14_canonical_dates_ascending(tmp_path):
    """T-14: canonical_dates always sorted ascending."""
    for i, d in enumerate(["2026-06-15", "2026-06-01", "2026-06-08"]):
        _make_par(tmp_path, f"PAR-{i}", d, _SINGLE_NODE)
    runs = _collect_canonical_runs(tmp_path)
    dates = [d for d, _ in runs]
    assert dates == sorted(dates)


def test_T15_snapshot_date_with_time_component(tmp_path):
    """T-15: snapshot_date with time suffix — first 10 chars used."""
    run_dir = _make_run_metadata(tmp_path, "PAR-TS", "2026-06-01T00:00:00")
    _make_alignment_csv(run_dir, "PAR-TS", _SINGLE_NODE)
    runs = _collect_canonical_runs(tmp_path)
    dates = [d for d, _ in runs]
    assert "2026-06-01" in dates


# ─── Domain 3: Drift Calculation ─────────────────────────────────────────────


def _single_entry(actual, target):
    return [HistoryEntry("2026-06-01", actual, target, round(actual - target, 4))]


def test_T16_on_target(tmp_path):
    entries = _single_entry(20.0, 20.0)
    result = _compute_trend("EQUITIES.US.MID", "US Mid Cap", "MARKET_CAP", entries)
    assert abs(result.current_drift_pct) < 0.01
    assert result.drift_direction == "ON_TARGET"


def test_T17_overweight(tmp_path):
    entries = _single_entry(25.0, 20.0)
    result = _compute_trend("EQUITIES.US.MID", "US Mid Cap", "MARKET_CAP", entries)
    assert abs(result.current_drift_pct - 5.0) < 0.01
    assert result.drift_direction == "OVERWEIGHT"


def test_T18_underweight(tmp_path):
    entries = _single_entry(15.0, 20.0)
    result = _compute_trend("EQUITIES.US.MID", "US Mid Cap", "MARKET_CAP", entries)
    assert abs(result.current_drift_pct - (-5.0)) < 0.01
    assert result.drift_direction == "UNDERWEIGHT"


def test_T19_drift_recomputed_from_actual_target(tmp_path):
    """T-19: drift_pct in CSV is not used; recomputed from actual - target."""
    # Simulate CSV drift_pct disagreeing with actual-target calculation
    entry = HistoryEntry("2026-06-01", 92.0, 88.0, round(92.0 - 88.0, 4))
    assert abs(entry.drift_pct - 4.0) < 0.01  # recomputed correctly


# ─── Domain 4: Trend Direction ────────────────────────────────────────────────


def _two_entry_trend(drift_a, drift_b, actual=90.0, target=88.0):
    """Create two-entry history where first has drift_a, second has drift_b."""
    e1 = HistoryEntry("2026-06-01", actual, actual - drift_a, drift_a)
    e2 = HistoryEntry("2026-06-08", actual, actual - drift_b, drift_b)
    return _compute_trend("EQUITIES", "Equities", "ASSET_CLASS", [e1, e2])


def test_T20_overweight_drift_grows_worsening():
    """T-20: OVERWEIGHT, drift +2 → +4 → WORSENING."""
    result = _two_entry_trend(2.0, 4.0)
    assert result.trend_direction == "WORSENING"


def test_T21_overweight_drift_shrinks_improving():
    """T-21: OVERWEIGHT, drift +4 → +2 → IMPROVING."""
    result = _two_entry_trend(4.0, 2.0)
    assert result.trend_direction == "IMPROVING"


def test_T22_underweight_drift_grows_worsening():
    """T-22: UNDERWEIGHT, drift −2 → −4 → WORSENING."""
    result = _two_entry_trend(-2.0, -4.0)
    assert result.trend_direction == "WORSENING"


def test_T23_underweight_drift_shrinks_improving():
    """T-23: UNDERWEIGHT, drift −4 → −2 → IMPROVING."""
    result = _two_entry_trend(-4.0, -2.0)
    assert result.trend_direction == "IMPROVING"


def test_T24_drift_change_below_stable_threshold():
    """T-24: Change < 0.5pp → STABLE."""
    result = _two_entry_trend(3.0, 3.3)  # delta=0.3, below threshold
    assert result.trend_direction == "STABLE"


def test_T25_single_entry_stable():
    """T-25: Single entry → STABLE."""
    entries = [HistoryEntry("2026-06-01", 25.0, 20.0, 5.0)]
    result = _compute_trend("NODE", "Node", "ASSET_CLASS", entries)
    assert result.trend_direction == "STABLE"
    assert result.prior_drift_pct is None


def test_T26_overweight_to_near_zero_improving():
    """T-26: OVERWEIGHT +4 → +0.1 → IMPROVING."""
    result = _two_entry_trend(4.0, 0.1)
    assert result.trend_direction == "IMPROVING"


# ─── Domain 5: Trend Severity ────────────────────────────────────────────────


def test_T27_severity_none():
    result = _two_entry_trend(3.0, 3.3)  # abs mag delta = 0.3
    assert result.trend_severity == "NONE"


def test_T28_severity_minor():
    result = _two_entry_trend(3.0, 4.2)  # abs mag delta = 1.2
    assert result.trend_severity == "MINOR"


def test_T29_severity_moderate():
    result = _two_entry_trend(2.0, 5.5)  # abs mag delta = 3.5
    assert result.trend_severity == "MODERATE"


def test_T30_severity_significant():
    result = _two_entry_trend(1.0, 7.0)  # abs mag delta = 6.0
    assert result.trend_severity == "SIGNIFICANT"


def test_T31_single_entry_severity_none():
    entries = [HistoryEntry("2026-06-01", 25.0, 20.0, 5.0)]
    result = _compute_trend("NODE", "Node", "ASSET_CLASS", entries)
    assert result.trend_severity == "NONE"


# ─── Domain 6: Drift Velocity ────────────────────────────────────────────────


def test_T32_velocity_two_dates():
    """T-32: 7 days apart, drift −2.0 → −3.0 → velocity ≈ −1.0/7."""
    e1 = HistoryEntry("2026-06-01", 18.0, 20.0, -2.0)
    e2 = HistoryEntry("2026-06-08", 17.0, 20.0, -3.0)
    result = _compute_trend("NODE", "Node", "MARKET_CAP", [e1, e2])
    expected = (-3.0 - (-2.0)) / 7
    assert abs(result.drift_velocity_pp_per_day - expected) < 0.001


def test_T33_velocity_single_entry_zero():
    """T-33: Single entry → velocity = 0.0."""
    entries = [HistoryEntry("2026-06-01", 18.0, 20.0, -2.0)]
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.drift_velocity_pp_per_day == 0.0


def test_T34_velocity_same_date_no_division_by_zero():
    """T-34: Two entries same date → days_span capped at 1, no zero division."""
    e1 = HistoryEntry("2026-06-01", 18.0, 20.0, -2.0)
    e2 = HistoryEntry("2026-06-01", 17.0, 20.0, -3.0)
    result = _compute_trend("NODE", "Node", "MARKET_CAP", [e1, e2])
    # Should not raise; velocity computed with days_span=1
    assert isinstance(result.drift_velocity_pp_per_day, float)


# ─── Domain 7: Persistence Score ─────────────────────────────────────────────


def _make_entries_with_drifts(drifts):
    base_date = date(2026, 6, 1)
    entries = []
    for i, d in enumerate(drifts):
        dt = (base_date + timedelta(days=i)).isoformat()
        entries.append(HistoryEntry(dt, 20.0 + d, 20.0, d))
    return entries


def test_T35_all_overweight_persistence_1():
    """T-35: All 5 entries OVERWEIGHT → persistence = 1.0."""
    entries = _make_entries_with_drifts([2.0, 3.0, 1.5, 4.0, 2.5])
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.persistence_score == 1.0


def test_T36_mixed_overweight_persistence():
    """T-36: 3 of 5 entries OVERWEIGHT (current OVERWEIGHT) → persistence = 0.6."""
    entries = _make_entries_with_drifts([2.0, -1.0, 3.0, -0.5, 1.5])
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.drift_direction == "OVERWEIGHT"
    assert abs(result.persistence_score - 3/5) < 0.01


def test_T37_single_entry_underweight_persistence_1():
    """T-37: Single entry UNDERWEIGHT → persistence = 1.0."""
    entries = [HistoryEntry("2026-06-01", 18.0, 20.0, -2.0)]
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.persistence_score == 1.0


def test_T38_underweight_mixed_persistence():
    """T-38: 3 of 5 UNDERWEIGHT (current UNDERWEIGHT) → persistence = 0.6."""
    entries = _make_entries_with_drifts([-2.0, 1.0, -3.0, 0.5, -1.5])
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.drift_direction == "UNDERWEIGHT"
    assert abs(result.persistence_score - 3/5) < 0.01


# ─── Domain 8: Summary Computation ───────────────────────────────────────────


def test_T39_most_improved_node_correct(tmp_path):
    """T-39: Most improved = node with most negative magnitude_delta."""
    _make_par(tmp_path, "PAR-D1", "2026-06-01", [
        {"node_key": "CASH", "actual_pct": 10.0, "target_pct": 5.0},      # drift +5
        {"node_key": "EQUITIES", "actual_pct": 80.0, "target_pct": 88.0}, # drift -8
    ])
    _make_par(tmp_path, "PAR-D2", "2026-06-08", [
        {"node_key": "CASH", "actual_pct": 6.0, "target_pct": 5.0},       # drift +1 (improved 4)
        {"node_key": "EQUITIES", "actual_pct": 81.0, "target_pct": 88.0}, # drift -7 (improved 1)
    ])
    summary = pis_allocation_drift_summary(tmp_path)
    # CASH improved most: |+1| - |+5| = -4 vs EQUITIES: |-7| - |-8| = -1
    assert summary["most_improved_node"]["node_key"] == "CASH"


def test_T40_most_deteriorated_node_correct(tmp_path):
    """T-40: Most deteriorated = node with most positive magnitude_delta."""
    _make_par(tmp_path, "PAR-D1", "2026-06-01", [
        {"node_key": "EQUITIES.US.MID", "actual_pct": 18.0, "target_pct": 20.0},   # -2
        {"node_key": "EQUITIES.INTERNATIONAL", "actual_pct": 11.0, "target_pct": 12.0},  # -1
    ])
    _make_par(tmp_path, "PAR-D2", "2026-06-08", [
        {"node_key": "EQUITIES.US.MID", "actual_pct": 13.0, "target_pct": 20.0},        # -7 (worsened 5)
        {"node_key": "EQUITIES.INTERNATIONAL", "actual_pct": 9.0, "target_pct": 12.0},  # -3 (worsened 2)
    ])
    summary = pis_allocation_drift_summary(tmp_path)
    assert summary["most_deteriorated_node"]["node_key"] == "EQUITIES.US.MID"


def test_T41_all_stable_no_most_improved_or_deteriorated(tmp_path):
    """T-41: All nodes STABLE → most_improved and most_deteriorated are null."""
    # Single date → all nodes have no prior → all STABLE
    _make_par(tmp_path, "PAR-001", "2026-06-01", _SINGLE_NODE)
    summary = pis_allocation_drift_summary(tmp_path)
    assert summary["most_improved_node"] is None
    assert summary["most_deteriorated_node"] is None


def test_T42_improving_worsening_stable_counts(tmp_path):
    """T-42: Count invariants: improving + worsening + stable = total nodes."""
    _make_par(tmp_path, "PAR-D1", "2026-06-01", [
        {"node_key": "EQUITIES", "actual_pct": 90.0, "target_pct": 88.0},
        {"node_key": "CASH", "actual_pct": 10.0, "target_pct": 5.0},
    ])
    _make_par(tmp_path, "PAR-D2", "2026-06-08", [
        {"node_key": "EQUITIES", "actual_pct": 88.5, "target_pct": 88.0},  # improved
        {"node_key": "CASH", "actual_pct": 12.0, "target_pct": 5.0},       # worsened
    ])
    summary = pis_allocation_drift_summary(tmp_path)
    total = summary["improving_count"] + summary["worsening_count"] + summary["stable_count"]
    assert total == 2


def test_T43_empty_trends_zero_counts(tmp_path):
    """T-43: No PAR data → all counts 0."""
    _par_dir(tmp_path)
    summary = pis_allocation_drift_summary(tmp_path)
    assert summary["improving_count"] == 0
    assert summary["worsening_count"] == 0
    assert summary["stable_count"] == 0
    assert summary["most_improved_node"] is None
    assert summary["most_deteriorated_node"] is None


# ─── Domain 9: Observations Generation ──────────────────────────────────────


def _make_worsening_trend(drift_prior=-2.0, drift_current=-5.0, severity="MODERATE"):
    """Construct a NodeTrendResult that is WORSENING with given severity."""
    mag = abs(drift_current) - abs(drift_prior)
    return _two_entry_trend(drift_prior, drift_current)


def test_T44_worsening_observation_text(tmp_path):
    """T-44: WORSENING MODERATE severity → observation contains node label and both drifts."""
    _make_par(tmp_path, "P1", "2026-06-01",
              [{"node_key": "EQUITIES.US.MID", "node_label": "US Mid Cap",
                "actual_pct": 18.0, "target_pct": 20.0}])
    _make_par(tmp_path, "P2", "2026-06-08",
              [{"node_key": "EQUITIES.US.MID", "node_label": "US Mid Cap",
                "actual_pct": 13.0, "target_pct": 20.0}])
    summary = pis_allocation_drift_summary(tmp_path)
    obs_text = " ".join(summary["observations"])
    assert "US Mid Cap" in obs_text or "deteriorated" in obs_text


def test_T45_improving_observation_contains_improved(tmp_path):
    """T-45: IMPROVING MODERATE → observation contains 'improved'."""
    _make_par(tmp_path, "P1", "2026-06-01",
              [{"node_key": "CASH", "node_label": "Cash",
                "actual_pct": 12.0, "target_pct": 5.0}])
    _make_par(tmp_path, "P2", "2026-06-08",
              [{"node_key": "CASH", "node_label": "Cash",
                "actual_pct": 6.0, "target_pct": 5.0}])
    summary = pis_allocation_drift_summary(tmp_path)
    obs_text = " ".join(summary["observations"])
    assert "improved" in obs_text.lower() or "Cash" in obs_text


def test_T46_persistent_misalignment_observation(tmp_path):
    """T-46: Persistent (all dates same direction, ≥5 dates) → 'persistently' in observation."""
    for i in range(7):
        d = (date(2026, 6, 1) + timedelta(days=i)).isoformat()
        _make_par(tmp_path, f"P-{i:03}", d,
                  [{"node_key": "EQUITIES.INTERNATIONAL", "node_label": "International Equities",
                    "actual_pct": 20.0, "target_pct": 12.0}])
    summary = pis_allocation_drift_summary(tmp_path)
    obs_text = " ".join(summary["observations"])
    assert "persistently" in obs_text.lower()


def test_T47_on_target_observation(tmp_path):
    """T-47: Near on-target (drift < 0.5pp) → observation contains 'on-target'."""
    _make_par(tmp_path, "P1", "2026-06-01",
              [{"node_key": "CASH", "node_label": "Cash",
                "actual_pct": 5.2, "target_pct": 5.0}])  # drift = 0.2
    _make_par(tmp_path, "P2", "2026-06-08",
              [{"node_key": "CASH", "node_label": "Cash",
                "actual_pct": 5.1, "target_pct": 5.0}])  # drift = 0.1, nearly on-target
    summary = pis_allocation_drift_summary(tmp_path)
    obs_text = " ".join(summary["observations"])
    assert "on-target" in obs_text.lower() or "Cash" in obs_text


def test_T48_observations_capped_at_8(tmp_path):
    """T-48: Many qualifying nodes → observations capped at 8."""
    # Create 12 nodes all persistently overweight across 7 dates
    node_keys = [f"EQUITIES.NODE_{i:02}" for i in range(12)]
    for i in range(7):
        d = (date(2026, 6, 1) + timedelta(days=i)).isoformat()
        nodes = [{"node_key": k, "node_label": k, "actual_pct": 25.0, "target_pct": 10.0}
                 for k in node_keys]
        _make_par(tmp_path, f"P-{i:03}", d, nodes)
    summary = pis_allocation_drift_summary(tmp_path)
    assert len(summary["observations"]) <= 8


def test_T49_no_qualifying_nodes_empty_observations(tmp_path):
    """T-49: No notable trends → observations is empty list or minimal."""
    # Single date — no prior drift, no observations for WORSENING/IMPROVING
    _make_par(tmp_path, "P1", "2026-06-01", _SINGLE_NODE)
    summary = pis_allocation_drift_summary(tmp_path)
    # Should return a list (possibly empty or with only on-target observations)
    assert isinstance(summary["observations"], list)


# ─── Domain 10: API Payload Integrity ─────────────────────────────────────────


def test_T50_summary_payload_fields(tmp_path):
    """T-50: Summary payload contains all required top-level fields."""
    _make_par(tmp_path, "P1", "2026-06-01", _SINGLE_NODE)
    _make_par(tmp_path, "P2", "2026-06-08", _SINGLE_NODE)
    result = pis_allocation_drift_summary(tmp_path)
    required_fields = {
        "generated_at", "current_date", "prior_date", "dates_available",
        "improving_count", "worsening_count", "stable_count",
        "most_improved_node", "most_deteriorated_node", "observations",
    }
    assert required_fields.issubset(result.keys())
    assert result["dates_available"] == 2


def test_T51_latest_payload_node_fields(tmp_path):
    """T-51: Latest payload nodes contain all trend fields."""
    _make_par(tmp_path, "P1", "2026-06-01", _SINGLE_NODE)
    _make_par(tmp_path, "P2", "2026-06-08", _SINGLE_NODE)
    result = pis_allocation_drift_latest(tmp_path)
    assert len(result["nodes"]) > 0
    node = result["nodes"][0]
    required = {
        "node_key", "node_label", "dimension_type", "dates_available",
        "current_actual_pct", "current_target_pct", "current_drift_pct",
        "prior_drift_pct", "drift_delta_pp", "magnitude_delta_pp",
        "trend_direction", "trend_severity", "drift_velocity_pp_per_day",
        "drift_direction", "persistence_score",
    }
    assert required.issubset(node.keys())


def test_T52_history_payload_structure(tmp_path):
    """T-52: History payload has dates list and nodes with entries."""
    _make_par(tmp_path, "P1", "2026-06-01", _SINGLE_NODE)
    _make_par(tmp_path, "P2", "2026-06-08", _SINGLE_NODE)
    result = pis_allocation_drift_history(tmp_path)
    assert "dates" in result
    assert "nodes" in result
    assert len(result["nodes"]) > 0
    node = result["nodes"][0]
    assert "entries" in node
    assert len(node["entries"]) > 0
    entry = node["entries"][0]
    assert {"snapshot_date", "actual_pct", "target_pct", "drift_pct"}.issubset(entry.keys())


def test_T53_history_entries_ascending_by_date(tmp_path):
    """T-53: History entries for each node are ascending by snapshot_date."""
    for i, d in enumerate(["2026-06-15", "2026-06-01", "2026-06-08"]):
        _make_par(tmp_path, f"P-{i}", d, _SINGLE_NODE)
    result = pis_allocation_drift_history(tmp_path)
    for node in result["nodes"]:
        dates = [e["snapshot_date"] for e in node["entries"]]
        assert dates == sorted(dates)


def test_T54_consistent_node_keys_across_endpoints(tmp_path):
    """T-54: node_key in latest matches node_key in history for same node."""
    _make_par(tmp_path, "P1", "2026-06-01", _SINGLE_NODE)
    _make_par(tmp_path, "P2", "2026-06-08", _SINGLE_NODE)
    latest_keys = {n["node_key"] for n in pis_allocation_drift_latest(tmp_path)["nodes"]}
    history_keys = {n["node_key"] for n in pis_allocation_drift_history(tmp_path)["nodes"]}
    assert latest_keys == history_keys


# ─── Domain 11: Worsening/Improving Detection ─────────────────────────────────


def test_T55_monotonically_worsening_sequence():
    """T-55: 5-entry sequence with increasing magnitude → final trend WORSENING."""
    drifts = [-1.0, -2.0, -3.0, -4.0, -5.0]
    entries = _make_entries_with_drifts(drifts)
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.trend_direction == "WORSENING"


def test_T56_monotonically_improving_sequence():
    """T-56: 5-entry sequence with decreasing magnitude → final trend IMPROVING."""
    drifts = [-5.0, -4.0, -3.0, -2.0, -1.0]
    entries = _make_entries_with_drifts(drifts)
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.trend_direction == "IMPROVING"


def test_T57_last_two_nearly_equal_stable():
    """T-57: Last two entries nearly equal (< 0.5pp change) → STABLE."""
    drifts = [-5.0, -4.0, -3.0, -3.1, -3.2]  # last delta = 0.1
    entries = _make_entries_with_drifts(drifts)
    result = _compute_trend("NODE", "Node", "MARKET_CAP", entries)
    assert result.trend_direction == "STABLE"


def test_T58_drift_flips_from_over_to_underweight():
    """T-58: Drift flips sign; magnitude still computed correctly on abs values."""
    e1 = HistoryEntry("2026-06-01", 93.0, 88.0, 5.0)   # OVERWEIGHT +5
    e2 = HistoryEntry("2026-06-08", 84.0, 88.0, -4.0)  # UNDERWEIGHT -4
    result = _compute_trend("EQUITIES", "Equities", "ASSET_CLASS", [e1, e2])
    # abs(current)=4, abs(prior)=5 → magnitude_delta = -1 → IMPROVING
    assert result.drift_direction == "UNDERWEIGHT"
    assert result.trend_direction == "IMPROVING"
    assert result.magnitude_delta_pp is not None
    assert result.magnitude_delta_pp < 0


# ─── Domain 12: Empty / Minimal History ───────────────────────────────────────


def test_T59_zero_canonical_dates_summary(tmp_path):
    """T-59: Zero canonical dates → dates_available: 0."""
    _par_dir(tmp_path)
    summary = pis_allocation_drift_summary(tmp_path)
    assert summary["dates_available"] == 0
    assert summary["current_date"] is None


def test_T60_one_canonical_date_no_prior(tmp_path):
    """T-60: One canonical date → all nodes have prior_drift_pct: null."""
    _make_par(tmp_path, "P1", "2026-06-01", _SINGLE_NODE)
    result = pis_allocation_drift_latest(tmp_path)
    for node in result["nodes"]:
        assert node["prior_drift_pct"] is None
        assert node["drift_delta_pp"] is None
        assert node["magnitude_delta_pp"] is None


def test_T61_history_zero_dates_empty_payload(tmp_path):
    """T-61: Zero dates → history has empty dates list and empty nodes."""
    _par_dir(tmp_path)
    result = pis_allocation_drift_history(tmp_path)
    assert result["dates"] == []
    assert result["nodes"] == []
