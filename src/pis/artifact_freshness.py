"""PIS artifact freshness detection (PIS-005).

Provides deterministic freshness checks for each derived artifact layer.
No heuristics — all checks compare latest dates from persisted CSVs.

Freshness hierarchy (each layer depends on the one above):
  Governance (snapshot index + evaluate_snapshot_governance)
      → Canonical (canonical_daily_snapshots.csv)
          → Change Detection (change_records.csv / change_summary.csv)
              → Lineage (lineage_records.csv / lineage_summary.csv)
                  → Attribution (attribution_records.csv / attribution_summary.csv)
                      → Benchmark Attribution (benchmark_return_series.csv)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from .governance import DEFAULT_GOVERNANCE_CONFIG, SnapshotGovernanceConfig, evaluate_snapshot_governance
from .storage import _read_csv_rows


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

Freshness = Literal["CURRENT", "STALE", "MISSING"]

# ---------------------------------------------------------------------------
# Default artifact paths
# ---------------------------------------------------------------------------

_SNAPSHOT_INDEX = "data/history/pis/pis_snapshot_index.csv"
_CANONICAL_CSV = "data/history/pis/canonical/canonical_daily_snapshots.csv"
_CHANGE_RECORDS = "data/history/pis/changes/change_records.csv"
_CHANGE_SUMMARY = "data/history/pis/changes/change_summary.csv"
_LINEAGE_RECORDS = "data/history/pis/lineage/lineage_records.csv"
_LINEAGE_SUMMARY = "data/history/pis/lineage/lineage_summary.csv"
_ATTRIBUTION_RECORDS = "data/history/pis/attribution/attribution_records.csv"
_ATTRIBUTION_SUMMARY = "data/history/pis/attribution/attribution_summary.csv"
_BENCHMARK_SERIES = "data/history/pis/benchmark_attribution/benchmark_return_series.csv"
_BENCHMARK_REC = "data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv"
_BENCHMARK_SOURCE = "data/history/pis/benchmark_attribution/source_benchmark_summary.csv"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _latest_date_from_csv(path: Path, date_field: str = "snapshot_date") -> str:
    """Return the latest non-empty value of ``date_field`` from *path*, or ``""``."""
    rows = _read_csv_rows(path)
    dates = [str(r.get(date_field, "")).strip() for r in rows if str(r.get(date_field, "")).strip()]
    return max(dates) if dates else ""


# ---------------------------------------------------------------------------
# Latest-date queries (one per layer)
# ---------------------------------------------------------------------------

def latest_pass_snapshot_date(
    *,
    index_path: str | Path = _SNAPSHOT_INDEX,
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> str:
    """Return the latest snapshot_date for which a PASS governance result exists.

    Evaluates governance inline from the index so the result is always
    current regardless of when snapshot_governance.csv was last written.
    """
    rows = _read_csv_rows(Path(index_path))
    dates: list[str] = []
    for row in rows:
        result = evaluate_snapshot_governance(row, config=config)
        if str(result.get("status", "")).upper() == "PASS":
            d = str(row.get("snapshot_date", "")).strip()
            if d:
                dates.append(d)
    return max(dates) if dates else ""


def latest_canonical_date(
    *,
    canonical_path: str | Path = _CANONICAL_CSV,
) -> str:
    """Return the latest snapshot_date in canonical_daily_snapshots.csv."""
    p = Path(canonical_path)
    if not p.exists():
        return ""
    return _latest_date_from_csv(p, "snapshot_date")


def latest_change_date(
    *,
    change_summary_path: str | Path = _CHANGE_SUMMARY,
) -> str:
    """Return the latest snapshot_date in change_summary.csv."""
    p = Path(change_summary_path)
    if not p.exists():
        return ""
    return _latest_date_from_csv(p, "snapshot_date")


def latest_lineage_date(
    *,
    lineage_summary_path: str | Path = _LINEAGE_SUMMARY,
) -> str:
    """Return the latest snapshot_date in lineage_summary.csv."""
    p = Path(lineage_summary_path)
    if not p.exists():
        return ""
    return _latest_date_from_csv(p, "snapshot_date")


def latest_attribution_date(
    *,
    attribution_summary_path: str | Path = _ATTRIBUTION_SUMMARY,
) -> str:
    """Return the latest snapshot_date in attribution_summary.csv."""
    p = Path(attribution_summary_path)
    if not p.exists():
        return ""
    return _latest_date_from_csv(p, "snapshot_date")


def latest_benchmark_date(
    *,
    benchmark_series_path: str | Path = _BENCHMARK_SERIES,
) -> str:
    """Return the latest snapshot_date in benchmark_return_series.csv."""
    p = Path(benchmark_series_path)
    if not p.exists():
        return ""
    return _latest_date_from_csv(p, "snapshot_date")


# ---------------------------------------------------------------------------
# Per-layer staleness predicates
# ---------------------------------------------------------------------------

def canonical_is_stale(
    *,
    index_path: str | Path = _SNAPSHOT_INDEX,
    canonical_path: str | Path = _CANONICAL_CSV,
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> bool:
    """True if governance has newer PASS snapshots than canonical_daily_snapshots.csv.

    Rule: governance_latest_PASS_date > canonical_latest_date → STALE
    """
    gov_latest = latest_pass_snapshot_date(index_path=index_path, config=config)
    if not gov_latest:
        return False
    can_latest = latest_canonical_date(canonical_path=canonical_path)
    return can_latest < gov_latest


def change_is_stale(
    *,
    canonical_path: str | Path = _CANONICAL_CSV,
    change_summary_path: str | Path = _CHANGE_SUMMARY,
) -> bool:
    """True if canonical has newer dates than change_summary.csv.

    Rule: canonical_latest > change_latest → STALE
    """
    can_latest = latest_canonical_date(canonical_path=canonical_path)
    if not can_latest:
        return False
    chg_latest = latest_change_date(change_summary_path=change_summary_path)
    return chg_latest < can_latest


def lineage_is_stale(
    *,
    change_summary_path: str | Path = _CHANGE_SUMMARY,
    lineage_summary_path: str | Path = _LINEAGE_SUMMARY,
) -> bool:
    """True if change detection has newer dates than lineage_summary.csv.

    Rule: change_latest > lineage_latest → STALE
    """
    chg_latest = latest_change_date(change_summary_path=change_summary_path)
    if not chg_latest:
        return False
    lin_latest = latest_lineage_date(lineage_summary_path=lineage_summary_path)
    return lin_latest < chg_latest


def attribution_is_stale(
    *,
    lineage_summary_path: str | Path = _LINEAGE_SUMMARY,
    attribution_summary_path: str | Path = _ATTRIBUTION_SUMMARY,
) -> bool:
    """True if lineage has newer dates than attribution_summary.csv.

    Rule: lineage_latest > attribution_latest → STALE
    """
    lin_latest = latest_lineage_date(lineage_summary_path=lineage_summary_path)
    if not lin_latest:
        return False
    att_latest = latest_attribution_date(attribution_summary_path=attribution_summary_path)
    return att_latest < lin_latest


def benchmark_is_stale(
    *,
    attribution_summary_path: str | Path = _ATTRIBUTION_SUMMARY,
    benchmark_series_path: str | Path = _BENCHMARK_SERIES,
) -> bool:
    """True if attribution has newer dates than benchmark_return_series.csv.

    Rule: attribution_latest > benchmark_latest → STALE
    """
    att_latest = latest_attribution_date(attribution_summary_path=attribution_summary_path)
    if not att_latest:
        return False
    bch_latest = latest_benchmark_date(benchmark_series_path=benchmark_series_path)
    return bch_latest < att_latest


# ---------------------------------------------------------------------------
# Composite freshness report
# ---------------------------------------------------------------------------

def _classify_status(latest: str, path: Path, gov_latest: str) -> Freshness:
    """Classify a single artifact layer into CURRENT / STALE / MISSING."""
    if not path.exists() or not latest:
        return "MISSING"
    if gov_latest and latest < gov_latest:
        return "STALE"
    return "CURRENT"


def artifact_freshness_report(
    *,
    index_path: str | Path = _SNAPSHOT_INDEX,
    canonical_path: str | Path = _CANONICAL_CSV,
    change_summary_path: str | Path = _CHANGE_SUMMARY,
    lineage_summary_path: str | Path = _LINEAGE_SUMMARY,
    attribution_summary_path: str | Path = _ATTRIBUTION_SUMMARY,
    benchmark_series_path: str | Path = _BENCHMARK_SERIES,
    config: SnapshotGovernanceConfig = DEFAULT_GOVERNANCE_CONFIG,
) -> dict[str, object]:
    """Return freshness status for all artifact layers.

    Exposes the data required for Phase D (dashboard visibility):
      - latest_pass_snapshot_date
      - latest_canonical_date
      - latest_change_date
      - latest_lineage_date
      - latest_attribution_date
      - latest_benchmark_date
      - canonical_status / change_status / lineage_status / attribution_status / benchmark_status
      - overall_refresh_status
    """
    gov_latest = latest_pass_snapshot_date(index_path=index_path, config=config)
    can_latest = latest_canonical_date(canonical_path=canonical_path)
    chg_latest = latest_change_date(change_summary_path=change_summary_path)
    lin_latest = latest_lineage_date(lineage_summary_path=lineage_summary_path)
    att_latest = latest_attribution_date(attribution_summary_path=attribution_summary_path)
    bch_latest = latest_benchmark_date(benchmark_series_path=benchmark_series_path)

    can_status: Freshness = _classify_status(can_latest, Path(canonical_path), gov_latest)
    chg_status: Freshness = _classify_status(chg_latest, Path(change_summary_path), gov_latest)
    lin_status: Freshness = _classify_status(lin_latest, Path(lineage_summary_path), gov_latest)
    att_status: Freshness = _classify_status(att_latest, Path(attribution_summary_path), gov_latest)
    bch_status: Freshness = _classify_status(bch_latest, Path(benchmark_series_path), gov_latest)

    all_current = all(s == "CURRENT" for s in [can_status, chg_status, lin_status, att_status, bch_status])
    any_missing = any(s == "MISSING" for s in [can_status, chg_status, lin_status, att_status, bch_status])

    if all_current:
        overall: Freshness = "CURRENT"
    elif any_missing:
        overall = "MISSING"
    else:
        overall = "STALE"

    return {
        "latest_pass_snapshot_date": gov_latest,
        "latest_canonical_date": can_latest,
        "latest_change_date": chg_latest,
        "latest_lineage_date": lin_latest,
        "latest_attribution_date": att_latest,
        "latest_benchmark_date": bch_latest,
        "canonical_status": can_status,
        "change_status": chg_status,
        "lineage_status": lin_status,
        "attribution_status": att_status,
        "benchmark_status": bch_status,
        "overall_refresh_status": overall,
    }
