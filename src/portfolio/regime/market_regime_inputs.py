from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from src.portfolio.regime.market_regime_sessions import trading_session_lag_from_proxy_and_evaluation


def normalized_rotation_context(rotation_summary: dict[str, Any] | None) -> dict[str, Any]:
    data = deepcopy(rotation_summary or {})

    proxy_returns = data.get("proxy_returns") or {}
    spread = proxy_returns.get("rotation_spread_pct") or {}
    tech_returns = proxy_returns.get("tech_returns") or {}
    latest_proxy_date_raw = proxy_returns.get("latest_proxy_date")
    latest_proxy_date = str(latest_proxy_date_raw).strip() if latest_proxy_date_raw is not None else None
    if latest_proxy_date == "":
        latest_proxy_date = None

    data_quality = data.get("data_quality") or {}

    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts=latest_proxy_date,
        portfolio_snapshot_ts=data.get("as_of_date"),
        freshness_evaluation_ts=data.get("freshness_evaluation_ts"),
    )

    return {
        "status": str(data.get("status") or "DATA_UNAVAILABLE").upper(),
        "signal": str(data.get("signal") or "DATA_UNAVAILABLE").upper(),
        "risk_score": float(data.get("risk_score") or 0.0),
        "confirmation_passed": bool((data.get("confirmation") or {}).get("confirmation_passed")),
        "spread_5d": _as_float(spread.get("5d")),
        "spread_20d": _as_float(spread.get("20d")),
        "spread_60d": _as_float(spread.get("60d")),
        "tech_5d": _as_float(tech_returns.get("5d")),
        "tech_20d": _as_float(tech_returns.get("20d")),
        "tech_60d": _as_float(tech_returns.get("60d")),
        "tech_pct": _as_float((data.get("portfolio_exposure") or {}).get("tech_pct")),
        "market_proxies_ts": latest_proxy_date,
        "portfolio_snapshot_ts": data.get("as_of_date"),
        "freshness": freshness,
        "missing_inputs": list(data_quality.get("missing_inputs") or []),
        "raw": data,
    }


def evaluate_market_proxy_freshness(
    *,
    market_proxies_ts: Any,
    portfolio_snapshot_ts: Any,
    freshness_evaluation_ts: Any = None,
    threshold_days: int = 2,
) -> dict[str, Any]:
    """Return deterministic freshness classification for market regime proxy inputs."""
    market_parsed = _parse_timestamp_to_date(market_proxies_ts, label="market proxy")
    snapshot_parsed = _parse_timestamp_to_date(portfolio_snapshot_ts, label="portfolio snapshot")

    market_ts = market_parsed.get("value")
    snapshot_ts = snapshot_parsed.get("value")

    evaluation_dt, evaluation_error, evaluation_source = _resolve_freshness_evaluation_time(
        portfolio_snapshot_ts=portfolio_snapshot_ts,
        freshness_evaluation_ts=freshness_evaluation_ts,
    )

    if not market_ts and not snapshot_ts:
        return {
            "freshness_status": "MISSING",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "calendar_lag_days": None,
            "trading_session_lag": None,
            "freshness_basis": "TRADING_SESSIONS",
            "missed_session": None,
            "expected_session": None,
            "freshness_evaluation_ts": _serialize_iso(evaluation_dt),
            "freshness_evaluation_source": evaluation_source,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "REFRESH_MARKET_PROXIES",
            "warnings": ["Market proxy timestamp missing.", "Portfolio snapshot timestamp missing."],
        }

    if market_parsed.get("error") or snapshot_parsed.get("error"):
        return {
            "freshness_status": "UNKNOWN",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "calendar_lag_days": None,
            "trading_session_lag": None,
            "freshness_basis": "TRADING_SESSIONS",
            "missed_session": None,
            "expected_session": None,
            "freshness_evaluation_ts": _serialize_iso(evaluation_dt),
            "freshness_evaluation_source": evaluation_source,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "VERIFY_TIMESTAMP_FORMATS",
            "warnings": [
                msg
                for msg in [market_parsed.get("error"), snapshot_parsed.get("error")]
                if msg
            ],
        }

    if not market_ts:
        return {
            "freshness_status": "MISSING",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "calendar_lag_days": None,
            "trading_session_lag": None,
            "freshness_basis": "TRADING_SESSIONS",
            "missed_session": None,
            "expected_session": None,
            "freshness_evaluation_ts": _serialize_iso(evaluation_dt),
            "freshness_evaluation_source": evaluation_source,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "REFRESH_MARKET_PROXIES",
            "warnings": ["Market proxy timestamp missing."],
        }

    if not snapshot_ts:
        return {
            "freshness_status": "PARTIAL",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "calendar_lag_days": None,
            "trading_session_lag": None,
            "freshness_basis": "TRADING_SESSIONS",
            "missed_session": None,
            "expected_session": None,
            "freshness_evaluation_ts": _serialize_iso(evaluation_dt),
            "freshness_evaluation_source": evaluation_source,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "REFRESH_CURRENT_HOLDINGS_PLUS_BUY_CANDIDATES",
            "warnings": ["Portfolio snapshot timestamp missing; unable to compute proxy age."],
        }

    if evaluation_dt is None:
        return {
            "freshness_status": "UNKNOWN",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "calendar_lag_days": None,
            "trading_session_lag": None,
            "freshness_basis": "TRADING_SESSIONS",
            "missed_session": None,
            "expected_session": None,
            "freshness_evaluation_ts": None,
            "freshness_evaluation_source": evaluation_source,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "VALIDATE_PROXY_AND_SNAPSHOT_TIMESTAMPS",
            "warnings": [
                str(evaluation_error or "Portfolio snapshot and evaluation timestamps do not permit a safe freshness evaluation.")
            ],
        }

    try:
        calendar_lag_days = (date.fromisoformat(snapshot_ts) - date.fromisoformat(market_ts)).days
    except Exception:
        return {
            "freshness_status": "UNKNOWN",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "calendar_lag_days": None,
            "trading_session_lag": None,
            "freshness_basis": "TRADING_SESSIONS",
            "missed_session": None,
            "expected_session": None,
            "freshness_evaluation_ts": _serialize_iso(evaluation_dt),
            "freshness_evaluation_source": evaluation_source,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "VERIFY_TIMESTAMP_FORMATS",
            "warnings": [
                "Market proxy timestamp could not be parsed; verify timestamp format."
            ],
        }

    session_lag = trading_session_lag_from_proxy_and_evaluation(
        proxy_session=market_proxies_ts,
        evaluation_time=evaluation_dt,
    )
    lag_sessions = session_lag.trading_session_lag

    if lag_sessions is None:
        return {
            "freshness_status": "UNKNOWN",
            "market_proxy_age_days": int(calendar_lag_days),
            "proxy_lag_days": int(calendar_lag_days),
            "calendar_lag_days": int(calendar_lag_days),
            "trading_session_lag": None,
            "freshness_basis": "TRADING_SESSIONS",
            "missed_session": session_lag.missed_session,
            "expected_session": session_lag.expected_session,
            "expected_session_close_utc": session_lag.expected_session_close_utc,
            "freshness_evaluation_ts": _serialize_iso(evaluation_dt),
            "freshness_evaluation_source": evaluation_source,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "VALIDATE_PROXY_AND_SNAPSHOT_TIMESTAMPS",
            "warnings": [str(w) for w in session_lag.warnings if str(w).strip()],
        }

    if lag_sessions <= 1:
        freshness_status = "FRESH"
        operator_action = "NONE"
    elif lag_sessions == 2:
        freshness_status = "DEGRADED"
        operator_action = "VALIDATE_PROXY_AND_SNAPSHOT_TIMESTAMPS"
    else:
        freshness_status = "STALE"
        operator_action = "REFRESH_MARKET_PROXIES"

    return {
        "freshness_status": freshness_status,
        "market_proxy_age_days": int(calendar_lag_days),
        "proxy_lag_days": int(calendar_lag_days),
        "calendar_lag_days": int(calendar_lag_days),
        "trading_session_lag": int(lag_sessions),
        "freshness_basis": "TRADING_SESSIONS",
        "missed_session": bool(session_lag.missed_session),
        "expected_session": session_lag.expected_session,
        "expected_session_close_utc": session_lag.expected_session_close_utc,
        "freshness_evaluation_ts": _serialize_iso(evaluation_dt),
        "freshness_evaluation_source": evaluation_source,
        "freshness_threshold_days": int(threshold_days),
        "operator_action": operator_action,
        "warnings": [str(w) for w in session_lag.warnings if str(w).strip()],
    }


def _as_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _render_market_local_now() -> datetime:
    return _utc_now().astimezone(ZoneInfo("America/New_York"))


def _serialize_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _resolve_freshness_evaluation_time(
    *,
    portfolio_snapshot_ts: Any,
    freshness_evaluation_ts: Any = None,
) -> tuple[datetime | None, str | None, str]:
    if freshness_evaluation_ts is not None:
        parsed, error = _parse_evaluation_time(freshness_evaluation_ts)
        return parsed, error, "freshness_evaluation_ts"

    if isinstance(portfolio_snapshot_ts, datetime):
        return portfolio_snapshot_ts, None, "portfolio_snapshot_timestamp"

    if isinstance(portfolio_snapshot_ts, date):
        snapshot_date = portfolio_snapshot_ts
    else:
        raw = str(portfolio_snapshot_ts or "").strip()
        if not raw:
            return None, "Portfolio snapshot timestamp missing.", "missing_portfolio_snapshot_ts"

        if _looks_like_explicit_timestamp(raw):
            parsed, error = _parse_evaluation_time(raw)
            return parsed, error, "portfolio_snapshot_timestamp"

        try:
            snapshot_date = date.fromisoformat(raw)
        except Exception:
            parsed, error = _parse_evaluation_time(raw)
            if parsed is not None:
                return parsed, error, "portfolio_snapshot_timestamp"
            return None, str(error or "Portfolio snapshot timestamp could not be parsed."), "portfolio_snapshot_timestamp"

    current_market_date = _render_market_local_now().date()
    if snapshot_date > current_market_date:
        return None, (
            f"Portfolio snapshot date {snapshot_date.isoformat()} is in the future relative to "
            f"market-local current date {current_market_date.isoformat()}; fail closed."
        ), "future_portfolio_snapshot"

    if snapshot_date == current_market_date:
        return _utc_now(), None, "runtime_now"

    return datetime.combine(snapshot_date, time(23, 59, 59), tzinfo=ZoneInfo("America/New_York")), None, "historical_snapshot_date"


def _looks_like_explicit_timestamp(value: str) -> bool:
    raw = str(value or "").strip()
    return bool(raw) and ("T" in raw or " " in raw or raw.endswith("Z") or ":" in raw[10:])


def _coerce_snapshot_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except Exception:
        pass
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except Exception:
        return None


def _parse_evaluation_time(v: Any) -> tuple[datetime | None, str | None]:
    market_tz = ZoneInfo("America/New_York")

    if v is None:
        return None, "Evaluation timestamp missing."

    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=market_tz), None
        return v, None

    if isinstance(v, date):
        return datetime.combine(v, time(23, 59, 59), tzinfo=market_tz), None

    raw = str(v).strip()
    if not raw:
        return None, "Evaluation timestamp missing."

    try:
        d = date.fromisoformat(raw)
        return datetime.combine(d, time(23, 59, 59), tzinfo=market_tz), None
    except Exception:
        pass

    normalized = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=market_tz), None
        return dt, None
    except Exception:
        return None, f"Evaluation timestamp could not be parsed: {raw}"


def _parse_timestamp_to_date(v: Any, *, label: str) -> dict[str, str | None]:
    if v is None:
        return {"value": None, "error": None}

    if isinstance(v, datetime):
        return {"value": v.date().isoformat(), "error": None}

    if isinstance(v, date):
        return {"value": v.isoformat(), "error": None}

    raw = str(v).strip()
    if not raw:
        return {"value": None, "error": None}

    try:
        return {"value": date.fromisoformat(raw).isoformat(), "error": None}
    except Exception:
        pass

    normalized = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return {"value": dt.date().isoformat(), "error": None}
    except Exception:
        return {
            "value": None,
            "error": f"{label.capitalize()} timestamp could not be parsed; verify timestamp format: {raw}",
        }
