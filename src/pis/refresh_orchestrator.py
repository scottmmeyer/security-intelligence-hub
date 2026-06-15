"""PIS derived artifact refresh orchestrator (PIS-005).

Implements deterministic, lock-protected refresh chain:

    Governance (read-only evaluation)
        → Canonical (canonical_daily_snapshots.csv)
            → Change Detection (change_records.csv / change_summary.csv)
                → Lineage (lineage_records.csv / lineage_summary.csv)
                    → Attribution (attribution_records.csv / attribution_summary.csv)
                        → Benchmark Attribution (benchmark_return_series.csv +
                           recommendation_benchmark_records.csv +
                           source_benchmark_summary.csv)

Orchestration contract:
  - Each stage only runs if its upstream freshness requires it.
  - Execution order is deterministic and cannot be reordered.
  - A single lock prevents concurrent refresh races.
  - No business logic is changed; only orchestration is added.
  - ``dry_run=True`` reports what would run without writing files.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from .artifact_freshness import (
    _ATTRIBUTION_SUMMARY,
    _BENCHMARK_SERIES,
    _CANONICAL_CSV,
    _CHANGE_RECORDS,
    _CHANGE_SUMMARY,
    _LINEAGE_RECORDS,
    _LINEAGE_SUMMARY,
    _SNAPSHOT_INDEX,
    artifact_freshness_report,
    attribution_is_stale,
    benchmark_is_stale,
    canonical_is_stale,
    change_is_stale,
    lineage_is_stale,
)
from .benchmark_attribution import (
    DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    BenchmarkAttributionConfig,
    BenchmarkPriceProvider,
    compute_benchmark_recommendation_attribution,
    compute_benchmark_return_series,
)
from .canonical_daily import DEFAULT_GOVERNANCE_CONFIG, refresh_canonical_daily
from .change_detection import compute_all_snapshot_changes
from .governance import SnapshotGovernanceConfig
from .performance_attribution import compute_performance_attribution
from .recommendation_lineage import compute_recommendation_lineage


# Single lock for the entire PIS refresh pipeline.
# Using threading.Lock (not RLock) so reentrancy is detected rather than silently
# allowed, which would produce double-writes.
_ORCHESTRATION_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def refresh_derived_artifacts(
    *,
    repo_root: str | Path = ".",
    index_path: str | Path = _SNAPSHOT_INDEX,
    canonical_path: str | Path = _CANONICAL_CSV,
    changes_root: str | Path = "data/history/pis/changes",
    lineage_root: str | Path = "data/history/pis/lineage",
    attribution_root: str | Path = "data/history/pis/attribution",
    benchmark_root: str | Path = "data/history/pis/benchmark_attribution",
    governance_config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
    benchmark_config: BenchmarkAttributionConfig = DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider: BenchmarkPriceProvider | None = None,
    allow_online_fallback: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    """Execute the deterministic PIS derived-artifact refresh chain.

    Each stage only runs if its upstream freshness requires it.  The entire
    chain is protected by ``_ORCHESTRATION_LOCK`` so concurrent callers
    (e.g. two simultaneous API calls) queue rather than race.

    Parameters
    ----------
    repo_root:
        Repository root used by change detection to resolve position file paths.
    index_path:
        Path to pis_snapshot_index.csv (governance source of truth).
    canonical_path:
        Path to canonical_daily_snapshots.csv.
    changes_root:
        Directory containing change_records.csv and change_summary.csv.
    lineage_root:
        Directory containing lineage_records.csv and lineage_summary.csv.
    attribution_root:
        Directory containing attribution_records.csv and attribution_summary.csv.
    benchmark_root:
        Directory containing benchmark_return_series.csv and related files.
    governance_config:
        Governance threshold config (value_pass_max, value_reject_gt, etc.).
    benchmark_config:
        Benchmark symbol and alignment policy config.
    price_provider:
        Optional price provider override for benchmark computation.
    allow_online_fallback:
        Whether benchmark computation may fetch prices from the network.
    dry_run:
        If True, reports what would run without writing any files.

    Returns
    -------
    dict with keys:
        refreshed  – list of stage names that were (or would be) recomputed.
        skipped    – list of stage names that were already current.
        dry_run    – bool echo of the input flag.
        started_at – ISO timestamp when the refresh began.
        completed_at – ISO timestamp when the refresh completed.
        freshness  – artifact_freshness_report() output after the run.
    """
    with _ORCHESTRATION_LOCK:
        return _execute_refresh_chain(
            repo_root=Path(repo_root),
            index_path=Path(index_path),
            canonical_path=Path(canonical_path),
            changes_root=Path(changes_root),
            lineage_root=Path(lineage_root),
            attribution_root=Path(attribution_root),
            benchmark_root=Path(benchmark_root),
            governance_config=governance_config,
            benchmark_config=benchmark_config,
            price_provider=price_provider,
            allow_online_fallback=allow_online_fallback,
            dry_run=dry_run,
        )


# ---------------------------------------------------------------------------
# Internal chain logic
# ---------------------------------------------------------------------------

def _execute_refresh_chain(
    *,
    repo_root: Path,
    index_path: Path,
    canonical_path: Path,
    changes_root: Path,
    lineage_root: Path,
    attribution_root: Path,
    benchmark_root: Path,
    governance_config: SnapshotGovernanceConfig,
    benchmark_config: BenchmarkAttributionConfig,
    price_provider: BenchmarkPriceProvider | None,
    allow_online_fallback: bool,
    dry_run: bool,
) -> dict[str, object]:
    started_at = datetime.now(timezone.utc).isoformat()
    refreshed: list[str] = []
    skipped: list[str] = []

    change_summary_path = changes_root / "change_summary.csv"
    change_records_path = changes_root / "change_records.csv"
    lineage_summary_path = lineage_root / "lineage_summary.csv"
    lineage_records_path = lineage_root / "lineage_records.csv"
    attribution_summary_path = attribution_root / "attribution_summary.csv"
    attribution_records_path = attribution_root / "attribution_records.csv"
    benchmark_series_path = benchmark_root / "benchmark_return_series.csv"
    benchmark_rec_path = benchmark_root / "recommendation_benchmark_records.csv"
    benchmark_source_path = benchmark_root / "source_benchmark_summary.csv"

    # ------------------------------------------------------------------
    # Step 1 – Canonical
    # Rule: governance_latest_PASS > canonical_latest → rebuild
    # ------------------------------------------------------------------
    if canonical_is_stale(
        index_path=index_path,
        canonical_path=canonical_path,
        config=governance_config,
    ):
        if not dry_run:
            refresh_canonical_daily(
                index_path=index_path,
                output_path=canonical_path,
                config=governance_config,
            )
        refreshed.append("canonical")
    else:
        skipped.append("canonical")

    # ------------------------------------------------------------------
    # Step 2 – Change Detection
    # Rule: canonical_latest > change_latest → recompute
    # Note: compute_all_snapshot_changes also calls canonical_selected_index_rows
    # internally; step 1 ensures canonical is already current before this runs.
    # ------------------------------------------------------------------
    if change_is_stale(
        canonical_path=canonical_path,
        change_summary_path=change_summary_path,
    ):
        if not dry_run:
            compute_all_snapshot_changes(
                index_path=index_path,
                changes_root=changes_root,
                repo_root=repo_root,
            )
        refreshed.append("change_detection")
    else:
        skipped.append("change_detection")

    # ------------------------------------------------------------------
    # Step 3 – Lineage
    # Rule: change_latest > lineage_latest → recompute
    # ------------------------------------------------------------------
    if lineage_is_stale(
        change_summary_path=change_summary_path,
        lineage_summary_path=lineage_summary_path,
    ):
        if not dry_run:
            compute_recommendation_lineage(
                change_records_path=change_records_path,
                change_summary_path=change_summary_path,
                lineage_root=lineage_root,
                repo_root=repo_root,
            )
        refreshed.append("lineage")
    else:
        skipped.append("lineage")

    # ------------------------------------------------------------------
    # Step 4 – Attribution
    # Rule: lineage_latest > attribution_latest → recompute
    # We pass candidates_override=None so attribution reads the freshly
    # written lineage files rather than re-extracting from PARs.
    # ------------------------------------------------------------------
    if attribution_is_stale(
        lineage_summary_path=lineage_summary_path,
        attribution_summary_path=attribution_summary_path,
    ):
        if not dry_run:
            compute_performance_attribution(
                change_records_path=change_records_path,
                change_summary_path=change_summary_path,
                lineage_root=lineage_root,
                attribution_root=attribution_root,
                repo_root=repo_root,
            )
        refreshed.append("attribution")
    else:
        skipped.append("attribution")

    # ------------------------------------------------------------------
    # Step 5 – Benchmark Attribution
    # Rule: attribution_latest > benchmark_latest → recompute
    # Two sub-steps: return series, then recommendation + source summaries.
    # ------------------------------------------------------------------
    if benchmark_is_stale(
        attribution_summary_path=attribution_summary_path,
        benchmark_series_path=benchmark_series_path,
    ):
        if not dry_run:
            compute_benchmark_return_series(
                canonical_index_path=index_path,
                canonical_output_path=canonical_path,
                output_path=benchmark_series_path,
                config=benchmark_config,
                price_provider=price_provider,
                allow_online_fallback=allow_online_fallback,
            )
            compute_benchmark_recommendation_attribution(
                benchmark_series_path=benchmark_series_path,
                attribution_records_path=attribution_records_path,
                change_records_path=change_records_path,
                recommendation_output_path=benchmark_rec_path,
                source_output_path=benchmark_source_path,
            )
        refreshed.append("benchmark_attribution")
    else:
        skipped.append("benchmark_attribution")

    # ------------------------------------------------------------------
    # Final freshness snapshot
    # ------------------------------------------------------------------
    completed_at = datetime.now(timezone.utc).isoformat()
    freshness = artifact_freshness_report(
        index_path=index_path,
        canonical_path=canonical_path,
        change_summary_path=change_summary_path,
        lineage_summary_path=lineage_summary_path,
        attribution_summary_path=attribution_summary_path,
        benchmark_series_path=benchmark_series_path,
        config=governance_config,
    )

    return {
        "refreshed": refreshed,
        "skipped": skipped,
        "dry_run": dry_run,
        "started_at": started_at,
        "completed_at": completed_at,
        "freshness": freshness,
    }


# ---------------------------------------------------------------------------
# Background startup trigger helper
# ---------------------------------------------------------------------------

def trigger_startup_refresh(
    *,
    repo_root: str | Path = ".",
    allow_online_fallback: bool = False,
) -> None:
    """Run ``refresh_derived_artifacts`` once at startup in the calling thread.

    Designed to be invoked inside a ``threading.Thread`` from the server
    ``main()`` so that startup does not block the HTTP listener.

    All exceptions are swallowed after printing to stderr so a failed refresh
    does not crash the server.
    """
    import sys

    try:
        result = refresh_derived_artifacts(
            repo_root=repo_root,
            allow_online_fallback=allow_online_fallback,
        )
        refreshed = result.get("refreshed", [])
        skipped = result.get("skipped", [])
        overall = result.get("freshness", {}).get("overall_refresh_status", "UNKNOWN")
        if refreshed:
            print(f"[PIS] Startup refresh completed. Refreshed: {refreshed}. Status: {overall}")
        else:
            print(f"[PIS] Startup refresh: all artifacts current ({skipped}). Status: {overall}")
    except Exception as exc:
        print(f"[PIS] Startup refresh failed (non-fatal): {exc}", file=sys.stderr)
