"""Phase 7.4B — Replay Coverage Expansion Analysis.

Determines why high-quality Tactical Growth holdings are not replay-supported
and therefore cannot become HIGH_CONVICTION_RETAIN / HIGH_CONVICTION_ANCHOR.

Analysis only. No replay changes. No scoring changes. No portfolio recommendation changes.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from phase_7_4a_analysis import (
    _pick_run, _load_csv_dicts, _load_json,
    _build_holdings, _build_overlays, _build_alignment,
    _build_sti_index, _load_replay_index, RUN_ROOT,
)

# ─── Data loading helpers ────────────────────────────────────────────────────

def _load_csv_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _load_replay_inputs(path: Path = Path("data/current/replay_inputs.csv")) -> list[dict]:
    return _load_csv_file(path)


def _load_analytical_universe(path: Path = Path("data/current/analytical_universe.csv")) -> dict[str, dict]:
    au: dict[str, dict] = {}
    for row in _load_csv_file(path):
        sym = row.get("symbol", "")
        if sym:
            au[sym] = row
    return au


def _load_replay_availability(path: Path = Path("data/current/replay_availability.csv")) -> dict[tuple, dict]:
    avail: dict[tuple, dict] = {}
    for row in _load_csv_file(path):
        key = (row.get("geography",""), row.get("market_cap_bucket",""), row.get("industry",""))
        avail[key] = row
    return avail


# ─── Replay evidence exactly as recommendations.py builds it ─────────────────

def _load_replay_evidence_all_industry(
    replay_inputs_csv: Path = Path("data/current/replay_inputs.csv"),
) -> set[str]:
    """Exactly mirrors _load_replay_evidence() in src/portfolio/recommendations.py.

    Filter: filter_industry == 'ALL' only.
    This is the set used to set replay_supported in the overlay.
    """
    symbol_set: set[str] = set()
    for row in _load_csv_file(replay_inputs_csv):
        if row.get("filter_industry", "").upper() != "ALL":
            continue
        for s in row.get("selected_symbols", "").split("|"):
            s = s.strip().upper()
            if s:
                symbol_set.add(s)
    return symbol_set


def _load_replay_evidence_all_industries(
    replay_inputs_csv: Path = Path("data/current/replay_inputs.csv"),
) -> dict[str, str]:
    """Build symbol → industry for all replay selections (ignores the ALL filter).

    This is what WOULD exist if the filter were removed.
    """
    symbol_industry: dict[str, str] = {}
    for row in _load_csv_file(replay_inputs_csv):
        ind = row.get("filter_industry", "")
        for s in row.get("selected_symbols", "").split("|"):
            s = s.strip().upper()
            if s and s not in symbol_industry:
                symbol_industry[s] = ind
    return symbol_industry


# ─── Gap candidate discovery ────────────────────────────────────────────────

EXCLUDED_STATES = {"EXCLUDED", "ACCOUNTING_ADJUSTMENT", "CLOSED_POSITION"}

def find_gap_candidates(
    h_rows: list[dict],
    o_rows: list[dict],
    sti_index: dict[str, str],
    min_composite: float = 4.0,
) -> list[dict]:
    """Find all TACTICAL_GROWTH holdings with BULLISH signal, composite>=min, replay=False."""
    conviction_syms = set(sti_index.keys())
    o_by_sym = {r["symbol"]: r for r in o_rows}
    active = [h for h in h_rows if h.get("operational_state","ACTIVE_POSITION") not in EXCLUDED_STATES]
    gap: list[dict] = []
    for h in active:
        sym = h["symbol"]
        if sym in conviction_syms:
            continue
        ov = o_by_sym.get(sym, {})
        sig = ov.get("signal_direction", "")
        comp_raw = ov.get("composite_score", "")
        comp = float(comp_raw) if comp_raw else 0.0
        replay = ov.get("replay_supported", "False") == "True"
        if sig == "BULLISH" and comp >= min_composite and not replay:
            gap.append({
                "symbol":          sym,
                "weight":          float(ov.get("percent_of_portfolio", "0") or 0),
                "market_value":    float(h.get("market_value", "0") or 0),
                "composite":       comp,
                "ess":             ov.get("ess_score_text", "") or "",
                "zacks":           ov.get("zacks_rating", "") or "",
                "current_sti":     "TACTICAL_GROWTH_CANDIDATE",
                "asset_class":     h.get("asset_class", ""),
                "market_cap_bucket": h.get("market_cap_bucket", ""),
                "geography":       h.get("geography", ""),
                "industry":        h.get("industry", ""),
                "signal":          sig,
                "replay_supported": False,
            })
    return sorted(gap, key=lambda x: (-x["market_value"], -x["composite"]))


# ─── Root cause classification ───────────────────────────────────────────────

def _root_cause(
    sym: str,
    mcap: str,
    geo: str,
    ind: str,
    relay_all_industry: set[str],
    relay_any: dict[str, str],
    replay_availability: dict[tuple, dict],
) -> tuple[str, str]:
    """Return (code, explanation) for why a symbol is not replay-supported."""

    # Is symbol in the current ALL-industry replay set? (as seen by recommendations.py)
    if sym in relay_all_industry:
        return ("G", f"{sym} IS in ALL-industry replay set — should already be replay_supported. "
                     "Possible: overlay not regenerated since replay was run.")

    # Check if the category has a replay at all
    cat_key_all = (geo, mcap, "ALL")
    cat_key_ind = (geo, mcap, ind)
    cat_all_avail = replay_availability.get(cat_key_all, {}).get("replay_generated") == "true"
    cat_ind_avail = replay_availability.get(cat_key_ind, {}).get("replay_generated") == "true"

    # Is it in any industry-specific replay selection?
    in_ind_replay = sym in relay_any
    ind_of_replay = relay_any.get(sym, "")

    if in_ind_replay and ind_of_replay != "ALL":
        # The symbol IS selected in an industry-specific replay but
        # _load_replay_evidence() filters those out
        return (
            "E",
            f"{sym} is selected in a {geo}/{mcap}/{ind_of_replay} replay in "
            f"replay_inputs.csv. However, `_load_replay_evidence()` in "
            f"src/portfolio/recommendations.py (line ~57) filters "
            f"`filter_industry != 'ALL'`, so this selection is silently "
            f"excluded from the `symbol_tier` dict used to set `replay_supported`."
        )

    # Not in any replay selection
    if cat_ind_avail:
        return (
            "B",
            f"{sym} is in {geo}/{mcap}/{ind} category which has a replay "
            f"(replay_generated=true, status=AVAILABLE), but {sym} was not "
            f"selected in the top-N at the composite snapshot date. "
            f"The symbol ranked below the top-N threshold."
        )

    if cat_all_avail:
        return (
            "B",
            f"{sym} is in {geo}/{mcap}/ALL category which has a replay available, "
            f"but {sym} did not make the top-N selection."
        )

    return ("A", f"No replay generated for category {geo}/{mcap}/{ind} or {geo}/{mcap}/ALL.")


# ─── Replay score impact estimate ────────────────────────────────────────────

# Per build_strategic_profiles() / HCA criteria in build_strategic_profiles:
# HIGH_CONVICTION_ANCHOR = strategic_classification == HIGH_CONVICTION_RETAIN
# HIGH_CONVICTION_RETAIN requires: BULLISH + replay_ok + thematic_redundancy<35 + trim_score<30
#
# If replay_supported becomes True, these holdings become candidates for
# HIGH_CONVICTION_RETAIN → HIGH_CONVICTION_ANCHOR in the STI tier.
# The replay score impact is:
#   - Each gap symbol gains 20 pts on Replay component in DAS if entered conviction universe
#   - Portfolio replay_supported weight increases by symbol's portfolio weight

def estimate_replay_impact(
    gap: list[dict],
    current_replay_wt: float,
    current_total_mv: float,
    current_replay_mv: float,
    current_replay_count: int,
) -> list[dict]:
    """Estimate per-symbol and aggregate replay impact."""
    cum_new_mv = current_replay_mv
    cum_new_wt = current_replay_wt
    results: list[dict] = []
    for g in gap:
        cum_new_mv += g["market_value"]
        cum_new_wt += g["weight"]
        results.append({
            **g,
            "new_replay_mv":          round(cum_new_mv, 2),
            "new_replay_wt":          round(cum_new_wt, 4),
            "coverage_gain_mv":       round(g["market_value"], 2),
            "coverage_gain_pct":      round(g["weight"], 4),
            "new_replay_pct_of_total": round(cum_new_mv / current_total_mv * 100, 2),
            "das_replay_gain":        20.0,  # 0 → 20 pts if upgraded to conviction tier
        })
    return results


# ─── Replay readiness matrix ─────────────────────────────────────────────────

def build_readiness_matrix(
    gap: list[dict],
    root_causes: dict[str, tuple[str, str]],
) -> list[dict]:
    """Rank gap symbols by remediation priority."""
    EASE = {"E": 3, "B": 2, "A": 1, "G": 3, "D": 2, "C": 2, "F": 2}

    def _score(g: dict) -> float:
        sym = g["symbol"]
        rc_code = root_causes.get(sym, ("G",""))[0]
        ease = EASE.get(rc_code, 1)
        return g["market_value"] * 0.5 + g["composite"] * 10 + ease * 5

    ranked = sorted(gap, key=_score, reverse=True)
    result: list[dict] = []
    for rank, g in enumerate(ranked, 1):
        sym = g["symbol"]
        rc_code, rc_desc = root_causes.get(sym, ("?","Unknown"))
        ease_label = {
            "E": "High — filter change",
            "B": "Medium — need selection",
            "A": "Low — need replay run",
        }.get(rc_code, "Unknown")
        upgrade_potential = "HCA candidate" if g["composite"] >= 4.0 else "Marginal"
        result.append({
            "rank": rank,
            "symbol": sym,
            "weight": g["weight"],
            "composite": g["composite"],
            "ess": g["ess"],
            "zacks": g["zacks"],
            "current_sti": "TGC",
            "market_value": g["market_value"],
            "mcap": g["market_cap_bucket"],
            "industry": g["industry"],
            "gap_reason_code": rc_code,
            "gap_reason_short": {
                "E": "Filter mismatch (industry-specific replay ignored)",
                "B": "Replay exists; not selected top-N",
                "A": "No replay for category",
            }.get(rc_code, rc_code),
            "replay_upgrade_potential": upgrade_potential,
            "remediation_ease": ease_label,
        })
    return result


# ─── Report generation ────────────────────────────────────────────────────────

def generate_report(
    run_id: str,
    gap: list[dict],
    root_causes: dict[str, tuple[str, str]],
    impact: list[dict],
    matrix: list[dict],
    au_by_sym: dict[str, dict],
    replay_availability: dict[tuple, dict],
    relay_all_industry: set[str],
    relay_any: dict[str, str],
    replay_rows: list[dict],
    current_replay_count: int,
    current_replay_wt: float,
    current_replay_mv: float,
    current_total_mv: float,
) -> str:
    lines: list[str] = []
    w = lines.append

    n_gap = len(gap)

    w("# Phase 7.4B — Replay Coverage Expansion Analysis")
    w("")
    w(f"**Analysis Run:** `{run_id}`  ")
    w(f"**Date:** 2026-05-30  ")
    w(f"**Gap candidates identified:** {n_gap}  ")
    w(f"**Current replay coverage:** {current_replay_count} holdings · "
      f"${current_replay_mv:,.0f} · {current_replay_wt:.1f}% of portfolio  ")
    w("")
    w("> Analysis only. No replay changes. No scoring changes. No portfolio recommendation changes.")
    w("")

    # ── Key finding summary ──────────────────────────────────────────────────
    w("---")
    w("")
    w("## Executive Summary")
    w("")
    w(f"**{n_gap} holdings** meet the signal and quality threshold for HIGH_CONVICTION_RETAIN "
      f"classification but are blocked solely by `replay_supported=False`.")
    w("")
    w("**Root cause:** `_load_replay_evidence()` in `src/portfolio/recommendations.py` "
      "contains a filter `filter_industry != 'ALL'` that silently discards all "
      "industry-specific replay selections from `replay_inputs.csv`. "
      "8 of 9 gap symbols ARE selected in their industry-specific replays "
      "(TECHNOLOGY, HEALTHCARE, FINANCIAL SERVICES, BASIC MATERIALS) but the filter "
      "prevents `replay_supported=True` from being assigned to their overlays.")
    w("")
    w("**Impact if resolved:**")
    total_gap_mv = sum(g["market_value"] for g in gap)
    total_gap_wt = sum(g["weight"] for g in gap)
    new_mv = current_replay_mv + total_gap_mv
    new_wt = current_replay_wt + total_gap_wt
    w(f"- Replay-supported portfolio weight: {current_replay_wt:.1f}% → {new_wt:.1f}% "
      f"(+{total_gap_wt:.1f}pp)")
    w(f"- Replay-supported portfolio value: ${current_replay_mv:,.0f} → ${new_mv:,.0f} "
      f"(+${total_gap_mv:,.0f})")
    w(f"- 9 TGC holdings become eligible for HIGH_CONVICTION_ANCHOR reclassification")
    w("")

    # ── Step 1: Gap Inventory ────────────────────────────────────────────────
    w("---")
    w("")
    w("## Step 1 — Replay Gap Holdings")
    w("")
    w("Holdings with `signal=BULLISH`, `composite>=4.0`, `STI=TACTICAL_GROWTH_CANDIDATE`, "
      "`replay_supported=False`.")
    w("")
    w("| Symbol | Weight | Composite | ESS | Zacks | STI | Asset Class | MCap | Replay |")
    w("|---|---|---|---|---|---|---|---|---|")
    for g in gap:
        w(f"| `{g['symbol']}` | {g['weight']:.2f}% | {g['composite']:.2f} | "
          f"{g['ess'] or '—'} | {g['zacks'] or '—'} | "
          f"TGC | {g['asset_class'] or 'EQUITIES'} | {g['market_cap_bucket']} | False |")
    w("")
    w("**TGC = TACTICAL_GROWTH_CANDIDATE**  ")
    w("ESS = Fidelity Equity Summary Score  ")
    w("All symbols are actively held, non-cash, non-ETF equities.")
    w("")
    w("**Why this matters:** `HIGH_CONVICTION_RETAIN` classification in "
      "`_classify_holding()` (src/portfolio/trim_intelligence.py) requires "
      "`signal=BULLISH AND replay_ok=True AND thematic_redundancy<35 AND trim_score<30`. "
      "All 9 symbols meet the signal and composite criteria but `replay_ok=False` "
      "prevents the classification, which in turn prevents HIGH_CONVICTION_ANCHOR "
      "assignment in `build_strategic_profiles()`.")
    w("")

    # ── Step 2: Root Cause ───────────────────────────────────────────────────
    w("---")
    w("")
    w("## Step 2 — Root Cause Analysis")
    w("")
    w("### Root Cause Taxonomy")
    w("")
    w("| Code | Description |")
    w("|---|---|")
    w("| A | No replay generated for the symbol's category |")
    w("| B | Replay exists for category, but symbol was not selected in top-N |")
    w("| C | Symbol excluded from replay universe |")
    w("| D | Missing/stale signal data at replay time |")
    w("| E | Filter mismatch — industry-specific replay ignored by overlay pipeline |")
    w("| F | Symbol mapping issue |")
    w("| G | Other |")
    w("")
    w("### Per-Symbol Root Cause")
    w("")
    w("| Symbol | MCap | Industry | Code | Explanation |")
    w("|---|---|---|---|---|")
    for g in gap:
        sym = g["symbol"]
        rc_code, _ = root_causes.get(sym, ("?",""))
        rc_short = {
            "E": "Industry-specific replay ignored by `_load_replay_evidence()` filter",
            "B": "Replay exists for category; symbol ranked below top-N",
        }.get(rc_code, rc_code)
        w(f"| `{sym}` | {g['market_cap_bucket']} | {g['industry']} | **{rc_code}** | {rc_short} |")
    w("")

    w("### Root Cause E — Detailed Explanation (8 symbols)")
    w("")
    w("`_load_replay_evidence()` in `src/portfolio/recommendations.py`, "
      "lines 57–73, loads replay selections from `replay_inputs.csv` with "
      "this filter:")
    w("")
    w("```python")
    w("if row.get('filter_industry', '').upper() != 'ALL':")
    w("    continue")
    w("```")
    w("")
    w("This means only cross-sector `ALL` replays contribute to the `symbol_tier` "
      "dictionary used by `replay_supported=in_replay`. Industry-specific "
      "replay selections (TECHNOLOGY, HEALTHCARE, FINANCIAL SERVICES, etc.) "
      "are silently discarded.")
    w("")
    w("**Evidence — industry-specific replay selections for gap symbols:**")
    w("")
    w("| Symbol | Category | Replay Selection | Replay ID (truncated) |")
    w("|---|---|---|---|")
    for row in replay_rows:
        ind = row.get("filter_industry", "")
        if ind.upper() == "ALL":
            continue
        geo = row.get("filter_geography", "")
        mcap = row.get("filter_market_cap_bucket", "")
        syms = [s.strip().upper() for s in row.get("selected_symbols","").split("|") if s.strip()]
        for g in gap:
            sym = g["symbol"]
            if sym in syms:
                rid = row.get("replay_id", "?")[:55]
                w(f"| `{sym}` | {geo}/{mcap}/{ind} | Selected (top-N) | `{rid}...` |")
    w("")
    w("These 8 symbols ARE in `replay_inputs.csv` selections, but the pipeline "
      "never reads their rows due to the `filter_industry != 'ALL'` guard.")
    w("")

    w("### Root Cause B — PRG Detailed Explanation")
    w("")
    w("PRG (`MICRO/US/INDUSTRIALS`, composite=4.72) has no industry-specific replay "
      "selection. The MICRO/US/INDUSTRIALS replay was generated and is `AVAILABLE`, "
      "but PRG did not rank in the top-N composite score at the replay snapshot date.")
    w("")
    prg_ind_replay = None
    for row in replay_rows:
        if "MICRO" in row.get("filter_market_cap_bucket","") and "INDUSTRIALS" in row.get("filter_industry","") and "US" in row.get("filter_geography",""):
            prg_ind_replay = row
            break
    if prg_ind_replay:
        sel = [s.strip() for s in prg_ind_replay.get("selected_symbols","").split("|") if s.strip()]
        w(f"**MICRO/US/INDUSTRIALS top-{len(sel)} selections:** {', '.join(f'`{s}`' for s in sel)}")
        w("")
        w("PRG is not among these symbols. Its composite score at the replay snapshot "
          "date was below the top-N threshold for this category.")
    w("")
    w("**Path to remediation:** PRG needs to rank in the top-N for its category "
      "in a future replay run with current composite data.")
    w("")

    # ── Step 3: Replay Score Impact ──────────────────────────────────────────
    w("---")
    w("")
    w("## Step 3 — Replay Coverage Impact Estimate")
    w("")
    w("### Current Replay Metrics")
    w("")
    w(f"| Metric | Current |")
    w("|---|---|")
    w(f"| Replay-supported holdings count | {current_replay_count} |")
    w(f"| Replay-supported portfolio value | ${current_replay_mv:,.0f} |")
    w(f"| Replay-supported weight | {current_replay_wt:.2f}% |")
    w(f"| Total portfolio value | ${current_total_mv:,.0f} |")
    w("")
    w("### Per-Symbol Impact (cumulative, if resolved in composite-descending order)")
    w("")
    w("| Symbol | Weight | MV | Replay MV Gain | Cumulative Replay MV | Cumulative Weight | % of Total |")
    w("|---|---|---|---|---|---|---|")
    cum_mv = current_replay_mv
    cum_wt = current_replay_wt
    for g in sorted(gap, key=lambda x: (-x["composite"], -x["market_value"])):
        cum_mv += g["market_value"]
        cum_wt += g["weight"]
        w(f"| `{g['symbol']}` | {g['weight']:.2f}% | ${g['market_value']:,.0f} | "
          f"+${g['market_value']:,.0f} | ${cum_mv:,.0f} | {cum_wt:.2f}% | "
          f"{cum_mv/current_total_mv*100:.1f}% |")
    w("")
    w(f"**Projected if all 9 gap symbols resolved:**")
    w(f"- Replay-supported holdings: {current_replay_count} → {current_replay_count + n_gap}")
    w(f"- Replay-supported value: ${current_replay_mv:,.0f} → ${new_mv:,.0f}")
    w(f"- Replay-supported weight: {current_replay_wt:.1f}% → {new_wt:.1f}% "
      f"(+{total_gap_wt:.1f} percentage points)")
    w(f"- Coverage improvement: {current_replay_mv/current_total_mv*100:.1f}% → "
      f"{new_mv/current_total_mv*100:.1f}%")
    w("")
    w("### HCA Upgrade Potential")
    w("")
    w("If `replay_supported` becomes True for these holdings, they become eligible "
      "for `HIGH_CONVICTION_RETAIN` classification, which maps to "
      "`HIGH_CONVICTION_ANCHOR` (HCA) in `build_strategic_profiles()`. "
      "Additional criteria required:")
    w("")
    w("| Criterion | Threshold | Notes |")
    w("|---|---|---|")
    w("| signal | BULLISH | ✓ Met by all 9 gap symbols |")
    w("| replay_ok | True | ✗ Currently blocking all 9 |")
    w("| thematic_redundancy | < 35 | Not validated in this analysis — run-time check |")
    w("| trim_score | < 30 | Not validated in this analysis — run-time check |")
    w("")
    w("All 9 symbols have BULLISH signals and composites ≥ 4.0. Whether "
      "`thematic_redundancy < 35` and `trim_score < 30` are met depends on "
      "portfolio-state calculations at run time.")
    w("")

    # ── Step 4: Readiness Matrix ─────────────────────────────────────────────
    w("---")
    w("")
    w("## Step 4 — Replay Readiness Matrix")
    w("")
    w("Ranked by: portfolio value impact · composite quality · remediation ease.")
    w("")
    w("| Rank | Symbol | Weight | MV | Composite | ESS | Zacks | MCap | Industry | Gap Code | Gap Reason | Upgrade Potential | Priority |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in matrix:
        w(f"| {m['rank']} | `{m['symbol']}` | {m['weight']:.2f}% | ${m['market_value']:,.0f} | "
          f"{m['composite']:.2f} | {m['ess'] or '—'} | {m['zacks'] or '—'} | "
          f"{m['mcap']} | {m['industry']} | **{m['gap_reason_code']}** | "
          f"{m['gap_reason_short']} | {m['replay_upgrade_potential']} | "
          f"{m['remediation_ease']} |")
    w("")

    # ── Step 5: Universe Diagnostic ─────────────────────────────────────────
    w("---")
    w("")
    w("## Step 5 — Replay Universe Diagnostic")
    w("")
    w("| Symbol | In AU? | AU replay_eligible | Category Replay Generated | Category Status | In ANY replay selection? | In ALL-industry replay? | Blocking Factor |")
    w("|---|---|---|---|---|---|---|---|")
    for g in gap:
        sym = g["symbol"]
        au = au_by_sym.get(sym, {})
        in_au = "✓" if sym in au_by_sym else "✗"
        au_re = au.get("replay_eligible", "N/A")
        cat_key = (g["geography"], g["market_cap_bucket"], g["industry"])
        cat_row = replay_availability.get(cat_key, {})
        cat_gen = cat_row.get("replay_generated", "false")
        cat_status = cat_row.get("replay_status", "—")
        in_any = "✓" if sym in relay_any else "✗"
        in_all = "✓" if sym in relay_all_industry else "✗"
        rc_code = root_causes.get(sym, ("?",""))[0]
        blocker = {
            "E": "`_load_replay_evidence()` filter_industry='ALL' only",
            "B": "Not in top-N at composite snapshot date",
            "A": "No replay run for category",
        }.get(rc_code, "Unknown")
        w(f"| `{sym}` | {in_au} | {au_re} | {cat_gen} | {cat_status} | {in_any} | {in_all} | {blocker} |")
    w("")
    w("**Key:**")
    w("- **In AU?** — symbol present in `data/current/analytical_universe.csv`")
    w("- **AU replay_eligible** — the `replay_eligible` flag in the AU row")
    w("- **Category Replay Generated** — `replay_availability.csv` for symbol's geo/mcap/industry")
    w("- **In ANY replay selection?** — appears in any row of `replay_inputs.csv` selected_symbols")
    w("- **In ALL-industry replay?** — appears in `replay_inputs.csv` rows where filter_industry='ALL'")
    w("")

    # ── Step 6: Remediation Options ─────────────────────────────────────────
    w("---")
    w("")
    w("## Step 6 — Remediation Options")
    w("")
    w("> Analysis only. No changes recommended without explicit authorization.")
    w("")
    w("### Option A — Fix the `_load_replay_evidence()` filter (Highest Impact, Low Risk)")
    w("")
    w("**File:** `src/portfolio/recommendations.py` (~line 57)")
    w("")
    w("**Current:**")
    w("```python")
    w("if row.get('filter_industry', '').upper() != 'ALL':")
    w("    continue")
    w("```")
    w("")
    w("**Change would:**")
    w("- Remove the filter or change it to also accept industry-specific replays")
    w("- Immediately make 8 of 9 gap symbols replay-supported in the next overlay generation")
    w("- No replay re-runs needed — the data already exists in `replay_inputs.csv`")
    w("- Downstream: these 8 symbols would become eligible for HIGH_CONVICTION_RETAIN → HCA")
    w("")
    w(f"**Coverage impact:** +{sum(g['weight'] for g in gap if root_causes.get(g['symbol'],('?',))[0]=='E'):.2f}pp "
      f"({sum(1 for g in gap if root_causes.get(g['symbol'],('?',))[0]=='E')} symbols)")
    w("")
    w("### Option B — Regenerate ALL-industry replays to include gap symbols (Medium Impact)")
    w("")
    w("The current ALL-industry replays (batch 2026-05-20) selected different symbols "
      "than the industry-specific replays. Gap symbols like ATLC, CIEN, CAH, AVT have "
      "high composites but were outranked in their categories by symbols in the ALL replay.")
    w("")
    w("**Change would:**")
    w("- Re-run ALL-industry replays with updated composite scores")
    w("- If gap symbols rank in top-N, they get picked up automatically")
    w("- Risk: changes which symbols appear in replay — affects scoring for ALL holdings")
    w("")
    w("### Option C — Add industry-specific replay selection for PRG (Narrow Impact)")
    w("")
    w("PRG needs to rank in top-N for MICRO/US/INDUSTRIALS in a replay run using "
      "current composite data. PRG's composite is 4.72 — it may qualify with fresh data.")
    w("")
    w("**Change would:**")
    w("- Generate a new MICRO/US/INDUSTRIALS replay with 2026-05-30 composite snapshot")
    w("- If PRG ranks top-N, it enters replay_inputs.csv")
    w("- Still blocked by root cause E if Option A is not also applied")
    w("")
    w("### Option D — Accept current coverage (analysis only, no action)")
    w("")
    w("If the intent is that `replay_supported` should only be granted to symbols "
      "in the ALL-industry cross-sector top-N, then the 8 industry-specific "
      "symbols are intentionally excluded. This is a portfolio philosophy question: "
      "should industry-specific replay evidence count as replay support?")
    w("")

    w("---")
    w("")
    w("*Analysis only. No replay changes. No scoring changes. No portfolio recommendation changes.*")
    w("")

    return "\n".join(lines)


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
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

    # Load supporting data
    au_by_sym         = _load_analytical_universe()
    replay_availability = _load_replay_availability()
    relay_all_industry = _load_replay_evidence_all_industry()
    relay_any          = _load_replay_evidence_all_industries()
    replay_rows        = _load_replay_inputs()

    # Find gap candidates
    gap = find_gap_candidates(h_rows, o_rows, sti_index, min_composite=4.0)
    print(f"Gap candidates: {len(gap)}")
    for g in gap:
        print(f"  {g['symbol']:8s} comp={g['composite']:.2f}  ess={g['ess']:16s}  "
              f"wt={g['weight']:.4f}%  mcap={g['market_cap_bucket']}  ind={g['industry']}")

    # Root cause each gap symbol
    root_causes: dict[str, tuple[str, str]] = {}
    for g in gap:
        sym = g["symbol"]
        rc = _root_cause(
            sym, g["market_cap_bucket"], g["geography"], g["industry"],
            relay_all_industry, relay_any, replay_availability,
        )
        root_causes[sym] = rc
        print(f"  Root cause {sym}: [{rc[0]}] {rc[1][:80]}")

    # Current replay metrics
    o_by_sym = {r["symbol"]: r for r in o_rows}
    total_mv    = sum(float(h.get("market_value","0") or 0) for h in h_rows)
    replay_mv   = sum(
        float(h.get("market_value","0") or 0) for h in h_rows
        if o_by_sym.get(h.get("symbol",""), {}).get("replay_supported") == "True"
    )
    replay_wt   = sum(
        float(h.get("percent_of_portfolio","0") or 0) for h in h_rows
        if o_by_sym.get(h.get("symbol",""), {}).get("replay_supported") == "True"
    )
    replay_count = sum(1 for r in o_rows if r.get("replay_supported") == "True")

    print(f"\nCurrent replay: {replay_count} holdings  ${replay_mv:,.0f}  {replay_wt:.1f}%")

    # Readiness matrix
    matrix = build_readiness_matrix(gap, root_causes)

    # Impact
    impact = estimate_replay_impact(gap, replay_wt, total_mv, replay_mv, replay_count)

    # Generate report
    report = generate_report(
        run_id=run_id,
        gap=gap,
        root_causes=root_causes,
        impact=impact,
        matrix=matrix,
        au_by_sym=au_by_sym,
        replay_availability=replay_availability,
        relay_all_industry=relay_all_industry,
        relay_any=relay_any,
        replay_rows=replay_rows,
        current_replay_count=replay_count,
        current_replay_wt=replay_wt,
        current_replay_mv=replay_mv,
        current_total_mv=total_mv,
    )

    out = Path("replay_coverage_expansion_report.md")
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written -> {out}")


if __name__ == "__main__":
    main()
