"""PIS snapshot registration from canonical SIH portfolio objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from datetime import date

from src.portfolio.models import PortfolioHolding as SIHPortfolioHolding
from src.portfolio.models import PortfolioSnapshot as SIHPortfolioSnapshot

from .models import PortfolioSnapshot, PositionSnapshot
from .storage import append_portfolio_history, summarize_portfolio_history


# ---------------------------------------------------------------------------
# Investable-state filter (single source of truth for PIS)
# ---------------------------------------------------------------------------
# Holdings that are not in this set must never generate change-detection records,
# lineage matches, or attribution entries.  Applying the filter here ensures that
# PIS snapshot history is consistent with the portfolio analytics layer, which
# already excludes these states before computing recommendations.
_PIS_INVESTABLE_STATES: frozenset[str] = frozenset({
    "ACTIVE_POSITION",
    "CASH_EQUIVALENT",
})


@dataclass(frozen=True)
class PortfolioRegistrationResult:
    snapshot_id: str
    registered: bool
    duplicate: bool
    position_count: int
    warning: str = ""


def _to_pis_snapshot(snapshot: SIHPortfolioSnapshot) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        snapshot_id=snapshot.portfolio_snapshot_id,
        snapshot_date=date.fromisoformat(snapshot.snapshot_date),
        account_id="PORTFOLIO",
        account_name=snapshot.account_name,
        source_file=snapshot.source_file,
        source_format=snapshot.source_format,
        portfolio_value=snapshot.total_market_value,
        cash_value=0.0,
        equity_value=snapshot.total_market_value,
        holding_count=snapshot.holding_count,
        ingestion_status=snapshot.ingestion_status,
        created_at_utc=datetime.fromisoformat(snapshot.created_at_utc),
        source_run_id=snapshot.run_id,
        warnings=tuple(snapshot.normalization_warnings),
    )


def _to_pis_positions(
    snapshot: SIHPortfolioSnapshot,
    holdings: Iterable[SIHPortfolioHolding],
) -> list[PositionSnapshot]:
    created_at_utc = datetime.fromisoformat(snapshot.created_at_utc)
    snapshot_date = date.fromisoformat(snapshot.snapshot_date)
    positions: list[PositionSnapshot] = []
    for holding in holdings:
        positions.append(
            PositionSnapshot(
                snapshot_id=snapshot.portfolio_snapshot_id,
                snapshot_date=snapshot_date,
                account_id="PORTFOLIO",
                account_name=snapshot.account_name,
                symbol=holding.symbol,
                description=holding.description,
                quantity=holding.quantity,
                market_value=holding.market_value,
                percent_of_account=holding.percent_of_portfolio,
                source_percent_of_account=holding.percent_of_portfolio,
                cost_basis_total=holding.cost_basis,
                security_type=holding.security_type,
                operational_state=holding.operational_state,
                is_cash_equivalent=holding.is_cash_equivalent,
                source_file=holding.source_file,
                created_at_utc=created_at_utc,
            )
        )
    return positions


def register_portfolio_snapshot_from_sih(
    *,
    snapshot: SIHPortfolioSnapshot,
    holdings: Iterable[SIHPortfolioHolding],
    history_root: str = "data/history/pis",
    index_path: str = "data/history/pis/pis_snapshot_index.csv",
) -> PortfolioRegistrationResult:
    """Register a canonical SIH portfolio snapshot with PIS.

    The function is intentionally best-effort for callers that require failure
    isolation: duplicate snapshots are treated as no-ops and other exceptions
    are surfaced to the caller.
    """

    if str(snapshot.ingestion_status).upper() == "REJECTED":
        return PortfolioRegistrationResult(
            snapshot_id=snapshot.portfolio_snapshot_id,
            registered=False,
            duplicate=False,
            position_count=0,
            warning="Skipped because SIH snapshot was rejected.",
        )

    pis_snapshot = _to_pis_snapshot(snapshot)
    # PIS-INTEGRITY-01: filter to investable states only before persisting positions.
    # This excludes PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, ZERO_VALUE_LEGACY_POSITION
    # and any future non-investable states, mirroring the filter applied by portfolio
    # analytics before computing recommendations.
    investable_holdings = [
        h for h in holdings
        if str(getattr(h, "operational_state", "ACTIVE_POSITION") or "ACTIVE_POSITION")
        in _PIS_INVESTABLE_STATES
    ]
    pis_positions = _to_pis_positions(snapshot, investable_holdings)
    pis_snapshot = PortfolioSnapshot(
        snapshot_id=pis_snapshot.snapshot_id,
        snapshot_date=pis_snapshot.snapshot_date,
        account_id=pis_snapshot.account_id,
        account_name=pis_snapshot.account_name,
        source_file=pis_snapshot.source_file,
        source_format=pis_snapshot.source_format,
        portfolio_value=pis_snapshot.portfolio_value,
        cash_value=sum(position.market_value for position in pis_positions if position.is_cash_equivalent),
        equity_value=max(0.0, pis_snapshot.portfolio_value - sum(position.market_value for position in pis_positions if position.is_cash_equivalent)),
        holding_count=pis_snapshot.holding_count,
        ingestion_status=pis_snapshot.ingestion_status,
        created_at_utc=pis_snapshot.created_at_utc,
        source_run_id=pis_snapshot.source_run_id,
        warnings=pis_snapshot.warnings,
    )

    summary_before = summarize_portfolio_history(index_path=index_path)
    already_registered = pis_snapshot.snapshot_id in set(summary_before.get("snapshot_ids", []))

    if already_registered:
        return PortfolioRegistrationResult(
            snapshot_id=pis_snapshot.snapshot_id,
            registered=False,
            duplicate=True,
            position_count=len(pis_positions),
            warning="Duplicate PIS snapshot suppressed.",
        )

    written = append_portfolio_history(
        snapshot=pis_snapshot,
        positions=pis_positions,
        history_root=history_root,
        index_path=index_path,
    )
    return PortfolioRegistrationResult(
        snapshot_id=pis_snapshot.snapshot_id,
        registered=True,
        duplicate=False,
        position_count=written,
    )
