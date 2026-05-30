#!/usr/bin/env python3
"""Research script: factor effectiveness report — composite v1 vs v2_yahoo.

Generates a side-by-side comparison of v1 and v2_yahoo composite scores across
the analytical universe, answering Phase 5 signal science questions at the
*score/ranking* level (market-outcome data required for alpha/IC metrics).

Outputs (printed + optional CSV):
  • Score delta distribution (v2 - v1)
  • Coverage analysis (which signals are present per row)
  • Directional agreement / disagreement between v1 and v2
  • ABR-driven upgrade / downgrade counts
  • Per-factor average contribution under v1 and v2
  • Segment breakdown: US vs INTERNATIONAL, cap tier, sector

Usage:
    PYTHONPATH=. .venv/bin/python scripts/research/factor_effectiveness_report.py
    PYTHONPATH=. .venv/bin/python scripts/research/factor_effectiveness_report.py --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean, median, stdev

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from src.effectiveness.factor_contribution import compare_versions
from src.effectiveness.composite_versioning import COMPOSITE_VERSION_REGISTRY

UNIVERSE_PATH = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"

# Direction buckets
_DIR_THRESHOLDS = {"BULLISH": 3.5, "NEUTRAL_LO": 2.0}


def _direction(score: float, ess: str) -> str:
    ess_up = ess.strip().upper()
    if ess_up in ("BULLISH", "VERY_BULLISH"):
        return "BULLISH"
    if ess_up in ("BEARISH", "VERY_BEARISH"):
        return "BEARISH" if score < 2.5 else "NEUTRAL"
    # No ESS
    if score >= 3.5:
        return "BULLISH"
    if score >= 2.0:
        return "NEUTRAL"
    return "BEARISH"


def _bucket(v: float, thresholds: list[float]) -> int:
    for i, t in enumerate(sorted(thresholds, reverse=True)):
        if v >= t:
            return i
    return len(thresholds)


def main(csv_output: str | None = None) -> None:
    # --- load universe ---
    with UNIVERSE_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    print(f"Loaded {len(rows)} rows from analytical_universe.csv")

    # Require v2 columns to be present.
    if "composite_v2_yahoo" not in (rows[0].keys() if rows else []):
        print(
            "[ERROR] composite_v2_yahoo column not found.  Run generate_v2_scores.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- score each row ---
    records = []
    for r in rows:
        sym = str(r.get("symbol", "")).strip().upper()
        ess = str(r.get("ess_score_text", "")).strip()
        zacks = str(r.get("zacks_rating", "")).strip()
        danelfin = str(r.get("danelfin_score", "")).strip()
        yahoo_norm = str(r.get("yahoo_abr_normalized", "")).strip()
        cap = str(r.get("market_cap_bucket", "")).strip().upper()
        geo = str(r.get("geography", "")).strip().upper()
        sector = str(r.get("sector", "")).strip().upper()

        try:
            v1_score = float(r.get("composite_score") or 0)
        except ValueError:
            v1_score = 3.0
        try:
            v2_score = float(r.get("composite_v2_yahoo") or 0)
        except ValueError:
            v2_score = v1_score

        delta = round(v2_score - v1_score, 6)
        dir_v1 = _direction(v1_score, ess)
        dir_v2 = _direction(v2_score, ess)
        has_abr = bool(yahoo_norm)
        has_ess = bool(ess)
        has_zacks = bool(zacks)
        has_danelfin = bool(danelfin)

        records.append({
            "symbol": sym,
            "cap": cap,
            "geo": geo,
            "sector": sector,
            "ess": ess,
            "has_ess": has_ess,
            "has_zacks": has_zacks,
            "has_danelfin": has_danelfin,
            "has_abr": has_abr,
            "yahoo_norm": yahoo_norm,
            "v1": v1_score,
            "v2": v2_score,
            "delta": delta,
            "dir_v1": dir_v1,
            "dir_v2": dir_v2,
        })

    total = len(records)
    abr_rows = [r for r in records if r["has_abr"]]
    no_abr   = [r for r in records if not r["has_abr"]]

    # --- summary statistics ---
    deltas = [r["delta"] for r in records]
    upgrades   = [r for r in records if r["dir_v2"] != r["dir_v1"] and r["v2"] > r["v1"]]
    downgrades = [r for r in records if r["dir_v2"] != r["dir_v1"] and r["v2"] < r["v1"]]
    unchanged  = [r for r in records if r["dir_v1"] == r["dir_v2"]]

    print("\n" + "="*70)
    print("COMPOSITE v1 vs v2_yahoo FACTOR EFFECTIVENESS REPORT")
    print("="*70)

    print(f"\n{'SIGNAL COVERAGE':}")
    print(f"  Total rows          : {total}")
    print(f"  Has ESS             : {sum(r['has_ess'] for r in records):>6}  ({100*sum(r['has_ess'] for r in records)/total:.1f}%)")
    print(f"  Has Zacks           : {sum(r['has_zacks'] for r in records):>6}  ({100*sum(r['has_zacks'] for r in records)/total:.1f}%)")
    print(f"  Has Danelfin        : {sum(r['has_danelfin'] for r in records):>6}  ({100*sum(r['has_danelfin'] for r in records)/total:.1f}%)")
    print(f"  Has Yahoo ABR       : {len(abr_rows):>6}  ({100*len(abr_rows)/total:.1f}%)")
    print(f"  All 4 signals       : {sum(r['has_ess'] and r['has_zacks'] and r['has_danelfin'] and r['has_abr'] for r in records):>6}")

    print(f"\n{'SCORE DELTA (v2 - v1)':}")
    print(f"  All rows   — mean={mean(deltas):+.4f}  median={median(deltas):+.4f}  stdev={stdev(deltas):.4f}"
          f"  range=[{min(deltas):+.4f}, {max(deltas):+.4f}]")
    if abr_rows:
        abr_deltas = [r["delta"] for r in abr_rows]
        print(f"  With ABR   — mean={mean(abr_deltas):+.4f}  median={median(abr_deltas):+.4f}  stdev={stdev(abr_deltas):.4f}")
    no_abr_deltas = [r["delta"] for r in no_abr]
    if no_abr_deltas:
        print(f"  No ABR     — mean={mean(no_abr_deltas):+.4f}  (should be near zero if only ABR matters)")

    print(f"\n{'DIRECTIONAL CHANGES (ESS-aware direction buckets)':}")
    print(f"  Unchanged direction : {len(unchanged):>6}  ({100*len(unchanged)/total:.1f}%)")
    print(f"  Directional upgrade : {len(upgrades):>6}  ({100*len(upgrades)/total:.1f}%)")
    print(f"  Directional downgrade:{len(downgrades):>6}  ({100*len(downgrades)/total:.1f}%)")
    for sym in [r["symbol"] for r in sorted(upgrades, key=lambda x: abs(x["delta"]), reverse=True)[:5]]:
        r = next(x for x in upgrades if x["symbol"] == sym)
        print(f"    ↑ {sym:<8} {r['dir_v1']}→{r['dir_v2']}  delta={r['delta']:+.4f}  abr_norm={r['yahoo_norm']}")
    for sym in [r["symbol"] for r in sorted(downgrades, key=lambda x: abs(x["delta"]), reverse=True)[:5]]:
        r = next(x for x in downgrades if x["symbol"] == sym)
        print(f"    ↓ {sym:<8} {r['dir_v1']}→{r['dir_v2']}  delta={r['delta']:+.4f}  abr_norm={r['yahoo_norm']}")

    # --- largest movers ---
    print(f"\n{'TOP 10 LARGEST DELTA (|v2-v1|)':}")
    print(f"  {'SYM':<8} {'Cap':<8} {'ESS':<14} {'Danelfin':>9} {'ABR_n':>6} {'v1':>7} {'v2':>7} {'Δ':>7}")
    for r in sorted(records, key=lambda x: abs(x["delta"]), reverse=True)[:10]:
        print(
            f"  {r['symbol']:<8} {r['cap']:<8} {r['ess']:<14} "
            f"{r['has_danelfin'] and next((x for x in records if x['symbol']==r['symbol']), None) and str(next((x for x in rows if x.get('symbol','').upper()==r['symbol']), {}).get('danelfin_score','n/a')):>9} "
            f"{r['yahoo_norm']:>6} {r['v1']:>7.4f} {r['v2']:>7.4f} {r['delta']:>+7.4f}"
        )

    # --- geography/cap breakdown ---
    for group_key in ("geo", "cap"):
        groups: dict[str, list] = {}
        for r in records:
            g = r[group_key]
            groups.setdefault(g, []).append(r)
        print(f"\n{'SCORE DELTA BY ' + group_key.upper():}")
        print(f"  {'Group':<20} {'Count':>6} {'With ABR':>9} {'Δ mean':>8} {'Δ stdev':>8}")
        for g in sorted(groups):
            grs = groups[g]
            gd = [r["delta"] for r in grs]
            gabr = sum(r["has_abr"] for r in grs)
            print(f"  {g:<20} {len(grs):>6} {gabr:>9} {mean(gd):>+8.4f} {stdev(gd) if len(gd)>1 else 0.0:>8.4f}")

    # --- Phase 5 signal science questions (score-level, pre-return data) ---
    print(f"\n{'SIGNAL SCIENCE (score-level diagnostics)':}")
    # Q4: Does Yahoo help in small caps?
    small_cap_with_abr = [r for r in records if r["cap"] in ("SMALL", "MICRO") and r["has_abr"]]
    large_cap_with_abr = [r for r in records if r["cap"] in ("LARGE", "MEGA") and r["has_abr"]]
    print(f"  Small/Micro cap rows with ABR: {len(small_cap_with_abr)}")
    print(f"  Large/Mega cap rows with ABR:  {len(large_cap_with_abr)}")
    if small_cap_with_abr:
        sm_deltas = [r["delta"] for r in small_cap_with_abr]
        print(f"  Small/Micro mean delta: {mean(sm_deltas):+.4f}")
    if large_cap_with_abr:
        lg_deltas = [r["delta"] for r in large_cap_with_abr]
        print(f"  Large/Mega mean delta:  {mean(lg_deltas):+.4f}")

    # Q6: Does Yahoo merely follow momentum? Proxy: is ABR correlated with ESS?
    ess_abr_pairs = [
        (r["ess"], float(r["yahoo_norm"]))
        for r in records
        if r["has_abr"] and r["has_ess"]
    ]
    if len(ess_abr_pairs) > 10:
        ess_score_map = {"VERY_BULLISH": 5, "BULLISH": 4, "NEUTRAL": 3, "BEARISH": 2, "VERY_BEARISH": 1}
        ess_nums = [ess_score_map.get(e, 3) for e, _ in ess_abr_pairs]
        abr_nums = [a for _, a in ess_abr_pairs]
        n = len(ess_nums)
        cov_xy = sum((x - mean(ess_nums)) * (y - mean(abr_nums)) for x, y in zip(ess_nums, abr_nums)) / n
        std_x = stdev(ess_nums)
        std_y = stdev(abr_nums)
        corr = cov_xy / (std_x * std_y) if std_x and std_y else 0.0
        print(f"\n  ESS vs Yahoo ABR Pearson correlation (n={n}): {corr:.3f}")
        print(f"  (If >0.7: Yahoo likely follows momentum/ESS; if <0.5: additive signal)")

    # Q2: False positive proxy — rows where v1=BULLISH but ABR=SELL-ISH (norm<2.5)
    if abr_rows:
        fp_candidates = [r for r in abr_rows if r["dir_v1"] == "BULLISH" and float(r["yahoo_norm"]) < 2.5]
        fn_candidates = [r for r in abr_rows if r["dir_v1"] == "BEARISH" and float(r["yahoo_norm"]) > 3.5]
        print(f"\n  Potential false positives (v1=BULLISH, Yahoo bearish): {len(fp_candidates)}")
        print(f"  Potential false negatives (v1=BEARISH, Yahoo bullish):  {len(fn_candidates)}")
        for r in sorted(fp_candidates, key=lambda x: x["delta"])[:5]:
            print(f"    {r['symbol']:<8} ESS={r['ess']:<14} v1={r['v1']:.3f} v2={r['v2']:.3f} abr_norm={r['yahoo_norm']}")

    print("\n" + "="*70)
    print("NOTE: alpha, IC, hit rate, and return-based metrics require forward")
    print("return data.  Run replay engine comparisons once v2 is promoted to")
    print("CURRENT_RECOMMENDATION mode in the replay registry.")
    print("="*70)

    # --- optional CSV output ---
    if csv_output:
        out_path = Path(csv_output)
        out_cols = ["symbol", "cap", "geo", "sector", "ess", "has_ess", "has_zacks",
                    "has_danelfin", "has_abr", "yahoo_norm", "v1", "v2", "delta", "dir_v1", "dir_v2"]
        with out_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=out_cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        print(f"\nDetailed CSV written → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Factor effectiveness report: v1 vs v2_yahoo.")
    parser.add_argument("--csv", metavar="FILE", help="Write per-symbol detail to CSV.")
    args = parser.parse_args()
    main(csv_output=args.csv)
