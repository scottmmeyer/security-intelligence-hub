import json, time, urllib.request, urllib.error
from pathlib import Path

key = ""
for line in Path(".env").read_text().splitlines():
    if "FMP_API_KEY=" in line:
        key = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

BASE = "https://financialmodelingprep.com/stable"
SYMBOLS = ["VRT", "DELL", "ARW", "AVGO", "PSX", "TSM", "ASML", "CVE", "TSLA", "VXUS"]

def fmp_get(endpoint):
    sep = "&" if "?" in endpoint else "?"
    url = f"{BASE}/{endpoint}{sep}apikey={key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SIH-DQ/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status, None
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except: body = None
        return body, e.code, f"HTTP {e.code}"
    except Exception as e:
        return None, 0, str(e)

results = {}
for sym in SYMBOLS:
    print(f"  {sym}...", end="", flush=True)
    sd = {}
    for ep_name, endpoint in [
        ("key_metrics_ttm", f"key-metrics-ttm?symbol={sym}"),
        ("grades_consensus", f"grades-consensus?symbol={sym}"),
        ("earnings",         f"earnings?symbol={sym}&limit=8"),
        ("income_growth",    f"income-statement-growth?symbol={sym}&limit=4"),
    ]:
        d, s, e = fmp_get(endpoint)
        sd[ep_name] = {"status": s, "error": e, "data": d}
        time.sleep(0.28)
    results[sym] = sd
    print(" " + " ".join(f"{ep[:2]}={sd[ep]['status']}" for ep in sd))

with open("data/analysis/fmp_dq_validation.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("Saved data/analysis/fmp_dq_validation.json")
