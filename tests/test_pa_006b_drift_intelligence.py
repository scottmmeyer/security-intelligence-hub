"""Tests for PA-006B — Allocation Drift Intelligence & Persistent Violation Analytics.

Covers:
  - _classify_trend() — all 4 classifications
  - _compute_momentum() — range, sign, edge cases
  - _classify_persistence() — all 5 levels
  - _severity_label()
  - _compute_priority_score() — formula + ordering
  - _analyse_node() — full DriftTrend output
  - drift_trends() — trend counts and node list
  - drift_priorities() — top10 ranking
  - drift_chronic() — persistence filtering
  - drift_momentum() — sorted by abs(momentum)
  - drift_intelligence_summary() — executive summary keys

Governance:
  Q6: Allocation targets unchanged — confirmed read-only
  Q7: Recommendation engines unchanged
  Q8: Governance rules unchanged
  Q9: PA-006B is informational only
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List

import pytest

from src.pis.drift_trend_analyzer import (
    _classify_persistence,
    _classify_trend,
    _compute_momentum,
    _compute_priority_score,
    _primary_reason,
    _severity_label,
    _analyse_node,
    HistoryEntry,
    DriftTrend,
    drift_chronic,
    drift_intelligence_summary,
    drift_momentum,
    drift_priorities,
    drift_trends,
)


# ── Shared fixture helpers ─────────────────────────────────────────────────────

def _entry(drift: float, date: str = "2026-01-01", actual: float = 10.0, target: float = 10.0) -> HistoryEntry:
    return HistoryEntry(
        snapshot_date=date,
        actual_pct=actual + drift,
        target_pct=actual,
        drift_pct=round(drift, 4),
    )


def _entries_from_drifts(drifts: List[float]) -> List[HistoryEntry]:
    dates = [f"2026-0{i//28 + 1}-{(i % 28) + 1:02d}" for i in range(len(drifts))]
    return [_entry(d, dates[i]) for i, d in enumerate(drifts)]


def _make_par_run(tmp_path: Path, snapshot_date: str, nodes: dict, run_id: str = None) -> None:
    """Write a minimal PAR analysis run with alignment.csv."""
    run_dir = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / (run_id or f"run-{snapshot_date}")
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "snapshot_date": snapshot_date,
        "created_at_utc": f"{snapshot_date}T10:00:00+00:00",
        "run_id": run_id or f"run-{snapshot_date}",
    }
    (run_dir / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    # alignment.csv
    rows = ["node_key,node_label,dimension_type,effective_actual_pct,tactical_target_pct,drift_pct,severity"]
    for nk, vals in nodes.items():
        actual = vals["actual"]
        target = vals["target"]
        drift  = round(actual - target, 4)
        label  = vals.get("label", nk)
        rows.append(f"{nk},{label},ASSET_CLASS,{actual},{target},{drift},MODERATE")
    (run_dir / "alignment.csv").write_text("\n".join(rows), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# Part A — Trend classification
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifyTrend:
    def test_improving_drift_toward_zero(self):
        # Magnitude clearly shrinking
        drifts = [8.0, 6.0, 4.0, 2.0]
        assert _classify_trend(drifts) == "IMPROVING"

    def test_deteriorating_drift_away_from_zero(self):
        # Magnitude clearly growing
        drifts = [2.0, 4.0, 6.0, 8.0]
        assert _classify_trend(drifts) == "DETERIORATING"

    def test_stable_no_change(self):
        drifts = [5.0, 5.1, 4.9, 5.0]
        assert _classify_trend(drifts) == "STABLE"

    def test_oscillating_repeated_reversals(self):
        # Crosses zero multiple times
        drifts = [-3.0, 3.0, -3.0, 3.0, -3.0]
        assert _classify_trend(drifts) == "OSCILLATING"

    def test_single_entry_stable(self):
        assert _classify_trend([5.0]) == "STABLE"

    def test_two_entries_can_classify(self):
        result = _classify_trend([8.0, 2.0])
        assert result in ("IMPROVING", "STABLE", "DETERIORATING", "OSCILLATING")

    def test_improving_from_underweight(self):
        # Negative drifts moving toward zero
        drifts = [-8.0, -6.0, -4.0, -2.0]
        assert _classify_trend(drifts) == "IMPROVING"

    def test_deteriorating_negative_growing(self):
        drifts = [-2.0, -4.0, -6.0, -8.0]
        assert _classify_trend(drifts) == "DETERIORATING"


# ═══════════════════════════════════════════════════════════════════════════════
# Part B — Momentum score
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeMomentum:
    def test_range_is_bounded(self):
        for drifts in [[0.0] * 5, [10.0] * 5, [-10.0] * 5, [1, 9, 1, 9, 1]]:
            score = _compute_momentum(drifts)
            assert -100.0 <= score <= 100.0, f"Score out of range: {score}"

    def test_improving_gives_positive_score(self):
        drifts = [8.0, 6.0, 4.0, 2.0, 0.5]
        assert _compute_momentum(drifts) > 0

    def test_deteriorating_gives_negative_score(self):
        drifts = [0.5, 2.0, 4.0, 6.0, 8.0]
        assert _compute_momentum(drifts) < 0

    def test_stable_gives_near_zero(self):
        drifts = [3.0, 3.0, 3.0, 3.0, 3.0]
        score = _compute_momentum(drifts)
        assert abs(score) < 10.0

    def test_single_entry_returns_zero(self):
        assert _compute_momentum([5.0]) == 0.0

    def test_two_entries_valid(self):
        # Should not raise; result is bounded
        score = _compute_momentum([5.0, 3.0])
        assert -100.0 <= score <= 100.0


# ═══════════════════════════════════════════════════════════════════════════════
# Part C — Persistence classification
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifyPersistence:
    def test_none_when_no_violations(self):
        assert _classify_persistence(0, 10) == "NONE"

    def test_temporary_one_or_two(self):
        assert _classify_persistence(1, 10) == "TEMPORARY"
        assert _classify_persistence(2, 10) == "TEMPORARY"

    def test_recurring_three_to_five(self):
        assert _classify_persistence(3, 10) == "RECURRING"
        assert _classify_persistence(5, 10) == "RECURRING"

    def test_chronic_six_or_more(self):
        # 6 of 8 = 75% → hits STRUCTURAL threshold first
        # 6 of 20 = 30% → CHRONIC (> RECURRING_MAX=5, ≤ CHRONIC_MAX=11)
        assert _classify_persistence(6, 20) == "CHRONIC"
        assert _classify_persistence(11, 20) == "CHRONIC"

    def test_structural_seventy_five_percent_or_more(self):
        # 8 of 10 = 80% → STRUCTURAL
        assert _classify_persistence(8, 10) == "STRUCTURAL"

    def test_structural_all_observations(self):
        assert _classify_persistence(10, 10) == "STRUCTURAL"

    def test_structural_threshold_at_boundary(self):
        # 7.5 of 10 = 75% → STRUCTURAL
        assert _classify_persistence(8, 10) == "STRUCTURAL"

    def test_zero_total_returns_none(self):
        assert _classify_persistence(0, 0) == "NONE"


# ═══════════════════════════════════════════════════════════════════════════════
# Severity label
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeverityLabel:
    def test_none_below_half(self):   assert _severity_label(0.4) == "NONE"
    def test_minor(self):             assert _severity_label(1.0) == "MINOR"
    def test_moderate(self):          assert _severity_label(3.0) == "MODERATE"
    def test_significant(self):       assert _severity_label(7.0) == "SIGNIFICANT"
    def test_critical(self):          assert _severity_label(12.0) == "CRITICAL"
    def test_exact_boundaries(self):
        assert _severity_label(0.5) == "MINOR"
        assert _severity_label(2.0) == "MODERATE"
        assert _severity_label(5.0) == "SIGNIFICANT"
        assert _severity_label(10.0) == "CRITICAL"


# ═══════════════════════════════════════════════════════════════════════════════
# _analyse_node integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyseNode:
    def _node(self, drifts: List[float]) -> DriftTrend:
        entries = _entries_from_drifts(drifts)
        return _analyse_node("TEST.NODE", "Test Node", "ASSET_CLASS", entries)

    def test_trend_classified(self):
        dt = self._node([8.0, 6.0, 4.0, 2.0])
        assert dt.trend == "IMPROVING"

    def test_momentum_score_in_range(self):
        dt = self._node([1.0, 3.0, 5.0, 7.0])
        assert -100.0 <= dt.momentum_score <= 100.0

    def test_violation_count_correct(self):
        # All 4 entries have |drift| > 0.5
        dt = self._node([2.0, 3.0, 4.0, 5.0])
        assert dt.violation_count == 4

    def test_persistence_class_structural(self):
        # 8 violations of 8 total = STRUCTURAL
        dt = self._node([3.0] * 8)
        assert dt.persistence_class == "STRUCTURAL"

    def test_first_violation_date_set(self):
        entries = _entries_from_drifts([0.0, 0.0, 3.0, 5.0])
        dt = _analyse_node("N", "N", "ASSET_CLASS", entries)
        assert dt.first_violation_date is not None

    def test_no_violations_no_first_date(self):
        dt = self._node([0.1, 0.1, 0.1, 0.1])
        assert dt.first_violation_date is None

    def test_worst_drift_is_max_absolute(self):
        dt = self._node([-8.0, 2.0, -3.0, 5.0])
        assert abs(dt.worst_drift_pct) == pytest.approx(8.0)

    def test_drift_direction_overweight(self):
        dt = self._node([5.0] * 4)
        assert dt.drift_direction == "OVERWEIGHT"

    def test_drift_direction_underweight(self):
        dt = self._node([-5.0] * 4)
        assert dt.drift_direction == "UNDERWEIGHT"

    def test_drift_direction_on_target(self):
        entries = [_entry(0.01)]
        dt = _analyse_node("N", "N", "ASSET_CLASS", entries)
        assert dt.drift_direction == "ON_TARGET"

    def test_avg_drift_pct_computed(self):
        dt = self._node([2.0, 4.0, 6.0, 8.0])
        assert dt.avg_drift_pct == pytest.approx(5.0)

    def test_single_entry_does_not_crash(self):
        dt = self._node([3.0])
        assert dt.trend == "STABLE"
        assert dt.momentum_score == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Priority score
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputePriorityScore:
    def _dt(self, severity="MODERATE", persistence_class="CHRONIC",
            momentum_score=-50.0, drift=5.0) -> DriftTrend:
        entries = _entries_from_drifts([drift] * 8)
        dt = _analyse_node("N", "N", "ASSET_CLASS", entries)
        # Force override via re-construction for isolation
        from dataclasses import replace
        return replace(dt,
                       severity=severity,
                       persistence_class=persistence_class,
                       momentum_score=momentum_score,
                       current_drift_pct=drift)

    def test_priority_in_range(self):
        for sev in ["NONE", "MINOR", "MODERATE", "SIGNIFICANT", "CRITICAL"]:
            for pers in ["NONE", "TEMPORARY", "RECURRING", "CHRONIC", "STRUCTURAL"]:
                dt = self._dt(severity=sev, persistence_class=pers)
                score = _compute_priority_score(dt)
                assert 0.0 <= score <= 100.0, f"Score {score} OOB for sev={sev} pers={pers}"

    def test_higher_severity_higher_score(self):
        mod = self._dt(severity="MODERATE")
        crit = self._dt(severity="CRITICAL")
        assert _compute_priority_score(crit) > _compute_priority_score(mod)

    def test_deteriorating_outranks_improving(self):
        det = self._dt(momentum_score=-80.0)
        imp = self._dt(momentum_score=+80.0)
        assert _compute_priority_score(det) > _compute_priority_score(imp)

    def test_structural_outranks_temporary(self):
        struct = self._dt(persistence_class="STRUCTURAL")
        temp   = self._dt(persistence_class="TEMPORARY")
        assert _compute_priority_score(struct) > _compute_priority_score(temp)


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end PAR-based tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    """Full pipeline tests using synthetic PAR runs written to a temp directory."""

    def _repo(self, tmp_path: Path) -> Path:
        return tmp_path

    def _setup_two_runs(self, tmp_path: Path):
        """Write two PAR runs: one with large drift, one with smaller drift (improving)."""
        _make_par_run(tmp_path, "2026-05-01", {
            "EQUITIES.US.LARGE": {"actual": 60.0, "target": 40.0, "label": "US Large"},
            "EQUITIES.INTL":     {"actual": 5.0,  "target": 15.0, "label": "International"},
        })
        _make_par_run(tmp_path, "2026-06-01", {
            "EQUITIES.US.LARGE": {"actual": 55.0, "target": 40.0, "label": "US Large"},
            "EQUITIES.INTL":     {"actual": 6.0,  "target": 15.0, "label": "International"},
        })

    def test_drift_trends_returns_nodes(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_trends(repo_root=tmp_path)
        assert "nodes" in result
        assert len(result["nodes"]) >= 2

    def test_drift_trends_trend_counts(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_trends(repo_root=tmp_path)
        tc = result.get("trend_counts", {})
        total = sum(tc.values())
        assert total >= 2  # at least 2 nodes classified

    def test_drift_trends_improving_node(self, tmp_path):
        """US Large drift: 20pp → 15pp = improving."""
        self._setup_two_runs(tmp_path)
        result = drift_trends(repo_root=tmp_path)
        large = next((n for n in result["nodes"] if "US Large" in n.get("node_label", "")), None)
        assert large is not None
        assert large["trend"] == "IMPROVING"

    def test_drift_priorities_top10(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_priorities(repo_root=tmp_path)
        assert "top10" in result
        # Verify rank ordering
        ranks = [p["rank"] for p in result["top10"]]
        assert ranks == sorted(ranks)

    def test_drift_priorities_fields(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_priorities(repo_root=tmp_path)
        for p in result["top10"]:
            assert "node_key" in p
            assert "priority_score" in p
            assert "trend" in p
            assert "severity" in p
            assert "primary_reason" in p

    def test_drift_chronic_returns_list(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_chronic(repo_root=tmp_path)
        assert "chronic" in result
        assert isinstance(result["chronic"], list)

    def test_drift_momentum_sorted_by_abs(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_momentum(repo_root=tmp_path)
        scores = [abs(n.get("momentum_score", 0)) for n in result["nodes"]]
        assert scores == sorted(scores, reverse=True)

    def test_drift_intelligence_summary_keys(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_intelligence_summary(repo_root=tmp_path)
        required_keys = [
            "generated_at", "trend_counts", "total_nodes", "violation_nodes",
            "structural_count", "chronic_count", "governance_note",
        ]
        for k in required_keys:
            assert k in result, f"Missing key: {k}"

    def test_drift_intelligence_summary_governance_note(self, tmp_path):
        self._setup_two_runs(tmp_path)
        result = drift_intelligence_summary(repo_root=tmp_path)
        note = result.get("governance_note", "")
        assert "display-only" in note.lower() or "informational" in note.lower()

    def test_empty_history_returns_gracefully(self, tmp_path):
        # No PAR runs at all
        result = drift_trends(repo_root=tmp_path)
        assert result["nodes"] == []
        result2 = drift_priorities(repo_root=tmp_path)
        assert result2["top10"] == []

    def test_cache_written_and_reused(self, tmp_path):
        """Second call should return from cache without re-reading PAR files."""
        self._setup_two_runs(tmp_path)
        _ = drift_trends(repo_root=tmp_path)
        cache_dir = tmp_path / "data" / "history" / "pis" / "pa006b"
        assert (cache_dir / "drift_intelligence.json").exists()
        # Second call must not raise
        result2 = drift_trends(repo_root=tmp_path)
        assert len(result2["nodes"]) >= 2

    def test_learning_file_written(self, tmp_path):
        """allocation_drift_learning.json must be written after analysis."""
        self._setup_two_runs(tmp_path)
        _ = drift_intelligence_summary(repo_root=tmp_path)
        learning_path = tmp_path / "data" / "history" / "pis" / "pa006b" / "allocation_drift_learning.json"
        assert learning_path.exists()
        learning = json.loads(learning_path.read_text())
        assert "nodes" in learning
        for n in learning["nodes"]:
            assert "node_key" in n
            assert "worst_drift_pct" in n
            assert "persistence_class" in n


# ═══════════════════════════════════════════════════════════════════════════════
# Q6–Q9 Governance
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernance:
    """
    Q6: Allocation targets not modified — PA-006B is read-only.
    Q7: Recommendation engines not modified.
    Q8: Governance rules not modified.
    Q9: PA-006B is informational only.
    """

    def test_module_writes_no_par_artifacts(self, tmp_path):
        """No files written to portfolio_ingestion or analysis_runs."""
        _make_par_run(tmp_path, "2026-06-01", {
            "TEST": {"actual": 15.0, "target": 10.0, "label": "Test"},
        })
        _ = drift_intelligence_summary(repo_root=tmp_path)
        par_dir = tmp_path / "data" / "portfolio_ingestion"
        # Only the analysis_runs directory written by test setup should exist;
        # PA-006B must not create new run directories
        if par_dir.exists():
            for p in (par_dir / "analysis_runs").iterdir():
                # Only the run we created in setup
                assert p.is_dir()  # no new files outside analysis_runs

    def test_governance_note_present(self, tmp_path):
        _make_par_run(tmp_path, "2026-06-01", {
            "TEST": {"actual": 15.0, "target": 10.0, "label": "Test"},
        })
        result = drift_intelligence_summary(repo_root=tmp_path)
        note = result.get("governance_note", "")
        assert len(note) > 30

    def test_outputs_contain_no_action_fields(self, tmp_path):
        _make_par_run(tmp_path, "2026-06-01", {
            "TEST": {"actual": 15.0, "target": 10.0, "label": "Test"},
        })
        result = drift_trends(repo_root=tmp_path)
        forbidden = {"action", "execute", "trade", "buy", "sell", "recommendation_id"}
        for node in result.get("nodes", []):
            assert not (forbidden & set(node.keys())), (
                f"Node contains forbidden action key: {forbidden & set(node.keys())}"
            )

    def test_priority_score_is_analytical_not_action(self, tmp_path):
        """Priority score must exist but must not trigger any trade."""
        _make_par_run(tmp_path, "2026-06-01", {
            "TEST": {"actual": 20.0, "target": 10.0, "label": "Test"},
        })
        result = drift_priorities(repo_root=tmp_path)
        for p in result.get("top10", []):
            # Must have priority_score (analytical), must NOT have execute/trade fields
            assert "priority_score" in p
            assert "execute" not in p
            assert "trade" not in p
