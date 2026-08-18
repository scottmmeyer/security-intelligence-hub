#!/usr/bin/env python3
"""Operator wrapper for ESS intake stage execution.

This wrapper delegates ESS intake to the registered pipeline stage contract.
It does not implement provider normalization, scoring, or portfolio analysis.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.models.pipeline_models import PipelineStatus
from src.pipeline.execution_summary import render_execution_summary
from src.pipeline.pipeline_runner import PipelineRunner
from src.pipeline.stage_registry import StageDefinition, default_stage_registry

_RUN_ID_PATTERN = re.compile(r"^RUN-REAL-ESS-(\d{8})-(\d{3})$")


def _parse_snapshot_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid --snapshot-date '{value}'. Expected YYYY-MM-DD.") from exc


def _build_run_id(snapshot_date: date, runs_root: Path) -> str:
    """Build RUN-REAL-ESS run_id following existing historical naming."""
    date_token = snapshot_date.strftime("%Y%m%d")
    max_suffix = 0

    manifests_dir = runs_root / "manifests"
    if manifests_dir.exists():
        for path in manifests_dir.glob(f"RUN-REAL-ESS-{date_token}-*_manifest.json"):
            stem = path.name.removesuffix("_manifest.json")
            match = _RUN_ID_PATTERN.fullmatch(stem)
            if match and match.group(1) == date_token:
                max_suffix = max(max_suffix, int(match.group(2)))

    return f"RUN-REAL-ESS-{date_token}-{max_suffix + 1:03d}"


def _select_ess_stage(
    registry_loader: Callable[[], tuple[StageDefinition, ...]] = default_stage_registry,
) -> StageDefinition:
    for stage in registry_loader():
        if stage.stage_name == "ess_intake":
            if stage.executor is None:
                raise ValueError("Registered ess_intake stage has no executor.")
            return stage
    raise ValueError("No registered ess_intake stage found in default stage registry.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ESS intake via registered pipeline stage wrapper.")
    parser.add_argument(
        "--snapshot-date",
        default=date.today().isoformat(),
        help="Snapshot date for ESS intake context (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional explicit run id. If omitted, auto-generates RUN-REAL-ESS-YYYYMMDD-###.",
    )
    parser.add_argument(
        "--runs-root",
        default="runs",
        help="Runs directory root for manifests/logs.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print full deterministic execution summary output.",
    )
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    pipeline_runner_factory: Callable[..., PipelineRunner] = PipelineRunner,
    stage_registry_loader: Callable[[], tuple[StageDefinition, ...]] = default_stage_registry,
) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        snapshot_date = _parse_snapshot_date(str(args.snapshot_date))
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    runs_root = Path(args.runs_root)

    try:
        ess_stage = _select_ess_stage(stage_registry_loader)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    run_id = str(args.run_id).strip() or _build_run_id(snapshot_date, runs_root)
    print("ESS intake operator wrapper")
    print(f"repo_root={_REPO_ROOT}")
    print(f"run_id={run_id}")
    print(f"snapshot_date={snapshot_date.isoformat()}")
    print(f"stage={ess_stage.stage_name}")

    runner = pipeline_runner_factory(runs_root=runs_root, stages=(ess_stage,))

    try:
        manifest = runner.run(run_id=run_id, snapshot_date=snapshot_date)
    except Exception as exc:
        print(f"ERROR: ESS intake execution failed: {exc}")
        return 1

    print(f"overall_status={manifest.overall_status}")
    print(f"warnings={len(manifest.warnings)} errors={len(manifest.errors)}")

    if args.summary:
        print("\n" + render_execution_summary(manifest))

    if manifest.overall_status in {PipelineStatus.FAILED.value, PipelineStatus.BLOCKED.value}:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
