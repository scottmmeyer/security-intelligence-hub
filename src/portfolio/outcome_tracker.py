"""Dislocation Outcome Tracking — persistence and computation.

ISSUE-12B — Detection Persistence:
  Appends dislocation detection snapshots to data/derived/dislocation_detections.csv
  at run time. Called from runner.py after dislocation_by_symbol is built.

ISSUE-12C — Outcome Computation Engine:
  Reads dislocation_detections.csv, fetches historical prices via yfinance,
  computes symbol and SPY returns, writes dislocation_outcomes.csv and
  dislocation_outcome_summary.json.

Governance (ISSUE-12 Final Recommendation):
  - Research only — no scoring, ranking, CW-DAS, or CRA influence
  - Outcomes are informational context for future calibration decisions
  - No threshold changes before December 2026 (minimum)
"""
from __future__ import annotations

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DERIVED_DIR = _REPO_ROOT / "data" / "derived"

DETECTIONS_CSV = _DERIVED_DIR / "dislocation_detections.csv"
OUTCOMES_CSV   = _DERIVED_DIR / "dislocation_outcomes.csv"
SUMMARY_JSON   = _DERIVED_DIR / "dislocation_outcome_summary.json"

DETECTIONS_HEADERS = [
    "detection_date",
    "run_id",
    "symbol",
    "tier",
    "dislocation_class",
    "active_classes",       # pipe-delimited e.g. "A1_FUNDAMENTAL_BEAT_DIVERGENCE|D1_REPLAY_SIGNAL_LAG"
    "ess_at_detection",
    "danelfin_at_detection",
    "replay_percentile_at_detection",
    "replay_supported_at_detection",
    "composite_score_at_detection",
    "cw_das_score_at_detection",
    "thesis_integrity_at_detection",
    "fundamental_modifier_at_detection",
    "dislocation_version",
    "price_at_detection",
]

OUTCOMES_HEADERS = [
    "detection_date",
    "symbol",
    "tier",
    "active_classes",
    "holding_period_days",
    "price_at_detection",
    "price_at_outcome",
    "spy_price_at_detection",
    "spy_price_at_outcome",
    "symbol_return_pct",
    "spy_return_pct",
    "excess_return_pct",
    "outcome_status",       # WIN | LOSS | FLAT
]

# Outcome status thresholds
_FLAT_BAND = 0.25   # excess return within ±0.25% is FLAT


# ─── ISSUE-12B: Detection Persistence ────────────────────────────────────────

def persist_dislocation_detections(
    detection_date: str,
    run_id: str,
    dislocation_payload: dict[str, dict],
    overlays: list,
    dq_payload: Optional[dict] = None,
    yahoo_prices: Optional[dict[str, float]] = None,
) -> int:
    """Append new dislocation detections to the detections CSV.

    Only records symbols with tier != NONE.
    De-duplicates: skips (detection_date, symbol, tier) combinations already
    in the file to avoid re-logging persistent detections on consecutive runs.

    Args:
        detection_date:       ISO date string (snapshot_date from runner)
        run_id:               PAR run ID for lineage
        dislocation_payload:  dislocation_by_symbol dict from runner
        overlays:             list of SecurityIntelligenceOverlay dicts/instances
        dq_payload:           deployment_queue payload dict (optional, for CW-DAS)
        yahoo_prices:         {symbol: current_price} from Yahoo supplemental (optional)

    Returns:
        Count of new rows appended.
    """
    _DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    # Build overlay lookup
    ov_by_sym: dict[str, dict] = {}
    for ov in overlays:
        sym = str(_f(ov, "symbol") or "").strip().upper()
        if sym:
            ov_by_sym[sym] = ov if isinstance(ov, dict) else _to_dict(ov)

    # Build DQ score lookup
    dq_by_sym: dict[str, dict] = {}
    if dq_payload:
        for entry in dq_payload.get("queue", []):
            sym = str(entry.get("symbol") or "").strip().upper()
            if sym:
                dq_by_sym[sym] = entry

    # Load existing keys to de-duplicate
    existing_keys: set[tuple[str, str, str]] = set()
    if DETECTIONS_CSV.exists():
        with open(DETECTIONS_CSV, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing_keys.add((row.get("detection_date",""),
                                   row.get("symbol",""),
                                   row.get("tier","")))

    new_rows: list[dict] = []
    for sym, det in dislocation_payload.items():
        tier = det.get("tier", "NONE")
        if tier == "NONE":
            continue

        key = (detection_date, sym, tier)
        if key in existing_keys:
            continue

        ov = ov_by_sym.get(sym, {})
        dq = dq_by_sym.get(sym, {})
        bd = dq.get("score_breakdown", {}) if dq else {}

        active_classes_list = det.get("active_classes", [])
        if not active_classes_list:
            active_classes_list = [det.get("dislocation_class", "")]
        active_classes_str = "|".join(c for c in active_classes_list if c and c != "NONE")

        price = None
        if yahoo_prices:
            price = yahoo_prices.get(sym)
        if price is None:
            # Try overlay composite as a fallback (no price)
            pass

        new_rows.append({
            "detection_date":                   detection_date,
            "run_id":                           run_id,
            "symbol":                           sym,
            "tier":                             tier,
            "dislocation_class":                det.get("dislocation_class", ""),
            "active_classes":                   active_classes_str,
            "ess_at_detection":                 str(ov.get("ess_score_text") or ""),
            "danelfin_at_detection":            str(ov.get("danelfin_score") or ""),
            "replay_percentile_at_detection":   str(ov.get("replay_percentile") or ""),
            "replay_supported_at_detection":    str(ov.get("replay_supported") or ""),
            "composite_score_at_detection":     str(ov.get("composite_score") or ""),
            "cw_das_score_at_detection":        str(dq.get("deployment_score") or ""),
            "thesis_integrity_at_detection":    str(bd.get("thesis_integrity") or ""),
            "fundamental_modifier_at_detection": str(bd.get("fundamental_modifier") or ""),
            "dislocation_version":              str(det.get("version", "")),
            "price_at_detection":               str(price) if price is not None else "",
        })
        existing_keys.add(key)

    if not new_rows:
        return 0

    write_header = not DETECTIONS_CSV.exists() or DETECTIONS_CSV.stat().st_size == 0
    with open(DETECTIONS_CSV, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DETECTIONS_HEADERS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    return len(new_rows)


def _f(obj, key: str) -> object:
    """Field accessor for dataclass or dict."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _to_dict(obj) -> dict:
    """Convert dataclass to dict (shallow)."""
    try:
        import dataclasses
        return dataclasses.asdict(obj) if dataclasses.is_dataclass(obj) else {}
    except Exception:
        return {}


# ─── ISSUE-12C: Outcome Computation Engine ────────────────────────────────────

def _to_float(v: object) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(str(v).strip())
        return None if (f != f) else f
    except (ValueError, TypeError):
        return None


def _outcome_status(excess_return: float) -> str:
    if excess_return > _FLAT_BAND:
        return "WIN"
    if excess_return < -_FLAT_BAND:
        return "LOSS"
    return "FLAT"


def fetch_price_history(
    symbol: str,
    start_date: str,
    end_date: str,
) -> dict[str, float]:
    """Fetch adjusted close prices for symbol between start and end dates.

    Returns {date_str: adjusted_close} or empty dict on failure.
    Uses yfinance adjusted close ('Close' from auto_adjust=True).
    """
    try:
        import yfinance as yf  # type: ignore
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date, auto_adjust=True)
        if hist is None or hist.empty:
            return {}
        result = {}
        for idx, row in hist.iterrows():
            d = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
            close = float(row["Close"])
            if not math.isnan(close):
                result[d] = close
        return result
    except Exception:
        return {}


def _nearest_price(prices: dict[str, float], target_date: str) -> Optional[float]:
    """Find the price for target_date or the nearest prior trading day (up to 5 days back)."""
    if not prices:
        return None
    for delta in range(6):
        d = str(date.fromisoformat(target_date) - timedelta(days=delta))
        if d in prices:
            return prices[d]
    return None


def compute_outcomes(
    holding_period_days: int = 90,
    detections_path: Path = DETECTIONS_CSV,
    outcomes_path: Path = OUTCOMES_CSV,
    today: Optional[str] = None,
    _fetch_fn=None,   # injectable for tests
) -> list[dict]:
    """Compute realized outcomes for mature detections.

    A detection is mature when detection_date + holding_period_days <= today.

    Args:
        holding_period_days: 30, 90, or 180
        detections_path:     path to dislocation_detections.csv
        outcomes_path:       path to write dislocation_outcomes.csv
        today:               ISO date override (defaults to date.today())
        _fetch_fn:           optional price-fetch callable for testing

    Returns:
        List of outcome row dicts (also written to outcomes_path).
    """
    if not detections_path.exists():
        return []

    today_date = date.fromisoformat(today) if today else date.today()
    cutoff = today_date - timedelta(days=holding_period_days)
    fetch = _fetch_fn or fetch_price_history

    # Load detections
    with open(detections_path, newline="", encoding="utf-8") as fh:
        detections = list(csv.DictReader(fh))

    # Filter to mature detections
    mature = [
        row for row in detections
        if row.get("detection_date")
        and date.fromisoformat(row["detection_date"]) <= cutoff
        and row.get("tier", "NONE") != "NONE"
        and row.get("price_at_detection", "").strip()  # must have entry price
    ]

    if not mature:
        return []

    # Batch fetch: collect unique symbols + SPY + date ranges
    symbols_needed: set[str] = {"SPY"}
    date_ranges: dict[str, tuple[str, str]] = {}  # symbol → (earliest_start, latest_end)

    for row in mature:
        sym = row["symbol"]
        det_date = row["detection_date"]
        outcome_date = str(date.fromisoformat(det_date) + timedelta(days=holding_period_days))
        symbols_needed.add(sym)
        if sym not in date_ranges:
            date_ranges[sym] = (det_date, outcome_date)
        else:
            start, end = date_ranges[sym]
            date_ranges[sym] = (min(start, det_date), max(end, outcome_date))

    # Also widen SPY range to cover all detection dates
    all_dates = [row["detection_date"] for row in mature]
    all_outcome_dates = [
        str(date.fromisoformat(d) + timedelta(days=holding_period_days))
        for d in all_dates
    ]
    spy_start = min(all_dates)
    spy_end = max(all_outcome_dates)
    # Add buffer day on each side
    spy_start_buf = str(date.fromisoformat(spy_start) - timedelta(days=5))
    spy_end_buf   = str(date.fromisoformat(spy_end)   + timedelta(days=5))

    # Fetch SPY history once
    spy_prices = fetch("SPY", spy_start_buf, spy_end_buf)

    # Fetch per-symbol history
    sym_prices: dict[str, dict[str, float]] = {"SPY": spy_prices}
    for sym in symbols_needed - {"SPY"}:
        start, end = date_ranges.get(sym, (spy_start_buf, spy_end_buf))
        buf_start = str(date.fromisoformat(start) - timedelta(days=5))
        buf_end   = str(date.fromisoformat(end)   + timedelta(days=5))
        sym_prices[sym] = fetch(sym, buf_start, buf_end)

    # Compute outcomes
    outcome_rows: list[dict] = []
    for row in mature:
        sym        = row["symbol"]
        det_date   = row["detection_date"]
        outcome_dt = str(date.fromisoformat(det_date) + timedelta(days=holding_period_days))

        # Prices
        entry_price_raw = _to_float(row.get("price_at_detection"))
        sym_prices_map  = sym_prices.get(sym, {})
        spy_map         = sym_prices.get("SPY", {})

        sym_entry = entry_price_raw  # use stored entry price
        sym_exit  = _nearest_price(sym_prices_map, outcome_dt)
        spy_entry = _nearest_price(spy_map, det_date)
        spy_exit  = _nearest_price(spy_map, outcome_dt)

        if sym_entry is None or sym_exit is None or spy_entry is None or spy_exit is None:
            # Insufficient price data — skip this detection
            continue

        if sym_entry <= 0 or spy_entry <= 0:
            continue

        sym_ret = (sym_exit - sym_entry) / sym_entry * 100.0
        spy_ret = (spy_exit - spy_entry) / spy_entry * 100.0
        excess  = sym_ret - spy_ret

        outcome_rows.append({
            "detection_date":        det_date,
            "symbol":                sym,
            "tier":                  row.get("tier", ""),
            "active_classes":        row.get("active_classes", ""),
            "holding_period_days":   str(holding_period_days),
            "price_at_detection":    f"{sym_entry:.4f}",
            "price_at_outcome":      f"{sym_exit:.4f}",
            "spy_price_at_detection": f"{spy_entry:.4f}",
            "spy_price_at_outcome":   f"{spy_exit:.4f}",
            "symbol_return_pct":     f"{sym_ret:.4f}",
            "spy_return_pct":        f"{spy_ret:.4f}",
            "excess_return_pct":     f"{excess:.4f}",
            "outcome_status":        _outcome_status(excess),
        })

    # Write outcomes CSV
    if outcome_rows:
        _DERIVED_DIR.mkdir(parents=True, exist_ok=True)
        write_header = not outcomes_path.exists() or outcomes_path.stat().st_size == 0
        with open(outcomes_path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=OUTCOMES_HEADERS, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(outcome_rows)

    return outcome_rows


# ─── Aggregation / Summary ────────────────────────────────────────────────────

def _safe_median(values: list[float]) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _safe_mean(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def build_outcome_summary(
    outcomes_path: Path = OUTCOMES_CSV,
    holding_period_days: int = 90,
    summary_path: Path = SUMMARY_JSON,
) -> dict:
    """Aggregate outcome rows into tier/class summary statistics.

    Args:
        outcomes_path:       path to dislocation_outcomes.csv
        holding_period_days: filter to this holding period
        summary_path:        path to write summary JSON

    Returns:
        Summary dict (also written to summary_path as JSON).
    """
    if not outcomes_path.exists():
        return {}

    with open(outcomes_path, newline="", encoding="utf-8") as fh:
        all_rows = list(csv.DictReader(fh))

    rows = [r for r in all_rows
            if str(r.get("holding_period_days", "")) == str(holding_period_days)]

    if not rows:
        return {}

    def _group_stats(group_rows: list[dict]) -> dict:
        excesses = [_to_float(r["excess_return_pct"]) for r in group_rows
                    if _to_float(r.get("excess_return_pct")) is not None]
        wins = sum(1 for r in group_rows if r.get("outcome_status") == "WIN")
        n = len(group_rows)
        return {
            "detection_count": n,
            "hit_rate": round(wins / n * 100, 2) if n else None,
            "median_excess_return": round(_safe_median(excesses), 4) if excesses else None,
            "mean_excess_return":   round(_safe_mean(excesses), 4) if excesses else None,
        }

    # By tier
    tier_groups: dict[str, list[dict]] = {}
    for r in rows:
        tier_groups.setdefault(r.get("tier", "UNKNOWN"), []).append(r)

    # By class — expand multi-class rows into each contributing class
    class_groups: dict[str, list[dict]] = {}
    for r in rows:
        classes_str = r.get("active_classes", "") or r.get("tier", "")
        classes = [c.strip() for c in classes_str.split("|") if c.strip()]
        if len(classes) > 1:
            class_groups.setdefault("MULTI_CLASS", []).append(r)
        for cls in classes:
            class_groups.setdefault(cls, []).append(r)
        if not classes:
            class_groups.setdefault("UNKNOWN", []).append(r)

    summary = {
        "holding_period_days": holding_period_days,
        "total_outcomes": len(rows),
        "computed_at": str(date.today()),
        "by_tier": {tier: _group_stats(grp) for tier, grp in tier_groups.items()},
        "by_class": {cls: _group_stats(grp) for cls, grp in class_groups.items()},
    }

    _DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    return summary
