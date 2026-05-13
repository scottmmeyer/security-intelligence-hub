"""Deterministic provider-to-canonical mapping validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, List

from src.providers.fidelity.fidelity_column_mapping import (
    FIDELITY_TO_CANONICAL_COLUMN_MAPPING,
    normalize_fidelity_ess_text,
    parse_market_cap_raw_usd,
    validate_fidelity_column_mapping,
)
from src.providers.fidelity.fidelity_ess_adapter import FidelityAdapterResult
from src.providers.fidelity.fidelity_schema_contract import UNIVERSE_REQUIRED_PROVIDER_COLUMNS


class ProviderMappingValidationError(ValueError):
    """Raised when provider mapping validation fails deterministically."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("Provider mapping validation failed: " + "; ".join(errors))


@dataclass(frozen=True)
class ProviderMappingValidationResult:
    """Validation output including row accounting metrics."""

    validated_rows: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    raw_rows_discovered: int
    raw_rows_parsed: int
    rows_validated: int
    rows_rejected: int
    duplicate_symbols: int
    malformed_values: int
    unmapped_columns: List[str]


def validate_fidelity_provider_mappings(adapter_result: FidelityAdapterResult) -> ProviderMappingValidationResult:
    """Validate adapted Fidelity rows against deterministic mapping rules."""

    errors: List[str] = []
    warnings: List[str] = []

    static_mapping_errors = validate_fidelity_column_mapping()
    if static_mapping_errors:
        errors.extend(static_mapping_errors)

    required_columns = UNIVERSE_REQUIRED_PROVIDER_COLUMNS[adapter_result.universe]
    required_missing = list(adapter_result.schema_evaluation.missing_required_columns)
    if required_missing:
        errors.append(
            "Required provider column validation failed: missing columns "
            + ", ".join(sorted(required_missing))
        )

    unmapped_required_fields = [
        column
        for column in required_columns
        if column in adapter_result.headers and column not in FIDELITY_TO_CANONICAL_COLUMN_MAPPING
    ]
    if unmapped_required_fields:
        errors.append(
            "Unmapped required provider fields detected: " + ", ".join(sorted(unmapped_required_fields))
        )

    if adapter_result.unmapped_columns:
        warnings.append(
            "Unmapped provider columns surfaced: " + ", ".join(sorted(adapter_result.unmapped_columns))
        )

    if adapter_result.schema_evaluation.unknown_columns:
        warnings.append(
            "Unknown Fidelity schema columns observed: "
            + ", ".join(sorted(adapter_result.schema_evaluation.unknown_columns))
        )

    source_name = Path(adapter_result.file_path).name
    if adapter_result.dropped_non_data_rows:
        warnings.append(
            f"Skipped {adapter_result.dropped_non_data_rows} non-data provider rows while parsing {source_name}."
        )
    if adapter_result.duplicate_symbol_rows:
        warnings.append(
            f"Skipped {adapter_result.duplicate_symbol_rows} duplicate symbol rows while parsing {source_name}."
        )

    validated_rows: List[Dict[str, Any]] = []
    seen_symbols: set[str] = set()
    duplicate_symbols = adapter_result.duplicate_symbol_rows
    malformed_values = 0
    rows_rejected = adapter_result.dropped_non_data_rows + adapter_result.duplicate_symbol_rows

    for row in adapter_result.adapted_rows:
        row_number = int(row.get("provider_row_number", 0))
        row_errors: List[str] = []

        symbol = (row.get("symbol") or "").strip().upper()
        if not symbol:
            row_errors.append(f"Malformed mapping at row {row_number}: symbol is empty.")
        elif not re.fullmatch(r"[A-Z0-9./-]+", symbol):
            row_errors.append(
                f"Malformed mapping at row {row_number}: symbol {symbol!r} is not a valid ticker token."
            )
        elif symbol in seen_symbols:
            duplicate_symbols += 1
            row_errors.append(f"Duplicate symbol detection at row {row_number}: duplicate symbol {symbol}.")
        else:
            seen_symbols.add(symbol)

        company_name = (row.get("company_name") or "").strip()
        if not company_name:
            row_errors.append(f"Malformed mapping at row {row_number}: company_name is empty.")

        security_type = (row.get("security_type") or "").strip()
        if not security_type:
            row_errors.append(f"Malformed mapping at row {row_number}: security_type is empty.")

        ess_text: str | None = None
        raw_ess_text = str(row.get("starmine_ess_text") or "")
        try:
            ess_text = normalize_fidelity_ess_text(raw_ess_text)
        except ValueError:
            malformed_values += 1
            row_errors.append(
                f"Invalid ESS category parsing at row {row_number}: {raw_ess_text!r} is not canonical."
            )

        if adapter_result.universe == "starmine" and not ess_text:
            row_errors.append(
                f"Unmapped required field at row {row_number}: starmine ESS text is required for starmine universe."
            )
        if adapter_result.universe == "non_starmine_zacks":
            analyst_rating = (row.get("analyst_rating") or "").strip()
            if not analyst_rating or analyst_rating == "--":
                row_errors.append(
                    f"Unmapped required field at row {row_number}: analyst_rating is required for non_starmine_zacks universe."
                )

        market_cap_raw = str(row.get("market_cap_raw_usd") or "")
        parsed_market_cap: int | None = None
        if not market_cap_raw.strip() or market_cap_raw.strip() == "--":
            row_errors.append(
                f"Unmapped required field at row {row_number}: market_cap_raw_usd is required."
            )
        try:
            parsed_market_cap = parse_market_cap_raw_usd(market_cap_raw)
        except ValueError:
            malformed_values += 1
            row_errors.append(
                f"Invalid market-cap parsing at row {row_number}: {market_cap_raw!r} is not parseable."
            )

        if row_errors:
            rows_rejected += 1
            errors.extend(row_errors)
            continue

        validated_row = dict(row)
        validated_row["symbol"] = symbol
        validated_row["starmine_ess_text"] = ess_text
        validated_row["market_cap_raw_usd"] = parsed_market_cap
        validated_rows.append(validated_row)

    return ProviderMappingValidationResult(
        validated_rows=validated_rows,
        errors=errors,
        warnings=warnings,
        raw_rows_discovered=adapter_result.raw_rows_discovered,
        raw_rows_parsed=len(adapter_result.adapted_rows),
        rows_validated=len(validated_rows),
        rows_rejected=rows_rejected,
        duplicate_symbols=duplicate_symbols,
        malformed_values=malformed_values,
        unmapped_columns=sorted(adapter_result.unmapped_columns),
    )


def assert_valid_fidelity_provider_mappings(adapter_result: FidelityAdapterResult) -> ProviderMappingValidationResult:
    """Raise deterministic validation exception if provider mappings fail."""

    result = validate_fidelity_provider_mappings(adapter_result)
    if result.errors:
        raise ProviderMappingValidationError(result.errors)
    return result
