"""ROTATION-RISK-01: Tech-to-hard-assets rotation monitor.

Display-only diagnostic built from existing artifacts. This module is strictly
advisory and must not mutate scoring, ranking, recommendation, CRA, or PAP
behavior.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional


_WINDOWS = (5, 20, 60)
_CAP_PRIORITY = ("LARGE", "MEGA", "MID", "SMALL", "MICRO")
_HARD_ASSET_INDUSTRIES = ("ENERGY", "BASIC MATERIALS", "INDUSTRIALS")


@dataclass(frozen=True)
class SeriesWindowReturns:
    replay_id: str
    market_cap_bucket: str
    latest_date: str
    returns: dict[int, float]


def _safe_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        return float(s)
    except Exception:
        return None


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _latest_run_id(repo_root: Path) -> str:
    manifest_path = repo_root / "data" / "portfolio_ingestion" / "manifest.json"
    if not manifest_path.exists():
        return ""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    portfolios = manifest.get("portfolios") or []
    if not portfolios:
        return ""
    latest = max(
        portfolios,
        key=lambda p: (str(p.get("snapshot_date", "")), str(p.get("created_at_utc", ""))),
    )
    return str(latest.get("run_id", "") or "")


def _load_holdings(repo_root: Path, run_id: str) -> list[dict[str, str]]:
    if not run_id:
        return []
    holdings_path = (
        repo_root
        / "data"
        / "portfolio_ingestion"
        / "analysis_runs"
        / run_id
        / "holdings.csv"
    )
    return _read_csv_rows(holdings_path)


def _effective_weight(row: dict[str, str], total_mv: float) -> float:
    pct = _safe_float(row.get("percent_of_portfolio"))
    if pct is not None and pct > 0:
        return pct
    if total_mv <= 0:
        return 0.0
    mv = _safe_float(row.get("market_value")) or 0.0
    return (mv / total_mv) * 100.0


def _industry_normalized(value: str) -> str:
    return str(value or "").strip().upper()


def _portfolio_exposure(holdings: list[dict[str, str]]) -> dict:
    if not holdings:
        return {
            "tech_pct": 0.0,
            "hard_assets_pct": 0.0,
            "other_pct": 0.0,
            "tech_symbol_count": 0,
            "hard_assets_symbol_count": 0,
            "total_symbol_count": 0,
        }

    total_mv = sum((_safe_float(r.get("market_value")) or 0.0) for r in holdings)
    tech_pct = 0.0
    hard_pct = 0.0
    tech_symbols: set[str] = set()
    hard_symbols: set[str] = set()

    for row in holdings:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        industry = _industry_normalized(row.get("industry") or "")
        weight = _effective_weight(row, total_mv)
        if industry == "TECHNOLOGY":
            tech_pct += weight
            tech_symbols.add(symbol)
        elif industry in _HARD_ASSET_INDUSTRIES:
            hard_pct += weight
            hard_symbols.add(symbol)

    tech_pct = round(max(0.0, tech_pct), 2)
    hard_pct = round(max(0.0, hard_pct), 2)
    other_pct = round(max(0.0, 100.0 - tech_pct - hard_pct), 2)
    return {
        "tech_pct": tech_pct,
        "hard_assets_pct": hard_pct,
        "other_pct": other_pct,
        "tech_symbol_count": len(tech_symbols),
        "hard_assets_symbol_count": len(hard_symbols),
        "total_symbol_count": len({str(r.get("symbol") or "").strip().upper() for r in holdings if r.get("symbol")}),
    }


def _latest_signal_snapshot(repo_root: Path) -> tuple[dict[str, float], str]:
    path = repo_root / "data" / "current" / "signal_snapshot.csv"
    rows = _read_csv_rows(path)
    if not rows:
        return {}, ""

    latest_snapshot = ""
    for row in rows:
        snap = str(row.get("snapshot_date") or "").strip()
        if snap and snap > latest_snapshot:
            latest_snapshot = snap

    by_symbol: dict[str, float] = {}
    for row in rows:
        if str(row.get("snapshot_date") or "").strip() != latest_snapshot:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        val = _safe_float(row.get("starmine_ess_numeric"))
        if symbol and val is not None:
            by_symbol[symbol] = val
    return by_symbol, latest_snapshot


def _cohort_confirmation(holdings: list[dict[str, str]], ess_by_symbol: dict[str, float]) -> dict:
    tech_vals: list[float] = []
    hard_vals: list[float] = []

    for row in holdings:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol or symbol not in ess_by_symbol:
            continue
        industry = _industry_normalized(row.get("industry") or "")
        score = ess_by_symbol[symbol]
        if industry == "TECHNOLOGY":
            tech_vals.append(score)
        elif industry in _HARD_ASSET_INDUSTRIES:
            hard_vals.append(score)

    def _share(values: Iterable[float], predicate) -> Optional[float]:
        values = list(values)
        if not values:
            return None
        return sum(1 for v in values if predicate(v)) / len(values)

    tech_bearish = _share(tech_vals, lambda v: v <= 2.0)
    hard_bullish = _share(hard_vals, lambda v: v >= 4.0)
    tech_avg = (sum(tech_vals) / len(tech_vals)) if tech_vals else None
    hard_avg = (sum(hard_vals) / len(hard_vals)) if hard_vals else None

    confirmation = bool(
        tech_bearish is not None
        and hard_bullish is not None
        and len(tech_vals) >= 2
        and len(hard_vals) >= 2
        and tech_bearish >= 0.35
        and hard_bullish >= 0.45
    )

    return {
        "tech_ess_avg": round(tech_avg, 3) if tech_avg is not None else None,
        "hard_assets_ess_avg": round(hard_avg, 3) if hard_avg is not None else None,
        "tech_bearish_share": round(tech_bearish, 3) if tech_bearish is not None else None,
        "hard_assets_bullish_share": round(hard_bullish, 3) if hard_bullish is not None else None,
        "tech_signal_coverage_count": len(tech_vals),
        "hard_assets_signal_coverage_count": len(hard_vals),
        "confirmation_passed": confirmation,
    }


def _select_replay_id(
    replay_inputs_rows: list[dict[str, str]],
    *,
    industry: str,
    preferred_cap: str = "",
) -> tuple[str, str]:
    if preferred_cap:
        caps = (preferred_cap,) + tuple(c for c in _CAP_PRIORITY if c != preferred_cap)
    else:
        caps = _CAP_PRIORITY

    for cap in caps:
        for row in replay_inputs_rows:
            if str(row.get("filter_geography") or "").strip().upper() != "US":
                continue
            if str(row.get("filter_market_cap_bucket") or "").strip().upper() != cap:
                continue
            if str(row.get("filter_industry") or "").strip().upper() != industry.upper():
                continue
            replay_id = str(row.get("replay_id") or "").strip()
            if replay_id:
                return replay_id, cap
    return "", ""


def _window_returns_for_replay(
    replay_perf_rows: list[dict[str, str]],
    replay_id: str,
    cap_bucket: str,
) -> Optional[SeriesWindowReturns]:
    points: list[tuple[str, float]] = []
    for row in replay_perf_rows:
        if str(row.get("replay_id") or "").strip() != replay_id:
            continue
        if str(row.get("series_type") or "").strip().upper() != "BENCHMARK":
            continue
        d = str(row.get("date") or "").strip()
        value = _safe_float(row.get("value"))
        if d and value is not None and value > 0:
            points.append((d, value))

    if len(points) < 2:
        return None

    points.sort(key=lambda x: x[0])
    latest_date = points[-1][0]
    out: dict[int, float] = {}
    for w in _WINDOWS:
        if len(points) <= w:
            continue
        older = points[-(w + 1)][1]
        latest = points[-1][1]
        if older > 0:
            out[w] = (latest / older) - 1.0

    if not out:
        return None
    return SeriesWindowReturns(
        replay_id=replay_id,
        market_cap_bucket=cap_bucket,
        latest_date=latest_date,
        returns=out,
    )


def _aggregate_hard_asset_returns(series: dict[str, SeriesWindowReturns]) -> dict[int, float]:
    out: dict[int, float] = {}
    for w in _WINDOWS:
        vals = [s.returns[w] for s in series.values() if w in s.returns]
        if vals:
            out[w] = sum(vals) / len(vals)
    return out


def _classify_signal(spreads: dict[int, float], confirmation: bool) -> tuple[str, str, int]:
    s5 = spreads.get(5)
    s20 = spreads.get(20)
    s60 = spreads.get(60)

    if s20 is None:
        return "DATA_UNAVAILABLE", "Insufficient 20-day proxy history for rotation inference.", 0

    if s20 >= 0.03 and (s5 is not None and s5 >= 0.01) and (confirmation or (s60 is not None and s60 >= 0.05)):
        return "ELEVATED_ROTATION_RISK", "Hard-asset proxies are outperforming technology with confirmation breadth.", 82

    if s20 >= 0.015:
        return "WATCHLIST_ROTATION", "Hard-asset outperformance is visible; confirmation is partial.", 64

    if s20 <= -0.015:
        return "TECH_LEADERSHIP", "Technology continues to lead hard-asset proxies over the 20-day window.", 28

    return "NO_CLEAR_SIGNAL", "Relative performance is mixed and does not indicate a clear rotation regime.", 48


def _upcoming_mei_events(repo_root: Path, days_ahead: int = 14) -> list[dict]:
    path = repo_root / "data" / "mei" / "event_calendar.json"
    if not path.exists():
        return []
    try:
        events = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    today = date.today()
    out: list[dict] = []
    for ev in events:
        d_raw = str(ev.get("event_date") or "")
        try:
            d = date.fromisoformat(d_raw[:10])
        except Exception:
            continue
        days = (d - today).days
        if 0 <= days <= days_ahead and str(ev.get("impact_level") or "").upper() == "HIGH":
            out.append(
                {
                    "event_id": ev.get("event_id", ""),
                    "event_name": ev.get("event_name", ""),
                    "event_date": d.isoformat(),
                    "days_away": days,
                    "sensitivity_tags": ev.get("sensitivity_tags", []),
                }
            )
    out.sort(key=lambda x: x.get("days_away", 9999))
    return out[:6]


def rotation_risk_summary(repo_root: Path, run_id: str = "") -> dict:
    """Build display-only rotation risk summary from existing repository artifacts."""
    as_of = date.today().isoformat()
    selected_run = run_id or _latest_run_id(repo_root)
    holdings = _load_holdings(repo_root, selected_run)

    exposure = _portfolio_exposure(holdings)
    ess_by_symbol, snapshot_date = _latest_signal_snapshot(repo_root)
    confirmation = _cohort_confirmation(holdings, ess_by_symbol)

    replay_inputs_path = repo_root / "data" / "current" / "replay_inputs.csv"
    replay_perf_path = repo_root / "data" / "current" / "replay_performance_series.csv"
    replay_inputs = _read_csv_rows(replay_inputs_path)
    replay_perf = _read_csv_rows(replay_perf_path)

    missing_inputs: list[str] = []
    if not replay_inputs:
        missing_inputs.append("replay_inputs.csv")
    if not replay_perf:
        missing_inputs.append("replay_performance_series.csv")

    tech_replay_id, selected_cap = _select_replay_id(replay_inputs, industry="TECHNOLOGY")
    tech_series = _window_returns_for_replay(replay_perf, tech_replay_id, selected_cap) if tech_replay_id else None

    hard_series: dict[str, SeriesWindowReturns] = {}
    hard_caps: dict[str, str] = {}
    for industry in _HARD_ASSET_INDUSTRIES:
        rid, cap = _select_replay_id(replay_inputs, industry=industry, preferred_cap=selected_cap)
        hard_caps[industry] = cap
        s = _window_returns_for_replay(replay_perf, rid, cap) if rid else None
        if s is not None:
            hard_series[industry] = s

    if tech_series is None:
        missing_inputs.append("TECHNOLOGY benchmark proxy")
    if len(hard_series) < 2:
        missing_inputs.append("hard-asset benchmark proxies")

    hard_returns = _aggregate_hard_asset_returns(hard_series)
    spreads: dict[int, float] = {}
    if tech_series is not None:
        for w in _WINDOWS:
            t = tech_series.returns.get(w)
            h = hard_returns.get(w)
            if t is not None and h is not None:
                spreads[w] = h - t

    signal, headline, risk_score = _classify_signal(spreads, confirmation["confirmation_passed"])

    prices_path = repo_root / "data" / "current" / "security_prices.csv"
    price_rows = _read_csv_rows(prices_path)
    price_status = "AVAILABLE" if price_rows else "EMPTY_OR_MISSING"

    status = "OK"
    if missing_inputs or signal == "DATA_UNAVAILABLE":
        status = "DATA_UNAVAILABLE"
        signal = "DATA_UNAVAILABLE"
        headline = "Core proxy data unavailable; rotation monitor is informationally disabled."
        risk_score = 0

    mei_events = _upcoming_mei_events(repo_root=repo_root, days_ahead=14)

    return {
        "status": status,
        "diagnostic_id": "ROTATION-RISK-01",
        "diagnostic_name": "Tech-to-hard-assets rotation monitor",
        "as_of_date": as_of,
        "run_id": selected_run,
        "signal": signal,
        "headline": headline,
        "risk_score": risk_score,
        "governance_note": "Display-only diagnostic; no effect on ESS, CW-DAS, UCF, CRA, PAP, replay, or execution behavior.",
        "portfolio_exposure": exposure,
        "proxy_returns": {
            "selected_cap_bucket": selected_cap or "",
            "latest_proxy_date": tech_series.latest_date if tech_series is not None else "",
            "tech_returns": {
                f"{w}d": round((tech_series.returns.get(w) or 0.0) * 100.0, 3)
                if tech_series is not None and w in tech_series.returns
                else None
                for w in _WINDOWS
            },
            "hard_assets_returns": {
                f"{w}d": round((hard_returns.get(w) or 0.0) * 100.0, 3)
                if w in hard_returns
                else None
                for w in _WINDOWS
            },
            "rotation_spread_pct": {
                f"{w}d": round((spreads.get(w) or 0.0) * 100.0, 3)
                if w in spreads
                else None
                for w in _WINDOWS
            },
            "hard_asset_industry_caps": hard_caps,
        },
        "confirmation": confirmation,
        "data_quality": {
            "price_history_status": price_status,
            "signal_snapshot_date": snapshot_date,
            "missing_inputs": missing_inputs,
            "hard_asset_proxy_count": len(hard_series),
        },
        "macro_context": {
            "upcoming_high_impact_events": mei_events,
        },
    }
