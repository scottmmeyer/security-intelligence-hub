"""
Phase 8.0B.0 — FMP Stable API Probe
Tests the new FMP 'stable' endpoint paths (post-2024 migration)
"""
import urllib.request, json, time

KEY = "7OjmiAAsVH4gor067gCkGeqDJzBUg0Je"
STABLE = "https://financialmodelingprep.com/stable"
V3 = "https://financialmodelingprep.com/api/v3"
V4 = "https://financialmodelingprep.com/api/v4"

def fmp_get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SIH-Research/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status, None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
            return body, e.code, None
        except:
            return None, e.code, str(e)
    except Exception as e:
        return None, None, str(e)

def tag(data, status, err):
    if err:
        return f"ERR: {err[:60]}"
    if data is None:
        return f"NULL HTTP={status}"
    if isinstance(data, dict):
        msg = data.get("Error Message") or data.get("message") or data.get("error") or ""
        if msg:
            return f"BLOCKED: {msg[:100]}"
        if data.get("statusCode") == 403 or status == 403:
            return "FORBIDDEN"
        return f"OK_DICT keys={list(data.keys())[:5]}"
    if isinstance(data, list):
        if len(data) == 0:
            return "EMPTY_LIST"
        return f"OK rows={len(data)} sample_keys={list(data[0].keys())[:5] if data else []}"
    return f"UNKNOWN type={type(data)}"

print("=== FMP STABLE API PROBE ===\n")
print("Testing new stable endpoint paths...\n")

sym = "VRT"
stable_endpoints = [
    ("stable/income-statement",       f"{STABLE}/income-statement?symbol={sym}&apikey={KEY}"),
    ("stable/income-stmt-annual",     f"{STABLE}/income-statement?symbol={sym}&period=annual&apikey={KEY}"),
    ("stable/income-stmt-quarter",    f"{STABLE}/income-statement?symbol={sym}&period=quarter&apikey={KEY}"),
    ("stable/balance-sheet",          f"{STABLE}/balance-sheet-statement?symbol={sym}&apikey={KEY}"),
    ("stable/cash-flow",              f"{STABLE}/cash-flow-statement?symbol={sym}&apikey={KEY}"),
    ("stable/key-metrics",            f"{STABLE}/key-metrics?symbol={sym}&apikey={KEY}"),
    ("stable/key-metrics-ttm",        f"{STABLE}/key-metrics-ttm?symbol={sym}&apikey={KEY}"),
    ("stable/ratios",                 f"{STABLE}/ratios?symbol={sym}&apikey={KEY}"),
    ("stable/ratios-ttm",             f"{STABLE}/ratios-ttm?symbol={sym}&apikey={KEY}"),
    ("stable/financial-growth",       f"{STABLE}/financial-growth?symbol={sym}&apikey={KEY}"),
    ("stable/analyst-estimates",      f"{STABLE}/analyst-estimates?symbol={sym}&apikey={KEY}"),
    ("stable/earnings-surprises",     f"{STABLE}/earnings-surprises?symbol={sym}&apikey={KEY}"),
    ("stable/profile",                f"{STABLE}/profile?symbol={sym}&apikey={KEY}"),
    ("stable/quote",                  f"{STABLE}/quote?symbol={sym}&apikey={KEY}"),
    ("stable/analyst-recommendations",f"{STABLE}/analyst-stock-recommendations?symbol={sym}&apikey={KEY}"),
    ("stable/price-target",           f"{STABLE}/price-target?symbol={sym}&apikey={KEY}"),
    ("stable/price-target-summary",   f"{STABLE}/price-target-summary?symbol={sym}&apikey={KEY}"),
    ("stable/upgrades-downgrades",    f"{STABLE}/upgrades-downgrades?symbol={sym}&apikey={KEY}"),
    ("stable/earnings-calendar",      f"{STABLE}/earnings?symbol={sym}&apikey={KEY}"),
    ("stable/company-outlook",        f"{STABLE}/company-outlook?symbol={sym}&apikey={KEY}"),
    # Also test v4 stable-ish endpoints that weren't legacy
    ("v4/commitment-of-traders",      f"{V4}/commitment_of_traders_report?apikey={KEY}"),
    ("v4/economic-calendar",          f"{V4}/economic_calendar?apikey={KEY}"),
    # Test if API key is recognized at all
    ("v3/stock-screener",             f"{V3}/stock-screener?marketCapMoreThan=1000000000&limit=5&apikey={KEY}"),
    ("v3/available-traded/list",      f"{V3}/available-traded/list?apikey={KEY}"),
    ("v3/financial-statement-symbol-lists", f"{V3}/financial-statement-symbol-lists?apikey={KEY}"),
]

results = {}
for name, url in stable_endpoints:
    data, status, err = fmp_get(url)
    t = tag(data, status, err)
    results[name] = t
    print(f"  {name:<45} {t}")
    time.sleep(0.2)

# Save results
with open("/tmp/fmp_stable_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== CHECK WHAT PLAN THE KEY IS ON ===\n")
# Try the account info endpoint
for ep in [
    f"https://financialmodelingprep.com/api/v3/is-the-market-open?apikey={KEY}",
    f"https://financialmodelingprep.com/stable/is-market-open?apikey={KEY}",
    f"https://financialmodelingprep.com/api/v4/account?apikey={KEY}",
    f"https://financialmodelingprep.com/stable/stock-list?apikey={KEY}",
    f"https://financialmodelingprep.com/stable/company-search?query=Apple&limit=3&apikey={KEY}",
]:
    data, status, err = fmp_get(ep)
    print(f"  {ep.split('?')[0].split('/')[-1]:<35} [{status}] {tag(data, status, err)[:100]}")
    time.sleep(0.2)

print("\n=== DONE ===")
