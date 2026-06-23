"""SCENARIO-01 — Portfolio Scenario Modeling.

Lightweight portfolio recomposition preview: given a set of sells and buys
(e.g. from a CRA proposal), estimates the resulting allocation map, ESS
coverage, and key concentration metrics — without a full PAR re-run.

Answers: "If I execute this rotation, what happens to my allocation?"

Governance: Read-only. No PAR artifacts, allocation targets, or scoring
engines are modified. The scenario is a display-only approximation.

Public API
----------
  scenario_preview(sells, buys, repo_root) → dict
  scenario_from_cra(repo_root)             → dict  (uses latest CRA proposal)
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_GOVERNANCE_NOTE = (
    "SCENARIO-01 is a lightweight approximation only. "
    "Projected metrics are estimates based on current holdings and proposed changes. "
    "A full PAR re-run is required for precise alignment scoring. "
    "No PAR artifacts, allocation targets, or scoring logic is modified."
)


def _load_latest_holdings(repo_root: Path) -> List[Dict]:
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


def _load_overlays(repo_root: Path) -> Dict[str, Dict]:
    runs = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not runs.exists():
        return {}
    dirs = sorted(
        (d for d in runs.iterdir() if d.is_dir() and (d / "security_overlays.csv").exists()),
        key=lambda d: d.stat().st_mtime,
    )
    if not dirs:
        return {}
    result = {}
    with (dirs[-1] / "security_overlays.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            sym = str(row.get("symbol") or "").strip().upper()
            if sym:
                result[sym] = row
    return result


def _load_alignment(repo_root: Path) -> List[Dict]:
    """Load alignment.csv from latest PAR run."""
    runs = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not runs.exists():
        return []
    dirs = sorted(
        (d for d in runs.iterdir() if d.is_dir() and (d / "alignment.csv").exists()),
        key=lambda d: d.stat().st_mtime,
    )
    if not dirs:
        return []
    with (dirs[-1] / "alignment.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(str(v or "").strip() or default)
    except (TypeError, ValueError):
        return default


def scenario_preview(
    sells: List[Dict],
    buys: List[Dict],
    repo_root: Path | str = ".",
) -> Dict:
    """
    Compute a scenario preview given proposed sells and buys.

    Args:
        sells: [{symbol, proceeds_usd}]  — positions to reduce
        buys:  [{symbol, amount_usd}]    — positions to increase

    Returns:
        Projected metrics: portfolio_mv, top5_concentration, ess_coverage,
        cash_pct, alignment_estimate, changed_weights.
    """
    root = Path(repo_root)

    holdings = _load_latest_holdings(root)
    overlays  = _load_overlays(root)
    alignment = _load_alignment(root)

    # Build current state
    by_sym: Dict[str, float] = {}
    for h in holdings:
        sym = str(h.get("symbol") or "").strip().upper()
        mv  = _safe_float(h.get("market_value"))
        if sym and mv > 0:
            by_sym[sym] = mv

    total_mv = sum(by_sym.values()) or 1.0

    # Apply sells
    sell_map = {str(s.get("symbol", "")).upper(): _safe_float(s.get("proceeds_usd", 0)) for s in sells}
    for sym, proceeds in sell_map.items():
        if sym in by_sym:
            by_sym[sym] = max(0.0, by_sym[sym] - proceeds)
        # Proceeds go to cash (represented as increased SPAXX)
        by_sym["SPAXX"] = by_sym.get("SPAXX", 0) + proceeds

    # Apply buys
    buy_map = {str(b.get("symbol", "")).upper(): _safe_float(b.get("amount_usd", 0)) for b in buys}
    for sym, amount in buy_map.items():
        by_sym[sym]    = by_sym.get(sym, 0) + amount
        by_sym["SPAXX"] = max(0, by_sym.get("SPAXX", 0) - amount)

    # Remove zero/negative positions
    by_sym = {s: mv for s, mv in by_sym.items() if mv > 0}
    new_total = sum(by_sym.values()) or 1.0

    # Compute new weights
    new_weights = {s: round(mv / new_total * 100, 4) for s, mv in by_sym.items()}

    # Top-5 concentration (excluding cash)
    equity_weights = sorted(
        [(s, w) for s, w in new_weights.items() if s not in ("SPAXX", "PENDING ACTIVITY")],
        key=lambda x: -x[1],
    )
    top5_sum = round(sum(w for _, w in equity_weights[:5]), 2)

    # Cash %
    cash_pct = round(new_weights.get("SPAXX", 0), 2)

    # ESS coverage estimate
    ess_covered = sum(
        1 for s in by_sym
        if s != "SPAXX" and overlays.get(s, {}).get("ess_score_text") not in (None, "", "UNKNOWN")
    )
    ess_total = sum(1 for s in by_sym if s != "SPAXX")
    ess_pct = round(ess_covered / ess_total * 100, 1) if ess_total else 0.0

    # Bullish signal count
    bullish_count = sum(
        1 for s in by_sym
        if overlays.get(s, {}).get("signal_direction") == "BULLISH"
    )

    # Weight changes
    changed_weights = []
    all_syms = set(by_sym.keys()) | set(sell_map.keys()) | set(buy_map.keys())
    for sym in sorted(all_syms):
        old_w = round(_safe_float(by_sym.get(sym, 0)) / total_mv * 100, 4) if sym in by_sym else (
            round((_safe_float({h.get("symbol",""):h for h in holdings}.get(sym, {}).get("market_value", 0)) / total_mv * 100), 4)
        )
        new_w = new_weights.get(sym, 0)
        delta = round(new_w - old_w, 4)
        if abs(delta) > 0.01:
            changed_weights.append({
                "symbol":     sym,
                "old_weight": old_w,
                "new_weight": new_w,
                "delta_pp":   delta,
                "action":     "SELL" if sym in sell_map else ("BUY" if sym in buy_map else "INDIRECT"),
            })

    changed_weights.sort(key=lambda x: abs(x["delta_pp"]), reverse=True)

    # Simple alignment estimate (based on current alignment data)
    # We approximate by comparing drift changes for affected nodes
    target_by_node: Dict[str, float] = {}
    for row in alignment:
        nk = str(row.get("node_key") or "").strip()
        tp = _safe_float(row.get("tactical_target_pct") or row.get("target_pct"))
        if nk and tp > 0:
            target_by_node[nk] = tp

    current_overall = None
    from pathlib import Path as _P
    try:
        for run_path in sorted(
            (d for d in (root / "data" / "portfolio_ingestion" / "analysis_runs").iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
        )[-1:]:
            meta = json.loads((run_path / "run_metadata.json").read_text(encoding="utf-8"))
            current_overall = meta.get("overall_alignment_score")
    except Exception:
        pass

    return {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "is_estimate":     True,
        "portfolio_mv":    round(new_total, 2),
        "cash_pct":        cash_pct,
        "top5_concentration_pct": top5_sum,
        "ess_coverage_pct": ess_pct,
        "bullish_count":   bullish_count,
        "position_count":  len([s for s in by_sym if s != "SPAXX"]),
        "changed_weights": changed_weights[:20],
        "current_alignment_score": current_overall,
        "alignment_note":  (
            "Alignment score estimate requires full PAR re-run. "
            f"Current score: {current_overall:.2f}" if current_overall else
            "Alignment score not available."
        ),
        "governance_note": _GOVERNANCE_NOTE,
    }


def scenario_from_cra(repo_root: Path | str = ".") -> Dict:
    """Build a scenario preview from the latest saved CRA draft/proposal."""
    root  = Path(repo_root)

    # Try to load latest CRA proposal
    try:
        cra_path = root / "data" / "portfolio_ingestion" / "cra_draft.json"
        if not cra_path.exists():
            # Try manifest
            manifest = root / "data" / "portfolio_ingestion" / "manifest.json"
            if manifest.exists():
                m = json.loads(manifest.read_text(encoding="utf-8"))
                portfolios = m.get("portfolios") or []
                if portfolios:
                    run_id = (portfolios[0].get("analysis_runs") or [{}])[-1].get("run_id", "")
                    cra_path = root / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "cra_proposal.json"
    except Exception:
        cra_path = None

    if not cra_path or not cra_path.exists():
        return {
            "status": "NO_CRA_PROPOSAL",
            "message": "No CRA proposal found. Run Capital Rotation Advisor first.",
            "governance_note": _GOVERNANCE_NOTE,
        }

    try:
        proposal = json.loads(cra_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"status": "ERROR", "error": str(e), "governance_note": _GOVERNANCE_NOTE}

    sources     = [s for s in proposal.get("sources", []) if not s.get("blocked_by_policy")]
    deployments = proposal.get("deployments", [])

    sells = [{"symbol": s["symbol"], "proceeds_usd": s.get("estimated_proceeds", 0)} for s in sources]
    buys  = [{"symbol": d["symbol"], "amount_usd": d.get("suggested_amount", 0)} for d in deployments]

    preview = scenario_preview(sells, buys, root)
    preview["source_proposal_id"] = proposal.get("proposal_id", "")
    preview["sell_count"]  = len(sells)
    preview["buy_count"]   = len(buys)
    return preview
