"""
Phase 8.0B.0 — FMP API Capability Probe
Writes results to /tmp/fmp_probe_results.json
"""
import urllib.request, json, time, sys

KEY = "7OjmiAAsVH4gor067gCkGeqDJzBUg0Je"
BASE = "https://financialmodelingprep.com/api"

SYMBOLS = ["VRT", "ARW", "SNX", "ATLC", "PSX", "CBOE", "AVT", "LRCX", "CAH", "DELL", "SANM", "PCB", "CIEN", "TSM", "MU"]


def fmp_get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SIH-Research/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data, r.status, None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
            return body, e.code, None
        except:
            return None, e.code, str(e)
    except Exception as e:
        return None, None, str(e)


def classify(data, status):
    """Return (tag, detail) for a response."""
    if data is None:
        return "ERR", f"HTTP {status}"
    if isinstance(data, dict):
        msg = data.get("Error Message") or data.get("message") or data.get("error") or ""
        if msg:
            return "BLOCKED", msg[:120]
        return "OK_DICT", list(data.keys())[:8]
    if isinstance(data, list):
        if len(data) == 0:
            return "EMPTY", ""
        return "OK", len(data)
    return "UNKNOWN", str(type(data))


# ── Phase 1: Probe all endpoint types with VRT ──────────────────────────────

print("\n=== PHASE 1: ENDPOINT AVAILABILITY (VRT) ===\n")

endpoint_defs = [
    ("income_statement_annual",    f"{BASE}/v3/income-statement/{{sym}}?period=annual&limit=5&apikey={KEY}"),
    ("income_statement_quarter",   f"{BASE}/v3/income-statement/{{sym}}?period=quarter&limit=8&apikey={KEY}"),
    ("cashflow_annual",            f"{BASE}/v3/cash-flow-statement/{{sym}}?period=annual&limit=4&apikey={KEY}"),
    ("cashflow_quarter",           f"{BASE}/v3/cash-flow-statement/{{sym}}?period=quarter&limit=8&apikey={KEY}"),
    ("balance_sheet_annual",       f"{BASE}/v3/balance-sheet-statement/{{sym}}?period=annual&limit=4&apikey={KEY}"),
    ("key_metrics_annual",         f"{BASE}/v3/key-metrics/{{sym}}?period=annual&limit=4&apikey={KEY}"),
    ("key_metrics_ttm",            f"{BASE}/v3/key-metrics-ttm/{{sym}}?apikey={KEY}"),
    ("financial_growth",           f"{BASE}/v3/financial-growth/{{sym}}?period=annual&limit=4&apikey={KEY}"),
    ("ratios_annual",              f"{BASE}/v3/ratios/{{sym}}?period=annual&limit=4&apikey={KEY}"),
    ("ratios_ttm",                 f"{BASE}/v3/ratios-ttm/{{sym}}?apikey={KEY}"),
    ("analyst_estimates",          f"{BASE}/v3/analyst-estimates/{{sym}}?limit=8&apikey={KEY}"),
    ("earnings_surprises",         f"{BASE}/v3/earnings-surprises/{{sym}}?apikey={KEY}"),
    ("profile",                    f"{BASE}/v3/profile/{{sym}}?apikey={KEY}"),
    ("quote",                      f"{BASE}/v3/quote/{{sym}}?apikey={KEY}"),
    ("analyst_recommendations",    f"{BASE}/v3/analyst-stock-recommendations/{{sym}}?limit=4&apikey={KEY}"),
    ("price_target_summary",       f"{BASE}/v4/price-target-summary?symbol={{sym}}&apikey={KEY}"),
    ("upgrades_downgrades",        f"{BASE}/v4/upgrades-downgrades?symbol={{sym}}&apikey={KEY}"),
    ("historical_earnings",        f"{BASE}/v3/historical/earning_calendar/{{sym}}?limit=8&apikey={KEY}"),
    ("discounted_cashflow",        f"{BASE}/v3/discounted-cash-flow/{{sym}}?apikey={KEY}"),
    ("enterprise_values",          f"{BASE}/v3/enterprise-values/{{sym}}?limit=4&apikey={KEY}"),
    ("etf_holders",                f"{BASE}/v3/etf-stock-exposure/{{sym}}?apikey={KEY}"),
    ("institutional_holders",      f"{BASE}/v3/institutional-holder/{{sym}}?apikey={KEY}"),
    ("shares_float",               f"{BASE}/v4/shares_float?symbol={{sym}}&apikey={KEY}"),
    ("income_growth",              f"{BASE}/v3/income-statement-growth/{{sym}}?period=annual&limit=4&apikey={KEY}"),
    ("cashflow_growth",            f"{BASE}/v3/cash-flow-statement-growth/{{sym}}?period=annual&limit=4&apikey={KEY}"),
]

endpoint_status = {}
vrt_raw = {}

for name, url_tmpl in endpoint_defs:
    url = url_tmpl.replace("{sym}", "VRT")
    data, status, err = fmp_get(url)
    tag, detail = classify(data, status)
    endpoint_status[name] = {"tag": tag, "detail": detail, "status": status}
    vrt_raw[name] = data
    print(f"  {name:<35} [{tag:8}] {detail}")
    time.sleep(0.2)


# ── Phase 2: Symbol coverage matrix ─────────────────────────────────────────

print("\n\n=== PHASE 2: SYMBOL COVERAGE MATRIX ===\n")
print(f"{'Symbol':<8} {'IS':<4} {'CF':<4} {'KM':<4} {'FG':<4} {'AE':<4} {'ES':<4} {'RTTTM':<6} {'DCF':<4}")

# Key endpoints for FMS coverage
fms_endpoints = {
    "IS": f"{BASE}/v3/income-statement/{{sym}}?period=annual&limit=5&apikey={KEY}",
    "CF": f"{BASE}/v3/cash-flow-statement/{{sym}}?period=annual&limit=4&apikey={KEY}",
    "KM": f"{BASE}/v3/key-metrics-ttm/{{sym}}?apikey={KEY}",
    "FG": f"{BASE}/v3/financial-growth/{{sym}}?period=annual&limit=4&apikey={KEY}",
    "AE": f"{BASE}/v3/analyst-estimates/{{sym}}?limit=4&apikey={KEY}",
    "ES": f"{BASE}/v3/earnings-surprises/{{sym}}?apikey={KEY}",
    "RT": f"{BASE}/v3/ratios-ttm/{{sym}}?apikey={KEY}",
    "PR": f"{BASE}/v3/profile/{{sym}}?apikey={KEY}",
}

coverage_matrix = {}
for sym in SYMBOLS:
    row = {}
    for ep_name, url_tmpl in fms_endpoints.items():
        url = url_tmpl.replace("{sym}", sym)
        data, status, err = fmp_get(url)
        tag, detail = classify(data, status)
        available = tag in ("OK", "OK_DICT")
        row[ep_name] = {"available": available, "tag": tag, "rows": detail if tag == "OK" else None}
        time.sleep(0.18)
    coverage_matrix[sym] = row

for sym, row in coverage_matrix.items():
    flags = " ".join("Y" if row[k]["available"] else "N" for k in ["IS","CF","KM","FG","AE","ES","RT","PR"])
    print(f"  {sym:<8} {flags}")


# ── Phase 3: Deep field inspection on accessible endpoints ──────────────────

print("\n\n=== PHASE 3: KEY FIELD INSPECTION (VRT) ===\n")

# Income statement fields
if isinstance(vrt_raw.get("income_statement_annual"), list) and vrt_raw["income_statement_annual"]:
    row = vrt_raw["income_statement_annual"][0]
    print("Income Statement (latest annual):")
    for k in ["date","period","revenue","netIncome","eps","epsdiluted","revenueGrowth","netIncomeGrowth"]:
        val = row.get(k, "__MISSING__")
        print(f"  {k}: {val}")

# Key metrics TTM
if isinstance(vrt_raw.get("key_metrics_ttm"), list) and vrt_raw["key_metrics_ttm"]:
    row = vrt_raw["key_metrics_ttm"][0]
    print("\nKey Metrics TTM:")
    for k in ["peRatioTTM","pegRatioTTM","priceToFreeCashFlowsRatioTTM","freeCashFlowPerShareTTM","revenuePerShareTTM","netIncomePerShareTTM","earningsYieldTTM"]:
        val = row.get(k, "__MISSING__")
        print(f"  {k}: {val}")

# Financial growth
if isinstance(vrt_raw.get("financial_growth"), list) and vrt_raw["financial_growth"]:
    row = vrt_raw["financial_growth"][0]
    print("\nFinancial Growth (latest annual):")
    for k in ["date","revenueGrowth","netIncomeGrowth","epsgrowth","freeCashFlowGrowth","operatingCashFlowGrowth"]:
        val = row.get(k, "__MISSING__")
        print(f"  {k}: {val}")

# Analyst estimates
ae = vrt_raw.get("analyst_estimates")
if isinstance(ae, list) and ae:
    row = ae[0]
    print("\nAnalyst Estimates (latest):")
    for k in ["date","estimatedRevenueAvg","estimatedEpsAvg","estimatedEpsHigh","estimatedEpsLow","numberAnalystEstimatedRevenue","numberAnalystsEstimatedEps"]:
        val = row.get(k, "__MISSING__")
        print(f"  {k}: {val}")

# Earnings surprises
es = vrt_raw.get("earnings_surprises")
if isinstance(es, list) and es:
    row = es[0]
    print("\nEarnings Surprises (latest):")
    for k in ["date","actualEarningResult","estimatedEarning"]:
        val = row.get(k, "__MISSING__")
        print(f"  {k}: {val}")

# Ratios TTM
rt = vrt_raw.get("ratios_ttm")
if isinstance(rt, list) and rt:
    row = rt[0]
    print("\nRatios TTM:")
    for k in ["peRatioTTM","pegRatioTTM","freeCashFlowYieldTTM","priceToFreeCashFlowsRatioTTM"]:
        val = row.get(k, "__MISSING__")
        print(f"  {k}: {val}")
elif isinstance(rt, dict):
    print("\nRatios TTM (dict):")
    for k in ["peRatioTTM","pegRatioTTM","freeCashFlowYieldTTM","priceToFreeCashFlowsRatioTTM"]:
        val = rt.get(k, "__MISSING__")
        print(f"  {k}: {val}")


# ── Phase 4: Rate limit test ─────────────────────────────────────────────────

print("\n\n=== PHASE 4: RATE LIMIT TEST ===\n")
import datetime

# Fire 10 rapid requests and measure timing
start = time.time()
hits = 0
errors = 0
for i in range(10):
    url = f"{BASE}/v3/quote/AAPL?apikey={KEY}"
    data, status, err = fmp_get(url)
    tag, _ = classify(data, status)
    if tag in ("OK","OK_DICT"):
        hits += 1
    else:
        errors += 1
        print(f"  Request {i+1}: {tag} — {_}")
    # No sleep — testing actual rate limit

elapsed = time.time() - start
print(f"  10 rapid requests: {hits} OK, {errors} errors in {elapsed:.2f}s")
print(f"  Rate limit test: {'PASSED (no throttle detected)' if errors == 0 else 'THROTTLED'}")

# Save full results
output = {
    "endpoint_status": endpoint_status,
    "coverage_matrix": coverage_matrix,
}
with open("/tmp/fmp_full_results.json", "w") as f:
    json.dump(output, f, indent=2, default=str)

print("\n\n=== COMPLETE — results saved to /tmp/fmp_full_results.json ===")
