"""UCF validation probe — runs build_ucf_verdicts over PAR-20260531-F794D952 data."""
import json
import csv
import math
from collections import Counter
from src.portfolio.unified_conviction import build_ucf_verdicts

# Load real PAR data
with open("data/portfolio_ingestion/analysis_runs/PAR-20260531-F794D952/deployment_queue.json") as f:
    dq = json.load(f)

queue_size = len(dq["queue"])
print(f"Queue size: {queue_size}")
print(f"Quartile cutoff: {math.ceil(queue_size * 0.25)}")
print(f"Half cutoff: {math.ceil(queue_size * 0.50)}")

# Load conviction_consistency_matrix
rows = []
with open("conviction_consistency_matrix.csv") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)
print(f"Matrix rows: {len(rows)}")

# Build dict-based profiles and overlays
profiles = []
overlays = []
for r in rows:
    profiles.append({
        "symbol": r["symbol"],
        "narrative_tier": r["narrative_tier"],
        "strategic_classification": r["strategic_classification"],
        "trim_priority_score": float(r["trim_score"] or 0),
    })
    comp_raw = r["composite_score"].strip() if r.get("composite_score") else ""
    overlays.append({
        "symbol": r["symbol"],
        "composite_score": float(comp_raw) if comp_raw else None,
        "ess_score_text": r.get("ess_score_text", ""),
        "signal_direction": r["signal_direction"],
        "replay_supported": r["replay_supported"].strip().lower() == "true",
        "replay_percentile": None,
        "percent_of_portfolio": float(r["weight_pct"] or 0),
        "is_overweight_vs_target": r["is_overweight"].strip().lower() == "true",
    })

verdicts = build_ucf_verdicts(profiles, overlays, dq)

# Label distribution
label_order = ["CORE_CONVICTION_LEADER","HIGH_CONVICTION_ANCHOR","DEPLOYMENT_CANDIDATE","TACTICAL_GROWTH","MAINTAIN","TRIM_WATCH"]
label_counts = Counter(v.ucf_label for v in verdicts)
print()
print("=== Label Distribution ===")
for label in label_order:
    print(f"  {label}: {label_counts.get(label, 0)}")

# Top 10 by rank
print()
print("=== Top 10 by UCF Rank ===")
for v in verdicts[:10]:
    print(f"  {v.ucf_rank:3d}  {v.symbol:8s}  {v.ucf_label:25s}  score={v.ucf_score:6.2f}")

# Canonical 8 symbols
canonical = ["AEIS","VRT","CVE","MU","PRIM","SPAXX","PRG","TSLA"]
print()
print("=== Canonical 8 Holdings ===")
for sym in canonical:
    v = next((x for x in verdicts if x.symbol == sym), None)
    if v:
        flags = ",".join(v.conflict_flags) if v.conflict_flags else "none"
        print(f"  {sym:8s}  label={v.ucf_label:25s}  rank={v.ucf_rank:3d}  score={v.ucf_score:6.2f}  flags=[{flags}]")

# Conflict flag summary
all_flags = [f for v in verdicts for f in v.conflict_flags]
flag_counts = Counter(all_flags)
print()
print("=== Conflict Flag Summary ===")
for flag, cnt in sorted(flag_counts.items()):
    print(f"  {flag}: {cnt}")

# Verification checks
print()
print("=== Acceptance Checks ===")
def find(sym): return next((x for x in verdicts if x.symbol == sym), None)
checks = [
    ("AEIS → CORE_CONVICTION_LEADER", find("AEIS") and find("AEIS").ucf_label == "CORE_CONVICTION_LEADER"),
    ("VRT  → CORE_CONVICTION_LEADER", find("VRT") and find("VRT").ucf_label == "CORE_CONVICTION_LEADER"),
    ("CVE  → HIGH_CONVICTION_ANCHOR", find("CVE") and find("CVE").ucf_label == "HIGH_CONVICTION_ANCHOR"),
    ("MU   → HIGH_CONVICTION_ANCHOR", find("MU") and find("MU").ucf_label == "HIGH_CONVICTION_ANCHOR"),
    ("PRIM → TRIM_WATCH",             find("PRIM") and find("PRIM").ucf_label == "TRIM_WATCH"),
    ("SPAXX→ MAINTAIN",               find("SPAXX") and find("SPAXX").ucf_label == "MAINTAIN"),
    ("PRG  → TACTICAL_GROWTH",        find("PRG") and find("PRG").ucf_label == "TACTICAL_GROWTH"),
    ("TSLA → TRIM_WATCH",             find("TSLA") and find("TSLA").ucf_label == "TRIM_WATCH"),
    ("AEIS rank=1",                    find("AEIS") and find("AEIS").ucf_rank == 1),
    ("VRT  rank=2",                    find("VRT") and find("VRT").ucf_rank == 2),
]
all_pass = True
for name, result in checks:
    status = "PASS" if result else "FAIL"
    if not result:
        all_pass = False
    print(f"  [{status}] {name}")
print()
print(f"Overall: {'ALL PASS' if all_pass else 'FAILURES DETECTED'}")
