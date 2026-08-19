"""PIS Momentum Intelligence (reporting-only).

This module provides a transparent momentum analytics layer for operators.
It intentionally does not alter scoring, recommendation generation, ranking,
allocation, deployment, market-regime gating, or execution behavior.
"""

from __future__ import annotations

import csv
import json
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

_TAXONOMY_UNKNOWN_VALUES = {"", "UNKNOWN", "N/A", "NA", "NONE"}


@dataclass(frozen=True)
class MomentumSeries:
    symbol: str
    source: str
    as_of_date: str
    freshness_days: int | None
    points: list[tuple[str, float]]


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
        out.append(
            {
                "symbol": symbol,
                "portfolio_weight": round(float(weight or 0.0), 4),
                "market_value": round(float(market_value or 0.0), 4),
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
        d = date_parser(file_path)
        if not d:
            continue
        for row in _read_csv_rows(file_path):
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


def pis_momentum_summary(*, repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    coverage_inventory = inventory_current_price_coverage(root)
    sector_parent_inventory = inventory_sector_parent_coverage(root)
    universe = _load_universe_metadata(root)
    holdings_snapshot_date, holdings = _load_holdings(root)

    market_series = _load_benchmark_series(root)
    market_horizons = _build_horizon_payload(market_series)
    market_state = _classify_absolute_momentum_state(market_horizons)

    security_series = _load_security_price_series(root)
    sector_proxy_series = _load_sector_proxy_series(root, security_series=security_series)

    ess_series = _load_ess_series(root)
    zacks_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/zacks/*_zacks.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("zacks_score")),
    )
    danelfin_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/danelfin/*_danelfin*.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("danelfin_score")),
    )
    yahoo_pt_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/yahoo/*_yahoo_supplemental.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("price_target")),
    )
    yahoo_abr_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/yahoo/*_yahoo_supplemental.csv",
        lambda p: p.name.split("_", 1)[0],
        lambda row: _to_float(row.get("abr")),
    )
    fmp_consensus_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/fmp/daily/fmp_grades_consensus_*.csv",
        lambda p: p.name.rsplit("_", 1)[-1].replace(".csv", ""),
        lambda row: _to_float(row.get("net_buy_score")),
    )
    fmp_income_growth_series = _load_daily_symbol_metric_series(
        root,
        "data/signals/fmp/latest/latest_fmp_income_growth.csv",
        lambda _p: _today_utc().isoformat(),
        lambda row: _to_float(row.get("revenue_growth_q1_yoy")),
    )

    # Sector universe from holdings metadata.
    holdings_symbols = [str(h["symbol"]) for h in holdings]
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
        parent_available = (
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
                "parent_available": parent_available and industry_series is not None,
                "parent_methodology": "CONSTITUENT_DERIVED" if parent_available and industry_series is not None else "UNAVAILABLE",
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
    industry_parent_available = len([row for row in industry_rows if bool(row.get("parent_available"))])
    industry_parent_coverage_pct = round((industry_parent_available / industry_parent_total) * 100.0, 2) if industry_parent_total else 0.0

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
    industry_relative_symbols = {str(row.get("symbol")) for row in applicable_rows if _has_relative_evidence(row.get("security_vs_industry", {}))}
    full_hierarchy_symbols = absolute_symbols & market_relative_symbols & sector_relative_symbols & industry_relative_symbols

    def _pct(count: int, denom: int) -> float:
        return round((count / denom) * 100.0, 2) if denom else 0.0

    absolute_evaluable_security_pct = _pct(len(absolute_symbols), len(applicable_rows))
    market_relative_evaluable_security_pct = _pct(len(market_relative_symbols), len(applicable_rows))
    sector_relative_evaluable_security_pct = _pct(len(sector_relative_symbols), len(applicable_rows))
    industry_relative_evaluable_security_pct = _pct(len(industry_relative_symbols), len(applicable_rows))
    full_hierarchy_security_pct = _pct(len(full_hierarchy_symbols), len(applicable_rows))

    def _weight_pct(symbols: set[str]) -> float:
        weight = sum(applicable_weights.get(symbol, 0.0) for symbol in symbols)
        return round((weight / applicable_total_weight) * 100.0, 2) if applicable_total_weight > 0 else 0.0

    absolute_evaluable_weight_pct = _weight_pct(absolute_symbols)
    market_relative_evaluable_weight_pct = _weight_pct(market_relative_symbols)
    sector_relative_evaluable_weight_pct = _weight_pct(sector_relative_symbols)
    industry_relative_evaluable_weight_pct = _weight_pct(industry_relative_symbols)
    full_hierarchy_weight_pct = _weight_pct(full_hierarchy_symbols)

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
                "required": industry_parent_total,
                "available": industry_parent_available,
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
