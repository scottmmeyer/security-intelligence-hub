"""ISSUE-12D — Dislocation Outcome Review Engine.

Governance and learning review panel for DIL/UCF recommendations.

Evaluates historical UCF conviction verdicts against observed portfolio behavior
and performance outcomes.  Produces cohort analysis by UCF label, governance
observations, and missed-winner identification.

Architectural constraint: this module observes SIH outputs (ucf_verdicts.json).
It NEVER modifies UCF, DIL, CW-DAS, or any recommendation logic.  All findings
are informational and governance-oriented.

SIH decides.  PIS observes.

Read from:
  - data/portfolio_ingestion/analysis_runs/*/ucf_verdicts.json (SIH output)
  - data/history/pis/action_attribution/attribution_cache.json (PIS-008)
  - data/history/pis/attribution/attribution_records.csv (PIS performance attribution)
  - data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv

Write to:
  - data/history/pis/dor/  (derived governance artifacts, fully regeneratable)

Public API
----------
  pis_dor_summary(repo_root)        → dict
  pis_dor_cohorts(repo_root)        → dict
  pis_dor_recommendations(repo_root) → dict
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Optional

from .action_attribution import _STATUS_RANK

# ─── Constants ────────────────────────────────────────────────────────────────

# UCF labels that generate actionable DIL recommendations
DIL_ELIGIBLE_LABELS = frozenset({
    "CORE_CONVICTION_LEADER",
    "HIGH_CONVICTION_ANCHOR",
    "DEPLOYMENT_CANDIDATE",
    "TRIM_WATCH",
})

# Direction per UCF label
UCF_DIRECTION: dict[str, str] = {
    "CORE_CONVICTION_LEADER": "BUY",
    "HIGH_CONVICTION_ANCHOR": "BUY",
    "DEPLOYMENT_CANDIDATE":   "BUY",
    "TACTICAL_GROWTH":        "BUY",
    "MAINTAIN":               "",
    "TRIM_WATCH":             "REDUCE",
}

# Ordering for cohort table display
_UCF_LABEL_RANK: dict[str, int] = {
    "CORE_CONVICTION_LEADER": 1,
    "HIGH_CONVICTION_ANCHOR": 2,
    "DEPLOYMENT_CANDIDATE":   3,
    "TACTICAL_GROWTH":        4,
    "MAINTAIN":               5,
    "TRIM_WATCH":             6,
}

_MAX_OBSERVATIONS = 6
_MAX_MISSED_WINNERS = 10
_CACHE_FILENAME = "dor_cache.json"


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DORRecord:
    record_id: str
    snapshot_date: str
    symbol: str
    ucf_label: str
    ucf_score: float
    ucf_rank: int
    recommended_direction: str
    signal_direction: str
    composite_score: float
    replay_supported: bool
    replay_percentile: float
    cw_das_score: float
    conflict_flags: tuple[str, ...]
    action_status: str
    action_confidence: str
    outcome: str
    directional_return_pct: float
    excess_return_pct: float
    observation_window_days: int
    governance_flags: tuple[str, ...]


@dataclass(frozen=True)
class CohortSummary:
    ucf_label: str
    direction: str
    total_count: int
    followed_count: int
    ignored_count: int
    follow_rate_pct: float
    winner_count: int
    loser_count: int
    neutral_count: int
    win_rate_pct: float
    avg_alpha_pct: float
    avg_return_pct: float
    missed_winner_count: int


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _safe_float(v: object) -> float:
    try:
        return float(str(v or "").strip() or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _safe_mean(values: list[float]) -> float:
    return round(mean(values), 2) if values else 0.0


# ─── Step 1 — UCF History ─────────────────────────────────────────────────────


def _load_ucf_history(repo_root: Path) -> list[dict]:
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not par_dir.exists():
        return []

    by_date: dict[str, tuple[str, Path]] = {}
    for par_path in par_dir.iterdir():
        if not par_path.is_dir():
            continue
        meta_file = par_path / "run_metadata.json"
        ucf_file = par_path / "ucf_verdicts.json"
        if not meta_file.exists() or not ucf_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        snap_date = str(meta.get("snapshot_date", ""))[:10]
        created_at = str(meta.get("created_at_utc", ""))
        if len(snap_date) != 10:
            continue
        try:
            date.fromisoformat(snap_date)
        except ValueError:
            continue
        if snap_date not in by_date or created_at > by_date[snap_date][0]:
            by_date[snap_date] = (created_at, ucf_file)

    records = []
    for snap_date in sorted(by_date):
        _, ucf_file = by_date[snap_date]
        try:
            ucf_data = json.loads(ucf_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for v in ucf_data.get("verdicts", []):
            symbol = str(v.get("symbol", "") or "").strip().upper()
            if not symbol:
                continue
            src = v.get("source_signals") or {}
            records.append({
                "snapshot_date": snap_date,
                "symbol": symbol,
                "ucf_label": str(v.get("ucf_label", "") or ""),
                "ucf_score": _safe_float(v.get("ucf_score")),
                "ucf_rank": int(v.get("ucf_rank") or 0),
                "signal_direction": str(src.get("signal_direction") or ""),
                "composite_score": _safe_float(src.get("composite_score")),
                "replay_supported": bool(src.get("replay_supported")),
                "replay_percentile": _safe_float(src.get("replay_percentile")),
                "cw_das_score": _safe_float(src.get("cw_das_score")),
                "conflict_flags": list(v.get("conflict_flags") or []),
            })
    return records


# ─── Step 2 — Action Attribution ──────────────────────────────────────────────


def _load_dil_action_attribution(repo_root: Path) -> dict[tuple[str, str], dict]:
    cache_path = (
        repo_root / "data" / "history" / "pis" / "action_attribution" / "attribution_cache.json"
    )
    if not cache_path.exists():
        return {}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    index: dict[tuple[str, str], dict] = {}
    for r in cache.get("records", []):
        if r.get("recommendation_source") != "DIL":
            continue
        sym = str(r.get("symbol", "") or "").upper()
        rec_date = str(r.get("recommendation_date", "") or "")[:10]
        key = (sym, rec_date)
        existing = index.get(key)
        if existing is None or _STATUS_RANK.get(r.get("action_status", ""), 0) > _STATUS_RANK.get(
            existing.get("action_status", ""), 0
        ):
            index[key] = r
    return index


# ─── Step 3 — Attribution Outcomes ────────────────────────────────────────────


def _load_attribution_outcomes(repo_root: Path) -> dict[str, dict[str, str]]:
    path = repo_root / "data" / "history" / "pis" / "attribution" / "attribution_records.csv"
    rows = _read_csv(path)
    index: dict[str, dict[str, str]] = {}
    for r in rows:
        sym = str(r.get("symbol", "") or "").upper()
        if sym:
            index[sym] = r  # last write per symbol (most recent)
    return index


# ─── Step 4 — Benchmark Alpha ─────────────────────────────────────────────────


def _load_benchmark_alpha(repo_root: Path) -> dict[str, float]:
    path = (
        repo_root
        / "data"
        / "history"
        / "pis"
        / "benchmark_attribution"
        / "recommendation_benchmark_records.csv"
    )
    rows = _read_csv(path)
    alpha: dict[str, float] = {}
    for r in rows:
        sym = str(r.get("symbol", "") or "").upper()
        raw = r.get("recommendation_excess_return_pct", "") or ""
        try:
            val: Optional[float] = float(raw.strip()) if raw.strip() else None
        except (TypeError, ValueError):
            val = None
        if sym and val is not None:
            alpha[sym] = val
    return alpha


# ─── Step 5 — Build DOR Records ───────────────────────────────────────────────


def _build_dor_records(repo_root: Path) -> list[DORRecord]:
    ucf_history = _load_ucf_history(repo_root)
    dil_attribution = _load_dil_action_attribution(repo_root)
    attribution_outcomes = _load_attribution_outcomes(repo_root)
    benchmark_alpha = _load_benchmark_alpha(repo_root)

    records: list[DORRecord] = []
    for entry in ucf_history:
        ucf_label = entry["ucf_label"]
        if ucf_label not in DIL_ELIGIBLE_LABELS:
            continue

        symbol = entry["symbol"]
        snap_date = entry["snapshot_date"]
        direction = UCF_DIRECTION.get(ucf_label, "")

        attr = dil_attribution.get((symbol, snap_date), {})
        action_status = str(attr.get("action_status", "IGNORED") or "IGNORED")
        action_conf = str(attr.get("action_confidence", "NONE") or "NONE")

        perf = attribution_outcomes.get(symbol, {})
        outcome = str(perf.get("outcome", "UNKNOWN") or "UNKNOWN")
        directional_return = _safe_float(perf.get("directional_return_pct"))
        excess_return = benchmark_alpha.get(symbol, 0.0)

        gov_flags: list[str] = []
        if action_status == "IGNORED" and outcome == "WINNER":
            gov_flags.append("MISSED_WINNER")
        if entry["conflict_flags"]:
            gov_flags.append("SIGNAL_CONFLICT")
        if action_status in ("FOLLOWED", "PARTIALLY_FOLLOWED") and outcome == "LOSER":
            gov_flags.append("FOLLOWED_LOSER")

        records.append(
            DORRecord(
                record_id=f"DOR-{snap_date}-{symbol}",
                snapshot_date=snap_date,
                symbol=symbol,
                ucf_label=ucf_label,
                ucf_score=entry["ucf_score"],
                ucf_rank=entry["ucf_rank"],
                recommended_direction=direction,
                signal_direction=entry["signal_direction"],
                composite_score=entry["composite_score"],
                replay_supported=entry["replay_supported"],
                replay_percentile=entry["replay_percentile"],
                cw_das_score=entry["cw_das_score"],
                conflict_flags=tuple(entry["conflict_flags"]),
                action_status=action_status,
                action_confidence=action_conf,
                outcome=outcome,
                directional_return_pct=directional_return,
                excess_return_pct=excess_return,
                observation_window_days=int(attr.get("response_days") or 0),
                governance_flags=tuple(gov_flags),
            )
        )
    return records


# ─── Step 6 — Cohort Analysis ─────────────────────────────────────────────────


def _build_cohorts(records: list[DORRecord]) -> list[CohortSummary]:
    by_label: dict[str, list[DORRecord]] = defaultdict(list)
    for r in records:
        by_label[r.ucf_label].append(r)

    summaries: list[CohortSummary] = []
    for label in sorted(by_label, key=lambda l: _UCF_LABEL_RANK.get(l, 99)):
        recs = by_label[label]
        total = len(recs)
        followed = [r for r in recs if r.action_status in ("FOLLOWED", "PARTIALLY_FOLLOWED")]
        ignored = [r for r in recs if r.action_status == "IGNORED"]

        winners = sum(1 for r in followed if r.outcome == "WINNER")
        losers = sum(1 for r in followed if r.outcome == "LOSER")
        neutral = sum(1 for r in followed if r.outcome == "NEUTRAL")
        win_rate = round(winners / (winners + losers) * 100, 1) if (winners + losers) > 0 else 0.0

        followed_returns = [r.directional_return_pct for r in followed if r.directional_return_pct != 0.0]
        followed_alpha = [r.excess_return_pct for r in followed if r.excess_return_pct != 0.0]

        missed_winners = sum(1 for r in ignored if r.outcome == "WINNER")

        summaries.append(
            CohortSummary(
                ucf_label=label,
                direction=UCF_DIRECTION.get(label, ""),
                total_count=total,
                followed_count=len(followed),
                ignored_count=len(ignored),
                follow_rate_pct=round(len(followed) / total * 100, 1) if total else 0.0,
                winner_count=winners,
                loser_count=losers,
                neutral_count=neutral,
                win_rate_pct=win_rate,
                avg_alpha_pct=_safe_mean(followed_alpha),
                avg_return_pct=_safe_mean(followed_returns),
                missed_winner_count=missed_winners,
            )
        )
    return summaries


# ─── Step 7 — Governance Observations ────────────────────────────────────────


def _generate_observations(records: list[DORRecord], cohorts: list[CohortSummary]) -> list[str]:
    obs: list[str] = []

    # High-conviction missed winners
    ccl_missed = [
        r for r in records
        if r.ucf_label == "CORE_CONVICTION_LEADER"
        and r.action_status == "IGNORED"
        and r.outcome == "WINNER"
    ]
    if ccl_missed:
        obs.append(
            f"{len(ccl_missed)} CORE_CONVICTION_LEADER recommendation"
            f"{'s were' if len(ccl_missed) > 1 else ' was'} ignored "
            "and later showed positive outcomes. Governance review recommended."
        )

    # Best performing cohort
    followed_cohorts = [c for c in cohorts if c.followed_count > 0 and (c.winner_count + c.loser_count) > 0]
    if followed_cohorts:
        best = max(followed_cohorts, key=lambda c: c.win_rate_pct)
        obs.append(
            f"{best.ucf_label} cohort has the highest win rate: "
            f"{best.win_rate_pct:.0f}% "
            f"({best.winner_count}W / {best.loser_count}L from {best.followed_count} followed)."
        )

    # Alpha context if available
    followed_with_alpha = [r for r in records if r.action_status in ("FOLLOWED", "PARTIALLY_FOLLOWED") and r.excess_return_pct != 0.0]
    if followed_with_alpha:
        avg_alpha = _safe_mean([r.excess_return_pct for r in followed_with_alpha])
        obs.append(
            f"Followed DIL recommendations averaged {avg_alpha:+.1f}pp alpha vs benchmark."
        )

    # Signal conflict governance
    conflict_followed = [
        r for r in records
        if "SIGNAL_CONFLICT" in r.governance_flags
        and r.action_status in ("FOLLOWED", "PARTIALLY_FOLLOWED")
    ]
    if conflict_followed:
        cf_winners = sum(1 for r in conflict_followed if r.outcome == "WINNER")
        obs.append(
            f"{len(conflict_followed)} DIL recommendations with signal conflicts were followed "
            f"({cf_winners} winners). Conflict-aware governance may improve selection."
        )

    # Total coverage
    dates = sorted({r.snapshot_date for r in records})
    obs.append(
        f"DIL outcome review covers {len(records)} recommendation-date pairs across "
        f"{len(dates)} canonical date{'s' if len(dates) != 1 else ''}."
    )

    # Coverage gap note if most outcomes unknown
    unknown_pct = sum(1 for r in records if r.outcome == "UNKNOWN") / len(records) * 100 if records else 100
    if unknown_pct > 80:
        obs.append(
            f"{unknown_pct:.0f}% of DIL outcome records have unknown outcomes. "
            "Outcome coverage will improve as the portfolio acts on more DIL recommendations."
        )

    return obs[:_MAX_OBSERVATIONS]


# ─── Missed winners ───────────────────────────────────────────────────────────


def _find_missed_winners(records: list[DORRecord]) -> list[dict]:
    missed = sorted(
        (r for r in records if "MISSED_WINNER" in r.governance_flags),
        key=lambda r: r.excess_return_pct,
        reverse=True,
    )[:_MAX_MISSED_WINNERS]
    return [
        {
            "record_id": r.record_id,
            "symbol": r.symbol,
            "ucf_label": r.ucf_label,
            "snapshot_date": r.snapshot_date,
            "recommended_direction": r.recommended_direction,
            "signal_direction": r.signal_direction,
            "outcome": r.outcome,
            "excess_return_pct": r.excess_return_pct,
        }
        for r in missed
    ]


# ─── Cache ────────────────────────────────────────────────────────────────────


def _cache_path(repo_root: Path) -> Path:
    return repo_root / "data" / "history" / "pis" / "dor" / _CACHE_FILENAME


def _cache_is_valid(cache: Path, repo_root: Path) -> bool:
    if not cache.exists():
        return False
    try:
        cache_mtime = cache.stat().st_mtime
    except OSError:
        return False
    watch = [
        repo_root / "data" / "history" / "pis" / "action_attribution" / "attribution_cache.json",
        repo_root / "data" / "history" / "pis" / "attribution" / "attribution_records.csv",
    ]
    for wp in watch:
        try:
            if wp.exists() and wp.stat().st_mtime > cache_mtime:
                return False
        except OSError:
            continue
    return True


def _get_computed(repo_root: Path) -> tuple[list[DORRecord], list[CohortSummary]]:
    cache = _cache_path(repo_root)
    if _cache_is_valid(cache, repo_root):
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            records = [DORRecord(**r) for r in cached.get("records", [])]
            cohorts = [CohortSummary(**c) for c in cached.get("cohorts", [])]
            return records, cohorts
        except Exception:
            pass

    records = _build_dor_records(repo_root)
    cohorts = _build_cohorts(records)

    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(
                {"records": [asdict(r) for r in records], "cohorts": [asdict(c) for c in cohorts]},
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass

    return records, cohorts


# ─── Public API ───────────────────────────────────────────────────────────────


def pis_dor_summary(repo_root: Path | str = ".") -> dict:
    """Summary cards for the Dislocation Outcome Review dashboard section."""
    repo_root = Path(repo_root)
    records, cohorts = _get_computed(repo_root)

    total = len(records)
    followed = [r for r in records if r.action_status in ("FOLLOWED", "PARTIALLY_FOLLOWED")]
    ignored = [r for r in records if r.action_status == "IGNORED"]
    winners = [r for r in followed if r.outcome == "WINNER"]
    losers = [r for r in followed if r.outcome == "LOSER"]
    neutral = [r for r in followed if r.outcome == "NEUTRAL"]
    unknown = [r for r in records if r.outcome == "UNKNOWN"]

    alpha_vals = [r.excess_return_pct for r in followed if r.excess_return_pct != 0.0]
    avg_alpha = _safe_mean(alpha_vals)
    win_rate = round(len(winners) / (len(winners) + len(losers)) * 100, 1) if (winners or losers) else 0.0

    missed = _find_missed_winners(records)
    obs = _generate_observations(records, cohorts)
    gov_flags = sorted({flag for r in records for flag in r.governance_flags})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_dil_records": total,
        "followed_count": len(followed),
        "ignored_count": len(ignored),
        "winner_count": len(winners),
        "loser_count": len(losers),
        "neutral_count": len(neutral),
        "unknown_count": len(unknown),
        "follow_rate_pct": round(len(followed) / total * 100, 1) if total else 0.0,
        "win_rate_pct": win_rate,
        "avg_alpha_pct": avg_alpha,
        "missed_winner_count": len(missed),
        "dates_covered": len({r.snapshot_date for r in records}),
        "observations": obs,
        "governance_flags": gov_flags,
    }


def pis_dor_cohorts(repo_root: Path | str = ".") -> dict:
    """UCF label cohort analysis for Dislocation Outcome Review."""
    repo_root = Path(repo_root)
    records, cohorts = _get_computed(repo_root)
    missed = _find_missed_winners(records)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohorts": [asdict(c) for c in cohorts],
        "missed_winners": missed,
    }


def pis_dor_recommendations(repo_root: Path | str = ".") -> dict:
    """Per-recommendation DOR records, sorted by governance priority."""
    repo_root = Path(repo_root)
    records, _ = _get_computed(repo_root)

    # Sort: governance-flagged first, then by ucf_label rank, then symbol
    def _sort_key(r: DORRecord) -> tuple:
        has_flag = int(bool(r.governance_flags))
        label_rank = _UCF_LABEL_RANK.get(r.ucf_label, 99)
        return (-has_flag, label_rank, r.snapshot_date, r.symbol)

    sorted_records = sorted(records, key=_sort_key)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(sorted_records),
        "records": [
            {
                "record_id": r.record_id,
                "snapshot_date": r.snapshot_date,
                "symbol": r.symbol,
                "ucf_label": r.ucf_label,
                "recommended_direction": r.recommended_direction,
                "signal_direction": r.signal_direction,
                "ucf_score": r.ucf_score,
                "replay_supported": r.replay_supported,
                "action_status": r.action_status,
                "outcome": r.outcome,
                "excess_return_pct": r.excess_return_pct,
                "governance_flags": list(r.governance_flags),
            }
            for r in sorted_records
        ],
    }
