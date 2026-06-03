"""Phase 7.3C — Optimizer Preferred Candidate Display Tests.

Validates:
  1.  preferred_display is None when decision is not SECURITY_SUPERIOR.
  2.  preferred_display is None when preferred candidate matches legacy vehicle.
  3.  preferred_display is populated when SECURITY_SUPERIOR and preferred differs
      from legacy.
  4.  preferred_display.preferred_symbol matches the top-PIS security candidate.
  5.  preferred_display.legacy_symbol matches the first legacy_vehicles entry.
  6.  preferred_display.pis_delta is correct (preferred.pis − best_etf.pis).
  7.  preferred_display.key_advantages contains "Higher PIS" when pis_delta > 0.
  8.  preferred_display.key_advantages contains "Replay-supported" when
      preferred is replay-supported.
  9.  preferred_display.key_advantages contains STI tier advantage text.
  10. preferred_display.key_advantages contains "No overweight amplification"
      when legacy ETF worsens OW but preferred does not.
  11. preferred_display.key_advantages contains "Avoids ETF gate failure"
      when best ETF fails the gate.
  12. preferred_display.legacy_summary carries ETF gate, suitability, NCS fields.
  13. preferred_display.preferred_summary carries PIS, composite_score, sti_tier,
      replay_supported fields.
  14. preferred_display is None when optimizer_decision is ETF_ADEQUATE.
  15. preferred_display is None when optimizer_decision is MANDATE_BLOCKED.
  16. preferred_display is None when optimizer_decision is NO_CANDIDATES.
  17. Legacy recommendation fields are NOT modified by preferred_display injection.
  18. All INCREASE_UNDERWEIGHT recs have preferred_display key in optimizer_metadata
      (value may be None).
  19. VOO scenario: VOO is legacy vehicle, VRT is preferred — comparison is correct.
  20. preferred_display.preferred_summary.worsens_overweight is always False.
  21. run_parallel_optimizer injects preferred_display=None for REDUCE_COHERENT.
  22. run_parallel_optimizer injects preferred_display=None for NOT_APPLICABLE.
  23. preferred_display is None when preferred candidate has same symbol as legacy
      (case-insensitive).
  24. Strong composite score advantage added when composite_score >= 4.0.
  25. Composite score advantage NOT added when composite_score < 4.0.

Governance:
  - Legacy recommendation count must be UNCHANGED.
  - Legacy recommendation order must be UNCHANGED.
  - preferred_display is purely additive metadata — no action authority.
  - No replacement of legacy recommendations until Phase 7.3D.
"""
from __future__ import annotations

from typing import Optional

import pytest

from src.portfolio.optimizer import (
    _build_preferred_display,
    run_parallel_optimizer,
)
from src.portfolio.models import (
    AllocationAlignmentResult,
    MandateDriftInterpretation,
    PortfolioHolding,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / factories
# ─────────────────────────────────────────────────────────────────────────────

_NOW  = "2026-05-30T00:00:00Z"
_RUN  = "RUN-73C-TEST"
_SNAP = "PSNAP-73C-TEST"


def _holding(
    symbol: str,
    pct: float = 2.0,
    mcb: str = "LARGE",
    composite: Optional[float] = None,
    ess: Optional[str] = None,
    replay: bool = False,
) -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id=_SNAP,
        snapshot_date="2026-05-30",
        account_name="Test73C",
        symbol=symbol,
        description=f"{symbol} test",
        quantity=100.0,
        market_value=pct * 1000,
        percent_of_portfolio=pct,
        asset_class="EQUITIES",
        geography="US",
        market_cap_bucket=mcb,
        mega_subtier="N/A",
        sector="Technology",
        industry="ALL",
        security_type="STOCK",
        cost_basis=None,
        composite_score=composite,
        ess_score_text=ess,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        exposure_thematic_mix=(),
        exposure_mega_subtier_mix=(),
        strategic_role=None,
        is_cash_equivalent=False,
    )


def _alignment(
    node_key: str,
    drift: float = -7.34,
    direction: str = "UNDERWEIGHT",
    sev: str = "MODERATE",
) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id=_RUN,
        portfolio_snapshot_id=_SNAP,
        node_key=node_key,
        node_label=node_key,
        dimension_type="MARKET_CAP",
        actual_pct=8.0,
        target_pct=15.0,
        tactical_target_pct=15.0,
        drift_pct=drift,
        drift_direction=direction,
        severity=sev,
        concentration_risk="LOW",
        alignment_score=0.5,
        recommendation_priority=2,
        created_at_utc=_NOW,
        etf_derived_actual_pct=0.0,
    )


def _mandate_interp(
    node_key: str,
    urgency: str = "MODERATE",
    label: str = "STANDARD_UNDERWEIGHT",
    suppress: bool = False,
) -> MandateDriftInterpretation:
    return MandateDriftInterpretation(
        node_key=node_key,
        node_label=node_key,
        mandate_type="CONCENTRATED_ALPHA",
        raw_drift_pct=-7.34,
        raw_severity="MODERATE",
        mandate_severity="MODERATE" if urgency != "INFORMATIONAL" else "LOW",
        mandate_drift_label=label,
        mandate_urgency=urgency,
        mandate_rationale="test",
        suppress_recommendation=suppress,
    )


def _rec(
    rec_id: str,
    rec_type: str = "INCREASE_UNDERWEIGHT",
    node_key: str = "EQUITIES.US.LARGE",
    sev: str = "MODERATE",
    veh_notes: Optional[list] = None,
    affected_symbols: Optional[list] = None,
    mandate_urgency: str = "MODERATE",
) -> dict:
    return {
        "recommendation_id": rec_id,
        "recommendation_type": rec_type,
        "affected_node_key": node_key,
        "severity": sev,
        "title": f"Build {node_key}",
        "rationale": "test",
        "priority": 2,
        "vehicle_suitability_notes": veh_notes or [],
        "affected_symbols": affected_symbols or [],
        "drift_pct": -7.34,
        "mandate_urgency": mandate_urgency,
        "mandate_drift_label": "STANDARD_UNDERWEIGHT",
        "confidence": "MODERATE",
    }


_VOO_SUITABILITY_FAIL = {
    "symbol": "VOO",
    "target_node_coverage_pct": 15.0,
    "off_target_exposure_pct": 60.0,
    "overlap_with_existing_pct": 30.0,
    "worsens_existing_overweight": True,
    "thematic_concentration_added": "",
    "strategic_role": "BROAD_US_EQUITY",
    "suitability_score": 40.0,
    "suitability_tier": "LOW",
    "suitability_explanation": "VOO worsens Hyper/Ultra Mega overweight",
}

_VOO_SUITABILITY_PASS = {
    "symbol": "VOO",
    "target_node_coverage_pct": 55.0,
    "off_target_exposure_pct": 20.0,
    "overlap_with_existing_pct": 5.0,
    "worsens_existing_overweight": False,
    "thematic_concentration_added": "",
    "strategic_role": "BROAD_US_EQUITY",
    "suitability_score": 70.0,
    "suitability_tier": "MEDIUM",
    "suitability_explanation": "VOO acceptable coverage",
}


def _make_security_candidate(
    symbol: str,
    pis: float,
    sti_tier: str = "TGC",
    replay: bool = False,
    composite: Optional[float] = None,
    ess: Optional[str] = None,
) -> dict:
    """Minimal SECURITY candidate dict for unit-testing _build_preferred_display."""
    return {
        "symbol": symbol,
        "candidate_type": "SECURITY",
        "pis": pis,
        "sti_tier": sti_tier,
        "replay_supported": replay,
        "composite_score": composite,
        "ess_score": ess,
        "worsens_overweight": False,
        "etf_gate": "NA",
        "suitability_tier": "NA",
        "ncs": 100.0,
    }


def _make_etf_candidate(
    symbol: str,
    pis: float,
    etf_gate: str = "FAIL [suitability=LOW]",
    suitability_tier: str = "LOW",
    ncs: float = 5.0,
    worsens_overweight: bool = True,
) -> dict:
    """Minimal ETF candidate dict for unit-testing _build_preferred_display."""
    return {
        "symbol": symbol,
        "candidate_type": "ETF",
        "pis": pis,
        "sti_tier": "NA",
        "replay_supported": False,
        "composite_score": None,
        "ess_score": None,
        "worsens_overweight": worsens_overweight,
        "etf_gate": etf_gate,
        "suitability_tier": suitability_tier,
        "ncs": ncs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: _build_preferred_display
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildPreferredDisplay:

    def test_01_none_when_decision_not_security_superior(self):
        """preferred_display is None for ETF_ADEQUATE."""
        pref = _make_security_candidate("VRT", pis=40.0, replay=True)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(
            preferred_candidate=pref,
            legacy_vehicles=["VOO"],
            candidates=[pref, etf],
            optimizer_decision="ETF_ADEQUATE",
        )
        assert result is None

    def test_02_none_when_preferred_is_legacy(self):
        """preferred_display is None when preferred symbol == legacy vehicle."""
        pref = _make_security_candidate("VOO", pis=40.0)
        result = _build_preferred_display(
            preferred_candidate=pref,
            legacy_vehicles=["VOO"],
            candidates=[pref],
            optimizer_decision="SECURITY_SUPERIOR",
        )
        assert result is None

    def test_03_populated_when_security_superior_differs(self):
        """preferred_display is populated when SECURITY_SUPERIOR and symbols differ."""
        pref = _make_security_candidate("VRT", pis=40.0, replay=True)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(
            preferred_candidate=pref,
            legacy_vehicles=["VOO"],
            candidates=[pref, etf],
            optimizer_decision="SECURITY_SUPERIOR",
        )
        assert result is not None

    def test_04_preferred_symbol_correct(self):
        pref = _make_security_candidate("VRT", pis=40.0)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert result["preferred_symbol"] == "VRT"

    def test_05_legacy_symbol_from_first_vehicle(self):
        pref = _make_security_candidate("VRT", pis=40.0)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO", "SPY"], [pref, etf], "SECURITY_SUPERIOR")
        assert result["legacy_symbol"] == "VOO"

    def test_06_pis_delta_correct(self):
        """pis_delta = preferred.pis - best_etf.pis."""
        pref = _make_security_candidate("VRT", pis=40.0)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert result["pis_delta"] == 35.0

    def test_07_higher_pis_advantage_added(self):
        """key_advantages contains 'Higher PIS' when pis_delta > 0."""
        pref = _make_security_candidate("VRT", pis=40.0)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert any("Higher PIS" in a for a in result["key_advantages"])

    def test_08_replay_advantage_added(self):
        """key_advantages contains 'Replay-supported' when preferred.replay_supported."""
        pref = _make_security_candidate("VRT", pis=40.0, replay=True)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert "Replay-supported" in result["key_advantages"]

    def test_09_ccl_sti_advantage_added(self):
        """key_advantages contains 'Core conviction leader' for CCL tier."""
        pref = _make_security_candidate("VRT", pis=40.0, sti_tier="CCL")
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert "Core conviction leader" in result["key_advantages"]

    def test_09b_hca_sti_advantage_added(self):
        """key_advantages contains 'High conviction anchor' for HCA tier."""
        pref = _make_security_candidate("LRCX", pis=38.0, sti_tier="HCA")
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert "High conviction anchor" in result["key_advantages"]

    def test_10_no_overweight_amplification_advantage(self):
        """'No overweight amplification' added when legacy ETF worsens OW."""
        pref = _make_security_candidate("VRT", pis=40.0)
        etf  = _make_etf_candidate("VOO", pis=5.0, worsens_overweight=True)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert "No overweight amplification" in result["key_advantages"]

    def test_11_avoids_etf_gate_failure_advantage(self):
        """'Avoids ETF gate failure' added when best ETF gate is FAIL."""
        pref = _make_security_candidate("DELL", pis=36.0)
        etf  = _make_etf_candidate("VOO", pis=5.0, etf_gate="FAIL [suitability=LOW]")
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert "Avoids ETF gate failure" in result["key_advantages"]

    def test_12_legacy_summary_fields(self):
        """legacy_summary carries required ETF fields."""
        pref = _make_security_candidate("VRT", pis=40.0)
        etf  = _make_etf_candidate("VOO", pis=5.0, ncs=4.5, suitability_tier="LOW")
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        ls = result["legacy_summary"]
        assert ls is not None
        assert ls["symbol"] == "VOO"
        assert ls["type"] == "ETF"
        assert "pis" in ls
        assert "etf_gate" in ls
        assert "suitability_tier" in ls
        assert "ncs" in ls
        assert "worsens_overweight" in ls

    def test_13_preferred_summary_fields(self):
        """preferred_summary carries required SECURITY fields."""
        pref = _make_security_candidate("VRT", pis=40.0, composite=4.556, sti_tier="CCL", replay=True)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        ps = result["preferred_summary"]
        assert ps["symbol"] == "VRT"
        assert ps["type"] == "SECURITY"
        assert ps["pis"] == 40.0
        assert ps["composite_score"] == 4.556
        assert ps["sti_tier"] == "CCL"
        assert ps["replay_supported"] is True
        assert ps["worsens_overweight"] is False

    def test_14_none_when_etf_adequate(self):
        pref = _make_security_candidate("VRT", pis=40.0)
        result = _build_preferred_display(pref, ["VOO"], [pref], "ETF_ADEQUATE")
        assert result is None

    def test_15_none_when_mandate_blocked(self):
        pref = _make_security_candidate("VRT", pis=0.0)
        result = _build_preferred_display(pref, ["VOO"], [pref], "MANDATE_BLOCKED")
        assert result is None

    def test_16_none_when_no_candidates(self):
        result = _build_preferred_display(None, ["VOO"], [], "NO_CANDIDATES")
        assert result is None

    def test_20_preferred_summary_worsens_overweight_always_false(self):
        """preferred_summary.worsens_overweight is always False for SECURITY candidates."""
        pref = _make_security_candidate("VRT", pis=40.0)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert result["preferred_summary"]["worsens_overweight"] is False

    def test_23_case_insensitive_legacy_match(self):
        """preferred_display is None when preferred symbol matches legacy case-insensitively."""
        pref = _make_security_candidate("voo", pis=40.0)
        result = _build_preferred_display(pref, ["VOO"], [pref], "SECURITY_SUPERIOR")
        assert result is None

    def test_24_strong_composite_advantage(self):
        """'Strong composite score' added when composite_score >= 4.0."""
        pref = _make_security_candidate("VRT", pis=40.0, composite=4.556)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert any("composite score" in a.lower() for a in result["key_advantages"])

    def test_25_no_composite_advantage_below_4(self):
        """'Strong composite score' NOT added when composite_score < 4.0."""
        pref = _make_security_candidate("VRT", pis=40.0, composite=3.2)
        etf  = _make_etf_candidate("VOO", pis=5.0)
        result = _build_preferred_display(pref, ["VOO"], [pref, etf], "SECURITY_SUPERIOR")
        assert not any("composite score" in a.lower() for a in result["key_advantages"])


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests: run_parallel_optimizer → preferred_display field
# ─────────────────────────────────────────────────────────────────────────────

class TestRunParallelOptimizerPreferredDisplay:

    def _voo_scenario(self):
        """Build the canonical VOO-fails / VRT-wins scenario."""
        holdings = [
            _holding("VRT",  pct=2.0, mcb="LARGE", composite=4.556, ess="BULLISH", replay=True),
            _holding("LRCX", pct=1.8, mcb="LARGE", composite=4.500, replay=True),
            _holding("DELL", pct=1.5, mcb="LARGE", composite=4.200, replay=True),
        ]
        alignment = [
            _alignment("EQUITIES.US.LARGE", drift=-7.34),
            _alignment("EQUITIES.US.MEGA.HYPER_MEGA", drift=12.0, direction="OVERWEIGHT", sev="HIGH"),
        ]
        rec = _rec(
            "R001",
            node_key="EQUITIES.US.LARGE",
            veh_notes=[_VOO_SUITABILITY_FAIL],
            affected_symbols=["VOO"],
        )
        profiles = [
            {"symbol": "VRT",  "narrative_tier": "CCL", "trim_priority_score": 0.0},
            {"symbol": "LRCX", "narrative_tier": "HCA", "trim_priority_score": 0.0},
            {"symbol": "DELL", "narrative_tier": "HCA", "trim_priority_score": 0.0},
        ]
        interps = [_mandate_interp("EQUITIES.US.LARGE")]
        return holdings, alignment, [rec], profiles, interps

    def test_17_legacy_rec_fields_unchanged(self):
        """The original recommendation dict fields are NOT modified."""
        holdings, alignment, recs, profiles, interps = self._voo_scenario()
        original_rec = dict(recs[0])

        scores = run_parallel_optimizer(
            recs_with_overlay=recs,
            holdings=holdings,
            overlays=[],
            profiles=profiles,
            alignment_results=alignment,
            mandate_interpretations=interps,
        )
        # Run injects optimizer_metadata into recs[0] in runner.py,
        # but run_parallel_optimizer returns scores dict — rec unchanged here
        assert recs[0]["recommendation_id"] == original_rec["recommendation_id"]
        assert recs[0]["affected_node_key"] == original_rec["affected_node_key"]
        assert recs[0].get("optimizer_metadata") is None  # NOT injected by run_parallel_optimizer itself

    def test_18_all_increase_underweight_have_preferred_display_key(self):
        """All INCREASE_UNDERWEIGHT optimizer results have preferred_display key."""
        holdings, alignment, recs, profiles, interps = self._voo_scenario()
        scores = run_parallel_optimizer(
            recs_with_overlay=recs,
            holdings=holdings,
            overlays=[],
            profiles=profiles,
            alignment_results=alignment,
            mandate_interpretations=interps,
        )
        for result in scores.values():
            if result["rec_type"] == "INCREASE_UNDERWEIGHT":
                assert "preferred_display" in result

    def test_19_voo_vrt_comparison_correct(self):
        """VOO scenario: VRT is preferred, VOO is legacy, comparison is valid."""
        holdings, alignment, recs, profiles, interps = self._voo_scenario()
        scores = run_parallel_optimizer(
            recs_with_overlay=recs,
            holdings=holdings,
            overlays=[],
            profiles=profiles,
            alignment_results=alignment,
            mandate_interpretations=interps,
        )
        result = scores["R001"]
        assert result["optimizer_decision"] == "SECURITY_SUPERIOR"
        pd = result["preferred_display"]
        assert pd is not None
        assert pd["preferred_symbol"] in ("VRT", "LRCX", "DELL")  # top security by PIS
        assert pd["legacy_symbol"] == "VOO"
        assert pd["legacy_summary"] is not None
        assert pd["legacy_summary"]["symbol"] == "VOO"
        assert pd["preferred_summary"] is not None

    def test_21_reduce_coherent_preferred_display_none(self):
        """REDUCE_OVERWEIGHT recs get preferred_display=None."""
        reduce_rec = _rec("R002", rec_type="REDUCE_OVERWEIGHT", node_key="EQUITIES.US.MEGA")
        reduce_rec["severity"] = "HIGH"
        alignment = [
            _alignment("EQUITIES.US.MEGA", drift=12.0, direction="OVERWEIGHT", sev="HIGH"),
        ]
        scores = run_parallel_optimizer(
            recs_with_overlay=[reduce_rec],
            holdings=[],
            overlays=[],
            profiles=[],
            alignment_results=alignment,
            mandate_interpretations=[],
        )
        assert scores["R002"]["preferred_display"] is None

    def test_22_not_applicable_preferred_display_none(self):
        """Non-build/non-reduce rec types get preferred_display=None."""
        narrative_rec = {
            "recommendation_id": "R003",
            "recommendation_type": "NARRATIVE_OBSERVATION",
            "affected_node_key": None,
            "severity": "LOW",
            "title": "Narrative",
            "rationale": "test",
            "priority": 3,
            "vehicle_suitability_notes": [],
            "affected_symbols": [],
            "drift_pct": 0.0,
            "mandate_urgency": "INFORMATIONAL",
            "mandate_drift_label": "",
            "confidence": "LOW",
        }
        scores = run_parallel_optimizer(
            recs_with_overlay=[narrative_rec],
            holdings=[],
            overlays=[],
            profiles=[],
            alignment_results=[],
            mandate_interpretations=[],
        )
        assert scores["R003"]["preferred_display"] is None

    def test_mandate_blocked_preferred_display_none(self):
        """MANDATE_BLOCKED optimizer decisions get preferred_display=None."""
        rec = _rec(
            "R004",
            node_key="EQUITIES.US.LARGE",
            veh_notes=[_VOO_SUITABILITY_PASS],
            affected_symbols=["VOO"],
            mandate_urgency="INFORMATIONAL",
        )
        rec["mandate_urgency"] = "INFORMATIONAL"
        alignment = [_alignment("EQUITIES.US.LARGE", drift=-5.0)]
        interps = [_mandate_interp("EQUITIES.US.LARGE", urgency="INFORMATIONAL",
                                   label="INTENTIONAL_UNDERWEIGHT")]
        scores = run_parallel_optimizer(
            recs_with_overlay=[rec],
            holdings=[],
            overlays=[],
            profiles=[],
            alignment_results=alignment,
            mandate_interpretations=interps,
        )
        assert scores["R004"]["optimizer_decision"] == "MANDATE_BLOCKED"
        assert scores["R004"]["preferred_display"] is None

    def test_optimizer_version_is_7_3c(self):
        """optimizer_version field is set to '7.3C'."""
        holdings, alignment, recs, profiles, interps = self._voo_scenario()
        scores = run_parallel_optimizer(
            recs_with_overlay=recs,
            holdings=holdings,
            overlays=[],
            profiles=profiles,
            alignment_results=alignment,
            mandate_interpretations=interps,
        )
        assert scores["R001"]["optimizer_version"] == "7.3C"

    def test_legacy_rec_count_and_order_unchanged(self):
        """rec list count and order are not modified by the optimizer run."""
        holdings, alignment, recs, profiles, interps = self._voo_scenario()
        extra_recs = recs + [
            _rec("R005", rec_type="REDUCE_OVERWEIGHT", node_key="EQUITIES.US.MEGA"),
        ]
        original_ids = [r["recommendation_id"] for r in extra_recs]

        run_parallel_optimizer(
            recs_with_overlay=extra_recs,
            holdings=holdings,
            overlays=[],
            profiles=profiles,
            alignment_results=alignment + [
                _alignment("EQUITIES.US.MEGA", drift=12.0, direction="OVERWEIGHT", sev="HIGH"),
            ],
            mandate_interpretations=interps,
        )
        # rec list itself is not mutated (optimizer returns a separate scores dict)
        assert [r["recommendation_id"] for r in extra_recs] == original_ids
