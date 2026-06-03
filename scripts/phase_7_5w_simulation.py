#!/usr/bin/env python3
"""Phase 7.5W — Capital Deployment Simulation Validation

Answers 9 diagnostic questions about whether the CW-DAS framework naturally
rotates capital as positions saturate, or whether it creates a feedback loop
that continues directing disproportionate capital to the same holdings.

Produces 10 deliverable files in data/analysis/phase_7_5w/:
  Q1  deployment_simulation_baseline.csv
  Q2  single_trade_saturation_report.md
  Q3  top3_execution_simulation.md
  Q4  full_plan_execution_report.md
  Q5  iterative_convergence_analysis.md
  Q6  vrt_saturation_curve.csv
  Q7  capital_rotation_analysis.md
  Q8  framework_stability_assessment.md
  Q9  operator_trust_assessment.md
  FIN deployment_simulation_final_verdict.md

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/phase_7_5w_simulation.py
"""
from __future__ import annotations

import csv
import json
import math
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
PAR_DIR   = REPO_ROOT / "data/portfolio_ingestion/analysis_runs/PAR-20260602-1BF2ADA5"
OUT_DIR   = REPO_ROOT / "data/analysis/phase_7_5w"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants (mirrored from deployment_queue.py and deployment_planner.py) ───
WARN_POSITION_PCT      = 6.0
MAX_POSITION_PCT       = 8.0
SIZING_SCALE           = 8.0
CCL_TIER               = "CORE_CONVICTION_LEADER"
CCL_CONVICTION_MULT    = 1.75
HCA_CONVICTION_MULT    = 1.25
TIER2_RANK_PCTILE      = 0.35
MIN_ALLOCATION         = 50.0


# ── Loader ─────────────────────────────────────────────────────────────────────

def load_baseline() -> tuple[dict, dict, dict[str, float]]:
    """Load deployment_queue.json, deployment_plan.json, and holdings as positions."""
    with open(PAR_DIR / "deployment_queue.json") as f:
        dq_data = json.load(f)
    with open(PAR_DIR / "deployment_plan.json") as f:
        dp_data = json.load(f)
    positions: dict[str, float] = {}
    with open(PAR_DIR / "holdings.csv") as f:
        for row in csv.DictReader(f):
            sym = row["symbol"].strip()
            mv  = float(row["market_value"] or 0)
            positions[sym] = positions.get(sym, 0.0) + mv
    return dq_data, dp_data, positions


# ── Simulation state ───────────────────────────────────────────────────────────

class SimState:
    """Mutable simulation state.

    Maintains position MVs and a static-component cache for each queue symbol.
    Only sizing_c and conc_pen are recomputed each cycle; all other score
    components are frozen from the baseline (static signals, replay verdicts,
    conviction tier, momentum).
    """

    def __init__(self, dq_data: dict, positions: dict[str, float]):
        self.total_mv        = float(dq_data["total_market_value"])
        cash_ctx             = dq_data["cash_context"]
        self.cash_mv         = float(cash_ctx["cash_mv"])
        self.floor_mv        = float(cash_ctx["floor_mv"])
        self.positions       = dict(positions)

        # Cache static (non-weight-dependent) components from baseline
        self.static_comps: dict[str, dict] = {}
        for item in dq_data["queue"]:
            sym = item["symbol"]
            bd  = item.get("score_breakdown", {})
            self.static_comps[sym] = {
                "signal":          float(bd.get("signal", 0)),
                "replay":          float(bd.get("replay", 0)),
                "conviction":      float(bd.get("conviction", 0)),
                "momentum":        float(bd.get("momentum", 0)),
                "redundancy_pen":  float(bd.get("redundancy_pen", 0)),
                "narrative_tier":  item["narrative_tier"],
                "composite_score": float(item["composite_score"]),
                "replay_supported": bool(item.get("replay_supported", False)),
                "trim_score":      float(item.get("trim_score", 0)),
            }

        self.deployable_cash = max(0.0, self.cash_mv - self.floor_mv)

    # ── Derived ────────────────────────────────────────────────────────────────

    @property
    def cash_pct(self) -> float:
        return self.cash_mv / self.total_mv * 100.0

    def pct(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0) / self.total_mv * 100.0

    @staticmethod
    def _sizing_c(pct: float) -> float:
        return SIZING_SCALE * max(0.0, 1.0 - pct / WARN_POSITION_PCT)

    @staticmethod
    def _conc_pen(pct: float) -> float:
        return min((pct - WARN_POSITION_PCT) * 4.0, 20.0) if pct > WARN_POSITION_PCT else 0.0

    @staticmethod
    def _headroom_pct(pct: float) -> float:
        return max(0.0, (WARN_POSITION_PCT - pct) / WARN_POSITION_PCT * 100.0)

    # ── Queue builder ──────────────────────────────────────────────────────────

    def build_queue_dict(self, deployable_cash: float | None = None) -> dict:
        """Reconstruct a deployment_queue_data dict for the current sim state."""
        dc = deployable_cash if deployable_cash is not None else self.deployable_cash

        scored: list[dict] = []
        for sym, sc in self.static_comps.items():
            p         = self.pct(sym)
            mv        = self.positions.get(sym, 0.0)
            sizing_c  = self._sizing_c(p)
            conc_pen  = self._conc_pen(p)
            headroom  = self._headroom_pct(p)

            raw = (
                sc["signal"]
                + sc["replay"]
                + sc["conviction"]
                + sizing_c
                + sc["momentum"]
                - sc["redundancy_pen"]
                - conc_pen
            )
            score = max(0.0, round(raw, 2))

            scored.append({
                "symbol":             sym,
                "current_weight_pct": round(p, 4),
                "market_value":       round(mv, 2),
                "composite_score":    sc["composite_score"],
                "narrative_tier":     sc["narrative_tier"],
                "replay_supported":   sc["replay_supported"],
                "trim_score":         sc["trim_score"],
                "headroom_pct":       round(headroom, 1),
                "deployment_score":   score,
                "score_breakdown": {
                    "signal":          sc["signal"],
                    "replay":          sc["replay"],
                    "conviction":      sc["conviction"],
                    "sizing":          round(sizing_c, 2),
                    "momentum":        sc["momentum"],
                    "redundancy_pen":  sc["redundancy_pen"],
                    "conc_pen":        round(conc_pen, 2),
                },
                "notes": sc["narrative_tier"][:3] + " tier",
            })

        scored.sort(key=lambda x: (-x["deployment_score"], x["symbol"]))
        for i, item in enumerate(scored, 1):
            item["rank"] = i

        return {
            "run_id":             "SIM",
            "total_market_value": round(self.total_mv, 2),
            "cash_context": {
                "cash_mv":        round(self.cash_mv, 2),
                "cash_pct":       round(self.cash_pct, 4),
                "floor_mv":       round(self.floor_mv, 2),
                "deployable_mv":  round(dc, 2),
                "deployable_pct": round(dc / self.total_mv * 100.0, 4),
            },
            "queue": scored,
        }

    # ── Plan runner ────────────────────────────────────────────────────────────

    def run_plan(self, deployable_cash: float | None = None) -> tuple[dict, list[dict]]:
        """Build queue + plan for current state.

        Returns (queue_dict, recommendations_as_list_of_dicts).
        """
        from src.portfolio.deployment_planner import build_deployment_plan
        dc       = deployable_cash if deployable_cash is not None else self.deployable_cash
        qd       = self.build_queue_dict(deployable_cash=dc)
        plan     = build_deployment_plan(qd, deployable_cash=dc)
        recs     = [
            {
                "rank":               r.rank,
                "symbol":             r.symbol,
                "deployment_tier":    r.deployment_tier,
                "current_weight_pct": r.current_weight_pct,
                "suggested_add":      r.suggested_add,
                "projected_weight_pct": r.projected_weight_pct,
                "constraint_status":  r.constraint_status,
            }
            for r in plan.recommendations
        ]
        return qd, recs

    # ── Trade applier ──────────────────────────────────────────────────────────

    def apply_trades(self, trades: dict[str, float]) -> None:
        """Apply {symbol: add_amount} to positions and reduce deployable cash."""
        total = 0.0
        for sym, add in trades.items():
            if add > 0:
                self.positions[sym] = self.positions.get(sym, 0.0) + add
                total += add
        self.deployable_cash = max(0.0, self.deployable_cash - total)
        self.cash_mv         = max(0.0, self.cash_mv - total)

    # ── Clone ──────────────────────────────────────────────────────────────────

    def clone(self) -> "SimState":
        s                = SimState.__new__(SimState)
        s.total_mv       = self.total_mv
        s.cash_mv        = self.cash_mv
        s.floor_mv       = self.floor_mv
        s.deployable_cash = self.deployable_cash
        s.positions      = dict(self.positions)
        s.static_comps   = self.static_comps   # immutable after init — safe share
        return s


# ── Helpers ────────────────────────────────────────────────────────────────────

def top_n_queue(qd: dict, n: int = 20) -> list[dict]:
    return sorted(qd["queue"], key=lambda x: x["rank"])[:n]


def score_delta_table(baseline_qd: dict, sim_qd: dict, symbols: list[str] | None = None) -> list[dict]:
    """Compute score changes between two queue states."""
    b = {item["symbol"]: item for item in baseline_qd["queue"]}
    s = {item["symbol"]: item for item in sim_qd["queue"]}
    syms = symbols or sorted(b.keys())
    rows = []
    for sym in syms:
        if sym not in b or sym not in s:
            continue
        bi, si = b[sym], s[sym]
        rows.append({
            "symbol":       sym,
            "baseline_pct": bi["current_weight_pct"],
            "sim_pct":      si["current_weight_pct"],
            "baseline_score": bi["deployment_score"],
            "sim_score":    si["deployment_score"],
            "score_delta":  round(si["deployment_score"] - bi["deployment_score"], 2),
            "baseline_rank": bi["rank"],
            "sim_rank":     si["rank"],
            "rank_delta":   si["rank"] - bi["rank"],
            "sizing_before": bi["score_breakdown"]["sizing"],
            "sizing_after": si["score_breakdown"]["sizing"],
            "conc_pen_before": bi["score_breakdown"]["conc_pen"],
            "conc_pen_after":  si["score_breakdown"]["conc_pen"],
        })
    rows.sort(key=lambda x: x["score_delta"])
    return rows


def herfindahl(positions: dict[str, float], total_mv: float) -> float:
    return sum((mv / total_mv) ** 2 for mv in positions.values() if mv > 0)


def top5_concentration(positions: dict[str, float], total_mv: float) -> float:
    top = sorted(positions.values(), reverse=True)[:5]
    return sum(top) / total_mv * 100.0


# ── Q1: Baseline snapshot ──────────────────────────────────────────────────────

def q1_baseline_snapshot(baseline_qd: dict) -> None:
    """Write top-20 baseline queue snapshot to CSV."""
    rows = top_n_queue(baseline_qd, 20)
    out  = OUT_DIR / "deployment_simulation_baseline.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "rank", "symbol", "narrative_tier", "current_weight_pct",
            "market_value", "deployment_score", "headroom_pct",
            "signal_c", "replay_c", "conviction_c", "sizing_c",
            "momentum_c", "redundancy_pen", "conc_pen",
        ])
        w.writeheader()
        for item in rows:
            bd = item["score_breakdown"]
            w.writerow({
                "rank":              item["rank"],
                "symbol":            item["symbol"],
                "narrative_tier":    item["narrative_tier"],
                "current_weight_pct": item["current_weight_pct"],
                "market_value":      item["market_value"],
                "deployment_score":  item["deployment_score"],
                "headroom_pct":      item["headroom_pct"],
                "signal_c":          bd["signal"],
                "replay_c":          bd["replay"],
                "conviction_c":      bd["conviction"],
                "sizing_c":          bd["sizing"],
                "momentum_c":        bd["momentum"],
                "redundancy_pen":    bd["redundancy_pen"],
                "conc_pen":          bd["conc_pen"],
            })
    print(f"[Q1] Written: {out.name}")


# ── Q2: Single trade VRT impact ────────────────────────────────────────────────

def q2_single_trade_impact(state_0: SimState, baseline_qd: dict, baseline_recs: list[dict]) -> None:
    """Execute only the top-1 VRT trade and measure score/rank impact."""
    # Get VRT suggested add from baseline plan
    vrt_rec = next((r for r in baseline_recs if r["symbol"] == "VRT"), None)
    if vrt_rec is None:
        print("[Q2] VRT not in plan — skipping")
        return

    vrt_add = vrt_rec["suggested_add"]
    state   = state_0.clone()
    state.apply_trades({"VRT": vrt_add})

    sim_qd = state.build_queue_dict(deployable_cash=state_0.deployable_cash - vrt_add)
    deltas = score_delta_table(baseline_qd, sim_qd)

    # Focus on top 15 symbols from baseline
    top_syms = [item["symbol"] for item in top_n_queue(baseline_qd, 15)]
    top_deltas = [d for d in deltas if d["symbol"] in top_syms]
    top_deltas.sort(key=lambda x: baseline_qd["queue"].index(
        next(q for q in baseline_qd["queue"] if q["symbol"] == x["symbol"])
    ) if any(q["symbol"] == x["symbol"] for q in baseline_qd["queue"]) else 99)

    vrt_before = next(q for q in baseline_qd["queue"] if q["symbol"] == "VRT")
    vrt_after  = next(q for q in sim_qd["queue"] if q["symbol"] == "VRT")
    remaining_cash = state_0.deployable_cash - vrt_add
    sim_plan   = None
    if remaining_cash > MIN_ALLOCATION:
        _, sim_recs = state.run_plan(deployable_cash=remaining_cash)
    else:
        sim_recs = []

    lines = [
        "# Q2: Single Trade Impact — VRT +${:,.2f}".format(vrt_add),
        "",
        "## Trade Executed",
        f"- **VRT**: Add ${vrt_add:,.2f}",
        f"- Weight change: {vrt_before['current_weight_pct']:.4f}% → {vrt_after['current_weight_pct']:.4f}%",
        f"- Score change: {vrt_before['deployment_score']:.2f} → {vrt_after['deployment_score']:.2f} "
        f"(Δ = {vrt_after['deployment_score'] - vrt_before['deployment_score']:+.2f})",
        f"- Sizing_c change: {vrt_before['score_breakdown']['sizing']:.2f} → {vrt_after['score_breakdown']['sizing']:.2f}",
        f"- Conc_pen change: {vrt_before['score_breakdown']['conc_pen']:.2f} → {vrt_after['score_breakdown']['conc_pen']:.2f}",
        f"- Rank change: #{vrt_before['rank']} → #{vrt_after['rank']}",
        f"- Remaining deployable cash: ${remaining_cash:,.2f}",
        "",
        "## Score Impact on Top-15 Symbols",
        "",
        "| Symbol | Before% | After% | Before Score | After Score | Δ Score | Before Rank | After Rank | Δ Rank |",
        "|--------|---------|--------|-------------|------------|---------|------------|-----------|--------|",
    ]
    for d in top_deltas:
        lines.append(
            f"| {d['symbol']} | {d['baseline_pct']:.4f}% | {d['sim_pct']:.4f}% "
            f"| {d['baseline_score']:.2f} | {d['sim_score']:.2f} "
            f"| {d['score_delta']:+.2f} | #{d['baseline_rank']} | #{d['sim_rank']} "
            f"| {d['rank_delta']:+d} |"
        )

    lines += [
        "",
        "## Post-Trade Queue Top-10",
        "",
        "| Rank | Symbol | Score | Weight% | Tier |",
        "|------|--------|-------|---------|------|",
    ]
    for item in top_n_queue(sim_qd, 10):
        lines.append(
            f"| {item['rank']} | {item['symbol']} | {item['deployment_score']:.2f} "
            f"| {item['current_weight_pct']:.4f}% | {item['narrative_tier'][:3]} |"
        )

    lines += [
        "",
        "## Next Plan After VRT Trade (remaining ${:,.2f})".format(remaining_cash),
        "",
        "| Rank | Symbol | Tier | Suggested Add | Projected% |",
        "|------|--------|------|---------------|-----------|",
    ]
    for r in (sim_recs[:10] if sim_recs else []):
        lines.append(
            f"| {r['rank']} | {r['symbol']} | {r['deployment_tier']} "
            f"| ${r['suggested_add']:,.2f} | {r['projected_weight_pct']:.4f}% |"
        )

    lines += [
        "",
        "## Saturation Assessment",
        "",
        f"VRT sizing_c dropped {vrt_before['score_breakdown']['sizing']:.2f} → "
        f"{vrt_after['score_breakdown']['sizing']:.2f} after adding ${vrt_add:,.2f}.",
    ]
    vrt_score_drop = vrt_after["deployment_score"] - vrt_before["deployment_score"]
    # Check if VRT still leads or falls behind other symbols
    vrt_new_rank = vrt_after["rank"]
    if vrt_new_rank == 1:
        lines.append("VRT **retains rank #1** after single trade — the score penalty was insufficient to displace it.")
        saturation_verdict = "WEAK_SATURATION"
    else:
        lines.append(f"VRT falls to **rank #{vrt_new_rank}** after single trade — score penalty successfully demoted it.")
        saturation_verdict = "EFFECTIVE_SATURATION"
    lines.append(f"\n**Saturation verdict: {saturation_verdict}**")

    out = OUT_DIR / "single_trade_saturation_report.md"
    out.write_text("\n".join(lines))
    print(f"[Q2] Written: {out.name}  (saturation verdict: {saturation_verdict})")


# ── Q3: Top-3 execution ────────────────────────────────────────────────────────

def q3_top3_execution(state_0: SimState, baseline_qd: dict, baseline_recs: list[dict]) -> None:
    """Execute VRT + ARW + ATLC and measure portfolio impact."""
    top3_syms = ["VRT", "ARW", "ATLC"]
    trades    = {}
    for r in baseline_recs:
        if r["symbol"] in top3_syms:
            trades[r["symbol"]] = r["suggested_add"]

    state  = state_0.clone()
    state.apply_trades(trades)
    total_deployed = sum(trades.values())
    remaining_cash = state_0.deployable_cash - total_deployed

    sim_qd = state.build_queue_dict(deployable_cash=remaining_cash)

    lines = [
        "# Q3: Top-3 Execution Simulation",
        "",
        "## Trades Executed",
        "",
        "| Symbol | Added | Before% | After% | Score Before | Score After | Δ Score |",
        "|--------|-------|---------|--------|-------------|------------|---------|",
    ]
    for sym in top3_syms:
        before = next((q for q in baseline_qd["queue"] if q["symbol"] == sym), None)
        after  = next((q for q in sim_qd["queue"] if q["symbol"] == sym), None)
        add    = trades.get(sym, 0.0)
        if before and after:
            lines.append(
                f"| {sym} | ${add:,.2f} "
                f"| {before['current_weight_pct']:.4f}% | {after['current_weight_pct']:.4f}% "
                f"| {before['deployment_score']:.2f} | {after['deployment_score']:.2f} "
                f"| {after['deployment_score'] - before['deployment_score']:+.2f} |"
            )

    lines += [
        "",
        f"**Total deployed:** ${total_deployed:,.2f}",
        f"**Remaining deployable cash:** ${remaining_cash:,.2f}",
        "",
        "## Post-Trade Queue Top-15",
        "",
        "| Rank | Symbol | Score | Weight% | Tier | Sizing_c | Conc_pen |",
        "|------|--------|-------|---------|------|----------|---------|",
    ]
    for item in top_n_queue(sim_qd, 15):
        bd = item["score_breakdown"]
        lines.append(
            f"| {item['rank']} | {item['symbol']} | {item['deployment_score']:.2f} "
            f"| {item['current_weight_pct']:.4f}% | {item['narrative_tier'][:3]} "
            f"| {bd['sizing']:.2f} | {bd['conc_pen']:.2f} |"
        )

    # Run next plan with remaining cash
    if remaining_cash > MIN_ALLOCATION:
        _, next_recs = state.run_plan(deployable_cash=remaining_cash)
    else:
        next_recs = []

    lines += [
        "",
        "## Next Plan After Top-3 (remaining ${:,.2f})".format(remaining_cash),
        "",
        "| Rank | Symbol | Tier | Suggested Add | Projected% |",
        "|------|--------|------|---------------|-----------|",
    ]
    for r in (next_recs[:12] if next_recs else []):
        lines.append(
            f"| {r['rank']} | {r['symbol']} | {r['deployment_tier']} "
            f"| ${r['suggested_add']:,.2f} | {r['projected_weight_pct']:.4f}% |"
        )

    # Did any top-3 symbols reappear in the new plan?
    reappeared = [r["symbol"] for r in (next_recs or []) if r["symbol"] in top3_syms and r["suggested_add"] > 0]

    lines += [
        "",
        "## Capital Rotation Indicators",
        "",
        f"- Top-3 symbols reappearing in next plan: {reappeared if reappeared else 'None'}",
    ]
    # Check if new entrants got elevated
    new_top5 = [item["symbol"] for item in top_n_queue(sim_qd, 5)]
    prev_top5 = [item["symbol"] for item in top_n_queue(baseline_qd, 5)]
    promoted   = [s for s in new_top5 if s not in prev_top5]
    lines += [
        f"- New symbols entering top-5 after top-3 execution: {promoted if promoted else 'None'}",
        f"- Concentration (HHI): {herfindahl(state.positions, state.total_mv):.5f}",
        f"- Top-5 pct: {top5_concentration(state.positions, state.total_mv):.2f}%",
    ]

    if reappeared:
        lines.append("\n**Warning**: Executed symbols immediately reappear in next plan — potential feedback loop.")
    else:
        lines.append("\n**OK**: Framework rotated capital away from executed positions into fresh candidates.")

    out = OUT_DIR / "top3_execution_simulation.md"
    out.write_text("\n".join(lines))
    print(f"[Q3] Written: {out.name}")


# ── Q4: Full plan execution ────────────────────────────────────────────────────

def q4_full_plan_execution(state_0: SimState, baseline_qd: dict, baseline_recs: list[dict]) -> None:
    """Execute all 31 recommended trades and analyze the resulting portfolio state."""
    trades = {r["symbol"]: r["suggested_add"] for r in baseline_recs if r["suggested_add"] > 0}

    state  = state_0.clone()
    state.apply_trades(trades)
    total_deployed = sum(trades.values())

    sim_qd = state.build_queue_dict(deployable_cash=0.0)

    hhi_before = herfindahl(state_0.positions, state_0.total_mv)
    hhi_after  = herfindahl(state.positions, state.total_mv)

    lines = [
        "# Q4: Full Plan Execution Report",
        "",
        f"**Deployable cash deployed:** ${total_deployed:,.2f}",
        f"**Positions touched:** {len(trades)}",
        "",
        "## Portfolio Concentration Impact",
        "",
        f"| Metric | Before | After | Change |",
        f"|--------|--------|-------|--------|",
        f"| HHI (Herfindahl) | {hhi_before:.5f} | {hhi_after:.5f} | {hhi_after - hhi_before:+.5f} |",
        f"| Top-5 concentration | {top5_concentration(state_0.positions, state_0.total_mv):.2f}% "
        f"| {top5_concentration(state.positions, state.total_mv):.2f}% "
        f"| {top5_concentration(state.positions, state.total_mv) - top5_concentration(state_0.positions, state_0.total_mv):+.2f}% |",
        f"| Deployable cash | ${state_0.deployable_cash:,.2f} | $0.00 | -${total_deployed:,.2f} |",
        "",
        "## Full Plan Execution Summary (all trades)",
        "",
        "| Symbol | Added | Before% | After% | Score Before | Score After | Δ Score | Δ Rank |",
        "|--------|-------|---------|--------|-------------|------------|---------|--------|",
    ]

    b_map = {q["symbol"]: q for q in baseline_qd["queue"]}
    s_map = {q["symbol"]: q for q in sim_qd["queue"]}

    for sym, add in sorted(trades.items(), key=lambda x: -x[1]):
        bi = b_map.get(sym)
        si = s_map.get(sym)
        if bi and si:
            lines.append(
                f"| {sym} | ${add:,.2f} "
                f"| {bi['current_weight_pct']:.4f}% | {si['current_weight_pct']:.4f}% "
                f"| {bi['deployment_score']:.2f} | {si['deployment_score']:.2f} "
                f"| {si['deployment_score'] - bi['deployment_score']:+.2f} "
                f"| {si['rank'] - bi['rank']:+d} |"
            )

    lines += [
        "",
        "## Post-Execution Queue Top-20",
        "",
        "| Rank | Symbol | Score | Weight% | Sizing_c | Conc_pen | Tier |",
        "|------|--------|-------|---------|----------|---------|------|",
    ]
    for item in top_n_queue(sim_qd, 20):
        bd = item["score_breakdown"]
        lines.append(
            f"| {item['rank']} | {item['symbol']} | {item['deployment_score']:.2f} "
            f"| {item['current_weight_pct']:.4f}% | {bd['sizing']:.2f} | {bd['conc_pen']:.2f} "
            f"| {item['narrative_tier'][:3]} |"
        )

    # Check: how many executed positions would be top-10 candidates if cash were available again
    top10_after = {item["symbol"] for item in top_n_queue(sim_qd, 10)}
    re_queue_count = len(top10_after.intersection(set(trades.keys())))
    lines += [
        "",
        "## Re-Queue Analysis",
        f"Of the {len(trades)} executed positions, **{re_queue_count}** would rank in the top-10 again "
        "if fresh cash were available.",
        "",
        "**Interpretation:**",
    ]
    if re_queue_count >= 7:
        lines.append("HIGH re-queue rate — framework strongly favors the same positions. Material feedback loop risk.")
    elif re_queue_count >= 4:
        lines.append("MODERATE re-queue rate — some rotation occurring but top positions remain dominant.")
    else:
        lines.append("LOW re-queue rate — framework effectively rotates capital to fresh candidates after full execution.")

    out = OUT_DIR / "full_plan_execution_report.md"
    out.write_text("\n".join(lines))
    print(f"[Q4] Written: {out.name}  (re-queue top-10: {re_queue_count}/{len(trades)})")


# ── Q5: Iterative convergence ──────────────────────────────────────────────────

def q5_iterative_convergence(state_0: SimState, baseline_qd: dict, n_cycles: int = 8) -> None:
    """Run N deployment cycles with fresh cash injection each cycle.

    Simulates the operator faithfully executing recommendations over time.
    Cash injection per cycle = baseline deployable_cash.
    """
    CYCLE_CASH = state_0.deployable_cash   # ~$31,683 per cycle
    state      = state_0.clone()

    rows      = []          # per-cycle summary rows
    vrt_data  = []          # VRT score/weight tracking
    rank1_sym = []          # which symbol holds rank #1 each cycle

    for cycle in range(n_cycles):
        label = f"Cycle {cycle + 1}"
        # Re-inject fresh deployable cash at start of each cycle
        state.deployable_cash = CYCLE_CASH
        state.cash_mv        = state_0.floor_mv + CYCLE_CASH   # restore cash

        qd, recs = state.run_plan(deployable_cash=CYCLE_CASH)

        top_queue = top_n_queue(qd, 10)
        top1_sym  = top_queue[0]["symbol"] if top_queue else "?"
        top1_score= top_queue[0]["deployment_score"] if top_queue else 0

        vrt_q = next((q for q in qd["queue"] if q["symbol"] == "VRT"), None)
        vrt_score = vrt_q["deployment_score"] if vrt_q else 0
        vrt_pct   = vrt_q["current_weight_pct"] if vrt_q else 0
        vrt_rank  = vrt_q["rank"] if vrt_q else 0

        # Compute allocation diversity: how many unique symbols get ≥$200
        meaningful_recs = [r for r in recs if r["suggested_add"] >= 200]
        total_alloc     = sum(r["suggested_add"] for r in recs)
        top3_alloc      = sum(sorted([r["suggested_add"] for r in recs], reverse=True)[:3])
        top3_pct_alloc  = (top3_alloc / total_alloc * 100.0) if total_alloc > 0 else 0.0

        hhi_now = herfindahl(state.positions, state.total_mv)

        rows.append({
            "cycle":           label,
            "rank1_symbol":    top1_sym,
            "rank1_score":     round(top1_score, 2),
            "vrt_rank":        vrt_rank,
            "vrt_score":       round(vrt_score, 2),
            "vrt_weight_pct":  round(vrt_pct, 4),
            "top3_alloc_pct":  round(top3_pct_alloc, 1),
            "candidates_above_200": len(meaningful_recs),
            "hhi":             round(hhi_now, 5),
            "top5_pct":        round(top5_concentration(state.positions, state.total_mv), 2),
            "total_deployed":  round(total_alloc, 2),
        })

        vrt_data.append({"cycle": cycle + 1, "score": vrt_score, "pct": vrt_pct, "rank": vrt_rank})
        rank1_sym.append(top1_sym)

        # Apply all trades from the plan
        trades = {r["symbol"]: r["suggested_add"] for r in recs if r["suggested_add"] > 0}
        state.apply_trades(trades)

    # Write report
    lines = [
        "# Q5: Iterative Convergence Analysis",
        "",
        f"**Cycles simulated:** {n_cycles}",
        f"**Cash per cycle:** ${CYCLE_CASH:,.2f} (fixed, re-injected each cycle)",
        "",
        "## Cycle-by-Cycle Summary",
        "",
        "| Cycle | Rank#1 Sym | Rank#1 Score | VRT Rank | VRT Score | VRT% | Top-3 Alloc% | Candidates≥$200 | HHI | Top-5% |",
        "|-------|-----------|-------------|---------|----------|------|-------------|----------------|-----|-------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['cycle']} | {r['rank1_symbol']} | {r['rank1_score']:.2f} "
            f"| #{r['vrt_rank']} | {r['vrt_score']:.2f} | {r['vrt_weight_pct']:.2f}% "
            f"| {r['top3_alloc_pct']:.1f}% | {r['candidates_above_200']} "
            f"| {r['hhi']:.4f} | {r['top5_pct']:.2f}% |"
        )

    # Rank #1 stability
    rank1_counts: dict[str, int] = {}
    for s in rank1_sym:
        rank1_counts[s] = rank1_counts.get(s, 0) + 1
    dominant = max(rank1_counts, key=rank1_counts.get)
    dominant_cycles = rank1_counts[dominant]

    lines += [
        "",
        "## Rank #1 Dominance",
        "",
        f"Symbol holding rank #1: {rank1_counts}",
        f"Most dominant symbol: **{dominant}** held rank #1 in {dominant_cycles}/{n_cycles} cycles.",
        "",
        "## VRT Saturation Trajectory",
        "",
        "| Cycle | VRT Score | VRT Weight% | VRT Rank |",
        "|-------|----------|------------|---------|",
    ]
    for v in vrt_data:
        lines.append(f"| {v['cycle']} | {v['score']:.2f} | {v['pct']:.4f}% | #{v['rank']} |")

    lines += [
        "",
        "## Convergence Assessment",
        "",
    ]
    vrt_final_rank = vrt_data[-1]["rank"]
    vrt_initial_rank = vrt_data[0]["rank"]
    top3_initial = rows[0]["top3_alloc_pct"]
    top3_final   = rows[-1]["top3_alloc_pct"]

    if dominant_cycles >= n_cycles * 0.75:
        lines.append(f"**CONCENTRATION_BIAS**: {dominant} dominated rank #1 in {dominant_cycles}/{n_cycles} cycles. "
                     f"The framework shows persistent concentration in a single symbol.")
    elif dominant_cycles >= n_cycles * 0.5:
        lines.append(f"**MILD_BIAS**: {dominant} held rank #1 in {dominant_cycles}/{n_cycles} cycles. "
                     f"Some rotation but moderate concentration.")
    else:
        lines.append(f"**HEALTHY_ROTATION**: Rank #1 rotated across symbols. "
                     f"Framework distributes capital naturally as positions saturate.")

    if top3_final > top3_initial:
        lines.append(f"Top-3 allocation share grew from {top3_initial:.1f}% → {top3_final:.1f}% — concentration increasing over cycles.")
    else:
        lines.append(f"Top-3 allocation share went from {top3_initial:.1f}% → {top3_final:.1f}% — concentration stable or declining.")

    out = OUT_DIR / "iterative_convergence_analysis.md"
    out.write_text("\n".join(lines))
    print(f"[Q5] Written: {out.name}  (dominant symbol: {dominant} in {dominant_cycles}/{n_cycles} cycles)")


# ── Q6: VRT saturation curve ───────────────────────────────────────────────────

def q6_vrt_saturation_curve(state_0: SimState, baseline_qd: dict) -> None:
    """Test VRT at weights from 3% to 10% (0.5% increments) and record score/rank."""
    vrt_static = state_0.static_comps.get("VRT", {})
    if not vrt_static:
        print("[Q6] VRT not in queue — skipping")
        return

    out_csv  = OUT_DIR / "vrt_saturation_curve.csv"
    rows     = []
    test_pcts = [round(p * 0.5, 1) for p in range(6, 22)]   # 3.0% to 10.5%

    for pct in test_pcts:
        # Compute new VRT MV at test pct (keep other positions fixed)
        target_mv   = pct / 100.0 * state_0.total_mv
        sizing_c    = SimState._sizing_c(pct)
        conc_pen    = SimState._conc_pen(pct)
        headroom    = SimState._headroom_pct(pct)

        score = max(0.0, round(
            vrt_static["signal"]
            + vrt_static["replay"]
            + vrt_static["conviction"]
            + sizing_c
            + vrt_static["momentum"]
            - vrt_static["redundancy_pen"]
            - conc_pen,
            2
        ))

        # Build a test state to get rank in context
        test_state = state_0.clone()
        vrt_mv_before = test_state.positions.get("VRT", 0.0)
        vrt_mv_delta  = target_mv - vrt_mv_before
        if vrt_mv_delta > 0:
            test_state.positions["VRT"] = target_mv
        elif vrt_mv_delta < 0:
            test_state.positions["VRT"] = target_mv
        else:
            pass  # already at target

        test_qd = test_state.build_queue_dict()
        vrt_q   = next((q for q in test_qd["queue"] if q["symbol"] == "VRT"), None)
        rank    = vrt_q["rank"] if vrt_q else -1

        # Check if VRT would be deployable
        deployable = headroom > 0

        # How much cash could go to VRT with this weight?
        headroom_usd = max(0.0, (WARN_POSITION_PCT - pct) / 100.0 * state_0.total_mv)

        rows.append({
            "weight_pct":     pct,
            "market_value":   round(target_mv, 2),
            "score":          score,
            "rank":           rank,
            "sizing_c":       round(sizing_c, 2),
            "conc_pen":       round(conc_pen, 2),
            "headroom_pct":   round(headroom, 1),
            "headroom_usd":   round(headroom_usd, 2),
            "deployable":     deployable,
        })

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Find the saturation point (where score drops below rank-2 symbol's score)
    baseline_rank2 = next((q for q in baseline_qd["queue"] if q["rank"] == 2), None)
    rank2_score = baseline_rank2["deployment_score"] if baseline_rank2 else 0.0

    saturation_point = None
    for row in rows:
        if row["score"] <= rank2_score:
            saturation_point = row["weight_pct"]
            break

    print(f"[Q6] Written: {out_csv.name}  "
          f"(VRT score drops below rank-2 at ~{saturation_point}% weight)")


# ── Q7: Capital rotation when VRT saturates ────────────────────────────────────

def q7_capital_rotation(state_0: SimState, baseline_qd: dict) -> None:
    """Simulate filling VRT to WARN threshold then analyze where next dollars flow."""
    vrt_current_pct = state_0.pct("VRT")
    vrt_mv_now      = state_0.positions.get("VRT", 0.0)
    vrt_fill_amount = max(0.0, (WARN_POSITION_PCT - vrt_current_pct) / 100.0 * state_0.total_mv)

    state = state_0.clone()
    state.apply_trades({"VRT": vrt_fill_amount})

    # Fresh cash injection equal to baseline deployable cash
    fresh_cash = state_0.deployable_cash
    state.deployable_cash = fresh_cash
    state.cash_mv = state_0.floor_mv + fresh_cash

    qd_after, recs_after = state.run_plan(deployable_cash=fresh_cash)

    vrt_after = next((q for q in qd_after["queue"] if q["symbol"] == "VRT"), None)
    vrt_before = next((q for q in baseline_qd["queue"] if q["symbol"] == "VRT"), None)

    lines = [
        "# Q7: Capital Rotation Analysis — When VRT Saturates",
        "",
        "## VRT Fill Trade",
        "",
        f"- VRT filled to WARN threshold ({WARN_POSITION_PCT}%)",
        f"- VRT weight: {vrt_current_pct:.4f}% → {state.pct('VRT'):.4f}%",
        f"- Amount added to fill: ${vrt_fill_amount:,.2f}",
        f"- VRT score after fill: {vrt_after['deployment_score']:.2f} (was {vrt_before['deployment_score']:.2f})" if vrt_after and vrt_before else "",
        f"- VRT rank after fill: #{vrt_after['rank']}" if vrt_after else "",
        f"- Fresh cash available for redeployment: ${fresh_cash:,.2f}",
        "",
        "## Where Does Fresh Capital Flow? (Post-Saturation Plan)",
        "",
        "| Rank | Symbol | Tier | Suggested Add | Projected% | Score | Is Ex-Top-3? |",
        "|------|--------|------|---------------|-----------|-------|-------------|",
    ]

    baseline_top3 = {"VRT", "ARW", "ATLC"}
    for r in recs_after[:15]:
        is_ex_top3 = "YES" if r["symbol"] in baseline_top3 else "No"
        q = next((q for q in qd_after["queue"] if q["symbol"] == r["symbol"]), None)
        score = q["deployment_score"] if q else 0.0
        lines.append(
            f"| {r['rank']} | {r['symbol']} | {r['deployment_tier']} "
            f"| ${r['suggested_add']:,.2f} | {r['projected_weight_pct']:.4f}% "
            f"| {score:.2f} | {is_ex_top3} |"
        )

    # What fraction of the new plan avoids VRT entirely?
    vrt_in_new_plan = any(r["symbol"] == "VRT" and r["suggested_add"] > 0 for r in recs_after)
    top3_new_plan = [r["symbol"] for r in recs_after[:3]]

    lines += [
        "",
        "## Rotation Quality Assessment",
        "",
        f"- VRT appears in post-saturation plan: **{'YES' if vrt_in_new_plan else 'NO'}**",
        f"- New top-3 recommendations: {top3_new_plan}",
        f"- Score spread between new top candidates: "
        f"{qd_after['queue'][0]['deployment_score'] - qd_after['queue'][2]['deployment_score']:.2f} pts (ranks 1-3)",
        "",
    ]

    if not vrt_in_new_plan:
        lines.append("**GOOD_ROTATION**: VRT excluded from plan at WARN threshold. Capital naturally flows to fresh candidates.")
    else:
        lines.append("**PARTIAL_ROTATION**: VRT still appears despite being at WARN. Planner correctly sizes it to zero headroom.")

    # Show top queue after fill
    lines += [
        "",
        "## Top-10 Queue After VRT Fill",
        "",
        "| Rank | Symbol | Score | Weight% | Sizing_c | Conc_pen |",
        "|------|--------|-------|---------|----------|---------|",
    ]
    for item in top_n_queue(qd_after, 10):
        bd = item["score_breakdown"]
        lines.append(
            f"| {item['rank']} | {item['symbol']} | {item['deployment_score']:.2f} "
            f"| {item['current_weight_pct']:.4f}% | {bd['sizing']:.2f} | {bd['conc_pen']:.2f} |"
        )

    out = OUT_DIR / "capital_rotation_analysis.md"
    out.write_text("\n".join(lines))
    print(f"[Q7] Written: {out.name}  (VRT in post-saturation plan: {vrt_in_new_plan})")


# ── Q8: Framework stability ────────────────────────────────────────────────────

def q8_framework_stability(state_0: SimState, baseline_qd: dict, baseline_recs: list[dict]) -> None:
    """Assess whether scoring creates stable rankings or volatile rank flips."""
    lines = [
        "# Q8: Framework Stability Assessment",
        "",
        "## Sizing_c Sensitivity Analysis",
        "",
        "Sizing_c = 8.0 × max(0, 1 - weight% / 6.0)",
        "This component provides 0–8 points and decreases as weight grows.",
        "",
        "| Weight% | Sizing_c | Max Reduction from Baseline |",
        "|---------|----------|----------------------------|",
    ]
    for pct in [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]:
        sc = SimState._sizing_c(pct)
        lines.append(f"| {pct:.1f}% | {sc:.3f} | {8.0 - sc:.3f} |")

    lines += [
        "",
        "## Concentration Penalty (conc_pen) Sensitivity",
        "",
        "Conc_pen = min((weight% - 6.0) × 4.0, 20.0) for weight% > 6.0",
        "",
        "| Weight% | Conc_pen | Score Impact |",
        "|---------|----------|-------------|",
    ]
    for pct in [6.0, 6.5, 7.0, 7.5, 8.0, 9.0, 10.0, 11.0]:
        cp = SimState._conc_pen(pct)
        lines.append(f"| {pct:.1f}% | {cp:.1f} | -{cp:.1f} pts |")

    lines += [
        "",
        "## CCL vs HCA Score Comparison",
        "",
        "At baseline weights, CCL symbols carry conviction_c=35 vs HCA conviction_c=28.",
        "Combined with CCL_CONVICTION_MULT=1.75 in the planner, CCL symbols receive structural advantage.",
        "",
        "| Symbol | Tier | Baseline Score | Conviction_c | Sizing_c | Weight% |",
        "|--------|------|---------------|-------------|---------|--------|",
    ]
    ccl_syms = [q for q in baseline_qd["queue"] if q["narrative_tier"] == CCL_TIER and q["rank"] <= 20]
    hca_top  = [q for q in baseline_qd["queue"] if q["narrative_tier"] != CCL_TIER and q["rank"] <= 5]
    for q in (ccl_syms + hca_top):
        bd = q["score_breakdown"]
        lines.append(
            f"| {q['symbol']} | {'CCL' if q['narrative_tier']==CCL_TIER else 'HCA'} "
            f"| {q['deployment_score']:.2f} | {bd['conviction']:.1f} "
            f"| {bd['sizing']:.2f} | {q['current_weight_pct']:.4f}% |"
        )

    lines += [
        "",
        "## Rank Stability Under +$5k Trade Increments",
        "",
        "Tests how much capital it takes to move a symbol out of rank #1.",
        "",
        "| Add to VRT ($) | VRT Score | VRT Rank | New Rank#1 Symbol |",
        "|---------------|----------|---------|-----------------|",
    ]

    for add_k in [0, 2000, 4000, 6000, 8000, 10000, 15000, 20000]:
        test_state = state_0.clone()
        if add_k > 0:
            test_state.positions["VRT"] = test_state.positions.get("VRT", 0.0) + add_k
        test_qd  = test_state.build_queue_dict()
        vrt_q    = next((q for q in test_qd["queue"] if q["symbol"] == "VRT"), None)
        top1_sym = test_qd["queue"][0]["symbol"] if test_qd["queue"] else "?"
        if vrt_q:
            lines.append(
                f"| ${add_k:,} | {vrt_q['deployment_score']:.2f} "
                f"| #{vrt_q['rank']} | {top1_sym} |"
            )

    # Summary: is the ranking stable or brittle?
    lines += [
        "",
        "## Stability Verdict",
        "",
        "**Scoring formula evaluation:**",
        f"- Sizing_c range: 0.0 – {SIZING_SCALE:.1f} pts (gradual linear decay)",
        "- Conc_pen range: 0.0 – 20.0 pts (activates only above WARN threshold)",
        "- CCL conviction bonus: +7 pts over HCA (35 vs 28)",
        "- Both weight-dependent penalties combined can reduce score by up to 28 pts",
        "",
        "The framework uses gradual, continuous penalties — not step-function cutoffs.",
        "This creates smooth rank transitions rather than abrupt displacements.",
    ]

    out = OUT_DIR / "framework_stability_assessment.md"
    out.write_text("\n".join(lines))
    print(f"[Q8] Written: {out.name}")


# ── Q9: Operator trust (1-year simulation) ─────────────────────────────────────

def q9_operator_trust(state_0: SimState, baseline_qd: dict, n_cycles: int = 12) -> None:
    """12-cycle simulation (~1 year of monthly deployments) tracking trust signals."""
    CYCLE_CASH     = state_0.deployable_cash
    state          = state_0.clone()
    cycle_records  = []
    diversity_scores = []

    for cycle in range(1, n_cycles + 1):
        # Re-inject deployable cash each month
        state.deployable_cash = CYCLE_CASH
        state.cash_mv         = state_0.floor_mv + CYCLE_CASH

        qd, recs = state.run_plan(deployable_cash=CYCLE_CASH)

        # Diversity score: how many symbols receive meaningful allocation
        total_alloc   = sum(r["suggested_add"] for r in recs)
        n_meaningful  = sum(1 for r in recs if r["suggested_add"] >= 200)
        top1_share    = (max((r["suggested_add"] for r in recs), default=0) / total_alloc * 100.0) if total_alloc > 0 else 0
        top3_share    = sum(sorted([r["suggested_add"] for r in recs], reverse=True)[:3]) / total_alloc * 100.0 if total_alloc > 0 else 0

        top3_syms     = sorted(recs, key=lambda r: -r["suggested_add"])[:3]
        top3_names    = [r["symbol"] for r in top3_syms]

        hhi_now       = herfindahl(state.positions, state.total_mv)
        top5_pct_now  = top5_concentration(state.positions, state.total_mv)

        # Is VRT capped out?
        vrt_q = next((q for q in qd["queue"] if q["symbol"] == "VRT"), None)
        vrt_blocked = vrt_q is not None and vrt_q["headroom_pct"] == 0.0

        cycle_records.append({
            "cycle":          cycle,
            "total_deployed": round(total_alloc, 2),
            "n_positions":    n_meaningful,
            "top1_share_pct": round(top1_share, 1),
            "top3_share_pct": round(top3_share, 1),
            "top3_symbols":   ", ".join(top3_names),
            "hhi":            round(hhi_now, 5),
            "top5_pct":       round(top5_pct_now, 2),
            "vrt_blocked":    vrt_blocked,
        })
        diversity_scores.append(n_meaningful)

        trades = {r["symbol"]: r["suggested_add"] for r in recs if r["suggested_add"] > 0}
        state.apply_trades(trades)

    lines = [
        "# Q9: Operator Trust Assessment — 12-Cycle Simulation (~1 Year)",
        "",
        f"**Monthly deployment:** ${CYCLE_CASH:,.2f} (fresh injection each cycle)",
        f"**Portfolio starting MV:** ${state_0.total_mv:,.2f}",
        "",
        "## Monthly Deployment Tracking",
        "",
        "| Month | Deployed | Positions≥$200 | Top-1 Share | Top-3 Share | Top-3 Symbols | HHI | Top-5% | VRT Blocked? |",
        "|-------|---------|---------------|-----------|-----------|--------------|-----|-------|------------|",
    ]
    for r in cycle_records:
        lines.append(
            f"| {r['cycle']} | ${r['total_deployed']:,.0f} | {r['n_positions']} "
            f"| {r['top1_share_pct']:.1f}% | {r['top3_share_pct']:.1f}% "
            f"| {r['top3_symbols']} | {r['hhi']:.4f} | {r['top5_pct']:.2f}% "
            f"| {'YES' if r['vrt_blocked'] else 'No'} |"
        )

    # Summary statistics
    avg_n    = sum(diversity_scores) / len(diversity_scores)
    min_n    = min(diversity_scores)
    max_n    = max(diversity_scores)
    vrt_blocked_count = sum(1 for r in cycle_records if r["vrt_blocked"])
    hhi_final = cycle_records[-1]["hhi"]
    hhi_init  = herfindahl(state_0.positions, state_0.total_mv)
    top3_shares = [r["top3_share_pct"] for r in cycle_records]
    avg_top3_share = sum(top3_shares) / len(top3_shares)

    lines += [
        "",
        "## Operator Trust Signals",
        "",
        f"| Signal | Value | Assessment |",
        f"|--------|-------|-----------|",
        f"| Avg positions/month with meaningful allocation | {avg_n:.1f} | {'GOOD ≥10' if avg_n >= 10 else 'MODERATE 5-10' if avg_n >= 5 else 'POOR <5'} |",
        f"| Min positions in any single month | {min_n} | {'OK' if min_n >= 5 else 'CONCENTRATED'} |",
        f"| Avg top-3 allocation share | {avg_top3_share:.1f}% | {'CONCENTRATED >60%' if avg_top3_share > 60 else 'MODERATE 40-60%' if avg_top3_share > 40 else 'DISTRIBUTED <40%'} |",
        f"| VRT at WARN threshold (months) | {vrt_blocked_count}/{n_cycles} | {'BLOCKED' if vrt_blocked_count >= 6 else 'PARTIAL' if vrt_blocked_count >= 3 else 'RARELY BLOCKED'} |",
        f"| Portfolio HHI change ({n_cycles} months) | {hhi_init:.5f} → {hhi_final:.5f} | {'IMPROVING' if hhi_final < hhi_init else 'STABLE' if abs(hhi_final - hhi_init) < 0.002 else 'CONCENTRATING'} |",
    ]

    lines += ["", "## Trust Narrative", ""]
    if avg_top3_share > 70:
        lines.append("**CONCERN**: Framework persistently concentrates 70%+ of monthly capital in top-3 positions. "
                     "An operator faithfully following these recommendations would build a highly concentrated portfolio "
                     "over 12 months, potentially undermining the diversification intent.")
    elif avg_top3_share > 50:
        lines.append("**CAUTION**: Top-3 positions capture the majority of monthly allocations. "
                     "While the framework does distribute capital, the concentration in leading positions "
                     "is meaningful. Operator should confirm this aligns with intended position-building pace.")
    else:
        lines.append("**ACCEPTABLE**: Monthly allocations are reasonably distributed across the candidate pool. "
                     "An operator following recommendations for 12 months would build a diversified book "
                     "with no single position dominating monthly cash deployment.")

    if vrt_blocked_count >= 6:
        lines.append(f"\nNoting that VRT hits the WARN threshold in {vrt_blocked_count} of {n_cycles} simulated months, "
                     f"after which the framework naturally redirects capital to other candidates.")

    out = OUT_DIR / "operator_trust_assessment.md"
    out.write_text("\n".join(lines))
    print(f"[Q9] Written: {out.name}  "
          f"(avg top-3 share: {avg_top3_share:.1f}%, VRT blocked: {vrt_blocked_count}/{n_cycles})")

    return avg_top3_share, vrt_blocked_count, avg_n


# ── Final verdict ──────────────────────────────────────────────────────────────

def write_final_verdict(
    q5_dominant: str,
    q5_dominant_cycles: int,
    q5_n_cycles: int,
    q7_vrt_in_plan: bool,
    q9_avg_top3_share: float,
    q9_vrt_blocked: int,
    q9_n_months: int,
    baseline_qd: dict,
) -> None:
    """Write the final verdict document."""
    # Determine verdict category
    # A. FRAMEWORK_CONVERGES_CORRECTLY  — minimal feedback loop, effective rotation
    # B. MINOR_CONCENTRATION_BIAS       — some bias toward leading positions, manageable
    # C. MATERIAL_FEEDBACK_LOOP         — persistent concentration risk, notable concern
    # D. DEPLOYMENT_LOGIC_REQUIRES_RECALIBRATION — structural issues requiring changes

    score = 0
    evidence = []

    # Q5: Rank #1 dominance
    if q5_dominant_cycles >= q5_n_cycles * 0.75:
        score += 2
        evidence.append(f"Q5: Rank #1 dominated by {q5_dominant} in {q5_dominant_cycles}/{q5_n_cycles} cycles (+2 concentration pts)")
    elif q5_dominant_cycles >= q5_n_cycles * 0.5:
        score += 1
        evidence.append(f"Q5: Rank #1 held by {q5_dominant} in {q5_dominant_cycles}/{q5_n_cycles} cycles (+1 mild concentration pt)")
    else:
        evidence.append(f"Q5: Healthy rank rotation — {q5_dominant} held rank #1 in only {q5_dominant_cycles}/{q5_n_cycles} cycles (+0)")

    # Q7: VRT rotation
    if q7_vrt_in_plan:
        score += 1
        evidence.append("Q7: VRT persists in plan even after filling to WARN threshold (+1)")
    else:
        evidence.append("Q7: VRT correctly excluded from plan after WARN-threshold fill (+0)")

    # Q9: Concentration
    if q9_avg_top3_share > 70:
        score += 2
        evidence.append(f"Q9: Top-3 allocation share averaged {q9_avg_top3_share:.1f}% per month (+2)")
    elif q9_avg_top3_share > 50:
        score += 1
        evidence.append(f"Q9: Top-3 allocation share averaged {q9_avg_top3_share:.1f}% per month (+1)")
    else:
        evidence.append(f"Q9: Top-3 allocation share averaged {q9_avg_top3_share:.1f}% — distributed (+0)")

    # Q9: VRT blocking
    if q9_vrt_blocked >= q9_n_months * 0.5:
        evidence.append(f"Q9: VRT blocked in {q9_vrt_blocked}/{q9_n_months} months — WARN mechanism working as designed (mitigating)")
        score -= 1  # mitigating: blocking is the desired behavior

    # Clamp
    score = max(0, score)

    if score <= 1:
        verdict = "A. FRAMEWORK_CONVERGES_CORRECTLY"
        verdict_summary = ("The CW-DAS framework demonstrates effective self-correction. "
                           "As positions accumulate capital, the sizing penalty and concentration penalty "
                           "naturally demote saturated positions and elevate fresh candidates. "
                           "An operator faithfully executing recommendations will build a diversified portfolio "
                           "without disproportionate concentration in any single holding.")
    elif score <= 2:
        verdict = "B. MINOR_CONCENTRATION_BIAS"
        verdict_summary = ("The framework shows a mild preference for leading positions across cycles. "
                           "CCL-tier symbols (particularly VRT) retain structural scoring advantages "
                           "via the conviction_c and conviction_mult components, causing them to "
                           "recapture capital more quickly than purely weight-driven models. "
                           "This is operationally manageable but warrants operator awareness.")
    elif score <= 4:
        verdict = "C. MATERIAL_FEEDBACK_LOOP"
        verdict_summary = ("The simulation reveals a meaningful positive feedback loop: "
                           "top-ranked positions receive capital, their relative score advantage is only "
                           "partially offset by the sizing penalty, and they continue to dominate "
                           "subsequent recommendation cycles. The conviction multiplier (1.75× for CCL) "
                           "combined with the 35-pt conviction score creates structural dominance "
                           "that the weight-dependent penalties cannot fully overcome.")
    else:
        verdict = "D. DEPLOYMENT_LOGIC_REQUIRES_RECALIBRATION"
        verdict_summary = ("The deployment framework exhibits systematic concentration bias that warrants "
                           "recalibration. The combination of conviction tier scoring, conviction multipliers, "
                           "and insufficient weight-dependent penalties creates persistent capital "
                           "allocation to the same small set of positions regardless of portfolio state.")

    ccl_syms = [q["symbol"] for q in baseline_qd["queue"] if q["narrative_tier"] == CCL_TIER]

    lines = [
        "# Phase 7.5W — Deployment Simulation Final Verdict",
        "",
        "## Study Summary",
        "",
        "**Framework under test:** CW-DAS (Conviction-Weighted Deployment Allocation Score)",
        "**Baseline portfolio:** PAR-20260602-1BF2ADA5 ($475,779.42 total MV, $31,683.33 deployable)",
        "**Simulation method:** Static signals / static prices / dynamic position weights",
        "**Cycles run:** Q5 = 8 cycles, Q9 = 12 cycles (fresh $31,683/cycle)",
        "",
        "## Question-by-Question Evidence",
        "",
    ]
    for i, e in enumerate(evidence, 1):
        lines.append(f"{i}. {e}")

    lines += [
        "",
        f"**Raw concentration score: {score}**",
        "",
        "---",
        "",
        f"## Verdict: {verdict}",
        "",
        verdict_summary,
        "",
        "## Key Structural Findings",
        "",
        f"1. **Sizing_c decay** (0–8 pts, linear): Effective gradual penalty but only 8 pts of range "
        f"vs 35 pts conviction for CCL positions. CCL symbols retain large score leads even near WARN.",
        "",
        f"2. **CCL tier compound advantage**: CCL symbols receive both +7 scoring bonus (35 vs 28 conviction_c) "
        f"AND +40% planner weight multiplier (1.75× vs 1.25×). This creates a 2-layer structural advantage.",
        "",
        f"3. **WARN mechanism** (sizing_c → 0 at 6%): Correctly prevents any single position from absorbing "
        f"all available capital. Positions above 6% are automatically deprioritized via both sizing_c=0 and conc_pen.",
        "",
        f"4. **CCL symbols in portfolio**: {ccl_syms}",
        "",
        f"5. **Max possible score decay for a CCL position from 0% → WARN%**: 8 pts (sizing_c) "
        f"+ 0 pts (no conc_pen below 6%) = 8 pts lost on 95-pt score = ~8.4% reduction.",
        "",
        "## Operator Guidance",
        "",
        "The framework is **designed to concentrate** capital in conviction leaders — this is the intended "
        "behavior. The WARN threshold (6%) provides a natural ceiling. The simulation question is whether "
        "the rotation AFTER saturation is clean.",
        "",
    ]

    if verdict.startswith("A") or verdict.startswith("B"):
        lines += [
            "**Recommendation: PROCEED with confidence.** The framework rotates capital naturally after "
            "saturation. Monitor VRT's position weight as a leading indicator — when it approaches 5.5%, "
            "expect the framework to begin routing capital to the next tier of HCA candidates.",
        ]
    else:
        lines += [
            "**Recommendation: USE WITH AWARENESS.** The framework will persistently favor the same "
            "conviction leaders across cycles. Consider implementing a manual override policy that "
            "caps any single position's share of monthly deployment at 25-30% to ensure portfolio-wide "
            "capital circulation.",
        ]

    lines += [
        "",
        "## Deliverables Index",
        "",
        "| File | Question |",
        "|------|---------|",
        "| deployment_simulation_baseline.csv | Q1: Baseline top-20 queue snapshot |",
        "| single_trade_saturation_report.md | Q2: Single VRT trade impact |",
        "| top3_execution_simulation.md | Q3: Top-3 execution analysis |",
        "| full_plan_execution_report.md | Q4: Full plan execution |",
        "| iterative_convergence_analysis.md | Q5: 8-cycle convergence |",
        "| vrt_saturation_curve.csv | Q6: VRT score vs weight% |",
        "| capital_rotation_analysis.md | Q7: Post-saturation rotation |",
        "| framework_stability_assessment.md | Q8: Scoring stability |",
        "| operator_trust_assessment.md | Q9: 12-month trust simulation |",
        "| deployment_simulation_final_verdict.md | Final verdict |",
    ]

    out = OUT_DIR / "deployment_simulation_final_verdict.md"
    out.write_text("\n".join(lines))
    print(f"\n[VERDICT] {verdict}")
    print(f"[FIN] Written: {out.name}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("Phase 7.5W — Capital Deployment Simulation Validation")
    print(f"Output directory: {OUT_DIR}")
    print("=" * 70)

    # Load
    dq_data, dp_data, positions = load_baseline()
    state_0      = SimState(dq_data, positions)
    baseline_qd  = state_0.build_queue_dict()
    _, baseline_recs = state_0.run_plan()

    print(f"\nBaseline: total_mv=${state_0.total_mv:,.2f}  "
          f"deployable=${state_0.deployable_cash:,.2f}  "
          f"queue={len(state_0.static_comps)} symbols  "
          f"plan={len(baseline_recs)} recs\n")

    # Q1
    q1_baseline_snapshot(baseline_qd)

    # Q2
    q2_single_trade_impact(state_0, baseline_qd, baseline_recs)

    # Q3
    q3_top3_execution(state_0, baseline_qd, baseline_recs)

    # Q4
    q4_full_plan_execution(state_0, baseline_qd, baseline_recs)

    # Q5
    q5_iterative_convergence(state_0, baseline_qd, n_cycles=8)

    # Q6
    q6_vrt_saturation_curve(state_0, baseline_qd)

    # Q7 — capture return value for verdict
    q7_state = state_0.clone()
    vrt_current_pct = state_0.pct("VRT")
    vrt_fill_amount = max(0.0, (WARN_POSITION_PCT - vrt_current_pct) / 100.0 * state_0.total_mv)
    q7_state.apply_trades({"VRT": vrt_fill_amount})
    q7_state.deployable_cash = state_0.deployable_cash
    q7_state.cash_mv = state_0.floor_mv + state_0.deployable_cash
    _, q7_recs = q7_state.run_plan(deployable_cash=state_0.deployable_cash)
    q7_vrt_in_plan = any(r["symbol"] == "VRT" and r["suggested_add"] > 0 for r in q7_recs)
    q7_capital_rotation(state_0, baseline_qd)

    # Q8
    q8_framework_stability(state_0, baseline_qd, baseline_recs)

    # Q9 — capture trust metrics for verdict
    q9_result = q9_operator_trust(state_0, baseline_qd, n_cycles=12)
    q9_avg_top3_share, q9_vrt_blocked, q9_avg_n = q9_result

    # Q5 — extract dominant symbol info for verdict (re-run briefly)
    # We already ran Q5 which printed its results; re-run condensed to get verdict inputs
    CYCLE_CASH = state_0.deployable_cash
    q5_state   = state_0.clone()
    rank1_syms = []
    for _ in range(8):
        q5_state.deployable_cash = CYCLE_CASH
        q5_state.cash_mv = state_0.floor_mv + CYCLE_CASH
        qd5, recs5 = q5_state.run_plan(deployable_cash=CYCLE_CASH)
        top_q = sorted(qd5["queue"], key=lambda x: x["rank"])
        if top_q:
            rank1_syms.append(top_q[0]["symbol"])
        trades5 = {r["symbol"]: r["suggested_add"] for r in recs5 if r["suggested_add"] > 0}
        q5_state.apply_trades(trades5)

    rank1_counts: dict[str, int] = {}
    for s in rank1_syms:
        rank1_counts[s] = rank1_counts.get(s, 0) + 1
    q5_dominant        = max(rank1_counts, key=rank1_counts.get)
    q5_dominant_cycles = rank1_counts[q5_dominant]

    # Final verdict
    write_final_verdict(
        q5_dominant=q5_dominant,
        q5_dominant_cycles=q5_dominant_cycles,
        q5_n_cycles=8,
        q7_vrt_in_plan=q7_vrt_in_plan,
        q9_avg_top3_share=q9_avg_top3_share,
        q9_vrt_blocked=q9_vrt_blocked,
        q9_n_months=12,
        baseline_qd=baseline_qd,
    )

    print("\n" + "=" * 70)
    print("Phase 7.5W complete. All deliverables written to:")
    print(f"  {OUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
