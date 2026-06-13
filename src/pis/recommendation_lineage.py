"""PIS recommendation lineage matching for observed portfolio changes."""

from __future__ import annotations

import csv
import json
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .change_detection import compute_all_snapshot_changes
from .storage import _read_csv_rows, _to_int


LINEAGE_HEADERS = [
    "lineage_id",
    "snapshot_id",
    "change_id",
    "symbol",
    "change_type",
    "matched_recommendation_id",
    "matched_recommendation",
    "recommendation_source",
    "recommendation_date",
    "confidence",
    "days_between",
    "created_at",
]

LINEAGE_SUMMARY_HEADERS = [
    "snapshot_id",
    "snapshot_date",
    "total_changes",
    "matched_high",
    "matched_medium",
    "matched_low",
    "unmatched",
    "matched_pap",
    "matched_cra",
    "matched_deployment_queue",
    "matched_reduction_queue",
    "matched_dil",
    "matched_other",
    "created_at",
]

_SOURCE_BREAKDOWN_ORDER = ["PAP", "CRA", "DEPLOYMENT_QUEUE", "REDUCTION_QUEUE", "DIL", "OTHER"]
_CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
_LINEAGE_REFRESH_LOCK = threading.Lock()


def _write_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _parse_date(raw: object) -> date | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _action_to_direction(raw: object) -> str:
    value = str(raw or "").strip().upper()
    if not value:
        return ""
    if any(token in value for token in ("BUY", "INCREASE", "ADD", "ACCUMULATE", "DEPLOY")):
        return "BUY"
    if any(token in value for token in ("REDUCE", "SELL", "TRIM", "EXIT")):
        return "REDUCE"
    return ""


def _change_to_direction(change_type: str) -> str:
    if change_type in {"NEW_POSITION", "INCREASED"}:
        return "BUY"
    if change_type in {"EXITED_POSITION", "REDUCED"}:
        return "REDUCE"
    return ""


def _source_from_recommendation(rec: dict[str, Any]) -> str:
    rec_type = str(rec.get("recommendation_type", "")).upper()
    action = _action_to_direction(rec.get("effective_action", ""))

    if rec_type in {"INCREASE_UNDERWEIGHT", "REDUCE_OVERWEIGHT"}:
        return "CRA"
    if rec_type in {"STRATEGIC_TRIM_CANDIDATE"}:
        return "REDUCTION_QUEUE"
    if action == "REDUCE" and str(rec.get("card_type", "")).upper() == "ACTION":
        return "REDUCTION_QUEUE"
    if rec_type.startswith("STRATEGIC_") or rec_type in {
        "PORTFOLIO_CONSTRUCTION_NARRATIVE",
        "REPLAY_ALIGNMENT_CONTEXT",
        "IMPROVE_REPLAY_ALIGNMENT",
    }:
        return "PAP"
    return "RECOMMENDATION_HISTORY"


def _normalize_source_for_summary(source: str) -> str:
    upper = str(source or "").upper()
    if upper in {"PAP", "CRA", "DEPLOYMENT_QUEUE", "REDUCTION_QUEUE", "DIL"}:
        return upper
    return "OTHER"


def _safe_json_load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_recommendation_candidates(run_dir: Path, run_date: date | None) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    recs = _safe_json_load(run_dir / "recommendations.json")
    if not isinstance(recs, list):
        return candidates

    for rec in recs:
        if not isinstance(rec, dict):
            continue
        recommendation_id = str(rec.get("recommendation_id", "")).strip()
        if not recommendation_id:
            continue

        rec_date = _parse_date(rec.get("created_at_utc")) or run_date
        if rec_date is None:
            continue

        source = _source_from_recommendation(rec)
        effective_action = _action_to_direction(rec.get("effective_action", ""))
        title = str(rec.get("title", "")).strip()
        rec_type = str(rec.get("recommendation_type", "")).strip().upper()

        theme_symbols: list[str] = []
        drilldown = rec.get("drilldown")
        if isinstance(drilldown, dict):
            holdings = drilldown.get("holdings")
            if isinstance(holdings, list):
                theme_symbols = sorted(
                    {
                        str(h.get("symbol", "")).strip().upper()
                        for h in holdings
                        if isinstance(h, dict) and str(h.get("symbol", "")).strip()
                    }
                )

        affected = rec.get("affected_symbols")
        affected_symbols = (
            [str(v).strip().upper() for v in affected if str(v).strip()]
            if isinstance(affected, list)
            else []
        )

        # Symbol-level candidates.
        for symbol in sorted(set(affected_symbols)):
            candidates.append(
                {
                    "recommendation_id": recommendation_id,
                    "source": source,
                    "recommendation_date": rec_date.isoformat(),
                    "symbol": symbol,
                    "direction": effective_action,
                    "matched_recommendation": title or f"{rec_type} {symbol}".strip(),
                    "theme_symbols": theme_symbols,
                }
            )

        # Theme-level candidate for recommendations without explicit symbols.
        if not affected_symbols:
            node_key = str(rec.get("affected_node_key", "")).strip()
            if node_key or theme_symbols:
                candidates.append(
                    {
                        "recommendation_id": recommendation_id,
                        "source": source,
                        "recommendation_date": rec_date.isoformat(),
                        "symbol": "",
                        "direction": effective_action,
                        "matched_recommendation": title or rec_type,
                        "theme_symbols": theme_symbols,
                    }
                )

    return candidates


def _extract_deployment_candidates(run_dir: Path, run_id: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    plan = _safe_json_load(run_dir / "deployment_plan.json")
    if not isinstance(plan, dict):
        return candidates

    rec_date = _parse_date(plan.get("generated_at"))
    if rec_date is None:
        return candidates

    for idx, row in enumerate(plan.get("recommendations", []), start=1):
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        recommendation_id = f"DP-{run_id}-{idx:03d}-{symbol}"
        candidates.append(
            {
                "recommendation_id": recommendation_id,
                "source": "DEPLOYMENT_QUEUE",
                "recommendation_date": rec_date.isoformat(),
                "symbol": symbol,
                "direction": "BUY",
                "matched_recommendation": f"DEPLOY {symbol}",
                "theme_symbols": [],
            }
        )

    return candidates


def _extract_dil_candidates(run_dir: Path, run_id: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    dil = _safe_json_load(run_dir / "ucf_verdicts.json")
    if not isinstance(dil, dict):
        return candidates

    rec_date = _parse_date(dil.get("generated_at"))
    if rec_date is None:
        return candidates

    for row in dil.get("verdicts", []):
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        label = str(row.get("ucf_label", "")).upper()
        if label in {"CORE_CONVICTION_LEADER", "HIGH_CONVICTION_ANCHOR", "DEPLOYMENT_CANDIDATE"}:
            direction = "BUY"
        elif label in {"TRIM_WATCH"}:
            direction = "REDUCE"
        else:
            continue

        recommendation_id = f"DIL-{run_id}-{symbol}"
        candidates.append(
            {
                "recommendation_id": recommendation_id,
                "source": "DIL",
                "recommendation_date": rec_date.isoformat(),
                "symbol": symbol,
                "direction": direction,
                "matched_recommendation": f"DIL {label} {symbol}",
                "theme_symbols": [],
            }
        )

    return candidates


def build_recommendation_candidates(
    *,
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
) -> list[dict[str, object]]:
    root = Path(analysis_runs_root)
    if not root.exists():
        return []

    candidates: list[dict[str, object]] = []
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        run_id = run_dir.name
        metadata = _safe_json_load(run_dir / "run_metadata.json")
        run_date = _parse_date(metadata.get("snapshot_date")) if isinstance(metadata, dict) else None

        candidates.extend(_extract_recommendation_candidates(run_dir, run_date))
        candidates.extend(_extract_deployment_candidates(run_dir, run_id))
        candidates.extend(_extract_dil_candidates(run_dir, run_id))

    # Deterministic stable ordering.
    candidates.sort(
        key=lambda r: (
            str(r.get("recommendation_date", "")),
            str(r.get("source", "")),
            str(r.get("recommendation_id", "")),
            str(r.get("symbol", "")),
        )
    )
    return candidates


def _theme_match(change_symbol: str, candidate: dict[str, object]) -> bool:
    if str(candidate.get("symbol", "")).strip():
        return False
    theme_symbols = candidate.get("theme_symbols", [])
    if isinstance(theme_symbols, list):
        return change_symbol in {str(v).strip().upper() for v in theme_symbols if str(v).strip()}
    return False


def _match_confidence(
    *,
    change_symbol: str,
    change_direction: str,
    snapshot_date: date,
    candidate: dict[str, object],
    candidates: list[dict[str, object]],
) -> tuple[str, int]:
    rec_date = _parse_date(candidate.get("recommendation_date"))
    if rec_date is None:
        return "NONE", 9999

    days_between = (snapshot_date - rec_date).days
    if days_between < 0 or days_between > 90:
        return "NONE", 9999

    symbol = str(candidate.get("symbol", "")).strip().upper()
    direction = str(candidate.get("direction", "")).strip().upper()
    symbol_match = symbol == change_symbol
    direction_match = bool(change_direction) and direction == change_direction
    theme_match = _theme_match(change_symbol, candidate)

    if symbol_match and direction_match and days_between <= 7:
        competing = 0
        for other in candidates:
            if str(other.get("recommendation_id", "")) == str(candidate.get("recommendation_id", "")):
                continue
            other_date = _parse_date(other.get("recommendation_date"))
            if other_date is None:
                continue
            other_days = (snapshot_date - other_date).days
            if other_days < 0 or other_days > 7:
                continue
            if str(other.get("symbol", "")).strip().upper() == change_symbol and str(other.get("direction", "")).upper() == change_direction:
                competing += 1
        if competing == 0:
            return "HIGH", days_between

    if (symbol_match and direction_match and days_between <= 30) or (theme_match and direction_match and days_between <= 30):
        return "MEDIUM", days_between

    if (symbol_match and direction_match and days_between <= 90) or (theme_match and days_between <= 90):
        return "LOW", days_between

    return "NONE", days_between


def _best_match(
    *,
    change_symbol: str,
    change_direction: str,
    snapshot_date: date,
    candidates: list[dict[str, object]],
) -> tuple[dict[str, object] | None, str, int]:
    best: dict[str, object] | None = None
    best_confidence = "NONE"
    best_days = 9999

    for candidate in candidates:
        confidence, days_between = _match_confidence(
            change_symbol=change_symbol,
            change_direction=change_direction,
            snapshot_date=snapshot_date,
            candidate=candidate,
            candidates=candidates,
        )
        if _CONFIDENCE_RANK[confidence] < _CONFIDENCE_RANK[best_confidence]:
            continue
        if _CONFIDENCE_RANK[confidence] == _CONFIDENCE_RANK[best_confidence] and days_between >= best_days:
            continue
        best = candidate
        best_confidence = confidence
        best_days = days_between

    if best is None or best_confidence == "NONE":
        return None, "NONE", 9999
    return best, best_confidence, best_days


def compute_recommendation_lineage(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    repo_root: str | Path = ".",
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    change_records_path = Path(change_records_path)
    change_summary_path = Path(change_summary_path)
    lineage_root = Path(lineage_root)
    root = Path(repo_root)

    if not change_records_path.exists() or not change_summary_path.exists():
        compute_all_snapshot_changes(repo_root=root)

    change_rows = _read_csv_rows(change_records_path)
    summary_rows = _read_csv_rows(change_summary_path)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not change_rows or not summary_rows:
        _write_rows(lineage_root / "lineage_records.csv", LINEAGE_HEADERS, [])
        _write_rows(lineage_root / "lineage_summary.csv", LINEAGE_SUMMARY_HEADERS, [])
        return {"lineage_records": [], "lineage_summary": []}

    candidates = list(candidates_override or build_recommendation_candidates(analysis_runs_root=root / "data/portfolio_ingestion/analysis_runs"))

    lineage_rows: list[dict[str, object]] = []
    summary_out: list[dict[str, object]] = []

    change_rows_by_snapshot: dict[str, list[dict[str, str]]] = {}
    for row in change_rows:
        change_rows_by_snapshot.setdefault(str(row.get("snapshot_id", "")), []).append(row)

    for summary in summary_rows:
        snapshot_id = str(summary.get("snapshot_id", ""))
        snapshot_date_raw = str(summary.get("snapshot_date", ""))
        snapshot_date = _parse_date(snapshot_date_raw)
        if not snapshot_id or snapshot_date is None:
            continue

        selected_changes = [
            row
            for row in change_rows_by_snapshot.get(snapshot_id, [])
            if str(row.get("change_type", "")) in {"NEW_POSITION", "EXITED_POSITION", "INCREASED", "REDUCED"}
        ]

        local_rows: list[dict[str, object]] = []
        for row in selected_changes:
            symbol = str(row.get("symbol", "")).strip().upper()
            change_type = str(row.get("change_type", "")).strip().upper()
            change_id = str(row.get("change_id", "")).strip()
            direction = _change_to_direction(change_type)

            best, confidence, days_between = _best_match(
                change_symbol=symbol,
                change_direction=direction,
                snapshot_date=snapshot_date,
                candidates=candidates,
            )

            if best is None:
                local_rows.append(
                    {
                        "lineage_id": f"LIN-{snapshot_id}-{change_id}",
                        "snapshot_id": snapshot_id,
                        "change_id": change_id,
                        "symbol": symbol,
                        "change_type": change_type,
                        "matched_recommendation_id": "",
                        "matched_recommendation": "",
                        "recommendation_source": "",
                        "recommendation_date": "",
                        "confidence": "NONE",
                        "days_between": "",
                        "created_at": created_at,
                    }
                )
                continue

            local_rows.append(
                {
                    "lineage_id": f"LIN-{snapshot_id}-{change_id}",
                    "snapshot_id": snapshot_id,
                    "change_id": change_id,
                    "symbol": symbol,
                    "change_type": change_type,
                    "matched_recommendation_id": str(best.get("recommendation_id", "")),
                    "matched_recommendation": str(best.get("matched_recommendation", "")),
                    "recommendation_source": str(best.get("source", "")),
                    "recommendation_date": str(best.get("recommendation_date", "")),
                    "confidence": confidence,
                    "days_between": int(days_between),
                    "created_at": created_at,
                }
            )

        lineage_rows.extend(local_rows)

        total_changes = len(local_rows)
        matched_high = sum(1 for r in local_rows if str(r.get("confidence", "")) == "HIGH")
        matched_medium = sum(1 for r in local_rows if str(r.get("confidence", "")) == "MEDIUM")
        matched_low = sum(1 for r in local_rows if str(r.get("confidence", "")) == "LOW")
        unmatched = sum(1 for r in local_rows if str(r.get("confidence", "")) == "NONE")

        by_source = {k: 0 for k in _SOURCE_BREAKDOWN_ORDER}
        for row in local_rows:
            confidence = str(row.get("confidence", "")).upper()
            if confidence == "NONE":
                continue
            normalized = _normalize_source_for_summary(str(row.get("recommendation_source", "")))
            by_source[normalized] += 1

        summary_out.append(
            {
                "snapshot_id": snapshot_id,
                "snapshot_date": snapshot_date_raw,
                "total_changes": total_changes,
                "matched_high": matched_high,
                "matched_medium": matched_medium,
                "matched_low": matched_low,
                "unmatched": unmatched,
                "matched_pap": by_source["PAP"],
                "matched_cra": by_source["CRA"],
                "matched_deployment_queue": by_source["DEPLOYMENT_QUEUE"],
                "matched_reduction_queue": by_source["REDUCTION_QUEUE"],
                "matched_dil": by_source["DIL"],
                "matched_other": by_source["OTHER"],
                "created_at": created_at,
            }
        )

    _write_rows(lineage_root / "lineage_records.csv", LINEAGE_HEADERS, lineage_rows)
    _write_rows(lineage_root / "lineage_summary.csv", LINEAGE_SUMMARY_HEADERS, summary_out)

    return {"lineage_records": lineage_rows, "lineage_summary": summary_out}


def _load_lineage_tables(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    repo_root: str | Path = ".",
    candidates_override: list[dict[str, object]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    lineage_root = Path(lineage_root)
    change_records_path = Path(change_records_path)
    change_summary_path = Path(change_summary_path)
    root = Path(repo_root)
    records_path = lineage_root / "lineage_records.csv"
    summary_path = lineage_root / "lineage_summary.csv"
    # Read paths should stay fast. Recompute only when lineage artifacts are missing,
    # or when tests explicitly provide override candidates.
    need_recompute = (
        candidates_override is not None
        or not records_path.exists()
        or not summary_path.exists()
    )

    if need_recompute:
        with _LINEAGE_REFRESH_LOCK:
            still_needed = (
                candidates_override is not None
                or not records_path.exists()
                or not summary_path.exists()
            )
            if still_needed:
                compute_recommendation_lineage(
                    change_records_path=change_records_path,
                    change_summary_path=change_summary_path,
                    lineage_root=lineage_root,
                    repo_root=root,
                    candidates_override=candidates_override,
                )

    summary_rows = _read_csv_rows(summary_path)
    record_rows = _read_csv_rows(records_path)
    summary_rows.sort(key=lambda r: str(r.get("snapshot_date", "")), reverse=True)
    return summary_rows, record_rows


def _lineage_payload_for_snapshot(
    snapshot_id: str,
    *,
    summary_rows: list[dict[str, str]],
    record_rows: list[dict[str, str]],
) -> dict[str, object]:
    target_summary = next((r for r in summary_rows if str(r.get("snapshot_id", "")) == snapshot_id), None)
    if target_summary is None:
        return {
            "summary": None,
            "matches": [],
            "unmatched": [],
            "source_breakdown": [],
        }

    details = [r for r in record_rows if str(r.get("snapshot_id", "")) == snapshot_id]
    matches = [
        {
            "lineage_id": str(r.get("lineage_id", "")),
            "change_id": str(r.get("change_id", "")),
            "symbol": str(r.get("symbol", "")),
            "change_type": str(r.get("change_type", "")),
            "matched_recommendation_id": str(r.get("matched_recommendation_id", "")),
            "matched_recommendation": str(r.get("matched_recommendation", "")),
            "recommendation_source": str(r.get("recommendation_source", "")),
            "recommendation_date": str(r.get("recommendation_date", "")),
            "confidence": str(r.get("confidence", "")),
            "days_between": _to_int(r.get("days_between", 0)),
        }
        for r in details
        if str(r.get("confidence", "")).upper() != "NONE"
    ]
    unmatched = [
        {
            "lineage_id": str(r.get("lineage_id", "")),
            "change_id": str(r.get("change_id", "")),
            "symbol": str(r.get("symbol", "")),
            "change_type": str(r.get("change_type", "")),
            "confidence": "NONE",
        }
        for r in details
        if str(r.get("confidence", "")).upper() == "NONE"
    ]

    source_breakdown = [
        {"source": "PAP", "count": _to_int(target_summary.get("matched_pap", 0))},
        {"source": "CRA", "count": _to_int(target_summary.get("matched_cra", 0))},
        {"source": "DEPLOYMENT_QUEUE", "count": _to_int(target_summary.get("matched_deployment_queue", 0))},
        {"source": "REDUCTION_QUEUE", "count": _to_int(target_summary.get("matched_reduction_queue", 0))},
        {"source": "DIL", "count": _to_int(target_summary.get("matched_dil", 0))},
        {"source": "OTHER", "count": _to_int(target_summary.get("matched_other", 0))},
    ]

    mapped_summary = {
        "snapshot_id": str(target_summary.get("snapshot_id", "")),
        "snapshot_date": str(target_summary.get("snapshot_date", "")),
        "total_changes": _to_int(target_summary.get("total_changes", 0)),
        "matched_high": _to_int(target_summary.get("matched_high", 0)),
        "matched_medium": _to_int(target_summary.get("matched_medium", 0)),
        "matched_low": _to_int(target_summary.get("matched_low", 0)),
        "unmatched": _to_int(target_summary.get("unmatched", 0)),
    }

    return {
        "summary": mapped_summary,
        "matches": matches,
        "unmatched": unmatched,
        "source_breakdown": source_breakdown,
    }


def pis_lineage_summary(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    repo_root: str | Path = ".",
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    summary_rows, _ = _load_lineage_tables(
        change_records_path=change_records_path,
        change_summary_path=change_summary_path,
        lineage_root=lineage_root,
        repo_root=repo_root,
        candidates_override=candidates_override,
    )

    out: list[dict[str, object]] = []
    for row in summary_rows:
        out.append(
            {
                "snapshot_id": str(row.get("snapshot_id", "")),
                "snapshot_date": str(row.get("snapshot_date", "")),
                "total_changes": _to_int(row.get("total_changes", 0)),
                "matched_high": _to_int(row.get("matched_high", 0)),
                "matched_medium": _to_int(row.get("matched_medium", 0)),
                "matched_low": _to_int(row.get("matched_low", 0)),
                "unmatched": _to_int(row.get("unmatched", 0)),
                "matched_pap": _to_int(row.get("matched_pap", 0)),
                "matched_cra": _to_int(row.get("matched_cra", 0)),
                "matched_deployment_queue": _to_int(row.get("matched_deployment_queue", 0)),
                "matched_reduction_queue": _to_int(row.get("matched_reduction_queue", 0)),
                "matched_dil": _to_int(row.get("matched_dil", 0)),
                "matched_other": _to_int(row.get("matched_other", 0)),
                "created_at": str(row.get("created_at", "")),
            }
        )
    return {"summary": out}


def pis_lineage_for_snapshot(
    snapshot_id: str,
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    repo_root: str | Path = ".",
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    summary_rows, record_rows = _load_lineage_tables(
        change_records_path=change_records_path,
        change_summary_path=change_summary_path,
        lineage_root=lineage_root,
        repo_root=repo_root,
        candidates_override=candidates_override,
    )

    return _lineage_payload_for_snapshot(
        snapshot_id,
        summary_rows=summary_rows,
        record_rows=record_rows,
    )


def pis_lineage_latest(
    *,
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    change_summary_path: str | Path = "data/history/pis/changes/change_summary.csv",
    lineage_root: str | Path = "data/history/pis/lineage",
    repo_root: str | Path = ".",
    candidates_override: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    summary_rows, record_rows = _load_lineage_tables(
        change_records_path=change_records_path,
        change_summary_path=change_summary_path,
        lineage_root=lineage_root,
        repo_root=repo_root,
        candidates_override=candidates_override,
    )

    if not summary_rows:
        return {
            "summary": None,
            "matches": [],
            "unmatched": [],
            "source_breakdown": [],
        }

    latest_snapshot_id = str(summary_rows[0].get("snapshot_id", ""))
    return _lineage_payload_for_snapshot(
        latest_snapshot_id,
        summary_rows=summary_rows,
        record_rows=record_rows,
    )
