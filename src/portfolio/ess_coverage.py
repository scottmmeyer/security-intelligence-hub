from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from src.models.provider_health_models import EssCoverageGapDetail, EssCoverageGapWarning
from src.portfolio.fidelity_signal import FidelitySignal, load_fidelity_signals
from src.portfolio.holdings_coverage import (
    classify_provider_applicability,
    load_base_universe_symbols,
)


def load_latest_equity_holdings(analysis_runs_root: Path) -> dict[str, dict[str, str]]:
    """Return current equity holdings from the most recent date-stamped PAR run."""
    if not analysis_runs_root.exists():
        return {}
    date_pars = sorted(
        [d for d in analysis_runs_root.iterdir() if d.name.startswith("PAR-2")],
        key=lambda p: p.name,
        reverse=True,
    )
    if not date_pars:
        return {}
    holdings_path = date_pars[0] / "holdings.csv"
    if not holdings_path.exists():
        return {}

    holdings: dict[str, dict[str, str]] = {}
    with holdings_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = (row.get("symbol") or "").strip().upper()
            asset = (row.get("asset_class") or "").strip().upper()
            if sym and asset == "EQUITIES":
                holdings[sym] = dict(row)
    return holdings


def _load_signal_rows_by_symbol(signal_snapshot_path: Path) -> dict[str, list[dict[str, Any]]]:
    rows_by_symbol: dict[str, list[dict[str, Any]]] = {}
    with signal_snapshot_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol") or "").strip().upper()
            if not sym:
                continue
            rows_by_symbol.setdefault(sym, []).append(dict(row))
    return rows_by_symbol


def _has_fresh_starmine(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        domain = str(row.get("coverage_domain") or "").strip().upper()
        ess_text = str(row.get("starmine_ess_text") or "").strip().upper()
        if domain == "STARMINE_COVERED" and ess_text:
            return True
    return False


def _load_latest_historical_signals(history_root: Path) -> dict[str, FidelitySignal]:
    latest_by_symbol: dict[str, FidelitySignal] = {}
    if not history_root.exists():
        return latest_by_symbol

    snapshot_files = sorted(history_root.glob("snapshot_date=*/run_id=*/signal_snapshots.csv"))
    for snapshot_file in snapshot_files:
        if not snapshot_file.exists():
            continue
        for signal in load_fidelity_signals(snapshot_file).values():
            existing = latest_by_symbol.get(signal.symbol)
            if existing is None or signal.refresh_date > existing.refresh_date:
                latest_by_symbol[signal.symbol] = signal
    return latest_by_symbol


def build_ess_coverage_gap_warning(
    *,
    snapshot_date: date,
    signal_snapshot_path: Path,
    analysis_runs_root: Path,
    base_universe_csv: Path | None = None,
    prior_signals: dict[str, FidelitySignal] | None = None,
) -> EssCoverageGapWarning | None:
    """Classify held-position ESS coverage gaps against merged effective signal state."""
    holdings = load_latest_equity_holdings(analysis_runs_root)
    if not holdings or not signal_snapshot_path.exists():
        return None

    if base_universe_csv is None:
        base_universe_csv = Path("data/current/base_equity_universe.csv")
    base_universe_symbols = load_base_universe_symbols(base_universe_csv)

    prior_ess = load_fidelity_signals(signal_snapshot_path)
    data_root = analysis_runs_root.parents[1] if len(analysis_runs_root.parents) >= 2 else analysis_runs_root
    historical_ess = _load_latest_historical_signals(data_root / "history" / "signals")
    rows_by_symbol = _load_signal_rows_by_symbol(signal_snapshot_path)
    concern_rows: list[tuple[float, EssCoverageGapDetail]] = []
    true_missing_symbols: list[str] = []
    stale_symbols: list[str] = []
    no_fresh_symbols: list[str] = []

    for sym, holding in holdings.items():
        is_applicable, _reason = classify_provider_applicability(
            holding,
            provider="zacks",
            base_universe_symbols=base_universe_symbols,
        )
        if not is_applicable:
            continue

        symbol_rows = rows_by_symbol.get(sym, [])
        previous = prior_ess.get(sym) or historical_ess.get(sym) or (prior_signals or {}).get(sym)

        if not symbol_rows:
            if previous is not None:
                gap_type = "STALE_ESS"
                stale_symbols.append(sym)
            else:
                gap_type = "TRUE_MISSING"
                true_missing_symbols.append(sym)
        else:
            last_ess_date = str(previous.refresh_date) if previous else ""
            if previous and last_ess_date and last_ess_date < snapshot_date.isoformat():
                gap_type = "STALE_ESS"
                stale_symbols.append(sym)
            elif not _has_fresh_starmine(symbol_rows):
                gap_type = "NO_FRESH_STARMINE"
                no_fresh_symbols.append(sym)
            else:
                continue

        company_name = (
            (holding.get("description") or "").strip()
            or (holding.get("company_name") or "").strip()
            or sym
        )
        try:
            pct = float(holding.get("percent_of_portfolio") or 0.0)
        except (TypeError, ValueError):
            pct = 0.0

        days_stale = 0
        if previous and previous.refresh_date:
            try:
                days_stale = max((snapshot_date - date.fromisoformat(previous.refresh_date)).days, 0)
            except ValueError:
                days_stale = 0

        concern_rows.append(
            (
                -pct,
                EssCoverageGapDetail(
                    symbol=sym,
                    company_name=company_name,
                    last_ess_date=str(previous.refresh_date) if previous else "",
                    current_ess_posture=str(previous.ess_text) if previous else "UNKNOWN",
                    days_stale=days_stale,
                    gap_type=gap_type,
                ),
            )
        )

    if not concern_rows:
        return None

    ordered = [detail for _, detail in sorted(concern_rows, key=lambda item: (item[0], item[1].symbol))]
    return EssCoverageGapWarning(
        snapshot_date=snapshot_date.isoformat(),
        warning_count=len(ordered),
        example_symbols=tuple(detail.symbol for detail in ordered[:3]),
        gaps=tuple(ordered),
        true_missing_count=len(true_missing_symbols),
        stale_coverage_count=len(stale_symbols),
        no_fresh_starmine_count=len(no_fresh_symbols),
        true_missing_symbols=tuple(sorted(true_missing_symbols)),
        stale_coverage_symbols=tuple(sorted(stale_symbols)),
        no_fresh_starmine_symbols=tuple(sorted(no_fresh_symbols)),
    )


def write_ess_coverage_warning(
    *,
    output_path: Path,
    snapshot_date: date,
    warning: EssCoverageGapWarning | None,
) -> None:
    """Persist the latest ESS coverage-gap state as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if warning is None:
        payload: dict[str, object] = {
            "warning_code": "ESS_COVERAGE_GAP",
            "status": "OK",
            "snapshot_date": snapshot_date.isoformat(),
            "warning_count": 0,
            "true_missing_count": 0,
            "stale_coverage_count": 0,
            "no_fresh_starmine_count": 0,
            "example_symbols": [],
            "true_missing_symbols": [],
            "stale_coverage_symbols": [],
            "no_fresh_starmine_symbols": [],
            "gaps": [],
            "summary_message": (
                "ESS Coverage Warning — 0 holdings require ESS attention "
                "(missing=0, stale=0, no_fresh_starmine=0)."
            ),
        }
    else:
        payload = asdict(warning)
        payload["summary_message"] = warning.summary_message
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_ess_coverage_warning(output_path: Path) -> dict[str, object]:
    """Load the ESS coverage-gap artifact when present."""
    if not output_path.exists():
        return {
            "warning_code": "ESS_COVERAGE_GAP",
            "status": "UNKNOWN",
            "snapshot_date": "",
            "warning_count": 0,
            "example_symbols": [],
            "gaps": [],
            "summary_message": "",
        }
    try:
        return json.loads(output_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "warning_code": "ESS_COVERAGE_GAP",
            "status": "ERROR",
            "snapshot_date": "",
            "warning_count": 0,
            "example_symbols": [],
            "gaps": [],
            "summary_message": "",
        }