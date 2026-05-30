import csv
from pathlib import Path

ROOT = Path("scripts/compare_zacks_ess_vs_internet.py").resolve().parent.parent
ESS_FILE = ROOT / "incoming/ess/starmine/ESS_2026May14.csv"
ZACKS_FILE = ROOT / "data/signals/zacks/latest_zacks.csv"

ess_by_symbol = {}
with open(ESS_FILE, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames or []
    zacks_col = next((h for h in headers if "zacks" in h.lower() or "analyst" in h.lower()), None)
    symbol_col = next((h for h in headers if h.strip().lower() in ("symbol", "ticker")), None)
    print(f"ESS file: {ESS_FILE.name}")
    print()
    if symbol_col and zacks_col:
        for row in reader:
            sym = (row.get(symbol_col) or "").strip()
            val = (row.get(zacks_col) or "").strip()
            if sym:
                                                                                    ol)}")
