"""Phase 7.4A — Conviction Capital Deployment Analysis.

Single-pass script: reads persisted run data, computes all six analysis steps,
writes conviction_capital_deployment_report.md.

Analysis only — no trade instructions, no execution sizing.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import sys
from pathlib import Path
from typing import Optional

# ─── Config ──────────────────────────────────────────────────────────────────

PREFERRED_RUNS = [
    "PAR-20260530-3A136D4F",
    "PAR-20260530-8FA7AE53",
    "PAR-20260530-7B861236",
]
RUN_ROOT = Path("data/portfolio_ingestion/analysis_runs")
MANDATE = "CONCENTRATED_ALPHA"

# CONCENTRATED_ALPHA target cash band
TARGET_CASH_PCT = 3.0   # midpoint of 2-5% band
MAX_CASH_PCT    = 5.0
MIN_CASH_PCT    = 2.0   # floor

# Concentration guardrails
MAX_POSITION_PCT  = 8.0   # ceiling - concern above this
WARN_POSITION_PCT = 6.0   # soft-warn threshold

# Focus symbols for concentration analysis
_FOCUS_SYMBOLS = {"VRT", "DELL", "LRCX", "AEIS", "MU"}


# ─── Data loading ─────────────────────────────────────────────────────────────

def _pick_run() -> str:
    for run_id in PREFERRED_RUNS:
        if (RUN_ROOT / run_id).exists():
            return run_id
    dirs = sorted(
        [d.name for d in RUN_ROOT.iterdir() if d.is_dir()],
        key=lambda n: (RUN_ROOT / n / "recommendations.json").stat().st_mtime
        if (RUN_ROOT / n / "recommendations.json").exists() else 0,
        reverse=True,
    )
    if dirs:
        return dirs[0]
    raise FileNotFoundError("No analysis run found.")


def _load_csv_dicts(path: Path) -> list[dict]:
    return list(csv.DictReader(open(path)))


def _load_json(path: Path) -> object:
    return json.load(open(path))


def _load_replay_index() -> set[str]:
    path = Path("data/current/replay_inputs.csv")
    if not path.exists():
        return set()
    symbols: set[str] = set()
    for row in csv.DictReader(open(path)):
        for sym in (row.get("selected_symbols") or "").split("|"):
            sym = sym.strip().upper()
            if sym:
                symbols.add(sym)
    return symbols


# ─── Build model objects from CSV rows ───────────────────────────────────────

def _build_holdings(h_rows: list[dict]) -> list:
    from src.portfolio.models import PortfolioHolding
    result = []
    for r in h_rows:
        try:
            result.append(PortfolioHolding(
                portfolio_snapshot_id=r["portfolio_snapshot_id"],
                snapshot_date=r["snapshot_date"],
                account_name=r["account_name"],
                symbol=r["symbol"],
                description=r.get("description", ""),
                quantity=float(r.get("quantity") or 0),
                market_value=float(r.get("market_value") or 0),
                percent_of_portfolio=float(r.get("percent_of_portfolio") or 0),
                asset_class=r.get("asset_class", ""),
                geography=r.get("geography", ""),
                market_cap_bucket=r.get("market_cap_bucket", ""),
                mega_subtier=r.get("mega_subtier", ""),
                sector=r.get("sector", ""),
                industry=r.get("industry", ""),
                security_type=r.get("security_type", ""),
                cost_basis=float(r["cost_basis"]) if r.get("cost_basis") else None,
                composite_score=float(r["composite_score"]) if r.get("composite_score") else None,
                ess_score_text=r.get("ess_score_text") or None,
                zacks_rating=r.get("zacks_rating") or None,
                benchmark_id=r.get("benchmark_id") or None,
                investable_vehicle_id=r.get("investable_vehicle_id") or None,
                source_file=r.get("source_file", ""),
                created_at_utc=r.get("created_at_utc", ""),
                exposure_thematic_mix=(),
                exposure_mega_subtier_mix=(),
                strategic_role=r.get("strategic_role") or None,
                is_cash_equivalent=r.get("is_cash_equivalent", "").upper() == "TRUE",
            ))
        except Exception as e:
            print(f"  HOLDING SKIP {r.get('symbol')}: {e}", file=sys.stderr)
    return result


def _build_overlays(o_rows: list[dict]) -> list:
    from src.portfolio.models import SecurityIntelligenceOverlay
    result = []
    for r in o_rows:
        try:
            result.append(SecurityIntelligenceOverlay(
                portfolio_snapshot_id=r["portfolio_snapshot_id"],
                symbol=r["symbol"],
                composite_score=float(r["composite_score"]) if r.get("composite_score") else None,
                ess_score_text=r.get("ess_score_text") or None,
                zacks_rating=r.get("zacks_rating") or None,
                best_replay_return=None,
                replay_percentile=None,
                replay_supported=r.get("replay_supported", "").upper() == "TRUE",
                percent_of_portfolio=float(r.get("percent_of_portfolio") or 0),
                is_overweight_vs_target=r.get("is_overweight_vs_target", "").upper() == "TRUE",
                signal_direction=r.get("signal_direction", "") or "",
                opportunity_flag=r.get("opportunity_flag", "") or "",
                flag_rationale=r.get("flag_rationale", "") or "",
                created_at_utc=r.get("created_at_utc", "") or "",
            ))
        except Exception as e:
            print(f"  OVERLAY SKIP {r.get('symbol')}: {e}", file=sys.stderr)
    return result


def _build_alignment(a_rows: list[dict]) -> list:
    from src.portfolio.models import AllocationAlignmentResult
    result = []
    for r in a_rows:
        try:
            result.append(AllocationAlignmentResult(
                analysis_run_id="replay",
                portfolio_snapshot_id="replay",
                node_key=r["node_key"],
                node_label=r["node_key"],
                dimension_type=r.get("dimension_type", ""),
                actual_pct=float(r.get("actual_pct", 0) or 0),
                target_pct=float(r.get("target_pct", 0) or 0),
                tactical_target_pct=float(r.get("tactical_target_pct", 0) or 0),
                drift_pct=float(r.get("drift_pct", 0) or 0),
                drift_direction=r["drift_direction"],
                severity=r["severity"],
                concentration_risk=r.get("concentration_risk", ""),
                alignment_score=float(r.get("alignment_score", 0) or 0),
                recommendation_priority=int(r.get("recommendation_priority", 0) or 0),
                created_at_utc=r.get("created_at_utc", ""),
                etf_derived_actual_pct=float(r.get("etf_derived_actual_pct", 0) or 0),
            ))
        except Exception:
            pass
    return result


# ─── STI tier derivation via Trim Intelligence ───────────────────────────────

_CONVICTION_NARRATIVE_TIERS = {
    "CORE_CONVICTION_LEADER",
    "HIGH_CONVICTION_ANCHOR",
}


def _build_sti_index(snap_id: str, holdings: list, overlays: list, alignment: list) -> dict[str, str]:
    """Return {symbol: narrative_tier} for conviction-tier holdings."""
    from src.portfolio.trim_intelligence import build_strategic_profiles
    profiles = build_strategic_profiles(snap_id, holdings, overlays, alignment)
    return {
        p.symbol.upper(): p.narrative_tier
        for p in profiles
        if p.narrative_tier in _CONVICTION_NARRATIVE_TIERS
    }


# ─── Step 1: Deployable Capital ───────────────────────────────────────────────

def step1_cash(h_rows: list[dict], snap: dict) -> dict:
    total_mv = float(snap.get("total_market_value") or 0)
    cash_pct = 0.0
    cash_mv  = 0.0
    cash_symbols = []
    for h in h_rows:
        if h.get("is_cash_equivalent", "").upper() == "TRUE" \
                or h.get("asset_class", "").upper() == "CASH":
            pct = float(h.get("percent_of_portfolio") or 0)
            mv  = float(h.get("market_value") or 0)
            cash_pct += pct
            cash_mv  += mv
            cash_symbols.append({"symbol": h["symbol"], "pct": pct, "mv": mv})

    target_mv      = total_mv * TARGET_CASH_PCT / 100.0
    excess_pct     = max(0.0, cash_pct - TARGET_CASH_PCT)
    excess_mv      = max(0.0, cash_mv - target_mv)
    floor_mv       = total_mv * MIN_CASH_PCT / 100.0
    deployable_mv  = max(0.0, cash_mv - floor_mv)
    deployable_pct = deployable_mv / total_mv * 100.0 if total_mv else 0.0

    return {
        "total_mv":        total_mv,
        "actual_cash_pct": round(cash_pct, 4),
        "actual_cash_mv":  round(cash_mv, 2),
        "target_cash_pct": TARGET_CASH_PCT,
        "target_cash_mv":  round(target_mv, 2),
        "excess_cash_pct": round(excess_pct, 4),
        "excess_cash_mv":  round(excess_mv, 2),
        "deployable_pct":  round(deployable_pct, 4),
        "deployable_mv":   round(deployable_mv, 2),
        "cash_symbols":    cash_symbols,
        "mandate":         MANDATE,
        "target_band":     f"{MIN_CASH_PCT}-{MAX_CASH_PCT}%",
    }


# ─── Step 2: Conviction Universe ──────────────────────────────────────────────

def step2_conviction_universe(
    h_rows: list[dict],
    o_rows: list[dict],
    sti_index: dict[str, str],
    replay_index: set[str],
) -> list[dict]:
    overlay_map = {r["symbol"].upper(): r for r in o_rows}
    universe = []
    for h in h_rows:
        sym  = h["symbol"].upper()
        tier = sti_index.get(sym)
        if not tier:
            continue
        if h.get("is_cash_equivalent", "").upper() == "TRUE":
            continue
        if h.get("asset_class", "").upper() == "CASH":
            continue
        if h.get("security_type", "").upper() in ("ETF", "FUND", "MUTUAL_FUND"):
            continue

        pct    = float(h.get("percent_of_portfolio") or 0)
        mv     = float(h.get("market_value") or 0)
        comp   = float(h.get("composite_score") or 0) or None
        ess    = h.get("ess_score_text") or "UNKNOWN"
        zacks  = h.get("zacks_rating") or "UNKNOWN"
        ov     = overlay_map.get(sym, {})
        replay = ov.get("replay_supported", "").upper() == "TRUE" or sym in replay_index
        sig    = ov.get("signal_direction", "") or "UNKNOWN"

        universe.append({
            "symbol":       sym,
            "current_pct":  round(pct, 4),
            "market_value": round(mv, 2),
            "composite":    comp,
            "ess":          ess,
            "zacks":        zacks,
            "replay":       replay,
            "signal_dir":   sig,
            "sti_tier":     tier,
        })

    return sorted(universe, key=lambda x: -(x["composite"] or 0))


# ─── Step 3: DAS ─────────────────────────────────────────────────────────────

def _das(entry: dict, ow_nodes: set, h_rows: list[dict]) -> tuple[float, dict]:
    """Compute Deployment Attractiveness Score.

    DAS = Signal(0-30) + Replay(0-20) + Conviction(0-25) + Sizing(0-15) + Momentum(0-10)
          - Redundancy Penalty(0-15) - Concentration Penalty(0-20)
    """
    sym  = entry["symbol"]
    comp = entry["composite"] or 0.0
    tier = entry["sti_tier"]
    pct  = entry["current_pct"]
    ess  = (entry["ess"] or "").upper()
    sig  = (entry["signal_dir"] or "").upper()

    signal_c    = min(comp / 5.0 * 30.0, 30.0)
    replay_c    = 20.0 if entry["replay"] else 0.0
    conviction_c = {"CORE_CONVICTION_LEADER": 25.0, "HIGH_CONVICTION_ANCHOR": 20.0}.get(tier, 10.0)
    headroom    = max(0.0, 1.0 - pct / WARN_POSITION_PCT) if WARN_POSITION_PCT else 0.0
    sizing_c    = 15.0 * headroom

    ess_bull = "BULLISH" in ess
    ess_bear = "BEARISH" in ess
    sig_bull = sig == "BULLISH"
    sig_bear = sig == "BEARISH"
    if ess_bull and sig_bull:
        momentum_c = 10.0
    elif ess_bull or sig_bull:
        momentum_c = 7.5
    elif ess_bear or sig_bear:
        momentum_c = 0.0
    else:
        momentum_c = 4.0

    redundancy_pen = 0.0
    for h in h_rows:
        if h["symbol"].upper() == sym:
            node = f"EQUITIES.{h.get('geography', 'US')}.{h.get('market_cap_bucket', 'LARGE')}"
            if any(node.startswith(ow) or ow.startswith(node) for ow in ow_nodes):
                redundancy_pen = 15.0
            break

    conc_pen = 0.0
    if pct > WARN_POSITION_PCT:
        conc_pen = min((pct - WARN_POSITION_PCT) * 4.0, 20.0)

    raw = signal_c + replay_c + conviction_c + sizing_c + momentum_c - redundancy_pen - conc_pen
    das = round(max(0.0, raw), 2)

    return das, {
        "signal": round(signal_c, 2), "replay": round(replay_c, 2),
        "conviction": round(conviction_c, 2), "sizing": round(sizing_c, 2),
        "momentum": round(momentum_c, 2), "redundancy_pen": round(redundancy_pen, 2),
        "conc_pen": round(conc_pen, 2), "raw": round(raw, 2),
    }


def step3_das(universe: list[dict], ow_nodes: set, h_rows: list[dict]) -> list[dict]:
    for e in universe:
        e["das"], e["das_breakdown"] = _das(e, ow_nodes, h_rows)
    return sorted(universe, key=lambda x: -x["das"])


# ─── Step 4: Concentration ───────────────────────────────────────────────────

def step4_concentration(
    universe: list[dict], cash: dict, a_rows: list[dict], h_rows: list[dict]
) -> list[dict]:
    total_mv   = cash["total_mv"]
    deployable = cash["deployable_mv"]
    ow_nodes   = {
        r["node_key"] for r in a_rows
        if r.get("drift_direction") == "OVERWEIGHT"
        and r.get("severity") in ("HIGH", "MODERATE")
    }
    holding_map = {h["symbol"].upper(): h for h in h_rows}
    check_syms  = _FOCUS_SYMBOLS | {e["symbol"] for e in universe[:10]}
    results     = []

    for sym in sorted(check_syms):
        h = holding_map.get(sym)
        if not h:
            continue
        curr_pct = float(h.get("percent_of_portfolio") or 0)
        curr_mv  = float(h.get("market_value") or 0)
        new_mv   = curr_mv + deployable
        new_pct  = (new_mv / total_mv * 100.0) if total_mv else 0.0
        node     = f"EQUITIES.{h.get('geography', 'US')}.{h.get('market_cap_bucket', 'LARGE')}"
        in_ow    = any(node.startswith(ow) or ow.startswith(node) for ow in ow_nodes)

        conc_concern     = new_pct > MAX_POSITION_PCT
        conc_warn        = WARN_POSITION_PCT < new_pct <= MAX_POSITION_PCT
        mandate_conflict = in_ow and new_pct > WARN_POSITION_PCT

        if conc_concern:
            flag = "CONCENTRATION_CONCERN"
        elif mandate_conflict:
            flag = "MANDATE_CONFLICT"
        elif conc_warn:
            flag = "SOFT_WARN"
        elif in_ow:
            flag = "OW_NODE"
        else:
            flag = "CLEAR"

        results.append({
            "symbol": sym, "current_pct": round(curr_pct, 4),
            "new_pct_if_full": round(new_pct, 4), "in_ow_node": in_ow,
            "node": node, "flag": flag,
        })

    return sorted(results, key=lambda x: -x["current_pct"])


# ─── Step 5: Ranking ─────────────────────────────────────────────────────────

def step5_ranking(universe: list[dict], conc: list[dict]) -> list[dict]:
    conc_map = {r["symbol"]: r for r in conc}
    ranked   = []
    _conc_impact = {
        "CONCENTRATION_CONCERN": "CONCERN - would exceed 8% threshold",
        "MANDATE_CONFLICT":      "CONFLICT - OW node + position growth",
        "SOFT_WARN":             "SOFT WARN - approaches 6% threshold",
        "OW_NODE":               "OW NODE - node already overweight",
        "CLEAR":                 "Clear",
    }
    for entry in universe:
        sym   = entry["symbol"]
        flag  = conc_map.get(sym, {}).get("flag", "CLEAR")
        tier  = entry["sti_tier"]
        comp  = entry["composite"] or 0
        parts = []
        if tier == "CORE_CONVICTION_LEADER":
            parts.append("Highest conviction tier")
        else:
            parts.append("High conviction anchor")
        if comp >= 4.5:
            parts.append(f"Strong composite ({comp:.2f})")
        elif comp >= 4.0:
            parts.append(f"Good composite ({comp:.2f})")
        if entry["replay"]:
            parts.append("Replay-supported")
        if "BULLISH" in (entry["ess"] or "").upper():
            parts.append("ESS bullish")
        if flag != "CLEAR":
            parts.append(f"Warn: {flag}")

        ranked.append({
            "rank": 0, "symbol": sym, "current_pct": entry["current_pct"],
            "composite": entry["composite"], "replay": "Yes" if entry["replay"] else "No",
            "tier": tier, "tier_short": "CCL" if tier == "CORE_CONVICTION_LEADER" else "HCA",
            "das": entry["das"], "conc_impact": _conc_impact.get(flag, flag),
            "commentary": "; ".join(parts), "flag": flag,
            "ess": entry["ess"], "zacks": entry["zacks"],
            "das_breakdown": entry["das_breakdown"],
        })

    ranked = sorted(ranked, key=lambda x: (-x["das"], -(x["composite"] or 0)))
    for i, r in enumerate(ranked[:15], 1):
        r["rank"] = i
    return ranked[:15]


# ─── Formatting helpers ───────────────────────────────────────────────────────

def _fmt_pct(v):
    return f"{float(v):.2f}%" if v is not None else "-"

def _fmt_mv(v):
    if v is None: return "-"
    n = float(v)
    if n >= 1_000_000: return f"${n/1_000_000:.2f}M"
    if n >= 1_000:     return f"${n/1_000:.1f}K"
    return f"${n:.0f}"

def _fmt_score(v):
    return f"{float(v):.3f}" if v is not None else "-"


# ─── Report generation ────────────────────────────────────────────────────────

def generate_report(
    run_id: str, snap: dict, cash: dict,
    universe: list[dict], ranked: list[dict], conc: list[dict],
) -> str:
    lines: list[str] = []
    w = lines.append
    total_mv  = cash["total_mv"]
    account   = snap.get("account_name", "Portfolio")
    snap_dt   = snap.get("snapshot_date", "-")
    ccl_count = sum(1 for e in universe if e["sti_tier"] == "CORE_CONVICTION_LEADER")
    hca_count = sum(1 for e in universe if e["sti_tier"] == "HIGH_CONVICTION_ANCHOR")

    w("# Phase 7.4A - Conviction Capital Deployment Analysis")
    w("")
    w(f"**Account:** {account}  ")
    w(f"**Snapshot Date:** {snap_dt}  ")
    w(f"**Analysis Run:** `{run_id}`  ")
    w(f"**Mandate:** {MANDATE}  ")
    w(f"**Total Portfolio MV:** {_fmt_mv(total_mv)}  ")
    w("")
    w("> Advisory analysis only. No trade instructions. No execution sizing.")
    w("> Do not deploy capital based solely on this output.")
    w("")

    # Step 1
    w("---")
    w("")
    w("## Step 1 - Deployable Capital")
    w("")
    w(f"**Mandate target band:** {cash['target_band']} (CONCENTRATED_ALPHA)")
    w(f"**Target cash midpoint:** {_fmt_pct(cash['target_cash_pct'])} = {_fmt_mv(cash['target_cash_mv'])}")
    w("")
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Actual Cash % | {_fmt_pct(cash['actual_cash_pct'])} |")
    w(f"| Actual Cash $ | {_fmt_mv(cash['actual_cash_mv'])} |")
    w(f"| Target Cash % | {_fmt_pct(cash['target_cash_pct'])} |")
    w(f"| Target Cash $ | {_fmt_mv(cash['target_cash_mv'])} |")
    w(f"| Excess Cash % | {_fmt_pct(cash['excess_cash_pct'])} |")
    w(f"| Excess Cash $ | {_fmt_mv(cash['excess_cash_mv'])} |")
    w(f"| **Deployable Cash** (above {MIN_CASH_PCT}% floor) | **{_fmt_pct(cash['deployable_pct'])}** |")
    w(f"| **Deployable $** | **{_fmt_mv(cash['deployable_mv'])}** |")
    w("")
    if cash["cash_symbols"]:
        w("**Cash instruments:**")
        for c in cash["cash_symbols"]:
            w(f"- `{c['symbol']}`: {_fmt_pct(c['pct'])} ({_fmt_mv(c['mv'])})")
    w("")
    excess = cash["excess_cash_pct"]
    if excess > 3.0:
        w(f"> Cash is {_fmt_pct(excess)} above mandate target. Significant deployable capital identified.")
    elif excess > 1.0:
        w(f"> Cash is {_fmt_pct(excess)} above mandate target - moderate deployment opportunity.")
    else:
        w("> Cash is within or near mandate target band. Limited excess capital.")
    w("")

    # Step 2
    w("---")
    w("")
    w("## Step 2 - Conviction Universe (Owned Holdings Only)")
    w("")
    w("Includes: CORE_CONVICTION_LEADER (CCL), HIGH_CONVICTION_ANCHOR (HCA)")
    w("")
    w(f"**{len(universe)} conviction-tier holdings identified in current portfolio.**")
    w("")
    w("| Symbol | Weight | Composite | ESS | Zacks | Replay | Signal | Tier |")
    w("|---|---|---|---|---|---|---|---|")
    for e in universe:
        ts = "CCL" if e["sti_tier"] == "CORE_CONVICTION_LEADER" else "HCA"
        w(f"| `{e['symbol']}` | {_fmt_pct(e['current_pct'])} | {_fmt_score(e['composite'])} | "
          f"{e['ess']} | {e['zacks']} | {'Y' if e['replay'] else '-'} | {e['signal_dir']} | {ts} |")
    w("")
    w(f"**Tier breakdown:** {ccl_count} CCL, {hca_count} HCA")
    w("")

    # Step 3
    w("---")
    w("")
    w("## Step 3 - Deployment Attractiveness Score (DAS) Methodology")
    w("")
    w("### Formula")
    w("")
    w("```")
    w("DAS = Signal(0-30) + Replay(0-20) + Conviction(0-25) + Sizing(0-15) + Momentum(0-10)")
    w("      - Redundancy Penalty(0-15) - Concentration Penalty(0-20)")
    w("Maximum possible: 100.0")
    w("```")
    w("")
    w("### Component Definitions")
    w("")
    w("| Component | Max | Calculation |")
    w("|---|---|---|")
    w("| Signal Quality | 30 | `composite / 5.0 x 30` (composite is 1-5 scale) |")
    w("| Replay Support | 20 | 20 if replay-supported, else 0 |")
    w("| Conviction Tier | 25 | CCL=25, HCA=20 |")
    w("| Sizing Headroom | 15 | `15 x (1 - current_pct / 6.0)` |")
    w("| Momentum | 10 | ESS+Signal: both bullish=10, one=7.5, neutral=4, bearish=0 |")
    w("| Redundancy Penalty | -15 | -15 if symbol node is OVERWEIGHT (MODERATE+) |")
    w("| Concentration Penalty | -20 | `-(pct - 6.0) x 4` when > 6%, capped at -20 |")
    w("")
    w("### STI Tier Classification")
    w("")
    w("Tiers derived by `build_strategic_profiles()` from the Trim Intelligence engine:")
    w("")
    w("| Tier | Code | Criteria |")
    w("|---|---|---|")
    w("| CORE_CONVICTION_LEADER | CCL | BULLISH signal + replay + composite >= 4.0 + weight >= 1.5% |")
    w("| HIGH_CONVICTION_ANCHOR | HCA | strategic_classification == HIGH_CONVICTION_RETAIN |")
    w("")
    w("### DAS Score Interpretation")
    w("")
    w("| DAS Range | Interpretation |")
    w("|---|---|")
    w("| 75-100 | TIER 1 - High-priority deployment candidate |")
    w("| 55-74  | TIER 2 - Attractive deployment candidate |")
    w("| 35-54  | TIER 3 - Reasonable candidate, review context |")
    w("| <35    | Below threshold - limited attractiveness |")
    w("")

    # Step 4
    w("---")
    w("")
    w("## Step 4 - Concentration Constraint Analysis")
    w("")
    w(f"**Scenario:** Full deployable cash ({_fmt_mv(cash['deployable_mv'])}) into one position.")
    w(f"**Concentration ceiling:** {MAX_POSITION_PCT}%    **Soft-warn:** {WARN_POSITION_PCT}%")
    w("")
    w("| Symbol | Current % | New % (full deploy) | Node | Flag |")
    w("|---|---|---|---|---|")
    focus_conc = [c for c in conc if c["symbol"] in _FOCUS_SYMBOLS]
    emoji_map  = {"CONCENTRATION_CONCERN": "RED", "MANDATE_CONFLICT": "ORANGE",
                  "SOFT_WARN": "YELLOW", "OW_NODE": "YELLOW", "CLEAR": "GREEN"}
    for c in focus_conc:
        ow_mark = " (OW)" if c["in_ow_node"] else ""
        w(f"| `{c['symbol']}` | {_fmt_pct(c['current_pct'])} | {_fmt_pct(c['new_pct_if_full'])} | "
          f"`{c['node']}`{ow_mark} | {emoji_map.get(c['flag'],'')} {c['flag']} |")
    w("")
    w("**Observations:**")
    for c in focus_conc:
        sym  = c["symbol"]
        flag = c["flag"]
        new  = c["new_pct_if_full"]
        if flag == "CONCENTRATION_CONCERN":
            w(f"- `{sym}`: Full deployment -> {_fmt_pct(new)}, exceeds {MAX_POSITION_PCT}% ceiling.")
        elif flag == "MANDATE_CONFLICT":
            w(f"- `{sym}`: In already-overweight node; deployment compounds allocation gap.")
        elif flag == "SOFT_WARN":
            w(f"- `{sym}`: Approaches {WARN_POSITION_PCT}% soft-warn at full deploy ({_fmt_pct(new)}).")
        elif flag == "OW_NODE":
            w(f"- `{sym}`: Node is overweight; consider allocation impact.")
        else:
            w(f"- `{sym}`: Full deploy ({_fmt_pct(new)}) within guardrails.")
    w("")

    # Step 5
    w("---")
    w("")
    w("## Step 5 - Top 15 Conviction Deployment Candidates")
    w("")
    w(f"Ranked by DAS descending. Universe: {len(universe)} conviction-tier holdings.")
    w("")
    w("| Rank | Symbol | Weight | Composite | Replay | Tier | DAS | Concentration Impact | Commentary |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in ranked:
        w(f"| {r['rank']} | `{r['symbol']}` | {_fmt_pct(r['current_pct'])} | "
          f"{_fmt_score(r['composite'])} | {r['replay']} | {r['tier_short']} | "
          f"**{r['das']}** | {r['conc_impact']} | {r['commentary']} |")
    w("")
    w("### DAS Component Breakdown")
    w("")
    w("| Symbol | Signal | Replay | Conv | Sizing | Momentum | Redund- | Conc- | DAS |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in ranked:
        bd = r["das_breakdown"]
        w(f"| `{r['symbol']}` | {bd['signal']} | {bd['replay']} | {bd['conviction']} | "
          f"{bd['sizing']:.1f} | {bd['momentum']} | {bd['redundancy_pen']} | "
          f"{bd['conc_pen']} | **{r['das']}** |")
    w("")
    t1 = [r for r in ranked if r["das"] >= 75]
    t2 = [r for r in ranked if 55 <= r["das"] < 75]
    t3 = [r for r in ranked if 35 <= r["das"] < 55]
    bl = [r for r in ranked if r["das"] < 35]
    w("**Tier summary:**")
    if t1: w(f"- TIER 1 (>= 75): {', '.join('`'+r['symbol']+'`' for r in t1)}")
    if t2: w(f"- TIER 2 (55-74): {', '.join('`'+r['symbol']+'`' for r in t2)}")
    if t3: w(f"- TIER 3 (35-54): {', '.join('`'+r['symbol']+'`' for r in t3)}")
    if bl: w(f"- Below threshold: {', '.join('`'+r['symbol']+'`' for r in bl)}")
    w("")

    # Step 6
    w("---")
    w("")
    w("## Step 6 - Deployment Observations")
    w("")
    w("### Capital Context")
    w("")
    w(f"Portfolio holds {_fmt_pct(cash['actual_cash_pct'])} in cash ({_fmt_mv(cash['actual_cash_mv'])}) "
      f"against a CONCENTRATED_ALPHA mandate target band of {cash['target_band']}. "
      f"Deployable capital (above the {MIN_CASH_PCT}% mandate floor) is "
      f"**{_fmt_mv(cash['deployable_mv'])}** ({_fmt_pct(cash['deployable_pct'])}).")
    w("")
    w("### Conviction Universe Quality")
    w("")
    if universe:
        avg_comp     = sum(e["composite"] or 0 for e in universe) / len(universe)
        replay_count = sum(1 for e in universe if e["replay"])
        w(f"- **{len(universe)} conviction-tier holdings** ({ccl_count} CCL, {hca_count} HCA)")
        w(f"- Average composite score: **{avg_comp:.3f}**")
        w(f"- Replay-supported: **{replay_count}/{len(universe)}**")
    w("")
    w("### Top Candidates")
    w("")
    for r in ranked[:3]:
        replay_yn = "Yes" if r["replay"] == "Yes" else "No"
        w(f"**{r['rank']}. `{r['symbol']}`** (DAS {r['das']}) - "
          f"{r['tier'].replace('_', ' ')}, "
          f"composite {_fmt_score(r['composite'])}, replay {replay_yn}. "
          f"{r['commentary']}")
        w("")
    w("")
    w("### Concentration Guardrails")
    w("")
    blocked = [c for c in focus_conc if c["flag"] in ("CONCENTRATION_CONCERN", "MANDATE_CONFLICT")]
    clear   = [c for c in focus_conc if c["flag"] == "CLEAR"]
    if blocked:
        w(f"Full-deployment flags {len(blocked)} monitored symbols "
          f"({', '.join('`'+c['symbol']+'`' for c in blocked)}) for concentration/mandate concerns.")
    if clear:
        w(f"Clean guardrails: {', '.join('`'+c['symbol']+'`' for c in clear)}")
    w("")
    w("### Key Limitations")
    w("")
    w("- DAS is a relative attractiveness ranking, not an absolute sizing model.")
    w("- STI tiers derived from `build_strategic_profiles()` using live signal, replay, and composite data.")
    w("- Concentration analysis uses a single-symbol full-deployment stress test.")
    w("- No forward guidance or market timing implied.")
    w("")
    w("---")
    w("")
    w("*Analysis only. Not investment advice. Not a trade instruction.*")
    w("")

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    sys.path.insert(0, ".")

    run_id  = _pick_run()
    run_dir = RUN_ROOT / run_id
    print(f"Using run: {run_id}")

    snap    = _load_json(run_dir / "snapshot.json")
    h_rows  = _load_csv_dicts(run_dir / "holdings.csv")
    o_rows  = _load_csv_dicts(run_dir / "security_overlays.csv")
    a_rows  = _load_csv_dicts(run_dir / "alignment.csv")

    holdings  = _build_holdings(h_rows)
    overlays  = _build_overlays(o_rows)
    alignment = _build_alignment(a_rows)
    replay_idx = _load_replay_index()

    snap_id   = snap["portfolio_snapshot_id"]
    sti_index = _build_sti_index(snap_id, holdings, overlays, alignment)
    ccl_n = sum(1 for v in sti_index.values() if v == "CORE_CONVICTION_LEADER")
    hca_n = sum(1 for v in sti_index.values() if v == "HIGH_CONVICTION_ANCHOR")
    print(f"STI index: {len(sti_index)} conviction symbols ({ccl_n} CCL, {hca_n} HCA)")

    ow_nodes = {
        r["node_key"] for r in a_rows
        if r.get("drift_direction") == "OVERWEIGHT"
        and r.get("severity") in ("HIGH", "MODERATE")
    }

    cash = step1_cash(h_rows, snap)
    print(f"Cash: {cash['actual_cash_pct']:.2f}%  Deployable: {_fmt_mv(cash['deployable_mv'])}")

    active_rows = [
        h for h in h_rows
        if h.get("operational_state", "ACTIVE_POSITION")
        not in ("EXCLUDED", "ACCOUNTING_ADJUSTMENT", "CLOSED_POSITION")
    ]
    universe = step2_conviction_universe(active_rows, o_rows, sti_index, replay_idx)
    print(f"Conviction universe: {len(universe)} holdings")

    universe = step3_das(universe, ow_nodes, active_rows)
    conc     = step4_concentration(universe, cash, a_rows, active_rows)
    ranked   = step5_ranking(universe, conc)
    print(f"Ranked candidates: {len(ranked)}")

    report = generate_report(run_id, snap, cash, universe, ranked, conc)
    out    = Path("conviction_capital_deployment_report.md")
    out.write_text(report, encoding="utf-8")
    print(f"Report written -> {out}")

    print("\n=== TOP 10 ===")
    print(f"{'Rank':>4}  {'Symbol':<8}  {'Weight':>7}  {'Comp':>6}  {'Replay':>6}  {'Tier':>4}  {'DAS':>6}  Flag")
    for r in ranked[:10]:
        print(
            f"{r['rank']:>4}  {r['symbol']:<8}  {r['current_pct']:>6.2f}%  "
            f"{(r['composite'] or 0):>6.3f}  {'Yes' if r['replay']=='Yes' else 'No ':>6}  "
            f"{r['tier_short']:>4}  {r['das']:>6.1f}  {r['flag']}"
        )


if __name__ == "__main__":
    main()
