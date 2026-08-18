from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def _is_populated(value: Any) -> bool:
    return bool(str(value or "").strip())


def count_nonblank_holdings_field(
    holdings_rows: Iterable[Mapping[str, Any]],
    *,
    field_name: str,
) -> int:
    return sum(1 for row in holdings_rows if _is_populated(row.get(field_name)))


def summarize_run_signal_coverage(run_dir: Path) -> dict[str, Any]:
    holdings_path = run_dir / "holdings.csv"
    if not holdings_path.exists():
        raise FileNotFoundError(f"Missing holdings.csv for run: {run_dir}")

    with holdings_path.open("r", encoding="utf-8", newline="") as fh:
        holdings_rows = list(csv.DictReader(fh))

    source_format = ""
    snapshot_path = run_dir / "snapshot.json"
    if snapshot_path.exists():
        try:
            snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            source_format = str(snapshot_payload.get("source_format") or "")
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            source_format = ""

    return {
        "run_id": run_dir.name,
        "source_format": source_format,
        "holdings_count": len(holdings_rows),
        "zacks_run_nonblank_holdings": count_nonblank_holdings_field(
            holdings_rows,
            field_name="zacks_rating",
        ),
        "danelfin_run_nonblank_holdings": count_nonblank_holdings_field(
            holdings_rows,
            field_name="danelfin_score",
        ),
    }
