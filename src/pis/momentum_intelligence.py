"""PIS Momentum Intelligence (reporting-only).

This module provides a transparent momentum analytics layer for operators.
It intentionally does not alter scoring, recommendation generation, ranking,
allocation, deployment, market-regime gating, or execution behavior.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from .momentum_price_history import (
    SECTOR_PARENT_ETF_MAP,
    inventory_current_price_coverage,
    inventory_sector_parent_coverage,
)


_HORIZON_WINDOWS: dict[str, int] = {
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "12M": 252,
}

_SHORT_HORIZONS = ("1W", "1M")
_INTERMEDIATE_HORIZONS = ("3M", "6M")
_LONG_HORIZONS = ("12M",)

_SECTOR_PROXY_FALLBACKS = dict(SECTOR_PARENT_ETF_MAP)

_MIN_INDUSTRY_CONSTITUENTS = 2
_MIN_INDUSTRY_PRICE_COVERAGE_PCT = 0.6

_EQUITY_LIKE_ASSET_TYPES = {
    "EQUITY",
    "EQUITIES",
    "STOCK",
    "COMMON STOCK",
    "COMMON_STOCK",
    "ADR",
}

_MARKET_FALLBACK_ASSET_TYPES = {
    "ETF",
    "FUND",
    "MUTUAL FUND",
    "MUTUAL_FUND",
}

_TAXONOMY_UNKNOWN_VALUES = {"", "UNKNOWN", "N/A", "NA", "NONE"}


@dataclass(frozen=True)
class MomentumSeries:
    symbol: str
    source: str
    as_of_date: str
    freshness_days: int | None
    points: list[tuple[str, float]]


@dataclass(frozen=True)
class MomentumEvaluationContext:
    repo_root: Path
    analysis_as_of: str
    universe: dict[str, dict[str, str]]
    security_type_map: dict[str, str]
    market_horizons: dict[str, dict[str, object]]
    security_series: dict[str, MomentumSeries]
    sector_proxy_series: dict[str, MomentumSeries]
    ess_series: dict[str, list[tuple[str, float]]]
    zacks_series: dict[str, list[tuple[str, float]]]
    danelfin_series: dict[str, list[tuple[str, float]]]
    yahoo_pt_series: dict[str, list[tuple[str, float]]]
    yahoo_abr_series: dict[str, list[tuple[str, float]]]
    fmp_consensus_series: dict[str, list[tuple[str, float]]]
    fmp_income_growth_series: dict[str, list[tuple[str, float]]]
    sector_members: dict[str, list[str]]
    industry_members: dict[str, list[str]]


@dataclass(frozen=True)
class AsOfBaseEvaluationContext:
    repo_root: Path
    as_of: str
    universe: dict[str, dict[str, str]]
    holdings_symbols_as_of: set[str]
    holding_asset_type_by_symbol: dict[str, str]
    market_series: MomentumSeries
    market_horizons: dict[str, dict[str, object]]
    ess_series: dict[str, list[tuple[str, float]]]
    zacks_series: dict[str, list[tuple[str, float]]]
    danelfin_series: dict[str, list[tuple[str, float]]]
    yahoo_pt_series: dict[str, list[tuple[str, float]]]
    yahoo_abr_series: dict[str, list[tuple[str, float]]]
    fmp_consensus_series: dict[str, list[tuple[str, float]]]
    fmp_income_growth_series: dict[str, list[tuple[str, float]]]


_AS_OF_BASE_CONTEXT_CACHE: dict[tuple[str, str], AsOfBaseEvaluationContext] = {}


def _to_float(value: object) -> float | None:
    try:
        text = str(value or "").strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _taxonomy_clean(value: object) -> str:
    return str(value or "").strip()


def _taxonomy_is_known(value: object) -> bool:
    v = _taxonomy_clean(value).upper()
    return v not in _TAXONOMY_UNKNOWN_VALUES


def _taxonomy_upper_or_unknown(value: object) -> str:
    v = _taxonomy_clean(value).upper()
    return v if v and v not in _TAXONOMY_UNKNOWN_VALUES else "UNKNOWN"


def _load_security_metadata_taxonomy(repo_root: Path) -> dict[str, dict[str, str]]:
    rows = _read_csv_rows(repo_root / "data/signals/security_metadata/latest_security_metadata.csv")
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        out[symbol] = {
            "sector": _taxonomy_clean(row.get("sector", "")),
            "industry": _taxonomy_clean(row.get("industry", "")),
        }
    return out


def _load_security_type_taxonomy(repo_root: Path) -> dict[str, str]:
    """Load the best available security_type classification for reporting use.

    This is classification context only. It does not supply price, benchmark,
    provider, or fundamental evidence.
    """
    out: dict[str, str] = {}

    snapshot_date, holdings = _load_holdings(repo_root)
    _ = snapshot_date
    for row in holdings:
        symbol = str(row.get("symbol", "")).strip().upper()
        asset_type = _taxonomy_upper_or_unknown(row.get("asset_type", ""))
        if symbol and asset_type != "UNKNOWN":
            out[symbol] = asset_type

    current_price_rows = _read_csv_rows(repo_root / "data/current/security_prices.csv")
    for row in current_price_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        security_type = _taxonomy_upper_or_unknown(row.get("security_type", ""))
        if symbol and security_type != "UNKNOWN" and symbol not in out:
            out[symbol] = security_type

    price_root = repo_root / "data/history/prices"
    if price_root.exists():
        for price_file in price_root.glob("symbol=*/prices.csv"):
            symbol = price_file.parent.name.replace("symbol=", "").strip().upper()
            if not symbol or symbol in out:
                continue
            for row in _read_csv_rows(price_file):
                security_type = _taxonomy_upper_or_unknown(row.get("security_type", ""))
                if security_type != "UNKNOWN":
                    out[symbol] = security_type
                    break

    return out


def _load_security_type_taxonomy_for_symbols(repo_root: Path, symbols: set[str]) -> dict[str, str]:
    requested = {str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()}
    if not requested:
        return {}

    out: dict[str, str] = {}
    _snapshot_date, holdings = _load_holdings(repo_root)
    for row in holdings:
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol not in requested:
            continue
        asset_type = _taxonomy_upper_or_unknown(row.get("asset_type", ""))
        if asset_type != "UNKNOWN":
            out[symbol] = asset_type

    current_price_rows = _read_csv_rows(repo_root / "data/current/security_prices.csv")
    for row in current_price_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol not in requested or symbol in out:
            continue
        security_type = _taxonomy_upper_or_unknown(row.get("security_type", ""))
        if security_type != "UNKNOWN":
            out[symbol] = security_type

    for symbol in sorted(requested - set(out.keys())):
        price_file = repo_root / f"data/history/prices/symbol={symbol}/prices.csv"
        if not price_file.exists():
            continue
        for row in _read_csv_rows(price_file):
            security_type = _taxonomy_upper_or_unknown(row.get("security_type", ""))
            if security_type != "UNKNOWN":
                out[symbol] = security_type
                break
    return out


def _resolve_momentum_security_metadata(
    symbol: str,
    *,
    universe: dict[str, dict[str, str]],
    security_type_map: dict[str, str],
    provenance_label: str,
) -> dict[str, object]:
    symbol_u = str(symbol or "").strip().upper()
    meta = universe.get(symbol_u, {})
    sector = str(meta.get("sector", "UNKNOWN")).strip() or "UNKNOWN"
    industry = str(meta.get("industry", "UNAVAILABLE")).strip() or "UNAVAILABLE"
    sector_source = str(meta.get("sector_source", "UNAVAILABLE")).strip() or "UNAVAILABLE"
    industry_source = str(meta.get("industry_source", "UNAVAILABLE")).strip() or "UNAVAILABLE"
    industry_granularity = str(meta.get("industry_granularity", "UNAVAILABLE")).strip() or "UNAVAILABLE"
    metadata_source = sector_source if sector_source != "UNAVAILABLE" else industry_source
    metadata_provenance = provenance_label if metadata_source != "UNAVAILABLE" else "UNAVAILABLE"
    security_type = security_type_map.get(symbol_u, "UNAVAILABLE")
    if not _taxonomy_is_known(security_type):
        security_type = "UNAVAILABLE"
    if metadata_source == "UNAVAILABLE" and security_type != "UNAVAILABLE":
        metadata_source = "PRICE_HISTORY"
    return {
        "symbol": symbol_u,
        "security_type": security_type,
        "sector": sector,
        "industry": industry,
        "metadata_source": metadata_source,
        "metadata_provenance": metadata_provenance,
        "sector_source": sector_source,
        "industry_source": industry_source,
        "industry_granularity": industry_granularity,
    }


def _industry_granularity_and_value(
    *,
    sector_value: str,
    candidates: list[tuple[str, str, str]],
) -> tuple[str, str, str]:
    """Return (industry, source, granularity).

    candidates: [(industry_value, source_label, paired_sector_value), ...]
    """
    sector_u = _taxonomy_upper_or_unknown(sector_value)

    # Prefer first distinct industry below sector.
    for industry_value, source, paired_sector_value in candidates:
        ind = _taxonomy_upper_or_unknown(industry_value)
        paired_sector = _taxonomy_upper_or_unknown(paired_sector_value)
        if ind in {"UNKNOWN", "ALL"}:
            continue
        if ind != paired_sector and ind != sector_u:
            return ind, source, "DISTINCT_INDUSTRY"

    # If only sector-level labels are present, do not treat as a distinct industry.
    for industry_value, source, _paired_sector_value in candidates:
        ind = _taxonomy_upper_or_unknown(industry_value)
        if ind == sector_u or ind == "ALL":
            return "UNAVAILABLE", source, "SECTOR_ONLY"

    return "UNAVAILABLE", "UNAVAILABLE", "UNAVAILABLE"


def _normalize_date(text: object) -> str:
    raw = str(text or "").strip()
    if len(raw) >= 10:
        return raw[:10]
    return ""


def _freshness_days(as_of_date: str) -> int | None:
    if not as_of_date:
        return None
    try:
        as_of = date.fromisoformat(as_of_date)
    except ValueError:
        return None
    return (_today_utc() - as_of).days


def _series_confidence(points: int, required_points: int) -> str:
    if points <= 1:
        return "UNAVAILABLE"
    if points >= required_points:
        return "HIGH"
    if points >= max(2, int(required_points * 0.6)):
        return "MEDIUM"
    return "LOW"


def _build_horizon_payload(series: MomentumSeries) -> dict[str, dict[str, object]]:
    payload: dict[str, dict[str, object]] = {}
    if not series.points:
        for horizon, required in _HORIZON_WINDOWS.items():
            payload[horizon] = {
                "state": "UNAVAILABLE",
                "return_pct": None,
                "source": series.source,
                "as_of_date": series.as_of_date,
                "history_available": 0,
                "freshness_days": series.freshness_days,
                "confidence": "UNAVAILABLE",
                "required_points": required + 1,
            }
        return payload

    closes = [p[1] for p in series.points]
    for horizon, required in _HORIZON_WINDOWS.items():
        required_points = required + 1
        if len(closes) < required_points:
            payload[horizon] = {
                "state": "UNAVAILABLE",
                "return_pct": None,
                "source": series.source,
                "as_of_date": series.as_of_date,
                "history_available": len(closes),
                "freshness_days": series.freshness_days,
                "confidence": _series_confidence(len(closes), required_points),
                "required_points": required_points,
            }
            continue

        end_price = closes[-1]
        start_price = closes[-required_points]
        if start_price <= 0:
            payload[horizon] = {
                "state": "UNAVAILABLE",
                "return_pct": None,
                "source": series.source,
                "as_of_date": series.as_of_date,
                "history_available": len(closes),
                "freshness_days": series.freshness_days,
                "confidence": "UNAVAILABLE",
                "required_points": required_points,
            }
            continue

        ret = ((end_price / start_price) - 1.0) * 100.0
        if ret >= 8.0:
            state = "STRONG"
        elif ret >= 2.0:
            state = "POSITIVE"
        elif ret <= -8.0:
            state = "WEAK"
        elif ret <= -2.0:
            state = "NEGATIVE"
        else:
            state = "NEUTRAL"

        payload[horizon] = {
            "state": state,
            "return_pct": round(ret, 4),
            "source": series.source,
            "as_of_date": series.as_of_date,
            "history_available": len(closes),
            "freshness_days": series.freshness_days,
            "confidence": _series_confidence(len(closes), required_points),
            "required_points": required_points,
        }

    return payload


def _classify_absolute_momentum_state(horizons: dict[str, dict[str, object]]) -> str:
    score = 0.0
    weight_map = {"1W": 0.5, "1M": 1.0, "3M": 1.5, "6M": 1.5, "12M": 1.0}
    usable = 0
    for horizon, weight in weight_map.items():
        ret = horizons.get(horizon, {}).get("return_pct")
        if not isinstance(ret, (int, float)):
            continue
        usable += 1
        if ret > 0:
            score += weight
        elif ret < 0:
            score -= weight

    if usable == 0:
        return "UNAVAILABLE"
    if score >= 3.0:
        return "STRONG"
    if score >= 1.0:
        return "IMPROVING"
    if score <= -3.0:
        return "WEAK"
    if score <= -1.0:
        return "WEAKENING"
    return "NEUTRAL"


def _compute_relative_horizons(
    child_horizons: dict[str, dict[str, object]],
    parent_horizons: dict[str, dict[str, object]],
    *,
    source_label: str,
) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for horizon in _HORIZON_WINDOWS:
        c = child_horizons.get(horizon, {})
        p = parent_horizons.get(horizon, {})
        c_ret = c.get("return_pct")
        p_ret = p.get("return_pct")
        if not isinstance(c_ret, (int, float)) or not isinstance(p_ret, (int, float)):
            out[horizon] = {
                "state": "UNAVAILABLE",
                "relative_return_pct": None,
                "source": source_label,
                "as_of_date": c.get("as_of_date") or p.get("as_of_date"),
                "history_available": min(
                    int(c.get("history_available") or 0),
                    int(p.get("history_available") or 0),
                ),
                "freshness_days": c.get("freshness_days") if c.get("freshness_days") is not None else p.get("freshness_days"),
                "confidence": "UNAVAILABLE",
            }
            continue

        rel = float(c_ret) - float(p_ret)
        if rel >= 3.0:
            state = "OUTPERFORMING"
        elif rel >= 1.0:
            state = "SLIGHTLY_OUTPERFORMING"
        elif rel <= -3.0:
            state = "UNDERPERFORMING"
        elif rel <= -1.0:
            state = "SLIGHTLY_UNDERPERFORMING"
        else:
            state = "INLINE"

        out[horizon] = {
            "state": state,
            "relative_return_pct": round(rel, 4),
            "source": source_label,
            "as_of_date": c.get("as_of_date") or p.get("as_of_date"),
            "history_available": min(
                int(c.get("history_available") or 0),
                int(p.get("history_available") or 0),
            ),
            "freshness_days": c.get("freshness_days") if c.get("freshness_days") is not None else p.get("freshness_days"),
            "confidence": "HIGH" if c.get("confidence") == "HIGH" and p.get("confidence") == "HIGH" else "MEDIUM",
        }
    return out


def _pick_relative_value(relative_horizons: dict[str, dict[str, object]]) -> float | None:
    for horizon in ("3M", "1M", "1W"):
        value = relative_horizons.get(horizon, {}).get("relative_return_pct")
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _has_relative_evidence(relative_horizons: dict[str, dict[str, object]]) -> bool:
    for horizon in _HORIZON_WINDOWS:
        value = relative_horizons.get(horizon, {}).get("relative_return_pct")
        if isinstance(value, (int, float)):
            return True
    return False


def _relative_strength_level(relative_horizons: dict[str, dict[str, object]]) -> str:
    value = _pick_relative_value(relative_horizons)
    if value is None:
        return "UNAVAILABLE"
    if value >= 3.0:
        return "HIGH"
    if value >= 1.0:
        return "MEDIUM"
    if value <= -3.0:
        return "LOW"
    if value <= -1.0:
        return "WEAK"
    return "NEUTRAL"


def _relative_momentum_change(relative_horizons: dict[str, dict[str, object]]) -> str:
    short_val = relative_horizons.get("1M", {}).get("relative_return_pct")
    if not isinstance(short_val, (int, float)):
        short_val = relative_horizons.get("1W", {}).get("relative_return_pct")
    intermediate_val = relative_horizons.get("3M", {}).get("relative_return_pct")
    if not isinstance(short_val, (int, float)) or not isinstance(intermediate_val, (int, float)):
        return "UNAVAILABLE"
    delta = float(short_val) - float(intermediate_val)
    if delta >= 1.5:
        return "ACCELERATING"
    if delta <= -1.5:
        return "FADING"
    return "STABLE"


def _classify_security_leadership_state(
    *,
    sector_vs_market_level: str,
    industry_vs_sector_level: str,
    security_vs_industry_level: str,
    security_vs_industry_change: str,
) -> str:
    levels = {
        sector_vs_market_level,
        industry_vs_sector_level,
        security_vs_industry_level,
    }
    if "UNAVAILABLE" in levels or security_vs_industry_change == "UNAVAILABLE":
        return "UNAVAILABLE"

    parents_strong = sector_vs_market_level in {"HIGH", "MEDIUM"} and industry_vs_sector_level in {"HIGH", "MEDIUM"}
    parent_weak = sector_vs_market_level in {"LOW", "WEAK"} and industry_vs_sector_level in {"LOW", "WEAK"}
    security_strong = security_vs_industry_level in {"HIGH", "MEDIUM"}
    security_weak = security_vs_industry_level in {"LOW", "WEAK"}

    if parents_strong and security_strong and security_vs_industry_change in {"ACCELERATING", "STABLE"}:
        return "MULTI_LEVEL_CONFIRMED_LEADERSHIP"
    if parents_strong and security_weak:
        return "SECURITY_LAGGARD_IN_STRONG_GROUP"
    if parent_weak and security_strong:
        return "SECURITY_RESILIENT_IN_WEAK_GROUP"
    if sector_vs_market_level in {"HIGH", "MEDIUM"} and industry_vs_sector_level in {"LOW", "WEAK"}:
        return "SECTOR_LED"
    if industry_vs_sector_level in {"HIGH", "MEDIUM"} and security_vs_industry_level in {"LOW", "WEAK", "NEUTRAL"}:
        return "INDUSTRY_LED"
    if security_strong and industry_vs_sector_level in {"NEUTRAL", "LOW", "WEAK"}:
        return "SECURITY_LED"
    if security_weak and security_vs_industry_change == "FADING":
        return "MULTI_LEVEL_DETERIORATION"
    if security_vs_industry_level == "NEUTRAL":
        return "GROUP_PARTICIPANT"
    return "MIXED"


def _classify_fundamental_momentum(signal_deltas: list[float]) -> str:
    if not signal_deltas:
        return "UNAVAILABLE"
    improving = sum(1 for x in signal_deltas if x > 0)
    deteriorating = sum(1 for x in signal_deltas if x < 0)
    if improving - deteriorating >= 2:
        return "IMPROVING"
    if deteriorating - improving >= 2:
        return "DETERIORATING"
    return "STABLE"


def _classify_confirmation_state(price_state: str, fundamental_state: str) -> str:
    if price_state == "UNAVAILABLE" or fundamental_state == "UNAVAILABLE":
        return "UNAVAILABLE"

    price_positive = price_state in {"STRONG", "IMPROVING", "POSITIVE"}
    price_negative = price_state in {"WEAK", "WEAKENING", "NEGATIVE"}

    if price_positive and fundamental_state == "IMPROVING":
        return "CONFIRMED_MOMENTUM"
    if price_positive and fundamental_state == "DETERIORATING":
        return "MOMENTUM_DIVERGENCE"
    if price_positive and fundamental_state == "STABLE":
        return "PRICE_ONLY_MOMENTUM"
    if price_negative and fundamental_state == "IMPROVING":
        return "FUNDAMENTAL_ONLY_IMPROVEMENT"
    if price_negative and fundamental_state == "DETERIORATING":
        return "BROAD_DOWNTREND"
    return "UNAVAILABLE"


def _classify_breadth_state(
    positive_share_short: float | None,
    outperform_share: float | None,
    improving_fund_share: float | None,
    top5_contribution_share: float | None,
    constituent_count: int,
) -> str:
    if constituent_count <= 0:
        return "UNAVAILABLE"
    if positive_share_short is None or outperform_share is None:
        return "UNAVAILABLE"

    if positive_share_short < 0.45 or outperform_share < 0.45:
        return "DETERIORATING"
    if positive_share_short >= 0.65 and outperform_share >= 0.60 and (improving_fund_share is None or improving_fund_share >= 0.5):
        if top5_contribution_share is not None and top5_contribution_share >= 0.65:
            return "HEALTHY_CONCENTRATED"
        return "BROAD"
    if top5_contribution_share is not None and top5_contribution_share >= 0.75:
        return "NARROW"
    return "HEALTHY_CONCENTRATED"


def _classify_extension_state(
    *,
    distance_ma20_pct: float | None,
    distance_52w_high_pct: float | None,
    recent_acceleration_pct: float | None,
    volatility_20d_pct: float | None,
) -> str:
    if (
        distance_ma20_pct is None
        and distance_52w_high_pct is None
        and recent_acceleration_pct is None
        and volatility_20d_pct is None
    ):
        return "UNAVAILABLE"

    elevated = False
    extended = False
    if distance_ma20_pct is not None:
        if distance_ma20_pct >= 0.15:
            extended = True
        elif distance_ma20_pct >= 0.08:
            elevated = True
    if distance_52w_high_pct is not None and distance_52w_high_pct >= -0.01:
        elevated = True
    if recent_acceleration_pct is not None and recent_acceleration_pct >= 4.0:
        elevated = True
    if volatility_20d_pct is not None and volatility_20d_pct >= 0.04:
        elevated = True
    if elevated and volatility_20d_pct is not None and volatility_20d_pct >= 0.055:
        extended = True

    if extended:
        return "EXTENDED"
    if elevated:
        return "ELEVATED"
    return "NORMAL"


def _load_benchmark_series(repo_root: Path) -> MomentumSeries:
    rows = _read_csv_rows(repo_root / "data/current/benchmark_returns.csv")
    points: list[tuple[str, float]] = []
    for row in rows:
        symbol = str(row.get("symbol_or_index", "")).strip().upper()
        if symbol not in {"^GSPC", "SPY"}:
            continue
        d = _normalize_date(row.get("date", ""))
        price = _to_float(row.get("adjusted_close"))
        if d and price and price > 0:
            points.append((d, float(price)))
    points.sort(key=lambda x: x[0])
    as_of = points[-1][0] if points else ""
    return MomentumSeries(
        symbol="^GSPC",
        source="data/current/benchmark_returns.csv",
        as_of_date=as_of,
        freshness_days=_freshness_days(as_of),
        points=points,
    )


def _load_sector_proxy_series(
    repo_root: Path,
    security_series: dict[str, MomentumSeries] | None = None,
) -> dict[str, MomentumSeries]:
    rows = _read_csv_rows(repo_root / "data/current/market_regime_proxy_price_history.csv")
    by_symbol: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        d = _normalize_date(row.get("date", ""))
        price = _to_float(row.get("price"))
        if not symbol or not d or price is None or price <= 0:
            continue
        by_symbol.setdefault(symbol, []).append((d, float(price)))

    out: dict[str, MomentumSeries] = {}
    for symbol, points in by_symbol.items():
        points.sort(key=lambda x: x[0])
        as_of = points[-1][0] if points else ""
        out[symbol] = MomentumSeries(
            symbol=symbol,
            source="data/current/market_regime_proxy_price_history.csv",
            as_of_date=as_of,
            freshness_days=_freshness_days(as_of),
            points=points,
        )

    # Coverage recovery path: use persisted ETF/security history as parent
    # sector series where dedicated proxy feed does not contain the symbol.
    if security_series:
        for parent_symbol in _SECTOR_PROXY_FALLBACKS.values():
            if parent_symbol in out:
                continue
            sec = security_series.get(parent_symbol)
            if sec and sec.points:
                out[parent_symbol] = sec
    return out


def _load_security_price_series(repo_root: Path) -> dict[str, MomentumSeries]:
    out: dict[str, MomentumSeries] = {}
    root = repo_root / "data/history/prices"
    if not root.exists():
        return out
    for price_file in root.glob("symbol=*/prices.csv"):
        symbol = price_file.parent.name.replace("symbol=", "").strip().upper()
        rows = _read_csv_rows(price_file)
        points: list[tuple[str, float]] = []
        for row in rows:
            d = _normalize_date(row.get("date", ""))
            price = _to_float(row.get("adjusted_close"))
            if d and price and price > 0:
                points.append((d, float(price)))
        points.sort(key=lambda x: x[0])
        as_of = points[-1][0] if points else ""
        out[symbol] = MomentumSeries(
            symbol=symbol,
            source=f"data/history/prices/symbol={symbol}/prices.csv",
            as_of_date=as_of,
            freshness_days=_freshness_days(as_of),
            points=points,
        )
    return out


def _load_security_price_series_for_symbols(repo_root: Path, symbols: set[str]) -> dict[str, MomentumSeries]:
    requested = {str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()}
    out: dict[str, MomentumSeries] = {}
    if not requested:
        return out

    for symbol in sorted(requested):
        price_file = repo_root / f"data/history/prices/symbol={symbol}/prices.csv"
        if not price_file.exists():
            continue
        rows = _read_csv_rows(price_file)
        points: list[tuple[str, float]] = []
        for row in rows:
            d = _normalize_date(row.get("date", ""))
            price = _to_float(row.get("adjusted_close"))
            if d and price and price > 0:
                points.append((d, float(price)))
        points.sort(key=lambda x: x[0])
        as_of = points[-1][0] if points else ""
        out[symbol] = MomentumSeries(
            symbol=symbol,
            source=f"data/history/prices/symbol={symbol}/prices.csv",
            as_of_date=as_of,
            freshness_days=_freshness_days(as_of),
            points=points,
        )
    return out


def _load_universe_metadata(repo_root: Path) -> dict[str, dict[str, str]]:
    """Load security metadata with source and granularity provenance.

    Sector precedence:
      1. portfolio_ingestion latest holdings.csv
      2. analytical_universe.csv
      3. security_metadata/latest_security_metadata.csv

    Industry precedence for DISTINCT industry:
      1. portfolio_ingestion latest holdings.csv (if distinct from sector)
      2. analytical_universe.csv (if distinct from sector)
      3. security_metadata/latest_security_metadata.csv (if distinct from sector)

    If only sector-level industry labels exist (industry == sector or industry == ALL),
    industry is set to UNAVAILABLE with INDUSTRY_GRANULARITY=SECTOR_ONLY.
    """
    portfolio_map: dict[str, dict[str, str]] = {}
    universe_map: dict[str, dict[str, str]] = {}
    security_meta_map = _load_security_metadata_taxonomy(repo_root)

    # First: portfolio ingestion for current holdings metadata.
    portfolio_runs_dir = repo_root / "data/portfolio_ingestion/analysis_runs"
    if portfolio_runs_dir.exists():
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
                    portfolio_map[symbol] = {
                        "sector": _taxonomy_clean(row.get("sector", "")),
                        "industry": _taxonomy_clean(row.get("industry", "")),
                        "geography": _taxonomy_clean(row.get("geography", "")),
                        "market_cap_bucket": _taxonomy_clean(row.get("market_cap_bucket", "")),
                    }

    # Second: analytical universe for broader symbols.
    universe_rows = _read_csv_rows(repo_root / "data/current/analytical_universe.csv")
    for row in universe_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        universe_map[symbol] = {
            "sector": _taxonomy_clean(row.get("sector", "")),
            "industry": _taxonomy_clean(row.get("industry", "")),
            "geography": _taxonomy_clean(row.get("geography", "")),
            "market_cap_bucket": _taxonomy_clean(row.get("market_cap_bucket", "")),
        }

    out: dict[str, dict[str, str]] = {}
    all_symbols = set(portfolio_map) | set(universe_map) | set(security_meta_map)
    for symbol in all_symbols:
        p = portfolio_map.get(symbol, {})
        u = universe_map.get(symbol, {})
        s = security_meta_map.get(symbol, {})

        sector = "UNKNOWN"
        sector_source = "UNAVAILABLE"
        if _taxonomy_is_known(p.get("sector")):
            sector = _taxonomy_upper_or_unknown(p.get("sector"))
            sector_source = "PORTFOLIO_ANALYSIS_HOLDINGS"
        elif _taxonomy_is_known(u.get("sector")):
            sector = _taxonomy_upper_or_unknown(u.get("sector"))
            sector_source = "ANALYTICAL_UNIVERSE"
        elif _taxonomy_is_known(s.get("sector")):
            sector = _taxonomy_upper_or_unknown(s.get("sector"))
            sector_source = "SECURITY_METADATA"

        industry, industry_source, granularity = _industry_granularity_and_value(
            sector_value=sector,
            candidates=[
                (_taxonomy_clean(p.get("industry", "")), "PORTFOLIO_ANALYSIS_HOLDINGS", _taxonomy_clean(p.get("sector", ""))),
                (_taxonomy_clean(u.get("industry", "")), "ANALYTICAL_UNIVERSE", _taxonomy_clean(u.get("sector", ""))),
                (_taxonomy_clean(s.get("industry", "")), "SECURITY_METADATA", _taxonomy_clean(s.get("sector", ""))),
            ],
        )

        out[symbol] = {
            "sector": sector,
            "industry": industry,
            "industry_granularity": granularity,
            "sector_source": sector_source,
            "industry_source": industry_source,
            "geography": _taxonomy_clean(p.get("geography") or u.get("geography") or ""),
            "market_cap_bucket": _taxonomy_clean(p.get("market_cap_bucket") or u.get("market_cap_bucket") or ""),
        }

    return out


def _latest_positions_file(repo_root: Path) -> tuple[str, Path | None]:
    rows = _read_csv_rows(repo_root / "data/history/pis/pis_snapshot_index.csv")
    if not rows:
        return "", None
    best = max(rows, key=lambda r: str(r.get("snapshot_date", "")))
    snapshot_date = str(best.get("snapshot_date", ""))
    positions_path = str(best.get("positions_path", "")).strip()
    if not positions_path:
        return snapshot_date, None
    p = Path(positions_path)
    if not p.is_absolute():
        p = repo_root / p
    return snapshot_date, p


def _load_holdings(repo_root: Path) -> tuple[str, list[dict[str, object]]]:
    snapshot_date, path = _latest_positions_file(repo_root)
    if path is None or not path.exists():
        return snapshot_date, []
    out: list[dict[str, object]] = []
    for row in _read_csv_rows(path):
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in {"CASH", "PENDING"}:
            continue
        weight = _to_float(row.get("percent_of_account"))
        market_value = _to_float(row.get("market_value"))
        asset_type = str(row.get("security_type", "")).strip().upper()
        out.append(
            {
                "symbol": symbol,
                "portfolio_weight": round(float(weight or 0.0), 4),
                "market_value": round(float(market_value or 0.0), 4),
                "asset_type": asset_type,
            }
        )
    out.sort(key=lambda x: float(x.get("market_value", 0.0)), reverse=True)
    return snapshot_date, out


def _load_holdings_as_of(repo_root: Path, as_of_date: str) -> tuple[str, list[dict[str, object]]]:
    rows = _read_csv_rows(repo_root / "data/history/pis/pis_snapshot_index.csv")
    if not rows:
        return "", []
    as_of = str(as_of_date or "")[:10]
    eligible = [row for row in rows if str(row.get("snapshot_date", "")) <= as_of] if as_of else rows
    if not eligible:
        return "", []
    best = max(eligible, key=lambda row: str(row.get("snapshot_date", "")))
    snapshot_date = str(best.get("snapshot_date", ""))
    positions_path = str(best.get("positions_path", "")).strip()
    if not positions_path:
        return snapshot_date, []
    p = Path(positions_path)
    if not p.is_absolute():
        p = repo_root / p
    if not p.exists():
        return snapshot_date, []

    out: list[dict[str, object]] = []
    for row in _read_csv_rows(p):
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in {"CASH", "PENDING"}:
            continue
        weight = _to_float(row.get("percent_of_account"))
        market_value = _to_float(row.get("market_value"))
        asset_type = str(row.get("security_type", "")).strip().upper()
        out.append(
            {
                "symbol": symbol,
                "portfolio_weight": round(float(weight or 0.0), 4),
                "market_value": round(float(market_value or 0.0), 4),
                "asset_type": asset_type,
            }
        )
    out.sort(key=lambda x: float(x.get("market_value", 0.0)), reverse=True)
    return snapshot_date, out


def _load_daily_symbol_metric_series(
    repo_root: Path,
    pattern: str,
    date_parser,
    value_extractor,
) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    for file_path in sorted(repo_root.glob(pattern)):
        file_date = _normalize_date(date_parser(file_path))
        for row in _read_csv_rows(file_path):
            row_date = _normalize_date(row.get("sourced_date", ""))
            d = row_date or file_date
            if not d:
                continue
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            v = value_extractor(row)
            if v is None:
                continue
            out.setdefault(symbol, []).append((d, float(v)))

    for series in out.values():
        series.sort(key=lambda x: x[0])
    return out


def _load_ess_series(repo_root: Path) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    root = repo_root / "data/history/signals"
    if not root.exists():
        return out
    for signal_file in sorted(root.glob("snapshot_date=*/run_id=*/signal_snapshots.csv")):
        for row in _read_csv_rows(signal_file):
            symbol = str(row.get("symbol", "")).strip().upper()
            d = _normalize_date(row.get("snapshot_date", ""))
            score = _to_float(row.get("starmine_ess_numeric"))
            if not symbol or not d or score is None:
                continue
            out.setdefault(symbol, []).append((d, float(score)))
    for series in out.values():
        series.sort(key=lambda x: x[0])
    return out


def _series_deltas(series: list[tuple[str, float]]) -> list[float]:
    if len(series) < 2:
        return []
    return [round(series[i][1] - series[i - 1][1], 6) for i in range(1, len(series))]


def _fundamental_snapshot_for_symbol(
    symbol: str,
    *,
    ess_series: dict[str, list[tuple[str, float]]],
    zacks_series: dict[str, list[tuple[str, float]]],
    danelfin_series: dict[str, list[tuple[str, float]]],
    yahoo_pt_series: dict[str, list[tuple[str, float]]],
    yahoo_abr_series: dict[str, list[tuple[str, float]]],
    fmp_consensus_series: dict[str, list[tuple[str, float]]],
    fmp_income_growth_series: dict[str, list[tuple[str, float]]],
) -> dict[str, object]:
    deltas: list[float] = []
    detail: dict[str, object] = {}

    for key, series_map in {
        "ESS_CHANGE": ess_series,
        "ZACKS_CHANGE": zacks_series,
        "DANELFIN_CHANGE": danelfin_series,
        "PRICE_TARGET_REVISIONS": yahoo_pt_series,
        "ANALYST_CONSENSUS_CHANGE": yahoo_abr_series,
        "FMP_CONSENSUS_CHANGE": fmp_consensus_series,
        "REVENUE_REVISIONS": fmp_income_growth_series,
    }.items():
        series = series_map.get(symbol, [])
        ds = _series_deltas(series)
        if ds:
            deltas.extend(ds)
        detail[key] = {
            "points": len(series),
            "latest": round(series[-1][1], 6) if series else None,
            "delta_count": len(ds),
            "latest_delta": round(ds[-1], 6) if ds else None,
            "as_of_date": series[-1][0] if series else None,
        }

    state = _classify_fundamental_momentum(deltas)
    return {
        "state": state,
        "signals_used": len(deltas),
        "details": detail,
    }


def _pct_change_from_series(series: MomentumSeries, periods: int) -> float | None:
    if len(series.points) < periods + 1:
        return None
    start = series.points[-periods - 1][1]
    end = series.points[-1][1]
    if start <= 0:
        return None
    return ((end / start) - 1.0) * 100.0


def _daily_return_volatility(series: MomentumSeries, lookback: int) -> float | None:
    if len(series.points) < lookback + 1:
        return None
    closes = [p[1] for p in series.points[-(lookback + 1):]]
    rets: list[float] = []
    for i in range(1, len(closes)):
        if closes[i - 1] <= 0:
            continue
        rets.append((closes[i] / closes[i - 1]) - 1.0)
    if len(rets) < 2:
        return None
    return float(pstdev(rets))


def _extension_metrics(series: MomentumSeries) -> dict[str, float | None]:
    closes = [p[1] for p in series.points]
    if not closes:
        return {
            "distance_from_ma20_pct": None,
            "distance_from_52w_high_pct": None,
            "recent_acceleration_pct": None,
            "volatility_20d_pct": None,
        }

    last = closes[-1]
    ma20 = mean(closes[-20:]) if len(closes) >= 20 else None
    high252 = max(closes[-252:]) if len(closes) >= 2 else None
    r1m = _pct_change_from_series(series, 21)
    r3m = _pct_change_from_series(series, 63)
    accel = None
    if r1m is not None and r3m is not None:
        accel = r1m - (r3m / 3.0)

    return {
        "distance_from_ma20_pct": round(((last / ma20) - 1.0), 6) if ma20 else None,
        "distance_from_52w_high_pct": round(((last / high252) - 1.0), 6) if high252 else None,
        "recent_acceleration_pct": round(accel, 6) if accel is not None else None,
        "volatility_20d_pct": round(float(_daily_return_volatility(series, 20)), 6) if _daily_return_volatility(series, 20) is not None else None,
    }


def _group_series_from_constituents(
    symbols: list[str],
    series_map: dict[str, MomentumSeries],
    *,
    group_key: str,
) -> MomentumSeries | None:
    points_by_date: dict[str, list[float]] = {}
    for symbol in symbols:
        series = series_map.get(symbol)
        if not series:
            continue
        for d, price in series.points:
            points_by_date.setdefault(d, []).append(price)
    if not points_by_date:
        return None

    # Equal-weight synthetic index.
    synthetic_points: list[tuple[str, float]] = []
    for d in sorted(points_by_date.keys()):
        values = points_by_date[d]
        if not values:
            continue
        synthetic_points.append((d, float(mean(values))))

    if not synthetic_points:
        return None
    as_of = synthetic_points[-1][0]
    return MomentumSeries(
        symbol=group_key,
        source="derived_equal_weight_constituents",
        as_of_date=as_of,
        freshness_days=_freshness_days(as_of),
        points=synthetic_points,
    )


def _filter_series_to_as_of(series: MomentumSeries | None, as_of_date: str) -> MomentumSeries | None:
    if series is None:
        return None
    as_of = str(as_of_date or "")[:10]
    if not as_of:
        return series
    filtered = [(d, price) for d, price in series.points if d <= as_of]
    if not filtered:
        return MomentumSeries(
            symbol=series.symbol,
            source=series.source,
            as_of_date=as_of,
            freshness_days=_freshness_days(as_of),
            points=[],
        )
    last_selected_date = filtered[-1][0]
    return MomentumSeries(
        symbol=series.symbol,
        source=series.source,
        as_of_date=last_selected_date,
        freshness_days=_freshness_days(last_selected_date),
        points=filtered,
    )


def _filter_metric_series_to_as_of(
    series: list[tuple[str, float]],
    as_of_date: str,
) -> list[tuple[str, float]]:
    as_of = str(as_of_date or "")[:10]
    if not as_of:
        return list(series)
    return [(d, value) for d, value in series if d <= as_of]


def _filter_metric_map_to_as_of(
    series_map: dict[str, list[tuple[str, float]]],
    as_of_date: str,
) -> dict[str, list[tuple[str, float]]]:
    as_of = str(as_of_date or "")[:10]
    if not as_of:
        return dict(series_map)
    return {
        symbol: _filter_metric_series_to_as_of(series, as_of)
        for symbol, series in series_map.items()
    }


def _get_as_of_base_context(repo_root: Path, as_of_date: str) -> AsOfBaseEvaluationContext:
    as_of = str(as_of_date or "")[:10]
    root_key = str(repo_root.resolve())
    key = (root_key, as_of)
    cached = _AS_OF_BASE_CONTEXT_CACHE.get(key)
    if cached is not None:
        return cached

    universe = _load_universe_metadata(repo_root)
    _holdings_snapshot_date, holdings_as_of = _load_holdings_as_of(repo_root, as_of)
    holdings_symbols_as_of = {str(item.get("symbol", "")).upper() for item in holdings_as_of if str(item.get("symbol", "")).strip()}
    holding_asset_type_by_symbol = {
        str(item.get("symbol", "")).upper(): str(item.get("asset_type", "")).upper()
        for item in holdings_as_of
    }

    market_series = _filter_series_to_as_of(_load_benchmark_series(repo_root), as_of) or MomentumSeries(
        symbol="^GSPC",
        source="UNAVAILABLE",
        as_of_date=as_of,
        freshness_days=_freshness_days(as_of),
        points=[],
    )
    market_horizons = _build_horizon_payload(market_series)

    ess_series = _filter_metric_map_to_as_of(_load_ess_series(repo_root), as_of)
    zacks_series = _filter_metric_map_to_as_of(
        _load_daily_symbol_metric_series(repo_root, "data/signals/zacks/*_zacks.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("zacks_score"))),
        as_of,
    )
    danelfin_series = _filter_metric_map_to_as_of(
        _load_daily_symbol_metric_series(repo_root, "data/signals/danelfin/*_danelfin*.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("danelfin_score"))),
        as_of,
    )
    yahoo_pt_series = _filter_metric_map_to_as_of(
        _load_daily_symbol_metric_series(repo_root, "data/signals/yahoo/*_yahoo_supplemental.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("price_target"))),
        as_of,
    )
    yahoo_abr_series = _filter_metric_map_to_as_of(
        _load_daily_symbol_metric_series(repo_root, "data/signals/yahoo/*_yahoo_supplemental.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("abr"))),
        as_of,
    )
    fmp_consensus_series = _filter_metric_map_to_as_of(
        _load_daily_symbol_metric_series(repo_root, "data/signals/fmp/daily/fmp_grades_consensus_*.csv", lambda p: p.name.rsplit("_", 1)[-1].replace(".csv", ""), lambda row: _to_float(row.get("net_buy_score"))),
        as_of,
    )
    fmp_income_growth_series = _filter_metric_map_to_as_of(
        _load_daily_symbol_metric_series(repo_root, "data/signals/fmp/latest/latest_fmp_income_growth.csv", lambda _p: _today_utc().isoformat(), lambda row: _to_float(row.get("revenue_growth_q1_yoy"))),
        as_of,
    )

    context = AsOfBaseEvaluationContext(
        repo_root=repo_root,
        as_of=as_of,
        universe=universe,
        holdings_symbols_as_of=holdings_symbols_as_of,
        holding_asset_type_by_symbol=holding_asset_type_by_symbol,
        market_series=market_series,
        market_horizons=market_horizons,
        ess_series=ess_series,
        zacks_series=zacks_series,
        danelfin_series=danelfin_series,
        yahoo_pt_series=yahoo_pt_series,
        yahoo_abr_series=yahoo_abr_series,
        fmp_consensus_series=fmp_consensus_series,
        fmp_income_growth_series=fmp_income_growth_series,
    )
    _AS_OF_BASE_CONTEXT_CACHE[key] = context
    return context


def _as_of_absolute_state_from_price_points(series: MomentumSeries) -> str:
    points = series.points
    if len(points) < 2:
        return "UNAVAILABLE"

    start_price = points[0][1]
    end_price = points[-1][1]
    if start_price <= 0 or end_price <= 0:
        return "UNAVAILABLE"

    ret = ((end_price / start_price) - 1.0) * 100.0
    if ret >= 8.0:
        return "STRONG"
    if ret >= 2.0:
        return "POSITIVE"
    if ret >= 0.0:
        return "IMPROVING"
    if ret <= -8.0:
        return "WEAK"
    if ret <= -2.0:
        return "NEGATIVE"
    if ret < 0.0:
        return "NEUTRAL"
    return "NEUTRAL"


def _history_status_for_points(points: list[tuple[str, float]]) -> str:
    if not points:
        return "UNAVAILABLE"
    if len(points) < 50:
        return "INSUFFICIENT_50"
    if len(points) < 200:
        return "INSUFFICIENT_200"
    if len(points) < 220:
        return "INSUFFICIENT_220"
    return "AVAILABLE"


def _currentness_state_for_series(series: MomentumSeries, *, points: list[tuple[str, float]] | None = None) -> str:
    filtered_points = list(points) if points is not None else list(series.points)
    if not filtered_points:
        return "MISSING"
    freshness_days = series.freshness_days
    if freshness_days is None:
        return "PARTIAL" if len(filtered_points) >= 5 else "MISSING"
    if freshness_days <= 5:
        return "CURRENT"
    return "STALE"


def build_trend_structure_context(
    series: MomentumSeries,
    *,
    as_of_date: str | None = None,
) -> dict[str, object]:
    """Compute a reporting-only 50-day / 200-day trend structure context.

    This is intentionally additive and non-decisioning. It summarizes the relationship
    between the latest price and the short/long simple moving averages, along with a
    20-trading-day change in each moving average, and preserves a clear "insufficient
    history" state rather than fabricating a trend signal.
    """
    effective_as_of = (as_of_date or series.as_of_date or "")[:10]
    points = [(d, price) for d, price in series.points if not effective_as_of or d <= effective_as_of]
    if not points:
        return {
            "as_of_date": effective_as_of,
            "history_status": "UNAVAILABLE",
            "currentness_state": "MISSING",
            "freshness_status": "MISSING",
            "coverage_status": "MISSING",
            "latest_price_date": None,
            "latest_price": None,
            "sma50": None,
            "sma200": None,
            "price_vs_sma50_pct": 0.0,
            "price_vs_sma200_pct": 0.0,
            "sma50_change_20d_pct": 0.0,
            "sma200_change_20d_pct": 0.0,
            "provenance": series.source,
            "reporting_only": True,
        }

    latest_date, latest_price = points[-1]
    latest_price_float = float(latest_price)

    def _sma_window(window: int) -> float | None:
        if len(points) < window:
            return None
        values = [p for _, p in points[-window:]]
        if not values:
            return None
        return float(sum(values) / len(values))

    def _pct_change(current: float | None, previous: float | None) -> float:
        if current is None or previous is None or previous <= 0:
            return 0.0
        return float(((current / previous) - 1.0) * 100.0)

    sma50 = _sma_window(50)
    sma200 = _sma_window(200)
    history_status = _history_status_for_points(points)
    currentness_state = _currentness_state_for_series(series, points=points)

    sma50_prior = None
    if len(points) >= 70:
        sma50_prior = float(sum(p for _, p in points[-70:-20]) / 50.0)

    sma200_prior = None
    if len(points) >= 220:
        sma200_prior = float(sum(p for _, p in points[-220:-20]) / 200.0)

    price_vs_sma50_pct = _pct_change(latest_price_float, sma50)
    price_vs_sma200_pct = _pct_change(latest_price_float, sma200)
    sma50_change_20d_pct = _pct_change(sma50, sma50_prior)
    sma200_change_20d_pct = _pct_change(sma200, sma200_prior)

    if sma50 is None:
        price_vs_sma50_pct = 0.0
    if sma200 is None:
        price_vs_sma200_pct = 0.0
    if sma50_prior is None:
        sma50_change_20d_pct = 0.0
    if sma200_prior is None:
        sma200_change_20d_pct = 0.0

    return {
        "as_of_date": effective_as_of,
        "history_status": history_status,
        "currentness_state": currentness_state,
        "freshness_status": currentness_state,
        "coverage_status": currentness_state,
        "latest_price_date": latest_date,
        "latest_price": round(latest_price_float, 6),
        "sma50": round(sma50, 6) if sma50 is not None else None,
        "sma200": round(sma200, 6) if sma200 is not None else None,
        "price_vs_sma50_pct": round(price_vs_sma50_pct, 6),
        "price_vs_sma200_pct": round(price_vs_sma200_pct, 6),
        "sma50_change_20d_pct": round(sma50_change_20d_pct, 6),
        "sma200_change_20d_pct": round(sma200_change_20d_pct, 6),
        "provenance": series.source,
        "reporting_only": True,
    }


def evaluate_momentum_as_of(
    symbol: str,
    as_of_date: str,
    *,
    repo_root: str | Path = ".",
) -> dict[str, object]:
    """Evaluate a symbol using only data observed on or before the requested as-of date.

    This is the historical reporting-only evaluator: it filters price, benchmark,
    sector-parent, industry-parent, and provider/fundamental evidence to <= as_of_date
    and deliberately never reuses current runtime summary as historical evidence.
    """

    root = Path(repo_root)
    sym = str(symbol or "").strip().upper()
    as_of = str(as_of_date or "")[:10]

    base_context = _get_as_of_base_context(root, as_of)
    universe = base_context.universe

    metadata_probe = universe.get(sym, {})
    inferred_sector = str(metadata_probe.get("sector", "UNKNOWN")).strip() or "UNKNOWN"
    inferred_industry = str(metadata_probe.get("industry", "UNAVAILABLE")).strip() or "UNAVAILABLE"

    context_symbols: set[str] = {sym}
    if sym in base_context.holdings_symbols_as_of:
        context_symbols.update(base_context.holdings_symbols_as_of)
    else:
        for symbol_name, meta in universe.items():
            sector = str(meta.get("sector", "")).strip()
            industry = str(meta.get("industry", "")).strip()
            if sector == inferred_sector or (inferred_industry != "UNAVAILABLE" and industry == inferred_industry):
                context_symbols.add(str(symbol_name).strip().upper())
    context_symbols.update(_SECTOR_PROXY_FALLBACKS.values())

    security_type_map = _load_security_type_taxonomy_for_symbols(root, context_symbols | {sym})

    security_series = _load_security_price_series_for_symbols(root, context_symbols)
    filtered_security_series: dict[str, MomentumSeries] = {
        name: (_filter_series_to_as_of(series, as_of) or MomentumSeries(symbol=name, source="UNAVAILABLE", as_of_date=as_of, freshness_days=_freshness_days(as_of), points=[]))
        for name, series in security_series.items()
    }
    raw_series = _filter_series_to_as_of(security_series.get(sym), as_of)
    raw_points = [d for d, _ in (raw_series.points if raw_series else [])]

    sec_series = raw_series or MomentumSeries(
        symbol=sym,
        source="UNAVAILABLE",
        as_of_date=as_of,
        freshness_days=_freshness_days(as_of),
        points=[],
    )

    sector_name = str(universe.get(sym, {}).get("sector", "UNKNOWN")).strip() or "UNKNOWN"
    industry_name = str(universe.get(sym, {}).get("industry", "UNAVAILABLE")).strip() or "UNAVAILABLE"

    # For holdings symbols on a known as-of portfolio snapshot, align parent
    # construction semantics with canonical live momentum (holdings cohort).
    if sym in set(base_context.holdings_symbols_as_of):
        peer_symbols = list(base_context.holdings_symbols_as_of)
    else:
        peer_symbols = list(context_symbols)

    metadata = _resolve_momentum_security_metadata(
        sym,
        universe=universe,
        security_type_map=security_type_map,
        provenance_label="CURRENT_TAXONOMY_FALLBACK",
    )
    sector_name = str(metadata.get("sector", "UNKNOWN")).strip() or "UNKNOWN"
    industry_name = str(metadata.get("industry", "UNAVAILABLE")).strip() or "UNAVAILABLE"

    sector_proxy = _SECTOR_PROXY_FALLBACKS.get(sector_name.upper())
    sector_proxy_series = _load_sector_proxy_series(root, security_series=security_series)
    filtered_sector_proxy: dict[str, MomentumSeries] = {}
    for sec_sym, series in sector_proxy_series.items():
        filtered = _filter_series_to_as_of(series, as_of)
        if filtered is not None:
            filtered_sector_proxy[sec_sym] = filtered

    sector_series = filtered_sector_proxy.get(sector_proxy) if sector_proxy else None
    if sector_series is None:
        candidates = [s for s in peer_symbols if str(universe.get(s, {}).get("sector", "")).strip() == sector_name]
        if candidates:
            sector_series = _group_series_from_constituents(
                [symbol_name for symbol_name in candidates if symbol_name in filtered_security_series],
                filtered_security_series,
                group_key=f"SECTOR::{sector_name.upper()}",
            )
    if sector_series is None:
        sector_series = MomentumSeries(symbol=f"SECTOR::{sector_name.upper()}", source="UNAVAILABLE", as_of_date=as_of, freshness_days=_freshness_days(as_of), points=[])

    industry_series = None
    if industry_name != "UNAVAILABLE":
        industry_candidates = [s for s in peer_symbols if str(universe.get(s, {}).get("industry", "")).strip() == industry_name]
        with_series = [item for item in industry_candidates if item in filtered_security_series and bool(filtered_security_series[item].points)]
        coverage_pct = (len(with_series) / len(industry_candidates)) if industry_candidates else 0.0
        constituent_asset_types = {base_context.holding_asset_type_by_symbol.get(item, "") for item in industry_candidates}
        has_equity_like_constituents = any(asset_type in _EQUITY_LIKE_ASSET_TYPES for asset_type in constituent_asset_types)
        parent_applicable = has_equity_like_constituents if industry_candidates else False
        parent_available = (
            parent_applicable
            and len(industry_candidates) >= _MIN_INDUSTRY_CONSTITUENTS
            and len(with_series) >= _MIN_INDUSTRY_CONSTITUENTS
            and coverage_pct >= _MIN_INDUSTRY_PRICE_COVERAGE_PCT
        )
        if parent_available:
            industry_series = _group_series_from_constituents(
                with_series,
                filtered_security_series,
                group_key=f"INDUSTRY::{industry_name.upper()}",
            )
    if industry_series is None:
        industry_series = MomentumSeries(symbol=f"INDUSTRY::{industry_name.upper()}", source="UNAVAILABLE", as_of_date=as_of, freshness_days=_freshness_days(as_of), points=[])

    sec_horizons = _build_horizon_payload(sec_series)
    sector_horizons = _build_horizon_payload(_filter_series_to_as_of(sector_series, as_of) or sector_series)
    industry_horizons = _build_horizon_payload(_filter_series_to_as_of(industry_series, as_of) or industry_series)

    abs_state = _classify_absolute_momentum_state(sec_horizons)
    sec_vs_market = _compute_relative_horizons(sec_horizons, base_context.market_horizons, source_label=f"{sym} vs market")
    sec_vs_sector = _compute_relative_horizons(sec_horizons, sector_horizons, source_label=f"{sym} vs sector")
    sec_vs_industry = _compute_relative_horizons(sec_horizons, industry_horizons, source_label=f"{sym} vs industry")
    industry_rel_level = _relative_strength_level(sec_vs_industry)
    industry_rel_change = _relative_momentum_change(sec_vs_industry)
    market_rel_level = _relative_strength_level(sec_vs_market)
    market_rel_change = _relative_momentum_change(sec_vs_market)
    fallback_allowed = str(metadata.get("security_type", "UNAVAILABLE")).strip().upper() in _MARKET_FALLBACK_ASSET_TYPES
    market_fallback_used = fallback_allowed and industry_name == "UNAVAILABLE" and market_rel_level != "UNAVAILABLE"
    rel_level = market_rel_level if market_fallback_used else industry_rel_level
    rel_change = market_rel_change if market_fallback_used else industry_rel_change

    fallback_used = abs_state == "UNAVAILABLE" and len(sec_series.points) >= 2
    if fallback_used:
        abs_state = _as_of_absolute_state_from_price_points(sec_series)

    sector_parent_used = bool(any(value.get("state") != "UNAVAILABLE" or value.get("relative_return_pct") is not None for value in sec_vs_sector.values()))
    industry_parent_used = bool(any(value.get("state") != "UNAVAILABLE" or value.get("relative_return_pct") is not None for value in sec_vs_industry.values()))

    filtered_ess = base_context.ess_series.get(sym, [])
    filtered_zacks = base_context.zacks_series.get(sym, [])
    filtered_danelfin = base_context.danelfin_series.get(sym, [])
    filtered_yahoo_pt = base_context.yahoo_pt_series.get(sym, [])
    filtered_yahoo_abr = base_context.yahoo_abr_series.get(sym, [])
    filtered_fmp_consensus = base_context.fmp_consensus_series.get(sym, [])
    filtered_fmp_growth = base_context.fmp_income_growth_series.get(sym, [])

    fundamentals = _fundamental_snapshot_for_symbol(
        sym,
        ess_series={sym: filtered_ess},
        zacks_series={sym: filtered_zacks},
        danelfin_series={sym: filtered_danelfin},
        yahoo_pt_series={sym: filtered_yahoo_pt},
        yahoo_abr_series={sym: filtered_yahoo_abr},
        fmp_consensus_series={sym: filtered_fmp_consensus},
        fmp_income_growth_series={sym: filtered_fmp_growth},
    )
    confirmation = _classify_confirmation_state(abs_state, str(fundamentals.get("state", "UNAVAILABLE")))
    extension_metrics = _extension_metrics(sec_series)
    extension_state = _classify_extension_state(
        distance_ma20_pct=extension_metrics["distance_from_ma20_pct"],
        distance_52w_high_pct=extension_metrics["distance_from_52w_high_pct"],
        recent_acceleration_pct=extension_metrics["recent_acceleration_pct"],
        volatility_20d_pct=extension_metrics["volatility_20d_pct"],
    )

    return {
        "symbol": sym,
        "as_of_date": as_of,
        "provenance": "HISTORICAL_AS_OF",
        "security_type": metadata.get("security_type", "UNAVAILABLE"),
        "sector": sector_name,
        "industry": industry_name,
        "metadata_source": metadata.get("metadata_source", "UNAVAILABLE"),
        "metadata_provenance": metadata.get("metadata_provenance", "UNAVAILABLE"),
        "market_fallback_used": market_fallback_used,
        "sector_parent_used": sector_parent_used,
        "industry_parent_used": industry_parent_used,
        "price_provenance": "HISTORICAL_PRICE_HISTORY_AS_OF",
        "absolute_state": abs_state,
        "vs_market": sec_vs_market,
        "vs_sector": sec_vs_sector,
        "vs_industry": sec_vs_industry,
        "relative_strength_level": rel_level,
        "relative_momentum_change": rel_change,
        "fundamental_momentum": fundamentals.get("state", "UNAVAILABLE"),
        "confirmation_state": confirmation,
        "extension_state": extension_state,
        "price_points_available": len(raw_points),
        "market_points_available": len([d for d, _ in (base_context.market_series.points if base_context.market_series else []) if d <= as_of]),
        "raw_price_points": raw_points,
        "raw_market_points": [d for d, _ in (base_context.market_series.points if base_context.market_series else []) if d <= as_of],
        "source_constraints": {
            "price_observations_filtered_to_as_of": True,
            "benchmark_observations_filtered_to_as_of": True,
            "sector_parent_observations_filtered_to_as_of": True,
            "industry_parent_observations_filtered_to_as_of": True,
            "provider_fundamental_evidence_filtered_to_as_of": True,
            "current_runtime_summary_not_reused": True,
            "historical_short_history_fallback_used": fallback_used,
        },
    }


def _change_label(previous: str | None, current: str | None) -> str:
    if not current:
        return "UNAVAILABLE"
    if not previous:
        return "RECONSTRUCTED_BASELINE"
    if previous == current:
        return "UNCHANGED"
    return f"{previous}->{current}"


def _historical_change_proxy(relative_horizons: dict[str, dict[str, object]]) -> dict[str, str]:
    short_val = relative_horizons.get("1W", {}).get("relative_return_pct")
    monthly_val = relative_horizons.get("1M", {}).get("relative_return_pct")
    if not isinstance(short_val, (int, float)):
        return {
            "change_since_prior": "UNAVAILABLE",
            "change_7d": "UNAVAILABLE",
            "change_30d": "UNAVAILABLE",
            "method": "RECONSTRUCTED_DERIVED",
        }

    if short_val >= 1.0:
        since_prior = "IMPROVING"
    elif short_val <= -1.0:
        since_prior = "WEAKENING"
    else:
        since_prior = "STABLE"

    change_30d = "UNAVAILABLE"
    if isinstance(monthly_val, (int, float)):
        if monthly_val >= 1.0:
            change_30d = "IMPROVING"
        elif monthly_val <= -1.0:
            change_30d = "WEAKENING"
        else:
            change_30d = "STABLE"

    return {
        "change_since_prior": since_prior,
        "change_7d": since_prior,
        "change_30d": change_30d,
        "method": "RECONSTRUCTED_DERIVED",
    }


def _build_methodology_payload() -> dict[str, object]:
    return {
        "momentum_is_not_recommendation": True,
        "governance_statement": "Momentum alone is insufficient for an investment recommendation.",
        "when_momentum_matters": [
            "When relative leadership confirms an improving fundamental thesis.",
            "When sector/industry participation breadth supports price leadership.",
        ],
        "when_to_ignore_momentum": [
            "When absolute strength is narrow and unsupported by breadth.",
            "When leadership is fading while fundamentals deteriorate.",
        ],
        "confirmation_logic": {
            "preferred_state": "improving fundamentals + improving relative momentum + healthy participation + acceptable extension",
            "caution_state": "strong price momentum + weakening fundamentals",
            "potential_early_state": "improving fundamentals + relative momentum accelerating + absolute leadership not yet established",
            "risk_state": "relative momentum fading + fundamentals deteriorating",
        },
        "thresholds": {
            "relative_level_high_pct": 3.0,
            "relative_level_medium_pct": 1.0,
            "relative_change_accelerating_delta_pct": 1.5,
            "extension_ma20_elevated_pct": 0.08,
            "extension_ma20_extended_pct": 0.15,
        },
        "horizon_windows": {
            "SHORT": ["1W", "1M"],
            "INTERMEDIATE": ["3M", "6M"],
            "LONG": ["12M"],
        },
    }


def _momentum_snapshot_index_path(repo_root: Path) -> Path:
    return repo_root / "data/history/pis/momentum_snapshot_index.csv"


def _momentum_snapshot_root(repo_root: Path) -> Path:
    return repo_root / "data/history/momentum"


def _read_snapshot_index(repo_root: Path) -> list[dict[str, str]]:
    path = _momentum_snapshot_index_path(repo_root)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_snapshot_index(repo_root: Path, rows: list[dict[str, object]]) -> None:
    path = _momentum_snapshot_index_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "snapshot_id",
        "as_of_date",
        "generated_at",
        "portfolio_reference",
        "artifact_path",
        "portfolio_value_if_available",
        "holdings_count",
        "market_state",
        "source_provenance",
    ]
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, path)


def _snapshot_payload_key(summary: dict[str, object]) -> str:
    rows = summary.get("portfolio_momentum_map", {}).get("holdings", [])
    hold = []
    for row in rows:
        hold.append(
            {
                "symbol": row.get("symbol"),
                "portfolio_weight": row.get("portfolio_weight"),
                "absolute_state": row.get("absolute_security_momentum", {}).get("state"),
                "confirmation_state": row.get("confirmation_state"),
                "relative_strength_level": row.get("relative_strength_level"),
                "relative_momentum_change": row.get("relative_momentum_change"),
                "fundamental_momentum": row.get("fundamental_momentum", {}).get("state"),
                "extension_state": row.get("extension_state"),
            }
        )
    payload = {
        "snapshot_date": summary.get("snapshot_date"),
        "market_state": summary.get("market_momentum", {}).get("market_absolute_momentum", {}).get("state"),
        "holdings": sorted(hold, key=lambda item: str(item.get("symbol", ""))),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def materialize_momentum_snapshot(*, repo_root: str | Path = ".", portfolio_reference: str = "current-runtime") -> dict[str, object]:
    root = Path(repo_root)
    summary = pis_momentum_summary(repo_root=root)
    as_of_date = str(summary.get("snapshot_date") or "").strip() or _today_utc().isoformat()
    payload = _snapshot_payload_key(summary)
    snapshot_id = f"MOM-{as_of_date}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12]}"
    index_path = _momentum_snapshot_index_path(root)
    index_rows = _read_snapshot_index(root)
    for row in index_rows:
        if row.get("snapshot_id") == snapshot_id:
            artifact_path = Path(str(row.get("artifact_path", "")))
            if not artifact_path.is_absolute():
                artifact_path = root / artifact_path
            if artifact_path.exists():
                with artifact_path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
    artifact_dir = _momentum_snapshot_root(root) / f"snapshot_date={as_of_date}" / f"snapshot_id={snapshot_id}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "momentum_snapshot.json"
    snapshot = {
        "snapshot_id": snapshot_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of_date": as_of_date,
        "portfolio_snapshot_reference": portfolio_reference,
        "portfolio_value_if_available": summary.get("total_value"),
        "holdings_count": len(summary.get("portfolio_momentum_map", {}).get("holdings", [])),
        "market_state": summary.get("market_momentum", {}).get("market_absolute_momentum", {}).get("state"),
        "coverage": summary.get("coverage", {}),
        "sector_rotation": summary.get("sector_rotation", []),
        "industry_rotation": summary.get("industry_rotation", []),
        "portfolio_momentum_rows": summary.get("portfolio_momentum_map", {}).get("holdings", []),
        "methodology": summary.get("methodology", {}),
        "source_provenance": {
            "source": "CURRENT_RUNTIME",
            "portfolio_reference": portfolio_reference,
            "generation_mode": "reporting_only",
            "base_summary": "pis_momentum_summary",
        },
        "artifact_path": str(artifact_path),
    }
    tmp_path = artifact_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
    os.replace(tmp_path, artifact_path)
    index_rows.append(
        {
            "snapshot_id": snapshot_id,
            "as_of_date": as_of_date,
            "generated_at": snapshot["generated_at"],
            "portfolio_reference": portfolio_reference,
            "artifact_path": str(artifact_path),
            "portfolio_value_if_available": str(summary.get("total_value", "")),
            "holdings_count": str(len(summary.get("portfolio_momentum_map", {}).get("holdings", []))),
            "market_state": str(summary.get("market_momentum", {}).get("market_absolute_momentum", {}).get("state", "")),
            "source_provenance": "CURRENT_RUNTIME",
        }
    )
    _write_snapshot_index(root, index_rows)
    return snapshot


def pis_momentum_snapshot_history(*, repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    rows = _read_snapshot_index(root)
    if not rows:
        return {
            "snapshot_count": 0,
            "earliest_snapshot": None,
            "latest_snapshot": None,
            "previous_snapshot": None,
            "snapshots": [],
        }
    ordered = sorted(rows, key=lambda row: (str(row.get("as_of_date", "")), str(row.get("generated_at", ""))))
    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) > 1 else None
    return {
        "snapshot_count": len(ordered),
        "earliest_snapshot": ordered[0],
        "latest_snapshot": latest,
        "previous_snapshot": previous,
        "snapshots": ordered,
    }


def pis_momentum_compare(*, repo_root: str | Path = ".") -> dict[str, object]:
    history = pis_momentum_snapshot_history(repo_root=repo_root)
    latest = history.get("latest_snapshot")
    prior = history.get("previous_snapshot")
    if not latest or not prior:
        return {
            "direction": "UNAVAILABLE",
            "current_snapshot": latest.get("snapshot_id") if latest else None,
            "prior_snapshot": prior.get("snapshot_id") if prior else None,
            "elapsed_days": None,
            "coverage_comparability": "INSUFFICIENT_OBSERVED_HISTORY",
            "positive_transition_weight": 0.0,
            "negative_transition_weight": 0.0,
            "mixed_or_unchanged_weight": 0.0,
            "unavailable_comparison_weight": 0.0,
            "top_positive_drivers": [],
            "top_negative_drivers": [],
        }
    current_path = Path(str(latest.get("artifact_path", "")))
    prior_path = Path(str(prior.get("artifact_path", "")))
    if not current_path.is_absolute():
        current_path = Path(repo_root) / current_path
    if not prior_path.is_absolute():
        prior_path = Path(repo_root) / prior_path
    if not current_path.exists() or not prior_path.exists():
        return {
            "direction": "UNAVAILABLE",
            "current_snapshot": latest.get("snapshot_id"),
            "prior_snapshot": prior.get("snapshot_id"),
            "elapsed_days": None,
            "coverage_comparability": "OBSERVED_ARTIFACT_MISSING",
            "positive_transition_weight": 0.0,
            "negative_transition_weight": 0.0,
            "mixed_or_unchanged_weight": 0.0,
            "unavailable_comparison_weight": 0.0,
            "top_positive_drivers": [],
            "top_negative_drivers": [],
        }
    with current_path.open("r", encoding="utf-8") as handle:
        current = json.load(handle)
    with prior_path.open("r", encoding="utf-8") as handle:
        prior_snapshot = json.load(handle)
    current_rows = {str(row.get("symbol", "")): row for row in current.get("portfolio_momentum_rows", []) if str(row.get("symbol", ""))}
    prior_rows = {str(row.get("symbol", "")): row for row in prior_snapshot.get("portfolio_momentum_rows", []) if str(row.get("symbol", ""))}
    positive = []
    negative = []
    mixed = []
    unavailable = []
    for symbol in sorted(set(current_rows) | set(prior_rows)):
        c = current_rows.get(symbol)
        p = prior_rows.get(symbol)
        c_state = str((c or {}).get("confirmation_state") or "UNAVAILABLE")
        p_state = str((p or {}).get("confirmation_state") or "UNAVAILABLE")
        c_weight = float((c or {}).get("portfolio_weight") or 0.0)
        p_weight = float((p or {}).get("portfolio_weight") or 0.0)
        weight = max(c_weight, p_weight)
        if c_state == "UNAVAILABLE" or p_state == "UNAVAILABLE":
            unavailable.append((symbol, weight))
            continue
        if c_state in {"CONFIRMED_MOMENTUM", "PRICE_ONLY_MOMENTUM"} and p_state in {"UNAVAILABLE", "MOMENTUM_DIVERGENCE", "BROAD_DOWNTREND"}:
            positive.append((symbol, weight))
        elif c_state in {"UNAVAILABLE", "MOMENTUM_DIVERGENCE", "BROAD_DOWNTREND"} and p_state in {"CONFIRMED_MOMENTUM", "PRICE_ONLY_MOMENTUM"}:
            negative.append((symbol, weight))
        else:
            mixed.append((symbol, weight))

    positive_weight = sum(w for _, w in positive)
    negative_weight = sum(w for _, w in negative)
    mixed_weight = sum(w for _, w in mixed)
    unavailable_weight = sum(w for _, w in unavailable)
    direction = "UNAVAILABLE"
    if max(positive_weight, negative_weight, mixed_weight, unavailable_weight) == 0:
        direction = "UNAVAILABLE"
    elif positive_weight > negative_weight and positive_weight > max(mixed_weight, unavailable_weight):
        direction = "IMPROVING"
    elif negative_weight > positive_weight and negative_weight > max(mixed_weight, unavailable_weight):
        direction = "DETERIORATING"
    elif mixed_weight > max(positive_weight, negative_weight, unavailable_weight):
        direction = "MIXED"
    elif unavailable_weight > max(positive_weight, negative_weight, mixed_weight):
        direction = "UNAVAILABLE"
    else:
        direction = "STABLE"

    return {
        "direction": direction,
        "current_snapshot": latest.get("snapshot_id"),
        "prior_snapshot": prior.get("snapshot_id"),
        "elapsed_days": None,
        "coverage_comparability": "OBSERVED_SNAPSHOT_PAIR" if len({latest.get("snapshot_id"), prior.get("snapshot_id")}) == 2 else "INSUFFICIENT_OBSERVED_HISTORY",
        "positive_transition_weight": round(positive_weight, 2),
        "negative_transition_weight": round(negative_weight, 2),
        "mixed_or_unchanged_weight": round(mixed_weight, 2),
        "unavailable_comparison_weight": round(unavailable_weight, 2),
        "top_positive_drivers": [symbol for symbol, _ in sorted(positive, key=lambda item: item[1], reverse=True)[:5]],
        "top_negative_drivers": [symbol for symbol, _ in sorted(negative, key=lambda item: item[1], reverse=True)[:5]],
    }


def _build_symbol_evaluation_record(
    symbol: str,
    *,
    repo_root: Path,
    universe: dict[str, dict[str, str]],
    security_type_map: dict[str, str],
    market_horizons: dict[str, dict[str, object]],
    security_series: dict[str, MomentumSeries],
    sector_proxy_series: dict[str, MomentumSeries],
    ess_series: dict[str, list[tuple[str, float]]],
    zacks_series: dict[str, list[tuple[str, float]]],
    danelfin_series: dict[str, list[tuple[str, float]]],
    yahoo_pt_series: dict[str, list[tuple[str, float]]],
    yahoo_abr_series: dict[str, list[tuple[str, float]]],
    fmp_consensus_series: dict[str, list[tuple[str, float]]],
    fmp_income_growth_series: dict[str, list[tuple[str, float]]],
    sector_members: dict[str, list[str]] | None = None,
    industry_members: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    symbol = str(symbol).strip().upper()
    metadata = _resolve_momentum_security_metadata(
        symbol,
        universe=universe,
        security_type_map=security_type_map,
        provenance_label="CURRENT_TAXONOMY",
    )
    sector_name = str(metadata.get("sector", "UNKNOWN")).strip() or "UNKNOWN"
    industry_name = str(metadata.get("industry", "UNAVAILABLE")).strip() or "UNAVAILABLE"
    sector_proxy = _SECTOR_PROXY_FALLBACKS.get(sector_name.upper())
    sector_series = sector_proxy_series.get(sector_proxy) if sector_proxy else None
    if sector_series is None:
        if sector_members and sector_name in sector_members:
            sector_candidates = list(sector_members.get(sector_name, []))
        else:
            sector_candidates = [s for s, m in universe.items() if str(m.get("sector", "")).strip() == sector_name]
        if sector_candidates:
            sector_series = _group_series_from_constituents(
                [s for s in sector_candidates if s in security_series],
                security_series,
                group_key=f"SECTOR::{sector_name.upper()}",
            )
    if sector_series is None:
        sector_horizons = _build_horizon_payload(MomentumSeries(symbol=f"SECTOR::{sector_name.upper()}", source="unavailable", as_of_date="", freshness_days=None, points=[]))
    else:
        sector_horizons = _build_horizon_payload(sector_series)

    if industry_name != "UNAVAILABLE":
        if industry_members and industry_name in industry_members:
            industry_candidates = list(industry_members.get(industry_name, []))
        else:
            industry_candidates = [s for s, m in universe.items() if str(m.get("industry", "")).strip() == industry_name]
    else:
        industry_candidates = []
    if industry_candidates:
        industry_series = _group_series_from_constituents([s for s in industry_candidates if s in security_series], security_series, group_key=f"INDUSTRY::{industry_name.upper()}")
    else:
        industry_series = None
    if industry_series is None:
        industry_horizons = _build_horizon_payload(MomentumSeries(symbol=f"INDUSTRY::{industry_name.upper()}", source="unavailable", as_of_date="", freshness_days=None, points=[]))
    else:
        industry_horizons = _build_horizon_payload(industry_series)

    sec_series = security_series.get(symbol)
    sec_horizons = _build_horizon_payload(sec_series if sec_series is not None else MomentumSeries(symbol=symbol, source="unavailable", as_of_date="", freshness_days=None, points=[]))
    abs_state = _classify_absolute_momentum_state(sec_horizons)
    sec_vs_market = _compute_relative_horizons(sec_horizons, market_horizons, source_label=f"{symbol} vs market")
    sec_vs_sector = _compute_relative_horizons(sec_horizons, sector_horizons, source_label=f"{symbol} vs sector")
    sec_vs_industry = _compute_relative_horizons(sec_horizons, industry_horizons, source_label=f"{symbol} vs industry")
    industry_rel_level = _relative_strength_level(sec_vs_industry)
    industry_rel_change = _relative_momentum_change(sec_vs_industry)
    market_rel_level = _relative_strength_level(sec_vs_market)
    market_rel_change = _relative_momentum_change(sec_vs_market)
    fallback_allowed = str(metadata.get("security_type", "UNAVAILABLE")).strip().upper() in _MARKET_FALLBACK_ASSET_TYPES
    market_fallback_used = fallback_allowed and industry_name == "UNAVAILABLE" and market_rel_level != "UNAVAILABLE"
    rel_level = market_rel_level if market_fallback_used else industry_rel_level
    rel_change = market_rel_change if market_fallback_used else industry_rel_change

    fundamentals = _fundamental_snapshot_for_symbol(
        symbol,
        ess_series=ess_series,
        zacks_series=zacks_series,
        danelfin_series=danelfin_series,
        yahoo_pt_series=yahoo_pt_series,
        yahoo_abr_series=yahoo_abr_series,
        fmp_consensus_series=fmp_consensus_series,
        fmp_income_growth_series=fmp_income_growth_series,
    )
    confirmation = _classify_confirmation_state(abs_state, str(fundamentals.get("state", "UNAVAILABLE")))
    extension_metrics = _extension_metrics(sec_series if sec_series is not None else MomentumSeries(symbol=symbol, source="unavailable", as_of_date="", freshness_days=None, points=[]))
    extension_state = _classify_extension_state(
        distance_ma20_pct=extension_metrics["distance_from_ma20_pct"],
        distance_52w_high_pct=extension_metrics["distance_from_52w_high_pct"],
        recent_acceleration_pct=extension_metrics["recent_acceleration_pct"],
        volatility_20d_pct=extension_metrics["volatility_20d_pct"],
    )
    sector_class = "UNAVAILABLE"
    if sector_horizons and any(isinstance(v.get("return_pct"), (int, float)) for v in sector_horizons.values()):
        sector_level = _relative_strength_level(_compute_relative_horizons(sector_horizons, market_horizons, source_label=f"{sector_name} vs market"))
        sector_change = _relative_momentum_change(_compute_relative_horizons(sector_horizons, market_horizons, source_label=f"{sector_name} vs market"))
        if sector_level == "HIGH" and sector_change == "ACCELERATING":
            sector_class = "LEADING"
        elif sector_level in {"HIGH", "MEDIUM"} and sector_change == "STABLE":
            sector_class = "IMPROVING"
        elif sector_level in {"LOW", "WEAK"} and sector_change in {"FADING", "STABLE"}:
            sector_class = "LAGGING"
        elif sector_level == "UNAVAILABLE":
            sector_class = "UNAVAILABLE"
        else:
            sector_class = "NEUTRAL"

    industry_class = "UNAVAILABLE"
    if industry_horizons and any(isinstance(v.get("return_pct"), (int, float)) for v in industry_horizons.values()):
        industry_level = _relative_strength_level(_compute_relative_horizons(industry_horizons, market_horizons, source_label=f"{industry_name} vs market"))
        industry_change = _relative_momentum_change(_compute_relative_horizons(industry_horizons, market_horizons, source_label=f"{industry_name} vs market"))
        if industry_level == "HIGH" and industry_change == "ACCELERATING":
            industry_class = "LEADING"
        elif industry_level in {"HIGH", "MEDIUM"}:
            industry_class = "IMPROVING"
        elif industry_level in {"LOW", "WEAK"}:
            industry_class = "WEAKENING"
        else:
            industry_class = "NEUTRAL"

    return {
        "symbol": symbol,
        "portfolio_weight": None,
        "security_type": metadata.get("security_type", "UNAVAILABLE"),
        "sector": sector_name,
        "industry": industry_name,
        "metadata_source": metadata.get("metadata_source", "UNAVAILABLE"),
        "metadata_provenance": metadata.get("metadata_provenance", "UNAVAILABLE"),
        "absolute_state": abs_state,
        "vs_market": sec_vs_market,
        "vs_sector": sec_vs_sector,
        "vs_industry": sec_vs_industry,
        "relative_strength_level": rel_level,
        "relative_momentum_change": rel_change,
        "fundamental_momentum": fundamentals,
        "confirmation_state": confirmation,
        "extension_state": extension_state,
        "market_fallback_used": market_fallback_used,
        "sector_parent_used": bool(any(value.get("state") != "UNAVAILABLE" or value.get("relative_return_pct") is not None for value in sec_vs_sector.values())),
        "industry_parent_used": bool(any(value.get("state") != "UNAVAILABLE" or value.get("relative_return_pct") is not None for value in sec_vs_industry.values())),
        "sector_rotation_context": sector_class,
        "industry_rotation_context": industry_class,
        "data_quality": {
            "price_history_available": sec_series is not None and bool(sec_series.points),
            "history_points": len(sec_series.points) if sec_series is not None else 0,
            "history_start": sec_series.points[0][0] if sec_series and sec_series.points else None,
            "history_end": sec_series.points[-1][0] if sec_series and sec_series.points else None,
            "sector_available": bool(sector_series and sector_series.points),
            "industry_available": bool(industry_series and industry_series.points),
            "fundamental_history_available": bool(fundamentals.get("signals_used")),
        },
        "coverage": {
            "price_history_available": sec_series is not None and bool(sec_series.points),
            "sector_available": bool(sector_series and sector_series.points),
            "industry_available": bool(industry_series and industry_series.points),
            "fundamental_history_available": bool(fundamentals.get("signals_used")),
        },
        "provenance": {
            "as_of_date": sec_series.as_of_date if sec_series is not None else None,
            "freshness_days": sec_series.freshness_days if sec_series is not None else None,
            "source": sec_series.source if sec_series is not None else "UNAVAILABLE",
            "methodology": "reporting_only_security_evaluation",
        },
    }


def evaluate_momentum_for_symbols(symbols: list[str] | tuple[str, ...], *, repo_root: str | Path = ".") -> list[dict[str, object]]:
    root = Path(repo_root)
    requested_symbols: list[str] = []
    seen: set[str] = set()
    for symbol in list(symbols):
        sym = str(symbol).strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        requested_symbols.append(sym)
    if not requested_symbols:
        return []

    universe = _load_universe_metadata(root)
    requested_set = set(requested_symbols)
    sector_names = {
        str(universe.get(symbol, {}).get("sector", "")).strip()
        for symbol in requested_symbols
        if str(universe.get(symbol, {}).get("sector", "")).strip()
    }
    industry_names = {
        str(universe.get(symbol, {}).get("industry", "")).strip()
        for symbol in requested_symbols
        if str(universe.get(symbol, {}).get("industry", "")).strip() and str(universe.get(symbol, {}).get("industry", "")).strip() != "UNAVAILABLE"
    }

    context_symbols = set(requested_set)
    for symbol_name, meta in universe.items():
        sector = str(meta.get("sector", "")).strip()
        industry = str(meta.get("industry", "")).strip()
        if sector in sector_names or industry in industry_names:
            context_symbols.add(str(symbol_name).strip().upper())
    context_symbols.update(_SECTOR_PROXY_FALLBACKS.values())

    security_type_map = _load_security_type_taxonomy_for_symbols(root, requested_set)
    holdings_snapshot_date, _holdings = _load_holdings(root)
    analysis_as_of = str(holdings_snapshot_date or "")[:10]

    market_series = _load_benchmark_series(root)
    if analysis_as_of:
        market_series = _filter_series_to_as_of(market_series, analysis_as_of) or MomentumSeries(
            symbol="^GSPC",
            source="data/current/benchmark_returns.csv",
            as_of_date=analysis_as_of,
            freshness_days=_freshness_days(analysis_as_of),
            points=[],
        )
    market_horizons = _build_horizon_payload(market_series)

    security_series = _load_security_price_series_for_symbols(root, context_symbols)
    if analysis_as_of:
        security_series = {
            symbol_name: (
                _filter_series_to_as_of(series, analysis_as_of)
                or MomentumSeries(
                    symbol=symbol_name,
                    source=series.source,
                    as_of_date=analysis_as_of,
                    freshness_days=_freshness_days(analysis_as_of),
                    points=[],
                )
            )
            for symbol_name, series in security_series.items()
        }

    sector_proxy_series = _load_sector_proxy_series(root, security_series=security_series)
    if analysis_as_of:
        sector_proxy_series = {
            symbol_name: (
                _filter_series_to_as_of(series, analysis_as_of)
                or MomentumSeries(
                    symbol=symbol_name,
                    source=series.source,
                    as_of_date=analysis_as_of,
                    freshness_days=_freshness_days(analysis_as_of),
                    points=[],
                )
            )
            for symbol_name, series in sector_proxy_series.items()
        }

    ess_series = _load_ess_series(root)
    zacks_series = _load_daily_symbol_metric_series(root, "data/signals/zacks/*_zacks.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("zacks_score")))
    danelfin_series = _load_daily_symbol_metric_series(root, "data/signals/danelfin/*_danelfin*.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("danelfin_score")))
    yahoo_pt_series = _load_daily_symbol_metric_series(root, "data/signals/yahoo/*_yahoo_supplemental.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("price_target")))
    yahoo_abr_series = _load_daily_symbol_metric_series(root, "data/signals/yahoo/*_yahoo_supplemental.csv", lambda p: p.name.split("_", 1)[0], lambda row: _to_float(row.get("abr")))
    fmp_consensus_series = _load_daily_symbol_metric_series(root, "data/signals/fmp/daily/fmp_grades_consensus_*.csv", lambda p: p.name.rsplit("_", 1)[-1].replace(".csv", ""), lambda row: _to_float(row.get("net_buy_score")))
    fmp_income_growth_series = _load_daily_symbol_metric_series(root, "data/signals/fmp/latest/latest_fmp_income_growth.csv", lambda _p: _today_utc().isoformat(), lambda row: _to_float(row.get("revenue_growth_q1_yoy")))
    if analysis_as_of:
        ess_series = _filter_metric_map_to_as_of(ess_series, analysis_as_of)
        zacks_series = _filter_metric_map_to_as_of(zacks_series, analysis_as_of)
        danelfin_series = _filter_metric_map_to_as_of(danelfin_series, analysis_as_of)
        yahoo_pt_series = _filter_metric_map_to_as_of(yahoo_pt_series, analysis_as_of)
        yahoo_abr_series = _filter_metric_map_to_as_of(yahoo_abr_series, analysis_as_of)
        fmp_consensus_series = _filter_metric_map_to_as_of(fmp_consensus_series, analysis_as_of)
        fmp_income_growth_series = _filter_metric_map_to_as_of(fmp_income_growth_series, analysis_as_of)

    sector_members: dict[str, list[str]] = {}
    industry_members: dict[str, list[str]] = {}
    for symbol_name in context_symbols:
        meta = universe.get(symbol_name, {})
        sector = str(meta.get("sector", "")).strip()
        industry = str(meta.get("industry", "")).strip()
        if sector:
            sector_members.setdefault(sector, []).append(symbol_name)
        if industry and industry != "UNAVAILABLE":
            industry_members.setdefault(industry, []).append(symbol_name)

    context = MomentumEvaluationContext(
        repo_root=root,
        analysis_as_of=analysis_as_of,
        universe=universe,
        security_type_map=security_type_map,
        market_horizons=market_horizons,
        security_series=security_series,
        sector_proxy_series=sector_proxy_series,
        ess_series=ess_series,
        zacks_series=zacks_series,
        danelfin_series=danelfin_series,
        yahoo_pt_series=yahoo_pt_series,
        yahoo_abr_series=yahoo_abr_series,
        fmp_consensus_series=fmp_consensus_series,
        fmp_income_growth_series=fmp_income_growth_series,
        sector_members=sector_members,
        industry_members=industry_members,
    )

    results: list[dict[str, object]] = []
    for sym in requested_symbols:
        results.append(
            _build_symbol_evaluation_record(
                sym,
                repo_root=context.repo_root,
                universe=context.universe,
                security_type_map=context.security_type_map,
                market_horizons=context.market_horizons,
                security_series=context.security_series,
                sector_proxy_series=context.sector_proxy_series,
                ess_series=context.ess_series,
                zacks_series=context.zacks_series,
                danelfin_series=context.danelfin_series,
                yahoo_pt_series=context.yahoo_pt_series,
                yahoo_abr_series=context.yahoo_abr_series,
                fmp_consensus_series=context.fmp_consensus_series,
                fmp_income_growth_series=context.fmp_income_growth_series,
                sector_members=context.sector_members,
                industry_members=context.industry_members,
            )
        )
    return results


def pis_momentum_summary(*, repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    coverage_inventory = inventory_current_price_coverage(root)
    sector_parent_inventory = inventory_sector_parent_coverage(root)
    universe = _load_universe_metadata(root)
    holdings_snapshot_date, holdings = _load_holdings(root)
    analysis_as_of = str(holdings_snapshot_date or "")[:10]

    market_series = _load_benchmark_series(root)
    if analysis_as_of:
        market_series = _filter_series_to_as_of(market_series, analysis_as_of) or MomentumSeries(
            symbol="^GSPC",
            source="data/current/benchmark_returns.csv",
            as_of_date=analysis_as_of,
            freshness_days=_freshness_days(analysis_as_of),
            points=[],
        )
    market_horizons = _build_horizon_payload(market_series)
    market_state = _classify_absolute_momentum_state(market_horizons)

    security_series = _load_security_price_series(root)
    if analysis_as_of:
        security_series = {
            symbol: (
                _filter_series_to_as_of(series, analysis_as_of)
                or MomentumSeries(
                    symbol=symbol,
                    source=series.source,
                    as_of_date=analysis_as_of,
                    freshness_days=_freshness_days(analysis_as_of),
                    points=[],
                )
            )
            for symbol, series in security_series.items()
        }
    sector_proxy_series = _load_sector_proxy_series(root, security_series=security_series)
    if analysis_as_of:
        sector_proxy_series = {
            symbol: (
                _filter_series_to_as_of(series, analysis_as_of)
                or MomentumSeries(
                    symbol=symbol,
                    source=series.source,
                    as_of_date=analysis_as_of,
                    freshness_days=_freshness_days(analysis_as_of),
                    points=[],
                )
            )
            for symbol, series in sector_proxy_series.items()
        }

    ess_series = _load_ess_series(root)
    if analysis_as_of:
        ess_series = _filter_metric_map_to_as_of(ess_series, analysis_as_of)
    zacks_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/zacks/*_zacks.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("zacks_score")),
    )
    if analysis_as_of:
        zacks_series = _filter_metric_map_to_as_of(zacks_series, analysis_as_of)
    danelfin_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/danelfin/*_danelfin*.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("danelfin_score")),
    )
    if analysis_as_of:
        danelfin_series = _filter_metric_map_to_as_of(danelfin_series, analysis_as_of)
    yahoo_pt_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/yahoo/*_yahoo_supplemental.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("price_target")),
    )
    if analysis_as_of:
        yahoo_pt_series = _filter_metric_map_to_as_of(yahoo_pt_series, analysis_as_of)
    yahoo_abr_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/yahoo/*_yahoo_supplemental.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("abr")),
    )
    if analysis_as_of:
        yahoo_abr_series = _filter_metric_map_to_as_of(yahoo_abr_series, analysis_as_of)
    fmp_consensus_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/fmp/daily/fmp_grades_consensus_*.csv",
        lambda p: p.name.rsplit("_", 1)[-1].replace(".csv", ""),
        lambda row: _to_float(row.get("net_buy_score")),
    )
    if analysis_as_of:
        fmp_consensus_series = _filter_metric_map_to_as_of(fmp_consensus_series, analysis_as_of)
    fmp_income_growth_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/fmp/latest/latest_fmp_income_growth.csv",
        lambda _p: _today_utc().isoformat(),
        lambda row: _to_float(row.get("revenue_growth_q1_yoy")),
    )
    if analysis_as_of:
        fmp_income_growth_series = _filter_metric_map_to_as_of(fmp_income_growth_series, analysis_as_of)

    # Sector universe from holdings metadata.
    holdings_symbols = [str(h["symbol"]) for h in holdings]
    holding_asset_type_by_symbol = {
        str(h["symbol"]): str(h.get("asset_type", "")).upper()
        for h in holdings
    }
    sectors: dict[str, list[str]] = {}
    industries: dict[str, list[str]] = {}
    for symbol in holdings_symbols:
        meta = universe.get(symbol, {})
        sector = str(meta.get("sector", "")).strip() or "UNKNOWN"
        industry = str(meta.get("industry", "")).strip() or "UNAVAILABLE"
        sectors.setdefault(sector, []).append(symbol)
        if industry != "UNAVAILABLE":
            industries.setdefault(industry, []).append(symbol)

    sector_rows: list[dict[str, object]] = []
    sector_abs_horizons_map: dict[str, dict[str, dict[str, object]]] = {}
    sector_parent_relative_map: dict[str, dict[str, dict[str, object]]] = {}
    for sector_name, symbols in sorted(sectors.items()):
        sector_upper = sector_name.upper()
        proxy_symbol = _SECTOR_PROXY_FALLBACKS.get(sector_upper)
        proxy_series = sector_proxy_series.get(proxy_symbol) if proxy_symbol else None
        if not proxy_series:
            proxy_series = _group_series_from_constituents(symbols, security_series, group_key=f"SECTOR::{sector_upper}")

        if proxy_series is None:
            sector_horizons = _build_horizon_payload(
                MomentumSeries(
                    symbol=f"SECTOR::{sector_upper}",
                    source="unavailable",
                    as_of_date="",
                    freshness_days=None,
                    points=[],
                )
            )
        else:
            sector_horizons = _build_horizon_payload(proxy_series)

        sector_abs_state = _classify_absolute_momentum_state(sector_horizons)
        sector_vs_market = _compute_relative_horizons(
            sector_horizons,
            market_horizons,
            source_label=f"{sector_name} vs market",
        )
        level = _relative_strength_level(sector_vs_market)
        change = _relative_momentum_change(sector_vs_market)

        # Breadth uses holdings in each sector due current data constraints.
        short_positive = 0
        outperforming = 0
        improving_fund = 0
        total_constituents = 0
        contribution_pool: list[float] = []
        for symbol in symbols:
            sec_series = security_series.get(symbol)
            if not sec_series:
                continue
            total_constituents += 1
            sec_h = _build_horizon_payload(sec_series)
            rel = _compute_relative_horizons(sec_h, market_horizons, source_label=f"{symbol} vs market")
            r1w = sec_h.get("1W", {}).get("return_pct")
            rr1w = rel.get("1W", {}).get("relative_return_pct")
            if isinstance(r1w, (int, float)) and r1w > 0:
                short_positive += 1
            if isinstance(rr1w, (int, float)) and rr1w > 0:
                outperforming += 1
            fund_state = _fundamental_snapshot_for_symbol(
                symbol,
                ess_series=ess_series,
                zacks_series=zacks_series,
                danelfin_series=danelfin_series,
                yahoo_pt_series=yahoo_pt_series,
                yahoo_abr_series=yahoo_abr_series,
                fmp_consensus_series=fmp_consensus_series,
                fmp_income_growth_series=fmp_income_growth_series,
            )["state"]
            if fund_state == "IMPROVING":
                improving_fund += 1
            mv = next((float(h.get("market_value", 0.0)) for h in holdings if str(h.get("symbol")) == symbol), 0.0)
            contribution_pool.append(mv)

        pos_share = (short_positive / total_constituents) if total_constituents else None
        out_share = (outperforming / total_constituents) if total_constituents else None
        fund_share = (improving_fund / total_constituents) if total_constituents else None
        top5_share = None
        if contribution_pool:
            total_mv = sum(contribution_pool)
            if total_mv > 0:
                top5_share = sum(sorted(contribution_pool, reverse=True)[:5]) / total_mv

        breadth_state = _classify_breadth_state(pos_share, out_share, fund_share, top5_share, total_constituents)

        if level == "HIGH" and change == "ACCELERATING":
            sector_class = "LEADING"
        elif level in {"HIGH", "MEDIUM"} and change == "STABLE":
            sector_class = "IMPROVING"
        elif level in {"LOW", "WEAK"} and change in {"FADING", "STABLE"}:
            sector_class = "LAGGING"
        elif level in {"LOW", "WEAK"} and change == "ACCELERATING":
            sector_class = "WEAKENING"
        elif level == "UNAVAILABLE":
            sector_class = "UNAVAILABLE"
        else:
            sector_class = "NEUTRAL"

        sector_rows.append(
            {
                "sector": sector_name,
                "proxy_symbol": proxy_symbol,
                "constituent_count": len(symbols),
                "parent_available": bool(proxy_series and proxy_series.points),
                "absolute_momentum": {
                    "state": sector_abs_state,
                    "horizons": sector_horizons,
                },
                "relative_to_market": {
                    "level": level,
                    "change": change,
                    "horizons": sector_vs_market,
                },
                "breadth": {
                    "state": breadth_state,
                    "positive_short_share": round(pos_share, 4) if pos_share is not None else None,
                    "outperform_parent_share": round(out_share, 4) if out_share is not None else None,
                    "improving_fund_share": round(fund_share, 4) if fund_share is not None else None,
                    "top5_contribution_share": round(top5_share, 4) if top5_share is not None else None,
                    "new_leaders": None,
                    "fading_leaders": None,
                },
                "fundamental_revision_direction": "UNAVAILABLE",
                "leadership_concentration": "UNAVAILABLE" if top5_share is None else ("NARROW" if top5_share >= 0.75 else "BALANCED"),
                "acceleration": change,
                "classification": sector_class,
            }
        )
        sector_abs_horizons_map[sector_name] = sector_horizons
        sector_parent_relative_map[sector_name] = sector_vs_market

    industry_rows: list[dict[str, object]] = []
    industry_relative_map: dict[str, dict[str, dict[str, object]]] = {}
    for industry_name, symbols in sorted(industries.items()):
        with_series = [s for s in symbols if s in security_series and security_series[s].points]
        coverage_pct = (len(with_series) / len(symbols)) if symbols else 0.0

        constituent_asset_types = {holding_asset_type_by_symbol.get(s, "") for s in symbols}
        has_equity_like_constituents = any(asset_type in _EQUITY_LIKE_ASSET_TYPES for asset_type in constituent_asset_types)

        if not has_equity_like_constituents:
            parent_applicable = False
            parent_blocker = "ASSET_CLASS_NOT_MEANINGFUL"
        else:
            parent_applicable = True
            if len(symbols) < _MIN_INDUSTRY_CONSTITUENTS:
                parent_blocker = "INSUFFICIENT_CONSTITUENTS"
            elif coverage_pct < _MIN_INDUSTRY_PRICE_COVERAGE_PCT:
                parent_blocker = "INSUFFICIENT_HISTORY"
            else:
                parent_blocker = "NONE"

        parent_available = (
            parent_applicable
            and
            len(with_series) >= _MIN_INDUSTRY_CONSTITUENTS
            and coverage_pct >= _MIN_INDUSTRY_PRICE_COVERAGE_PCT
        )
        industry_series = None
        if parent_available:
            industry_series = _group_series_from_constituents(
                with_series,
                security_series,
                group_key=f"INDUSTRY::{industry_name.upper()}",
            )
        if industry_series is None:
            ind_horizons = _build_horizon_payload(
                MomentumSeries(
                    symbol=f"INDUSTRY::{industry_name.upper()}",
                    source="unavailable",
                    as_of_date="",
                    freshness_days=None,
                    points=[],
                )
            )
        else:
            ind_horizons = _build_horizon_payload(industry_series)

        # Parent sector for this industry based on first mapped symbol.
        first_symbol = symbols[0] if symbols else ""
        sector_name = str(universe.get(first_symbol, {}).get("sector", "UNKNOWN"))
        sector_source = str(universe.get(first_symbol, {}).get("sector_source", "UNAVAILABLE"))
        sector_abs_horizons = sector_abs_horizons_map.get(sector_name)

        ind_vs_market = _compute_relative_horizons(ind_horizons, market_horizons, source_label=f"{industry_name} vs market")
        if sector_abs_horizons is None:
            ind_vs_sector = {h: {"state": "UNAVAILABLE", "relative_return_pct": None} for h in _HORIZON_WINDOWS}
        else:
            ind_vs_sector = _compute_relative_horizons(ind_horizons, sector_abs_horizons, source_label=f"{industry_name} vs sector")

        level = _relative_strength_level(ind_vs_market)
        change = _relative_momentum_change(ind_vs_market)

        if level == "HIGH" and change == "ACCELERATING":
            cls = "LEADING"
        elif level in {"HIGH", "MEDIUM"}:
            cls = "IMPROVING"
        elif level in {"LOW", "WEAK"}:
            cls = "WEAKENING"
        elif level == "UNAVAILABLE":
            cls = "UNAVAILABLE"
        else:
            cls = "NEUTRAL"

        industry_rows.append(
            {
                "industry": industry_name,
                "sector": sector_name,
                "sector_source": sector_source,
                "industry_source": str(universe.get(first_symbol, {}).get("industry_source", "UNAVAILABLE")),
                "industry_granularity": str(universe.get(first_symbol, {}).get("industry_granularity", "UNAVAILABLE")),
                "constituent_count": len(symbols),
                "parent_applicable": parent_applicable,
                "parent_applicability_reason": "APPLICABLE" if parent_applicable else parent_blocker,
                "parent_available": parent_available and industry_series is not None,
                "parent_methodology": "CONSTITUENT_DERIVED" if parent_available and industry_series is not None else "UNAVAILABLE",
                "direct_proxy_available": False,
                "recognized_proxy_available": False,
                "parent_blocker": parent_blocker,
                "parent_constituents_with_history": len(with_series),
                "parent_constituent_coverage_pct": round(coverage_pct, 4) if symbols else 0.0,
                "parent_min_constituents_required": _MIN_INDUSTRY_CONSTITUENTS,
                "parent_min_coverage_required": _MIN_INDUSTRY_PRICE_COVERAGE_PCT,
                "parent_weighting_method": "EQUAL_WEIGHT" if parent_available and industry_series is not None else "UNAVAILABLE",
                "parent_history_start": industry_series.points[0][0] if industry_series and industry_series.points else None,
                "parent_history_end": industry_series.points[-1][0] if industry_series and industry_series.points else None,
                "parent_provenance": f"CONSTITUENT_DERIVED::{industry_name}" if parent_available and industry_series is not None else "UNAVAILABLE",
                "parent_confidence": (
                    "HIGH"
                    if parent_available and len(with_series) >= 5 and coverage_pct >= 0.8
                    else "MEDIUM"
                    if parent_available
                    else "UNAVAILABLE"
                ),
                "absolute_momentum": {
                    "state": _classify_absolute_momentum_state(ind_horizons),
                    "horizons": ind_horizons,
                },
                "relative_to_market": {
                    "level": level,
                    "change": change,
                    "horizons": ind_vs_market,
                },
                "relative_to_sector": {
                    "level": _relative_strength_level(ind_vs_sector),
                    "change": _relative_momentum_change(ind_vs_sector),
                    "horizons": ind_vs_sector,
                },
                "breadth": {
                    "state": "UNAVAILABLE",
                    "positive_short_share": None,
                    "outperform_parent_share": None,
                    "improving_fund_share": None,
                    "top5_contribution_share": None,
                    "new_leaders": None,
                    "fading_leaders": None,
                },
                "fundamental_revision_direction": "UNAVAILABLE",
                "leadership_concentration": "UNAVAILABLE",
                "acceleration": change,
                "classification": cls,
            }
        )
        industry_relative_map[industry_name] = ind_vs_market

    portfolio_rows: list[dict[str, object]] = []
    cohorts: dict[str, list[str]] = {
        "CONFIRMED LEADERS": [],
        "EMERGING LEADERS": [],
        "STRONG-GROUP LAGGARDS": [],
        "RESILIENT IN WEAK GROUPS": [],
        "PRICE/FUNDAMENTAL DIVERGENCES": [],
        "FADING LEADERS": [],
        "REVERSALS": [],
    }

    for holding in holdings:
        symbol = str(holding.get("symbol", "")).upper()
        sec_series = security_series.get(symbol)
        sec_horizons = _build_horizon_payload(
            sec_series
            if sec_series is not None
            else MomentumSeries(symbol=symbol, source="unavailable", as_of_date="", freshness_days=None, points=[])
        )
        sec_abs_state = _classify_absolute_momentum_state(sec_horizons)

        meta = universe.get(symbol, {})
        sector_name = str(meta.get("sector", "UNKNOWN"))
        industry_name = str(meta.get("industry", "UNAVAILABLE"))
        sector_source = str(meta.get("sector_source", "UNAVAILABLE"))
        industry_source = str(meta.get("industry_source", "UNAVAILABLE"))
        industry_granularity = str(meta.get("industry_granularity", "UNAVAILABLE"))

        sector_row = next((r for r in sector_rows if r.get("sector") == sector_name), None)
        industry_row = next((r for r in industry_rows if r.get("industry") == industry_name), None)

        if sector_row is not None:
            sec_vs_sector = _compute_relative_horizons(sec_horizons, sector_row["absolute_momentum"]["horizons"], source_label=f"{symbol} vs sector")
        else:
            sec_vs_sector = {h: {"state": "UNAVAILABLE", "relative_return_pct": None} for h in _HORIZON_WINDOWS}

        if industry_row is not None:
            sec_vs_industry = _compute_relative_horizons(sec_horizons, industry_row["absolute_momentum"]["horizons"], source_label=f"{symbol} vs industry")
        else:
            sec_vs_industry = {h: {"state": "UNAVAILABLE", "relative_return_pct": None} for h in _HORIZON_WINDOWS}

        sec_vs_market = _compute_relative_horizons(sec_horizons, market_horizons, source_label=f"{symbol} vs market")

        rel_level = _relative_strength_level(sec_vs_industry)
        rel_change = _relative_momentum_change(sec_vs_industry)

        sector_level = "UNAVAILABLE"
        if sector_row is not None:
            sector_level = str(sector_row["relative_to_market"]["level"])
        industry_level = "UNAVAILABLE"
        if industry_row is not None:
            industry_level = str(industry_row["relative_to_market"]["level"])

        sec_state = _classify_security_leadership_state(
            sector_vs_market_level=sector_level,
            industry_vs_sector_level=industry_level,
            security_vs_industry_level=rel_level,
            security_vs_industry_change=rel_change,
        )

        fundamentals = _fundamental_snapshot_for_symbol(
            symbol,
            ess_series=ess_series,
            zacks_series=zacks_series,
            danelfin_series=danelfin_series,
            yahoo_pt_series=yahoo_pt_series,
            yahoo_abr_series=yahoo_abr_series,
            fmp_consensus_series=fmp_consensus_series,
            fmp_income_growth_series=fmp_income_growth_series,
        )

        confirmation = _classify_confirmation_state(sec_abs_state, str(fundamentals.get("state", "UNAVAILABLE")))
        ext_metrics = _extension_metrics(
            sec_series if sec_series is not None else MomentumSeries(symbol=symbol, source="unavailable", as_of_date="", freshness_days=None, points=[])
        )
        extension_state = _classify_extension_state(
            distance_ma20_pct=ext_metrics["distance_from_ma20_pct"],
            distance_52w_high_pct=ext_metrics["distance_from_52w_high_pct"],
            recent_acceleration_pct=ext_metrics["recent_acceleration_pct"],
            volatility_20d_pct=ext_metrics["volatility_20d_pct"],
        )

        if sec_state == "MULTI_LEVEL_CONFIRMED_LEADERSHIP" and confirmation == "CONFIRMED_MOMENTUM":
            cohorts["CONFIRMED LEADERS"].append(symbol)
        if rel_change == "ACCELERATING" and rel_level in {"MEDIUM", "NEUTRAL"}:
            cohorts["EMERGING LEADERS"].append(symbol)
        if sec_state == "SECURITY_LAGGARD_IN_STRONG_GROUP":
            cohorts["STRONG-GROUP LAGGARDS"].append(symbol)
        if sec_state == "SECURITY_RESILIENT_IN_WEAK_GROUP":
            cohorts["RESILIENT IN WEAK GROUPS"].append(symbol)
        if confirmation == "MOMENTUM_DIVERGENCE":
            cohorts["PRICE/FUNDAMENTAL DIVERGENCES"].append(symbol)
        if rel_change == "FADING":
            cohorts["FADING LEADERS"].append(symbol)
        if sec_abs_state in {"WEAK", "WEAKENING"} and str(fundamentals.get("state")) == "IMPROVING":
            cohorts["REVERSALS"].append(symbol)

        changes = _historical_change_proxy(sec_vs_industry)
        if rel_level != "UNAVAILABLE" and rel_change != "UNAVAILABLE" and confirmation != "UNAVAILABLE":
            evaluation_status = "FULLY_EVALUATED"
        elif sec_abs_state != "UNAVAILABLE" or rel_level != "UNAVAILABLE" or str(fundamentals.get("state")) != "UNAVAILABLE":
            evaluation_status = "PARTIALLY_EVALUATED"
        else:
            evaluation_status = "UNAVAILABLE"

        portfolio_rows.append(
            {
                "symbol": symbol,
                "portfolio_weight": holding.get("portfolio_weight"),
                "sector": sector_name,
                "industry": industry_name,
                "sector_source": sector_source,
                "industry_source": industry_source,
                "industry_granularity": industry_granularity,
                "market_state": market_state,
                "sector_state": sector_row["classification"] if sector_row else "UNAVAILABLE",
                "industry_state": industry_row["classification"] if industry_row else "UNAVAILABLE",
                "security_state": sec_state,
                "absolute_security_momentum": {
                    "state": sec_abs_state,
                    "horizons": sec_horizons,
                },
                "security_vs_market": sec_vs_market,
                "security_vs_sector": sec_vs_sector,
                "security_vs_industry": sec_vs_industry,
                "relative_strength_level": rel_level,
                "relative_momentum_change": rel_change,
                "fundamental_momentum": fundamentals,
                "confirmation_state": confirmation,
                "breadth_context": sector_row["breadth"]["state"] if sector_row else "UNAVAILABLE",
                "extension_state": extension_state,
                "extension_metrics": ext_metrics,
                "change_detection": changes,
                "history_label": "RECONSTRUCTED_DERIVED",
                "evaluation_status": evaluation_status,
            }
        )

    portfolio_rows.sort(key=lambda r: float(r.get("portfolio_weight") or 0.0), reverse=True)

    mu_row = next((row for row in portfolio_rows if row.get("symbol") == "MU"), None)
    if mu_row is None:
        mu_drilldown = {
            "symbol": "MU",
            "mu_available": False,
            "questions": {
                "is_absolute_rising": "UNAVAILABLE",
                "vs_market": "UNAVAILABLE",
                "vs_sector": "UNAVAILABLE",
                "vs_industry": "UNAVAILABLE",
                "leadership_change": "UNAVAILABLE",
                "semiconductor_fundamentals": "UNAVAILABLE",
                "mu_fundamentals": "UNAVAILABLE",
                "confirmation_state": "UNAVAILABLE",
                "extension": "UNAVAILABLE",
                "leader_inside_leading_industry": "UNAVAILABLE",
            },
            "data_gap": "MU security price history unavailable under data/history/prices",
            "mu_history": {
                "first_date": None,
                "last_date": None,
                "points": 0,
            },
            "parent_availability": {
                "market_parent_available": False,
                "sector_parent_available": False,
                "industry_parent_available": False,
            },
        }
    else:
        abs_1m = mu_row["absolute_security_momentum"]["horizons"]["1M"].get("return_pct")
        mu_symbol = "MU"
        mu_series = security_series.get(mu_symbol)
        mu_points = len(mu_series.points) if mu_series else 0
        mu_first = mu_series.points[0][0] if mu_series and mu_series.points else None
        mu_last = mu_series.points[-1][0] if mu_series and mu_series.points else None
        mu_sector = str(mu_row.get("sector") or "UNKNOWN")
        mu_industry = str(mu_row.get("industry") or "UNAVAILABLE")
        mu_sector_row = next((s for s in sector_rows if str(s.get("sector")) == mu_sector), None)
        mu_industry_row = next((i for i in industry_rows if str(i.get("industry")) == mu_industry), None)
        mu_drilldown = {
            "symbol": "MU",
            "mu_available": True,
            "taxonomy": {
                "sector": mu_sector,
                "sector_source": str(mu_row.get("sector_source") or "UNAVAILABLE"),
                "industry": mu_industry,
                "industry_source": str(mu_row.get("industry_source") or "UNAVAILABLE"),
                "industry_granularity": str(mu_row.get("industry_granularity") or "UNAVAILABLE"),
            },
            "questions": {
                "is_absolute_rising": "YES" if isinstance(abs_1m, (int, float)) and abs_1m > 0 else "NO" if isinstance(abs_1m, (int, float)) else "UNAVAILABLE",
                "vs_market": mu_row["relative_strength_level"],
                "vs_sector": _relative_strength_level(mu_row["security_vs_sector"]),
                "vs_industry": _relative_strength_level(mu_row["security_vs_industry"]),
                "leadership_change": mu_row["relative_momentum_change"],
                "semiconductor_fundamentals": "UNAVAILABLE",
                "mu_fundamentals": mu_row["fundamental_momentum"]["state"],
                "confirmation_state": mu_row["confirmation_state"],
                "extension": mu_row["extension_state"],
                "leader_inside_leading_industry": "YES" if mu_row["security_state"] == "MULTI_LEVEL_CONFIRMED_LEADERSHIP" else "NO",
            },
            "mu_history": {
                "first_date": mu_first,
                "last_date": mu_last,
                "points": mu_points,
            },
            "parent_availability": {
                "market_parent_available": bool(market_series.points),
                "sector_parent_available": bool(mu_sector_row and mu_sector_row.get("parent_available")),
                "industry_parent_available": bool(mu_industry_row and mu_industry_row.get("parent_available")),
            },
        }

    sector_parent_total = len([row for row in sector_parent_inventory if row.parent_series])
    sector_parent_available = len([
        row for row in sector_parent_inventory
        if row.parent_series and row.history_available
    ])
    sector_parent_coverage_pct = round((sector_parent_available / sector_parent_total) * 100.0, 2) if sector_parent_total else 0.0

    industry_parent_total = len(industry_rows)
    industry_parent_applicable = len([row for row in industry_rows if bool(row.get("parent_applicable"))])
    industry_parent_not_applicable = industry_parent_total - industry_parent_applicable
    industry_parent_available = len([
        row
        for row in industry_rows
        if bool(row.get("parent_applicable")) and bool(row.get("parent_available"))
    ])
    industry_parent_coverage_pct = round((industry_parent_available / industry_parent_applicable) * 100.0, 2) if industry_parent_applicable else 0.0

    applicable_symbols = {row.symbol for row in coverage_inventory.rows}
    applicable_weights = {
        str(row.get("symbol")): float(row.get("portfolio_weight") or 0.0)
        for row in portfolio_rows
        if str(row.get("symbol")) in applicable_symbols
    }
    applicable_total_weight = sum(applicable_weights.values())

    full_history_symbols = {row.symbol for row in coverage_inventory.rows if row.coverage_status == "PRESENT"}
    any_history_symbols = {row.symbol for row in coverage_inventory.rows if row.coverage_status in {"PRESENT", "PARTIAL"}}

    full_history_security_coverage_pct = round((len(full_history_symbols) / coverage_inventory.applicable_count) * 100.0, 2) if coverage_inventory.applicable_count else 0.0
    any_history_security_coverage_pct = round((len(any_history_symbols) / coverage_inventory.applicable_count) * 100.0, 2) if coverage_inventory.applicable_count else 0.0

    full_history_weight = sum(applicable_weights.get(symbol, 0.0) for symbol in full_history_symbols)
    any_history_weight = sum(applicable_weights.get(symbol, 0.0) for symbol in any_history_symbols)
    full_history_weight_coverage_pct = round((full_history_weight / applicable_total_weight) * 100.0, 2) if applicable_total_weight > 0 else 0.0
    any_history_weight_coverage_pct = round((any_history_weight / applicable_total_weight) * 100.0, 2) if applicable_total_weight > 0 else 0.0

    applicable_rows = [row for row in portfolio_rows if str(row.get("symbol")) in applicable_symbols]

    absolute_symbols = {str(row.get("symbol")) for row in applicable_rows if str(row.get("absolute_security_momentum", {}).get("state")) != "UNAVAILABLE"}
    market_relative_symbols = {str(row.get("symbol")) for row in applicable_rows if _has_relative_evidence(row.get("security_vs_market", {}))}
    sector_relative_symbols = {str(row.get("symbol")) for row in applicable_rows if _has_relative_evidence(row.get("security_vs_sector", {}))}
    industry_rows_by_name = {
        str(row.get("industry")): row
        for row in industry_rows
    }
    industry_relative_applicable_symbols = {
        str(row.get("symbol"))
        for row in applicable_rows
        if bool(industry_rows_by_name.get(str(row.get("industry")), {}).get("parent_applicable"))
    }
    industry_relative_symbols = {
        str(row.get("symbol"))
        for row in applicable_rows
        if str(row.get("symbol")) in industry_relative_applicable_symbols
        and _has_relative_evidence(row.get("security_vs_industry", {}))
    }
    full_hierarchy_symbols = absolute_symbols & market_relative_symbols & sector_relative_symbols & industry_relative_symbols

    def _pct(count: int, denom: int) -> float:
        return round((count / denom) * 100.0, 2) if denom else 0.0

    absolute_evaluable_security_pct = _pct(len(absolute_symbols), len(applicable_rows))
    market_relative_evaluable_security_pct = _pct(len(market_relative_symbols), len(applicable_rows))
    sector_relative_evaluable_security_pct = _pct(len(sector_relative_symbols), len(applicable_rows))
    industry_relative_evaluable_security_pct = _pct(len(industry_relative_symbols), len(industry_relative_applicable_symbols))
    full_hierarchy_security_pct = _pct(len(full_hierarchy_symbols), len(industry_relative_applicable_symbols))

    def _weight_pct(symbols: set[str], *, denominator_symbols: set[str] | None = None) -> float:
        if denominator_symbols is None:
            denominator_symbols = set(applicable_weights.keys())
        weight = sum(applicable_weights.get(symbol, 0.0) for symbol in symbols)
        denominator_weight = sum(applicable_weights.get(symbol, 0.0) for symbol in denominator_symbols)
        return round((weight / denominator_weight) * 100.0, 2) if denominator_weight > 0 else 0.0

    absolute_evaluable_weight_pct = _weight_pct(absolute_symbols)
    market_relative_evaluable_weight_pct = _weight_pct(market_relative_symbols)
    sector_relative_evaluable_weight_pct = _weight_pct(sector_relative_symbols)
    industry_relative_evaluable_weight_pct = _weight_pct(
        industry_relative_symbols,
        denominator_symbols=industry_relative_applicable_symbols,
    )
    full_hierarchy_weight_pct = _weight_pct(
        full_hierarchy_symbols,
        denominator_symbols=industry_relative_applicable_symbols,
    )

    total_weight = sum(float(row.get("portfolio_weight") or 0.0) for row in portfolio_rows)
    evaluable_weight = sum(
        float(row.get("portfolio_weight") or 0.0)
        for row in portfolio_rows
        if str(row.get("evaluation_status")) == "FULLY_EVALUATED"
    )
    evaluable_weight_pct = round((evaluable_weight / total_weight) * 100.0, 2) if total_weight > 0 else 0.0

    if evaluable_weight_pct >= 90.0:
        portfolio_coverage_state = "FULLY_EVALUATED"
    elif evaluable_weight_pct > 0:
        portfolio_coverage_state = "PARTIALLY_EVALUATED"
    else:
        portfolio_coverage_state = "UNAVAILABLE"

    def _build_top_trades_trend_exposure(
        rows: list[dict[str, object]],
        series_lookup: dict[str, MomentumSeries],
        *,
        as_of_date: str | None,
    ) -> dict[str, object]:
        exposures: list[dict[str, object]] = []
        for row in rows:
            symbol = str(row.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            ctx = build_trend_structure_context(
                series_lookup.get(symbol) if symbol in series_lookup else MomentumSeries(
                    symbol=symbol,
                    source="unavailable",
                    as_of_date=str(as_of_date or ""),
                    freshness_days=None,
                    points=[],
                ),
                as_of_date=str(as_of_date or ""),
            )
            history_status = str(ctx.get("history_status") or "UNAVAILABLE")
            price_vs_sma50 = float(ctx.get("price_vs_sma50_pct") or 0.0)
            price_vs_sma200 = float(ctx.get("price_vs_sma200_pct") or 0.0)
            if history_status == "AVAILABLE":
                if price_vs_sma50 > 0 and price_vs_sma200 > 0:
                    bucket = "LEADING"
                elif price_vs_sma50 < 0 and price_vs_sma200 < 0:
                    bucket = "LAGGING"
                else:
                    bucket = "NEUTRAL"
            elif history_status.startswith("INSUFFICIENT_"):
                bucket = "INSUFFICIENT_HISTORY"
            else:
                bucket = "UNAVAILABLE"
            exposures.append({
                "symbol": symbol,
                "bucket": bucket,
                "history_status": history_status,
                "currentness_state": str(ctx.get("currentness_state") or "MISSING"),
                "price_vs_sma50_pct": round(price_vs_sma50, 6),
                "price_vs_sma200_pct": round(price_vs_sma200, 6),
            })

        leaders = [e for e in exposures if e["bucket"] == "LEADING"]
        laggards = [e for e in exposures if e["bucket"] == "LAGGING"]
        neutral = [e for e in exposures if e["bucket"] == "NEUTRAL"]
        insufficient_history = [e for e in exposures if e["bucket"] == "INSUFFICIENT_HISTORY"]
        unavailable = [e for e in exposures if e["bucket"] == "UNAVAILABLE"]

        return {
            "reporting_only": True,
            "as_of_date": as_of_date,
            "leaders": [e["symbol"] for e in leaders],
            "laggards": [e["symbol"] for e in laggards],
            "neutral": [e["symbol"] for e in neutral],
            "insufficient_history": [e["symbol"] for e in insufficient_history],
            "unavailable": [e["symbol"] for e in unavailable],
            "per_symbol": exposures,
            "total_symbols": len(exposures),
        }

    top_trades_trend_exposure = _build_top_trades_trend_exposure(
        portfolio_rows,
        security_series,
        as_of_date=holdings_snapshot_date,
    )

    return {
        "status": "ok",
        "reporting_only": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": holdings_snapshot_date,
        "methodology": _build_methodology_payload(),
        "coverage": {
            "security_history_coverage_pct": coverage_inventory.coverage_pct,
            "full_history_security_coverage_pct": full_history_security_coverage_pct,
            "any_history_security_coverage_pct": any_history_security_coverage_pct,
            "full_history_portfolio_weight_coverage_pct": full_history_weight_coverage_pct,
            "any_history_portfolio_weight_coverage_pct": any_history_weight_coverage_pct,
            "sector_parent_coverage_pct": sector_parent_coverage_pct,
            "industry_parent_coverage_pct": industry_parent_coverage_pct,
            "portfolio_momentum_evaluable_weight_pct": evaluable_weight_pct,
            "portfolio_coverage_state": portfolio_coverage_state,
            "hierarchy_availability": {
                "absolute_evaluable_security_pct": absolute_evaluable_security_pct,
                "market_relative_evaluable_security_pct": market_relative_evaluable_security_pct,
                "sector_relative_evaluable_security_pct": sector_relative_evaluable_security_pct,
                "industry_relative_evaluable_security_pct": industry_relative_evaluable_security_pct,
                "full_hierarchy_security_pct": full_hierarchy_security_pct,
                "absolute_evaluable_weight_pct": absolute_evaluable_weight_pct,
                "market_relative_evaluable_weight_pct": market_relative_evaluable_weight_pct,
                "sector_relative_evaluable_weight_pct": sector_relative_evaluable_weight_pct,
                "industry_relative_evaluable_weight_pct": industry_relative_evaluable_weight_pct,
                "full_hierarchy_weight_pct": full_hierarchy_weight_pct,
            },
            "security_counts": {
                "applicable": coverage_inventory.applicable_count,
                "present": coverage_inventory.present_count,
                "missing": coverage_inventory.missing_count,
                "partial": coverage_inventory.partial_count,
            },
            "sector_parent_counts": {
                "required": sector_parent_total,
                "available": sector_parent_available,
            },
            "industry_parent_counts": {
                "required": industry_parent_applicable,
                "available": industry_parent_available,
                "total": industry_parent_total,
                "not_applicable": industry_parent_not_applicable,
            },
        },
        "data_availability": {
            "price_history": {
                "security_price_series_count": len(security_series),
                "market_series_points": len(market_series.points),
                "sector_proxy_symbols": sorted(list(sector_proxy_series.keys())),
            },
            "fundamental_history": {
                "ess_symbols": len(ess_series),
                "zacks_symbols": len(zacks_series),
                "danelfin_symbols": len(danelfin_series),
                "yahoo_symbols": len(yahoo_pt_series),
                "fmp_consensus_symbols": len(fmp_consensus_series),
            },
            "limitations": [
                "Coverage state is computed from current-holdings applicability and available per-symbol price history.",
                "Industry-level proxy histories are derived from available constituents when direct proxies are absent.",
                "7d/30d state transitions are reconstructed from available return snapshots and labeled RECONSTRUCTED_DERIVED.",
            ],
        },
        "market_momentum": {
            "market_absolute_momentum": {
                "state": market_state,
                "horizons": market_horizons,
            }
        },
        "entry_timing_context": {
            "reporting_only": True,
            "as_of_date": holdings_snapshot_date,
            "holdings": [
                {
                    "symbol": row.get("symbol"),
                    "trend_structure_context": build_trend_structure_context(
                        security_series.get(str(row.get("symbol", "")).upper())
                        if str(row.get("symbol", "")).upper() in security_series
                        else MomentumSeries(
                            symbol=str(row.get("symbol", "")).upper(),
                            source="unavailable",
                            as_of_date=str(holdings_snapshot_date or ""),
                            freshness_days=None,
                            points=[],
                        ),
                        as_of_date=str(holdings_snapshot_date or ""),
                    ),
                }
                for row in portfolio_rows
            ],
            "top_trades_trend_exposure": top_trades_trend_exposure,
        },
        "sector_rotation": sector_rows,
        "industry_rotation": industry_rows,
        "portfolio_momentum_map": {
            "holdings": portfolio_rows,
            "cohorts": cohorts,
        },
        "security_drilldown": {
            "mu": mu_drilldown,
        },
        "change_detection": {
            "method": "RECONSTRUCTED_DERIVED",
            "labels": {
                "since_prior": "Derived from short-horizon relative returns",
                "7d": "Derived from 1W horizon",
                "30d": "Derived from 1M horizon",
            },
        },
    }


def pis_momentum_methodology(*, repo_root: str | Path = ".") -> dict[str, object]:
    _ = repo_root
    return _build_methodology_payload()
