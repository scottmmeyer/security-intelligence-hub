"""Deterministic intake readiness validation for ESS ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping

from src.models.pipeline_models import PipelineStatus

DEFAULT_INTAKE_DIRECTORIES: Mapping[str, str] = {
    "starmine": "incoming/ess/starmine",
    "non_starmine_zacks": "incoming/ess/non_starmine_zacks",
}

INTAKE_BLOCKED_REASON = "NO_ELIGIBLE_ESS_INTAKE_FILES"
INTAKE_OPERATOR_GUIDANCE = (
    "No eligible ESS intake files were discovered. Place new provider export files into intake "
    "directories before rerunning pipeline."
)


@dataclass(frozen=True)
class IntakeReadinessResult:
    """Deterministic intake readiness evaluation result."""

    status: str
    discovered_files: Dict[str, List[Path]]
    intake_directories_checked: Dict[str, str]
    eligible_file_count: int
    blocked_reason: str | None
    operator_guidance: str | None

    @property
    def is_ready(self) -> bool:
        return self.status != PipelineStatus.BLOCKED.value

    @property
    def starmine_eligible_file_count(self) -> int:
        return len(self.discovered_files.get("starmine", []))

    @property
    def non_starmine_zacks_eligible_file_count(self) -> int:
        return len(self.discovered_files.get("non_starmine_zacks", []))

    def to_validation_summary(self) -> Dict[str, str]:
        return {
            "intake_directories_checked": "|".join(
                [
                    self.intake_directories_checked["starmine"],
                    self.intake_directories_checked["non_starmine_zacks"],
                ]
            ),
            "eligible_file_count": str(self.eligible_file_count),
            "starmine_eligible_file_count": str(self.starmine_eligible_file_count),
            "non_starmine_zacks_eligible_file_count": str(self.non_starmine_zacks_eligible_file_count),
            "intake_readiness": self.status,
            "blocked_reason": self.blocked_reason or "",
            "operator_guidance": self.operator_guidance or "",
        }


def _discover_eligible_csv_files(intake_dir: str | Path) -> List[Path]:
    path = Path(intake_dir)
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.csv") if item.is_file())


def validate_intake_readiness(
    intake_directories: Mapping[str, str | Path] | None = None,
) -> IntakeReadinessResult:
    """Validate ESS intake readiness before ingestion begins."""

    configured_directories = intake_directories or DEFAULT_INTAKE_DIRECTORIES
    directories_checked = {
        "starmine": str(configured_directories["starmine"]),
        "non_starmine_zacks": str(configured_directories["non_starmine_zacks"]),
    }

    discovered = {
        "starmine": _discover_eligible_csv_files(directories_checked["starmine"]),
        "non_starmine_zacks": _discover_eligible_csv_files(directories_checked["non_starmine_zacks"]),
    }
    eligible_file_count = sum(len(items) for items in discovered.values())

    if eligible_file_count == 0:
        return IntakeReadinessResult(
            status=PipelineStatus.BLOCKED.value,
            discovered_files=discovered,
            intake_directories_checked=directories_checked,
            eligible_file_count=0,
            blocked_reason=INTAKE_BLOCKED_REASON,
            operator_guidance=INTAKE_OPERATOR_GUIDANCE,
        )

    return IntakeReadinessResult(
        status=PipelineStatus.COMPLETE.value,
        discovered_files=discovered,
        intake_directories_checked=directories_checked,
        eligible_file_count=eligible_file_count,
        blocked_reason=None,
        operator_guidance=None,
    )
