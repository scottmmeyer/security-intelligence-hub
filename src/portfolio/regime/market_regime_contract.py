from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

REGIMES = {
    "NORMAL",
    "SEMI_AI_PULLBACK",
    "BROAD_RISK_OFF",
    "DEFENSIVE_ROTATION",
    "RECOVERY_CONFIRMATION",
    "UNKNOWN",
}

SEVERITIES = {"LOW", "MODERATE", "HIGH"}

DEPLOYMENT_POSTURES = {
    "NORMAL_DEPLOY",
    "CAUTION_DEPLOY",
    "PAUSE_NEW_BUYS",
    "ONLY_NON_STRESSED_SECTORS",
    "HOLD_CASH_RESERVE",
}

TRIM_POSTURES = {
    "HOLD_WINNERS",
    "REVIEW_OVERWEIGHTS",
    "TRIM_WEAK_SIGNALS_ONLY",
    "RAISE_CASH_FROM_DETERIORATING_NAMES",
}

CASH_POSTURES = {
    "DEPLOY_EXCESS",
    "HOLD_EXCESS",
    "RAISE_RESERVE",
}

CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW"}
FRESHNESS_STATUSES = {"FRESH", "STALE", "PARTIAL", "MISSING", "UNKNOWN"}
FRESHNESS_ACTIONS = {
    "NONE",
    "REFRESH_MARKET_PROXIES",
    "REFRESH_CURRENT_HOLDINGS_PLUS_BUY_CANDIDATES",
    "VALIDATE_PROXY_AND_SNAPSHOT_TIMESTAMPS",
    "VERIFY_TIMESTAMP_FORMATS",
}


@dataclass(frozen=True)
class MarketRegimeGuardrail:
    regime: str
    severity: str
    deployment_posture: str
    trim_posture: str
    cash_posture: str
    operator_summary: str
    evidence: list[str]
    affected_symbols: list[str]
    stressed_sectors: list[str]
    safe_to_deploy: bool
    confidence: str
    data_freshness: dict[str, Any]
    guardrail_version: str
    recommended_operator_checks: list[str]
    scoring_impact: str = "none"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scoring_impact"] = "none"
        return payload


def validate_guardrail_payload(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("regime") not in REGIMES:
        issues.append("invalid_regime")
    if payload.get("severity") not in SEVERITIES:
        issues.append("invalid_severity")
    if payload.get("deployment_posture") not in DEPLOYMENT_POSTURES:
        issues.append("invalid_deployment_posture")
    if payload.get("trim_posture") not in TRIM_POSTURES:
        issues.append("invalid_trim_posture")
    if payload.get("cash_posture") not in CASH_POSTURES:
        issues.append("invalid_cash_posture")
    if payload.get("confidence") not in CONFIDENCE_LEVELS:
        issues.append("invalid_confidence")
    if payload.get("scoring_impact") != "none":
        issues.append("invalid_scoring_impact")
    freshness = payload.get("data_freshness")
    if not isinstance(freshness, dict):
        issues.append("invalid_data_freshness")
    else:
        if freshness.get("freshness_status") not in FRESHNESS_STATUSES:
            issues.append("invalid_freshness_status")
        action = freshness.get("operator_action")
        if action is not None and action not in FRESHNESS_ACTIONS:
            issues.append("invalid_freshness_operator_action")
    return issues


def unknown_guardrail(
    *,
    market_proxies_ts: str | None = None,
    portfolio_snapshot_ts: str | None = None,
    reason: str = "Market regime signal is inconclusive; using conservative display-only posture.",
    freshness_status: str = "UNKNOWN",
    proxy_lag_days: int | None = None,
    freshness_threshold_days: int = 2,
    operator_action: str = "REFRESH_MARKET_PROXIES",
    operator_summary: str | None = None,
) -> MarketRegimeGuardrail:
    freshness = str(freshness_status or "UNKNOWN").upper()
    if operator_summary is None:
        if freshness == "FRESH":
            operator_summary = (
                "Market regime is currently UNKNOWN despite fresh inputs. "
                "Use conservative posture: deploy cautiously, review overweights, and hold excess cash."
            )
        else:
            operator_summary = (
                "Market regime inputs are unavailable or stale. Use conservative posture: "
                "deploy cautiously, review overweights, and hold excess cash."
            )

    return MarketRegimeGuardrail(
        regime="UNKNOWN",
        severity="LOW",
        deployment_posture="CAUTION_DEPLOY",
        trim_posture="REVIEW_OVERWEIGHTS",
        cash_posture="HOLD_EXCESS",
        operator_summary=operator_summary,
        evidence=[reason],
        affected_symbols=[],
        stressed_sectors=[],
        safe_to_deploy=False,
        confidence="LOW",
        data_freshness={
            "market_proxies_ts": market_proxies_ts,
            "portfolio_snapshot_ts": portfolio_snapshot_ts,
            "freshness_status": freshness_status,
            "market_proxy_age_days": proxy_lag_days,
            "proxy_lag_days": proxy_lag_days,
            "freshness_threshold_days": int(freshness_threshold_days),
            "operator_action": operator_action,
        },
        guardrail_version="MRG-1.0",
        recommended_operator_checks=[
            "Confirm replay/market proxy freshness before changing posture.",
            "Review reduction queue for weak-signal names.",
            "Avoid panic-selling high-conviction winners without signal deterioration.",
        ],
    )
