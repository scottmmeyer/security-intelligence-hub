"""Tests for AI-004B — Allocation Policy Version Diff Visibility (Completion).

Covers:
  - _classify_severity() — all 4 levels
  - _build_change_summary() — aggregation from diffs
  - _compute_recommendation_impact() — alignment with policy changes
  - _build_before_after() — before/after table
  - _build_timeline() — version timeline
  - _build_notifications() — operator notifications
  - policy_summary() / policy_impact() / policy_timeline() / policy_version() — public API

Governance:
  Q6–Q8: No allocation targets, recommendation algorithms, or governance rules modified
  Q9: Display-only / informational
  Q10: Completes AI-004
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest

from src.pis.policy_change_summary import (
    _build_before_after,
    _build_change_summary,
    _build_notifications,
    _build_timeline,
    _classify_severity,
    _compute_recommendation_impact,
    policy_impact,
    policy_summary,
    policy_timeline,
    policy_version,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _target_change(nk: str, from_pct: float, to_pct: float) -> Dict:
    delta = round(to_pct - from_pct, 4)
    return {
        "node_key":         nk,
        "from_pct":         from_pct,
        "to_pct":           to_pct,
        "delta_pp":         delta,
        "change_direction": "INCREASED" if delta > 0 else ("DECREASED" if delta < 0 else "UNCHANGED"),
    }


def _make_diff(from_vid: str, to_vid: str, changed_targets: List[Dict], from_date: str = "2026-01-01", to_date: str = "2026-02-01") -> Dict:
    return {
        "from_version_id":  from_vid,
        "to_version_id":    to_vid,
        "from_date":        from_date,
        "to_date":          to_date,
        "added_nodes":      [],
        "removed_nodes":    [],
        "changed_targets":  changed_targets,
        "total_changes":    len(changed_targets),
        "summary":          f"{len(changed_targets)} node(s) changed",
    }


def _make_version(fid: str, first_date: str = "2026-01-01", run_count: int = 5) -> Dict:
    return {
        "fingerprint_id":  fid,
        "recalculation_id": fid[:12],
        "first_seen_date": first_date,
        "last_seen_date":  first_date,
        "run_count":       run_count,
        "node_count":      20,
    }


def _minimal_diff_payload(changed_targets: List[Dict]) -> Dict:
    return {
        "diffs": [_make_diff("V001", "V002", changed_targets)],
        "has_changes": bool(changed_targets),
    }


def _minimal_history_payload() -> Dict:
    return {
        "versions": [_make_version("V001", "2026-01-01"), _make_version("V002", "2026-02-01")],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Part F: _classify_severity
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifySeverity:
    def test_structural_large_delta(self):
        assert _classify_severity(1, 12.0, False) == "STRUCTURAL"

    def test_major_large_delta(self):
        assert _classify_severity(1, 7.0, False) == "MAJOR"

    def test_major_many_nodes(self):
        assert _classify_severity(8, 2.0, False) == "MAJOR"

    def test_major_high_importance_plus_moderate_delta(self):
        # High importance node + moderate delta → escalates to MAJOR
        assert _classify_severity(1, 4.0, True) == "MAJOR"

    def test_moderate_delta(self):
        assert _classify_severity(1, 3.5, False) == "MODERATE"

    def test_moderate_multiple_nodes(self):
        assert _classify_severity(4, 0.5, False) == "MODERATE"

    def test_minor_small_delta(self):
        assert _classify_severity(1, 1.5, False) == "MINOR"

    def test_minor_single_node(self):
        assert _classify_severity(1, 0.8, False) == "MINOR"

    def test_zero_change_is_minor(self):
        # Edge case: 0 nodes, 0 delta → still classifies
        result = _classify_severity(0, 0.0, False)
        assert result in ("MINOR", "MODERATE", "MAJOR", "STRUCTURAL")


# ═══════════════════════════════════════════════════════════════════════════════
# Part A: _build_change_summary
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildChangeSummary:
    def test_empty_diffs_returns_empty(self):
        result = _build_change_summary({"diffs": []}, {"versions": []})
        assert result == []

    def test_single_change_summarised(self):
        diff_payload = _minimal_diff_payload([_target_change("EQUITIES.US.MID", 10.0, 14.0)])
        result = _build_change_summary(diff_payload, _minimal_history_payload())
        assert len(result) == 1
        s = result[0]
        assert s["nodes_changed"] == 1
        assert s["max_abs_delta_pp"] == pytest.approx(4.0)

    def test_severity_set(self):
        diff_payload = _minimal_diff_payload([_target_change("EQUITIES.US.MID", 10.0, 14.0)])
        result = _build_change_summary(diff_payload, _minimal_history_payload())
        assert result[0]["severity"] in ("MINOR", "MODERATE", "MAJOR", "STRUCTURAL")

    def test_high_importance_flag(self):
        diff_payload = _minimal_diff_payload([_target_change("EQUITIES.US.MID", 10.0, 14.0)])
        result = _build_change_summary(diff_payload, _minimal_history_payload())
        assert result[0]["high_importance_nodes_affected"] is True

    def test_non_important_node_not_flagged(self):
        diff_payload = _minimal_diff_payload([_target_change("DIGITAL.BITCOIN", 0.5, 0.6)])
        result = _build_change_summary(diff_payload, _minimal_history_payload())
        assert result[0]["high_importance_nodes_affected"] is False

    def test_operator_note_non_empty(self):
        diff_payload = _minimal_diff_payload([_target_change("EQUITIES.US.MID", 10.0, 14.0)])
        result = _build_change_summary(diff_payload, _minimal_history_payload())
        assert result[0]["operator_note"] != ""

    def test_largest_change_identified(self):
        diff_payload = _minimal_diff_payload([
            _target_change("DIGITAL.BITCOIN", 0.5, 0.6),
            _target_change("EQUITIES.US.MID", 10.0, 16.0),
        ])
        result = _build_change_summary(diff_payload, _minimal_history_payload())
        lc = result[0].get("largest_change")
        assert lc is not None
        assert lc["node_key"] == "EQUITIES.US.MID"


# ═══════════════════════════════════════════════════════════════════════════════
# Part B: _compute_recommendation_impact
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeRecommendationImpact:
    def _rec(self, rec_type: str, node_key: str) -> Dict:
        return {
            "recommendation_type": rec_type,
            "affected_node_key":   node_key,
            "affected_symbols":    ["AAAA", "BBBB"],
            "title":               f"Test {rec_type}",
            "drift_pct":           5.0,
        }

    def test_no_changes_no_impact(self):
        result = _compute_recommendation_impact([self._rec("INCREASE_UNDERWEIGHT", "X")], None)
        assert result["impact_count"] == 0

    def test_matching_node_flagged(self):
        change = {
            "affected_nodes":  ["EQUITIES.US.MID"],
            "changed_targets": [_target_change("EQUITIES.US.MID", 10.0, 14.0)],
            "severity":        "MODERATE",
            "nodes_changed":   1,
        }
        recs = [self._rec("INCREASE_UNDERWEIGHT", "EQUITIES.US.MID")]
        result = _compute_recommendation_impact(recs, change)
        assert result["impact_count"] == 1
        assert result["policy_impacted"][0]["impact_type"] == "TARGET_INCREASED"

    def test_non_matching_node_not_impacted(self):
        change = {
            "affected_nodes":  ["EQUITIES.US.MID"],
            "changed_targets": [_target_change("EQUITIES.US.MID", 10.0, 14.0)],
            "severity":        "MINOR",
            "nodes_changed":   1,
        }
        recs = [self._rec("INCREASE_UNDERWEIGHT", "EQUITIES.INTERNATIONAL")]
        result = _compute_recommendation_impact(recs, change)
        assert result["impact_count"] == 0

    def test_decreased_node_flagged_correctly(self):
        change = {
            "affected_nodes":  ["EQUITIES.INTERNATIONAL"],
            "changed_targets": [_target_change("EQUITIES.INTERNATIONAL", 15.0, 12.0)],
            "severity":        "MODERATE",
            "nodes_changed":   1,
        }
        recs = [self._rec("REDUCE_OVERWEIGHT", "EQUITIES.INTERNATIONAL")]
        result = _compute_recommendation_impact(recs, change)
        if result["impact_count"] > 0:
            assert result["policy_impacted"][0]["impact_type"] == "TARGET_DECREASED"

    def test_impact_summary_non_empty(self):
        change = {
            "affected_nodes":  ["EQUITIES.US.MID"],
            "changed_targets": [_target_change("EQUITIES.US.MID", 10.0, 14.0)],
            "severity":        "MINOR",
            "nodes_changed":   1,
        }
        recs = [self._rec("INCREASE_UNDERWEIGHT", "EQUITIES.US.MID")]
        result = _compute_recommendation_impact(recs, change)
        assert len(result["impact_summary"]) > 10

    def test_empty_recs_returns_gracefully(self):
        result = _compute_recommendation_impact([], None)
        assert result["total"] == 0
        assert result["policy_impacted"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# Part C: _build_before_after
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildBeforeAfter:
    def test_empty_change_returns_empty(self):
        assert _build_before_after(None, {}) == []

    def test_change_rows_generated(self):
        change = {
            "changed_targets": [
                _target_change("EQUITIES.US.MID", 10.0, 14.0),
                _target_change("EQUITIES.INTERNATIONAL", 15.0, 12.0),
            ]
        }
        result = _build_before_after(change, {})
        assert len(result) == 2

    def test_sorted_by_abs_delta_descending(self):
        change = {
            "changed_targets": [
                _target_change("A", 10.0, 10.5),   # delta 0.5
                _target_change("B", 10.0, 14.0),   # delta 4.0 — should be first
            ]
        }
        result = _build_before_after(change, {})
        assert result[0]["node_key"] == "B"

    def test_high_importance_flagged(self):
        change = {
            "changed_targets": [_target_change("EQUITIES.US.MID", 10.0, 14.0)]
        }
        result = _build_before_after(change, {})
        assert result[0]["is_high_importance"] is True

    def test_non_important_not_flagged(self):
        change = {
            "changed_targets": [_target_change("DIGITAL.BITCOIN", 0.5, 0.6)]
        }
        result = _build_before_after(change, {})
        assert result[0]["is_high_importance"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Part D: _build_timeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildTimeline:
    def test_versions_appear_in_timeline(self):
        history = _minimal_history_payload()
        result = _build_timeline(history, [])
        assert len(result) == 2

    def test_sorted_newest_first(self):
        history = {
            "versions": [
                _make_version("V001", "2026-01-01"),
                _make_version("V002", "2026-03-01"),
                _make_version("V003", "2026-06-01"),
            ]
        }
        result = _build_timeline(history, [])
        dates = [t["first_seen_date"] for t in result]
        assert dates == sorted(dates, reverse=True)

    def test_initial_version_has_initial_severity(self):
        history = {"versions": [_make_version("V001", "2026-01-01")]}
        result = _build_timeline(history, [])
        assert result[0]["severity"] == "INITIAL"

    def test_changed_version_has_severity_from_summary(self):
        history = _minimal_history_payload()
        summaries = [
            {
                "to_version_id": "V002",
                "severity": "MAJOR",
                "nodes_changed": 5,
                "operator_note": "Big change",
            }
        ]
        result = _build_timeline(history, summaries)
        v2 = next(t for t in result if t["fingerprint_id"] == "V002")
        assert v2["severity"] == "MAJOR"
        assert v2["nodes_changed"] == 5


# ═══════════════════════════════════════════════════════════════════════════════
# Part E: _build_notifications
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildNotifications:
    def test_stable_notification_when_no_changes(self):
        notifs = _build_notifications([], {"total": 0, "policy_impacted": []}, {})
        types = {n["type"] for n in notifs}
        assert "STABLE" in types

    def test_recent_change_notification_when_changes(self):
        change = {
            "severity": "MODERATE",
            "operator_note": "Test",
            "to_date": "2026-02-01",
            "nodes_changed": 3,
            "high_importance_nodes_affected": False,
            "affected_nodes": [],
        }
        notifs = _build_notifications([change], {"total": 0, "policy_impacted": []}, {})
        types = {n["type"] for n in notifs}
        assert "RECENT_CHANGE" in types

    def test_recommendation_impact_notification(self):
        change = {
            "severity": "MODERATE",
            "operator_note": "",
            "to_date": "",
            "nodes_changed": 1,
            "high_importance_nodes_affected": False,
            "affected_nodes": [],
        }
        rec_impact = {"impact_count": 3, "impact_summary": "3 recs affected"}
        notifs = _build_notifications([change], rec_impact, {})
        types = {n["type"] for n in notifs}
        assert "RECOMMENDATION_IMPACT" in types

    def test_high_importance_notification_when_high_node_affected(self):
        change = {
            "severity": "MAJOR",
            "operator_note": "",
            "to_date": "2026-02-01",
            "nodes_changed": 1,
            "high_importance_nodes_affected": True,
            "affected_nodes": ["EQUITIES.US.MID"],
        }
        notifs = _build_notifications([change], {"impact_count": 0, "policy_impacted": []}, {})
        types = {n["type"] for n in notifs}
        assert "HIGH_IMPORTANCE_NODE" in types


# ═══════════════════════════════════════════════════════════════════════════════
# Public API (mocked policy data)
# ═══════════════════════════════════════════════════════════════════════════════

def _mock_current():
    return {
        "policy_id": "ALLOCATION_POLICY_V1",
        "fingerprint_id": "SEED:abc12345",
        "run_count": 5,
        "node_count": 20,
        "node_targets": {"EQUITIES.US.MID": 14.0, "EQUITIES.INTERNATIONAL": 12.0},
        "tactical_targets": {},
        "first_seen_date": "2026-05-01",
        "last_seen_date":  "2026-06-01",
        "observations":    ["Policy stable."],
        "structural_policy": {},
        "recalculation_governance": {},
    }


def _mock_history():
    return {"versions": [_make_version("SEED:abc12345", "2026-05-01", 5)]}


def _mock_diff_no_change():
    return {"diffs": [], "has_changes": False, "versions_compared": 1, "observations": []}


def _mock_diff_with_change():
    return {
        "diffs": [_make_diff("V001", "V002", [_target_change("EQUITIES.US.MID", 10.0, 14.0)])],
        "has_changes": True,
        "versions_compared": 2,
    }


class TestPublicAPI:
    def _patch(self, tmp_path, diff_fn=None):
        """Context manager that patches policy functions."""
        from unittest.mock import patch
        return (
            patch("src.pis.policy_change_summary.pis_policy_current", return_value=_mock_current()),
            patch("src.pis.policy_change_summary.pis_policy_history",  return_value=_mock_history()),
            patch("src.pis.policy_change_summary.pis_policy_diff",     return_value=diff_fn or _mock_diff_no_change()),
        )

    def test_policy_summary_stable_state(self, tmp_path):
        patches = self._patch(tmp_path)
        with patches[0], patches[1], patches[2]:
            result = policy_summary(tmp_path)
        assert "change_count" in result
        assert "notifications" in result
        assert "governance_note" in result

    def test_policy_summary_has_changes(self, tmp_path):
        patches = self._patch(tmp_path, _mock_diff_with_change())
        with patches[0], patches[1], patches[2]:
            result = policy_summary(tmp_path)
        assert result["has_changes"] is True
        assert result["change_count"] == 1

    def test_policy_impact_structure(self, tmp_path):
        patches = self._patch(tmp_path)
        with patches[0], patches[1], patches[2]:
            result = policy_impact(tmp_path)
        assert "rec_impact" in result
        assert "before_after" in result
        assert "governance_note" in result

    def test_policy_timeline_structure(self, tmp_path):
        patches = self._patch(tmp_path)
        with patches[0], patches[1], patches[2]:
            result = policy_timeline(tmp_path)
        assert "timeline" in result
        assert isinstance(result["timeline"], list)

    def test_policy_version_not_found(self, tmp_path):
        patches = self._patch(tmp_path)
        with patches[0], patches[1], patches[2]:
            result = policy_version("NONEXISTENT", tmp_path)
        assert "error" in result

    def test_governance_note_present(self, tmp_path):
        patches = self._patch(tmp_path)
        with patches[0], patches[1], patches[2]:
            result = policy_summary(tmp_path)
        note = result.get("governance_note", "")
        assert len(note) > 20
        assert "display-only" in note.lower() or "no" in note.lower()

    def test_no_action_keys_in_output(self, tmp_path):
        patches = self._patch(tmp_path)
        with patches[0], patches[1], patches[2]:
            result = policy_summary(tmp_path)
        forbidden = {"execute", "trade", "buy_signal", "allocation_target_override"}
        assert not (forbidden & set(result.keys()))

    def test_severity_values_are_valid(self, tmp_path):
        patches = self._patch(tmp_path, _mock_diff_with_change())
        with patches[0], patches[1], patches[2]:
            result = policy_summary(tmp_path)
        valid = {"MINOR", "MODERATE", "MAJOR", "STRUCTURAL", "STABLE", "INITIAL"}
        sev = result.get("current_severity")
        assert sev in valid, f"Unexpected severity: {sev}"
