"""PIS-008 — Recommendation Action Attribution Engine.

Classifies every recommendation against observed portfolio behavior to produce
FOLLOWED / PARTIALLY_FOLLOWED / OPPOSED / IGNORED / EXPIRED status labels.
Computes source-level effectiveness scorecards and identifies missed opportunities.

This module is STRICTLY READ-ONLY with respect to all existing PAR artifacts,
lineage records, and change records.  It reads:
  - data/history/pis/lineage/lineage_records.csv
  - data/history/pis/changes/change_records.csv
  - data/history/pis/attribution/attribution_records.csv (optional)
  - PAR analysis_runs/*/recommendations.json (via recommendation_lineage)

It writes only to:
  - data/history/pis/action_attribution/  (derived, fully regeneratable)

Public API
----------
  pis_action_attribution_summary(repo_root)        → dict
  pis_action_attribution_recommendations(repo_root) → dict
  pis_action_attribution_sources(repo_root)         → dict
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from .recommendation_lineage import (
    build_recommendation_candidates,
    _change_to_direction,
    _normalize_source_for_summary,
)

# ─── Constants ────────────────────────────────────────────────────────────────

_MAX_ATTRIBUTION_WINDOW_DAYS = 30
_PARTIAL_MV_THRESHOLD = 500.0
_MAX_MISSED_OPPORTUNITIES = 10
_MAX_OBSERVATIONS = 6

_STATUS_RANK = {
    "FOLLOWED": 5,
    "PARTIALLY_FOLLOWED": 4,
    "OPPOSED": 3,
    "EXPIRED": 2,
    "IGNORED": 1,
}

_CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}

_CACHE_FILENAME = "attribution_cache.json"

# ─── Data models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ActionAttributionRecord:
    attribution_id: str
    recommendation_id: str
    recommendation_source: str
    recommendation_date: str        # YYYY-MM-DD
    symbol: str
    recommended_direction: str      # BUY | REDUCE | ""
    action_status: str              # FOLLOWED | PARTIALLY_FOLLOWED | OPPOSED | IGNORED | EXPIRED
    action_confidence: str          # HIGH | MEDIUM | LOW | NONE
    observed_change_type: str       # NEW_POSITION | INCREASED | REDUCED | EXITED_POSITION | ""
    observed_date: str              # YYYY-MM-DD | ""
    response_days: Optional[int]
    delta_quantity: float
    delta_market_value: float
    outcome: str                    # WINNER | NEUTRAL | LOSER | UNKNOWN
    lineage_confidence: str
    created_at: str


@dataclass(frozen=True)
class SourceScorecard:
    source: str
    total_recommendations: int
    followed_count: int
    partially_followed_count: int
    ignored_count: int
    opposed_count: int
    expired_count: int
    follow_rate_pct: float
    ignore_rate_pct: float
    oppose_rate_pct: float
    avg_response_days: Optional[float]
    winner_count: int
    loser_count: int
    win_rate_pct: float


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _safe_float(value: object) -> float:
    try:
        return float(str(value or "").strip() or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: object) -> Optional[int]:
    s = str(value or "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _parse_date_str(raw: object) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    return value[:10]


def _days_between(date_a: str, date_b: str) -> Optional[int]:
    """Return (date_b - date_a) in calendar days, or None if either is empty."""
    if not date_a or not date_b:
        return None
    try:
        a = date.fromisoformat(date_a[:10])
        b = date.fromisoformat(date_b[:10])
        return (b - a).days
    except ValueError:
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _normalize_source(raw: str) -> str:
    return _normalize_source_for_summary(raw)


# ─── Classification ───────────────────────────────────────────────────────────


def classify_action_status(
    *,
    lineage_confidence: str,
    change_type: str,
    recommended_direction: str,
    days_between: Optional[int],
    delta_market_value: float,
) -> tuple[str, str]:
    """Return (action_status, action_confidence).

    Logic:
    1. NONE confidence → IGNORED (no recommendation matched this change, or no
       change occurred for this recommendation within any window).
    2. Direction mismatch → OPPOSED (portfolio moved opposite to recommendation).
    3. days_between > MAX_WINDOW → EXPIRED.
    4. Small delta + LOW lineage confidence → PARTIALLY_FOLLOWED.
    5. Everything else that matches direction → FOLLOWED.
    """
    # IGNORED: no match at all
    if lineage_confidence == "NONE":
        return "IGNORED", "HIGH"

    change_dir = _change_to_direction(change_type)

    # No change direction (e.g., UNCHANGED) → IGNORED
    if not change_dir:
        return "IGNORED", "MEDIUM"

    # No recommended direction — benefit of the doubt
    if not recommended_direction:
        return "FOLLOWED", "LOW"

    # Direction mismatch → OPPOSED
    if change_dir != recommended_direction:
        return "OPPOSED", lineage_confidence

    # Expired: response delay exceeds attribution window
    if days_between is not None and days_between > _MAX_ATTRIBUTION_WINDOW_DAYS:
        return "EXPIRED", "MEDIUM"

    # Partial: small execution (< threshold) with LOW confidence signal
    if abs(delta_market_value) < _PARTIAL_MV_THRESHOLD and lineage_confidence == "LOW":
        return "PARTIALLY_FOLLOWED", "LOW"

    return "FOLLOWED", lineage_confidence


# ─── Data loading ─────────────────────────────────────────────────────────────


def _load_lineage_records(repo_root: Path) -> list[dict[str, str]]:
    return _read_csv(repo_root / "data" / "history" / "pis" / "lineage" / "lineage_records.csv")


def _load_change_records(repo_root: Path) -> dict[str, dict[str, str]]:
    """Return {change_id: change_row}."""
    rows = _read_csv(repo_root / "data" / "history" / "pis" / "changes" / "change_records.csv")
    return {row["change_id"]: row for row in rows if row.get("change_id")}


def _load_attribution_outcomes(repo_root: Path) -> dict[str, str]:
    """Return {change_id: outcome (WINNER|NEUTRAL|LOSER)}."""
    rows = _read_csv(repo_root / "data" / "history" / "pis" / "attribution" / "attribution_records.csv")
    return {
        row.get("change_id", ""): row.get("outcome", "UNKNOWN")
        for row in rows
        if row.get("change_id")
    }


# ─── Core computation ─────────────────────────────────────────────────────────


def _build_attribution_records(repo_root: Path) -> list[ActionAttributionRecord]:
    """Build the full list of ActionAttributionRecord from existing lineage + change + recommendation data."""
    lineage_rows = _load_lineage_records(repo_root)
    change_index = _load_change_records(repo_root)
    outcome_index = _load_attribution_outcomes(repo_root)

    # Build recommendation candidate index: (recommendation_id, symbol) → direction
    try:
        candidates = build_recommendation_candidates(
            analysis_runs_root=repo_root / "data" / "portfolio_ingestion" / "analysis_runs",
        )
    except Exception:
        candidates = []

    # Index by (recommendation_id, symbol) → direction, source, date
    cand_index: dict[tuple[str, str], dict] = {}
    cand_by_rec: dict[str, dict] = {}
    for c in candidates:
        rec_id = str(c.get("recommendation_id", ""))
        sym = str(c.get("symbol", "")).upper()
        if rec_id:
            cand_index[(rec_id, sym)] = c
            if rec_id not in cand_by_rec:
                cand_by_rec[rec_id] = c

    generated_at = datetime.now(timezone.utc).isoformat()
    records: list[ActionAttributionRecord] = []

    # Track which recommendation_ids have been processed via lineage
    processed_rec_ids: set[str] = set()

    for lin in lineage_rows:
        change_id = str(lin.get("change_id", "")).strip()
        symbol = str(lin.get("symbol", "")).strip().upper()
        change_type = str(lin.get("change_type", "")).strip()
        lineage_conf = str(lin.get("confidence", "NONE")).strip() or "NONE"
        matched_rec_id = str(lin.get("matched_recommendation_id", "")).strip()
        rec_source = str(lin.get("recommendation_source", "")).strip()
        rec_date = _parse_date_str(lin.get("recommendation_date", ""))
        raw_days = lin.get("days_between", "")

        days_val = _safe_int(raw_days)

        # Look up change details
        change_row = change_index.get(change_id, {})
        delta_quantity = _safe_float(change_row.get("delta_quantity", 0))
        delta_mv = _safe_float(change_row.get("delta_market_value", 0))
        observed_date = _parse_date_str(change_row.get("snapshot_date", ""))

        # Outcome
        outcome = outcome_index.get(change_id, "UNKNOWN")

        # Direction from recommendation candidate
        rec_key = (matched_rec_id, symbol)
        cand = cand_index.get(rec_key) or cand_by_rec.get(matched_rec_id)
        rec_direction = str((cand or {}).get("direction", "")).strip().upper() if cand else ""
        if not rec_source and cand:
            rec_source = str(cand.get("source", "")).strip()
        if not rec_date and cand:
            rec_date = _parse_date_str(cand.get("recommendation_date", ""))

        # Clamp negative days to 0
        if days_val is not None and days_val < 0:
            days_val = 0

        action_status, action_conf = classify_action_status(
            lineage_confidence=lineage_conf,
            change_type=change_type,
            recommended_direction=rec_direction,
            days_between=days_val,
            delta_market_value=delta_mv,
        )

        source_norm = _normalize_source(rec_source) if rec_source else "OTHER"

        attribution_id = f"AA-{matched_rec_id or change_id}-{symbol}"

        record = ActionAttributionRecord(
            attribution_id=attribution_id,
            recommendation_id=matched_rec_id or "",
            recommendation_source=source_norm,
            recommendation_date=rec_date,
            symbol=symbol,
            recommended_direction=rec_direction,
            action_status=action_status,
            action_confidence=action_conf,
            observed_change_type=change_type,
            observed_date=observed_date,
            response_days=days_val,
            delta_quantity=delta_quantity,
            delta_market_value=delta_mv,
            outcome=outcome,
            lineage_confidence=lineage_conf,
            created_at=generated_at,
        )
        records.append(record)

        if matched_rec_id:
            processed_rec_ids.add(matched_rec_id)

    # Handle recommendations with no lineage match at all → IGNORED
    # Build symbol → change dates index for window checking
    symbol_change_dates: dict[str, list[str]] = defaultdict(list)
    for chg in change_index.values():
        sym = str(chg.get("symbol", "")).upper()
        ct = str(chg.get("change_type", ""))
        if ct != "UNCHANGED" and sym:
            symbol_change_dates[sym].append(_parse_date_str(chg.get("snapshot_date", "")))

    seen_unmatched: set[tuple[str, str]] = set()
    for cand in candidates:
        rec_id = str(cand.get("recommendation_id", ""))
        sym = str(cand.get("symbol", "")).upper()
        if not rec_id or not sym:
            continue
        if rec_id in processed_rec_ids:
            continue

        dedup_key = (rec_id, sym)
        if dedup_key in seen_unmatched:
            continue
        seen_unmatched.add(dedup_key)

        rec_date = _parse_date_str(cand.get("recommendation_date", ""))
        rec_direction = str(cand.get("direction", "")).upper()
        source = _normalize_source(str(cand.get("source", "")))

        # Check if symbol had any change within the attribution window
        dates_with_change = symbol_change_dates.get(sym, [])
        has_window_change = any(
            (d := _days_between(rec_date, chg_date)) is not None and 0 <= d <= _MAX_ATTRIBUTION_WINDOW_DAYS
            for chg_date in dates_with_change
        )

        # If symbol changed in window but wasn't matched, confidence is MEDIUM;
        # otherwise HIGH (clearly nothing happened)
        action_conf = "MEDIUM" if has_window_change else "HIGH"

        attribution_id = f"AA-{rec_id}-{sym}-IGNORED"
        record = ActionAttributionRecord(
            attribution_id=attribution_id,
            recommendation_id=rec_id,
            recommendation_source=source,
            recommendation_date=rec_date,
            symbol=sym,
            recommended_direction=rec_direction,
            action_status="IGNORED",
            action_confidence=action_conf,
            observed_change_type="",
            observed_date="",
            response_days=None,
            delta_quantity=0.0,
            delta_market_value=0.0,
            outcome="UNKNOWN",
            lineage_confidence="NONE",
            created_at=generated_at,
        )
        records.append(record)

    return records


# ─── Scorecard ────────────────────────────────────────────────────────────────


def _compute_scorecards(records: list[ActionAttributionRecord]) -> list[SourceScorecard]:
    by_source: dict[str, list[ActionAttributionRecord]] = defaultdict(list)
    for r in records:
        by_source[r.recommendation_source].append(r)

    scorecards: list[SourceScorecard] = []
    for source, recs in by_source.items():
        total = len(recs)
        followed = sum(1 for r in recs if r.action_status == "FOLLOWED")
        partial = sum(1 for r in recs if r.action_status == "PARTIALLY_FOLLOWED")
        ignored = sum(1 for r in recs if r.action_status == "IGNORED")
        opposed = sum(1 for r in recs if r.action_status == "OPPOSED")
        expired = sum(1 for r in recs if r.action_status == "EXPIRED")

        responded = [r for r in recs if r.response_days is not None]
        avg_days: Optional[float] = (
            round(sum(r.response_days for r in responded) / len(responded), 1)
            if responded else None
        )

        followed_recs = [r for r in recs if r.action_status in {"FOLLOWED", "PARTIALLY_FOLLOWED"}]
        winners = sum(1 for r in followed_recs if r.outcome == "WINNER")
        losers = sum(1 for r in followed_recs if r.outcome == "LOSER")
        win_rate = round(winners / (winners + losers) * 100, 1) if (winners + losers) > 0 else 0.0

        scorecards.append(SourceScorecard(
            source=source,
            total_recommendations=total,
            followed_count=followed,
            partially_followed_count=partial,
            ignored_count=ignored,
            opposed_count=opposed,
            expired_count=expired,
            follow_rate_pct=round((followed + partial) / total * 100, 1) if total else 0.0,
            ignore_rate_pct=round(ignored / total * 100, 1) if total else 0.0,
            oppose_rate_pct=round(opposed / total * 100, 1) if total else 0.0,
            avg_response_days=avg_days,
            winner_count=winners,
            loser_count=losers,
            win_rate_pct=win_rate,
        ))

    return sorted(scorecards, key=lambda s: s.total_recommendations, reverse=True)


# ─── Missed opportunities ─────────────────────────────────────────────────────


def _find_missed_opportunities(records: list[ActionAttributionRecord]) -> list[dict]:
    missed = []
    for r in records:
        if r.action_status != "IGNORED":
            continue
        if r.outcome == "WINNER" and r.recommended_direction:
            missed.append({
                "recommendation_id": r.recommendation_id,
                "symbol": r.symbol,
                "recommendation_source": r.recommendation_source,
                "recommendation_date": r.recommendation_date,
                "recommended_direction": r.recommended_direction,
                "outcome": r.outcome,
            })
    return missed[:_MAX_MISSED_OPPORTUNITIES]


# ─── Observations ─────────────────────────────────────────────────────────────


def _generate_observations(
    records: list[ActionAttributionRecord],
    scorecards: list[SourceScorecard],
) -> list[str]:
    obs: list[str] = []

    # Best follow rate source
    actionable = [s for s in scorecards if s.total_recommendations >= 3]
    if actionable:
        best = max(actionable, key=lambda s: s.follow_rate_pct)
        if best.follow_rate_pct > 50:
            obs.append(
                f"{best.source} has the highest follow rate at {best.follow_rate_pct:.0f}% "
                f"({best.followed_count} of {best.total_recommendations} recommendations followed)."
            )

    # Most ignored source
    ignored_sources = [s for s in scorecards if s.ignore_rate_pct > 60 and s.total_recommendations >= 3]
    if ignored_sources:
        worst = max(ignored_sources, key=lambda s: s.ignore_rate_pct)
        obs.append(
            f"{worst.source} recommendations are ignored {worst.ignore_rate_pct:.0f}% of the time."
        )

    # Opposed recommendations
    opposed = [r for r in records if r.action_status == "OPPOSED"]
    if opposed:
        obs.append(
            f"{len(opposed)} recommendation{'s were' if len(opposed) > 1 else ' was'} opposed — "
            "the portfolio moved in the opposite direction."
        )

    # Missed opportunities
    missed = _find_missed_opportunities(records)
    if missed:
        obs.append(
            f"{len(missed)} ignored recommendation{'s' if len(missed) > 1 else ''} later showed "
            "positive outcomes (missed opportunities)."
        )

    # Overall follow rate summary
    total = len(records)
    followed = sum(1 for r in records if r.action_status in {"FOLLOWED", "PARTIALLY_FOLLOWED"})
    if total > 0:
        pct = round(followed / total * 100, 0)
        obs.append(f"Overall follow rate: {pct:.0f}% ({followed} of {total} recommendations acted upon).")

    return obs[:_MAX_OBSERVATIONS]


# ─── Cache ────────────────────────────────────────────────────────────────────


def _cache_path(repo_root: Path) -> Path:
    return repo_root / "data" / "history" / "pis" / "action_attribution" / _CACHE_FILENAME


def _cache_is_valid(cache_path: Path, repo_root: Path) -> bool:
    if not cache_path.exists():
        return False
    try:
        cache_mtime = cache_path.stat().st_mtime
    except OSError:
        return False
    watch_paths = [
        repo_root / "data" / "history" / "pis" / "lineage" / "lineage_records.csv",
        repo_root / "data" / "history" / "pis" / "changes" / "change_records.csv",
    ]
    for wp in watch_paths:
        try:
            if wp.exists() and wp.stat().st_mtime > cache_mtime:
                return False
        except OSError:
            continue
    return True


def _load_cache(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


# ─── Public API ───────────────────────────────────────────────────────────────


def _get_computed(repo_root: Path) -> tuple[list[ActionAttributionRecord], list[SourceScorecard]]:
    """Compute or load from cache. Returns (records, scorecards)."""
    cache = _cache_path(repo_root)

    if _cache_is_valid(cache, repo_root):
        cached = _load_cache(cache)
        if cached is not None:
            # Reconstruct from cache
            records = [
                ActionAttributionRecord(**r)
                for r in cached.get("records", [])
            ]
            scorecards = [
                SourceScorecard(**s)
                for s in cached.get("scorecards", [])
            ]
            return records, scorecards

    records = _build_attribution_records(repo_root)
    scorecards = _compute_scorecards(records)

    # Write cache
    cache_payload = {
        "records": [asdict(r) for r in records],
        "scorecards": [asdict(s) for s in scorecards],
    }
    _write_cache(cache, cache_payload)

    return records, scorecards


def pis_action_attribution_summary(repo_root: Path | str = ".") -> dict:
    """Summary cards payload for the Action Attribution dashboard section."""
    repo_root = Path(repo_root)
    records, scorecards = _get_computed(repo_root)

    total = len(records)
    followed = sum(1 for r in records if r.action_status == "FOLLOWED")
    partial = sum(1 for r in records if r.action_status == "PARTIALLY_FOLLOWED")
    ignored = sum(1 for r in records if r.action_status == "IGNORED")
    opposed = sum(1 for r in records if r.action_status == "OPPOSED")
    expired = sum(1 for r in records if r.action_status == "EXPIRED")

    responded = [r for r in records if r.response_days is not None]
    avg_days: Optional[float] = (
        round(sum(r.response_days for r in responded) / len(responded), 1)
        if responded else None
    )

    sources = sorted({r.recommendation_source for r in records if r.recommendation_source})
    dates = sorted({r.recommendation_date[:10] for r in records if r.recommendation_date})

    missed = _find_missed_opportunities(records)
    observations = _generate_observations(records, scorecards)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_attribution_records": total,
        "followed_count": followed,
        "partially_followed_count": partial,
        "ignored_count": ignored,
        "opposed_count": opposed,
        "expired_count": expired,
        "follow_rate_pct": round((followed + partial) / total * 100, 1) if total else 0.0,
        "ignore_rate_pct": round(ignored / total * 100, 1) if total else 0.0,
        "oppose_rate_pct": round(opposed / total * 100, 1) if total else 0.0,
        "avg_response_days": avg_days,
        "sources_covered": sources,
        "dates_covered": len(dates),
        "missed_opportunities_count": len(missed),
        "observations": observations,
    }


def pis_action_attribution_recommendations(repo_root: Path | str = ".") -> dict:
    """Per-recommendation action status records."""
    repo_root = Path(repo_root)
    records, _ = _get_computed(repo_root)

    # Sort: OPPOSED first, then FOLLOWED, PARTIAL, IGNORED, EXPIRED
    sorted_records = sorted(
        records,
        key=lambda r: (
            -_STATUS_RANK.get(r.action_status, 0),
            r.recommendation_date or "",
            r.symbol,
        ),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(sorted_records),
        "records": [asdict(r) for r in sorted_records],
    }


def pis_action_attribution_sources(repo_root: Path | str = ".") -> dict:
    """Source-level effectiveness scorecards."""
    repo_root = Path(repo_root)
    _, scorecards = _get_computed(repo_root)
    missed = _find_missed_opportunities(_get_computed(repo_root)[0])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scorecards": [asdict(s) for s in scorecards],
        "missed_opportunities": missed,
    }
