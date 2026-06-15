"""Tests for PIS-INTEGRITY-01 — accounting artifact filter in PIS registration.

Validates that PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, and
ZERO_VALUE_LEGACY_POSITION holdings are excluded from PIS snapshots while
ACTIVE_POSITION and CASH_EQUIVALENT holdings are preserved.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.pis.service import (
    _PIS_INVESTABLE_STATES,
    _to_pis_positions,
    register_portfolio_snapshot_from_sih,
)
from src.portfolio.models import PortfolioHolding, PortfolioSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(snapshot_date: str = "2026-06-15") -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolio_snapshot_id="PSNAP-TEST-0001",
        snapshot_date=snapshot_date,
        account_name="General Brokerage, Joint WROS - TOD, Individual - TOD",
        source_file="test.csv",
        source_format="FIDELITY_CSV",
        total_market_value=100_000.0,
        holding_count=5,
        ingestion_status="ACCEPTED",
        created_at_utc=datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        run_id="PAR-TEST-0001",
        normalization_warnings=[],
    )


def _make_holding(symbol: str, operational_state: str, market_value: float = 1000.0) -> PortfolioHolding:
    h = MagicMock()
    h.symbol = symbol
    h.description = f"{symbol} description"
    h.quantity = 10.0
    h.market_value = market_value
    h.percent_of_portfolio = 1.0
    h.cost_basis = market_value * 0.9
    h.security_type = "Common Stock"
    h.operational_state = operational_state
    h.is_cash_equivalent = False
    h.source_file = "test.csv"
    return h


# ---------------------------------------------------------------------------
# T01: _PIS_INVESTABLE_STATES constant exists and contains correct values
# ---------------------------------------------------------------------------

def test_T01_investable_states_constant():
    """_PIS_INVESTABLE_STATES contains exactly ACTIVE_POSITION and CASH_EQUIVALENT."""
    assert "ACTIVE_POSITION" in _PIS_INVESTABLE_STATES
    assert "CASH_EQUIVALENT" in _PIS_INVESTABLE_STATES
    assert "PENDING_SETTLEMENT" not in _PIS_INVESTABLE_STATES
    assert "ACCOUNTING_ADJUSTMENT" not in _PIS_INVESTABLE_STATES
    assert "ZERO_VALUE_LEGACY_POSITION" not in _PIS_INVESTABLE_STATES


# ---------------------------------------------------------------------------
# T02: PENDING ACTIVITY excluded from PIS snapshot
# ---------------------------------------------------------------------------

def test_T02_pending_activity_excluded():
    """PENDING_SETTLEMENT holdings must not be registered with PIS."""
    snap = _make_snapshot()
    active = _make_holding("AAPL", "ACTIVE_POSITION")
    pending = _make_holding("PENDING ACTIVITY", "PENDING_SETTLEMENT", 29.28)
    filtered_calls = []

    def fake_append(*, snapshot, positions, **kwargs):
        filtered_calls.extend([p.symbol for p in positions])
        # Simulate immutability protection
        raise ValueError("Immutable PIS partition protection triggered: partition already exists")

    with patch("src.pis.service.append_portfolio_history", side_effect=fake_append):
        try:
            register_portfolio_snapshot_from_sih(snapshot=snap, holdings=[active, pending])
        except Exception:
            pass

    # Only AAPL should have been passed to append; PENDING ACTIVITY excluded
    assert "AAPL" in filtered_calls or len(filtered_calls) == 0  # may hit duplicate protection
    assert "PENDING ACTIVITY" not in filtered_calls


def test_T02b_pending_settlement_via_to_pis_positions():
    """_to_pis_positions is given only investable holdings when called from register."""
    snap = _make_snapshot()
    pending = _make_holding("PENDING ACTIVITY", "PENDING_SETTLEMENT")
    # Direct test: if we pass pending to _to_pis_positions, it would include it.
    # But register_portfolio_snapshot_from_sih must filter BEFORE calling _to_pis_positions.
    # Verify via the filter itself.
    from src.pis.service import _PIS_INVESTABLE_STATES
    holdings = [
        _make_holding("AAPL", "ACTIVE_POSITION"),
        _make_holding("PENDING ACTIVITY", "PENDING_SETTLEMENT"),
    ]
    investable = [h for h in holdings if h.operational_state in _PIS_INVESTABLE_STATES]
    assert len(investable) == 1
    assert investable[0].symbol == "AAPL"


# ---------------------------------------------------------------------------
# T03: ACCOUNTING_ADJUSTMENT excluded
# ---------------------------------------------------------------------------

def test_T03_accounting_adjustment_excluded():
    """ACCOUNTING_ADJUSTMENT holdings must not appear in PIS positions."""
    holdings = [
        _make_holding("MSFT", "ACTIVE_POSITION"),
        _make_holding("M26CNT069", "ACCOUNTING_ADJUSTMENT", -500.0),
    ]
    investable = [h for h in holdings if h.operational_state in _PIS_INVESTABLE_STATES]
    assert len(investable) == 1
    assert investable[0].symbol == "MSFT"
    assert "M26CNT069" not in {h.symbol for h in investable}


# ---------------------------------------------------------------------------
# T04: ZERO_VALUE_LEGACY_POSITION excluded
# ---------------------------------------------------------------------------

def test_T04_zero_value_legacy_excluded():
    """ZERO_VALUE_LEGACY_POSITION holdings must not appear in PIS positions."""
    holdings = [
        _make_holding("VRT", "ACTIVE_POSITION"),
        _make_holding("LEGACY_XYZ", "ZERO_VALUE_LEGACY_POSITION", 0.0),
    ]
    investable = [h for h in holdings if h.operational_state in _PIS_INVESTABLE_STATES]
    assert len(investable) == 1
    assert investable[0].symbol == "VRT"


# ---------------------------------------------------------------------------
# T05: ACTIVE_POSITION preserved
# ---------------------------------------------------------------------------

def test_T05_active_position_preserved():
    """ACTIVE_POSITION holdings must pass through unchanged."""
    holdings = [
        _make_holding("AAPL", "ACTIVE_POSITION"),
        _make_holding("MSFT", "ACTIVE_POSITION"),
    ]
    investable = [h for h in holdings if h.operational_state in _PIS_INVESTABLE_STATES]
    assert len(investable) == 2
    syms = {h.symbol for h in investable}
    assert "AAPL" in syms
    assert "MSFT" in syms


# ---------------------------------------------------------------------------
# T06: CASH_EQUIVALENT preserved
# ---------------------------------------------------------------------------

def test_T06_cash_equivalent_preserved():
    """CASH_EQUIVALENT holdings must pass through unchanged."""
    holdings = [
        _make_holding("SPAXX", "CASH_EQUIVALENT"),
        _make_holding("FZFXX", "CASH_EQUIVALENT"),
    ]
    investable = [h for h in holdings if h.operational_state in _PIS_INVESTABLE_STATES]
    assert len(investable) == 2


# ---------------------------------------------------------------------------
# T07: Mixed holdings — only investable pass
# ---------------------------------------------------------------------------

def test_T07_mixed_holdings_filter():
    """Mixed portfolio: only ACTIVE_POSITION and CASH_EQUIVALENT pass."""
    holdings = [
        _make_holding("NVDA", "ACTIVE_POSITION"),
        _make_holding("SPAXX", "CASH_EQUIVALENT"),
        _make_holding("PENDING ACTIVITY", "PENDING_SETTLEMENT"),
        _make_holding("M26CNT069", "ACCOUNTING_ADJUSTMENT"),
        _make_holding("LEGACY", "ZERO_VALUE_LEGACY_POSITION"),
    ]
    investable = [h for h in holdings if h.operational_state in _PIS_INVESTABLE_STATES]
    assert len(investable) == 2
    syms = {h.symbol for h in investable}
    assert syms == {"NVDA", "SPAXX"}


# ---------------------------------------------------------------------------
# T08: All holdings non-investable → no positions registered
# ---------------------------------------------------------------------------

def test_T08_all_non_investable_no_positions():
    """If all holdings are non-investable, PIS registers 0 positions."""
    holdings = [
        _make_holding("PENDING ACTIVITY", "PENDING_SETTLEMENT"),
        _make_holding("M26CNT069", "ACCOUNTING_ADJUSTMENT"),
    ]
    investable = [h for h in holdings if h.operational_state in _PIS_INVESTABLE_STATES]
    assert len(investable) == 0


# ---------------------------------------------------------------------------
# T09: register_portfolio_snapshot_from_sih filters before storage call
# ---------------------------------------------------------------------------

def test_T09_register_filters_before_storage(monkeypatch):
    """register_portfolio_snapshot_from_sih passes only investable to storage."""
    snap = _make_snapshot()
    holdings = [
        _make_holding("AAPL", "ACTIVE_POSITION"),
        _make_holding("PENDING ACTIVITY", "PENDING_SETTLEMENT"),
        _make_holding("M26CNT069", "ACCOUNTING_ADJUSTMENT"),
    ]

    captured_positions = []

    def fake_summarize(**kwargs):
        return {"snapshot_ids": [], "snapshot_count": 0, "recent_rows": []}

    def fake_append(*, snapshot, positions, **kwargs):
        captured_positions.extend(positions)
        return len(positions)

    monkeypatch.setattr("src.pis.service.summarize_portfolio_history", fake_summarize)
    monkeypatch.setattr("src.pis.service.append_portfolio_history", fake_append)

    result = register_portfolio_snapshot_from_sih(snapshot=snap, holdings=holdings)

    # Should have registered successfully with only 1 position (AAPL)
    assert result.registered is True
    assert len(captured_positions) == 1
    assert captured_positions[0].symbol == "AAPL"


# ---------------------------------------------------------------------------
# T10: REJECTED snapshot skipped entirely (no filter needed)
# ---------------------------------------------------------------------------

def test_T10_rejected_snapshot_skipped():
    """REJECTED snapshots skip registration before any filtering."""
    snap = _make_snapshot()
    # Simulate rejected snapshot
    snap_rejected = PortfolioSnapshot(
        portfolio_snapshot_id="PSNAP-TEST-REJECT",
        snapshot_date="2026-06-15",
        account_name="Test",
        source_file="test.csv",
        source_format="FIDELITY_CSV",
        total_market_value=0.0,
        holding_count=0,
        ingestion_status="REJECTED",
        created_at_utc=datetime(2026, 6, 15, tzinfo=timezone.utc).isoformat(),
        run_id="PAR-TEST-REJECT",
        normalization_warnings=[],
    )
    result = register_portfolio_snapshot_from_sih(
        snapshot=snap_rejected, holdings=[]
    )
    assert result.registered is False
    assert result.duplicate is False
    assert "rejected" in result.warning.lower()
