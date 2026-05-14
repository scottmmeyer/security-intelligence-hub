"""Validation helpers for WP-04/WP-05 replay contracts and coverage governance."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from src.models.analytical_models import AnalyticalUniverseRow, PerformanceSeriesType, ReplaySelection

REPLAY_STATUS_ENUM = {
    "AVAILABLE",
    "PARTIAL",
    "NOT_GENERATED",
    "MISSING_MAPPING",
    "MISSING_MARKET_DATA",
    "BLOCKED",
    "FAILED",
    "STALE",
}


def _required_category_keys_from_registry(registry: Dict[str, Any]) -> set[Tuple[str, str, str]]:
    dimensions = registry.get("dimensions", {})
    geographies = dimensions.get("geography", [])
    market_caps = dimensions.get("market_cap_bucket", [])
    industry_scopes = dimensions.get("industry_scope", ["ALL"])
    return {
        (str(geo), str(bucket), str(industry))
        for geo in geographies
        for bucket in market_caps
        for industry in industry_scopes
    }


def validate_benchmark_mapping_completeness(registry: Dict[str, Any]) -> List[str]:
    """Validate ACTIVE benchmark assignment coverage for each category dimension tuple."""

    errors: List[str] = []
    required_keys = _required_category_keys_from_registry(registry)

    active_keys = {
        (
            str(item.get("geography", "")),
            str(item.get("market_cap_bucket", "")),
            str(item.get("industry_scope", "ALL")),
        )
        for item in registry.get("benchmark_assignments", [])
        if isinstance(item, dict) and str(item.get("assignment_status", "")).upper() == "ACTIVE"
    }

    missing = sorted(required_keys.difference(active_keys))
    if missing:
        errors.append(
            "Benchmark mapping completeness failure for category keys: "
            + ", ".join(f"{geo}/{bucket}/{industry}" for geo, bucket, industry in missing)
        )

    ids_defined = {
        str(item.get("benchmark_id", ""))
        for item in registry.get("benchmark_definitions", [])
        if isinstance(item, dict)
    }
    for assignment in registry.get("benchmark_assignments", []):
        if not isinstance(assignment, dict):
            continue
        if str(assignment.get("assignment_status", "")).upper() != "ACTIVE":
            continue
        benchmark_id = str(assignment.get("benchmark_id", ""))
        if benchmark_id not in ids_defined:
            errors.append(f"Benchmark mapping references undefined benchmark_id={benchmark_id!r}.")

    return errors


def validate_investable_vehicle_mapping_completeness(registry: Dict[str, Any]) -> List[str]:
    """Validate ACTIVE investable vehicle assignment coverage for each category tuple."""

    errors: List[str] = []
    required_keys = _required_category_keys_from_registry(registry)

    active_keys = {
        (
            str(item.get("geography", "")),
            str(item.get("market_cap_bucket", "")),
            str(item.get("industry_scope", "ALL")),
        )
        for item in registry.get("vehicle_assignments", [])
        if isinstance(item, dict) and str(item.get("assignment_status", "")).upper() == "ACTIVE"
    }

    missing = sorted(required_keys.difference(active_keys))
    if missing:
        errors.append(
            "Investable vehicle mapping completeness failure for category keys: "
            + ", ".join(f"{geo}/{bucket}/{industry}" for geo, bucket, industry in missing)
        )

    ids_defined = {
        str(item.get("vehicle_id", ""))
        for item in registry.get("investable_vehicles", [])
        if isinstance(item, dict)
    }
    for assignment in registry.get("vehicle_assignments", []):
        if not isinstance(assignment, dict):
            continue
        if str(assignment.get("assignment_status", "")).upper() != "ACTIVE":
            continue
        vehicle_id = str(assignment.get("vehicle_id", ""))
        if vehicle_id not in ids_defined:
            errors.append(f"Investable mapping references undefined vehicle_id={vehicle_id!r}.")

    return errors


def validate_analytical_universe_required_fields(rows: Iterable[AnalyticalUniverseRow]) -> List[str]:
    """Validate required analytical universe fields for deterministic replay contracts."""

    errors: List[str] = []
    required_non_empty = (
        "security_id",
        "symbol",
        "security_type",
        "snapshot_date",
        "run_id",
        "market_cap_bucket",
        "geography",
        "country",
        "industry",
        "sector",
        "benchmark_id",
        "investable_vehicle_id",
        "provider_lineage",
    )

    for index, row in enumerate(rows, start=1):
        for field_name in required_non_empty:
            value = str(getattr(row, field_name, "")).strip()
            if not value:
                errors.append(f"Analytical universe row {index} missing required field {field_name}.")

        if not isinstance(row.composite_score, (int, float)):
            errors.append(f"Analytical universe row {index} has non-numeric composite_score.")

        try:
            date.fromisoformat(row.snapshot_date)
        except ValueError:
            errors.append(
                f"Analytical universe row {index} has invalid snapshot_date {row.snapshot_date!r}."
            )

    return errors


def validate_replay_no_lookahead(
    selection: ReplaySelection,
    start_snapshot_rows: Sequence[AnalyticalUniverseRow],
) -> List[str]:
    """Enforce that selected symbols originate from the start-date snapshot only."""

    errors: List[str] = []
    try:
        start_date = date.fromisoformat(selection.start_date)
        composite_date = date.fromisoformat(selection.composite_score_snapshot_date)
    except ValueError:
        return ["Replay selection has invalid start_date or composite_score_snapshot_date."]

    if composite_date != start_date:
        errors.append(
            "Replay no-lookahead violation: composite_score_snapshot_date must equal start_date."
        )

    rows_by_symbol = {row.symbol: row for row in start_snapshot_rows}
    for symbol in selection.selected_symbols:
        row = rows_by_symbol.get(symbol)
        if row is None:
            errors.append(
                f"Replay no-lookahead violation: selected symbol {symbol!r} absent from start snapshot universe."
            )
            continue
        if row.snapshot_date != selection.composite_score_snapshot_date:
            errors.append(
                "Replay no-lookahead violation: selected symbol "
                f"{symbol!r} uses snapshot_date={row.snapshot_date} outside composite snapshot date."
            )

    return errors


def validate_top_n_selection_reproducibility(
    selection: ReplaySelection,
    filtered_rows: Sequence[AnalyticalUniverseRow],
) -> List[str]:
    """Check deterministic top-N ordering against stored selection symbols."""

    expected = [
        row.symbol
        for row in sorted(filtered_rows, key=lambda item: (-float(item.composite_score), item.symbol))[
            : selection.top_n
        ]
    ]
    observed = list(selection.selected_symbols)
    if observed != expected:
        return [
            "Top-N reproducibility failure: observed selected_symbols do not match deterministic ranking order."
        ]
    return []


def validate_performance_series_shape(
    series_rows: Sequence[Dict[str, Any]],
    *,
    replay_id: str,
) -> List[str]:
    """Validate performance series contract shape and deterministic semantics."""

    errors: List[str] = []
    allowed_types = {item.value for item in PerformanceSeriesType}
    seen_keys: set[Tuple[str, str, str]] = set()

    date_by_type: Dict[str, List[str]] = {}
    for index, row in enumerate(series_rows, start=1):
        series_type = str(row.get("series_type", ""))
        if series_type not in allowed_types:
            errors.append(f"Performance series row {index} has invalid series_type={series_type!r}.")

        row_replay_id = str(row.get("replay_id", ""))
        if row_replay_id != replay_id:
            errors.append(
                f"Performance series row {index} replay_id mismatch: expected {replay_id!r}, observed {row_replay_id!r}."
            )

        row_date = str(row.get("date", ""))
        try:
            date.fromisoformat(row_date)
        except ValueError:
            errors.append(f"Performance series row {index} has invalid date={row_date!r}.")

        for numeric_field in ("value", "cumulative_return"):
            try:
                float(row.get(numeric_field, ""))
            except (TypeError, ValueError):
                errors.append(
                    f"Performance series row {index} has non-numeric {numeric_field}={row.get(numeric_field)!r}."
                )

        uniqueness_key = (str(row.get("series_id", "")), series_type, row_date)
        if uniqueness_key in seen_keys:
            errors.append(
                f"Performance series row {index} duplicates series key {uniqueness_key!r}."
            )
        seen_keys.add(uniqueness_key)

        date_by_type.setdefault(series_type, []).append(row_date)

    for series_type, dates in date_by_type.items():
        if dates != sorted(dates):
            errors.append(
                f"Performance series ordering failure for {series_type}: dates are not sorted ascending."
            )

    return errors


def validate_benchmark_mapping_scope_symbols(
    registry: Dict[str, Any],
    *,
    required_symbols_by_category: Dict[Tuple[str, str, str], Sequence[str]],
) -> List[str]:
    """Ensure category assignments resolve to one of the required benchmark symbols."""

    errors: List[str] = []
    assignments = registry.get("benchmark_assignments", [])
    definitions = {
        str(item.get("benchmark_id", "")): str(item.get("symbol_or_index", "")).upper()
        for item in registry.get("benchmark_definitions", [])
        if isinstance(item, dict)
    }

    active_by_key = {
        (
            str(item.get("geography", "")).upper(),
            str(item.get("market_cap_bucket", "")).upper(),
            str(item.get("industry_scope", "ALL")).upper(),
        ): str(item.get("benchmark_id", ""))
        for item in assignments
        if isinstance(item, dict) and str(item.get("assignment_status", "")).upper() == "ACTIVE"
    }

    for key, allowed_symbols in required_symbols_by_category.items():
        benchmark_id = active_by_key.get((key[0].upper(), key[1].upper(), key[2].upper()))
        if not benchmark_id:
            errors.append(f"Missing benchmark assignment for category={key!r}.")
            continue
        symbol = definitions.get(benchmark_id, "")
        allowed_set = {str(item).upper() for item in allowed_symbols}
        if symbol not in allowed_set:
            errors.append(
                "Benchmark assignment symbol mismatch for "
                f"category={key!r}: observed {symbol!r}, allowed {sorted(allowed_set)}."
            )

    return errors


def validate_vehicle_mapping_scope_symbols(
    registry: Dict[str, Any],
    *,
    required_symbols_by_category: Dict[Tuple[str, str, str], Sequence[str]],
) -> List[str]:
    """Ensure category assignments resolve to one of the required ETF/fund symbols."""

    errors: List[str] = []
    assignments = registry.get("vehicle_assignments", [])
    definitions = {
        str(item.get("vehicle_id", "")): str(item.get("symbol", "")).upper()
        for item in registry.get("investable_vehicles", [])
        if isinstance(item, dict)
    }

    active_by_key = {
        (
            str(item.get("geography", "")).upper(),
            str(item.get("market_cap_bucket", "")).upper(),
            str(item.get("industry_scope", "ALL")).upper(),
        ): str(item.get("vehicle_id", ""))
        for item in assignments
        if isinstance(item, dict) and str(item.get("assignment_status", "")).upper() == "ACTIVE"
    }

    for key, allowed_symbols in required_symbols_by_category.items():
        vehicle_id = active_by_key.get((key[0].upper(), key[1].upper(), key[2].upper()))
        if not vehicle_id:
            errors.append(f"Missing investable vehicle assignment for category={key!r}.")
            continue
        symbol = definitions.get(vehicle_id, "")
        allowed_set = {str(item).upper() for item in allowed_symbols}
        if symbol not in allowed_set:
            errors.append(
                "Investable vehicle assignment symbol mismatch for "
                f"category={key!r}: observed {symbol!r}, allowed {sorted(allowed_set)}."
            )

    return errors


def validate_replay_availability_consistency(rows: Sequence[Dict[str, Any]]) -> List[str]:
    """Validate replay availability row contract and status coherence."""

    errors: List[str] = []
    required_fields = (
        "geography",
        "market_cap_bucket",
        "industry",
        "benchmark_available",
        "vehicle_available",
        "stock_replay_available",
        "top_n_available",
        "replay_generated",
        "replay_status",
        "missing_dependencies",
        "generated_at_utc",
    )
    seen_keys: set[Tuple[str, str, str]] = set()

    def _as_bool(value: Any) -> bool | None:
        raw = str(value).strip().lower()
        if raw in {"true", "1", "yes"}:
            return True
        if raw in {"false", "0", "no"}:
            return False
        return None

    for index, row in enumerate(rows, start=1):
        for field_name in required_fields:
            if field_name not in row:
                errors.append(f"Replay availability row {index} missing field {field_name}.")

        key = (
            str(row.get("geography", "")).upper(),
            str(row.get("market_cap_bucket", "")).upper(),
            str(row.get("industry", "")).upper(),
        )
        if key in seen_keys:
            errors.append(f"Replay availability duplicate category row detected for {key!r}.")
        seen_keys.add(key)

        status = str(row.get("replay_status", "")).upper()
        if status not in REPLAY_STATUS_ENUM:
            errors.append(f"Replay availability row {index} has invalid replay_status={status!r}.")

        benchmark_available = _as_bool(row.get("benchmark_available", ""))
        vehicle_available = _as_bool(row.get("vehicle_available", ""))
        replay_generated = _as_bool(row.get("replay_generated", ""))
        if benchmark_available is None or vehicle_available is None or replay_generated is None:
            errors.append(f"Replay availability row {index} has non-boolean availability values.")
            continue

        if status == "AVAILABLE" and not (benchmark_available and vehicle_available and replay_generated):
            errors.append(
                f"Replay availability row {index} is AVAILABLE but required flags are not all true."
            )

        if status in {"NOT_GENERATED", "MISSING_MAPPING", "MISSING_MARKET_DATA", "BLOCKED"} and replay_generated:
            errors.append(
                f"Replay availability row {index} has status {status} but replay_generated is true."
            )

    return errors


def validate_orphaned_replay_metadata(
    replay_matrix_rows: Sequence[Dict[str, Any]],
    *,
    history_root: str | Path = "data/history/replays",
    replay_id_prefix: str | None = None,
) -> List[str]:
    """Validate replay metadata references and detect orphaned replay directories."""

    errors: List[str] = []
    expected_replay_ids = {
        str(row.get("replay_id", "")).strip()
        for row in replay_matrix_rows
        if str(row.get("replay_id", "")).strip()
    }

    for row in replay_matrix_rows:
        replay_id = str(row.get("replay_id", "")).strip()
        metadata_path = Path(str(row.get("replay_metadata_path", "")))
        availability_path = Path(str(row.get("replay_availability_path", "")))
        series_path = Path(str(row.get("replay_series_path", "")))
        if replay_id and not metadata_path.exists():
            errors.append(f"Replay metadata missing for replay_id={replay_id}: {metadata_path}")
        if replay_id and not availability_path.exists():
            errors.append(f"Replay availability metadata missing for replay_id={replay_id}: {availability_path}")
        if replay_id and not series_path.exists():
            errors.append(f"Replay series output missing for replay_id={replay_id}: {series_path}")

    history_root_path = Path(history_root)
    if history_root_path.exists():
        # Phase A: scan both top-level replay_id=... dirs (legacy) AND
        # snapshot_date=.../replay_id=... dirs (new WP-05C partitioned structure).
        for child in history_root_path.iterdir():
            if child.is_dir() and child.name.startswith("replay_id="):
                # Legacy flat layout
                replay_id = child.name.split("replay_id=", 1)[-1]
                if replay_id_prefix and replay_id_prefix not in replay_id:
                    continue
                if replay_id not in expected_replay_ids:
                    errors.append(
                        f"Orphaned replay partition detected without replay_matrix reference: {child}"
                    )
            elif child.is_dir() and child.name.startswith("snapshot_date="):
                # WP-05C partitioned layout: snapshot_date=<date>/replay_id=<id>
                for grandchild in child.iterdir():
                    if not grandchild.is_dir() or not grandchild.name.startswith("replay_id="):
                        continue
                    replay_id = grandchild.name.split("replay_id=", 1)[-1]
                    if replay_id_prefix and replay_id_prefix not in replay_id:
                        continue
                    if replay_id not in expected_replay_ids:
                        errors.append(
                            f"Orphaned replay partition detected without replay_matrix reference: {grandchild}"
                        )

    return errors


def validate_empty_replay_outputs(replay_matrix_rows: Sequence[Dict[str, Any]]) -> List[str]:
    """Validate replay matrix output contracts are non-empty when replay is generated."""

    errors: List[str] = []
    for row in replay_matrix_rows:
        replay_id = str(row.get("replay_id", "")).strip()
        if not replay_id:
            continue
        try:
            count = int(str(row.get("performance_row_count", "0")))
        except ValueError:
            errors.append(f"Replay matrix row has invalid performance_row_count for replay_id={replay_id}.")
            continue
        if count <= 0:
            errors.append(f"Replay output is empty for replay_id={replay_id}.")
    return errors


def validate_replay_ui_mismatch(
    replay_matrix_rows: Sequence[Dict[str, Any]],
    replay_input_rows: Sequence[Dict[str, Any]],
) -> List[str]:
    """Validate replay matrix references are represented in replay input contracts used by UI."""

    errors: List[str] = []
    matrix_ids = {
        str(row.get("replay_id", "")).strip()
        for row in replay_matrix_rows
        if str(row.get("replay_id", "")).strip()
    }
    input_ids = {
        str(row.get("replay_id", "")).strip()
        for row in replay_input_rows
        if str(row.get("replay_id", "")).strip()
    }

    missing_in_inputs = sorted(matrix_ids.difference(input_ids))
    for replay_id in missing_in_inputs:
        errors.append(f"Replay/UI mismatch: replay_id missing from replay_inputs.csv: {replay_id}")
    return errors


def validate_unsupported_category_exposure(
    availability_rows: Sequence[Dict[str, Any]],
    *,
    supported_categories: Sequence[Tuple[str, str, str]],
) -> List[str]:
    """Ensure unsupported categories are not marked AVAILABLE in UI-facing availability rows."""

    errors: List[str] = []
    supported = {(geo.upper(), bucket.upper(), industry.upper()) for geo, bucket, industry in supported_categories}

    for row in availability_rows:
        key = (
            str(row.get("geography", "")).upper(),
            str(row.get("market_cap_bucket", "")).upper(),
            str(row.get("industry", "")).upper(),
        )
        status = str(row.get("replay_status", "")).upper()
        if key not in supported and status == "AVAILABLE":
            errors.append(
                "Unsupported category exposure violation: category outside generation scope marked AVAILABLE "
                f"for {key!r}."
            )

    return errors


# ---------------------------------------------------------------------------
# Phase E — Temporal validation hardening (WP-05C)
# ---------------------------------------------------------------------------


def validate_no_duplicate_snapshot_registry_entries(
    registry_rows: Sequence[Dict[str, Any]],
    *,
    key_fields: Sequence[str],
) -> List[str]:
    """Validate that no two rows in a snapshot registry share the same composite key.

    Snapshot registries are append-oriented historical truth; duplicate entries
    indicate a broken publish pipeline or double-write.
    """
    errors: List[str] = []
    seen: set[tuple[str, ...]] = set()

    for index, row in enumerate(registry_rows, start=1):
        key = tuple(str(row.get(field, "")).strip() for field in key_fields)
        if key in seen:
            errors.append(
                f"Snapshot registry duplicate detected at row {index}: "
                + ", ".join(f"{f}={v!r}" for f, v in zip(key_fields, key))
            )
        seen.add(key)

    return errors


def validate_partial_current_publication(
    current_root: str | Path = "data/current",
) -> List[str]:
    """Detect a stale .tmp directory from a previously failed atomic publication.

    If data/current/.tmp/ exists, a prior publication was interrupted before the
    atomic swap completed. Current outputs may be inconsistent.
    """
    tmp_path = Path(current_root) / ".tmp"
    if tmp_path.exists() and tmp_path.is_dir():
        return [
            f"Partial current publication detected: stale tmp directory exists at {tmp_path}. "
            "A prior atomic publication may have failed. Inspect and remove .tmp/ before re-running."
        ]
    return []


def validate_current_outputs_freshness(
    current_root: str | Path = "data/current",
    *,
    max_staleness_days: int = 7,
) -> List[str]:
    """Validate that current snapshot metadata exists and is within the staleness threshold."""

    errors: List[str] = []
    metadata_path = Path(current_root) / "current_snapshot_metadata.json"

    if not metadata_path.exists():
        errors.append(
            f"Current snapshot metadata missing: {metadata_path}. "
            "Run build_wp05b_replay_matrix() to publish current outputs."
        )
        return errors

    import json as _json

    try:
        metadata = _json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Current snapshot metadata unreadable: {exc}")
        return errors

    generated_at_str = str(metadata.get("generated_at_utc", "")).strip()
    if not generated_at_str:
        errors.append("Current snapshot metadata missing generated_at_utc field.")
        return errors

    try:
        generated_at = datetime.fromisoformat(generated_at_str)
        age_days = (datetime.now(timezone.utc) - generated_at).days
        if age_days > max_staleness_days:
            errors.append(
                f"Current outputs are stale: generated {age_days} days ago "
                f"(threshold: {max_staleness_days} days). Rebuild to refresh."
            )
    except ValueError:
        errors.append(f"Current snapshot metadata has unparseable generated_at_utc: {generated_at_str!r}.")

    return errors


def validate_replay_mode_consistency(
    replay_mode: str,
    start_date: str,
    end_date: str,
) -> List[str]:
    """Validate that the declared replay_mode is consistent with the replay window dates."""

    errors: List[str] = []
    try:
        today = date.today()
        end = date.fromisoformat(end_date)
        start = date.fromisoformat(start_date)
    except ValueError as exc:
        return [f"Replay mode consistency check blocked by invalid date: {exc}"]

    if replay_mode == "FORWARD_SIMULATION" and end <= today:
        errors.append(
            f"Replay mode mismatch: declared FORWARD_SIMULATION but end_date={end_date} is not in the future."
        )
    if replay_mode == "CURRENT_RECOMMENDATION" and end != today:
        errors.append(
            f"Replay mode mismatch: declared CURRENT_RECOMMENDATION but end_date={end_date} != today={today}."
        )
    if replay_mode == "HISTORICAL_VALIDATION" and end >= today:
        errors.append(
            f"Replay mode mismatch: declared HISTORICAL_VALIDATION but end_date={end_date} is today or future."
        )
    if start > end:
        errors.append(f"Replay window invalid: start_date={start_date} is after end_date={end_date}.")

    return errors


def validate_current_history_synchronization(
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/replays",
) -> List[str]:
    """Validate that replay_matrix.csv references history partitions that exist.

    Detects current/history drift: if the current replay_matrix.csv lists replay
    IDs that no longer have matching history directories, the contract is broken.
    """
    import csv as _csv

    errors: List[str] = []
    matrix_path = Path(current_root) / "replay_matrix.csv"

    if not matrix_path.exists():
        return [f"replay_matrix.csv missing from current root: {matrix_path}"]

    history_root_path = Path(history_root)
    try:
        with matrix_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(_csv.DictReader(handle))
    except Exception as exc:
        return [f"replay_matrix.csv unreadable: {exc}"]

    for row in rows:
        replay_id = str(row.get("replay_id", "")).strip()
        if not replay_id:
            continue
        metadata_path_str = str(row.get("replay_metadata_path", "")).strip()
        if metadata_path_str:
            metadata_path = Path(metadata_path_str)
            if not metadata_path.exists():
                errors.append(
                    f"Current/history sync failure: replay_id={replay_id} metadata path missing: {metadata_path}"
                )

    return errors
