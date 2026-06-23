"""MEI-005 — Event Impact History.

Tracks the portfolio's observed behavior around historical market events.
Provides a long-term learning repository for event attribution.

History entries are appended to data/mei/event_history.json by the
operator or future automation (not generated automatically in Phase 1).

Phase 1 returns the existing history as-is.  If no history has been
recorded yet, returns an empty history with appropriate messaging.

This module is STRICTLY READ-ONLY with respect to all PAR artifacts,
ESS snapshots, CW-DAS, UCF, CRA, and PIS data.

Public API
----------
  mei_event_history(repo_root)         → dict  (full history payload)
  mei_event_history_summary(repo_root) → dict  (summary cards)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

_HISTORY_FILENAME = "data/mei/event_history.json"


# ─── I/O helpers ─────────────────────────────────────────────────────────────


def _repo(repo_root: Optional[Path]) -> Path:
    return Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_history(repo_root: Optional[Path] = None) -> list[dict]:
    path = _repo(repo_root) / _HISTORY_FILENAME
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _safe_float(v: object) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


# ─── Public API ───────────────────────────────────────────────────────────────


def mei_event_history(repo_root: Optional[Path] = None) -> dict:
    """Return full historical event impact log.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "total_events_tracked": int,
      "last_event_date": "YYYY-MM-DD" | None,
      "events": [
        {
          "event_id": str,
          "event_name": str,
          "event_date": str,
          "event_type": str,
          "portfolio_return_pct": float | None,
          "best_performers": [str],
          "worst_performers": [str],
          "notes": str,
          "recorded_at": str | None,
        }, ...
      ]
    }
    """
    root = _repo(repo_root)
    today = date.today()
    history = _load_history(root)

    # Sort descending by event_date
    history.sort(key=lambda e: e.get("event_date", ""), reverse=True)

    last_date = history[0]["event_date"] if history else None

    normalized: list[dict] = []
    for entry in history:
        normalized.append({
            "event_id": str(entry.get("event_id", "")),
            "event_name": str(entry.get("event_name", "")),
            "event_date": str(entry.get("event_date", "")),
            "event_type": str(entry.get("event_type", "")),
            "portfolio_return_pct": _safe_float(entry.get("portfolio_return_pct")),
            "best_performers": list(entry.get("best_performers", [])),
            "worst_performers": list(entry.get("worst_performers", [])),
            "notes": str(entry.get("notes", "")),
            "recorded_at": entry.get("recorded_at"),
        })

    return {
        "as_of_date": today.isoformat(),
        "total_events_tracked": len(history),
        "last_event_date": last_date,
        "events": normalized,
    }


def mei_event_history_summary(repo_root: Optional[Path] = None) -> dict:
    """Return summary stats for the event history section.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "total_events_tracked": int,
      "last_event_date": str | None,
      "avg_portfolio_return_pct": float | None,
      "positive_event_count": int,
      "negative_event_count": int,
      "observations": [str, ...]
    }
    """
    root = _repo(repo_root)
    full = mei_event_history(root)

    events = full.get("events", [])
    returns = [e["portfolio_return_pct"] for e in events if e["portfolio_return_pct"] is not None]
    avg_ret = sum(returns) / len(returns) if returns else None
    positive = sum(1 for r in returns if r >= 0)
    negative = sum(1 for r in returns if r < 0)

    obs: list[str] = []
    if not events:
        obs.append("No historical event outcomes have been recorded yet.")
        obs.append("Phase 1 initializes the history repository. Outcomes will be tracked as events occur.")
    else:
        obs.append(f"{len(events)} historical event(s) tracked.")
        if avg_ret is not None:
            sign = "+" if avg_ret >= 0 else ""
            obs.append(f"Average portfolio return across tracked events: {sign}{avg_ret:.2f}%.")
        if positive > 0 or negative > 0:
            obs.append(f"{positive} positive, {negative} negative event outcomes recorded.")

    return {
        "as_of_date": full.get("as_of_date", ""),
        "total_events_tracked": full.get("total_events_tracked", 0),
        "last_event_date": full.get("last_event_date"),
        "avg_portfolio_return_pct": avg_ret,
        "positive_event_count": positive,
        "negative_event_count": negative,
        "observations": obs,
    }
