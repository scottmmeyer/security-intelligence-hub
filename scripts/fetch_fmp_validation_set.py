"""Fetch FMP data for validation symbols and write to latest cache."""
import sys, time
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

from src.scoring.fetch_fmp_signals import (
    fetch_key_metrics_ttm, fetch_grades_consensus,
    fetch_earnings_surprises, fetch_income_growth,
    _get_api_key, _write_csv, _FMP_LATEST_DIR,
    KEY_METRICS_HEADERS, GRADES_CONSENSUS_HEADERS,
    EARNINGS_SURPRISES_HEADERS, INCOME_GROWTH_HEADERS,
)

SYMS = ["VRT","DELL","ARW","PSX","CAH","SNX","TSM","ASML","CVE","TSLA","AVGO","VXUS"]
today = date.today().isoformat()
api_key = _get_api_key()
print("API key loaded:", bool(api_key))

km_rows, gr_rows, es_rows, ig_rows = [], [], [], []

for sym in SYMS:
    print(f"Fetching {sym}...", end=" ", flush=True)
    km = fetch_key_metrics_ttm(sym, api_key, today)
    km["sourced_date"] = today
    km_rows.append(km)

    gr = fetch_grades_consensus(sym, api_key, today)
    gr["sourced_date"] = today
    gr_rows.append(gr)

    es = fetch_earnings_surprises(sym, api_key, today)
    es["sourced_date"] = today
    es_rows.append(es)

    ig = fetch_income_growth(sym, api_key, today)
    ig["sourced_date"] = today
    ig_rows.append(ig)

    print(f"pe={km.get('pe_ratio_ttm','')} ev={km.get('ev_ebitda_ttm','')} roe={km.get('roe_ttm','')} beat_rate={es.get('beat_rate_8q','')} rev_gr={ig.get('revenue_growth_q1_yoy','')} consensus={gr.get('consensus_label','')}")
    time.sleep(0.35)

_FMP_LATEST_DIR.mkdir(parents=True, exist_ok=True)
_write_csv(_FMP_LATEST_DIR / "latest_fmp_key_metrics.csv",          km_rows,  KEY_METRICS_HEADERS)
_write_csv(_FMP_LATEST_DIR / "latest_fmp_grades_consensus.csv",     gr_rows,  GRADES_CONSENSUS_HEADERS)
_write_csv(_FMP_LATEST_DIR / "latest_fmp_earnings_surprises.csv",   es_rows,  EARNINGS_SURPRISES_HEADERS)
_write_csv(_FMP_LATEST_DIR / "latest_fmp_income_growth.csv",        ig_rows,  INCOME_GROWTH_HEADERS)

print("\nDone.", _FMP_LATEST_DIR)
