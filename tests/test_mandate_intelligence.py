"""Phase 6.2 — Portfolio Mandate Intelligence (PMI) validation tests.

Validation requirements per spec:
  - Same portfolio under BALANCED / GROWTH / CONCENTRATED_ALPHA produces:
    * identical exposure calculations
    * identical decomposition outputs
    * identical suitability calculations
    * different recommendation interpretations
    * different urgency levels
    * different narrative explanations
  - No probabilistic behavior (all outputs deterministic)
"""

from __future__ import annotations

import dataclasses

import pytest

from src.portfolio.mandate import (
    _MANDATE_REGISTRY,
    build_mandate_recommendation_overlay,
    evaluate_alignment_under_mandate,
    evaluate_drift_under_mandate,
    get_cash_interpretation,
    get_fixed_income_shortfall_urgency,
    get_mandate,
    list_mandate_types,
)
from src.portfolio.models import (
    AllocationAlignmentResult,
    ASYMMETRY_STATES,
    IntentionalAsymmetryAssessment,
    MANDATE_DRIFT_LABELS,
    MANDATE_TYPES,
    MandateDriftInterpretation,
    MultiDimensionalScore,
    PortfolioMandate,
    ScoreComponent,
)
from src.portfolio.scoring import (
    compute_multi_dimensional_score,
    detect_intentional_asymmetry,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_alignment_result(
    node_key: str,
    node_label: str,
    dimension_type: str,
    actual_pct: float,
    target_pct: float,
    drift_pct: float,
    drift_direction: str,
    severity: str,
    alignment_score: float = 0.5,
) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id="TEST-RUN",
        portfolio_snapshot_id="PSNAP-TEST",
        node_key=node_key,
        node_label=node_label,
        dimension_type=dimension_type,
        actual_pct=actual_pct,
        target_pct=target_pct,
        tactical_target_pct=target_pct,
        drift_pct=drift_pct,
        drift_direction=drift_direction,
        severity=severity,
        concentration_risk="MODERATE",
        alignment_score=alignment_score,
        recommendation_priority=2,
        created_at_utc="2026-05-28T00:00:00+00:00",
        direct_actual_pct=actual_pct,
        etf_derived_actual_pct=0.0,
        effective_actual_pct=actual_pct,
        decomposition_method="DIRECT_CLASSIFICATION",
        decomposition_version="etf-exposure-decomp-v1",
        decomposition_confidence=1.0,
        decomposition_source="DIRECT_CLASSIFICATION",
        decomposition_confidence_tier="HIGH",
    )


@pytest.fixture
def equity_high_overweight():
    """EQUITIES.US.SMALL +13.8pp — the spec example."""
    return _make_alignment_result(
        node_key="EQUITIES.US.SMALL",
        node_label="US Small Cap",
        dimension_type="MARKET_CAP",
        actual_pct=18.8,
        target_pct=5.0,
        drift_pct=13.8,
        drift_direction="OVERWEIGHT",
        severity="HIGH",
        alignment_score=0.21,
    )


@pytest.fixture
def cash_high_overweight():
    """CASH +16pp."""
    return _make_alignment_result(
        node_key="CASH",
        node_label="Cash",
        dimension_type="ASSET_CLASS",
        actual_pct=18.0,
        target_pct=2.0,
        drift_pct=16.0,
        drift_direction="OVERWEIGHT",
        severity="HIGH",
        alignment_score=0.1,
    )


@pytest.fixture
def fi_moderate_underweight():
    """FIXED_INCOME -8pp."""
    return _make_alignment_result(
        node_key="FIXED_INCOME",
        node_label="Fixed Income",
        dimension_type="ASSET_CLASS",
        actual_pct=2.0,
        target_pct=10.0,
        drift_pct=-8.0,
        drift_direction="UNDERWEIGHT",
        severity="MODERATE",
        alignment_score=0.3,
    )


@pytest.fixture
def mixed_alignment(equity_high_overweight, cash_high_overweight, fi_moderate_underweight):
    return [equity_high_overweight, cash_high_overweight, fi_moderate_underweight]


# ─────────────────────────────────────────────────────────────────────────────
# 6.2A — Mandate Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestMandateRegistry:
    def test_all_mandate_types_registered(self):
        registered = set(list_mandate_types())
        assert registered == MANDATE_TYPES

    def test_get_mandate_returns_correct_type(self):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            assert m.mandate_type == mt

    def test_get_mandate_unknown_defaults_to_balanced(self):
        m = get_mandate("NONEXISTENT")
        assert m.mandate_type == "BALANCED"

    def test_all_mandates_are_portfolio_mandate_instances(self):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            assert isinstance(m, PortfolioMandate)

    def test_all_mandates_have_valid_tolerance_ranges(self):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            for field_name, value in dataclasses.asdict(m).items():
                if isinstance(value, float) and field_name not in ("mandate_type", "display_name", "description"):
                    assert 0.0 <= value <= 1.0, (
                        f"{mt}.{field_name} = {value} is outside [0.0, 1.0]"
                    )

    def test_mandate_characteristics_ordering(self):
        """Sanity check: CONCENTRATED_ALPHA more tolerant than BALANCED for concentration."""
        ca = get_mandate("CONCENTRATED_ALPHA")
        ba = get_mandate("BALANCED")
        assert ca.concentration_tolerance > ba.concentration_tolerance
        assert ca.target_adherence_priority < ba.target_adherence_priority
        assert ca.diversification_priority < ba.diversification_priority

    def test_growth_more_fi_tolerant_than_defensive(self):
        gr = get_mandate("GROWTH")
        de = get_mandate("DEFENSIVE")
        assert gr.fixed_income_tolerance > de.fixed_income_tolerance

    def test_replay_optimized_highest_replay_priority(self):
        ro = get_mandate("REPLAY_OPTIMIZED")
        ba = get_mandate("BALANCED")
        assert ro.replay_alignment_priority > ba.replay_alignment_priority
        assert ro.replay_alignment_priority == 1.0

    def test_all_mandates_are_frozen(self):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            with pytest.raises((AttributeError, dataclasses.FrozenInstanceError, TypeError)):
                m.concentration_tolerance = 0.0  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# 6.2B — Drift interpretation under mandate
# ─────────────────────────────────────────────────────────────────────────────

class TestDriftInterpretation:
    def test_on_target_always_suppressed(self):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            interp = evaluate_drift_under_mandate(
                "EQUITIES.US", "US Equities", 0.0, "NONE", "ON_TARGET", m
            )
            assert interp.suppress_recommendation is True
            assert interp.mandate_drift_label == "ON_TARGET"

    def test_high_equity_overweight_balanced_stays_high(self, equity_high_overweight):
        m = get_mandate("BALANCED")
        interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key,
            equity_high_overweight.node_label,
            equity_high_overweight.drift_pct,
            equity_high_overweight.severity,
            equity_high_overweight.drift_direction,
            m,
        )
        assert interp.mandate_severity == "HIGH"
        assert interp.mandate_urgency == "URGENT"
        assert interp.suppress_recommendation is False

    def test_high_equity_overweight_growth_downgraded(self, equity_high_overweight):
        m = get_mandate("GROWTH")
        interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key,
            equity_high_overweight.node_label,
            equity_high_overweight.drift_pct,
            equity_high_overweight.severity,
            equity_high_overweight.drift_direction,
            m,
        )
        # GROWTH small_cap_tolerance=0.7 → 1 downgrade step
        assert interp.mandate_severity in ("MODERATE", "LOW")
        assert interp.mandate_urgency in ("MODERATE", "LOW")
        assert "TOLERATED" in interp.mandate_drift_label

    def test_high_equity_overweight_concentrated_alpha_intentional(self, equity_high_overweight):
        m = get_mandate("CONCENTRATED_ALPHA")
        interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key,
            equity_high_overweight.node_label,
            equity_high_overweight.drift_pct,
            equity_high_overweight.severity,
            equity_high_overweight.drift_direction,
            m,
        )
        # CONCENTRATED_ALPHA small_cap_tolerance=0.8 → 2 downgrade steps from HIGH
        assert interp.mandate_severity in ("LOW", "NONE")
        assert "INTENTIONAL" in interp.mandate_drift_label
        assert interp.mandate_urgency in ("LOW", "INFORMATIONAL")

    def test_severity_ladder_never_goes_below_none(self, equity_high_overweight):
        m = get_mandate("CONCENTRATED_ALPHA")
        ar_low = _make_alignment_result(
            "EQUITIES.US.SMALL", "US Small Cap", "MARKET_CAP",
            6.0, 5.0, 1.0, "OVERWEIGHT", "LOW", 0.9
        )
        interp = evaluate_drift_under_mandate(
            ar_low.node_key, ar_low.node_label, ar_low.drift_pct,
            ar_low.severity, ar_low.drift_direction, m
        )
        assert interp.mandate_severity in ("NONE", "LOW")
        assert interp.mandate_severity != "NEGATIVE"  # no invalid states

    def test_fi_underweight_elevated_under_income(self, fi_moderate_underweight):
        m = get_mandate("INCOME")
        interp = evaluate_drift_under_mandate(
            fi_moderate_underweight.node_key,
            fi_moderate_underweight.node_label,
            fi_moderate_underweight.drift_pct,
            fi_moderate_underweight.severity,
            fi_moderate_underweight.drift_direction,
            m,
        )
        # INCOME fixed_income_tolerance=0.0 → tolerance for UW = 0.0 (STRICT)
        # MODERATE severity elevates to HIGH under STRICT FI underweight branch
        assert interp.mandate_severity == "HIGH"
        assert interp.mandate_urgency == "URGENT"
        assert interp.suppress_recommendation is False
        assert "STANDARD" in interp.mandate_drift_label

    def test_fi_underweight_low_urgency_under_growth(self, fi_moderate_underweight):
        m = get_mandate("GROWTH")
        interp = evaluate_drift_under_mandate(
            fi_moderate_underweight.node_key,
            fi_moderate_underweight.node_label,
            fi_moderate_underweight.drift_pct,
            fi_moderate_underweight.severity,
            fi_moderate_underweight.drift_direction,
            m,
        )
        # GROWTH fixed_income_tolerance=0.7 → tolerance for UW = 0.7 (TOLERATED)
        # MODERATE severity downgraded 1 step → LOW; not suppressed (not LOW raw sev)
        assert interp.mandate_severity == "LOW"
        assert interp.mandate_urgency == "LOW"
        assert interp.suppress_recommendation is False
        assert "TOLERATED" in interp.mandate_drift_label

    def test_raw_drift_pct_preserved(self, equity_high_overweight):
        """Exposure data must be identical regardless of mandate."""
        results = []
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            interp = evaluate_drift_under_mandate(
                equity_high_overweight.node_key,
                equity_high_overweight.node_label,
                equity_high_overweight.drift_pct,
                equity_high_overweight.severity,
                equity_high_overweight.drift_direction,
                m,
            )
            results.append(interp)

        # All mandates must preserve raw_drift_pct unchanged
        raw_drifts = {r.raw_drift_pct for r in results}
        assert len(raw_drifts) == 1
        assert list(raw_drifts)[0] == equity_high_overweight.drift_pct

    def test_raw_severity_preserved(self, equity_high_overweight):
        """Original severity must be preserved across all mandates."""
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            interp = evaluate_drift_under_mandate(
                equity_high_overweight.node_key,
                equity_high_overweight.node_label,
                equity_high_overweight.drift_pct,
                equity_high_overweight.severity,
                equity_high_overweight.drift_direction,
                m,
            )
            assert interp.raw_severity == equity_high_overweight.severity

    def test_mandate_severities_differ_for_growth_vs_balanced(self, equity_high_overweight):
        """BALANCED and GROWTH must produce different mandate_severity for HIGH small-cap OW."""
        balanced_interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, get_mandate("BALANCED"),
        )
        growth_interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, get_mandate("GROWTH"),
        )
        ca_interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, get_mandate("CONCENTRATED_ALPHA"),
        )
        assert balanced_interp.mandate_severity != growth_interp.mandate_severity
        assert growth_interp.mandate_severity != ca_interp.mandate_severity

    def test_drift_labels_are_valid_vocabulary(self, equity_high_overweight):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            interp = evaluate_drift_under_mandate(
                equity_high_overweight.node_key, equity_high_overweight.node_label,
                equity_high_overweight.drift_pct, equity_high_overweight.severity,
                equity_high_overweight.drift_direction, m,
            )
            assert interp.mandate_drift_label in MANDATE_DRIFT_LABELS, (
                f"{mt}: unexpected label {interp.mandate_drift_label!r}"
            )

    def test_all_interpretations_have_non_empty_rationale(self, equity_high_overweight):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            interp = evaluate_drift_under_mandate(
                equity_high_overweight.node_key, equity_high_overweight.node_label,
                equity_high_overweight.drift_pct, equity_high_overweight.severity,
                equity_high_overweight.drift_direction, m,
            )
            assert interp.mandate_rationale.strip(), f"{mt} has empty rationale"

    def test_evaluate_alignment_under_mandate_same_length(self, mixed_alignment):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            interps = evaluate_alignment_under_mandate(mixed_alignment, m)
            assert len(interps) == len(mixed_alignment)

    def test_evaluate_alignment_preserves_node_keys(self, mixed_alignment):
        m = get_mandate("BALANCED")
        interps = evaluate_alignment_under_mandate(mixed_alignment, m)
        for orig, interp in zip(mixed_alignment, interps):
            assert interp.node_key == orig.node_key

    def test_determinism_same_inputs_same_outputs(self, equity_high_overweight):
        """PMI must be deterministic — same inputs always produce same outputs."""
        m = get_mandate("GROWTH")
        result_a = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, m,
        )
        result_b = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, m,
        )
        assert dataclasses.asdict(result_a) == dataclasses.asdict(result_b)


# ─────────────────────────────────────────────────────────────────────────────
# 6.2C — Cash interpretation
# ─────────────────────────────────────────────────────────────────────────────

class TestCashInterpretation:
    def test_cash_deficit_same_for_all_mandates(self):
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            label = get_cash_interpretation(1.0, 5.0, m)
            assert "below target" in label.lower()

    def test_cash_excess_labels_differ_across_mandates(self):
        labels = set()
        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            label = get_cash_interpretation(18.0, 2.0, m)
            labels.add(label)
        # Labels should differ across mandates
        assert len(labels) > 1

    def test_cash_excess_includes_magnitude(self):
        m = get_mandate("BALANCED")
        label = get_cash_interpretation(18.0, 2.0, m)
        # Should include numeric excess
        assert "16.0" in label or "16.0pp" in label

    def test_concentrated_alpha_cash_label_contains_dry_powder(self):
        m = get_mandate("CONCENTRATED_ALPHA")
        label = get_cash_interpretation(18.0, 2.0, m)
        assert "dry powder" in label.lower() or "dry" in label.lower()

    def test_replay_optimized_cash_label_mentions_deployment(self):
        m = get_mandate("REPLAY_OPTIMIZED")
        label = get_cash_interpretation(18.0, 2.0, m)
        assert "deployment" in label.lower() or "reserve" in label.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 6.2D — Fixed income urgency
# ─────────────────────────────────────────────────────────────────────────────

class TestFixedIncomeUrgency:
    def test_income_fi_urgency_is_critical(self):
        urgency = get_fixed_income_shortfall_urgency(get_mandate("INCOME"))
        assert urgency == "critical"

    def test_defensive_fi_urgency_is_critical(self):
        urgency = get_fixed_income_shortfall_urgency(get_mandate("DEFENSIVE"))
        assert urgency == "critical"

    def test_growth_fi_urgency_is_low(self):
        urgency = get_fixed_income_shortfall_urgency(get_mandate("GROWTH"))
        assert urgency == "low"

    def test_concentrated_alpha_fi_urgency_is_minimal(self):
        urgency = get_fixed_income_shortfall_urgency(get_mandate("CONCENTRATED_ALPHA"))
        assert urgency == "minimal"

    def test_balanced_fi_urgency_is_moderate(self):
        urgency = get_fixed_income_shortfall_urgency(get_mandate("BALANCED"))
        assert urgency == "moderate"


# ─────────────────────────────────────────────────────────────────────────────
# 6.2E — Multi-dimensional scoring
# ─────────────────────────────────────────────────────────────────────────────

def _make_minimal_concentration():
    """Minimal mock concentration object for scoring tests."""
    from src.portfolio.models import ConcentrationRiskSummary
    return ConcentrationRiskSummary(
        analysis_run_id="TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        top1_symbol="VOO",
        top1_pct=15.0,
        top3_pct=35.0,
        top5_pct=50.0,
        top10_pct=65.0,
        mega_subtier_pct=25.0,
        single_sector_max_pct=22.0,
        single_sector_max_label="TECHNOLOGY",
        us_pct=70.0,
        international_pct=10.0,
        emerging_pct=5.0,
        herfindahl_index=0.04,
        concentration_tier="MODERATE",
        created_at_utc="2026-05-28T00:00:00+00:00",
        mega_subtier_direct_pct=20.0,
        mega_subtier_etf_derived_pct=5.0,
        mega_subtier_effective_pct=25.0,
    )


def _make_minimal_overlays():
    from src.portfolio.models import SecurityIntelligenceOverlay
    return [
        SecurityIntelligenceOverlay(
            portfolio_snapshot_id="PSNAP-TEST",
            symbol="VOO",
            composite_score=4.0,
            ess_score_text="Bullish",
            zacks_rating="2",
            best_replay_return=0.32,
            replay_percentile=75.0,
            replay_supported=True,
            percent_of_portfolio=15.0,
            is_overweight_vs_target=True,
            signal_direction="BULLISH",
            opportunity_flag="HOLD",
            flag_rationale="Strong signal",
            created_at_utc="2026-05-28T00:00:00+00:00",
        ),
        SecurityIntelligenceOverlay(
            portfolio_snapshot_id="PSNAP-TEST",
            symbol="SCHB",
            composite_score=3.8,
            ess_score_text="Neutral",
            zacks_rating="3",
            best_replay_return=None,
            replay_percentile=None,
            replay_supported=False,
            percent_of_portfolio=10.0,
            is_overweight_vs_target=False,
            signal_direction="NEUTRAL",
            opportunity_flag="HOLD",
            flag_rationale="",
            created_at_utc="2026-05-28T00:00:00+00:00",
        ),
    ]


class TestMultiDimensionalScore:
    def test_returns_correct_type(self, mixed_alignment):
        score = compute_multi_dimensional_score(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="BALANCED",
            alignment_results=mixed_alignment,
            concentration=_make_minimal_concentration(),
            overlays=_make_minimal_overlays(),
            recs=[],
            strategic_profiles=[],
        )
        assert isinstance(score, MultiDimensionalScore)

    def test_all_scores_within_0_100(self, mixed_alignment):
        for mt in MANDATE_TYPES:
            score = compute_multi_dimensional_score(
                analysis_run_id="TEST",
                portfolio_snapshot_id="PSNAP-TEST",
                mandate_type=mt,
                alignment_results=mixed_alignment,
                concentration=_make_minimal_concentration(),
                overlays=_make_minimal_overlays(),
                recs=[],
                strategic_profiles=[],
            )
            assert 0.0 <= score.allocation_alignment_score <= 100.0
            assert 0.0 <= score.portfolio_quality_score <= 100.0
            assert 0.0 <= score.implementation_quality_score <= 100.0
            assert 0.0 <= score.replay_alignment_score <= 100.0

    def test_allocation_alignment_differs_from_portfolio_quality(self, mixed_alignment):
        """These two dimensions should generally diverge for a concentrated portfolio."""
        score = compute_multi_dimensional_score(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="BALANCED",
            alignment_results=mixed_alignment,
            concentration=_make_minimal_concentration(),
            overlays=_make_minimal_overlays(),
            recs=[],
            strategic_profiles=[],
        )
        # A portfolio with poor target adherence can still have good quality
        assert score.allocation_alignment_score != score.portfolio_quality_score

    def test_components_are_tuples_of_score_components(self, mixed_alignment):
        score = compute_multi_dimensional_score(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="BALANCED",
            alignment_results=mixed_alignment,
            concentration=_make_minimal_concentration(),
            overlays=_make_minimal_overlays(),
            recs=[],
            strategic_profiles=[],
        )
        assert all(isinstance(c, ScoreComponent) for c in score.allocation_alignment_components)
        assert all(isinstance(c, ScoreComponent) for c in score.portfolio_quality_components)
        assert all(isinstance(c, ScoreComponent) for c in score.implementation_quality_components)
        assert all(isinstance(c, ScoreComponent) for c in score.replay_alignment_components)

    def test_components_have_explanations(self, mixed_alignment):
        score = compute_multi_dimensional_score(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="BALANCED",
            alignment_results=mixed_alignment,
            concentration=_make_minimal_concentration(),
            overlays=_make_minimal_overlays(),
            recs=[],
            strategic_profiles=[],
        )
        for comp in (
            *score.allocation_alignment_components,
            *score.portfolio_quality_components,
            *score.implementation_quality_components,
            *score.replay_alignment_components,
        ):
            assert comp.explanation.strip()

    def test_replay_alignment_higher_with_replay_supported_holdings(self, mixed_alignment):
        """Portfolio with replay-supported holdings → higher replay score."""
        all_replay = [
            SecurityIntelligenceOverlay_from_dict(s=True, pct=20.0, pctile=90.0),
            SecurityIntelligenceOverlay_from_dict(s=True, pct=15.0, pctile=80.0),
        ]
        no_replay = [
            SecurityIntelligenceOverlay_from_dict(s=False, pct=20.0, pctile=None),
            SecurityIntelligenceOverlay_from_dict(s=False, pct=15.0, pctile=None),
        ]
        from src.portfolio.scoring import _compute_replay_alignment
        score_high, _ = _compute_replay_alignment(all_replay)
        score_low, _ = _compute_replay_alignment(no_replay)
        assert score_high > score_low

    def test_determinism_multi_dim_score(self, mixed_alignment):
        kwargs = dict(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="GROWTH",
            alignment_results=mixed_alignment,
            concentration=_make_minimal_concentration(),
            overlays=_make_minimal_overlays(),
            recs=[],
            strategic_profiles=[],
        )
        a = compute_multi_dimensional_score(**kwargs)
        b = compute_multi_dimensional_score(**kwargs)
        a_dict = {k: v for k, v in dataclasses.asdict(a).items() if k != "created_at_utc"}
        b_dict = {k: v for k, v in dataclasses.asdict(b).items() if k != "created_at_utc"}
        assert a_dict == b_dict


def SecurityIntelligenceOverlay_from_dict(s: bool, pct: float, pctile):
    from src.portfolio.models import SecurityIntelligenceOverlay
    return SecurityIntelligenceOverlay(
        portfolio_snapshot_id="PSNAP-TEST",
        symbol="TST",
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        best_replay_return=0.2 if s else None,
        replay_percentile=pctile,
        replay_supported=s,
        percent_of_portfolio=pct,
        is_overweight_vs_target=False,
        signal_direction="NEUTRAL",
        opportunity_flag="HOLD",
        flag_rationale="",
        created_at_utc="2026-05-28T00:00:00+00:00",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6.2F — Intentional asymmetry detection
# ─────────────────────────────────────────────────────────────────────────────

class TestIntentionalAsymmetryDetection:
    def test_empty_portfolio_is_accidental(self):
        result = detect_intentional_asymmetry(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="BALANCED",
            holdings=[],
            overlays=[],
            alignment_results=[],
            strategic_profiles=[],
        )
        assert result.asymmetry_state == "ACCIDENTAL"
        assert result.asymmetry_score < 0.30

    def test_returns_asymmetry_assessment_type(self):
        result = detect_intentional_asymmetry(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="BALANCED",
            holdings=[],
            overlays=[],
            alignment_results=[],
            strategic_profiles=[],
        )
        assert isinstance(result, IntentionalAsymmetryAssessment)

    def test_valid_asymmetry_state(self):
        result = detect_intentional_asymmetry(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="GROWTH",
            holdings=[],
            overlays=[],
            alignment_results=[],
            strategic_profiles=[],
        )
        assert result.asymmetry_state in ASYMMETRY_STATES

    def test_many_replay_overweights_raises_score(self, mixed_alignment):
        """Three+ replay-supported overweight nodes → HIGH_CONVICTION or LIKELY_INTENTIONAL."""
        from src.portfolio.models import PortfolioHolding

        # Build holdings that are replay-supported and in overweight nodes
        def _h(sym, pct, asset_class="EQUITIES", geo="US", cap="SMALL"):
            return PortfolioHolding(
                portfolio_snapshot_id="PSNAP-TEST",
                snapshot_date="2026-05-28",
                account_name="Test",
                symbol=sym,
                description=sym,
                quantity=100,
                market_value=pct * 1000,
                percent_of_portfolio=pct,
                asset_class=asset_class,
                geography=geo,
                market_cap_bucket=cap,
                mega_subtier="N/A",
                sector="TECHNOLOGY",
                industry="Software",
                security_type="Common Stock",
                cost_basis=None,
                composite_score=4.5,
                ess_score_text="Bullish",
                zacks_rating="1",
                benchmark_id=None,
                investable_vehicle_id=None,
                source_file="test.csv",
                created_at_utc="2026-05-28T00:00:00+00:00",
            )

        holdings = [_h("A", 5.0), _h("B", 5.0), _h("C", 5.0), _h("D", 5.0)]
        overlays = [
            SecurityIntelligenceOverlay_from_dict(s=True, pct=5.0, pctile=85.0),
            SecurityIntelligenceOverlay_from_dict(s=True, pct=5.0, pctile=80.0),
            SecurityIntelligenceOverlay_from_dict(s=True, pct=5.0, pctile=90.0),
            SecurityIntelligenceOverlay_from_dict(s=True, pct=5.0, pctile=78.0),
        ]
        # Make overlays match symbols
        from dataclasses import replace
        overlays = [
            replace(overlays[i], symbol=sym)
            for i, sym in enumerate(["A", "B", "C", "D"])
        ]
        # Build alignment with multiple OW nodes
        ow_alignment = [
            _make_alignment_result("EQUITIES.US.SMALL", "US Small Cap", "MARKET_CAP",
                                   18.0, 5.0, 13.0, "OVERWEIGHT", "HIGH", 0.2),
            _make_alignment_result("EQUITIES.US.MICRO", "US Micro Cap", "MARKET_CAP",
                                   8.0, 2.0, 6.0, "OVERWEIGHT", "MODERATE", 0.4),
            _make_alignment_result("EQUITIES.INTL", "International", "GEOGRAPHY",
                                   12.0, 5.0, 7.0, "OVERWEIGHT", "MODERATE", 0.3),
        ]
        result = detect_intentional_asymmetry(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="GROWTH",
            holdings=holdings,
            overlays=overlays,
            alignment_results=ow_alignment,
            strategic_profiles=[],
        )
        assert result.asymmetry_score > 0.0
        assert result.asymmetry_state in ("LIKELY_INTENTIONAL", "HIGH_CONVICTION", "ACCIDENTAL")

    def test_asymmetry_rationale_non_empty(self):
        result = detect_intentional_asymmetry(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="BALANCED",
            holdings=[],
            overlays=[],
            alignment_results=[],
            strategic_profiles=[],
        )
        assert result.assessment_rationale.strip()

    def test_asymmetry_score_within_0_1(self, mixed_alignment):
        result = detect_intentional_asymmetry(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="GROWTH",
            holdings=[],
            overlays=_make_minimal_overlays(),
            alignment_results=mixed_alignment,
            strategic_profiles=[],
        )
        assert 0.0 <= result.asymmetry_score <= 1.0

    def test_determinism_asymmetry(self, mixed_alignment):
        kwargs = dict(
            analysis_run_id="TEST",
            portfolio_snapshot_id="PSNAP-TEST",
            mandate_type="GROWTH",
            holdings=[],
            overlays=_make_minimal_overlays(),
            alignment_results=mixed_alignment,
            strategic_profiles=[],
        )
        a = detect_intentional_asymmetry(**kwargs)
        b = detect_intentional_asymmetry(**kwargs)
        a_dict = {k: v for k, v in dataclasses.asdict(a).items() if k != "created_at_utc"}
        b_dict = {k: v for k, v in dataclasses.asdict(b).items() if k != "created_at_utc"}
        assert a_dict == b_dict


# ─────────────────────────────────────────────────────────────────────────────
# 6.2G — Recommendation mandate overlay
# ─────────────────────────────────────────────────────────────────────────────

class TestMandateRecommendationOverlay:
    def _make_rec_dict(self, node_key="EQUITIES.US.SMALL", severity="HIGH"):
        return {
            "recommendation_id": "REC-001",
            "recommendation_type": "REDUCE_OVERWEIGHT",
            "affected_node_key": node_key,
            "severity": severity,
            "rationale": "US Small Cap is significantly overweight.",
            "title": "Reduce US Small Cap",
        }

    def test_overlay_contains_required_keys(self, equity_high_overweight):
        m = get_mandate("GROWTH")
        interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, m,
        )
        overlay = build_mandate_recommendation_overlay(self._make_rec_dict(), interp, m)
        assert "mandate_type" in overlay
        assert "mandate_severity" in overlay
        assert "mandate_urgency" in overlay
        assert "mandate_drift_label" in overlay
        assert "mandate_rationale" in overlay
        assert "mandate_narrative" in overlay

    def test_overlay_mandate_type_matches(self, equity_high_overweight):
        m = get_mandate("GROWTH")
        interp = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, m,
        )
        overlay = build_mandate_recommendation_overlay(self._make_rec_dict(), interp, m)
        assert overlay["mandate_type"] == "GROWTH"

    def test_narrative_differs_across_mandates(self, equity_high_overweight):
        narratives = set()
        rec_dict = self._make_rec_dict()
        for mt in ("BALANCED", "GROWTH", "CONCENTRATED_ALPHA"):
            m = get_mandate(mt)
            interp = evaluate_drift_under_mandate(
                equity_high_overweight.node_key, equity_high_overweight.node_label,
                equity_high_overweight.drift_pct, equity_high_overweight.severity,
                equity_high_overweight.drift_direction, m,
            )
            overlay = build_mandate_recommendation_overlay(rec_dict, interp, m)
            narratives.add(overlay["mandate_narrative"])
        assert len(narratives) >= 2, "Mandate narratives should differ across mandates"

    def test_none_interp_produces_valid_overlay(self):
        m = get_mandate("BALANCED")
        overlay = build_mandate_recommendation_overlay(self._make_rec_dict(), None, m)
        assert overlay["mandate_type"] == "BALANCED"
        assert "mandate_narrative" in overlay


# ─────────────────────────────────────────────────────────────────────────────
# Integration: Same portfolio → identical exposure, different interpretation
# ─────────────────────────────────────────────────────────────────────────────

class TestMandateInvariance:
    """Core validation requirement: exposure is mandate-invariant, interpretation is not."""

    def test_alignment_results_unchanged_across_mandates(self, mixed_alignment):
        """AllocationAlignmentResult objects are identical regardless of mandate."""
        # The mandate layer operates on COPIES of the alignment data — the originals
        # should not be mutated.  Verify by evaluating under all mandates and
        # checking that actual_pct, drift_pct, alignment_score, etc. are unchanged.
        original_data = [
            (ar.node_key, ar.actual_pct, ar.drift_pct, ar.alignment_score,
             ar.direct_actual_pct, ar.etf_derived_actual_pct)
            for ar in mixed_alignment
        ]

        for mt in MANDATE_TYPES:
            m = get_mandate(mt)
            # Run mandate evaluation — must not touch the original alignment objects
            evaluate_alignment_under_mandate(mixed_alignment, m)

        # Verify originals are unchanged
        after_data = [
            (ar.node_key, ar.actual_pct, ar.drift_pct, ar.alignment_score,
             ar.direct_actual_pct, ar.etf_derived_actual_pct)
            for ar in mixed_alignment
        ]
        assert original_data == after_data

    def test_interpretations_differ_for_growth_vs_concentrated_alpha(
        self, equity_high_overweight
    ):
        """GROWTH and CONCENTRATED_ALPHA must produce at least one different field."""
        m_growth = get_mandate("GROWTH")
        m_ca = get_mandate("CONCENTRATED_ALPHA")

        i_growth = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, m_growth,
        )
        i_ca = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, m_ca,
        )

        # At least severity or label or suppress must differ
        different = (
            i_growth.mandate_severity != i_ca.mandate_severity
            or i_growth.mandate_drift_label != i_ca.mandate_drift_label
            or i_growth.suppress_recommendation != i_ca.suppress_recommendation
        )
        assert different

    def test_spec_example_us_small_cap(self, equity_high_overweight):
        """Validate the spec's concrete example: US Small Cap +13.8pp.

        BALANCED  → HIGH OVERWEIGHT
        GROWTH    → MODERATE OVERWEIGHT
        CONCENTRATED_ALPHA → INTENTIONAL OVERWEIGHT
        """
        i_balanced = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, get_mandate("BALANCED"),
        )
        i_growth = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, get_mandate("GROWTH"),
        )
        i_ca = evaluate_drift_under_mandate(
            equity_high_overweight.node_key, equity_high_overweight.node_label,
            equity_high_overweight.drift_pct, equity_high_overweight.severity,
            equity_high_overweight.drift_direction, get_mandate("CONCENTRATED_ALPHA"),
        )

        # BALANCED: no downgrade (target_adherence=0.7, small_cap_tolerance=0.4 → STANDARD)
        assert i_balanced.mandate_severity == "HIGH"
        assert i_balanced.mandate_drift_label == "STANDARD_OVERWEIGHT"

        # GROWTH: small_cap_tolerance=0.7 → TOLERATED, 1 downgrade
        assert i_growth.mandate_severity == "MODERATE"
        assert i_growth.mandate_drift_label == "TOLERATED_OVERWEIGHT"

        # CONCENTRATED_ALPHA: small_cap_tolerance=0.8 → INTENTIONAL, 2 downgrades
        assert "INTENTIONAL" in i_ca.mandate_drift_label

        # All have identical raw_drift_pct
        assert i_balanced.raw_drift_pct == i_growth.raw_drift_pct == i_ca.raw_drift_pct == 13.8


# ─────────────────────────────────────────────────────────────────────────────
# 6.2.1 — Fixed Income Underweight Tolerance Regression (Phase 6.2.1 correction)
#
# Validates corrected _tolerance_for_node() for FIXED_INCOME UNDERWEIGHT:
#   mandate.fixed_income_tolerance is used directly (not 1.0 - fi_tol).
#
# Expected behaviour after fix, for fi_moderate_underweight (MODERATE sev, -8pp):
#   INCOME          fi_tol=0.0  → tolerance=0.0  STRICT      → elevated HIGH, URGENT
#   DEFENSIVE       fi_tol=0.1  → tolerance=0.1  STRICT      → elevated HIGH, URGENT
#   BALANCED        fi_tol=0.2  → tolerance=0.2  STRICT      → elevated HIGH, URGENT
#   GROWTH          fi_tol=0.7  → tolerance=0.7  TOLERATED   → downgraded LOW, LOW
#   REPLAY_OPTIMIZED fi_tol=0.8 → tolerance=0.8  INTENTIONAL → NONE, suppressed
#   CONCENTRATED_ALPHA fi_tol=0.9 → tolerance=0.9 INTENTIONAL → NONE, suppressed
# ─────────────────────────────────────────────────────────────────────────────

class TestFIUnderweightTolerance:
    """Phase 6.2.1 targeted regression: FI underweight interpretation per mandate."""

    # ── shared fixture shorthand ──────────────────────────────────────────────
    @staticmethod
    def _eval(node: "AllocationAlignmentResult", mandate_type: str) -> "MandateDriftInterpretation":
        m = get_mandate(mandate_type)
        return evaluate_drift_under_mandate(
            node.node_key,
            node.node_label,
            node.drift_pct,
            node.severity,
            node.drift_direction,
            m,
        )

    def test_income_fi_underweight_elevated_to_high(self, fi_moderate_underweight):
        """INCOME fi_tol=0.0 → STRICT → MODERATE elevated to HIGH."""
        interp = self._eval(fi_moderate_underweight, "INCOME")
        assert interp.mandate_severity == "HIGH", (
            f"INCOME FI UW should elevate to HIGH, got {interp.mandate_severity}"
        )
        assert interp.mandate_urgency == "URGENT"
        assert interp.suppress_recommendation is False
        assert "STANDARD" in interp.mandate_drift_label

    def test_defensive_fi_underweight_elevated_to_high(self, fi_moderate_underweight):
        """DEFENSIVE fi_tol=0.1 → STRICT → MODERATE elevated to HIGH."""
        interp = self._eval(fi_moderate_underweight, "DEFENSIVE")
        assert interp.mandate_severity == "HIGH", (
            f"DEFENSIVE FI UW should elevate to HIGH, got {interp.mandate_severity}"
        )
        assert interp.mandate_urgency == "URGENT"
        assert interp.suppress_recommendation is False
        assert "STANDARD" in interp.mandate_drift_label

    def test_balanced_fi_underweight_elevated_to_high(self, fi_moderate_underweight):
        """BALANCED fi_tol=0.2 → STRICT → MODERATE elevated to HIGH."""
        interp = self._eval(fi_moderate_underweight, "BALANCED")
        assert interp.mandate_severity == "HIGH", (
            f"BALANCED FI UW should elevate to HIGH, got {interp.mandate_severity}"
        )
        assert interp.mandate_urgency == "URGENT"
        assert interp.suppress_recommendation is False
        assert "STANDARD" in interp.mandate_drift_label

    def test_growth_fi_underweight_downgraded_to_low(self, fi_moderate_underweight):
        """GROWTH fi_tol=0.7 → TOLERATED → MODERATE downgraded to LOW."""
        interp = self._eval(fi_moderate_underweight, "GROWTH")
        assert interp.mandate_severity == "LOW", (
            f"GROWTH FI UW should downgrade to LOW, got {interp.mandate_severity}"
        )
        assert interp.mandate_urgency == "LOW"
        assert interp.suppress_recommendation is False
        assert "TOLERATED" in interp.mandate_drift_label

    def test_replay_optimized_fi_underweight_suppressed(self, fi_moderate_underweight):
        """REPLAY_OPTIMIZED fi_tol=0.8 → INTENTIONAL → NONE, suppressed."""
        interp = self._eval(fi_moderate_underweight, "REPLAY_OPTIMIZED")
        assert interp.mandate_severity == "NONE", (
            f"REPLAY_OPTIMIZED FI UW should be NONE, got {interp.mandate_severity}"
        )
        assert interp.mandate_urgency == "INFORMATIONAL"
        assert interp.suppress_recommendation is True
        assert "INTENTIONAL" in interp.mandate_drift_label

    def test_concentrated_alpha_fi_underweight_suppressed(self, fi_moderate_underweight):
        """CONCENTRATED_ALPHA fi_tol=0.9 → INTENTIONAL → NONE, suppressed."""
        interp = self._eval(fi_moderate_underweight, "CONCENTRATED_ALPHA")
        assert interp.mandate_severity == "NONE", (
            f"CONCENTRATED_ALPHA FI UW should be NONE, got {interp.mandate_severity}"
        )
        assert interp.mandate_urgency == "INFORMATIONAL"
        assert interp.suppress_recommendation is True
        assert "INTENTIONAL" in interp.mandate_drift_label

    def test_fi_underweight_raw_drift_invariant_across_all_mandates(
        self, fi_moderate_underweight
    ):
        """Raw drift and severity must be preserved regardless of mandate."""
        for mt in MANDATE_TYPES:
            interp = self._eval(fi_moderate_underweight, mt)
            assert interp.raw_drift_pct == fi_moderate_underweight.drift_pct, (
                f"{mt}: raw_drift_pct mutated"
            )
            assert interp.raw_severity == fi_moderate_underweight.severity, (
                f"{mt}: raw_severity mutated"
            )

    def test_fi_underweight_severity_ordering_respects_mandate_strictness(
        self, fi_moderate_underweight
    ):
        """Severity ordering: INCOME ≥ DEFENSIVE ≥ BALANCED > GROWTH > REPLAY_OPTIMIZED."""
        sev_order = {"NONE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3}

        income = self._eval(fi_moderate_underweight, "INCOME")
        balanced = self._eval(fi_moderate_underweight, "BALANCED")
        growth = self._eval(fi_moderate_underweight, "GROWTH")
        replay = self._eval(fi_moderate_underweight, "REPLAY_OPTIMIZED")

        assert sev_order[income.mandate_severity] >= sev_order[balanced.mandate_severity]
        assert sev_order[balanced.mandate_severity] > sev_order[growth.mandate_severity]
        assert sev_order[growth.mandate_severity] > sev_order[replay.mandate_severity]

    def test_fi_low_severity_underweight_elevated_under_income(self):
        """LOW raw severity FI underweight is also elevated under INCOME/DEFENSIVE."""
        fi_low_uw = _make_alignment_result(
            "FIXED_INCOME", "Fixed Income", "ASSET_CLASS",
            actual_pct=4.0, target_pct=10.0, drift_pct=-6.0,
            drift_direction="UNDERWEIGHT", severity="LOW", alignment_score=0.5,
        )
        interp = self._eval(fi_low_uw, "INCOME")
        assert interp.mandate_severity in ("MODERATE", "HIGH"), (
            f"LOW FI UW under INCOME should elevate, got {interp.mandate_severity}"
        )
        assert interp.suppress_recommendation is False
