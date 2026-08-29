"""Dislocation & Recovery Intelligence (DRI) industry map (reporting-only).

This module provides an additive, observational industry map using existing
price and taxonomy artifacts. It is strictly reporting-only and must not
influence ranking, allocation, recommendations, or execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from .momentum_intelligence import (
    _build_horizon_payload,
    _classify_absolute_momentum_state,
    _compute_relative_horizons,
    _filter_metric_series_to_as_of,
    _filter_series_to_as_of,
    _load_benchmark_series,
    _load_ess_series,
    _load_holdings,
    _load_holdings_as_of,
    _load_security_price_series,
    _load_security_type_taxonomy,
    _load_universe_metadata,
    _read_csv_rows,
    _relative_momentum_change,
    _relative_strength_level,
)

_MIN_INDUSTRY_CONSTITUENTS = 2
_MIN_INDUSTRY_COVERAGE_PCT = 0.6
_NON_INDUSTRY_VALUES = {"", "UNAVAILABLE", "UNKNOWN", "N/A", "NA", "NONE", "ALL"}
_NON_SECTOR_VALUES = {"", "UNKNOWN", "UNAVAILABLE", "N/A", "NA", "NONE", "ALL"}
_EQUITY_LIKE_SECURITY_TYPES = {
    "EQUITY",
    "EQUITIES",
    "STOCK",
    "COMMON STOCK",
    "COMMON_STOCK",
    "ADR",
}

_HORIZON_WINDOWS: dict[str, int] = {
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "12M": 252,
}


def _empty_horizons() -> dict[str, dict[str, object]]:
    return {
        horizon: {
            "state": "UNAVAILABLE",
            "return_pct": None,
            "source": "unavailable",
            "as_of_date": "",
            "history_available": 0,
            "freshness_days": None,
            "confidence": "UNAVAILABLE",
            "required_points": required + 1,
        }
        for horizon, required in {
            "1W": 5,
            "1M": 21,
            "3M": 63,
            "6M": 126,
            "12M": 252,
        }.items()
    }


def _empty_relative_horizons() -> dict[str, dict[str, object]]:
    return {
        horizon: {"state": "UNAVAILABLE", "relative_return_pct": None}
        for horizon in _HORIZON_WINDOWS
    }


def _security_points_by_date(points: list[tuple[str, float]]) -> dict[str, float]:
    return {d: float(price) for d, price in points if price > 0}


def _benchmark_horizon_windows(
    market_series,
) -> dict[str, dict[str, object]]:
    points = list(market_series.points) if market_series else []
    if not points:
        return {
            horizon: {
                "periods": periods,
                "required_points": periods + 1,
                "start_date": None,
                "end_date": None,
                "return_pct": None,
                "available": False,
            }
            for horizon, periods in _HORIZON_WINDOWS.items()
        }

    end_date, end_price = points[-1]
    windows: dict[str, dict[str, object]] = {}
    for horizon, periods in _HORIZON_WINDOWS.items():
        required_points = periods + 1
        if len(points) < required_points:
            windows[horizon] = {
                "periods": periods,
                "required_points": required_points,
                "start_date": None,
                "end_date": end_date,
                "return_pct": None,
                "available": False,
            }
            continue

        start_date, start_price = points[-required_points]
        bench_ret = ((end_price / start_price) - 1.0) * 100.0 if start_price > 0 else None
        windows[horizon] = {
            "periods": periods,
            "required_points": required_points,
            "start_date": start_date,
            "end_date": end_date,
            "return_pct": round(bench_ret, 4) if isinstance(bench_ret, (int, float)) else None,
            "available": isinstance(bench_ret, (int, float)),
        }
    return windows


def _fixed_cohort_horizon_return(
    symbols: list[str],
    price_points_by_symbol: dict[str, dict[str, float]],
    *,
    start_date: str | None,
    end_date: str | None,
) -> dict[str, object]:
    out = {
        "eligible_symbols": [],
        "eligible_count": 0,
        "excluded_missing_start_count": 0,
        "excluded_missing_end_count": 0,
        "return_pct": None,
        "constituent_returns": [],
    }
    if not start_date or not end_date:
        return out

    constituent_returns: list[float] = []
    eligible_symbols: list[str] = []
    miss_start = 0
    miss_end = 0

    for symbol in symbols:
        by_date = price_points_by_symbol.get(symbol, {})
        start_price = by_date.get(start_date)
        end_price = by_date.get(end_date)
        if start_price is None:
            miss_start += 1
        if end_price is None:
            miss_end += 1
        if start_price is None or end_price is None:
            continue
        if start_price <= 0:
            continue
        ret = ((end_price / start_price) - 1.0) * 100.0
        constituent_returns.append(float(ret))
        eligible_symbols.append(symbol)

    out["eligible_symbols"] = sorted(eligible_symbols)
    out["eligible_count"] = len(eligible_symbols)
    out["excluded_missing_start_count"] = miss_start
    out["excluded_missing_end_count"] = miss_end
    out["constituent_returns"] = constituent_returns
    if len(constituent_returns) >= _MIN_INDUSTRY_CONSTITUENTS:
        out["return_pct"] = round(float(mean(constituent_returns)), 4)
    return out


def _build_fixed_cohort_horizons(
    *,
    industry: str,
    symbols: list[str],
    filtered_series_map,
    benchmark_windows: dict[str, dict[str, object]],
    market_horizons: dict[str, dict[str, object]],
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    dict[str, object],
]:
    horizons = _empty_horizons()
    relative = _empty_relative_horizons()
    return_coverage: dict[str, dict[str, object]] = {}
    return_windows: dict[str, dict[str, object]] = {}

    price_points_by_symbol: dict[str, dict[str, float]] = {}
    for symbol in symbols:
        series = filtered_series_map.get(symbol)
        price_points_by_symbol[symbol] = _security_points_by_date(list(series.points) if series else [])

    for horizon, periods in _HORIZON_WINDOWS.items():
        bench_window = benchmark_windows.get(horizon, {})
        start_date = str(bench_window.get("start_date") or "") or None
        end_date = str(bench_window.get("end_date") or "") or None

        cohort = _fixed_cohort_horizon_return(
            symbols,
            price_points_by_symbol,
            start_date=start_date,
            end_date=end_date,
        )

        eligible_count = int(cohort.get("eligible_count") or 0)
        coverage_pct = round((eligible_count / len(symbols)) * 100.0, 4) if symbols else 0.0
        return_coverage[horizon] = {
            "industry_member_count": len(symbols),
            "eligible_return_member_count": eligible_count,
            "excluded_missing_start_count": int(cohort.get("excluded_missing_start_count") or 0),
            "excluded_missing_end_count": int(cohort.get("excluded_missing_end_count") or 0),
            "return_coverage_pct": coverage_pct,
            "single_member_blocked": eligible_count < _MIN_INDUSTRY_CONSTITUENTS,
        }
        return_windows[horizon] = {
            "return_start_date": start_date,
            "return_end_date": end_date,
            "benchmark_start_date": start_date,
            "benchmark_end_date": end_date,
            "benchmark_window_aligned": bool(start_date and end_date),
        }

        return_pct = cohort.get("return_pct")
        horizons[horizon] = {
            "state": "UNAVAILABLE",
            "return_pct": return_pct if isinstance(return_pct, (int, float)) else None,
            "source": f"fixed_cohort_equal_weight::{industry}",
            "as_of_date": end_date or "",
            "history_available": eligible_count,
            "freshness_days": market_horizons.get(horizon, {}).get("freshness_days"),
            "confidence": "HIGH" if isinstance(return_pct, (int, float)) else "UNAVAILABLE",
            "required_points": periods + 1,
        }

        if isinstance(return_pct, (int, float)):
            if return_pct >= 8.0:
                horizons[horizon]["state"] = "STRONG"
            elif return_pct >= 2.0:
                horizons[horizon]["state"] = "POSITIVE"
            elif return_pct <= -8.0:
                horizons[horizon]["state"] = "WEAK"
            elif return_pct <= -2.0:
                horizons[horizon]["state"] = "NEGATIVE"
            else:
                horizons[horizon]["state"] = "NEUTRAL"

    relative = _compute_relative_horizons(
        horizons,
        market_horizons,
        source_label=f"{industry} vs market",
    )
    return horizons, relative, return_coverage, return_windows


def _normalized_fixed_cohort_series(
    cohort_symbols: list[str],
    filtered_series_map,
    *,
    start_date: str,
    end_date: str,
) -> list[tuple[str, float]]:
    if not cohort_symbols:
        return []

    points_by_symbol: dict[str, dict[str, float]] = {}
    date_sets: list[set[str]] = []
    for symbol in cohort_symbols:
        series = filtered_series_map.get(symbol)
        by_date = _security_points_by_date(list(series.points) if series else [])
        if start_date not in by_date or end_date not in by_date:
            return []
        window_dates = {d for d in by_date.keys() if start_date <= d <= end_date}
        points_by_symbol[symbol] = by_date
        date_sets.append(window_dates)

    common_dates = sorted(set.intersection(*date_sets)) if date_sets else []
    if not common_dates or start_date not in common_dates or end_date not in common_dates:
        return []

    out: list[tuple[str, float]] = []
    for d in common_dates:
        normalized_values: list[float] = []
        for symbol in cohort_symbols:
            by_date = points_by_symbol[symbol]
            start_price = by_date.get(start_date)
            px = by_date.get(d)
            if start_price is None or px is None or start_price <= 0:
                normalized_values = []
                break
            normalized_values.append(px / start_price)
        if normalized_values:
            out.append((d, float(mean(normalized_values))))
    return out


def _drawdown_from_normalized_series(points: list[tuple[str, float]]) -> tuple[float | None, int]:
    if not points:
        return None, 0
    closes = [v for _, v in points]
    if not closes:
        return None, 0
    drawdown = round(((closes[-1] / max(closes)) - 1.0) * 100.0, 4)
    return drawdown, max(len(closes) - 1, 0)


def _share(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 4)


def _trend_metrics(points: list[tuple[str, float]]) -> dict[str, float | None]:
    if not points:
        return {
            "price_vs_sma50_pct": None,
            "price_vs_sma200_pct": None,
            "sma50_change_20d_pct": None,
            "sma200_change_20d_pct": None,
        }

    latest = points[-1][1]

    def _sma(window: int, offset: int = 0) -> float | None:
        if len(points) < window + offset:
            return None
        end = len(points) - offset
        start = end - window
        values = [price for _, price in points[start:end]]
        return float(sum(values) / len(values)) if values else None

    sma50 = _sma(50)
    sma200 = _sma(200)
    sma50_prev = _sma(50, offset=20)
    sma200_prev = _sma(200, offset=20)

    def _pct(cur: float | None, base: float | None) -> float | None:
        if cur is None or base is None or base <= 0:
            return None
        return round(((cur / base) - 1.0) * 100.0, 6)

    return {
        "price_vs_sma50_pct": _pct(latest, sma50),
        "price_vs_sma200_pct": _pct(latest, sma200),
        "sma50_change_20d_pct": _pct(sma50, sma50_prev),
        "sma200_change_20d_pct": _pct(sma200, sma200_prev),
    }


def _breadth_at_cutoff(
    symbols: list[str],
    security_series,
    market_horizons: dict[str, dict[str, object]],
    *,
    as_of_date: str,
) -> dict[str, dict[str, float | int | None]]:
    above_50_num = 0
    above_50_den = 0
    above_200_num = 0
    above_200_den = 0
    pos_1m_num = 0
    pos_1m_den = 0
    out_1m_num = 0
    out_1m_den = 0

    market_1m = market_horizons.get("1M", {}).get("return_pct")

    for symbol in symbols:
        raw_series = security_series.get(symbol)
        series = _filter_series_to_as_of(raw_series, as_of_date)
        points = list(series.points) if series else []
        if not points:
            continue

        trend = _trend_metrics(points)

        px_vs_50 = trend.get("price_vs_sma50_pct")
        if isinstance(px_vs_50, (int, float)):
            above_50_den += 1
            if px_vs_50 > 0:
                above_50_num += 1

        px_vs_200 = trend.get("price_vs_sma200_pct")
        if isinstance(px_vs_200, (int, float)):
            above_200_den += 1
            if px_vs_200 > 0:
                above_200_num += 1

        if len(points) >= 22:
            start = points[-22][1]
            end = points[-1][1]
            if start > 0:
                ret_1m = ((end / start) - 1.0) * 100.0
                pos_1m_den += 1
                if ret_1m > 0:
                    pos_1m_num += 1
                if isinstance(market_1m, (int, float)):
                    out_1m_den += 1
                    if ret_1m > float(market_1m):
                        out_1m_num += 1

    return {
        "above_50dma": {
            "numerator": above_50_num,
            "denominator": above_50_den,
            "share_pct": _share(above_50_num, above_50_den),
        },
        "above_200dma": {
            "numerator": above_200_num,
            "denominator": above_200_den,
            "share_pct": _share(above_200_num, above_200_den),
        },
        "positive_1m": {
            "numerator": pos_1m_num,
            "denominator": pos_1m_den,
            "share_pct": _share(pos_1m_num, pos_1m_den),
        },
        "outperform_market_1m": {
            "numerator": out_1m_num,
            "denominator": out_1m_den,
            "share_pct": _share(out_1m_num, out_1m_den),
        },
    }


def _deltas_20d(
    current_breadth: dict[str, dict[str, float | int | None]],
    prior_breadth: dict[str, dict[str, float | int | None]],
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for key in ("above_50dma", "above_200dma", "positive_1m", "outperform_market_1m"):
        current_share = current_breadth.get(key, {}).get("share_pct")
        prior_share = prior_breadth.get(key, {}).get("share_pct")
        if isinstance(current_share, (int, float)) and isinstance(prior_share, (int, float)):
            out[f"{key}_share_change_20d_pp"] = round(float(current_share) - float(prior_share), 4)
        else:
            out[f"{key}_share_change_20d_pp"] = None
    return out


def _ess_context(symbols: list[str], ess_series, *, as_of_date: str) -> dict[str, object]:
    latest_scores: list[float] = []
    delta_20d: list[float] = []

    for symbol in symbols:
        series = _filter_metric_series_to_as_of(ess_series.get(symbol, []), as_of_date)
        if not series:
            continue
        latest_scores.append(float(series[-1][1]))
        if len(series) >= 21:
            delta_20d.append(float(series[-1][1]) - float(series[-21][1]))

    improving = sum(1 for d in delta_20d if d > 0)
    deteriorating = sum(1 for d in delta_20d if d < 0)
    flat = sum(1 for d in delta_20d if d == 0)

    return {
        "ess_observations": len(latest_scores),
        "ess_latest_mean": round(mean(latest_scores), 4) if latest_scores else None,
        "ess_latest_median": round(median(latest_scores), 4) if latest_scores else None,
        "ess_delta_20d_mean": round(mean(delta_20d), 4) if delta_20d else None,
        "ess_delta_20d_improving_count": improving,
        "ess_delta_20d_deteriorating_count": deteriorating,
        "ess_delta_20d_flat_count": flat,
    }


def _canonical_research_symbols(repo_root: Path) -> tuple[set[str], dict[str, str]]:
    rows = _read_csv_rows(repo_root / "data/current/analytical_universe.csv")
    symbols: set[str] = set()
    security_types: dict[str, str] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        symbols.add(symbol)
        sec_type = str(row.get("security_type") or "").strip().upper()
        if sec_type:
            security_types[symbol] = sec_type
    return symbols, security_types


def _is_equity_like(security_type: str) -> bool:
    return str(security_type or "").strip().upper() in _EQUITY_LIKE_SECURITY_TYPES


def _normalized_taxonomy_value(raw_value: str, *, unknown_values: set[str], fallback: str) -> str:
    value = str(raw_value or "").strip()
    if not value or value.upper() in unknown_values:
        return fallback
    return value


def _industry_rows(
    *,
    symbols: list[str],
    universe: dict[str, dict[str, str]],
    security_series,
    market_horizons: dict[str, dict[str, object]],
    benchmark_windows: dict[str, dict[str, object]],
    ess_series,
    as_of_date: str,
    portfolio_weight_by_symbol: dict[str, float],
) -> list[dict[str, object]]:
    industry_map: dict[str, list[str]] = {}
    industry_sector: dict[str, str] = {}

    for symbol in symbols:
        meta = universe.get(symbol, {})
        industry = _normalized_taxonomy_value(
            str(meta.get("industry") or ""),
            unknown_values=_NON_INDUSTRY_VALUES,
            fallback="UNAVAILABLE",
        )
        sector = _normalized_taxonomy_value(
            str(meta.get("sector") or ""),
            unknown_values=_NON_SECTOR_VALUES,
            fallback="UNKNOWN",
        )
        if industry == "UNAVAILABLE":
            continue
        industry_map.setdefault(industry, []).append(symbol)
        industry_sector.setdefault(industry, sector)

    rows: list[dict[str, object]] = []

    for industry, symbols in sorted(industry_map.items()):
        unique_symbols = sorted(set(symbols))
        filtered_by_symbol = {
            s: _filter_series_to_as_of(security_series.get(s), as_of_date)
            for s in unique_symbols
        }
        with_history = [s for s in unique_symbols if filtered_by_symbol.get(s) is not None and filtered_by_symbol[s].points]
        coverage_pct = round((len(with_history) / len(unique_symbols)) * 100.0, 4) if unique_symbols else 0.0
        parent_available = (
            len(unique_symbols) >= _MIN_INDUSTRY_CONSTITUENTS
            and (coverage_pct / 100.0) >= _MIN_INDUSTRY_COVERAGE_PCT
            and len(with_history) >= _MIN_INDUSTRY_CONSTITUENTS
        )

        filtered_series_map = {}
        for symbol in with_history:
            filtered = filtered_by_symbol.get(symbol)
            if filtered is not None:
                filtered_series_map[symbol] = filtered

        horizons, relative, return_coverage, return_windows = _build_fixed_cohort_horizons(
            industry=industry,
            symbols=unique_symbols,
            filtered_series_map=filtered_series_map,
            benchmark_windows=benchmark_windows,
            market_horizons=market_horizons,
        )

        drawdown_cohort = return_coverage.get("6M", {}).get("eligible_return_member_count", 0)
        drawdown_start = return_windows.get("6M", {}).get("return_start_date")
        drawdown_end = return_windows.get("6M", {}).get("return_end_date")
        drawdown_symbols = []
        if drawdown_cohort >= _MIN_INDUSTRY_CONSTITUENTS:
            cohort = _fixed_cohort_horizon_return(
                unique_symbols,
                {s: _security_points_by_date(list(filtered_series_map.get(s).points)) if filtered_series_map.get(s) else {} for s in unique_symbols},
                start_date=drawdown_start,
                end_date=drawdown_end,
            )
            drawdown_symbols = list(cohort.get("eligible_symbols") or [])

        normalized_series: list[tuple[str, float]] = []
        if drawdown_symbols and isinstance(drawdown_start, str) and isinstance(drawdown_end, str):
            normalized_series = _normalized_fixed_cohort_series(
                drawdown_symbols,
                filtered_series_map,
                start_date=drawdown_start,
                end_date=drawdown_end,
            )

        drawdown_pct, lookback_days = _drawdown_from_normalized_series(normalized_series)

        trend_lists = {
            "price_vs_sma50_pct": [],
            "price_vs_sma200_pct": [],
            "sma50_change_20d_pct": [],
            "sma200_change_20d_pct": [],
        }
        for symbol in unique_symbols:
            filtered = _filter_series_to_as_of(security_series.get(symbol), as_of_date)
            points = list(filtered.points) if filtered else []
            trend = _trend_metrics(points)
            for key, value in trend.items():
                if isinstance(value, (int, float)):
                    trend_lists[key].append(float(value))

        breadth_now = _breadth_at_cutoff(unique_symbols, security_series, market_horizons, as_of_date=as_of_date)

        prior_cutoff = as_of_date
        if len(normalized_series) >= 21:
            prior_cutoff = normalized_series[-21][0]
        breadth_20d_ago = _breadth_at_cutoff(unique_symbols, security_series, market_horizons, as_of_date=prior_cutoff)

        deltas = _deltas_20d(breadth_now, breadth_20d_ago)

        row = {
            "industry": industry,
            "sector": industry_sector.get(industry, "UNKNOWN"),
            "members": unique_symbols,
            "member_count": len(unique_symbols),
            "history_coverage": {
                "members_with_history": len(with_history),
                "coverage_pct": coverage_pct,
                "parent_available": bool(parent_available and any(
                    isinstance(horizons.get(h, {}).get("return_pct"), (int, float))
                    for h in ("1M", "3M", "6M")
                )),
                "min_constituents_required": _MIN_INDUSTRY_CONSTITUENTS,
                "min_coverage_required_pct": _MIN_INDUSTRY_COVERAGE_PCT * 100.0,
            },
            "returns": {
                "return_1m_pct": horizons.get("1M", {}).get("return_pct"),
                "return_3m_pct": horizons.get("3M", {}).get("return_pct"),
                "return_6m_pct": horizons.get("6M", {}).get("return_pct"),
                "return_1m_vs_market_pct": relative.get("1M", {}).get("relative_return_pct"),
                "return_3m_vs_market_pct": relative.get("3M", {}).get("relative_return_pct"),
                "return_6m_vs_market_pct": relative.get("6M", {}).get("relative_return_pct"),
                "coverage": {
                    "1M": return_coverage.get("1M", {}),
                    "3M": return_coverage.get("3M", {}),
                    "6M": return_coverage.get("6M", {}),
                },
                "windows": {
                    "1M": return_windows.get("1M", {}),
                    "3M": return_windows.get("3M", {}),
                    "6M": return_windows.get("6M", {}),
                },
            },
            "drawdown": {
                "from_available_history_high_pct": drawdown_pct,
                "lookback_days_available": lookback_days,
                "series_method": "NORMALIZED_FIXED_COHORT_EQUAL_WEIGHT",
                "series_start_date": normalized_series[0][0] if normalized_series else None,
                "series_end_date": normalized_series[-1][0] if normalized_series else None,
                "series_constituent_count": len(drawdown_symbols),
            },
            "breadth": {
                "above_50dma": breadth_now["above_50dma"],
                "above_200dma": breadth_now["above_200dma"],
                "positive_1m": breadth_now["positive_1m"],
                "outperform_market_1m": breadth_now["outperform_market_1m"],
                "above_50dma_share_change_20d_pp": deltas["above_50dma_share_change_20d_pp"],
                "above_200dma_share_change_20d_pp": deltas["above_200dma_share_change_20d_pp"],
                "positive_1m_share_change_20d_pp": deltas["positive_1m_share_change_20d_pp"],
                "outperform_market_1m_share_change_20d_pp": deltas["outperform_market_1m_share_change_20d_pp"],
            },
            "trend_medians": {
                "price_vs_sma50_pct": round(median(trend_lists["price_vs_sma50_pct"]), 6) if trend_lists["price_vs_sma50_pct"] else None,
                "price_vs_sma200_pct": round(median(trend_lists["price_vs_sma200_pct"]), 6) if trend_lists["price_vs_sma200_pct"] else None,
                "sma50_change_20d_pct": round(median(trend_lists["sma50_change_20d_pct"]), 6) if trend_lists["sma50_change_20d_pct"] else None,
                "sma200_change_20d_pct": round(median(trend_lists["sma200_change_20d_pct"]), 6) if trend_lists["sma200_change_20d_pct"] else None,
            },
            "momentum_context": {
                "absolute_state": _classify_absolute_momentum_state(horizons),
                "relative_strength_level": _relative_strength_level(relative),
                "relative_momentum_change": _relative_momentum_change(relative),
            },
            "fundamental_context": _ess_context(unique_symbols, ess_series, as_of_date=as_of_date),
            "portfolio_context": {
                "portfolio_member_count": len([s for s in unique_symbols if s in portfolio_weight_by_symbol]),
                "portfolio_weight_pct": round(sum(float(portfolio_weight_by_symbol.get(s, 0.0)) for s in unique_symbols), 4),
                "portfolio_symbols": sorted([s for s in unique_symbols if s in portfolio_weight_by_symbol]),
            },
            "reporting_only": True,
        }
        rows.append(row)

    return rows


def pis_dri_industry_map(
    *,
    repo_root: str | Path = ".",
    as_of_date: str | None = None,
) -> dict[str, object]:
    """Return reporting-only industry dislocation and recovery map."""

    root = Path(repo_root)

    if as_of_date:
        resolved_as_of, holdings = _load_holdings_as_of(root, as_of_date[:10])
        as_of = resolved_as_of or as_of_date[:10]
    else:
        as_of, holdings = _load_holdings(root)

    universe = _load_universe_metadata(root)
    research_symbols, research_security_types = _canonical_research_symbols(root)
    security_types = _load_security_type_taxonomy(root)
    security_series = _load_security_price_series(root)
    market_series = _filter_series_to_as_of(_load_benchmark_series(root), as_of)
    market_horizons = _build_horizon_payload(market_series)
    benchmark_windows = _benchmark_horizon_windows(market_series)
    ess_series = _load_ess_series(root)

    portfolio_weight_by_symbol = {
        str(h.get("symbol") or "").strip().upper(): float(h.get("portfolio_weight") or 0.0)
        for h in holdings
        if str(h.get("symbol") or "").strip()
    }

    research_considered = set(research_symbols)
    if not research_considered:
        research_considered = set(universe.keys())

    applicable_symbols: list[str] = []
    excluded_non_equity = 0
    excluded_missing_taxonomy = 0

    for symbol in sorted(research_considered):
        meta = universe.get(symbol, {})
        industry = _normalized_taxonomy_value(
            str(meta.get("industry") or ""),
            unknown_values=_NON_INDUSTRY_VALUES,
            fallback="UNAVAILABLE",
        )
        if industry == "UNAVAILABLE":
            excluded_missing_taxonomy += 1
            continue

        sec_type = security_types.get(symbol) or research_security_types.get(symbol) or ""
        if sec_type and not _is_equity_like(sec_type):
            excluded_non_equity += 1
            continue

        applicable_symbols.append(symbol)

    industries_before_coverage = len({
        _normalized_taxonomy_value(
            str(universe.get(symbol, {}).get("industry") or ""),
            unknown_values=_NON_INDUSTRY_VALUES,
            fallback="UNAVAILABLE",
        )
        for symbol in applicable_symbols
    } - {"UNAVAILABLE"})

    industries = _industry_rows(
        symbols=applicable_symbols,
        universe=universe,
        security_series=security_series,
        market_horizons=market_horizons,
        benchmark_windows=benchmark_windows,
        ess_series=ess_series,
        as_of_date=as_of,
        portfolio_weight_by_symbol=portfolio_weight_by_symbol,
    )

    industries_with_parent = [row for row in industries if row.get("history_coverage", {}).get("parent_available")]
    coverage_values = [
        float(row.get("history_coverage", {}).get("coverage_pct") or 0.0)
        for row in industries
    ]

    return {
        "status": "ok",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_date": as_of,
        "reporting_only": True,
        "methodology": {
            "industry_parent_method": "Fixed-cohort equal-weight mean of constituent point-to-point returns on benchmark-anchored horizon dates.",
            "relative_method": "Industry fixed-cohort horizon returns minus benchmark returns over exact same dates (1M/3M/6M shown).",
            "drawdown_method": "Percent from available-history high to latest level using normalized fixed-cohort equal-weight index.",
            "breadth_method": "Raw member fractions above 50DMA/200DMA, positive 1M return, and outperforming market over 1M.",
            "fundamental_method": "ESS-only aggregate context (latest and 20d deltas) where available.",
            "no_lookahead_rule": "All inputs are filtered to observations on or before as_of_date.",
            "industry_return_method": "FIXED_COHORT_MEAN_CONSTITUENT_RETURN",
            "synthetic_industry_series_method": "NORMALIZED_FIXED_COHORT_EQUAL_WEIGHT",
            "constituent_weighting": "EQUAL_WEIGHT",
            "shortened_security_windows_used": False,
            "governance": "Reporting-only; no effect on SIH scoring, recommendations, ranking, allocation, or execution.",
        },
        "coverage_summary": {
            "industry_count": len(industries),
            "industries_with_parent_history": len(industries_with_parent),
            "industries_without_parent_history": max(len(industries) - len(industries_with_parent), 0),
            "mean_member_history_coverage_pct": round(mean(coverage_values), 4) if coverage_values else 0.0,
            "holding_count": len({str(h.get("symbol") or "").strip().upper() for h in holdings if str(h.get("symbol") or "").strip()}),
            "research_universe_symbols_considered": len(research_considered),
            "dri_applicable_symbols": len(applicable_symbols),
            "dri_industries_before_coverage_gate": industries_before_coverage,
            "dri_industries_after_coverage_gate": len(industries),
            "exclusions": {
                "missing_industry_taxonomy": excluded_missing_taxonomy,
                "non_equity_security_type": excluded_non_equity,
            },
        },
        "industries": industries,
    }
