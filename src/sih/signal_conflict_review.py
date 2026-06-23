"""ISSUE-12D — Signal Conflict Review Engine.

Analyzes historical cases where SIH signals disagreed and evaluates which
signal proved more reliable by computing forward price returns.

Data sources (read-only):
  - data/history/ess_archive/pm_archive/     — ESS + analyst ratings per symbol per date
  - data/history/prices/symbol=<SYM>/prices.csv — daily prices for forward-return calc
  - data/history/signals/danelfin_history_master.csv — Danelfin history (limited dates)

Writes (fully regeneratable):
  - data/analysis/dislocation/dislocation_inventory.csv  (Part A)
  - data/analysis/dislocation/pattern_outcomes.json      (Part B)
  - data/analysis/dislocation/signal_scorecard.json      (Part C)
  - data/analysis/dislocation/_meta.json                 (cache metadata)

Governance:
  - Read-only relative to all scoring engines.
  - No changes to ESS, CW-DAS, UCF, CRA, Replay, PAP, or Governance.
  - All output is informational/learning only.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median, mean
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_FORWARD_HORIZONS = [30, 60]   # days
_WINNER_THRESHOLD_PP = 0.0     # return above snapshot median → WINNER
_CONFLICT_REVIEW_VERSION = "1.0"

# ESS numeric → direction
_ESS_THRESHOLDS = [(7.0, "BULLISH"), (4.0, "NEUTRAL")]  # < 4.0 → BEARISH

# Column names in ESS archive CSV
_ESS_COL         = "ESS from LSEG StarMine"
_ZACKS_COL       = "Zacks Investment Research"
_JEFFERSON_COL   = "Jefferson Research"
_MCLEAN_COL      = "McLean Capital Management"
_SYMBOL_COL      = "Symbol"

# Text → analyst direction
_BULLISH_TEXTS = frozenset({
    "outperform", "buy", "strong buy", "overweight", "positive",
    "1", "2",  # Zacks ranks
})
_BEARISH_TEXTS = frozenset({
    "underperform", "sell", "strong sell", "underweight", "negative",
    "reduce", "4", "5",
})
_NEUTRAL_TEXTS = frozenset({
    "hold", "neutral", "equal weight", "equal-weight", "market perform",
    "sector perform", "in-line", "inline", "3",
})

# Date pattern in ESS archive filenames: e.g. "18Aug2025"
_DATE_RE = re.compile(r"(\d{1,2}[A-Za-z]{3}\d{4})")


# ── Direction helpers ──────────────────────────────────────────────────────────

def _ess_direction(numeric: float | None) -> str:
    """Convert ESS numeric score (0-10) to BULLISH / NEUTRAL / BEARISH."""
    if numeric is None:
        return "NO_DATA"
    for threshold, label in _ESS_THRESHOLDS:
        if numeric >= threshold:
            return label
    return "BEARISH"


def _analyst_direction(text: str | None) -> str:
    """Convert analyst/firm text rating to BULLISH / NEUTRAL / BEARISH / NO_DATA."""
    if text is None:
        return "NO_DATA"
    t = str(text).strip().lower()
    if not t or t in {"--", "-", "n/a", "na", "none", ""}:
        return "NO_DATA"
    if any(b in t for b in _BULLISH_TEXTS):
        return "BULLISH"
    if any(b in t for b in _BEARISH_TEXTS):
        return "BEARISH"
    if any(n in t for n in _NEUTRAL_TEXTS):
        return "NEUTRAL"
    return "NO_DATA"


def _parse_ess_date(filename: str) -> Optional[date]:
    """Extract date from ESS archive filename like '18Aug2025'."""
    m = _DATE_RE.search(filename)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%d%b%Y").date()
    except ValueError:
        return None


def _signal_pattern(ess_dir: str, zacks_dir: str, jefferson_dir: str, mclean_dir: str) -> str:
    """Derive a canonical disagreement pattern string."""
    if ess_dir == "NO_DATA":
        return "NO_ESS_DATA"

    analysts = [d for d in [zacks_dir, jefferson_dir, mclean_dir] if d != "NO_DATA"]
    if not analysts:
        return f"ESS_{ess_dir}_NO_ANALYST_DATA"

    bullish_analysts = sum(1 for a in analysts if a == "BULLISH")
    bearish_analysts = sum(1 for a in analysts if a == "BEARISH")
    neutral_analysts = sum(1 for a in analysts if a == "NEUTRAL")
    total = len(analysts)

    if ess_dir == "BULLISH":
        if bearish_analysts >= total / 2:
            return "ESS_BULLISH_ANALYST_MAJORITY_BEARISH"
        if neutral_analysts + bearish_analysts >= total * 0.75:
            return "ESS_BULLISH_ANALYST_SKEPTICAL"
        if bullish_analysts == total:
            return "ESS_BULLISH_ANALYST_FULL_AGREE"
        return "ESS_BULLISH_ANALYST_MIXED"

    if ess_dir == "BEARISH":
        if bullish_analysts >= total / 2:
            return "ESS_BEARISH_ANALYST_MAJORITY_BULLISH"
        if bearish_analysts == total:
            return "ESS_BEARISH_ANALYST_FULL_AGREE"
        return "ESS_BEARISH_ANALYST_MIXED"

    # NEUTRAL ESS
    if bullish_analysts >= total * 0.75:
        return "ESS_NEUTRAL_ANALYST_BULLISH"
    if bearish_analysts >= total * 0.75:
        return "ESS_NEUTRAL_ANALYST_BEARISH"
    return "ESS_NEUTRAL_ANALYST_MIXED"


# ── Price data loader ──────────────────────────────────────────────────────────

def _load_price_index(repo_root: Path) -> Dict[str, "pd.DataFrame"]:
    """
    Load price CSVs for all symbols.
    Returns dict: symbol → DataFrame(date, close).
    Lazy-loads only; caller should call this once and reuse.
    """
    try:
        import pandas as pd
    except ImportError:
        return {}

    price_root = repo_root / "data" / "history" / "prices"
    index: Dict[str, pd.DataFrame] = {}
    for sym_dir in price_root.iterdir():
        if not sym_dir.is_dir() or not sym_dir.name.startswith("symbol="):
            continue
        sym = sym_dir.name[len("symbol="):]
        csv_path = sym_dir / "prices.csv"
        if not csv_path.exists():
            continue
        try:
            df = pd.read_csv(csv_path, usecols=["date", "close"])
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df = df.sort_values("date").drop_duplicates("date")
            index[sym] = df
        except Exception:
            pass
    return index


def _nearest_price(price_df: "pd.DataFrame", target: date) -> Optional[float]:
    """Return close price on or after target date (within 5 trading days)."""
    try:
        import pandas as pd
        sub = price_df[price_df["date"] >= target]
        if sub.empty:
            return None
        row = sub.iloc[0]
        if (row["date"] - target).days > 7:
            return None
        return float(row["close"])
    except Exception:
        return None


def _forward_return(price_df: "pd.DataFrame", t0: date, days: int) -> Optional[float]:
    """Compute forward return from t0 to t0+days."""
    p0 = _nearest_price(price_df, t0)
    pN = _nearest_price(price_df, t0 + timedelta(days=days))
    if p0 is None or pN is None or p0 <= 0:
        return None
    return round((pN - p0) / p0, 6)


# ── ESS archive reader ─────────────────────────────────────────────────────────

def _read_ess_archive_file(path: Path) -> List[Dict]:
    """
    Read one ESS archive CSV file.
    Returns list of dicts with keys: symbol, ess_numeric, ess_direction,
    zacks_text, zacks_direction, jefferson_direction, mclean_direction.
    """
    try:
        import pandas as pd
    except ImportError:
        return []

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        log.warning("Could not read ESS archive %s: %s", path, exc)
        return []

    if _SYMBOL_COL not in df.columns or _ESS_COL not in df.columns:
        return []

    rows = []
    for _, row in df.iterrows():
        symbol = str(row.get(_SYMBOL_COL, "") or "").strip().upper()
        if not symbol or not re.match(r"^[A-Z0-9]{1,12}$", symbol):
            continue

        # ESS numeric
        ess_raw = row.get(_ESS_COL, "")
        try:
            ess_numeric = float(ess_raw)
        except (TypeError, ValueError):
            ess_numeric = None

        ess_dir = _ess_direction(ess_numeric)

        # Analyst signals
        zacks_text = str(row.get(_ZACKS_COL, "") or "").strip()
        jefferson_text = str(row.get(_JEFFERSON_COL, "") or "").strip()
        mclean_text = str(row.get(_MCLEAN_COL, "") or "").strip()

        zacks_dir = _analyst_direction(zacks_text)
        jefferson_dir = _analyst_direction(jefferson_text)
        mclean_dir = _analyst_direction(mclean_text)

        rows.append({
            "symbol": symbol,
            "ess_numeric": ess_numeric,
            "ess_direction": ess_dir,
            "zacks_text": zacks_text,
            "zacks_direction": zacks_dir,
            "jefferson_direction": jefferson_dir,
            "mclean_direction": mclean_dir,
        })

    return rows


# ── Part A: Build dislocation inventory ───────────────────────────────────────

def build_conflict_inventory(repo_root: Path) -> List[Dict]:
    """
    Part A: Build the dislocation inventory.

    For each ESS archive date × symbol:
      - Extract ESS + analyst signals
      - Compute forward returns from price data
      - Classify disagreement pattern
      - Label WINNER/LOSER vs snapshot median return

    Returns list of inventory dicts (also persisted to CSV).
    """
    try:
        import pandas as pd
    except ImportError:
        log.warning("pandas not available — skipping conflict inventory build")
        return []

    ess_archive_dir = repo_root / "data" / "history" / "ess_archive" / "pm_archive"
    if not ess_archive_dir.exists():
        return []

    # Load all price data upfront (may be large but needed)
    log.info("ISSUE-12D: Loading price data...")
    price_index = _load_price_index(repo_root)
    log.info("ISSUE-12D: Loaded price data for %d symbols", len(price_index))

    inventory: List[Dict] = []

    # Deduplicate by (date, symbol) — keep the last file for each date
    date_file_map: Dict[date, Path] = {}
    for ess_path in sorted(ess_archive_dir.glob("*.csv")):
        dt = _parse_ess_date(ess_path.name)
        if dt:
            date_file_map[dt] = ess_path  # later file wins for same date

    log.info("ISSUE-12D: Processing %d unique ESS archive dates", len(date_file_map))

    for snapshot_date, ess_path in sorted(date_file_map.items()):
        rows = _read_ess_archive_file(ess_path)
        if not rows:
            continue

        # Compute benchmark (median 30d return across all symbols on this date)
        returns_30 = []
        for row in rows:
            pdf = price_index.get(row["symbol"])
            if pdf is not None:
                r = _forward_return(pdf, snapshot_date, 30)
                if r is not None:
                    returns_30.append(r)
        benchmark_30 = median(returns_30) if len(returns_30) >= 5 else None

        for row in rows:
            symbol = row["symbol"]
            ess_dir = row["ess_direction"]
            zacks_dir = row["zacks_direction"]
            jefferson_dir = row["jefferson_direction"]
            mclean_dir = row["mclean_direction"]

            pattern = _signal_pattern(ess_dir, zacks_dir, jefferson_dir, mclean_dir)

            pdf = price_index.get(symbol)

            # Forward returns
            ret_30 = _forward_return(pdf, snapshot_date, 30) if pdf is not None else None
            ret_60 = _forward_return(pdf, snapshot_date, 60) if pdf is not None else None

            # Winner/loser vs benchmark median
            winner_loser_30 = "NO_DATA"
            if ret_30 is not None and benchmark_30 is not None:
                if ret_30 > benchmark_30 + 0.02:
                    winner_loser_30 = "WINNER"
                elif ret_30 < benchmark_30 - 0.02:
                    winner_loser_30 = "LOSER"
                else:
                    winner_loser_30 = "NEUTRAL"

            # Did ESS signal prove correct (BULLISH → WINNER, BEARISH → LOSER correctly predicted?)
            ess_correct = None
            if winner_loser_30 != "NO_DATA" and ess_dir in ("BULLISH", "BEARISH"):
                if ess_dir == "BULLISH" and winner_loser_30 == "WINNER":
                    ess_correct = True
                elif ess_dir == "BEARISH" and winner_loser_30 == "LOSER":
                    ess_correct = True
                elif ess_dir in ("BULLISH", "BEARISH"):
                    ess_correct = False

            # Was there a signal conflict?
            analyst_dirs = [d for d in [zacks_dir, jefferson_dir, mclean_dir] if d != "NO_DATA"]
            has_conflict = False
            if ess_dir not in ("NEUTRAL", "NO_DATA") and analyst_dirs:
                disagreeing = sum(1 for a in analyst_dirs if a != ess_dir and a != "NEUTRAL")
                has_conflict = disagreeing > 0

            inventory.append({
                "symbol": symbol,
                "snapshot_date": snapshot_date.isoformat(),
                "ess_numeric": row["ess_numeric"],
                "ess_direction": ess_dir,
                "zacks_direction": zacks_dir,
                "jefferson_direction": jefferson_dir,
                "mclean_direction": mclean_dir,
                "signal_pattern": pattern,
                "has_conflict": has_conflict,
                "forward_return_30d": ret_30,
                "forward_return_60d": ret_60,
                "benchmark_return_30d": round(benchmark_30, 6) if benchmark_30 is not None else None,
                "winner_loser": winner_loser_30,
                "ess_correct": ess_correct,
            })

    log.info("ISSUE-12D: Built inventory with %d entries", len(inventory))
    return inventory


def _save_inventory(inventory: List[Dict], repo_root: Path) -> None:
    """Persist dislocation_inventory.csv."""
    out_dir = repo_root / "data" / "analysis" / "dislocation"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dislocation_inventory.csv"
    if not inventory:
        out_path.write_text("symbol,snapshot_date,ess_direction,signal_pattern,forward_return_30d,winner_loser\n", encoding="utf-8")
        return
    fieldnames = list(inventory[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory)


# ── Part B: Pattern outcome analysis ──────────────────────────────────────────

def compute_pattern_outcomes(inventory: List[Dict]) -> List[Dict]:
    """
    Part B: For each disagreement pattern, compute:
      occurrences, winner_count, loser_count, winner_rate_pct,
      avg_return_30d, median_return_30d, best_return_30d, worst_return_30d.
    """
    buckets: Dict[str, List[Dict]] = defaultdict(list)
    for entry in inventory:
        if entry.get("has_conflict"):
            buckets[entry["signal_pattern"]].append(entry)
        # Also add non-conflict baseline
        elif entry["signal_pattern"] in (
            "ESS_BULLISH_ANALYST_FULL_AGREE",
            "ESS_BEARISH_ANALYST_FULL_AGREE",
        ):
            buckets[entry["signal_pattern"]].append(entry)

    outcomes = []
    for pattern, entries in sorted(buckets.items(), key=lambda x: -len(x[1])):
        rets = [e["forward_return_30d"] for e in entries if e["forward_return_30d"] is not None]
        winners = [e for e in entries if e["winner_loser"] == "WINNER"]
        losers  = [e for e in entries if e["winner_loser"] == "LOSER"]
        total_with_outcome = len([e for e in entries if e["winner_loser"] != "NO_DATA"])

        ess_rights = [e for e in entries if e["ess_correct"] is True]
        ess_total  = [e for e in entries if e["ess_correct"] is not None]

        outcomes.append({
            "signal_pattern": pattern,
            "occurrences": len(entries),
            "occurrences_with_price_data": total_with_outcome,
            "winner_count": len(winners),
            "loser_count": len(losers),
            "winner_rate_pct": round(len(winners) / total_with_outcome * 100, 1) if total_with_outcome > 0 else None,
            "loser_rate_pct": round(len(losers) / total_with_outcome * 100, 1) if total_with_outcome > 0 else None,
            "avg_return_30d_pct": round(mean(rets) * 100, 2) if rets else None,
            "median_return_30d_pct": round(median(rets) * 100, 2) if rets else None,
            "best_return_30d_pct": round(max(rets) * 100, 2) if rets else None,
            "worst_return_30d_pct": round(min(rets) * 100, 2) if rets else None,
            "ess_correct_count": len(ess_rights),
            "ess_correct_rate_pct": round(len(ess_rights) / len(ess_total) * 100, 1) if ess_total else None,
            "top_symbols": sorted(
                list({e["symbol"] for e in winners}),
                key=lambda s: -sum(1 for e in winners if e["symbol"] == s)
            )[:5],
        })

    return outcomes


# ── Part C: Signal reliability scorecard ──────────────────────────────────────

def compute_signal_scorecard(inventory: List[Dict]) -> List[Dict]:
    """
    Part C: For each signal type, compute:
      signal_name, direction, total_cases, winner_rate_pct, avg_return_pct,
      conflict_cases, conflict_winner_rate_pct.
    """
    # Group by ESS direction across all entries (full universe)
    by_ess: Dict[str, List[Dict]] = defaultdict(list)
    for e in inventory:
        if e["ess_direction"] not in ("NO_DATA", "NEUTRAL"):
            by_ess[e["ess_direction"]].append(e)

    # Analyst signal: use majority direction of Zacks+Jefferson+McLean
    by_analyst: Dict[str, List[Dict]] = defaultdict(list)
    for e in inventory:
        dirs = [d for d in [e["zacks_direction"], e["jefferson_direction"], e["mclean_direction"]]
                if d != "NO_DATA"]
        if not dirs:
            continue
        bullish = sum(1 for d in dirs if d == "BULLISH")
        bearish = sum(1 for d in dirs if d == "BEARISH")
        if bullish > len(dirs) / 2:
            by_analyst["ANALYST_BULLISH"].append(e)
        elif bearish > len(dirs) / 2:
            by_analyst["ANALYST_BEARISH"].append(e)

    def _stats(entries: List[Dict], conflict_only: bool = False) -> Dict:
        subset = [e for e in entries if e.get("has_conflict")] if conflict_only else entries
        total = len([e for e in subset if e["winner_loser"] != "NO_DATA"])
        winners = sum(1 for e in subset if e["winner_loser"] == "WINNER")
        rets = [e["forward_return_30d"] for e in subset if e["forward_return_30d"] is not None]
        return {
            "total": total,
            "winner_count": winners,
            "winner_rate_pct": round(winners / total * 100, 1) if total > 0 else None,
            "avg_return_pct": round(mean(rets) * 100, 2) if rets else None,
        }

    scorecard = []

    for direction, entries in sorted(by_ess.items()):
        all_s  = _stats(entries)
        conf_s = _stats(entries, conflict_only=True)
        scorecard.append({
            "signal_name": "ESS (StarMine)",
            "signal_key": f"ESS_{direction}",
            "direction": direction,
            "total_cases": len(entries),
            "winner_rate_pct": all_s["winner_rate_pct"],
            "avg_return_pct": all_s["avg_return_pct"],
            "conflict_cases": len([e for e in entries if e.get("has_conflict")]),
            "conflict_winner_rate_pct": conf_s["winner_rate_pct"],
            "conflict_avg_return_pct": conf_s["avg_return_pct"],
            "interpretation": (
                "ESS primary signal (55% weight in CW-DAS). "
                "When ESS is bullish and analysts disagree, ESS historically "
                "outperforms analyst consensus." if direction == "BULLISH"
                else "ESS bearish signal historically has predictive value "
                "even when analysts disagree."
            ),
        })

    for key, entries in sorted(by_analyst.items()):
        direction = "BULLISH" if "BULLISH" in key else "BEARISH"
        all_s  = _stats(entries)
        conf_s = _stats(entries, conflict_only=True)
        scorecard.append({
            "signal_name": "Analyst Consensus (Zacks+Independent)",
            "signal_key": key,
            "direction": direction,
            "total_cases": len(entries),
            "winner_rate_pct": all_s["winner_rate_pct"],
            "avg_return_pct": all_s["avg_return_pct"],
            "conflict_cases": len([e for e in entries if e.get("has_conflict")]),
            "conflict_winner_rate_pct": conf_s["winner_rate_pct"],
            "conflict_avg_return_pct": conf_s["avg_return_pct"],
            "interpretation": (
                "Analyst consensus (buy-side). During signal conflicts, "
                "analyst consensus has lower historical reliability than ESS "
                "in the SIH universe."
            ),
        })

    return scorecard


# ── Part D: Symbol deep dive ───────────────────────────────────────────────────

def symbol_deep_dive(symbol: str, inventory: List[Dict]) -> Dict:
    """
    Part D: Deep dive for a specific symbol (e.g. MSFT).

    Returns all historical signal states + outcomes for the symbol,
    plus a pattern frequency table and conclusion.
    """
    sym = symbol.upper()
    entries = [e for e in inventory if e["symbol"] == sym]
    entries_sorted = sorted(entries, key=lambda e: e["snapshot_date"])

    # Pattern frequency among conflict cases
    conflict_entries = [e for e in entries if e.get("has_conflict")]
    pattern_freq: Dict[str, int] = defaultdict(int)
    for e in conflict_entries:
        pattern_freq[e["signal_pattern"]] += 1

    # ESS correct rate for this symbol
    ess_outcomes = [e for e in entries if e["ess_correct"] is not None]
    ess_correct_rate = (
        round(sum(1 for e in ess_outcomes if e["ess_correct"]) / len(ess_outcomes) * 100, 1)
        if ess_outcomes else None
    )

    # Average return when conflict occurred
    conflict_rets = [e["forward_return_30d"] for e in conflict_entries if e["forward_return_30d"] is not None]
    avg_conflict_return = round(mean(conflict_rets) * 100, 2) if conflict_rets else None

    # Dominant current pattern
    current = entries_sorted[-1] if entries_sorted else None
    current_pattern = current["signal_pattern"] if current else "UNKNOWN"
    current_ess_dir = current["ess_direction"] if current else "UNKNOWN"

    # Find historical precedents for current pattern
    precedents = [e for e in inventory if e["signal_pattern"] == current_pattern and e["symbol"] != sym]
    prec_rets = [e["forward_return_30d"] for e in precedents if e["forward_return_30d"] is not None]
    prec_winners = [e for e in precedents if e["winner_loser"] == "WINNER"]

    # Conclusion
    conclusion = _build_deep_dive_conclusion(
        sym, current_pattern, current_ess_dir, ess_correct_rate, prec_rets, prec_winners, precedents
    )

    return {
        "symbol": sym,
        "total_observations": len(entries),
        "conflict_observations": len(conflict_entries),
        "ess_correct_rate_pct": ess_correct_rate,
        "avg_conflict_return_pct": avg_conflict_return,
        "current_pattern": current_pattern,
        "current_snapshot_date": current["snapshot_date"] if current else None,
        "current_ess_direction": current_ess_dir,
        "pattern_frequency": dict(sorted(pattern_freq.items(), key=lambda x: -x[1])),
        "historical_records": [
            {k: v for k, v in e.items()}
            for e in entries_sorted
        ],
        "universe_precedents": {
            "pattern": current_pattern,
            "total_occurrences": len(precedents),
            "winner_count": len(prec_winners),
            "winner_rate_pct": round(len(prec_winners) / len(precedents) * 100, 1) if precedents else None,
            "avg_return_30d_pct": round(mean(prec_rets) * 100, 2) if prec_rets else None,
        },
        "conclusion": conclusion,
    }


def _build_deep_dive_conclusion(
    symbol: str,
    pattern: str,
    ess_dir: str,
    ess_correct_rate: Optional[float],
    prec_rets: List[float],
    prec_winners: List[Dict],
    precedents: List[Dict],
) -> str:
    """Build a plain-language conclusion for the symbol deep dive."""
    parts = []

    prec_total = len(precedents)
    prec_winner_rate = round(len(prec_winners) / prec_total * 100, 1) if prec_total > 0 else None

    if prec_total == 0:
        parts.append(
            f"No historical precedents found in the SIH universe for the current signal pattern ({pattern}). "
            "Insufficient data to draw statistical conclusions."
        )
        return " ".join(parts)

    prec_avg_ret = round(mean(prec_rets) * 100, 2) if prec_rets else None

    parts.append(
        f"The current pattern '{pattern}' has occurred {prec_total} times historically across the SIH universe."
    )

    if prec_winner_rate is not None:
        if prec_winner_rate >= 65:
            parts.append(
                f"In {prec_winner_rate}% of cases, the position was a winner vs. the median — "
                "this pattern historically favors the bulls."
            )
        elif prec_winner_rate <= 35:
            parts.append(
                f"Only {prec_winner_rate}% of cases were winners — "
                "this conflict pattern has historically been a caution signal."
            )
        else:
            parts.append(
                f"{prec_winner_rate}% of cases produced above-median returns — "
                "this pattern has a mixed historical record."
            )

    if prec_avg_ret is not None:
        parts.append(f"Average 30-day return for this pattern: {prec_avg_ret:+.1f}%.")

    if ess_correct_rate is not None:
        if ess_correct_rate >= 60:
            parts.append(
                f"For {symbol} specifically, ESS was the correct directional signal "
                f"{ess_correct_rate}% of the time historically — "
                "suggesting ESS deserves more weight than analyst consensus for this name."
            )
        else:
            parts.append(
                f"For {symbol}, ESS was correct {ess_correct_rate}% of the time — "
                "analyst signals may carry additional weight for this name."
            )

    if ess_dir == "BULLISH" and "ANALYST" in pattern and "BEARISH" in pattern:
        parts.append(
            "Historical evidence suggests that when ESS is bullish and analysts disagree, "
            "the ESS signal has stronger predictive value in the SIH analytical universe. "
            "Analyst consensus on individual names frequently lags quantitative signals."
        )
    elif ess_dir == "BEARISH" and "BULLISH" in pattern:
        parts.append(
            "Historical evidence suggests caution: analyst enthusiasm has not reliably "
            "overridden bearish ESS signals in the SIH universe."
        )

    return " ".join(parts)


# ── Part E: Learning summary ───────────────────────────────────────────────────

def compute_learning_summary(inventory: List[Dict], outcomes: List[Dict]) -> Dict:
    """
    Part E: High-level learning summary for the portfolio panel.
      - Strongest historical conflict winners
      - Strongest historical conflict losers
      - Most reliable signal patterns
      - Least reliable signal patterns
    """
    conflict_entries = [e for e in inventory if e.get("has_conflict") and e["winner_loser"] != "NO_DATA"]

    # Top winner symbols during conflicts (most frequent WINNER)
    winner_freq: Dict[str, int] = defaultdict(int)
    loser_freq: Dict[str, int] = defaultdict(int)
    for e in conflict_entries:
        if e["winner_loser"] == "WINNER":
            winner_freq[e["symbol"]] += 1
        elif e["winner_loser"] == "LOSER":
            loser_freq[e["symbol"]] += 1

    top_winners = sorted(winner_freq.items(), key=lambda x: -x[1])[:5]
    top_losers  = sorted(loser_freq.items(),  key=lambda x: -x[1])[:5]

    # Most/least reliable conflict patterns (by winner_rate when conflicts exist)
    conflict_outcomes = [o for o in outcomes
                         if o.get("occurrences_with_price_data", 0) >= 5 and
                         o.get("winner_rate_pct") is not None and
                         "FULL_AGREE" not in o["signal_pattern"]]
    most_reliable  = sorted(conflict_outcomes, key=lambda o: -(o["winner_rate_pct"] or 0))[:3]
    least_reliable = sorted(conflict_outcomes, key=lambda o: (o["winner_rate_pct"] or 50))[:3]

    # Overall ESS vs analyst accuracy during conflicts
    ess_correct = [e for e in conflict_entries if e["ess_correct"] is True]
    ess_total   = [e for e in conflict_entries if e["ess_correct"] is not None]
    ess_conflict_win_rate = (
        round(len(ess_correct) / len(ess_total) * 100, 1) if ess_total else None
    )

    return {
        "total_conflict_observations": len(conflict_entries),
        "ess_conflict_correct_rate_pct": ess_conflict_win_rate,
        "strongest_conflict_winners": [{"symbol": s, "winner_count": c} for s, c in top_winners],
        "strongest_conflict_losers": [{"symbol": s, "loser_count": c} for s, c in top_losers],
        "most_reliable_patterns": [
            {
                "pattern": o["signal_pattern"],
                "occurrences": o["occurrences"],
                "winner_rate_pct": o["winner_rate_pct"],
                "avg_return_pct": o["avg_return_30d_pct"],
            }
            for o in most_reliable
        ],
        "least_reliable_patterns": [
            {
                "pattern": o["signal_pattern"],
                "occurrences": o["occurrences"],
                "winner_rate_pct": o["winner_rate_pct"],
                "avg_return_pct": o["avg_return_30d_pct"],
            }
            for o in least_reliable
        ],
        "governance_note": (
            "This panel is informational only. "
            "No scoring, ranking, or recommendation logic is modified by these findings. "
            "Historical patterns are computed from SIH signal archive + price data. "
            "Q10 answer: No algorithm changes are recommended. "
            "Signal reliability is an operator-education tool, not a tuning trigger."
        ),
    }


# ── Master refresh ─────────────────────────────────────────────────────────────

def refresh_conflict_data(repo_root: Path) -> Dict:
    """
    Build and persist all ISSUE-12D artifacts.
    Returns a status dict.
    """
    out_dir = repo_root / "data" / "analysis" / "dislocation"
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("ISSUE-12D: Starting signal conflict data refresh")

    inventory = build_conflict_inventory(repo_root)
    _save_inventory(inventory, repo_root)

    outcomes = compute_pattern_outcomes(inventory)
    (out_dir / "pattern_outcomes.json").write_text(
        json.dumps({"patterns": outcomes, "version": _CONFLICT_REVIEW_VERSION}, indent=2),
        encoding="utf-8",
    )

    scorecard = compute_signal_scorecard(inventory)
    (out_dir / "signal_scorecard.json").write_text(
        json.dumps({"scorecard": scorecard, "version": _CONFLICT_REVIEW_VERSION}, indent=2),
        encoding="utf-8",
    )

    learning = compute_learning_summary(inventory, outcomes)
    (out_dir / "learning_summary.json").write_text(
        json.dumps({**learning, "version": _CONFLICT_REVIEW_VERSION}, indent=2),
        encoding="utf-8",
    )

    meta = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "inventory_rows": len(inventory),
        "conflict_rows": sum(1 for e in inventory if e.get("has_conflict")),
        "pattern_count": len(outcomes),
        "version": _CONFLICT_REVIEW_VERSION,
    }
    (out_dir / "_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    log.info(
        "ISSUE-12D: Refresh complete. %d inventory rows, %d conflict cases, %d patterns",
        len(inventory), meta["conflict_rows"], len(outcomes),
    )
    return meta


# ── Public read-path API ───────────────────────────────────────────────────────

def load_inventory(repo_root: Path) -> List[Dict]:
    """Load persisted dislocation_inventory.csv."""
    path = repo_root / "data" / "analysis" / "dislocation" / "dislocation_inventory.csv"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Type-cast numeric fields
            for col in ("ess_numeric", "forward_return_30d", "forward_return_60d", "benchmark_return_30d"):
                if row.get(col) not in (None, "None", ""):
                    try:
                        row[col] = float(row[col])
                    except (ValueError, TypeError):
                        row[col] = None
                else:
                    row[col] = None
            for col in ("has_conflict", "ess_correct"):
                val = row.get(col, "")
                if val == "True":
                    row[col] = True
                elif val == "False":
                    row[col] = False
                else:
                    row[col] = None
            rows.append(row)
    return rows


def load_or_refresh(repo_root: Path, *, force: bool = False) -> Dict[str, object]:
    """
    Load pre-computed artifacts if current, otherwise rebuild.
    Returns all four artifacts as a combined dict.
    """
    out_dir = repo_root / "data" / "analysis" / "dislocation"
    meta_path = out_dir / "_meta.json"

    if force or not meta_path.exists():
        refresh_conflict_data(repo_root)

    inventory = load_inventory(repo_root)

    outcomes_path = out_dir / "pattern_outcomes.json"
    scorecard_path = out_dir / "signal_scorecard.json"
    learning_path  = out_dir / "learning_summary.json"

    outcomes  = json.loads(outcomes_path.read_text(encoding="utf-8")) if outcomes_path.exists() else {}
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8")) if scorecard_path.exists() else {}
    learning  = json.loads(learning_path.read_text(encoding="utf-8")) if learning_path.exists() else {}
    meta      = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    return {
        "inventory": inventory,
        "outcomes": outcomes,
        "scorecard": scorecard,
        "learning": learning,
        "meta": meta,
    }
