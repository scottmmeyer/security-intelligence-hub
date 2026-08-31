from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts import refresh_signals as rs
from src.scoring import fetch_fmp_signals as fmp
from src.history.pit_observation_manager import append_pit_observations, query_pit_observations


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_FMP_STABLE_ANNUAL_PARSING_TEST() -> None:
    payload = [
        {
            "symbol": "CRM",
            "date": "2031-01-31",
            "revenueLow": 70450324705,
            "revenueHigh": 73560100852,
            "revenueAvg": 71498000000,
            "epsLow": 24.88672,
            "epsHigh": 26.32122,
            "epsAvg": 25.37,
            "numAnalystsRevenue": 21,
            "numAnalystsEps": 8,
        }
    ]
    rows = fmp._parse_analyst_estimates("CRM", payload, "2026-08-30", period="annual")
    assert len(rows) == 1
    row = rows[0]
    assert row["forecast_horizon"] == "ANNUAL"
    assert row["period_date"] == "2031-01-31"
    assert row["fiscal_period"] == "2031-01-31"
    assert row["estimated_eps_avg"] == "25.37"
    assert row["estimated_revenue_avg"] == "7.1498e+10"
    assert row["analyst_count_eps"] == "8"
    assert row["analyst_count_revenue"] == "21"


def test_FMP_STABLE_QUARTER_PARSING_TEST() -> None:
    payload = [
        {
            "symbol": "CRM",
            "date": "2027-04-30",
            "revenueLow": 10000000000,
            "revenueHigh": 11000000000,
            "revenueAvg": 10500000000,
            "epsLow": 2.1,
            "epsHigh": 2.4,
            "epsAvg": 2.2,
            "numAnalystsRevenue": 18,
            "numAnalystsEps": 12,
        }
    ]
    rows = fmp._parse_analyst_estimates("CRM", payload, "2026-08-30", period="quarter")
    assert len(rows) == 1
    row = rows[0]
    assert row["forecast_horizon"] == "QUARTER"
    assert row["period_date"] == "2027-04-30"
    assert row["fiscal_period"] == "2027-04-30"
    assert row["estimated_eps_avg"] == "2.2"
    assert row["estimated_revenue_avg"] == "1.05e+10"


def test_FMP_ANNUAL_VS_QUARTER_PERIOD_SEPARATION_TEST() -> None:
    annual_rows = fmp._parse_analyst_estimates(
        "CRM",
        [{"symbol": "CRM", "date": "2031-01-31", "epsAvg": 25.0, "revenueAvg": 71000000000}],
        "2026-08-30",
        period="annual",
    )
    quarter_rows = fmp._parse_analyst_estimates(
        "CRM",
        [{"symbol": "CRM", "date": "2027-04-30", "epsAvg": 2.2, "revenueAvg": 10500000000}],
        "2026-08-30",
        period="quarter",
    )
    assert annual_rows[0]["forecast_horizon"] == "ANNUAL"
    assert quarter_rows[0]["forecast_horizon"] == "QUARTER"


def test_FMP_ESTIMATE_PERIOD_PRESERVATION_TEST() -> None:
    rows = [
        {
            "symbol": "CRM",
            "sourced_date": "2026-08-30",
            "fetch_status": "SUCCESS",
            "period_date": "2027-01-31",
            "period_label": "",
            "fiscal_period": "2027-01-31",
            "forecast_horizon": "ANNUAL",
            "request_period": "annual",
            "estimated_eps_avg": "2.11",
            "estimated_revenue_avg": "100.5",
        }
    ]
    observations, attempted, succeeded = rs._to_pit_observations_from_fmp_estimate_rows(
        rows=rows,
        symbols=["CRM"],
        snapshot_date="2026-08-30",
        retrieved_at_utc="2026-08-30T10:00:00+00:00",
        run_id="RUN-EST-001",
    )
    assert attempted == 1
    assert succeeded == 1
    assert observations
    assert all(obs["fiscal_period"] == "2027-01-31" for obs in observations)
    assert all(obs["forecast_horizon"] == "ANNUAL" for obs in observations)


def test_FMP_EPS_REVENUE_COEXISTENCE_TEST() -> None:
    rows = [
        {
            "symbol": "MSFT",
            "sourced_date": "2026-08-30",
            "fetch_status": "SUCCESS",
            "period_date": "2027-03-31",
            "fiscal_period": "2027-03-31",
            "forecast_horizon": "QUARTER",
            "request_period": "quarter",
            "estimated_eps_avg": "3.20",
            "estimated_revenue_avg": "68000",
        }
    ]
    observations, _, _ = rs._to_pit_observations_from_fmp_estimate_rows(
        rows=rows,
        symbols=["MSFT"],
        snapshot_date="2026-08-30",
        retrieved_at_utc="2026-08-30T10:00:00+00:00",
        run_id="RUN-EST-002",
    )
    metrics = {obs["metric"] for obs in observations}
    assert "eps_estimate_avg" in metrics
    assert "revenue_estimate_avg" in metrics


def test_FMP_ESTIMATE_STATISTIC_MAPPING_TEST() -> None:
    rows = [
        {
            "symbol": "NVDA",
            "sourced_date": "2026-08-30",
            "fetch_status": "SUCCESS",
            "period_date": "2027-04-30",
            "fiscal_period": "2027-04-30",
            "forecast_horizon": "QUARTER",
            "request_period": "quarter",
            "estimated_eps_high": "4.50",
            "estimated_eps_low": "3.90",
            "analyst_count_eps": "36",
            "analyst_count_revenue": "28",
        }
    ]
    observations, _, _ = rs._to_pit_observations_from_fmp_estimate_rows(
        rows=rows,
        symbols=["NVDA"],
        snapshot_date="2026-08-30",
        retrieved_at_utc="2026-08-30T10:00:00+00:00",
        run_id="RUN-EST-003",
    )
    by_metric = {obs["metric"]: obs for obs in observations}
    assert by_metric["eps_estimate_high"]["provider_field_name"] == "estimated_eps_high"
    assert by_metric["eps_estimate_low"]["provider_field_name"] == "estimated_eps_low"
    assert by_metric["analyst_count_eps"]["value"] == "36"
    assert by_metric["analyst_count_revenue"]["value"] == "28"


def test_FMP_ESTIMATE_PIT_INTEGRATION_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fmp_root = tmp_path / "signals" / "fmp"
    headers = [
        "symbol", "sourced_date", "fetch_status", "failure_type", "failure_reason",
        "period_date", "period_label", "fiscal_period", "forecast_horizon",
        "request_period",
        "estimated_revenue_avg", "estimated_revenue_high", "estimated_revenue_low",
        "estimated_eps_avg", "estimated_eps_high", "estimated_eps_low",
        "analyst_count_revenue", "analyst_count_eps",
    ]
    _write_csv(
        fmp_root / "latest" / "latest_fmp_analyst_estimates.csv",
        headers,
        [
            {
                "symbol": "CRM",
                "sourced_date": "2026-08-30",
                "fetch_status": "SUCCESS",
                "failure_type": "",
                "failure_reason": "",
                "period_date": "2027-01-31",
                "period_label": "",
                "fiscal_period": "2027-01-31",
                "forecast_horizon": "ANNUAL",
                "request_period": "annual",
                "estimated_revenue_avg": "100.0",
                "estimated_revenue_high": "105.0",
                "estimated_revenue_low": "95.0",
                "estimated_eps_avg": "2.0",
                "estimated_eps_high": "2.3",
                "estimated_eps_low": "1.8",
                "analyst_count_revenue": "20",
                "analyst_count_eps": "18",
            }
        ],
    )
    _write_csv(
        fmp_root / "latest" / "latest_fmp_grades_consensus.csv",
        ["symbol", "sourced_date", "consensus_label"],
        [{"symbol": "CRM", "sourced_date": "2026-08-30", "consensus_label": "BUY"}],
    )
    _write_csv(
        fmp_root / "latest" / "latest_fmp_earnings_surprises.csv",
        ["symbol", "sourced_date", "latest_eps_estimate"],
        [{"symbol": "CRM", "sourced_date": "2026-08-30", "latest_eps_estimate": "1.9"}],
    )

    history_root = tmp_path / "history" / "pit_observations"
    index_path = tmp_path / "history" / "pit_observation_index.csv"

    def _append_proxy(**kwargs):
        return append_pit_observations(
            observations=kwargs["observations"],
            provider=kwargs["provider"],
            snapshot_date=kwargs["snapshot_date"],
            run_id=kwargs["run_id"],
            history_root=history_root,
            index_path=index_path,
        )

    monkeypatch.setattr(rs, "_FMP_DIR", fmp_root)
    monkeypatch.setattr(rs, "append_pit_observations", _append_proxy)

    result = rs._append_pit_for_provider(
        provider="fmp",
        submitted_symbols=["CRM"],
        snapshot_date="2026-08-30",
        run_id="RUN-EST-004",
        retrieved_at_utc="2026-08-30T12:00:00+00:00",
    )

    assert result["pit_observations_written"] > 0
    rows = query_pit_observations(
        symbol="CRM",
        cutoff_retrieved_at_utc="2026-08-30T23:59:59+00:00",
        provider="FMP",
        history_root=history_root,
    )
    assert any(row["fiscal_period"] == "2027-01-31" for row in rows)
    assert any(row["forecast_horizon"] == "ANNUAL" for row in rows)
    assert any(row["metric"] == "eps_estimate_avg" for row in rows)
    assert any(row["metric"] == "revenue_estimate_avg" for row in rows)


def test_FMP_ESTIMATE_PIT_IDEMPOTENCE_TEST(tmp_path: Path) -> None:
    obs = {
        "symbol": "CRM",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-30",
        "retrieved_at_utc": "2026-08-30T12:00:00+00:00",
        "run_id": "RUN-EST-005",
        "metric": "eps_estimate_avg",
        "value": "2.0",
        "forecast_horizon": "ANNUAL",
        "fiscal_period": "2027-01-31",
        "source_provenance": "FMP_ANALYST_ESTIMATES_STABLE",
    }
    history_root = tmp_path / "history" / "pit_observations"
    index_path = tmp_path / "history" / "pit_observation_index.csv"

    first = append_pit_observations(
        observations=[obs],
        provider="fmp",
        snapshot_date="2026-08-30",
        run_id="RUN-EST-005",
        history_root=history_root,
        index_path=index_path,
    )
    second = append_pit_observations(
        observations=[obs],
        provider="fmp",
        snapshot_date="2026-08-30",
        run_id="RUN-EST-005",
        history_root=history_root,
        index_path=index_path,
    )

    assert first.written == 1
    assert second.written == 0
    assert second.skipped_duplicate == 1


def test_FMP_NO_ESTIMATE_COVERAGE_TEST() -> None:
    rows = [
        {
            "symbol": "CRM",
            "sourced_date": "2026-08-30",
            "fetch_status": "PROVIDER_NO_DATA",
            "period_date": "2027-01-31",
            "fiscal_period": "2027-01-31",
            "forecast_horizon": "ANNUAL",
            "request_period": "annual",
            "estimated_eps_avg": "",
            "estimated_revenue_avg": "",
            "analyst_count_eps": "",
            "analyst_count_revenue": "",
        }
    ]
    observations, attempted, succeeded = rs._to_pit_observations_from_fmp_estimate_rows(
        rows=rows,
        symbols=["CRM"],
        snapshot_date="2026-08-30",
        retrieved_at_utc="2026-08-30T10:00:00+00:00",
        run_id="RUN-EST-006",
    )
    assert attempted == 1
    assert succeeded == 0
    assert observations == []


def test_FMP_ESTIMATE_NO_LOOKAHEAD_TEST(tmp_path: Path) -> None:
    history_root = tmp_path / "history" / "pit_observations"
    index_path = tmp_path / "history" / "pit_observation_index.csv"

    older = {
        "symbol": "CRM",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-30",
        "retrieved_at_utc": "2026-08-30T12:00:00+00:00",
        "run_id": "RUN-EST-007A",
        "metric": "revenue_estimate_avg",
        "value": "100.0",
        "forecast_horizon": "ANNUAL",
        "fiscal_period": "2027-01-31",
        "source_provenance": "FMP_ANALYST_ESTIMATES_STABLE",
    }
    newer = dict(older)
    newer["snapshot_date"] = "2026-08-31"
    newer["retrieved_at_utc"] = "2026-08-31T12:00:00+00:00"
    newer["run_id"] = "RUN-EST-007B"
    newer["value"] = "120.0"

    append_pit_observations(
        observations=[older],
        provider="fmp",
        snapshot_date="2026-08-30",
        run_id="RUN-EST-007A",
        history_root=history_root,
        index_path=index_path,
    )
    append_pit_observations(
        observations=[newer],
        provider="fmp",
        snapshot_date="2026-08-31",
        run_id="RUN-EST-007B",
        history_root=history_root,
        index_path=index_path,
    )

    rows = query_pit_observations(
        symbol="CRM",
        cutoff_retrieved_at_utc="2026-08-30T23:59:59+00:00",
        provider="FMP",
        metric="revenue_estimate_avg",
        history_root=history_root,
    )
    assert len(rows) == 1
    assert rows[0]["value"] == "100.0"


def test_FMP_ANNUAL_ONLY_REQUEST_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _fake_get(url: str, api_key: str):
        calls.append(url)
        assert "period=annual" in url
        payload = [{
            "symbol": "CRM",
            "date": "2031-01-31",
            "epsAvg": 25.0,
            "epsHigh": 26.0,
            "epsLow": 24.0,
            "revenueAvg": 71000000000,
            "revenueHigh": 73000000000,
            "revenueLow": 70000000000,
            "numAnalystsEps": 8,
            "numAnalystsRevenue": 21,
        }]
        return payload, 200, None, {"retries_performed": 0, "rate_limit_events": 0}

    monkeypatch.setattr(fmp, "_fmp_get_with_retry_detailed", _fake_get)
    _, stats = fmp.fetch_fmp_analyst_estimates(
        ["CRM"],
        api_key="TEST",
        output_dir=tmp_path / "signals" / "fmp",
        delay=0.0,
        verbose=False,
        periods=["annual"],
    )
    assert stats["periods_requested"] == ["annual"]
    assert stats["network_requests_by_period"] == {"annual": 1}
    assert stats["with_data"] == 1
    assert len(calls) == 1


def test_FMP_DISABLED_QUARTER_NO_REQUEST_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _fake_get(url: str, api_key: str):
        calls.append(url)
        payload = [{"symbol": "MSFT", "date": "2031-06-30", "epsAvg": 20.0, "revenueAvg": 100.0}]
        return payload, 200, None, {"retries_performed": 0, "rate_limit_events": 0}

    monkeypatch.setattr(fmp, "_fmp_get_with_retry_detailed", _fake_get)
    _, stats = fmp.fetch_fmp_analyst_estimates(
        ["MSFT"],
        api_key="TEST",
        output_dir=tmp_path / "signals" / "fmp",
        delay=0.0,
        verbose=False,
        periods=["annual"],
    )
    assert all("period=quarter" not in url for url in calls)
    assert int(stats["network_requests_by_period"].get("annual") or 0) == 1
    assert int(stats["network_requests_by_period"].get("quarter") or 0) == 0


def test_FMP_PERIOD_CAPABILITY_REPORTING_TEST(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rs, "_fmp_api_key", lambda: "TEST")
    monkeypatch.setattr(rs, "_all_universe_symbols", lambda: ["CRM"])
    monkeypatch.setattr(
        rs,
        "is_fmp_daily_stale",
        lambda dataset, fmp_dir=None: dataset in {"analyst_estimates", "key_metrics", "grades_consensus"},
    )
    monkeypatch.setattr(rs, "fetch_fmp_daily_signals", lambda *args, **kwargs: (Path("a"), Path("b")))
    monkeypatch.setattr(
        rs,
        "fetch_fmp_analyst_estimates",
        lambda *args, **kwargs: (
            Path("latest.csv"),
            {
                "attempted": 1,
                "with_data": 1,
                "no_coverage": 0,
                "failed": 0,
                "periods_requested": ["annual"],
                "periods_available": ["annual"],
                "periods_plan_limited": [],
                "network_requests_by_period": {"annual": 1},
                "retries_performed": 0,
                "rate_limit_events": 0,
            },
        ),
    )

    triggered, metrics = rs._refresh_fmp(dry_run=False, verbose=False, mode="daily", collect_report=True)
    assert triggered is True
    assert metrics["estimate_periods_requested"] == ["annual"]
    assert metrics["estimate_periods_available"] == ["annual"]
    assert "quarter" in metrics["estimate_periods_plan_limited"]
    capability = metrics["estimate_period_capability"]
    assert capability.get("annual") == "AVAILABLE"
    assert capability.get("quarter") == "PLAN_LIMIT"


def test_FMP_ANNUAL_PIT_HORIZON_TEST() -> None:
    rows = [
        {
            "symbol": "CRM",
            "sourced_date": "2026-08-30",
            "fetch_status": "SUCCESS",
            "request_period": "annual",
            "period_date": "2030-01-31",
            "fiscal_period": "2030-01-31",
            "forecast_horizon": "ANNUAL",
            "estimated_eps_avg": "20.0",
        }
    ]
    observations, _, _ = rs._to_pit_observations_from_fmp_estimate_rows(
        rows=rows,
        symbols=["CRM"],
        snapshot_date="2026-08-30",
        retrieved_at_utc="2026-08-30T10:00:00+00:00",
        run_id="RUN-EST-008",
    )
    assert observations
    assert all(obs["forecast_horizon"] == "ANNUAL" for obs in observations)


def test_FMP_PERIOD_VS_RETRIEVAL_TIME_TEST() -> None:
    retrieved = "2026-08-30T10:00:00+00:00"
    rows = [
        {
            "symbol": "CRM",
            "sourced_date": "2026-08-30",
            "fetch_status": "SUCCESS",
            "request_period": "annual",
            "period_date": "2024-01-31",
            "fiscal_period": "2024-01-31",
            "forecast_horizon": "ANNUAL",
            "estimated_revenue_avg": "100.0",
        }
    ]
    observations, _, _ = rs._to_pit_observations_from_fmp_estimate_rows(
        rows=rows,
        symbols=["CRM"],
        snapshot_date="2026-08-30",
        retrieved_at_utc=retrieved,
        run_id="RUN-EST-009",
    )
    assert observations
    assert all(obs["retrieved_at_utc"] == retrieved for obs in observations)
    assert all(obs["fiscal_period"] == "2024-01-31" for obs in observations)
