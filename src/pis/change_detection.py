"""PIS portfolio change detection between consecutive snapshot dates."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .canonical_daily import canonical_selected_index_rows
from .storage import _read_csv_rows, _to_float, _to_int


CHANGE_HEADERS = [
    "change_id",
    "snapshot_id",
    "prior_snapshot_id",
    "snapshot_date",
    "prior_snapshot_date",
    "change_type",
    "symbol",
    "old_quantity",
    "new_quantity",
    "old_market_value",
    "new_market_value",
    "delta_quantity",
    "delta_market_value",
    "created_at",
]

SUMMARY_HEADERS = [
    "snapshot_id",
    "prior_snapshot_id",
    "snapshot_date",
    "prior_snapshot_date",
    "portfolio_value_change",
    "cash_change",
    "position_count_change",
    "new_holdings_count",
    "exited_holdings_count",
    "increased_holdings_count",
    "reduced_holdings_count",
    "unchanged_holdings_count",
    "created_at",
]


@dataclass(frozen=True)
class _DateSnapshotGroup:
    snapshot_date: str
    snapshot_ids: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def _write_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _aggregate_positions(rows: list[dict[str, str]], repo_root: Path) -> tuple[dict[str, dict[str, float]], float, int]:
    symbols: dict[str, dict[str, float]] = {}
    cash_total = 0.0
    position_count = 0
    for row in rows:
        positions_path = Path(str(row.get("positions_path", "")).strip())
        if not positions_path.is_absolute():
            positions_path = repo_root / positions_path
        for pos in _read_csv_rows(positions_path):
            symbol = str(pos.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            qty = _to_float(pos.get("quantity", 0))
            mv = _to_float(pos.get("market_value", 0))
            if str(pos.get("is_cash_equivalent", "")).strip().lower() in {"1", "true", "yes"}:
                cash_total += mv
            symbols.setdefault(symbol, {"quantity": 0.0, "market_value": 0.0})
            symbols[symbol]["quantity"] += qty
            symbols[symbol]["market_value"] += mv
            position_count += 1
    return symbols, round(cash_total, 2), position_count


def _snapshot_groups(index_path: Path) -> list[_DateSnapshotGroup]:
    rows = canonical_selected_index_rows(index_path=index_path)

    groups: list[_DateSnapshotGroup] = []
    for row in sorted(rows, key=lambda r: str(r.get("snapshot_date", ""))):
        snapshot_date = str(row.get("snapshot_date", "")).strip()
        snapshot_id = str(row.get("snapshot_id", "")).strip()
        if not snapshot_date or not snapshot_id:
            continue
        groups.append(
            _DateSnapshotGroup(
                snapshot_date=snapshot_date,
                snapshot_ids=(snapshot_id,),
                rows=(row,),
            )
        )
    return groups


def _snapshot_key(ids: tuple[str, ...], snapshot_date: str) -> str:
    if not ids:
        return f"PIS-DATE-{snapshot_date}"
    return "|".join(ids)


def compute_all_snapshot_changes(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    changes_root: str | Path = "data/history/pis/changes",
    repo_root: str | Path = ".",
) -> dict[str, object]:
    """Compute and persist change records for all consecutive snapshot dates."""
    groups = _snapshot_groups(Path(index_path))
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if len(groups) < 2:
        _write_rows(Path(changes_root) / "change_records.csv", CHANGE_HEADERS, [])
        _write_rows(Path(changes_root) / "change_summary.csv", SUMMARY_HEADERS, [])
        return {"change_records": [], "change_summary": []}

    all_changes: list[dict[str, object]] = []
    all_summaries: list[dict[str, object]] = []

    root = Path(repo_root)
    integrity_warnings: list[str] = []
    for idx in range(1, len(groups)):
        prior = groups[idx - 1]
        current = groups[idx]

        prior_symbols, prior_cash, prior_positions = _aggregate_positions(list(prior.rows), root)
        current_symbols, current_cash, current_positions = _aggregate_positions(list(current.rows), root)

        # R1 integrity check: if the index says a snapshot has positions but none
        # were loaded from disk, the partition file is missing or corrupt.  Emitting
        # a warning and skipping this pair prevents silently classifying every prior
        # symbol as EXITED_POSITION.
        for group, loaded_count in ((prior, prior_positions), (current, current_positions)):
            for index_row in group.rows:
                expected = _to_int(index_row.get("position_count", 0))
                if expected > 0 and loaded_count == 0:
                    sid = str(index_row.get("snapshot_id", group.snapshot_date))
                    integrity_warnings.append(
                        f"INTEGRITY_WARNING: snapshot {sid} ({group.snapshot_date}) "
                        f"expected {expected} positions but 0 were loaded from disk. "
                        "Skipping this snapshot pair to prevent silent change-detection corruption."
                    )

        if integrity_warnings and any(
            str(index_row.get("snapshot_id", "")) in w
            for group in (prior, current)
            for index_row in group.rows
            for w in integrity_warnings
        ):
            # Skip pairs that involve a corrupt snapshot; record zero-change summary
            current_snapshot_id = _snapshot_key(current.snapshot_ids, current.snapshot_date)
            prior_snapshot_id = _snapshot_key(prior.snapshot_ids, prior.snapshot_date)
            all_summaries.append(
                {
                    "snapshot_id": current_snapshot_id,
                    "prior_snapshot_id": prior_snapshot_id,
                    "snapshot_date": current.snapshot_date,
                    "prior_snapshot_date": prior.snapshot_date,
                    "portfolio_value_change": 0.0,
                    "cash_change": 0.0,
                    "position_count_change": 0,
                    "new_holdings_count": 0,
                    "exited_holdings_count": 0,
                    "increased_holdings_count": 0,
                    "reduced_holdings_count": 0,
                    "unchanged_holdings_count": 0,
                    "created_at": created_at,
                }
            )
            continue

        all_symbols = sorted(set(prior_symbols.keys()) | set(current_symbols.keys()))
        current_snapshot_id = _snapshot_key(current.snapshot_ids, current.snapshot_date)
        prior_snapshot_id = _snapshot_key(prior.snapshot_ids, prior.snapshot_date)

        new_count = 0
        exited_count = 0
        increased_count = 0
        reduced_count = 0
        unchanged_count = 0

        for symbol in all_symbols:
            old = prior_symbols.get(symbol, {"quantity": 0.0, "market_value": 0.0})
            new = current_symbols.get(symbol, {"quantity": 0.0, "market_value": 0.0})

            old_exists = symbol in prior_symbols
            new_exists = symbol in current_symbols
            delta_q = round(new["quantity"] - old["quantity"], 8)
            delta_mv = round(new["market_value"] - old["market_value"], 2)

            if new_exists and not old_exists:
                change_type = "NEW_POSITION"
                new_count += 1
            elif old_exists and not new_exists:
                change_type = "EXITED_POSITION"
                exited_count += 1
            else:
                if delta_q > 0:
                    change_type = "INCREASED"
                    increased_count += 1
                elif delta_q < 0:
                    change_type = "REDUCED"
                    reduced_count += 1
                else:
                    change_type = "UNCHANGED"
                    unchanged_count += 1

            change_id = f"CHG-{current.snapshot_date}-{prior.snapshot_date}-{symbol}"
            all_changes.append(
                {
                    "change_id": change_id,
                    "snapshot_id": current_snapshot_id,
                    "prior_snapshot_id": prior_snapshot_id,
                    "snapshot_date": current.snapshot_date,
                    "prior_snapshot_date": prior.snapshot_date,
                    "change_type": change_type,
                    "symbol": symbol,
                    "old_quantity": round(old["quantity"], 8),
                    "new_quantity": round(new["quantity"], 8),
                    "old_market_value": round(old["market_value"], 2),
                    "new_market_value": round(new["market_value"], 2),
                    "delta_quantity": delta_q,
                    "delta_market_value": delta_mv,
                    "created_at": created_at,
                }
            )

        prior_value = sum(_to_float(r.get("portfolio_value", 0)) for r in prior.rows)
        current_value = sum(_to_float(r.get("portfolio_value", 0)) for r in current.rows)

        all_summaries.append(
            {
                "snapshot_id": current_snapshot_id,
                "prior_snapshot_id": prior_snapshot_id,
                "snapshot_date": current.snapshot_date,
                "prior_snapshot_date": prior.snapshot_date,
                "portfolio_value_change": round(current_value - prior_value, 2),
                "cash_change": round(current_cash - prior_cash, 2),
                "position_count_change": int(current_positions - prior_positions),
                "new_holdings_count": new_count,
                "exited_holdings_count": exited_count,
                "increased_holdings_count": increased_count,
                "reduced_holdings_count": reduced_count,
                "unchanged_holdings_count": unchanged_count,
                "created_at": created_at,
            }
        )

    _write_rows(Path(changes_root) / "change_records.csv", CHANGE_HEADERS, all_changes)
    _write_rows(Path(changes_root) / "change_summary.csv", SUMMARY_HEADERS, all_summaries)

    result: dict[str, object] = {"change_records": all_changes, "change_summary": all_summaries}
    if integrity_warnings:
        result["integrity_warnings"] = integrity_warnings
    return result


def _load_change_tables(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    changes_root: str | Path = "data/history/pis/changes",
    repo_root: str | Path = ".",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    summary_path = Path(changes_root) / "change_summary.csv"
    changes_path = Path(changes_root) / "change_records.csv"
    compute_all_snapshot_changes(index_path=index_path, changes_root=changes_root, repo_root=repo_root)
    summary_rows = _read_csv_rows(summary_path)
    change_rows = _read_csv_rows(changes_path)
    summary_rows.sort(key=lambda r: str(r.get("snapshot_date", "")), reverse=True)
    return summary_rows, change_rows


def pis_change_summary(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    changes_root: str | Path = "data/history/pis/changes",
    repo_root: str | Path = ".",
) -> dict[str, object]:
    summary_rows, _ = _load_change_tables(index_path=index_path, changes_root=changes_root, repo_root=repo_root)
    out: list[dict[str, object]] = []
    for row in summary_rows:
        out.append(
            {
                "snapshot_id": str(row.get("snapshot_id", "")),
                "prior_snapshot_id": str(row.get("prior_snapshot_id", "")),
                "snapshot_date": str(row.get("snapshot_date", "")),
                "prior_snapshot_date": str(row.get("prior_snapshot_date", "")),
                "portfolio_value_change": _to_float(row.get("portfolio_value_change", 0)),
                "cash_change": _to_float(row.get("cash_change", 0)),
                "position_count_change": _to_int(row.get("position_count_change", 0)),
                "new_holdings_count": _to_int(row.get("new_holdings_count", 0)),
                "exited_holdings_count": _to_int(row.get("exited_holdings_count", 0)),
                "increased_holdings_count": _to_int(row.get("increased_holdings_count", 0)),
                "reduced_holdings_count": _to_int(row.get("reduced_holdings_count", 0)),
                "unchanged_holdings_count": _to_int(row.get("unchanged_holdings_count", 0)),
                "created_at": str(row.get("created_at", "")),
            }
        )
    return {"summary": out}


def pis_changes_for_snapshot(
    snapshot_id: str,
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    changes_root: str | Path = "data/history/pis/changes",
    repo_root: str | Path = ".",
) -> dict[str, object]:
    summary_rows, change_rows = _load_change_tables(index_path=index_path, changes_root=changes_root, repo_root=repo_root)
    target = next((r for r in summary_rows if str(r.get("snapshot_id", "")) == snapshot_id), None)
    if target is None:
        return {
            "summary": None,
            "new_positions": [],
            "exited_positions": [],
            "increased_positions": [],
            "reduced_positions": [],
            "unchanged_positions": [],
        }

    detail = [r for r in change_rows if str(r.get("snapshot_id", "")) == snapshot_id]

    def _map_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
        return [
            {
                "change_id": str(r.get("change_id", "")),
                "symbol": str(r.get("symbol", "")),
                "change_type": str(r.get("change_type", "")),
                "old_quantity": _to_float(r.get("old_quantity", 0)),
                "new_quantity": _to_float(r.get("new_quantity", 0)),
                "old_market_value": _to_float(r.get("old_market_value", 0)),
                "new_market_value": _to_float(r.get("new_market_value", 0)),
                "delta_quantity": _to_float(r.get("delta_quantity", 0)),
                "delta_market_value": _to_float(r.get("delta_market_value", 0)),
            }
            for r in rows
        ]

    mapped_summary = {
        "snapshot_id": str(target.get("snapshot_id", "")),
        "prior_snapshot_id": str(target.get("prior_snapshot_id", "")),
        "snapshot_date": str(target.get("snapshot_date", "")),
        "prior_snapshot_date": str(target.get("prior_snapshot_date", "")),
        "portfolio_value_change": _to_float(target.get("portfolio_value_change", 0)),
        "cash_change": _to_float(target.get("cash_change", 0)),
        "position_count_change": _to_int(target.get("position_count_change", 0)),
        "new_holdings_count": _to_int(target.get("new_holdings_count", 0)),
        "exited_holdings_count": _to_int(target.get("exited_holdings_count", 0)),
        "increased_holdings_count": _to_int(target.get("increased_holdings_count", 0)),
        "reduced_holdings_count": _to_int(target.get("reduced_holdings_count", 0)),
        "unchanged_holdings_count": _to_int(target.get("unchanged_holdings_count", 0)),
        "created_at": str(target.get("created_at", "")),
    }

    return {
        "summary": mapped_summary,
        "new_positions": _map_rows([r for r in detail if str(r.get("change_type", "")) == "NEW_POSITION"]),
        "exited_positions": _map_rows([r for r in detail if str(r.get("change_type", "")) == "EXITED_POSITION"]),
        "increased_positions": _map_rows([r for r in detail if str(r.get("change_type", "")) == "INCREASED"]),
        "reduced_positions": _map_rows([r for r in detail if str(r.get("change_type", "")) == "REDUCED"]),
        "unchanged_positions": _map_rows([r for r in detail if str(r.get("change_type", "")) == "UNCHANGED"]),
    }


def pis_changes_latest(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    changes_root: str | Path = "data/history/pis/changes",
    repo_root: str | Path = ".",
) -> dict[str, object]:
    summaries = pis_change_summary(index_path=index_path, changes_root=changes_root, repo_root=repo_root).get("summary", [])
    if not summaries:
        return {
            "summary": None,
            "new_positions": [],
            "exited_positions": [],
            "increased_positions": [],
            "reduced_positions": [],
            "unchanged_positions": [],
        }
    latest_snapshot_id = str(summaries[0].get("snapshot_id", ""))
    return pis_changes_for_snapshot(
        latest_snapshot_id,
        index_path=index_path,
        changes_root=changes_root,
        repo_root=repo_root,
    )
