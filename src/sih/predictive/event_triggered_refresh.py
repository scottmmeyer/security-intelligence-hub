"""MEI-004 — Event-Triggered Signal Refresh.

After a HIGH-impact MEI event fires, schedules or suggests a signal refresh
for holdings most exposed to the event.

The refresh infrastructure (scripts/refresh_signals.py) already exists.
This module provides the trigger logic and tracks refresh suggestions.

Governance: Read-only. No signal data is modified; only a refresh suggestion
is produced. Actual refresh requires operator confirmation or schedule trigger.

Public API
----------
  check_pending_refresh_triggers(repo_root) → dict
  mark_event_processed(event_id, repo_root) → None
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_TRIGGERS_FILE   = "data/mei/refresh_triggers.json"
_OUTCOMES_FILE   = "data/mei/event_outcomes.json"
_CALENDAR_FILE   = "data/mei/event_calendar.json"

_TRIGGER_IMPACT_LEVELS = frozenset({"HIGH"})  # Only HIGH events trigger

_GOVERNANCE_NOTE = (
    "MEI-004 is advisory only. "
    "Signal refresh triggers are suggestions — no automatic data modification occurs. "
    "Operators initiate actual refreshes through the signal refresh panel."
)


def _load_events(repo_root: Path) -> List[Dict]:
    """Load all events (historical + forward calendar)."""
    events = []
    for fname in ["data/mei/historical_events.json", _CALENDAR_FILE]:
        path = repo_root / fname
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                events.extend(data if isinstance(data, list) else [])
            except (OSError, json.JSONDecodeError):
                pass
    return events


def _load_trigger_state(repo_root: Path) -> Dict:
    path = repo_root / _TRIGGERS_FILE
    if not path.exists():
        return {"processed_events": [], "last_checked": ""}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"processed_events": [], "last_checked": ""}


def _save_trigger_state(repo_root: Path, state: Dict) -> None:
    path = repo_root / _TRIGGERS_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def _load_exposures(repo_root: Path, event_id: str) -> List[str]:
    """Load highest-exposure symbols for an event from MEI exposure data."""
    try:
        from src.mei.exposures import mei_exposures
        data = mei_exposures(repo_root)
        for ev_exp in data.get("events", []):
            if ev_exp.get("event_id") == event_id:
                highs = [s.get("symbol") for s in ev_exp.get("high_exposure", []) if s.get("symbol")]
                mods  = [s.get("symbol") for s in ev_exp.get("moderate_exposure", []) if s.get("symbol")]
                return (highs + mods)[:20]
    except Exception:
        pass
    return []


def check_pending_refresh_triggers(repo_root: Path | str = ".") -> Dict:
    """
    Check for HIGH-impact events that have fired (past due date) and
    have not yet triggered a signal refresh suggestion.

    Returns:
        { pending: [{event_id, event_name, event_date, days_ago, affected_symbols}],
          last_checked, governance_note }
    """
    root    = Path(repo_root)
    today   = date.today()
    state   = _load_trigger_state(root)
    processed = set(state.get("processed_events", []))
    events  = _load_events(root)

    pending = []
    for ev in events:
        try:
            ev_date = date.fromisoformat(str(ev.get("event_date", "")))
        except ValueError:
            continue

        if ev_date > today:
            continue  # Future event
        if ev.get("impact_level") not in _TRIGGER_IMPACT_LEVELS:
            continue
        eid = str(ev.get("event_id", ""))
        if not eid or eid in processed:
            continue

        days_ago = (today - ev_date).days
        exposed_syms = _load_exposures(root, eid)

        pending.append({
            "event_id":          eid,
            "event_name":        ev.get("event_name", ""),
            "event_type":        ev.get("event_type", ""),
            "event_date":        str(ev_date),
            "days_ago":          days_ago,
            "impact_level":      ev.get("impact_level", ""),
            "sensitivity_tags":  ev.get("sensitivity_tags", []),
            "affected_symbols":  exposed_syms,
            "refresh_suggestion": f"Consider refreshing Zacks + Danelfin signals for {len(exposed_syms)} exposed holdings.",
        })

    # Sort: most recent first
    pending.sort(key=lambda p: p["event_date"], reverse=True)

    state["last_checked"] = today.isoformat()
    _save_trigger_state(root, state)

    return {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "pending_count":  len(pending),
        "pending":        pending[:10],
        "governance_note": _GOVERNANCE_NOTE,
    }


def mark_event_processed(event_id: str, repo_root: Path | str = ".") -> None:
    """Mark an event as having triggered a refresh (clears from pending list)."""
    root  = Path(repo_root)
    state = _load_trigger_state(root)
    processed = set(state.get("processed_events", []))
    processed.add(event_id.strip())
    state["processed_events"] = sorted(processed)
    _save_trigger_state(root, state)
