"""DISLOCATION-03 — Security-Level Conflict Alpha Insights.

Given a security's current signal state (ESS direction, Zacks direction,
analyst consensus direction), derives the conflict pattern and looks up
its historical alpha from the DISLOCATION-02 alpha report.

Surfaces conflict alpha intelligence directly on security profiles so
operators see it at the point of decision, not only inside Conflict Review.

Data sources (read-only):
  - data/analysis/dislocation/conflict_alpha_report.json  (DISLOCATION-02)
  - Latest PAR analysis run: security_overlays.csv + analyst_consensus

Governance:
  - Read-only. No CW-DAS, ESS, UCF, CRA, Replay, PAP, or governance changes.
  - Display / explainability only.

Public API
----------
  derive_security_conflict_alpha(symbol, ess_dir, zacks_dir, yahoo_dir, repo_root)
      → SecurityConflictAlpha | None

  batch_security_conflict_alpha(overlays, analyst_data, repo_root)
      → dict[symbol, SecurityConflictAlpha]

  security_alpha_summary(repo_root)
      → dict   (API payload for /api/conflict-review/security-alpha-summary)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ── Re-use pattern detection from ISSUE-12D ───────────────────────────────────
from src.sih.signal_conflict_review import (
    _analyst_direction as _analyst_dir,
    _ess_direction as _ess_dir_from_numeric,
    _signal_pattern,
)

_ALPHA_REPORT_PATH = "data/analysis/dislocation/conflict_alpha_report.json"

# ESS text → direction (without needing the numeric score)
_ESS_TEXT_TO_DIR = {
    "VERY_BULLISH": "BULLISH",
    "BULLISH":      "BULLISH",
    "NEUTRAL":      "NEUTRAL",
    "BEARISH":      "BEARISH",
    "VERY_BEARISH": "BEARISH",
}

# Zacks normalized score (1–5 ascending) → direction
def _zacks_dir(score) -> str:
    if score is None:
        return "NO_DATA"
    try:
        z = float(score)
    except (TypeError, ValueError):
        return "NO_DATA"
    if z >= 4.0:
        return "BULLISH"    # Rank 1–2 = Strong Buy/Buy
    if z <= 2.0:
        return "BEARISH"    # Rank 4–5 = Sell/Strong Sell
    return "NEUTRAL"


# Yahoo ABR / consensus_label → direction
def _yahoo_dir(consensus_label: str | None) -> str:
    if not consensus_label:
        return "NO_DATA"
    lab = consensus_label.upper()
    if lab in ("STRONG_BUY", "BUY", "MODERATE_BUY"):
        return "BULLISH"
    if lab in ("HOLD",):
        return "NEUTRAL"
    if lab in ("SELL", "STRONG_SELL", "MODERATE_SELL"):
        return "BEARISH"
    return "NO_DATA"


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SecurityConflictAlpha:
    symbol:                str
    ess_direction:         str         # BULLISH | NEUTRAL | BEARISH | NO_DATA
    zacks_direction:       str         # BULLISH | NEUTRAL | BEARISH | NO_DATA
    yahoo_direction:       str         # BULLISH | NEUTRAL | BEARISH | NO_DATA
    signal_pattern:        str         # pattern key
    pattern_label:         str         # human-readable
    is_conflict:           bool

    # Alpha data (None if pattern not in alpha report)
    alpha_class:           Optional[str]    # ALPHA_LEADER | ALPHA_NEUTRAL | ALPHA_LAGGARD
    excess_return_pct:     Optional[float]
    avg_return_30d_pct:    Optional[float]
    win_rate_pct:          Optional[float]
    t_statistic:           Optional[float]
    significance:          Optional[str]    # NOTEWORTHY | SUGGESTIVE | WEAK | INSUFFICIENT_DATA
    observations:          int
    insight:               str             # plain-language insight

    def to_dict(self) -> Dict:
        return {
            "symbol":              self.symbol,
            "ess_direction":       self.ess_direction,
            "zacks_direction":     self.zacks_direction,
            "yahoo_direction":     self.yahoo_direction,
            "signal_pattern":      self.signal_pattern,
            "pattern_label":       self.pattern_label,
            "is_conflict":         self.is_conflict,
            "alpha_class":         self.alpha_class,
            "excess_return_pct":   self.excess_return_pct,
            "avg_return_30d_pct":  self.avg_return_30d_pct,
            "win_rate_pct":        self.win_rate_pct,
            "t_statistic":         self.t_statistic,
            "significance":        self.significance,
            "observations":        self.observations,
            "insight":             self.insight,
        }


# ── Conflict pattern constants (mirrors signal_conflict_review) ───────────────

_CONFLICT_PATTERNS = frozenset({
    "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
    "ESS_BULLISH_ANALYST_SKEPTICAL",
    "ESS_BULLISH_ANALYST_MIXED",
    "ESS_BEARISH_ANALYST_MAJORITY_BULLISH",
    "ESS_BEARISH_ANALYST_MIXED",
    "ESS_NEUTRAL_ANALYST_BULLISH",
    "ESS_NEUTRAL_ANALYST_BEARISH",
    "ESS_NEUTRAL_ANALYST_MIXED",
})

_PATTERN_LABELS = {
    "ESS_BULLISH_ANALYST_MAJORITY_BEARISH": "ESS Buy / Analyst Sell",
    "ESS_BULLISH_ANALYST_SKEPTICAL":        "ESS Buy / Analysts Skeptical",
    "ESS_BULLISH_ANALYST_FULL_AGREE":       "ESS Buy / All Agree Buy",
    "ESS_BULLISH_ANALYST_MIXED":            "ESS Buy / Analysts Mixed",
    "ESS_BEARISH_ANALYST_MAJORITY_BULLISH": "ESS Sell / Analyst Buy",
    "ESS_BEARISH_ANALYST_FULL_AGREE":       "ESS Sell / All Agree Sell",
    "ESS_BEARISH_ANALYST_MIXED":            "ESS Sell / Analysts Mixed",
    "ESS_NEUTRAL_ANALYST_BULLISH":          "ESS Neutral / Analysts Buy",
    "ESS_NEUTRAL_ANALYST_BEARISH":          "ESS Neutral / Analysts Sell",
    "ESS_NEUTRAL_ANALYST_MIXED":            "ESS Neutral / Analysts Mixed",
}


# ── Alpha report loader ────────────────────────────────────────────────────────

def _load_alpha_index(repo_root: Path) -> Dict[str, Dict]:
    """Load conflict_alpha_report.json and return {pattern → pattern_dict}."""
    path = repo_root / _ALPHA_REPORT_PATH
    if not path.exists():
        # Lazy-generate
        try:
            from src.sih.conflict_alpha_analysis import conflict_alpha_report
            report = conflict_alpha_report(repo_root)
        except Exception:
            return {}
    else:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {p["signal_pattern"]: p for p in report.get("patterns", [])}


# ── Core derivation ────────────────────────────────────────────────────────────

def derive_security_conflict_alpha(
    symbol: str,
    ess_text: Optional[str],
    ess_numeric: Optional[float],
    zacks_score: Optional[float],
    yahoo_consensus: Optional[str],
    alpha_index: Dict[str, Dict],
) -> Optional[SecurityConflictAlpha]:
    """
    Derive a SecurityConflictAlpha for a single security.

    Args:
        symbol:          Ticker symbol.
        ess_text:        e.g. "VERY_BULLISH" from overlay (preferred).
        ess_numeric:     Numeric ESS score 0–10 (fallback if ess_text missing).
        zacks_score:     Normalized 1–5 (1=StrongBuy, 5=StrongSell).
        yahoo_consensus: e.g. "STRONG_BUY", "HOLD", "SELL".
        alpha_index:     Pre-loaded {pattern → alpha data} from alpha report.

    Returns:
        SecurityConflictAlpha if pattern can be determined, else None.
    """
    # Derive ESS direction
    if ess_text and ess_text.upper() in _ESS_TEXT_TO_DIR:
        ess_direction = _ESS_TEXT_TO_DIR[ess_text.upper()]
    elif ess_numeric is not None:
        ess_direction = _ess_dir_from_numeric(ess_numeric)
    else:
        ess_direction = "NO_DATA"

    # Derive analyst directions — use Zacks + Yahoo as proxies for
    # the multi-analyst signals the ESS archive provided
    zacks_direction = _zacks_dir(zacks_score)
    yahoo_direction = _yahoo_dir(yahoo_consensus)

    # Map Yahoo to the "jefferson_direction" slot and Zacks to "zacks_direction"
    # (best approximation given live data availability)
    pattern = _signal_pattern(ess_direction, zacks_direction, yahoo_direction, "NO_DATA")

    if pattern in ("NO_ESS_DATA", "ESS_BULLISH_NO_ANALYST_DATA",
                   "ESS_BEARISH_NO_ANALYST_DATA", "ESS_NEUTRAL_NO_ANALYST_DATA"):
        # Insufficient signal data
        return None

    is_conflict = pattern in _CONFLICT_PATTERNS
    label = _PATTERN_LABELS.get(pattern, pattern.replace("_", " "))

    # Alpha lookup
    alpha_data = alpha_index.get(pattern, {})
    alpha_class        = alpha_data.get("alpha_class")
    excess_return_pct  = alpha_data.get("excess_return_pct")
    avg_return_30d_pct = alpha_data.get("avg_return_30d_pct")
    win_rate_pct       = alpha_data.get("win_rate_pct")
    t_statistic        = alpha_data.get("t_statistic")
    significance       = alpha_data.get("significance", "INSUFFICIENT_DATA")
    observations       = alpha_data.get("observations", 0)

    # Build insight
    insight = _build_insight(
        symbol, pattern, label, is_conflict,
        alpha_class, excess_return_pct, win_rate_pct, significance,
        ess_direction,
    )

    return SecurityConflictAlpha(
        symbol=symbol,
        ess_direction=ess_direction,
        zacks_direction=zacks_direction,
        yahoo_direction=yahoo_direction,
        signal_pattern=pattern,
        pattern_label=label,
        is_conflict=is_conflict,
        alpha_class=alpha_class,
        excess_return_pct=excess_return_pct,
        avg_return_30d_pct=avg_return_30d_pct,
        win_rate_pct=win_rate_pct,
        t_statistic=t_statistic,
        significance=significance,
        observations=observations,
        insight=insight,
    )


def _build_insight(
    symbol: str, pattern: str, label: str, is_conflict: bool,
    alpha_class: Optional[str], excess_return_pct: Optional[float],
    win_rate_pct: Optional[float], significance: Optional[str],
    ess_direction: str,
) -> str:
    if not alpha_class or excess_return_pct is None:
        if is_conflict:
            return (
                f"{symbol} shows a {label} signal conflict. "
                "Historical alpha data not available for this pattern."
            )
        return f"{symbol}: signals are aligned — no active conflict."

    excess_str = f"{excess_return_pct:+.1f}pp"
    win_str    = f"{win_rate_pct:.0f}%" if win_rate_pct is not None else "—"
    sig_lower  = (significance or "").lower()

    if alpha_class == "ALPHA_LEADER":
        return (
            f"{symbol} shows a {label} conflict pattern. "
            f"Historically this pattern generated {excess_str} excess return vs the universe median "
            f"({win_str} above-median rate, {sig_lower} evidence). "
            "This is historically a favorable disagreement pattern — "
            "ESS signal has tended to be the more reliable indicator."
        )
    if alpha_class == "ALPHA_LAGGARD":
        return (
            f"{symbol} shows a {label} conflict pattern. "
            f"Historically this pattern underperformed by {excess_str} vs the universe median "
            f"({win_str} above-median rate, {sig_lower} evidence). "
            "This is historically an unfavorable disagreement pattern — "
            "analyst consensus may deserve additional weight."
        )
    return (
        f"{symbol} shows a {label} conflict pattern. "
        f"Historically this pattern produced {excess_str} excess return vs universe median. "
        "No material alpha advantage or disadvantage identified. "
        "Informational only — operator judgment required."
    )


# ── Batch derivation ──────────────────────────────────────────────────────────

def batch_security_conflict_alpha(
    overlays: List[Dict],
    analyst_data: Dict[str, Dict],
    repo_root: Path,
) -> Dict[str, SecurityConflictAlpha]:
    """
    Derive SecurityConflictAlpha for every security in the overlay list.

    Args:
        overlays:     List of security_overlays dicts from PAR run.
        analyst_data: analyst_consensus_by_symbol dict (keyed uppercase symbol).
        repo_root:    Repository root path.

    Returns:
        Dict[uppercase symbol → SecurityConflictAlpha] for securities where
        a pattern can be determined.
    """
    alpha_index = _load_alpha_index(repo_root)
    result: Dict[str, SecurityConflictAlpha] = {}

    for ov in overlays:
        symbol = str(ov.get("symbol") or "").strip().upper()
        if not symbol:
            continue

        ess_text    = str(ov.get("ess_score_text") or "").strip() or None
        ess_numeric = _safe_float(ov.get("starmine_ess_numeric") or ov.get("ess_numeric"))
        zacks_score = _safe_float(ov.get("zacks_rating"))
        ac          = analyst_data.get(symbol, {})
        yahoo_cons  = str(ac.get("consensus_label") or "").strip() or None

        sca = derive_security_conflict_alpha(
            symbol, ess_text, ess_numeric, zacks_score, yahoo_cons, alpha_index
        )
        if sca is not None:
            result[symbol] = sca

    return result


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── Public API functions ───────────────────────────────────────────────────────

def get_security_conflict_alpha(
    symbol: str,
    repo_root: Path | str = ".",
    ess_text: Optional[str] = None,
    ess_numeric: Optional[float] = None,
    zacks_score: Optional[float] = None,
    yahoo_consensus: Optional[str] = None,
) -> Dict:
    """
    API handler for GET /api/conflict-review/security-alpha/<symbol>.
    Signals can be passed as query params; if absent, the latest PAR run is consulted.
    """
    root = Path(repo_root)
    alpha_index = _load_alpha_index(root)

    # If signals not provided, try to load from latest PAR analysis run
    if ess_text is None and ess_numeric is None:
        ov, ac = _load_latest_signals(symbol.upper(), root)
        if ov:
            ess_text    = str(ov.get("ess_score_text") or "").strip() or None
            ess_numeric = _safe_float(ov.get("zacks_rating"))  # fallback unused
            zacks_score = _safe_float(ov.get("zacks_rating"))
        if ac:
            yahoo_consensus = str(ac.get("consensus_label") or "").strip() or None

    sca = derive_security_conflict_alpha(
        symbol.upper(), ess_text, ess_numeric, zacks_score, yahoo_consensus, alpha_index
    )
    if sca is None:
        return {
            "symbol": symbol.upper(),
            "error": "Insufficient signal data to determine conflict pattern.",
        }
    return sca.to_dict()


def security_alpha_summary(repo_root: Path | str = ".") -> Dict:
    """
    API handler for GET /api/conflict-review/security-alpha-summary.
    Returns alpha insights for all securities in the latest PAR run.
    """
    root = Path(repo_root)
    overlays, analyst_data = _load_latest_par_data(root)

    if not overlays:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "NO_PAR_DATA",
            "securities": {},
        }

    alphas = batch_security_conflict_alpha(overlays, analyst_data, root)

    # Build summary counts
    leaders  = [s for s in alphas.values() if s.alpha_class == "ALPHA_LEADER"]
    laggards = [s for s in alphas.values() if s.alpha_class == "ALPHA_LAGGARD"]
    conflicts = [s for s in alphas.values() if s.is_conflict]

    return {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "status":         "OK",
        "total_analyzed": len(alphas),
        "conflict_count": len(conflicts),
        "leader_count":   len(leaders),
        "laggard_count":  len(laggards),
        "leaders":        [s.to_dict() for s in sorted(leaders,  key=lambda x: -(x.excess_return_pct or 0))],
        "laggards":       [s.to_dict() for s in sorted(laggards, key=lambda x:  (x.excess_return_pct or 0))],
        "securities":     {sym: sca.to_dict() for sym, sca in alphas.items()},
    }


# ── PAR data loaders ──────────────────────────────────────────────────────────

def _load_latest_par_data(repo_root: Path):
    """Load security_overlays + analyst_consensus from latest PAR run."""
    import csv as _csv
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not par_dir.exists():
        return [], {}

    # Find latest run by manifest
    manifest = repo_root / "data" / "portfolio_ingestion" / "manifest.json"
    latest_run_dir = None
    if manifest.exists():
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
            portfolios = m.get("portfolios") or []
            if portfolios:
                runs = portfolios[0].get("analysis_runs") or []
                if runs:
                    latest_run_id = runs[-1].get("run_id")
                    if latest_run_id:
                        latest_run_dir = par_dir / latest_run_id
        except (OSError, json.JSONDecodeError):
            pass

    if latest_run_dir is None:
        # Fall back to last-modified directory
        dirs = sorted(
            (d for d in par_dir.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
        )
        if dirs:
            latest_run_dir = dirs[-1]

    if not latest_run_dir:
        return [], {}

    # Read security_overlays.csv
    overlays = []
    ov_path = latest_run_dir / "security_overlays.csv"
    if ov_path.exists():
        with ov_path.open(encoding="utf-8", newline="") as f:
            overlays = list(_csv.DictReader(f))

    # Read analyst_consensus.json
    analyst_data: Dict[str, Dict] = {}
    ac_path = latest_run_dir / "analyst_consensus.json"
    if ac_path.exists():
        try:
            raw = json.loads(ac_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for entry in raw:
                    sym = str(entry.get("symbol") or "").upper()
                    if sym:
                        analyst_data[sym] = entry
            elif isinstance(raw, dict):
                analyst_data = {k.upper(): v for k, v in raw.items()}
        except (OSError, json.JSONDecodeError):
            pass

    return overlays, analyst_data


def _load_latest_signals(symbol: str, repo_root: Path):
    """Load overlay + analyst data for a single symbol from latest PAR."""
    overlays, analyst_data = _load_latest_par_data(repo_root)
    ov = next((o for o in overlays if str(o.get("symbol","")).upper() == symbol), None)
    ac = analyst_data.get(symbol)
    return ov, ac
