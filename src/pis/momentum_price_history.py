"""Momentum price-history coverage and restoration utilities (reporting-only).

This module uses existing repo-supported market-data providers and persistence
contracts to inventory and restore price history for current portfolio momentum
analytics without changing scoring or recommendation behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from src.history.market_data_manager import persist_benchmark_returns, persist_security_prices
from src.models.market_data_models import BenchmarkReturnRow
from src.replay.history_providers import YahooHistoricalPriceProvider


APPLICABLE_SECURITY_TYPES = {
    "EQUITY",
    "EQUITIES",
    "STOCK",
    "COMMON STOCK",
    "COMMON_STOCK",
    "ADR",
    "ETF",
}

SECTOR_PARENT_ETF_MAP = {
    "TECHNOLOGY": "XLK",
    "ENERGY": "XLE",
    "BASIC MATERIALS": "XLB",
    "INDUSTRIALS": "XLI",
    "HEALTHCARE": "XLV",
    "FINANCIAL SERVICES": "XLF",
    "FINANCIALS": "XLF",
    "CONSUMER CYCLICAL": "XLY",
    "CONSUMER DEFENSIVE": "XLP",
    "CONSUMER STAPLES": "XLP",
    "UTILITIES": "XLU",
    "REAL ESTATE": "XLRE",
    "COMMUNICATION SERVICES": "XLC",
}


@dataclass(frozen=True)
class PriceCoverageRow:
    symbol: str
    asset_type: str
    sector: str
    industry: str
    first_price_date: str | None
    last_price_date: str | None
    trading_days_available: int
    source: str | None
    freshness_days: int | None
    coverage_status: str


@dataclass(frozen=True)
class CoverageInventory:
    snapshot_date: str
    applicable_count: int
    not_applicable_count: int
    present_count: int
    missing_count: int
    partial_count: int
    coverage_pct: float
    rows: tuple[PriceCoverageRow, ...]
    not_applicable_symbols: tuple[str, ...]


@dataclass(frozen=True)
class SectorParentCoverageRow:
    sector: str
    current_holdings_count: int
    parent_series: str | None
    parent_source: str | None
    history_available: bool
    first_date: str | None
    last_date: str | None
    trading_days_available: int


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_float(value: object) -> float | None:
    try:
        text = str(value or "").strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _normalize_date(value: object) -> str:
    raw = str(value or "").strip()
    return raw[:10] if len(raw) >= 10 else ""


def _freshness_days(last_date: str | None) -> int | None:
    if not last_date:
        return None
    try:
        d = date.fromisoformat(last_date)
    except ValueError:
        return None
    return (date.today() - d).days


def _latest_positions_file(repo_root: Path) -> tuple[str, Path | None]:
    rows = _read_csv_rows(repo_root / "data/history/pis/pis_snapshot_index.csv")
    if not rows:
        return "", None
    best = max(rows, key=lambda row: str(row.get("snapshot_date", "")))
    positions_path = str(best.get("positions_path", "")).strip()
    if not positions_path:
        return str(best.get("snapshot_date", "")), None
    p = Path(positions_path)
    if not p.is_absolute():
        p = repo_root / p
    return str(best.get("snapshot_date", "")), p


def _load_universe_metadata(repo_root: Path) -> dict[str, dict[str, str]]:
    """Load security metadata from authoritative sources.
    
    Priority:
    1. Portfolio analysis holdings.csv (has enriched sector/industry for current portfolio)
    2. Analytical universe CSV (has ESS/Zacks/Yahoo data for broader universe)
    """
    out: dict[str, dict[str, str]] = {}

    # First: check portfolio ingestion for current holdings metadata
    portfolio_runs_dir = repo_root / "data/portfolio_ingestion/analysis_runs"
    if portfolio_runs_dir.exists():
        # Find latest portfolio analysis run
        latest_run = max(
            (d for d in portfolio_runs_dir.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            default=None,
        )
        if latest_run:
            holdings_path = latest_run / "holdings.csv"
            if holdings_path.exists():
                for row in _read_csv_rows(holdings_path):
                    symbol = str(row.get("symbol", "")).strip().upper()
                    if not symbol:
                        continue
                    out[symbol] = {
                        "sector": str(row.get("sector", "")).strip(),
                        "industry": str(row.get("industry", "")).strip(),
                        "security_type": str(row.get("security_type", "")).strip(),
                    }

    # Second: load analytical_universe for securities not in portfolio analysis
    universe_rows = _read_csv_rows(repo_root / "data/current/analytical_universe.csv")
    for row in universe_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in out:
            continue
        out[symbol] = {
            "sector": str(row.get("sector", "")).strip(),
            "industry": str(row.get("industry", "")).strip(),
            "security_type": str(row.get("security_type", "")).strip(),
        }
    return out


def load_current_holdings(repo_root: Path) -> tuple[str, list[dict[str, object]]]:
    snapshot_date, positions_path = _latest_positions_file(repo_root)
    if positions_path is None or not positions_path.exists():
        return snapshot_date, []

    universe = _load_universe_metadata(repo_root)
    out: list[dict[str, object]] = []
    for row in _read_csv_rows(positions_path):
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in {"CASH", "PENDING"}:
            continue
        sec_type = str(row.get("security_type", "")).strip().upper()
        metadata = universe.get(symbol, {})
        sector = str(metadata.get("sector", "")).strip()
        industry = str(metadata.get("industry", "")).strip()
        weight = _to_float(row.get("percent_of_account")) or 0.0
        out.append(
            {
                "symbol": symbol,
                "asset_type": sec_type,
                "sector": sector,
                "industry": industry,
                "portfolio_weight": float(weight),
            }
        )
    return snapshot_date, out


def _price_series_stats(repo_root: Path, symbol: str) -> tuple[str | None, str | None, int, str | None]:
    price_file = repo_root / "data/history/prices" / f"symbol={symbol}" / "prices.csv"
    if not price_file.exists():
        return None, None, 0, None
    rows = _read_csv_rows(price_file)
    if not rows:
        return None, None, 0, None
    dates = sorted([_normalize_date(r.get("date", "")) for r in rows if _normalize_date(r.get("date", ""))])
    if not dates:
        return None, None, 0, None
    source = str(rows[-1].get("source_provider", "")).strip() or None
    return dates[0], dates[-1], len(dates), source


def _coverage_status(trading_days: int, freshness: int | None) -> str:
    if trading_days <= 0:
        return "MISSING"
    if trading_days < 253:
        return "PARTIAL"
    if freshness is None:
        return "PARTIAL"
    if freshness > 5:
        return "PARTIAL"
    return "PRESENT"


def inventory_current_price_coverage(repo_root: str | Path = ".") -> CoverageInventory:
    root = Path(repo_root)
    snapshot_date, holdings = load_current_holdings(root)

    rows: list[PriceCoverageRow] = []
    not_applicable_symbols: list[str] = []

    applicable_count = 0
    present_count = 0
    missing_count = 0
    partial_count = 0

    for holding in holdings:
        symbol = str(holding["symbol"])
        asset_type = str(holding["asset_type"])
        sector = str(holding["sector"])
        industry = str(holding["industry"])

        if asset_type not in APPLICABLE_SECURITY_TYPES:
            not_applicable_symbols.append(symbol)
            continue

        applicable_count += 1
        first_date, last_date, trading_days, source = _price_series_stats(root, symbol)
        freshness = _freshness_days(last_date)
        status = _coverage_status(trading_days, freshness)
        if status == "PRESENT":
            present_count += 1
        elif status == "PARTIAL":
            partial_count += 1
        else:
            missing_count += 1

        rows.append(
            PriceCoverageRow(
                symbol=symbol,
                asset_type=asset_type,
                sector=sector,
                industry=industry,
                first_price_date=first_date,
                last_price_date=last_date,
                trading_days_available=trading_days,
                source=source,
                freshness_days=freshness,
                coverage_status=status,
            )
        )

    coverage_pct = 0.0
    if applicable_count > 0:
        coverage_pct = round((present_count / applicable_count) * 100.0, 2)

    return CoverageInventory(
        snapshot_date=snapshot_date,
        applicable_count=applicable_count,
        not_applicable_count=len(not_applicable_symbols),
        present_count=present_count,
        missing_count=missing_count,
        partial_count=partial_count,
        coverage_pct=coverage_pct,
        rows=tuple(sorted(rows, key=lambda r: r.symbol)),
        not_applicable_symbols=tuple(sorted(not_applicable_symbols)),
    )


def inventory_sector_parent_coverage(repo_root: str | Path = ".") -> list[SectorParentCoverageRow]:
    root = Path(repo_root)
    _snapshot_date, holdings = load_current_holdings(root)

    sector_counts: dict[str, int] = {}
    for h in holdings:
        asset_type = str(h["asset_type"])
        if asset_type not in APPLICABLE_SECURITY_TYPES:
            continue
        sector = str(h["sector"] or "UNKNOWN").strip()
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    rows: list[SectorParentCoverageRow] = []
    for sector, count in sorted(sector_counts.items()):
        parent = SECTOR_PARENT_ETF_MAP.get(sector.upper())
        first_date = None
        last_date = None
        trading_days = 0
        source = None
        history_available = False
        if parent:
            first_date, last_date, trading_days, source = _price_series_stats(root, parent)
            history_available = trading_days > 0

        rows.append(
            SectorParentCoverageRow(
                sector=sector,
                current_holdings_count=count,
                parent_series=parent,
                parent_source=source,
                history_available=history_available,
                first_date=first_date,
                last_date=last_date,
                trading_days_available=trading_days,
            )
        )
    return rows


def restore_current_portfolio_price_history(
    *,
    repo_root: str | Path = ".",
    lookback_calendar_days: int = 420,
    include_sector_parents: bool = True,
    include_benchmark: bool = True,
) -> dict[str, object]:
    """Restore price history for applicable current holdings and required parents.

    Uses existing Yahoo historical provider and existing immutable persistence
    contracts; does not alter normal signal refresh semantics.
    """

    root = Path(repo_root)
    before = inventory_current_price_coverage(root)
    provider = YahooHistoricalPriceProvider()

    snapshot_date, holdings = load_current_holdings(root)
    end_date = date.today()
    start_date = end_date - timedelta(days=max(30, int(lookback_calendar_days)))

    applicable_symbols = sorted(
        {
            str(h["symbol"])
            for h in holdings
            if str(h.get("asset_type", "")).upper() in APPLICABLE_SECURITY_TYPES
        }
    )

    target_symbols: set[str] = set(applicable_symbols)
    parent_symbols: set[str] = set()

    if include_sector_parents:
        for row in inventory_sector_parent_coverage(root):
            if row.parent_series:
                parent_symbols.add(row.parent_series)
        target_symbols.update(parent_symbols)

    historical_rows = []
    fetched_symbols: list[str] = []
    failed_symbols: list[str] = []
    for symbol in sorted(target_symbols):
        try:
            rows = provider.get_historical_prices(
                security_id=f"YF:{symbol}",
                symbol=symbol,
                security_type="ETF" if symbol in parent_symbols else "EQUITY",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        except Exception:
            rows = []
        if rows:
            fetched_symbols.append(symbol)
            historical_rows.extend(rows)
        else:
            failed_symbols.append(symbol)

    security_persist = {"current_rows": 0, "history_rows_appended": 0, "symbol_partition_count": 0}
    if historical_rows:
        security_persist = persist_security_prices(rows=historical_rows)

    benchmark_persist = {"current_rows": 0, "history_rows_appended": 0, "benchmark_partition_count": 0}
    benchmark_symbol = "^GSPC"
    if include_benchmark:
        bm_prices = provider.get_historical_prices(
            security_id="BENCH:BM_US_LARGE_SP500",
            symbol=benchmark_symbol,
            security_type="BENCHMARK_INDEX",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        bm_points = sorted([(r.date, float(r.adjusted_close)) for r in bm_prices if r.adjusted_close > 0], key=lambda x: x[0])
        if bm_points:
            base = bm_points[0][1]
            bm_rows = [
                BenchmarkReturnRow(
                    benchmark_id="BM_US_LARGE_SP500",
                    symbol_or_index=benchmark_symbol,
                    date=d,
                    adjusted_close=round(v, 8),
                    cumulative_return=round((v / base) - 1.0, 8),
                    source_provider="YAHOO_FINANCE",
                )
                for d, v in bm_points
                if base > 0
            ]
            benchmark_persist = persist_benchmark_returns(rows=bm_rows)

    after = inventory_current_price_coverage(root)
    sector_after = inventory_sector_parent_coverage(root)

    return {
        "snapshot_date": snapshot_date,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "applicable_symbols": applicable_symbols,
        "sector_parent_symbols": sorted(parent_symbols),
        "target_symbol_count": len(target_symbols),
        "fetched_symbols": sorted(fetched_symbols),
        "failed_symbols": sorted(failed_symbols),
        "security_persistence": security_persist,
        "benchmark_persistence": benchmark_persist,
        "coverage_before": {
            "applicable": before.applicable_count,
            "present": before.present_count,
            "missing": before.missing_count,
            "partial": before.partial_count,
            "coverage_pct": before.coverage_pct,
        },
        "coverage_after": {
            "applicable": after.applicable_count,
            "present": after.present_count,
            "missing": after.missing_count,
            "partial": after.partial_count,
            "coverage_pct": after.coverage_pct,
        },
        "sector_parent_coverage_after": [
            {
                "sector": row.sector,
                "current_holdings_count": row.current_holdings_count,
                "parent_series": row.parent_series,
                "parent_source": row.parent_source,
                "history_available": row.history_available,
                "first_date": row.first_date,
                "last_date": row.last_date,
                "trading_days_available": row.trading_days_available,
            }
            for row in sector_after
        ],
    }
