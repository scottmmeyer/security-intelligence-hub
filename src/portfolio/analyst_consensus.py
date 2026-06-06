"""Analyst consensus loading, labeling, and conflict badge logic.

Phase 7.5J — Analyst Consensus Transparency.

Governance: transparency-only.  No scoring, ranking, or deployment queue
logic depends on these functions.  The module is consumed by the UI layer
(via runner.py) to surface analyst consensus information to the operator.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from .models import AnalystConsensus

# ── ABR label scale ──────────────────────────────────────────────────────────
# Yahoo Finance Average Broker Recommendation (ABR): 1.0 (Strong Buy) → 5.0 (Sell)

def abr_to_label(abr: Optional[float]) -> str:
    """Map a numeric ABR value to a consensus label string.

    Boundaries: STRONG_BUY [1.0, 1.5], BUY (1.5, 2.0], MODERATE_BUY (2.0, 2.5],
                HOLD (2.5, 3.5], SELL (3.5, 5.0].
    ABR=1.5 → STRONG_BUY per spec (upper-inclusive on STRONG_BUY boundary).
    """
    if abr is None:
        return "NO_CONSENSUS"
    if abr <= 1.5:
        return "STRONG_BUY"
    if abr <= 2.0:
        return "BUY"
    if abr <= 2.5:
        return "MODERATE_BUY"
    if abr <= 3.5:
        return "HOLD"
    return "SELL"


def _abr_strength(abr: Optional[float]) -> str:
    """Derive consensus_strength from ABR distance from the neutral midpoint (3.0)."""
    if abr is None:
        return "NONE"
    dist = abs(abr - 2.5)          # distance from HOLD midpoint
    if dist >= 1.25:
        return "HIGH"
    if dist >= 0.75:
        return "MODERATE"
    return "LOW"


# ── Loader ───────────────────────────────────────────────────────────────────

def load_analyst_consensus(yahoo_csv_path: Path) -> dict[str, AnalystConsensus]:
    """Load analyst consensus from a Yahoo supplemental CSV.

    Returns a dict keyed by uppercase symbol.  Returns empty dict if the file
    does not exist or cannot be parsed.

    Expected columns: symbol, abr, price_target, current_price, upside_pct,
                       sourced_date, eps_growth_5yr (ignored).
    """
    if not yahoo_csv_path.exists():
        return {}

    result: dict[str, AnalystConsensus] = {}
    try:
        with open(yahoo_csv_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                sym = (row.get("symbol") or "").strip().upper()
                if not sym:
                    continue

                def _float(key: str) -> Optional[float]:
                    v = row.get(key, "").strip()
                    try:
                        return float(v) if v else None
                    except ValueError:
                        return None

                def _int(key: str) -> Optional[int]:
                    v = row.get(key, "").strip()
                    try:
                        return int(v) if v else None
                    except ValueError:
                        return None

                abr = _float("abr")
                result[sym] = AnalystConsensus(
                    symbol=sym,
                    abr=abr,
                    analyst_count=_int("analyst_count"),   # ISSUE-08: populated from CSV
                    price_target=_float("price_target"),
                    current_price=_float("current_price"),
                    upside_pct=_float("upside_pct"),
                    consensus_label=abr_to_label(abr),
                    consensus_strength=_abr_strength(abr),
                    refresh_date=(row.get("sourced_date") or "").strip(),
                )
    except Exception:
        return {}

    return result


# ── Conflict badge ───────────────────────────────────────────────────────────

_ESS_BULLISH_SET: frozenset[str] = frozenset({"VERY_BULLISH", "BULLISH"})
_ESS_BEARISH_SET: frozenset[str] = frozenset({"VERY_BEARISH", "BEARISH"})
_ABR_BUY_SET: frozenset[str] = frozenset({"STRONG_BUY", "BUY", "MODERATE_BUY"})
_ABR_SELL_SET: frozenset[str] = frozenset({"HOLD", "SELL"})


def compute_conflict_badge(
    ess_text: Optional[str],
    consensus_label: str,
) -> str:
    """Compute an informational conflict badge between ESS and ABR consensus.

    Returns one of:
      CONSENSUS_ALIGNED      — ESS and ABR point in the same direction
      CONSENSUS_DIVERGENCE   — ESS and ABR point in opposite directions
      CONSENSUS_NEUTRAL      — one or both signals are neutral/unknown
      NO_CONSENSUS           — no ABR data available

    This badge is informational only.  It has no effect on scoring, ranking,
    or the deployment queue.
    """
    if consensus_label == "NO_CONSENSUS":
        return "NO_CONSENSUS"

    ess = (ess_text or "").strip().upper()
    if not ess or ess in ("UNKNOWN", "NEUTRAL", "NEUTRAL_BEARISH", "NEUTRAL_BULLISH"):
        return "CONSENSUS_NEUTRAL"

    ess_bullish = ess in _ESS_BULLISH_SET
    ess_bearish = ess in _ESS_BEARISH_SET
    abr_buy = consensus_label in _ABR_BUY_SET
    abr_sell = consensus_label in _ABR_SELL_SET

    if (ess_bullish and abr_buy) or (ess_bearish and abr_sell):
        return "CONSENSUS_ALIGNED"
    if (ess_bullish and abr_sell) or (ess_bearish and abr_buy):
        return "CONSENSUS_DIVERGENCE"
    return "CONSENSUS_NEUTRAL"
