"""MEI-002 — Portfolio Event Exposure Analysis.

For every upcoming market event, identifies which holdings are most
exposed based on the event's sensitivity_tags and each holding's
per-tag sensitivity level.

Reads from:
  - Latest PAR holdings.csv (active portfolio positions)
  - src/mei/events.py (upcoming event calendar)
  - src/mei/security_profiles.py (per-symbol sensitivity profiles)

This module is STRICTLY READ-ONLY.  No recommendation, scoring, or
governance artifact is ever modified.

Exposure bucketing
------------------
  HIGH exposure    — holding has HIGH sensitivity to any event tag
  MODERATE exposure — holding has MODERATE (and no HIGH) sensitivity
  LOW exposure     — holding has LOW or NONE sensitivity to all event tags

Public API
----------
  mei_exposures(repo_root)          → dict  (full per-event exposure payload)
  mei_exposures_summary(repo_root)  → dict  (summary cards)
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Optional

from src.mei.events import mei_events, _days_away
from src.mei.security_profiles import mei_security_profiles_bulk

_HOLDING_ASSET_CLASSES = {"EQUITIES", "FIXED_INCOME", "DIGITAL"}


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
            meta = json.loads((d / "run_metadata.json").read_text(encoding="utf-8"))
            return str(meta.get("created_at_utc", ""))
        except Exception:
            return d.name

    return max(dirs, key=_ts)


def _load_active_holdings(repo_root: Path) -> list[dict]:
    """Return active holdings from the latest PAR run (EQUITIES + FIXED_INCOME + DIGITAL)."""
    run = _latest_par_run(repo_root)
    if run is None:
        return []
    path = run / "holdings.csv"
    if not path.exists():
        return []
    holdings: list[dict] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                asset_class = str(row.get("asset_class", "")).strip().upper()
                if asset_class in _HOLDING_ASSET_CLASSES:
                    sym = str(row.get("symbol", "")).strip().upper()
                    if sym:
                        holdings.append({
                            "symbol": sym,
                            "asset_class": asset_class,
                            "industry": str(row.get("industry", "")).strip().upper(),
                            "market_cap_bucket": str(row.get("market_cap_bucket", "")).strip().upper(),
                            "percent_of_portfolio": _safe_float(row.get("percent_of_portfolio")),
                        })
    except Exception:
        pass
    return holdings


def _safe_float(v: object, default: float = 0.0) -> float:
    try:
        return float(str(v or "").strip() or default)
    except (TypeError, ValueError):
        return default


# ─── Exposure bucketing ───────────────────────────────────────────────────────


def _bucket(sensitivities: dict[str, str], sensitivity_tags: list[str]) -> str:
    """Return HIGH / MODERATE / LOW based on highest sensitivity level across tags."""
    levels = [sensitivities.get(tag, "NONE") for tag in sensitivity_tags]
    if "HIGH" in levels:
        return "HIGH"
    if "MODERATE" in levels:
        return "MODERATE"
    return "LOW"


# ─── Public API ───────────────────────────────────────────────────────────────


def mei_exposures(repo_root: Optional[Path] = None) -> dict:
    """Return per-event portfolio exposure analysis.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "analysis_run_id": str | None,
      "total_holdings_analyzed": int,
      "total_events": int,
      "event_exposures": [
        {
          "event_id": str,
          "event_name": str,
          "event_date": str,
          "impact_level": str,
          "days_away": int,
          "sensitivity_tags": [str],
          "high_exposure": [{"symbol": str, "industry": str, "pct": float}],
          "moderate_exposure": [...],
          "low_exposure": [...],
          "high_count": int,
          "moderate_count": int,
          "low_count": int,
        }, ...
      ]
    }
    """
    root = _repo(repo_root)
    today = date.today()

    # Load events (next 14 days)
    cal = mei_events(root)
    events = cal.get("events", [])

    # Load holdings
    holdings = _load_active_holdings(root)
    symbols = [h["symbol"] for h in holdings]

    # Determine analysis_run_id
    run = _latest_par_run(root)
    analysis_run_id: Optional[str] = None
    if run is not None:
        try:
            meta = json.loads((run / "run_metadata.json").read_text(encoding="utf-8"))
            analysis_run_id = meta.get("run_id")
        except Exception:
            analysis_run_id = run.name

    # Build profiles once for all holdings
    profiles_payload = mei_security_profiles_bulk(symbols, root)
    profiles = profiles_payload.get("profiles", {})

    # Build index of holding metadata
    holding_meta: dict[str, dict] = {h["symbol"]: h for h in holdings}

    # For each event, bucket holdings by exposure
    event_exposures: list[dict] = []
    for ev in events:
        tags: list[str] = ev.get("sensitivity_tags", [])
        if not tags:
            continue

        high_list: list[dict] = []
        moderate_list: list[dict] = []
        low_list: list[dict] = []

        for sym in symbols:
            profile = profiles.get(sym, {})
            sens = profile.get("sensitivities", {})
            bucket = _bucket(sens, tags)
            meta = holding_meta.get(sym, {})
            record = {
                "symbol": sym,
                "industry": meta.get("industry", ""),
                "market_cap_bucket": meta.get("market_cap_bucket", ""),
                "pct_of_portfolio": meta.get("percent_of_portfolio", 0.0),
                "top_sensitivities": profile.get("top_sensitivities", []),
            }
            if bucket == "HIGH":
                high_list.append(record)
            elif bucket == "MODERATE":
                moderate_list.append(record)
            else:
                low_list.append(record)

        # Sort by portfolio weight descending within each bucket
        for lst in (high_list, moderate_list, low_list):
            lst.sort(key=lambda x: x["pct_of_portfolio"], reverse=True)

        event_exposures.append({
            "event_id": ev.get("event_id", ""),
            "event_name": ev.get("event_name", ""),
            "event_date": ev.get("event_date", ""),
            "impact_level": ev.get("impact_level", ""),
            "days_away": _days_away(ev, today),
            "consensus_expectation": ev.get("consensus_expectation", ""),
            "sensitivity_tags": tags,
            "high_exposure": high_list,
            "moderate_exposure": moderate_list,
            "low_exposure": low_list,
            "high_count": len(high_list),
            "moderate_count": len(moderate_list),
            "low_count": len(low_list),
        })

    return {
        "as_of_date": today.isoformat(),
        "analysis_run_id": analysis_run_id,
        "total_holdings_analyzed": len(symbols),
        "total_events": len(event_exposures),
        "event_exposures": event_exposures,
    }


def mei_exposures_summary(repo_root: Optional[Path] = None) -> dict:
    """Return summary cards: which events have the broadest portfolio exposure.

    Response shape
    --------------
    {
      "as_of_date": "YYYY-MM-DD",
      "total_events_analyzed": int,
      "max_high_exposure_event": {event_id, event_name, high_count} | None,
      "high_impact_high_exposure": int,   # HIGH-impact events with ≥5 HIGH-exposure holdings
      "most_exposed_symbols": [str, ...], # symbols appearing in HIGH bucket most often
      "event_summary_table": [
        {event_id, event_name, event_date, impact_level, days_away, high_count, moderate_count, low_count}
      ]
    }
    """
    root = _repo(repo_root)
    today = date.today()
    full = mei_exposures(root)

    exposures = full.get("event_exposures", [])
    if not exposures:
        return {
            "as_of_date": today.isoformat(),
            "total_events_analyzed": 0,
            "max_high_exposure_event": None,
            "high_impact_high_exposure": 0,
            "most_exposed_symbols": [],
            "event_summary_table": [],
        }

    # Count how many times each symbol appears in HIGH bucket
    symbol_high_count: dict[str, int] = {}
    for ev in exposures:
        for h in ev.get("high_exposure", []):
            sym = h["symbol"]
            symbol_high_count[sym] = symbol_high_count.get(sym, 0) + 1

    most_exposed = sorted(symbol_high_count, key=lambda s: symbol_high_count[s], reverse=True)[:10]

    max_ev = max(exposures, key=lambda e: e["high_count"], default=None)
    hi_hi_count = sum(
        1 for e in exposures
        if e.get("impact_level") == "HIGH" and e.get("high_count", 0) >= 5
    )

    summary_table = [
        {
            "event_id": e["event_id"],
            "event_name": e["event_name"],
            "event_date": e["event_date"],
            "impact_level": e["impact_level"],
            "days_away": e["days_away"],
            "high_count": e["high_count"],
            "moderate_count": e["moderate_count"],
            "low_count": e["low_count"],
        }
        for e in sorted(exposures, key=lambda e: (e.get("event_date", ""), _IMPACT_ORDER.get(str(e.get("impact_level")), 9)))
    ]

    return {
        "as_of_date": today.isoformat(),
        "total_events_analyzed": len(exposures),
        "max_high_exposure_event": {
            "event_id": max_ev["event_id"],
            "event_name": max_ev["event_name"],
            "event_date": max_ev["event_date"],
            "high_count": max_ev["high_count"],
        } if max_ev else None,
        "high_impact_high_exposure": hi_hi_count,
        "most_exposed_symbols": most_exposed,
        "event_summary_table": summary_table,
    }


_IMPACT_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
