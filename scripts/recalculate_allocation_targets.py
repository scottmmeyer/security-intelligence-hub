#!/usr/bin/env python3
"""
Allocation Intelligence Recalculation CLI

Usage:
    PYTHONPATH=. .venv/bin/python scripts/recalculate_allocation_targets.py
    PYTHONPATH=. .venv/bin/python scripts/recalculate_allocation_targets.py --commit

Without --commit:
  - Loads policy, dimensions, methodology
  - Extracts seed targets (first run) OR loads current targets
  - Extracts replay evidence from replay_inputs.csv + replay_performance_series.csv
  - Proposes recalculation deltas
  - Runs all 8 validators
  - Prints change_summary and validator results
  - Writes to data/allocation/proposed/ (no current/ changes)

With --commit:
  - Does everything above, then publishes to data/current/
  - Saves snapshot to data/allocation/recalculation_snapshots/
  - Updates data/allocation/manifest.json
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is importable when run from any directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.allocation.dimensions_loader import load_dimensions
from src.allocation.methodology_loader import load_methodology, extract_seed_targets
from src.allocation.recalculation_engine import propose_recalculation
from src.allocation.replay_integration import load_replay_evidence
from src.allocation.structural_policy import load_structural_policy
from src.allocation.tactical_overlay import (
    load_active_overlays,
    expire_stale_overlays,
    compute_effective_allocations,
)
from src.allocation.validators import run_all_validators
from src.history.allocation_manager import (
    AllocationStoragePaths,
    load_all_snapshots,
    load_latest_targets,
    publish_proposed_targets,
    save_proposed_targets,
)


def _print_header(title: str) -> None:
    width = 72
    print("\n" + "─" * width)
    print(f"  {title}")
    print("─" * width)


def _print_validator_results(validation_results: dict[str, list[str]]) -> None:
    _print_header("Validator Results")
    all_passed = True
    for name, errors in validation_results.items():
        if errors:
            all_passed = False
            print(f"  ✗ {name}:")
            for err in errors:
                print(f"      {err}")
        else:
            print(f"  ✓ {name}: PASS")
    if all_passed:
        print("\n  All 8 validators passed.")
    else:
        print("\n  *** One or more validators failed — review before committing. ***")
    return all_passed


def _print_change_summary(snapshot, targets) -> None:
    _print_header("Change Summary")
    for line in snapshot.change_summary:
        print(f"  {line}")
    print(f"\n  {snapshot.unchanged_summary}")
    print(f"  Triggered by: {snapshot.triggered_by}")
    print(f"  Recalculation ID: {snapshot.recalculation_id}")


def _targets_from_csv_rows(rows: list[dict]):
    """Reconstruct StrategicAllocationTarget list from CSV rows for --propose mode."""
    from src.allocation.models import StrategicAllocationTarget

    targets = []
    for row in rows:
        try:
            targets.append(
                StrategicAllocationTarget(
                    target_id=row["target_id"],
                    snapshot_date=row["snapshot_date"],
                    recalculation_id=row["recalculation_id"],
                    node_key=row["node_key"],
                    node_label=row["node_label"],
                    parent_key=row["parent_key"] or None,
                    asset_class=row["asset_class"],
                    geography=row["geography"] or None,
                    market_structure=row["market_structure"] or None,
                    mega_subtier=row["mega_subtier"] or None,
                    hierarchy_depth=int(row["hierarchy_depth"]),
                    target_pct_of_parent=float(row["target_pct_of_parent"]),
                    target_pct_of_total=float(row["target_pct_of_total"]),
                    prior_target_pct_of_total=float(row["prior_target_pct_of_total"]) if row.get("prior_target_pct_of_total") else None,
                    delta_pct=float(row["delta_pct"]) if row.get("delta_pct") else None,
                    confidence_score=float(row["confidence_score"]),
                    evidence_summary=row["evidence_summary"],
                    evidence_ids=tuple(x.strip() for x in row.get("evidence_ids", "").split("|") if x.strip()),
                    methodology_basis_ref=row["methodology_basis_ref"],
                    policy_bounded=row.get("policy_bounded", "False").upper() == "TRUE",
                )
            )
        except (KeyError, ValueError) as exc:
            print(f"  Warning: skipping malformed row for {row.get('node_key', '?')}: {exc}", file=sys.stderr)

    return targets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SIH Allocation Intelligence Recalculation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Publish proposed targets to data/current/ (default: propose only)",
    )
    parser.add_argument(
        "--policy", default="config/allocation_policy.yaml", metavar="PATH",
        help="Path to allocation_policy.yaml (default: config/allocation_policy.yaml)",
    )
    parser.add_argument(
        "--dimensions", default="config/allocation_dimensions.yaml", metavar="PATH",
        help="Path to allocation_dimensions.yaml",
    )
    parser.add_argument(
        "--methodology", default="config/allocation_methodology.yaml", metavar="PATH",
        help="Path to allocation_methodology.yaml",
    )
    parser.add_argument(
        "--force-seed", action="store_true",
        help="Force re-seed from methodology even if current targets exist",
    )
    args = parser.parse_args()

    paths = AllocationStoragePaths()
    paths.ensure_dirs()

    print("\n══════════════════════════════════════════════════════════════════════")
    print("  SIH Allocation Intelligence — Recalculation Engine")
    print("══════════════════════════════════════════════════════════════════════")

    # ── Step 1: Load config ─────────────────────────────────────────────────
    _print_header("Loading Configuration")
    try:
        policy = load_structural_policy(args.policy)
        print(f"  Policy:      {policy.policy_id} v{policy.policy_version} ({policy.effective_date})")
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR loading policy: {exc}", file=sys.stderr)
        return 1

    try:
        all_nodes = load_dimensions(args.dimensions)
        print(f"  Dimensions:  {len(all_nodes)} hierarchy nodes loaded")
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR loading dimensions: {exc}", file=sys.stderr)
        return 1

    try:
        methodology = load_methodology(args.methodology)
        print(f"  Methodology: {len(methodology)} node rationale entries loaded")
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR loading methodology: {exc}", file=sys.stderr)
        return 1

    # ── Step 2: Load or seed targets ─────────────────────────────────────────
    _print_header("Targets")
    existing_rows = load_latest_targets(paths) if not args.force_seed else []

    if existing_rows:
        print(f"  Found {len(existing_rows)} existing targets in data/current/")
        current_targets = _targets_from_csv_rows(existing_rows)
        prior_recalculation_id = existing_rows[0].get("recalculation_id") if existing_rows else None
        is_seed = False
    else:
        print("  No existing targets found — seeding from methodology YAML.")
        try:
            seed_snapshot, current_targets, seed_evidence = extract_seed_targets(
                methodology, all_nodes, policy
            )
        except ValueError as exc:
            print(f"  ERROR during seed extraction: {exc}", file=sys.stderr)
            return 1
        prior_recalculation_id = None
        is_seed = True
        print(f"  Seeded {len(current_targets)} targets from config/allocation_methodology.yaml")

    # ── Step 3: Load replay evidence ──────────────────────────────────────────
    _print_header("Replay Evidence")
    evidence_records = load_replay_evidence(all_nodes)
    replay_count = sum(1 for e in evidence_records if e.evidence_type != "METHODOLOGY_BASELINE")
    baseline_count = sum(1 for e in evidence_records if e.evidence_type == "METHODOLOGY_BASELINE")
    print(f"  Evidence records: {len(evidence_records)} total ({replay_count} replay, {baseline_count} methodology baseline)")

    # ── Step 4: Seed path → publish directly, skip recalculation ────────────
    if is_seed:
        snapshot = seed_snapshot
        proposed_targets = current_targets
        evidence = seed_evidence
    else:
        # ── Step 4b: Propose recalculation ─────────────────────────────────
        snapshot, proposed_targets = propose_recalculation(
            current_targets=current_targets,
            evidence_records=evidence_records,
            all_nodes=all_nodes,
            policy=policy,
            prior_recalculation_id=prior_recalculation_id,
        )
        evidence = evidence_records

    # ── Step 5: Load overlays and compute recommendations ─────────────────
    raw_overlays = load_active_overlays(paths.current_overlays)
    active_overlays = expire_stale_overlays(raw_overlays)
    recommendations = compute_effective_allocations(
        proposed_targets, active_overlays, policy
    )

    # ── Step 6: Run validators ────────────────────────────────────────────
    validation_results = run_all_validators(
        targets=proposed_targets,
        snapshot=snapshot,
        evidence_records=evidence,
        overlays=active_overlays,
        all_nodes=all_nodes,
        policy=policy,
    )

    # ── Step 7: Print results ─────────────────────────────────────────────
    _print_change_summary(snapshot, proposed_targets)
    all_passed = _print_validator_results(validation_results)

    # Print allocation table
    _print_header("Proposed Allocation Summary")
    l1_targets = sorted(
        [t for t in proposed_targets if t.hierarchy_depth == 1],
        key=lambda t: -t.target_pct_of_total,
    )
    for t in l1_targets:
        bar = "█" * int(t.target_pct_of_total / 2)
        print(f"  {t.asset_class:<18} {t.target_pct_of_total:6.2f}%  {bar}")

    # ── Step 8: Save proposed or commit ──────────────────────────────────
    save_proposed_targets(proposed_targets, snapshot, recommendations, paths)
    print(f"\n  Proposed targets written to: data/allocation/proposed/")

    if args.commit:
        if not all_passed:
            print(
                "\n  *** Commit blocked: one or more validators failed. "
                "Fix issues and retry. ***",
                file=sys.stderr,
            )
            return 1
        _print_header("Committing to data/current/")
        publish_proposed_targets(proposed_targets, snapshot, recommendations, evidence, paths)
        print(f"  Published {len(proposed_targets)} targets to data/current/strategic_allocation_targets.csv")
        print(f"  Snapshot saved: data/allocation/recalculation_snapshots/{snapshot.recalculation_id}.json")
        print(f"  Manifest updated: data/allocation/manifest.json")
        print(f"\n  ✓ Commit complete — Recalculation ID: {snapshot.recalculation_id}")
    else:
        print("\n  Run with --commit to publish to data/current/")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
