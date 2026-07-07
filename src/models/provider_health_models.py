from __future__ import annotations

from dataclasses import dataclass, field


GAP_TYPE_TRUE_MISSING = "TRUE_MISSING"
GAP_TYPE_STALE_ESS = "STALE_ESS"
GAP_TYPE_NO_FRESH_STARMINE = "NO_FRESH_STARMINE"
GAP_TYPE_NO_SCORE_AVAILABLE = "NO_SCORE_AVAILABLE"
GAP_TYPE_NO_COVERAGE_AVAILABLE = "NO_COVERAGE_AVAILABLE"

GAP_TYPE_ORDER = (
    GAP_TYPE_TRUE_MISSING,
    GAP_TYPE_STALE_ESS,
    GAP_TYPE_NO_FRESH_STARMINE,
    GAP_TYPE_NO_SCORE_AVAILABLE,
    GAP_TYPE_NO_COVERAGE_AVAILABLE,
)


@dataclass(frozen=True)
class EssCoverageGapDetail:
    """Structured detail for one holding with ESS coverage concern."""

    symbol: str
    company_name: str
    last_ess_date: str
    current_ess_posture: str
    days_stale: int
    gap_type: str = GAP_TYPE_NO_FRESH_STARMINE
    reason: str = ""


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
    no_score_available_count: int = 0
    no_coverage_available_count: int = 0
    true_missing_symbols: tuple[str, ...] = field(default_factory=tuple)
    stale_coverage_symbols: tuple[str, ...] = field(default_factory=tuple)
    no_fresh_starmine_symbols: tuple[str, ...] = field(default_factory=tuple)
    no_score_available_symbols: tuple[str, ...] = field(default_factory=tuple)
    no_coverage_available_symbols: tuple[str, ...] = field(default_factory=tuple)
    counts_by_gap_type: dict[str, int] = field(default_factory=dict)

    @property
    def summary_message(self) -> str:
        examples = ", ".join(self.example_symbols)
        if examples:
            return (
                f"ESS Coverage Warning — {self.warning_count} holdings absent from latest ESS file. "
                f"Examples: {examples}"
            )
        return f"ESS Coverage Warning — {self.warning_count} holdings absent from latest ESS file."