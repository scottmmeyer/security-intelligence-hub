from __future__ import annotations

import copy
import csv
from pathlib import Path

from src.history.pit_observation_manager import (
    append_pit_observations,
    query_pit_observations,
)
from scripts.refresh_signals import _to_pit_observations_from_rows


def _paths(tmp_path: Path) -> tuple[Path, Path]:
    history_root = tmp_path / "history" / "pit_observations"
    index_path = tmp_path / "history" / "pit_observation_index.csv"
    return history_root, index_path


def _count_rows(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def test_pit_append_only_preserves_earlier_observations(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)

    first = {
        "symbol": "CRM",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-30",
        "retrieved_at_utc": "2026-08-30T10:00:00+00:00",
        "run_id": "RUN-001",
        "metric": "price_target",
        "value": "300.0",
        "forecast_horizon": "12M",
        "fiscal_period": "FY2027",
        "source_provenance": "YAHOO_FINANCE_SUPPLEMENTAL",
    }
    second = {
        "symbol": "CRM",
        "snapshot_date": "2026-08-31",
        "sourced_date": "2026-08-31",
        "retrieved_at_utc": "2026-08-31T10:00:00+00:00",
        "run_id": "RUN-002",
        "metric": "price_target",
        "value": "310.0",
        "forecast_horizon": "12M",
        "fiscal_period": "FY2027",
        "source_provenance": "YAHOO_FINANCE_SUPPLEMENTAL",
    }

    r1 = append_pit_observations(
        observations=[first],
        provider="yahoo",
        snapshot_date="2026-08-30",
        run_id="RUN-001",
        history_root=history_root,
        index_path=index_path,
    )
    r2 = append_pit_observations(
        observations=[second],
        provider="yahoo",
        snapshot_date="2026-08-31",
        run_id="RUN-002",
        history_root=history_root,
        index_path=index_path,
    )

    assert r1.written == 1
    assert r2.written == 1
    first_partition = history_root / "snapshot_date=2026-08-30" / "run_id=RUN-001" / "provider=YAHOO" / "observations.csv"
    second_partition = history_root / "snapshot_date=2026-08-31" / "run_id=RUN-002" / "provider=YAHOO" / "observations.csv"
    assert _count_rows(first_partition) == 1
    assert _count_rows(second_partition) == 1


def test_pit_idempotence_same_run_skips_duplicates(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)
    obs = {
        "symbol": "MSFT",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-30",
        "retrieved_at_utc": "2026-08-30T10:00:00+00:00",
        "run_id": "RUN-SAME",
        "metric": "abr",
        "value": "1.45",
        "forecast_horizon": "UNSPECIFIED",
        "fiscal_period": "UNSPECIFIED",
        "source_provenance": "ZACKS_QUOTE_FEED",
    }

    first = append_pit_observations(
        observations=[obs],
        provider="zacks",
        snapshot_date="2026-08-30",
        run_id="RUN-SAME",
        history_root=history_root,
        index_path=index_path,
    )
    second = append_pit_observations(
        observations=[obs],
        provider="zacks",
        snapshot_date="2026-08-30",
        run_id="RUN-SAME",
        history_root=history_root,
        index_path=index_path,
    )

    assert first.written == 1
    assert second.written == 0
    assert second.skipped_duplicate == 1


def test_pit_time_semantics_round_trip(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)
    obs = {
        "symbol": "NVDA",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-15",
        "retrieved_at_utc": "2026-08-30T15:45:00+00:00",
        "run_id": "RUN-TIME",
        "metric": "eps_growth_5yr",
        "value": "18.2",
        "forecast_horizon": "5Y",
        "fiscal_period": "UNSPECIFIED",
        "source_provenance": "YAHOO_FINANCE_SUPPLEMENTAL",
    }

    append_pit_observations(
        observations=[obs],
        provider="yahoo",
        snapshot_date="2026-08-30",
        run_id="RUN-TIME",
        history_root=history_root,
        index_path=index_path,
    )

    rows = query_pit_observations(
        symbol="NVDA",
        cutoff_retrieved_at_utc="2026-08-31T00:00:00+00:00",
        history_root=history_root,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["snapshot_date"] == "2026-08-30"
    assert row["sourced_date"] == "2026-08-15"
    assert row["retrieved_at_utc"] == "2026-08-30T15:45:00+00:00"


def test_pit_missing_source_date_kept_unavailable(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)
    obs = {
        "symbol": "CRM",
        "snapshot_date": "2026-08-30",
        "sourced_date": "",
        "retrieved_at_utc": "2026-08-30T12:00:00+00:00",
        "run_id": "RUN-NOSOURCE",
        "metric": "analyst_count",
        "value": "35",
        "forecast_horizon": "UNSPECIFIED",
        "fiscal_period": "UNSPECIFIED",
        "source_provenance": "YAHOO_FINANCE_SUPPLEMENTAL",
    }
    append_pit_observations(
        observations=[obs],
        provider="yahoo",
        snapshot_date="2026-08-30",
        run_id="RUN-NOSOURCE",
        history_root=history_root,
        index_path=index_path,
    )
    rows = query_pit_observations(
        symbol="CRM",
        cutoff_retrieved_at_utc="2026-08-31T00:00:00+00:00",
        history_root=history_root,
    )
    assert len(rows) == 1
    assert rows[0]["sourced_date"] == "UNAVAILABLE"


def test_pit_no_lookahead_cutoff_filter(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)
    older = {
        "symbol": "CRM",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-30",
        "retrieved_at_utc": "2026-08-30T10:00:00+00:00",
        "run_id": "RUN-A",
        "metric": "price_target",
        "value": "300",
        "forecast_horizon": "12M",
        "fiscal_period": "FY2027",
        "source_provenance": "YAHOO_FINANCE_SUPPLEMENTAL",
    }
    newer = dict(older)
    newer["retrieved_at_utc"] = "2026-08-31T10:00:00+00:00"
    newer["snapshot_date"] = "2026-08-31"
    newer["run_id"] = "RUN-B"
    newer["value"] = "320"

    append_pit_observations(
        observations=[older],
        provider="yahoo",
        snapshot_date="2026-08-30",
        run_id="RUN-A",
        history_root=history_root,
        index_path=index_path,
    )
    append_pit_observations(
        observations=[newer],
        provider="yahoo",
        snapshot_date="2026-08-31",
        run_id="RUN-B",
        history_root=history_root,
        index_path=index_path,
    )

    rows = query_pit_observations(
        symbol="CRM",
        cutoff_retrieved_at_utc="2026-08-30T23:59:59+00:00",
        history_root=history_root,
    )
    assert len(rows) == 1
    assert rows[0]["value"] == "300"


def test_pit_forecast_period_separation(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)
    base = {
        "symbol": "NVDA",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-30",
        "retrieved_at_utc": "2026-08-30T10:00:00+00:00",
        "run_id": "RUN-FISCAL",
        "metric": "eps_estimate",
        "value": "5.10",
        "source_provenance": "FMP_STABLE_API",
    }
    fy27 = dict(base)
    fy27["forecast_horizon"] = "FY+1"
    fy27["fiscal_period"] = "FY2027"
    fy28 = dict(base)
    fy28["forecast_horizon"] = "FY+2"
    fy28["fiscal_period"] = "FY2028"
    fy28["value"] = "5.80"

    result = append_pit_observations(
        observations=[fy27, fy28],
        provider="fmp",
        snapshot_date="2026-08-30",
        run_id="RUN-FISCAL",
        history_root=history_root,
        index_path=index_path,
    )
    assert result.written == 2

    latest = query_pit_observations(
        symbol="NVDA",
        cutoff_retrieved_at_utc="2026-09-01T00:00:00+00:00",
        provider="fmp",
        metric="eps_estimate",
        latest_only=False,
        history_root=history_root,
    )
    assert len(latest) == 2
    assert {row["fiscal_period"] for row in latest} == {"FY2027", "FY2028"}


def test_pit_provider_coexistence(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)
    common = {
        "symbol": "CRM",
        "snapshot_date": "2026-08-30",
        "sourced_date": "2026-08-30",
        "retrieved_at_utc": "2026-08-30T10:00:00+00:00",
        "run_id": "RUN-PROVIDER",
        "metric": "price_target",
        "forecast_horizon": "12M",
        "fiscal_period": "UNSPECIFIED",
    }

    yahoo_obs = dict(common)
    yahoo_obs["value"] = "320"
    yahoo_obs["source_provenance"] = "YAHOO_FINANCE_SUPPLEMENTAL"
    fmp_obs = dict(common)
    fmp_obs["value"] = "315"
    fmp_obs["source_provenance"] = "FMP_STABLE_API"

    append_pit_observations(
        observations=[yahoo_obs],
        provider="yahoo",
        snapshot_date="2026-08-30",
        run_id="RUN-PROVIDER",
        history_root=history_root,
        index_path=index_path,
    )
    append_pit_observations(
        observations=[fmp_obs],
        provider="fmp",
        snapshot_date="2026-08-30",
        run_id="RUN-PROVIDER",
        history_root=history_root,
        index_path=index_path,
    )

    rows = query_pit_observations(
        symbol="CRM",
        cutoff_retrieved_at_utc="2026-08-31T00:00:00+00:00",
        metric="price_target",
        history_root=history_root,
    )
    assert len(rows) == 2
    assert {row["provider"] for row in rows} == {"YAHOO", "FMP"}


def test_pit_refresh_integration_mapping(tmp_path: Path) -> None:
    history_root, index_path = _paths(tmp_path)
    source_rows = {
        "CRM": {
            "symbol": "CRM",
            "abr": "1.3",
            "price_target": "320.5",
            "analyst_count": "42",
            "eps_growth_5yr": "12.4",
            "sourced_date": "2026-08-30",
        }
    }
    source_copy = copy.deepcopy(source_rows)

    observations, attempted, succeeded = _to_pit_observations_from_rows(
        provider="yahoo",
        rows_by_symbol=source_rows,
        symbols=["CRM", "MSFT"],
        snapshot_date="2026-08-30",
        retrieved_at_utc="2026-08-30T13:00:00+00:00",
        run_id="RUN-REFRESH",
        source_provenance="YAHOO_FINANCE_SUPPLEMENTAL",
        source_endpoint="yfinance.Ticker.info + get_growth_estimates",
    )

    assert attempted == 2
    assert succeeded == 1
    result = append_pit_observations(
        observations=observations,
        provider="yahoo",
        snapshot_date="2026-08-30",
        run_id="RUN-REFRESH",
        history_root=history_root,
        index_path=index_path,
    )

    assert result.written == 4
    assert result.skipped_duplicate == 0
    assert source_rows == source_copy
