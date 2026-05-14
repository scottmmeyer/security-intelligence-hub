"""WP-04 analytical universe contract builder and partitioned storage manager."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from src.models.analytical_models import AnalyticalUniverseRow
from src.replay.registry_loader import resolve_category_mapping
from src.scoring.fetch_danelfin_scores import load_latest_danelfin_scores
from src.scoring.fetch_zacks_scores import load_latest_zacks_scores

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_WATCHLIST_PATH = _REPO_ROOT / "data" / "supplemental" / "watchlist.csv"
_DEFAULT_PORTFOLIO_VEHICLES_PATH = _REPO_ROOT / "data" / "supplemental" / "portfolio_vehicles.csv"

ANALYTICAL_UNIVERSE_HEADERS = [
    "security_id",
    "symbol",
    "security_type",
    "snapshot_date",
    "run_id",
    "market_cap_bucket",
    "geography",
    "country",
    "industry",
    "sector",
    "composite_score",
    "ess_score_text",
    "zacks_rating",
    "yahoo_score",
    "danelfin_score",
    "benchmark_id",
    "investable_vehicle_id",
    "price_at_snapshot",
    "provider_lineage",
]

_ESS_TEXT_SCORE_MAP = {
    "VERY_BULLISH": 5.0,
    "BULLISH": 4.0,
    "NEUTRAL": 3.0,
    "BEARISH": 2.0,
    "VERY_BEARISH": 1.0,
}

_ZACKS_TEXT_SCORE_MAP = {
    "STRONG BUY": 5.0,
    "STRONG_BUY": 5.0,
    "OUTPERFORM": 4.0,
    "BUY": 4.0,
    "OVERWEIGHT": 4.0,
    "NEUTRAL": 3.0,
    "HOLD": 3.0,
    "MARKET PERFORM": 3.0,
    "MARKET_PERFORM": 3.0,
    "EQUAL WEIGHT": 3.0,
    "EQUAL_WEIGHT": 3.0,
    "UNDERPERFORM": 2.0,
    "SELL": 2.0,
    "UNDERWEIGHT": 2.0,
    "STRONG SELL": 1.0,
    "STRONG_SELL": 1.0,
}


@dataclass(frozen=True)
class AnalyticalUniverseStoragePaths:
    current_output_path: Path
    partition_dir: Path
    partition_output_path: Path


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _load_watchlist_rows(
    watchlist_path: Path | str = _DEFAULT_WATCHLIST_PATH,
) -> List[Dict[str, str]]:
    """Load supplemental watchlist symbols as base-universe-compatible row dicts.

    Watchlist symbols are only injected when the symbol is NOT already present
    in the ESS-sourced base universe (ESS always wins on conflict).
    """
    watchlist_path = Path(watchlist_path)
    if not watchlist_path.exists():
        return []
    rows = []
    with watchlist_path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            symbol = str(raw.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            rows.append({
                "symbol": symbol,
                "company_name": str(raw.get("company_name", "") or ""),
                "security_type": str(raw.get("security_type", "") or "Common Stock"),
                "geography": str(raw.get("geography", "") or "US").strip().upper(),
                "market_cap_raw_usd": str(raw.get("market_cap_raw_usd", "") or ""),
                "market_cap_bucket": str(raw.get("market_cap_bucket", "") or "LARGE").strip().upper(),
                "coverage_domain": "WATCHLIST",
                "starmine_ess_text": str(raw.get("starmine_ess_text", "") or ""),
                "zacks_rating": "",
                "ess_zacks_rating": str(raw.get("ess_zacks_rating", "") or ""),
                "provider": "WATCHLIST",
                "source_file": "watchlist",
                "snapshot_date": "",
                "created_at_utc": "",
                "run_id": "",
            })
    return rows



PORTFOLIO_VEHICLE_HEADERS = [
    "symbol",
    "vehicle_name",
    "vehicle_type",
    "benchmark_id",
    "market_cap_bucket",
    "geography",
    "total_assets_usd",
    "note",
]


def load_portfolio_vehicles(
    path: Path | str = _DEFAULT_PORTFOLIO_VEHICLES_PATH,
) -> List[Dict[str, str]]:
    """Load portfolio vehicles (ETFs, mutual funds) that are held alongside equities.

    These are NOT scored through the composite engine.  They are tracked
    separately and benchmarked against their declared benchmark_id.
    Returns a list of dicts with the PORTFOLIO_VEHICLE_HEADERS fields.
    """
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv_rows(path: Path, headers: list[str], rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _ensure_file_with_headers(path: Path, headers: list[str]) -> None:
    if not path.exists():
        _write_csv_rows(path, headers, [])
        return

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        existing = next(reader, [])

    if not existing:
        _write_csv_rows(path, headers, [])
        return

    if existing != headers:
        raise ValueError(
            f"Analytical universe header mismatch for {path}: expected {headers}, observed {existing}."
        )


def _score_from_inputs(ess_score_text: str, zacks_rating: str, ess_zacks_rating: str, yahoo_score: str, danelfin_score: str) -> float:
    ess_score = _ESS_TEXT_SCORE_MAP.get(str(ess_score_text or "").strip().upper(), 0.0)

    def _to_float(raw: str) -> float:
        value = str(raw or "").strip()
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    # zacks_rating is a numeric score (1.0–5.0, already inverted) from internet fetch,
    # or a text token from a legacy/fallback source.
    zacks_key = str(zacks_rating or "").strip()
    zacks_score_raw = _to_float(zacks_key)
    if zacks_score_raw and 1.0 <= zacks_score_raw <= 5.0:
        zacks_score = zacks_score_raw
    elif zacks_key.upper() in _ZACKS_TEXT_SCORE_MAP:
        zacks_score = _ZACKS_TEXT_SCORE_MAP[zacks_key.upper()]
    else:
        # No internet fetch yet — fall back to ESS file's Zacks rank (stored as rank 1–5,
        # must be inverted to ascending score: score = 6 - rank).
        ess_zacks_raw = _to_float(str(ess_zacks_rating or "").strip())
        if ess_zacks_raw and 1.0 <= ess_zacks_raw <= 5.0:
            zacks_score = round(6.0 - ess_zacks_raw, 2)
        else:
            zacks_score = 3.0  # true last-resort NEUTRAL

    return round(
        (ess_score * 0.55)
        + (zacks_score * 0.25)
        + (_to_float(yahoo_score) * 0.10)
        + (_to_float(danelfin_score) * 0.10),
        6,
    )


def build_analytical_universe_storage_paths(
    *,
    snapshot_date: str,
    run_id: str,
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/analytical_universe",
) -> AnalyticalUniverseStoragePaths:
    current_root_path = Path(current_root)
    history_root_path = Path(history_root)
    partition_dir = history_root_path / f"snapshot_date={snapshot_date}" / f"run_id={run_id}"
    return AnalyticalUniverseStoragePaths(
        current_output_path=current_root_path / "analytical_universe.csv",
        partition_dir=partition_dir,
        partition_output_path=partition_dir / "analytical_universe.csv",
    )


def ensure_analytical_universe_contracts(
    *,
    current_root: str | Path = "data/current",
) -> None:
    """Ensure current analytical universe output contract exists."""

    _ensure_file_with_headers(Path(current_root) / "analytical_universe.csv", ANALYTICAL_UNIVERSE_HEADERS)


def build_analytical_universe_rows_from_current(
    *,
    run_id: str,
    snapshot_date: str,
    benchmark_registry: Dict[str, object],
    vehicle_registry: Dict[str, object],
    current_root: str | Path = "data/current",
    zacks_signals_dir: str | Path = "data/signals/zacks",
    danelfin_signals_dir: str | Path = "data/signals/danelfin",
    watchlist_path: str | Path = _DEFAULT_WATCHLIST_PATH,
) -> List[AnalyticalUniverseRow]:
    """Build analytical universe rows by merging current base universe and signal outputs."""

    current_root_path = Path(current_root)
    base_rows = _read_csv_rows(current_root_path / "base_equity_universe.csv")

    # Merge watchlist symbols — ESS symbols always win on conflict
    ess_symbols = {str(r.get("symbol", "")).strip().upper() for r in base_rows if r.get("symbol")}
    watchlist_rows = _load_watchlist_rows(watchlist_path)
    for wrow in watchlist_rows:
        if wrow["symbol"] not in ess_symbols:
            base_rows.append(wrow)

    signal_rows = _read_csv_rows(current_root_path / "signal_snapshot.csv")
    signal_by_symbol = {
        str(row.get("symbol", "")).strip().upper(): row
        for row in signal_rows
        if str(row.get("symbol", "")).strip()
    }

    zacks_scores_by_symbol = load_latest_zacks_scores(zacks_signals_dir)
    danelfin_scores_by_symbol = load_latest_danelfin_scores(danelfin_signals_dir)

    analytical_rows: List[AnalyticalUniverseRow] = []
    for base_row in sorted(base_rows, key=lambda row: str(row.get("symbol", ""))):
        symbol = str(base_row.get("symbol", "")).strip().upper()
        if not symbol:
            continue

        signal_row = signal_by_symbol.get(symbol, {})
        raw_geography = str(base_row.get("geography", "")).strip().upper()
        geography = raw_geography if raw_geography in {"US", "INTERNATIONAL"} else "US"

        raw_market_cap = str(base_row.get("market_cap_bucket", "")).strip().upper()
        market_cap_bucket = (
            raw_market_cap
            if raw_market_cap in {"MEGA", "LARGE", "MID", "SMALL", "MICRO"}
            else "LARGE"
        )

        benchmark_id = "UNMAPPED"
        vehicle_id = "UNMAPPED"
        try:
            benchmark, vehicle = resolve_category_mapping(
                geography=geography,
                market_cap_bucket=market_cap_bucket,
                industry_scope="ALL",
                benchmark_registry=benchmark_registry,
                vehicle_registry=vehicle_registry,
            )
            benchmark_id = benchmark.benchmark_id
            vehicle_id = vehicle.vehicle_id
        except ValueError:
            benchmark_id = "UNMAPPED"
            vehicle_id = "UNMAPPED"

        ess_score_text = str(signal_row.get("starmine_ess_text") or base_row.get("starmine_ess_text") or "").strip()
        # Zacks score: prefer internet fetch cache; fall back to ESS file's Zacks rank (ess_zacks_rating).
        fetched_zacks_score = zacks_scores_by_symbol.get(symbol)
        zacks_rating = str(fetched_zacks_score) if fetched_zacks_score is not None else ""
        ess_zacks_rating = str(base_row.get("ess_zacks_rating", "")).strip()
        yahoo_score = str(base_row.get("yahoo_score", "")).strip()
        # Danelfin score: prefer cache; fall back to base row value (may be blank).
        fetched_danelfin_score = danelfin_scores_by_symbol.get(symbol)
        danelfin_score = (
            str(fetched_danelfin_score)
            if fetched_danelfin_score is not None
            else str(base_row.get("danelfin_score", "")).strip()
        )

        analytical_rows.append(
            AnalyticalUniverseRow(
                security_id=f"{str(base_row.get('provider', 'UNKNOWN')).strip().upper()}:{symbol}",
                symbol=symbol,
                security_type=str(base_row.get("security_type", "UNKNOWN")).strip() or "UNKNOWN",
                snapshot_date=snapshot_date,
                run_id=run_id,
                market_cap_bucket=market_cap_bucket,
                geography=geography,
                country="US" if geography == "US" else "UNKNOWN",
                industry=str(base_row.get("industry", "ALL")).strip() or "ALL",
                sector=str(base_row.get("sector", "ALL")).strip() or "ALL",
                composite_score=_score_from_inputs(ess_score_text, zacks_rating, ess_zacks_rating, yahoo_score, danelfin_score),
                ess_score_text=ess_score_text,
                zacks_rating=zacks_rating,
                yahoo_score=yahoo_score,
                danelfin_score=danelfin_score,
                benchmark_id=benchmark_id,
                investable_vehicle_id=vehicle_id,
                price_at_snapshot="",
                provider_lineage=(
                    f"provider={str(base_row.get('provider', '')).strip()};"
                    f"source_file={str(base_row.get('source_file', '')).strip()}"
                ),
            )
        )

    return analytical_rows


def write_analytical_universe_rows(
    *,
    rows: Iterable[AnalyticalUniverseRow],
    snapshot_date: str,
    run_id: str,
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/analytical_universe",
) -> int:
    """Write analytical universe rows to current and immutable run partition outputs."""

    typed_rows = list(rows)
    ensure_analytical_universe_contracts(current_root=current_root)
    paths = build_analytical_universe_storage_paths(
        snapshot_date=snapshot_date,
        run_id=run_id,
        current_root=current_root,
        history_root=history_root,
    )

    if paths.partition_dir.exists():
        raise ValueError(
            "Immutable analytical-universe partition protection triggered: partition already exists for "
            f"run_id={run_id} at {paths.partition_dir}."
        )

    deduped_by_security: Dict[str, AnalyticalUniverseRow] = {}
    for row in typed_rows:
        existing = deduped_by_security.get(row.security_id)
        if existing is None:
            deduped_by_security[row.security_id] = row
            continue

        # Keep the strongest score deterministically; tie-break by symbol then lineage text.
        if (row.composite_score, row.symbol, row.provider_lineage) > (
            existing.composite_score,
            existing.symbol,
            existing.provider_lineage,
        ):
            deduped_by_security[row.security_id] = row

    normalized_rows: List[Dict[str, object]] = []
    for row in sorted(deduped_by_security.values(), key=lambda item: (item.symbol, item.security_id)):
        normalized_rows.append(
            {
                "security_id": row.security_id,
                "symbol": row.symbol,
                "security_type": row.security_type,
                "snapshot_date": row.snapshot_date,
                "run_id": row.run_id,
                "market_cap_bucket": row.market_cap_bucket,
                "geography": row.geography,
                "country": row.country,
                "industry": row.industry,
                "sector": row.sector,
                "composite_score": row.composite_score,
                "ess_score_text": row.ess_score_text,
                "zacks_rating": row.zacks_rating,
                "yahoo_score": row.yahoo_score,
                "danelfin_score": row.danelfin_score,
                "benchmark_id": row.benchmark_id,
                "investable_vehicle_id": row.investable_vehicle_id,
                "price_at_snapshot": row.price_at_snapshot,
                "provider_lineage": row.provider_lineage,
            }
        )

    paths.partition_dir.mkdir(parents=True, exist_ok=False)
    _write_csv_rows(paths.partition_output_path, ANALYTICAL_UNIVERSE_HEADERS, normalized_rows)
    _write_csv_rows(paths.current_output_path, ANALYTICAL_UNIVERSE_HEADERS, normalized_rows)
    return len(normalized_rows)
