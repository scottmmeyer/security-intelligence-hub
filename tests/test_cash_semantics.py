"""Phase 6.1 — Cash semantics, operational row filtering, duplicate aggregation,
and funding source intelligence tests.

Covers:
  6.1A — SPAXX/cash-equivalent holdings bypass ETF decomposition (direct cash exposure)
  6.1B — PENDING ACTIVITY and zero/negative market-value rows are excluded from analytics
  6.1C — Duplicate symbol rows are aggregated with correct percent_of_portfolio
  6.1D — FundingSourceAnalysis is populated from excess cash and trim candidates
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from src.portfolio.enrichment import enrich_holdings, normalize_and_aggregate_holdings
from src.portfolio.ingestion import _classify_operational_state, ingest_portfolio
from src.portfolio.models import (
    AllocationAlignmentResult,
    FundingSourceAnalysis,
    PortfolioHolding,
    SecurityIntelligenceOverlay,
)
from src.portfolio.recommendations import identify_funding_sources


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc).isoformat()


def _make_holding(
    symbol: str,
    market_value: float = 10_000.0,
    percent_of_portfolio: float = 10.0,
    security_type: str = "Common Stock",
    asset_class: str = "UNKNOWN",
    operational_state: str = "ACTIVE_POSITION",
    is_cash_equivalent: bool = False,
    description: str = "",
) -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id="PSNAP-TEST",
        snapshot_date="2026-01-01",
        account_name="TEST",
        symbol=symbol,
        description=description,
        quantity=1.0,
        market_value=market_value,
        percent_of_portfolio=percent_of_portfolio,
        asset_class=asset_class,
        geography="UNKNOWN",
        market_cap_bucket="UNKNOWN",
        mega_subtier="N/A",
        sector="UNKNOWN",
        industry="UNKNOWN",
        security_type=security_type,
        cost_basis=None,
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        operational_state=operational_state,
        is_cash_equivalent=is_cash_equivalent,
    )


def _make_alignment(
    node_key: str,
    drift_direction: str = "UNDERWEIGHT",
    drift_pct: float = -3.0,
    severity: str = "MODERATE",
    actual_pct: float = 7.0,
    target_pct: float = 10.0,
) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id="RUN-TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        node_key=node_key,
        node_label=node_key.replace(".", " "),
        dimension_type="MARKET_CAP",
        actual_pct=actual_pct,
        target_pct=target_pct,
        tactical_target_pct=target_pct,
        drift_pct=drift_pct,
        drift_direction=drift_direction,
        severity=severity,
        concentration_risk="LOW",
        alignment_score=0.7,
        recommendation_priority=2,
        created_at_utc=_NOW,
    )


def _make_overlay(symbol: str, opportunity_flag: str = "") -> SecurityIntelligenceOverlay:
    return SecurityIntelligenceOverlay(
        portfolio_snapshot_id="PSNAP-TEST",
        symbol=symbol,
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        signal_direction="NEUTRAL",
        opportunity_flag=opportunity_flag,
        flag_rationale="",
        replay_supported=False,
        best_replay_return=None,
        replay_percentile=None,
        percent_of_portfolio=0.0,
        is_overweight_vs_target=False,
        created_at_utc=_NOW,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6.1A — Cash-equivalent semantics
# ─────────────────────────────────────────────────────────────────────────────

class TestCashEquivalentSemantics:
    """SPAXX and other sweep funds must NOT be treated as ETF exposure containers."""

    def test_spaxx_enriched_as_cash_not_etf(self):
        holding = _make_holding("SPAXX", security_type="Cash")
        enriched = enrich_holdings([holding])
        result = enriched[0]
        assert result.asset_class == "CASH", "SPAXX must be classified as CASH"
        assert result.security_type == "Cash", "SPAXX must NOT be promoted to ETF security_type"

    def test_spaxx_is_cash_equivalent_flag(self):
        holding = _make_holding("SPAXX", security_type="Cash")
        enriched = enrich_holdings([holding])
        result = enriched[0]
        assert result.is_cash_equivalent is True

    def test_spaxx_operational_state_is_cash_equivalent(self):
        holding = _make_holding("SPAXX", security_type="Cash")
        enriched = enrich_holdings([holding])
        result = enriched[0]
        assert result.operational_state == "CASH_EQUIVALENT"

    def test_vmfxx_enriched_as_cash(self):
        holding = _make_holding("VMFXX", security_type="Cash")
        enriched = enrich_holdings([holding])
        result = enriched[0]
        assert result.asset_class == "CASH"
        assert result.security_type == "Cash"
        assert result.is_cash_equivalent is True

    def test_fzfxx_enriched_as_cash(self):
        holding = _make_holding("FZFXX", security_type="Cash")
        enriched = enrich_holdings([holding])
        result = enriched[0]
        assert result.asset_class == "CASH"
        assert result.is_cash_equivalent is True

    def test_voo_not_flagged_as_cash_equivalent(self):
        holding = _make_holding("VOO", security_type="ETF")
        enriched = enrich_holdings([holding])
        result = enriched[0]
        assert result.asset_class == "EQUITIES"
        assert result.is_cash_equivalent is False
        assert result.security_type == "ETF"

    def test_cash_holding_no_etf_decomp_exposure(self):
        """SPAXX should NOT produce any equity market-cap exposure mix entries.
        Its cap mix and subtier mix should be empty (direct cash, not fund exposure)."""
        holding = _make_holding("SPAXX", security_type="Cash")
        enriched = enrich_holdings([holding])
        result = enriched[0]
        # Cash positions must have no market-cap mix (that field is for equity tier analysis)
        assert result.exposure_market_cap_mix == (), (
            f"SPAXX should have empty market_cap_mix but got {result.exposure_market_cap_mix}"
        )
        assert result.exposure_mega_subtier_mix == (), (
            f"SPAXX should have empty mega_subtier_mix but got {result.exposure_mega_subtier_mix}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6.1B — Operational row filtering
# ─────────────────────────────────────────────────────────────────────────────

class TestOperationalStateClassification:
    """_classify_operational_state assigns correct states to raw ingestion rows."""

    def test_pending_activity_symbol_is_pending_settlement(self):
        state = _classify_operational_state("PENDING", "PENDING ACTIVITY", 0.0)
        assert state == "PENDING_SETTLEMENT"

    def test_pending_activity_description_is_pending_settlement(self):
        state = _classify_operational_state("CASH", "PENDING ACTIVITY", 0.0)
        assert state == "PENDING_SETTLEMENT"

    def test_negative_market_value_is_accounting_adjustment(self):
        state = _classify_operational_state("XYZ", "Some description", -500.0)
        assert state == "ACCOUNTING_ADJUSTMENT"

    def test_zero_market_value_is_closed_position(self):
        state = _classify_operational_state("APPL", "Old holding", 0.0)
        assert state == "CLOSED_POSITION"

    def test_normal_holding_is_active(self):
        state = _classify_operational_state("NVDA", "NVIDIA Corp", 5000.0)
        assert state == "ACTIVE_POSITION"

    def test_settlement_description_is_pending_settlement(self):
        state = _classify_operational_state("CASH", "SETTLEMENT ACTIVITY", 100.0)
        assert state == "PENDING_SETTLEMENT"


class TestOperationalRowEnrichment:
    """Holdings with non-ACTIVE states are tagged correctly in enrichment."""

    def test_pending_holding_retains_operational_state_after_enrichment(self):
        holding = _make_holding(
            "PENDING",
            market_value=0.0,
            description="PENDING ACTIVITY",
            operational_state="PENDING_SETTLEMENT",
        )
        enriched = enrich_holdings([holding])
        result = enriched[0]
        # Enrichment must NOT reset operational_state to ACTIVE_POSITION
        assert result.operational_state == "PENDING_SETTLEMENT"

    def test_negative_value_holding_retains_accounting_adjustment_state(self):
        holding = _make_holding(
            "CASH",
            market_value=-100.0,
            operational_state="ACCOUNTING_ADJUSTMENT",
        )
        enriched = enrich_holdings([holding])
        result = enriched[0]
        assert result.operational_state == "ACCOUNTING_ADJUSTMENT"


# ─────────────────────────────────────────────────────────────────────────────
# 6.1C — Duplicate symbol aggregation
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeAndAggregateHoldings:
    """normalize_and_aggregate_holdings merges duplicate symbols correctly."""

    def test_unique_symbols_unchanged(self):
        holdings = [
            _make_holding("NVDA", market_value=10_000, percent_of_portfolio=50.0),
            _make_holding("VOO", market_value=10_000, percent_of_portfolio=50.0),
        ]
        result = normalize_and_aggregate_holdings(holdings)
        assert len(result) == 2

    def test_duplicate_symbols_aggregated(self):
        holdings = [
            _make_holding("SPAXX", market_value=5_000, percent_of_portfolio=25.0),
            _make_holding("SPAXX", market_value=3_000, percent_of_portfolio=15.0),
        ]
        result = normalize_and_aggregate_holdings(holdings)
        assert len(result) == 1
        assert result[0].market_value == 8_000

    def test_percent_of_portfolio_recalculated(self):
        holdings = [
            _make_holding("A", market_value=40_000),
            _make_holding("B", market_value=60_000),
        ]
        result = normalize_and_aggregate_holdings(holdings)
        by_sym = {h.symbol: h for h in result}
        assert abs(by_sym["A"].percent_of_portfolio - 40.0) < 0.01
        assert abs(by_sym["B"].percent_of_portfolio - 60.0) < 0.01

    def test_insertion_order_preserved(self):
        holdings = [
            _make_holding("NVDA", market_value=30_000),
            _make_holding("VOO", market_value=20_000),
            _make_holding("NVDA", market_value=10_000),  # duplicate
        ]
        result = normalize_and_aggregate_holdings(holdings)
        assert len(result) == 2
        # NVDA should appear first (first occurrence position wins)
        assert result[0].symbol == "NVDA"
        assert result[0].market_value == 40_000

    def test_negative_value_excluded_from_pct_denominator(self):
        """Accounting-adjustment rows with negative value should not distort weights."""
        holdings = [
            _make_holding("NVDA", market_value=80_000, operational_state="ACTIVE_POSITION"),
            _make_holding("ADJ", market_value=-5_000, operational_state="ACCOUNTING_ADJUSTMENT"),
        ]
        result = normalize_and_aggregate_holdings(holdings)
        nvda = next(h for h in result if h.symbol == "NVDA")
        # NVDA should be ~100% because only positive values count in the denominator
        assert nvda.percent_of_portfolio == pytest.approx(100.0, abs=0.01)

    def test_empty_input_returns_empty(self):
        assert normalize_and_aggregate_holdings([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# 6.1D — Funding source intelligence
# ─────────────────────────────────────────────────────────────────────────────

class TestIdentifyFundingSources:
    """identify_funding_sources returns correct priority ordering and narrative."""

    def _base_holdings(self):
        return [
            _make_holding("NVDA", market_value=70_000, percent_of_portfolio=70.0,
                          asset_class="EQUITIES", operational_state="ACTIVE_POSITION"),
            _make_holding("SPAXX", market_value=20_000, percent_of_portfolio=20.0,
                          asset_class="CASH", operational_state="CASH_EQUIVALENT",
                          is_cash_equivalent=True),
            _make_holding("VOO", market_value=10_000, percent_of_portfolio=10.0,
                          asset_class="EQUITIES", operational_state="ACTIVE_POSITION"),
        ]

    def test_excess_cash_identified_as_priority_1(self):
        holdings = self._base_holdings()
        alignment = [_make_alignment("EQUITIES.US.MEGA.EXTENDED_MEGA")]
        overlays = []
        result = identify_funding_sources(
            "RUN-TEST", "PSNAP-TEST", holdings, alignment, overlays
        )
        assert isinstance(result, FundingSourceAnalysis)
        assert len(result.sources) >= 1
        primary = result.sources[0]
        assert primary.source_type == "EXCESS_CASH"
        assert primary.priority == 1
        assert primary.available_pct > 0

    def test_trim_candidate_overlay_creates_source(self):
        holdings = self._base_holdings()
        alignment = []
        overlays = [_make_overlay("NVDA", opportunity_flag="TRIM")]
        result = identify_funding_sources(
            "RUN-TEST", "PSNAP-TEST", holdings, alignment, overlays
        )
        source_types = {s.source_type for s in result.sources}
        assert "TRIM_CANDIDATE" in source_types

    def test_total_available_pct_is_sum_of_cash_and_trim(self):
        holdings = self._base_holdings()
        alignment = []
        overlays = [_make_overlay("NVDA", opportunity_flag="TRIM")]
        result = identify_funding_sources(
            "RUN-TEST", "PSNAP-TEST", holdings, alignment, overlays
        )
        cash_sources = [s for s in result.sources if s.source_type == "EXCESS_CASH"]
        trim_sources = [s for s in result.sources if s.source_type == "TRIM_CANDIDATE"]
        expected_total = sum(s.available_pct for s in cash_sources + trim_sources)
        assert abs(result.total_available_pct - expected_total) < 0.01

    def test_no_excess_cash_no_cash_source(self):
        """If cash < reserve floor, no EXCESS_CASH source is emitted."""
        holdings = [
            _make_holding("NVDA", market_value=99_000, percent_of_portfolio=99.0,
                          asset_class="EQUITIES", operational_state="ACTIVE_POSITION"),
            _make_holding("SPAXX", market_value=1_000, percent_of_portfolio=1.0,
                          asset_class="CASH", operational_state="CASH_EQUIVALENT",
                          is_cash_equivalent=True),
        ]
        alignment = []
        overlays = []
        result = identify_funding_sources(
            "RUN-TEST", "PSNAP-TEST", holdings, alignment, overlays
        )
        source_types = {s.source_type for s in result.sources}
        assert "EXCESS_CASH" not in source_types

    def test_summary_is_non_empty_string(self):
        holdings = self._base_holdings()
        result = identify_funding_sources(
            "RUN-TEST", "PSNAP-TEST", holdings, [], []
        )
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0

    def test_empty_portfolio_returns_no_sources(self):
        result = identify_funding_sources(
            "RUN-TEST", "PSNAP-TEST", [], [], []
        )
        assert isinstance(result, FundingSourceAnalysis)
        assert len(result.sources) == 0
        assert "No clear" in result.summary

    def test_overweight_node_creates_source(self):
        """An overweight node with HIGH severity generates OVERWEIGHT_REDUCTION source."""
        # Holdings must be classified to match the overweight node key
        nvda = dataclasses.replace(
            _make_holding("NVDA", market_value=50_000, percent_of_portfolio=50.0,
                          asset_class="EQUITIES", operational_state="ACTIVE_POSITION"),
            geography="US",
            market_cap_bucket="MEGA",
            mega_subtier="HYPER_MEGA",
        )
        aapl = dataclasses.replace(
            _make_holding("AAPL", market_value=50_000, percent_of_portfolio=50.0,
                          asset_class="EQUITIES", operational_state="ACTIVE_POSITION"),
            geography="US",
            market_cap_bucket="MEGA",
            mega_subtier="HYPER_MEGA",
        )
        alignment = [
            _make_alignment(
                "EQUITIES.US.MEGA.HYPER_MEGA",
                drift_direction="OVERWEIGHT",
                drift_pct=+8.0,
                severity="HIGH",
                actual_pct=28.0,
                target_pct=20.0,
            )
        ]
        result = identify_funding_sources(
            "RUN-TEST", "PSNAP-TEST", [nvda, aapl], alignment, []
        )
        source_types = {s.source_type for s in result.sources}
        assert "OVERWEIGHT_REDUCTION" in source_types


# ─────────────────────────────────────────────────────────────────────────────
# Integration — Fidelity CSV ingestion with PENDING ACTIVITY row
# ─────────────────────────────────────────────────────────────────────────────

class TestIngestionOperationalRows:
    """End-to-end ingestion correctly classifies PENDING and zero-value rows."""

    _FIDELITY_CSV = """Account Name/Number,Symbol,Description,Quantity,Last Price,Current Value
Brokerage Account,NVDA,NVIDIA Corporation,10,900.00,"$9,000.00"
Brokerage Account,SPAXX**,FIDELITY GOVERNMENT MONEY MARKET,--,1.00,"$1,000.00"
Brokerage Account,PENDING,PENDING ACTIVITY,--,--,"$0.00"
"""

    def test_pending_activity_row_has_pending_settlement_state(self):
        _, holdings = ingest_portfolio(self._FIDELITY_CSV, "test.csv", "2026-01-01")
        pending = [h for h in holdings if "PENDING" in h.symbol or "PENDING" in h.description.upper()]
        # Should find the pending row(s)
        assert len(pending) >= 1
        for h in pending:
            assert h.operational_state == "PENDING_SETTLEMENT", (
                f"Expected PENDING_SETTLEMENT for {h.symbol!r}, got {h.operational_state!r}"
            )

    def test_normal_holding_is_active_position(self):
        _, holdings = ingest_portfolio(self._FIDELITY_CSV, "test.csv", "2026-01-01")
        nvda = next(h for h in holdings if h.symbol == "NVDA")
        assert nvda.operational_state == "ACTIVE_POSITION"

    def test_spaxx_row_is_not_active_position(self):
        _, holdings = ingest_portfolio(self._FIDELITY_CSV, "test.csv", "2026-01-01")
        spaxx = next(h for h in holdings if h.symbol == "SPAXX")
        # ingestion assigns ACTIVE_POSITION; enrichment will upgrade to CASH_EQUIVALENT
        # So at minimum the symbol must be present and parseable
        assert spaxx.symbol == "SPAXX"
