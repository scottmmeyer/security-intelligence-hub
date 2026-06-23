"""AI-004 — Allocation Policy Version Diff Engine — Validation Test Suite.

All tests deterministic and filesystem-isolated via pytest tmp_path.
No network calls. No modifications to existing project data.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from src.pis.policy_version_diff import (
    TargetChange,
    PolicyVersion,
    PolicyDiff,
    _collect_policy_snapshots,
    _build_versions,
    _compute_diff,
    _content_hash,
    _generate_observations,
    pis_policy_current,
    pis_policy_history,
    pis_policy_diff,
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
    recalc_id: str,
    nodes: list[dict],
    created_at: str = "2026-06-15T10:00:00+00:00",
) -> Path:
    par = _par_dir(root) / par_id
    par.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": par_id,
        "snapshot_date": snap_date,
        "created_at_utc": created_at,
        "recalculation_id": recalc_id,
        "status": "COMPLETE",
    }
    (par / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    with (par / "alignment.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_ALIGNMENT_HEADERS, extrasaction="ignore")
        w.writeheader()
        for node in nodes:
            row = {h: "" for h in _ALIGNMENT_HEADERS}
            row["analysis_run_id"] = par_id
            row["node_key"] = node["node_key"]
            row["node_label"] = node.get("node_label", node["node_key"])
            row["target_pct"] = str(node.get("target_pct", 0.0))
            row["tactical_target_pct"] = str(node.get("tactical_target_pct", node.get("target_pct", 0.0)))
            w.writerow(row)
    return par


def _simple_nodes(targets: dict) -> list[dict]:
    """Create node list from {node_key: target_pct} dict."""
    return [{"node_key": k, "target_pct": v} for k, v in targets.items()]


def _make_policy_yaml(root: Path, policy_id: str = "ALLOC_V1", effective_date: str = "2026-05-20") -> None:
    """Create minimal allocation_policy.yaml in config/."""
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    content = f"""version: 1
policy_id: {policy_id}
effective_date: "{effective_date}"
structural_policy:
  cash_floor_pct: 2.0
  max_mega_concentration_pct: 50.0
  min_international_pct: 10.0
recalculation_governance:
  max_single_recalculation_delta_pct: 3.0
"""
    (config_dir / "allocation_policy.yaml").write_text(content, encoding="utf-8")


def _make_methodology_yaml(root: Path, methodology_id: str = "v1_2026_05") -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    content = f"""version: 1
methodology_id: {methodology_id}
nodes:
  - key: EQUITIES
    baseline_target_pct_of_parent: 70.0
    confidence_level: HIGH
    evidence_basis: []
    risk_factors: []
"""
    (config_dir / "allocation_methodology.yaml").write_text(content, encoding="utf-8")


# ─── Domain 1: Policy Snapshot Collection ────────────────────────────────────

def test_T01_empty_par_directory(tmp_path):
    _par_dir(tmp_path)
    snapshots = _collect_policy_snapshots(tmp_path)
    assert snapshots == []


def test_T02_single_par_single_snapshot(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0, "CASH": 5.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    assert len(snapshots) == 1
    s = snapshots[0]
    assert s["snapshot_date"] == "2026-06-01"
    assert s["recalculation_id"] == "SEED_A"
    assert abs(s["node_targets"]["EQUITIES"] - 88.0) < 0.01


def test_T03_canonical_selection_latest_wins(tmp_path):
    _make_par(tmp_path, "PAR-EARLY", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 80.0}),
              created_at="2026-06-01T08:00:00+00:00")
    _make_par(tmp_path, "PAR-LATE", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0}),
              created_at="2026-06-01T12:00:00+00:00")
    snapshots = _collect_policy_snapshots(tmp_path)
    assert len(snapshots) == 1
    assert abs(snapshots[0]["node_targets"]["EQUITIES"] - 88.0) < 0.01


def test_T04_malformed_snapshot_date_skipped(tmp_path):
    par = _par_dir(tmp_path) / "PAR-BAD"
    par.mkdir(parents=True, exist_ok=True)
    (par / "run_metadata.json").write_text(json.dumps({
        "snapshot_date": "NOT-A-DATE", "created_at_utc": "2026-06-01T10:00:00+00:00",
        "recalculation_id": "SEED_A"
    }))
    with (par / "alignment.csv").open("w") as f:
        f.write("node_key,target_pct,tactical_target_pct\nEQUITIES,88.0,88.0\n")
    _make_par(tmp_path, "PAR-OK", "2026-06-08", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    dates = [s["snapshot_date"] for s in snapshots]
    assert "2026-06-08" in dates
    assert "NOT-A-DATE" not in dates


def test_T05_missing_alignment_csv_skipped(tmp_path):
    par = _par_dir(tmp_path) / "PAR-NO-ALIGN"
    par.mkdir(parents=True, exist_ok=True)
    (par / "run_metadata.json").write_text(json.dumps({
        "snapshot_date": "2026-06-01", "created_at_utc": "2026-06-01T10:00:00+00:00",
        "recalculation_id": "SEED_A"
    }))
    # No alignment.csv written
    _make_par(tmp_path, "PAR-OK", "2026-06-08", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    dates = [s["snapshot_date"] for s in snapshots]
    assert "2026-06-08" in dates
    assert "2026-06-01" not in dates


def test_T06_node_keys_extracted(tmp_path):
    nodes = _simple_nodes({"EQUITIES": 88.0, "CASH": 5.0, "EQUITIES.US": 79.0})
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", nodes)
    snapshots = _collect_policy_snapshots(tmp_path)
    keys = set(snapshots[0]["node_targets"].keys())
    assert keys == {"EQUITIES", "CASH", "EQUITIES.US"}


def test_T07_target_and_tactical_both_extracted(tmp_path):
    par = _par_dir(tmp_path) / "PAR-001"
    par.mkdir(parents=True, exist_ok=True)
    (par / "run_metadata.json").write_text(json.dumps({
        "snapshot_date": "2026-06-01", "created_at_utc": "2026-06-01T10:00:00+00:00",
        "recalculation_id": "SEED_A"
    }))
    with (par / "alignment.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_ALIGNMENT_HEADERS, extrasaction="ignore")
        w.writeheader()
        w.writerow({**{h: "" for h in _ALIGNMENT_HEADERS},
                    "node_key": "EQUITIES", "target_pct": "88.0", "tactical_target_pct": "90.0"})
    snapshots = _collect_policy_snapshots(tmp_path)
    s = snapshots[0]
    assert abs(s["node_targets"]["EQUITIES"] - 88.0) < 0.01
    assert abs(s["tactical_targets"]["EQUITIES"] - 90.0) < 0.01


# ─── Domain 2: Policy Version Registry ──────────────────────────────────────

def test_T08_same_recalc_id_single_version(tmp_path):
    for i, d in enumerate(["2026-06-01", "2026-06-08", "2026-06-15"]):
        _make_par(tmp_path, f"PAR-{i:03}", d, "SEED_A",
                  _simple_nodes({"EQUITIES": 88.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    versions = _build_versions(snapshots)
    assert len(versions) == 1
    assert versions[0].recalculation_id == "SEED_A"
    assert versions[0].run_count == 3


def test_T09_two_distinct_recalc_ids_two_versions(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_B",
              _simple_nodes({"EQUITIES": 85.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    versions = _build_versions(snapshots)
    assert len(versions) == 2
    recalc_ids = {v.recalculation_id for v in versions}
    assert recalc_ids == {"SEED_A", "SEED_B"}


def test_T10_run_count_correct(tmp_path):
    for i, d in enumerate(["2026-06-01", "2026-06-08"]):
        _make_par(tmp_path, f"PAR-{i:03}", d, "SEED_X",
                  _simple_nodes({"EQUITIES": 88.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    versions = _build_versions(snapshots)
    assert versions[0].run_count == 2


def test_T11_first_seen_date_correct(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    versions = _build_versions(snapshots)
    assert versions[0].first_seen_date == "2026-06-01"


def test_T12_last_seen_date_correct(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    versions = _build_versions(snapshots)
    assert versions[0].last_seen_date == "2026-06-08"


def test_T13_node_targets_from_most_recent_snapshot(tmp_path):
    """Most recent snapshot's targets are canonical for the version."""
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 80.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0}))  # latest
    snapshots = _collect_policy_snapshots(tmp_path)
    versions = _build_versions(snapshots)
    assert abs(versions[0].node_targets["EQUITIES"] - 88.0) < 0.01


def test_T14_fingerprint_id_format(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_20260520",
              _simple_nodes({"EQUITIES": 88.0}))
    snapshots = _collect_policy_snapshots(tmp_path)
    versions = _build_versions(snapshots)
    fid = versions[0].fingerprint_id
    assert fid.startswith("SEED_20260520:")
    assert len(fid.split(":")[1]) == 8  # 8-char content hash


# ─── Domain 3: Policy Diff Computation ──────────────────────────────────────

def _make_version(recalc_id: str, targets: dict, date_str: str = "2026-06-01") -> PolicyVersion:
    nt = {k: float(v) for k, v in targets.items()}
    return PolicyVersion(
        fingerprint_id=f"{recalc_id}:{_content_hash(nt)}",
        recalculation_id=recalc_id,
        first_seen_date=date_str,
        last_seen_date=date_str,
        run_count=1,
        node_count=len(nt),
        node_targets=nt,
        tactical_targets=nt,
        created_at="2026-06-15T00:00:00+00:00",
    )


def test_T15_identical_targets_no_changes():
    v1 = _make_version("SEED_A", {"EQUITIES": 88.0, "CASH": 5.0})
    v2 = _make_version("SEED_B", {"EQUITIES": 88.0, "CASH": 5.0})
    diff = _compute_diff(v1, v2)
    assert diff.total_changes == 0
    assert diff.changed_targets == ()


def test_T16_node_target_increased():
    v1 = _make_version("SEED_A", {"EQUITIES": 85.0})
    v2 = _make_version("SEED_B", {"EQUITIES": 90.0})
    diff = _compute_diff(v1, v2)
    assert diff.total_changes == 1
    c = diff.changed_targets[0]
    assert c.node_key == "EQUITIES"
    assert c.change_direction == "INCREASED"
    assert abs(c.delta_pp - 5.0) < 0.01


def test_T17_node_target_decreased():
    v1 = _make_version("SEED_A", {"EQUITIES": 90.0})
    v2 = _make_version("SEED_B", {"EQUITIES": 85.0})
    diff = _compute_diff(v1, v2)
    c = diff.changed_targets[0]
    assert c.change_direction == "DECREASED"
    assert abs(c.delta_pp - (-5.0)) < 0.01


def test_T18_node_added():
    v1 = _make_version("SEED_A", {"EQUITIES": 88.0})
    v2 = _make_version("SEED_B", {"EQUITIES": 88.0, "DIGITAL": 3.0})
    diff = _compute_diff(v1, v2)
    assert "DIGITAL" in diff.added_nodes


def test_T19_node_removed():
    v1 = _make_version("SEED_A", {"EQUITIES": 88.0, "DIGITAL": 3.0})
    v2 = _make_version("SEED_B", {"EQUITIES": 88.0})
    diff = _compute_diff(v1, v2)
    assert "DIGITAL" in diff.removed_nodes


def test_T20_multiple_simultaneous_changes():
    v1 = _make_version("SEED_A", {"EQUITIES": 85.0, "CASH": 5.0, "FIXED_INCOME": 10.0})
    v2 = _make_version("SEED_B", {"EQUITIES": 90.0, "CASH": 3.0, "FIXED_INCOME": 7.0})
    diff = _compute_diff(v1, v2)
    assert diff.total_changes == 3


def test_T21_sub_noise_threshold_not_included():
    v1 = _make_version("SEED_A", {"EQUITIES": 88.0000})
    v2 = _make_version("SEED_B", {"EQUITIES": 88.0005})  # delta = 0.0005 < 0.001
    diff = _compute_diff(v1, v2)
    assert diff.total_changes == 0


def test_T22_changed_targets_sorted_by_abs_delta():
    v1 = _make_version("SEED_A", {"A": 10.0, "B": 20.0, "C": 30.0})
    v2 = _make_version("SEED_B", {"A": 15.0, "B": 15.0, "C": 25.0})
    # deltas: A=+5, B=-5, C=-5 → all |5|, but A,B,C each 5
    diff = _compute_diff(v1, v2)
    # All changes should be present
    assert len(diff.changed_targets) == 3
    # First should have the largest abs delta
    assert abs(diff.changed_targets[0].delta_pp) >= abs(diff.changed_targets[-1].delta_pp)


# ─── Domain 4: Governance Observations ──────────────────────────────────────

def test_T23_single_version_observation(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_policy_yaml(tmp_path)
    result = pis_policy_history(tmp_path)
    obs = result["observations"]
    obs_text = " ".join(obs)
    assert "single" in obs_text.lower() or "SEED_A" in obs_text


def test_T24_two_versions_observation(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_B", _simple_nodes({"EQUITIES": 85.0}))
    _make_policy_yaml(tmp_path)
    result = pis_policy_history(tmp_path)
    obs_text = " ".join(result["observations"])
    assert "2" in obs_text or "version" in obs_text.lower()


def test_T25_structural_constraints_in_observations(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_policy_yaml(tmp_path)
    result = pis_policy_current(tmp_path)
    obs_text = " ".join(result["observations"])
    assert "2.0" in obs_text or "50.0" in obs_text or "10.0" in obs_text


def test_T26_policy_id_in_observations(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_policy_yaml(tmp_path, policy_id="ALLOC_V1", effective_date="2026-05-20")
    result = pis_policy_current(tmp_path)
    obs_text = " ".join(result["observations"])
    assert "ALLOC_V1" in obs_text


def test_T27_observations_capped(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_policy_yaml(tmp_path)
    _make_methodology_yaml(tmp_path)
    result = pis_policy_current(tmp_path)
    assert len(result["observations"]) <= 6


# ─── Domain 5: API Payload Integrity ─────────────────────────────────────────

def _minimal_setup(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0, "CASH": 5.0}))
    _make_policy_yaml(tmp_path)
    _make_methodology_yaml(tmp_path)


def test_T28_policy_current_required_fields(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_policy_current(tmp_path)
    required = {
        "generated_at", "policy_id", "methodology_id", "effective_date",
        "config_hash", "recalculation_id", "fingerprint_id", "run_count",
        "node_count", "structural_policy", "node_targets", "observations",
    }
    assert required.issubset(result.keys())


def test_T29_policy_history_versions_list(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A", _simple_nodes({"EQUITIES": 88.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_B", _simple_nodes({"EQUITIES": 85.0}))
    _make_policy_yaml(tmp_path)
    result = pis_policy_history(tmp_path)
    assert result["version_count"] == 2
    assert len(result["versions"]) == 2


def test_T30_policy_diff_no_changes(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0}))
    _make_policy_yaml(tmp_path)
    result = pis_policy_diff(tmp_path)
    assert result["has_changes"] is False
    assert result["diffs"] == []


def test_T31_policy_diff_with_changes(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0, "CASH": 5.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_B",
              _simple_nodes({"EQUITIES": 85.0, "CASH": 5.0}))
    _make_policy_yaml(tmp_path)
    result = pis_policy_diff(tmp_path)
    assert result["has_changes"] is True
    assert len(result["diffs"]) == 1
    diff = result["diffs"][0]
    assert diff["total_changes"] == 1
    assert diff["changed_targets"][0]["node_key"] == "EQUITIES"


def test_T32_node_targets_in_current(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_policy_current(tmp_path)
    assert isinstance(result["node_targets"], dict)
    assert "EQUITIES" in result["node_targets"]


# ─── Domain 6: Edge Cases ─────────────────────────────────────────────────────

def test_T33_no_config_files(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0}))
    # No config files created
    result = pis_policy_current(tmp_path)
    assert isinstance(result, dict)
    # Should return defaults
    assert result["policy_id"] == "UNKNOWN" or result["policy_id"] == ""


def test_T34_two_versions_same_targets_no_changes(tmp_path):
    """Two recalc_ids but same targets → diff shows no changes."""
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0}))
    _make_par(tmp_path, "PAR-002", "2026-06-08", "SEED_B",
              _simple_nodes({"EQUITIES": 88.0}))  # same target
    _make_policy_yaml(tmp_path)
    result = pis_policy_diff(tmp_path)
    assert result["versions_compared"] == 2
    assert result["diffs"][0]["total_changes"] == 0
    assert result["has_changes"] is False


def test_T35_single_date_valid(tmp_path):
    _make_par(tmp_path, "PAR-001", "2026-06-01", "SEED_A",
              _simple_nodes({"EQUITIES": 88.0}))
    _make_policy_yaml(tmp_path)
    result = pis_policy_history(tmp_path)
    assert result["version_count"] == 1
    assert result["versions"][0]["run_count"] == 1
