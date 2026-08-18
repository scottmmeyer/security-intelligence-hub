from __future__ import annotations

import csv
import json
from pathlib import Path

from src.validation.run_signal_coverage import (
    count_nonblank_holdings_field,
    summarize_run_signal_coverage,
)


def _write_holdings(run_dir: Path, rows: list[dict[str, str]]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    headers = sorted({k for row in rows for k in row.keys()})
    with (run_dir / "holdings.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _write_snapshot(run_dir: Path, *, source_format: str) -> None:
    payload = {
        "source_format": source_format,
        "snapshot_date": "2026-08-17",
    }
    (run_dir / "snapshot.json").write_text(json.dumps(payload), encoding="utf-8")


def test_count_nonblank_holdings_field_uses_zacks_rating() -> None:
    rows = [
        {"symbol": "AAA", "zacks_rating": "5.0", "zacks_score": ""},
        {"symbol": "BBB", "zacks_rating": "", "zacks_score": "4.0"},
        {"symbol": "CCC", "zacks_rating": "3.0"},
    ]
    assert count_nonblank_holdings_field(rows, field_name="zacks_rating") == 2


def test_summarize_run_signal_coverage_ignores_missing_zacks_score(tmp_path: Path) -> None:
    run_dir = tmp_path / "PAR-TEST-ZACKS"
    _write_holdings(
        run_dir,
        rows=[
            {"symbol": "AAA", "zacks_rating": "5.0", "danelfin_score": "9"},
            {"symbol": "BBB", "zacks_rating": "", "danelfin_score": "8"},
            {"symbol": "CCC", "danelfin_score": "7"},
        ],
    )
    _write_snapshot(run_dir, source_format="FIDELITY_CSV")

    summary = summarize_run_signal_coverage(run_dir)
    assert summary["source_format"] == "FIDELITY_CSV"
    assert summary["zacks_run_nonblank_holdings"] == 1
    assert summary["danelfin_run_nonblank_holdings"] == 3


def test_summarize_run_signal_coverage_reports_54_for_fidelity_and_generic(tmp_path: Path) -> None:
    rows = [
        {
            "symbol": f"SYM{i:03d}",
            "zacks_rating": "4.0" if i <= 54 else "",
            "danelfin_score": "8.0" if i <= 54 else "",
        }
        for i in range(1, 78)
    ]

    fidelity_dir = tmp_path / "PAR-FIDELITY"
    generic_dir = tmp_path / "PAR-GENERIC"
    _write_holdings(fidelity_dir, rows)
    _write_snapshot(fidelity_dir, source_format="FIDELITY_CSV")
    _write_holdings(generic_dir, rows)
    _write_snapshot(generic_dir, source_format="GENERIC_CSV")

    fidelity_summary = summarize_run_signal_coverage(fidelity_dir)
    generic_summary = summarize_run_signal_coverage(generic_dir)

    assert fidelity_summary["zacks_run_nonblank_holdings"] == 54
    assert generic_summary["zacks_run_nonblank_holdings"] == 54
    assert fidelity_summary["danelfin_run_nonblank_holdings"] == 54
    assert generic_summary["danelfin_run_nonblank_holdings"] == 54
