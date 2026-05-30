"""Classification module: security type policy, geography resolution, and benchmark assignment.

Phase 1 — Benchmark & Classification Integrity Framework.
"""
from src.classification.security_type_policy import (
    SecurityTypeInfo,
    SecurityTypePolicy,
    load_security_type_policy,
)
from src.classification.geography_resolver import (
    GeographyResolution,
    load_adr_domicile_policy,
    load_geography_overrides,
    resolve_geography,
)
from src.classification.benchmark_assignment_engine import (
    BenchmarkAssignment,
    assign_benchmarks,
)
from src.classification.classification_validators import (
    ClassificationFinding,
    FindingLevel,
    validate_universe_classifications,
)

__all__ = [
    # Security type
    "SecurityTypeInfo",
    "SecurityTypePolicy",
    "load_security_type_policy",
    # Geography
    "GeographyResolution",
    "load_adr_domicile_policy",
    "load_geography_overrides",
    "resolve_geography",
    # Benchmark assignment
    "BenchmarkAssignment",
    "assign_benchmarks",
    # Validators
    "ClassificationFinding",
    "FindingLevel",
    "validate_universe_classifications",
]
