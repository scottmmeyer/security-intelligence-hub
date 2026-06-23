"""MEI-002 — Event Outcome Attribution & Portfolio Learning.

Computes historical portfolio and security-level returns around known market
events, builds event effectiveness scores, and provides a learning repository
for how event types have historically impacted the portfolio.

Data sources (read-only):
  - data/mei/historical_events.json   — seeded past macro events
  - data/mei/event_calendar.json      — forward-looking calendar (future events)
  - data/history/prices/symbol=<SYM>/prices.csv — daily close prices
  - Latest PAR holdings.csv           — current portfolio positions

Writes (fully regeneratable):
  - data/mei/event_outcomes.json      — computed attribution results

Governance:
  - Read-only relative to ALL scoring, recommendation, and governance engines.
  - No changes to CW-DAS, ESS, UCF, CRA, PAP, MEI exposures, or any other system.
  - Display-only / learning output.

Public API
----------
  mei_outcomes(repo_root)                → dict
  mei_outcome_by_event(event_id, repo_root) → dict
  mei_event_impact(repo_root)            → dict  (event type effectiveness)
  mei_outcome_summary(repo_root)         → dict  (executive summary)
  refresh_event_outcomes(repo_root)      → dict  (rebuild + persist)
"""

from __future__ import annotations

import csv
import json
import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_OUTCOMES_FILE     = "data/mei/event_outcomes.json"
_HISTORICAL_EVENTS = "data/mei/historical_events.json"
_CALENDAR_EVENTS   = "data/mei/event_calendar.json"

# Attribution windows (calendar days after event)
_WINDOWS = [1, 5, 10]

# Min absolute return to classify as significant move
_SIGNIFICANT_RETURN = 0.01   # 1%

_MEI_002_VERSION = "1.0"

# Event type labels for display
_EVENT_TYPE_LABELS = {
    "MONETARY_POLICY":  "FOMC / Fed Policy",
    "INFLATION":        "Inflation Data (CPI/PPI)",
    "LABOR_MARKET":     "Labor Market (NFP)",
    "TRADE_POLICY":     "Trade / Tariff Policy",
    "CONSUMER_SURVEY":  "Consumer Data",
    "HOUSING":          "Housing Data",
    "GDP":              "GDP Release",
    "EARNINGS":         "Earnings",
    "TREASURY_AUCTION": "Treasury Auction",
    "FED_SPEECH":       "Fed Speech",
    "OPEX":             "Options Expiration",
}

# ── Price data helpers ────────────────────────────────────────────────────────

def _load_price_series(symbol: str, repo_root: Path) -> Dict[str, float]:
    """Return {date_str → close_price} for a symbol."""
    path = repo_root / "data" / "history" / "prices" / f"symbol={symbol}" / "prices.csv"
    if not path.exists():
        return {}
    result = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            d = str(row.get("date") or "").strip()[:10]
            try:
                result[d] = float(row.get("close") or row.get("adjusted_close") or 0)
            except (TypeError, ValueError):
                pass
    return result


def _nearest_price_after(prices: Dict[str, float], target: date, max_gap: int = 5) -> Optional[Tuple[str, float]]:
    """Return (date_str, price) on or just after target, within max_gap days."""
    for i in range(max_gap + 1):
        d = (target + timedelta(days=i)).isoformat()
        if d in prices and prices[d] > 0:
            return d, prices[d]
    return None


def _nearest_price_before(prices: Dict[str, float], target: date, max_gap: int = 5) -> Optional[Tuple[str, float]]:
    """Return (date_str, price) on or just before target, within max_gap days."""
    for i in range(max_gap + 1):
        d = (target - timedelta(days=i)).isoformat()
        if d in prices and prices[d] > 0:
            return d, prices[d]
    return None


def _forward_return(prices: Dict[str, float], event_date: date, days: int) -> Optional[float]:
    """Compute return from close on event_date to close at event_date + days."""
    p0_pair = _nearest_price_before(prices, event_date, max_gap=3)
    pN_pair = _nearest_price_after(prices, event_date + timedelta(days=days), max_gap=5)
    if p0_pair is None or pN_pair is None:
        return None
    p0, pN = p0_pair[1], pN_pair[1]
    if p0 <= 0:
        return None
    return round((pN - p0) / p0, 6)


# ── Portfolio data helpers ────────────────────────────────────────────────────

def _load_latest_holdings(repo_root: Path) -> List[Dict]:
    """Load holdings from the latest PAR analysis run."""
    runs = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not runs.exists():
        return []
    dirs = sorted(
        (d for d in runs.iterdir() if d.is_dir() and (d / "holdings.csv").exists()),
        key=lambda d: d.stat().st_mtime,
    )
    if not dirs:
        return []
    with (dirs[-1] / "holdings.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _active_holdings(holdings: List[Dict]) -> List[Dict]:
    """Filter to equity holdings with a non-zero market value."""
    result = []
    for h in holdings:
        sym = str(h.get("symbol") or "").strip().upper()
        if not sym or sym in ("SPAXX", "PENDING ACTIVITY"):
            continue
        try:
            mv = float(h.get("market_value") or 0)
        except (TypeError, ValueError):
            mv = 0
        if mv > 0:
            result.append({**h, "_symbol": sym, "_mv": mv})
    return result


def _portfolio_mv(holdings: List[Dict]) -> float:
    return sum(h["_mv"] for h in holdings) or 1.0


# ── Event loaders ─────────────────────────────────────────────────────────────

def _load_all_past_events(repo_root: Path) -> List[Dict]:
    """Load historical events (seeded) that fall within available price data."""
    result = []
    today = date.today()
    price_end = date(2026, 5, 26)   # known price data upper bound

    # Seeded historical events
    hist_path = repo_root / _HISTORICAL_EVENTS
    if hist_path.exists():
        try:
            events = json.loads(hist_path.read_text(encoding="utf-8"))
            for e in events:
                try:
                    d = date.fromisoformat(str(e.get("event_date", "")))
                    if d <= min(today, price_end):
                        result.append(e)
                except ValueError:
                    pass
        except (OSError, json.JSONDecodeError):
            pass

    # Calendar events that have passed
    cal_path = repo_root / _CALENDAR_EVENTS
    if cal_path.exists():
        try:
            events = json.loads(cal_path.read_text(encoding="utf-8"))
            for e in events:
                try:
                    d = date.fromisoformat(str(e.get("event_date", "")))
                    if d < today:
                        result.append(e)
                except ValueError:
                    pass
        except (OSError, json.JSONDecodeError):
            pass

    # De-duplicate by event_id (historical seeded wins over duplicates)
    seen = {}
    for e in result:
        eid = str(e.get("event_id") or "")
        if eid not in seen:
            seen[eid] = e
    return sorted(seen.values(), key=lambda x: str(x.get("event_date", "")))


# ── Part A + B + C: Compute outcome for one event ────────────────────────────

def _compute_event_outcome(
    event: Dict,
    holdings: List[Dict],
    price_cache: Dict[str, Dict[str, float]],
    total_mv: float,
) -> Dict:
    """Compute portfolio and security attribution for one past event."""
    event_date = date.fromisoformat(str(event["event_date"]))
    symbol_rets: Dict[str, Dict[str, Optional[float]]] = {}

    # Compute per-security returns for each window
    for h in holdings:
        sym = h["_symbol"]
        prices = price_cache.get(sym, {})
        if not prices:
            continue
        rets = {}
        for w in _WINDOWS:
            r = _forward_return(prices, event_date, w)
            rets[f"return_{w}d"] = round(r * 100, 4) if r is not None else None
        if any(v is not None for v in rets.values()):
            symbol_rets[sym] = {
                **rets,
                "market_value": h["_mv"],
                "weight_pct": round(h["_mv"] / total_mv * 100, 4),
            }

    # Portfolio-level weighted returns
    portfolio_rets: Dict[str, Optional[float]] = {}
    for w in _WINDOWS:
        key = f"return_{w}d"
        weighted = []
        for sym, data in symbol_rets.items():
            r = data.get(key)
            wt = data.get("weight_pct", 0)
            if r is not None and wt > 0:
                weighted.append(r * wt / 100)
        portfolio_rets[key] = round(sum(weighted), 4) if weighted else None

    # Best / worst contributors (5d window as primary)
    primary = "return_5d"
    sorted_syms = sorted(
        [(sym, d.get(primary)) for sym, d in symbol_rets.items() if d.get(primary) is not None],
        key=lambda x: x[1],
    )
    top_winners = [{"symbol": s, "return_pct": r} for s, r in sorted_syms[-5:][::-1]]
    top_losers  = [{"symbol": s, "return_pct": r} for s, r in sorted_syms[:5]]

    # Surprise factor — how abnormal was the 1d move?
    r1 = portfolio_rets.get("return_1d")
    surprise_factor = None
    if r1 is not None:
        surprise_factor = round(abs(r1) / 1.0, 2)  # normalised: >1.0 = above typical ±1%

    # Coverage
    covered = len(symbol_rets)
    total_holdings = len(holdings)
    coverage_pct = round(covered / total_holdings * 100, 1) if total_holdings > 0 else 0.0

    return {
        "event_id":        event.get("event_id"),
        "event_name":      event.get("event_name"),
        "event_type":      event.get("event_type"),
        "event_date":      event.get("event_date"),
        "impact_level":    event.get("impact_level"),
        "sensitivity_tags": event.get("sensitivity_tags", []),
        "portfolio_return_1d":  portfolio_rets.get("return_1d"),
        "portfolio_return_5d":  portfolio_rets.get("return_5d"),
        "portfolio_return_10d": portfolio_rets.get("return_10d"),
        "surprise_factor": surprise_factor,
        "top_winners":     top_winners,
        "top_losers":      top_losers,
        "securities_attributed": covered,
        "total_holdings":  total_holdings,
        "coverage_pct":    coverage_pct,
        "security_returns": symbol_rets,
    }


# ── Part D: Event effectiveness aggregation ───────────────────────────────────

def _compute_event_type_effectiveness(outcomes: List[Dict]) -> List[Dict]:
    """Aggregate outcomes by event_type to show historical effectiveness."""
    by_type: Dict[str, List[Dict]] = defaultdict(list)
    for o in outcomes:
        if o.get("portfolio_return_5d") is not None:
            by_type[o.get("event_type", "UNKNOWN")].append(o)

    results = []
    for etype, group in sorted(by_type.items(), key=lambda x: -len(x[1])):
        r5s = [o["portfolio_return_5d"] for o in group if o.get("portfolio_return_5d") is not None]
        r1s = [o["portfolio_return_1d"] for o in group if o.get("portfolio_return_1d") is not None]
        surprises = [o["surprise_factor"] for o in group if o.get("surprise_factor") is not None]

        avg_r5 = round(mean(r5s), 4) if r5s else None
        avg_r1 = round(mean(r1s), 4) if r1s else None
        volatility = round(pstdev(r5s), 4) if len(r5s) >= 2 else None
        avg_surprise = round(mean(surprises), 2) if surprises else None

        # Predictability: fraction of events where 1d & 5d moved in same direction
        consistent = sum(
            1 for o in group
            if o.get("portfolio_return_1d") is not None
            and o.get("portfolio_return_5d") is not None
            and (o["portfolio_return_1d"] >= 0) == (o["portfolio_return_5d"] >= 0)
        )
        consistency_pct = round(consistent / len(group) * 100, 1) if group else None

        # Importance score: avg(|5d return|) × frequency
        importance = round(mean(abs(r) for r in r5s) * len(r5s), 2) if r5s else 0.0

        results.append({
            "event_type":       etype,
            "event_type_label": _EVENT_TYPE_LABELS.get(etype, etype.replace("_", " ")),
            "event_count":      len(group),
            "avg_return_1d_pct":   avg_r1,
            "avg_return_5d_pct":   avg_r5,
            "volatility_5d_pct":   volatility,
            "avg_surprise_factor": avg_surprise,
            "consistency_pct":     consistency_pct,
            "importance_score":    importance,
            "example_events":  [o.get("event_id", "") for o in sorted(group, key=lambda x: str(x.get("event_date","")))[-3:]],
        })

    return sorted(results, key=lambda x: -x["importance_score"])


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _outcomes_path(repo_root: Path) -> Path:
    return repo_root / _OUTCOMES_FILE


def _load_cached_outcomes(repo_root: Path) -> Optional[Dict]:
    path = _outcomes_path(repo_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_outcomes(repo_root: Path, payload: Dict) -> None:
    path = _outcomes_path(repo_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


# ── Master computation ────────────────────────────────────────────────────────

def _build_outcomes(repo_root: Path) -> Dict:
    past_events = _load_all_past_events(repo_root)
    holdings    = _active_holdings(_load_latest_holdings(repo_root))
    total_mv    = _portfolio_mv(holdings)

    # Pre-load all price series we'll need
    syms_needed = {h["_symbol"] for h in holdings}
    price_cache: Dict[str, Dict[str, float]] = {}
    for sym in syms_needed:
        ps = _load_price_series(sym, repo_root)
        if ps:
            price_cache[sym] = ps

    outcomes = []
    for event in past_events:
        try:
            o = _compute_event_outcome(event, holdings, price_cache, total_mv)
            outcomes.append(o)
        except Exception as exc:
            log.warning("MEI-002: Failed to compute outcome for %s: %s", event.get("event_id"), exc)

    effectiveness = _compute_event_type_effectiveness(outcomes)

    # Summary stats
    attributed = [o for o in outcomes if o.get("portfolio_return_5d") is not None]
    r5s = [o["portfolio_return_5d"] for o in attributed]

    # Most impactful events (by abs 5d portfolio return)
    most_impactful = sorted(
        attributed, key=lambda o: abs(o.get("portfolio_return_5d") or 0), reverse=True
    )[:5]

    payload = {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "version":        _MEI_002_VERSION,
        "event_count":    len(outcomes),
        "attributed_count": len(attributed),
        "avg_portfolio_return_5d": round(mean(r5s), 4) if r5s else None,
        "outcomes":       outcomes,
        "effectiveness":  effectiveness,
        "most_impactful": [
            {k: v for k, v in o.items() if k != "security_returns"}
            for o in most_impactful
        ],
        "governance_note": (
            "MEI-002 is informational only. "
            "No recommendation, scoring, CW-DAS, ESS, UCF, CRA, or governance logic is modified. "
            "Portfolio returns are approximated from holdings × price data and may differ from "
            "actual account performance. Operator judgment required before acting on any finding."
        ),
    }
    return payload


# ── Public API ────────────────────────────────────────────────────────────────

def _get_outcomes(repo_root: Path, force: bool = False) -> Dict:
    """Return cached or freshly computed outcomes."""
    if not force:
        cached = _load_cached_outcomes(repo_root)
        if cached:
            return cached
    payload = _build_outcomes(repo_root)
    _save_outcomes(repo_root, payload)
    return payload


def mei_outcomes(repo_root: Path | str = ".") -> Dict:
    """Part A/B/C: Full event outcome attribution results.

    Returns:
        { generated_at, event_count, attributed_count,
          outcomes: [per-event attribution],
          effectiveness: [per-event-type aggregated stats],
          most_impactful: [top 5 by abs return] }
    """
    root = Path(repo_root)
    data = _get_outcomes(root)
    # Strip security_returns from outcomes list (large; use per-event endpoint)
    return {
        **data,
        "outcomes": [
            {k: v for k, v in o.items() if k != "security_returns"}
            for o in data.get("outcomes", [])
        ],
    }


def mei_outcome_by_event(event_id: str, repo_root: Path | str = ".") -> Dict:
    """Return full outcome (including security_returns) for a specific event."""
    root = Path(repo_root)
    data = _get_outcomes(root)
    event_id = event_id.strip().upper()
    for o in data.get("outcomes", []):
        if str(o.get("event_id") or "").upper() == event_id:
            return o
    return {"error": f"Event not found: {event_id}", "event_id": event_id}


def mei_event_impact(repo_root: Path | str = ".") -> Dict:
    """Part D: Event effectiveness / importance ranking by type.

    Returns:
        { generated_at, effectiveness: [per-type stats sorted by importance] }
    """
    root = Path(repo_root)
    data = _get_outcomes(root)
    return {
        "generated_at":  data.get("generated_at"),
        "effectiveness": data.get("effectiveness", []),
    }


def mei_outcome_summary(repo_root: Path | str = ".") -> Dict:
    """Executive summary for the MEI-002 dashboard section.

    Returns key metrics and the most impactful events.
    """
    root = Path(repo_root)
    data = _get_outcomes(root)
    return {
        "generated_at":   data.get("generated_at"),
        "event_count":    data.get("event_count"),
        "attributed_count": data.get("attributed_count"),
        "avg_portfolio_return_5d": data.get("avg_portfolio_return_5d"),
        "most_impactful": data.get("most_impactful", []),
        "top_event_types": (data.get("effectiveness") or [])[:3],
        "governance_note": data.get("governance_note"),
    }


def refresh_event_outcomes(repo_root: Path | str = ".") -> Dict:
    """Force rebuild of event_outcomes.json. Returns meta dict."""
    root = Path(repo_root)
    payload = _build_outcomes(root)
    _save_outcomes(root, payload)
    return {
        "ok": True,
        "event_count":     payload.get("event_count"),
        "attributed_count": payload.get("attributed_count"),
        "generated_at":    payload.get("generated_at"),
        "version":         payload.get("version"),
    }
