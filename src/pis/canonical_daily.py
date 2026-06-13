"""PIS Stage B canonical daily snapshot selection."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .governance import DEFAULT_GOVERNANCE_CONFIG, SnapshotGovernanceConfig, evaluate_snapshot_governance
from .storage import _read_csv_rows, _to_float, _to_int


CANONICAL_HEADERS = [
    "snapshot_date",
    "canonical_snapshot_id",
    "governance_status",
    "selection_policy",
    "selection_reason",
    "source_file",
    "portfolio_value",
    "cash",
    "position_count",
]


_GOVERNANCE_RANK = {"PASS": 2, "WARNING": 1, "REJECT": 0}


@dataclass(frozen=True)
class _Candidate:
    row: dict[str, str]
    governance_status: str
    created_at_utc: str


def _parse_datetime(raw: str) -> datetime:
    value = str(raw or "").strip()
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _write_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _selection_rank(candidate: _Candidate) -> tuple[datetime, int, str]:
    return (
        _parse_datetime(candidate.created_at_utc),
        _GOVERNANCE_RANK.get(candidate.governance_status, 0),
        str(candidate.row.get("snapshot_id", "")),
    )


def _as_output_row(
    *,
    snapshot_date: str,
    candidate: _Candidate,
    selection_policy: str,
    selection_reason: str,
) -> dict[str, object]:
    row = candidate.row
    return {
        "snapshot_date": snapshot_date,
        "canonical_snapshot_id": str(row.get("snapshot_id", "")),
        "governance_status": candidate.governance_status,
        "selection_policy": selection_policy,
        "selection_reason": selection_reason,
        "source_file": str(row.get("source_file", "")),
        "portfolio_value": round(_to_float(row.get("portfolio_value", 0.0)), 2),
        "cash": round(_to_float(row.get("cash_value", 0.0)), 2),
        "position_count": _to_int(row.get("position_count", 0)),
    }


def select_canonical_daily_rows(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> list[dict[str, object]]:
    rows = _read_csv_rows(Path(index_path))
    by_date: dict[str, list[_Candidate]] = {}

    for row in rows:
        snapshot_date = str(row.get("snapshot_date", "")).strip()
        if not snapshot_date:
            continue
        governance = evaluate_snapshot_governance(row, config=config)
        status = str(governance.get("status", "REJECT")).upper()
        by_date.setdefault(snapshot_date, []).append(
            _Candidate(
                row=row,
                governance_status=status,
                created_at_utc=str(row.get("created_at_utc", "")),
            )
        )

    out: list[dict[str, object]] = []
    for snapshot_date in sorted(by_date.keys(), reverse=True):
        candidates = by_date[snapshot_date]
        pass_candidates = [c for c in candidates if c.governance_status == "PASS"]
        warning_candidates = [c for c in candidates if c.governance_status == "WARNING"]

        if pass_candidates:
            selected = max(pass_candidates, key=_selection_rank)
            out.append(
                _as_output_row(
                    snapshot_date=snapshot_date,
                    candidate=selected,
                    selection_policy="PASS_THEN_LATEST_INGESTION",
                    selection_reason="Selected latest-ingested PASS candidate.",
                )
            )
            continue

        if warning_candidates:
            selected = max(warning_candidates, key=_selection_rank)
            out.append(
                _as_output_row(
                    snapshot_date=snapshot_date,
                    candidate=selected,
                    selection_policy="WARNING_FALLBACK_THEN_LATEST_INGESTION",
                    selection_reason="No PASS candidate available; selected latest WARNING candidate.",
                )
            )
            continue

        out.append(
            {
                "snapshot_date": snapshot_date,
                "canonical_snapshot_id": "",
                "governance_status": "REJECT",
                "selection_policy": "NO_ELIGIBLE_CANDIDATE",
                "selection_reason": "All candidates for this date were REJECT.",
                "source_file": "",
                "portfolio_value": 0.0,
                "cash": 0.0,
                "position_count": 0,
            }
        )

    return out


def persist_canonical_daily_rows(
    *,
    rows: list[dict[str, object]],
    output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
) -> None:
    _write_rows(Path(output_path), CANONICAL_HEADERS, rows)


def refresh_canonical_daily(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> list[dict[str, object]]:
    rows = select_canonical_daily_rows(index_path=index_path, config=config)
    persist_canonical_daily_rows(rows=rows, output_path=output_path)
    return rows


def canonical_selected_index_rows(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> list[dict[str, str]]:
    canonical_rows = refresh_canonical_daily(index_path=index_path, output_path=output_path, config=config)
    selected_ids = {
        str(row.get("canonical_snapshot_id", "")).strip()
        for row in canonical_rows
        if str(row.get("canonical_snapshot_id", "")).strip()
    }
    index_rows = _read_csv_rows(Path(index_path))
    selected = [row for row in index_rows if str(row.get("snapshot_id", "")).strip() in selected_ids]
    selected.sort(key=lambda row: str(row.get("snapshot_date", "")), reverse=True)
    return selected


def pis_canonical_history(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> dict[str, object]:
    rows = refresh_canonical_daily(index_path=index_path, output_path=output_path, config=config)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "history": rows,
    }


def pis_canonical_latest(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> dict[str, object]:
    rows = refresh_canonical_daily(index_path=index_path, output_path=output_path, config=config)
    latest = rows[0] if rows else {
        "snapshot_date": "",
        "canonical_snapshot_id": "",
        "governance_status": "",
        "selection_policy": "",
        "selection_reason": "",
        "source_file": "",
        "portfolio_value": 0.0,
        "cash": 0.0,
        "position_count": 0,
    }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest": latest,
    }


def pis_canonical_summary(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> dict[str, object]:
    rows = refresh_canonical_daily(index_path=index_path, output_path=output_path, config=config)
    selected = [row for row in rows if str(row.get("canonical_snapshot_id", "")).strip()]
    selected_status_counts = {"PASS": 0, "WARNING": 0, "REJECT": 0}
    for row in selected:
        status = str(row.get("governance_status", "")).upper()
        if status in selected_status_counts:
            selected_status_counts[status] += 1

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_dates": len(rows),
        "selected_dates": len(selected),
        "unselected_dates": len(rows) - len(selected),
        "selected_status_counts": selected_status_counts,
    }
