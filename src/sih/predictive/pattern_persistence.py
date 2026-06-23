"""DISLOCATION-04 — Signal Conflict Pattern Persistence.

For each security in the ESS archive, tracks how many consecutive dates
the symbol has been in the same conflict pattern, and whether that pattern
has been stable or shifting.

Answers: "MSFT has been ESS_BULLISH_ANALYST_SKEPTICAL for 5 of 8 archive dates."

Data sources (read-only):
  - data/analysis/dislocation/dislocation_inventory.csv  (ISSUE-12D)
  - data/analysis/dislocation/conflict_alpha_report.json  (DISLOCATION-02)

Writes (regeneratable):
  - data/analysis/dislocation/pattern_persistence.json

Public API
----------
  symbol_pattern_persistence(symbol, repo_root) → dict
  all_pattern_persistence(repo_root)            → dict
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_PERSISTENCE_FILE = "data/analysis/dislocation/pattern_persistence.json"
_ALPHA_FILE       = "data/analysis/dislocation/conflict_alpha_report.json"

_PATTERN_LABELS = {
    "ESS_BULLISH_ANALYST_MAJORITY_BEARISH": "ESS Buy / Analyst Sell",
    "ESS_BULLISH_ANALYST_SKEPTICAL":        "ESS Buy / Analysts Skeptical",
    "ESS_BULLISH_ANALYST_FULL_AGREE":       "ESS Buy / All Agree Buy",
    "ESS_BULLISH_ANALYST_MIXED":            "ESS Buy / Analysts Mixed",
    "ESS_BEARISH_ANALYST_MAJORITY_BULLISH": "ESS Sell / Analyst Buy",
    "ESS_BEARISH_ANALYST_FULL_AGREE":       "ESS Sell / All Agree Sell",
    "ESS_BEARISH_ANALYST_MIXED":            "ESS Sell / Analysts Mixed",
}

_CONFLICT_PATTERNS = frozenset(_PATTERN_LABELS.keys())


def _load_inventory(repo_root: Path) -> List[Dict]:
    from src.sih.signal_conflict_review import load_inventory
    return load_inventory(repo_root)


def _load_alpha_index(repo_root: Path) -> Dict[str, Dict]:
    path = repo_root / _ALPHA_FILE
    if not path.exists():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        return {p["signal_pattern"]: p for p in report.get("patterns", [])}
    except (OSError, json.JSONDecodeError):
        return {}


def _compute_persistence(entries: List[Dict]) -> Dict:
    """Compute pattern persistence stats for one symbol."""
    sorted_entries = sorted(entries, key=lambda e: e.get("snapshot_date", ""))
    if not sorted_entries:
        return {}

    dates = len(sorted_entries)
    current_pattern = sorted_entries[-1].get("signal_pattern", "")
    current_date    = sorted_entries[-1].get("snapshot_date", "")

    # Count how many dates the current pattern has appeared
    pattern_counts: Dict[str, int] = defaultdict(int)
    for e in sorted_entries:
        p = e.get("signal_pattern", "")
        if p:
            pattern_counts[p] += 1

    # Consecutive streak — how many consecutive dates ending at latest had same pattern
    streak = 0
    for e in reversed(sorted_entries):
        if e.get("signal_pattern") == current_pattern:
            streak += 1
        else:
            break

    current_count    = pattern_counts.get(current_pattern, 0)
    persistence_pct  = round(current_count / dates * 100, 1) if dates > 0 else 0.0
    is_conflict      = current_pattern in _CONFLICT_PATTERNS

    # Trend: is current pattern strengthening or rotating?
    if len(sorted_entries) >= 3:
        recent = sorted_entries[-3:]
        all_same = all(e.get("signal_pattern") == current_pattern for e in recent)
        trend = "PERSISTENT" if all_same else "ROTATING"
    else:
        trend = "INSUFFICIENT_DATA"

    # Dominant pattern (most frequent)
    dominant = max(pattern_counts, key=lambda k: pattern_counts[k]) if pattern_counts else ""

    return {
        "symbol":             sorted_entries[0].get("symbol", ""),
        "dates_observed":     dates,
        "current_pattern":    current_pattern,
        "current_pattern_label": _PATTERN_LABELS.get(current_pattern, current_pattern.replace("_", " ")),
        "current_date":       current_date,
        "current_count":      current_count,
        "persistence_pct":    persistence_pct,
        "streak":             streak,
        "trend":              trend,
        "is_current_conflict": is_conflict,
        "dominant_pattern":   dominant,
        "pattern_counts":     dict(sorted(pattern_counts.items(), key=lambda x: -x[1])),
        "history":            [
            {"date": e["snapshot_date"], "pattern": e.get("signal_pattern", ""),
             "ess_direction": e.get("ess_direction", "")}
            for e in sorted_entries
        ],
    }


def _attach_alpha(persistence: Dict, alpha_index: Dict[str, Dict]) -> Dict:
    """Attach alpha data for the current conflict pattern."""
    pattern = persistence.get("current_pattern", "")
    alpha   = alpha_index.get(pattern, {})
    persistence["alpha_class"]         = alpha.get("alpha_class")
    persistence["excess_return_pct"]   = alpha.get("excess_return_pct")
    persistence["win_rate_pct"]        = alpha.get("win_rate_pct")
    persistence["significance"]        = alpha.get("significance")
    persistence["alpha_observations"]  = alpha.get("observations", 0)
    return persistence


def _build_all(repo_root: Path) -> Dict:
    inventory   = _load_inventory(repo_root)
    alpha_index = _load_alpha_index(repo_root)

    # Group by symbol
    by_symbol: Dict[str, List[Dict]] = defaultdict(list)
    for e in inventory:
        sym = str(e.get("symbol") or "").strip().upper()
        if sym:
            by_symbol[sym].append(e)

    results = []
    for sym, entries in sorted(by_symbol.items()):
        pers = _compute_persistence(entries)
        if pers:
            pers = _attach_alpha(pers, alpha_index)
            results.append(pers)

    # Sort: most-persistent conflicted symbols first
    results.sort(key=lambda r: (
        -(r.get("persistence_pct", 0) if r.get("is_current_conflict") else 0),
        r.get("symbol", ""),
    ))

    return {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "total_symbols": len(results),
        "conflict_count": sum(1 for r in results if r.get("is_current_conflict")),
        "persistent_conflicts": [
            r for r in results
            if r.get("is_current_conflict") and r.get("persistence_pct", 0) >= 50
        ][:20],
        "all_symbols": results,
        "governance_note": (
            "DISLOCATION-04 is informational only. "
            "Pattern persistence is derived from historical ESS archive and analyst ratings. "
            "No scoring, CW-DAS, UCF, CRA, or recommendation logic is modified."
        ),
    }


def _cache_path(repo_root: Path) -> Path:
    return repo_root / _PERSISTENCE_FILE


def _get_persistence(repo_root: Path, force: bool = False) -> Dict:
    cache = _cache_path(repo_root)
    inv   = repo_root / "data" / "analysis" / "dislocation" / "dislocation_inventory.csv"
    if not force and cache.exists() and inv.exists():
        try:
            if cache.stat().st_mtime >= inv.stat().st_mtime:
                return json.loads(cache.read_text(encoding="utf-8"))
        except OSError:
            pass
    payload = _build_all(repo_root)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    return payload


def symbol_pattern_persistence(symbol: str, repo_root: Path | str = ".") -> Dict:
    """Return pattern persistence for a single symbol."""
    root    = Path(repo_root)
    data    = _get_persistence(root)
    sym     = symbol.strip().upper()
    for r in data.get("all_symbols", []):
        if r.get("symbol") == sym:
            return r
    return {"symbol": sym, "error": "Symbol not in ESS archive.", "dates_observed": 0}


def all_pattern_persistence(repo_root: Path | str = ".") -> Dict:
    """Return persistence analysis for all symbols."""
    return _get_persistence(Path(repo_root))
