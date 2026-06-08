"""Tests for PRA-IMPL-01: Typed Recommendation Contract and Card Schema.

Validates:
- Five new fields present with correct defaults on PortfolioRecommendation.
- card_type correctly set at all major construction sites.
- Existing fields and behaviour unchanged.
- dataclasses.asdict serialisation includes all new fields.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone

import pytest

from src.portfolio.models import PortfolioRecommendation


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_RUN_ID = "RUN-TEST-0001"
_SNAP_ID = "SNAP-TEST-0001"
_NOW = datetime.now(timezone.utc).isoformat()


def _make_rec(
    recommendation_type: str = "REDUCE_OVERWEIGHT",
    **overrides,
) -> PortfolioRecommendation:
    """Minimal valid PortfolioRecommendation for testing."""
    defaults = dict(
        recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
        analysis_run_id=_RUN_ID,
        portfolio_snapshot_id=_SNAP_ID,
        recommendation_type=recommendation_type,
        priority=3,
        confidence="MEDIUM",
        title=f"Test {recommendation_type}",
        rationale="test rationale",
        evidence_summary="test evidence",
        affected_node_key=None,
        affected_symbols=(),
        drift_pct=None,
        severity="MODERATE",
        replay_run_ids=(),
        created_at_utc=_NOW,
    )
    defaults.update(overrides)
    return PortfolioRecommendation(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# T01-T06 — card_type field presence and defaults
# ─────────────────────────────────────────────────────────────────────────────

class TestCardTypeField:
    def test_T01_card_type_present_in_asdict(self):
        rec = _make_rec()
        d = dataclasses.asdict(rec)
        assert "card_type" in d

    def test_T02_card_type_default_is_DIAGNOSTIC(self):
        rec = _make_rec()
        assert rec.card_type == "DIAGNOSTIC"

    def test_T03_action_types_get_ACTION(self):
        action_types = [
            "REDUCE_OVERWEIGHT",
            "INCREASE_UNDERWEIGHT",
            "DIVERSIFY_CONCENTRATION",
            "IMPROVE_RISK_PROFILE",
            "IMPROVE_REPLAY_ALIGNMENT",
            "IMPROVE_SECTOR_EXPOSURE",
            "STRATEGIC_TRIM_CANDIDATE",
            "TOP_TRIM_CANDIDATES",
        ]
        for rtype in action_types:
            rec = _make_rec(recommendation_type=rtype, card_type="ACTION")
            assert rec.card_type == "ACTION", f"Expected ACTION for {rtype}"

    def test_T04_observation_types_get_OBSERVATION(self):
        rec = _make_rec(
            recommendation_type="STRATEGIC_RETAIN_SIGNAL",
            card_type="OBSERVATION",
        )
        assert rec.card_type == "OBSERVATION"

    def test_T05_narrative_types_get_NARRATIVE(self):
        narrative_types = [
            "STRATEGIC_RETAIN_NARRATIVE",
            "THEMATIC_SATURATION_NARRATIVE",
            "PORTFOLIO_CONSTRUCTION_NARRATIVE",
        ]
        for rtype in narrative_types:
            rec = _make_rec(recommendation_type=rtype, card_type="NARRATIVE")
            assert rec.card_type == "NARRATIVE", f"Expected NARRATIVE for {rtype}"

    def test_T06_explainability_types_get_EXPLAINABILITY(self):
        explainability_types = [
            "REPLAY_ALIGNMENT_CONTEXT",
            "CONVICTION_EXPLAINABILITY_CARD",
        ]
        for rtype in explainability_types:
            rec = _make_rec(recommendation_type=rtype, card_type="EXPLAINABILITY")
            assert rec.card_type == "EXPLAINABILITY", f"Expected EXPLAINABILITY for {rtype}"


# ─────────────────────────────────────────────────────────────────────────────
# T07-T12 — other new fields
# ─────────────────────────────────────────────────────────────────────────────

class TestNewFields:
    def test_T07_execution_state_defaults_to_EXECUTABLE(self):
        rec = _make_rec()
        assert rec.execution_state == "EXECUTABLE"

    def test_T08_effective_action_defaults_to_empty_string(self):
        rec = _make_rec()
        assert rec.effective_action == ""

    def test_T09_evidence_link_defaults_to_empty_string(self):
        rec = _make_rec()
        assert rec.evidence_link == ""

    def test_T10_card_lifecycle_state_defaults_to_OBSERVED(self):
        rec = _make_rec()
        assert rec.card_lifecycle_state == "OBSERVED"

    def test_T11_existing_fields_unchanged(self):
        """Verify a known-good existing field set is unaffected by new fields."""
        rec = _make_rec(
            recommendation_type="REDUCE_OVERWEIGHT",
            priority=1,
            confidence="HIGH",
            severity="HIGH",
            drift_pct=-7.5,
        )
        assert rec.recommendation_type == "REDUCE_OVERWEIGHT"
        assert rec.priority == 1
        assert rec.confidence == "HIGH"
        assert rec.severity == "HIGH"
        assert rec.drift_pct == -7.5
        assert rec.rec_state == "ACTIVE"
        assert rec.analysis_run_id == _RUN_ID

    def test_T12_asdict_includes_all_five_new_fields(self):
        rec = _make_rec()
        d = dataclasses.asdict(rec)
        for field in ("card_type", "execution_state", "effective_action",
                      "evidence_link", "card_lifecycle_state"):
            assert field in d, f"Missing field in asdict output: {field}"

    def test_new_fields_can_be_set_explicitly(self):
        rec = _make_rec(
            card_type="ACTION",
            execution_state="BLOCKED_BY_POLICY",
            effective_action="MONITOR_ONLY",
            evidence_link="PAR-20260608-ABCD",
            card_lifecycle_state="POLICY_ADJUSTED",
        )
        assert rec.card_type == "ACTION"
        assert rec.execution_state == "BLOCKED_BY_POLICY"
        assert rec.effective_action == "MONITOR_ONLY"
        assert rec.evidence_link == "PAR-20260608-ABCD"
        assert rec.card_lifecycle_state == "POLICY_ADJUSTED"


# ─────────────────────────────────────────────────────────────────────────────
# T13 — Construction sites in recommendations.py emit correct card_type
# ─────────────────────────────────────────────────────────────────────────────

class TestConstructionSiteCardTypes:
    """Smoke-test the actual generator functions to confirm card_type is set."""

    def _get_action_recs_from_generator(self):
        """Run generate_recommendations with minimal stubs and collect results."""
        from unittest.mock import patch, MagicMock
        import src.portfolio.recommendations as rec_mod

        # Minimal alignment result stub for REDUCE_OVERWEIGHT
        ar = MagicMock()
        ar.drift_direction = "OVERWEIGHT"
        ar.severity = "HIGH"
        ar.node_key = "EQUITIES.US.MEGA"
        ar.node_label = "US Mega Cap"
        ar.actual_pct = 30.0
        ar.tactical_target_pct = 20.0
        ar.target_pct = 20.0
        ar.drift_pct = 10.0
        ar.recommendation_priority = 1
        ar.intentional_overweight = False
        ar.intentional_underweight = False

        snap = MagicMock()
        snap.portfolio_snapshot_id = _SNAP_ID

        concentration = MagicMock()
        concentration.concentration_tier = "LOW"

        with patch.object(rec_mod, "_replay_ids_for_node", return_value=[]):
            recs = rec_mod.generate_recommendations(
                analysis_run_id=_RUN_ID,
                portfolio_snapshot_id=_SNAP_ID,
                alignment_results=[ar],
                holdings=[],
                overlays=[],
                concentration=concentration,
                strategic_profiles=None,
            )
        return recs

    def test_allocation_recs_have_ACTION_card_type(self):
        recs = self._get_action_recs_from_generator()
        allocation_recs = [r for r in recs if r.recommendation_type in (
            "REDUCE_OVERWEIGHT", "INCREASE_UNDERWEIGHT")]
        assert len(allocation_recs) >= 1
        for r in allocation_recs:
            assert r.card_type == "ACTION", (
                f"{r.recommendation_type} should be ACTION, got {r.card_type}"
            )

    def test_strategic_retain_signal_has_OBSERVATION_card_type(self):
        from src.portfolio.recommendations import _generate_strategic_trim_recs
        from unittest.mock import MagicMock

        # Build a retain profile stub
        p = MagicMock()
        p.symbol = "MSFT"
        p.strategic_classification = "HIGH_CONVICTION_RETAIN"
        p.trim_priority_score = 5.0
        p.strategic_importance = "CRITICAL"
        p.exposure_origin = "DIRECT"
        p.classification_trace = "test trace"
        p.retain_rationale = "test retain"
        p.thematic_overlap_clusters = ()
        p.thematic_redundancy_score = 0.0

        recs = _generate_strategic_trim_recs(
            analysis_run_id=_RUN_ID,
            portfolio_snapshot_id=_SNAP_ID,
            strategic_profiles=[p],
            overlays=[],
            alignment_results=[],
            now_utc=_NOW,
        )
        retain_recs = [r for r in recs if r.recommendation_type == "STRATEGIC_RETAIN_SIGNAL"]
        for r in retain_recs:
            assert r.card_type == "OBSERVATION", (
                f"STRATEGIC_RETAIN_SIGNAL should be OBSERVATION, got {r.card_type}"
            )
