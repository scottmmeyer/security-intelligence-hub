from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.portfolio.regime.market_regime_inputs import evaluate_market_proxy_freshness
from src.replay.history_providers import PricePoint, YahooHistoricalPriceProvider
from src.sih.rotation_risk_monitor import (
    _HARD_ASSET_INDUSTRIES,
    _classify_signal,
    _cohort_confirmation,
    _latest_run_id,
    _latest_signal_snapshot,
    _load_holdings,
    _portfolio_exposure,
)

DEDICATED_HISTORY_CSV = "market_regime_proxy_price_history.csv"
DEDICATED_INPUTS_CSV = "market_regime_proxy_inputs.csv"
DEDICATED_SUMMARY_JSON = "market_regime_proxy_summary.json"

DEDICATED_HISTORY_SOURCE = "dedicated_market_regime_price_history"
LEGACY_YAHOO_SNAPSHOT_FALLBACK_SOURCE = "legacy_yahoo_snapshot_fallback"
LEGACY_REPLAY_FALLBACK_SOURCE = "legacy_replay_fallback"

_PROXY_SYMBOLS_BY_COHORT = {
    "TECHNOLOGY": "XLK",
    "ENERGY": "XLE",
    "BASIC MATERIALS": "XLB",
    "INDUSTRIALS": "XLI",
}

_REQUIRED_COHORTS = ("TECHNOLOGY", "ENERGY", "BASIC MATERIALS", "INDUSTRIALS")
_REQUIRED_SYMBOLS = tuple(_PROXY_SYMBOLS_BY_COHORT[c] for c in _REQUIRED_COHORTS)
_REQUIRED_WINDOWS = (5, 20, 60)
_MIN_REQUIRED_OBSERVATIONS = 61


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def _latest_portfolio_snapshot_date(repo_root: Path) -> str:
    manifest_path = repo_root / "data" / "portfolio_ingestion" / "manifest.json"
    if not manifest_path.exists():
        return date.today().isoformat()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        portfolios = [
            p
            for p in (manifest.get("portfolios") or [])
            if isinstance(p, dict) and p.get("status") == "COMPLETE"
        ]
        if not portfolios:
            return date.today().isoformat()
        latest = portfolios[-1]
        snap = str(latest.get("snapshot_date") or latest.get("as_of_date") or "").strip()
        return snap or date.today().isoformat()
    except Exception:
        return date.today().isoformat()


def _normalize_points(points: list[PricePoint]) -> list[tuple[str, float]]:
    out = [(str(p.date), float(p.value)) for p in points if str(p.date).strip()]
    out.sort(key=lambda x: x[0])
    return out


def _validate_history_rows(rows: list[dict[str, str]]) -> tuple[list[str], dict[str, int], str | None, str | None]:
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()
    by_symbol_dates: dict[str, list[str]] = {s: [] for s in _REQUIRED_SYMBOLS}
    by_symbol_count: dict[str, int] = {s: 0 for s in _REQUIRED_SYMBOLS}
    earliest_date: str | None = None

    today = date.today().isoformat()

    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        d = str(row.get("date") or "").strip()
        price_raw = str(row.get("price") or "").strip()
        if symbol not in _REQUIRED_SYMBOLS:
            warnings.append(f"unexpected_symbol:{symbol}")
            continue
        if not d:
            warnings.append(f"missing_date:{symbol}")
            continue
        if d > today:
            warnings.append(f"future_date:{symbol}:{d}")
            continue

        key = (symbol, d)
        if key in seen:
            warnings.append(f"duplicate_symbol_date:{symbol}:{d}")
            continue
        seen.add(key)

        try:
            price = float(price_raw)
        except Exception:
            warnings.append(f"invalid_price:{symbol}:{d}")
            continue
        if price <= 0:
            warnings.append(f"nonpositive_price:{symbol}:{d}")
            continue

        by_symbol_dates[symbol].append(d)
        by_symbol_count[symbol] += 1
        if earliest_date is None or d < earliest_date:
            earliest_date = d

    insufficient = [s for s, c in by_symbol_count.items() if c < _MIN_REQUIRED_OBSERVATIONS]
    for s in insufficient:
        warnings.append(f"insufficient_observations:{s}:{by_symbol_count[s]}")

    date_sets = [set(v) for v in by_symbol_dates.values() if v]
    latest_common_date: str | None = None
    if len(date_sets) == len(_REQUIRED_SYMBOLS):
        common = set.intersection(*date_sets)
        if common:
            latest_common_date = sorted(common)[-1]
        else:
            warnings.append("latest_common_date_missing")
    else:
        warnings.append("latest_common_date_missing")

    return warnings, by_symbol_count, earliest_date, latest_common_date


def fetch_market_regime_proxy_history(
    *,
    repo_root: Path,
    symbols: tuple[str, ...] = _REQUIRED_SYMBOLS,
    lookback_calendar_days: int = 120,
    min_required_observations: int = _MIN_REQUIRED_OBSERVATIONS,
    provider: YahooHistoricalPriceProvider | None = None,
) -> dict[str, Any]:
    current_root = repo_root / "data" / "current"
    current_root.mkdir(parents=True, exist_ok=True)
    target_history = current_root / DEDICATED_HISTORY_CSV

    tx_id = f"MRG-HISTORY-{uuid.uuid4()}"
    before_hash = _sha256(target_history)
    before_rows = _row_count(target_history)

    requested = tuple(str(s).strip().upper() for s in symbols if str(s).strip())
    warnings: list[str] = []

    if requested != _REQUIRED_SYMBOLS:
        return {
            "attempted": True,
            "status": "failed",
            "published": False,
            "symbols": list(requested),
            "observations_by_symbol": {},
            "earliest_date": None,
            "latest_common_date": None,
            "missing_symbols": sorted(list(set(_REQUIRED_SYMBOLS).difference(set(requested)))),
            "insufficient_symbols": [],
            "warnings": ["symbol_set_must_match_required_proxies"],
            "transaction_id": tx_id,
            "hashes_before": {"sha256": before_hash, "rows": before_rows},
            "hashes_after": {"sha256": _sha256(target_history), "rows": _row_count(target_history)},
        }

    end = date.today()
    start = end - timedelta(days=int(lookback_calendar_days))

    history_provider = provider or YahooHistoricalPriceProvider()
    batch = history_provider.get_batch_prices(list(requested), start.isoformat(), end.isoformat())

    rows: list[dict[str, str]] = []
    observations_by_symbol: dict[str, int] = {}
    missing_symbols: list[str] = []

    retrieved_at = datetime.now(timezone.utc).isoformat()
    for symbol in requested:
        points = _normalize_points(list(batch.get(symbol, [])))
        observations_by_symbol[symbol] = len(points)
        if not points:
            missing_symbols.append(symbol)
        for d, v in points:
            rows.append(
                {
                    "date": d,
                    "symbol": symbol,
                    "proxy_group": "technology" if symbol == "XLK" else "hard_asset",
                    "price": f"{float(v):.8f}",
                    "price_field": "adjusted_close",
                    "provider": "YAHOO_FINANCE",
                    "source_timestamp": d,
                    "retrieved_at_utc": retrieved_at,
                    "status": "OK",
                }
            )

    rows.sort(key=lambda r: (r["date"], r["symbol"]))

    validation_warnings, obs_counts, earliest_date, latest_common_date = _validate_history_rows(rows)
    warnings.extend(validation_warnings)

    insufficient_symbols = sorted([s for s, c in obs_counts.items() if c < int(min_required_observations)])

    published = False
    status = "completed"
    if missing_symbols or insufficient_symbols or warnings or not latest_common_date:
        status = "failed"
    else:
        stage_dir = Path(tempfile.mkdtemp(prefix="market-regime-history-stage-"))
        staged = stage_dir / DEDICATED_HISTORY_CSV
        with staged.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "date",
                    "symbol",
                    "proxy_group",
                    "price",
                    "price_field",
                    "provider",
                    "source_timestamp",
                    "retrieved_at_utc",
                    "status",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        staged.replace(target_history)
        published = True

    return {
        "attempted": True,
        "status": status,
        "published": published,
        "symbols": list(requested),
        "observations_by_symbol": observations_by_symbol,
        "earliest_date": earliest_date,
        "latest_common_date": latest_common_date,
        "missing_symbols": sorted(missing_symbols),
        "insufficient_symbols": insufficient_symbols,
        "warnings": warnings,
        "transaction_id": tx_id,
        "artifact": f"data/current/{DEDICATED_HISTORY_CSV}",
        "hashes_before": {"sha256": before_hash, "rows": before_rows},
        "hashes_after": {"sha256": _sha256(target_history), "rows": _row_count(target_history)},
    }


def _load_dedicated_price_history(repo_root: Path) -> tuple[dict[str, list[tuple[str, float]]], list[str]]:
    history_path = repo_root / "data" / "current" / DEDICATED_HISTORY_CSV
    if not history_path.exists():
        return {}, ["dedicated_history_missing"]

    rows: list[dict[str, str]] = []
    with history_path.open("r", encoding="utf-8", newline="") as fh:
        rows = [dict(r) for r in csv.DictReader(fh)]

    warnings, _, _, _ = _validate_history_rows(rows)
    if warnings:
        return {}, warnings

    by_symbol: dict[str, list[tuple[str, float]]] = {s: [] for s in _REQUIRED_SYMBOLS}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol not in by_symbol:
            continue
        by_symbol[symbol].append((str(row.get("date") or "").strip(), float(row.get("price") or 0.0)))

    for symbol in by_symbol:
        by_symbol[symbol].sort(key=lambda x: x[0])
    return by_symbol, []


def _load_legacy_snapshot_history(repo_root: Path) -> tuple[dict[str, list[tuple[str, float]]], list[str]]:
    yahoo_dir = repo_root / "data" / "signals" / "yahoo"
    out: dict[str, dict[str, float]] = {s: {} for s in _REQUIRED_SYMBOLS}
    if not yahoo_dir.exists():
        return {}, ["legacy_yahoo_snapshot_dir_missing"]

    files = sorted(yahoo_dir.glob("20??-??-??_yahoo_supplemental.csv"))
    for path in files:
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                symbol = str(row.get("symbol") or "").strip().upper()
                if symbol not in out:
                    continue
                d = str(row.get("sourced_date") or "").strip()
                try:
                    price = float(str(row.get("current_price") or "").strip())
                except Exception:
                    continue
                if d and price > 0:
                    out[symbol][d] = price

    normalized = {
        s: sorted([(d, v) for d, v in values.items()], key=lambda x: x[0])
        for s, values in out.items()
    }

    # Reuse strict minimum requirement to prevent weak fallback publication.
    warnings: list[str] = []
    for s in _REQUIRED_SYMBOLS:
        if len(normalized.get(s, [])) < _MIN_REQUIRED_OBSERVATIONS:
            warnings.append(f"legacy_insufficient_observations:{s}:{len(normalized.get(s, []))}")
    return normalized, warnings


def _compute_returns_from_trading_observations(
    by_symbol_prices: dict[str, list[tuple[str, float]]],
) -> tuple[dict[str, dict[int, float]], str | None, list[str]]:
    warnings: list[str] = []
    date_sets = [set(d for d, _ in by_symbol_prices.get(s, [])) for s in _REQUIRED_SYMBOLS]
    if any(len(x) == 0 for x in date_sets):
        return {}, None, ["missing_symbol_history"]

    common = set.intersection(*date_sets)
    if not common:
        return {}, None, ["latest_common_date_missing"]

    latest_common_date = sorted(common)[-1]

    returns_by_cohort: dict[str, dict[int, float]] = {}
    for cohort in _REQUIRED_COHORTS:
        symbol = _PROXY_SYMBOLS_BY_COHORT[cohort]
        ordered = by_symbol_prices.get(symbol, [])
        dates = [d for d, _ in ordered]
        prices = [float(v) for _, v in ordered]
        if latest_common_date not in dates:
            warnings.append(f"latest_common_not_in_symbol:{symbol}")
            continue
        idx = dates.index(latest_common_date)
        cohort_returns: dict[int, float] = {}
        for w in _REQUIRED_WINDOWS:
            older_idx = idx - w
            if older_idx < 0:
                warnings.append(f"insufficient_window:{symbol}:{w}")
                continue
            older = prices[older_idx]
            latest = prices[idx]
            if older <= 0 or latest <= 0:
                warnings.append(f"nonpositive_window_price:{symbol}:{w}")
                continue
            cohort_returns[w] = (latest / older) - 1.0
        if cohort_returns:
            returns_by_cohort[cohort] = cohort_returns

    return returns_by_cohort, latest_common_date, warnings


def _required_missing_inputs(returns_by_cohort: dict[str, dict[int, float]]) -> list[str]:
    missing: list[str] = []
    for cohort in _REQUIRED_COHORTS:
        symbol = _PROXY_SYMBOLS_BY_COHORT[cohort]
        cohort_returns = returns_by_cohort.get(cohort, {})
        for w in _REQUIRED_WINDOWS:
            if w not in cohort_returns:
                missing.append(f"{cohort} ({symbol}) missing {w}d window")
    return missing


def _build_rotation_summary_from_returns(
    *,
    repo_root: Path,
    run_id: str,
    latest_common_date: str,
    returns_by_cohort: dict[str, dict[int, float]],
    input_source: str,
) -> dict[str, Any]:
    selected_run = run_id or _latest_run_id(repo_root)
    holdings = _load_holdings(repo_root, selected_run)
    exposure = _portfolio_exposure(holdings)
    ess_by_symbol, snapshot_date = _latest_signal_snapshot(repo_root)
    confirmation = _cohort_confirmation(holdings, ess_by_symbol)

    tech_returns = returns_by_cohort.get("TECHNOLOGY", {})
    hard_returns: dict[int, float] = {}
    for w in _REQUIRED_WINDOWS:
        vals = [
            returns_by_cohort.get(industry, {}).get(w)
            for industry in _HARD_ASSET_INDUSTRIES
            if returns_by_cohort.get(industry, {}).get(w) is not None
        ]
        if vals:
            hard_returns[w] = sum(float(v) for v in vals if v is not None) / len(vals)

    spreads: dict[int, float] = {}
    for w in _REQUIRED_WINDOWS:
        t = tech_returns.get(w)
        h = hard_returns.get(w)
        if t is not None and h is not None:
            spreads[w] = float(h) - float(t)

    signal, headline, risk_score = _classify_signal(spreads, bool(confirmation.get("confirmation_passed")))
    missing_inputs = _required_missing_inputs(returns_by_cohort)

    status = "OK"
    if missing_inputs or signal == "DATA_UNAVAILABLE":
        status = "DATA_UNAVAILABLE"
        signal = "DATA_UNAVAILABLE"
        headline = "Core proxy data unavailable; rotation monitor is informationally disabled."
        risk_score = 0

    return {
        "status": status,
        "diagnostic_id": "ROTATION-RISK-01",
        "diagnostic_name": "Tech-to-hard-assets rotation monitor",
        "as_of_date": _latest_portfolio_snapshot_date(repo_root),
        "run_id": selected_run,
        "signal": signal,
        "headline": headline,
        "risk_score": risk_score,
        "governance_note": "Display-only diagnostic; no effect on ESS, CW-DAS, UCF, CRA, PAP, replay, or execution behavior.",
        "portfolio_exposure": exposure,
        "proxy_returns": {
            "selected_cap_bucket": "DEDICATED_PROXY",
            "latest_proxy_date": latest_common_date,
            "tech_returns": {f"{w}d": round(tech_returns.get(w, 0.0) * 100.0, 3) if w in tech_returns else None for w in _REQUIRED_WINDOWS},
            "hard_assets_returns": {f"{w}d": round(hard_returns.get(w, 0.0) * 100.0, 3) if w in hard_returns else None for w in _REQUIRED_WINDOWS},
            "rotation_spread_pct": {f"{w}d": round(spreads.get(w, 0.0) * 100.0, 3) if w in spreads else None for w in _REQUIRED_WINDOWS},
            "hard_asset_industry_caps": {k: "DEDICATED_PROXY" for k in _HARD_ASSET_INDUSTRIES},
        },
        "confirmation": confirmation,
        "data_quality": {
            "price_history_status": "AVAILABLE",
            "signal_snapshot_date": snapshot_date,
            "missing_inputs": missing_inputs,
            "hard_asset_proxy_count": len([x for x in _HARD_ASSET_INDUSTRIES if x in returns_by_cohort]),
        },
        "provenance": {
            "provider": "YAHOO_FINANCE",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_source": input_source,
            "symbols": {cohort: _PROXY_SYMBOLS_BY_COHORT[cohort] for cohort in _REQUIRED_COHORTS},
        },
    }


def _build_inputs_rows(
    *,
    latest_common_date: str,
    returns_by_cohort: dict[str, dict[int, float]],
    input_source: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cohort in _REQUIRED_COHORTS:
        symbol = _PROXY_SYMBOLS_BY_COHORT[cohort]
        cohort_returns = returns_by_cohort.get(cohort, {})
        for w in _REQUIRED_WINDOWS:
            value = cohort_returns.get(w)
            rows.append(
                {
                    "date": latest_common_date,
                    "proxy_group": "technology" if cohort == "TECHNOLOGY" else "hard_asset",
                    "proxy_component": cohort,
                    "source_symbol_or_cohort": symbol,
                    "source_value": "",
                    "derived_return": f"{value:.10f}" if value is not None else "",
                    "window": f"{w}d",
                    "source_timestamp": latest_common_date,
                    "provider": "YAHOO_FINANCE",
                    "status": "OK" if value is not None else "MISSING_WINDOW",
                    "input_source": input_source,
                }
            )
    return rows


def _validate_inputs_csv(path: Path) -> list[str]:
    required = {
        "date",
        "proxy_group",
        "proxy_component",
        "source_symbol_or_cohort",
        "source_value",
        "derived_return",
        "window",
        "source_timestamp",
        "provider",
        "status",
        "input_source",
    }
    if not path.exists():
        return [f"missing_file:{path.name}"]
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = sorted(required.difference(set(reader.fieldnames or [])))
        if missing:
            return [f"missing_columns:{','.join(missing)}"]
        rows = list(reader)
        if not rows:
            return ["inputs_rows_empty"]
    return []


def _validate_summary_json(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing_file:{path.name}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid_json:{exc}"]

    required = {
        "status",
        "source",
        "generated_at_utc",
        "latest_proxy_date",
        "required_inputs",
        "missing_inputs",
        "technology_proxy",
        "hard_asset_proxy",
        "freshness",
        "provenance",
        "warnings",
        "rotation_summary",
        "input_source",
        "transaction_id",
    }
    missing = sorted(required.difference(set(payload.keys())))
    if missing:
        return [f"missing_keys:{','.join(missing)}"]

    latest_proxy_date = str(payload.get("latest_proxy_date") or "").strip()
    if not latest_proxy_date:
        return ["latest_proxy_date_blank"]
    return []


def build_market_regime_proxy_artifacts(
    *,
    repo_root: Path,
    run_id: str = "",
) -> dict[str, Any]:
    current_root = repo_root / "data" / "current"
    current_root.mkdir(parents=True, exist_ok=True)

    target_inputs = current_root / DEDICATED_INPUTS_CSV
    target_summary = current_root / DEDICATED_SUMMARY_JSON
    history_path = current_root / DEDICATED_HISTORY_CSV

    tx_id = f"MRG-DEDICATED-{uuid.uuid4()}"

    before = {
        "inputs": {"sha256": _sha256(target_inputs), "rows": _row_count(target_inputs)},
        "summary": {"sha256": _sha256(target_summary), "rows": None},
    }
    latest_proxy_date_before: str | None = None
    if target_summary.exists():
        try:
            prior_payload = json.loads(target_summary.read_text(encoding="utf-8"))
            latest_proxy_date_before = str(prior_payload.get("latest_proxy_date") or "").strip() or None
        except Exception:
            latest_proxy_date_before = None

    source_warnings: list[str] = []
    if history_path.exists():
        by_symbol_prices, source_warnings = _load_dedicated_price_history(repo_root)
        input_source = DEDICATED_HISTORY_SOURCE
    else:
        by_symbol_prices, source_warnings = _load_legacy_snapshot_history(repo_root)
        input_source = LEGACY_YAHOO_SNAPSHOT_FALLBACK_SOURCE

    returns_by_cohort, latest_common_date, return_warnings = _compute_returns_from_trading_observations(by_symbol_prices)
    missing_inputs = _required_missing_inputs(returns_by_cohort)

    all_warnings = list(source_warnings) + list(return_warnings)

    if not latest_common_date:
        latest_common_date = ""

    rotation_summary = _build_rotation_summary_from_returns(
        repo_root=repo_root,
        run_id=run_id,
        latest_common_date=latest_common_date,
        returns_by_cohort=returns_by_cohort,
        input_source=input_source,
    )

    inputs_rows = _build_inputs_rows(
        latest_common_date=latest_common_date,
        returns_by_cohort=returns_by_cohort,
        input_source=input_source,
    )

    freshness = evaluate_market_proxy_freshness(
        market_proxies_ts=latest_common_date,
        portfolio_snapshot_ts=_latest_portfolio_snapshot_date(repo_root),
        threshold_days=2,
    )

    tech_proxy = (rotation_summary.get("proxy_returns") or {}).get("tech_returns") or {}
    hard_proxy = (rotation_summary.get("proxy_returns") or {}).get("hard_assets_returns") or {}

    summary_payload = {
        "status": "completed" if (not missing_inputs and latest_common_date and not all_warnings) else "failed",
        "source": "dedicated_market_regime_proxy_artifact",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_proxy_date": latest_common_date,
        "required_inputs": [
            {
                "cohort": cohort,
                "symbol": _PROXY_SYMBOLS_BY_COHORT[cohort],
                "windows": [f"{w}d" for w in _REQUIRED_WINDOWS],
            }
            for cohort in _REQUIRED_COHORTS
        ],
        "missing_inputs": list(missing_inputs),
        "technology_proxy": tech_proxy,
        "hard_asset_proxy": hard_proxy,
        "freshness": {
            "status": str(freshness.get("freshness_status") or "UNKNOWN"),
            "portfolio_date": _latest_portfolio_snapshot_date(repo_root),
            "proxy_date": latest_common_date,
            "lag_days": freshness.get("proxy_lag_days"),
            "threshold_days": int(freshness.get("freshness_threshold_days") or 2),
        },
        "provenance": {
            "provider": "YAHOO_FINANCE",
            "transaction_id": tx_id,
            "input_source": input_source,
            "proxy_symbol_map": dict(_PROXY_SYMBOLS_BY_COHORT),
        },
        "warnings": list(all_warnings),
        "rotation_summary": rotation_summary,
        "input_source": input_source,
        "transaction_id": tx_id,
    }

    stage_dir = Path(tempfile.mkdtemp(prefix="market-regime-dedicated-stage-"))
    staged_inputs = stage_dir / DEDICATED_INPUTS_CSV
    staged_summary = stage_dir / DEDICATED_SUMMARY_JSON

    with staged_inputs.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "date",
                "proxy_group",
                "proxy_component",
                "source_symbol_or_cohort",
                "source_value",
                "derived_return",
                "window",
                "source_timestamp",
                "provider",
                "status",
                "input_source",
            ],
        )
        writer.writeheader()
        for row in inputs_rows:
            writer.writerow(row)

    staged_summary.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    schema_errors: list[str] = []
    schema_errors.extend(_validate_inputs_csv(staged_inputs))
    schema_errors.extend(_validate_summary_json(staged_summary))
    if missing_inputs:
        schema_errors.append("missing_required_inputs")
    if not latest_common_date:
        schema_errors.append("latest_common_date_missing")
    if all_warnings:
        schema_errors.extend(all_warnings)

    published = False
    status = "completed"
    reason = "completed"

    if schema_errors:
        status = "failed"
        reason = "validation_failed"
    else:
        staged_inputs.replace(target_inputs)
        staged_summary.replace(target_summary)
        published = True

    after = {
        "inputs": {"sha256": _sha256(target_inputs), "rows": _row_count(target_inputs)},
        "summary": {"sha256": _sha256(target_summary), "rows": None},
    }

    latest_proxy_date_after = None
    if target_summary.exists():
        try:
            payload = json.loads(target_summary.read_text(encoding="utf-8"))
            latest_proxy_date_after = str(payload.get("latest_proxy_date") or "").strip() or None
        except Exception:
            latest_proxy_date_after = None

    return {
        "attempted": True,
        "status": status,
        "reason": reason,
        "published": published,
        "input_source": input_source if published else None,
        "latest_proxy_date_before": latest_proxy_date_before,
        "latest_proxy_date_after": latest_proxy_date_after,
        "missing_inputs": list(missing_inputs),
        "warnings": schema_errors if status != "completed" else [],
        "transaction_id": tx_id,
        "artifacts": [
            f"data/current/{DEDICATED_INPUTS_CSV}",
            f"data/current/{DEDICATED_SUMMARY_JSON}",
        ],
        "hashes_before": before,
        "hashes_after": after,
    }


def load_market_regime_rotation_summary(repo_root: Path) -> tuple[dict[str, Any] | None, str, list[str]]:
    summary_path = repo_root / "data" / "current" / DEDICATED_SUMMARY_JSON
    if not summary_path.exists():
        return None, LEGACY_REPLAY_FALLBACK_SOURCE, []

    warnings = _validate_summary_json(summary_path)
    if warnings:
        payload = {}
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        input_source = str(payload.get("input_source") or DEDICATED_HISTORY_SOURCE)
        return None, input_source, warnings

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    rotation_summary = payload.get("rotation_summary")
    if not isinstance(rotation_summary, dict):
        return None, str(payload.get("input_source") or DEDICATED_HISTORY_SOURCE), ["rotation_summary_missing"]

    return rotation_summary, str(payload.get("input_source") or DEDICATED_HISTORY_SOURCE), []
