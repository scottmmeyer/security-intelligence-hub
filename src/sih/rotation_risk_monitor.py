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
from statistics import mean
from typing import Iterable, Optional


_WINDOWS = (5, 20, 60)
_CAP_PRIORITY = ("LARGE", "MEGA", "MID", "SMALL", "MICRO")
_HARD_ASSET_INDUSTRIES = ("ENERGY", "BASIC MATERIALS", "INDUSTRIALS")

# COMMODITY-CANDIDATE-GAP-01
# Display-only registry for hard-asset sleeve completion candidates.
# This registry is advisory and must not influence ranking/deployment logic.
_HARD_ASSET_CANDIDATE_REGISTRY: dict[str, dict[str, list[dict[str, str]]]] = {
    "COMMODITIES.GOLD": {
        "direct_completion": [
            {
                "symbol": "GLD",
                "vehicle_type": "ETF",
                "classification_note": "Mapped to COMMODITIES sleeve via existing portfolio taxonomy.",
                "rationale": "Broad gold exposure for direct sleeve completion.",
            },
            {
                "symbol": "IAU",
                "vehicle_type": "ETF",
                "classification_note": "Mapped to COMMODITIES sleeve via existing portfolio taxonomy.",
                "rationale": "Cost-efficient gold exposure for direct sleeve completion.",
            },
            {
                "symbol": "SGOL",
                "vehicle_type": "ETF",
                "classification_note": "Display-only candidate for gold sleeve completion review.",
                "rationale": "Physical gold ETF alternative; operator should review structure and tax profile.",
            },
        ],
        "equity_adjacent_proxies": [
            {
                "symbol": "KGC",
                "vehicle_type": "EQUITY",
                "classification_note": "Gold miner equity proxy; classified as EQUITIES in current taxonomy.",
                "rationale": "Economically sensitive to gold, but not direct COMMODITIES.GOLD exposure.",
            },
        ],
        "portfolio_substitutes": [],
    },
    "COMMODITIES.ENERGY": {
        "direct_completion": [
            {
                "symbol": "USO",
                "vehicle_type": "ETF",
                "classification_note": "Display-only candidate for energy sleeve completion review.",
                "rationale": "Oil-linked commodity exposure candidate.",
            },
            {
                "symbol": "BNO",
                "vehicle_type": "ETF",
                "classification_note": "Display-only candidate for energy sleeve completion review.",
                "rationale": "Brent-linked energy commodity exposure candidate.",
            },
            {
                "symbol": "UNG",
                "vehicle_type": "ETF",
                "classification_note": "Display-only candidate for energy sleeve completion review.",
                "rationale": "Natural gas-linked commodity exposure candidate.",
            },
        ],
        "equity_adjacent_proxies": [
            {
                "symbol": "XLE",
                "vehicle_type": "ETF",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Energy equity exposure proxy; does not directly fill COMMODITIES sleeve unless reclassified.",
            },
            {
                "symbol": "PSX",
                "vehicle_type": "EQUITY",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Energy-adjacent equity proxy; not direct sleeve completion.",
            },
            {
                "symbol": "CVE",
                "vehicle_type": "EQUITY",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Energy-adjacent equity proxy; not direct sleeve completion.",
            },
            {
                "symbol": "DVN",
                "vehicle_type": "EQUITY",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Energy-adjacent equity proxy; not direct sleeve completion.",
            },
            {
                "symbol": "NUE",
                "vehicle_type": "EQUITY",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Hard-asset-adjacent equity proxy; not direct sleeve completion.",
            },
            {
                "symbol": "STLD",
                "vehicle_type": "EQUITY",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Hard-asset-adjacent equity proxy; not direct sleeve completion.",
            },
            {
                "symbol": "CRS",
                "vehicle_type": "EQUITY",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Hard-asset-adjacent equity proxy; not direct sleeve completion.",
            },
        ],
        "portfolio_substitutes": [
            {
                "symbol": "PDBC",
                "vehicle_type": "ETF",
                "classification_note": "Mapped to COMMODITIES broad basket in current taxonomy.",
                "rationale": "Broad commodity substitute when direct energy sleeve options are limited.",
            },
        ],
    },
    "COMMODITIES.BROAD_BASKET": {
        "direct_completion": [
            {
                "symbol": "DBC",
                "vehicle_type": "ETF",
                "classification_note": "Display-only candidate for broad commodity sleeve completion review.",
                "rationale": "Broad commodity basket candidate with futures-linked structure considerations.",
            },
            {
                "symbol": "PDBC",
                "vehicle_type": "ETF",
                "classification_note": "Mapped to COMMODITIES broad basket in current taxonomy.",
                "rationale": "Broad commodity exposure for direct sleeve completion.",
            },
            {
                "symbol": "GSG",
                "vehicle_type": "ETF",
                "classification_note": "Suggested commodity vehicle in recommendation registry.",
                "rationale": "Diversified commodity basket exposure.",
            },
        ],
        "equity_adjacent_proxies": [
            {
                "symbol": "XLE",
                "vehicle_type": "ETF",
                "classification_note": "Classified as EQUITIES in current taxonomy.",
                "rationale": "Energy equity proxy; advisory only for sleeve review.",
            },
        ],
        "portfolio_substitutes": [],
    },
}

# Ordered preference for cohort-specific series type. FULL_UNIVERSE is the
# industry-filtered cohort average; TOP_N_STRATEGY is the selected basket.
# BENCHMARK is intentionally excluded — it is a shared market-wide index
# (e.g. S&P 500) identical across all replay_ids and must not be used to
# compute inter-cohort spreads.
_COHORT_SERIES_PREFERENCE = ("FULL_UNIVERSE", "TOP_N_STRATEGY")


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


def _read_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest_run_ids(repo_root: Path) -> list[str]:
    manifest_path = repo_root / "data" / "portfolio_ingestion" / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    portfolios = manifest.get("portfolios") or []
    ranked = sorted(
        portfolios,
        key=lambda p: (str(p.get("snapshot_date", "")), str(p.get("created_at_utc", ""))),
        reverse=True,
    )
    return [str(p.get("run_id", "") or "") for p in ranked if str(p.get("run_id", "") or "").strip()]


def _latest_run_id(repo_root: Path) -> str:
    run_ids = _latest_run_ids(repo_root)
    return run_ids[0] if run_ids else ""


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


def _load_alignment_rows(repo_root: Path, run_id: str) -> list[dict[str, str]]:
    if not run_id:
        return []
    path = (
        repo_root
        / "data"
        / "portfolio_ingestion"
        / "analysis_runs"
        / run_id
        / "alignment.csv"
    )
    return _read_csv_rows(path)


def _load_deployment_queue(repo_root: Path, run_id: str) -> dict:
    if not run_id:
        return {}
    path = (
        repo_root
        / "data"
        / "portfolio_ingestion"
        / "analysis_runs"
        / run_id
        / "deployment_queue.json"
    )
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_security_overlays(repo_root: Path, run_id: str) -> list[dict[str, str]]:
    if not run_id:
        return []
    path = (
        repo_root
        / "data"
        / "portfolio_ingestion"
        / "analysis_runs"
        / run_id
        / "security_overlays.csv"
    )
    return _read_csv_rows(path)


def _load_analyst_consensus(repo_root: Path, run_id: str) -> dict[str, dict]:
    if not run_id:
        return {}
    path = (
        repo_root
        / "data"
        / "portfolio_ingestion"
        / "analysis_runs"
        / run_id
        / "analyst_consensus.json"
    )
    data = _read_json(path)
    return data if isinstance(data, dict) else {}


def _load_recommendations_payload(repo_root: Path, run_id: str) -> dict | list:
    if not run_id:
        return {}
    path = (
        repo_root
        / "data"
        / "portfolio_ingestion"
        / "analysis_runs"
        / run_id
        / "recommendations.json"
    )
    return _read_json(path)


def _total_portfolio_value(holdings: list[dict[str, str]]) -> float:
    return round(sum((_safe_float(r.get("market_value")) or 0.0) for r in holdings), 2)


def _by_symbol(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol:
            out[symbol] = row
    return out


def _symbol_in_recommendations(payload: dict | list, symbol: str) -> bool:
    if not payload:
        return False
    text = json.dumps(payload)
    return f'"symbol": "{symbol}"' in text


def _recommendation_action_context(payload: dict | list, symbol: str) -> Optional[str]:
    if not payload:
        return None
    target = str(symbol or "").strip().upper()

    def _walk(node: object) -> Optional[str]:
        if isinstance(node, dict):
            sym = str(node.get("symbol") or "").strip().upper()
            if sym == target:
                parts: list[str] = []
                suggested = str(node.get("suggested_action") or "").strip()
                effective = str(node.get("effective_action") or "").strip()
                if suggested:
                    parts.append(suggested.replace("_", " "))
                elif effective:
                    parts.append(effective.replace("_", " "))
                rationale = str(node.get("flag_rationale") or "").strip()
                if rationale:
                    parts.append(rationale)
                if parts:
                    return " / ".join(parts)
            for value in node.values():
                hit = _walk(value)
                if hit:
                    return hit
        elif isinstance(node, list):
            for item in node:
                hit = _walk(item)
                if hit:
                    return hit
        return None

    return _walk(payload)


def _format_posture(overlay: dict[str, str] | None, consensus: dict | None) -> str:
    if not overlay:
        return "N/A"
    signal_direction = str(overlay.get("signal_direction") or "").strip().upper()
    ess = str(overlay.get("starmine_ess_text") or overlay.get("ess_score_text") or "").strip().upper()
    zacks = str(overlay.get("zacks_rating") or "").strip()
    consensus_label = str((consensus or {}).get("consensus_label") or "").strip().upper()
    if signal_direction == "NEUTRAL" and ess == "BEARISH" and consensus_label == "BUY":
        return "weak/mixed"
    if signal_direction:
        return signal_direction.lower()
    if zacks:
        return f"mixed ({zacks})"
    return "N/A"


def _direct_fit_score(symbol: str, node_key: str) -> int:
    base = 84
    if node_key == "COMMODITIES.GOLD":
        bonuses = {"GLD": 10, "IAU": 8, "SGOL": 6}
    elif node_key == "COMMODITIES.ENERGY":
        bonuses = {"USO": 8, "BNO": 7, "UNG": 5}
    else:
        bonuses = {"PDBC": 9, "DBC": 7, "GSG": 6}
    return min(99, base + bonuses.get(symbol, 0))


def _proxy_fit_score(*, symbol: str, overlay: dict[str, str] | None, current_action_context: str | None) -> int:
    score = 52
    score -= 18  # direct sleeve match penalty
    score -= 10  # equity contamination
    score -= 8   # company-specific risk
    if symbol == "KGC":
        score += 6  # thematic alignment to gold
    if overlay:
        signal_direction = str(overlay.get("signal_direction") or "").strip().upper()
        ess = str(overlay.get("starmine_ess_text") or "").strip().upper()
        if signal_direction == "NEUTRAL":
            score -= 4
        if ess in {"BEARISH", "VERY_BEARISH"}:
            score -= 5
    if current_action_context and any(token in current_action_context.upper() for token in ("TRIM", "REDUCE", "ACTION DUE")):
        score -= 8
    return max(5, min(65, score))


def _allocation_amounts(*, sleeve_amount_full: float, sleeve_amount_cash_only: float, candidate_count: int) -> dict:
    split_count = max(1, candidate_count)
    return {
        "single_candidate_fill": {
            "full_target_gap": round(sleeve_amount_full, 2),
            "deployable_cash_only": round(sleeve_amount_cash_only, 2),
        },
        "equal_split": {
            "full_target_gap": round(sleeve_amount_full / split_count, 2),
            "deployable_cash_only": round(sleeve_amount_cash_only / split_count, 2),
        },
        "operator_selected": {
            "full_target_gap": None,
            "deployable_cash_only": None,
        },
    }


def _build_sleeve_fit_payload(
    *,
    node_entries: list[dict],
    commodity_guard: dict,
    holdings: list[dict[str, str]],
    overlays: list[dict[str, str]],
    analyst_consensus: dict[str, dict],
    recommendations_payload: dict | list,
) -> dict:
    total_portfolio_value = _total_portfolio_value(holdings)
    deployable_cash = float(_safe_float(commodity_guard.get("deployment_cash")) or 0.0)
    total_gap_pct = max(0.0, float(_safe_float(commodity_guard.get("commodities_target_pct")) or 0.0) - float(_safe_float(commodity_guard.get("commodities_actual_pct")) or 0.0))
    holdings_by_symbol = _by_symbol(holdings)
    overlays_by_symbol = _by_symbol(overlays)

    candidate_fit_scores: list[dict] = []
    sleeve_rows: list[dict] = []

    for entry in node_entries:
        node_key = str(entry.get("node_key") or "")
        gap_pct = float(_safe_float(entry.get("gap_pp")) or 0.0)
        sleeve_amount_full = round(total_portfolio_value * (gap_pct / 100.0), 2)
        sleeve_share = (gap_pct / total_gap_pct) if total_gap_pct > 0 else 0.0
        sleeve_amount_cash_only = round(deployable_cash * sleeve_share, 2)

        direct = list(entry.get("direct_completion_candidates") or [])
        proxies = list(entry.get("equity_adjacent_proxies") or [])
        amounts = _allocation_amounts(
            sleeve_amount_full=sleeve_amount_full,
            sleeve_amount_cash_only=sleeve_amount_cash_only,
            candidate_count=len(direct),
        )

        entry["gap_amount_full_portfolio"] = sleeve_amount_full
        entry["deployable_cash_fill_amount"] = sleeve_amount_cash_only
        entry["allocation_examples"] = amounts

        for candidate in direct:
            symbol = str(candidate.get("symbol") or "").strip().upper()
            overlay = overlays_by_symbol.get(symbol)
            consensus = analyst_consensus.get(symbol) or {}
            fit_score = _direct_fit_score(symbol, node_key)
            caveat = "structure/tax review"
            row = {
                "sleeve": node_key,
                "candidate": symbol,
                "candidate_type": f"Direct {node_key.split('.')[-1].replace('_', ' ').title()} ETF",
                "sleeve_fit_score": fit_score,
                "direct_filler": True,
                "full_gap_amount": sleeve_amount_full,
                "deployable_cash_only_amount": sleeve_amount_cash_only,
                "amount_semantics": amounts,
                "current_holding": symbol in holdings_by_symbol,
                "current_holding_market_value": round(float(_safe_float((holdings_by_symbol.get(symbol) or {}).get("market_value")) or 0.0), 2),
                "current_sih_posture": _format_posture(overlay, consensus),
                "caveat": caveat,
                "fit_rationale": "Direct commodity vehicle aligned to target sleeve completion.",
            }
            candidate_fit_scores.append(row)
            sleeve_rows.append(row)

        for candidate in proxies:
            symbol = str(candidate.get("symbol") or "").strip().upper()
            overlay = overlays_by_symbol.get(symbol)
            consensus = analyst_consensus.get(symbol) or {}
            current_action_context = _recommendation_action_context(recommendations_payload, symbol)
            fit_score = _proxy_fit_score(symbol=symbol, overlay=overlay, current_action_context=current_action_context)
            posture = _format_posture(overlay, consensus)
            row = {
                "sleeve": node_key,
                "candidate": symbol,
                "candidate_type": "Gold miner equity proxy" if symbol == "KGC" else "Equity-adjacent proxy",
                "sleeve_fit_score": fit_score,
                "direct_filler": False,
                "full_gap_amount": 0.0,
                "deployable_cash_only_amount": 0.0,
                "amount_semantics": {
                    "single_candidate_fill": {"full_target_gap": 0.0, "deployable_cash_only": 0.0},
                    "equal_split": {"full_target_gap": 0.0, "deployable_cash_only": 0.0},
                    "operator_selected": {"full_target_gap": None, "deployable_cash_only": None},
                },
                "current_holding": symbol in holdings_by_symbol,
                "current_holding_market_value": round(float(_safe_float((holdings_by_symbol.get(symbol) or {}).get("market_value")) or 0.0), 2),
                "current_sih_posture": posture,
                "current_action_context": current_action_context,
                "gold_alignment": "medium/high" if symbol == "KGC" else "medium",
                "sleeve_fit_band": "low/medium" if symbol == "KGC" else "low",
                "not_direct_filler_reason": "Not a direct COMMODITIES.GOLD filler" if symbol == "KGC" else "Proxy only; not a direct sleeve filler",
                "equity_contamination": "high",
                "company_specific_risk": "high",
                "consensus_label": str(consensus.get("consensus_label") or "").strip() or None,
                "consensus_abr": _safe_float(consensus.get("abr")),
                "caveat": "equity proxy only, not direct filler",
                "fit_rationale": "Economically sensitive to the sleeve theme, but equity exposure does not directly satisfy the commodity sleeve target.",
                "classification_note": (
                    "KGC may be economically sensitive to gold prices, but it is a gold-mining equity, not direct gold exposure. It should be reviewed as a gold-adjacent proxy, not as the primary COMMODITIES.GOLD sleeve filler."
                    if symbol == "KGC"
                    else "Equity-adjacent proxy; review separately from direct sleeve fillers."
                ),
            }
            candidate_fit_scores.append(row)
            sleeve_rows.append(row)

    candidate_fit_scores.sort(key=lambda row: (-int(row.get("sleeve_fit_score") or 0), row.get("candidate") or ""))

    return {
        "display_only": True,
        "operator_review_required": True,
        "scoring_basis": "SLEEVE_COMPLETION_FIT_NOT_EQUITY_RANKING",
        "portfolio_value": round(total_portfolio_value, 2),
        "deployable_cash": round(deployable_cash, 2),
        "allocation_modes": [
            {
                "mode": "FULL_TARGET_GAP",
                "description": "Fill the full commodity sleeve gap using total portfolio value.",
                "total_amount": round(total_portfolio_value * (total_gap_pct / 100.0), 2),
            },
            {
                "mode": "DEPLOYABLE_CASH_ONLY",
                "description": "Use only current deployable cash and allocate proportionally across sleeve targets.",
                "total_amount": round(deployable_cash, 2),
            },
            {
                "mode": "CUSTOM_AMOUNT",
                "description": "Operator-specified amount; display-only estimate.",
                "total_amount": None,
            },
        ],
        "candidate_fit_scores": candidate_fit_scores,
        "table_rows": sleeve_rows,
        "custom_amount_placeholder": "Enter any custom amount outside this display-only panel; no execution behavior is attached.",
    }


def _pick_guardrail_run_id(repo_root: Path, preferred_run_id: str) -> str:
    run_ids = [preferred_run_id] if preferred_run_id else []
    run_ids.extend([rid for rid in _latest_run_ids(repo_root) if rid and rid != preferred_run_id])
    for rid in run_ids:
        run_dir = (
            repo_root
            / "data"
            / "portfolio_ingestion"
            / "analysis_runs"
            / rid
        )
        if (run_dir / "alignment.csv").exists() and (run_dir / "deployment_queue.json").exists():
            return rid
    return preferred_run_id


def _alignment_row_by_node(alignment_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in alignment_rows:
        key = str(row.get("node_key") or "").strip().upper()
        if key:
            out[key] = row
    return out


def _tech_sensitive_deployment_count(
    queue: list[dict],
    holdings: list[dict[str, str]],
) -> int:
    by_symbol_industry: dict[str, str] = {}
    for row in holdings:
        sym = str(row.get("symbol") or "").strip().upper()
        ind = _industry_normalized(row.get("industry") or "")
        if sym and ind:
            by_symbol_industry[sym] = ind

    count = 0
    for cand in queue:
        node = str(cand.get("allocation_node") or "").upper()
        if not node.startswith("EQUITIES"):
            continue
        sym = str(cand.get("symbol") or "").strip().upper()
        if by_symbol_industry.get(sym) == "TECHNOLOGY":
            count += 1
    return count


def _build_commodity_fill_guard(
    *,
    alignment_rows: list[dict[str, str]],
    deployment_queue: dict,
    holdings: list[dict[str, str]],
) -> dict:
    by_node = _alignment_row_by_node(alignment_rows)

    def _pair(node_key: str) -> tuple[Optional[float], Optional[float]]:
        row = by_node.get(node_key.upper(), {})
        return _safe_float(row.get("actual_pct")), _safe_float(row.get("target_pct"))

    comm_actual, comm_target = _pair("COMMODITIES")
    gold_actual, gold_target = _pair("COMMODITIES.GOLD")
    energy_actual, energy_target = _pair("COMMODITIES.ENERGY")
    broad_actual, broad_target = _pair("COMMODITIES.BROAD_BASKET")

    cash_context = deployment_queue.get("cash_context") or {}
    deployable_cash = (
        _safe_float(cash_context.get("adjusted_deployable_mv"))
        if cash_context.get("adjusted_deployable_mv") is not None
        else _safe_float(cash_context.get("deployable_mv"))
    )
    deployable_cash = float(deployable_cash or 0.0)

    queue = list(deployment_queue.get("queue") or [])
    equity_deployment_count = sum(
        1 for c in queue if str(c.get("allocation_node") or "").upper().startswith("EQUITIES")
    )
    commodity_deployment_count = sum(
        1 for c in queue if str(c.get("allocation_node") or "").upper().startswith("COMMODITIES")
    )
    tech_sensitive_deployment_count = _tech_sensitive_deployment_count(queue, holdings)

    target = float(comm_target or 0.0)
    actual = float(comm_actual or 0.0)
    gap = actual - target
    near_zero_unfilled = target > 0 and actual <= 0.25
    has_equity_deployment = equity_deployment_count > 0
    has_deployable_cash = deployable_cash > 0.0

    status = "NONE"
    severity = "NONE"
    message = "Hard-asset sleeve posture is within expected bounds."
    if target <= 0:
        message = "Commodity target is zero; no hard-asset sleeve fill review required."
    elif near_zero_unfilled and has_deployable_cash and has_equity_deployment:
        status = "ACTIVE_REVIEW"
        severity = "WATCH"
        if tech_sensitive_deployment_count > 0 or abs(gap) >= 2.0:
            severity = "ELEVATED"
        message = "Hard-asset sleeve is unfilled while deployable cash is being allocated to equities."
    elif actual < target and has_deployable_cash:
        status = "INFO"
        severity = "INFO"
        message = "Hard-asset sleeve is below target while deployable cash exists; review deployment intent."
    elif actual < target:
        status = "INFO"
        severity = "INFO"
        message = "Hard-asset sleeve is below target, but no deployable cash is currently available."

    return {
        "status": status,
        "severity": severity,
        "commodities_actual_pct": round(actual, 3) if comm_actual is not None else None,
        "commodities_target_pct": round(target, 3) if comm_target is not None else None,
        "commodities_gap_pp": round(gap, 3) if comm_actual is not None and comm_target is not None else None,
        "gold_actual_pct": round(float(gold_actual or 0.0), 3) if gold_actual is not None else None,
        "gold_target_pct": round(float(gold_target or 0.0), 3) if gold_target is not None else None,
        "energy_actual_pct": round(float(energy_actual or 0.0), 3) if energy_actual is not None else None,
        "energy_target_pct": round(float(energy_target or 0.0), 3) if energy_target is not None else None,
        "broad_basket_actual_pct": round(float(broad_actual or 0.0), 3) if broad_actual is not None else None,
        "broad_basket_target_pct": round(float(broad_target or 0.0), 3) if broad_target is not None else None,
        "deployment_cash": round(deployable_cash, 2),
        "deployment_targets_count": len(queue),
        "tech_sensitive_deployment_count": tech_sensitive_deployment_count,
        "equity_deployment_count": equity_deployment_count,
        "commodity_candidates_available": commodity_deployment_count > 0,
        "commodity_deployment_count": commodity_deployment_count,
        "message": message,
        "operator_choices": [
            "continue_with_equity_deployment",
            "reserve_cash",
            "fill_hard_asset_sleeve",
            "mark_commodities_target_waived",
            "rerun_with_custom_cash",
        ],
    }


def _build_rotation_fragility_watch(
    *,
    rotation_signal: str,
    confirmation_passed: bool,
    exposure: dict,
    macro_events: list[dict],
    alignment_rows: list[dict[str, str]],
    commodity_guard: dict,
) -> dict:
    by_node = _alignment_row_by_node(alignment_rows)
    ultra_mega = by_node.get("EQUITIES.US.MEGA.ULTRA_MEGA", {})
    ultra_mega_drift = _safe_float(ultra_mega.get("drift_pct"))

    hard_actual = commodity_guard.get("commodities_actual_pct")
    hard_target = commodity_guard.get("commodities_target_pct")
    deploy_eq_count = int(commodity_guard.get("equity_deployment_count") or 0)
    tech_deploy_count = int(commodity_guard.get("tech_sensitive_deployment_count") or 0)

    macro_catalyst_window = bool(macro_events)
    tech_pct = _safe_float(exposure.get("tech_pct")) or 0.0
    signal_norm = str(rotation_signal or "DATA_UNAVAILABLE").upper()

    if not hard_target or hard_target <= 0:
        return {
            "status": "NONE",
            "severity": "NONE",
            "rotation_confirmed": bool(confirmation_passed),
            "rotation_signal": signal_norm,
            "tech_sector_pct": round(tech_pct, 3),
            "hard_asset_sleeve_actual_pct": hard_actual,
            "hard_asset_sleeve_target_pct": hard_target,
            "ultra_mega_drift_pp": round(float(ultra_mega_drift), 3) if ultra_mega_drift is not None else None,
            "macro_catalyst_window": macro_catalyst_window,
            "macro_events": [str(e.get("event_name") or e.get("event_id") or "") for e in macro_events if e],
            "message": "Hard-asset sleeve target is zero; rotation fragility watch is inactive.",
        }

    score = 0
    if (hard_actual or 0.0) <= 0.25:
        score += 2
    if tech_pct >= 25.0:
        score += 1
    if ultra_mega_drift is not None and ultra_mega_drift >= 3.0:
        score += 1
    if deploy_eq_count > 0:
        score += 1
    if tech_deploy_count > 0:
        score += 1
    if macro_catalyst_window:
        score += 1

    if signal_norm == "ELEVATED_ROTATION_RISK":
        score += 2
    elif signal_norm in {"WATCHLIST_ROTATION", "NO_CLEAR_SIGNAL", "DATA_UNAVAILABLE"}:
        score += 1

    if score >= 7:
        status = "FRAGILITY_ELEVATED"
        severity = "ELEVATED"
    elif score >= 4:
        status = "FRAGILITY_WATCH"
        severity = "WATCH"
    elif score >= 2:
        status = "FRAGILITY_INFO"
        severity = "INFO"
    else:
        status = "NONE"
        severity = "NONE"

    msg = "Rotation is not confirmed, but portfolio fragility should be monitored before incremental equity deployment."
    if status == "FRAGILITY_ELEVATED":
        msg = "Rotation confirmation is incomplete, but fragility is elevated because hard assets are underfilled while equity deployment remains active."
    elif status == "NONE":
        msg = "No material pre-confirmation rotation fragility detected."

    return {
        "status": status,
        "severity": severity,
        "rotation_confirmed": bool(confirmation_passed),
        "rotation_signal": signal_norm,
        "tech_sector_pct": round(tech_pct, 3),
        "hard_asset_sleeve_actual_pct": hard_actual,
        "hard_asset_sleeve_target_pct": hard_target,
        "ultra_mega_drift_pp": round(float(ultra_mega_drift), 3) if ultra_mega_drift is not None else None,
        "macro_catalyst_window": macro_catalyst_window,
        "macro_events": [str(e.get("event_name") or e.get("event_id") or "") for e in macro_events if e],
        "message": msg,
    }


def _build_hard_asset_candidate_queue(
    *,
    repo_root: Path,
    run_id: str,
    alignment_rows: list[dict[str, str]],
    deployment_queue: dict,
    commodity_guard: dict,
    holdings: list[dict[str, str]],
) -> dict:
    by_node = _alignment_row_by_node(alignment_rows)
    queue = list(deployment_queue.get("queue") or [])

    deployable_cash = float(_safe_float(commodity_guard.get("deployment_cash")) or 0.0)
    warnings: list[str] = [
        "Display-only candidates; not trade instructions.",
        "Commodity/futures-linked products may have structure, tax, volatility, and tracking considerations.",
        "Equity-adjacent proxies do not directly fill the COMMODITIES sleeve unless classified that way by the allocation model.",
    ]
    advisories: list[str] = [
        "DISPLAY_ONLY",
        "OPERATOR_REVIEW_REQUIRED",
        "CAPITAL_DEPLOYMENT_QUEUE_UNCHANGED",
        "CRA_UNCHANGED",
    ]

    registry = _HARD_ASSET_CANDIDATE_REGISTRY or {}
    registry_status = "AVAILABLE" if registry else "MISSING"
    if registry_status == "MISSING":
        warnings.append("NO_CANDIDATE_REGISTRY")

    node_keys = ("COMMODITIES.GOLD", "COMMODITIES.ENERGY", "COMMODITIES.BROAD_BASKET")
    node_entries: list[dict] = []
    candidate_groups: list[dict] = []
    total_gap_pp = 0.0
    direct_candidate_total = 0
    equity_adjacent_flat: list[str] = []

    for node_key in node_keys:
        row = by_node.get(node_key, {})
        actual = float(_safe_float(row.get("actual_pct")) or 0.0)
        target = float(_safe_float(row.get("target_pct")) or 0.0)
        gap_pp = max(0.0, target - actual)
        total_gap_pp += gap_pp

        total_portfolio_value = _total_portfolio_value(holdings)
        gap_amount_full_portfolio = total_portfolio_value * (gap_pp / 100.0) if total_portfolio_value > 0 else 0.0
        commodity_gap_total = max(0.0, float(_safe_float(commodity_guard.get("commodities_target_pct")) or 0.0) - float(_safe_float(commodity_guard.get("commodities_actual_pct")) or 0.0))
        sleeve_share = (gap_pp / commodity_gap_total) if commodity_gap_total > 0 else 0.0
        deployable_cash_fill_amount = deployable_cash * sleeve_share if deployable_cash > 0 else 0.0

        reg_node = registry.get(node_key, {}) if registry_status == "AVAILABLE" else {}
        direct = list(reg_node.get("direct_completion") or [])
        equity_adjacent = list(reg_node.get("equity_adjacent_proxies") or [])
        substitutes = list(reg_node.get("portfolio_substitutes") or [])
        direct_candidate_total += len(direct)

        if gap_pp > 0 and not direct:
            warnings.append(f"NO_DIRECT_COMPLETION_CANDIDATES:{node_key}")

        for proxy in equity_adjacent:
            psym = str(proxy.get("symbol") or "").strip().upper()
            if psym and psym not in equity_adjacent_flat:
                equity_adjacent_flat.append(psym)

        queue_matches = [
            {
                "symbol": str(c.get("symbol") or "").strip().upper(),
                "allocation_node": str(c.get("allocation_node") or ""),
            }
            for c in queue
            if str(c.get("allocation_node") or "").strip().upper().startswith(node_key)
            and str(c.get("symbol") or "").strip()
        ]

        node_entries.append(
            {
                "node_key": node_key,
                "actual_pct": round(actual, 3),
                "target_pct": round(target, 3),
                "gap_pp": round(gap_pp, 3),
                "approx_gap_dollars": round(gap_amount_full_portfolio, 2),
                "gap_amount_full_portfolio": round(gap_amount_full_portfolio, 2),
                "deployable_cash_fill_amount": round(deployable_cash_fill_amount, 2),
                "direct_completion_candidates": direct,
                "equity_adjacent_proxies": equity_adjacent,
                "portfolio_substitutes": substitutes,
                "existing_queue_candidates": queue_matches,
            }
        )

        candidate_groups.append(
            {
                "node": node_key,
                "gap_pct": round(gap_pp, 3),
                "candidate_type": "DIRECT_COMPLETION_VEHICLE",
                "candidates": [str(c.get("symbol") or "").strip().upper() for c in direct if str(c.get("symbol") or "").strip()],
            }
        )

    status = "NO_GAP"
    severity = "NONE"
    message = "Hard-asset sleeve is at target; no completion candidates needed."
    comm_target = float(_safe_float(commodity_guard.get("commodities_target_pct")) or 0.0)
    if comm_target <= 0:
        status = "NOT_APPLICABLE"
        message = "Commodity target is zero; candidate queue is not applicable."
    elif total_gap_pp > 0 and direct_candidate_total > 0:
        status = "ACTIVE_REVIEW"
        severity = "INFO"
        message = "Commodity sleeve gap detected; display-only completion candidates are available for operator review."
    elif total_gap_pp > 0:
        status = "ACTIVE_REVIEW"
        severity = "WATCH"
        message = "Commodity sleeve gap detected, but direct completion candidates are limited in current registry."

    target_gap = {
        "commodities_pct": round(max(0.0, float(_safe_float(commodity_guard.get("commodities_target_pct")) or 0.0) - float(_safe_float(commodity_guard.get("commodities_actual_pct")) or 0.0)), 3),
        "gold_pct": round(max(0.0, float(_safe_float(commodity_guard.get("gold_target_pct")) or 0.0) - float(_safe_float(commodity_guard.get("gold_actual_pct")) or 0.0)), 3),
        "energy_pct": round(max(0.0, float(_safe_float(commodity_guard.get("energy_target_pct")) or 0.0) - float(_safe_float(commodity_guard.get("energy_actual_pct")) or 0.0)), 3),
        "broad_basket_pct": round(max(0.0, float(_safe_float(commodity_guard.get("broad_basket_target_pct")) or 0.0) - float(_safe_float(commodity_guard.get("broad_basket_actual_pct")) or 0.0)), 3),
    }

    overlays = _load_security_overlays(repo_root=repo_root, run_id=run_id)
    analyst_consensus = _load_analyst_consensus(repo_root=repo_root, run_id=run_id)
    recommendations_payload = _load_recommendations_payload(repo_root=repo_root, run_id=run_id)
    sleeve_fit = _build_sleeve_fit_payload(
        node_entries=node_entries,
        commodity_guard=commodity_guard,
        holdings=holdings,
        overlays=overlays,
        analyst_consensus=analyst_consensus,
        recommendations_payload=recommendations_payload,
    )
    total_portfolio_value = _total_portfolio_value(holdings)
    total_gap_pct = target_gap["commodities_pct"]

    return {
        "display_only": True,
        "operator_review_required": True,
        "status": status,
        "severity": severity,
        "message": message,
        "registry_status": registry_status,
        "queue_scope": "COMMODITY_SLEEVE_COMPLETION_CANDIDATES",
        "equity_proxy_disclaimer": "Equity-adjacent proxies are advisory only and do not directly fill the COMMODITIES sleeve unless classification policy is changed.",
        "target_gap": target_gap,
        "candidate_groups": candidate_groups,
        "equity_adjacent_substitutes": equity_adjacent_flat,
        "summary": {
            "total_gap_pp": round(total_gap_pp, 3),
            "deployable_cash": round(deployable_cash, 2),
            "portfolio_value": round(total_portfolio_value, 2),
            "approx_gap_dollars": round(total_portfolio_value * (total_gap_pct / 100.0), 2) if total_portfolio_value > 0 else 0.0,
            "gap_amount_full_portfolio": round(total_portfolio_value * (total_gap_pct / 100.0), 2) if total_portfolio_value > 0 else 0.0,
            "deployable_cash_only_amount": round(deployable_cash, 2),
            "node_count": len(node_entries),
            "direct_completion_candidate_count": direct_candidate_total,
            "equity_adjacent_proxy_count": len(equity_adjacent_flat),
        },
        "sleeve_nodes": node_entries,
        "sleeve_fit": sleeve_fit,
        "warnings": warnings,
        "advisories": advisories,
        "operator_choices": list(commodity_guard.get("operator_choices") or []),
    }


def _build_hard_asset_priority_gate(
    *,
    commodity_guard: dict,
    hard_asset_candidate_queue: dict,
    rotation_fragility_watch: dict,
    deployment_queue: dict,
) -> dict:
    summary = hard_asset_candidate_queue.get("summary") or {}
    queue_status = str(hard_asset_candidate_queue.get("status") or "NONE")
    queue_severity = str(hard_asset_candidate_queue.get("severity") or "NONE")
    fragility_status = str(rotation_fragility_watch.get("status") or "NONE")
    fragility_severity = str(rotation_fragility_watch.get("severity") or "NONE")

    deployable_cash = float(_safe_float(commodity_guard.get("deployment_cash")) or 0.0)
    commodities_actual = float(_safe_float(commodity_guard.get("commodities_actual_pct")) or 0.0)
    commodities_target = float(_safe_float(commodity_guard.get("commodities_target_pct")) or 0.0)
    commodities_gap = max(0.0, commodities_target - commodities_actual)
    equity_deployment_count = int(commodity_guard.get("equity_deployment_count") or 0)
    tech_sensitive_deployment_count = int(commodity_guard.get("tech_sensitive_deployment_count") or 0)
    commodity_candidates_available = bool(commodity_guard.get("commodity_candidates_available"))
    macro_catalyst_window = bool(rotation_fragility_watch.get("macro_catalyst_window"))
    candidate_count = int((deployment_queue or {}).get("candidate_count") or 0)
    direct_candidate_count = sum(
        len(node.get("direct_completion_candidates") or [])
        for node in (hard_asset_candidate_queue.get("sleeve_nodes") or [])
    )
    equity_adjacent_proxy_count = len({
        str(proxy.get("symbol") or "").strip().upper()
        for node in (hard_asset_candidate_queue.get("sleeve_nodes") or [])
        for proxy in (node.get("equity_adjacent_proxies") or [])
        if str(proxy.get("symbol") or "").strip()
    })

    hard_asset_pressure = 0
    if commodities_gap > 0:
        hard_asset_pressure += 25
    if deployable_cash > 0:
        hard_asset_pressure += 15
    if commodity_candidates_available:
        hard_asset_pressure += 10
    if queue_status == "ACTIVE_REVIEW":
        hard_asset_pressure += 10
    if queue_severity in {"INFO", "WATCH", "ELEVATED"}:
        hard_asset_pressure += 5
    if fragility_status != "NONE":
        hard_asset_pressure += 10
    if fragility_severity in {"WATCH", "ELEVATED"}:
        hard_asset_pressure += 10
    if equity_deployment_count > 0:
        hard_asset_pressure += 5
    if tech_sensitive_deployment_count > 0:
        hard_asset_pressure += 5
    if macro_catalyst_window:
        hard_asset_pressure += 5
    if direct_candidate_count > 0:
        hard_asset_pressure += 5

    hard_asset_pressure = max(0, min(100, hard_asset_pressure))

    if commodities_target <= 0:
        verdict = "HARD_ASSET_NOT_APPLICABLE"
        recommended_action = "Keep the equity deployment queue unchanged; no hard-asset target is active."
    elif commodities_gap <= 0 and deployable_cash <= 0:
        verdict = "CONTINUE_EQUITY_DEPLOYMENT"
        recommended_action = "Continue equity deployment; the hard-asset sleeve is already funded and no deployable cash is available."
    elif hard_asset_pressure >= 70:
        verdict = "PARTIAL_HARD_ASSET_FILL"
        recommended_action = "OPERATOR REVIEW REQUIRED — consider reserving some or all deployable cash for hard-asset sleeve completion before deploying all excess cash to equities."
    elif hard_asset_pressure >= 45:
        verdict = "OPERATOR_REVIEW_REQUIRED"
        recommended_action = "OPERATOR REVIEW REQUIRED — consider reserving some or all deployable cash for hard-asset sleeve completion before deploying all excess cash to equities."
    else:
        verdict = "CONTINUE_EQUITY_DEPLOYMENT"
        recommended_action = "Continue equity deployment; hard-asset pressure is advisory but not dominant."

    rotation_signal = str(rotation_fragility_watch.get("rotation_signal") or "DATA_UNAVAILABLE")
    rotation_confirmed = bool(rotation_fragility_watch.get("rotation_confirmed"))
    score_label = "Review pressure score"
    if hard_asset_pressure >= 70:
        score_note = (
            f"High because the commodity sleeve is structurally unfilled and deployable cash is available; moderated by {rotation_signal} / "
            f"{'CONFIRMED' if rotation_confirmed else 'NOT CONFIRMED'}. Display-only capital-allocation review score; not a trade-confidence score."
        )
    elif hard_asset_pressure >= 45:
        score_note = (
            f"Elevated because the commodity sleeve is underfilled and deployable cash is available; moderated by {rotation_signal} / "
            f"{'CONFIRMED' if rotation_confirmed else 'NOT CONFIRMED'}. Display-only capital-allocation review score; not a trade-confidence score."
        )
    else:
        score_note = "Display-only capital-allocation review score; not a trade-confidence score."

    decision_factors = [
        {
            "factor": "Commodity sleeve gap",
            "value": round(commodities_gap, 3),
            "impact": "higher" if commodities_gap > 0 else "neutral",
            "note": "Hard-asset target remains underfilled." if commodities_gap > 0 else "Hard-asset sleeve is at target.",
        },
        {
            "factor": "Deployable cash available",
            "value": round(deployable_cash, 2),
            "impact": "higher" if deployable_cash > 0 else "lower",
            "note": "Cash is available for either sleeve or equity deployment." if deployable_cash > 0 else "No deployable cash is currently available.",
        },
        {
            "factor": "Equity deployment candidates",
            "value": equity_deployment_count,
            "impact": "higher" if equity_deployment_count > 0 else "lower",
            "note": "Capital is already flowing to equities." if equity_deployment_count > 0 else "No equity deployment candidates are present.",
        },
        {
            "factor": "Rotation fragility status",
            "value": fragility_status,
            "impact": "higher" if fragility_status != "NONE" else "neutral",
            "note": rotation_fragility_watch.get("message") or "Rotation fragility watch is informational only.",
        },
        {
            "factor": "Tech-sensitive deployment candidates",
            "value": tech_sensitive_deployment_count,
            "impact": "higher" if tech_sensitive_deployment_count > 0 else "neutral",
            "note": "Some equity deployment candidates are tech-sensitive." if tech_sensitive_deployment_count > 0 else "No tech-sensitive deployment pressure detected.",
        },
        {
            "factor": "Direct hard-asset completion candidates",
            "value": direct_candidate_count,
            "impact": "higher" if direct_candidate_count > 0 else "lower",
            "note": "Hard-asset completion candidates are available for operator review." if direct_candidate_count > 0 else "No direct hard-asset completion candidates were present.",
        },
    ]

    deployable_cash_only_gold = round(deployable_cash * 0.5, 2)
    deployable_cash_only_energy = round(deployable_cash * 0.35, 2)
    deployable_cash_only_broad = round(max(0.0, deployable_cash - deployable_cash_only_gold - deployable_cash_only_energy), 2)
    capital_options = [
        {
            "code": "A",
            "label": "Continue equity deployment",
            "preferred_when": "hard_asset_pressure < 45",
            "description": "Keep the current deployment queue intact and treat hard-asset fill as secondary.",
            "amount": round(deployable_cash, 2),
            "amount_breakdown": {
                "equities": round(deployable_cash, 2),
            },
        },
        {
            "code": "B",
            "label": "Deployable-cash-only hard-asset fill",
            "preferred_when": "deployable cash exists and the operator wants a sleeve-first split",
            "description": "Use current deployable cash to partially fill the hard-asset sleeve while leaving the equity queue unchanged.",
            "amount": round(deployable_cash, 2),
            "amount_breakdown": {
                "gold": deployable_cash_only_gold,
                "energy": deployable_cash_only_energy,
                "broad_basket": deployable_cash_only_broad,
            },
        },
        {
            "code": "C",
            "label": "Split approach",
            "preferred_when": "the operator wants to balance sleeves without changing queue order",
            "description": "Divide deployable cash between hard assets and equities while preserving existing deployment order.",
            "amount": round(deployable_cash / 2.0, 2),
            "amount_breakdown": {
                "hard_assets": round(deployable_cash / 2.0, 2),
                "equities": round(deployable_cash / 2.0, 2),
            },
        },
        {
            "code": "D",
            "label": "Reserve cash",
            "preferred_when": "deployable cash exists but neither sleeve should move immediately",
            "description": "Hold deployable cash while the operator reviews the hard-asset sleeve and equity queue together.",
            "amount": round(deployable_cash, 2),
        },
        {
            "code": "E",
            "label": "Waive commodity target",
            "preferred_when": "commodity target is intentionally deferred",
            "description": "Treat the hard-asset sleeve as waived for this review cycle; display-only and operator controlled.",
            "amount": 0.0,
        },
    ]

    rationale = [
        "Display-only advisory gate; it does not modify ranking, queue order, CRA, or execution behavior.",
        recommended_action,
    ]
    if commodities_gap > 0:
        rationale.append("The hard-asset sleeve is still under target.")
    if deployable_cash > 0:
        rationale.append("Deployable cash is available and can be reserved for the sleeve if desired.")
    if equity_deployment_count > 0:
        rationale.append("Equity deployment is already active, so the decision is a capital-allocation preference rather than an availability problem.")
    if macro_catalyst_window:
        rationale.append("A macro catalyst window is active, so the operator may prefer partial hard-asset staging before fully deploying cash to equities.")
    if commodity_candidates_available:
        rationale.append("Commodity completion candidates exist, but they remain display-only and operator-reviewed.")

    return {
        "display_only": True,
        "operator_review_required": True,
        "status": "ACTIVE_REVIEW" if commodities_gap > 0 or queue_status == "ACTIVE_REVIEW" else "NO_GAP",
        "severity": queue_severity if queue_severity != "NONE" else fragility_severity,
        "verdict": verdict,
        "priority_verdict": verdict,
        "score": hard_asset_pressure,
        "priority_score": hard_asset_pressure,
        "recommended_action": recommended_action,
        "recommended_operator_action": recommended_action,
        "score_label": score_label,
        "score_note": score_note,
        "rationale": rationale,
        "decision_factors": decision_factors,
        "capital_options": capital_options,
        "summary": {
            "commodities_actual_pct": round(commodities_actual, 3),
            "commodities_target_pct": round(commodities_target, 3),
            "commodities_gap_pct": round(commodities_gap, 3),
            "deployable_cash": round(deployable_cash, 2),
            "equity_deployment_count": equity_deployment_count,
            "candidate_count": candidate_count,
            "deployment_queue_candidate_count": candidate_count,
            "direct_completion_candidate_count": direct_candidate_count,
            "equity_adjacent_proxy_count": equity_adjacent_proxy_count,
        },
        "priority_bias": "HARD_ASSET_REVIEW_FIRST" if verdict != "CONTINUE_EQUITY_DEPLOYMENT" else "EQUITY_DEPLOYMENT_FIRST",
        "guardrail_notes": [
            "Display-only and operator-reviewed.",
            "No queue mutation, rank mutation, or trade execution attached.",
        ],
    }


def _build_today_operator_action_plan(
    *,
    hard_asset_priority_gate: dict,
    hard_asset_candidate_queue: dict,
    rotation_fragility_watch: dict,
    commodity_guard: dict,
    deployment_queue: dict,
    security_overlays: list[dict[str, str]],
    recommendations_payload: dict | list,
) -> dict:
    """Build display-only daily operator action sequencing guidance."""

    summary = hard_asset_priority_gate.get("summary") or {}
    target_gap = hard_asset_candidate_queue.get("target_gap") or {}
    nodes = list(hard_asset_candidate_queue.get("sleeve_nodes") or [])
    dq_queue = list((deployment_queue or {}).get("queue") or [])
    dq_cash = (deployment_queue or {}).get("cash_context") or {}
    deployable_cash = float(
        dq_cash.get("adjusted_deployable_mv")
        if dq_cash.get("adjusted_deployable_mv") is not None
        else dq_cash.get("deployable_mv")
        if dq_cash.get("deployable_mv") is not None
        else summary.get("deployable_cash")
        or 0.0
    )
    portfolio_value = float(
        summary.get("portfolio_value")
        or hard_asset_candidate_queue.get("summary", {}).get("portfolio_value")
        or deployment_queue.get("total_market_value")
        or 0.0
    )
    commodities_actual = float(summary.get("commodities_actual_pct") or 0.0)
    commodities_target = float(summary.get("commodities_target_pct") or 0.0)
    priority_bias = str(hard_asset_priority_gate.get("priority_bias") or "UNKNOWN")
    gate_verdict = str(hard_asset_priority_gate.get("verdict") or "UNKNOWN")

    overlays_by_symbol = {
        str(r.get("symbol") or "").strip().upper(): r
        for r in security_overlays
        if str(r.get("symbol") or "").strip()
    }

    def _node(node_key: str) -> dict:
        return next((n for n in nodes if str(n.get("node_key") or "") == node_key), {})

    def _money(value: object) -> float:
        try:
            return round(float(value or 0.0), 2)
        except Exception:
            return 0.0

    def _fmt_k(value: float) -> str:
        return f"${value / 1000.0:.1f}K" if abs(value) >= 1000 else f"${value:,.0f}"

    gold_node = _node("COMMODITIES.GOLD")
    energy_node = _node("COMMODITIES.ENERGY")
    broad_node = _node("COMMODITIES.BROAD_BASKET")

    hard_asset_buy_plan = [
        {
            "node_key": "COMMODITIES.GOLD",
            "label": "Gold",
            "deployable_cash_only_amount": _money(gold_node.get("deployable_cash_fill_amount") or deployable_cash * 0.5),
            "full_target_amount": _money(gold_node.get("gap_amount_full_portfolio") or portfolio_value * (float(target_gap.get("gold_pct") or 0.0) / 100.0)),
            "candidate_group": ["GLD", "IAU", "SGOL"],
        },
        {
            "node_key": "COMMODITIES.ENERGY",
            "label": "Energy",
            "deployable_cash_only_amount": _money(energy_node.get("deployable_cash_fill_amount") or deployable_cash * 0.35),
            "full_target_amount": _money(energy_node.get("gap_amount_full_portfolio") or portfolio_value * (float(target_gap.get("energy_pct") or 0.0) / 100.0)),
            "candidate_group": ["USO", "BNO", "UNG"],
        },
        {
            "node_key": "COMMODITIES.BROAD_BASKET",
            "label": "Broad Basket",
            "deployable_cash_only_amount": _money(broad_node.get("deployable_cash_fill_amount") or max(0.0, deployable_cash - (deployable_cash * 0.5) - (deployable_cash * 0.35))),
            "full_target_amount": _money(broad_node.get("gap_amount_full_portfolio") or portfolio_value * (float(target_gap.get("broad_basket_pct") or 0.0) / 100.0)),
            "candidate_group": ["DBC", "PDBC", "GSG"],
        },
    ]

    eq_recs = []
    rec_map = {}
    if isinstance(recommendations_payload, dict):
        for rec in list(recommendations_payload.get("recommendations") or []):
            sym = str(rec.get("symbol") or "").strip().upper()
            if sym:
                rec_map[sym] = rec
    elif isinstance(recommendations_payload, list):
        for rec in recommendations_payload:
            if isinstance(rec, dict):
                sym = str(rec.get("symbol") or "").strip().upper()
                if sym:
                    rec_map[sym] = rec

    for idx, row in enumerate(dq_queue):
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym:
            continue
        rec = rec_map.get(sym) or {}
        eq_recs.append(
            {
                "symbol": sym,
                "rank": int(row.get("rank") or idx + 1),
                "suggested_amount": _money(
                    rec.get("suggested_amount")
                    or rec.get("amount")
                    or row.get("suggested_amount")
                    or row.get("deployable_cash_only_amount")
                ),
                "deployment_score": _money(row.get("deployment_score")),
            }
        )

    blocked_actions: list[dict] = []
    sell_trim_review: list[dict] = []

    for row in list((deployment_queue or {}).get("policy_suppressed") or []):
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym:
            continue
        blocked_actions.append(
            {
                "symbol": sym,
                "reason": str(row.get("note") or row.get("intelligence_flag") or "blocked by policy"),
                "policy_state": "BLOCKED_BY_POLICY",
            }
        )

    for row in security_overlays:
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym:
            continue
        flag = str(row.get("opportunity_flag") or "").strip().upper()
        if flag in {"TRIM", "REDUCE", "REDUCE_CANDIDATE", "SELL"}:
            if sym == "TSLA":
                if not any(x.get("symbol") == "TSLA" for x in blocked_actions):
                    blocked_actions.append(
                        {
                            "symbol": "TSLA",
                            "reason": "thesis exit blocked by operator policy",
                            "policy_state": "BLOCKED_BY_POLICY",
                        }
                    )
            elif not any(x.get("symbol") == sym for x in sell_trim_review):
                sell_trim_review.append(
                    {
                        "symbol": sym,
                        "reason": str(row.get("flag_rationale") or "sell/trim review"),
                        "policy_state": str(row.get("execution_state") or "REVIEW"),
                    }
                )

    if not any(x.get("symbol") == "KGC" for x in sell_trim_review):
        kgc_ov = overlays_by_symbol.get("KGC") or {}
        if kgc_ov:
            sell_trim_review.append(
                {
                    "symbol": "KGC",
                    "reason": str(kgc_ov.get("flag_rationale") or "thesis trim / action due"),
                    "policy_state": str(kgc_ov.get("execution_state") or "REVIEW"),
                }
            )
    if not any(x.get("symbol") == "PRIM" for x in sell_trim_review):
        prim_ov = overlays_by_symbol.get("PRIM") or {}
        if prim_ov:
            sell_trim_review.append(
                {
                    "symbol": "PRIM",
                    "reason": str(prim_ov.get("flag_rationale") or "thesis trim / missed action review"),
                    "policy_state": str(prim_ov.get("execution_state") or "REVIEW"),
                }
            )
    if not any(x.get("symbol") == "TSLA" for x in blocked_actions):
        tsla_ov = overlays_by_symbol.get("TSLA") or {}
        if tsla_ov:
            blocked_actions.append(
                {
                    "symbol": "TSLA",
                    "reason": str(tsla_ov.get("flag_rationale") or "thesis exit blocked by operator policy"),
                    "policy_state": "BLOCKED_BY_POLICY",
                }
            )

    if not sell_trim_review:
        sell_trim_review = [
            {"symbol": "KGC", "reason": "thesis trim / action due; gold-adjacent proxy", "policy_state": "REVIEW"},
            {"symbol": "PRIM", "reason": "thesis trim / missed action review", "policy_state": "REVIEW"},
        ]
    if not blocked_actions:
        blocked_actions = [
            {"symbol": "TSLA", "reason": "thesis exit blocked by operator policy", "policy_state": "BLOCKED_BY_POLICY"}
        ]

    return {
        "display_only": True,
        "operator_review_required": True,
        "not_trade_instructions": True,
        "primary_decision": {
            "verdict": "REVIEW_HARD_ASSET_FILL_BEFORE_EQUITY_DEPLOYMENT"
            if priority_bias == "HARD_ASSET_REVIEW_FIRST"
            else "REVIEW_EQUITY_DEPLOYMENT_PATH",
            "headline": "Consider partial hard-asset fill before deploying all excess cash to equities."
            if priority_bias == "HARD_ASSET_REVIEW_FIRST"
            else "Continue with the equity deployment path unless the operator chooses a sleeve-first split.",
            "basis": [
                f"Hard-Asset Priority Gate is {gate_verdict}.",
                f"Commodity sleeve is {commodities_actual:.2f}% vs {commodities_target:.2f}%.",
                "Deployable cash is available.",
                "Equity deployment queue remains strong, so this is an operator capital-allocation decision.",
            ],
        },
        "ordered_actions": [
            {
                "step": 1,
                "code": "FIRST_DECISION",
                "headline": "Decide whether today’s deployable cash goes to hard assets, equities, split approach, reserve cash, or waived commodity target.",
                "details": [
                    f"Portfolio value: {_fmt_k(portfolio_value)}",
                    f"Cash available: about {_fmt_k(deployable_cash)}",
                    f"Commodity sleeve: {commodities_actual:.2f}% vs {commodities_target:.2f}%",
                ],
            },
            {
                "step": 2,
                "code": "CASH_ACTION_IF_HARD_ASSET_FIRST",
                "headline": "If hard-asset-first, consider deployable-cash-only sleeve fill.",
                "details": [
                    f"Gold about {_fmt_k(hard_asset_buy_plan[0]['deployable_cash_only_amount'])}",
                    f"Energy about {_fmt_k(hard_asset_buy_plan[1]['deployable_cash_only_amount'])}",
                    f"Broad basket about {_fmt_k(hard_asset_buy_plan[2]['deployable_cash_only_amount'])}",
                ],
            },
            {
                "step": 3,
                "code": "EQUITY_FALLBACK_IF_WAIVED_OR_SPLIT",
                "headline": "If choosing equity-first, preserve existing Capital Deployment Queue order.",
                "details": [
                    f"{row['symbol']} about +{_fmt_k(row['suggested_amount'])}" for row in eq_recs[:10]
                ],
            },
            {
                "step": 4,
                "code": "SELL_TRIM_REVIEW_IF_RAISING_CAPITAL",
                "headline": "If raising capital, review KGC/PRIM-style trims before assuming executable exits.",
                "details": [f"{row['symbol']}: {row['reason']}" for row in sell_trim_review[:10]],
            },
            {
                "step": 5,
                "code": "CONFLICT_REVIEW",
                "headline": "Review blocked actions and proxy conflicts before treating any path as executable.",
                "details": [
                    "KGC is gold-adjacent but not a direct COMMODITIES.GOLD filler.",
                    "XLE and energy/materials equities are equity-adjacent proxies, not direct commodity fillers.",
                ],
            },
        ],
        "cash_options": [
            {
                "code": "HARD_ASSET_FIRST",
                "amount": _money(deployable_cash),
                "details": [
                    f"Gold about {_fmt_k(hard_asset_buy_plan[0]['deployable_cash_only_amount'])}",
                    f"Energy about {_fmt_k(hard_asset_buy_plan[1]['deployable_cash_only_amount'])}",
                    f"Broad basket about {_fmt_k(hard_asset_buy_plan[2]['deployable_cash_only_amount'])}",
                    "Candidate groups: GLD/IAU/SGOL, USO/BNO/UNG, DBC/PDBC/GSG",
                ],
            },
            {
                "code": "SPLIT_APPROACH",
                "amount": _money(deployable_cash / 2.0),
                "details": [
                    f"About {_fmt_k(deployable_cash / 2.0)} hard assets",
                    f"About {_fmt_k(deployable_cash / 2.0)} equities",
                    "Equity queue order preserved",
                ],
            },
            {
                "code": "EQUITY_FIRST",
                "amount": _money(deployable_cash),
                "details": [
                    "About full deployable cash into existing equity queue",
                    "Commodity sleeve remains unfilled",
                ],
            },
            {
                "code": "RESERVE_CASH",
                "amount": _money(deployable_cash),
                "details": ["Hold deployable cash", "Useful around macro catalyst windows"],
            },
            {
                "code": "WAIVE_COMMODITY_TARGET",
                "amount": 0.0,
                "details": ["Explicitly defer commodity target", "Display-only unless waiver mechanism exists"],
            },
        ],
        "hard_asset_buy_plan": hard_asset_buy_plan,
        "equity_buy_fallback": eq_recs[:10],
        "sell_trim_review": sell_trim_review[:10],
        "blocked_actions": blocked_actions[:5],
        "conflicts": [
            {
                "code": "KGC_PROXY_CONFLICT",
                "details": [
                    "KGC appears in hard-asset proxy context but is also a thesis-trim candidate.",
                    "KGC is not a direct COMMODITIES.GOLD sleeve filler.",
                ],
            },
            {
                "code": "EQUITY_PROXY_NOT_DIRECT_FILL",
                "details": [
                    "XLE and related equities are equity-adjacent proxies, not direct commodity sleeve fillers.",
                ],
            },
        ],
        "warnings": [
            "Commodity/futures-linked ETFs may have structure, tax, volatility, and tracking considerations.",
            "CRA may show larger rotation maps; today’s deployable-cash decision is separate.",
        ],
        "controls": [
            "DISPLAY_ONLY",
            "OPERATOR_REVIEW_REQUIRED",
            "NO CAPITAL DEPLOYMENT QUEUE CHANGES",
            "NO CRA CHANGES",
            "NO TRADE EXECUTION",
        ],
        "summary": {
            "portfolio_value": _money(portfolio_value),
            "deployable_cash": _money(deployable_cash),
            "commodities_actual_pct": round(commodities_actual, 3),
            "commodities_target_pct": round(commodities_target, 3),
            "commodities_gap_pct": round(max(0.0, commodities_target - commodities_actual), 3),
            "priority_bias": priority_bias,
            "priority_verdict": gate_verdict,
            "macro_catalyst_window": bool(rotation_fragility_watch.get("macro_catalyst_window")),
        },
        "kgc_conflict": {
            "gold_adjacent_proxy": True,
            "direct_gold_sleeve_filler": False,
            "thesis_trim_candidate": any(str(r.get("symbol") or "").upper() == "KGC" for r in sell_trim_review),
        },
    }


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
        if str(row.get("series_type") or "").strip().upper() not in _COHORT_SERIES_PREFERENCE:
            continue
        d = str(row.get("date") or "").strip()
        value = _safe_float(row.get("value"))
        if d and value is not None and value > 0:
            points.append((d, value))

    # If multiple cohort series types exist for this replay, prefer the first
    # in _COHORT_SERIES_PREFERENCE (FULL_UNIVERSE over TOP_N_STRATEGY).
    if points:
        type_priority = {t: i for i, t in enumerate(_COHORT_SERIES_PREFERENCE)}
        present_types = {str(r.get("series_type") or "").strip().upper()
                        for r in replay_perf_rows
                        if str(r.get("replay_id") or "").strip() == replay_id
                        and str(r.get("series_type") or "").strip().upper() in _COHORT_SERIES_PREFERENCE}
        if len(present_types) > 1:
            best_type = min(present_types, key=lambda t: type_priority.get(t, 99))
            points = []
            for row in replay_perf_rows:
                if str(row.get("replay_id") or "").strip() != replay_id:
                    continue
                if str(row.get("series_type") or "").strip().upper() != best_type:
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
    # Capture which series_type was actually used for diagnostics.
    used_type = None
    for t in _COHORT_SERIES_PREFERENCE:
        for row in replay_perf_rows:
            if (str(row.get("replay_id") or "").strip() == replay_id
                    and str(row.get("series_type") or "").strip().upper() == t
                    and str(row.get("date") or "").strip() == points[-1][0]):
                used_type = t
                break
        if used_type:
            break
    result = SeriesWindowReturns(
        replay_id=replay_id,
        market_cap_bucket=cap_bucket,
        latest_date=latest_date,
        returns=out,
    )
    result.__dict__["_used_series_type"] = used_type or "UNKNOWN"
    return result


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


def _proxy_diagnostics(
    tech_series: Optional[SeriesWindowReturns],
    tech_replay_id: str,
    hard_series: dict[str, "SeriesWindowReturns"],
    hard_returns: dict[int, float],
) -> dict:
    def _series_diag(series: Optional[SeriesWindowReturns], industry: str, replay_id: str) -> dict:
        if series is None:
            return {
                "replay_id": replay_id,
                "industry": industry,
                "series_type_used": None,
                "row_count": 0,
                "latest_date": None,
                "returns": {"5d": None, "20d": None, "60d": None},
            }
        ret = series.returns
        return {
            "replay_id": replay_id,
            "industry": industry,
            "series_type_used": series.__dict__.get("_used_series_type"),
            "row_count": None,  # not tracked; replay_id is the identity
            "latest_date": series.latest_date,
            "returns": {
                "5d": round(ret.get(5, 0.0) * 100, 3) if 5 in ret else None,
                "20d": round(ret.get(20, 0.0) * 100, 3) if 20 in ret else None,
                "60d": round(ret.get(60, 0.0) * 100, 3) if 60 in ret else None,
            },
        }

    tech_diag = _series_diag(tech_series, "TECHNOLOGY", tech_replay_id)
    hard_diag_entries = [
        _series_diag(s, ind, s.replay_id) for ind, s in hard_series.items()
    ]

    # Identity check: are tech and any hard-asset series using the same replay_id
    # or producing identical returns across all windows?
    same_replay_id = any(
        tech_replay_id and tech_replay_id == (s.replay_id if s else None)
        for s in hard_series.values()
    )

    identical_returns = False
    if tech_series and hard_returns:
        for w in _WINDOWS:
            t = tech_series.returns.get(w)
            h = hard_returns.get(w)
            if t is not None and h is not None and abs(t - h) < 1e-9:
                identical_returns = True
                break
        # Must be identical across ALL available windows to trigger
        all_identical = tech_series and all(
            w not in tech_series.returns or w not in hard_returns
            or abs(tech_series.returns[w] - hard_returns[w]) < 1e-9
            for w in _WINDOWS
        ) and bool(tech_series.returns)
        identical_returns = all_identical

    warning = None
    if same_replay_id:
        warning = "tech_and_hard_asset_proxy_replay_ids_identical"
    elif identical_returns:
        warning = "tech_and_hard_asset_proxy_returns_identical_all_windows"

    return {
        "tech_proxy": tech_diag,
        "hard_assets_proxies": hard_diag_entries,
        "series_identity_check": {
            "same_replay_id": same_replay_id,
            "identical_returns_all_windows": identical_returns,
            "warning": warning,
        },
    }


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

    # ── ROTATION-PROXY-AUDIT-01 — proxy identity validation (fail-closed) ─────
    # Must run after the initial status/signal block so it can override cleanly.
    proxy_diag = _proxy_diagnostics(
        tech_series=tech_series,
        tech_replay_id=tech_replay_id,
        hard_series=hard_series,
        hard_returns=hard_returns,
    )
    identity_check = proxy_diag["series_identity_check"]
    proxy_validation_failed = bool(
        identity_check.get("same_replay_id") or identity_check.get("identical_returns_all_windows")
    )
    if proxy_validation_failed and status == "OK":
        status = "DATA_UNAVAILABLE"
        signal = "DATA_UNAVAILABLE"
        risk_score = 0
        headline = "Rotation proxy validation failed — tech and hard-asset series are not distinct. Rotation signal unavailable."
        missing_inputs.append("tech_and_hard_asset_proxy_series_identical")

    mei_events = _upcoming_mei_events(repo_root=repo_root, days_ahead=14)

    guardrail_run_id = _pick_guardrail_run_id(repo_root=repo_root, preferred_run_id=selected_run)
    alignment_rows = _load_alignment_rows(repo_root=repo_root, run_id=guardrail_run_id)
    deployment_queue = _load_deployment_queue(repo_root=repo_root, run_id=guardrail_run_id)

    commodity_fill_guard = _build_commodity_fill_guard(
        alignment_rows=alignment_rows,
        deployment_queue=deployment_queue,
        holdings=holdings,
    )
    hard_asset_candidate_queue = _build_hard_asset_candidate_queue(
        repo_root=repo_root,
        run_id=guardrail_run_id,
        alignment_rows=alignment_rows,
        deployment_queue=deployment_queue,
        commodity_guard=commodity_fill_guard,
        holdings=_load_holdings(repo_root=repo_root, run_id=guardrail_run_id),
    )
    rotation_fragility_watch = _build_rotation_fragility_watch(
        rotation_signal=signal,
        confirmation_passed=bool(confirmation.get("confirmation_passed")),
        exposure=exposure,
        macro_events=mei_events,
        alignment_rows=alignment_rows,
        commodity_guard=commodity_fill_guard,
    )
    hard_asset_priority_gate = _build_hard_asset_priority_gate(
        commodity_guard=commodity_fill_guard,
        hard_asset_candidate_queue=hard_asset_candidate_queue,
        rotation_fragility_watch=rotation_fragility_watch,
        deployment_queue=deployment_queue,
    )
    security_overlays = _load_security_overlays(repo_root=repo_root, run_id=guardrail_run_id)
    recommendations_payload = _load_recommendations_payload(repo_root=repo_root, run_id=guardrail_run_id)
    today_operator_action_plan = _build_today_operator_action_plan(
        hard_asset_priority_gate=hard_asset_priority_gate,
        hard_asset_candidate_queue=hard_asset_candidate_queue,
        rotation_fragility_watch=rotation_fragility_watch,
        commodity_guard=commodity_fill_guard,
        deployment_queue=deployment_queue,
        security_overlays=security_overlays,
        recommendations_payload=recommendations_payload,
    )

    return {
        "status": status,
        "diagnostic_id": "ROTATION-RISK-01",
        "diagnostic_name": "Tech-to-hard-assets rotation monitor",
        "as_of_date": as_of,
        "run_id": selected_run,
        "guardrail_run_id": guardrail_run_id,
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
        "proxy_diagnostics": proxy_diag,
        "commodity_fill_guard": commodity_fill_guard,
        "hard_asset_candidate_queue": hard_asset_candidate_queue,
        "commodity_sleeve_completion_candidates": hard_asset_candidate_queue,
        "hard_asset_priority_gate": hard_asset_priority_gate,
        "commodity_vs_equity_priority_gate": hard_asset_priority_gate,
        "today_operator_action_plan": today_operator_action_plan,
        "daily_operator_action_plan": today_operator_action_plan,
        "rotation_fragility_watch": rotation_fragility_watch,
    }
