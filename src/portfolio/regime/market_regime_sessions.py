from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


@dataclass(frozen=True)
class TradingSessionLagResult:
    expected_session: str | None
    expected_session_close_utc: str | None
    trading_session_lag: int | None
    missed_session: bool | None
    warnings: list[str]


def trading_session_lag_from_proxy_and_evaluation(
    *,
    proxy_session: Any,
    evaluation_time: Any,
    calendar_name: str = "XNYS",
) -> TradingSessionLagResult:
    proxy_session_date, proxy_error = _parse_session_date(proxy_session)
    evaluation_dt, eval_error = _parse_evaluation_time(evaluation_time)

    warnings: list[str] = []
    if proxy_error:
        warnings.append(proxy_error)
    if eval_error:
        warnings.append(eval_error)
    if proxy_session_date is None or evaluation_dt is None:
        return TradingSessionLagResult(
            expected_session=None,
            expected_session_close_utc=None,
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings,
        )

    try:
        import exchange_calendars as xc
    except Exception:
        return TradingSessionLagResult(
            expected_session=None,
            expected_session_close_utc=None,
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings + ["Exchange calendar package unavailable."],
        )

    try:
        cal = xc.get_calendar(calendar_name)
    except Exception as exc:
        return TradingSessionLagResult(
            expected_session=None,
            expected_session_close_utc=None,
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings + [f"Exchange calendar unavailable: {exc}"],
        )

    market_tz = ZoneInfo(str(cal.tz))
    eval_market = evaluation_dt.astimezone(market_tz)
    eval_date = pd.Timestamp(eval_market.date())

    try:
        expected = _latest_completed_session(cal, eval_date, evaluation_dt)
    except Exception as exc:
        return TradingSessionLagResult(
            expected_session=None,
            expected_session_close_utc=None,
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings + [f"Could not resolve expected session: {exc}"],
        )

    if expected is None:
        return TradingSessionLagResult(
            expected_session=None,
            expected_session_close_utc=None,
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings + ["Expected session unavailable from exchange calendar."],
        )

    proxy_ts = pd.Timestamp(proxy_session_date.isoformat())
    expected_date = expected.date()

    try:
        if not cal.is_session(proxy_ts):
            return TradingSessionLagResult(
                expected_session=expected_date.isoformat(),
                expected_session_close_utc=cal.session_close(expected).isoformat(),
                trading_session_lag=None,
                missed_session=None,
                warnings=warnings + [
                    f"Proxy session is not an exchange trading session: {proxy_session_date.isoformat()}"
                ],
            )
    except Exception as exc:
        return TradingSessionLagResult(
            expected_session=expected_date.isoformat(),
            expected_session_close_utc=cal.session_close(expected).isoformat(),
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings + [f"Could not validate proxy session: {exc}"],
        )

    if proxy_session_date > expected_date:
        return TradingSessionLagResult(
            expected_session=expected_date.isoformat(),
            expected_session_close_utc=cal.session_close(expected).isoformat(),
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings + [
                "Proxy session occurs after expected completed session; refusing to classify as fresh."
            ],
        )

    try:
        sessions = cal.sessions_in_range(proxy_ts, expected)
    except Exception as exc:
        return TradingSessionLagResult(
            expected_session=expected_date.isoformat(),
            expected_session_close_utc=cal.session_close(expected).isoformat(),
            trading_session_lag=None,
            missed_session=None,
            warnings=warnings + [f"Could not compute trading-session lag: {exc}"],
        )

    lag = max(len(sessions) - 1, 0)
    return TradingSessionLagResult(
        expected_session=expected_date.isoformat(),
        expected_session_close_utc=cal.session_close(expected).isoformat(),
        trading_session_lag=int(lag),
        missed_session=bool(lag >= 1),
        warnings=warnings,
    )


def _latest_completed_session(cal: Any, eval_date: pd.Timestamp, evaluation_dt: datetime) -> pd.Timestamp | None:
    eval_utc = pd.Timestamp(evaluation_dt.astimezone(timezone.utc))
    if cal.is_session(eval_date):
        session = cal.date_to_session(eval_date, direction="none")
        session_close = cal.session_close(session)
        if eval_utc >= session_close:
            return session
        return cal.previous_session(session)
    return cal.date_to_session(eval_date, direction="previous")


def _parse_session_date(v: Any) -> tuple[date | None, str | None]:
    if v is None:
        return None, "Proxy session timestamp missing."
    if isinstance(v, datetime):
        return v.date(), None
    if isinstance(v, date):
        return v, None

    raw = str(v).strip()
    if not raw:
        return None, "Proxy session timestamp missing."

    try:
        return date.fromisoformat(raw), None
    except Exception:
        pass

    normalized = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return dt.date(), None
    except Exception:
        return None, f"Proxy session timestamp could not be parsed: {raw}"


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