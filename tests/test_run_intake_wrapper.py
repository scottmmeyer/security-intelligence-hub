from __future__ import annotations

from datetime import date
from pathlib import Path

from src.pipeline.stage_registry import StageDefinition


def _load_wrapper_module():
    from scripts import _run_intake

    return _run_intake


class _FakeManifest:
    def __init__(self, *, run_id: str, snapshot_date: date, overall_status: str) -> None:
        self.run_id = run_id
        self.snapshot_date = snapshot_date
        self.overall_status = overall_status
        self.warnings: tuple[str, ...] = ()
        self.errors: tuple[str, ...] = ()
        self.stages = ()
        self.artifacts = ()
        self.validation_summary = {}


class _RecordingRunner:
    last_init: dict | None = None
    last_run: dict | None = None
    status: str = "COMPLETE"

    def __init__(self, *, runs_root: Path, stages: tuple[StageDefinition, ...]) -> None:
        type(self).last_init = {
            "runs_root": runs_root,
            "stages": stages,
        }

    def run(self, *, run_id: str, snapshot_date: date) -> _FakeManifest:
        type(self).last_run = {
            "run_id": run_id,
            "snapshot_date": snapshot_date,
        }
        return _FakeManifest(run_id=run_id, snapshot_date=snapshot_date, overall_status=type(self).status)


def test_wrapper_invokes_registered_ess_stage_only(tmp_path: Path) -> None:
    mod = _load_wrapper_module()

    marker = {"called": False}

    def _ess_executor(_context):
        marker["called"] = True
        raise AssertionError("Executor should not be called in this mocked test")

    stages = (
        StageDefinition("benchmark_validation", "placeholder"),
        StageDefinition("ess_intake", "ess", _ess_executor),
        StageDefinition("normalization", "placeholder"),
    )

    _RecordingRunner.status = "COMPLETE"
    rc = mod.main(
        [
            "--snapshot-date",
            "2026-08-18",
            "--run-id",
            "RUN-REAL-ESS-20260818-009",
            "--runs-root",
            str(tmp_path / "runs"),
        ],
        pipeline_runner_factory=_RecordingRunner,
        stage_registry_loader=lambda: stages,
    )

    assert rc == 0
    assert marker["called"] is False
    assert _RecordingRunner.last_init is not None
    chosen_stages = _RecordingRunner.last_init["stages"]
    assert len(chosen_stages) == 1
    assert chosen_stages[0].stage_name == "ess_intake"
    assert chosen_stages[0].executor is _ess_executor
    assert _RecordingRunner.last_run == {
        "run_id": "RUN-REAL-ESS-20260818-009",
        "snapshot_date": date(2026, 8, 18),
    }


def test_wrapper_generates_next_run_id_from_existing_manifests(tmp_path: Path) -> None:
    mod = _load_wrapper_module()
    manifests = tmp_path / "runs" / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    (manifests / "RUN-REAL-ESS-20260818-001_manifest.json").write_text("{}", encoding="utf-8")
    (manifests / "RUN-REAL-ESS-20260818-003_manifest.json").write_text("{}", encoding="utf-8")

    generated = mod._build_run_id(date(2026, 8, 18), tmp_path / "runs")
    assert generated == "RUN-REAL-ESS-20260818-004"


def test_wrapper_returns_nonzero_on_blocked_or_failed_stage(tmp_path: Path) -> None:
    mod = _load_wrapper_module()
    stages = (StageDefinition("ess_intake", "ess", lambda _ctx: None),)

    _RecordingRunner.status = "BLOCKED"
    blocked_rc = mod.main(
        ["--snapshot-date", "2026-08-18", "--runs-root", str(tmp_path / "runs")],
        pipeline_runner_factory=_RecordingRunner,
        stage_registry_loader=lambda: stages,
    )
    assert blocked_rc == 1

    _RecordingRunner.status = "FAILED"
    failed_rc = mod.main(
        ["--snapshot-date", "2026-08-18", "--runs-root", str(tmp_path / "runs")],
        pipeline_runner_factory=_RecordingRunner,
        stage_registry_loader=lambda: stages,
    )
    assert failed_rc == 1


def test_wrapper_fails_when_ess_stage_missing(tmp_path: Path) -> None:
    mod = _load_wrapper_module()
    stages = (StageDefinition("normalization", "placeholder"),)

    rc = mod.main(
        ["--snapshot-date", "2026-08-18", "--runs-root", str(tmp_path / "runs")],
        pipeline_runner_factory=_RecordingRunner,
        stage_registry_loader=lambda: stages,
    )

    assert rc == 2


def test_wrapper_source_does_not_reference_portfolio_or_refresh_entrypoints() -> None:
    wrapper_path = Path(__file__).resolve().parents[1] / "scripts" / "_run_intake.py"
    source = wrapper_path.read_text(encoding="utf-8")

    assert "process_incoming_portfolio" not in source
    assert "refresh_signals" not in source
    assert "run_analysis(" not in source
