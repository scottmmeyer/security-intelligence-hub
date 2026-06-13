"""Canonical PIS Phase 1 snapshot models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Immutable portfolio snapshot for a single Fidelity account."""

    snapshot_id: str
    snapshot_date: date
    account_id: str
    account_name: str
    source_file: str
    source_format: str
    portfolio_value: float
    cash_value: float
    equity_value: float
    holding_count: int
    ingestion_status: str
    created_at_utc: datetime
    source_run_id: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PositionSnapshot:
    """Immutable portfolio position row tied to a portfolio snapshot."""

    snapshot_id: str
    snapshot_date: date
    account_id: str
    account_name: str
    symbol: str
    description: str
    quantity: float
    market_value: float
    percent_of_account: float
    source_percent_of_account: Optional[float]
    cost_basis_total: Optional[float]
    security_type: str
    operational_state: str
    is_cash_equivalent: bool
    source_file: str
    created_at_utc: datetime
