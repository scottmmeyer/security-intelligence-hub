"""Deterministic explainability layer for portfolio recommendations."""

from __future__ import annotations

import csv
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPLANATION_VERSION = "1"

EXPLANATION_HEADERS = [
    "recommendation_id",
    "analysis_run_id",
    "snapshot_date",
    "symbol",
    "recommendation_type",
    "primary_reason",
    "supporting_reasons_json",
    "signal_drivers_json",
    "policy_drivers_json",
    "funding_drivers_json",
    "philosophy_drivers_json",
    "explanation_version",
    "created_at_utc",
]

SUMMARY_HEADERS = [
    "analysis_run_id",
    "snapshot_date",
    "recommendation_count",
    "explainable_count",
    "multi_driver_count",
    "policy_driver_count",
    "signal_driver_count",
    "funding_driver_count",
    "philosophy_breakdown_json",
    "created_at_utc",
]

_REFRESH_LOCK = threading.Lock()
_FUNDING_RE = re.compile(
    r"Funding source:\s*(?P<source>[A-Za-z ]+)\s*\((?P<symbols>[^)]*?),\s*~(?P<pct>[0-9.]+)% available\)",
    re.IGNORECASE,
)
_FUNDING_ALTERNATIVES_RE = re.compile(
    r"Alternatives considered:\s*(?P<alts>[^.]+)\.",
    re.IGNORECASE,
)
_FUNDING_POLICY_RE = re.compile(
    r"Policy alignment:\s*(?P<policy>[^.]+)\.",
    re.IGNORECASE,
)


def _write_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_json_load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_first_symbol(rec: dict[str, Any]) -> str:
    affected = rec.get("affected_symbols")
    if isinstance(affected, list):
        for value in affected:
            symbol = str(value or "").strip().upper()
            if symbol:
                return symbol
    return ""


def _split_sentences(text: str) -> list[str]:
    value = str(text or "").strip()
    if not value:
        return []
    parts = re.split(r"(?<=[.!?])\s+", value)
    return [part.strip() for part in parts if part.strip()]


def _json_dump(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _source_label_for_recommendation(rec_type: str) -> str:
    value = str(rec_type or "").upper()
    if value in {"INCREASE_UNDERWEIGHT", "REDUCE_OVERWEIGHT", "DIVERSIFY_CONCENTRATION", "IMPROVE_REPLAY_ALIGNMENT", "IMPROVE_RISK_PROFILE", "PORTFOLIO_CONSTRUCTION_NARRATIVE", "THEMATIC_SATURATION_NARRATIVE", "TOP_TRIM_CANDIDATES", "STRATEGIC_RETAIN_NARRATIVE", "CONCENTRATION_ECOSYSTEM"}:
        return "PAP"
    return "SIH"


def _philosophy_scores(rec: dict[str, Any]) -> list[dict[str, object]]:
    rec_type = str(rec.get("recommendation_type", "")).upper()
    scores = {
        "Concentrated Alpha": 0,
        "Capital Rotation": 0,
        "Risk Reduction": 0,
        "Cash Deployment": 0,
        "Dislocation Recovery": 0,
    }

    if rec_type in {"PORTFOLIO_CONSTRUCTION_NARRATIVE", "STRATEGIC_RETAIN_NARRATIVE", "THEMATIC_SATURATION_NARRATIVE", "CONCENTRATION_ECOSYSTEM"}:
        scores["Concentrated Alpha"] += 3
    if rec_type in {"INCREASE_UNDERWEIGHT", "IMPROVE_REPLAY_ALIGNMENT"}:
        scores["Concentrated Alpha"] += 2
    if rec_type in {"IMPROVE_REPLAY_ALIGNMENT"}:
        scores["Dislocation Recovery"] += 2
    if rec_type in {"INCREASE_UNDERWEIGHT"}:
        scores["Cash Deployment"] += 3
    if rec_type in {"REDUCE_OVERWEIGHT", "TOP_TRIM_CANDIDATES", "STRATEGIC_TRIM_CANDIDATE"}:
        scores["Capital Rotation"] += 3
    if rec_type in {"REDUCE_OVERWEIGHT", "DIVERSIFY_CONCENTRATION", "IMPROVE_RISK_PROFILE", "TOP_TRIM_CANDIDATES", "STRATEGIC_TRIM_CANDIDATE"}:
        scores["Risk Reduction"] += 3

    if rec.get("replay_run_ids"):
        scores["Concentrated Alpha"] += 1
        scores["Dislocation Recovery"] += 1

    execution_state = str(rec.get("execution_state", "")).upper()
    if execution_state in {"BLOCKED_BY_POLICY", "DEFERRED_BY_POLICY"}:
        scores["Capital Rotation"] += 1
        scores["Risk Reduction"] += 1

    ranked = [
        {"philosophy": name, "score": score}
        for name, score in scores.items()
        if score > 0
    ]
    ranked.sort(key=lambda row: (-int(row["score"]), str(row["philosophy"])))
    return ranked


def _policy_drivers(rec: dict[str, Any]) -> list[dict[str, object]]:
    drivers: list[dict[str, object]] = []
    execution_state = str(rec.get("execution_state", "")).upper()
    if execution_state and execution_state != "EXECUTABLE":
        drivers.append({
            "driver_type": "execution_state",
            "value": execution_state,
        })

    mandate_label = str(rec.get("mandate_drift_label", "")).upper()
    if mandate_label:
        drivers.append({
            "driver_type": "mandate_drift_label",
            "value": mandate_label,
        })

    mandate_urgency = str(rec.get("mandate_urgency", "")).upper()
    if mandate_urgency:
        drivers.append({
            "driver_type": "mandate_urgency",
            "value": mandate_urgency,
        })

    symbol_states = rec.get("symbol_execution_states")
    if isinstance(symbol_states, dict):
        for symbol, state in sorted(symbol_states.items()):
            if not isinstance(state, dict):
                continue
            policy_type = str(state.get("policy_type", "")).upper()
            if policy_type:
                drivers.append({
                    "driver_type": "symbol_policy",
                    "symbol": str(symbol).upper(),
                    "value": policy_type,
                })
    return drivers


def _funding_drivers(rec: dict[str, Any]) -> list[dict[str, object]]:
    rationale = str(rec.get("rationale", ""))
    match = _FUNDING_RE.search(rationale)
    if not match:
        return []
    source = "_".join(match.group("source").strip().upper().split())
    symbols = [segment.strip().upper() for segment in match.group("symbols").split(",") if segment.strip()]
    drivers: list[dict[str, object]] = [{
        "driver_type": "funding_source",
        "source_type": source,
        "symbols": symbols,
        "available_pct": float(match.group("pct")),
    }]

    alt_match = _FUNDING_ALTERNATIVES_RE.search(rationale)
    if alt_match:
        alternatives = [part.strip().upper().replace(" ", "_") for part in alt_match.group("alts").split(",") if part.strip()]
        if alternatives:
            drivers.append({
                "driver_type": "funding_alternatives",
                "alternatives": alternatives,
            })

    policy_match = _FUNDING_POLICY_RE.search(rationale)
    if policy_match:
        drivers.append({
            "driver_type": "funding_policy_alignment",
            "value": policy_match.group("policy").strip(),
        })

    return drivers


def _signal_drivers(rec: dict[str, Any], run_dir: Path) -> list[dict[str, object]]:
    drivers: list[dict[str, object]] = []
    drilldown = rec.get("drilldown")
    if isinstance(drilldown, dict):
        holdings = drilldown.get("holdings")
        if isinstance(holdings, list):
            for holding in holdings[:5]:
                if not isinstance(holding, dict):
                    continue
                symbol = str(holding.get("symbol", "")).strip().upper()
                if not symbol:
                    continue
                composite = holding.get("composite_score")
                if composite not in {None, ""}:
                    drivers.append({"source": "CW-DAS", "symbol": symbol, "value": composite})
                ess = str(holding.get("ess_score_text", "")).strip().upper()
                if ess:
                    drivers.append({"source": "ESS", "symbol": symbol, "value": ess})
                zacks = str(holding.get("zacks_rating", "")).strip().upper()
                if zacks:
                    drivers.append({"source": "Zacks", "symbol": symbol, "value": zacks})
                danelfin = holding.get("danelfin_score")
                if danelfin not in {None, ""}:
                    drivers.append({"source": "Danelfin", "symbol": symbol, "value": danelfin})
                cw_das = holding.get("cw_das_score")
                if cw_das not in {None, ""}:
                    drivers.append({"source": "CW-DAS", "symbol": symbol, "value": cw_das})

    consensus = _safe_json_load(run_dir / "analyst_consensus.json")
    if isinstance(consensus, dict):
        first_symbol = _safe_first_symbol(rec)
        payload = consensus.get(first_symbol)
        if isinstance(payload, dict):
            for key in ("consensus_label", "price_target", "abr"):
                value = payload.get(key)
                if value not in {None, ""}:
                    drivers.append({"source": "Yahoo", "symbol": first_symbol, "field": key, "value": value})

    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, object]] = []
    for row in drivers:
        key = (str(row.get("source", "")), str(row.get("symbol", "")), str(row.get("field", "value")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _supporting_reasons(rec: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    rationale_sentences = _split_sentences(str(rec.get("rationale", "")))
    if len(rationale_sentences) > 1:
        reasons.extend(rationale_sentences[1:3])
    evidence_summary = str(rec.get("evidence_summary", "")).strip()
    if evidence_summary:
        reasons.append(evidence_summary)
    reasoning_trace = str(rec.get("reasoning_trace", "")).strip()
    if reasoning_trace:
        reasons.append(reasoning_trace)
    if rec.get("severity"):
        reasons.append(f"Severity: {rec['severity']}")
    if rec.get("drift_pct") not in {None, ""}:
        reasons.append(f"Drift: {float(rec['drift_pct']):+.1f}pp")
    # preserve order, remove duplicates
    output: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        normalized = reason.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _primary_reason(rec: dict[str, Any]) -> str:
    rationale_sentences = _split_sentences(str(rec.get("rationale", "")))
    if rationale_sentences:
        return rationale_sentences[0]
    title = str(rec.get("title", "")).strip()
    return title or "Recommendation explanation unavailable."


def build_recommendation_explanation(rec: dict[str, Any], run_dir: Path, snapshot_date: str, analysis_run_id: str) -> dict[str, object]:
    symbol = _safe_first_symbol(rec)
    signal_drivers = _signal_drivers(rec, run_dir)
    policy_drivers = _policy_drivers(rec)
    funding_drivers = _funding_drivers(rec)
    philosophy_drivers = _philosophy_scores(rec)
    return {
        "recommendation_id": str(rec.get("recommendation_id", "")),
        "analysis_run_id": analysis_run_id,
        "snapshot_date": snapshot_date,
        "symbol": symbol,
        "recommendation_type": str(rec.get("recommendation_type", "")),
        "primary_reason": _primary_reason(rec),
        "supporting_reasons": _supporting_reasons(rec),
        "signal_drivers": signal_drivers,
        "policy_drivers": policy_drivers,
        "funding_drivers": funding_drivers,
        "philosophy_drivers": philosophy_drivers,
        "explanation_version": EXPLANATION_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_label": _source_label_for_recommendation(str(rec.get("recommendation_type", ""))),
    }


def refresh_allocation_explanations(
    *,
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    output_root: str | Path = "data/history/explanations",
) -> dict[str, object]:
    root = Path(analysis_runs_root)
    output_root = Path(output_root)
    explanation_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    if not root.exists():
        _write_rows(output_root / "recommendation_explanations.csv", EXPLANATION_HEADERS, [])
        _write_rows(output_root / "explanation_summary.csv", SUMMARY_HEADERS, [])
        return {"explanations": [], "summary": []}

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for run_dir in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name):
        recommendations = _safe_json_load(run_dir / "recommendations.json")
        run_metadata = _safe_json_load(run_dir / "run_metadata.json")
        if not isinstance(recommendations, list) or not isinstance(run_metadata, dict):
            continue
        analysis_run_id = str(run_metadata.get("run_id", run_dir.name))
        snapshot_date = str(run_metadata.get("snapshot_date", ""))
        run_explanations: list[dict[str, object]] = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            recommendation_id = str(rec.get("recommendation_id", "")).strip()
            if not recommendation_id:
                continue
            explanation = build_recommendation_explanation(rec, run_dir, snapshot_date, analysis_run_id)
            run_explanations.append(explanation)
            explanation_rows.append({
                "recommendation_id": explanation["recommendation_id"],
                "analysis_run_id": explanation["analysis_run_id"],
                "snapshot_date": explanation["snapshot_date"],
                "symbol": explanation["symbol"],
                "recommendation_type": explanation["recommendation_type"],
                "primary_reason": explanation["primary_reason"],
                "supporting_reasons_json": _json_dump(explanation["supporting_reasons"]),
                "signal_drivers_json": _json_dump(explanation["signal_drivers"]),
                "policy_drivers_json": _json_dump(explanation["policy_drivers"]),
                "funding_drivers_json": _json_dump(explanation["funding_drivers"]),
                "philosophy_drivers_json": _json_dump(explanation["philosophy_drivers"]),
                "explanation_version": explanation["explanation_version"],
                "created_at_utc": created_at,
            })

        philosophy_counts: dict[str, int] = {}
        for explanation in run_explanations:
            for row in explanation["philosophy_drivers"]:
                philosophy = str(row.get("philosophy", ""))
                if philosophy:
                    philosophy_counts[philosophy] = philosophy_counts.get(philosophy, 0) + 1

        summary_rows.append({
            "analysis_run_id": analysis_run_id,
            "snapshot_date": snapshot_date,
            "recommendation_count": len(recommendations),
            "explainable_count": len(run_explanations),
            "multi_driver_count": sum(1 for e in run_explanations if len(e["philosophy_drivers"]) > 1),
            "policy_driver_count": sum(1 for e in run_explanations if e["policy_drivers"]),
            "signal_driver_count": sum(1 for e in run_explanations if e["signal_drivers"]),
            "funding_driver_count": sum(1 for e in run_explanations if e["funding_drivers"]),
            "philosophy_breakdown_json": _json_dump(philosophy_counts),
            "created_at_utc": created_at,
        })

    explanation_rows.sort(key=lambda row: (str(row.get("snapshot_date", "")), str(row.get("recommendation_id", ""))), reverse=True)
    summary_rows.sort(key=lambda row: str(row.get("snapshot_date", "")), reverse=True)
    _write_rows(output_root / "recommendation_explanations.csv", EXPLANATION_HEADERS, explanation_rows)
    _write_rows(output_root / "explanation_summary.csv", SUMMARY_HEADERS, summary_rows)
    return {"explanations": explanation_rows, "summary": summary_rows}


def _ensure_tables(
    *,
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    output_root: str | Path = "data/history/explanations",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    output_root = Path(output_root)
    explanations_path = output_root / "recommendation_explanations.csv"
    summary_path = output_root / "explanation_summary.csv"
    if not explanations_path.exists() or not summary_path.exists():
        with _REFRESH_LOCK:
            if not explanations_path.exists() or not summary_path.exists():
                refresh_allocation_explanations(analysis_runs_root=analysis_runs_root, output_root=output_root)
    return _read_csv_rows(explanations_path), _read_csv_rows(summary_path)


def _map_explanation_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "recommendation_id": str(row.get("recommendation_id", "")),
        "analysis_run_id": str(row.get("analysis_run_id", "")),
        "snapshot_date": str(row.get("snapshot_date", "")),
        "symbol": str(row.get("symbol", "")),
        "recommendation_type": str(row.get("recommendation_type", "")),
        "primary_reason": str(row.get("primary_reason", "")),
        "supporting_reasons": json.loads(str(row.get("supporting_reasons_json", "[]") or "[]")),
        "signal_drivers": json.loads(str(row.get("signal_drivers_json", "[]") or "[]")),
        "policy_drivers": json.loads(str(row.get("policy_drivers_json", "[]") or "[]")),
        "funding_drivers": json.loads(str(row.get("funding_drivers_json", "[]") or "[]")),
        "philosophy_drivers": json.loads(str(row.get("philosophy_drivers_json", "[]") or "[]")),
        "explanation_version": str(row.get("explanation_version", EXPLANATION_VERSION)),
        "created_at_utc": str(row.get("created_at_utc", "")),
    }


def explanations_latest(
    *,
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    output_root: str | Path = "data/history/explanations",
) -> dict[str, object]:
    explanations, summaries = _ensure_tables(analysis_runs_root=analysis_runs_root, output_root=output_root)
    if not summaries:
        return {"analysis_run_id": "", "snapshot_date": "", "explanations": [], "summary": None}
    latest_run_id = str(summaries[0].get("analysis_run_id", ""))
    latest_rows = [_map_explanation_row(row) for row in explanations if str(row.get("analysis_run_id", "")) == latest_run_id]
    return {
        "analysis_run_id": latest_run_id,
        "snapshot_date": str(summaries[0].get("snapshot_date", "")),
        "explanations": latest_rows,
        "summary": {
            "recommendation_count": int(float(str(summaries[0].get("recommendation_count", 0)) or 0)),
            "explainable_count": int(float(str(summaries[0].get("explainable_count", 0)) or 0)),
            "multi_driver_count": int(float(str(summaries[0].get("multi_driver_count", 0)) or 0)),
        },
    }


def explanation_for_recommendation(
    recommendation_id: str,
    *,
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    output_root: str | Path = "data/history/explanations",
) -> dict[str, object]:
    explanations, _ = _ensure_tables(analysis_runs_root=analysis_runs_root, output_root=output_root)
    row = next((row for row in explanations if str(row.get("recommendation_id", "")) == recommendation_id), None)
    if row is None:
        return {"explanation": None}
    return {"explanation": _map_explanation_row(row)}


def explanation_summary(
    *,
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    output_root: str | Path = "data/history/explanations",
) -> dict[str, object]:
    explanations, summaries = _ensure_tables(analysis_runs_root=analysis_runs_root, output_root=output_root)
    mapped_summaries = []
    for row in summaries:
        mapped_summaries.append({
            "analysis_run_id": str(row.get("analysis_run_id", "")),
            "snapshot_date": str(row.get("snapshot_date", "")),
            "recommendation_count": int(float(str(row.get("recommendation_count", 0)) or 0)),
            "explainable_count": int(float(str(row.get("explainable_count", 0)) or 0)),
            "multi_driver_count": int(float(str(row.get("multi_driver_count", 0)) or 0)),
            "policy_driver_count": int(float(str(row.get("policy_driver_count", 0)) or 0)),
            "signal_driver_count": int(float(str(row.get("signal_driver_count", 0)) or 0)),
            "funding_driver_count": int(float(str(row.get("funding_driver_count", 0)) or 0)),
            "philosophy_breakdown": json.loads(str(row.get("philosophy_breakdown_json", "{}") or "{}")),
            "created_at_utc": str(row.get("created_at_utc", "")),
        })
    source_counts: dict[str, int] = {}
    for row in explanations:
        rec_type = str(row.get("recommendation_type", ""))
        source = _source_label_for_recommendation(rec_type)
        source_counts[source] = source_counts.get(source, 0) + 1
    return {
        "history": mapped_summaries,
        "source_summary": source_counts,
    }


def explanations_for_run(
    analysis_run_id: str,
    *,
    analysis_runs_root: str | Path = "data/portfolio_ingestion/analysis_runs",
    output_root: str | Path = "data/history/explanations",
) -> dict[str, dict[str, object]]:
    explanations, _ = _ensure_tables(analysis_runs_root=analysis_runs_root, output_root=output_root)
    return {
        str(row.get("recommendation_id", "")): _map_explanation_row(row)
        for row in explanations
        if str(row.get("analysis_run_id", "")) == analysis_run_id
    }
