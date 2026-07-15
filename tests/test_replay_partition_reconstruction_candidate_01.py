from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from src.replay.replay_engine import PERFORMANCE_SERIES_HEADERS, REPLAY_SELECTION_HEADERS
from src.replay.replay_partition_reconstruction import (
    ReplayReconstructionError,
    reconstruct_replay_current_candidate,
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _mk_series_rows(replay_id: str, start: str = "2026-05-01") -> list[dict[str, object]]:
    dates = [
        "2026-05-01",
        "2026-05-02",
        "2026-05-03",
        "2026-05-04",
        "2026-05-05",
        "2026-05-06",
        "2026-05-07",
    ]
    rows: list[dict[str, object]] = []
    for i, d in enumerate(dates):
        rows.append(
            {
                "series_id": f"{replay_id}:FULL_UNIVERSE",
                "replay_id": replay_id,
                "series_type": "FULL_UNIVERSE",
                "date": d,
                "value": 100.0 + i,
                "cumulative_return": i / 100.0,
                "source": "test",
                "coverage_status": "AVAILABLE",
            }
        )
        rows.append(
            {
                "series_id": f"{replay_id}:BENCHMARK",
                "replay_id": replay_id,
                "series_type": "BENCHMARK",
                "date": d,
                "value": 90.0 + i,
                "cumulative_return": i / 120.0,
                "source": "test",
                "coverage_status": "AVAILABLE",
            }
        )
        rows.append(
            {
                "series_id": f"{replay_id}:INVESTABLE_VEHICLE",
                "replay_id": replay_id,
                "series_type": "INVESTABLE_VEHICLE",
                "date": d,
                "value": 95.0 + i,
                "cumulative_return": i / 130.0,
                "source": "test",
                "coverage_status": "AVAILABLE",
            }
        )
        rows.append(
            {
                "series_id": f"{replay_id}:TOP_N_STRATEGY",
                "replay_id": replay_id,
                "series_type": "TOP_N_STRATEGY",
                "date": d,
                "value": 102.0 + i,
                "cumulative_return": i / 90.0,
                "source": "test",
                "coverage_status": "AVAILABLE",
            }
        )
    return rows


def _mk_selection_row(
    replay_id: str,
    industry: str,
    start_date: str = "2025-05-14",
    end_date: str = "2026-05-14",
    cap: str = "LARGE",
    geo: str = "US",
    subtier: str = "",
) -> dict[str, object]:
    return {
        "replay_id": replay_id,
        "start_date": start_date,
        "end_date": end_date,
        "filter_market_cap_bucket": cap,
        "filter_geography": geo,
        "filter_industry": industry,
        "filter_analytical_subtier": subtier,
        "selection_method": "TOP_N_COMPOSITE_AT_START",
        "top_n": 20,
        "selected_symbols": "AAA|BBB|CCC",
        "composite_score_snapshot_date": "2025-05-14",
        "replay_mode": "HISTORICAL_VALIDATION",
    }


def _mk_registry_row(
    replay_id: str,
    industry: str,
    generated_at: str,
    status: str = "AVAILABLE",
    start_date: str = "2025-05-14",
    end_date: str = "2026-05-14",
    geo: str = "US",
    cap: str = "LARGE",
) -> dict[str, object]:
    return {
        "replay_id": replay_id,
        "snapshot_date": "2025-05-14",
        "start_date": start_date,
        "end_date": end_date,
        "geography": geo,
        "market_cap_bucket": cap,
        "industry": industry,
        "benchmark_available": "true",
        "vehicle_available": "true",
        "stock_replay_available": "true",
        "top_n_available": "true",
        "replay_status": status,
        "replay_mode": "HISTORICAL_VALIDATION",
        "generated_at_utc": generated_at,
    }


def _materialize_partition(repo_root: Path, replay_id: str, selection_row: dict[str, object], series_rows: list[dict[str, object]]) -> None:
    pdir = repo_root / "data" / "history" / "replays" / "snapshot_date=2025-05-14" / f"replay_id={replay_id}"
    _write_csv(pdir / "replay_selection.csv", REPLAY_SELECTION_HEADERS, [selection_row])
    _write_csv(pdir / "replay_performance_series.csv", PERFORMANCE_SERIES_HEADERS, series_rows)


def _build_repo_fixture(tmp_path: Path, include_industry: list[str] | None = None) -> Path:
    repo_root = tmp_path / "repo"
    include_industry = include_industry or [
        "ALL",
        "TECHNOLOGY",
        "ENERGY",
        "BASIC MATERIALS",
        "INDUSTRIALS",
        "COMMUNICATION SERVICES",
    ]

    registry_rows: list[dict[str, object]] = []
    for idx, industry in enumerate(include_industry):
        rid = f"REPLAY-2025-05-14-TO-2026-05-14-US-LARGE-{industry.replace(' ', '_')}-TOP20-RUN-WP05D-TEST{idx:03d}-US-LARGE-{industry.replace(' ', '_')}"
        registry_rows.append(_mk_registry_row(rid, industry, f"2026-05-15T00:00:{idx:02d}+00:00"))
        _materialize_partition(repo_root, rid, _mk_selection_row(rid, industry), _mk_series_rows(rid))

    reg_path = repo_root / "data" / "history" / "replay_snapshot_registry.csv"
    _write_csv(
        reg_path,
        [
            "replay_id",
            "snapshot_date",
            "start_date",
            "end_date",
            "geography",
            "market_cap_bucket",
            "industry",
            "benchmark_available",
            "vehicle_available",
            "stock_replay_available",
            "top_n_available",
            "replay_status",
            "replay_mode",
            "generated_at_utc",
        ],
        registry_rows,
    )

    return repo_root


def test_reconstructs_candidate_files_with_manifest_and_validation(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    out = tmp_path / "candidate"

    result = reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=out,
        portfolio_snapshot_date_for_freshness="2026-07-15",
    )

    assert Path(result["candidate_inputs_path"]).exists()
    assert Path(result["candidate_series_path"]).exists()
    assert Path(result["manifest_path"]).exists()
    assert Path(result["validation_path"]).exists()

    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["published"] is False
    assert manifest["mode"] == "candidate_only"
    assert manifest["candidate_files"]["replay_inputs.csv"]["rows"] > 0
    assert manifest["candidate_files"]["replay_performance_series.csv"]["rows"] > 0


def test_canonical_schemas_are_preserved(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    out = tmp_path / "candidate"
    result = reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=out,
    )
    manifest = result["manifest"]
    assert manifest["candidate_files"]["replay_inputs.csv"]["schema"] == REPLAY_SELECTION_HEADERS
    assert manifest["candidate_files"]["replay_performance_series.csv"]["schema"] == PERFORMANCE_SERIES_HEADERS


def test_candidate_includes_broader_scope_not_just_four_industries(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    out = tmp_path / "candidate"
    result = reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=out,
    )
    industries = set(result["manifest"]["industry_counts"].keys())
    assert len(industries) > 4
    assert {"TECHNOLOGY", "ENERGY", "BASIC MATERIALS", "INDUSTRIALS"}.issubset(industries)


def test_rejects_missing_required_cohort(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path, include_industry=["ALL", "TECHNOLOGY", "ENERGY", "INDUSTRIALS"])
    with pytest.raises(ReplayReconstructionError, match="Missing required market-regime cohorts"):
        reconstruct_replay_current_candidate(
            repo_root=repo_root,
            snapshot_date="2025-05-14",
            output_root=tmp_path / "candidate",
        )


def test_rejects_incomplete_expected_broader_scope(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    # Corrupt one partition selection to create registry-vs-candidate industry mismatch.
    reg = repo_root / "data" / "history" / "replay_snapshot_registry.csv"
    rows = list(csv.DictReader(reg.open("r", encoding="utf-8", newline="")))
    target = rows[-1]
    rid = target["replay_id"]
    sel = repo_root / "data" / "history" / "replays" / "snapshot_date=2025-05-14" / f"replay_id={rid}" / "replay_selection.csv"
    sel_rows = list(csv.DictReader(sel.open("r", encoding="utf-8", newline="")))
    sel_rows[0]["filter_industry"] = "ENERGY"
    _write_csv(sel, REPLAY_SELECTION_HEADERS, sel_rows)

    with pytest.raises(ReplayReconstructionError, match="industry coverage mismatch"):
        reconstruct_replay_current_candidate(
            repo_root=repo_root,
            snapshot_date="2025-05-14",
            output_root=tmp_path / "candidate",
        )


def test_rejects_incompatible_selection_schema(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    reg = repo_root / "data" / "history" / "replay_snapshot_registry.csv"
    row = list(csv.DictReader(reg.open("r", encoding="utf-8", newline="")))[0]
    rid = row["replay_id"]
    sel = repo_root / "data" / "history" / "replays" / "snapshot_date=2025-05-14" / f"replay_id={rid}" / "replay_selection.csv"
    bad_headers = [h for h in REPLAY_SELECTION_HEADERS if h != "top_n"]
    bad_row = {k: "" for k in bad_headers}
    bad_row["replay_id"] = rid
    _write_csv(sel, bad_headers, [bad_row])

    with pytest.raises(ReplayReconstructionError, match="schema mismatch"):
        reconstruct_replay_current_candidate(
            repo_root=repo_root,
            snapshot_date="2025-05-14",
            output_root=tmp_path / "candidate",
        )


def test_rejects_duplicate_semantic_series_keys(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    reg = repo_root / "data" / "history" / "replay_snapshot_registry.csv"
    rid = list(csv.DictReader(reg.open("r", encoding="utf-8", newline="")))[0]["replay_id"]
    ser = repo_root / "data" / "history" / "replays" / "snapshot_date=2025-05-14" / f"replay_id={rid}" / "replay_performance_series.csv"
    rows = list(csv.DictReader(ser.open("r", encoding="utf-8", newline="")))
    rows.append(dict(rows[0]))
    _write_csv(ser, PERFORMANCE_SERIES_HEADERS, rows)

    with pytest.raises(ReplayReconstructionError, match=r"Duplicate replay_id\+series_type\+date"):
        reconstruct_replay_current_candidate(
            repo_root=repo_root,
            snapshot_date="2025-05-14",
            output_root=tmp_path / "candidate",
        )


def test_rejects_orphan_performance_rows(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    reg = repo_root / "data" / "history" / "replay_snapshot_registry.csv"
    rid = list(csv.DictReader(reg.open("r", encoding="utf-8", newline="")))[0]["replay_id"]
    ser = repo_root / "data" / "history" / "replays" / "snapshot_date=2025-05-14" / f"replay_id={rid}" / "replay_performance_series.csv"
    rows = list(csv.DictReader(ser.open("r", encoding="utf-8", newline="")))
    rows[0]["replay_id"] = "ORPHAN-REPLAY-ID"
    _write_csv(ser, PERFORMANCE_SERIES_HEADERS, rows)

    with pytest.raises(ReplayReconstructionError, match="Orphan series row"):
        reconstruct_replay_current_candidate(
            repo_root=repo_root,
            snapshot_date="2025-05-14",
            output_root=tmp_path / "candidate",
        )


def test_rejects_mixed_incompatible_window_configurations(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path, include_industry=["ALL", "TECHNOLOGY", "ENERGY", "BASIC MATERIALS", "INDUSTRIALS"])

    # Add duplicate scope with conflicting dates.
    rid = "REPLAY-2025-05-14-TO-2026-06-30-US-LARGE-TECHNOLOGY-TOP20-RUN-WP05D-CONFLICT-US-LARGE-TECHNOLOGY"
    reg = repo_root / "data" / "history" / "replay_snapshot_registry.csv"
    rows = list(csv.DictReader(reg.open("r", encoding="utf-8", newline="")))
    rows.append(_mk_registry_row(rid, "TECHNOLOGY", "2026-05-16T00:00:00+00:00", start_date="2025-05-14", end_date="2026-06-30"))
    _write_csv(
        reg,
        [
            "replay_id",
            "snapshot_date",
            "start_date",
            "end_date",
            "geography",
            "market_cap_bucket",
            "industry",
            "benchmark_available",
            "vehicle_available",
            "stock_replay_available",
            "top_n_available",
            "replay_status",
            "replay_mode",
            "generated_at_utc",
        ],
        rows,
    )
    _materialize_partition(
        repo_root,
        rid,
        _mk_selection_row(rid, "TECHNOLOGY", end_date="2026-06-30"),
        _mk_series_rows(rid),
    )

    with pytest.raises(ReplayReconstructionError, match="mixed incompatible partition windows"):
        reconstruct_replay_current_candidate(
            repo_root=repo_root,
            snapshot_date="2025-05-14",
            output_root=tmp_path / "candidate",
        )


def test_excludes_unqualified_registry_statuses(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    reg = repo_root / "data" / "history" / "replay_snapshot_registry.csv"
    rows = list(csv.DictReader(reg.open("r", encoding="utf-8", newline="")))
    rows.append(
        _mk_registry_row(
            replay_id="REPLAY-2025-05-14-TO-2026-05-14-US-LARGE-HEALTHCARE-TOP20-RUN-WP05D-BLOCKED-US-LARGE-HEALTHCARE",
            industry="HEALTHCARE",
            generated_at="2026-05-17T00:00:00+00:00",
            status="BLOCKED",
        )
    )
    _write_csv(
        reg,
        [
            "replay_id",
            "snapshot_date",
            "start_date",
            "end_date",
            "geography",
            "market_cap_bucket",
            "industry",
            "benchmark_available",
            "vehicle_available",
            "stock_replay_available",
            "top_n_available",
            "replay_status",
            "replay_mode",
            "generated_at_utc",
        ],
        rows,
    )

    result = reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=tmp_path / "candidate",
    )
    assert "HEALTHCARE" not in result["manifest"]["industry_counts"]


def test_deterministic_hashes_across_repeated_runs(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    out1 = tmp_path / "candidate1"
    out2 = tmp_path / "candidate2"

    r1 = reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=out1,
        restoration_id="R1",
    )
    r2 = reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=out2,
        restoration_id="R2",
    )

    assert _sha256(Path(r1["candidate_inputs_path"])) == _sha256(Path(r2["candidate_inputs_path"]))
    assert _sha256(Path(r1["candidate_series_path"])) == _sha256(Path(r2["candidate_series_path"]))


def test_semantic_validation_reports_stale_not_missing(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    result = reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=tmp_path / "candidate",
        portfolio_snapshot_date_for_freshness="2026-07-15",
    )

    freshness = result["validation_report"]["semantic_market_regime"]["freshness"]
    latest_proxy = result["validation_report"]["semantic_market_regime"]["latest_proxy_date"]
    assert latest_proxy
    assert freshness["freshness_status"] in {"STALE", "FRESH"}
    assert freshness["freshness_status"] != "MISSING"
    assert freshness.get("proxy_lag_days") is not None


def test_rejects_output_path_equal_to_data_current(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)
    with pytest.raises(ReplayReconstructionError, match="must not be data/current"):
        reconstruct_replay_current_candidate(
            repo_root=repo_root,
            snapshot_date="2025-05-14",
            output_root=repo_root / "data" / "current",
        )


def test_real_current_artifacts_and_immutable_sources_unchanged(tmp_path: Path) -> None:
    repo_root = _build_repo_fixture(tmp_path)

    current_root = repo_root / "data" / "current"
    current_root.mkdir(parents=True, exist_ok=True)
    current_inputs = current_root / "replay_inputs.csv"
    current_series = current_root / "replay_performance_series.csv"
    current_inputs.write_text("replay_id\nDUMMY\n", encoding="utf-8")
    current_series.write_text("series_id,replay_id,series_type,date,value,cumulative_return,source,coverage_status\nX,D,TOP_N_STRATEGY,2026-01-01,1,0,s,AVAILABLE\n", encoding="utf-8")

    imm_sample = next((repo_root / "data" / "history" / "replays" / "snapshot_date=2025-05-14").glob("replay_id=*/replay_selection.csv"))

    before_current_inputs = _sha256(current_inputs)
    before_current_series = _sha256(current_series)
    before_immutable = _sha256(imm_sample)

    reconstruct_replay_current_candidate(
        repo_root=repo_root,
        snapshot_date="2025-05-14",
        output_root=tmp_path / "candidate",
    )

    assert _sha256(current_inputs) == before_current_inputs
    assert _sha256(current_series) == before_current_series
    assert _sha256(imm_sample) == before_immutable
