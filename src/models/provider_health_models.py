from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EssCoverageGapDetail:
    """Structured detail for one holding absent from the latest ESS file."""

    symbol: str
    company_name: str
    last_ess_date: str
    current_ess_posture: str
    days_stale: int


@dataclass(frozen=True)
class EssCoverageGapWarning:
    """Structured ESS coverage-drop warning for held positions."""

    snapshot_date: str
    warning_code: str = "ESS_COVERAGE_GAP"
    status: str = "WARNING"
    warning_count: int = 0
    example_symbols: tuple[str, ...] = field(default_factory=tuple)
    gaps: tuple[EssCoverageGapDetail, ...] = field(default_factory=tuple)

    @property
    def summary_message(self) -> str:
        examples = ", ".join(self.example_symbols)
        if examples:
            return (
                f"ESS Coverage Warning — {self.warning_count} holdings absent from latest ESS file. "
                f"Examples: {examples}"
            )
        return f"ESS Coverage Warning — {self.warning_count} holdings absent from latest ESS file."