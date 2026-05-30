"""
Map replay_inputs.csv + replay_performance_series.csv to AllocationEvidence per node.

Uses replay_filter_mapping from AllocationDimensionNode to associate performance data
with hierarchy nodes. LOW/NONE sophistication nodes receive METHODOLOGY_BASELINE records.
"""

from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .dimensions_loader import AllocationDimensionNode
from .models import AllocationEvidence

_DEFAULT_REPLAY_INPUTS_PATH = Path("data/current/replay_inputs.csv")
_DEFAULT_REPLAY_SERIES_PATH = Path("data/current/replay_performance_series.csv")


def load_replay_evidence(
    all_nodes: dict[str, AllocationDimensionNode],
    replay_inputs_path: Path | str = _DEFAULT_REPLAY_INPUTS_PATH,
    replay_series_path: Path | str = _DEFAULT_REPLAY_SERIES_PATH,
    as_of_date: str | None = None,
    lookback_days: int = 90,
) -> list[AllocationEvidence]:
    """
    Build AllocationEvidence records for each node using replay data.

    HIGH sophistication nodes: compute relative_return and outperformance_persistence
    from replay_performance_series.csv filtered by node's replay_filter_mapping.

    LOW/NONE nodes: emit a single METHODOLOGY_BASELINE evidence record (no replay math).
    """
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    batch_id = uuid.uuid4().hex[:8].upper()
    evidence_records: list[AllocationEvidence] = []

    # Load replay inputs and series if available
    replay_inputs = _load_csv_rows(Path(replay_inputs_path))
    replay_series = _load_csv_rows(Path(replay_series_path))

    for node_key, node in all_nodes.items():
        if node.replay_sophistication in ("LOW", "NONE"):
            evidence_records.append(_make_baseline_evidence(node_key, node, as_of_date, batch_id))
            continue

        if node.replay_sophistication == "HIGH":
            records = _extract_high_sophistication_evidence(
                node_key, node, replay_inputs, replay_series, as_of_date, batch_id
            )
            if records:
                evidence_records.extend(records)
            else:
                # No replay data available for this node — fall back to baseline
                evidence_records.append(_make_baseline_evidence(node_key, node, as_of_date, batch_id))

    return evidence_records


def _make_baseline_evidence(
    node_key: str,
    node: AllocationDimensionNode,
    evidence_date: str,
    batch_id: str,
) -> AllocationEvidence:
    """Create a METHODOLOGY_BASELINE evidence record for a LOW/NONE node."""
    return AllocationEvidence(
        evidence_id=f"EV_{batch_id}_{node_key.replace('.', '_')}_BASE",
        evidence_date=evidence_date,
        evidence_type="METHODOLOGY_BASELINE",
        node_key=node_key,
        asset_class=node.asset_class,
        metric_name="baseline_target_pct_of_parent",
        metric_value=0.0,
        benchmark_comparison=None,
        significance="LOW",
        replay_id=None,
        human_readable=f"{node_key}: methodology baseline only (replay_sophistication={node.replay_sophistication})",
    )


def _extract_high_sophistication_evidence(
    node_key: str,
    node: AllocationDimensionNode,
    replay_inputs: list[dict],
    replay_series: list[dict],
    as_of_date: str,
    batch_id: str,
) -> list[AllocationEvidence]:
    """
    Match replay records to this node using replay_filter_mapping and compute
    relative return metrics.
    """
    filter_map = node.replay_filter_mapping
    if not filter_map:
        return []

    # Filter replay_inputs matching this node's dimension filters
    matching_inputs = [
        row for row in replay_inputs
        if _matches_filter(row, filter_map)
    ]

    if not matching_inputs:
        return []

    matching_replay_ids = {row.get("replay_id", "") for row in matching_inputs if row.get("replay_id")}

    # Filter replay_series to matching replays and recent lookback
    matching_series = [
        row for row in replay_series
        if row.get("replay_id", "") in matching_replay_ids
        and row.get("series_date", "") <= as_of_date
    ]

    if not matching_series:
        return []

    # Compute aggregate relative returns (node vs. benchmark)
    # relative_return = mean of (cumulative_return - benchmark_return) across matching replays
    relative_returns: list[float] = []
    for row in matching_series:
        try:
            ret = float(row.get("relative_return", 0.0))
            relative_returns.append(ret)
        except (ValueError, TypeError):
            pass

    if not relative_returns:
        return []

    mean_relative = sum(relative_returns) / len(relative_returns)
    persistence = _compute_persistence(relative_returns)
    volatility_of_relative = _compute_volatility_penalty(relative_returns)

    evidence_id = f"EV_{batch_id}_{node_key.replace('.', '_')}_REPLAY"
    significance = "HIGH" if abs(mean_relative) > 0.05 else "MEDIUM" if abs(mean_relative) > 0.02 else "LOW"

    return [
        AllocationEvidence(
            evidence_id=evidence_id,
            evidence_date=as_of_date,
            evidence_type="REPLAY_OUTPERFORMANCE" if mean_relative > 0 else "REPLAY_OUTPERFORMANCE",
            node_key=node_key,
            asset_class=node.asset_class,
            metric_name="relative_return_90d",
            metric_value=round(mean_relative, 6),
            benchmark_comparison=f"BM_{node_key.replace('.', '_')}",
            significance=significance,
            replay_id="|".join(sorted(matching_replay_ids)[:5]),
            human_readable=(
                f"{node_key}: {mean_relative:+.2%} relative return "
                f"({len(matching_series)} periods, persistence={persistence:.2f})"
            ),
        ),
        AllocationEvidence(
            evidence_id=f"{evidence_id}_PERSIST",
            evidence_date=as_of_date,
            evidence_type="FACTOR_PERSISTENCE",
            node_key=node_key,
            asset_class=node.asset_class,
            metric_name="outperformance_persistence",
            metric_value=round(persistence, 6),
            benchmark_comparison=None,
            significance=significance,
            replay_id="|".join(sorted(matching_replay_ids)[:5]),
            human_readable=f"{node_key}: persistence={persistence:.3f}, vol_penalty={volatility_of_relative:.3f}",
        ),
        AllocationEvidence(
            evidence_id=f"{evidence_id}_VOLPEN",
            evidence_date=as_of_date,
            evidence_type="VOLATILITY_WARNING" if volatility_of_relative > 0.3 else "FACTOR_PERSISTENCE",
            node_key=node_key,
            asset_class=node.asset_class,
            metric_name="volatility_penalty",
            metric_value=round(volatility_of_relative, 6),
            benchmark_comparison=None,
            significance="HIGH" if volatility_of_relative > 0.3 else "LOW",
            replay_id=None,
            human_readable=f"{node_key}: volatility_penalty={volatility_of_relative:.3f}",
        ),
    ]


def _matches_filter(row: dict, filter_map: dict) -> bool:
    """Return True if this replay input row satisfies all dimension filter criteria."""
    for field, expected_value in filter_map.items():
        row_value = row.get(field, "")
        if str(row_value).strip().upper() != str(expected_value).strip().upper():
            return False
    return True


def _compute_persistence(returns: list[float]) -> float:
    """Fraction of periods with positive relative return (0.0–1.0)."""
    if not returns:
        return 0.5
    positive = sum(1 for r in returns if r > 0)
    return positive / len(returns)


def _compute_volatility_penalty(returns: list[float]) -> float:
    """
    Standard deviation of returns normalized to a 0.0–0.5 penalty.
    High dispersion → higher penalty.
    """
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = variance ** 0.5
    # Normalize: 0.20 std dev (~20% ann) → 0.4 penalty; cap at 0.5
    return round(min(0.5, std_dev * 2.0), 4)


def _load_csv_rows(path: Path) -> list[dict]:
    """Load CSV as list of dicts. Returns empty list if file doesn't exist."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
