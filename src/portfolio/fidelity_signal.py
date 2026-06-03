"""Fidelity analyst signal transparency module — Phase 7.5K.

Governance: transparency-only.  No scoring, no ranking, no deployment queue
changes.  All functions are read-only display helpers.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ── ESS label → analyst-language mapping ─────────────────────────────────────

_ESS_TO_RATING: dict[str, str] = {
    "VERY_BULLISH": "STRONG_BUY",
    "BULLISH":      "BUY",
    "NEUTRAL":      "HOLD",
    "BEARISH":      "SELL",
    "VERY_BEARISH": "STRONG_SELL",
}

_ESS_TO_DIRECTION: dict[str, str] = {
    "VERY_BULLISH": "BULLISH",
    "BULLISH":      "BULLISH",
    "NEUTRAL":      "NEUTRAL",
    "BEARISH":      "BEARISH",
    "VERY_BEARISH": "BEARISH",
}


# ── Model ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FidelitySignal:
    """ESS-based Fidelity analyst opinion for a single symbol.

    Governance note: This is a transparency-only display artifact derived
    from the StarMine ESS data already in signal_snapshot.csv.  These fields
    are not read by any scoring, ranking, or deployment-queue function.
    """

    symbol: str
    ess_text: str                     # VERY_BULLISH / BULLISH / NEUTRAL / BEARISH / VERY_BEARISH
    ess_numeric: Optional[float]      # 1.0–5.0 normalised scale (None when not available)
    fidelity_rating: str              # Analyst-language label (STRONG_BUY … STRONG_SELL)
    fidelity_direction: str           # BULLISH / NEUTRAL / BEARISH
    refresh_date: str                 # snapshot_date from signal_snapshot
    coverage_domain: str              # STARMINE_COVERED / NON_STARMINE_ANALYST / UNKNOWN


# ── Label helpers ─────────────────────────────────────────────────────────────

def ess_text_to_rating(ess_text: Optional[str]) -> str:
    """Map ESS text label to analyst-language rating string."""
    return _ESS_TO_RATING.get((ess_text or "").upper().strip(), "UNKNOWN")


def ess_text_to_direction(ess_text: Optional[str]) -> str:
    """Map ESS text label to BULLISH / NEUTRAL / BEARISH direction."""
    return _ESS_TO_DIRECTION.get((ess_text or "").upper().strip(), "UNKNOWN")


# ── Loader ────────────────────────────────────────────────────────────────────

def load_fidelity_signals(signal_snapshot_path: Path) -> dict[str, FidelitySignal]:
    """Load Fidelity analyst signals from signal_snapshot.csv.

    For symbols with multiple rows (e.g. STARMINE_COVERED + NON_COVERED
    from the ESS dedup logic), prefers the STARMINE_COVERED row with
    a populated ess_text.  Returns a dict keyed by uppercase symbol.
    """
    rows: list[dict[str, str]] = []
    with open(signal_snapshot_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # Build best-row-per-symbol: prefer STARMINE_COVERED with non-empty ess_text
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        sym = (row.get("symbol") or "").strip().upper()
        if not sym:
            continue
        ess = (row.get("starmine_ess_text") or "").strip()
        domain = (row.get("coverage_domain") or "").strip()

        existing = best.get(sym)
        if existing is None:
            best[sym] = row
        else:
            existing_ess = (existing.get("starmine_ess_text") or "").strip()
            # Prefer row with non-empty ESS text
            if not existing_ess and ess:
                best[sym] = row
            # Among rows with ESS text, prefer STARMINE_COVERED
            elif existing_ess and ess and domain == "STARMINE_COVERED":
                best[sym] = row

    result: dict[str, FidelitySignal] = {}
    for sym, row in best.items():
        ess_text = (row.get("starmine_ess_text") or "").strip()
        if not ess_text:
            continue  # Skip symbols with no ESS coverage
        try:
            ess_numeric: Optional[float] = float(row.get("starmine_ess_numeric") or "")
        except (ValueError, TypeError):
            ess_numeric = None
        result[sym] = FidelitySignal(
            symbol=sym,
            ess_text=ess_text,
            ess_numeric=ess_numeric,
            fidelity_rating=ess_text_to_rating(ess_text),
            fidelity_direction=ess_text_to_direction(ess_text),
            refresh_date=(row.get("snapshot_date") or "").strip(),
            coverage_domain=(row.get("coverage_domain") or "").strip(),
        )

    return result


# ── Consensus matrix ──────────────────────────────────────────────────────────

def _zacks_score_to_direction(zacks_score: Optional[float]) -> str:
    """Map normalised Zacks score (1–5) to BULLISH / NEUTRAL / BEARISH."""
    if zacks_score is None:
        return "UNKNOWN"
    if zacks_score >= 4.0:
        return "BULLISH"
    if zacks_score >= 3.0:
        return "NEUTRAL"
    return "BEARISH"


def _consensus_label_to_direction(consensus_label: Optional[str]) -> str:
    """Map Yahoo ABR consensus label to BULLISH / NEUTRAL / BEARISH."""
    label = (consensus_label or "").upper()
    if label in ("STRONG_BUY", "BUY", "MODERATE_BUY"):
        return "BULLISH"
    if label == "HOLD":
        return "NEUTRAL"
    if label == "SELL":
        return "BEARISH"
    return "UNKNOWN"  # NO_CONSENSUS or missing


def compute_consensus_matrix(
    ess_text: Optional[str],
    consensus_label: Optional[str],
    zacks_score: Optional[float],
) -> dict:
    """Compute 3-signal consensus matrix classification.

    Signals:
      1. ESS (StarMine via Fidelity)          — ess_text
      2. Yahoo ABR consensus                   — consensus_label (from Phase 7.5J)
      3. Zacks normalised score                — zacks_score (1–5)

    Classifications:
      FULL_ALIGNMENT_BULLISH   — all available signals point bullish
      FULL_ALIGNMENT_BEARISH   — all available signals point bearish
      PARTIAL_ALIGNMENT        — majority (2 of 3 or 2 of 2) agree
      MAJOR_DIVERGENCE         — available signals strongly disagree
      INSUFFICIENT_DATA        — fewer than 2 signals available

    Governance: display-only — does not affect scoring, ranking, or deployment.
    """
    ess_dir   = ess_text_to_direction(ess_text)
    abr_dir   = _consensus_label_to_direction(consensus_label)
    zacks_dir = _zacks_score_to_direction(zacks_score)

    dirs = {
        "ess":   ess_dir,
        "yahoo": abr_dir,
        "zacks": zacks_dir,
    }

    known = [d for d in [ess_dir, abr_dir, zacks_dir] if d not in ("UNKNOWN",)]
    bullish_count  = known.count("BULLISH")
    bearish_count  = known.count("BEARISH")
    total_known    = len(known)

    if total_known < 2:
        classification = "INSUFFICIENT_DATA"
    elif bullish_count == total_known:
        classification = "FULL_ALIGNMENT_BULLISH"
    elif bearish_count == total_known:
        classification = "FULL_ALIGNMENT_BEARISH"
    elif bullish_count > bearish_count:
        classification = "PARTIAL_ALIGNMENT"
    elif bearish_count > bullish_count:
        classification = "PARTIAL_ALIGNMENT"
    else:
        # Equal bullish and bearish counts (e.g. 1 each with 1 neutral or 1/1)
        classification = "MAJOR_DIVERGENCE"

    return {
        "ess_direction":   ess_dir,
        "yahoo_direction": abr_dir,
        "zacks_direction": zacks_dir,
        "signals_available": total_known,
        "classification":  classification,
    }
