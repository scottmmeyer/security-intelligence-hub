from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from src.models.provider_health_models import (
    EssCoverageGapDetail,
    EssCoverageGapWarning,
    GAP_TYPE_NO_COVERAGE_AVAILABLE,
    GAP_TYPE_NO_FRESH_STARMINE,
    GAP_TYPE_NO_SCORE_AVAILABLE,
    GAP_TYPE_ORDER,
    GAP_TYPE_STALE_ESS,
    GAP_TYPE_TRUE_MISSING,
)
from src.portfolio.fidelity_signal import FidelitySignal, load_fidelity_signals
from src.portfolio.holdings_coverage import load_base_universe_symbols


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


def build_ess_coverage_gap_warning(
    *,
    incoming_ess_symbols: set[str] | None = None,
    incoming_rows: list[dict[str, object]] | None = None,
    snapshot_date: date,
    signal_snapshot_path: Path,
    analysis_runs_root: Path,
    base_universe_csv: Path | None = None,
    prior_signals: dict[str, FidelitySignal] | None = None,
) -> EssCoverageGapWarning | None:
    """Classify held-position ESS coverage gaps while preserving subtype diagnostics."""
    holdings = load_latest_equity_holdings(analysis_runs_root)
    if not holdings or not signal_snapshot_path.exists():
        return None

    if base_universe_csv is None:
        base_universe_csv = Path("data/current/base_equity_universe.csv")
    base_universe_symbols = load_base_universe_symbols(base_universe_csv)

    if incoming_rows is None:
        incoming_rows = []
        if signal_snapshot_path.exists():
            with signal_snapshot_path.open("r", encoding="utf-8", newline="") as fh:
                incoming_rows = [dict(row) for row in csv.DictReader(fh)]
    rows_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in incoming_rows:
        sym = str(row.get("symbol") or "").strip().upper()
        if sym:
            rows_by_symbol.setdefault(sym, []).append(dict(row))

    if incoming_ess_symbols is None:
        incoming_ess_symbols = set()
        if signal_snapshot_path.exists():
            with signal_snapshot_path.open("r", encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    row_snapshot_date = str(row.get("snapshot_date") or "").strip()
                    sym = str(row.get("symbol") or "").strip().upper()
                    domain = str(row.get("coverage_domain") or "").strip().upper()
                    ess_text = str(row.get("starmine_ess_text") or "").strip().upper()
                    if (
                        row_snapshot_date == snapshot_date.isoformat()
                        and sym
                        and domain == "STARMINE_COVERED"
                        and ess_text
                    ):
                        incoming_ess_symbols.add(sym)

    prior_ess = load_fidelity_signals(signal_snapshot_path)
    gap_rows: list[tuple[float, EssCoverageGapDetail]] = []
    by_gap_type: dict[str, list[str]] = {k: [] for k in GAP_TYPE_ORDER}

    def _status_tokens(row: dict[str, Any]) -> set[str]:
        fields = (
            "status",
            "coverage_status",
            "signal_coverage_status",
            "provider_status",
            "fetch_status",
            "error_code",
            "reason",
        )
        tokens: set[str] = set()
        for field in fields:
            val = str(row.get(field) or "").strip().upper()
            if val:
                tokens.add(val)
        return tokens

    for sym, holding in holdings.items():
        previous = prior_ess.get(sym) or (prior_signals or {}).get(sym)
        security_type = str(holding.get("security_type") or "").strip().upper()
        if security_type in {"ETF", "MUTUAL FUND", "CONTRA_ENTRY"}:
            continue
        # Preserve compatibility: when security_type is missing, do not hard-exclude
        # by base-universe membership for stale previously-covered names (legacy
        # holdings snapshots often omit that column).
        if security_type and base_universe_symbols and sym not in base_universe_symbols:
            continue
        if (not security_type) and base_universe_symbols and sym not in base_universe_symbols and previous is None:
            continue

        if sym in incoming_ess_symbols:
            continue

        symbol_rows = rows_by_symbol.get(sym, [])
        gap_type = ""
        reason = ""

        tokens = set()
        for row in symbol_rows:
            tokens |= _status_tokens(row)

        domain_values = {str(row.get("coverage_domain") or "").strip().upper() for row in symbol_rows}
        has_non_starmine = "NON_STARMINE_ANALYST" in domain_values
        has_rows = bool(symbol_rows)

        if "NO_SCORE_AVAILABLE" in tokens:
            gap_type = GAP_TYPE_NO_SCORE_AVAILABLE
            reason = "Holding has provider row but no score available in latest incoming ESS view."
        elif "NO_COVERAGE_AVAILABLE" in tokens:
            gap_type = GAP_TYPE_NO_COVERAGE_AVAILABLE
            reason = "Holding has provider row but no coverage available in latest incoming ESS view."
        elif has_non_starmine:
            gap_type = GAP_TYPE_NO_FRESH_STARMINE
            reason = "Holding is marked NON_STARMINE_ANALYST in latest incoming ESS view."
        elif previous is None and not has_rows:
            gap_type = GAP_TYPE_TRUE_MISSING
            reason = "Holding is ESS-applicable but was never covered and is absent from latest incoming ESS file."
        elif previous is not None:
            last_date = str(previous.refresh_date or "").strip()
            if last_date and last_date < snapshot_date.isoformat():
                gap_type = GAP_TYPE_STALE_ESS
                reason = "Holding had prior ESS coverage but latest incoming ESS file is missing a fresh covered row."
            else:
                gap_type = GAP_TYPE_TRUE_MISSING
                reason = "Holding had prior ESS coverage but is absent from latest incoming ESS file."
        else:
            gap_type = GAP_TYPE_NO_FRESH_STARMINE
            reason = "Holding has incoming provider rows but no fresh StarMine ESS coverage."

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

        by_gap_type[gap_type].append(sym)

        gap_rows.append(
            (
                -pct,
                EssCoverageGapDetail(
                    symbol=sym,
                    company_name=company_name,
                    last_ess_date=str(previous.refresh_date) if previous else "",
                    current_ess_posture=str(previous.ess_text) if previous else "UNKNOWN",
                    days_stale=days_stale,
                    gap_type=gap_type,
                    reason=reason,
                ),
            )
        )

    if not gap_rows:
        return None

    ordered = [detail for _, detail in sorted(gap_rows, key=lambda item: (item[0], item[1].symbol))]
    return EssCoverageGapWarning(
        snapshot_date=snapshot_date.isoformat(),
        warning_count=len(ordered),
        example_symbols=tuple(detail.symbol for detail in ordered[:3]),
        gaps=tuple(ordered),
        true_missing_count=len(by_gap_type[GAP_TYPE_TRUE_MISSING]),
        stale_coverage_count=len(by_gap_type[GAP_TYPE_STALE_ESS]),
        no_fresh_starmine_count=len(by_gap_type[GAP_TYPE_NO_FRESH_STARMINE]),
        no_score_available_count=len(by_gap_type[GAP_TYPE_NO_SCORE_AVAILABLE]),
        no_coverage_available_count=len(by_gap_type[GAP_TYPE_NO_COVERAGE_AVAILABLE]),
        true_missing_symbols=tuple(sorted(by_gap_type[GAP_TYPE_TRUE_MISSING])),
        stale_coverage_symbols=tuple(sorted(by_gap_type[GAP_TYPE_STALE_ESS])),
        no_fresh_starmine_symbols=tuple(sorted(by_gap_type[GAP_TYPE_NO_FRESH_STARMINE])),
        no_score_available_symbols=tuple(sorted(by_gap_type[GAP_TYPE_NO_SCORE_AVAILABLE])),
        no_coverage_available_symbols=tuple(sorted(by_gap_type[GAP_TYPE_NO_COVERAGE_AVAILABLE])),
        counts_by_gap_type={k: len(v) for k, v in by_gap_type.items()},
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
            "no_score_available_count": 0,
            "no_coverage_available_count": 0,
            "example_symbols": [],
            "true_missing_symbols": [],
            "stale_coverage_symbols": [],
            "no_fresh_starmine_symbols": [],
            "no_score_available_symbols": [],
            "no_coverage_available_symbols": [],
            "counts_by_gap_type": {
                GAP_TYPE_TRUE_MISSING: 0,
                GAP_TYPE_STALE_ESS: 0,
                GAP_TYPE_NO_FRESH_STARMINE: 0,
                GAP_TYPE_NO_SCORE_AVAILABLE: 0,
                GAP_TYPE_NO_COVERAGE_AVAILABLE: 0,
            },
            "gaps": [],
            "summary_message": "ESS Coverage Warning — 0 holdings absent from latest ESS file.",
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