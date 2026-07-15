from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from src.portfolio.regime.market_regime_guardrail import market_regime_guardrail_latest
from src.portfolio.regime.market_regime_proxy_artifacts import (
    DEDICATED_HISTORY_CSV,
    DEDICATED_HISTORY_SOURCE,
    DEDICATED_INPUTS_CSV,
    DEDICATED_SUMMARY_JSON,
    LEGACY_REPLAY_FALLBACK_SOURCE,
    LEGACY_YAHOO_SNAPSHOT_FALLBACK_SOURCE,
    build_market_regime_proxy_artifacts,
    fetch_market_regime_proxy_history,
    load_market_regime_rotation_summary,
)


class _FakeProvider:
    def __init__(self, data_by_symbol: dict[str, list[tuple[str, float]]]) -> None:
        self.data_by_symbol = data_by_symbol
        self.calls: list[tuple[list[str], str, str]] = []

    def get_batch_prices(self, symbols: list[str], start_date: str, end_date: str):
        self.calls.append((list(symbols), start_date, end_date))

        class _Point:
            def __init__(self, d: str, v: float) -> None:
                self.date = d
                self.value = v

        return {
            s: [_Point(d, v) for d, v in self.data_by_symbol.get(s, [])]
            for s in symbols
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _seed_manifest_and_holdings(repo_root: Path) -> None:
    run_id = "PAR-TEST-001"
    manifest = {
        "portfolios": [
            {
                "run_id": run_id,
                "snapshot_date": "2026-07-15",
                "created_at_utc": "2026-07-15T12:00:00Z",
                "status": "COMPLETE",
            }
        ]
    }
    (repo_root / "data" / "portfolio_ingestion").mkdir(parents=True, exist_ok=True)
    (repo_root / "data" / "portfolio_ingestion" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    _write_csv(
        repo_root / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "holdings.csv",
        ["symbol", "industry", "market_value"],
        [
            {"symbol": "MSFT", "industry": "TECHNOLOGY", "market_value": 10000},
            {"symbol": "XOM", "industry": "ENERGY", "market_value": 8000},
            {"symbol": "NUE", "industry": "BASIC MATERIALS", "market_value": 6000},
            {"symbol": "CAT", "industry": "INDUSTRIALS", "market_value": 7000},
        ],
    )

    _write_csv(
        repo_root / "data" / "current" / "signal_snapshot.csv",
        ["symbol", "snapshot_date", "starmine_ess_numeric"],
        [
            {"symbol": "MSFT", "snapshot_date": "2026-07-15", "starmine_ess_numeric": 1.8},
            {"symbol": "XOM", "snapshot_date": "2026-07-15", "starmine_ess_numeric": 4.5},
            {"symbol": "NUE", "snapshot_date": "2026-07-15", "starmine_ess_numeric": 4.3},
            {"symbol": "CAT", "snapshot_date": "2026-07-15", "starmine_ess_numeric": 4.1},
        ],
    )


def _symbol_series(start: date, count: int, base: float) -> list[tuple[str, float]]:
    return [((start + timedelta(days=i)).isoformat(), base + i) for i in range(count)]


def _write_dedicated_history(repo_root: Path, series_by_symbol: dict[str, list[tuple[str, float]]]) -> None:
    path = repo_root / "data" / "current" / DEDICATED_HISTORY_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for symbol, points in series_by_symbol.items():
        for d, v in points:
            rows.append(
                {
                    "date": d,
                    "symbol": symbol,
                    "proxy_group": "technology" if symbol == "XLK" else "hard_asset",
                    "price": v,
                    "price_field": "adjusted_close",
                    "provider": "YAHOO_FINANCE",
                    "source_timestamp": d,
                    "retrieved_at_utc": "2026-07-15T00:00:00Z",
                    "status": "OK",
                }
            )
    rows.sort(key=lambda r: (str(r["date"]), str(r["symbol"])))
    _write_csv(
        path,
        [
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
        rows,
    )


def _write_legacy_snapshots(repo_root: Path, series_by_symbol: dict[str, list[tuple[str, float]]]) -> None:
    yahoo_dir = repo_root / "data" / "signals" / "yahoo"
    yahoo_dir.mkdir(parents=True, exist_ok=True)

    by_date: dict[str, dict[str, float]] = {}
    for symbol, points in series_by_symbol.items():
        for d, v in points:
            by_date.setdefault(d, {})[symbol] = v

    for d, symbol_values in sorted(by_date.items()):
        rows = []
        for symbol, v in sorted(symbol_values.items()):
            rows.append(
                {
                    "symbol": symbol,
                    "price_target": "",
                    "abr": "",
                    "analyst_count": "",
                    "eps_growth_5yr": "",
                    "current_price": f"{v:.2f}",
                    "upside_pct": "",
                    "sourced_date": d,
                }
            )
        _write_csv(
            yahoo_dir / f"{d}_yahoo_supplemental.csv",
            [
                "symbol",
                "price_target",
                "abr",
                "analyst_count",
                "eps_growth_5yr",
                "current_price",
                "upside_pct",
                "sourced_date",
            ],
            rows,
        )


def test_fetch_requests_exact_four_symbols_and_publishes_on_61_plus(tmp_path: Path) -> None:
    repo_root = tmp_path
    start = date(2026, 3, 1)
    provider = _FakeProvider(
        {
            "XLK": _symbol_series(start, 70, 100),
            "XLE": _symbol_series(start, 70, 110),
            "XLB": _symbol_series(start, 70, 120),
            "XLI": _symbol_series(start, 70, 130),
        }
    )

    result = fetch_market_regime_proxy_history(repo_root=repo_root, provider=provider)

    assert provider.calls
    assert provider.calls[0][0] == ["XLK", "XLE", "XLB", "XLI"]
    assert result["status"] == "completed"
    assert result["published"] is True
    assert result["missing_symbols"] == []
    assert result["insufficient_symbols"] == []
    for s in ("XLK", "XLE", "XLB", "XLI"):
        assert result["observations_by_symbol"][s] >= 61


def test_fetch_fails_with_sixty_observations(tmp_path: Path) -> None:
    repo_root = tmp_path
    start = date(2026, 3, 1)
    provider = _FakeProvider(
        {
            "XLK": _symbol_series(start, 60, 100),
            "XLE": _symbol_series(start, 60, 110),
            "XLB": _symbol_series(start, 60, 120),
            "XLI": _symbol_series(start, 60, 130),
        }
    )

    result = fetch_market_regime_proxy_history(repo_root=repo_root, provider=provider)
    assert result["status"] == "failed"
    assert sorted(result["insufficient_symbols"]) == ["XLB", "XLE", "XLI", "XLK"]


def test_fetch_rejects_duplicate_nonpositive_future_and_missing_symbols(tmp_path: Path) -> None:
    repo_root = tmp_path
    today = date.today()
    bad = {
        "XLK": [((today - timedelta(days=2)).isoformat(), 100.0), ((today - timedelta(days=2)).isoformat(), 101.0)],
        "XLE": [((today + timedelta(days=1)).isoformat(), 110.0)],
        "XLB": [((today - timedelta(days=1)).isoformat(), -5.0)],
        "XLI": [],
    }
    provider = _FakeProvider(bad)
    result = fetch_market_regime_proxy_history(repo_root=repo_root, provider=provider)

    assert result["status"] == "failed"
    warning_text = " ".join(result["warnings"])
    assert "duplicate_symbol_date" in warning_text
    assert "future_date" in warning_text
    assert "nonpositive_price" in warning_text
    assert "XLI" in " ".join(result["missing_symbols"] + result["insufficient_symbols"])


def test_fetch_preserves_prior_history_on_failure(tmp_path: Path) -> None:
    repo_root = tmp_path
    current = repo_root / "data" / "current"
    current.mkdir(parents=True, exist_ok=True)
    history = current / DEDICATED_HISTORY_CSV
    history.write_text(
        "date,symbol,proxy_group,price,price_field,provider,source_timestamp,retrieved_at_utc,status\n"
        "2026-07-10,XLK,technology,100,adjusted_close,YAHOO_FINANCE,2026-07-10,2026-07-10T00:00:00Z,OK\n",
        encoding="utf-8",
    )
    before = _sha256(history)

    provider = _FakeProvider({"XLK": [], "XLE": [], "XLB": [], "XLI": []})
    result = fetch_market_regime_proxy_history(repo_root=repo_root, provider=provider)

    assert result["status"] == "failed"
    assert _sha256(history) == before


def test_builder_prefers_dedicated_history_and_keeps_replay_hashes(tmp_path: Path) -> None:
    repo_root = tmp_path
    _seed_manifest_and_holdings(repo_root)

    start = date(2026, 3, 1)
    _write_dedicated_history(
        repo_root,
        {
            "XLK": _symbol_series(start, 70, 100),
            "XLE": _symbol_series(start, 70, 110),
            "XLB": _symbol_series(start, 70, 120),
            "XLI": _symbol_series(start, 70, 130),
        },
    )

    replay_inputs = repo_root / "data" / "current" / "replay_inputs.csv"
    replay_series = repo_root / "data" / "current" / "replay_performance_series.csv"
    replay_inputs.write_text("replay_id\nRID1\n", encoding="utf-8")
    replay_series.write_text("replay_id\nRID1\n", encoding="utf-8")
    replay_hashes_before = (_sha256(replay_inputs), _sha256(replay_series))

    result = build_market_regime_proxy_artifacts(repo_root=repo_root)
    assert result["status"] == "completed"
    assert result["published"] is True
    assert result["input_source"] == DEDICATED_HISTORY_SOURCE
    assert result["missing_inputs"] == []

    summary_path = repo_root / "data" / "current" / DEDICATED_SUMMARY_JSON
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["input_source"] == DEDICATED_HISTORY_SOURCE
    assert payload["latest_proxy_date"]
    assert payload["freshness"]["status"] in {"FRESH", "STALE"}

    # Ensure trading-observation windows are computed and present.
    for k in ("5d", "20d", "60d"):
        assert payload["technology_proxy"][k] is not None
        assert payload["hard_asset_proxy"][k] is not None

    assert (_sha256(replay_inputs), _sha256(replay_series)) == replay_hashes_before


def test_builder_uses_legacy_snapshot_fallback_when_dedicated_missing(tmp_path: Path) -> None:
    repo_root = tmp_path
    _seed_manifest_and_holdings(repo_root)

    start = date(2026, 3, 1)
    _write_legacy_snapshots(
        repo_root,
        {
            "XLK": _symbol_series(start, 70, 100),
            "XLE": _symbol_series(start, 70, 110),
            "XLB": _symbol_series(start, 70, 120),
            "XLI": _symbol_series(start, 70, 130),
        },
    )

    result = build_market_regime_proxy_artifacts(repo_root=repo_root)
    assert result["status"] == "completed"
    assert result["input_source"] == LEGACY_YAHOO_SNAPSHOT_FALLBACK_SOURCE


def test_loader_and_guardrail_surface_dedicated_input_source(tmp_path: Path) -> None:
    repo_root = tmp_path
    current_root = repo_root / "data" / "current"
    current_root.mkdir(parents=True, exist_ok=True)

    summary, source, warnings = load_market_regime_rotation_summary(repo_root)
    assert summary is None
    assert source == LEGACY_REPLAY_FALLBACK_SOURCE
    assert warnings == []

    summary_path = current_root / DEDICATED_SUMMARY_JSON
    summary_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "source": "dedicated_market_regime_proxy_artifact",
                "generated_at_utc": "2026-07-15T00:00:00Z",
                "latest_proxy_date": "2026-07-15",
                "required_inputs": [],
                "missing_inputs": [],
                "technology_proxy": {"5d": 1.0, "20d": 2.0, "60d": 3.0},
                "hard_asset_proxy": {"5d": 0.8, "20d": 1.2, "60d": 1.8},
                "freshness": {},
                "provenance": {},
                "warnings": [],
                "rotation_summary": {
                    "status": "OK",
                    "signal": "NO_CLEAR_SIGNAL",
                    "risk_score": 48,
                    "as_of_date": "2026-07-15",
                    "confirmation": {"confirmation_passed": False},
                    "proxy_returns": {
                        "latest_proxy_date": "2026-07-15",
                        "tech_returns": {"5d": 1.0, "20d": 2.0, "60d": 3.0},
                        "rotation_spread_pct": {"5d": 0.1, "20d": 0.2, "60d": 0.3},
                    },
                    "portfolio_exposure": {"tech_pct": 30.0},
                    "data_quality": {"missing_inputs": []},
                },
                "input_source": DEDICATED_HISTORY_SOURCE,
                "transaction_id": "MRG-DEDICATED-test",
            }
        ),
        encoding="utf-8",
    )

    payload = market_regime_guardrail_latest(repo_root)
    assert payload["input_source"] == DEDICATED_HISTORY_SOURCE
