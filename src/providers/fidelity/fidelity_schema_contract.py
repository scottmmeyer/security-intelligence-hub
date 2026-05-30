"""Deterministic Fidelity ESS provider-native schema contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

FIDELITY_SCHEMA_VERSION = "FIDELITY_ESS_EXPORT_V1"

# Fidelity's screener export uses an abbreviated column header for the ESS field.
# This maps known abbreviations to the canonical full-length column name so the
# rest of the pipeline sees a consistent header regardless of export source.
FIDELITY_COLUMN_ALIASES: dict[str, str] = {
    "ESS from LSEG StarMine": "Equity Summary Score (ESS) from LSEG StarMine",
    "Fwd EPS LTG (3-5 Yrs)": "Forward EPS Long Term Growth (3-5 Yrs)",
}

FIDELITY_KNOWN_COLUMNS: tuple[str, ...] = (
    "Symbol",
    "Company Name",
    "Security Type",
    "Security Price",
    "Equity Summary Score (ESS) from LSEG StarMine",
    "Forward EPS Long Term Growth (3-5 Yrs)",
    "Market Capitalization",
    "Jefferson Research",
    "Zacks Investment Research",
    "McLean Capital Management",
    "Geography",
)

UNIVERSE_REQUIRED_PROVIDER_COLUMNS: dict[str, tuple[str, ...]] = {
    "starmine": (
        "Symbol",
        "Company Name",
        "Security Type",
        "Equity Summary Score (ESS) from LSEG StarMine",
        "Market Capitalization",
    ),
    "non_starmine_zacks": (
        "Symbol",
        "Company Name",
        "Security Type",
        "Zacks Investment Research",
        "Market Capitalization",
    ),
}

UNIVERSE_OPTIONAL_PROVIDER_COLUMNS: dict[str, tuple[str, ...]] = {
    "starmine": (
        "Security Price",
        "Forward EPS Long Term Growth (3-5 Yrs)",
        "Jefferson Research",
        "Zacks Investment Research",
        "McLean Capital Management",
        "Geography",
    ),
    "non_starmine_zacks": (
        "Security Price",
        "Forward EPS Long Term Growth (3-5 Yrs)",
        "Jefferson Research",
        "McLean Capital Management",
        "Geography",
    ),
}


@dataclass(frozen=True)
class FidelitySchemaEvaluation:
    """Evaluation output for provider-native Fidelity schema detection."""

    headers: tuple[str, ...]
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    missing_required_columns: tuple[str, ...]
    unknown_columns: tuple[str, ...]


def _sanitize_headers(headers: Sequence[str]) -> tuple[str, ...]:
    return tuple((item or "").strip() for item in headers if (item or "").strip())


def _normalize_column_name(name: str) -> str:
    """Resolve abbreviated Fidelity column names to their canonical equivalents."""
    return FIDELITY_COLUMN_ALIASES.get(name, name)


def evaluate_fidelity_schema(headers: Sequence[str], universe: str) -> FidelitySchemaEvaluation:
    """Evaluate provider-native schema shape without mutating source structure."""

    if universe not in UNIVERSE_REQUIRED_PROVIDER_COLUMNS:
        raise ValueError(f"Unsupported fidelity universe {universe!r}.")

    sanitized_headers = tuple(_normalize_column_name(h) for h in _sanitize_headers(headers))
    header_set = set(sanitized_headers)
    required_columns = UNIVERSE_REQUIRED_PROVIDER_COLUMNS[universe]
    optional_columns = UNIVERSE_OPTIONAL_PROVIDER_COLUMNS[universe]
    missing_required_columns = tuple(sorted(set(required_columns).difference(header_set)))
    known_set = set(FIDELITY_KNOWN_COLUMNS)
    unknown_columns = tuple(sorted(column for column in sanitized_headers if column not in known_set))

    return FidelitySchemaEvaluation(
        headers=sanitized_headers,
        required_columns=required_columns,
        optional_columns=optional_columns,
        missing_required_columns=missing_required_columns,
        unknown_columns=unknown_columns,
    )
