"""Provider-native normalization orchestration for canonical ESS outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from src.normalize.ess_normalizer import normalize_ess_rows
from src.normalize.market_cap_normalizer import load_market_cap_config, normalize_market_cap
from src.providers.fidelity.fidelity_ess_adapter import adapt_fidelity_ess_file
from src.validation.provider_mapping_validator import validate_fidelity_provider_mappings


@dataclass(frozen=True)
class ProviderNormalizationResult:
    """Provider normalization result with deterministic row accounting."""

    normalized_signal_rows: List[Dict[str, Any]]
    base_universe_rows: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    raw_rows_discovered: int
    raw_rows_parsed: int
    rows_validated: int
    rows_normalized: int
    rows_rejected: int
    duplicate_symbols: int
    malformed_values: int
    unmapped_columns: List[str]


def normalize_fidelity_ess_file(
    *,
    file_path: str | Path,
    universe: str,
    snapshot_date: date,
    run_id: str,
    coverage_mapping: Dict[str, str],
    market_cap_config_path: str | Path = "config/market_cap_buckets.yaml",
) -> ProviderNormalizationResult:
    """Normalize Fidelity provider-native file into canonical signal and universe rows."""

    adapter_result = adapt_fidelity_ess_file(
        file_path=file_path,
        universe=universe,
        snapshot_date=snapshot_date,
        provider="FIDELITY",
    )
    mapping_result = validate_fidelity_provider_mappings(adapter_result)

    if mapping_result.errors:
        return ProviderNormalizationResult(
            normalized_signal_rows=[],
            base_universe_rows=[],
            errors=mapping_result.errors,
            warnings=mapping_result.warnings,
            raw_rows_discovered=mapping_result.raw_rows_discovered,
            raw_rows_parsed=mapping_result.raw_rows_parsed,
            rows_validated=mapping_result.rows_validated,
            rows_normalized=0,
            rows_rejected=mapping_result.rows_rejected,
            duplicate_symbols=mapping_result.duplicate_symbols,
            malformed_values=mapping_result.malformed_values,
            unmapped_columns=mapping_result.unmapped_columns,
        )

    canonical_inputs: List[Dict[str, str]] = []
    for row in mapping_result.validated_rows:
        canonical_inputs.append(
            {
                "snapshot_date": str(row.get("snapshot_date") or ""),
                "symbol": str(row.get("symbol") or ""),
                "provider": str(row.get("provider") or ""),
                "source_file": str(row.get("source_file") or ""),
                "starmine_ess_text": str(row.get("starmine_ess_text") or ""),
            }
        )

    normalized_signal_rows = normalize_ess_rows(
        rows=canonical_inputs,
        universe=universe,
        coverage_mapping=coverage_mapping,
        derive_numeric=True,
    )

    market_cap_config = load_market_cap_config(file_path=market_cap_config_path)
    base_universe_rows: List[Dict[str, Any]] = []

    for validated_row, signal_row in zip(mapping_result.validated_rows, normalized_signal_rows):
        market_cap_value = validated_row.get("market_cap_raw_usd")
        market_cap_bucket = "UNKNOWN"
        if isinstance(market_cap_value, int):
            normalized_cap = normalize_market_cap(
                market_cap_raw_usd=market_cap_value,
                market_cap_snapshot_date=snapshot_date,
                provider=str(signal_row.get("provider") or "FIDELITY"),
                config=market_cap_config,
            )
            market_cap_bucket = normalized_cap.market_cap_bucket

        geography = (validated_row.get("geography") or "").strip() if isinstance(validated_row.get("geography"), str) else ""
        if not geography:
            geography = "UNKNOWN"

        base_universe_rows.append(
            {
                "symbol": signal_row.get("symbol"),
                "company_name": validated_row.get("company_name") or "",
                "security_type": validated_row.get("security_type") or "",
                "geography": geography,
                "market_cap_raw_usd": market_cap_value if market_cap_value is not None else "",
                "market_cap_bucket": market_cap_bucket,
                "coverage_domain": signal_row.get("coverage_domain"),
                "starmine_ess_text": signal_row.get("starmine_ess_text") or "",
                "zacks_rating": "",
                "ess_zacks_rating": validated_row.get("analyst_rating") or "",
                "provider": signal_row.get("provider"),
                "source_file": signal_row.get("source_file"),
                "snapshot_date": signal_row.get("snapshot_date"),
                "run_id": run_id,
                "provider_schema_version": validated_row.get("provider_schema_version", "UNKNOWN"),
                "provider_column_lineage": validated_row.get("provider_column_lineage", {}),
                "unmapped_provider_columns": validated_row.get("unmapped_provider_columns", []),
            }
        )

    return ProviderNormalizationResult(
        normalized_signal_rows=normalized_signal_rows,
        base_universe_rows=base_universe_rows,
        errors=[],
        warnings=mapping_result.warnings,
        raw_rows_discovered=mapping_result.raw_rows_discovered,
        raw_rows_parsed=mapping_result.raw_rows_parsed,
        rows_validated=mapping_result.rows_validated,
        rows_normalized=len(normalized_signal_rows),
        rows_rejected=mapping_result.rows_rejected,
        duplicate_symbols=mapping_result.duplicate_symbols,
        malformed_values=mapping_result.malformed_values,
        unmapped_columns=mapping_result.unmapped_columns,
    )
