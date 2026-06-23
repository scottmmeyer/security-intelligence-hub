from __future__ import annotations

from pathlib import Path

from src.models.pipeline_models import PipelineStatus
from src.validation.intake_readiness_validator import validate_intake_readiness


def test_intake_readiness_blocks_when_no_eligible_files(tmp_path: Path) -> None:
    directories = {
        "starmine": tmp_path / "incoming" / "ess" / "starmine",
        "non_starmine_zacks": tmp_path / "incoming" / "ess" / "non_starmine_zacks",
    }
    directories["starmine"].mkdir(parents=True, exist_ok=True)
    directories["non_starmine_zacks"].mkdir(parents=True, exist_ok=True)

    result = validate_intake_readiness(intake_directories=directories)

    assert result.status == PipelineStatus.BLOCKED.value
    assert result.is_ready is False
    assert result.eligible_file_count == 0
    assert result.to_validation_summary()["operator_guidance"].startswith(
        "No eligible ESS intake files were discovered"
    )


def test_intake_readiness_passes_with_eligible_files(tmp_path: Path) -> None:
    directories = {
        "starmine": tmp_path / "incoming" / "ess" / "starmine",
        "non_starmine_zacks": tmp_path / "incoming" / "ess" / "non_starmine_zacks",
    }
    directories["starmine"].mkdir(parents=True, exist_ok=True)
    directories["non_starmine_zacks"].mkdir(parents=True, exist_ok=True)

    (directories["starmine"] / "starmine.csv").write_text("col\nvalue\n", encoding="utf-8")
    (directories["non_starmine_zacks"] / "non_starmine.csv").write_text("col\nvalue\n", encoding="utf-8")

    result = validate_intake_readiness(intake_directories=directories)

    assert result.status == PipelineStatus.COMPLETE.value
    assert result.is_ready is True
    assert result.eligible_file_count == 2
    assert result.starmine_eligible_file_count == 1
    assert result.non_starmine_zacks_eligible_file_count == 1


def test_intake_readiness_accepts_hyphenated_non_ess_filename(tmp_path: Path) -> None:
    directories = {
        "starmine": tmp_path / "incoming" / "ess" / "starmine",
        "non_starmine_zacks": tmp_path / "incoming" / "ess" / "non_starmine_zacks",
    }
    directories["starmine"].mkdir(parents=True, exist_ok=True)
    directories["non_starmine_zacks"].mkdir(parents=True, exist_ok=True)

    (directories["non_starmine_zacks"] / "non-ess.csv").write_text("col\nvalue\n", encoding="utf-8")

    result = validate_intake_readiness(intake_directories=directories)

    assert result.status == PipelineStatus.COMPLETE.value
    assert result.non_starmine_zacks_eligible_file_count == 1


def test_intake_readiness_accepts_uppercase_csv_extension(tmp_path: Path) -> None:
    directories = {
        "starmine": tmp_path / "incoming" / "ess" / "starmine",
        "non_starmine_zacks": tmp_path / "incoming" / "ess" / "non_starmine_zacks",
    }
    directories["starmine"].mkdir(parents=True, exist_ok=True)
    directories["non_starmine_zacks"].mkdir(parents=True, exist_ok=True)

    (directories["non_starmine_zacks"] / "non-ess.CSV").write_text("col\nvalue\n", encoding="utf-8")

    result = validate_intake_readiness(intake_directories=directories)

    assert result.status == PipelineStatus.COMPLETE.value
    assert result.non_starmine_zacks_eligible_file_count == 1
