"""Display-only action-latency escalation for reduction candidates.

ACTION-LATENCY-01 scope and governance:
- Advisory-only classification layer.
- No mutation of scoring, ranking, allocation, recommendation, CW-DAS, CRA,
  UCF, PAP, Replay, or execution workflows.
- Uses existing recommendation lineage + action attribution artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from src.pis.action_attribution import pis_action_attribution_recommendations
from src.pis.recommendation_lineage import build_recommendation_candidates

_REDUCE_SOURCES = frozenset({"REDUCTION_QUEUE", "CRA", "DIL"})
_ACTED_STATUSES = frozenset({"FOLLOWED", "PARTIALLY_FOLLOWED"})


@dataclass(frozen=True)
class ActionLatencyInput:
    symbol: str
    snapshot_date: str
    active_reduction_intent: bool
    conviction_protected: bool
    first_trim_signal_date: Optional[str]
    last_action_status: str
    acted_after_signal: bool
    return_1d: Optional[float]
    return_5d: Optional[float]
    return_1m: Optional[float]
    action_window_days: int = 7


def _safe_iso_date(raw: str | None) -> Optional[date]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _days_between(older: str | None, newer: str | None) -> Optional[int]:
    d_old = _safe_iso_date(older)
    d_new = _safe_iso_date(newer)
    if d_old is None or d_new is None:
        return None
    return (d_new - d_old).days


def _adverse_triggers(*, r1d: Optional[float], r5d: Optional[float], r1m: Optional[float]) -> list[str]:
    triggers: list[str] = []
    if r1d is not None and r1d <= -8.0:
        triggers.append(f"1D drawdown {r1d:.2f}% <= -8.00%")
    if r5d is not None and r5d <= -10.0:
        triggers.append(f"5D drawdown {r5d:.2f}% <= -10.00%")
    if r1m is not None and r1m <= -20.0:
        triggers.append(f"1M drawdown {r1m:.2f}% <= -20.00%")
    return triggers


def evaluate_action_latency_state(inp: ActionLatencyInput) -> dict:
    """Classify display-only action-latency state for one symbol."""
    symbol = inp.symbol.upper()
    age_days = _days_between(inp.first_trim_signal_date, inp.snapshot_date)
    triggers = _adverse_triggers(r1d=inp.return_1d, r5d=inp.return_5d, r1m=inp.return_1m)
    adverse_move = len(triggers) > 0

    out = {
        "symbol": symbol,
        "status": "NONE",
        "first_trim_signal_date": inp.first_trim_signal_date or "",
        "signal_age_days": age_days,
        "last_action_status": inp.last_action_status or "",
        "acted_after_signal": bool(inp.acted_after_signal),
        "active_reduction_intent": bool(inp.active_reduction_intent),
        "conviction_protected": bool(inp.conviction_protected),
        "adverse_move_triggered": adverse_move,
        "adverse_move_triggers": triggers,
        "message": "",
    }

    if not inp.active_reduction_intent:
        out["message"] = "No active trim intent detected for this holding."
        return out

    if inp.conviction_protected:
        out["message"] = "Conviction-protected holding; missed-action escalation suppressed."
        return out

    if inp.acted_after_signal:
        out["message"] = "Trim/exit action already observed after signal generation."
        return out

    # No historical first-seen date available: still surface near-term action due,
    # but do not classify as MISSED_ACTION_REVIEW.
    if age_days is None:
        if adverse_move:
            out["status"] = "ACTION_DUE"
            out["message"] = (
                "Active trim intent with adverse move detected, but no historical first-seen "
                "signal date is available for latency aging."
            )
        else:
            out["status"] = "ACTION_DUE"
            out["message"] = "Active trim intent detected; operator review is due."
        return out

    is_stale = age_days >= max(1, int(inp.action_window_days))

    if is_stale and adverse_move:
        out["status"] = "MISSED_ACTION_REVIEW"
        out["message"] = (
            "Prior trim signal aged without action and adverse move thresholds were breached. "
            "Review trim, hold override, or exit decision."
        )
        return out

    if is_stale and not adverse_move:
        out["status"] = "TRIM_SIGNAL_AGING"
        out["message"] = "Trim signal is aging without observed action."
        return out

    out["status"] = "ACTION_DUE"
    out["message"] = "Recent trim signal detected; operator review is due."
    return out


def _is_active_reduction_intent(
    *,
    overlay: dict,
    fidelity: dict,
    ucf: dict,
) -> bool:
    ucf_label = str(ucf.get("ucf_label") or "").upper()
    if ucf_label == "TRIM_WATCH":
        return True

    opportunity_flag = str(overlay.get("opportunity_flag") or "").upper()
    if opportunity_flag in {"TRIM", "WATCH"}:
        return True

    ess_text = str(fidelity.get("ess_text") or overlay.get("ess_score_text") or "").upper()
    fid_rating = str(fidelity.get("fidelity_rating") or "").upper()
    if "BEARISH" in ess_text or fid_rating in {"SELL", "STRONG_SELL"}:
        return True

    try:
        zacks = float(overlay.get("zacks_rating") or 0)
    except (TypeError, ValueError):
        zacks = 0.0
    if zacks >= 3.5:
        return True

    return False


def _history_maps(*, repo_root: Path, symbols: set[str]) -> tuple[dict[str, str], dict[str, dict]]:
    """Return (first_trim_signal_date_by_symbol, latest_action_record_by_symbol)."""
    first_seen: dict[str, str] = {}
    latest_action: dict[str, dict] = {}

    try:
        candidates = build_recommendation_candidates(
            analysis_runs_root=repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
        )
        for row in candidates:
            sym = str(row.get("symbol") or "").upper()
            src = str(row.get("source") or "").upper()
            direction = str(row.get("direction") or "").upper()
            rec_date = str(row.get("recommendation_date") or "")[:10]
            if not sym or sym not in symbols:
                continue
            if src not in _REDUCE_SOURCES or direction != "REDUCE" or not rec_date:
                continue
            if sym not in first_seen or rec_date < first_seen[sym]:
                first_seen[sym] = rec_date
    except Exception:
        pass

    try:
        payload = pis_action_attribution_recommendations(repo_root=repo_root)
        for row in payload.get("records", []):
            sym = str(row.get("symbol") or "").upper()
            src = str(row.get("recommendation_source") or "").upper()
            direction = str(row.get("recommended_direction") or "").upper()
            rec_date = str(row.get("recommendation_date") or "")[:10]
            if not sym or sym not in symbols:
                continue
            if src not in _REDUCE_SOURCES or direction != "REDUCE":
                continue
            prev = latest_action.get(sym)
            if prev is None or rec_date > str(prev.get("recommendation_date") or "")[:10]:
                latest_action[sym] = row
    except Exception:
        pass

    return first_seen, latest_action


def build_action_latency_by_symbol(
    *,
    repo_root: Path | str,
    symbols: list[str],
    snapshot_date: str,
    overlays_by_symbol: dict[str, dict],
    fidelity_by_symbol: dict[str, dict],
    ucf_by_symbol: dict[str, dict],
    price_context_by_symbol: dict[str, dict],
    action_window_days: int = 7,
) -> dict[str, dict]:
    """Build display-only action-latency payload keyed by symbol."""
    root = Path(repo_root)
    normalized = sorted({str(s or "").upper() for s in symbols if str(s or "").strip()})
    symbol_set = set(normalized)
    first_seen_map, latest_action_map = _history_maps(repo_root=root, symbols=symbol_set)

    result: dict[str, dict] = {}
    for sym in normalized:
        ov = overlays_by_symbol.get(sym, {}) if overlays_by_symbol else {}
        fs = fidelity_by_symbol.get(sym, {}) if fidelity_by_symbol else {}
        ucf = ucf_by_symbol.get(sym, {}) if ucf_by_symbol else {}
        pc = price_context_by_symbol.get(sym, {}) if price_context_by_symbol else {}

        ucf_label = str(ucf.get("ucf_label") or "").upper()
        conviction_protected = ucf_label in {"CORE_CONVICTION_LEADER", "HIGH_CONVICTION_ANCHOR"}
        active_intent = _is_active_reduction_intent(overlay=ov, fidelity=fs, ucf=ucf)

        last_action = latest_action_map.get(sym, {})
        last_status = str(last_action.get("action_status") or "")
        acted_after_signal = last_status in _ACTED_STATUSES

        entry = evaluate_action_latency_state(
            ActionLatencyInput(
                symbol=sym,
                snapshot_date=snapshot_date,
                active_reduction_intent=active_intent,
                conviction_protected=conviction_protected,
                first_trim_signal_date=first_seen_map.get(sym),
                last_action_status=last_status,
                acted_after_signal=acted_after_signal,
                return_1d=_to_float_or_none(pc.get("return_1d")),
                return_5d=_to_float_or_none(pc.get("return_5d")),
                return_1m=_to_float_or_none(pc.get("return_1m")),
                action_window_days=action_window_days,
            )
        )

        # Keep relevant source context for UI explainability.
        entry["ucf_label"] = ucf_label
        entry["ess_text"] = str(fs.get("ess_text") or ov.get("ess_score_text") or "")
        entry["fidelity_rating"] = str(fs.get("fidelity_rating") or "")
        entry["opportunity_flag"] = str(ov.get("opportunity_flag") or "")
        result[sym] = entry

    return result


def _to_float_or_none(value: object) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
