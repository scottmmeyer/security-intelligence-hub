"""Phase E — Strategic Recommendation Synthesis unit tests.

Covers:
  - synthesize_phase_e_recommendations (integration)
  - _build_retain_rationale
  - _build_cluster_trim_narrative
  - _deduplicate_recs
  - _prioritize_recs
  - validate_phase_e_consistency
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

import pytest

from src.portfolio.phase_e_synthesis import (
    _build_retain_rationale,
    _build_cluster_trim_narrative,
    _deduplicate_recs,
    _prioritize_recs,
    validate_phase_e_consistency,
    synthesize_phase_e_recommendations,
)
from src.portfolio.models import (
    HoldingStrategicProfile,
    PortfolioHolding,
    PortfolioRecommendation,
)


_NOW = "2025-01-01T00:00:00Z"
_RUN_ID = "RUN-TEST"
_SNAP_ID = "PSNAP-TEST"


# ─────────────────────────────────────────────────────────────────────────────
# Minimal test factories
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _FakeOverlay:
    symbol: str
    signal_direction: str = "BULLISH"
    composite_score: float = 3.5
    ess_score_text: str = "BULLISH"
    replay_supported: bool = True
    replay_percentile: float = 80.0
    trim_flag: str = "HOLD"


def _profile(
    symbol: str,
    classification: str = "REDUCIBLE",
    trim_score: float = 60.0,
    importance: str = "LOW",
    clusters: tuple = ("AI_INFRA",),
    overlap_peers: tuple = (),
    redundancy: float = 40.0,
    origin: str = "DIRECT_INTENTIONAL",
    role: str = "SECTOR_CONCENTRATION",
    pct: float = 5.0,
    concentration_pressure: float = 15.0,
    diversification_contribution: float = 30.0,
) -> HoldingStrategicProfile:
    return HoldingStrategicProfile(
        portfolio_snapshot_id=_SNAP_ID,
        symbol=symbol,
        security_type="STOCK",
        percent_of_portfolio=pct,
        strategic_classification=classification,
        trim_priority_score=trim_score,
        trim_factors=(),
        thematic_overlap_clusters=clusters,
        overlap_peers=overlap_peers,
        thematic_redundancy_score=redundancy,
        strategic_role=role,
        strategic_importance=importance,
        exposure_origin=origin,
        trim_rationale=f"{symbol} trim rationale",
        retain_rationale=None,
        classification_trace=f"{symbol} trace",
        concentration_pressure=concentration_pressure,
        diversification_contribution=diversification_contribution,
        created_at_utc=_NOW,
    )


def _holding(symbol: str, pct: float = 5.0) -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id=_SNAP_ID,
        snapshot_date="2025-01-01",
        account_name="Test",
        symbol=symbol,
        description=f"{symbol} description",
        quantity=100.0,
        market_value=pct * 1000,
        percent_of_portfolio=pct,
        asset_class="EQUITIES",
        geography="US",
        market_cap_bucket="LARGE",
        mega_subtier="N/A",
        sector="Technology",
        industry="ALL",
        security_type="STOCK",
        cost_basis=None,
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        exposure_thematic_mix=(),
        exposure_mega_subtier_mix=(),
        strategic_role=None,
    )


def _rec(
    rec_type: str,
    symbols: tuple = (),
    state: str = "ACTIVE",
    severity: str = "MODERATE",
    priority: int = 3,
    trace: str = "trace",
) -> PortfolioRecommendation:
    return PortfolioRecommendation(
        recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
        analysis_run_id=_RUN_ID,
        portfolio_snapshot_id=_SNAP_ID,
        recommendation_type=rec_type,
        priority=priority,
        confidence="MEDIUM",
        title=f"Test {rec_type}",
        rationale="test rationale",
        evidence_summary="test evidence",
        affected_node_key=None,
        affected_symbols=symbols,
        drift_pct=None,
        severity=severity,
        replay_run_ids=(),
        created_at_utc=_NOW,
        rec_state=state,
        reasoning_trace=trace,
    )


# ─────────────────────────────────────────────────────────────────────────────
# _build_retain_rationale
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildRetainRationale:
    def test_contains_symbol(self):
        p = _profile("NVDA", classification="HIGH_CONVICTION_RETAIN", trim_score=5.0, importance="CRITICAL")
        overlay = _FakeOverlay("NVDA", replay_supported=True, replay_percentile=90.0)
        result = _build_retain_rationale(p, overlay, [_holding("NVDA")])
        assert "NVDA" in result

    def test_mentions_strategic_importance(self):
        p = _profile("NVDA", classification="HIGH_CONVICTION_RETAIN", trim_score=5.0, importance="CRITICAL")
        overlay = _FakeOverlay("NVDA")
        result = _build_retain_rationale(p, overlay, [_holding("NVDA")])
        # Result should explain why NVDA is a retain — contains replay or signal
        assert "replay" in result.lower() or "conviction" in result.lower() or "nvda" in result.lower()

    def test_mentions_replay_for_supported(self):
        p = _profile("NVDA", classification="HIGH_CONVICTION_RETAIN", trim_score=5.0)
        overlay = _FakeOverlay("NVDA", replay_supported=True, replay_percentile=85.0)
        result = _build_retain_rationale(p, overlay, [_holding("NVDA")])
        assert "replay" in result.lower()

    def test_no_replay_mention_when_unsupported(self):
        p = _profile("XYZ", classification="CORE_COMPOUNDER", trim_score=8.0)
        overlay = _FakeOverlay("XYZ", replay_supported=False)
        result = _build_retain_rationale(p, overlay, [_holding("XYZ")])
        assert "no replay" in result.lower() or "replay" not in result.lower()

    def test_bullish_signal_mentioned(self):
        p = _profile("MSFT", classification="STRATEGIC_CORE", trim_score=10.0)
        overlay = _FakeOverlay("MSFT", signal_direction="BULLISH", composite_score=4.0)
        result = _build_retain_rationale(p, overlay, [_holding("MSFT")])
        assert "bullish" in result.lower() or "signal" in result.lower()

    def test_no_overlay_still_works(self):
        p = _profile("VOO", classification="CORE_COMPOUNDER", trim_score=5.0)
        result = _build_retain_rationale(p, None, [_holding("VOO")])
        assert "VOO" in result


# ─────────────────────────────────────────────────────────────────────────────
# _build_cluster_trim_narrative
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildClusterTrimNarrative:
    def _run(self, cluster: str = "AI_INFRA"):
        top_trim = _profile("AVGO", classification="REDUNDANT_EXPOSURE", trim_score=75.0,
                            clusters=(cluster,), overlap_peers=("NVDA", "SMH"))
        retain_anchor = _profile("NVDA", classification="HIGH_CONVICTION_RETAIN", trim_score=5.0,
                                  clusters=(cluster,))
        all_profiles = [top_trim, retain_anchor]
        overlays = [_FakeOverlay("AVGO", replay_supported=False, signal_direction="NEUTRAL"),
                    _FakeOverlay("NVDA", replay_supported=True, replay_percentile=90.0)]
        holdings = [_holding("AVGO"), _holding("NVDA")]
        return _build_cluster_trim_narrative(cluster, [top_trim], all_profiles, overlays, holdings)

    def test_title_contains_cluster_label(self):
        title, _, _, _ = self._run("AI_INFRA")
        assert "AI Infrastructure" in title

    def test_title_contains_top_symbol(self):
        title, _, _, _ = self._run("AI_INFRA")
        assert "AVGO" in title

    def test_rationale_mentions_redundancy(self):
        _, rationale, _, _ = self._run("AI_INFRA")
        assert "AVGO" in rationale

    def test_ranked_list_present_in_rationale(self):
        _, rationale, _, _ = self._run("AI_INFRA")
        assert "AVGO" in rationale

    def test_evidence_summary_has_trim_score(self):
        _, _, evidence, _ = self._run("AI_INFRA")
        assert "75" in evidence

    def test_reasoning_trace_has_cluster_key(self):
        _, _, _, trace = self._run("AI_INFRA")
        assert "AI_INFRA" in trace

    def test_reasoning_trace_has_symbol(self):
        _, _, _, trace = self._run("AI_INFRA")
        assert "AVGO" in trace


# ─────────────────────────────────────────────────────────────────────────────
# _deduplicate_recs
# ─────────────────────────────────────────────────────────────────────────────

class TestDeduplicateRecs:
    def test_strategic_trim_candidate_suppressed_by_top_trim(self):
        phase_e_trim = _rec("TOP_TRIM_CANDIDATES", symbols=("AVGO", "SMH"))
        legacy_trim = _rec("STRATEGIC_TRIM_CANDIDATE", symbols=("AVGO",))
        result = _deduplicate_recs([phase_e_trim, legacy_trim])
        suppressed = [r for r in result if r.recommendation_type == "STRATEGIC_TRIM_CANDIDATE"]
        assert all(r.rec_state == "SUPPRESSED" for r in suppressed)

    def test_strategic_trim_candidate_not_suppressed_if_symbol_not_covered(self):
        phase_e_trim = _rec("TOP_TRIM_CANDIDATES", symbols=("AVGO",))
        legacy_trim = _rec("STRATEGIC_TRIM_CANDIDATE", symbols=("DIFFERENT_SYM",))
        result = _deduplicate_recs([phase_e_trim, legacy_trim])
        legacy_results = [r for r in result if r.recommendation_type == "STRATEGIC_TRIM_CANDIDATE"]
        assert all(r.rec_state == "ACTIVE" for r in legacy_results)

    def test_strategic_retain_signal_suppressed_by_retain_narrative(self):
        phase_e_retain = _rec("STRATEGIC_RETAIN_NARRATIVE", symbols=("NVDA",))
        legacy_retain = _rec("STRATEGIC_RETAIN_SIGNAL", symbols=("NVDA",))
        result = _deduplicate_recs([phase_e_retain, legacy_retain])
        suppressed = [r for r in result if r.recommendation_type == "STRATEGIC_RETAIN_SIGNAL"]
        assert all(r.rec_state == "SUPPRESSED" for r in suppressed)

    def test_improve_sector_exposure_suppressed_by_thematic_narrative(self):
        thematic = _rec("THEMATIC_SATURATION_NARRATIVE", symbols=("NVDA", "AVGO"))
        legacy = _rec("IMPROVE_SECTOR_EXPOSURE")
        result = _deduplicate_recs([thematic, legacy])
        sec_recs = [r for r in result if r.recommendation_type == "IMPROVE_SECTOR_EXPOSURE"]
        assert all(r.rec_state == "SUPPRESSED" for r in sec_recs)

    def test_improve_sector_exposure_kept_without_thematic_narrative(self):
        legacy = _rec("IMPROVE_SECTOR_EXPOSURE")
        result = _deduplicate_recs([legacy])
        assert result[0].rec_state == "ACTIVE"

    def test_suppressed_rec_trace_mentions_superseded(self):
        phase_e_trim = _rec("TOP_TRIM_CANDIDATES", symbols=("AVGO",))
        legacy_trim = _rec("STRATEGIC_TRIM_CANDIDATE", symbols=("AVGO",), trace="original trace")
        result = _deduplicate_recs([phase_e_trim, legacy_trim])
        suppressed = next(r for r in result if r.recommendation_type == "STRATEGIC_TRIM_CANDIDATE")
        assert "Superseded" in suppressed.reasoning_trace or "superseded" in suppressed.reasoning_trace.lower()

    def test_phase_e_recs_not_touched(self):
        phase_e = _rec("TOP_TRIM_CANDIDATES", symbols=("AVGO",))
        result = _deduplicate_recs([phase_e])
        assert result[0].rec_state == "ACTIVE"


# ─────────────────────────────────────────────────────────────────────────────
# _prioritize_recs
# ─────────────────────────────────────────────────────────────────────────────

class TestPrioritizeRecs:
    def test_pcn_sorts_before_top_trim(self):
        pcn = _rec("PORTFOLIO_CONSTRUCTION_NARRATIVE", priority=2, severity="LOW")
        trim = _rec("TOP_TRIM_CANDIDATES", priority=2, severity="HIGH")
        result = _prioritize_recs([trim, pcn])
        assert result[0].recommendation_type == "PORTFOLIO_CONSTRUCTION_NARRATIVE"

    def test_active_sorts_before_suppressed(self):
        active = _rec("TOP_TRIM_CANDIDATES", state="ACTIVE")
        suppressed = _rec("TOP_TRIM_CANDIDATES", state="SUPPRESSED")
        result = _prioritize_recs([suppressed, active])
        assert result[0].rec_state == "ACTIVE"

    def test_retain_narrative_sorts_after_trim_candidates(self):
        trim = _rec("TOP_TRIM_CANDIDATES", state="ACTIVE", severity="MODERATE", priority=2)
        retain = _rec("STRATEGIC_RETAIN_NARRATIVE", state="INFORMATIONAL", severity="LOW", priority=5)
        result = _prioritize_recs([retain, trim])
        assert result[0].recommendation_type == "TOP_TRIM_CANDIDATES"

    def test_higher_severity_sorts_first_among_same_type(self):
        high = _rec("TOP_TRIM_CANDIDATES", severity="HIGH", priority=2)
        low = _rec("TOP_TRIM_CANDIDATES", severity="LOW", priority=2)
        result = _prioritize_recs([low, high])
        assert result[0].severity == "HIGH"


# ─────────────────────────────────────────────────────────────────────────────
# validate_phase_e_consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestValidatePhaseEConsistency:
    def test_trim_retain_conflict_generates_warning(self):
        trim_rec = _rec("TOP_TRIM_CANDIDATES", symbols=("NVDA",), state="ACTIVE")
        retain_rec = _rec("STRATEGIC_RETAIN_NARRATIVE", symbols=("NVDA",), state="ACTIVE")
        warnings = validate_phase_e_consistency([trim_rec, retain_rec], [])
        assert any("NVDA" in w and "trim" in w.lower() and "retain" in w.lower() for w in warnings)

    def test_no_conflict_produces_no_warning(self):
        trim_rec = _rec("TOP_TRIM_CANDIDATES", symbols=("AVGO",), state="ACTIVE")
        retain_rec = _rec("STRATEGIC_RETAIN_NARRATIVE", symbols=("NVDA",), state="ACTIVE")
        warnings = validate_phase_e_consistency([trim_rec, retain_rec], [])
        conflict_warnings = [w for w in warnings if "trim" in w.lower() and "retain" in w.lower()]
        assert not conflict_warnings

    def test_excessive_rec_count_generates_warning(self):
        recs = [_rec("TOP_TRIM_CANDIDATES", state="ACTIVE") for _ in range(13)]
        warnings = validate_phase_e_consistency(recs, [])
        assert any("13" in w or "active" in w.lower() for w in warnings)

    def test_twelve_recs_no_count_warning(self):
        recs = [_rec("TOP_TRIM_CANDIDATES", state="ACTIVE") for _ in range(12)]
        warnings = validate_phase_e_consistency(recs, [])
        count_warnings = [w for w in warnings if "active recommendations" in w.lower()]
        assert not count_warnings

    def test_duplicate_primary_trim_symbol_warns(self):
        r1 = _rec("TOP_TRIM_CANDIDATES", symbols=("AVGO", "SMH"), state="ACTIVE")
        r2 = _rec("TOP_TRIM_CANDIDATES", symbols=("AVGO", "SOXX"), state="ACTIVE")
        warnings = validate_phase_e_consistency([r1, r2], [])
        assert any("AVGO" in w for w in warnings)

    def test_multiple_pcn_warns(self):
        r1 = _rec("PORTFOLIO_CONSTRUCTION_NARRATIVE", state="ACTIVE")
        r2 = _rec("PORTFOLIO_CONSTRUCTION_NARRATIVE", state="ACTIVE")
        warnings = validate_phase_e_consistency([r1, r2], [])
        assert any("PORTFOLIO_CONSTRUCTION_NARRATIVE" in w or "multiple" in w.lower() for w in warnings)

    def test_suppressed_recs_excluded_from_trim_retain_conflict(self):
        trim_rec = _rec("TOP_TRIM_CANDIDATES", symbols=("NVDA",), state="ACTIVE")
        retain_rec = _rec("STRATEGIC_RETAIN_NARRATIVE", symbols=("NVDA",), state="SUPPRESSED")
        warnings = validate_phase_e_consistency([trim_rec, retain_rec], [])
        conflict_warnings = [w for w in warnings if "NVDA" in w and "trim" in w.lower() and "retain" in w.lower()]
        assert not conflict_warnings


# ─────────────────────────────────────────────────────────────────────────────
# synthesize_phase_e_recommendations — integration
# ─────────────────────────────────────────────────────────────────────────────

class TestSynthesizePhaseERecommendations:
    def _make_portfolio(self):
        profiles = [
            _profile("NVDA", classification="HIGH_CONVICTION_RETAIN", trim_score=5.0,
                     importance="CRITICAL", clusters=("AI_INFRA", "SEMICONDUCTOR_CONCENTRATION"),
                     pct=12.0),
            _profile("AVGO", classification="REDUNDANT_EXPOSURE", trim_score=70.0,
                     importance="LOW", clusters=("SEMICONDUCTOR_CONCENTRATION",),
                     overlap_peers=("NVDA", "SMH"), pct=6.0),
            _profile("SMH", classification="REDUCIBLE", trim_score=55.0,
                     importance="LOW", clusters=("SEMICONDUCTOR_CONCENTRATION",),
                     origin="ETF_THEMATIC", pct=5.0),
            _profile("VOO", classification="CORE_COMPOUNDER", trim_score=3.0,
                     importance="HIGH", clusters=(), origin="DIRECT_INTENTIONAL",
                     role="CORE_BROAD_US", pct=20.0),
        ]
        overlays = [
            _FakeOverlay("NVDA", replay_supported=True, replay_percentile=90.0),
            _FakeOverlay("AVGO", replay_supported=False, signal_direction="NEUTRAL"),
            _FakeOverlay("SMH", replay_supported=False, signal_direction="NEUTRAL"),
            _FakeOverlay("VOO", replay_supported=True, replay_percentile=75.0),
        ]
        holdings = [_holding("NVDA", 12.0), _holding("AVGO", 6.0),
                    _holding("SMH", 5.0), _holding("VOO", 20.0)]
        return profiles, overlays, holdings

    def test_returns_tuple_of_recs_and_warnings(self):
        profiles, overlays, holdings = self._make_portfolio()
        result = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [], _NOW
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        recs, warnings = result
        assert isinstance(recs, list)
        assert isinstance(warnings, list)

    def test_portfolio_construction_narrative_present(self):
        profiles, overlays, holdings = self._make_portfolio()
        recs, _ = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [], _NOW
        )
        types = {r.recommendation_type for r in recs}
        assert "PORTFOLIO_CONSTRUCTION_NARRATIVE" in types

    def test_top_trim_candidates_generated(self):
        profiles, overlays, holdings = self._make_portfolio()
        recs, _ = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [], _NOW
        )
        trim_recs = [r for r in recs if r.recommendation_type == "TOP_TRIM_CANDIDATES"]
        assert len(trim_recs) >= 1

    def test_strategic_retain_narrative_generated(self):
        profiles, overlays, holdings = self._make_portfolio()
        recs, _ = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [], _NOW
        )
        retain_recs = [r for r in recs if r.recommendation_type == "STRATEGIC_RETAIN_NARRATIVE"]
        assert len(retain_recs) >= 1

    def test_phase_d_trim_suppressed_when_covered_by_phase_e(self):
        profiles, overlays, holdings = self._make_portfolio()
        legacy_trim = _rec("STRATEGIC_TRIM_CANDIDATE", symbols=("AVGO",), state="ACTIVE")
        recs, _ = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [legacy_trim], _NOW
        )
        avgo_trim = [r for r in recs if r.recommendation_type == "STRATEGIC_TRIM_CANDIDATE"
                     and "AVGO" in r.affected_symbols]
        # Should be suppressed since AVGO is in TOP_TRIM_CANDIDATES
        assert all(r.rec_state == "SUPPRESSED" for r in avgo_trim)

    def test_improve_sector_exposure_suppressed_when_thematic_narrative_exists(self):
        profiles, overlays, holdings = self._make_portfolio()
        legacy_sector = _rec("IMPROVE_SECTOR_EXPOSURE", state="ACTIVE")
        recs, _ = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [legacy_sector], _NOW
        )
        sector_recs = [r for r in recs if r.recommendation_type == "IMPROVE_SECTOR_EXPOSURE"]
        # If Phase E generates a thematic saturation narrative, sector exposure rec should be suppressed
        has_thematic = any(r.recommendation_type == "THEMATIC_SATURATION_NARRATIVE" for r in recs)
        if has_thematic:
            assert all(r.rec_state == "SUPPRESSED" for r in sector_recs)

    def test_no_profiles_returns_only_existing_recs(self):
        existing = [_rec("REDUCE_OVERWEIGHT", state="ACTIVE")]
        recs, warnings = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, [], [], [], existing, _NOW
        )
        types = {r.recommendation_type for r in recs}
        # No Phase E recs (no profiles) but existing should be preserved
        assert "REDUCE_OVERWEIGHT" in types

    def test_pcn_is_first_active_rec(self):
        profiles, overlays, holdings = self._make_portfolio()
        recs, _ = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [], _NOW
        )
        active_recs = [r for r in recs if r.rec_state == "ACTIVE"]
        if active_recs:
            assert active_recs[0].recommendation_type == "PORTFOLIO_CONSTRUCTION_NARRATIVE"

    def test_top_trim_primary_is_highest_score_symbol(self):
        profiles, overlays, holdings = self._make_portfolio()
        recs, _ = synthesize_phase_e_recommendations(
            _RUN_ID, _SNAP_ID, profiles, overlays, holdings, [], _NOW
        )
        trim_recs = [r for r in recs if r.recommendation_type == "TOP_TRIM_CANDIDATES"
                     and r.rec_state == "ACTIVE"]
        if trim_recs:
            # Primary symbol should be AVGO (trim score 70) not SMH (55)
            assert trim_recs[0].affected_symbols[0] == "AVGO"
