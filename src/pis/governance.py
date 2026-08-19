"""PIS Stage A snapshot governance classification and persistence."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


GOVERNANCE_HEADERS = [
    "snapshot_id",
    "snapshot_date",
    "governance_status",
    "reasons",
    "scope_valid",
    "value_valid",
    "source_valid",
]


@dataclass(frozen=True)
class SnapshotGovernanceConfig:
    expected_account_scope_tokens: tuple[str, ...] = (
        "General Brokerage",
        "Joint WROS - TOD",
        "Individual - TOD",
    )
    disallowed_account_scope_tokens: tuple[str, ...] = (
        "401(k)",
        "FIS 401(K) PLAN",
        "BrokerageLink",
        "BrokerageLink Roth",
    )
    value_pass_max: float = 600000.0
    value_reject_gt: float = 750000.0
    warning_source_artifact_patterns: tuple[str, ...] = (
        "test.csv",
        "audit_test.csv",
        "upload.csv",
        "certification_run.csv",
        "cert_step3.csv",
    )


DEFAULT_GOVERNANCE_CONFIG = SnapshotGovernanceConfig()


def _to_bool(value: bool) -> str:
    return "true" if value else "false"


def _to_float(raw: str | object) -> float:
    try:
        return float(str(raw or "").strip() or 0.0)
    except ValueError:
        return 0.0


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _contains_any_token(value: str, tokens: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(token.lower() in lowered for token in tokens)


def _contains_all_tokens(value: str, tokens: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return all(token.lower() in lowered for token in tokens)


def evaluate_snapshot_governance(
    snapshot_row: dict[str, str],
    *,
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> dict[str, object]:
    """Classify a snapshot row into PASS, WARNING, or REJECT deterministically."""

    reasons: list[str] = []
    hard_reject = False
    warning_flag = False

    account_name = str(snapshot_row.get("account_name", ""))
    # A snapshot is in-scope when account_name matches any approved account class.
    scope_has_expected = _contains_any_token(account_name, config.expected_account_scope_tokens)
    scope_has_disallowed = _contains_any_token(account_name, config.disallowed_account_scope_tokens)

    scope_valid = scope_has_expected and not scope_has_disallowed
    if scope_has_disallowed:
        reasons.append("SCOPE_DISALLOWED_ACCOUNT_CLASS")
        hard_reject = True
    elif not scope_has_expected:
        reasons.append("SCOPE_EXPECTED_ACCOUNT_PATTERN_MISSING")
        hard_reject = True

    portfolio_value = _to_float(snapshot_row.get("portfolio_value", 0.0))
    value_valid = True
    if portfolio_value > config.value_reject_gt:
        reasons.append("VALUE_EXCEEDS_REJECT_THRESHOLD")
        value_valid = False
        hard_reject = True
    elif portfolio_value > config.value_pass_max:
        reasons.append("VALUE_IN_WARNING_BAND")
        warning_flag = True

    source_file = str(snapshot_row.get("source_file", "")).strip().lower()
    source_is_artifact = source_file in {item.strip().lower() for item in config.warning_source_artifact_patterns}
    source_valid = not source_is_artifact
    if source_is_artifact:
        reasons.append("SOURCE_TEST_OR_BACKFILL_ARTIFACT")
        warning_flag = True

    status = "REJECT" if hard_reject else "WARNING" if warning_flag else "PASS"

    return {
        "status": status,
        "reasons": reasons,
        "scope_valid": scope_valid,
        "value_valid": value_valid,
        "source_valid": source_valid,
    }


def build_snapshot_governance_rows(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> list[dict[str, object]]:
    rows = _read_csv_rows(Path(index_path))

    evaluated_rows: list[dict[str, object]] = []
    for row in rows:
        evaluation = evaluate_snapshot_governance(row, config=config)
        evaluated_rows.append(
            {
                "snapshot_id": str(row.get("snapshot_id", "")),
                "snapshot_date": str(row.get("snapshot_date", "")),
                "governance_status": str(evaluation["status"]),
                "reasons": "|".join(str(item) for item in evaluation["reasons"]),
                "scope_valid": _to_bool(bool(evaluation["scope_valid"])),
                "value_valid": _to_bool(bool(evaluation["value_valid"])),
                "source_valid": _to_bool(bool(evaluation["source_valid"])),
            }
        )

    return sorted(
        evaluated_rows,
        key=lambda item: (str(item.get("snapshot_date", "")), str(item.get("snapshot_id", ""))),
        reverse=True,
    )


def persist_snapshot_governance(
    *,
    governance_rows: list[dict[str, object]],
    output_path: str | Path = "data/history/pis/governance/snapshot_governance.csv",
) -> None:
    _write_csv_rows(Path(output_path), GOVERNANCE_HEADERS, governance_rows)


def refresh_snapshot_governance(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/governance/snapshot_governance.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> list[dict[str, object]]:
    rows = build_snapshot_governance_rows(index_path=index_path, config=config)
    persist_snapshot_governance(governance_rows=rows, output_path=output_path)
    return rows


def _status_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts = {"PASS": 0, "WARNING": 0, "REJECT": 0}
    for row in rows:
        status = str(row.get("governance_status", "")).upper()
        if status in counts:
            counts[status] += 1
    return counts


def pis_governance_latest(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/governance/snapshot_governance.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> dict[str, object]:
    rows = refresh_snapshot_governance(index_path=index_path, output_path=output_path, config=config)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_snapshot_date": rows[0]["snapshot_date"] if rows else "",
        "status_counts": _status_counts(rows),
        "snapshots": rows,
    }


def pis_governance_summary(
    *,
    index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    output_path: str | Path = "data/history/pis/governance/snapshot_governance.csv",
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> dict[str, object]:
    rows = refresh_snapshot_governance(index_path=index_path, output_path=output_path, config=config)
    by_date: dict[str, dict[str, int]] = {}
    for row in rows:
        snapshot_date = str(row.get("snapshot_date", ""))
        if snapshot_date not in by_date:
            by_date[snapshot_date] = {"PASS": 0, "WARNING": 0, "REJECT": 0}
        status = str(row.get("governance_status", "")).upper()
        if status in by_date[snapshot_date]:
            by_date[snapshot_date][status] += 1

    daily = [
        {
            "snapshot_date": snapshot_date,
            "pass_count": counts["PASS"],
            "warning_count": counts["WARNING"],
            "reject_count": counts["REJECT"],
        }
        for snapshot_date, counts in sorted(by_date.items(), key=lambda item: item[0], reverse=True)
    ]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_snapshots": len(rows),
        "status_counts": _status_counts(rows),
        "daily": daily,
    }
