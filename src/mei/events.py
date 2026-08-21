"""MEI-001 — Weekly Market Event Calendar.

Reads the curated event calendar from data/mei/event_calendar.json and returns
events filtered to a configurable lookahead window.  This module is STRICTLY
READ-ONLY — it never modifies any existing data or recommendation artifacts.

Public API
----------
  mei_events(repo_root, days_ahead=14)  → dict  (full calendar payload)
  mei_events_summary(repo_root)         → dict  (summary cards payload)
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

_DEFAULT_DAYS_AHEAD = 14
_CALENDAR_FILENAME = "data/mei/event_calendar.json"

# Impact ordering for sorting purposes
_IMPACT_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# ─── I/O helpers ─────────────────────────────────────────────────────────────


def _repo(repo_root: Optional[Path]) -> Path:
    if repo_root is not None:
        return Path(repo_root)
    return Path(__file__).resolve().parents[2]


def _load_events(repo_root: Optional[Path] = None) -> list[dict]:
    path = _repo(repo_root) / _CALENDAR_FILENAME
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ─── Filtering helpers ────────────────────────────────────────────────────────


def _in_window(event: dict, start: date, end: date) -> bool:
    try:
        start_raw = str(event.get("start_date") or event.get("event_date") or "")
        end_raw = str(event.get("end_date") or start_raw)
        event_start = date.fromisoformat(start_raw)
        event_end = date.fromisoformat(end_raw)
        return event_start <= end and event_end >= start
    except ValueError:
        return False


def _days_away(event: dict, today: date) -> int:
    try:
        start_raw = str(event.get("start_date") or event.get("event_date") or "")
        return (date.fromisoformat(start_raw) - today).days
    except (KeyError, ValueError):
        return 9999


# ─── Observation generator ────────────────────────────────────────────────────


def _generate_observations(
    events_by_impact: dict[str, list[dict]], today: date
) -> list[str]:
    obs: list[str] = []
    high = events_by_impact.get("HIGH", [])
    medium = events_by_impact.get("MEDIUM", [])

    if not high and not medium:
        obs.append("No HIGH or MEDIUM impact events in the next 14 days.")
        return obs

    for ev in sorted(high, key=lambda e: e.get("event_date", ""))[:2]:
        d = _days_away(ev, today)
        when = "today" if d == 0 else ("tomorrow" if d == 1 else f"in {d} days")
        obs.append(
            f"{ev.get('event_name', 'Unknown event')} occurs {when} ({ev.get('event_date','')})."
            f"  Impact: HIGH.  Sensitivity tags: {', '.join(ev.get('sensitivity_tags', []))or 'N/A'}."
        )

    if len(high) > 2:
        obs.append(f"{len(high) - 2} additional HIGH impact event(s) in the next 14 days.")

    return obs


# ─── Public API ───────────────────────────────────────────────────────────────


def mei_events(
    repo_root: Optional[Path] = None,
    days_ahead: int = _DEFAULT_DAYS_AHEAD,
) -> dict:
    """Return events within the next *days_ahead* days from today.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "window_days": int,
      "window_end": "YYYY-MM-DD",
      "total_events": int,
      "high_impact_count": int,
      "medium_impact_count": int,
      "low_impact_count": int,
      "next_high_event": {event_id, event_name, event_date, days_away} | None,
      "events": [...],           # all events in window, sorted by date
      "events_by_impact": {HIGH: [...], MEDIUM: [...], LOW: [...]},
    }
    """
    today = date.today()
    end = today + timedelta(days=days_ahead)
    all_events = _load_events(repo_root)

    windowed: list[dict] = []
    for ev in all_events:
        if _in_window(ev, today, end):
            windowed.append({**ev, "days_away": _days_away(ev, today)})

    windowed.sort(key=lambda e: (e.get("event_date", ""), _IMPACT_ORDER.get(str(e.get("impact_level")), 9)))

    high = [e for e in windowed if e.get("impact_level") == "HIGH"]
    medium = [e for e in windowed if e.get("impact_level") == "MEDIUM"]
    low = [e for e in windowed if e.get("impact_level") == "LOW"]

    next_high = high[0] if high else None

    return {
        "as_of_date": today.isoformat(),
        "window_days": days_ahead,
        "window_end": end.isoformat(),
        "total_events": len(windowed),
        "high_impact_count": len(high),
        "medium_impact_count": len(medium),
        "low_impact_count": len(low),
        "next_high_event": {
            "event_id": next_high["event_id"],
            "event_name": next_high["event_name"],
            "event_date": next_high["event_date"],
            "days_away": next_high["days_away"],
        } if next_high else None,
        "events": windowed,
        "events_by_impact": {"HIGH": high, "MEDIUM": medium, "LOW": low},
    }


def mei_events_summary(repo_root: Optional[Path] = None) -> dict:
    """Return summary cards for the MEI event calendar dashboard section.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "events_next_14_days": int,
      "high_impact_next_14_days": int,
      "medium_impact_next_14_days": int,
      "events_next_30_days": int,
      "next_high_impact_event": {event dict} | None,
      "observations": [str, ...]
    }
    """
    today = date.today()
    all_events = _load_events(repo_root)

    end_14 = today + timedelta(days=14)
    end_30 = today + timedelta(days=30)

    upcoming_14 = [e for e in all_events if _in_window(e, today, end_14)]
    upcoming_30 = [e for e in all_events if _in_window(e, today, end_30)]

    high_14 = [e for e in upcoming_14 if e.get("impact_level") == "HIGH"]
    medium_14 = [e for e in upcoming_14 if e.get("impact_level") == "MEDIUM"]

    sorted_high = sorted(high_14, key=lambda e: e.get("event_date", ""))
    next_high = (
        {**sorted_high[0], "days_away": _days_away(sorted_high[0], today)}
        if sorted_high else None
    )

    by_impact: dict[str, list[dict]] = {
        "HIGH": [{**e, "days_away": _days_away(e, today)} for e in sorted_high],
        "MEDIUM": [],
        "LOW": [],
    }
    obs = _generate_observations(by_impact, today)

    return {
        "as_of_date": today.isoformat(),
        "events_next_14_days": len(upcoming_14),
        "high_impact_next_14_days": len(high_14),
        "medium_impact_next_14_days": len(medium_14),
        "events_next_30_days": len(upcoming_30),
        "next_high_impact_event": next_high,
        "observations": obs,
    }
