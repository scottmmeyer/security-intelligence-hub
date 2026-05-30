#!/usr/bin/env python3
"""Phase 6.4C — Generate taxonomy_reconciliation_report.md for a given run_id.

Usage:
    python scripts/_generate_taxonomy_report.py [run_id]

If run_id is omitted, uses the most recent analysis run.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.portfolio.reconciliation import _rc12_taxonomy_normalization
from src.portfolio.taxonomy import (
    CANONICAL_NODES,
    DISPLAY_LABELS,
    _ALIAS_MAP,
    find_aliases_in_collection,
    normalize_node_key,
)

_INGESTION_ROOT = _REPO_ROOT / "data" / "portfolio_ingestion"
_OUTPUT_PATH = _REPO_ROOT / "taxonomy_reconciliation_report.md"


def _latest_run_id() -> str | None:
    runs_dir = _INGESTION_ROOT / "analysis_runs"
    if not runs_dir.exists():
        return None
    dirs = sorted(
        (d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("PAR-")),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return dirs[0].name if dirs else None


def _badge(status: str) -> str:
    return {"PASS": "✅ PASS", "WARN": "⚠️ WARN", "FAIL": "❌ FAIL"}.get(status, status)


def _render(run_id: str, alignment: list, run_meta: dict) -> str:
    rc12 = _rc12_taxonomy_normalization(alignment)

    # Collect all node keys from alignment
    all_node_keys = sorted(set(
        r.get("node_key", "") for r in alignment if r.get("node_key")
    ))

    # Classify each node
    canonical_keys = sorted(n for n in all_node_keys if n in CANONICAL_NODES)
    alias_keys = [(k, c) for k, c in find_aliases_in_collection(all_node_keys) if c is not None]
    unknown_keys = [k for k, c in find_aliases_in_collection(all_node_keys) if c is None]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    snap_date = run_meta.get("snapshot_date", "?")

    lines: list[str] = []
    lines.append(f"# Taxonomy Reconciliation Report")
    lines.append(f"")
    lines.append(f"**Run ID:** `{run_id}`  ")
    lines.append(f"**Snapshot Date:** {snap_date}  ")
    lines.append(f"**Generated:** {generated_at}  ")
    lines.append(f"**RC-12 Status:** {_badge(rc12.status)}  ")
    lines.append(f"")

    # ── Executive Summary ──────────────────────────────────────────────────────
    lines.append(f"## Executive Summary")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total alignment node keys | {len(all_node_keys)} |")
    lines.append(f"| Canonical (defined in allocation_dimensions.yaml) | {len(canonical_keys)} |")
    lines.append(f"| Structurally extended (generated, not in YAML) | {len(unknown_keys)} |")
    lines.append(f"| Alias violations (non-canonical form) | {len(alias_keys)} |")
    lines.append(f"| Canonical taxonomy registry size | {len(CANONICAL_NODES)} |")
    lines.append(f"")

    if rc12.status == "PASS":
        lines.append(f"> ✅ All alignment node keys use canonical dot-notation taxonomy.")
    elif rc12.status == "WARN":
        lines.append(f"> ⚠️ {len(unknown_keys)} alignment node key(s) are structurally valid but not explicitly defined in `allocation_dimensions.yaml`. No alias collisions found.")
    else:
        lines.append(f"> ❌ {len(alias_keys)} alias collision(s) detected. Alignment output contains non-canonical node key forms.")
    lines.append(f"")

    # ── Section 1: Node Inventory ──────────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 1 — Node Inventory")
    lines.append(f"")
    lines.append(f"All node keys present in alignment output, classified against the canonical taxonomy.")
    lines.append(f"")
    lines.append(f"| Node Key | Status | Display Label | Sources |")
    lines.append(f"|----------|--------|---------------|---------|")

    for key in all_node_keys:
        if key in CANONICAL_NODES:
            status_icon = "✅ Canonical"
            label = DISPLAY_LABELS.get(key, key)
            sources = "allocation_dimensions.yaml"
        else:
            canonical = normalize_node_key(key)
            if canonical != key.upper() and canonical in CANONICAL_NODES:
                status_icon = "❌ Alias"
                label = DISPLAY_LABELS.get(canonical, canonical)
                sources = f"alias of `{canonical}`"
            else:
                status_icon = "⚠️ Extended"
                # Infer label from parent
                parts = key.split(".")
                label = " → ".join(p.replace("_", " ").title() for p in parts)
                sources = "alignment engine (dynamic)"
        lines.append(f"| `{key}` | {status_icon} | {label} | {sources} |")

    lines.append(f"")

    # ── Section 2: Duplicate Detection ────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 2 — Duplicate / Alias Detection")
    lines.append(f"")

    # Report the pre-fix aliases that were found and fixed
    lines.append(f"### Known Alias Patterns (Phase 6.4C)")
    lines.append(f"")
    lines.append(f"The following alias collisions were identified and resolved by normalizing sector")
    lines.append(f"field values in `exposure_decomposition.py` (Phase 6.4C fix):")
    lines.append(f"")
    lines.append(f"| Canonical Node | Alias Form | Locations Found | Resolution |")
    lines.append(f"|----------------|-----------|-----------------|------------|")
    lines.append(f"| `FIXED_INCOME` | `FIXED INCOME` | Non-EQUITIES sector block in `exposure_decomposition.py` | ✅ Fixed — normalize_node_key() call added |")
    lines.append(f"| `DIGITAL` | `DIGITAL ASSETS` | Non-EQUITIES sector block in `exposure_decomposition.py` | ✅ Fixed — normalize_node_key() call added |")
    lines.append(f"")

    if alias_keys:
        lines.append(f"### Active Alias Violations (requires attention)")
        lines.append(f"")
        lines.append(f"| Alias | Canonical | Root Cause |")
        lines.append(f"|-------|-----------|------------|")
        for alias, canonical in alias_keys:
            lines.append(f"| `{alias}` | `{canonical}` | Alias key produced in alignment output |")
        lines.append(f"")
    else:
        lines.append(f"### Active Alias Violations")
        lines.append(f"")
        lines.append(f"> ✅ No active alias violations in this alignment output.")
        lines.append(f"")

    if unknown_keys:
        lines.append(f"### Structurally Extended Nodes (not in allocation_dimensions.yaml)")
        lines.append(f"")
        lines.append(f"These nodes follow the canonical dot-notation pattern and are generated by the")
        lines.append(f"alignment engine, but are not explicitly defined in `allocation_dimensions.yaml`.")
        lines.append(f"They represent a taxonomy coverage gap — consider adding them to the YAML.")
        lines.append(f"")
        lines.append(f"| Node Key | Parent in YAML | Suggested YAML Addition |")
        lines.append(f"|----------|---------------|-------------------------|")
        for key in unknown_keys:
            parts = key.split(".")
            parent = ".".join(parts[:-1]) if len(parts) > 1 else "ROOT"
            parent_in_yaml = "✅" if parent in CANONICAL_NODES else "⚠️ Also missing"
            lines.append(f"| `{key}` | `{parent}` ({parent_in_yaml}) | Add under `{parent}` children |")
        lines.append(f"")

    # ── Section 3: Canonical Taxonomy Registry ─────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 3 — Canonical Taxonomy Registry")
    lines.append(f"")
    lines.append(f"Source: `src/portfolio/taxonomy.py` (loaded from `config/allocation_dimensions.yaml`)")
    lines.append(f"")
    lines.append(f"**{len(CANONICAL_NODES)} canonical node keys registered.**")
    lines.append(f"")
    lines.append(f"| Node Key | Label | Hierarchy Level |")
    lines.append(f"|----------|-------|-----------------|")
    for key in sorted(CANONICAL_NODES):
        label = DISPLAY_LABELS.get(key, key)
        level = key.count(".") + 1
        lines.append(f"| `{key}` | {label} | L{level} |")
    lines.append(f"")

    lines.append(f"### Alias Map Summary")
    lines.append(f"")
    lines.append(f"**{len(_ALIAS_MAP)} alias entries registered.** Selected entries:")
    lines.append(f"")
    lines.append(f"| Alias (uppercased) | Canonical |")
    lines.append(f"|-------------------|-----------|")
    for alias, canonical in sorted(_ALIAS_MAP.items())[:20]:
        lines.append(f"| `{alias}` | `{canonical}` |")
    if len(_ALIAS_MAP) > 20:
        lines.append(f"| *...{len(_ALIAS_MAP) - 20} more* | |")
    lines.append(f"")

    # ── Section 4: RC-12 Check ────────────────────────────────────────────────
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Section 4 — RC-12: Taxonomy Normalization Check")
    lines.append(f"")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Check ID | RC-12 |")
    lines.append(f"| Status | {_badge(rc12.status)} |")
    lines.append(f"| Expected | {rc12.expected} |")
    lines.append(f"| Actual | {rc12.actual} |")
    lines.append(f"| Variance | {rc12.variance} |")
    lines.append(f"| Tolerance | {rc12.tolerance} |")
    lines.append(f"| Detail | {rc12.detail[:300]} |")
    lines.append(f"")

    if rc12.sub_checks:
        lines.append(f"### RC-12 Sub-Checks")
        lines.append(f"")
        lines.append(f"| Node Key | Root Cause | Status |")
        lines.append(f"|----------|------------|--------|")
        for sc in rc12.sub_checks[:20]:
            node = sc.get("node_key", "?")
            cause = sc.get("root_cause", "?")
            st = _badge(sc.get("status", "?"))
            lines.append(f"| `{node}` | {cause} | {st} |")
        if len(rc12.sub_checks) > 20:
            lines.append(f"| *...{len(rc12.sub_checks)-20} more* | | |")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*Report generated by `scripts/_generate_taxonomy_report.py` — Phase 6.4C*")

    return "\n".join(lines)


def main() -> None:
    run_id = sys.argv[1] if len(sys.argv) > 1 else _latest_run_id()
    if not run_id:
        print("No analysis runs found.", file=sys.stderr)
        sys.exit(1)

    run_dir = _INGESTION_ROOT / "analysis_runs" / run_id
    if not run_dir.exists():
        print(f"Run not found: {run_id}", file=sys.stderr)
        sys.exit(1)

    alignment = list(csv.DictReader(open(run_dir / "alignment.csv")))
    run_meta = json.loads((run_dir / "run_metadata.json").read_text()) if (run_dir / "run_metadata.json").exists() else {}

    md = _render(run_id, alignment, run_meta)
    _OUTPUT_PATH.write_text(md)
    print(f"Report written to: {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
