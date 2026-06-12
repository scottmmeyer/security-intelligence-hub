from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from src.models.provider_health_models import EssCoverageGapDetail, EssCoverageGapWarning
from src.portfolio.fidelity_signal import load_fidelity_signals


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
    incoming_ess_symbols: set[str],
    snapshot_date: date,
    signal_snapshot_path: Path,
    analysis_runs_root: Path,
) -> EssCoverageGapWarning | None:
    """Detect held positions that lost ESS coverage between snapshots."""
    holdings = load_latest_equity_holdings(analysis_runs_root)
    if not holdings or not signal_snapshot_path.exists():
        return None

    prior_ess = load_fidelity_signals(signal_snapshot_path)
    gap_rows: list[tuple[float, EssCoverageGapDetail]] = []

    for sym, holding in holdings.items():
        if sym in incoming_ess_symbols:
            continue
        previous = prior_ess.get(sym)
        if previous is None:
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
        if previous.refresh_date:
            try:
                days_stale = max((snapshot_date - date.fromisoformat(previous.refresh_date)).days, 0)
            except ValueError:
                days_stale = 0

        gap_rows.append(
            (
                -pct,
                EssCoverageGapDetail(
                    symbol=sym,
                    company_name=company_name,
                    last_ess_date=previous.refresh_date,
                    current_ess_posture=previous.ess_text,
                    days_stale=days_stale,
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
            "example_symbols": [],
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