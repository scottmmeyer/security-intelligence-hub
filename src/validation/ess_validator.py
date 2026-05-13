"""Deterministic ESS intake validation contracts."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ALLOWED_ESS_TEXT_CATEGORIES = {
    "VERY_BEARISH",
    "BEARISH",
    "NEUTRAL",
    "BULLISH",
    "VERY_BULLISH",
}

UNIVERSE_REQUIRED_COLUMNS = {
    "starmine": ("snapshot_date", "symbol", "provider", "source_file", "starmine_ess_text"),
    "non_starmine_zacks": ("snapshot_date", "symbol", "provider", "source_file", "analyst_rating"),
}


class EssValidationError(ValueError):
    """Raised when ESS input file fails deterministic validation."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("ESS validation failed: " + "; ".join(errors))


@dataclass(frozen=True)
class EssValidationResult:
    """Deterministic ESS validation result payload."""

    rows: List[Dict[str, str]]
    errors: List[str]


def _load_csv(file_path: str | Path) -> tuple[List[str], List[Dict[str, str]]]:
    csv_path = Path(file_path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = [dict(row) for row in reader]
    return headers, rows


def validate_ess_rows(
    *,
    rows: List[Dict[str, str]],
    headers: List[str],
    universe: str,
    allowed_coverage_domains: List[str],
    allowed_source_types: List[str],
) -> List[str]:
    """Validate ESS rows against deterministic schema and lineage rules."""

    errors: List[str] = []
    if universe not in UNIVERSE_REQUIRED_COLUMNS:
        return [f"Invalid intake universe {universe!r}."]

    required_columns = set(UNIVERSE_REQUIRED_COLUMNS[universe])
    missing_columns = sorted(required_columns.difference(headers))
    if missing_columns:
        errors.append(f"Required column validation failed: missing columns {', '.join(missing_columns)}")

    if not rows:
        errors.append("Empty file detection: ESS file has no data rows.")
        return errors

    seen_symbols: set[str] = set()
    for row_index, row in enumerate(rows, start=2):
        symbol_raw = (row.get("symbol") or "").strip()
        symbol = symbol_raw.upper()
        if not symbol:
            errors.append(f"Malformed row detection at row {row_index}: symbol is empty.")
        elif symbol in seen_symbols:
            errors.append(f"Duplicate symbol detection at row {row_index}: duplicate symbol {symbol}.")
        else:
            seen_symbols.add(symbol)

        snapshot_date_raw = (row.get("snapshot_date") or "").strip()
        if not snapshot_date_raw:
            errors.append(f"Snapshot metadata validation at row {row_index}: snapshot_date is empty.")
        else:
            try:
                date.fromisoformat(snapshot_date_raw)
            except ValueError:
                errors.append(
                    f"Snapshot metadata validation at row {row_index}: invalid snapshot_date {snapshot_date_raw!r}."
                )

        provider = (row.get("provider") or "").strip()
        source_file = (row.get("source_file") or "").strip()
        if not provider or not source_file:
            errors.append(
                f"Source lineage validation at row {row_index}: provider and source_file are required."
            )

        ess_text = (row.get("starmine_ess_text") or "").strip()
        if ess_text and ess_text.upper() not in ALLOWED_ESS_TEXT_CATEGORIES:
            errors.append(
                f"Invalid ESS text category detection at row {row_index}: {ess_text!r} is not allowed."
            )

        coverage_domain = (row.get("coverage_domain") or "").strip()
        if coverage_domain and coverage_domain not in allowed_coverage_domains:
            errors.append(
                f"Invalid coverage-domain detection at row {row_index}: {coverage_domain!r} is not allowed."
            )

        source_type = (row.get("starmine_ess_source_type") or "").strip()
        if source_type and source_type not in allowed_source_types:
            errors.append(
                f"Source lineage validation at row {row_index}: source type {source_type!r} is invalid."
            )

        if universe == "starmine" and not ess_text:
            errors.append(
                f"Malformed row detection at row {row_index}: starmine_ess_text is required for starmine universe."
            )

    return errors


def validate_ess_file(
    *,
    file_path: str | Path,
    universe: str,
    allowed_coverage_domains: List[str],
    allowed_source_types: List[str],
) -> EssValidationResult:
    """Validate a concrete ESS file and return rows plus explicit errors."""

    headers, rows = _load_csv(file_path)
    errors = validate_ess_rows(
        rows=rows,
        headers=headers,
        universe=universe,
        allowed_coverage_domains=allowed_coverage_domains,
        allowed_source_types=allowed_source_types,
    )
    return EssValidationResult(rows=rows, errors=errors)


def assert_valid_ess_file(
    *,
    file_path: str | Path,
    universe: str,
    allowed_coverage_domains: List[str],
    allowed_source_types: List[str],
) -> List[Dict[str, str]]:
    """Fail-closed ESS file validation helper returning validated rows."""

    result = validate_ess_file(
        file_path=file_path,
        universe=universe,
        allowed_coverage_domains=allowed_coverage_domains,
        allowed_source_types=allowed_source_types,
    )
    if result.errors:
        raise EssValidationError(result.errors)
    return result.rows
