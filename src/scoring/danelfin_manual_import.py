from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from src.scoring.fetch_danelfin_scores import (
    _DEFAULT_OUTPUT_DIR,
    _OUTPUT_HEADERS,
    _load_rows_by_symbol,
    _write_csv,
)


MANUAL_ACQUISITION_METHOD = "MANUAL_DANELFIN_UI"
DEFAULT_OPERATOR_SOURCE = "PAIR_PAGE"
PROVENANCE_FILENAME = "latest_danelfin.provenance.json"


@dataclass(frozen=True)
class ManualDanelfinObservation:
    symbol: str
    danelfin_raw: int
    sourced_date: str
    operator_source: str = DEFAULT_OPERATOR_SOURCE
    acquisition_method: str = MANUAL_ACQUISITION_METHOD
    observed_at: str | None = None


def _normalize_symbol(symbol: object) -> str:
    return str(symbol or "").strip().upper()


def _parse_raw_score(raw_score: object) -> int:
    text = str(raw_score or "").strip()
    if not text:
        raise ValueError("Danelfin raw score is required.")
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"Invalid Danelfin raw score: {text!r}") from exc
    if not value.is_integer():
        raise ValueError(f"Danelfin raw score must be integer-compatible: {text!r}")
    integer_value = int(value)
    if not 1 <= integer_value <= 10:
        raise ValueError(f"Danelfin raw score must be between 1 and 10: {integer_value}")
    return integer_value


def _validate_source_date(sourced_date: object, *, allow_future: bool = False) -> str:
    text = str(sourced_date or "").strip()
    if not text:
        raise ValueError("Danelfin source date is required.")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Invalid Danelfin source date: {text!r}") from exc
    if not allow_future and parsed > date.today():
        raise ValueError(f"Danelfin source date cannot be in the future: {text!r}")
    return parsed.isoformat()


def _normalize_observation(
    observation: ManualDanelfinObservation | dict[str, object],
    *,
    allow_future: bool = False,
) -> ManualDanelfinObservation:
    if isinstance(observation, ManualDanelfinObservation):
        symbol = _normalize_symbol(observation.symbol)
        raw = observation.danelfin_raw
        sourced_date = observation.sourced_date
        operator_source = str(observation.operator_source or DEFAULT_OPERATOR_SOURCE).strip() or DEFAULT_OPERATOR_SOURCE
        acquisition_method = str(observation.acquisition_method or MANUAL_ACQUISITION_METHOD).strip() or MANUAL_ACQUISITION_METHOD
        observed_at = observation.observed_at
    else:
        symbol = _normalize_symbol(observation.get("symbol"))
        raw = observation.get("danelfin_raw")
        sourced_date = observation.get("sourced_date")
        operator_source = str(observation.get("operator_source") or DEFAULT_OPERATOR_SOURCE).strip() or DEFAULT_OPERATOR_SOURCE
        acquisition_method = str(observation.get("acquisition_method") or MANUAL_ACQUISITION_METHOD).strip() or MANUAL_ACQUISITION_METHOD
        observed_at = observation.get("observed_at")
    if not symbol:
        raise ValueError("Danelfin symbol is required.")
    normalized_date = _validate_source_date(sourced_date, allow_future=allow_future)
    normalized_raw = _parse_raw_score(raw)
    observed_text = str(observed_at or "").strip() or None
    return ManualDanelfinObservation(
        symbol=symbol,
        danelfin_raw=normalized_raw,
        sourced_date=normalized_date,
        operator_source=operator_source,
        acquisition_method=acquisition_method,
        observed_at=observed_text,
    )


def _row_is_valid(row: dict[str, str] | None) -> bool:
    if not row:
        return False
    raw_text = str(row.get("danelfin_raw", "")).strip()
    score_text = str(row.get("danelfin_score", "")).strip()
    if not raw_text and not score_text:
        return False
    try:
        raw_value = int(raw_text)
        score_value = float(score_text)
    except (TypeError, ValueError):
        return False
    if not 1 <= raw_value <= 10:
        return False
    return abs(score_value - round(raw_value / 2.0, 4)) < 1e-9


def _row_quality(row: dict[str, str] | None) -> str:
    if not row:
        return "EMPTY_NO_DATA"
    raw_text = str(row.get("danelfin_raw", "")).strip()
    score_text = str(row.get("danelfin_score", "")).strip()
    if not raw_text and not score_text:
        return "EMPTY_NO_DATA"
    if not raw_text or not score_text:
        return "MALFORMED"
    if _row_is_valid(row):
        return "VALID_SCORE"
    return "MALFORMED"


def _row_sourced_date(row: dict[str, str] | None) -> str:
    if not row:
        return ""
    return str(row.get("sourced_date", "")).strip()


def _manual_row(observation: ManualDanelfinObservation) -> dict[str, str]:
    return {
        "symbol": observation.symbol,
        "danelfin_raw": str(observation.danelfin_raw),
        "danelfin_score": f"{observation.danelfin_raw / 2.0:.4f}",
        "sourced_date": observation.sourced_date,
    }


def _merge_manual_row(
    existing: dict[str, str] | None,
    manual_row: dict[str, str],
) -> tuple[dict[str, str] | None, str | None]:
    if existing is None:
        return manual_row, None

    existing_quality = _row_quality(existing)
    incoming_quality = _row_quality(manual_row)

    if incoming_quality == "MALFORMED":
        return None, "incoming_malformed"
    if existing_quality == "MALFORMED":
        return manual_row, None
    if existing_quality == "EMPTY_NO_DATA" and incoming_quality == "VALID_SCORE":
        return manual_row, None
    if existing_quality == "EMPTY_NO_DATA" and incoming_quality == "EMPTY_NO_DATA":
        return existing, "both_empty"
    if existing_quality == "VALID_SCORE" and incoming_quality == "EMPTY_NO_DATA":
        return existing, "incoming_empty_placeholder"

    existing_date = _row_sourced_date(existing)
    manual_date = str(manual_row.get("sourced_date", "")).strip()

    if existing_quality == "VALID_SCORE" and incoming_quality == "VALID_SCORE":
        if existing_date > manual_date:
            return existing, "existing_newer_valid"
        if existing_date < manual_date:
            return manual_row, None
        if existing.get("danelfin_raw") == manual_row.get("danelfin_raw") and existing.get("danelfin_score") == manual_row.get("danelfin_score"):
            return existing, "idempotent_same_day_value"
        return None, "conflicts_with_existing_same_day_value"

    if existing_quality == "EMPTY_NO_DATA" and incoming_quality == "VALID_SCORE":
        return manual_row, None

    if existing_date > manual_date:
        return existing, None
    if existing_date < manual_date:
        return manual_row, None

    if existing.get("danelfin_raw") == manual_row.get("danelfin_raw") and existing.get("danelfin_score") == manual_row.get("danelfin_score"):
        return existing, None

    return None, "conflicts_with_existing_same_day_value"


def _load_provenance(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    entries = data.get("symbols") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for symbol, payload in entries.items():
        if isinstance(payload, dict):
            result[str(symbol).strip().upper()] = {str(k): str(v) for k, v in payload.items()}
    return result


def load_latest_danelfin_provenance(
    signals_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> dict[str, dict[str, str]]:
    return _load_provenance(Path(signals_dir) / PROVENANCE_FILENAME)


def import_manual_danelfin_observations(
    observations: Sequence[ManualDanelfinObservation | dict[str, object]],
    *,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    operator_source: str = DEFAULT_OPERATOR_SOURCE,
    acquisition_method: str = MANUAL_ACQUISITION_METHOD,
    observed_at: str | None = None,
    allow_future_date: bool = False,
) -> dict[str, object]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    latest_path = output_dir / "latest_danelfin.csv"
    provenance_path = output_dir / PROVENANCE_FILENAME
    dated_path = output_dir / f"{date.today().isoformat()}_danelfin_manual.csv"

    existing_rows = _load_rows_by_symbol(latest_path)
    provenance = _load_provenance(provenance_path)
    normalized = [
        _normalize_observation(obs, allow_future=allow_future_date)
        for obs in observations
    ]

    applied: list[str] = []
    skipped: list[dict[str, str]] = []
    merged_rows: dict[str, dict[str, str]] = dict(existing_rows)

    for obs in normalized:
        manual_row = _manual_row(obs)
        current = merged_rows.get(obs.symbol)
        replacement, reason = _merge_manual_row(current, manual_row)
        if replacement is None:
            if reason:
                skipped.append({"symbol": obs.symbol, "reason": reason})
            continue
        if replacement is current:
            skipped.append({"symbol": obs.symbol, "reason": reason or "no_change"})
            continue
        merged_rows[obs.symbol] = replacement
        provenance[obs.symbol] = {
            "symbol": obs.symbol,
            "danelfin_raw": str(obs.danelfin_raw),
            "danelfin_score": f"{obs.danelfin_raw / 2.0:.4f}",
            "sourced_date": obs.sourced_date,
            "acquisition_method": obs.acquisition_method or acquisition_method,
            "operator_source": obs.operator_source or operator_source,
            "observed_at": observed_at or obs.observed_at or datetime.now(timezone.utc).isoformat(),
        }
        applied.append(obs.symbol)

    if applied:
        dated_rows = [merged_rows[symbol] for symbol in applied]
        _write_csv(dated_path, dated_rows)
    _write_csv(latest_path, list(merged_rows.values()))
    if applied:
        provenance_path.write_text(
            json.dumps({"symbols": provenance}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return {
        "output_dir": str(output_dir),
        "latest_path": str(latest_path),
        "dated_path": str(dated_path),
        "applied_symbols": applied,
        "skipped": skipped,
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "provenance_path": str(provenance_path),
    }


def read_manual_danelfin_csv(csv_path: Path | str) -> list[ManualDanelfinObservation]:
    path = Path(csv_path)
    observations: list[ManualDanelfinObservation] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            observations.append(
                _normalize_observation(
                    {
                        "symbol": row.get("symbol", ""),
                        "danelfin_raw": row.get("danelfin_raw", ""),
                        "sourced_date": row.get("sourced_date", ""),
                        "operator_source": row.get("operator_source", DEFAULT_OPERATOR_SOURCE),
                        "acquisition_method": row.get("acquisition_method", MANUAL_ACQUISITION_METHOD),
                        "observed_at": row.get("observed_at", ""),
                    }
                )
            )
    return observations
