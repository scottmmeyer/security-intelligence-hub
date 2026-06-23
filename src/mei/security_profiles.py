"""MEI-003 — Security Event Sensitivity Profiles.

Maintains a curated registry of per-security event sensitivities, with
sector/industry-based defaults for unregistered symbols.

Reads curated overrides from data/mei/security_sensitivities.json.
Sector defaults are derived from the symbol's industry classification as
stored in the latest PAR holdings.csv artifact.

This module is STRICTLY READ-ONLY — no recommendation, scoring, or
governance artifact is ever modified.

Sensitivity levels: HIGH | MODERATE | LOW | NONE

Sensitivity categories
----------------------
  INTEREST_RATE        — Fed policy, rate decisions
  INFLATION            — CPI, PPI, PCE releases
  CONSUMER_SPENDING    — Retail sales, consumer sentiment
  ENERGY               — Oil prices, energy supply/demand
  CREDIT               — Treasury auctions, credit spreads
  HOUSING              — Housing starts, home sales
  TECHNOLOGY_CAPEX     — AI/data center investment cycles
  INTERNATIONAL_TRADE  — Tariffs, trade policy, export controls
  REGULATORY           — FDA, antitrust, financial regulation
  LABOR                — NFP, jobless claims, wage data

Public API
----------
  mei_security_profile(symbol, repo_root)    → dict
  mei_security_profiles_bulk(symbols, repo_root) → dict {symbol: profile}
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

_SENSITIVITIES_FILENAME = "data/mei/security_sensitivities.json"

ALL_TAGS: list[str] = [
    "INTEREST_RATE",
    "INFLATION",
    "CONSUMER_SPENDING",
    "ENERGY",
    "CREDIT",
    "HOUSING",
    "TECHNOLOGY_CAPEX",
    "INTERNATIONAL_TRADE",
    "REGULATORY",
    "LABOR",
]

_LEVEL_ORDER = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "NONE": 3}

# ─── Sector/industry defaults ─────────────────────────────────────────────────
# Keyed on the `industry` field from holdings.csv (upper-cased).
# ETFs / ALL / broad funds use the "_ALL" key.

_SECTOR_DEFAULTS: dict[str, dict[str, str]] = {
    "TECHNOLOGY": {
        "INTEREST_RATE": "HIGH",
        "TECHNOLOGY_CAPEX": "HIGH",
        "INFLATION": "MODERATE",
        "INTERNATIONAL_TRADE": "MODERATE",
        "REGULATORY": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "ENERGY": "NONE",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "LOW",
    },
    "SEMICONDUCTORS": {
        "INTEREST_RATE": "HIGH",
        "TECHNOLOGY_CAPEX": "HIGH",
        "INTERNATIONAL_TRADE": "HIGH",
        "INFLATION": "MODERATE",
        "REGULATORY": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "ENERGY": "NONE",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "LOW",
    },
    "HEALTHCARE": {
        "REGULATORY": "HIGH",
        "CONSUMER_SPENDING": "MODERATE",
        "LABOR": "MODERATE",
        "INFLATION": "MODERATE",
        "INTEREST_RATE": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
        "ENERGY": "NONE",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "INTERNATIONAL_TRADE": "LOW",
    },
    "ENERGY": {
        "ENERGY": "HIGH",
        "INFLATION": "HIGH",
        "INTERNATIONAL_TRADE": "HIGH",
        "CONSUMER_SPENDING": "MODERATE",
        "REGULATORY": "MODERATE",
        "INTEREST_RATE": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "LOW",
    },
    "FINANCIAL SERVICES": {
        "INTEREST_RATE": "HIGH",
        "CREDIT": "HIGH",
        "INFLATION": "MODERATE",
        "REGULATORY": "MODERATE",
        "HOUSING": "MODERATE",
        "CONSUMER_SPENDING": "MODERATE",
        "TECHNOLOGY_CAPEX": "LOW",
        "ENERGY": "NONE",
        "INTERNATIONAL_TRADE": "LOW",
        "LABOR": "LOW",
    },
    "BANKS - REGIONAL": {
        "INTEREST_RATE": "HIGH",
        "CREDIT": "HIGH",
        "HOUSING": "HIGH",
        "INFLATION": "MODERATE",
        "REGULATORY": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "TECHNOLOGY_CAPEX": "NONE",
        "ENERGY": "NONE",
        "INTERNATIONAL_TRADE": "NONE",
        "LABOR": "LOW",
    },
    "INDUSTRIALS": {
        "TECHNOLOGY_CAPEX": "MODERATE",
        "CONSUMER_SPENDING": "MODERATE",
        "INTEREST_RATE": "MODERATE",
        "INTERNATIONAL_TRADE": "MODERATE",
        "INFLATION": "MODERATE",
        "ENERGY": "MODERATE",
        "LABOR": "MODERATE",
        "REGULATORY": "LOW",
        "CREDIT": "LOW",
        "HOUSING": "LOW",
    },
    "CONSUMER CYCLICAL": {
        "CONSUMER_SPENDING": "HIGH",
        "INTEREST_RATE": "HIGH",
        "INFLATION": "HIGH",
        "LABOR": "HIGH",
        "ENERGY": "MODERATE",
        "CREDIT": "MODERATE",
        "HOUSING": "MODERATE",
        "INTERNATIONAL_TRADE": "MODERATE",
        "REGULATORY": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
    },
    "BASIC MATERIALS": {
        "INFLATION": "HIGH",
        "INTERNATIONAL_TRADE": "HIGH",
        "ENERGY": "MODERATE",
        "INTEREST_RATE": "MODERATE",
        "REGULATORY": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
        "CREDIT": "LOW",
        "HOUSING": "LOW",
        "LABOR": "LOW",
    },
    "COMMUNICATION SERVICES": {
        "REGULATORY": "MODERATE",
        "CONSUMER_SPENDING": "MODERATE",
        "INTEREST_RATE": "MODERATE",
        "TECHNOLOGY_CAPEX": "LOW",
        "INFLATION": "LOW",
        "ENERGY": "NONE",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "INTERNATIONAL_TRADE": "LOW",
        "LABOR": "LOW",
    },
    "OIL & GAS MIDSTREAM": {
        "ENERGY": "HIGH",
        "INFLATION": "MODERATE",
        "INTEREST_RATE": "MODERATE",
        "CREDIT": "MODERATE",
        "INTERNATIONAL_TRADE": "MODERATE",
        "REGULATORY": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
        "HOUSING": "NONE",
        "LABOR": "LOW",
    },
    "AEROSPACE & DEFENSE": {
        "REGULATORY": "HIGH",
        "INTERNATIONAL_TRADE": "HIGH",
        "TECHNOLOGY_CAPEX": "MODERATE",
        "INTEREST_RATE": "MODERATE",
        "INFLATION": "MODERATE",
        "LABOR": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "ENERGY": "LOW",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
    },
    "CONSUMER ELECTRONICS": {
        "CONSUMER_SPENDING": "HIGH",
        "INTEREST_RATE": "MODERATE",
        "INTERNATIONAL_TRADE": "HIGH",
        "TECHNOLOGY_CAPEX": "MODERATE",
        "INFLATION": "MODERATE",
        "REGULATORY": "LOW",
        "ENERGY": "LOW",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "MODERATE",
    },
    "CYBERSECURITY": {
        "REGULATORY": "HIGH",
        "TECHNOLOGY_CAPEX": "HIGH",
        "INTEREST_RATE": "HIGH",
        "INFLATION": "MODERATE",
        "INTERNATIONAL_TRADE": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "ENERGY": "NONE",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "LOW",
    },
    # Broad/ETF defaults
    "ALL": {
        "INTEREST_RATE": "MODERATE",
        "INFLATION": "MODERATE",
        "CONSUMER_SPENDING": "MODERATE",
        "ENERGY": "LOW",
        "CREDIT": "MODERATE",
        "HOUSING": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
        "INTERNATIONAL_TRADE": "MODERATE",
        "REGULATORY": "LOW",
        "LABOR": "MODERATE",
    },
    "BITCOIN": {
        "REGULATORY": "HIGH",
        "INTEREST_RATE": "MODERATE",
        "INFLATION": "MODERATE",
        "INTERNATIONAL_TRADE": "MODERATE",
        "CONSUMER_SPENDING": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
        "ENERGY": "LOW",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "NONE",
    },
    "ETHEREUM": {
        "REGULATORY": "HIGH",
        "INTEREST_RATE": "MODERATE",
        "INFLATION": "LOW",
        "INTERNATIONAL_TRADE": "LOW",
        "CONSUMER_SPENDING": "LOW",
        "TECHNOLOGY_CAPEX": "LOW",
        "ENERGY": "LOW",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "NONE",
    },
    "XRP": {
        "REGULATORY": "HIGH",
        "INTEREST_RATE": "LOW",
        "INFLATION": "NONE",
        "INTERNATIONAL_TRADE": "MODERATE",
        "CONSUMER_SPENDING": "NONE",
        "TECHNOLOGY_CAPEX": "NONE",
        "ENERGY": "NONE",
        "CREDIT": "LOW",
        "HOUSING": "NONE",
        "LABOR": "NONE",
    },
    "MONEY MARKET": {
        "INTEREST_RATE": "LOW",
        "CREDIT": "LOW",
        "INFLATION": "LOW",
        "CONSUMER_SPENDING": "NONE",
        "ENERGY": "NONE",
        "HOUSING": "NONE",
        "TECHNOLOGY_CAPEX": "NONE",
        "INTERNATIONAL_TRADE": "NONE",
        "REGULATORY": "NONE",
        "LABOR": "NONE",
    },
}

_FIXED_INCOME_DEFAULT: dict[str, str] = {
    "INTEREST_RATE": "HIGH",
    "CREDIT": "HIGH",
    "INFLATION": "HIGH",
    "CONSUMER_SPENDING": "LOW",
    "ENERGY": "NONE",
    "HOUSING": "MODERATE",
    "TECHNOLOGY_CAPEX": "NONE",
    "INTERNATIONAL_TRADE": "LOW",
    "REGULATORY": "LOW",
    "LABOR": "LOW",
}

_UNKNOWN_DEFAULT: dict[str, str] = {tag: "LOW" for tag in ALL_TAGS}


# ─── I/O helpers ─────────────────────────────────────────────────────────────


def _repo(repo_root: Optional[Path]) -> Path:
    return Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_curated(repo_root: Optional[Path] = None) -> dict[str, dict]:
    """Load per-symbol curated sensitivity overrides from JSON."""
    path = _repo(repo_root) / _SENSITIVITIES_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _latest_par_run(repo_root: Path) -> Optional[Path]:
    """Return the most recently created PAR analysis run directory, or None."""
    runs_root = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not runs_root.exists():
        return None
    dirs = [d for d in runs_root.iterdir() if d.is_dir() and (d / "run_metadata.json").exists()]
    if not dirs:
        return None
    # Sort by created_at_utc from metadata (fall back to dir name)
    def _ts(d: Path) -> str:
        try:
            meta = json.loads((d / "run_metadata.json").read_text(encoding="utf-8"))
            return str(meta.get("created_at_utc", ""))
        except Exception:
            return d.name
    return max(dirs, key=_ts)


def _load_holdings_index(repo_root: Path) -> dict[str, dict]:
    """Return {symbol: {industry, asset_class, market_cap_bucket}} from latest PAR."""
    run = _latest_par_run(repo_root)
    if run is None:
        return {}
    path = run / "holdings.csv"
    if not path.exists():
        return {}
    index: dict[str, dict] = {}
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sym = str(row.get("symbol", "")).strip().upper()
                if sym:
                    index[sym] = {
                        "industry": str(row.get("industry", "")).strip().upper(),
                        "asset_class": str(row.get("asset_class", "")).strip().upper(),
                        "market_cap_bucket": str(row.get("market_cap_bucket", "")).strip().upper(),
                    }
    except Exception:
        pass
    return index


# ─── Default derivation ───────────────────────────────────────────────────────


def _sector_defaults(industry: str, asset_class: str) -> dict[str, str]:
    """Return sensitivity defaults for an industry/asset_class combination."""
    if asset_class in {"FIXED_INCOME"}:
        return dict(_FIXED_INCOME_DEFAULT)

    if asset_class in {"CASH"}:
        return dict(_SECTOR_DEFAULTS.get("MONEY MARKET", _UNKNOWN_DEFAULT))

    if asset_class in {"DIGITAL"}:
        return dict(_SECTOR_DEFAULTS.get(industry, _SECTOR_DEFAULTS.get("BITCOIN", _UNKNOWN_DEFAULT)))

    return dict(_SECTOR_DEFAULTS.get(industry, _SECTOR_DEFAULTS.get("ALL", _UNKNOWN_DEFAULT)))


def _top_sensitivities(sensitivities: dict[str, str]) -> list[str]:
    """Return tags classified HIGH or MODERATE, sorted by level."""
    candidates = [(tag, level) for tag, level in sensitivities.items() if level in {"HIGH", "MODERATE"}]
    candidates.sort(key=lambda x: _LEVEL_ORDER.get(x[1], 9))
    return [tag for tag, _ in candidates]


def _build_observations(symbol: str, sensitivities: dict[str, str], source: str) -> list[str]:
    high = [t for t, l in sensitivities.items() if l == "HIGH"]
    mod = [t for t, l in sensitivities.items() if l == "MODERATE"]
    obs: list[str] = []
    if source == "CURATED":
        obs.append(f"{symbol} has a curated sensitivity profile with analyst-verified inputs.")
    else:
        obs.append(f"{symbol} sensitivity profile is derived from sector/industry classification defaults.")
    if high:
        obs.append(f"HIGH sensitivity to: {', '.join(high)}.")
    if mod:
        obs.append(f"MODERATE sensitivity to: {', '.join(mod)}.")
    if not high and not mod:
        obs.append("No HIGH or MODERATE event sensitivities identified.")
    return obs


# ─── Public API ───────────────────────────────────────────────────────────────


def mei_security_profile(
    symbol: str,
    repo_root: Optional[Path] = None,
) -> dict:
    """Return event sensitivity profile for a single symbol.

    Response shape
    --------------
    {
      "symbol": str,
      "industry": str,
      "asset_class": str,
      "market_cap_bucket": str,
      "sensitivity_source": "CURATED" | "SECTOR_DEFAULT",
      "sensitivities": {tag: level, ...},
      "top_sensitivities": [tag, ...],
      "observations": [str, ...]
    }
    """
    root = _repo(repo_root)
    symbol = symbol.strip().upper()

    curated = _load_curated(root)
    holdings_index = _load_holdings_index(root)

    meta = holdings_index.get(symbol, {})
    industry = meta.get("industry", "UNKNOWN")
    asset_class = meta.get("asset_class", "EQUITIES")
    market_cap_bucket = meta.get("market_cap_bucket", "UNKNOWN")

    if symbol in curated:
        source = "CURATED"
        base = _sector_defaults(industry, asset_class)
        # Curated overrides win over sector defaults
        sensitivities = {**base, **curated[symbol]}
    else:
        source = "SECTOR_DEFAULT"
        sensitivities = _sector_defaults(industry, asset_class)

    # Ensure all tags present
    for tag in ALL_TAGS:
        sensitivities.setdefault(tag, "NONE")

    return {
        "symbol": symbol,
        "industry": industry,
        "asset_class": asset_class,
        "market_cap_bucket": market_cap_bucket,
        "sensitivity_source": source,
        "sensitivities": sensitivities,
        "top_sensitivities": _top_sensitivities(sensitivities),
        "observations": _build_observations(symbol, sensitivities, source),
    }


def mei_security_profiles_bulk(
    symbols: list[str],
    repo_root: Optional[Path] = None,
) -> dict:
    """Return sensitivity profiles for multiple symbols.

    Response shape: {"profiles": {symbol: profile_dict}}
    """
    root = _repo(repo_root)
    curated = _load_curated(root)
    holdings_index = _load_holdings_index(root)

    profiles: dict[str, dict] = {}
    for sym in symbols:
        sym = sym.strip().upper()
        if not sym:
            continue
        meta = holdings_index.get(sym, {})
        industry = meta.get("industry", "UNKNOWN")
        asset_class = meta.get("asset_class", "EQUITIES")
        market_cap_bucket = meta.get("market_cap_bucket", "UNKNOWN")

        if sym in curated:
            source = "CURATED"
            base = _sector_defaults(industry, asset_class)
            sens = {**base, **curated[sym]}
        else:
            source = "SECTOR_DEFAULT"
            sens = _sector_defaults(industry, asset_class)

        for tag in ALL_TAGS:
            sens.setdefault(tag, "NONE")

        profiles[sym] = {
            "symbol": sym,
            "industry": industry,
            "asset_class": asset_class,
            "market_cap_bucket": market_cap_bucket,
            "sensitivity_source": source,
            "sensitivities": sens,
            "top_sensitivities": _top_sensitivities(sens),
        }

    return {"profiles": profiles, "total": len(profiles)}
