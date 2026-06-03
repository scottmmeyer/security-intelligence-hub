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
from src.scoring.market_cap_subtier_classifier import classify_analytical_subtiers, load_subtier_policy
from src.classification.security_type_policy import load_security_type_policy
from src.classification.geography_resolver import (
    load_adr_domicile_policy,
    load_geography_overrides,
    resolve_geography,
)
from src.classification.benchmark_assignment_engine import assign_benchmarks

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_WATCHLIST_PATH = _REPO_ROOT / "data" / "supplemental" / "watchlist.csv"
_DEFAULT_PORTFOLIO_VEHICLES_PATH = _REPO_ROOT / "data" / "supplemental" / "portfolio_vehicles.csv"
_DEFAULT_SUBTIER_POLICY_PATH = _REPO_ROOT / "config" / "market_cap_subtier_policy.yaml"
_DEFAULT_SECURITY_METADATA_PATH = _REPO_ROOT / "data" / "signals" / "security_metadata" / "latest_security_metadata.csv"

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
    "analytical_market_cap_subtier",
    "classification_policy_id",
    "classification_snapshot_date",
    # Phase 1 classification integrity fields
    "replay_eligible",
    "scoring_eligible",
    "allocation_eligible",
    "benchmark_confidence",
    "sector_benchmark_id",
    "classification_method",
    # ---------------------------------------------------------------------------
    # Factor research and governance fields — Phase 2+: composite versioning.
    # Additive only; composite_score (v1) is never overwritten by these fields.
    # ---------------------------------------------------------------------------
    "yahoo_abr_normalized",
    "composite_v2_yahoo",
    "composite_version",
    "score_generation_timestamp",
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

# ---------------------------------------------------------------------------
# Composite v2 — Yahoo ABR experimental research weights
# ---------------------------------------------------------------------------
# v1 (production):  ESS=0.55, Zacks=0.25, Yahoo=0.10 (unused), Danelfin=0.10
# v2 (research):    ESS=0.50, Zacks=0.225, Danelfin=0.175, Yahoo=0.10
#
# ESS reduced slightly to accommodate Yahoo.  Danelfin upweighted reflecting
# improved coverage.  Renormalization over available signals still applies.
# These weights are intentionally conservative for initial validation.
_V2_YAHOO_WEIGHTS: dict = {
    "ess":      0.500,
    "zacks":    0.225,
    "danelfin": 0.175,
    "yahoo":    0.100,
}
_COMPOSITE_V2_VERSION_TAG = "v2_yahoo_exp_20260522"


def normalize_yahoo_abr(abr_raw: str | float) -> float:
    """Convert Yahoo analyst-buy-rating (1=Strong Buy … 5=Strong Sell) to 1–5 ascending.

    Returns ``6.0 - abr`` clipped to [1.0, 5.0], or 0.0 if no valid ABR present.
    ABR=1.0 (Strong Buy) → 5.0; ABR=5.0 (Strong Sell) → 1.0.
    """
    try:
        abr = float(str(abr_raw or "").strip())
    except (ValueError, TypeError):
        return 0.0
    if not (1.0 <= abr <= 5.0):
        return 0.0
    return round(max(1.0, min(5.0, 6.0 - abr)), 6)


def score_composite_v2_yahoo(
    ess_score_text: str,
    zacks_rating: str,
    ess_zacks_rating: str,
    yahoo_abr_normalized: str,
    danelfin_score: str,
) -> float:
    """Compute experimental composite_v2_yahoo score.

    Identical flow to ``_score_from_inputs`` but uses ``_V2_YAHOO_WEIGHTS`` and
    treats ``yahoo_abr_normalized`` (already on 1–5 ascending scale) as the Yahoo
    factor.  Renormalizes over available signals only.
    """
    def _to_float(raw: str) -> float:
        value = str(raw or "").strip()
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    ess_text = str(ess_score_text or "").strip().upper()
    ess_available = ess_text in _ESS_TEXT_SCORE_MAP
    ess_score = _ESS_TEXT_SCORE_MAP.get(ess_text, 0.0)

    zacks_key = str(zacks_rating or "").strip()
    zacks_score_raw = _to_float(zacks_key)
    if zacks_score_raw and 1.0 <= zacks_score_raw <= 5.0:
        zacks_score = zacks_score_raw
        zacks_available = True
    elif zacks_key.upper() in _ZACKS_TEXT_SCORE_MAP:
        zacks_score = _ZACKS_TEXT_SCORE_MAP[zacks_key.upper()]
        zacks_available = True
    else:
        ess_zacks_raw = _to_float(str(ess_zacks_rating or "").strip())
        if ess_zacks_raw and 1.0 <= ess_zacks_raw <= 5.0:
            zacks_score = round(6.0 - ess_zacks_raw, 2)
            zacks_available = True
        else:
            zacks_score = 3.0
            zacks_available = False

    yahoo_val = _to_float(yahoo_abr_normalized)
    danelfin_val = _to_float(danelfin_score)

    w = _V2_YAHOO_WEIGHTS
    signals = [
        (ess_score,    w["ess"],      ess_available),
        (zacks_score,  w["zacks"],    zacks_available),
        (yahoo_val,    w["yahoo"],    yahoo_val > 0.0),
        (danelfin_val, w["danelfin"], danelfin_val > 0.0),
    ]
    total_weight = sum(wt for _, wt, avail in signals if avail)
    if total_weight == 0.0:
        return 3.0
    return round(
        sum(score * wt for score, wt, avail in signals if avail) / total_weight,
        6,
    )


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


def _load_security_metadata(
    metadata_path: Path | str = _DEFAULT_SECURITY_METADATA_PATH,
) -> Dict[str, str]:
    """Load symbol → sector mapping from security metadata cache.

    Returns a dict mapping uppercase symbol to uppercase sector name.
    Symbols not in the cache will not appear; callers should default to "ALL".
    """
    path = Path(metadata_path)
    if not path.exists():
        return {}
    sector_map: Dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = str(row.get("symbol", "")).strip().upper()
            sector = str(row.get("sector", "")).strip()
            if symbol and sector:
                sector_map[symbol] = sector.upper()
    return sector_map


def _load_full_security_metadata(
    metadata_path: Path | str = _DEFAULT_SECURITY_METADATA_PATH,
) -> Dict[str, Dict[str, str]]:
    """Load symbol → full metadata dict (country, quote_type, sector, industry) from cache."""
    path = Path(metadata_path)
    if not path.exists():
        return {}
    result: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


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

    if existing == headers:
        return

    # Additive schema evolution: existing columns may be a subset of expected.
    # Reject if the file has columns not present in the expected schema (schema divergence).
    headers_set = set(headers)
    unknown_cols = [h for h in existing if h not in headers_set]
    if unknown_cols:
        raise ValueError(
            f"Analytical universe has unrecognized columns in {path}: {unknown_cols}. "
            f"Expected schema: {headers}."
        )
    # Existing file has fewer columns — additive evolution is OK; caller will overwrite.


def _score_from_inputs(ess_score_text: str, zacks_rating: str, ess_zacks_rating: str, yahoo_score: str, danelfin_score: str) -> float:
    def _to_float(raw: str) -> float:
        value = str(raw or "").strip()
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    ess_text = str(ess_score_text or "").strip().upper()
    ess_available = ess_text in _ESS_TEXT_SCORE_MAP
    ess_score = _ESS_TEXT_SCORE_MAP.get(ess_text, 0.0)

    # zacks_rating is a numeric score (1.0–5.0, already inverted) from internet fetch,
    # or a text token from a legacy/fallback source.
    zacks_key = str(zacks_rating or "").strip()
    zacks_score_raw = _to_float(zacks_key)
    if zacks_score_raw and 1.0 <= zacks_score_raw <= 5.0:
        zacks_score = zacks_score_raw
        zacks_available = True
    elif zacks_key.upper() in _ZACKS_TEXT_SCORE_MAP:
        zacks_score = _ZACKS_TEXT_SCORE_MAP[zacks_key.upper()]
        zacks_available = True
    else:
        # No internet fetch yet — fall back to ESS file's Zacks rank (stored as rank 1–5,
        # must be inverted to ascending score: score = 6 - rank).
        ess_zacks_raw = _to_float(str(ess_zacks_rating or "").strip())
        if ess_zacks_raw and 1.0 <= ess_zacks_raw <= 5.0:
            zacks_score = round(6.0 - ess_zacks_raw, 2)
            zacks_available = True
        else:
            zacks_score = 3.0  # true last-resort NEUTRAL
            zacks_available = False

    yahoo_val = _to_float(yahoo_score)
    danelfin_val = _to_float(danelfin_score)

    # Compute a weighted average using only signals that are actually present.
    # Missing signals (especially ESS, which carries 55% of the base weight) are
    # excluded from both numerator and denominator rather than defaulting to 0.0,
    # which would unfairly penalise securities without full coverage (e.g. international
    # or watchlist names that lack StarMine data).
    signals = [
        (ess_score,    0.55, ess_available),
        (zacks_score,  0.25, zacks_available),
        (yahoo_val,    0.10, yahoo_val > 0.0),
        (danelfin_val, 0.10, danelfin_val > 0.0),
    ]
    total_weight = sum(w for _, w, avail in signals if avail)
    if total_weight == 0.0:
        return 3.0  # no signals available → neutral

    return round(
        sum(score * w for score, w, avail in signals if avail) / total_weight,
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
    subtier_policy_path: str | Path = _DEFAULT_SUBTIER_POLICY_PATH,
    security_metadata_path: str | Path = _DEFAULT_SECURITY_METADATA_PATH,
) -> List[AnalyticalUniverseRow]:
    """Build analytical universe rows by merging current base universe and signal outputs."""

    current_root_path = Path(current_root)
    sector_by_symbol = _load_security_metadata(security_metadata_path)
    base_rows = _read_csv_rows(current_root_path / "base_equity_universe.csv")

    # Merge watchlist symbols — ESS symbols always win on conflict
    ess_symbols = {str(r.get("symbol", "")).strip().upper() for r in base_rows if r.get("symbol")}
    watchlist_rows = _load_watchlist_rows(watchlist_path)
    for wrow in watchlist_rows:
        if wrow["symbol"] not in ess_symbols:
            base_rows.append(wrow)

    # Build symbol → raw market cap map for subtier classification (needs raw USD values).
    base_raw_map: Dict[str, int] = {}
    for r in base_rows:
        sym = str(r.get("symbol", "")).strip().upper()
        raw = r.get("market_cap_raw_usd", "")
        try:
            base_raw_map[sym] = int(raw) if raw not in ("", None) else 0
        except (ValueError, TypeError):
            base_raw_map[sym] = 0

    signal_rows = _read_csv_rows(current_root_path / "signal_snapshot.csv")
    # Coverage-aware dedup: STARMINE_COVERED always wins over NON_STARMINE_ANALYST.
    # A plain last-row-wins dict comprehension would silently overwrite valid covered
    # rows with ESS_NONE sentinel rows when both appear for the same symbol.
    _COVERAGE_PRIORITY: Dict[str, int] = {"STARMINE_COVERED": 1, "NON_STARMINE_ANALYST": 0}
    signal_by_symbol: Dict[str, dict] = {}
    for _row in signal_rows:
        _sym = str(_row.get("symbol", "")).strip().upper()
        if not _sym:
            continue
        _existing = signal_by_symbol.get(_sym)
        if _existing is None:
            signal_by_symbol[_sym] = _row
        else:
            _new_pri = _COVERAGE_PRIORITY.get(str(_row.get("coverage_domain", "")), 0)
            _old_pri = _COVERAGE_PRIORITY.get(str(_existing.get("coverage_domain", "")), 0)
            if _new_pri > _old_pri:
                signal_by_symbol[_sym] = _row

    zacks_scores_by_symbol = load_latest_zacks_scores(zacks_signals_dir)
    danelfin_scores_by_symbol = load_latest_danelfin_scores(danelfin_signals_dir)

    # Phase 22D.2 WS-B: ESS history archive fallback.
    # Symbols absent from signal_snapshot.csv or classified NON_STARMINE_ANALYST
    # have an empty starmine_ess_text in the pipeline, but may have valid recent
    # ESS data in ess_history_master.csv.  Load the archive and use it as a
    # fallback when the primary signal path yields no ESS text.
    _ess_archive_path = _REPO_ROOT / "ess_history_master.csv"
    ess_archive_by_symbol: Dict[str, str] = {}
    if _ess_archive_path.exists():
        _ess_archive_dates: Dict[str, str] = {}
        with _ess_archive_path.open("r", encoding="utf-8", newline="") as _efh:
            for _erow in csv.DictReader(_efh):
                _esym = str(_erow.get("symbol", "")).strip().upper()
                _ecat = str(_erow.get("ess_category", "")).strip()
                _edate = str(_erow.get("capture_date", "")).strip()
                if _esym and _ecat and _edate:
                    if _esym not in _ess_archive_dates or _edate > _ess_archive_dates[_esym]:
                        _ess_archive_dates[_esym] = _edate
                        ess_archive_by_symbol[_esym] = _ecat

    # --- load classification policy data once (reused across all rows) ---
    type_policy = load_security_type_policy()
    domicile_map = load_adr_domicile_policy()
    geo_overrides = load_geography_overrides()
    full_metadata = _load_full_security_metadata(security_metadata_path)

    analytical_rows: List[AnalyticalUniverseRow] = []
    for base_row in sorted(base_rows, key=lambda row: str(row.get("symbol", ""))):
        symbol = str(base_row.get("symbol", "")).strip().upper()
        if not symbol:
            continue

        signal_row = signal_by_symbol.get(symbol, {})
        meta = full_metadata.get(symbol, {})

        raw_market_cap = str(base_row.get("market_cap_bucket", "")).strip().upper()
        market_cap_bucket = (
            raw_market_cap
            if raw_market_cap in {"MEGA", "LARGE", "MID", "SMALL", "MICRO"}
            else "LARGE"
        )

        raw_security_type = str(base_row.get("security_type", "UNKNOWN")).strip() or "UNKNOWN"
        type_info = type_policy.get_type_info(raw_security_type)

        # Geography resolution — replaces the prior "US or default to US" heuristic.
        geo_resolution = resolve_geography(
            symbol=symbol,
            security_type=raw_security_type,
            country=meta.get("country", ""),
            quote_type=meta.get("quote_type", ""),
            existing_geography=str(base_row.get("geography", "")).strip().upper(),
            domicile_map=domicile_map,
            overrides=geo_overrides,
        )
        geography = geo_resolution.geography
        # Use UNKNOWN as the stored geography (not silently defaulting to US);
        # the audit script (V01) will flag equities with geography=UNKNOWN.

        # Country: use yfinance metadata if available; otherwise derive from geography.
        resolved_country = meta.get("country", "").strip()
        if not resolved_country:
            resolved_country = "US" if geography == "US" else "UNKNOWN"

        # Benchmark assignment — uses classification engine for confidence + method.
        bm_assignment = assign_benchmarks(
            symbol=symbol,
            security_type_info=type_info,
            geography_resolution=geo_resolution,
            market_cap_bucket=market_cap_bucket,
            benchmark_registry=benchmark_registry,
            vehicle_registry=vehicle_registry,
        )
        benchmark_id = bm_assignment.primary_benchmark_id
        # NOT_APPLICABLE (for ETFs/funds/bonds) → preserve as UNMAPPED for UI compat
        if benchmark_id == "NOT_APPLICABLE":
            benchmark_id = "UNMAPPED"

        # Vehicle ID — direct lookup from registry (benchmark_assignment_engine doesn't expose this)
        vehicle_id = "UNMAPPED"
        lookup_geo = geography if geography in {"US", "INTERNATIONAL"} else "US"
        try:
            _bm, vehicle = resolve_category_mapping(
                geography=lookup_geo,
                market_cap_bucket=market_cap_bucket,
                industry_scope="ALL",
                benchmark_registry=benchmark_registry,
                vehicle_registry=vehicle_registry,
            )
            vehicle_id = vehicle.vehicle_id
        except ValueError:
            vehicle_id = "UNMAPPED"

        ess_score_text = str(signal_row.get("starmine_ess_text") or base_row.get("starmine_ess_text") or "").strip()
        # Phase 22D.2 WS-B: if the primary signal path yielded no ESS text
        # (symbol absent from snapshot or NON_STARMINE_ANALYST), fall back to
        # the most recent entry in ess_history_master.csv.
        if not ess_score_text:
            ess_score_text = ess_archive_by_symbol.get(symbol, "")
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
                security_type=raw_security_type,
                snapshot_date=snapshot_date,
                run_id=run_id,
                market_cap_bucket=market_cap_bucket,
                geography=geography,
                country=resolved_country,
                industry=sector_by_symbol.get(symbol, str(base_row.get("industry", "")).strip().upper() or "ALL"),
                sector=sector_by_symbol.get(symbol, str(base_row.get("sector", "")).strip().upper() or "ALL"),
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
                # Subtier fields injected below via classifier; placeholders here.
                analytical_market_cap_subtier="",
                classification_policy_id="",
                classification_snapshot_date="",
                # Phase 1 eligibility flags from security type policy
                replay_eligible=type_info.replay_eligible,
                scoring_eligible=type_info.scoring_eligible,
                allocation_eligible=type_info.allocation_eligible,
                # Phase 1 benchmark integrity fields
                benchmark_confidence=bm_assignment.benchmark_confidence,
                sector_benchmark_id=bm_assignment.sector_benchmark_id,
                classification_method=bm_assignment.classification_method,
            )
        )

    # --- inject dynamic analytical subtiers ---
    policy = load_subtier_policy(subtier_policy_path)
    row_dicts = [
        {
            "symbol": r.symbol,
            "market_cap_bucket": r.market_cap_bucket,
            "market_cap_raw_usd": str(base_raw_map.get(r.symbol, "")),
        }
        for r in analytical_rows
    ]
    enriched_dicts = classify_analytical_subtiers(row_dicts, policy, snapshot_date)
    subtier_by_symbol = {
        d["symbol"]: (
            d["analytical_market_cap_subtier"],
            d["classification_policy_id"],
            d["classification_snapshot_date"],
        )
        for d in enriched_dicts
    }

    final_rows: List[AnalyticalUniverseRow] = []
    for row in analytical_rows:
        sub, pid, csd = subtier_by_symbol.get(row.symbol, ("", "", ""))
        final_rows.append(
            AnalyticalUniverseRow(
                security_id=row.security_id,
                symbol=row.symbol,
                security_type=row.security_type,
                snapshot_date=row.snapshot_date,
                run_id=row.run_id,
                market_cap_bucket=row.market_cap_bucket,
                geography=row.geography,
                country=row.country,
                industry=row.industry,
                sector=row.sector,
                composite_score=row.composite_score,
                ess_score_text=row.ess_score_text,
                zacks_rating=row.zacks_rating,
                yahoo_score=row.yahoo_score,
                danelfin_score=row.danelfin_score,
                benchmark_id=row.benchmark_id,
                investable_vehicle_id=row.investable_vehicle_id,
                price_at_snapshot=row.price_at_snapshot,
                provider_lineage=row.provider_lineage,
                analytical_market_cap_subtier=sub,
                classification_policy_id=pid,
                classification_snapshot_date=csd,
                # Propagate Phase 1 eligibility and benchmark integrity fields unchanged
                replay_eligible=row.replay_eligible,
                scoring_eligible=row.scoring_eligible,
                allocation_eligible=row.allocation_eligible,
                benchmark_confidence=row.benchmark_confidence,
                sector_benchmark_id=row.sector_benchmark_id,
                classification_method=row.classification_method,
            )
        )

    return final_rows


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
                "analytical_market_cap_subtier": row.analytical_market_cap_subtier,
                "classification_policy_id": row.classification_policy_id,
                "classification_snapshot_date": row.classification_snapshot_date,
                "replay_eligible": row.replay_eligible,
                "scoring_eligible": row.scoring_eligible,
                "allocation_eligible": row.allocation_eligible,
                "benchmark_confidence": row.benchmark_confidence,
                "sector_benchmark_id": row.sector_benchmark_id,
                "classification_method": row.classification_method,
                "yahoo_abr_normalized": row.yahoo_abr_normalized,
                "composite_v2_yahoo": row.composite_v2_yahoo,
                "composite_version": row.composite_version,
                "score_generation_timestamp": row.score_generation_timestamp,
            }
        )

    paths.partition_dir.mkdir(parents=True, exist_ok=False)
    _write_csv_rows(paths.partition_output_path, ANALYTICAL_UNIVERSE_HEADERS, normalized_rows)
    _write_csv_rows(paths.current_output_path, ANALYTICAL_UNIVERSE_HEADERS, normalized_rows)
    return len(normalized_rows)
