"""MEI-004 — Recommendation Context Overlay.

Overlays upcoming market event awareness on active recommendations.
Display-only — no recommendation, score, or ranking is ever modified.

For each actionable recommendation (DEPLOYMENT_CANDIDATE, REDUCE_OVERWEIGHT,
INCREASE_UNDERWEIGHT), determines:
  - Whether any HIGH/MEDIUM impact events occur in the next 14 days
  - The highest sensitivity level to those events' tags
  - A plain-language operator note

Reads from:
  - Latest PAR deployment_queue.json
  - Latest PAR recommendations.json
  - src/mei/events.py
  - src/mei/security_profiles.py

Public API
----------
  mei_recommendation_context(repo_root)         → dict
  mei_recommendation_context_summary(repo_root) → dict
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Optional

from src.mei.events import mei_events, _days_away
from src.mei.security_profiles import mei_security_profiles_bulk

_ACTIONABLE_REC_TYPES = {
    "REDUCE_OVERWEIGHT",
    "INCREASE_UNDERWEIGHT",
}

_LEVEL_ORDER = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "NONE": 3}
_IMPACT_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# ─── I/O helpers ─────────────────────────────────────────────────────────────


def _repo(repo_root: Optional[Path]) -> Path:
    return Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]


def _latest_par_run(repo_root: Path) -> Optional[Path]:
    runs_root = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not runs_root.exists():
        return None
    dirs = [d for d in runs_root.iterdir() if d.is_dir() and (d / "run_metadata.json").exists()]
    if not dirs:
        return None

    def _ts(d: Path) -> str:
        try:
            return str(json.loads((d / "run_metadata.json").read_text(encoding="utf-8")).get("created_at_utc", ""))
        except Exception:
            return d.name

    return max(dirs, key=_ts)


def _safe_float(v: object, default: float = 0.0) -> float:
    try:
        return float(str(v or "").strip() or default)
    except (TypeError, ValueError):
        return default


# ─── Recommendation loaders ───────────────────────────────────────────────────


def _load_deployment_candidates(run: Path) -> list[dict]:
    """Load BUY-side candidates from deployment_queue.json."""
    path = run / "deployment_queue.json"
    if not path.exists():
        return []
    try:
        dq = json.loads(path.read_text(encoding="utf-8"))
        queue = dq.get("queue", []) if isinstance(dq, dict) else []
        result: list[dict] = []
        for item in queue:
            sym = str(item.get("symbol", "")).strip().upper()
            if not sym:
                continue
            result.append({
                "symbol": sym,
                "recommendation_type": "DEPLOYMENT_CANDIDATE",
                "composite_score": _safe_float(item.get("composite_score")),
                "narrative_tier": str(item.get("narrative_tier", "")),
                "rank": int(item.get("rank", 0)),
            })
        return result
    except Exception:
        return []


def _load_actionable_recommendations(run: Path) -> list[dict]:
    """Load SELL/INCREASE side from recommendations.json."""
    path = run / "recommendations.json"
    if not path.exists():
        return []
    try:
        recs = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(recs, list):
            return []
        result: list[dict] = []
        for rec in recs:
            rec_type = str(rec.get("recommendation_type", "")).strip()
            if rec_type not in _ACTIONABLE_REC_TYPES:
                continue
            for sym in rec.get("affected_symbols", []):
                sym = str(sym).strip().upper()
                if sym:
                    result.append({
                        "symbol": sym,
                        "recommendation_type": rec_type,
                        "priority": int(rec.get("priority", 5)),
                        "confidence": str(rec.get("confidence", "")),
                        "title": str(rec.get("title", "")),
                    })
        return result
    except Exception:
        return []


# ─── Context derivation ───────────────────────────────────────────────────────


def _highest_level(sensitivities: dict[str, str], tags: list[str]) -> str:
    levels = [sensitivities.get(tag, "NONE") for tag in tags]
    best = "NONE"
    for lv in levels:
        if _LEVEL_ORDER.get(lv, 9) < _LEVEL_ORDER.get(best, 9):
            best = lv
    return best


def _build_operator_note(
    symbol: str,
    rec_type: str,
    upcoming_events: list[dict],
    max_sensitivity: str,
) -> str:
    if not upcoming_events:
        return (
            f"No HIGH or MEDIUM impact events in the next 14 days. "
            f"{rec_type.replace('_', ' ').title()} recommendation unlikely to be "
            f"impacted by near-term macro events."
        )

    event_names = [e["event_name"] for e in upcoming_events[:2]]
    events_str = " and ".join(event_names)
    days = upcoming_events[0]["days_away"]
    when = "today" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")

    if max_sensitivity == "HIGH":
        return (
            f"{events_str} occurs {when}. {symbol} has HIGH event sensitivity. "
            f"Near-term volatility possible despite intact thesis. "
            f"Consider timing in context of event outcome."
        )
    elif max_sensitivity == "MODERATE":
        return (
            f"{events_str} occurs {when}. {symbol} has MODERATE event sensitivity. "
            f"Modest near-term volatility possible; thesis intact."
        )
    else:
        return (
            f"{events_str} occurs {when}. {symbol} has LOW sensitivity to this event. "
            f"Recommendation unlikely to be materially impacted."
        )


# ─── Public API ───────────────────────────────────────────────────────────────


def mei_recommendation_context(repo_root: Optional[Path] = None) -> dict:
    """Return event context overlay for all active recommendations.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "analysis_run_id": str | None,
      "total_recommendations": int,
      "event_exposed_count": int,
      "clean_count": int,
      "items": [
        {
          "symbol": str,
          "recommendation_type": str,
          "composite_score": float | None,
          "narrative_tier": str,
          "upcoming_events": [
            {"event_id", "event_name", "event_date", "days_away", "impact_level",
             "sensitivity_tags", "symbol_sensitivity"}
          ],
          "max_sensitivity": "HIGH" | "MODERATE" | "LOW" | "NONE",
          "event_exposure_label": "EVENT_EXPOSED" | "CLEAN",
          "operator_note": str,
        }, ...
      ]
    }
    """
    root = _repo(repo_root)
    today = date.today()

    run = _latest_par_run(root)
    analysis_run_id: Optional[str] = None
    if run is not None:
        try:
            meta = json.loads((run / "run_metadata.json").read_text(encoding="utf-8"))
            analysis_run_id = meta.get("run_id")
        except Exception:
            analysis_run_id = run.name

    # Collect recommendations
    all_recs: list[dict] = []
    if run is not None:
        all_recs.extend(_load_deployment_candidates(run))
        all_recs.extend(_load_actionable_recommendations(run))

    # Dedup by symbol (keep first / highest-priority entry)
    seen: set[str] = set()
    deduped: list[dict] = []
    for rec in all_recs:
        sym = rec["symbol"]
        if sym not in seen:
            seen.add(sym)
            deduped.append(rec)

    # Load upcoming events (HIGH/MEDIUM only — actionable)
    cal = mei_events(root)
    upcoming = [
        e for e in cal.get("events", [])
        if e.get("impact_level") in {"HIGH", "MEDIUM"}
    ]
    upcoming.sort(key=lambda e: e.get("event_date", ""))

    # Build profiles
    symbols = [r["symbol"] for r in deduped]
    profiles_payload = mei_security_profiles_bulk(symbols, root)
    profiles = profiles_payload.get("profiles", {})

    items: list[dict] = []
    for rec in deduped:
        sym = rec["symbol"]
        sens = profiles.get(sym, {}).get("sensitivities", {})

        # Find events where symbol has any sensitivity to event's tags
        matched_events: list[dict] = []
        for ev in upcoming:
            tags = ev.get("sensitivity_tags", [])
            level = _highest_level(sens, tags)
            if level != "NONE":
                matched_events.append({
                    "event_id": ev.get("event_id", ""),
                    "event_name": ev.get("event_name", ""),
                    "event_date": ev.get("event_date", ""),
                    "days_away": _days_away(ev, today),
                    "impact_level": ev.get("impact_level", ""),
                    "sensitivity_tags": tags,
                    "symbol_sensitivity": level,
                })

        matched_events.sort(key=lambda e: (e["days_away"], _IMPACT_ORDER.get(e["impact_level"], 9)))

        if matched_events:
            levels = [e["symbol_sensitivity"] for e in matched_events]
            best_level = min(levels, key=lambda lv: _LEVEL_ORDER.get(lv, 9))
        else:
            best_level = "NONE"

        label = "EVENT_EXPOSED" if matched_events else "CLEAN"
        note = _build_operator_note(sym, rec["recommendation_type"], matched_events, best_level)

        items.append({
            "symbol": sym,
            "recommendation_type": rec["recommendation_type"],
            "composite_score": rec.get("composite_score"),
            "narrative_tier": rec.get("narrative_tier", ""),
            "rank": rec.get("rank"),
            "upcoming_events": matched_events,
            "max_sensitivity": best_level,
            "event_exposure_label": label,
            "operator_note": note,
        })

    # Sort: DEPLOYMENT_CANDIDATE first, then by rank/priority
    items.sort(key=lambda x: (
        0 if x["recommendation_type"] == "DEPLOYMENT_CANDIDATE" else 1,
        x.get("rank") or x.get("priority") or 99,
    ))

    exposed = [i for i in items if i["event_exposure_label"] == "EVENT_EXPOSED"]
    clean = [i for i in items if i["event_exposure_label"] == "CLEAN"]

    return {
        "as_of_date": today.isoformat(),
        "analysis_run_id": analysis_run_id,
        "total_recommendations": len(items),
        "event_exposed_count": len(exposed),
        "clean_count": len(clean),
        "items": items,
    }


def mei_recommendation_context_summary(repo_root: Optional[Path] = None) -> dict:
    """Return summary stats for the recommendation context overlay.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "total_recommendations": int,
      "event_exposed_count": int,
      "clean_count": int,
      "high_sensitivity_exposed": int,
      "observations": [str, ...]
    }
    """
    root = _repo(repo_root)
    full = mei_recommendation_context(root)

    items = full.get("items", [])
    exposed = [i for i in items if i["event_exposure_label"] == "EVENT_EXPOSED"]
    high_sens = [i for i in exposed if i["max_sensitivity"] == "HIGH"]

    obs: list[str] = []
    if not items:
        obs.append("No active recommendations to evaluate.")
    elif not exposed:
        obs.append("No active recommendations have event exposure in the next 14 days.")
    else:
        obs.append(
            f"{len(exposed)} of {len(items)} active recommendations have upcoming event exposure."
        )
        if high_sens:
            syms = ", ".join(i["symbol"] for i in high_sens[:5])
            obs.append(f"HIGH sensitivity event exposure: {syms}.")
        obs.append("MEI is informational only — no recommendation scores or rankings are modified.")

    return {
        "as_of_date": full.get("as_of_date", ""),
        "analysis_run_id": full.get("analysis_run_id"),
        "total_recommendations": full.get("total_recommendations", 0),
        "event_exposed_count": full.get("event_exposed_count", 0),
        "clean_count": full.get("clean_count", 0),
        "high_sensitivity_exposed": len(high_sens),
        "observations": obs,
    }
