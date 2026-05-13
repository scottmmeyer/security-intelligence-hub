"""Deterministic Fidelity provider-native to canonical field mapping."""

from __future__ import annotations

from typing import Dict, List

from src.validation.ess_validator import ALLOWED_ESS_TEXT_CATEGORIES

FIDELITY_TO_CANONICAL_COLUMN_MAPPING: dict[str, str] = {
    "Symbol": "symbol",
    "Company Name": "company_name",
    "Security Type": "security_type",
    "Security Price": "security_price_raw",
    "Equity Summary Score (ESS) from LSEG StarMine": "starmine_ess_text",
    "Forward EPS Long Term Growth (3-5 Yrs)": "yahoo_growth_projection_placeholder",
    "Market Capitalization": "market_cap_raw_usd",
    "Jefferson Research": "jefferson_rating",
    "Zacks Investment Research": "analyst_rating",
    "McLean Capital Management": "mclean_rating",
    "Geography": "geography",
}


def validate_fidelity_column_mapping() -> List[str]:
    """Validate static mapping contracts for deterministic failures."""

    errors: List[str] = []
    seen_targets: set[str] = set()
    for provider_column, canonical_target in FIDELITY_TO_CANONICAL_COLUMN_MAPPING.items():
        if not provider_column.strip():
            errors.append("Malformed mapping definition: provider column cannot be empty.")
        if not canonical_target.strip():
            errors.append(f"Missing canonical target for provider column {provider_column!r}.")
        if canonical_target in seen_targets:
            errors.append(f"Duplicate canonical mapping target detected: {canonical_target!r}.")
        seen_targets.add(canonical_target)
    return errors


def normalize_fidelity_ess_text(raw_value: str) -> str | None:
    """Normalize Fidelity ESS text categories into canonical category tokens."""

    cleaned = (raw_value or "").strip()
    if not cleaned or cleaned == "--":
        return None

    normalized = cleaned.upper().replace(" ", "_")
    if normalized not in ALLOWED_ESS_TEXT_CATEGORIES:
        raise ValueError(f"invalid ESS category {raw_value!r}")
    return normalized


def parse_market_cap_raw_usd(raw_value: str) -> int | None:
    """Parse provider-native market cap strings like $1.74B into integer USD."""

    cleaned = (raw_value or "").strip().upper().replace(",", "")
    if not cleaned or cleaned == "--":
        return None

    if cleaned.startswith("$"):
        cleaned = cleaned[1:]

    multiplier = 1.0
    if cleaned.endswith("K"):
        multiplier = 1_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("M"):
        multiplier = 1_000_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("B"):
        multiplier = 1_000_000_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("T"):
        multiplier = 1_000_000_000_000.0
        cleaned = cleaned[:-1]

    try:
        parsed = float(cleaned)
    except ValueError as exc:
        raise ValueError(f"invalid market_cap value {raw_value!r}") from exc

    if parsed < 0:
        raise ValueError(f"invalid market_cap value {raw_value!r}: cannot be negative")

    return int(round(parsed * multiplier))
