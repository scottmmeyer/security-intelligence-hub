"""WP-05D stock historical replay curve foundation.

Provides coverage-aware computation of FULL_UNIVERSE and TOP_N_STRATEGY
cumulative return curves from individual equity price histories.

Design principles:
  - No-lookahead: universe membership is frozen at start_date.
  - No rebalancing: equal-weight basket held through end_date.
  - Fail-closed: if coverage < threshold, curve is not emitted.
  - No fabrication: missing symbols are reported, not filled.
  - Batch-first: multi-symbol price fetch preferred over per-symbol loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Sequence, Tuple

from src.models.analytical_models import AnalyticalUniverseRow, ReplaySelection
from src.replay.history_providers import (
    PricePoint,
    SecurityPriceHistoryProvider,
    ensure_chronological,
    equal_weighted_mean_series,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FULL_UNIVERSE_COVERAGE_THRESHOLD: float = 0.60
"""Minimum fraction of universe symbols that must have sufficient price history
for the FULL_UNIVERSE curve to be emitted."""

TOP_N_COVERAGE_THRESHOLD: float = 0.80
"""Minimum fraction of selected top-N symbols that must have sufficient price
history for the TOP_N_STRATEGY curve to be emitted."""

MAX_SYMBOLS_PER_CATEGORY: int = 500
"""Safety cap on universe size. Prevents runaway provider calls for unexpectedly
large analytical universes. Make configurable once category sizes are known."""

MINIMUM_CURVE_POINTS: int = 2
"""A symbol contributes to the mean only if it has at least this many price
observations in the replay window."""

# ---------------------------------------------------------------------------
# Coverage status vocabulary
# ---------------------------------------------------------------------------

STOCK_COVERAGE_STATUS_AVAILABLE = "AVAILABLE"
"""All requested symbols had sufficient price history."""

STOCK_COVERAGE_STATUS_PARTIAL = "PARTIAL"
"""Coverage fraction >= threshold but < 1.0; curve built from available subset."""

STOCK_COVERAGE_STATUS_MISSING_MARKET_DATA = "MISSING_MARKET_DATA"
"""No price data at all for any requested symbol."""

STOCK_COVERAGE_STATUS_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
"""Some symbols had data but none had enough points to meet MINIMUM_CURVE_POINTS."""

STOCK_COVERAGE_STATUS_FAILED = "FAILED"
"""Coverage fraction < threshold; curve not emitted."""

STOCK_COVERAGE_STATUS_ENUM = {
    STOCK_COVERAGE_STATUS_AVAILABLE,
    STOCK_COVERAGE_STATUS_PARTIAL,
    STOCK_COVERAGE_STATUS_MISSING_MARKET_DATA,
    STOCK_COVERAGE_STATUS_INSUFFICIENT_HISTORY,
    STOCK_COVERAGE_STATUS_FAILED,
}


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StockCurveResult:
    """Outcome of building a stock-derived equal-weight replay curve.

    Carries both the performance points and complete coverage diagnostics.
    """

    series_type: str
    """FULL_UNIVERSE or TOP_N_STRATEGY."""

    symbols_requested: Tuple[str, ...]
    """All symbols considered for this curve."""

    symbols_available: Tuple[str, ...]
    """Symbols that met MINIMUM_CURVE_POINTS within the replay window."""

    symbols_missing: Tuple[str, ...]
    """Symbols with no price data at all."""

    symbols_insufficient: Tuple[str, ...]
    """Symbols with some price data but fewer than MINIMUM_CURVE_POINTS."""

    coverage_fraction: float
    """len(symbols_available) / len(symbols_requested)."""

    coverage_status: str
    """One of STOCK_COVERAGE_STATUS_* constants."""

    points: Tuple[PricePoint, ...]
    """Equal-weight cumulative mean series. Empty if coverage_status == FAILED."""

    final_return: float | None
    """Last cumulative return value if points is non-empty, else None."""

    coverage_threshold_used: float
    """The threshold applied when classifying coverage_status."""

    symbols_truncated: bool = False
    """True if the requested universe exceeded MAX_SYMBOLS_PER_CATEGORY."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_symbol_series(
    symbol_series: Dict[str, List[PricePoint]],
    requested_symbols: Sequence[str],
) -> Tuple[List[str], List[str], List[str], Dict[str, List[PricePoint]]]:
    """Partition requested symbols into available, insufficient, and missing.

    Returns (available, insufficient, missing, available_series_map).
    """
    available: List[str] = []
    insufficient: List[str] = []
    missing: List[str] = []
    available_map: Dict[str, List[PricePoint]] = {}

    for symbol in requested_symbols:
        pts = symbol_series.get(symbol, [])
        if not pts:
            missing.append(symbol)
        elif len(pts) < MINIMUM_CURVE_POINTS:
            insufficient.append(symbol)
        else:
            available.append(symbol)
            available_map[symbol] = pts

    return available, insufficient, missing, available_map


def _coverage_status_from_fraction(
    fraction: float,
    threshold: float,
    total_requested: int,
    available_count: int,
    missing_count: int,
) -> str:
    if total_requested == 0:
        return STOCK_COVERAGE_STATUS_FAILED
    if missing_count == total_requested:
        return STOCK_COVERAGE_STATUS_MISSING_MARKET_DATA
    if available_count == 0:
        return STOCK_COVERAGE_STATUS_INSUFFICIENT_HISTORY
    if fraction < threshold:
        return STOCK_COVERAGE_STATUS_FAILED
    if available_count < total_requested:
        return STOCK_COVERAGE_STATUS_PARTIAL
    return STOCK_COVERAGE_STATUS_AVAILABLE


def _fetch_symbol_series(
    symbols: Sequence[str],
    start_date: str,
    end_date: str,
    provider: SecurityPriceHistoryProvider,
) -> Dict[str, List[PricePoint]]:
    """Fetch price series per symbol, preferring batch if provider supports it."""
    # Try batch download first (YahooHistoricalPriceProvider exposes get_batch_prices)
    if hasattr(provider, "get_batch_prices"):
        try:
            batch: Dict[str, List[PricePoint]] = provider.get_batch_prices(  # type: ignore[attr-defined]
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
            )
            # Fill any symbols that came back empty with empty lists
            return {s: list(batch.get(s, [])) for s in symbols}
        except Exception:
            pass  # Fall through to per-symbol loop

    result: Dict[str, List[PricePoint]] = {}
    for symbol in symbols:
        try:
            result[symbol] = list(provider.get_symbol_series(symbol, start_date, end_date))
        except Exception:
            result[symbol] = []
    return result


def _compute_final_return(points: Sequence[PricePoint]) -> float | None:
    """Return the last cumulative return value from an ordered series."""
    ordered = ensure_chronological(points)
    if len(ordered) < 2:
        return None
    base = ordered[0].value
    if base == 0:
        return None
    return round(float((ordered[-1].value / base) - 1.0), 8)


# ---------------------------------------------------------------------------
# Public curve builders
# ---------------------------------------------------------------------------

def build_full_universe_curve(
    *,
    universe_rows: Sequence[AnalyticalUniverseRow],
    start_date: str,
    end_date: str,
    provider: SecurityPriceHistoryProvider,
    filter_geography: str = "",
    filter_market_cap_bucket: str = "",
    filter_industry: str = "",
    coverage_threshold: float = FULL_UNIVERSE_COVERAGE_THRESHOLD,
    max_symbols: int = MAX_SYMBOLS_PER_CATEGORY,
) -> StockCurveResult:
    """Build a FULL_UNIVERSE equal-weight cumulative return curve.

    Applies point-in-time universe membership (only start_date rows) with
    optional geography / market_cap_bucket / industry filters.  No lookahead:
    membership is frozen at start_date and never updated.

    Args:
        universe_rows: Full analytical universe rows (any snapshot dates).
        start_date:    Replay start date — selects the universe snapshot.
        end_date:      Replay end date.
        provider:      Price provider for adjusted-close history.
        filter_geography, filter_market_cap_bucket, filter_industry:
                       Optional filters applied after start_date selection.
                       Empty string / 'ALL' means no filter.
        coverage_threshold: Minimum symbol coverage fraction to emit the curve.
        max_symbols:   Hard cap on universe size for safety.

    Returns:
        StockCurveResult with coverage diagnostics and (if above threshold)
        equal-weight performance points.
    """
    # 1. Point-in-time snapshot at start_date — no future rows
    start_rows = [r for r in universe_rows if r.snapshot_date == start_date]

    # 2. Apply filters
    geo_filter = filter_geography.upper()
    cap_filter = filter_market_cap_bucket.upper()
    ind_filter = filter_industry.upper()

    filtered_rows = [
        r for r in start_rows
        if (not geo_filter or r.geography.upper() == geo_filter)
        and (not cap_filter or r.market_cap_bucket.upper() == cap_filter)
        and (ind_filter in ("", "ALL") or r.industry.upper() == ind_filter)
        and getattr(r, "replay_eligible", True) is not False
        and str(getattr(r, "replay_eligible", True)).lower() != "false"
    ]

    # 3. Unique symbols, deterministic sort, safety cap
    seen: set[str] = set()
    symbols: List[str] = []
    for row in sorted(filtered_rows, key=lambda r: r.symbol):
        if row.symbol not in seen:
            seen.add(row.symbol)
            symbols.append(row.symbol)

    truncated = len(symbols) > max_symbols
    if truncated:
        symbols = symbols[:max_symbols]

    if not symbols:
        return StockCurveResult(
            series_type="FULL_UNIVERSE",
            symbols_requested=(),
            symbols_available=(),
            symbols_missing=(),
            symbols_insufficient=(),
            coverage_fraction=0.0,
            coverage_status=STOCK_COVERAGE_STATUS_FAILED,
            points=(),
            final_return=None,
            coverage_threshold_used=coverage_threshold,
            symbols_truncated=truncated,
        )

    # 4. Fetch prices
    raw_series = _fetch_symbol_series(symbols, start_date, end_date, provider)

    # 5. Classify coverage
    available, insufficient, missing, available_map = _classify_symbol_series(raw_series, symbols)
    coverage_fraction = len(available) / len(symbols)
    status = _coverage_status_from_fraction(
        fraction=coverage_fraction,
        threshold=coverage_threshold,
        total_requested=len(symbols),
        available_count=len(available),
        missing_count=len(missing),
    )

    # 6. Build curve only if above threshold
    points: List[PricePoint] = []
    final_return: float | None = None
    if status != STOCK_COVERAGE_STATUS_FAILED:
        points = equal_weighted_mean_series(available_map)
        final_return = _compute_final_return(points)

    return StockCurveResult(
        series_type="FULL_UNIVERSE",
        symbols_requested=tuple(symbols),
        symbols_available=tuple(available),
        symbols_missing=tuple(missing),
        symbols_insufficient=tuple(insufficient),
        coverage_fraction=coverage_fraction,
        coverage_status=status,
        points=tuple(points),
        final_return=final_return,
        coverage_threshold_used=coverage_threshold,
        symbols_truncated=truncated,
    )


def build_top_n_curve(
    *,
    selection: ReplaySelection,
    provider: SecurityPriceHistoryProvider,
    coverage_threshold: float = TOP_N_COVERAGE_THRESHOLD,
) -> StockCurveResult:
    """Build a TOP_N_STRATEGY equal-weight cumulative return curve.

    Uses the frozen selected_symbols from the ReplaySelection.  Membership is
    not updated during the replay — no lookahead, no replacement of missing
    symbols.

    Args:
        selection:          Frozen ReplaySelection with selected_symbols.
        provider:           Price provider for adjusted-close history.
        coverage_threshold: Minimum symbol coverage fraction to emit the curve.

    Returns:
        StockCurveResult with coverage diagnostics and (if above threshold)
        equal-weight performance points.
    """
    symbols = list(selection.selected_symbols)

    if not symbols:
        return StockCurveResult(
            series_type="TOP_N_STRATEGY",
            symbols_requested=(),
            symbols_available=(),
            symbols_missing=(),
            symbols_insufficient=(),
            coverage_fraction=0.0,
            coverage_status=STOCK_COVERAGE_STATUS_FAILED,
            points=(),
            final_return=None,
            coverage_threshold_used=coverage_threshold,
        )

    raw_series = _fetch_symbol_series(symbols, selection.start_date, selection.end_date, provider)
    available, insufficient, missing, available_map = _classify_symbol_series(raw_series, symbols)
    coverage_fraction = len(available) / len(symbols)
    status = _coverage_status_from_fraction(
        fraction=coverage_fraction,
        threshold=coverage_threshold,
        total_requested=len(symbols),
        available_count=len(available),
        missing_count=len(missing),
    )

    points: List[PricePoint] = []
    final_return: float | None = None
    if status != STOCK_COVERAGE_STATUS_FAILED:
        points = equal_weighted_mean_series(available_map)
        final_return = _compute_final_return(points)

    return StockCurveResult(
        series_type="TOP_N_STRATEGY",
        symbols_requested=tuple(symbols),
        symbols_available=tuple(available),
        symbols_missing=tuple(missing),
        symbols_insufficient=tuple(insufficient),
        coverage_fraction=coverage_fraction,
        coverage_status=status,
        points=tuple(points),
        final_return=final_return,
        coverage_threshold_used=coverage_threshold,
    )
