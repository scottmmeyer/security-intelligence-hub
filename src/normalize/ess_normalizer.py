"""Deterministic ESS normalization scaffolding."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, List

ESS_TEXT_TO_NUMERIC_MAP = {
    "VERY_BEARISH": 1.0,
    "BEARISH": 2.0,
    "NEUTRAL": 3.0,
    "BULLISH": 4.0,
    "VERY_BULLISH": 5.0,
}


@dataclass(frozen=True)
class NormalizedEssRecord:
    """Canonical normalized ESS record with provenance-aware fields."""

    snapshot_date: str
    symbol: str
    provider: str
    source_file: str
    coverage_domain: str
    signal_coverage_status: str
    starmine_ess_text: str | None
    starmine_ess_numeric: float | None
    starmine_ess_numeric_estimated: bool
    starmine_ess_source_type: str
    # Raw 0.1–10.0 Fidelity ESS score, present only when the provider export
    # includes a dedicated numeric-score column (vs. text-label only).
    starmine_ess_raw_score: float | None


def normalize_symbol(raw_symbol: str) -> str:
    """Normalize symbol deterministically to uppercase trimmed token."""

    return raw_symbol.strip().upper()


def assign_coverage_domain(universe: str, row: Dict[str, str], mapping: Dict[str, str]) -> str:
    """Assign deterministic coverage domain with optional row override."""

    explicit_domain = (row.get("coverage_domain") or "").strip()
    if explicit_domain:
        return explicit_domain

    domain = mapping.get(universe)
    if not domain:
        raise ValueError(f"No coverage-domain mapping configured for universe {universe!r}.")
    return domain


def _resolve_source_type(row: Dict[str, str], numeric_value: float | None) -> str:
    source_type = (row.get("starmine_ess_source_type") or "").strip()
    if source_type:
        return source_type
    if numeric_value is not None:
        return "DIRECT_NUMERIC"
    return "UNKNOWN"


def _resolve_numeric_mapping(
    *,
    ess_text: str | None,
    direct_numeric_raw: str,
    derive_numeric: bool,
    source_type: str,
) -> tuple[float | None, bool, str]:
    if direct_numeric_raw.strip():
        return float(direct_numeric_raw), False, source_type or "DIRECT_NUMERIC"

    if derive_numeric and ess_text:
        mapped = ESS_TEXT_TO_NUMERIC_MAP.get(ess_text.upper())
        if mapped is not None:
            return mapped, True, "TEXT_MAPPED"

    if source_type == "MANUAL_ESTIMATE":
        estimate_raw = direct_numeric_raw.strip()
        if estimate_raw:
            return float(estimate_raw), True, "MANUAL_ESTIMATE"

    return None, False, source_type or "UNKNOWN"


def normalize_ess_rows(
    *,
    rows: List[Dict[str, str]],
    universe: str,
    coverage_mapping: Dict[str, str],
    derive_numeric: bool = False,
) -> List[Dict[str, Any]]:
    """Normalize ESS rows into canonical deterministic records."""

    normalized: List[Dict[str, Any]] = []
    for row in rows:
        symbol = normalize_symbol(row.get("symbol", ""))
        coverage_domain = assign_coverage_domain(universe=universe, row=row, mapping=coverage_mapping)

        ess_text_raw = (row.get("starmine_ess_text") or "").strip()
        ess_text = ess_text_raw if ess_text_raw else None
        source_type_hint = (row.get("starmine_ess_source_type") or "").strip()
        direct_numeric_raw = (row.get("starmine_ess_numeric") or "").strip()
        source_type = _resolve_source_type(row=row, numeric_value=float(direct_numeric_raw) if direct_numeric_raw else None)
        # Raw 0.1–10.0 score: present when provider exports a separate numeric column
        raw_score_str = (row.get("starmine_ess_raw_score") or "").strip()
        ess_raw_score: float | None = None
        if raw_score_str:
            try:
                v = float(raw_score_str)
                ess_raw_score = v if 0.0 <= v <= 10.0 else None
            except ValueError:
                pass
        starmine_numeric, estimated, resolved_source_type = _resolve_numeric_mapping(
            ess_text=ess_text,
            direct_numeric_raw=direct_numeric_raw,
            derive_numeric=derive_numeric,
            source_type=source_type_hint or source_type,
        )

        signal_coverage_status = "UNKNOWN"
        if coverage_domain == "STARMINE_COVERED":
            signal_coverage_status = "COVERED" if ess_text or starmine_numeric is not None else "PARTIAL"
        elif coverage_domain == "NON_STARMINE_ANALYST":
            signal_coverage_status = "NON_COVERED"
        elif coverage_domain == "PARTIAL_COVERAGE":
            signal_coverage_status = "PARTIAL"

        normalized_record = NormalizedEssRecord(
            snapshot_date=row["snapshot_date"],
            symbol=symbol,
            provider=(row.get("provider") or "").strip(),
            source_file=(row.get("source_file") or "").strip(),
            coverage_domain=coverage_domain,
            signal_coverage_status=signal_coverage_status,
            starmine_ess_text=ess_text,
            starmine_ess_numeric=starmine_numeric,
            starmine_ess_numeric_estimated=estimated,
            starmine_ess_source_type=resolved_source_type,
            starmine_ess_raw_score=ess_raw_score,
        )
        normalized.append(asdict(normalized_record))

    return normalized


def parse_snapshot_date(snapshot_date_value: str) -> date:
    """Parse snapshot date into date type for downstream append logic."""

    return date.fromisoformat(snapshot_date_value)


# TODO(WP-04): integrate additional provider-specific coverage-domain mapping rules.