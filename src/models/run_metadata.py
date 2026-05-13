"""Run-level lineage metadata contracts.

This model captures deterministic provenance for historical snapshot creation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class RunMetadata:
    """Lineage metadata for deterministic benchmark processing runs."""

    run_id: str
    snapshot_date: date
    source_provider: str
    source_file: str
    created_at: datetime
    processing_status: str


# TODO(WP-03): extend processing_status enum policy when ESS run lineage begins.