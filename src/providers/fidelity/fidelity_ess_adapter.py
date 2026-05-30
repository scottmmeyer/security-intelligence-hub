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
    FIDELITY_COLUMN_ALIASES,
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

# ESS cell format from the screener export: numeric score and text label are
# placed in the same cell separated by whitespace / newlines, e.g.:
#   "7\nNeutral"  or  "9\nBullish"  or just  "Bullish" (text-only older exports)
_ESS_NUMERIC_RE = re.compile(r"""(?x)
    ^\s*
    (?P<num>[0-9]+(?:\.[0-9]+)?)   # leading numeric part (the 0.1–10.0 score)
    [\s\n,]+                        # whitespace / newline separator
    (?P<text>[A-Za-z][A-Za-z_ ]+)  # trailing text label
    \s*$
""")


def _parse_ess_cell(raw: str) -> tuple[float | None, str | None]:
    """Parse a combined ESS cell value into (raw_score_0_10, ess_text_label).

    Handles three observed Fidelity export formats:
      - ``"7\\nNeutral"``   → (7.0, "Neutral")
      - ``"9\\nBullish"``  → (9.0, "Bullish")
      - ``"Bullish"``      → (None, "Bullish")   (text-only, older exports)
    """
    cleaned = (raw or "").strip()
    if not cleaned:
        return None, None
    m = _ESS_NUMERIC_RE.match(cleaned)
    if m:
        try:
            num = float(m.group("num"))
            raw_score = num if 0.0 <= num <= 10.0 else None
        except ValueError:
            raw_score = None
        return raw_score, m.group("text").strip()
    # No numeric prefix — treat entire value as text label only
    return None, cleaned


def _load_provider_csv(file_path: str | Path) -> tuple[List[str], List[Dict[str, str]]]:
    csv_path = Path(file_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        raw_headers: List[str] = list(reader.fieldnames or [])
        # Normalize abbreviated column names to canonical equivalents so the
        # rest of the pipeline sees a consistent schema regardless of export source.
        canonical_headers = [FIDELITY_COLUMN_ALIASES.get(h.strip(), h.strip()) for h in raw_headers]
        rows: List[Dict[str, str]] = []
        for row in reader:
            normalized_row = {FIDELITY_COLUMN_ALIASES.get(k.strip(), k.strip()): v for k, v in row.items()}
            rows.append(normalized_row)
    return canonical_headers, rows


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
            raw_value = (row.get(provider_column) or "").strip()

            # The ESS column in Fidelity's screener export contains both a
            # 0.1–10.0 numeric score and a text label in one cell (e.g. "7\nNeutral").
            # Parse them out so we preserve the precision that the text label loses.
            if canonical_target == "starmine_ess_text":
                raw_score, ess_text = _parse_ess_cell(raw_value)
                canonical_row["starmine_ess_text"] = ess_text or ""
                if raw_score is not None:
                    canonical_row["starmine_ess_raw_score"] = str(raw_score)
            else:
                canonical_row[canonical_target] = raw_value

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
