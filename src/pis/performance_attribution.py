"""PIS performance attribution derived from canonical-governed changes and lineage."""

from __future__ import annotations

import csv
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .recommendation_lineage import compute_recommendation_lineage
from .storage import _read_csv_rows, _to_float, _to_int


ATTRIBUTION_RECORD_HEADERS = [
    "attribution_id",
    "snapshot_id",
    "snapshot_date",
    "change_id",
    "symbol",
    "change_type",
    "matched_recommendation_id",
    "matched_recommendation",
    "recommendation_source",
    "recommendation_date",
    "confidence",
    "old_market_value",
    "new_market_value",
    "delta_market_value",
    "directional_attribution",
    "directional_return_pct",
    "outcome",
    "created_at",
]

ATTRIBUTION_SUMMARY_HEADERS = [
    "snapshot_id",
    "snapshot_date",
    "matched_recommendations",
    "winner_count",
    "neutral_count",
    "loser_count",
    "total_directional_attribution",
    "average_directional_return_pct",
    "top_winner_symbol",
    "top_loser_symbol",
    "created_at",
]


@dataclass(frozen=True)
class AttributionThresholds:
    winner_min_score: float = 50.0
    loser_max_score: float = -50.0


DEFAULT_ATTRIBUTION_THRESHOLDS = AttributionThresholds()
_ATTRIBUTION_REFRESH_LOCK = threading.Lock()


def _write_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _direction_multiplier(change_type: str) -> int:
    if change_type in {"NEW_POSITION", "INCREASED"}:
        return 1
    if change_type in {"EXITED_POSITION", "REDUCED"}:
        return -1
    return 0


def classify_outcome(
    directional_attribution: float,
    *,
    thresholds: AttributionThresholds = DEFAULT_ATTRIBUTION_THRESHOLDS,
) -> str:
    if directional_attribution >= thresholds.winner_min_score:
        return "WINNER"
    if directional_attribution <= thresholds.loser_max_score:
        return "LOSER"
    return "NEUTRAL"


def _map_record(row: dict[str, str]) -> dict[str, object]:
    return {
        "attribution_id": str(row.get("attribution_id", "")),
        "snapshot_id": str(row.get("snapshot_id", "")),
        "snapshot_date": str(row.get("snapshot_date", "")),
        "change_id": str(row.get("change_id", "")),
        "symbol": str(row.get("symbol", "")),
        "change_type": str(row.get("change_type", "")),
        "matched_recommendation_id": str(row.get("matched_recommendation_id", "")),
        "matched_recommendation": str(row.get("matched_recommendation", "")),
        "recommendation_source": str(row.get("recommendation_source", "")),
        "recommendation_date": str(row.get("recommendation_date", "")),
        "confidence": str(row.get("confidence", "")),
        "old_market_value": round(_to_float(row.get("old_market_value", 0)), 2),
        "new_market_value": round(_to_float(row.get("new_market_value", 0)), 2),
        "delta_market_value": round(_to_float(row.get("delta_market_value", 0)), 2),
        "directional_attribution": round(_to_float(row.get("directional_attribution", 0)), 2),
        "directional_return_pct": round(_to_float(row.get("directional_return_pct", 0)), 2),
        "outcome": str(row.get("outcome", "NEUTRAL")),
        "created_at": str(row.get("created_at", "")),
    }


def _map_summary(row: dict[str, str]) -> dict[str, object]:
    return {
        "snapshot_id": str(row.get("snapshot_id", "")),
        "snapshot_date": str(row.get("snapshot_date", "")),
        "matched_recommendations": _to_int(row.get("matched_recommendations", 0)),
        "winner_count": _to_int(row.get("winner_count", 0)),
        "neutral_count": _to_int(row.get("neutral_count", 0)),
        "loser_count": _to_int(row.get("loser_count", 0)),
        "total_directional_attribution": round(_to_float(row.get("total_directional_attribution", 0)), 2),
        "average_directional_return_pct": round(_to_float(row.get("average_directional_return_pct", 0)), 2),
        "top_winner_symbol": str(row.get("top_winner_symbol", "")),
        "top_loser_symbol": str(row.get("top_loser_symbol", "")),
        "created_at": str(row.get("created_at", "")),
    }


def _recommendation_ranked(records: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_recommendation: dict[str, dict[str, object]] = {}
    for row in records:
        recommendation_id = str(row.get("matched_recommendation_id", "")).strip()
        if not recommendation_id:
            continue
        agg = by_recommendation.setdefault(
            recommendation_id,
            {
                "matched_recommendation_id": recommendation_id,
                "matched_recommendation": str(row.get("matched_recommendation", "")),
                "recommendation_source": str(row.get("recommendation_source", "")),
                "count": 0,
                "total_directional_attribution": 0.0,
            },
        )
        agg["count"] = int(agg["count"]) + 1
        agg["total_directional_attribution"] = float(agg["total_directional_attribution"]) + float(
            row.get("directional_attribution", 0.0)
        )

    ranked = [
        {
            **row,
            "total_directional_attribution": round(float(row["total_directional_attribution"]), 2),
        }
        for row in by_recommendation.values()
    ]
    winners = [r for r in ranked if float(r["total_directional_attribution"]) > 0]
    losers = [r for r in ranked if float(r["total_directional_attribution"]) < 0]
    winners.sort(key=lambda r: float(r["total_directional_attribution"]), reverse=True)
    losers.sort(key=lambda r: float(r["total_directional_attribution"]))
    return winners[:5], losers[:5]


def _source_performance(records: list[dict[str, object]]) -> list[dict[str, object]]:
    by_source: dict[str, dict[str, object]] = {}
    for row in records:
        source = str(row.get("recommendation_source", "") or "OTHER")
        outcome = str(row.get("outcome", "NEUTRAL"))
        agg = by_source.setdefault(
            source,
            {
                "source": source,
                "matched_count": 0,
                "winner_count": 0,
                "neutral_count": 0,
                "loser_count": 0,
                "total_directional_attribution": 0.0,
                "win_rate_pct": 0.0,
            },
        )
        agg["matched_count"] = int(agg["matched_count"]) + 1
        if outcome == "WINNER":
            agg["winner_count"] = int(agg["winner_count"]) + 1
        elif outcome == "LOSER":
            agg["loser_count"] = int(agg["loser_count"]) + 1
        else:
            agg["neutral_count"] = int(agg["neutral_count"]) + 1
        agg["total_directional_attribution"] = float(agg["total_directional_attribution"]) + float(
            row.get("directional_attribution", 0.0)
        )

    output: list[dict[str, object]] = []
    for source, row in sorted(by_source.items(), key=lambda kv: kv[0]):
        matched_count = int(row["matched_count"])
        winner_count = int(row["winner_count"])
        row["source"] = source
        row["total_directional_attribution"] = round(float(row["total_directional_attribution"]), 2)
        row["win_rate_pct"] = round((winner_count / matched_count) * 100.0, 2) if matched_count else 0.0
        output.append(row)
    return output


def compute_performance_attribution(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    attribution_root: str | Path = "data/history/pis/attribution",
    repo_root: str | Path = ".",
    thresholds: AttributionThresholds = DEFAULT_ATTRIBUTION_THRESHOLDS,
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    change_records_path = Path(change_records_path)
    change_summary_path = Path(change_summary_path)
    lineage_root = Path(lineage_root)
    attribution_root = Path(attribution_root)

    lineage_records_path = lineage_root / "lineage_records.csv"
    lineage_summary_path = lineage_root / "lineage_summary.csv"
    need_lineage_recompute = (
        candidates_override is not None
        or not lineage_records_path.exists()
        or not lineage_summary_path.exists()
    )

    # Attribution derives from canonical-governed lineage and change artifacts.
    if need_lineage_recompute:
        compute_recommendation_lineage(
            change_records_path=change_records_path,
            change_summary_path=change_summary_path,
            lineage_root=lineage_root,
            repo_root=repo_root,
            candidates_override=candidates_override,
        )

    change_rows = _read_csv_rows(change_records_path)
    change_summary_rows = _read_csv_rows(change_summary_path)
    lineage_rows = _read_csv_rows(lineage_records_path)

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not change_rows or not change_summary_rows or not lineage_rows:
        _write_rows(attribution_root / "attribution_records.csv", ATTRIBUTION_RECORD_HEADERS, [])
        _write_rows(attribution_root / "attribution_summary.csv", ATTRIBUTION_SUMMARY_HEADERS, [])
        return {"attribution_records": [], "attribution_summary": []}

    change_by_id: dict[tuple[str, str], dict[str, str]] = {}
    for row in change_rows:
        snapshot_id = str(row.get("snapshot_id", ""))
        change_id = str(row.get("change_id", ""))
        if snapshot_id and change_id:
            change_by_id[(snapshot_id, change_id)] = row

    snapshot_dates = {
        str(row.get("snapshot_id", "")): str(row.get("snapshot_date", ""))
        for row in change_summary_rows
    }

    records: list[dict[str, object]] = []
    for lineage_row in lineage_rows:
        confidence = str(lineage_row.get("confidence", "")).upper()
        recommendation_id = str(lineage_row.get("matched_recommendation_id", "")).strip()
        if confidence == "NONE" or not recommendation_id:
            continue

        snapshot_id = str(lineage_row.get("snapshot_id", ""))
        change_id = str(lineage_row.get("change_id", ""))
        change_row = change_by_id.get((snapshot_id, change_id))
        if change_row is None:
            continue

        change_type = str(change_row.get("change_type", "")).upper()
        old_market_value = round(_to_float(change_row.get("old_market_value", 0)), 2)
        new_market_value = round(_to_float(change_row.get("new_market_value", 0)), 2)
        delta_market_value = round(_to_float(change_row.get("delta_market_value", 0)), 2)
        directional_attribution = round(delta_market_value * _direction_multiplier(change_type), 2)
        baseline = abs(old_market_value) if abs(old_market_value) > 0 else abs(new_market_value)
        directional_return_pct = round((directional_attribution / baseline) * 100.0, 2) if baseline > 0 else 0.0
        outcome = classify_outcome(directional_attribution, thresholds=thresholds)

        records.append(
            {
                "attribution_id": f"ATTR-{snapshot_id}-{change_id}",
                "snapshot_id": snapshot_id,
                "snapshot_date": snapshot_dates.get(snapshot_id, ""),
                "change_id": change_id,
                "symbol": str(change_row.get("symbol", "")),
                "change_type": change_type,
                "matched_recommendation_id": recommendation_id,
                "matched_recommendation": str(lineage_row.get("matched_recommendation", "")),
                "recommendation_source": str(lineage_row.get("recommendation_source", "")),
                "recommendation_date": str(lineage_row.get("recommendation_date", "")),
                "confidence": confidence,
                "old_market_value": old_market_value,
                "new_market_value": new_market_value,
                "delta_market_value": delta_market_value,
                "directional_attribution": directional_attribution,
                "directional_return_pct": directional_return_pct,
                "outcome": outcome,
                "created_at": created_at,
            }
        )

    records.sort(key=lambda row: (str(row.get("snapshot_date", "")), str(row.get("attribution_id", ""))), reverse=True)

    summary_rows: list[dict[str, object]] = []
    for summary_row in sorted(change_summary_rows, key=lambda row: str(row.get("snapshot_date", "")), reverse=True):
        snapshot_id = str(summary_row.get("snapshot_id", ""))
        snapshot_date = str(summary_row.get("snapshot_date", ""))
        if not snapshot_id:
            continue

        local = [row for row in records if str(row.get("snapshot_id", "")) == snapshot_id]
        winners = [row for row in local if str(row.get("outcome", "")) == "WINNER"]
        losers = [row for row in local if str(row.get("outcome", "")) == "LOSER"]
        neutral = [row for row in local if str(row.get("outcome", "")) == "NEUTRAL"]

        total_directional_attribution = round(sum(_to_float(row.get("directional_attribution", 0)) for row in local), 2)
        avg_return = (
            round(sum(_to_float(row.get("directional_return_pct", 0)) for row in local) / len(local), 2)
            if local
            else 0.0
        )
        top_winner = max(local, key=lambda row: _to_float(row.get("directional_attribution", 0))) if local else None
        top_loser = min(local, key=lambda row: _to_float(row.get("directional_attribution", 0))) if local else None

        summary_rows.append(
            {
                "snapshot_id": snapshot_id,
                "snapshot_date": snapshot_date,
                "matched_recommendations": len(local),
                "winner_count": len(winners),
                "neutral_count": len(neutral),
                "loser_count": len(losers),
                "total_directional_attribution": total_directional_attribution,
                "average_directional_return_pct": avg_return,
                "top_winner_symbol": str(top_winner.get("symbol", "")) if top_winner else "",
                "top_loser_symbol": str(top_loser.get("symbol", "")) if top_loser else "",
                "created_at": created_at,
            }
        )

    _write_rows(attribution_root / "attribution_records.csv", ATTRIBUTION_RECORD_HEADERS, records)
    _write_rows(attribution_root / "attribution_summary.csv", ATTRIBUTION_SUMMARY_HEADERS, summary_rows)

    return {
        "attribution_records": records,
        "attribution_summary": summary_rows,
    }


def _load_attribution_tables(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    attribution_root: str | Path = "data/history/pis/attribution",
    repo_root: str | Path = ".",
    thresholds: AttributionThresholds = DEFAULT_ATTRIBUTION_THRESHOLDS,
    candidates_override: list[dict[str, object]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    attribution_root = Path(attribution_root)
    records_path = attribution_root / "attribution_records.csv"
    summary_path = attribution_root / "attribution_summary.csv"
    need_recompute = (
        candidates_override is not None
        or thresholds != DEFAULT_ATTRIBUTION_THRESHOLDS
        or not records_path.exists()
        or not summary_path.exists()
    )

    if need_recompute:
        with _ATTRIBUTION_REFRESH_LOCK:
            compute_performance_attribution(
                change_records_path=change_records_path,
                change_summary_path=change_summary_path,
                lineage_root=lineage_root,
                attribution_root=attribution_root,
                repo_root=repo_root,
                thresholds=thresholds,
                candidates_override=candidates_override,
            )

    summary_rows = _read_csv_rows(summary_path)
    record_rows = _read_csv_rows(records_path)
    summary_rows.sort(key=lambda row: str(row.get("snapshot_date", "")), reverse=True)
    record_rows.sort(key=lambda row: (str(row.get("snapshot_date", "")), str(row.get("attribution_id", ""))), reverse=True)
    return summary_rows, record_rows


def pis_attribution_history(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    attribution_root: str | Path = "data/history/pis/attribution",
    repo_root: str | Path = ".",
    thresholds: AttributionThresholds = DEFAULT_ATTRIBUTION_THRESHOLDS,
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    summary_rows, _ = _load_attribution_tables(
        change_records_path=change_records_path,
        change_summary_path=change_summary_path,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=repo_root,
        thresholds=thresholds,
        candidates_override=candidates_override,
    )
    return {"summary": [_map_summary(row) for row in summary_rows]}


def pis_attribution_latest(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    attribution_root: str | Path = "data/history/pis/attribution",
    repo_root: str | Path = ".",
    thresholds: AttributionThresholds = DEFAULT_ATTRIBUTION_THRESHOLDS,
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    summary_rows, record_rows = _load_attribution_tables(
        change_records_path=change_records_path,
        change_summary_path=change_summary_path,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=repo_root,
        thresholds=thresholds,
        candidates_override=candidates_override,
    )

    if not summary_rows:
        return {
            "summary": None,
            "records": [],
            "top_winning_recommendations": [],
            "top_losing_recommendations": [],
            "source_performance": [],
        }

    latest_snapshot_id = str(summary_rows[0].get("snapshot_id", ""))
    latest_records = [_map_record(row) for row in record_rows if str(row.get("snapshot_id", "")) == latest_snapshot_id]
    latest_records.sort(key=lambda row: float(row.get("directional_attribution", 0)), reverse=True)

    top_winners, top_losers = _recommendation_ranked(latest_records)

    return {
        "summary": _map_summary(summary_rows[0]),
        "records": latest_records,
        "top_winning_recommendations": top_winners,
        "top_losing_recommendations": top_losers,
        "source_performance": _source_performance(latest_records),
    }


def pis_attribution_summary(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    attribution_root: str | Path = "data/history/pis/attribution",
    repo_root: str | Path = ".",
    thresholds: AttributionThresholds = DEFAULT_ATTRIBUTION_THRESHOLDS,
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    summary_rows, record_rows = _load_attribution_tables(
        change_records_path=change_records_path,
        change_summary_path=change_summary_path,
        lineage_root=lineage_root,
        attribution_root=attribution_root,
        repo_root=repo_root,
        thresholds=thresholds,
        candidates_override=candidates_override,
    )

    mapped_records = [_map_record(row) for row in record_rows]
    total_count = len(mapped_records)
    winner_count = sum(1 for row in mapped_records if str(row.get("outcome", "")) == "WINNER")
    neutral_count = sum(1 for row in mapped_records if str(row.get("outcome", "")) == "NEUTRAL")
    loser_count = sum(1 for row in mapped_records if str(row.get("outcome", "")) == "LOSER")
    total_directional_attribution = round(sum(_to_float(row.get("directional_attribution", 0)) for row in mapped_records), 2)
    avg_return_pct = round(
        sum(_to_float(row.get("directional_return_pct", 0)) for row in mapped_records) / total_count,
        2,
    ) if total_count else 0.0

    top_winners, top_losers = _recommendation_ranked(mapped_records)

    return {
        "summary": {
            "snapshot_count": len(summary_rows),
            "matched_recommendations": total_count,
            "winner_count": winner_count,
            "neutral_count": neutral_count,
            "loser_count": loser_count,
            "total_directional_attribution": total_directional_attribution,
            "average_directional_return_pct": avg_return_pct,
        },
        "top_winning_recommendations": top_winners,
        "top_losing_recommendations": top_losers,
        "source_performance": _source_performance(mapped_records),
    }
