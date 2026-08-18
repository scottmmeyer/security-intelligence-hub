from __future__ import annotations

from pathlib import Path
from typing import Any

from src.portfolio.regime.market_regime_contract import MarketRegimeGuardrail, unknown_guardrail
from src.portfolio.regime.market_regime_inputs import normalized_rotation_context
from src.portfolio.regime.market_regime_proxy_artifacts import (
    LEGACY_REPLAY_FALLBACK_SOURCE,
    load_market_regime_rotation_summary,
)
from src.sih.rotation_risk_monitor import rotation_risk_summary


def build_market_regime_guardrail_from_rotation_summary(
    rotation_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    ctx = normalized_rotation_context(rotation_summary)
    freshness = ctx.get("freshness") if isinstance(ctx.get("freshness"), dict) else {}
    freshness_status = str(freshness.get("freshness_status") or "UNKNOWN").upper()
    freshness_warnings = [str(x) for x in list(freshness.get("warnings") or []) if str(x).strip()]

    if ctx["status"] == "DATA_UNAVAILABLE" or ctx["signal"] == "DATA_UNAVAILABLE":
        return unknown_guardrail(
            market_proxies_ts=ctx["market_proxies_ts"],
            portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
            reason="Market proxy data unavailable or stale; using conservative display-only posture.",
            freshness_status=freshness_status,
            proxy_lag_days=freshness.get("proxy_lag_days"),
            freshness_threshold_days=int(freshness.get("freshness_threshold_days") or 2),
            operator_action=str(freshness.get("operator_action") or "REFRESH_MARKET_PROXIES"),
            operator_summary=(
                "Market regime inputs are unavailable or stale. Use conservative posture: "
                "deploy cautiously, review overweights, and hold excess cash."
            ),
        ).to_dict()

    if freshness_status in {"STALE", "MISSING", "PARTIAL", "UNKNOWN"}:
        proxy_ts = str(ctx.get("market_proxies_ts") or "unknown")
        snapshot_ts = str(ctx.get("portfolio_snapshot_ts") or "unknown")
        lag = freshness.get("market_proxy_age_days")

        reason = (
            "Market proxy freshness is "
            f"{freshness_status.lower()}; using conservative display-only posture until market proxy refresh completes."
        )
        if freshness_status == "STALE" and isinstance(lag, int):
            reason = (
                "Market proxy data is stale: "
                f"proxy date {proxy_ts} is {lag} day(s) behind portfolio date {snapshot_ts}."
            )
        elif freshness_status == "UNKNOWN":
            reason = "Market proxy timestamp could not be parsed; verify timestamp format."
        elif freshness_status == "MISSING":
            reason = "Market proxy timestamp is missing; verify market proxy data availability."
        if ctx["missing_inputs"]:
            reason = (
                "Market proxy inputs incomplete: " + ", ".join(str(x) for x in ctx["missing_inputs"]) + ". " + reason
            )
        if freshness_warnings:
            reason = reason + " " + " ".join(freshness_warnings)
        return unknown_guardrail(
            market_proxies_ts=ctx["market_proxies_ts"],
            portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
            reason=reason,
            freshness_status=freshness_status,
            proxy_lag_days=freshness.get("proxy_lag_days"),
            freshness_threshold_days=int(freshness.get("freshness_threshold_days") or 2),
            operator_action=str(freshness.get("operator_action") or "REFRESH_MARKET_PROXIES"),
        ).to_dict()

    raw = ctx["raw"]
    market_proxies = raw.get("market_proxies") or {}
    soxx_vs_spy = _f(market_proxies.get("soxx_vs_spy"))
    qqq_vs_spy = _f(market_proxies.get("qqq_vs_spy"))
    soxx_drawdown = _f(market_proxies.get("soxx_drawdown_pct"))
    soxx_below_20d = bool(market_proxies.get("soxx_below_20d")) if "soxx_below_20d" in market_proxies else None
    soxx_below_50d = bool(market_proxies.get("soxx_below_50d")) if "soxx_below_50d" in market_proxies else None

    evidence: list[str] = []
    spread_vals = [v for v in (ctx["spread_5d"], ctx["spread_20d"], ctx["spread_60d"]) if v is not None]
    positive_spreads = sum(1 for v in spread_vals if v > 0)
    negative_spreads = sum(1 for v in spread_vals if v < 0)
    tech_negative = sum(1 for v in (ctx["tech_5d"], ctx["tech_20d"], ctx["tech_60d"]) if v is not None and v < 0)

    # SEMI_AI_PULLBACK requires explicit semiconductor/high-beta proxy inputs.
    if (
        soxx_vs_spy is not None
        and qqq_vs_spy is not None
        and soxx_drawdown is not None
        and soxx_below_20d is not None
        and soxx_below_50d is not None
        and soxx_vs_spy < 0
        and qqq_vs_spy < 0
        and (soxx_drawdown <= -5.0 or (soxx_below_20d and soxx_below_50d))
    ):
        evidence.extend(
            [
                "Semiconductor proxy underperforming broad market.",
                "High-beta technology proxy underperforming broad market.",
                "Semiconductor trend weakness or drawdown threshold met.",
            ]
        )
        return _build_payload(
            regime="SEMI_AI_PULLBACK",
            severity="MODERATE",
            deployment_posture="PAUSE_NEW_BUYS",
            trim_posture="TRIM_WEAK_SIGNALS_ONLY",
            cash_posture="HOLD_EXCESS",
            confidence="MEDIUM",
            safe_to_deploy=False,
            operator_summary=(
                "Semiconductor and high-beta technology are under stress versus broad market. "
                "Pause stressed-sector adds; trim only deteriorating weak-signal names."
            ),
            evidence=evidence,
            stressed_sectors=["SEMI", "HIGH_BETA_TECH"],
            affected_symbols=_extract_symbols(raw),
            market_proxies_ts=ctx["market_proxies_ts"],
            portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
            data_freshness=freshness,
            recommended_operator_checks=[
                "Pause new buys in stressed sectors.",
                "Review overweights in semi/AI concentration sleeves.",
                "Trim only weak-signal deteriorating names.",
                "Avoid panic-selling high-conviction winners without signal deterioration.",
            ],
        )

    if positive_spreads >= 3 and tech_negative >= 2 and ctx["signal"] in {"ELEVATED_ROTATION_RISK", "WATCHLIST_ROTATION"}:
        evidence.extend(
            [
                "Risk proxies show broad defensive outperformance versus technology.",
                "Technology proxy returns are negative across multiple windows.",
            ]
        )
        return _build_payload(
            regime="BROAD_RISK_OFF",
            severity="HIGH" if ctx["risk_score"] >= 70 else "MODERATE",
            deployment_posture="HOLD_CASH_RESERVE",
            trim_posture="RAISE_CASH_FROM_DETERIORATING_NAMES",
            cash_posture="RAISE_RESERVE",
            confidence="MEDIUM",
            safe_to_deploy=False,
            operator_summary=(
                "Broad risk-off posture detected. Preserve liquidity, avoid new risk adds, "
                "and raise cash only from deteriorating names."
            ),
            evidence=evidence,
            stressed_sectors=["HIGH_BETA_TECH"],
            affected_symbols=_extract_symbols(raw),
            market_proxies_ts=ctx["market_proxies_ts"],
            portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
            data_freshness=freshness,
            recommended_operator_checks=[
                "Hold cash reserve and defer discretionary buys.",
                "Use reduction queue to identify deteriorating names.",
                "Avoid broad de-risking of high-conviction winners absent signal deterioration.",
            ],
        )

    if positive_spreads >= 2 and ctx["signal"] in {"ELEVATED_ROTATION_RISK", "WATCHLIST_ROTATION"}:
        evidence.extend(
            [
                "Defensive/cyclical sectors are outperforming technology proxies.",
                "Rotation stress visible, but not a full broad risk-off confirmation.",
            ]
        )
        return _build_payload(
            regime="DEFENSIVE_ROTATION",
            severity="MODERATE",
            deployment_posture="ONLY_NON_STRESSED_SECTORS",
            trim_posture="REVIEW_OVERWEIGHTS",
            cash_posture="HOLD_EXCESS",
            confidence="MEDIUM",
            safe_to_deploy=False,
            operator_summary=(
                "Defensive rotation underway. Restrict new deployment to non-stressed sectors and "
                "review concentrated overweights before adding risk."
            ),
            evidence=evidence,
            stressed_sectors=["HIGH_BETA_TECH"],
            affected_symbols=_extract_symbols(raw),
            market_proxies_ts=ctx["market_proxies_ts"],
            portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
            data_freshness=freshness,
            recommended_operator_checks=[
                "Prefer non-stressed sector deployment candidates.",
                "Review concentration nodes before adding exposure.",
                "Keep weak-signal trim candidates prioritized.",
            ],
        )

    if ctx["confirmation_passed"] and negative_spreads >= 1 and ctx["signal"] in {"NO_CLEAR_SIGNAL", "WATCHLIST_ROTATION"}:
        evidence.extend(
            [
                "Stressed sectors are regaining relative strength versus defensive proxies.",
                "Confirmation signals indicate improving regime stability.",
            ]
        )
        return _build_payload(
            regime="RECOVERY_CONFIRMATION",
            severity="LOW",
            deployment_posture="CAUTION_DEPLOY",
            trim_posture="HOLD_WINNERS",
            cash_posture="DEPLOY_EXCESS",
            confidence="MEDIUM",
            safe_to_deploy=True,
            operator_summary=(
                "Recovery confirmation is improving. Resume deployment cautiously while preserving "
                "conviction winners and monitoring stress proxies."
            ),
            evidence=evidence,
            stressed_sectors=[],
            affected_symbols=_extract_symbols(raw),
            market_proxies_ts=ctx["market_proxies_ts"],
            portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
            data_freshness=freshness,
            recommended_operator_checks=[
                "Deploy excess cash in tranches.",
                "Prefer candidates with fresh strong signal agreement.",
                "Continue monitoring rotation proxies for reversal risk.",
            ],
        )

    if ctx["confirmation_passed"] and abs(ctx["spread_20d"] or 0.0) < 0.35 and ctx["signal"] == "NO_CLEAR_SIGNAL":
        evidence.append("No material stress or defensive-rotation signal detected in available proxies.")
        return _build_payload(
            regime="NORMAL",
            severity="LOW",
            deployment_posture="NORMAL_DEPLOY",
            trim_posture="HOLD_WINNERS",
            cash_posture="DEPLOY_EXCESS",
            confidence="MEDIUM",
            safe_to_deploy=True,
            operator_summary="Market posture appears stable in current display-only proxy set.",
            evidence=evidence,
            stressed_sectors=[],
            affected_symbols=_extract_symbols(raw),
            market_proxies_ts=ctx["market_proxies_ts"],
            portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
            data_freshness=freshness,
            recommended_operator_checks=[
                "Proceed with normal deployment discipline.",
                "Maintain weak-signal trim discipline for deteriorating names.",
            ],
        )

    reason = "Market regime signal is inconclusive with fresh proxy inputs; using conservative display-only posture."
    operator_summary = (
        "Market regime is currently UNKNOWN with fresh proxy inputs and inconclusive regime evidence. "
        "Use conservative posture while waiting for a clearer regime confirmation."
    )
    if ctx["missing_inputs"]:
        reason = (
            "Market proxy inputs incomplete: " + ", ".join(str(x) for x in ctx["missing_inputs"]) + ". "
            "Using conservative display-only posture."
        )
        operator_summary = (
            "Market proxy inputs are incomplete. Use conservative posture until required inputs are restored."
        )
    return unknown_guardrail(
        market_proxies_ts=ctx["market_proxies_ts"],
        portfolio_snapshot_ts=ctx["portfolio_snapshot_ts"],
        reason=reason,
        freshness_status=freshness_status,
        proxy_lag_days=freshness.get("proxy_lag_days"),
        freshness_threshold_days=int(freshness.get("freshness_threshold_days") or 2),
        operator_action=str(freshness.get("operator_action") or "REFRESH_MARKET_PROXIES"),
        operator_summary=operator_summary,
    ).to_dict()


def market_regime_guardrail_latest(repo_root: Path, run_id: str = "") -> dict[str, Any]:
    input_source = LEGACY_REPLAY_FALLBACK_SOURCE
    try:
        dedicated_rotation, source_label, warnings = load_market_regime_rotation_summary(repo_root=repo_root)
        if dedicated_rotation is not None:
            rotation = dedicated_rotation
            input_source = source_label
        elif source_label == LEGACY_REPLAY_FALLBACK_SOURCE:
            rotation = rotation_risk_summary(repo_root=repo_root, run_id=run_id)
            input_source = LEGACY_REPLAY_FALLBACK_SOURCE
        else:
            reason = "Dedicated market regime proxy artifact is invalid; replay fallback is disabled when dedicated artifact is present."
            if warnings:
                reason = reason + " " + " ".join(str(x) for x in warnings)
            payload = unknown_guardrail(reason=reason).to_dict()
            payload["scoring_impact"] = "none"
            payload["input_source"] = source_label
            return payload
    except Exception:
        rotation = None
    payload = build_market_regime_guardrail_from_rotation_summary(rotation)
    payload["scoring_impact"] = "none"
    payload["input_source"] = input_source
    return payload


def _build_payload(
    *,
    regime: str,
    severity: str,
    deployment_posture: str,
    trim_posture: str,
    cash_posture: str,
    confidence: str,
    safe_to_deploy: bool,
    operator_summary: str,
    evidence: list[str],
    stressed_sectors: list[str],
    affected_symbols: list[str],
    market_proxies_ts: str | None,
    portfolio_snapshot_ts: str | None,
    data_freshness: dict[str, Any] | None,
    recommended_operator_checks: list[str],
) -> dict[str, Any]:
    freshness = data_freshness if isinstance(data_freshness, dict) else {}
    return MarketRegimeGuardrail(
        regime=regime,
        severity=severity,
        deployment_posture=deployment_posture,
        trim_posture=trim_posture,
        cash_posture=cash_posture,
        operator_summary=operator_summary,
        evidence=evidence,
        affected_symbols=sorted(set(affected_symbols)),
        stressed_sectors=sorted(set(stressed_sectors)),
        safe_to_deploy=bool(safe_to_deploy),
        confidence=confidence,
        data_freshness={
            "market_proxies_ts": market_proxies_ts,
            "portfolio_snapshot_ts": portfolio_snapshot_ts,
            "freshness_status": str(freshness.get("freshness_status") or "UNKNOWN"),
            "market_proxy_age_days": freshness.get("market_proxy_age_days"),
            "proxy_lag_days": freshness.get("proxy_lag_days"),
            "freshness_threshold_days": int(freshness.get("freshness_threshold_days") or 2),
            "operator_action": str(freshness.get("operator_action") or "VERIFY_TIMESTAMP_FORMATS"),
        },
        guardrail_version="MRG-1.0",
        recommended_operator_checks=recommended_operator_checks,
        scoring_impact="none",
    ).to_dict()


def _extract_symbols(payload: dict[str, Any]) -> list[str]:
    out: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            symbol = str(node.get("symbol") or "").strip().upper()
            if symbol:
                out.add(symbol)
            affected = node.get("affected_symbols")
            if isinstance(affected, list):
                for s in affected:
                    ss = str(s or "").strip().upper()
                    if ss:
                        out.add(ss)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload.get("today_operator_action_plan") or {})
    return sorted(out)


def _f(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None
