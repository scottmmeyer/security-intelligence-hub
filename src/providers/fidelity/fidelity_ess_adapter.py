"""Fidelity provider-native ESS adapter."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Any, Dict, List

from src.providers.fidelity.fidelity_column_mapping import FIDELITY_TO_CANONICAL_COLUMN_MAPPING
from src.providers.fidelity.fidelity_schema_contract import (
    FIDELITY_SCHEMA_VERSION,
    FidelitySchemaEvaluation,
    evaluate_fidelity_schema,
)


@dataclass(frozen=True)
class FidelityAdapterResult:
    """Adapter output preserving provider-native lineage and mapping context."""

    universe: str
    file_path: str
    headers: tuple[str, ...]
    schema_evaluation: FidelitySchemaEvaluation
    raw_rows_discovered: int
    duplicate_symbol_rows: int
    dropped_non_data_rows: int
    adapted_rows: List[Dict[str, Any]]
    unmapped_columns: tuple[str, ...]
    column_lineage: Dict[str, str]


_TICKER_PATTERN = re.compile(r"[A-Z0-9./-]+")


def _load_provider_csv(file_path: str | Path) -> tuple[List[str], List[Dict[str, str]]]:
    csv_path = Path(file_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = [dict(row) for row in reader]
    return headers, rows


def adapt_fidelity_ess_file(
    *,
    file_path: str | Path,
    universe: str,
    snapshot_date: date,
    provider: str = "FIDELITY",
) -> FidelityAdapterResult:
    """Adapt a Fidelity provider-native ESS export into canonical-ready rows."""

    headers, raw_rows = _load_provider_csv(file_path=file_path)
    schema_evaluation = evaluate_fidelity_schema(headers=headers, universe=universe)
    header_set = set(schema_evaluation.headers)

    unmapped_columns = tuple(
        sorted(column for column in schema_evaluation.headers if column not in FIDELITY_TO_CANONICAL_COLUMN_MAPPING)
    )
    column_lineage = {
        canonical_target: provider_column
        for provider_column, canonical_target in FIDELITY_TO_CANONICAL_COLUMN_MAPPING.items()
        if provider_column in header_set
    }

    adapted_rows: List[Dict[str, Any]] = []
    raw_rows_discovered = len(raw_rows)
    duplicate_symbol_rows = 0
    dropped_non_data_rows = 0
    seen_symbols: set[str] = set()
    source_file = Path(file_path).name
    for row_index, row in enumerate(raw_rows, start=2):
        provider_symbol = (row.get("Symbol") or "").strip().upper()
        # Fidelity exports can include explanatory footer lines that are not security rows.
        if not _TICKER_PATTERN.fullmatch(provider_symbol):
            dropped_non_data_rows += 1
            continue
        if provider_symbol in seen_symbols:
            duplicate_symbol_rows += 1
            continue
        seen_symbols.add(provider_symbol)

        canonical_row: Dict[str, Any] = {
            "snapshot_date": snapshot_date.isoformat(),
            "provider": provider,
            "source_file": source_file,
            "provider_native_universe": universe,
            "provider_schema_version": FIDELITY_SCHEMA_VERSION,
            "provider_row_number": row_index,
            "provider_column_lineage": dict(column_lineage),
            "unmapped_provider_columns": list(unmapped_columns),
            "provider_native_row": dict(row),
        }

        for provider_column, canonical_target in FIDELITY_TO_CANONICAL_COLUMN_MAPPING.items():
            if provider_column not in header_set:
                continue
            canonical_row[canonical_target] = (row.get(provider_column) or "").strip()

        adapted_rows.append(canonical_row)

    return FidelityAdapterResult(
        universe=universe,
        file_path=str(file_path),
        headers=schema_evaluation.headers,
        schema_evaluation=schema_evaluation,
        raw_rows_discovered=raw_rows_discovered,
        duplicate_symbol_rows=duplicate_symbol_rows,
        dropped_non_data_rows=dropped_non_data_rows,
        adapted_rows=adapted_rows,
        unmapped_columns=unmapped_columns,
        column_lineage=column_lineage,
    )
