from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any


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
    threshold_days: int = 2,
) -> dict[str, Any]:
    """Return deterministic freshness classification for market regime proxy inputs."""
    market_parsed = _parse_timestamp_to_date(market_proxies_ts, label="market proxy")
    snapshot_parsed = _parse_timestamp_to_date(portfolio_snapshot_ts, label="portfolio snapshot")

    market_ts = market_parsed.get("value")
    snapshot_ts = snapshot_parsed.get("value")

    if not market_ts and not snapshot_ts:
        return {
            "freshness_status": "MISSING",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "REFRESH_MARKET_PROXIES",
            "warnings": ["Market proxy timestamp missing.", "Portfolio snapshot timestamp missing."],
        }

    if market_parsed.get("error") or snapshot_parsed.get("error"):
        return {
            "freshness_status": "UNKNOWN",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
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
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "REFRESH_MARKET_PROXIES",
            "warnings": ["Market proxy timestamp missing."],
        }

    if not snapshot_ts:
        return {
            "freshness_status": "PARTIAL",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "REFRESH_CURRENT_HOLDINGS_PLUS_BUY_CANDIDATES",
            "warnings": ["Portfolio snapshot timestamp missing; unable to compute proxy age."],
        }

    try:
        lag_days = max((date.fromisoformat(snapshot_ts) - date.fromisoformat(market_ts)).days, 0)
    except Exception:
        return {
            "freshness_status": "UNKNOWN",
            "market_proxy_age_days": None,
            "proxy_lag_days": None,
            "freshness_threshold_days": int(threshold_days),
            "operator_action": "VERIFY_TIMESTAMP_FORMATS",
            "warnings": [
                "Market proxy timestamp could not be parsed; verify timestamp format."
            ],
        }

    freshness_status = "FRESH" if lag_days <= threshold_days else "STALE"
    return {
        "freshness_status": freshness_status,
        "market_proxy_age_days": int(lag_days),
        "proxy_lag_days": int(lag_days),
        "freshness_threshold_days": int(threshold_days),
        "operator_action": "NONE" if freshness_status == "FRESH" else "REFRESH_MARKET_PROXIES",
        "warnings": [],
    }


def _as_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


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
