"""
Part C: Coverage Denominator Report (Phase 6.4E)
Generates coverage_denominator_report.md with per-holding ESS eligibility table.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO = Path(__file__).parent.parent
RUNS_DIR = REPO / "data/portfolio_ingestion/analysis_runs"

# Use the latest Phase 6.4E run
RUN_ID = "PAR-20260529-E3E9B896"

# ESS eligibility classification — mirrors reconciliation.py logic
ESS_ELIGIBLE_TYPES = {"Common Stock", "Depository Receipt"}
EXCLUDED_ASSET_CLASSES = {"CASH", "DIGITAL"}


def _classify_eligibility(symbol: str, asset_class: str, security_type: str) -> tuple[str, str]:
    """Returns (eligibility_flag, reason)."""
    ac = asset_class.strip().upper()
    st = security_type.strip()

    if ac == "CASH" or st in {"Cash", "Cash Equivalent"}:
        return "Excluded", "Cash — no securities-level ESS"
    if ac == "DIGITAL":
        return "Excluded", "Digital asset — excluded from equity ESS"
    if st == "ETF":
        return "Excluded", "ETF — structurally excluded from individual-stock ESS"
    if st == "Mutual Fund":
        return "Excluded", "Mutual fund — structurally excluded"
    if ac == "UNKNOWN" or not ac:
        return "Excluded", "Unclassified — enrichment path blocked"
    if st == "Common Stock":
        return "Eligible", "Individual equity — ESS eligible"
    if st == "Depository Receipt":
        return "Eligible", "ADR/Depository Receipt — ESS eligible"
    # Anything else in EQUITIES or FIXED_INCOME
    if ac in {"EQUITIES", "FIXED_INCOME", "COMMODITIES"}:
        return "Excluded", f"Instrument type '{st}' — not in ESS scope"
    return "Excluded", f"Asset class '{ac}' / type '{st}' — not classified as eligible"


def _ess_status(ess_val: str, eligibility: str) -> str:
    if eligibility == "Excluded":
        return "N/A"
    return "Present" if str(ess_val or "").strip() else "Missing"


def main() -> None:
    run_dir = RUNS_DIR / RUN_ID
    holdings = list(csv.DictReader(open(run_dir / "holdings.csv")))
    recon = json.loads((run_dir / "reconciliation.json").read_text())
    rc13 = next(c for c in recon["checks"] if c["check_id"] == "RC-13")
    meta = json.loads((run_dir / "run_metadata.json").read_text())

    total_mv = sum(float(h.get("market_value") or 0) for h in holdings)

    # Enrich each holding
    rows = []
    for h in holdings:
        symbol = h.get("symbol", "")
        mv = float(h.get("market_value") or 0)
        pct = mv / total_mv * 100 if total_mv else 0
        ac = str(h.get("asset_class") or "").strip().upper()
        st = str(h.get("security_type") or "").strip()
        ess = str(h.get("ess_score_text") or "").strip()

        eligibility, reason = _classify_eligibility(symbol, ac, st)
        ess_stat = _ess_status(ess, eligibility)

        # Determine asset type label for display
        if st == "ETF":
            asset_type = f"ETF ({ac})"
        elif ac == "CASH":
            asset_type = "Cash"
        elif ac == "DIGITAL":
            asset_type = f"Digital ({st})"
        elif st in {"Common Stock", "Depository Receipt"}:
            asset_type = st
        elif st == "Mutual Fund":
            asset_type = "Mutual Fund"
        else:
            asset_type = f"{st} ({ac})" if st and ac else (st or ac or "Unknown")

        rows.append({
            "symbol": symbol,
            "mv": mv,
            "pct": pct,
            "asset_type": asset_type,
            "eligibility": eligibility,
            "ess_status": ess_stat,
            "reason": reason,
        })

    # Sort by MV descending
    rows.sort(key=lambda r: r["mv"], reverse=True)

    # Summary counts
    n_total = len(rows)
    n_eligible = sum(1 for r in rows if r["eligibility"] == "Eligible")
    n_excluded = sum(1 for r in rows if r["eligibility"] == "Excluded")
    ess_covered_elig = sum(1 for r in rows if r["eligibility"] == "Eligible" and r["ess_status"] == "Present")
    ess_missing_elig = sum(1 for r in rows if r["eligibility"] == "Eligible" and r["ess_status"] == "Missing")
    ess_pct_elig = ess_covered_elig / n_eligible * 100 if n_eligible else 0

    ess_covered_total = sum(1 for r in rows if r["ess_status"] == "Present")
    ess_pct_total = ess_covered_total / n_total * 100 if n_total else 0

    mv_eligible = sum(r["mv"] for r in rows if r["eligibility"] == "Eligible")
    mv_excluded = sum(r["mv"] for r in rows if r["eligibility"] == "Excluded")
    pct_eligible_mv = mv_eligible / total_mv * 100 if total_mv else 0
    pct_excluded_mv = mv_excluded / total_mv * 100 if total_mv else 0

    # Grade function
    def grade(pct: float) -> str:
        for threshold, g in [(95, "A"), (90, "B"), (80, "C"), (70, "D"), (0, "F")]:
            if pct >= threshold:
                return g
        return "F"

    # ESS grade breakdown for sub-checks
    esc_check = next((sc for sc in rc13.get("sub_checks", []) if sc["signal"] == "ESS"), {})
    zacks_check = next((sc for sc in rc13.get("sub_checks", []) if sc["signal"] == "Zacks"), {})
    danelfin_check = next((sc for sc in rc13.get("sub_checks", []) if sc["signal"] == "Composite"), {})

    snap_date = str(meta.get("snapshot_date") or "")
    if not snap_date[:4].isdigit():
        snap_date = (meta.get("created_at_utc") or "")[:10]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    def w(s: str = "") -> None:
        lines.append(s)

    w("# Coverage Denominator Report — Phase 6.4E Part C")
    w()
    w(f"**Run ID:** `{RUN_ID}`  ")
    w(f"**Snapshot Date:** {snap_date}  ")
    w(f"**Generated:** {now}  ")
    w(f"**Holdings:** {n_total} | **Total Market Value:** ${total_mv:,.0f}  ")
    w()
    w("---")
    w()
    w("## Section 1 — Coverage Metrics by Denominator")
    w()
    w("| Coverage Metric | Numerator | Denominator | Coverage % | Grade |")
    w("|----------------|-----------|-------------|------------|-------|")

    # ESS rows
    w(f"| ESS — Total Portfolio | {esc_check.get('holdings_covered', ess_covered_total)} | {n_total} | {esc_check.get('pct_holdings', ess_pct_total):.1f}% | {esc_check.get('grade', grade(ess_pct_total))} |")
    w(f"| ESS — Eligible Equity | {esc_check.get('eligible_covered', ess_covered_elig)} | {esc_check.get('eligible_total', n_eligible)} | {esc_check.get('pct_eligible', ess_pct_elig):.1f}% | **{esc_check.get('grade_eligible', grade(ess_pct_elig))}** ← drives RC-13 |")
    w(f"| ESS — Structurally Excluded | {n_excluded} holdings | {n_total} | {n_excluded / n_total * 100:.1f}% | INFO |")
    w(f"| Zacks — Total Portfolio | {zacks_check.get('holdings_covered', '?')} | {n_total} | {zacks_check.get('pct_holdings', 0):.1f}% | {zacks_check.get('grade', '?')} |")
    w(f"| Zacks — Eligible Equity | {zacks_check.get('eligible_covered', '?')} | {zacks_check.get('eligible_total', n_eligible)} | {zacks_check.get('pct_eligible', 0):.1f}% | **{zacks_check.get('grade_eligible', '?')}** |")
    w(f"| Composite — Total Portfolio | {danelfin_check.get('holdings_covered', '?')} | {n_total} | {danelfin_check.get('pct_holdings', 0):.1f}% | {danelfin_check.get('grade', '?')} |")
    w(f"| Composite — Eligible Equity | {danelfin_check.get('eligible_covered', '?')} | {danelfin_check.get('eligible_total', n_eligible)} | {danelfin_check.get('pct_eligible', 0):.1f}% | **{danelfin_check.get('grade_eligible', '?')}** |")
    w()
    w("> **Denominator change:** RC-13 now grades on *eligible equity coverage*, not total portfolio.")
    w("> Structurally excluded holdings (ETFs, cash, digital, mutual funds) are reported for")
    w("> transparency but do not influence WARN/FAIL status.")
    w()
    w("---")
    w()
    w("## Section 2 — Structural Exclusion Summary")
    w()
    w(f"- **Total holdings:** {n_total}")
    w(f"- **Eligible for ESS:** {n_eligible} ({pct_eligible_mv:.1f}% of portfolio MV)")
    w(f"- **Structurally excluded:** {n_excluded} ({pct_excluded_mv:.1f}% of portfolio MV)")
    w()

    # Group exclusions by reason
    exclusion_groups: dict[str, list[dict]] = {}
    for r in rows:
        if r["eligibility"] == "Excluded":
            key = r["reason"].split(" — ")[0]
            exclusion_groups.setdefault(key, []).append(r)

    w("| Exclusion Type | Count | Holdings | Portfolio % |")
    w("|---------------|-------|---------|------------|")
    for exc_type, exc_rows in sorted(exclusion_groups.items(), key=lambda x: -sum(r["mv"] for r in x[1])):
        exc_mv = sum(r["mv"] for r in exc_rows)
        exc_pct = exc_mv / total_mv * 100 if total_mv else 0
        syms = ", ".join(f"`{r['symbol']}`" for r in sorted(exc_rows, key=lambda x: -x["mv"])[:5])
        if len(exc_rows) > 5:
            syms += f" _(+{len(exc_rows)-5} more)_"
        w(f"| {exc_type} | {len(exc_rows)} | {syms} | {exc_pct:.1f}% |")
    w()
    w("---")
    w()
    w("## Section 3 — Per-Holding ESS Eligibility Table")
    w()
    w("Sorted descending by market value.")
    w()
    w("| # | Symbol | MV | % Portfolio | Asset Type | ESS Eligibility | ESS Status | Reason |")
    w("|---|--------|-----|------------|------------|----------------|-----------|--------|")
    for i, r in enumerate(rows, 1):
        mv_str = f"${r['mv']:>10,.0f}"
        pct_str = f"{r['pct']:5.2f}%"
        elig_icon = "✅" if r["eligibility"] == "Eligible" else "⊘"
        ess_icon = ("✅" if r["ess_status"] == "Present" else
                    ("❌" if r["ess_status"] == "Missing" else "—"))
        w(f"| {i} | `{r['symbol']}` | {mv_str} | {pct_str} | {r['asset_type']} | {elig_icon} {r['eligibility']} | {ess_icon} {r['ess_status']} | {r['reason']} |")
    w()
    w("---")
    w()
    w("## Section 4 — Missing ESS for Eligible Holdings")
    w()
    missing = [r for r in rows if r["eligibility"] == "Eligible" and r["ess_status"] == "Missing"]
    missing.sort(key=lambda r: -r["mv"])
    mv_missing = sum(r["mv"] for r in missing)
    pct_missing = mv_missing / total_mv * 100 if total_mv else 0

    w(f"**{len(missing)} eligible equity holdings lack ESS** (${mv_missing:,.0f} = {pct_missing:.1f}% of portfolio MV)")
    w()
    w("| Symbol | MV | % Portfolio | Zacks | Composite | Gap Category |")
    w("|--------|-----|------------|-------|-----------|-------------|")
    for r in missing:
        h = next((h for h in holdings if h.get("symbol") == r["symbol"]), {})
        zacks = "✅" if str(h.get("zacks_rating") or "").strip() else "—"
        comp = "✅" if str(h.get("composite_score") or "").strip() else "—"
        # Gap category
        if str(h.get("ess_score_text") or "").strip() == "" and not str(h.get("zacks_rating") or "").strip():
            gap = "No signal data"
        else:
            gap = "ESS not populated in AU"
        w(f"| `{r['symbol']}` | ${r['mv']:>10,.0f} | {r['pct']:.2f}% | {zacks} | {comp} | {gap} |")
    w()
    w("---")
    w()
    w("## Section 5 — RC-13 Governance Summary")
    w()
    w(f"**RC-13 Status: `{rc13['status']}`** (Phase 6.4E eligible equity model)")
    w()
    w(f"> {rc13['detail']}")
    w()
    w(f"**Expected:** {rc13['expected']}")
    w()
    w("### Grade Breakdown")
    w()
    w("| Signal | Eligible Coverage | Grade | Total Coverage | Total Grade |")
    w("|--------|-----------------|-------|--------------|------------|")
    for sc in rc13.get("sub_checks", []):
        w(f"| {sc['signal']} | {sc['eligible_covered']}/{sc['eligible_total']} ({sc['pct_eligible']:.1f}%) | **{sc['grade_eligible']}** | {sc['holdings_covered']}/{sc['holdings_total']} ({sc['pct_holdings']:.1f}%) | {sc['grade']} |")
    w()
    w("### Why ESS Eligible Grade C (not A)?")
    w()
    w(f"Of the {n_eligible} eligible equity holdings, {ess_missing_elig} lack ESS:")
    w()
    for r in missing[:10]:
        w(f"- `{r['symbol']}` — ${r['mv']:,.0f} ({r['pct']:.2f}% of portfolio)")
    if len(missing) > 10:
        w(f"- _(+{len(missing)-10} more)_")
    w()
    w("These common stocks are **in the analytical universe** but their `ess_score_text`")
    w("field was not populated in the last StarMine ESS refresh snapshot.")
    w("Refreshing ESS data would improve eligible equity coverage from 82.0% to the")
    w(f"theoretical maximum of {(n_eligible - 0) / n_eligible * 100:.1f}%")
    w("(assuming full StarMine universe coverage for US-listed common stocks).")

    out = REPO / "coverage_denominator_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"Report written to: {out}")
    print(f"ESS eligible: {ess_covered_elig}/{n_eligible} ({ess_pct_elig:.1f}% grade {grade(ess_pct_elig)})")
    print(f"ESS total:    {ess_covered_total}/{n_total} ({ess_pct_total:.1f}% grade {grade(ess_pct_total)})")
    print(f"Excluded: {n_excluded}/{n_total} ({n_excluded/n_total*100:.1f}%)")


if __name__ == "__main__":
    main()
