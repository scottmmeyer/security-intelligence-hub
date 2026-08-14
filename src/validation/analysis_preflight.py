"""Deterministic SIH analysis preflight validation.

This module provides a read-only preflight contract that classifies runtime
readiness as READY, DEGRADED, or BLOCKED before advisory outputs are treated as
trustworthy action guidance.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


PRECHECK_READY = "READY"
PRECHECK_DEGRADED = "DEGRADED"
PRECHECK_BLOCKED = "BLOCKED"

COMPONENT_READY = "READY"
COMPONENT_DEGRADED = "DEGRADED"
COMPONENT_BLOCKED = "BLOCKED"
COMPONENT_UNAVAILABLE = "UNAVAILABLE"
COMPONENT_NOT_APPLICABLE = "NOT_APPLICABLE"

KNOWN_L1_ASSET_CLASSES = frozenset({"EQUITIES", "FIXED_INCOME", "DIGITAL", "COMMODITIES", "CASH"})

DEFAULT_POLICY = {
    "max_active_ess_age_days": 14,
    "l1_recognized_mv_coverage_block_threshold_pct": 90.0,
}


@dataclass(frozen=True)
class PreflightComponentResult:
    name: str
    status: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    messages: tuple[str, ...] = field(default_factory=tuple)
    snapshot_date: str = ""
    metrics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisPreflightResult:
    status: str
    checked_at: str
    reason_codes: tuple[str, ...]
    messages: tuple[str, ...]
    snapshot_date: str
    components: Mapping[str, PreflightComponentResult]
    suppression_flags: Mapping[str, bool]
    metrics: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["components"] = {
            key: asdict(value) for key, value in self.components.items()
        }
        return payload


@dataclass(frozen=True)
class HoldingsCoverage:
    total_market_value: float
    recognized_market_value: float
    coverage_pct: float
    holding_count: int
    recognized_count: int
    unknown_count: int


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _parse_iso_date(raw: str) -> date | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _safe_float(raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _stable_unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return tuple(ordered)


def load_preflight_policy(repo_root: Path) -> dict[str, Any]:
    """Load tracked preflight policy values with deterministic defaults."""

    merged = dict(DEFAULT_POLICY)
    policy_path = repo_root / "config" / "preflight_policy.yaml"
    if not policy_path.exists():
        return merged

    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return merged
    block = payload.get("analysis_preflight", payload)
    if not isinstance(block, dict):
        return merged

    try:
        if "max_active_ess_age_days" in block:
            parsed = int(block["max_active_ess_age_days"])
            if parsed > 0:
                merged["max_active_ess_age_days"] = parsed
    except (TypeError, ValueError):
        pass
    try:
        if "l1_recognized_mv_coverage_block_threshold_pct" in block:
            parsed = float(block["l1_recognized_mv_coverage_block_threshold_pct"])
            if 0.0 <= parsed <= 100.0:
                merged["l1_recognized_mv_coverage_block_threshold_pct"] = parsed
    except (TypeError, ValueError):
        pass
    return merged


def _load_latest_holdings_rows(repo_root: Path) -> list[dict[str, str]]:
    runs_root = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not runs_root.exists():
        return []
    candidates: list[tuple[float, Path]] = []
    for run_dir in runs_root.iterdir():
        hpath = run_dir / "holdings.csv"
        if run_dir.is_dir() and hpath.exists():
            candidates.append((hpath.stat().st_mtime, hpath))
    if not candidates:
        return []
    candidates.sort(key=lambda item: item[0], reverse=True)
    return _read_csv_rows(candidates[0][1])


def _compute_holdings_coverage(holdings: Iterable[Mapping[str, Any]]) -> HoldingsCoverage:
    total_mv = 0.0
    recognized_mv = 0.0
    total_count = 0
    recognized_count = 0

    for row in holdings:
        mv = _safe_float(row.get("market_value"))
        if mv <= 0:
            continue
        total_count += 1
        total_mv += mv
        asset_class = str(row.get("asset_class", "")).strip().upper()
        if asset_class in KNOWN_L1_ASSET_CLASSES:
            recognized_count += 1
            recognized_mv += mv

    coverage_pct = round((recognized_mv / total_mv * 100.0), 4) if total_mv > 0 else 0.0
    unknown_count = max(total_count - recognized_count, 0)
    return HoldingsCoverage(
        total_market_value=round(total_mv, 4),
        recognized_market_value=round(recognized_mv, 4),
        coverage_pct=coverage_pct,
        holding_count=total_count,
        recognized_count=recognized_count,
        unknown_count=unknown_count,
    )


def _build_au_component(
    *,
    repo_root: Path,
    coverage_threshold_pct: float,
    holdings_rows: list[Mapping[str, Any]],
) -> tuple[PreflightComponentResult, str]:
    au_path = repo_root / "data" / "current" / "analytical_universe.csv"
    reason_codes: list[str] = []
    messages: list[str] = []
    metrics: dict[str, Any] = {
        "analytical_universe_path": str(au_path),
        "exists": au_path.exists(),
    }
    snapshot_date = ""

    if not au_path.exists():
        reason_codes.append("PF-AU-001")
        messages.append("Canonical analytical universe is missing.")
        return (
            PreflightComponentResult(
                name="analytical_universe",
                status=COMPONENT_BLOCKED,
                reason_codes=tuple(reason_codes),
                messages=tuple(messages),
                metrics=metrics,
            ),
            "",
        )

    try:
        rows = _read_csv_rows(au_path)
    except Exception as exc:
        reason_codes.append("PF-AU-003")
        messages.append(f"Canonical analytical universe is unreadable: {exc}")
        return (
            PreflightComponentResult(
                name="analytical_universe",
                status=COMPONENT_BLOCKED,
                reason_codes=tuple(reason_codes),
                messages=tuple(messages),
                metrics=metrics,
            ),
            "",
        )

    metrics["row_count"] = len(rows)
    if not rows:
        reason_codes.append("PF-AU-003")
        messages.append("Canonical analytical universe is empty.")
        return (
            PreflightComponentResult(
                name="analytical_universe",
                status=COMPONENT_BLOCKED,
                reason_codes=tuple(reason_codes),
                messages=tuple(messages),
                metrics=metrics,
            ),
            "",
        )

    seen: set[str] = set()
    duplicate_count = 0
    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        if not sym:
            continue
        if sym in seen:
            duplicate_count += 1
        seen.add(sym)

    metrics["duplicate_symbol_count"] = duplicate_count
    if duplicate_count > 0:
        reason_codes.append("PF-AU-005")
        messages.append("Canonical analytical universe contains duplicate symbols.")

    date_candidates = {
        str(row.get("snapshot_date", "")).strip()
        for row in rows
        if str(row.get("snapshot_date", "")).strip()
    }
    valid_dates = sorted({d for d in date_candidates if _parse_iso_date(d) is not None})
    if valid_dates:
        snapshot_date = valid_dates[-1]
    else:
        reason_codes.append("PF-AU-004")
        messages.append("Canonical analytical universe has no valid snapshot_date values.")

    coverage = _compute_holdings_coverage(holdings_rows)
    metrics.update(
        {
            "l1_recognized_mv_coverage_pct": coverage.coverage_pct,
            "l1_recognized_mv_coverage_block_threshold_pct": coverage_threshold_pct,
            "holdings_market_value_total": coverage.total_market_value,
            "holdings_market_value_recognized": coverage.recognized_market_value,
            "holdings_count": coverage.holding_count,
            "holdings_recognized_count": coverage.recognized_count,
            "holdings_unknown_count": coverage.unknown_count,
        }
    )

    if coverage.holding_count > 0 and coverage.coverage_pct < coverage_threshold_pct:
        reason_codes.append("PF-AU-002")
        messages.append(
            "Recognized L1 market-value coverage is below blocking threshold."
        )

    blocked = {"PF-AU-001", "PF-AU-002", "PF-AU-003", "PF-AU-004", "PF-AU-005"}
    status = COMPONENT_BLOCKED if any(code in blocked for code in reason_codes) else COMPONENT_READY
    return (
        PreflightComponentResult(
            name="analytical_universe",
            status=status,
            reason_codes=tuple(reason_codes),
            messages=tuple(messages),
            snapshot_date=snapshot_date,
            metrics=metrics,
        ),
        snapshot_date,
    )


def _build_ess_component(
    *,
    repo_root: Path,
    max_age_days: int,
    require_active_ess: bool,
    holdings_rows: list[Mapping[str, Any]],
    snapshot_date_hint: str,
) -> PreflightComponentResult:
    signal_path = repo_root / "data" / "current" / "signal_snapshot.csv"
    reason_codes: list[str] = []
    messages: list[str] = []
    metrics: dict[str, Any] = {
        "signal_snapshot_path": str(signal_path),
        "max_active_ess_age_days": max_age_days,
        "require_active_ess": require_active_ess,
        "exists": signal_path.exists(),
    }
    component_snapshot_date = snapshot_date_hint

    if not signal_path.exists():
        reason_codes.append("PF-ESS-003")
        messages.append("signal_snapshot.csv is missing.")
        status = COMPONENT_BLOCKED if require_active_ess else COMPONENT_UNAVAILABLE
        return PreflightComponentResult(
            name="ess_freshness",
            status=status,
            reason_codes=tuple(reason_codes),
            messages=tuple(messages),
            snapshot_date=component_snapshot_date,
            metrics=metrics,
        )

    try:
        rows = _read_csv_rows(signal_path)
    except Exception as exc:
        reason_codes.append("PF-ESS-003")
        messages.append(f"signal_snapshot.csv is unreadable: {exc}")
        status = COMPONENT_BLOCKED if require_active_ess else COMPONENT_UNAVAILABLE
        return PreflightComponentResult(
            name="ess_freshness",
            status=status,
            reason_codes=tuple(reason_codes),
            messages=tuple(messages),
            snapshot_date=component_snapshot_date,
            metrics=metrics,
        )

    by_symbol: dict[str, dict[str, str]] = {}
    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        if not sym:
            continue
        current = by_symbol.get(sym)
        candidate_domain = str(row.get("coverage_domain", "")).strip().upper()
        if current is None:
            by_symbol[sym] = row
            continue
        current_domain = str(current.get("coverage_domain", "")).strip().upper()
        if candidate_domain == "STARMINE_COVERED" and current_domain != "STARMINE_COVERED":
            by_symbol[sym] = row

    holdings_symbols = {
        str(r.get("symbol", "")).strip().upper()
        for r in holdings_rows
        if _safe_float(r.get("market_value")) > 0
    }
    target_symbols = holdings_symbols or set(by_symbol.keys())

    today = date.today()
    fresh = 0
    stale = 0
    missing = 0
    unknown_freshness = 0
    newest_date: date | None = None
    oldest_fresh_age_days = 0

    holdings_mv_by_symbol = {
        str(r.get("symbol", "")).strip().upper(): _safe_float(r.get("market_value"))
        for r in holdings_rows
    }
    fresh_mv = 0.0
    stale_mv = 0.0
    missing_mv = 0.0

    for sym in sorted(s for s in target_symbols if s):
        row = by_symbol.get(sym)
        mv = holdings_mv_by_symbol.get(sym, 0.0)
        if row is None:
            missing += 1
            missing_mv += mv
            continue

        ess_text = str(row.get("starmine_ess_text", "")).strip().upper()
        snapshot_raw = str(row.get("snapshot_date", "")).strip()
        parsed = _parse_iso_date(snapshot_raw)
        if parsed is None:
            unknown_freshness += 1
            missing_mv += mv
            continue

        newest_date = parsed if newest_date is None or parsed > newest_date else newest_date
        age_days = (today - parsed).days
        if ess_text and age_days <= max_age_days:
            fresh += 1
            fresh_mv += mv
            oldest_fresh_age_days = max(oldest_fresh_age_days, age_days)
        elif ess_text:
            stale += 1
            stale_mv += mv
        else:
            missing += 1
            missing_mv += mv

    total_mv = sum(v for v in holdings_mv_by_symbol.values() if v > 0)
    metrics.update(
        {
            "target_symbol_count": len(target_symbols),
            "fresh_ess_rows": fresh,
            "stale_ess_rows": stale,
            "missing_ess_rows": missing,
            "unknown_freshness_rows": unknown_freshness,
            "fresh_portfolio_mv_coverage_pct": round((fresh_mv / total_mv * 100.0), 4) if total_mv > 0 else None,
            "stale_portfolio_mv_coverage_pct": round((stale_mv / total_mv * 100.0), 4) if total_mv > 0 else None,
            "missing_portfolio_mv_coverage_pct": round((missing_mv / total_mv * 100.0), 4) if total_mv > 0 else None,
            "newest_ess_timestamp": newest_date.isoformat() if newest_date else "",
            "oldest_active_ess_age_days": oldest_fresh_age_days,
        }
    )

    if stale > 0:
        reason_codes.append("PF-ESS-001")
        messages.append("Stale ESS rows exceed active freshness policy.")
    if unknown_freshness > 0:
        reason_codes.append("PF-ESS-002")
        messages.append("ESS freshness is unknown for one or more symbols.")
    if fresh == 0 and len(target_symbols) > 0:
        reason_codes.append("PF-ESS-004")
        messages.append("No fresh ESS rows are available for active symbols.")

    if require_active_ess and reason_codes:
        status = COMPONENT_BLOCKED
    elif reason_codes:
        status = COMPONENT_DEGRADED
    else:
        status = COMPONENT_READY

    return PreflightComponentResult(
        name="ess_freshness",
        status=status,
        reason_codes=tuple(reason_codes),
        messages=tuple(messages),
        snapshot_date=(newest_date.isoformat() if newest_date else component_snapshot_date),
        metrics=metrics,
    )


def _build_geography_component(
    *,
    repo_root: Path,
    au_component: PreflightComponentResult,
    holdings_rows: list[Mapping[str, Any]],
) -> PreflightComponentResult:
    au_path = Path(str(au_component.metrics.get("analytical_universe_path", "")))
    reason_codes: list[str] = []
    messages: list[str] = []
    if au_component.status == COMPONENT_BLOCKED or not au_path.exists() or not au_path.is_file():
        return PreflightComponentResult(
            name="geography",
            status=COMPONENT_UNAVAILABLE,
            reason_codes=("PF-GEO-002",),
            messages=("Geography assessment unavailable because analytical universe is missing.",),
            snapshot_date=au_component.snapshot_date,
            metrics={"known_geography_symbol_coverage_pct": 0.0},
        )

    try:
        rows = _read_csv_rows(au_path)
    except Exception:
        return PreflightComponentResult(
            name="geography",
            status=COMPONENT_UNAVAILABLE,
            reason_codes=("PF-GEO-002",),
            messages=("Geography assessment unavailable because analytical universe is unreadable.",),
            snapshot_date=au_component.snapshot_date,
            metrics={"known_geography_symbol_coverage_pct": 0.0},
        )
    total = len(rows)
    known = 0
    unknown = 0
    geo_by_symbol: dict[str, str] = {}
    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        geo = str(row.get("geography", "")).strip().upper()
        if sym:
            geo_by_symbol[sym] = geo
        if geo and geo not in {"UNKNOWN", "N/A"}:
            known += 1
        else:
            unknown += 1

    holdings_mv_total = 0.0
    holdings_known_mv = 0.0
    holdings_unknown_mv = 0.0
    for holding in holdings_rows:
        sym = str(holding.get("symbol", "")).strip().upper()
        mv = _safe_float(holding.get("market_value"))
        if mv <= 0:
            continue
        holdings_mv_total += mv
        geo = geo_by_symbol.get(sym, "")
        if geo and geo not in {"UNKNOWN", "N/A"}:
            holdings_known_mv += mv
        else:
            holdings_unknown_mv += mv

    metadata_path = repo_root / "data" / "signals" / "security_metadata" / "latest_security_metadata.csv"
    metadata_tech_failures = 0
    metadata_provider_no_data = 0
    if metadata_path.exists():
        for row in _read_csv_rows(metadata_path):
            status = str(row.get("metadata_status", "")).strip().upper()
            if status in {"PROVIDER_NO_DATA", "NO_DATA", "NO_COVERAGE"}:
                metadata_provider_no_data += 1
            elif "ERROR" in status or "FAIL" in status:
                metadata_tech_failures += 1

    metrics = {
        "known_geography_symbol_count": known,
        "unknown_geography_symbol_count": unknown,
        "known_geography_symbol_coverage_pct": round((known / total * 100.0), 4) if total > 0 else 0.0,
        "known_geography_portfolio_mv_coverage_pct": round((holdings_known_mv / holdings_mv_total * 100.0), 4)
        if holdings_mv_total > 0
        else None,
        "unknown_geography_portfolio_mv_coverage_pct": round((holdings_unknown_mv / holdings_mv_total * 100.0), 4)
        if holdings_mv_total > 0
        else None,
        "metadata_technical_failure_count": metadata_tech_failures,
        "metadata_provider_no_data_count": metadata_provider_no_data,
    }

    if unknown > 0 or holdings_unknown_mv > 0:
        reason_codes.append("PF-GEO-001")
        messages.append("Geography coverage is incomplete and explicitly degraded.")

    return PreflightComponentResult(
        name="geography",
        status=COMPONENT_DEGRADED if reason_codes else COMPONENT_READY,
        reason_codes=tuple(reason_codes),
        messages=tuple(messages),
        snapshot_date=au_component.snapshot_date,
        metrics=metrics,
    )


def _build_fmp_component(*, repo_root: Path) -> PreflightComponentResult:
    path = repo_root / "data" / "signals" / "fmp" / "latest" / "latest_fmp_enriched_universe.csv"
    metrics: dict[str, Any] = {"fmp_enriched_path": str(path), "exists": path.exists()}
    if not path.exists():
        return PreflightComponentResult(
            name="fmp",
            status=COMPONENT_UNAVAILABLE,
            reason_codes=("PF-FMP-002",),
            messages=("FMP enriched universe artifact is unavailable.",),
            metrics=metrics,
        )

    rows = _read_csv_rows(path)
    if not rows:
        return PreflightComponentResult(
            name="fmp",
            status=COMPONENT_UNAVAILABLE,
            reason_codes=("PF-FMP-002",),
            messages=("FMP enriched universe artifact is empty.",),
            metrics=metrics,
        )

    full = partial = no_data = applicable = fetch_failure = 0
    for row in rows:
        status = str(row.get("fmp_coverage_status", "")).strip().upper()
        if status == "ETF_NOT_APPLICABLE":
            continue
        applicable += 1
        if status == "FULL":
            full += 1
        elif status == "PARTIAL":
            partial += 1
        elif status == "NO_DATA":
            no_data += 1
        elif "FAIL" in status or "ERROR" in status:
            fetch_failure += 1

    metrics.update(
        {
            "applicable_symbols": applicable,
            "full_count": full,
            "partial_count": partial,
            "no_data_count": no_data,
            "fetch_failure_count": fetch_failure,
        }
    )

    reason_codes: list[str] = []
    messages: list[str] = []
    if partial > 0:
        reason_codes.append("PF-FMP-001")
        messages.append("FMP coverage is partial for part of the applicable universe.")
    if no_data > 0:
        reason_codes.append("PF-FMP-003")
        messages.append("FMP has explicit NO_DATA rows for part of the applicable universe.")
    if fetch_failure > 0:
        reason_codes.append("PF-FMP-004")
        messages.append("FMP reports explicit fetch failures.")

    status = COMPONENT_READY if not reason_codes else COMPONENT_DEGRADED
    if applicable == 0:
        status = COMPONENT_UNAVAILABLE
    return PreflightComponentResult(
        name="fmp",
        status=status,
        reason_codes=tuple(reason_codes),
        messages=tuple(messages),
        metrics=metrics,
    )


def _build_optional_providers_component(*, repo_root: Path) -> PreflightComponentResult:
    provider_paths = {
        "zacks": repo_root / "data" / "signals" / "zacks" / "latest_zacks.csv",
        "danelfin": repo_root / "data" / "signals" / "danelfin" / "latest_danelfin.csv",
        "yahoo_supplemental": repo_root / "data" / "signals" / "yahoo" / "latest_yahoo_supplemental.csv",
    }

    metrics: dict[str, Any] = {}
    reason_codes: list[str] = []
    messages: list[str] = []
    unavailable = 0
    for provider, path in provider_paths.items():
        exists = path.exists()
        row_count = 0
        if exists:
            try:
                row_count = len(_read_csv_rows(path))
            except Exception:
                row_count = 0
        metrics[provider] = {
            "path": str(path),
            "exists": exists,
            "row_count": row_count,
        }
        if not exists or row_count == 0:
            unavailable += 1
            reason_codes.append("PF-PROVIDER-001")
            messages.append(f"Optional provider lane unavailable: {provider}.")

    if unavailable == len(provider_paths):
        status = COMPONENT_UNAVAILABLE
    elif unavailable > 0:
        status = COMPONENT_DEGRADED
    else:
        status = COMPONENT_READY
    return PreflightComponentResult(
        name="optional_providers",
        status=status,
        reason_codes=tuple(reason_codes),
        messages=tuple(messages),
        metrics=metrics,
    )


def _build_replay_component(*, repo_root: Path) -> PreflightComponentResult:
    availability_path = repo_root / "data" / "current" / "replay_availability.csv"
    matrix_path = repo_root / "data" / "current" / "replay_matrix.csv"
    metrics: dict[str, Any] = {
        "replay_availability_path": str(availability_path),
        "replay_matrix_path": str(matrix_path),
        "replay_unavailable_not_score_zero": True,
    }

    if not availability_path.exists() and not matrix_path.exists():
        return PreflightComponentResult(
            name="replay",
            status=COMPONENT_DEGRADED,
            reason_codes=("PF-REPLAY-001",),
            messages=("Replay artifacts are unavailable and must not be treated as score zero.",),
            metrics=metrics,
        )

    rows = _read_csv_rows(availability_path) if availability_path.exists() else []
    generated = 0
    for row in rows:
        replay_generated = str(row.get("replay_generated", "")).strip().lower()
        if replay_generated in {"true", "1", "yes"}:
            generated += 1
    metrics.update({"availability_row_count": len(rows), "generated_count": generated})

    if rows and generated > 0:
        return PreflightComponentResult(
            name="replay",
            status=COMPONENT_READY,
            metrics=metrics,
        )

    return PreflightComponentResult(
        name="replay",
        status=COMPONENT_DEGRADED,
        reason_codes=("PF-REPLAY-001",),
        messages=("Replay is unavailable for current artifacts and is not equivalent to zero returns.",),
        metrics=metrics,
    )


def _build_pis_component(*, repo_root: Path) -> PreflightComponentResult:
    manifest_path = repo_root / "data" / "portfolio_ingestion" / "manifest.json"
    history_path = repo_root / "data" / "history" / "pis" / "canonical" / "canonical_daily_snapshots.csv"
    current_state_available = False
    historical_gap = not history_path.exists()

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            runs = manifest.get("portfolios", []) if isinstance(manifest, dict) else []
            current_state_available = any(str(item.get("status", "")).upper() == "COMPLETE" for item in runs if isinstance(item, dict))
        except Exception:
            current_state_available = False

    metrics = {
        "manifest_path": str(manifest_path),
        "pis_history_path": str(history_path),
        "current_state": "CURRENT_STATE_AVAILABLE" if current_state_available else "UNAVAILABLE",
        "historical_state": "HISTORICAL_GAP" if historical_gap else "AVAILABLE",
    }

    reason_codes: list[str] = []
    messages: list[str] = []
    if historical_gap:
        reason_codes.append("PF-PIS-001")
        messages.append("Historical PIS/private state has gaps and is explicitly degraded.")
    if not current_state_available:
        reason_codes.append("PF-PIS-002")
        messages.append("Current PIS state is unavailable.")

    if not current_state_available:
        status = COMPONENT_UNAVAILABLE
    elif reason_codes:
        status = COMPONENT_DEGRADED
    else:
        status = COMPONENT_READY

    return PreflightComponentResult(
        name="pis_history",
        status=status,
        reason_codes=tuple(reason_codes),
        messages=tuple(messages),
        metrics=metrics,
    )


def _build_benchmark_component(*, repo_root: Path) -> PreflightComponentResult:
    bench_path = repo_root / "data" / "current" / "benchmark_returns.csv"
    registry_path = repo_root / "data" / "history" / "analytical_snapshot_registry.csv"
    metrics: dict[str, Any] = {
        "benchmark_returns_path": str(bench_path),
        "analytical_snapshot_registry_path": str(registry_path),
        "exists": bench_path.exists(),
    }
    reason_codes: list[str] = []
    messages: list[str] = []

    if not bench_path.exists():
        reason_codes.append("PF-BENCH-001")
        messages.append("Benchmark returns artifact is missing.")
        return PreflightComponentResult(
            name="benchmark_foundation",
            status=COMPONENT_BLOCKED,
            reason_codes=tuple(reason_codes),
            messages=tuple(messages),
            metrics=metrics,
        )

    rows = _read_csv_rows(bench_path)
    if not rows:
        reason_codes.append("PF-BENCH-001")
        messages.append("Benchmark returns artifact is empty.")
        return PreflightComponentResult(
            name="benchmark_foundation",
            status=COMPONENT_BLOCKED,
            reason_codes=tuple(reason_codes),
            messages=tuple(messages),
            metrics=metrics,
        )

    dates: list[date] = []
    benchmark_ids: set[str] = set()
    for row in rows:
        bid = str(row.get("benchmark_id", "")).strip()
        if bid:
            benchmark_ids.add(bid)
        d = _parse_iso_date(str(row.get("date", "")))
        if d is not None:
            dates.append(d)

    if not dates:
        reason_codes.append("PF-FOUNDATION-001")
        messages.append("Benchmark returns have invalid or missing date values.")
        status = COMPONENT_BLOCKED
    else:
        curve_depth = len(dates)
        min_date = min(dates)
        max_date = max(dates)
        metrics.update(
            {
                "curve_depth": curve_depth,
                "history_start_date": min_date.isoformat(),
                "history_end_date": max_date.isoformat(),
                "benchmark_count": len(benchmark_ids),
            }
        )
        status = COMPONENT_READY

    last_foundation_run = ""
    if registry_path.exists():
        registry_rows = _read_csv_rows(registry_path)
        if registry_rows:
            last_foundation_run = str(registry_rows[-1].get("created_at_utc", "")).strip()
    metrics["last_successful_foundation_run"] = last_foundation_run

    return PreflightComponentResult(
        name="benchmark_foundation",
        status=status,
        reason_codes=tuple(reason_codes),
        messages=tuple(messages),
        metrics=metrics,
    )


def run_analysis_preflight(
    *,
    repo_root: str | Path,
    require_active_ess: bool = True,
    holdings_rows: Iterable[Mapping[str, Any]] | None = None,
) -> AnalysisPreflightResult:
    """Execute deterministic preflight checks without any provider fetches."""

    root = Path(repo_root)
    checked_at = _now_utc_iso()
    policy = load_preflight_policy(root)
    max_active_ess_age_days = int(policy["max_active_ess_age_days"])
    l1_coverage_threshold_pct = float(policy["l1_recognized_mv_coverage_block_threshold_pct"])
    resolved_holdings = list(holdings_rows or _load_latest_holdings_rows(root))

    au_component, snapshot_date_hint = _build_au_component(
        repo_root=root,
        coverage_threshold_pct=l1_coverage_threshold_pct,
        holdings_rows=resolved_holdings,
    )
    ess_component = _build_ess_component(
        repo_root=root,
        max_age_days=max_active_ess_age_days,
        require_active_ess=require_active_ess,
        holdings_rows=resolved_holdings,
        snapshot_date_hint=snapshot_date_hint,
    )
    geo_component = _build_geography_component(
        repo_root=root,
        au_component=au_component,
        holdings_rows=resolved_holdings,
    )
    fmp_component = _build_fmp_component(repo_root=root)
    providers_component = _build_optional_providers_component(repo_root=root)
    replay_component = _build_replay_component(repo_root=root)
    pis_component = _build_pis_component(repo_root=root)
    benchmark_component = _build_benchmark_component(repo_root=root)

    components = {
        "analytical_universe": au_component,
        "ess_freshness": ess_component,
        "geography": geo_component,
        "fmp": fmp_component,
        "optional_providers": providers_component,
        "replay": replay_component,
        "pis_history": pis_component,
        "benchmark_foundation": benchmark_component,
    }

    blocked_components = [
        name
        for name, comp in components.items()
        if comp.status == COMPONENT_BLOCKED
    ]
    degraded_or_unavailable = [
        name
        for name, comp in components.items()
        if comp.status in {COMPONENT_DEGRADED, COMPONENT_UNAVAILABLE}
    ]

    if blocked_components:
        status = PRECHECK_BLOCKED
    elif degraded_or_unavailable:
        status = PRECHECK_DEGRADED
    else:
        status = PRECHECK_READY

    reason_codes: list[str] = []
    messages: list[str] = []
    for comp in components.values():
        reason_codes.extend(list(comp.reason_codes))
        messages.extend(list(comp.messages))

    if status == PRECHECK_BLOCKED:
        messages.insert(0, "Action-oriented outputs are suppressed until blocking prerequisites are resolved.")

    suppression = {
        "suppress_action_recommendation_cards": status == PRECHECK_BLOCKED,
        "suppress_deployment_queue": status == PRECHECK_BLOCKED,
        "suppress_deployment_plan": status == PRECHECK_BLOCKED,
        "suppress_capital_allocation_guidance": status == PRECHECK_BLOCKED,
        "suppress_actionable_adds_trims": status == PRECHECK_BLOCKED,
    }

    global_metrics = {
        "policy": {
            "max_active_ess_age_days": max_active_ess_age_days,
            "l1_recognized_mv_coverage_block_threshold_pct": l1_coverage_threshold_pct,
        },
        "blocked_components": blocked_components,
        "degraded_or_unavailable_components": degraded_or_unavailable,
        "holdings_rows_evaluated": len(resolved_holdings),
        "require_active_ess": require_active_ess,
    }

    return AnalysisPreflightResult(
        status=status,
        checked_at=checked_at,
        reason_codes=_stable_unique(reason_codes),
        messages=tuple(messages),
        snapshot_date=snapshot_date_hint,
        components=components,
        suppression_flags=suppression,
        metrics=global_metrics,
    )


def format_preflight_summary(result: AnalysisPreflightResult) -> str:
    """Return concise human-readable summary for CLI diagnostics."""

    lines = [f"OVERALL STATUS: {result.status}", f"CHECKED AT: {result.checked_at}"]
    if result.snapshot_date:
        lines.append(f"SNAPSHOT DATE: {result.snapshot_date}")
    lines.append("COMPONENT STATUS:")
    for name, component in result.components.items():
        lines.append(f"- {name}: {component.status}")
        for code in component.reason_codes:
            lines.append(f"  - {code}")
    if result.reason_codes:
        lines.append("REASON CODES: " + ", ".join(result.reason_codes))
    return "\n".join(lines)