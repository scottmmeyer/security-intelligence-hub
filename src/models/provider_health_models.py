from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EssCoverageGapDetail:
    """Structured detail for one holding with ESS coverage concern."""

    symbol: str
    company_name: str
    last_ess_date: str
    current_ess_posture: str
    days_stale: int
    gap_type: str = "NO_FRESH_STARMINE"


@dataclass(frozen=True)
class EssCoverageGapWarning:
    """Structured ESS coverage-drop warning for held positions."""

    snapshot_date: str
    warning_code: str = "ESS_COVERAGE_GAP"
    status: str = "WARNING"
    warning_count: int = 0
    example_symbols: tuple[str, ...] = field(default_factory=tuple)
    gaps: tuple[EssCoverageGapDetail, ...] = field(default_factory=tuple)
    true_missing_count: int = 0
    stale_coverage_count: int = 0
    no_fresh_starmine_count: int = 0
    true_missing_symbols: tuple[str, ...] = field(default_factory=tuple)
    stale_coverage_symbols: tuple[str, ...] = field(default_factory=tuple)
    no_fresh_starmine_symbols: tuple[str, ...] = field(default_factory=tuple)

    @property
    def summary_message(self) -> str:
        examples = ", ".join(self.example_symbols)
        base = (
            "ESS Coverage Warning — "
            f"{self.warning_count} holdings require ESS attention "
            f"(missing={self.true_missing_count}, stale={self.stale_coverage_count}, "
            f"no_fresh_starmine={self.no_fresh_starmine_count})."
        )
        if examples:
            return f"{base} Examples: {examples}"
        return base