from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts import process_incoming_portfolio as pip


def _write(path: Path, content: str = "Account,Symbol\nA,ABC\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_filename_date_valid() -> None:
    parsed, error = pip.parse_filename_date("Portfolio_Positions_Jun-27-2026.csv")
    assert parsed == "2026-06-27"
    assert error is None


def test_parse_filename_date_invalid_unparseable() -> None:
    parsed, error = pip.parse_filename_date("Portfolio_Positions_without_date.csv")
    assert parsed is None
    assert "missing filename date token" in str(error)


def test_parse_filename_date_invalid_calendar() -> None:
    parsed, error = pip.parse_filename_date("Portfolio_Positions_Feb-31-2026.csv")
    assert parsed is None
    assert "invalid filename date token" in str(error)


def test_validate_target_date_success() -> None:
    out = pip.validate_target_date("2026-06-27")
    assert out.isoformat() == "2026-06-27"


def test_validate_target_date_failure() -> None:
    with pytest.raises(ValueError):
        pip.validate_target_date("06-27-2026")


def test_discover_csv_files_stable_order_and_ignore_non_csv(tmp_path: Path) -> None:
    _write(tmp_path / "b.csv")
    _write(tmp_path / "a.csv")
    _write(tmp_path / "ignore.txt")

    files = pip.discover_csv_files(tmp_path)
    assert [f.name for f in files] == ["a.csv", "b.csv"]


def test_default_target_date_gate_selects_only_matching(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")
    _write(tmp_path / "Portfolio_Positions_Jun-26-2026.csv")

    files = pip.discover_csv_files(tmp_path)
    selected, skipped = pip.select_files_for_processing(
        files,
        target_date="2026-06-27",
        all_dates=False,
    )

    assert [p.name for p, _ in selected] == ["Portfolio_Positions_Jun-27-2026.csv"]
    assert len(skipped) == 1
    assert "stale date" in skipped[0].reason


def test_explicit_target_date_gate_selects_requested_date(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-25-2026.csv")
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")

    files = pip.discover_csv_files(tmp_path)
    selected, _ = pip.select_files_for_processing(
        files,
        target_date="2026-06-25",
        all_dates=False,
    )

    assert [p.name for p, _ in selected] == ["Portfolio_Positions_Jun-25-2026.csv"]


def test_all_dates_selects_all_parseable(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-25-2026.csv")
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")
    _write(tmp_path / "Portfolio_Positions_no_date.csv")

    files = pip.discover_csv_files(tmp_path)
    selected, skipped = pip.select_files_for_processing(
        files,
        target_date="2026-06-27",
        all_dates=True,
    )

    assert [p.name for p, _ in selected] == [
        "Portfolio_Positions_Jun-25-2026.csv",
        "Portfolio_Positions_Jun-27-2026.csv",
    ]
    assert len(skipped) == 1


def test_all_dates_requires_confirmation_unless_dry_run(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")

    rc = pip.main(
        ["--all-dates", "--target-date", "2026-06-27"],
        incoming_dir=tmp_path,
    )
    assert rc != 0

    rc_dry = pip.main(
        ["--all-dates", "--dry-run", "--target-date", "2026-06-27"],
        incoming_dir=tmp_path,
    )
    assert rc_dry == 0


def test_dry_run_never_calls_run_analysis(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")

    called = {"count": 0}

    def _runner(*args, **kwargs):
        called["count"] += 1
        return {"status": "SHOULD_NOT_RUN"}

    rc = pip.main(
        ["--target-date", "2026-06-27", "--dry-run"],
        incoming_dir=tmp_path,
        analysis_runner=_runner,
    )
    assert rc == 0
    assert called["count"] == 0


def test_per_file_run_analysis_success_recorded(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")

    def _runner(*args, **kwargs):
        return {"status": "ACCEPTED", "run_id": "R1"}

    rc = pip.main(
        ["--target-date", "2026-06-27"],
        incoming_dir=tmp_path,
        analysis_runner=_runner,
    )
    assert rc == 0


def test_per_file_failure_status_recorded_and_nonzero(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")

    def _runner(*args, **kwargs):
        return {"status": "FAILED", "run_id": "R2"}

    rc = pip.main(
        ["--target-date", "2026-06-27"],
        incoming_dir=tmp_path,
        analysis_runner=_runner,
    )
    assert rc == 1


def test_per_file_exception_captured_and_batch_continues(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026 (1).csv")

    calls = {"n": 0}

    def _runner(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return {"status": "ACCEPTED", "run_id": "R3"}

    rc = pip.main(
        ["--target-date", "2026-06-27"],
        incoming_dir=tmp_path,
        analysis_runner=_runner,
    )
    assert calls["n"] == 2
    assert rc == 1


def test_invalid_target_date_returns_nonzero(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")

    rc = pip.main(
        ["--target-date", "06-27-2026", "--dry-run"],
        incoming_dir=tmp_path,
    )
    assert rc == 2


def test_mandate_is_delegated_to_runner_not_locally_validated(tmp_path: Path) -> None:
    _write(tmp_path / "Portfolio_Positions_Jun-27-2026.csv")

    seen = {"mandate": ""}

    def _runner(*args, **kwargs):
        seen["mandate"] = kwargs.get("mandate_type", "")
        return {"status": "ACCEPTED", "run_id": "R4"}

    rc = pip.main(
        ["--target-date", "2026-06-27", "--mandate-type", "NOT_A_REAL_MANDATE"],
        incoming_dir=tmp_path,
        analysis_runner=_runner,
    )
    assert rc == 0
    assert seen["mandate"] == "NOT_A_REAL_MANDATE"
