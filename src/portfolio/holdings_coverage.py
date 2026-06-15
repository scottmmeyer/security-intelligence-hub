from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


_PRIMARY_FIELDS: dict[str, tuple[str, ...]] = {
    "zacks": ("zacks_rank", "zacks_score"),
    "danelfin": ("danelfin_raw", "danelfin_score"),
    "yahoo": ("price_target", "analyst_count", "current_price"),
}


@dataclass(frozen=True)
class ActiveHoldingsBaseline:
    run_id: str
    holdings_path: Path
    holdings: list[dict[str, str]]


def find_latest_holdings_run(analysis_runs_root: Path) -> Path | None:
    candidates: list[tuple[float, Path]] = []
    if not analysis_runs_root.exists():
        return None
    for run_dir in analysis_runs_root.iterdir():
        holdings_path = run_dir / "holdings.csv"
        if run_dir.is_dir() and holdings_path.exists():
            candidates.append((holdings_path.stat().st_mtime, run_dir))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def load_active_holdings_baseline(analysis_runs_root: Path) -> ActiveHoldingsBaseline | None:
    run_dir = find_latest_holdings_run(analysis_runs_root)
    if run_dir is None:
        return None

    holdings_path = run_dir / "holdings.csv"
    with holdings_path.open("r", encoding="utf-8", newline="") as fh:
        all_rows = list(csv.DictReader(fh))

    holdings = [
        dict(row)
        for row in all_rows
        if str(row.get("asset_class", "")).strip().upper() == "EQUITIES"
        and str(row.get("symbol", "")).strip()
    ]
    return ActiveHoldingsBaseline(run_id=run_dir.name, holdings_path=holdings_path, holdings=holdings)


def load_active_holding_symbols(analysis_runs_root: Path) -> set[str]:
    baseline = load_active_holdings_baseline(analysis_runs_root)
    if baseline is None:
        return set()
    return {
        str(row.get("symbol", "")).strip().upper()
        for row in baseline.holdings
        if str(row.get("symbol", "")).strip()
    }


def load_base_universe_symbols(base_universe_csv: Path) -> set[str]:
    if not base_universe_csv.exists():
        return set()
    symbols: set[str] = set()
    with base_universe_csv.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            symbol = str(row.get("symbol", "")).strip().upper()
            if symbol:
                symbols.add(symbol)
    return symbols


def classify_provider_applicability(
    holding_row: dict[str, str],
    *,
    provider: str,
    base_universe_symbols: set[str],
) -> tuple[bool, str]:
    del provider  # current applicability model is common across stock providers

    symbol = str(holding_row.get("symbol", "")).strip().upper()
    if not symbol:
        return False, "missing_symbol"

    if str(holding_row.get("asset_class", "")).strip().upper() != "EQUITIES":
        return False, "non_equity_asset"

    if str(holding_row.get("operational_state", "")).strip().upper() == "ZERO_VALUE_LEGACY_POSITION":
        return False, "zero_value_legacy_position"

    security_type = str(holding_row.get("security_type", "")).strip().upper()
    if security_type == "CONTRA_ENTRY":
        return False, "contra_entry"

    if symbol not in base_universe_symbols:
        return False, "not_in_base_equity_universe"

    return True, "applicable"


def load_provider_applicable_symbols(
    analysis_runs_root: Path,
    base_universe_csv: Path,
    *,
    provider: str,
) -> set[str]:
    baseline = load_active_holdings_baseline(analysis_runs_root)
    if baseline is None:
        return set()

    base_universe_symbols = load_base_universe_symbols(base_universe_csv)
    applicable: set[str] = set()
    for row in baseline.holdings:
        is_applicable, _reason = classify_provider_applicability(
            row,
            provider=provider,
            base_universe_symbols=base_universe_symbols,
        )
        if is_applicable:
            applicable.add(str(row.get("symbol", "")).strip().upper())
    return applicable


def _parse_iso_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def summarize_holdings_coverage(
    *,
    provider: str,
    latest_csv: Path,
    analysis_runs_root: Path,
    base_universe_csv: Path,
    threshold_days: int = 2,
    today: date | None = None,
) -> dict[str, object]:
    today = today or date.today()
    baseline = load_active_holdings_baseline(analysis_runs_root)
    if baseline is None:
        return {
            "run_id": None,
            "active_holdings_baseline": 0,
            "applicable_holdings": 0,
            "covered_today": 0,
            "covered_within_threshold": 0,
            "stale": 0,
            "missing": 0,
            "not_applicable": 0,
            "failed": 0,
            "status": "UNKNOWN",
            "symbols": {},
        }

    primary_fields = _PRIMARY_FIELDS.get(provider, ())
    base_universe_symbols = load_base_universe_symbols(base_universe_csv)

    rows_by_symbol: dict[str, dict[str, str]] = {}
    if latest_csv.exists():
        with latest_csv.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                symbol = str(row.get("symbol", "")).strip().upper()
                if symbol:
                    rows_by_symbol[symbol] = dict(row)

    symbols: dict[str, dict[str, object]] = {}
    applicable_holdings = 0
    covered_today = 0
    covered_within_threshold = 0
    stale = 0
    missing = 0
    not_applicable = 0
    failed = 0

    for row in baseline.holdings:
        symbol = str(row.get("symbol", "")).strip().upper()
        is_applicable, reason = classify_provider_applicability(
            row,
            provider=provider,
            base_universe_symbols=base_universe_symbols,
        )
        info: dict[str, object] = {
            "applicability_reason": reason,
            "applicable": is_applicable,
        }
        latest_row = rows_by_symbol.get(symbol)
        sourced_date = str((latest_row or {}).get("sourced_date", "")).strip()
        info["sourced_date"] = sourced_date

        if not is_applicable:
            not_applicable += 1
            info["classification"] = "NOT_APPLICABLE"
            symbols[symbol] = info
            continue

        applicable_holdings += 1
        if latest_row is None:
            missing += 1
            info["classification"] = "MISSING"
            symbols[symbol] = info
            continue

        has_primary_data = any(str(latest_row.get(field, "")).strip() for field in primary_fields)
        info["has_primary_data"] = has_primary_data
        sourced = _parse_iso_date(sourced_date)
        if sourced is None:
            missing += 1
            info["classification"] = "MISSING"
            symbols[symbol] = info
            continue

        age_days = (today - sourced).days
        info["age_days"] = age_days
        if sourced == today and has_primary_data:
            covered_today += 1
            covered_within_threshold += 1
            info["classification"] = "COVERED_TODAY"
        elif sourced == today and not has_primary_data:
            failed += 1
            info["classification"] = "FAILED"
        elif age_days <= threshold_days and has_primary_data:
            covered_within_threshold += 1
            info["classification"] = "COVERED_WITHIN_THRESHOLD"
        elif has_primary_data:
            stale += 1
            info["classification"] = "STALE"
        else:
            failed += 1
            info["classification"] = "FAILED"
        symbols[symbol] = info

    if missing > 0:
        status = "NON_COMPLIANT"
    elif stale > 0 or failed > 0:
        status = "DEGRADED"
    else:
        status = "COMPLIANT"

    return {
        "run_id": baseline.run_id,
        "active_holdings_baseline": len(baseline.holdings),
        "applicable_holdings": applicable_holdings,
        "covered_today": covered_today,
        "covered_within_threshold": covered_within_threshold,
        "stale": stale,
        "missing": missing,
        "not_applicable": not_applicable,
        "failed": failed,
        "status": status,
        "symbols": symbols,
    }