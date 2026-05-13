"""Pipeline observability and execution scaffolding package."""

from .execution_summary import render_execution_summary
from .pipeline_runner import PipelineRunner
from .stage_registry import (
    StageContext,
    StageDefinition,
    StageExecutionOutput,
    default_stage_registry,
)

__all__ = [
    "PipelineRunner",
    "StageContext",
    "StageDefinition",
    "StageExecutionOutput",
    "default_stage_registry",
    "render_execution_summary",
]