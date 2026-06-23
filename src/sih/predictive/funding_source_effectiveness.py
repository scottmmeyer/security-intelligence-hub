"""RESEARCH-01 — Funding Source Effectiveness.

Studies whether CRA capital sources historically led to better portfolio
outcomes than the positions they funded.

Core question: "When CRA sold LMAT (TAX_AWARE_EXIT) and bought DELL (CCL),
did DELL subsequently outperform LMAT?"

Reads from:
  - data/analysis/dislocation/dislocation_inventory.csv (signal states)
  - data/history/prices/                               (forward returns)
  - Latest PAR holdings (to identify current CRA candidates)

Governance: Read-only / research only.

Public API
----------
  funding_effectiveness_study(repo_root) → dict
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Optional, Tuple


_STUDY_FILE = "data/analysis/dislocation/funding_effectiveness.json"

_GOVERNANCE_NOTE = (
    "RESEARCH-01 is research-only. "
    "No CRA capital source selection logic, recommendation algorithms, "
    "or governance rules are modified. "
    "Effectiveness estimates are based on historical price data and are "
    "not predictive of future outcomes."
)

_CATEGORY_INTENT = {
    "SIGNAL_DETERIORATION": "THESIS_EXIT_OR_TRIM",
    "STRATEGIC_EXIT":       "THESIS_EXIT_OR_TRIM",
    "OVERWEIGHT_REDUCTION": "STRUCTURAL_REALLOCATION",
    "TAX_AWARE_EXIT":       "TAX_FUNDING",
    "LOW_CONVICTION_REDUCTION": "OPPORTUNITY_COST",
}


def _load_price(symbol: str, repo_root: Path) -> Dict[str, float]:
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


def _forward_return(prices: Dict[str, float], from_date: date, days: int) -> Optional[float]:
    p0 = None
    for i in range(4):
        d = (from_date + timedelta(days=i)).isoformat()
        if d in prices and prices[d] > 0:
            p0 = prices[d]
            break
    if p0 is None:
        return None
    pN = None
    target = from_date + timedelta(days=days)
    for i in range(6):
        d = (target + timedelta(days=i)).isoformat()
        if d in prices and prices[d] > 0:
            pN = prices[d]
            break
    if pN is None:
        return None
    return round((pN - p0) / p0, 6)


def _load_inventory(repo_root: Path) -> List[Dict]:
    path = repo_root / "data" / "analysis" / "dislocation" / "dislocation_inventory.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for col in ("forward_return_30d", "ess_numeric"):
            if row.get(col) not in (None, "None", ""):
                try: row[col] = float(row[col])
                except: row[col] = None
            else: row[col] = None
    return rows


def _study_category_effectiveness(
    inventory: List[Dict],
    price_cache: Dict[str, Dict[str, float]],
) -> Dict:
    """
    For each CRA category, compute:
    - Average return of source positions AFTER they would have been reduced
    - Useful for: "Did we sell too early? Did BEARISH ESS correctly predict the move?"
    """
    by_category: Dict[str, List[float]] = defaultdict(list)
    by_intent:   Dict[str, List[float]] = defaultdict(list)

    for entry in inventory:
        category = entry.get("signal_pattern", "")
        sym = str(entry.get("symbol") or "").upper()
        snap_date_str = entry.get("snapshot_date", "")
        if not snap_date_str or not sym:
            continue
        try:
            snap_date = date.fromisoformat(snap_date_str)
        except ValueError:
            continue

        prices = price_cache.get(sym, {})
        ret_30 = _forward_return(prices, snap_date, 30)
        if ret_30 is None:
            continue

        # Group by ESS direction (proxy for CRA category)
        ess_dir = entry.get("ess_direction", "")
        by_category[f"ESS_{ess_dir}"].append(ret_30)

        # Winner/loser context
        wl = entry.get("winner_loser", "NO_DATA")
        if wl in ("WINNER", "LOSER"):
            by_intent[wl].append(ret_30)

    results = {}
    for cat, rets in sorted(by_category.items()):
        pct_rets = [r * 100 for r in rets]
        results[cat] = {
            "n":           len(rets),
            "avg_return":  round(mean(pct_rets), 3) if pct_rets else None,
            "median":      round(median(pct_rets), 3) if pct_rets else None,
            "positive_pct": round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1) if rets else None,
        }

    return results


def funding_effectiveness_study(repo_root: Path | str = ".") -> Dict:
    """
    Compute effectiveness of CRA signal categories.

    Returns:
        { category_outcomes: {...}, key_findings: [...], governance_note }
    """
    root      = Path(repo_root)
    inventory = _load_inventory(root)

    if not inventory:
        return {
            "status": "NO_INVENTORY",
            "category_outcomes": {},
            "key_findings": [],
            "governance_note": _GOVERNANCE_NOTE,
        }

    # Pre-load prices for all symbols in inventory
    syms = {str(e.get("symbol") or "").upper() for e in inventory if e.get("symbol")}
    price_cache: Dict[str, Dict[str, float]] = {}
    for sym in syms:
        prices = _load_price(sym, root)
        if prices:
            price_cache[sym] = prices

    category_outcomes = _study_category_effectiveness(inventory, price_cache)

    # Generate key findings
    findings = []
    bearish_ess = category_outcomes.get("ESS_BEARISH", {})
    bullish_ess = category_outcomes.get("ESS_BULLISH", {})
    if bearish_ess.get("avg_return") is not None:
        ret = bearish_ess["avg_return"]
        pos = bearish_ess.get("positive_pct", 0)
        if ret < 0:
            findings.append(
                f"BEARISH ESS signals: avg 30d return {ret:+.2f}% ({pos:.0f}% positive). "
                "Selling BEARISH ESS holdings before they deteriorate further appears supported."
            )
        else:
            findings.append(
                f"BEARISH ESS signals: avg 30d return {ret:+.2f}% ({pos:.0f}% positive). "
                "Some BEARISH ESS positions rebounded — premature exits may be costly."
            )

    if bullish_ess.get("avg_return") is not None and bearish_ess.get("avg_return") is not None:
        diff = bullish_ess["avg_return"] - bearish_ess["avg_return"]
        findings.append(
            f"ESS signal spread: BULLISH ({bullish_ess['avg_return']:+.2f}%) outperformed "
            f"BEARISH ({bearish_ess['avg_return']:+.2f}%) by {diff:+.2f}pp over 30 days. "
            "This supports using ESS direction as a primary CRA triage signal."
        )

    payload = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "inventory_entries": len(inventory),
        "symbols_analyzed": len(price_cache),
        "category_outcomes": category_outcomes,
        "key_findings":     findings,
        "governance_note":  _GOVERNANCE_NOTE,
    }

    try:
        out = root / _STUDY_FILE
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    return payload
