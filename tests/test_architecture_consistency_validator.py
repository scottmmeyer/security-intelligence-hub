from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_validator_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "validate_architecture_consistency.py"
    spec = importlib.util.spec_from_file_location("architecture_validator", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _bootstrap_valid_repo(tmp_path: Path, module) -> Path:
    root = tmp_path / "repo"

    full_doc_set = set(module.REQUIRED_PHILOSOPHY_DOCS).union(module.REQUIRED_GOVERNANCE_ARTIFACTS)
    for rel_path in sorted(full_doc_set):
        path = root / rel_path

        if rel_path == "docs/CANONICAL_TERMINOLOGY.md":
            sections = ["# Canonical Terminology"]
            for term in module.CANONICAL_TERMS:
                sections.append(f"\n## {term}\nDeterministic definition.")
            content = "\n".join(sections)
        elif rel_path == "docs/SNAPSHOT_CONSISTENCY_RULES.md":
            content = "\n".join(
                [
                    "# Snapshot Consistency Rules",
                    "snapshot_date required.",
                    "run_id propagation required.",
                    "provider propagation required.",
                    "source_file propagation required.",
                    "coverage_domain consistency required.",
                    "benchmark context consistency required.",
                    "append-only semantics required.",
                    "immutable publication required.",
                    "fail-closed validation required.",
                ]
            )
        elif rel_path.startswith("docs/"):
            content = (
                "Immutable append-only benchmark-relative provider lineage point-in-time "
                "coverage domain fail-closed normalization validation snapshot run artifact manifest."
            )
        else:
            content = "governance artifact"

        _write(path, content)

    return root


def test_architecture_validator_passes_for_complete_foundation(tmp_path: Path) -> None:
    module = _load_validator_module()
    root = _bootstrap_valid_repo(tmp_path, module)

    errors = module.run_validation(root)

    assert errors == []


def test_required_document_presence_detection(tmp_path: Path) -> None:
    module = _load_validator_module()
    root = _bootstrap_valid_repo(tmp_path, module)

    (root / "docs" / "PROVIDER_LINEAGE_PHILOSOPHY.md").unlink()
    errors = module.run_validation(root)

    assert any("Missing required philosophy/foundation docs" in err for err in errors)


def test_terminology_integrity_detection(tmp_path: Path) -> None:
    module = _load_validator_module()
    root = _bootstrap_valid_repo(tmp_path, module)

    _write(root / "docs" / "CANONICAL_TERMINOLOGY.md", "# Canonical Terminology\n## Snapshot\nOnly one term.")
    errors = module.run_validation(root)

    assert any("Missing canonical terms" in err for err in errors)


def test_snapshot_consistency_rule_validation(tmp_path: Path) -> None:
    module = _load_validator_module()
    root = _bootstrap_valid_repo(tmp_path, module)

    _write(
        root / "docs" / "SNAPSHOT_CONSISTENCY_RULES.md",
        "# Snapshot Consistency Rules\nOnly snapshot_date is described.",
    )
    errors = module.run_validation(root)

    assert any("Snapshot consistency rules missing required tokens" in err for err in errors)


def test_required_governance_artifact_detection(tmp_path: Path) -> None:
    module = _load_validator_module()
    root = _bootstrap_valid_repo(tmp_path, module)

    (root / "master_plan.md").unlink()
    errors = module.run_validation(root)

    assert any("Missing required governance artifacts" in err for err in errors)
