"""Phase 7.4C — Conviction Model Validation.

Validates whether the Deployment Attractiveness Score (DAS) aligns with
concentrated-alpha portfolio philosophy. Produces conviction_model_validation_report.md.

Analysis only. No formula changes.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

# ─── Re-use data pipeline from 7.4A ─────────────────────────────────────────

from phase_7_4a_analysis import (
    _pick_run,
    _load_csv_dicts,
    _load_json,
    _load_replay_index,
    _build_holdings,
    _build_overlays,
    _build_alignment,
    _build_sti_index,
    step1_cash,
    step2_conviction_universe,
    step3_das,
    RUN_ROOT,
    WARN_POSITION_PCT,
)

# ─── Constants ───────────────────────────────────────────────────────────────

TIER_RANK = {
    "CORE_CONVICTION_LEADER": 1,
    "HIGH_CONVICTION_ANCHOR": 2,
}
TIER_SHORT = {
    "CORE_CONVICTION_LEADER": "CCL",
    "HIGH_CONVICTION_ANCHOR": "HCA",
}
TOP_N = 20  # candidates to analyze


# ─── Statistical helpers ─────────────────────────────────────────────────────

def _rank_list(values: list[float], descending: bool = True) -> list[int]:
    """Return ordinal ranks (1 = best) with average rank for ties."""
    indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=descending)
    ranks = [0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) - 1 and indexed[j][1] == indexed[j + 1][1]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_rho(a: list[float], b: list[float]) -> float:
    """Spearman rank correlation coefficient."""
    n = len(a)
    if n < 2:
        return float("nan")
    ra = _rank_list(a)
    rb = _rank_list(b)
    d_sq = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1.0 - (6.0 * d_sq) / (n * (n ** 2 - 1))


def spearman_rho_between_ranks(ra: list[float], rb: list[float]) -> float:
    """Spearman rho from pre-computed ranks."""
    n = len(ra)
    if n < 2:
        return float("nan")
    d_sq = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1.0 - (6.0 * d_sq) / (n * (n ** 2 - 1))


# ─── Build conviction ranking (baseline) ─────────────────────────────────────

def conviction_rank(entry: dict) -> tuple:
    """Sort key for 'pure conviction' ordering.

    Priority:
      1. Tier: CCL before HCA (tier_rank 1 < 2)
      2. Composite score descending
      3. Replay support (yes before no)
      4. Symbol (deterministic tiebreak)
    """
    return (
        TIER_RANK.get(entry["sti_tier"], 9),
        -(entry["composite"] or 0),
        0 if entry["replay"] else 1,
        entry["symbol"],
    )


# ─── Sizing headroom as % of total DAS ───────────────────────────────────────

def _headroom_share(entry: dict) -> float:
    """What fraction of DAS came from sizing headroom?"""
    das = entry["das"]
    if das <= 0:
        return 0.0
    return entry["das_breakdown"]["sizing"] / das * 100.0


def _conviction_share(entry: dict) -> float:
    das = entry["das"]
    if das <= 0:
        return 0.0
    return entry["das_breakdown"]["conviction"] / das * 100.0


# ─── Formatting helpers ───────────────────────────────────────────────────────

def _fmt_pct(v): return f"{float(v):.2f}%" if v is not None else "-"
def _fmt_score(v): return f"{float(v):.3f}" if v is not None else "-"
def _fmt_rho(v): return f"{v:.4f}"
def _fmt_contrib(v): return f"{float(v):.1f}"


# ─── Main analysis ────────────────────────────────────────────────────────────

def run_validation() -> tuple[list[dict], dict]:
    """Return (enriched_universe, stats_dict)."""
    run_id  = _pick_run()
    run_dir = RUN_ROOT / run_id
    print(f"Using run: {run_id}")

    snap      = _load_json(run_dir / "snapshot.json")
    h_rows    = _load_csv_dicts(run_dir / "holdings.csv")
    o_rows    = _load_csv_dicts(run_dir / "security_overlays.csv")
    a_rows    = _load_csv_dicts(run_dir / "alignment.csv")
    holdings  = _build_holdings(h_rows)
    overlays  = _build_overlays(o_rows)
    alignment = _build_alignment(a_rows)
    replay_idx = _load_replay_index()

    snap_id   = snap["portfolio_snapshot_id"]
    sti_index = _build_sti_index(snap_id, holdings, overlays, alignment)

    ow_nodes = {
        r["node_key"] for r in a_rows
        if r.get("drift_direction") == "OVERWEIGHT"
        and r.get("severity") in ("HIGH", "MODERATE")
    }

    active_rows = [
        h for h in h_rows
        if h.get("operational_state", "ACTIVE_POSITION")
        not in ("EXCLUDED", "ACCOUNTING_ADJUSTMENT", "CLOSED_POSITION")
    ]

    universe = step2_conviction_universe(active_rows, o_rows, sti_index, replay_idx)
    universe = step3_das(universe, ow_nodes, active_rows)

    # Sort by DAS descending → DAS rank
    universe_das = sorted(universe, key=lambda x: (-x["das"], -(x["composite"] or 0)))
    for i, e in enumerate(universe_das, 1):
        e["das_rank"] = i

    # Sort by conviction → conviction rank
    universe_conv = sorted(universe, key=conviction_rank)
    for i, e in enumerate(universe_conv, 1):
        e["conv_rank"] = i

    # Merge back
    by_sym = {e["symbol"]: e for e in universe_das}
    for e in universe_conv:
        by_sym[e["symbol"]]["conv_rank"] = e["conv_rank"]

    # Top-N by DAS
    top = universe_das[:TOP_N]
    n   = len(top)

    # Enrich: headroom %, conviction %, rank delta
    for e in top:
        bd = e["das_breakdown"]
        e["headroom_share_pct"] = _headroom_share(e)
        e["conviction_share_pct"] = _conviction_share(e)
        e["rank_delta"] = e["das_rank"] - e["conv_rank"]
        e["tier_num"] = TIER_RANK.get(e["sti_tier"], 9)
        e["tier_short"] = TIER_SHORT.get(e["sti_tier"], e["sti_tier"][:6])

    # ── Spearman correlations (over ALL conviction holdings, not just top-N) ──
    all_syms = list(by_sym.values())
    das_vals  = [e["das"]             for e in all_syms]
    comp_vals = [e["composite"] or 0  for e in all_syms]
    tier_vals = [e["tier_num"]        for e in all_syms]
    head_vals = [e["das_breakdown"]["sizing"] for e in all_syms]

    rho_das_comp   = spearman_rho(das_vals, comp_vals)
    rho_das_tier   = spearman_rho(das_vals, tier_vals)    # higher tier_num = lower conviction
    rho_das_head   = spearman_rho(das_vals, head_vals)
    rho_comp_head  = spearman_rho(comp_vals, head_vals)

    # Also run on top-N only
    top_das   = [e["das"]             for e in top]
    top_comp  = [e["composite"] or 0  for e in top]
    top_tier  = [e["tier_num"]        for e in top]
    top_head  = [e["das_breakdown"]["sizing"] for e in top]

    rho_top_das_comp = spearman_rho(top_das, top_comp)
    rho_top_das_tier = spearman_rho(top_das, top_tier)
    rho_top_das_head = spearman_rho(top_das, top_head)

    # ── Disagreement cases: |rank_delta| >= 3 or CCL below HCA ──────────────
    disagreements = []
    for e in universe_das:
        delta = abs(e.get("rank_delta", 0))
        ccl_below_hca = (
            e["sti_tier"] == "HIGH_CONVICTION_ANCHOR"
            and e["das_rank"] < e["conv_rank"]
            and e["conv_rank"] - e["das_rank"] >= 3
        )
        hca_over_ccl = (
            e["sti_tier"] == "HIGH_CONVICTION_ANCHOR"
            and e["das_rank"] <= 3
            and any(
                o["sti_tier"] == "CORE_CONVICTION_LEADER"
                and o["das_rank"] > e["das_rank"]
                for o in universe_das
            )
        )
        if delta >= 3 or hca_over_ccl:
            disagreements.append(e)

    # ── Component share summary ───────────────────────────────────────────────
    all_das_sum = sum(e["das"] for e in top if e["das"] > 0)

    def _avg_share(component: str) -> float:
        vals = [e["das_breakdown"][component] for e in top if e["das"] > 0]
        return sum(vals) / len(vals) if vals else 0.0

    def _avg_share_pct(component: str) -> float:
        shares = [
            e["das_breakdown"][component] / e["das"] * 100.0
            for e in top if e["das"] > 0
        ]
        return sum(shares) / len(shares) if shares else 0.0

    avg_shares_pts = {
        "signal":         _avg_share("signal"),
        "replay":         _avg_share("replay"),
        "conviction":     _avg_share("conviction"),
        "sizing":         _avg_share("sizing"),
        "momentum":       _avg_share("momentum"),
        "redundancy_pen": _avg_share("redundancy_pen"),
        "conc_pen":       _avg_share("conc_pen"),
    }
    avg_shares_pct = {k: _avg_share_pct(k) for k in avg_shares_pts}

    stats = {
        "run_id":              run_id,
        "n_total":             len(universe_das),
        "n_top":               n,
        "rho_das_comp":        rho_das_comp,
        "rho_das_tier":        rho_das_tier,
        "rho_das_head":        rho_das_head,
        "rho_comp_head":       rho_comp_head,
        "rho_top_das_comp":    rho_top_das_comp,
        "rho_top_das_tier":    rho_top_das_tier,
        "rho_top_das_head":    rho_top_das_head,
        "avg_shares_pts":      avg_shares_pts,
        "avg_shares_pct":      avg_shares_pct,
        "disagreements":       disagreements,
        "ccl_symbols":         [e["symbol"] for e in universe_das if e["sti_tier"] == "CORE_CONVICTION_LEADER"],
        "hca_ranked_above_ccl":[
            e for e in universe_das[:6]
            if e["sti_tier"] == "HIGH_CONVICTION_ANCHOR"
        ],
    }

    return top, stats


# ─── Report generation ────────────────────────────────────────────────────────

def generate_report(top: list[dict], stats: dict) -> str:
    lines: list[str] = []
    w = lines.append

    run_id = stats["run_id"]
    n      = stats["n_top"]

    w("# Phase 7.4C - Conviction Model Validation Report")
    w("")
    w(f"**Analysis Run:** `{run_id}`  ")
    w(f"**Conviction universe:** {stats['n_total']} holdings  ")
    w(f"**Top-N analyzed:** {n}  ")
    w("")
    w("> Analysis only. No formula changes. Objective: determine whether DAS")
    w("> over-weights sizing headroom relative to conviction, replay, and composite.")
    w("")

    # ── Observation ──────────────────────────────────────────────────────────
    w("---")
    w("")
    w("## Observation")
    w("")
    w("In the Phase 7.4A output, `ARW`, `PSX`, and `SNX` (all HCA-tier, small positions)")
    w("outrank `MU`, `VRT`, `AEIS`, and `CVE` (CCL-tier or larger positions). This")
    w("raises the question: is the sizing headroom component over-represented in DAS?")
    w("")
    w("The sizing headroom component is defined as:")
    w("")
    w("```")
    w(f"sizing_c = 15.0 x max(0.0, 1.0 - current_pct / {WARN_POSITION_PCT})")
    w("```")
    w("")
    w("A position at 0% weight earns full 15 pts. At 6% it earns 0 pts.")
    w(f"This creates a theoretical spread of **15 points** from smallest to largest position.")
    w(f"The conviction tier spread is **5 points** (CCL=25 vs HCA=20).")
    w(f"Ratio: sizing headroom max spread is **3x** the tier spread.")
    w("")

    # ── Section 1: Component Breakdown (top 20) ───────────────────────────────
    w("---")
    w("")
    w("## Section 1 - Factor Contribution Breakdown (Top 20 by DAS)")
    w("")
    w("| Rank | Symbol | DAS | Composite | Replay | Tier | Weight | Signal | Replay+ | Conv | Sizing | Momentum | Pen | Headroom% | Conv% |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for e in top:
        bd     = e["das_breakdown"]
        replay_yn = "Y" if e["replay"] else "N"
        pen    = -(bd["redundancy_pen"] + bd["conc_pen"])
        w(
            f"| {e['das_rank']} | `{e['symbol']}` | {e['das']} | "
            f"{_fmt_score(e['composite'])} | {replay_yn} | {e['tier_short']} | "
            f"{_fmt_pct(e['current_pct'])} | "
            f"{_fmt_contrib(bd['signal'])} | {_fmt_contrib(bd['replay'])} | "
            f"{_fmt_contrib(bd['conviction'])} | {_fmt_contrib(bd['sizing'])} | "
            f"{_fmt_contrib(bd['momentum'])} | {pen:.0f} | "
            f"{e['headroom_share_pct']:.1f}% | {e['conviction_share_pct']:.1f}% |"
        )
    w("")
    w("**Column key:** `Signal` = composite-derived (0-30) · `Replay+` = replay bonus (0-20) · "
      "`Conv` = tier bonus (0-25) · `Sizing` = headroom bonus (0-15) · "
      "`Momentum` = ESS+direction (0-10) · `Pen` = redundancy + concentration penalties · "
      "`Headroom%` = sizing component as % of DAS · `Conv%` = conviction component as % of DAS")
    w("")

    # ── Section 2: Average component contribution ─────────────────────────────
    w("---")
    w("")
    w("## Section 2 - Average Factor Contribution (Top 20)")
    w("")
    w("| Component | Avg Points | Avg % of DAS | Max Possible | Utilization |")
    w("|---|---|---|---|---|")
    maxes = {
        "signal": 30, "replay": 20, "conviction": 25,
        "sizing": 15, "momentum": 10,
        "redundancy_pen": 15, "conc_pen": 20,
    }
    for comp, max_pts in maxes.items():
        avg_pts = stats["avg_shares_pts"][comp]
        avg_pct = stats["avg_shares_pct"][comp]
        util    = avg_pts / max_pts * 100.0
        label   = comp.replace("_pen", " Penalty").replace("_", " ").title()
        w(f"| {label} | {avg_pts:.2f} | {avg_pct:.1f}% | {max_pts} | {util:.0f}% |")
    w("")
    sizing_avg   = stats["avg_shares_pts"]["sizing"]
    conv_avg     = stats["avg_shares_pts"]["conviction"]
    signal_avg   = stats["avg_shares_pts"]["signal"]
    sizing_pct   = stats["avg_shares_pct"]["sizing"]
    conv_pct     = stats["avg_shares_pct"]["conviction"]
    w(f"**Key finding:** Sizing headroom averages **{sizing_avg:.1f} pts ({sizing_pct:.1f}% of DAS)**. "
      f"Conviction tier averages **{conv_avg:.1f} pts ({conv_pct:.1f}% of DAS)**. "
      f"Signal averages **{signal_avg:.1f} pts**.")
    w("")
    ratio = sizing_pct / conv_pct if conv_pct else 0
    w(f"Sizing headroom contribution is **{ratio:.1f}x** the conviction tier contribution on average.")
    w("")

    # ── Section 3: Rank Correlations ─────────────────────────────────────────
    w("---")
    w("")
    w("## Section 3 - Rank Correlation Analysis")
    w("")
    w("### Spearman Rank Correlations (Full Conviction Universe, n={n_total})".format(
        n_total=stats["n_total"]
    ))
    w("")
    w("| Correlation | rho | Interpretation |")
    w("|---|---|---|")

    rho_dc = stats["rho_das_comp"]
    rho_dt = stats["rho_das_tier"]   # note: tier_num is inverted (1=CCL=best)
    rho_dh = stats["rho_das_head"]
    rho_ch = stats["rho_comp_head"]

    def _interp(rho: float, invert: bool = False) -> str:
        r = -rho if invert else rho
        if r >= 0.80:   return "Very strong positive alignment"
        if r >= 0.60:   return "Strong positive alignment"
        if r >= 0.40:   return "Moderate alignment"
        if r >= 0.20:   return "Weak alignment"
        if r >= -0.20:  return "No meaningful correlation"
        if r >= -0.40:  return "Weak inverse relationship"
        if r >= -0.60:  return "Moderate inverse relationship"
        return "Strong inverse relationship"

    w(f"| DAS vs Composite Score | {_fmt_rho(rho_dc)} | {_interp(rho_dc)} |")
    # For tier: lower tier_num = higher conviction; positive rho with tier_num = DAS
    # favors lower conviction (HCA); negative = DAS favors CCL.
    tier_interp = ("DAS aligns with higher conviction tier" if rho_dt < 0
                   else "DAS slightly favors lower-conviction (HCA) positions")
    w(f"| DAS vs Conviction Tier | {_fmt_rho(rho_dt)} | {tier_interp} |")
    w(f"| DAS vs Sizing Headroom | {_fmt_rho(rho_dh)} | {_interp(rho_dh)} |")
    w(f"| Composite vs Sizing Headroom | {_fmt_rho(rho_ch)} | {_interp(rho_ch)} |")
    w("")
    w("### Spearman Rank Correlations (Top 20 Only)")
    w("")
    w("| Correlation | rho |")
    w("|---|---|")
    w(f"| DAS vs Composite Score | {_fmt_rho(stats['rho_top_das_comp'])} |")
    w(f"| DAS vs Conviction Tier | {_fmt_rho(stats['rho_top_das_tier'])} |")
    w(f"| DAS vs Sizing Headroom | {_fmt_rho(stats['rho_top_das_head'])} |")
    w("")
    w("**Interpretation of tier correlation sign convention:**")
    w("Tier_num = 1 for CCL (highest conviction), 2 for HCA. A *negative* DAS vs tier_num")
    w("rho means DAS tends to rank higher-conviction symbols higher — which is desirable.")
    w("A *positive* rho means DAS is rewarding lower-conviction symbols more.")
    w("")

    # ── Section 4: Disagreement Cases ────────────────────────────────────────
    w("---")
    w("")
    w("## Section 4 - Cases Where DAS Materially Disagrees With Conviction Ranking")
    w("")
    w("**Definition:** |DAS rank - conviction rank| >= 3, or HCA symbol ranks")
    w("in top 3 while any CCL symbol ranks lower.")
    w("")
    if not stats["disagreements"]:
        w("No material disagreements found.")
    else:
        w("| Symbol | Tier | DAS Rank | Conv Rank | Delta | DAS | Composite | Weight | Sizing pts | Sizing% | Root Cause |")
        w("|---|---|---|---|---|---|---|---|---|---|---|")
        for e in sorted(stats["disagreements"], key=lambda x: abs(x.get("rank_delta", 0)), reverse=True):
            delta = e.get("rank_delta", 0)
            bd    = e["das_breakdown"]
            # Root cause
            if bd["sizing"] > bd["conviction"] and e["sti_tier"] == "HIGH_CONVICTION_ANCHOR":
                root = "Sizing headroom exceeds tier bonus"
            elif e["sti_tier"] == "HIGH_CONVICTION_ANCHOR" and delta < 0:
                root = "HCA ranked above CCL by DAS"
            elif bd["conc_pen"] > 0 or bd["redundancy_pen"] > 0:
                root = "Penalties suppressing DAS"
            else:
                root = "Composite + sizing combination"
            sign = "+" if delta > 0 else ""
            w(
                f"| `{e['symbol']}` | {e['tier_short']} | {e['das_rank']} | "
                f"{e['conv_rank']} | {sign}{delta} | {e['das']} | "
                f"{_fmt_score(e['composite'])} | {_fmt_pct(e['current_pct'])} | "
                f"{_fmt_contrib(bd['sizing'])} | {e['headroom_share_pct']:.1f}% | {root} |"
            )
    w("")
    w("**DAS rank vs conviction rank summary:**")
    w("")
    w("| Symbol | Tier | DAS Rank | Conv Rank | Delta | Sizing pts | Conviction pts |")
    w("|---|---|---|---|---|---|---|")
    all_entries = sorted(
        [e for e in top], key=lambda x: x["das_rank"]
    )
    for e in all_entries:
        delta = e.get("rank_delta", 0)
        bd = e["das_breakdown"]
        sign = "+" if delta > 0 else ""
        arrow = " <--" if abs(delta) >= 3 else ""
        w(
            f"| `{e['symbol']}` | {e['tier_short']} | {e['das_rank']} | "
            f"{e['conv_rank']} | {sign}{delta}{arrow} | "
            f"{_fmt_contrib(bd['sizing'])} | {_fmt_contrib(bd['conviction'])} |"
        )
    w("")

    # ── Section 5: HCA-over-CCL breakdown ────────────────────────────────────
    w("---")
    w("")
    w("## Section 5 - HCA Symbols Ranked Above CCL Symbols")
    w("")
    hca_top = stats["hca_ranked_above_ccl"]
    ccl_syms = stats["ccl_symbols"]

    if hca_top:
        w("The following HCA-tier symbols appear in the top 6 by DAS, ranking above")
        w(f"some CCL symbols ({', '.join('`'+s+'`' for s in ccl_syms)}):")
        w("")
        w("| Symbol | DAS Rank | DAS | Weight | Signal | Conv | Sizing | Momentum | Why ranked above CCL? |")
        w("|---|---|---|---|---|---|---|---|---|")
        for e in sorted(hca_top, key=lambda x: x["das_rank"]):
            bd = e["das_breakdown"]
            # Find which CCL symbol it beats
            beaten = [
                f"`{o['symbol']}`(rank {o['das_rank']})"
                for o in top
                if o["sti_tier"] == "CORE_CONVICTION_LEADER"
                and o["das_rank"] > e["das_rank"]
            ]
            beaten_str = ", ".join(beaten[:3]) if beaten else "-"
            why = []
            if bd["sizing"] > 10:
                why.append(f"Sizing={bd['sizing']:.1f}pts (small pos)")
            if bd["signal"] > 27:
                why.append(f"Signal={bd['signal']:.1f}pts (high comp)")
            w(
                f"| `{e['symbol']}` | {e['das_rank']} | {e['das']} | "
                f"{_fmt_pct(e['current_pct'])} | {_fmt_contrib(bd['signal'])} | "
                f"{_fmt_contrib(bd['conviction'])} | {_fmt_contrib(bd['sizing'])} | "
                f"{_fmt_contrib(bd['momentum'])} | {'; '.join(why)} |"
            )
        w("")
        w("**Mechanism:** These HCA symbols have small current positions, earning near-maximum")
        w("sizing headroom (approaching 15 pts). Combined with their high composite scores,")
        w("the total exceeds what CCL symbols earn despite the 5-pt tier gap.")
    else:
        w("No HCA symbols appear in top 3 above CCL symbols.")
    w("")

    # ── Section 6: Numerical Illustration ────────────────────────────────────
    w("---")
    w("")
    w("## Section 6 - Numerical Illustration of Sizing vs Conviction Trade-off")
    w("")
    w("For two hypothetical positions with identical composite (4.7) and replay support:")
    w("")
    w("| Attribute | Position A (CCL, 3%) | Position B (HCA, 0.8%) |")
    w("|---|---|---|")
    w(f"| Signal | {4.7/5*30:.1f} | {4.7/5*30:.1f} |")
    w("| Replay | 20.0 | 20.0 |")
    w("| Conviction | **25.0** (CCL) | **20.0** (HCA) |")
    w(f"| Sizing | {15*(1-3/6):.1f} | {15*(1-0.8/6):.1f} |")
    w("| Momentum | 10.0 | 10.0 |")

    sig   = 4.7 / 5 * 30
    siz_a = 15 * (1 - 3 / 6)
    siz_b = 15 * (1 - 0.8 / 6)
    das_a = sig + 20 + 25 + siz_a + 10
    das_b = sig + 20 + 20 + siz_b + 10
    w(f"| **DAS** | **{das_a:.1f}** | **{das_b:.1f}** |")
    w("")
    winner = "B (HCA)" if das_b > das_a else "A (CCL)"
    margin = abs(das_b - das_a)
    w(f"**Result:** Position {winner} wins by {margin:.1f} pts despite CCL carrying a "
      f"5-pt tier advantage over HCA.")
    w("")
    sizing_diff = siz_b - siz_a
    w(f"The sizing headroom gap ({siz_b:.1f} vs {siz_a:.1f} = **+{sizing_diff:.1f} pts for B**)")
    w(f"more than offsets the conviction tier gap (25 vs 20 = **+5 pts for A**).")
    w(f"At 0.8% vs 3.0%, the headroom advantage is {sizing_diff:.1f} pts vs the 5-pt tier gap.")
    w("")

    # ── Section 7: Recommended Adjustments ───────────────────────────────────
    w("---")
    w("")
    w("## Section 7 - Recommended Adjustments")
    w("")
    w("> These are analytical recommendations only. No formula changes were made.")
    w("")
    w("### Finding 1: Sizing headroom can override conviction tier")
    w("")
    w(f"- The sizing component (max 15 pts) creates a spread of up to **{15:.0f} pts**")
    w(f"  between a 0% and {WARN_POSITION_PCT:.0f}% position.")
    w(f"- The conviction tier spread is only **5 pts** (CCL=25 vs HCA=20).")
    w(f"- Any HCA symbol with a position < ~1.5% and composite > 4.0 can outrank a")
    w(f"  CCL symbol at 3%+ weight with a similar or slightly lower composite.")
    w("")
    w("**Option A — Cap sizing headroom contribution:**")
    w("  Reduce sizing max from 15 to 8-10. This narrows the headroom spread to within")
    w("  the conviction tier gap range.")
    w("")
    w("**Option B — Scale conviction tier advantage:**")
    w("  Widen the tier spread: CCL=30, HCA=18. Increases the conviction gap from 5 to 12 pts,")
    w("  ensuring CCL symbols can only be outranked by HCA symbols with materially better signals.")
    w("")
    w("**Option C — Add a conviction multiplier:**")
    w("  Apply a tier multiplier to the final DAS: CCL x 1.05, HCA x 1.00.")
    w("  This preserves relative scoring within tiers while enforcing cross-tier ordering.")
    w("")
    w("**Option D — Accept current behavior as correct (if philosophy agrees):**")
    w("  If small HCA positions with high composites are genuinely better *deployment*")
    w("  candidates (more room to grow), then the current DAS accurately reflects")
    w("  deployment opportunity rather than intrinsic conviction quality. This is a")
    w("  philosophy question: is DAS ranking *where to put capital* or *which holdings")
    w("  are most important to the portfolio*?")
    w("")
    w("### Finding 2: Composite-DAS alignment is strong")
    w("")
    rho_dc = stats["rho_das_comp"]
    w(f"Spearman rho(DAS, composite) = {_fmt_rho(rho_dc)}. This is {'strong' if rho_dc >= 0.7 else 'moderate'}")
    w("alignment — the formula correctly rewards high composite scores.")
    w("")
    w("### Finding 3: Tier-DAS alignment depends on position size")
    w("")
    rho_dt = stats["rho_das_tier"]
    dir_str = "slightly inverting" if rho_dt > 0 else "correctly respecting"
    w(f"Spearman rho(DAS, tier_num) = {_fmt_rho(rho_dt)}.")
    w(f"The DAS formula is **{dir_str}** conviction tier ordering when sizing headroom")
    w(f"differences are large (>2% weight differential between CCL and HCA symbols).")
    w("")
    w("### Recommended decision framework")
    w("")
    w("If the goal of DAS is to rank **deployment attractiveness** (where cash will have")
    w("the most impact on portfolio construction):")
    w("  - Current formula is defensible: small positions have more room to grow.")
    w("  - Consider Option A or B to prevent HCA from systematically outranking CCL.")
    w("")
    w("If the goal is to rank **conviction quality** (which positions deserve more capital")
    w("because they are the most important holdings):")
    w("  - Current formula under-weights tier; Option B or C is most appropriate.")
    w("")
    w("**Key question for the portfolio manager:**")
    w("> Is ARW (HCA, 0.91%, composite 4.89) a better deployment target than")
    w("> VRT (CCL, 3.62%, composite 4.56)? If yes, the DAS formula is correct.")
    w("> If no — VRT should rank higher as a core conviction holding — adjust")
    w("> the sizing weight or tier spread.")
    w("")
    w("---")
    w("")
    w("*Analysis only. No formula changes made. Findings are advisory.*")
    w("")

    return "\n".join(lines)


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    top, stats = run_validation()

    print(f"\nRho(DAS, composite) = {stats['rho_das_comp']:.4f}")
    print(f"Rho(DAS, tier)      = {stats['rho_das_tier']:.4f}  (negative = CCL ranked higher)")
    print(f"Rho(DAS, headroom)  = {stats['rho_das_head']:.4f}")

    print(f"\nAvg component shares (top {stats['n_top']}):")
    for k, pts in stats["avg_shares_pts"].items():
        pct = stats["avg_shares_pct"][k]
        print(f"  {k:<18s}: {pts:5.2f} pts  ({pct:5.1f}% of DAS)")

    print(f"\nMaterial disagreements: {len(stats['disagreements'])}")
    for d in stats["disagreements"]:
        delta = d.get("rank_delta", 0)
        sign = "+" if delta > 0 else ""
        print(f"  {d['symbol']:6s}  DAS#{d['das_rank']}  Conv#{d['conv_rank']}  delta={sign}{delta}")

    report = generate_report(top, stats)
    out = Path("conviction_model_validation_report.md")
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written -> {out}")


if __name__ == "__main__":
    main()
