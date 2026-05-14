from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence

REQUIRED_PHILOSOPHY_DOCS: tuple[str, ...] = (
    "docs/SECURITY_INTELLIGENCE_ARCHITECTURE.md",
    "docs/SDLC_GOVERNANCE.md",
    "docs/WAYPOINT_NAVIGATION.md",
    "docs/BENCHMARK_PHILOSOPHY.md",
    "docs/ESS_INTAKE_PHILOSOPHY.md",
    "docs/SNAPSHOT_LINEAGE_PHILOSOPHY.md",
    "docs/CANONICAL_TERMINOLOGY.md",
    "docs/SECURITY_IDENTITY_PHILOSOPHY.md",
    "docs/TEMPORAL_INTEGRITY_PHILOSOPHY.md",
    "docs/PROVIDER_LINEAGE_PHILOSOPHY.md",
    "docs/SNAPSHOT_CONSISTENCY_RULES.md",
    "docs/PERSISTENCE_VERIFICATION_PHILOSOPHY.md",
    "docs/ARCHITECTURE_CONSISTENCY_CHECKLIST.md",
    "docs/OUTCOME_VISUALIZATION_CONTRACT.md",
    "docs/HISTORICAL_MARKET_DATA_PHILOSOPHY.md",
    "docs/REPLAY_RETURN_ENGINE_PHILOSOPHY.md",
)

REQUIRED_GOVERNANCE_ARTIFACTS: tuple[str, ...] = (
    "navigation_state.yaml",
    "master_plan.md",
    "wdd_log.md",
)

CANONICAL_TERMS: tuple[str, ...] = (
    "Snapshot",
    "Run",
    "Manifest",
    "Artifact",
    "Canonical",
    "Provider",
    "Coverage Domain",
    "Benchmark",
    "Benchmark Relative",
    "Historical Truth",
    "Point in Time Intelligence",
    "Lineage",
    "Normalization",
    "Validation",
    "Outcome Window",
    "Derived Value",
    "Authoritative Value",
    "Estimated Value",
    "Immutable",
    "Security Master",
    "Signal Snapshot",
    "Coverage Universe",
)

REQUIRED_TERMINOLOGY_REFERENCES: tuple[str, ...] = (
    "snapshot",
    "lineage",
    "benchmark relative",
    "provider",
    "point in time",
    "immutable",
    "normalization",
    "validation",
)

SNAPSHOT_RULES_REQUIRED: tuple[str, ...] = (
    "snapshot date",
    "run id",
    "provider",
    "source file",
    "coverage domain",
    "benchmark",
    "append only",
    "immutable",
    "fail closed",
)

CONSISTENCY_DOCS: tuple[str, ...] = (
    "docs/SECURITY_INTELLIGENCE_ARCHITECTURE.md",
    "docs/SNAPSHOT_LINEAGE_PHILOSOPHY.md",
    "docs/ESS_INTAKE_PHILOSOPHY.md",
    "docs/CANONICAL_TERMINOLOGY.md",
    "docs/TEMPORAL_INTEGRITY_PHILOSOPHY.md",
    "docs/PROVIDER_LINEAGE_PHILOSOPHY.md",
    "docs/SNAPSHOT_CONSISTENCY_RULES.md",
    "docs/ARCHITECTURE_CONSISTENCY_CHECKLIST.md",
    "docs/OUTCOME_VISUALIZATION_CONTRACT.md",
    "docs/HISTORICAL_MARKET_DATA_PHILOSOPHY.md",
    "docs/REPLAY_RETURN_ENGINE_PHILOSOPHY.md",
)

PRINCIPLE_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "immutable_snapshot": ("immutable", "append only"),
    "benchmark_relative": ("benchmark relative",),
    "provider_lineage": ("provider lineage",),
    "temporal_integrity": ("point in time", "temporal"),
    "fail_closed": ("fail closed",),
    "coverage_domain": ("coverage domain",),
}


def _normalize(text: str) -> str:
    normalized = text.lower()
    for token in ("-", "_", "/", ":", ",", ".", "(", ")"):
        normalized = normalized.replace(token, " ")
    return " ".join(normalized.split())


def _missing_paths(root: Path, rel_paths: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for rel_path in rel_paths:
        if not (root / rel_path).exists():
            missing.append(rel_path)
    return missing


def _read_text(root: Path, rel_path: str) -> str:
    return (root / rel_path).read_text(encoding="utf-8")


def validate_required_documents(root: Path) -> list[str]:
    errors: list[str] = []
    missing = _missing_paths(root, REQUIRED_PHILOSOPHY_DOCS)
    if missing:
        errors.append(
            "Missing required philosophy/foundation docs: " + ", ".join(sorted(missing))
        )
    return errors


def validate_governance_artifacts(root: Path) -> list[str]:
    errors: list[str] = []
    missing = _missing_paths(root, REQUIRED_GOVERNANCE_ARTIFACTS)
    if missing:
        errors.append("Missing required governance artifacts: " + ", ".join(sorted(missing)))
    return errors


def validate_canonical_terminology(root: Path) -> list[str]:
    errors: list[str] = []
    terminology_path = root / "docs/CANONICAL_TERMINOLOGY.md"
    if not terminology_path.exists():
        return ["Missing required terminology document: docs/CANONICAL_TERMINOLOGY.md"]

    headings = []
    for line in terminology_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            headings.append(_normalize(line[3:]))

    required = {_normalize(term) for term in CANONICAL_TERMS}
    found = set(headings)
    missing_terms = sorted(required.difference(found))

    if missing_terms:
        errors.append("Missing canonical terms: " + ", ".join(missing_terms))

    return errors


def validate_snapshot_consistency_rules(root: Path) -> list[str]:
    rules_path = root / "docs/SNAPSHOT_CONSISTENCY_RULES.md"
    if not rules_path.exists():
        return ["Missing snapshot consistency rules doc: docs/SNAPSHOT_CONSISTENCY_RULES.md"]

    text = _normalize(rules_path.read_text(encoding="utf-8"))
    missing_tokens: list[str] = []
    for token in SNAPSHOT_RULES_REQUIRED:
        if _normalize(token) not in text:
            missing_tokens.append(token)

    if missing_tokens:
        return [
            "Snapshot consistency rules missing required tokens: "
            + ", ".join(sorted(missing_tokens))
        ]
    return []


def validate_terminology_references(root: Path) -> list[str]:
    errors: list[str] = []
    corpus_parts: list[str] = []

    for rel_path in CONSISTENCY_DOCS:
        path = root / rel_path
        if path.exists() and rel_path != "docs/CANONICAL_TERMINOLOGY.md":
            corpus_parts.append(path.read_text(encoding="utf-8"))

    corpus = _normalize("\n".join(corpus_parts))
    missing_refs: list[str] = []
    for token in REQUIRED_TERMINOLOGY_REFERENCES:
        if _normalize(token) not in corpus:
            missing_refs.append(token)

    if missing_refs:
        errors.append(
            "Required terminology references not found across architecture docs: "
            + ", ".join(sorted(missing_refs))
        )

    return errors


def validate_principle_consistency(root: Path) -> list[str]:
    errors: list[str] = []

    doc_texts: Dict[str, str] = {}
    for rel_path in CONSISTENCY_DOCS:
        path = root / rel_path
        if path.exists():
            doc_texts[rel_path] = _normalize(path.read_text(encoding="utf-8"))

    for principle, keywords in PRINCIPLE_KEYWORDS.items():
        mention_count = 0
        for text in doc_texts.values():
            if any(_normalize(keyword) in text for keyword in keywords):
                mention_count += 1
        if mention_count < 2:
            errors.append(
                f"Principle representation is too sparse for {principle}: expected mentions in at least 2 docs, found {mention_count}."
            )

    return errors


def run_validation(root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_required_documents(root))
    errors.extend(validate_governance_artifacts(root))
    errors.extend(validate_canonical_terminology(root))
    errors.extend(validate_snapshot_consistency_rules(root))
    errors.extend(validate_terminology_references(root))
    errors.extend(validate_principle_consistency(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate architecture consistency artifacts.")
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Repository root to validate (default: current directory).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors = run_validation(root)

    if errors:
        print("ARCHITECTURE CONSISTENCY: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("ARCHITECTURE CONSISTENCY: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
