"""SIGNAL-GOV-02A: Signal Conflict Classifier.

Classifies analyst disagreement and signal conflict for symbols based on
available signal data (FMP Street consensus, Zacks, Danelfin, Yahoo ABR).

Produces advisory badges only.  No scores, rankings, or recommendations
are changed.  Output is informational governance visibility.

Badge types:
  CONFLICTING_SIGNAL         – bullish and bearish signals coexist
  HIGH_ANALYST_DISAGREEMENT  – high-accuracy named sources materially disagree
                               (requires operator annotation; auto-detected
                               when sell_ratio >= configured threshold AND
                               any single source is explicitly sell-rated)
  HIGH_HOLD_RATIO            – majority of opinions are Hold/Neutral
  HOLD_CONSENSUS             – aggregate consensus label is HOLD or SELL
  SIGNIFICANT_CONFLICT       – sell ratio exceeds configured threshold
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"

_DEFAULT_SIGNIFICANT_SELL_RATIO_PCT = 15.0
_DEFAULT_HIGH_HOLD_RATIO_PCT = 50.0

# Zacks score scale: 5=Strong Buy, 4=Buy, 3=Hold, 2=Sell, 1=Strong Sell
_ZACKS_BULLISH_MIN = 4.0
_ZACKS_BEARISH_MAX = 2.0

# Danelfin raw scale: 7–10 = bullish, 4–6 = neutral, 1–3 = bearish
_DANELFIN_BULLISH_MIN = 7.0
_DANELFIN_BEARISH_MAX = 3.0

# Yahoo ABR: 1.0=Strong Buy → 5.0=Strong Sell; ≤2.5 bullish, ≥3.5 bearish
_YAHOO_BULLISH_MAX = 2.5
_YAHOO_BEARISH_MIN = 3.5


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SignalConflict:
    """A single advisory conflict badge for a symbol."""
    type: str           # CONFLICTING_SIGNAL | HIGH_ANALYST_DISAGREEMENT | ...
    severity: str       # WARN | INFO
    description: str    # human-readable one-liner

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "severity": self.severity, "description": self.description}


@dataclass
class SignalInputs:
    """Parsed signal inputs for a single symbol."""
    symbol: str
    # FMP Street aggregate
    buy_count: int = 0
    hold_count: int = 0
    sell_count: int = 0
    total_analysts: int = 0
    consensus_label: str = ""   # BUY | HOLD | SELL
    # Individual signals
    zacks_score: float | None = None    # 1–5
    danelfin_raw: float | None = None   # 1–10
    yahoo_abr: float | None = None      # 1.0–5.0
    # Operator annotation for named-source disagreement
    operator_annotated_disagreement: bool = False


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _sell_ratio_pct(inputs: SignalInputs) -> float:
    if inputs.total_analysts <= 0:
        return 0.0
    return (inputs.sell_count / inputs.total_analysts) * 100.0


def _hold_ratio_pct(inputs: SignalInputs) -> float:
    if inputs.total_analysts <= 0:
        return 0.0
    return (inputs.hold_count / inputs.total_analysts) * 100.0


def _has_bullish_source(inputs: SignalInputs) -> bool:
    if inputs.buy_count > 0:
        return True
    if inputs.zacks_score is not None and inputs.zacks_score >= _ZACKS_BULLISH_MIN:
        return True
    if inputs.danelfin_raw is not None and inputs.danelfin_raw >= _DANELFIN_BULLISH_MIN:
        return True
    if inputs.yahoo_abr is not None and inputs.yahoo_abr <= _YAHOO_BULLISH_MAX:
        return True
    return False


def _has_bearish_source(inputs: SignalInputs) -> bool:
    if inputs.sell_count > 0:
        return True
    if inputs.zacks_score is not None and inputs.zacks_score <= _ZACKS_BEARISH_MAX:
        return True
    if inputs.danelfin_raw is not None and inputs.danelfin_raw <= _DANELFIN_BEARISH_MAX:
        return True
    if inputs.yahoo_abr is not None and inputs.yahoo_abr >= _YAHOO_BEARISH_MIN:
        return True
    return False


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------

def classify_signal_conflicts(
    inputs: SignalInputs,
    significant_sell_ratio_pct: float = _DEFAULT_SIGNIFICANT_SELL_RATIO_PCT,
    high_hold_ratio_pct: float = _DEFAULT_HIGH_HOLD_RATIO_PCT,
) -> list[SignalConflict]:
    """Classify all applicable conflict badges for the given signal inputs.

    Returns a list of SignalConflict instances.  An empty list means no
    advisory badges apply.  Results are ordered by severity: WARN before INFO.
    """
    badges: list[SignalConflict] = []
    sell_ratio = _sell_ratio_pct(inputs)
    hold_ratio = _hold_ratio_pct(inputs)

    # ── SIGNIFICANT_CONFLICT — sell ratio ≥ threshold ──────────────────────
    if sell_ratio >= significant_sell_ratio_pct and inputs.total_analysts > 0:
        badges.append(SignalConflict(
            type="SIGNIFICANT_CONFLICT",
            severity=SEVERITY_WARN,
            description=(
                f"{inputs.sell_count} of {inputs.total_analysts} analysts "
                f"({sell_ratio:.1f}%) recommend Sell — exceeds "
                f"{significant_sell_ratio_pct:.0f}% threshold."
            ),
        ))

    # ── HIGH_ANALYST_DISAGREEMENT — operator annotation OR auto-detect ─────
    # Auto-detect: sell_ratio >= 10% AND at least one bullish source present
    auto_disagreement = (
        sell_ratio >= 10.0
        and inputs.buy_count > 0
        and inputs.sell_count > 0
        and inputs.total_analysts >= 5
    )
    if inputs.operator_annotated_disagreement or auto_disagreement:
        # Don't double-badge: only add if not already SIGNIFICANT_CONFLICT
        if not any(b.type == "SIGNIFICANT_CONFLICT" for b in badges):
            badges.append(SignalConflict(
                type="HIGH_ANALYST_DISAGREEMENT",
                severity=SEVERITY_WARN,
                description=(
                    "High-confidence analyst sources hold materially different "
                    "views on this security." if inputs.operator_annotated_disagreement
                    else (
                        f"Named analysts disagree: {inputs.buy_count} Buy vs "
                        f"{inputs.sell_count} Sell among {inputs.total_analysts} covering analysts."
                    )
                ),
            ))

    # ── CONFLICTING_SIGNAL — bullish + bearish coexist ──────────────────────
    # Only when not already flagged at higher level
    already_flagged = any(
        b.type in ("SIGNIFICANT_CONFLICT", "HIGH_ANALYST_DISAGREEMENT") for b in badges
    )
    if not already_flagged and _has_bullish_source(inputs) and _has_bearish_source(inputs):
        badges.append(SignalConflict(
            type="CONFLICTING_SIGNAL",
            severity=SEVERITY_WARN,
            description=(
                "At least one bullish and one bearish source are present. "
                "Signal evidence is mixed."
            ),
        ))

    # ── HOLD_CONSENSUS — aggregate label is HOLD ────────────────────────────
    label = (inputs.consensus_label or "").upper()
    if label in ("HOLD", "SELL") and inputs.total_analysts > 0:
        badges.append(SignalConflict(
            type="HOLD_CONSENSUS",
            severity=SEVERITY_INFO,
            description=(
                f"Street consensus is {label} across "
                f"{inputs.total_analysts} analysts."
            ),
        ))
    # ── HIGH_HOLD_RATIO — majority opinion is Hold ──────────────────────────
    elif (
        hold_ratio >= high_hold_ratio_pct
        and inputs.total_analysts > 0
        and label not in ("HOLD", "SELL")
    ):
        badges.append(SignalConflict(
            type="HIGH_HOLD_RATIO",
            severity=SEVERITY_INFO,
            description=(
                f"{inputs.hold_count} of {inputs.total_analysts} analysts "
                f"({hold_ratio:.0f}%) hold a Hold/Neutral view."
            ),
        ))

    return badges


# ---------------------------------------------------------------------------
# Data loading utilities
# ---------------------------------------------------------------------------

def _load_fmp_index(repo_root: Path) -> dict[str, dict[str, Any]]:
    fmp_path = repo_root / "data/signals/fmp/latest/latest_fmp_grades_consensus.csv"
    idx: dict[str, dict[str, Any]] = {}
    if not fmp_path.exists():
        return idx
    for row in csv.DictReader(fmp_path.open(encoding="utf-8")):
        sym = (row.get("symbol") or "").strip().upper()
        if sym:
            idx[sym] = row
    return idx


def _load_zacks_index(repo_root: Path) -> dict[str, float]:
    zacks_path = repo_root / "data/signals/zacks/latest_zacks.csv"
    idx: dict[str, float] = {}
    if not zacks_path.exists():
        return idx
    for row in csv.DictReader(zacks_path.open(encoding="utf-8")):
        sym = (row.get("symbol") or "").strip().upper()
        raw = row.get("zacks_score") or ""
        try:
            idx[sym] = float(raw)
        except (ValueError, TypeError):
            pass
    return idx


def _load_danelfin_index(repo_root: Path) -> dict[str, float]:
    dan_path = repo_root / "data/signals/danelfin/latest_danelfin.csv"
    idx: dict[str, float] = {}
    if not dan_path.exists():
        return idx
    for row in csv.DictReader(dan_path.open(encoding="utf-8")):
        sym = (row.get("symbol") or "").strip().upper()
        raw = row.get("danelfin_raw") or ""
        try:
            idx[sym] = float(raw)
        except (ValueError, TypeError):
            pass
    return idx


def _load_yahoo_index(repo_root: Path) -> dict[str, float]:
    yahoo_path = repo_root / "data/signals/yahoo/latest_yahoo_supplemental.csv"
    idx: dict[str, float] = {}
    if not yahoo_path.exists():
        return idx
    for row in csv.DictReader(yahoo_path.open(encoding="utf-8")):
        sym = (row.get("symbol") or "").strip().upper()
        raw = row.get("abr") or ""
        try:
            idx[sym] = float(raw)
        except (ValueError, TypeError):
            pass
    return idx


def _load_operator_annotations(repo_root: Path) -> set[str]:
    """Load operator-annotated HIGH_ANALYST_DISAGREEMENT symbols.

    Reads from config/signal_conflict_annotations.csv if present.
    File format: symbol,reason  (header row required)
    """
    ann_path = repo_root / "config/signal_conflict_annotations.csv"
    syms: set[str] = set()
    if not ann_path.exists():
        return syms
    for row in csv.DictReader(ann_path.open(encoding="utf-8")):
        sym = (row.get("symbol") or "").strip().upper()
        if sym:
            syms.add(sym)
    return syms


def build_signal_inputs(
    symbol: str,
    fmp_idx: dict[str, dict[str, Any]],
    zacks_idx: dict[str, float],
    danelfin_idx: dict[str, float],
    yahoo_idx: dict[str, float],
    operator_annotations: set[str],
) -> SignalInputs:
    """Build a SignalInputs from pre-loaded signal indices."""
    sym = symbol.upper()
    fmp = fmp_idx.get(sym, {})

    def _int(v: Any) -> int:
        try:
            return int(float(v or 0))
        except (ValueError, TypeError):
            return 0

    return SignalInputs(
        symbol=sym,
        buy_count=_int(fmp.get("buy_count")) + _int(fmp.get("strong_buy_count")),
        hold_count=_int(fmp.get("hold_count")),
        sell_count=_int(fmp.get("sell_count")) + _int(fmp.get("strong_sell_count")),
        total_analysts=_int(fmp.get("total_analysts")),
        consensus_label=str(fmp.get("consensus_label") or "").strip().upper(),
        zacks_score=zacks_idx.get(sym),
        danelfin_raw=danelfin_idx.get(sym),
        yahoo_abr=yahoo_idx.get(sym),
        operator_annotated_disagreement=(sym in operator_annotations),
    )


# ---------------------------------------------------------------------------
# Public convenience API
# ---------------------------------------------------------------------------

def get_conflicts_for_symbols(
    symbols: list[str],
    repo_root: Path | str = ".",
    config: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Return conflict badge dicts keyed by symbol (uppercase).

    Args:
        symbols: list of ticker symbols to classify
        repo_root: repository root path
        config: optional config dict; may contain
                signal_conflict.significant_conflict_sell_ratio_pct

    Returns:
        { "VRT": [], "NUE": [{"type": "CONFLICTING_SIGNAL", "severity": "WARN", "description": "..."}] }
    """
    repo_root = Path(repo_root)
    cfg = (config or {}).get("signal_conflict", {})
    sell_ratio_threshold = float(
        cfg.get("significant_conflict_sell_ratio_pct", _DEFAULT_SIGNIFICANT_SELL_RATIO_PCT)
    )

    fmp = _load_fmp_index(repo_root)
    zacks = _load_zacks_index(repo_root)
    danelfin = _load_danelfin_index(repo_root)
    yahoo = _load_yahoo_index(repo_root)
    annotations = _load_operator_annotations(repo_root)

    result: dict[str, list[dict[str, str]]] = {}
    for sym in symbols:
        sym_up = sym.upper()
        inputs = build_signal_inputs(sym_up, fmp, zacks, danelfin, yahoo, annotations)
        conflicts = classify_signal_conflicts(inputs, significant_sell_ratio_pct=sell_ratio_threshold)
        result[sym_up] = [c.to_dict() for c in conflicts]
    return result
