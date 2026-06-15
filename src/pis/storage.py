"""Append-only storage for PIS Phase 1 snapshots."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Iterable

from .models import PortfolioSnapshot, PositionSnapshot


SNAPSHOT_HEADERS = [
    "snapshot_id",
    "snapshot_date",
    "account_id",
    "account_name",
    "source_file",
    "source_run_id",
    "source_format",
    "portfolio_value",
    "cash_value",
    "equity_value",
    "holding_count",
    "ingestion_status",
    "created_at_utc",
    "warnings",
]

POSITION_HEADERS = [
    "snapshot_id",
    "snapshot_date",
    "account_id",
    "account_name",
    "symbol",
    "description",
    "quantity",
    "market_value",
    "percent_of_account",
    "source_percent_of_account",
    "cost_basis_total",
    "security_type",
    "operational_state",
    "is_cash_equivalent",
    "source_file",
    "created_at_utc",
]

INDEX_HEADERS = [
    "snapshot_id",
    "snapshot_date",
    "account_id",
    "account_name",
    "source_file",
    "source_run_id",
    "source_format",
    "partition_path",
    "snapshot_path",
    "positions_path",
    "position_count",
    "portfolio_value",
    "cash_value",
    "equity_value",
    "ingestion_status",
    "created_at_utc",
]


@dataclass(frozen=True)
class PortfolioHistoryStoragePaths:
    partition_dir: Path
    snapshot_path: Path
    positions_path: Path
    index_path: Path


def _ensure_file_with_headers(path: Path, headers: list[str]) -> None:
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            existing_headers = next(csv.reader(handle), [])
        if existing_headers and existing_headers != headers:
            raise ValueError(
                f"PIS contract header mismatch for {path}: expected {headers}, observed {existing_headers}."
            )
        if not existing_headers:
            with path.open("w", encoding="utf-8", newline="") as handle:
                csv.DictWriter(handle, fieldnames=headers).writeheader()
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=headers).writeheader()


def _write_csv_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_float(raw: str | object) -> float:
    try:
        return float(str(raw or "").strip() or 0.0)
    except ValueError:
        return 0.0


def _to_int(raw: str | object) -> int:
    try:
        return int(float(str(raw or "").strip() or 0))
    except ValueError:
        return 0


def _sort_index_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (str(row.get("snapshot_date", "")), str(row.get("created_at_utc", ""))),
        reverse=True,
    )


def _resolve_repo_path(path_value: str, repo_root: Path) -> Path:
    p = Path(str(path_value or "").strip())
    if p.is_absolute():
        return p
    return repo_root / p


def pis_snapshot_inventory(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
) -> list[dict[str, object]]:
    """Return account-level snapshot inventory rows, newest first."""
    rows = _sort_index_rows(_read_csv_rows(Path(index_path)))
    inventory: list[dict[str, object]] = []
    for row in rows:
        inventory.append(
            {
                "snapshot_date": str(row.get("snapshot_date", "")),
                "snapshot_id": str(row.get("snapshot_id", "")),
                "account_number": str(row.get("account_id", "")),
                "account_name": str(row.get("account_name", "")),
                "positions": _to_int(row.get("position_count", 0)),
                "market_value": _to_float(row.get("portfolio_value", 0)),
                "cash_value": _to_float(row.get("cash_value", 0)),
                "source_file": str(row.get("source_file", "")),
                "source_run_id": str(row.get("source_run_id", "")),
                "ingestion_timestamp": str(row.get("created_at_utc", "")),
            }
        )
    return inventory


def pis_value_timeline(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
) -> list[dict[str, object]]:
    """Return canonical daily timeline, newest first."""
    from .canonical_daily import pis_canonical_history

    history = pis_canonical_history(index_path=index_path).get("history", [])
    selected = [
        row for row in history if str(row.get("canonical_snapshot_id", "")).strip()
    ]

    timeline: list[dict[str, object]] = []
    for i, row in enumerate(selected):
        snapshot_date = str(row.get("snapshot_date", ""))
        portfolio_value = round(_to_float(row.get("portfolio_value", 0.0)), 2)
        cash_value = round(_to_float(row.get("cash", 0.0)), 2)
        positions = _to_int(row.get("position_count", 0))
        prior_value = _to_float(selected[i + 1].get("portfolio_value", 0.0)) if i + 1 < len(selected) else None
        change = None if prior_value is None else portfolio_value - prior_value
        timeline.append(
            {
                "snapshot_date": snapshot_date,
                "portfolio_value": portfolio_value,
                "cash_value": cash_value,
                "positions": positions,
                "change_vs_prior_snapshot": None if change is None else round(change, 2),
            }
        )
    return timeline


def pis_latest_snapshot_summary(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    repo_root: str | Path = ".",
) -> dict[str, object]:
    """Return latest snapshot totals + top 10 holdings by value."""
    from .canonical_daily import canonical_selected_index_rows

    rows = canonical_selected_index_rows(index_path=index_path)
    if not rows:
        return {
            "snapshot_date": "",
            "total_value": 0.0,
            "cash": 0.0,
            "position_count": 0,
            "largest_holdings": [],
        }

    latest_row = max(rows, key=lambda r: str(r.get("snapshot_date", "")))
    latest_date = str(latest_row.get("snapshot_date", ""))

    total_value = _to_float(latest_row.get("portfolio_value", 0))
    cash = _to_float(latest_row.get("cash_value", 0))
    position_count = _to_int(latest_row.get("position_count", 0))

    symbol_values: dict[str, float] = {}
    root = Path(repo_root)
    positions_path = _resolve_repo_path(str(latest_row.get("positions_path", "")), root)
    for pos in _read_csv_rows(positions_path):
        symbol = str(pos.get("symbol", "")).strip().upper()
        if not symbol or symbol in {"CASH", "PENDING"}:
            continue
        symbol_values[symbol] = symbol_values.get(symbol, 0.0) + _to_float(pos.get("market_value", 0))

    largest_holdings = [
        {"symbol": sym, "market_value": round(val, 2)}
        for sym, val in sorted(symbol_values.items(), key=lambda kv: kv[1], reverse=True)[:10]
    ]

    return {
        "snapshot_date": latest_date,
        "total_value": round(total_value, 2),
        "cash": round(cash, 2),
        "position_count": position_count,
        "largest_holdings": largest_holdings,
    }


def pis_snapshot_history_health(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
) -> dict[str, object]:
    """Return simple history integrity counters for read-only dashboard trust signals."""
    rows = _read_csv_rows(Path(index_path))
    if not rows:
        return {
            "first_snapshot_date": "",
            "latest_snapshot_date": "",
            "snapshot_count": 0,
            "missing_days": 0,
            "duplicate_uploads_prevented": 0,
        }

    snapshot_ids = {str(r.get("snapshot_id", "")).strip() for r in rows if str(r.get("snapshot_id", "")).strip()}
    dates = sorted({str(r.get("snapshot_date", "")).strip() for r in rows if str(r.get("snapshot_date", "")).strip()})
    first_date = dates[0]
    latest_date = dates[-1]

    missing_days = 0
    try:
        start = date.fromisoformat(first_date)
        end = date.fromisoformat(latest_date)
        observed = set(dates)
        d = start
        while d <= end:
            if d.isoformat() not in observed:
                missing_days += 1
            d += timedelta(days=1)
    except ValueError:
        missing_days = 0

    return {
        "first_snapshot_date": first_date,
        "latest_snapshot_date": latest_date,
        "snapshot_count": len(snapshot_ids),
        "missing_days": missing_days,
        # Duplicate suppression events are intentionally not persisted in phase 1.
        "duplicate_uploads_prevented": 0,
    }


def pis_sih_lineage_summary(
    *,
    manifest_path: str | Path = "data/portfolio_ingestion/manifest.json",
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    repo_root: str | Path = ".",
) -> dict[str, object]:
    """Return SIH analysis lineage counters for the PIS read-only dashboard."""
    mpath = Path(manifest_path)
    if not mpath.exists():
        return {
            "total_sih_analyses_captured": 0,
            "latest_par": "",
            "latest_mandate": "",
            "latest_upload_date": "",
        }
    try:
        import json

        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        portfolios = list(manifest.get("portfolios") or [])
    except Exception:
        portfolios = []

    if not portfolios:
        return {
            "total_sih_analyses_captured": 0,
            "latest_par": "",
            "latest_mandate": "",
            "latest_upload_date": "",
        }

    # Filter to portfolios with ISO-format snapshot dates (YYYY-MM-DD) before
    # finding the latest.  Non-date entries (e.g. CONCENTRATED_ALPHA) sort
    # lexicographically after date strings and must be excluded.
    dated_portfolios = [
        p for p in portfolios
        if len(str(p.get("snapshot_date", "")).strip()) == 10
        and str(p.get("snapshot_date", "")).strip()[4:5] == "-"
    ]
    if not dated_portfolios:
        dated_portfolios = portfolios
    latest = max(dated_portfolios, key=lambda r: (str(r.get("snapshot_date", "")), str(r.get("created_at_utc", ""))))
    latest_par = str(latest.get("run_id", ""))
    latest_upload_date = str(latest.get("snapshot_date", ""))

    latest_mandate = ""
    if latest_par:
        run_meta = Path(repo_root) / Path(analysis_runs_root) / latest_par / "run_metadata.json"
        try:
            import json

            meta = json.loads(run_meta.read_text(encoding="utf-8"))
            latest_mandate = str(meta.get("mandate_type", ""))
        except Exception:
            latest_mandate = ""

    return {
        "total_sih_analyses_captured": len(portfolios),
        "latest_par": latest_par,
        "latest_mandate": latest_mandate,
        "latest_upload_date": latest_upload_date,
    }


def pis_dashboard_summary(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    manifest_path: str | Path = "data/portfolio_ingestion/manifest.json",
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    repo_root: str | Path = ".",
) -> dict[str, object]:
    """Return compact rollup for PIS dashboard header and quick status."""
    health = pis_snapshot_history_health(index_path=index_path)
    lineage = pis_sih_lineage_summary(
        manifest_path=manifest_path,
        analysis_runs_root=analysis_runs_root,
        repo_root=repo_root,
    )
    return {
        "health": health,
        "lineage": lineage,
    }


def summarize_portfolio_history(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
) -> dict[str, object]:
    """Return a small admin summary for the PIS beta UI."""

    rows = _read_csv_rows(Path(index_path))
    if not rows:
        return {
            "snapshot_count": 0,
            "latest_snapshot_id": "",
            "latest_snapshot_date": "",
            "account_count": 0,
            "position_count": 0,
            "snapshot_ids": [],
            "recent_rows": [],
        }

    latest_row = max(rows, key=lambda row: (str(row.get("snapshot_date", "")), str(row.get("created_at_utc", ""))))
    latest_snapshot_id = str(latest_row.get("snapshot_id", ""))
    latest_date = str(latest_row.get("snapshot_date", ""))
    latest_rows = [row for row in rows if str(row.get("snapshot_id", "")) == latest_snapshot_id]
    account_count = len({str(row.get("account_id", "")).strip() for row in latest_rows if str(row.get("account_id", "")).strip()})
    position_count = sum(int(row.get("position_count", "0") or 0) for row in latest_rows)

    return {
        "snapshot_count": len(rows),
        "latest_snapshot_id": latest_snapshot_id,
        "latest_snapshot_date": latest_date,
        "account_count": account_count,
        "position_count": position_count,
        "snapshot_ids": sorted({str(row.get("snapshot_id", "")).strip() for row in rows if str(row.get("snapshot_id", "")).strip()}),
        "recent_rows": rows[-5:],
    }


def build_portfolio_history_storage_paths(
    *,
    snapshot_date: str,
    account_id: str,
    snapshot_id: str,
    history_root: str | Path = "data/history/pis",
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
) -> PortfolioHistoryStoragePaths:
    history_root_path = Path(history_root)
    partition_dir = history_root_path / f"snapshot_date={snapshot_date}" / f"account_id={account_id}" / f"snapshot_id={snapshot_id}"
    return PortfolioHistoryStoragePaths(
        partition_dir=partition_dir,
        snapshot_path=partition_dir / "portfolio_snapshot.csv",
        positions_path=partition_dir / "position_snapshots.csv",
        index_path=Path(index_path),
    )


def ensure_portfolio_history_contracts(*, index_path: str | Path = "data/history/pis/pis_snapshot_index.csv") -> None:
    _ensure_file_with_headers(Path(index_path), INDEX_HEADERS)


def _snapshot_to_row(snapshot: PortfolioSnapshot) -> dict[str, object]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "account_id": snapshot.account_id,
        "account_name": snapshot.account_name,
        "source_file": snapshot.source_file,
        "source_run_id": snapshot.source_run_id,
        "source_format": snapshot.source_format,
        "portfolio_value": str(snapshot.portfolio_value),
        "cash_value": str(snapshot.cash_value),
        "equity_value": str(snapshot.equity_value),
        "holding_count": str(snapshot.holding_count),
        "ingestion_status": snapshot.ingestion_status,
        "created_at_utc": snapshot.created_at_utc.isoformat(),
        "warnings": "|".join(snapshot.warnings),
    }


def _position_to_row(position: PositionSnapshot) -> dict[str, object]:
    return {
        "snapshot_id": position.snapshot_id,
        "snapshot_date": position.snapshot_date.isoformat(),
        "account_id": position.account_id,
        "account_name": position.account_name,
        "symbol": position.symbol,
        "description": position.description,
        "quantity": str(position.quantity),
        "market_value": str(position.market_value),
        "percent_of_account": str(position.percent_of_account),
        "source_percent_of_account": "" if position.source_percent_of_account is None else str(position.source_percent_of_account),
        "cost_basis_total": "" if position.cost_basis_total is None else str(position.cost_basis_total),
        "security_type": position.security_type,
        "operational_state": position.operational_state,
        "is_cash_equivalent": str(position.is_cash_equivalent),
        "source_file": position.source_file,
        "created_at_utc": position.created_at_utc.isoformat(),
    }


def append_portfolio_history(
    *,
    snapshot: PortfolioSnapshot,
    positions: list[PositionSnapshot],
    history_root: str | Path = "data/history/pis",
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
) -> int:
    """Persist a single portfolio snapshot partition immutably.

    Returns the number of persisted position rows.
    """

    ensure_portfolio_history_contracts(index_path=index_path)
    storage_paths = build_portfolio_history_storage_paths(
        snapshot_date=snapshot.snapshot_date.isoformat(),
        account_id=snapshot.account_id,
        snapshot_id=snapshot.snapshot_id,
        history_root=history_root,
        index_path=index_path,
    )

    snapshot_row = _snapshot_to_row(snapshot)
    position_rows = [_position_to_row(position) for position in positions]
    if any(position.snapshot_id != snapshot.snapshot_id for position in positions):
        raise ValueError(f"Position rows must belong to snapshot_id={snapshot.snapshot_id}.")

    if storage_paths.partition_dir.exists():
        existing_snapshot_rows = _read_csv_rows(storage_paths.snapshot_path)
        existing_position_rows = _read_csv_rows(storage_paths.positions_path)
        if existing_snapshot_rows == [snapshot_row] and existing_position_rows == position_rows:
            return len(position_rows)
        raise ValueError(
            "Immutable PIS partition protection triggered: partition already exists with different content for "
            f"snapshot_id={snapshot.snapshot_id}."
        )

    existing_index_rows = _read_csv_rows(storage_paths.index_path)
    if any(str(row.get("snapshot_id", "")) == snapshot.snapshot_id for row in existing_index_rows):
        raise ValueError(
            f"PIS index append blocked: snapshot_id {snapshot.snapshot_id} is already registered in the index."
        )

    storage_paths.partition_dir.mkdir(parents=True, exist_ok=False)
    _write_csv_rows(storage_paths.snapshot_path, SNAPSHOT_HEADERS, [snapshot_row])
    _write_csv_rows(storage_paths.positions_path, POSITION_HEADERS, position_rows)

    index_entry = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "account_id": snapshot.account_id,
        "account_name": snapshot.account_name,
        "source_file": snapshot.source_file,
        "source_run_id": snapshot.source_run_id,
        "source_format": snapshot.source_format,
        "partition_path": str(storage_paths.partition_dir),
        "snapshot_path": str(storage_paths.snapshot_path),
        "positions_path": str(storage_paths.positions_path),
        "position_count": str(len(position_rows)),
        "portfolio_value": str(snapshot.portfolio_value),
        "cash_value": str(snapshot.cash_value),
        "equity_value": str(snapshot.equity_value),
        "ingestion_status": snapshot.ingestion_status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with storage_paths.index_path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=INDEX_HEADERS).writerow(index_entry)

    return len(position_rows)
