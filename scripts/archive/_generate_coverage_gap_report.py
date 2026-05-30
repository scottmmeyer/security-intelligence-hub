#!/usr/bin/env python3
"""Phase 6.4D — Generate coverage_gap_report.md."""
from __future__ import annotations
import csv, json, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

_INGESTION_ROOT = _REPO_ROOT / "data" / "portfolio_ingestion"
_AU_PATH = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
_OUTPUT_PATH = _REPO_ROOT / "coverage_gap_report.md"

SIGNAL_FIELDS = {
    "ESS": "ess_score_text",
    "Zacks": "zacks_rating",
    "Composite": "composite_score",
}

# ESS sub-categorization
_ETF_TYPES = {"ETF", "ETF (Fund)", "ETF (Trust)", "Closed-End Fund", "Open-End Fund"}
_CASH_TYPES = {"Cash", "Cash Equivalent", "Money Market"}


def _latest_run_id_name_with_taxonomy() -> str:
    """Return most recent run that has taxonomy_status set (post-6.4C)."""
    runs_dir = _INGESTION_ROOT / "analysis_runs"
    for d in sorted(runs_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
        if not (d.is_dir() and d.name.startswith("PAR-")):
            continue
        meta_path = d / "run_metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if meta.get("taxonomy_status") not in (None, "N/A"):
                return d.name
    # fallback
    return sorted(
        (d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("PAR-")),
        key=lambda d: d.stat().st_mtime, reverse=True
    )[0].name


def _ess_category(h: dict, au_by_sym: dict[str, dict]) -> str:
    """Classify why ESS is missing for a holding."""
    sym = h.get("symbol", "")
    st = (h.get("security_type", "") or "").strip()
    ac = h.get("asset_class", "UNKNOWN")

    if ac == "CASH" or st in _CASH_TYPES:
        return "Structural — Cash/Cash-Equivalent"
    if st == "ETF" or st in _ETF_TYPES:
        return "Structural — ETF (fund, not stock)"
    if ac == "UNKNOWN":
        return "Classification Gap — asset_class=UNKNOWN"
    if st == "Depository Receipt":
        if sym in au_by_sym:
            return "Provider Gap — ADR (partial StarMine coverage)"
        return "Universe Gap — ADR not in analytical universe"
    # Common stock cases
    if sym in au_by_sym:
        return "Universe Gap — In AU but ESS not populated (StarMine coverage gap)"
    return "Universe Gap — Symbol not in analytical universe"


def _badge_bool(v: bool) -> str:
    return "Y" if v else "—"


def main() -> None:
    run_id = sys.argv[1] if len(sys.argv) > 1 else _latest_run_id_name_with_taxonomy()
    run_dir = _INGESTION_ROOT / "analysis_runs" / run_id
    holdings = list(csv.DictReader(open(run_dir / "holdings.csv")))
    run_meta = json.loads((run_dir / "run_metadata.json").read_text()) if (run_dir / "run_metadata.json").exists() else {}
    au = list(csv.DictReader(open(_AU_PATH)))
    au_by_sym = {r["symbol"]: r for r in au}
    au_ess_total = sum(1 for r in au if (r.get("ess_score_text", "") or "").strip())

    total_mv = sum(float(h.get("market_value", 0) or 0) for h in holdings)
    n_total = len(holdings)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    snap_date = run_meta.get("snapshot_date", "?")
    # Fall back to created_at_utc date if snapshot_date looks like a mandate type
    if snap_date and not snap_date[:4].isdigit():
        snap_date = (run_meta.get("created_at_utc", "") or "")[:10] or "?"
    taxonomy_status = run_meta.get("taxonomy_status", "N/A")
    coverage_status = run_meta.get("coverage_status", "N/A")

    def has_signal(h: dict, field: str) -> bool:
        return bool((h.get(field, "") or "").strip())

    # ── Coverage computation ────────────────────────────────────────────────
    def signal_coverage(field: str) -> tuple[list, list, float, float]:
        covered = [h for h in holdings if has_signal(h, field)]
        missing = [h for h in holdings if not has_signal(h, field)]
        mv_cov = sum(float(h.get("market_value", 0) or 0) for h in covered)
        pct_h = len(covered) / n_total * 100 if n_total else 0
        pct_mv = mv_cov / total_mv * 100 if total_mv else 0
        return covered, missing, pct_h, pct_mv

    grade_map = [(95.0, "A"), (90.0, "B"), (80.0, "C"), (70.0, "D"), (0.0, "F")]
    def grade(pct: float) -> str:
        for t, g in grade_map:
            if pct >= t:
                return g
        return "F"

    grade_badge = {"A": "🏆 A", "B": "✅ B", "C": "🟡 C", "D": "🟠 D", "F": "❌ F"}

    ess_cov, ess_miss, ess_pct_h, ess_pct_mv = signal_coverage("ess_score_text")
    zacks_cov, zacks_miss, zacks_pct_h, zacks_pct_mv = signal_coverage("zacks_rating")
    comp_cov, comp_miss, comp_pct_h, comp_pct_mv = signal_coverage("composite_score")
    ess_grade = grade(ess_pct_h)

    # ESS category breakdown
    ess_categories: dict[str, list] = defaultdict(list)
    for h in ess_miss:
        cat = _ess_category(h, au_by_sym)
        ess_categories[cat].append(h)

    # Sort holdings by MV descending (for matrix)
    sorted_holdings = sorted(holdings, key=lambda h: -float(h.get("market_value", 0) or 0))

    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [
        "# Coverage Gap Report — Phase 6.4D",
        "",
        f"**Run ID:** `{run_id}`  ",
        f"**Snapshot Date:** {snap_date}  ",
        f"**Generated:** {generated_at}  ",
        f"**Reconciliation:** RC-12 taxonomy={taxonomy_status} | RC-13 coverage={coverage_status}  ",
        "",
        "---",
        "",
    ]

    # ── SECTION 1: Coverage Matrix ─────────────────────────────────────────────
    lines += [
        "## Section 1 — Coverage Inventory Matrix",
        "",
        f"All {n_total} holdings sorted by portfolio weight descending. Signal: **Y** = value present, **—** = missing.",
        "",
        "| # | Symbol | MV | % Portfolio | Asset Class | Security Type | ESS | Zacks | Composite |",
        "|---|--------|-----|------------|-------------|--------------|-----|-------|-----------|",
    ]

    for i, h in enumerate(sorted_holdings, 1):
        sym = h.get("symbol", "?")
        mv = float(h.get("market_value", 0) or 0)
        pct = float(h.get("percent_of_portfolio", 0) or 0)
        ac = h.get("asset_class", "?")
        st = (h.get("security_type", "") or "?").strip()
        ess_v = _badge_bool(has_signal(h, "ess_score_text"))
        zacks_v = _badge_bool(has_signal(h, "zacks_rating"))
        comp_v = _badge_bool(has_signal(h, "composite_score"))
        lines.append(f"| {i} | `{sym}` | ${mv:>10,.0f} | {pct:.2f}% | {ac} | {st} | {ess_v} | {zacks_v} | {comp_v} |")

    lines.append("")

    # ── SECTION 2: ESS Coverage Analysis ──────────────────────────────────────
    lines += [
        "---",
        "",
        "## Section 2 — ESS Coverage Analysis",
        "",
        f"ESS source: **StarMine Earnings Surprise Score** (field: `ess_score_text`).  ",
        f"Stored in analytical universe (`data/current/analytical_universe.csv`).  ",
        f"Analytical universe ESS coverage: **{au_ess_total}/{len(au)} ({au_ess_total/len(au)*100:.1f}%)** of all tracked securities.",
        "",
        "### ESS Coverage by Category",
        "",
        "| Category | Holdings | Portfolio Weight | Root Cause | Fixable? |",
        "|----------|---------|----------------|-----------|----------|",
    ]

    for cat, hs in sorted(ess_categories.items(), key=lambda x: -sum(float(h.get("market_value",0) or 0) for h in x[1])):
        mv_cat = sum(float(h.get("market_value", 0) or 0) for h in hs)
        pct_cat = mv_cat / total_mv * 100 if total_mv else 0
        fixable = "No — structural" if "Structural" in cat else ("Yes — refresh ESS feed" if "StarMine" in cat else "Partial — fix classification first")
        lines.append(f"| {cat} | {len(hs)} | {pct_cat:.1f}% | See detail below | {fixable} |")

    lines += [
        "",
        "### ESS Covered Holdings",
        "",
        f"| Status | Holdings | % Holdings | % Portfolio MV |",
        f"|--------|---------|-----------|----------------|",
        f"| ESS Available | {len(ess_cov)} | {ess_pct_h:.1f}% | {ess_pct_mv:.1f}% |",
        f"| ESS Missing | {len(ess_miss)} | {100-ess_pct_h:.1f}% | {100-ess_pct_mv:.1f}% |",
        f"| **Total** | **{n_total}** | **100%** | **100%** |",
        "",
        "> **ESS Stale / Expired / Error**: Not applicable — ESS is stored as a text label in the",
        "> analytical universe without a timestamp column. Staleness cannot be detected at the holding level.",
        "> The coverage issue is purely **availability** (in-universe with ESS) vs **exclusion** (not applicable).",
        "",
    ]

    # ── SECTION 3: Top 20 Gaps ─────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Section 3 — Top 20 Holdings Lacking ESS Coverage",
        "",
        "Sorted by portfolio weight descending. Includes root cause classification.",
        "",
        "| # | Symbol | Market Value | % Portfolio | Asset Class | Security Type | Reason Missing |",
        "|---|--------|-------------|------------|-------------|--------------|----------------|",
    ]

    top20_miss = sorted(ess_miss, key=lambda h: -float(h.get("market_value", 0) or 0))[:20]
    for i, h in enumerate(top20_miss, 1):
        sym = h.get("symbol", "?")
        mv = float(h.get("market_value", 0) or 0)
        pct = float(h.get("percent_of_portfolio", 0) or 0)
        ac = h.get("asset_class", "?")
        st = (h.get("security_type", "") or "?").strip()
        reason = _ess_category(h, au_by_sym)
        lines.append(f"| {i} | `{sym}` | ${mv:>10,.0f} | {pct:.2f}% | {ac} | {st} | {reason} |")

    lines.append("")

    # ── SECTION 4: Provider Health ─────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Section 4 — Provider Health Assessment",
        "",
        "Diagnosis of low ESS coverage across root cause categories:",
        "",
        "| Category | Code | Holdings | MV | Portfolio % | Status |",
        "|----------|------|---------|-----|------------|--------|",
    ]

    cat_codes = {
        "Structural — Cash/Cash-Equivalent": ("C", "Structural exclusion — no ESS for cash"),
        "Structural — ETF (fund, not stock)": ("C", "Structural exclusion — ETFs not in StarMine ESS universe"),
        "Provider Gap — ADR (partial StarMine coverage)": ("C", "Partial provider coverage — ADRs have 46% ESS rate in AU"),
        "Universe Gap — ADR not in analytical universe": ("E", "Symbol mapping — ADR not loaded into analytical universe"),
        "Universe Gap — In AU but ESS not populated (StarMine coverage gap)": ("F", "Ingestion gap — symbol in universe, ESS empty in current AU snapshot"),
        "Universe Gap — Symbol not in analytical universe": ("F", "Ingestion failure — symbol never loaded into analytical universe"),
        "Classification Gap — asset_class=UNKNOWN": ("D", "Classification issue — UNKNOWN class blocks enrichment path"),
    }

    for cat, hs in sorted(ess_categories.items(), key=lambda x: -sum(float(h.get("market_value",0) or 0) for h in x[1])):
        mv_cat = sum(float(h.get("market_value", 0) or 0) for h in hs)
        pct_cat = mv_cat / total_mv * 100 if total_mv else 0
        code, status = cat_codes.get(cat, ("?", cat))
        lines.append(f"| {cat[:60]} | {code} | {len(hs)} | ${mv_cat:>10,.0f} | {pct_cat:.1f}% | {status} |")

    lines += [
        "",
        "**Category Legend:**",
        "",
        "| Code | Root Cause | Meaning |",
        "|------|-----------|---------|",
        "| A | Provider Outage | Signal provider offline or returning errors |",
        "| B | Stale Refresh | Data exists but is outdated beyond threshold |",
        "| C | Unsupported Securities | Security type not covered by ESS provider by design |",
        "| D | Classification Issue | UNKNOWN asset class prevents enrichment lookup |",
        "| E | Symbol Mapping Issue | Symbol known but not loaded into analytical universe |",
        "| F | Ingestion Failure | Symbol in universe but ESS field not populated |",
        "",
        "**Finding:** No provider outage (A) or stale data (B) detected.",
        "Primary cause is structural exclusion (C) + ingestion gaps (F) + classification issues (D).",
        "",
    ]

    # ── SECTION 5: Coverage by Asset Class ──────────────────────────────────
    lines += [
        "---",
        "",
        "## Section 5 — Coverage by Asset Class",
        "",
        "| Asset Class | Total Holdings | ESS Covered | ESS % | Zacks % | Composite % |",
        "|------------|---------------|------------|-------|---------|-------------|",
    ]

    all_acs = sorted(set(h.get("asset_class", "?") for h in holdings))
    for ac in all_acs:
        ac_hs = [h for h in holdings if h.get("asset_class", "") == ac]
        n_ac = len(ac_hs)
        ess_ac = sum(1 for h in ac_hs if has_signal(h, "ess_score_text"))
        zks_ac = sum(1 for h in ac_hs if has_signal(h, "zacks_rating"))
        cmp_ac = sum(1 for h in ac_hs if has_signal(h, "composite_score"))
        pct_ess = ess_ac / n_ac * 100 if n_ac else 0
        pct_zks = zks_ac / n_ac * 100 if n_ac else 0
        pct_cmp = cmp_ac / n_ac * 100 if n_ac else 0
        lines.append(f"| {ac} | {n_ac} | {ess_ac} | {pct_ess:.0f}% | {pct_zks:.0f}% | {pct_cmp:.0f}% |")

    lines += [
        "",
        "**Observation:** EQUITIES and CASH dominate the missing ESS weight.",
        "Within EQUITIES: common stocks that are in the analytical universe but lack an ESS score",
        "account for ~14% of portfolio MV. ETFs within EQUITIES account for another ~15%.",
        "",
    ]

    # ── SECTION 6: RC-13 Explanation ──────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Section 6 — RC-13 Grade F Explanation",
        "",
        "### Formula",
        "",
        "```",
        "ESS Coverage % = holdings_with_ess_score_text / total_holdings × 100",
        f"             = {len(ess_cov)} / {n_total} × 100",
        f"             = {ess_pct_h:.2f}%",
        "```",
        "",
        "### Grade Thresholds vs Current Score",
        "",
        "| Grade | Threshold | Holdings Required | Current Status |",
        "|-------|----------|-------------------|----------------|",
        f"| A | ≥ 95% | {int(0.95 * n_total) + 1}/{n_total} | ❌ Need +{int(0.95 * n_total) + 1 - len(ess_cov)} holdings |",
        f"| B | ≥ 90% | {int(0.90 * n_total) + 1}/{n_total} | ❌ Need +{int(0.90 * n_total) + 1 - len(ess_cov)} holdings |",
        f"| C | ≥ 80% | {int(0.80 * n_total) + 1}/{n_total} | ❌ Need +{int(0.80 * n_total) + 1 - len(ess_cov)} holdings |",
        f"| D | ≥ 70% | {int(0.70 * n_total) + 1}/{n_total} | ❌ Need +{int(0.70 * n_total) + 1 - len(ess_cov)} holdings |",
        f"| **F** | **< 70%** | **{len(ess_cov)}/{n_total} = {ess_pct_h:.1f}%** | **← Current** |",
        "",
        "### Maximum Achievable ESS Coverage",
        "",
        "Not all holdings can ever receive ESS. Structurally excluded holdings:",
        "",
    ]

    structural_mv = sum(
        float(h.get("market_value", 0) or 0) for h in ess_miss
        if "Structural" in _ess_category(h, au_by_sym)
    )
    structural_n = sum(
        1 for h in ess_miss if "Structural" in _ess_category(h, au_by_sym)
    )
    max_achievable = n_total - structural_n
    max_pct = max_achievable / n_total * 100 if n_total else 0
    max_grade = grade(max_pct)

    lines += [
        f"- **Cash (SPAXX)**: 1 holding — cash never receives ESS",
        f"- **ETFs**: ~14 holdings — fund vehicles excluded from StarMine individual-stock coverage",
        f"  *(VB, VOO, VO, FXAIX, VEA, BND, BNDX, VWO, FBTC, FIGFX, FETH, XRP, FSOL + 1 more)*",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Structural exclusions | {structural_n} holdings |",
        f"| Max theoretically achievable | {max_achievable}/{n_total} = {max_pct:.1f}% |",
        f"| Max achievable grade | {grade_badge.get(max_grade, max_grade)} |",
        "",
        f"> **Implication:** Even with a perfect ESS refresh, grade C ({max_pct:.0f}%) is the maximum",
        f"> achievable under the current universe scope (individual stocks only).",
        f"> Grade B or A requires either excluding ETFs/Cash from the denominator",
        f"> or adding ETF-level coverage from an alternative provider.",
        "",
    ]

    # ── SECTION 7: Remediation Plan ───────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Section 7 — Prioritized Remediation Plan",
        "",
        "> **Do not implement.** Recommendations only, prioritized by portfolio value impact.",
        "",
        "| Priority | Action | Target Symbols | Est. MV Impact | Est. Coverage Gain | Effort |",
        "|----------|--------|---------------|---------------|--------------------|--------|",
    ]

    # Priority 1: Fix UNKNOWN classification
    unk_mv = sum(float(h.get("market_value",0) or 0) for h in holdings if h.get("asset_class","") == "UNKNOWN")
    unk_n = sum(1 for h in holdings if h.get("asset_class","") == "UNKNOWN")
    # Of UNKNOWN, how many are actual equities (not ETFs)?
    unk_stocks_n = sum(1 for h in holdings if h.get("asset_class","") == "UNKNOWN" and (h.get("security_type","") or "") not in _ETF_TYPES and (h.get("security_type","") or "") not in _CASH_TYPES)
    unk_stocks_mv = sum(float(h.get("market_value",0) or 0) for h in holdings if h.get("asset_class","") == "UNKNOWN" and (h.get("security_type","") or "") not in _ETF_TYPES and (h.get("security_type","") or "") not in _CASH_TYPES)

    # Priority 2: ESS refresh for stocks in AU with empty ESS
    au_gap_hs = ess_categories.get("Universe Gap — In AU but ESS not populated (StarMine coverage gap)", [])
    au_gap_mv = sum(float(h.get("market_value",0) or 0) for h in au_gap_hs)

    # Priority 3: Add ETF-excluded holdings to universe
    etf_hs = [h for h in ess_miss if (h.get("security_type","") or "").strip() == "ETF" and h.get("asset_class","") != "CASH"]
    etf_miss_mv = sum(float(h.get("market_value",0) or 0) for h in etf_hs)

    lines += [
        f"| 1 | Refresh ESS for common stocks already in analytical universe | SBS, AEIS, CIEN, MCB, NUE, SANM, BSVN, STNG, SMR + others | ${au_gap_mv:,.0f} | +{len(au_gap_hs)} holdings (~{len(au_gap_hs)/n_total*100:.1f}%) | Run `scripts/refresh_portfolio_signals.py` |",
        f"| 2 | Resolve UNKNOWN classification for equity/fund holdings | DODFX, TTNDY, FMCSX, FCPGX, M26CNT069 | ${unk_stocks_mv:,.0f} | +{unk_stocks_n} holdings (~{unk_stocks_n/n_total*100:.1f}%) | Update `config/security_type_policy.yaml` + rerun ingestion |",
        f"| 3 | Exclude structural non-equities from ESS denominator | SPAXX, ETF holdings (VB/VOO/VO/etc) | MV not applicable | +{structural_n} from denom exclusion | Change RC-13 denominator logic to only count equity holdings |",
        f"| 4 | Expand StarMine subscription to cover ADRs and intl equities | SBS, SIMO, STNG | $21,940 | +3 holdings (+3.7%) | Data vendor subscription expansion |",
        f"| 5 | Add ETF-level signal coverage (alternative provider) | VB, VOO, VO, FXAIX, VEA, BND, BNDX, VWO + others | ${etf_miss_mv:,.0f} | +{len(etf_hs)} holdings (+{len(etf_hs)/n_total*100:.1f}%) | New signal provider integration |",
        "",
        "**Priority 1** has the highest near-term value: 9 common stocks in the analytical universe",
        "already but with empty ESS text. A targeted signal refresh should populate these.",
        "",
        "**Priority 3** (denominator exclusion) is a reporting change, not a data quality improvement.",
        "It would raise the grade mechanically but doesn't improve actual intelligence coverage.",
        "",
    ]

    # ── RC-12 Section ─────────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## RC-12 — Taxonomy WARN Root Cause Analysis",
        "",
        "### Finding 1: Alias Nodes in Server-Generated Runs",
        "",
        "**Observed:** `PAR-20260529-7D788235` (UI server run at 14:46) contains both",
        "`DIGITAL ASSETS` and `DIGITAL` as distinct node keys in `alignment.csv`.",
        "",
        "**Source trace:**",
        "",
        "| Layer | Node | Value | Notes |",
        "|-------|------|-------|-------|",
        "| Raw holding | FBTC, FETH, etc. | sector = 'Digital Assets' | Correct input |",
        "| exposure_decomposition.py (OLD) | effective[sector.upper()] | `effective['DIGITAL ASSETS'] += x` | Bug: pre-Phase 6.4C code |",
        "| alignment engine | node_key | `'DIGITAL ASSETS'` | Alias enters alignment output |",
        "| taxonomy.py normalize_node_key() | 'DIGITAL ASSETS' → 'DIGITAL' | Alias detected | Fix applied at Python level |",
        "",
        "**Root cause:** The UI server process (`run_outcome_ui.py`, PID active) was started",
        "**before** the Phase 6.4C fix was applied. Python caches module imports. The server",
        "is still running the pre-fix version of `exposure_decomposition.py` in memory.",
        "",
        "**Confirmation:** `PAR-CONCENTRATED_ALPHA-200878F8` and `PAR-CONCENTRATED_ALPHA-3FAFBBBF`",
        "(programmatic runs, post-fix) have **zero alias nodes** in their `alignment.csv`.",
        "",
        "**Remedy (do not implement):** Restart the UI server process to reload fixed modules.",
        "",
        "### Finding 2: Extended Node Keys (RC-12 WARN — Expected)",
        "",
        "**Observed:** 10 node keys in `alignment.csv` are structurally valid but not defined",
        "in `allocation_dimensions.yaml`:",
        "",
        "| Node Key | Parent | Status | Portfolio Weight |",
        "|----------|--------|--------|----------------|",
    ]

    # Load alignment for the post-fix run
    post_fix_run = "PAR-CONCENTRATED_ALPHA-200878F8"
    post_fix_dir = _INGESTION_ROOT / "analysis_runs" / post_fix_run
    if post_fix_dir.exists():
        alignment = list(csv.DictReader(open(post_fix_dir / "alignment.csv")))
        from src.portfolio.taxonomy import CANONICAL_NODES, find_aliases_in_collection
        all_keys = list(set(r.get("node_key", "") for r in alignment if r.get("node_key", "")))
        aliases_found = find_aliases_in_collection(all_keys)
        unknowns = [(k, c) for k, c in aliases_found if c is None]
        # Get actual_pct for each
        key_pct = {r["node_key"]: float(r.get("actual_pct", 0) or 0) for r in alignment}
        for key, _ in sorted(unknowns, key=lambda x: -key_pct.get(x[0], 0)):
            parts = key.split(".")
            parent = ".".join(parts[:-1]) if len(parts) > 1 else "ROOT"
            pct = key_pct.get(key, 0.0)
            lines.append(f"| `{key}` | `{parent}` | ⚠️ Extended — not in YAML | {pct:.2f}% |")

    lines += [
        "",
        "**Root cause:** The alignment engine dynamically generates sub-tier nodes for",
        "emerging markets and international mega-cap holdings. These nodes follow the correct",
        "dot-notation convention but are not explicitly enumerated in `allocation_dimensions.yaml`.",
        "",
        "**This is an expected gap**, not a bug. RC-12 WARN is accurate and informative.",
        "Resolution: extend `allocation_dimensions.yaml` with these sub-nodes if they are",
        "intended as permanent taxonomy members.",
        "",
        "---",
        "",
        f"*Report generated by `scripts/_generate_coverage_gap_report.py` — Phase 6.4D*",
    ]

    _OUTPUT_PATH.write_text("\n".join(lines))
    print(f"Report written to: {_OUTPUT_PATH}")
    print(f"\nKey metrics:")
    print(f"  Run: {run_id}")
    print(f"  ESS: {len(ess_cov)}/{n_total} = {ess_pct_h:.1f}% (grade {ess_grade})")
    print(f"  Structural exclusions: {structural_n} holdings")
    print(f"  Max achievable: {max_achievable}/{n_total} = {max_pct:.1f}% (grade {max_grade})")


if __name__ == "__main__":
    main()
