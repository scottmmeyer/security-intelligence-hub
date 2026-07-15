from __future__ import annotations

import csv
import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable

from src.portfolio.regime.market_regime_inputs import evaluate_market_proxy_freshness
from src.replay.replay_engine import PERFORMANCE_SERIES_HEADERS, REPLAY_SELECTION_HEADERS
from src.sih.rotation_risk_monitor import rotation_risk_summary


REQUIRED_MARKET_REGIME_COHORTS = (
    "TECHNOLOGY",
    "ENERGY",
    "BASIC MATERIALS",
    "INDUSTRIALS",
)


class ReplayReconstructionError(ValueError):
    """Raised when candidate reconstruction contracts are violated."""


@dataclass(frozen=True)
class _RegistryEntry:
    replay_id: str
    snapshot_date: str
    start_date: str
    end_date: str
    geography: str
    market_cap_bucket: str
    industry: str
    benchmark_available: bool
    vehicle_available: bool
    stock_replay_available: bool
    top_n_available: bool
    replay_status: str
    replay_mode: str
    generated_at_utc: str


def reconstruct_replay_current_candidate(
    *,
    repo_root: str | Path,
    snapshot_date: str,
    output_root: str | Path,
    restoration_id: str | None = None,
    candidate_only: bool = True,
    allowed_registry_statuses: Iterable[str] = ("AVAILABLE",),
    required_market_regime_cohorts: Iterable[str] = REQUIRED_MARKET_REGIME_COHORTS,
    portfolio_snapshot_date_for_freshness: str = "2026-07-15",
) -> dict[str, Any]:
    """Build replay current candidate artifacts from immutable partitions only.

    This function never writes to data/current and rejects output paths under
    data/current. It emits a candidate replay_inputs.csv + replay_performance_series.csv
    and validation artifacts under output_root.
    """
    repo_root_path = Path(repo_root).resolve()
    output_root_path = Path(output_root).resolve()
    restoration_id = restoration_id or _build_restoration_id(snapshot_date)

    if not candidate_only:
        raise ReplayReconstructionError("candidate_only=True is required for reconstruction.")

    _reject_current_output_root(repo_root_path, output_root_path)

    allowed_statuses = {str(s).strip().upper() for s in allowed_registry_statuses if str(s).strip()}
    if not allowed_statuses:
        raise ReplayReconstructionError("At least one allowed registry status is required.")

    required_cohorts = tuple(_norm_industry(x) for x in required_market_regime_cohorts)
    if not required_cohorts:
        raise ReplayReconstructionError("At least one required market-regime cohort is required.")

    registry_path = repo_root_path / "data" / "history" / "replay_snapshot_registry.csv"
    if not registry_path.exists():
        raise ReplayReconstructionError(f"Missing registry file: {registry_path}")

    entries_all_snapshot = _load_registry_snapshot_entries(registry_path, snapshot_date)
    if not entries_all_snapshot:
        raise ReplayReconstructionError(f"No registry rows found for snapshot_date={snapshot_date}.")

    entries_qualified = [
        e for e in entries_all_snapshot if e.replay_status in allowed_statuses
    ]
    if not entries_qualified:
        raise ReplayReconstructionError(
            f"No registry rows qualified by status for snapshot_date={snapshot_date}; "
            f"allowed={sorted(allowed_statuses)}."
        )

    partitions, excluded_registry_rows, legacy_schema_normalized_count = _load_partition_payloads(
        repo_root=repo_root_path,
        snapshot_date=snapshot_date,
        registry_entries=entries_qualified,
    )
    if not partitions:
        raise ReplayReconstructionError(
            "No usable immutable partitions remained after filtering missing/unreadable registry entries."
        )

    selected = _select_latest_compatible_partitions(partitions)

    candidate_inputs = [p["selection_row"] for p in selected]
    candidate_series = [row for p in selected for row in p["series_rows"]]

    _validate_candidate_schemas(candidate_inputs, candidate_series)
    _validate_candidate_content(candidate_inputs, candidate_series)

    registry_expected_industries = {
        _norm_industry(p["registry"].industry)
        for p in selected
        if _norm_industry(p["registry"].industry)
    }

    _validate_cohorts_and_scope(
        candidate_inputs=candidate_inputs,
        required_cohorts=required_cohorts,
        expected_registry_industries=registry_expected_industries,
    )

    candidate_inputs_sorted = sorted(
        candidate_inputs,
        key=lambda r: (
            str(r.get("filter_geography") or "").upper(),
            str(r.get("filter_market_cap_bucket") or "").upper(),
            str(r.get("filter_industry") or "").upper(),
            str(r.get("filter_analytical_subtier") or "").upper(),
            str(r.get("replay_id") or ""),
        ),
    )
    candidate_series_sorted = sorted(
        candidate_series,
        key=lambda r: (
            str(r.get("replay_id") or ""),
            str(r.get("series_type") or "").upper(),
            str(r.get("date") or ""),
            str(r.get("series_id") or ""),
        ),
    )

    output_root_path.mkdir(parents=True, exist_ok=True)
    candidate_inputs_path = output_root_path / "replay_inputs.csv"
    candidate_series_path = output_root_path / "replay_performance_series.csv"

    _write_csv(candidate_inputs_path, REPLAY_SELECTION_HEADERS, candidate_inputs_sorted)
    _write_csv(candidate_series_path, PERFORMANCE_SERIES_HEADERS, candidate_series_sorted)

    latest_proxy_date, freshness = _run_market_regime_semantic_validation(
        candidate_inputs_path=candidate_inputs_path,
        candidate_series_path=candidate_series_path,
        portfolio_snapshot_date_for_freshness=portfolio_snapshot_date_for_freshness,
    )

    files_meta = {
        "replay_inputs.csv": _file_meta(candidate_inputs_path, REPLAY_SELECTION_HEADERS),
        "replay_performance_series.csv": _file_meta(candidate_series_path, PERFORMANCE_SERIES_HEADERS),
    }

    source_replay_ids = [p["registry"].replay_id for p in selected]
    source_run_ids = sorted({p["run_token"] for p in selected if p["run_token"]})
    source_statuses = sorted({p["registry"].replay_status for p in selected})

    industry_counts = Counter(
        _norm_industry(str(r.get("filter_industry") or ""))
        for r in candidate_inputs_sorted
        if _norm_industry(str(r.get("filter_industry") or ""))
    )

    missing_required = [x for x in required_cohorts if industry_counts.get(x, 0) <= 0]

    warnings: list[str] = []
    if excluded_registry_rows:
        warnings.append(
            f"Excluded {len(excluded_registry_rows)} registry rows with missing/unreadable partition files."
        )
    if legacy_schema_normalized_count > 0:
        warnings.append(
            f"Normalized {legacy_schema_normalized_count} legacy replay_selection rows missing filter_analytical_subtier."
        )
    if freshness.get("freshness_status") == "STALE":
        warnings.append("Candidate is structurally complete but stale relative to requested portfolio date.")

    validation_status = "pass"
    if missing_required:
        validation_status = "fail"

    manifest = {
        "restoration_id": restoration_id,
        "mode": "candidate_only",
        "published": False,
        "source_snapshot_date": snapshot_date,
        "source_registry": str(registry_path),
        "source_partition_count": len(selected),
        "source_replay_ids": source_replay_ids,
        "source_run_ids": source_run_ids,
        "source_statuses": source_statuses,
        "candidate_files": files_meta,
        "industry_counts": dict(industry_counts),
        "required_cohorts": list(required_cohorts),
        "missing_required_cohorts": missing_required,
        "validation_status": validation_status,
        "warnings": warnings,
    }

    validation_report = {
        "restoration_id": restoration_id,
        "snapshot_date": snapshot_date,
        "candidate_only": True,
        "output_root": str(output_root_path),
        "schema": {
            "replay_inputs": list(REPLAY_SELECTION_HEADERS),
            "replay_performance_series": list(PERFORMANCE_SERIES_HEADERS),
        },
        "file_validation": {
            "replay_inputs_exists": candidate_inputs_path.exists(),
            "replay_series_exists": candidate_series_path.exists(),
            "replay_inputs_rows": files_meta["replay_inputs.csv"]["rows"],
            "replay_series_rows": files_meta["replay_performance_series.csv"]["rows"],
            "replay_inputs_sha256": files_meta["replay_inputs.csv"]["sha256"],
            "replay_series_sha256": files_meta["replay_performance_series.csv"]["sha256"],
        },
        "scope_validation": {
            "expected_registry_industries": sorted(registry_expected_industries),
            "candidate_industries": sorted(industry_counts.keys()),
            "required_cohorts": list(required_cohorts),
            "missing_required_cohorts": missing_required,
        },
        "semantic_market_regime": {
            "latest_proxy_date": latest_proxy_date,
            "freshness": freshness,
        },
        "provenance": {
            "selected_partition_count": len(selected),
            "selected_replay_ids": source_replay_ids,
            "selected_run_tokens": source_run_ids,
            "allowed_registry_statuses": sorted(allowed_statuses),
            "excluded_registry_rows": len(entries_all_snapshot) - len(entries_qualified),
            "excluded_missing_partition_rows": excluded_registry_rows,
            "legacy_selection_schema_normalized_count": legacy_schema_normalized_count,
        },
    }

    manifest_path = output_root_path / "reconstruction_manifest.json"
    validation_path = output_root_path / "validation_report.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    validation_path.write_text(json.dumps(validation_report, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "manifest": manifest,
        "validation_report": validation_report,
        "output_root": str(output_root_path),
        "candidate_inputs_path": str(candidate_inputs_path),
        "candidate_series_path": str(candidate_series_path),
        "manifest_path": str(manifest_path),
        "validation_path": str(validation_path),
    }


def _build_restoration_id(snapshot_date: str) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    clean = str(snapshot_date).replace("-", "")
    return f"REPLAY_RESTORE_{clean}_{ts}"


def _reject_current_output_root(repo_root: Path, output_root: Path) -> None:
    current_root = (repo_root / "data" / "current").resolve()
    if output_root == current_root:
        raise ReplayReconstructionError("Output root must not be data/current.")
    if current_root in output_root.parents:
        raise ReplayReconstructionError("Output root must not be inside data/current.")


def _parse_bool(v: Any) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def _load_registry_snapshot_entries(registry_path: Path, snapshot_date: str) -> list[_RegistryEntry]:
    out: list[_RegistryEntry] = []
    with registry_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if str(row.get("snapshot_date") or "").strip() != str(snapshot_date):
                continue
            replay_id = str(row.get("replay_id") or "").strip()
            if not replay_id:
                continue
            out.append(
                _RegistryEntry(
                    replay_id=replay_id,
                    snapshot_date=str(row.get("snapshot_date") or "").strip(),
                    start_date=str(row.get("start_date") or "").strip(),
                    end_date=str(row.get("end_date") or "").strip(),
                    geography=str(row.get("geography") or "").strip().upper(),
                    market_cap_bucket=str(row.get("market_cap_bucket") or "").strip().upper(),
                    industry=_norm_industry(row.get("industry")),
                    benchmark_available=_parse_bool(row.get("benchmark_available")),
                    vehicle_available=_parse_bool(row.get("vehicle_available")),
                    stock_replay_available=_parse_bool(row.get("stock_replay_available")),
                    top_n_available=_parse_bool(row.get("top_n_available")),
                    replay_status=str(row.get("replay_status") or "").strip().upper(),
                    replay_mode=str(row.get("replay_mode") or "").strip().upper(),
                    generated_at_utc=str(row.get("generated_at_utc") or "").strip(),
                )
            )
    return out


def _load_partition_payloads(
    *,
    repo_root: Path,
    snapshot_date: str,
    registry_entries: list[_RegistryEntry],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    out: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    legacy_schema_normalized_count = 0
    replay_root = repo_root / "data" / "history" / "replays" / f"snapshot_date={snapshot_date}"

    for entry in registry_entries:
        replay_dir = replay_root / f"replay_id={entry.replay_id}"
        sel_path = replay_dir / "replay_selection.csv"
        ser_path = replay_dir / "replay_performance_series.csv"
        if not sel_path.exists() or not ser_path.exists():
            excluded.append(
                {
                    "replay_id": entry.replay_id,
                    "reason": "missing_partition_files",
                }
            )
            continue

        try:
            sel_rows = _read_csv(sel_path)
            ser_rows = _read_csv(ser_path)
        except Exception:
            excluded.append(
                {
                    "replay_id": entry.replay_id,
                    "reason": "partition_read_error",
                }
            )
            continue
        if len(sel_rows) != 1:
            excluded.append(
                {
                    "replay_id": entry.replay_id,
                    "reason": "selection_row_count_invalid",
                }
            )
            continue
        selection_row, normalized_legacy = _normalize_selection_row(sel_rows[0])
        if normalized_legacy:
            legacy_schema_normalized_count += 1

        if selection_row.get("replay_id") != entry.replay_id:
            excluded.append(
                {
                    "replay_id": entry.replay_id,
                    "reason": "selection_replay_id_mismatch",
                }
            )
            continue

        if str(selection_row.get("selected_symbols") or "").strip() == "":
            excluded.append(
                {
                    "replay_id": entry.replay_id,
                    "reason": "selection_selected_symbols_empty",
                }
            )
            continue

        run_token = _extract_run_token(entry.replay_id, entry)

        out.append(
            {
                "registry": entry,
                "replay_dir": replay_dir,
                "selection_row": selection_row,
                "series_rows": ser_rows,
                "run_token": run_token,
            }
        )

    return out, excluded, legacy_schema_normalized_count


def _normalize_selection_row(row: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    canonical = list(REPLAY_SELECTION_HEADERS)
    keys = list(row.keys())
    if keys == canonical:
        return row, False

    legacy = [h for h in canonical if h != "filter_analytical_subtier"]
    if keys == legacy:
        normalized: dict[str, Any] = {}
        for key in canonical:
            if key == "filter_analytical_subtier":
                normalized[key] = ""
            else:
                normalized[key] = row.get(key, "")
        return normalized, True

    raise ReplayReconstructionError(
        f"replay_selection schema mismatch in immutable partition. keys={keys}"
    )


def _select_latest_compatible_partitions(partitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not partitions:
        raise ReplayReconstructionError("No partitions were provided for selection.")

    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    compatibility_groups: dict[tuple[str, ...], set[tuple[str, str]]] = defaultdict(set)

    for p in partitions:
        row = p["selection_row"]
        stable_key = (
            str(row.get("filter_geography") or "").upper(),
            str(row.get("filter_market_cap_bucket") or "").upper(),
            _norm_industry(row.get("filter_industry")),
            str(row.get("filter_analytical_subtier") or "").upper(),
            str(row.get("selection_method") or "").upper(),
            str(row.get("top_n") or ""),
        )
        config_window = (
            str(row.get("start_date") or ""),
            str(row.get("end_date") or ""),
        )
        compatibility_groups[stable_key].add(config_window)
        grouped[(
            stable_key[0],
            stable_key[1],
            stable_key[2],
            stable_key[3],
            stable_key[4],
            stable_key[5],
            str(row.get("start_date") or ""),
            str(row.get("end_date") or ""),
            str(row.get("replay_mode") or "").upper(),
        )].append(p)

    incompatible = [k for k, v in compatibility_groups.items() if len(v) > 1]
    if incompatible:
        raise ReplayReconstructionError(
            "Detected mixed incompatible partition windows for the same replay selection scope."
        )

    selected: list[dict[str, Any]] = []
    for key, items in grouped.items():
        items_sorted = sorted(
            items,
            key=lambda x: (
                _safe_dt(x["registry"].generated_at_utc),
                x["registry"].replay_id,
            ),
            reverse=True,
        )
        selected.append(items_sorted[0])

    return selected


def _validate_candidate_schemas(inputs_rows: list[dict[str, Any]], series_rows: list[dict[str, Any]]) -> None:
    if not inputs_rows:
        raise ReplayReconstructionError("Candidate replay_inputs is empty.")
    if not series_rows:
        raise ReplayReconstructionError("Candidate replay_performance_series is empty.")

    input_keys = list(inputs_rows[0].keys())
    if input_keys != list(REPLAY_SELECTION_HEADERS):
        raise ReplayReconstructionError(
            f"replay_inputs schema mismatch. expected={list(REPLAY_SELECTION_HEADERS)} got={input_keys}"
        )

    series_keys = list(series_rows[0].keys())
    if series_keys != list(PERFORMANCE_SERIES_HEADERS):
        raise ReplayReconstructionError(
            f"replay_performance_series schema mismatch. expected={list(PERFORMANCE_SERIES_HEADERS)} got={series_keys}"
        )



def _validate_candidate_content(inputs_rows: list[dict[str, Any]], series_rows: list[dict[str, Any]]) -> None:
    today = date.today().isoformat()

    replay_ids: set[str] = set()
    input_dup = 0
    for row in inputs_rows:
        rid = str(row.get("replay_id") or "").strip()
        if not rid:
            raise ReplayReconstructionError("Found replay_inputs row with empty replay_id.")
        if rid in replay_ids:
            input_dup += 1
        replay_ids.add(rid)

        if str(row.get("selected_symbols") or "").strip() == "":
            raise ReplayReconstructionError(f"selected_symbols empty for replay_id={rid}.")

    if input_dup > 0:
        raise ReplayReconstructionError("Duplicate replay_id rows detected in candidate replay_inputs.")

    expected_types_by_replay: dict[str, set[str]] = defaultdict(set)
    for row in series_rows:
        rid = str(row.get("replay_id") or "").strip()
        if not rid:
            raise ReplayReconstructionError("Found replay_performance_series row with empty replay_id.")
        if rid not in replay_ids:
            raise ReplayReconstructionError(f"Orphan series row detected for replay_id={rid}.")

        st = str(row.get("series_type") or "").strip().upper()
        if not st:
            raise ReplayReconstructionError("Found replay_performance_series row with empty series_type.")

        d = str(row.get("date") or "").strip()
        if not _is_iso_date(d):
            raise ReplayReconstructionError(f"Invalid date value in replay_performance_series: {d}")
        if d > today:
            raise ReplayReconstructionError(f"Future date detected in replay_performance_series: {d}")

        try:
            float(str(row.get("value") or "").strip())
        except Exception as exc:
            raise ReplayReconstructionError(
                f"Invalid numeric value in replay_performance_series for replay_id={rid}: {row.get('value')}"
            ) from exc

        expected_types_by_replay[rid].add(st)

    semantic_keys_seen: set[tuple[str, str, str]] = set()
    for row in series_rows:
        key = (
            str(row.get("replay_id") or "").strip(),
            str(row.get("series_type") or "").strip().upper(),
            str(row.get("date") or "").strip(),
        )
        if key in semantic_keys_seen:
            raise ReplayReconstructionError(
                f"Duplicate replay_id+series_type+date key detected: {key}"
            )
        semantic_keys_seen.add(key)



def _validate_cohorts_and_scope(
    *,
    candidate_inputs: list[dict[str, Any]],
    required_cohorts: tuple[str, ...],
    expected_registry_industries: set[str],
) -> None:
    candidate_industries = {
        _norm_industry(row.get("filter_industry"))
        for row in candidate_inputs
        if _norm_industry(row.get("filter_industry"))
    }

    missing_required = [c for c in required_cohorts if c not in candidate_industries]
    if missing_required:
        raise ReplayReconstructionError(
            f"Missing required market-regime cohorts: {', '.join(missing_required)}"
        )

    if len(candidate_industries) <= 4:
        raise ReplayReconstructionError(
            "Candidate replay_inputs appears narrowed to too few industries."
        )

    if candidate_industries != expected_registry_industries:
        missing = sorted(expected_registry_industries - candidate_industries)
        extra = sorted(candidate_industries - expected_registry_industries)
        raise ReplayReconstructionError(
            "Candidate industry coverage mismatch with registry expected scope. "
            f"missing={missing}, extra={extra}"
        )



def _run_market_regime_semantic_validation(
    *,
    candidate_inputs_path: Path,
    candidate_series_path: Path,
    portfolio_snapshot_date_for_freshness: str,
) -> tuple[str | None, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="replay_reconstruct_semantic_") as td:
        root = Path(td)
        current = root / "data" / "current"
        current.mkdir(parents=True, exist_ok=True)
        current.joinpath("replay_inputs.csv").write_bytes(candidate_inputs_path.read_bytes())
        current.joinpath("replay_performance_series.csv").write_bytes(candidate_series_path.read_bytes())

        summary = rotation_risk_summary(root)
        latest_proxy_date_raw = ((summary.get("proxy_returns") or {}).get("latest_proxy_date") or "")
        latest_proxy_date = str(latest_proxy_date_raw).strip() or None
        if not latest_proxy_date:
            raise ReplayReconstructionError("Candidate rotation_risk_summary produced empty latest_proxy_date.")

        freshness = evaluate_market_proxy_freshness(
            market_proxies_ts=latest_proxy_date,
            portfolio_snapshot_ts=portfolio_snapshot_date_for_freshness,
        )

        if str(freshness.get("freshness_status") or "").upper() == "MISSING":
            raise ReplayReconstructionError("Candidate freshness evaluated to MISSING; expected STALE/FRESH with numeric lag.")

        if freshness.get("proxy_lag_days") is None and freshness.get("market_proxy_age_days") is None:
            raise ReplayReconstructionError("Candidate freshness did not produce numeric lag metrics.")

        return latest_proxy_date, freshness



def _extract_run_token(replay_id: str, entry: _RegistryEntry) -> str:
    suffix = replay_id
    top_match = re.search(r"-TOP\d+-", replay_id)
    if top_match:
        suffix = replay_id[top_match.end() :]

    tail = f"-{entry.geography}-{entry.market_cap_bucket}-{entry.industry.replace(' ', '_')}"
    if suffix.endswith(tail):
        suffix = suffix[: -len(tail)]

    return suffix.strip("-")



def _safe_dt(value: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        return datetime.min
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return datetime.min



def _norm_industry(v: Any) -> str:
    return str(v or "").strip().upper().replace("_", " ")



def _is_iso_date(v: str) -> bool:
    try:
        date.fromisoformat(v)
        return True
    except Exception:
        return False



def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))



def _write_csv(path: Path, headers: Iterable[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)



def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()



def _file_meta(path: Path, schema: Iterable[str]) -> dict[str, Any]:
    rows = _read_csv(path)
    out: dict[str, Any] = {
        "rows": len(rows),
        "sha256": _sha256(path),
        "schema": list(schema),
        "size_bytes": path.stat().st_size,
    }
    if path.name == "replay_performance_series.csv":
        dates = [str(r.get("date") or "").strip() for r in rows if str(r.get("date") or "").strip()]
        out["min_date"] = min(dates) if dates else ""
        out["max_date"] = max(dates) if dates else ""
    return out
