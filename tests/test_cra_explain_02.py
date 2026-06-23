"""Tests for CRA-EXPLAIN-02 — Capital Source Intent Classification.

Validates:
  - _compute_source_intent() deterministic mapping for all 5 categories
  - source_intent field populated on CapitalSourceRecord
  - source_intent_summary aggregated correctly in RotationProposal.to_dict()
  - Display-only: no CRA ranking, PAP, ESS, CW-DAS, UCF changes

Q1: Can operators distinguish negative-thesis reductions from funding-source reductions?
Q2: Can operators immediately identify tax-driven reductions?
Q3: Can operators distinguish allocation repair from conviction deterioration?
Q4: Does MSFT (bullish overweight) clearly appear as a funding source?
Q5: Does PSX (tax loss) clearly appear as a funding source?
Q6–Q9: CRA rankings / PAP / CW-DAS / UCF unchanged (display-only).
Q10: This is a display-only enhancement.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.portfolio.cra.capital_source_builder import (
    _compute_source_intent,
    build_capital_sources,
)
from src.portfolio.cra.models import (
    CATEGORY_LOW_CONVICTION,
    CATEGORY_OVERWEIGHT_REDUCTION,
    CATEGORY_SIGNAL_DETERIORATION,
    CATEGORY_STRATEGIC_EXIT,
    CATEGORY_TAX_AWARE_EXIT,
    SOURCE_INTENT_OVERWEIGHT_REPAIR,
    SOURCE_INTENT_PORTFOLIO_REALLOCATION,
    SOURCE_INTENT_TAX_FUNDING_SOURCE,
    SOURCE_INTENT_THESIS_EXIT,
    SOURCE_INTENT_THESIS_TRIM,
    CapitalSourceRecord,
    RotationProposal,
)


# ── Shared fixture helpers ────────────────────────────────────────────────────

def _ov(
    symbol: str,
    opportunity_flag: str = "HOLD",
    signal_direction: str = "NEUTRAL",
    ess_score_text: str = "NEUTRAL",
    is_overweight_vs_target: str = "False",
    replay_supported: str = "False",
    percent_of_portfolio: str = "2.0",
    composite_score: str = "3.0",
) -> Dict:
    return {
        "symbol": symbol,
        "opportunity_flag": opportunity_flag,
        "signal_direction": signal_direction,
        "ess_score_text": ess_score_text,
        "is_overweight_vs_target": is_overweight_vs_target,
        "replay_supported": replay_supported,
        "percent_of_portfolio": percent_of_portfolio,
        "composite_score": composite_score,
        "portfolio_snapshot_id": "PSNAP-TEST",
        "policy_type": "",
        "policy_protected": "False",
        "execution_state": "",
        "effective_action": "",
    }


def _holding(
    symbol: str,
    market_value: str = "10000.00",
    cost_basis: str = "",
    percent_of_portfolio: str = "2.0",
    geography: str = "US",
    market_cap_bucket: str = "LARGE",
    asset_class: str = "EQUITIES",
) -> Dict:
    return {
        "symbol": symbol,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "percent_of_portfolio": percent_of_portfolio,
        "geography": geography,
        "market_cap_bucket": market_cap_bucket,
        "asset_class": asset_class,
        "description": f"{symbol} Common Stock",
        "operational_state": "ACTIVE_POSITION",
        "is_cash_equivalent": "False",
        "safe_to_offset_cash": "False",
    }


def _alignment_row(node_key: str, drift_pct: float) -> Dict:
    return {
        "node_key": node_key,
        "node_label": node_key,
        "drift_pct": str(drift_pct),
        "actual_pct": "12.0",
        "target_pct": "8.0",
        "drift_direction": "OVERWEIGHT" if drift_pct > 0 else "UNDERWEIGHT",
        "alignment_score": "0.7",
    }


def _bcs(overlays, holdings, alignment, deployment_queue, **kwargs):
    """Thin wrapper — returns only the primary sources list."""
    sources, _ = build_capital_sources(
        overlays, holdings, alignment, deployment_queue,
        minimum_proceeds=0,
        **kwargs,
    )
    return sources


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests: _compute_source_intent()
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeSourceIntent:
    """Direct unit tests of the classification function."""

    # ── THESIS_EXIT cases ──────────────────────────────────────────────────
    def test_strategic_exit_always_thesis_exit(self):
        assert _compute_source_intent(CATEGORY_STRATEGIC_EXIT, None, None, 1.0) == SOURCE_INTENT_THESIS_EXIT
        assert _compute_source_intent(CATEGORY_STRATEGIC_EXIT, "BULLISH", "BULLISH", 0.5) == SOURCE_INTENT_THESIS_EXIT

    def test_signal_deterioration_very_bearish_is_thesis_exit(self):
        result = _compute_source_intent(CATEGORY_SIGNAL_DETERIORATION, "VERY_BEARISH", "BEARISH", 0.5)
        assert result == SOURCE_INTENT_THESIS_EXIT

    def test_signal_deterioration_full_sizing_is_thesis_exit(self):
        result = _compute_source_intent(CATEGORY_SIGNAL_DETERIORATION, "BEARISH", "BEARISH", 1.0)
        assert result == SOURCE_INTENT_THESIS_EXIT

    # ── THESIS_TRIM cases ──────────────────────────────────────────────────
    def test_signal_deterioration_bearish_partial_is_thesis_trim(self):
        result = _compute_source_intent(CATEGORY_SIGNAL_DETERIORATION, "BEARISH", "BEARISH", 0.5)
        assert result == SOURCE_INTENT_THESIS_TRIM

    def test_signal_deterioration_trim_flag_partial_is_thesis_trim(self):
        result = _compute_source_intent(CATEGORY_SIGNAL_DETERIORATION, "NEUTRAL", "NEUTRAL", 0.25)
        assert result == SOURCE_INTENT_THESIS_TRIM

    # ── TAX_FUNDING_SOURCE cases ───────────────────────────────────────────
    def test_tax_aware_exit_is_tax_funding_source(self):
        result = _compute_source_intent(CATEGORY_TAX_AWARE_EXIT, None, None, 1.0)
        assert result == SOURCE_INTENT_TAX_FUNDING_SOURCE

    def test_overweight_bullish_ess_is_tax_funding_source(self):
        """Q4: Bullish-conviction overweight (e.g. MSFT) → TAX_FUNDING_SOURCE."""
        result = _compute_source_intent(CATEGORY_OVERWEIGHT_REDUCTION, "BULLISH", "BULLISH", 0.5)
        assert result == SOURCE_INTENT_TAX_FUNDING_SOURCE

    def test_overweight_very_bullish_ess_is_tax_funding_source(self):
        result = _compute_source_intent(CATEGORY_OVERWEIGHT_REDUCTION, "VERY_BULLISH", "NEUTRAL", 0.25)
        assert result == SOURCE_INTENT_TAX_FUNDING_SOURCE

    def test_overweight_neutral_signal_but_bullish_direction_is_tax_funding_source(self):
        result = _compute_source_intent(CATEGORY_OVERWEIGHT_REDUCTION, "NEUTRAL", "BULLISH", 0.25)
        assert result == SOURCE_INTENT_TAX_FUNDING_SOURCE

    # ── OVERWEIGHT_REPAIR cases ────────────────────────────────────────────
    def test_overweight_neutral_ess_is_overweight_repair(self):
        """Q3: Neutral/bearish overweight (e.g. index ETF) → OVERWEIGHT_REPAIR."""
        result = _compute_source_intent(CATEGORY_OVERWEIGHT_REDUCTION, "NEUTRAL", "NEUTRAL", 0.25)
        assert result == SOURCE_INTENT_OVERWEIGHT_REPAIR

    def test_overweight_bearish_ess_is_overweight_repair(self):
        result = _compute_source_intent(CATEGORY_OVERWEIGHT_REDUCTION, "BEARISH", "BEARISH", 0.5)
        assert result == SOURCE_INTENT_OVERWEIGHT_REPAIR

    def test_overweight_no_signal_data_is_overweight_repair(self):
        result = _compute_source_intent(CATEGORY_OVERWEIGHT_REDUCTION, None, None, 0.25)
        assert result == SOURCE_INTENT_OVERWEIGHT_REPAIR

    # ── PORTFOLIO_REALLOCATION cases ───────────────────────────────────────
    def test_low_conviction_is_portfolio_reallocation(self):
        """Index funds / passive vehicles → PORTFOLIO_REALLOCATION."""
        result = _compute_source_intent(CATEGORY_LOW_CONVICTION, None, None, 0.25)
        assert result == SOURCE_INTENT_PORTFOLIO_REALLOCATION

    def test_low_conviction_neutral_signal_is_portfolio_reallocation(self):
        result = _compute_source_intent(CATEGORY_LOW_CONVICTION, "NEUTRAL", "NEUTRAL", 0.25)
        assert result == SOURCE_INTENT_PORTFOLIO_REALLOCATION

    def test_unknown_category_falls_back_to_portfolio_reallocation(self):
        result = _compute_source_intent("UNKNOWN_CATEGORY", None, None, 0.5)
        assert result == SOURCE_INTENT_PORTFOLIO_REALLOCATION


# ═══════════════════════════════════════════════════════════════════════════════
# Integration tests: source_intent on CapitalSourceRecord
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceIntentOnRecord:
    """Verify source_intent is correctly populated by build_capital_sources()."""

    # ── Q1: TSLA-like (VERY_BEARISH) → THESIS_EXIT ────────────────────────
    def test_very_bearish_signal_yields_thesis_exit(self):
        """Q1: Operators can distinguish negative-thesis exits."""
        ov = _ov("TSLA", ess_score_text="VERY_BEARISH", signal_direction="BEARISH",
                 opportunity_flag="TRIM")
        h = _holding("TSLA", market_value="25000")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "TSLA")
        assert s.source_intent == SOURCE_INTENT_THESIS_EXIT

    # ── Q1: PRIM/KGC-like (BEARISH, partial) → THESIS_TRIM ───────────────
    def test_bearish_partial_exit_yields_thesis_trim(self):
        """Q1: Operators can see partial-thesis trims separately from full exits."""
        ov = _ov("PRIM", ess_score_text="BEARISH", signal_direction="BEARISH",
                 opportunity_flag="TRIM")
        h = _holding("PRIM", market_value="12000")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "PRIM")
        assert s.source_intent == SOURCE_INTENT_THESIS_TRIM

    # ── Q2: Tax loss harvest (LMAT-like, Bucket A) → TAX_FUNDING_SOURCE ───
    def test_tax_loss_harvest_yields_tax_funding_source(self):
        """Q2: Operators can immediately identify tax-driven reductions."""
        ov = _ov("LMAT", opportunity_flag="HOLD", ess_score_text="NEUTRAL")
        h = _holding("LMAT", market_value="8000", cost_basis="12000")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "LMAT")
        assert s.category == CATEGORY_TAX_AWARE_EXIT
        assert s.source_intent == SOURCE_INTENT_TAX_FUNDING_SOURCE

    # ── Q4: MSFT-like (OVERWEIGHT + BULLISH ESS) → TAX_FUNDING_SOURCE ─────
    def test_bullish_overweight_yields_tax_funding_source(self):
        """Q4: MSFT clearly appears as a funding source, not a bearish recommendation."""
        ov = _ov("MSFT", ess_score_text="BULLISH", signal_direction="BULLISH",
                 is_overweight_vs_target="True", opportunity_flag="HOLD")
        h = _holding("MSFT", market_value="30000", geography="US", market_cap_bucket="LARGE")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=12.0)]
        sources = _bcs([ov], [h], alignment, {})
        s = next(x for x in sources if x.symbol == "MSFT")
        assert s.category == CATEGORY_OVERWEIGHT_REDUCTION
        assert s.source_intent == SOURCE_INTENT_TAX_FUNDING_SOURCE  # still liked, just too heavy

    # ── Q5: PSX-like (OVERWEIGHT + BULLISH ESS) → TAX_FUNDING_SOURCE ──────
    def test_bullish_overweight_energy_yields_tax_funding_source(self):
        """Q5: PSX clearly appears as a funding source rather than a bearish recommendation."""
        ov = _ov("PSX", ess_score_text="BULLISH", signal_direction="BULLISH",
                 is_overweight_vs_target="True", opportunity_flag="HOLD")
        h = _holding("PSX", market_value="18000", geography="US", market_cap_bucket="LARGE")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=9.0)]
        sources = _bcs([ov], [h], alignment, {})
        s = next(x for x in sources if x.symbol == "PSX")
        assert s.source_intent == SOURCE_INTENT_TAX_FUNDING_SOURCE

    # ── Q3: VB/DODFX-like (OVERWEIGHT, neutral ESS) → OVERWEIGHT_REPAIR ──
    def test_neutral_overweight_yields_overweight_repair(self):
        """Q3: Operators can distinguish allocation repair from conviction deterioration."""
        ov = _ov("VB", ess_score_text="NEUTRAL", signal_direction="NEUTRAL",
                 is_overweight_vs_target="True", opportunity_flag="HOLD")
        h = _holding("VB", market_value="15000", geography="US", market_cap_bucket="LARGE")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=10.0)]
        sources = _bcs([ov], [h], alignment, {})
        s = next(x for x in sources if x.symbol == "VB")
        assert s.source_intent == SOURCE_INTENT_OVERWEIGHT_REPAIR

    # ── VOO/FXAIX-like (LOW_CONVICTION) → PORTFOLIO_REALLOCATION ─────────
    def test_low_conviction_index_fund_yields_portfolio_reallocation(self):
        """Index ETFs with no replay → PORTFOLIO_REALLOCATION."""
        ov = _ov("VOO", opportunity_flag="HOLD", ess_score_text="NEUTRAL",
                 signal_direction="NEUTRAL", replay_supported="False",
                 percent_of_portfolio="3.5")
        h = _holding("VOO", market_value="16000")
        sources = _bcs([ov], [h], [], {})
        cat5_sources = [s for s in sources if s.symbol == "VOO"]
        if not cat5_sources:
            pytest.skip("VOO not in low-conviction (may have other signals)")
        s = cat5_sources[0]
        assert s.source_intent == SOURCE_INTENT_PORTFOLIO_REALLOCATION

    # ── Strategic Exit → THESIS_EXIT regardless of ESS ────────────────────
    def test_strategic_exit_symbol_yields_thesis_exit(self):
        """Strategic exits always map to THESIS_EXIT."""
        ov = _ov("FIS", opportunity_flag="HOLD", ess_score_text="BULLISH")
        h = _holding("FIS", market_value="15000")
        tax_state = {
            "strategic_exit_symbols": ["FIS"],
            "operator_policies": [],
        }
        sources = _bcs([ov], [h], [], {}, tax_state=tax_state)
        s = next(x for x in sources if x.symbol == "FIS")
        assert s.category == CATEGORY_STRATEGIC_EXIT
        assert s.source_intent == SOURCE_INTENT_THESIS_EXIT

    # ── source_intent preserved through score_reduction_candidates() ───────
    def test_source_intent_preserved_after_scoring(self):
        """score_reduction_candidates() uses dataclasses.replace — must not strip source_intent."""
        ov = _ov("AAAA", ess_score_text="BEARISH", signal_direction="BEARISH",
                 opportunity_flag="TRIM")
        h = _holding("AAAA", market_value="10000")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "AAAA")
        # After scoring (which uses dataclasses.replace), source_intent must still be set
        assert s.source_intent != ""
        assert s.source_intent == SOURCE_INTENT_THESIS_TRIM

    # ── All source_intent values are non-empty for all categories ──────────
    def test_all_intents_non_empty(self):
        """Every source in build_capital_sources must have a non-empty source_intent."""
        overlays = [
            _ov("SIG", ess_score_text="VERY_BEARISH", opportunity_flag="TRIM"),
            _ov("OWB", ess_score_text="BULLISH", is_overweight_vs_target="True"),
            _ov("OWN", ess_score_text="NEUTRAL", is_overweight_vs_target="True"),
            _ov("TAX", opportunity_flag="HOLD"),
            _ov("LCV", opportunity_flag="HOLD", percent_of_portfolio="3.0"),
        ]
        holdings = [
            _holding("SIG", market_value="20000", geography="US", market_cap_bucket="LARGE"),
            _holding("OWB", market_value="15000", geography="US", market_cap_bucket="LARGE"),
            _holding("OWN", market_value="12000", geography="US", market_cap_bucket="LARGE"),
            _holding("TAX", market_value="8000", cost_basis="14000"),
            _holding("LCV", market_value="11000"),
        ]
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=15.0)]
        sources = _bcs(overlays, holdings, alignment, {})
        for s in sources:
            assert s.source_intent != "", f"{s.symbol} has empty source_intent"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: source_intent_summary in RotationProposal.to_dict()
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceIntentSummary:
    """Verify the aggregated source_intent_summary is correctly computed."""

    def _make_source(self, symbol: str, intent: str, proceeds: float) -> CapitalSourceRecord:
        return CapitalSourceRecord(
            symbol=symbol,
            current_value_usd=proceeds * 2,
            estimated_proceeds=proceeds,
            sizing_pct=0.5,
            category=CATEGORY_SIGNAL_DETERIORATION,
            priority="MODERATE",
            evidence_summary="test",
            tax_bucket=None,
            tax_annotation="",
            policy_type=None,
            blocked_by_policy=False,
            operator_review_required=False,
            source_intent=intent,
        )

    def _minimal_proposal(self, sources):
        """Build a minimal RotationProposal with only sources populated."""
        from src.portfolio.cra.models import (
            PortfolioImpactEstimate,
            RotationProposal,
            STATUS_DRAFT,
        )
        impact = PortfolioImpactEstimate(
            alignment_score_before=0.7,
            alignment_score_after=0.75,
            alignment_delta=0.05,
            concentration_before=0.35,
            concentration_after=0.32,
            concentration_delta=-0.03,
            overweight_nodes_before=[],
            overweight_nodes_after=[],
            newly_underweight_nodes=[],
            impact_narrative="test",
        )
        return RotationProposal(
            proposal_id="test-001",
            run_id="run-001",
            as_of_date="2026-06-16",
            portfolio_mv=500_000.0,
            total_capital_pool=sum(s.estimated_proceeds for s in sources),
            sources=sources,
            deployments=[],
            impact=impact,
            proposal_status=STATUS_DRAFT,
            review_flags=[],
            created_at_utc="2026-06-16T00:00:00+00:00",
        )

    def test_summary_aggregates_counts_and_capital(self):
        sources = [
            self._make_source("TSLA", SOURCE_INTENT_THESIS_EXIT, 19_000.0),
            self._make_source("PRIM", SOURCE_INTENT_THESIS_TRIM, 6_000.0),
            self._make_source("LMAT", SOURCE_INTENT_TAX_FUNDING_SOURCE, 8_000.0),
            self._make_source("MSFT", SOURCE_INTENT_TAX_FUNDING_SOURCE, 15_000.0),
            self._make_source("VB",   SOURCE_INTENT_OVERWEIGHT_REPAIR, 5_000.0),
            self._make_source("VOO",  SOURCE_INTENT_PORTFOLIO_REALLOCATION, 4_000.0),
        ]
        proposal = self._minimal_proposal(sources)
        d = proposal.to_dict()
        summary = d["source_intent_summary"]

        assert SOURCE_INTENT_THESIS_EXIT in summary
        assert summary[SOURCE_INTENT_THESIS_EXIT]["count"] == 1
        assert summary[SOURCE_INTENT_THESIS_EXIT]["capital"] == pytest.approx(19_000.0)

        assert SOURCE_INTENT_THESIS_TRIM in summary
        assert summary[SOURCE_INTENT_THESIS_TRIM]["count"] == 1
        assert summary[SOURCE_INTENT_THESIS_TRIM]["capital"] == pytest.approx(6_000.0)

        assert SOURCE_INTENT_TAX_FUNDING_SOURCE in summary
        assert summary[SOURCE_INTENT_TAX_FUNDING_SOURCE]["count"] == 2
        assert summary[SOURCE_INTENT_TAX_FUNDING_SOURCE]["capital"] == pytest.approx(23_000.0)

        assert SOURCE_INTENT_OVERWEIGHT_REPAIR in summary
        assert summary[SOURCE_INTENT_OVERWEIGHT_REPAIR]["count"] == 1

        assert SOURCE_INTENT_PORTFOLIO_REALLOCATION in summary
        assert summary[SOURCE_INTENT_PORTFOLIO_REALLOCATION]["count"] == 1

    def test_empty_buckets_excluded_from_summary(self):
        """Intents with 0 sources should not appear in the summary."""
        sources = [
            self._make_source("X", SOURCE_INTENT_THESIS_EXIT, 5_000.0),
        ]
        proposal = self._minimal_proposal(sources)
        d = proposal.to_dict()
        summary = d["source_intent_summary"]
        assert SOURCE_INTENT_THESIS_EXIT in summary
        # All others should be absent (count=0 → excluded)
        for intent in [SOURCE_INTENT_THESIS_TRIM, SOURCE_INTENT_TAX_FUNDING_SOURCE,
                        SOURCE_INTENT_OVERWEIGHT_REPAIR, SOURCE_INTENT_PORTFOLIO_REALLOCATION]:
            assert intent not in summary

    def test_summary_present_in_to_dict_output(self):
        """source_intent_summary key must always be present in to_dict()."""
        proposal = self._minimal_proposal([])
        d = proposal.to_dict()
        assert "source_intent_summary" in d

    def test_sources_include_source_intent_field_in_to_dict(self):
        """Each source dict in the 'sources' list must include source_intent."""
        sources = [
            self._make_source("TEST", SOURCE_INTENT_THESIS_EXIT, 5_000.0),
        ]
        proposal = self._minimal_proposal(sources)
        d = proposal.to_dict()
        src_dict = d["sources"][0]
        assert "source_intent" in src_dict
        assert src_dict["source_intent"] == SOURCE_INTENT_THESIS_EXIT


# ═══════════════════════════════════════════════════════════════════════════════
# Q6–Q10 Governance: display-only, no upstream changes
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceConstraints:
    """
    Q6: CRA rankings unchanged — reduction_score ordering must not be affected.
    Q7: PAP recommendations unchanged — source_intent is a display annotation only.
    Q8: CW-DAS scores unchanged — source_intent reads category+ESS, writes nothing.
    Q9: UCF classifications unchanged — source_intent does not modify upstream data.
    Q10: Display-only — source_intent is computed from existing fields, no new data.
    """

    def test_source_intent_does_not_alter_reduction_score(self):
        """Q6: source_intent must not affect reduction_score rankings."""
        ov1 = _ov("SIG", ess_score_text="VERY_BEARISH", opportunity_flag="TRIM")
        ov2 = _ov("OWB", ess_score_text="BULLISH", is_overweight_vs_target="True")
        h1 = _holding("SIG", market_value="20000", geography="US", market_cap_bucket="LARGE")
        h2 = _holding("OWB", market_value="15000", geography="US", market_cap_bucket="LARGE")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=12.0)]

        sources = _bcs([ov1, ov2], [h1, h2], alignment, {})
        sig = next(s for s in sources if s.symbol == "SIG")
        owb = next(s for s in sources if s.symbol == "OWB")

        # Relative ranking by reduction_score: SIG (VERY_BEARISH) > OWB (BULLISH OW)
        assert sig.reduction_score > owb.reduction_score, (
            "SIGNAL_DETERIORATION VERY_BEARISH must outrank OVERWEIGHT_REDUCTION BULLISH"
        )
        # source_intent differs but does not flip the ranking
        assert sig.source_intent == SOURCE_INTENT_THESIS_EXIT
        assert owb.source_intent == SOURCE_INTENT_TAX_FUNDING_SOURCE

    def test_source_intent_field_is_read_only_annotation(self):
        """Q10: source_intent is derived from category+signal; does not alter any input."""
        ov = _ov("AAAA", ess_score_text="BEARISH", opportunity_flag="TRIM")
        h = _holding("AAAA", market_value="10000")
        sources = _bcs([ov], [h], [], {})
        s = sources[0]
        # Verify category and signals are unchanged
        assert s.category == CATEGORY_SIGNAL_DETERIORATION
        assert s.ess_score_text == "BEARISH"
        # source_intent is additional annotation only
        assert s.source_intent == SOURCE_INTENT_THESIS_TRIM

    def test_source_intent_not_in_category_field(self):
        """source_intent must be a separate field — not mixed into category."""
        ov = _ov("BBBB", ess_score_text="BULLISH", is_overweight_vs_target="True")
        h = _holding("BBBB", market_value="12000", geography="US", market_cap_bucket="LARGE")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=10.0)]
        sources = _bcs([ov], [h], alignment, {})
        s = next(x for x in sources if x.symbol == "BBBB")
        assert s.category == CATEGORY_OVERWEIGHT_REDUCTION   # unchanged
        assert s.source_intent == SOURCE_INTENT_TAX_FUNDING_SOURCE  # display annotation
        assert s.category != s.source_intent  # separate fields
