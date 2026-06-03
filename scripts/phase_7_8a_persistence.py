"""Phase 7.8A — Signal Persistence & Leadership Intelligence

Master computation script that:
1. Loads all available ESS, Zacks, Danelfin, and analytical universe history
2. Computes composite score time series per symbol
3. Computes all persistence metrics
4. Produces all 6 CSV/data deliverables

Run: PYTHONPATH=. .venv/bin/python3 scripts/phase_7_8a_persistence.py
"""
import csv
import re
import os
import json
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict
import statistics

# ── Output directory ─────────────────────────────────────────────────────────
OUT_DIR = Path("data/analysis/phase_7_8a")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Operator symbols of interest ─────────────────────────────────────────────
OPERATOR_SYMS = {"VRT", "ARW", "SNX", "ATLC", "PSX"}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — ESS Time Series Builder
# ─────────────────────────────────────────────────────────────────────────────

ESS_DIR_MAIN = Path("data/history/ess_archive/pm_processed_inputs")
ESS_DIR_OLD  = Path("data/history/ess_archive/pm_archive")


def parse_ess_date(fname):
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', fname)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = re.search(r'(\d{1,2})([A-Za-z]{3})(\d{4})', fname)
    if m:
        try:
            return datetime.strptime(m.group(1) + m.group(2) + m.group(3), '%d%b%Y').strftime('%Y-%m-%d')
        except ValueError:
            pass
    m = re.search(r'(\d{4})([A-Za-z]{3})(\d{2})', fname)
    if m:
        try:
            return datetime.strptime(m.group(3) + m.group(2) + m.group(1), '%d%b%Y').strftime('%Y-%m-%d')
        except ValueError:
            pass
    # Month-only like "May2026" — use 15th as approximation
    m = re.search(r'([A-Za-z]{3,9})(\d{4})', fname)
    if m:
        try:
            return datetime.strptime('15' + m.group(1)[:3] + m.group(2), '%d%b%Y').strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def ess_score_to_numeric(text):
    """Convert ESS text or numeric to 1-5 normalized score."""
    t = str(text).strip()
    # Try numeric (old format: 1-10 scale from LSEG StarMine)
    try:
        val = float(t)
        # Convert 1-10 → 1-5
        normalized = round((val - 1) / 9 * 4 + 1, 2)  # 1→1, 10→5
        return normalized
    except ValueError:
        pass
    # Text format
    t_upper = t.upper()
    if 'VERY_BULLISH' in t_upper or 'VERY BULLISH' in t_upper:
        return 5
    if 'BULLISH' in t_upper:
        return 4
    if 'NEUTRAL' in t_upper:
        return 3
    if 'VERY_BEARISH' in t_upper or 'VERY BEARISH' in t_upper:
        return 1
    if 'BEARISH' in t_upper:
        return 2
    return None


def ess_score_to_text(text):
    """Normalize ESS value to text category."""
    t = str(text).strip()
    try:
        val = float(t)
        # 0-10 numeric from old format
        if val >= 8.0:
            return 'VERY_BULLISH'
        if val >= 6.0:
            return 'BULLISH'
        if val >= 4.0:
            return 'NEUTRAL'
        if val >= 2.0:
            return 'BEARISH'
        return 'VERY_BEARISH'
    except ValueError:
        pass
    t_upper = t.upper()
    if 'VERY_BULLISH' in t_upper or 'VERY BULLISH' in t_upper:
        return 'VERY_BULLISH'
    if 'BULLISH' in t_upper:
        return 'BULLISH'
    if 'NEUTRAL' in t_upper:
        return 'NEUTRAL'
    if 'VERY_BEARISH' in t_upper or 'VERY BEARISH' in t_upper:
        return 'VERY_BEARISH'
    if 'BEARISH' in t_upper:
        return 'BEARISH'
    return ''


def load_ess_snapshots():
    """Load all ESS CSVs and return list of (date_str, {symbol: (score_numeric, text)})."""
    snapshots = []
    seen_dates = set()

    for ess_dir in [ESS_DIR_MAIN, ESS_DIR_OLD]:
        if not ess_dir.exists():
            continue
        for f in sorted(ess_dir.iterdir()):
            if not f.name.endswith('.csv'):
                continue
            if re.search(r'_\d+\.csv$', f.name):
                continue
            if 'backup' in f.name.lower():
                continue
            d = parse_ess_date(f.name)
            if not d:
                continue
            if d in seen_dates:
                continue
            seen_dates.add(d)
            try:
                rows = list(csv.DictReader(open(f, encoding='utf-8', errors='replace')))
            except Exception:
                continue

            # Find the ESS column (handles BOM prefix on Symbol too)
            cols = list(rows[0].keys()) if rows else []
            ess_col = None
            for c in cols:
                c_clean = c.strip().lstrip('\ufeff')
                if 'equity summary' in c_clean.lower():
                    ess_col = c
                    break
                if c_clean.upper() == 'ESS' or c_clean.lower() == 'ess from lseg starmine':
                    ess_col = c
                    break
            # Old format: "ESS from LSEG StarMine" (partial match)
            if not ess_col:
                for c in cols:
                    if 'ess' in c.lower() and 'starmine' in c.lower():
                        ess_col = c
                        break
            if not ess_col:
                continue

            # Find symbol column (handles BOM)
            sym_col = None
            for c in cols:
                if c.strip().lstrip('\ufeff').lower() == 'symbol':
                    sym_col = c
                    break

            score_map = {}
            for row in rows:
                sym = row.get(sym_col, '').strip() if sym_col else ''
                if not sym:
                    # fallback: any col named Symbol
                    for k, v in row.items():
                        if k.strip().lstrip('\ufeff').lower() == 'symbol':
                            sym = v.strip()
                            break
                if not sym:
                    continue
                ess_val = row.get(ess_col, '').strip()
                if not ess_val:
                    continue
                score = ess_score_to_numeric(ess_val)
                text = ess_score_to_text(ess_val)
                if score is not None and text:
                    score_map[sym] = (score, text)
            if score_map:
                snapshots.append((d, score_map))

    snapshots.sort(key=lambda x: x[0])
    print(f"[ESS] Loaded {len(snapshots)} snapshots from "
          f"{snapshots[0][0] if snapshots else 'N/A'} to "
          f"{snapshots[-1][0] if snapshots else 'N/A'}")
    for d, sm in snapshots:
        print(f"  {d}: {len(sm)} symbols")
    return snapshots


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Zacks & Danelfin History
# ─────────────────────────────────────────────────────────────────────────────

def load_signal_history(csv_path, provider):
    """Load a signal history master CSV → dict: {symbol: [(date, score), ...]}"""
    by_sym = defaultdict(list)
    try:
        rows = list(csv.DictReader(open(csv_path, encoding='utf-8', errors='replace')))
        for r in rows:
            sym = r.get('symbol', '').strip()
            d = r.get('capture_date', '').strip()
            score = r.get('normalized_5pt_score', '').strip()
            if sym and d and score:
                try:
                    by_sym[sym].append((d, float(score)))
                except ValueError:
                    pass
    except Exception as e:
        print(f"[{provider}] Error loading {csv_path}: {e}")
    # Sort each symbol's history
    for sym in by_sym:
        by_sym[sym].sort()
    dates = sorted(set(r.get('capture_date', '') for r in rows)) if 'rows' in dir() else []
    print(f"[{provider}] Loaded {len(by_sym)} symbols, dates: {dates}")
    return by_sym


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Analytical Universe History (composite scores)
# ─────────────────────────────────────────────────────────────────────────────

def load_universe_snapshots():
    """Load analytical universe history → dict: {symbol: [(date, composite, ess_text, zacks, danelfin), ...]}"""
    base = Path("data/history/analytical_universe")
    # Also include current
    by_sym = defaultdict(list)
    seen = set()  # (date, symbol)

    paths_to_load = []

    # History dirs
    for sd_dir in sorted(base.iterdir()):
        if not sd_dir.is_dir():
            continue
        sd = sd_dir.name.replace('snapshot_date=', '')
        for run_dir in sd_dir.iterdir():
            if not run_dir.is_dir():
                continue
            f = run_dir / 'analytical_universe.csv'
            if f.exists():
                paths_to_load.append((sd, f))

    # Current
    curr_f = Path("data/current/analytical_universe.csv")
    if curr_f.exists():
        paths_to_load.append(('2026-06-01', curr_f))

    loaded_dates = set()
    for sd, f in sorted(paths_to_load):
        if sd in loaded_dates:
            continue  # one snapshot per date
        loaded_dates.add(sd)
        try:
            rows = list(csv.DictReader(open(f, encoding='utf-8', errors='replace')))
        except Exception:
            continue
        for r in rows:
            sym = r.get('symbol', '').strip()
            if not sym:
                continue
            key = (sd, sym)
            if key in seen:
                continue
            seen.add(key)
            comp = r.get('composite_score', '')
            ess = r.get('ess_score_text', '')
            zacks = r.get('zacks_rating', '')
            danelfin = r.get('danelfin_score', '')
            try:
                comp_f = float(comp)
            except (ValueError, TypeError):
                comp_f = None
            by_sym[sym].append((sd, comp_f, ess, zacks, danelfin))

    for sym in by_sym:
        by_sym[sym].sort()

    unique_dates = sorted(loaded_dates)
    print(f"[UNIVERSE] Loaded {len(by_sym)} symbols across {len(unique_dates)} snapshot dates: {unique_dates[0]} to {unique_dates[-1]}")
    return by_sym, sorted(unique_dates)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Compute Persistence Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_persistence(universe_by_sym, all_dates, zacks_by_sym, danelfin_by_sym, ess_snapshots):
    """Compute persistence metrics for every symbol across all observed dates."""

    # Build per-date composite ranking
    # date → sorted list of (composite_score, symbol)
    date_rankings = defaultdict(list)
    for sym, entries in universe_by_sym.items():
        for (d, comp, ess, zacks, danelfin) in entries:
            if comp is not None:
                date_rankings[d].append((comp, sym))

    for d in date_rankings:
        date_rankings[d].sort(reverse=True)

    # Build rank maps: date → {symbol: rank_pct (0-100, 0=best)}
    date_rank_pcts = {}
    for d, ranked in date_rankings.items():
        n = len(ranked)
        rank_map = {}
        for i, (score, sym) in enumerate(ranked):
            rank_map[sym] = (i / n * 100.0) if n > 0 else 50.0  # 0 = top
        date_rank_pcts[d] = rank_map

    # Build ESS lookup: {symbol: {date: (numeric, text)}}
    ess_by_sym_date = defaultdict(dict)
    for d, score_map in ess_snapshots:
        for sym, (num, txt) in score_map.items():
            ess_by_sym_date[sym][d] = (num, txt)

    # Collect all symbols observed in universe
    all_syms = set(universe_by_sym.keys())
    all_universe_dates = sorted(date_rank_pcts.keys())

    print(f"[PERSISTENCE] Computing for {len(all_syms)} symbols across {len(all_universe_dates)} dates")

    results = []
    for sym in sorted(all_syms):
        entries = universe_by_sym.get(sym, [])
        dates_present = [e[0] for e in entries]
        n_obs = len(dates_present)
        if n_obs == 0:
            continue

        # Rank percentiles on each observed date
        rank_pcts = []
        for d in dates_present:
            rp = date_rank_pcts.get(d, {}).get(sym)
            if rp is not None:
                rank_pcts.append((d, rp))

        if not rank_pcts:
            continue

        sorted_rank_pcts = sorted(rank_pcts)
        rank_values = [rp for _, rp in sorted_rank_pcts]
        rank_dates = [d for d, _ in sorted_rank_pcts]

        n_top10 = sum(1 for rp in rank_values if rp <= 10.0)
        n_top5  = sum(1 for rp in rank_values if rp <= 5.0)
        n_top1  = sum(1 for rp in rank_values if rp <= 1.0)

        # Leadership streaks (top 10%)
        current_streak = 0
        longest_streak = 0
        running = 0
        for rp in rank_values:
            if rp <= 10.0:
                running += 1
                current_streak = running
            else:
                longest_streak = max(longest_streak, running)
                running = 0
        longest_streak = max(longest_streak, running)
        # current_streak: how many consecutive recent dates in top 10%
        current_streak = 0
        for rp in reversed(rank_values):
            if rp <= 10.0:
                current_streak += 1
            else:
                break

        # Composite score history
        comp_scores = [e[1] for e in entries if e[1] is not None]
        avg_comp = round(statistics.mean(comp_scores), 4) if comp_scores else None
        current_comp = next((e[1] for e in reversed(entries) if e[1] is not None), None)

        # ESS history
        ess_history = ess_by_sym_date.get(sym, {})
        ess_dates = sorted(ess_history.keys())
        ess_scores = [ess_history[d][0] for d in ess_dates]
        current_ess = ess_history.get(sorted(ess_history.keys())[-1])[1] if ess_history else ''
        avg_ess = round(statistics.mean(ess_scores), 2) if ess_scores else None

        # ESS volatility = std dev of numeric scores
        ess_vol = round(statistics.stdev(ess_scores), 3) if len(ess_scores) > 1 else 0.0

        # Zacks history
        z_entries = zacks_by_sym.get(sym, [])
        z_scores = [s for _, s in z_entries]
        avg_z = round(statistics.mean(z_scores), 2) if z_scores else None
        current_z = z_scores[-1] if z_scores else None
        z_vol = round(statistics.stdev(z_scores), 3) if len(z_scores) > 1 else 0.0

        # Danelfin history
        d_entries = danelfin_by_sym.get(sym, [])
        d_scores = [s for _, s in d_entries]
        avg_d = round(statistics.mean(d_scores), 2) if d_scores else None
        current_d = d_scores[-1] if d_scores else None
        d_vol = round(statistics.stdev(d_scores), 3) if len(d_scores) > 1 else 0.0

        # Rank volatility = std dev of rank percentiles
        rank_vol = round(statistics.stdev(rank_values), 3) if len(rank_values) > 1 else 0.0

        # Persistence Rate = n_top10 / n_obs
        persistence_rate = round(n_top10 / n_obs * 100.0, 1)

        # First/last observed dates
        first_obs = dates_present[0]
        last_obs = dates_present[-1]
        first_top10 = next((rank_dates[i] for i, rp in enumerate(rank_values) if rp <= 10.0), '')
        first_top5  = next((rank_dates[i] for i, rp in enumerate(rank_values) if rp <= 5.0), '')
        first_top1  = next((rank_dates[i] for i, rp in enumerate(rank_values) if rp <= 1.0), '')

        # Current rank percentile
        current_rank_pct = rank_pcts[-1][1] if rank_pcts else None

        # Days span
        if len(dates_present) > 1:
            d0 = datetime.strptime(dates_present[0], '%Y-%m-%d')
            d1 = datetime.strptime(dates_present[-1], '%Y-%m-%d')
            days_span = (d1 - d0).days
        else:
            days_span = 0

        results.append({
            'symbol': sym,
            'days_observed': n_obs,
            'days_span': days_span,
            'first_observed': first_obs,
            'last_observed': last_obs,
            'days_top10pct': n_top10,
            'days_top5pct': n_top5,
            'days_top1pct': n_top1,
            'persistence_rate_pct': persistence_rate,
            'current_streak_top10': current_streak,
            'longest_streak_top10': longest_streak,
            'current_rank_pct': round(current_rank_pct, 2) if current_rank_pct is not None else '',
            'avg_composite_score': avg_comp,
            'current_composite_score': round(current_comp, 4) if current_comp else '',
            'first_top10': first_top10,
            'first_top5': first_top5,
            'first_top1': first_top1,
            'avg_ess_score': avg_ess,
            'current_ess_text': current_ess,
            'ess_obs_count': len(ess_scores),
            'ess_volatility': ess_vol,
            'avg_zacks_score': avg_z,
            'current_zacks_score': current_z,
            'zacks_obs_count': len(z_scores),
            'zacks_volatility': z_vol,
            'avg_danelfin_score': avg_d,
            'current_danelfin_score': current_d,
            'danelfin_obs_count': len(d_scores),
            'danelfin_volatility': d_vol,
            'rank_volatility': rank_vol,
        })

    return results, date_rankings, date_rank_pcts


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Signal Stability Score
# ─────────────────────────────────────────────────────────────────────────────

def compute_sss(row):
    """Signal Stability Score: higher = more stable. Range 0-100."""
    # Components (each 0-20 points):
    # 1. ESS stability (low vol = high score)
    ess_vol = row.get('ess_volatility') or 0
    ess_stab = max(0, 20 - ess_vol * 10)  # 0 vol → 20, 2.0 vol → 0

    # 2. Zacks stability
    z_vol = row.get('zacks_volatility') or 0
    z_stab = max(0, 20 - z_vol * 10)

    # 3. Danelfin stability
    d_vol = row.get('danelfin_volatility') or 0
    d_stab = max(0, 20 - d_vol * 10)

    # 4. Rank stability (low rank vol = high score)
    rank_vol = row.get('rank_volatility') or 0
    rank_stab = max(0, 20 - rank_vol * 0.5)  # 0 vol → 20, 40 vol → 0

    # 5. Persistence reward
    pers = row.get('persistence_rate_pct') or 0
    pers_score = pers / 5  # 100% persist → 20

    sss = round(ess_stab + z_stab + d_stab + rank_stab + pers_score, 1)
    return min(100.0, sss)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Leadership Classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_leadership(row):
    """
    A. PERSISTENT_LEADER: high persistence rate + long streaks + stable signals
    B. EMERGING_LEADER: recent top10 streak but limited history
    C. MOMENTUM_SURGE: high current score but low persistence or short history
    D. LEADERSHIP_FAILURE: was top10, no longer
    E. CONSISTENT_MID: always present but never top10
    """
    pers = row.get('persistence_rate_pct') or 0
    n_obs = row.get('days_observed') or 0
    current_streak = row.get('current_streak_top10') or 0
    longest_streak = row.get('longest_streak_top10') or 0
    n_top10 = row.get('days_top10pct') or 0
    current_rank_pct = row.get('current_rank_pct')
    try:
        crp = float(current_rank_pct)
    except (TypeError, ValueError):
        crp = 50.0

    in_top10_now = crp <= 10.0

    if pers >= 60 and longest_streak >= 4 and n_obs >= 5:
        return 'A_PERSISTENT_LEADER'
    elif pers >= 40 and longest_streak >= 3 and n_obs >= 5:
        return 'A_PERSISTENT_LEADER'
    elif current_streak >= 2 and n_obs <= 6 and in_top10_now:
        return 'B_EMERGING_LEADER'
    elif current_streak >= 2 and pers < 40 and in_top10_now:
        return 'B_EMERGING_LEADER'
    elif in_top10_now and pers < 30 and current_streak <= 1:
        return 'C_MOMENTUM_SURGE'
    elif not in_top10_now and n_top10 > 0 and current_streak == 0:
        return 'D_LEADERSHIP_FAILURE'
    else:
        return 'E_CONSISTENT_MID'


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — Persistence Score (composite ranking metric)
# ─────────────────────────────────────────────────────────────────────────────

def compute_persistence_score(row):
    """
    Weighted persistence score for ranking purposes:
    - 40% persistence rate
    - 20% top5% rate (days_top5pct / days_observed)
    - 20% longest streak (normalized)
    - 20% signal stability (SSS)
    Max = 100
    """
    n_obs = row.get('days_observed') or 1
    pers = row.get('persistence_rate_pct') or 0  # 0-100
    top5_rate = (row.get('days_top5pct') or 0) / n_obs * 100  # 0-100
    longest_streak = row.get('longest_streak_top10') or 0
    sss = row.get('sss') or 0

    # Normalize longest streak (assume max ~10 observations)
    max_obs = 10
    streak_norm = min(1.0, longest_streak / max_obs) * 100

    ps = (pers * 0.40) + (top5_rate * 0.20) + (streak_norm * 0.20) + (sss * 0.20)
    return round(ps, 2)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 70)
    print("PHASE 7.8A — Signal Persistence & Leadership Intelligence")
    print("=" * 70)

    # Load data
    ess_snapshots = load_ess_snapshots()
    zacks_by_sym = load_signal_history('data/history/signals/zacks_history_master.csv', 'ZACKS')
    danelfin_by_sym = load_signal_history('data/history/signals/danelfin_history_master.csv', 'DANELFIN')
    universe_by_sym, all_dates = load_universe_snapshots()

    # Compute persistence
    results, date_rankings, date_rank_pcts = compute_persistence(
        universe_by_sym, all_dates, zacks_by_sym, danelfin_by_sym, ess_snapshots
    )

    print(f"\n[MAIN] Persistence computed for {len(results)} symbols")

    # Add SSS and persistence score
    for row in results:
        row['sss'] = compute_sss(row)
        row['leadership_class'] = classify_leadership(row)

    for row in results:
        row['persistence_score'] = compute_persistence_score(row)

    # Sort by persistence score desc
    results.sort(key=lambda x: x['persistence_score'], reverse=True)

    # ── Q1: signal_persistence_inventory.csv ──────────────────────────────
    print("\n[Q1] Writing signal_persistence_inventory.csv ...")
    inv_fields = [
        'symbol', 'days_observed', 'days_span', 'first_observed', 'last_observed',
        'days_top10pct', 'days_top5pct', 'days_top1pct', 'persistence_rate_pct',
        'current_streak_top10', 'longest_streak_top10', 'current_rank_pct',
        'avg_composite_score', 'current_composite_score',
        'first_top10', 'first_top5', 'first_top1',
        'avg_ess_score', 'current_ess_text', 'ess_obs_count', 'ess_volatility',
        'avg_zacks_score', 'current_zacks_score', 'zacks_obs_count', 'zacks_volatility',
        'avg_danelfin_score', 'current_danelfin_score', 'danelfin_obs_count', 'danelfin_volatility',
        'rank_volatility', 'sss', 'persistence_score', 'leadership_class',
    ]
    with open(OUT_DIR / 'signal_persistence_inventory.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=inv_fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(results)
    print(f"  Written: {len(results)} rows")

    # ── Q4: top25_signal_leaders.csv ──────────────────────────────────────
    print("\n[Q4] Writing top25_signal_leaders.csv ...")
    top25 = results[:25]
    top25_fields = [
        'symbol', 'persistence_score', 'persistence_rate_pct',
        'days_observed', 'days_top10pct', 'days_top5pct', 'days_top1pct',
        'longest_streak_top10', 'current_streak_top10', 'current_rank_pct',
        'avg_ess_score', 'current_ess_text',
        'avg_zacks_score', 'current_zacks_score',
        'avg_danelfin_score', 'current_danelfin_score',
        'avg_composite_score', 'current_composite_score',
        'sss', 'leadership_class',
    ]
    with open(OUT_DIR / 'top25_signal_leaders.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=top25_fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(top25)
    print(f"  Written: {len(top25)} rows")

    # ── Q6: signal_stability_scores.csv ───────────────────────────────────
    print("\n[Q6] Writing signal_stability_scores.csv ...")
    top50 = results[:50]
    sss_fields = [
        'symbol', 'sss', 'ess_volatility', 'zacks_volatility', 'danelfin_volatility',
        'rank_volatility', 'persistence_rate_pct', 'leadership_class',
        'avg_ess_score', 'avg_zacks_score', 'avg_danelfin_score',
        'days_observed', 'current_rank_pct',
    ]
    with open(OUT_DIR / 'signal_stability_scores.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sss_fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(top50)
    print(f"  Written: {len(top50)} rows")

    # ── Operator symbol quick reference ───────────────────────────────────
    print("\n[OPERATOR] Key symbol metrics:")
    op_results = {r['symbol']: r for r in results if r['symbol'] in OPERATOR_SYMS}
    for sym in ['VRT', 'ARW', 'SNX', 'ATLC', 'PSX']:
        r = op_results.get(sym)
        if r:
            print(f"  {sym}: ps={r['persistence_score']}, pers={r['persistence_rate_pct']}%, "
                  f"top10={r['days_top10pct']}/{r['days_observed']}, "
                  f"streak={r['current_streak_top10']}, class={r['leadership_class']}, "
                  f"comp={r['current_composite_score']}, ess={r['current_ess_text']}, "
                  f"rank={r['current_rank_pct']}")
        else:
            print(f"  {sym}: NOT FOUND in universe history")

    # Write operator JSON for report building
    with open(OUT_DIR / '_operator_data.json', 'w') as f:
        json.dump(op_results, f, indent=2, default=str)

    # Top 10 by persistence score for quick reference
    print("\n[TOP 10 by persistence score]:")
    for i, r in enumerate(results[:10]):
        print(f"  {i+1}. {r['symbol']}: ps={r['persistence_score']}, "
              f"pers={r['persistence_rate_pct']}%, class={r['leadership_class']}")

    # Leadership class distribution
    class_counts = defaultdict(int)
    for r in results:
        class_counts[r['leadership_class']] += 1
    print("\n[Leadership class distribution]:")
    for cls, cnt in sorted(class_counts.items()):
        print(f"  {cls}: {cnt}")

    # Full data dump for report building
    with open(OUT_DIR / '_all_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n[COMPLETE] All data written to {OUT_DIR}/")
