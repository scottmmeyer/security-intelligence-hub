import json
from pathlib import Path

r = json.load(open("data/analysis/fmp_dq_validation.json"))

KM_FIELDS = ["peRatioTTM", "evToEbitdaTTM", "priceToFreeCashFlowsRatioTTM",
             "freeCashFlowYieldTTM", "roeTTM", "roicTTM", "earningsYieldTTM",
             "revenuePerShareTTM", "netIncomePerShareTTM"]

GC_FIELDS = ["strongBuy", "buy", "hold", "sell", "strongSell"]
ES_FIELDS = ["date", "actualEarningResult", "estimatedEarning", "symbol"]
IG_FIELDS = ["date", "revenueGrowth", "epsgrowth", "grossProfitGrowth"]

print("=" * 70)
print("SECTION 1: KEY METRICS TTM")
print("=" * 70)
for sym in r:
    d = r[sym]["key_metrics_ttm"]["data"]
    item = d[0] if isinstance(d, list) and d else (d if isinstance(d, dict) else {})
    vals = {f: item.get(f) for f in KM_FIELDS}
    present = sum(1 for v in vals.values() if v is not None and v != "")
    print(f"\n  {sym} ({present}/{len(KM_FIELDS)} fields populated):")
    for f, v in vals.items():
        print(f"    {f}: {v}")

print("\n" + "=" * 70)
print("SECTION 2: GRADES CONSENSUS")
print("=" * 70)
for sym in r:
    d = r[sym]["grades_consensus"]["data"]
    item = d[0] if isinstance(d, list) and d else {}
    if not item:
        print(f"\n  {sym}: EMPTY RESPONSE")
        continue
    sb  = item.get("strongBuy", 0)
    b   = item.get("buy", 0)
    h   = item.get("hold", 0)
    s   = item.get("sell", 0)
    ss  = item.get("strongSell", 0)
    total = sum(x or 0 for x in [sb, b, h, s, ss])
    print(f"  {sym}: sb={sb} b={b} h={h} s={s} ss={ss} total={total}")

print("\n" + "=" * 70)
print("SECTION 3: EARNINGS SURPRISES")
print("=" * 70)
for sym in r:
    d = r[sym]["earnings"]["data"]
    if not isinstance(d, list) or not d:
        print(f"  {sym}: EMPTY")
        continue
    beats = 0
    rows = []
    for item in d[:8]:
        actual = item.get("actualEarningResult") or item.get("actualEPS")
        est    = item.get("estimatedEarning") or item.get("estimatedEPS")
        dt     = item.get("date", "")
        if actual is not None and est is not None:
            try:
                a, e_ = float(actual), float(est)
                pct = round((a - e_) / abs(e_) * 100, 1) if e_ != 0 else None
                if a >= e_: beats += 1
                rows.append(f"  {dt[:7]}  act={a:6.2f} est={e_:6.2f} surp={pct}%")
            except: pass
    print(f"\n  {sym}: {len(d)} quarters, {beats}/{min(len(d),8)} beats")
    for row in rows[:4]:
        print("   ", row)
    # Check field names
    if d:
        all_keys = list(d[0].keys())
        print(f"    keys: {all_keys}")

print("\n" + "=" * 70)
print("SECTION 4: INCOME STATEMENT GROWTH")
print("=" * 70)
for sym in r:
    d = r[sym]["income_growth"]["data"]
    if not isinstance(d, list) or not d:
        print(f"  {sym}: EMPTY")
        continue
    print(f"\n  {sym}: {len(d)} periods")
    for item in d[:2]:
        dt  = item.get("date", "?")
        rev = item.get("revenueGrowth") or item.get("growthRevenue")
        eps = item.get("epsgrowth") or item.get("growthEPS") or item.get("growthEps")
        gp  = item.get("grossProfitGrowth") or item.get("growthGrossProfit")
        print(f"    {dt[:10]}  rev={rev}  eps={eps}  gp={gp}")
    if d:
        print(f"    available keys: {list(d[0].keys())}")

print("\n" + "=" * 70)
print("SECTION 5: NULL RATE SUMMARY")
print("=" * 70)
for sym in r:
    d_km = r[sym]["key_metrics_ttm"]["data"]
    item_km = d_km[0] if isinstance(d_km, list) and d_km else {}
    km_populated = sum(1 for f in KM_FIELDS if item_km.get(f) is not None)
    d_gc = r[sym]["grades_consensus"]["data"]
    item_gc = d_gc[0] if isinstance(d_gc, list) and d_gc else {}
    gc_populated = sum(1 for f in GC_FIELDS if item_gc.get(f) is not None)
    d_es = r[sym]["earnings"]["data"]
    es_populated = len(d_es) if isinstance(d_es, list) else 0
    d_ig = r[sym]["income_growth"]["data"]
    ig_populated = len(d_ig) if isinstance(d_ig, list) else 0
    print(f"  {sym:<6}: km={km_populated}/{len(KM_FIELDS)} gc={gc_populated}/{len(GC_FIELDS)} es={es_populated}Q ig={ig_populated}Q")
