from __future__ import annotations

import csv
import sys
import types
from datetime import date

from src.scoring import fetch_security_metadata as module


def _read_rows(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _install_fake_yfinance(monkeypatch, info_factory):
    class _FakeTicker:
        def __init__(self, symbol: str):
            self._symbol = symbol

        @property
        def info(self):
            return info_factory(self._symbol)

    fake_mod = types.SimpleNamespace(Ticker=_FakeTicker)
    monkeypatch.setitem(sys.modules, "yfinance", fake_mod)


def test_successful_metadata_response_persists_success_status(tmp_path, monkeypatch):
    def _info(_symbol: str):
        return {
            "sector": "Technology",
            "industry": "Semiconductors",
            "country": "United States",
            "quoteType": "EQUITY",
        }

    _install_fake_yfinance(monkeypatch, _info)

    output_path, stats = module.fetch_security_metadata_for_symbols(
        ["NVDA"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        max_retries=1,
        retry_backoff_seconds=0,
        verbose=False,
        collect_stats=True,
    )

    rows = _read_rows(output_path)
    assert rows[0]["metadata_status"] == module.STATUS_SUCCESS
    assert rows[0]["country"] == "United States"
    assert rows[0]["failure_type"] == ""
    assert rows[0]["attempt_count"] == "1"
    assert stats["success"] == 1


def test_valid_provider_no_data_persists_provider_no_data_status(tmp_path, monkeypatch):
    _install_fake_yfinance(monkeypatch, lambda _symbol: {})

    output_path, stats = module.fetch_security_metadata_for_symbols(
        ["AAA"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        max_retries=1,
        retry_backoff_seconds=0,
        verbose=False,
        collect_stats=True,
    )

    rows = _read_rows(output_path)
    assert rows[0]["metadata_status"] == module.STATUS_PROVIDER_NO_DATA
    assert rows[0]["failure_type"] == ""
    assert rows[0]["failure_reason"] == ""
    assert stats["provider_no_data"] == 1


def test_retryable_timeout_failure_not_silently_persisted_as_no_data(tmp_path, monkeypatch):
    def _info(_symbol: str):
        raise TimeoutError("request timed out")

    _install_fake_yfinance(monkeypatch, _info)

    output_path, stats = module.fetch_security_metadata_for_symbols(
        ["BBB"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        max_retries=2,
        retry_backoff_seconds=0,
        verbose=False,
        collect_stats=True,
    )

    rows = _read_rows(output_path)
    row = rows[0]
    assert row["metadata_status"] == module.STATUS_RETRYABLE_FAILURE
    assert row["metadata_status"] != module.STATUS_PROVIDER_NO_DATA
    assert row["failure_type"] == "TIMEOUT"
    assert row["attempt_count"] == "2"
    assert stats["retryable_failure"] == 1


def test_nonretryable_failure_persists_nonretryable_status(tmp_path, monkeypatch):
    def _info(_symbol: str):
        raise ValueError("bad payload schema")

    _install_fake_yfinance(monkeypatch, _info)

    output_path, stats = module.fetch_security_metadata_for_symbols(
        ["CCC"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        max_retries=3,
        retry_backoff_seconds=0,
        verbose=False,
        collect_stats=True,
    )

    row = _read_rows(output_path)[0]
    assert row["metadata_status"] == module.STATUS_NONRETRYABLE_FAILURE
    assert row["failure_type"] == "VALUEERROR"
    assert row["attempt_count"] == "1"
    assert stats["nonretryable_failure"] == 1


def test_preserves_existing_successful_row_on_technical_failure(tmp_path, monkeypatch):
    today = date.today().isoformat()
    latest_path = tmp_path / "latest_security_metadata.csv"
    with latest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=module._OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "DDD",
                "sector": "Technology",
                "industry": "Semiconductors",
                "country": "United States",
                "quote_type": "EQUITY",
                "sourced_date": today,
                "metadata_status": module.STATUS_SUCCESS,
                "failure_type": "",
                "failure_reason": "",
                "attempt_count": "1",
                "last_attempt_utc": "",
            }
        )

    def _info(_symbol: str):
        raise OSError("connection reset by peer")

    _install_fake_yfinance(monkeypatch, _info)

    output_path, stats = module.fetch_security_metadata_for_symbols(
        ["DDD"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        max_retries=1,
        retry_backoff_seconds=0,
        verbose=False,
        collect_stats=True,
    )

    row = _read_rows(output_path)[0]
    assert row["metadata_status"] == module.STATUS_RETRYABLE_FAILURE
    assert row["sector"] == "Technology"
    assert row["country"] == "United States"
    assert stats["preserved_existing_rows"] == 1


def test_retry_failed_only_selects_failed_and_legacy_empty_rows(tmp_path, monkeypatch):
    today = date.today().isoformat()
    latest_path = tmp_path / "latest_security_metadata.csv"
    with latest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=module._OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "OK1",
                "sector": "Industrials",
                "industry": "Electrical Equipment",
                "country": "United States",
                "quote_type": "EQUITY",
                "sourced_date": today,
                "metadata_status": module.STATUS_SUCCESS,
                "failure_type": "",
                "failure_reason": "",
                "attempt_count": "1",
                "last_attempt_utc": "",
            }
        )
        writer.writerow(
            {
                "symbol": "FAIL1",
                "sector": "",
                "industry": "",
                "country": "",
                "quote_type": "",
                "sourced_date": today,
                "metadata_status": module.STATUS_RETRYABLE_FAILURE,
                "failure_type": "TIMEOUT",
                "failure_reason": "TimeoutError",
                "attempt_count": "3",
                "last_attempt_utc": "",
            }
        )
        # Legacy empty row with no metadata_status should be retried.
        writer.writerow(
            {
                "symbol": "LEGACY1",
                "sector": "",
                "industry": "",
                "country": "",
                "quote_type": "",
                "sourced_date": today,
                "metadata_status": "",
                "failure_type": "",
                "failure_reason": "",
                "attempt_count": "",
                "last_attempt_utc": "",
            }
        )

    calls = []

    def _fake_fetch_with_retry(symbol: str, *, max_retries: int, retry_backoff_seconds: float):
        calls.append(symbol)
        return (
            {
                "sector": "Technology",
                "industry": "Software",
                "country": "United States",
                "quote_type": "EQUITY",
            },
            module.STATUS_SUCCESS,
            "",
            "",
            1,
        )

    monkeypatch.setattr(module, "_fetch_security_metadata_with_retry", _fake_fetch_with_retry)

    output_path, stats = module.fetch_security_metadata_for_symbols(
        ["OK1", "FAIL1", "LEGACY1", "NEW1"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        retry_failed_only=True,
        verbose=False,
        collect_stats=True,
    )

    assert calls == ["FAIL1", "LEGACY1", "NEW1"]
    assert stats["attempted"] == 3
    assert stats["retried_failed_checkpoint"] == 3

    rows = {row["symbol"]: row for row in _read_rows(output_path)}
    assert rows["OK1"]["metadata_status"] == module.STATUS_SUCCESS
    assert rows["FAIL1"]["metadata_status"] == module.STATUS_SUCCESS
    assert rows["LEGACY1"]["metadata_status"] == module.STATUS_SUCCESS
    assert rows["NEW1"]["metadata_status"] == module.STATUS_SUCCESS


def test_existing_successful_row_updates_normally_on_new_success(tmp_path, monkeypatch):
    today = date.today().isoformat()
    latest_path = tmp_path / "latest_security_metadata.csv"
    with latest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=module._OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "UPD1",
                "sector": "Old Sector",
                "industry": "Old Industry",
                "country": "Old Country",
                "quote_type": "EQUITY",
                "sourced_date": today,
                "metadata_status": module.STATUS_SUCCESS,
                "failure_type": "",
                "failure_reason": "",
                "attempt_count": "1",
                "last_attempt_utc": "",
            }
        )

    def _info(_symbol: str):
        return {
            "sector": "Technology",
            "industry": "Semiconductors",
            "country": "United States",
            "quoteType": "EQUITY",
        }

    _install_fake_yfinance(monkeypatch, _info)

    output_path, _stats = module.fetch_security_metadata_for_symbols(
        ["UPD1"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        max_retries=1,
        retry_backoff_seconds=0,
        verbose=False,
        collect_stats=True,
    )

    row = _read_rows(output_path)[0]
    assert row["metadata_status"] == module.STATUS_SUCCESS
    assert row["sector"] == "Technology"
    assert row["industry"] == "Semiconductors"
    assert row["country"] == "United States"


def test_legacy_empty_row_retry_exhaustion_records_retryable_failure(tmp_path, monkeypatch):
    today = date.today().isoformat()
    latest_path = tmp_path / "latest_security_metadata.csv"
    with latest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=module._OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "LEGFAIL",
                "sector": "",
                "industry": "",
                "country": "",
                "quote_type": "",
                "sourced_date": today,
                "metadata_status": "",
                "failure_type": "",
                "failure_reason": "",
                "attempt_count": "",
                "last_attempt_utc": "",
            }
        )

    def _info(_symbol: str):
        raise TimeoutError("request timed out")

    _install_fake_yfinance(monkeypatch, _info)

    output_path, stats = module.fetch_security_metadata_for_symbols(
        ["LEGFAIL"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        retry_failed_only=True,
        max_retries=2,
        retry_backoff_seconds=0,
        verbose=False,
        collect_stats=True,
    )

    row = _read_rows(output_path)[0]
    assert row["metadata_status"] == module.STATUS_RETRYABLE_FAILURE
    assert row["metadata_status"] != module.STATUS_PROVIDER_NO_DATA
    assert row["failure_type"] == "TIMEOUT"
    assert stats["retryable_failure"] == 1


def test_smart_refresh_with_legacy_rows_does_not_refetch_all_symbols(tmp_path, monkeypatch):
    today = date.today().isoformat()
    latest_path = tmp_path / "latest_security_metadata.csv"
    with latest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=module._OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "LEGGOOD",
                "sector": "Industrials",
                "industry": "Machinery",
                "country": "United States",
                "quote_type": "EQUITY",
                "sourced_date": today,
                "metadata_status": "",
                "failure_type": "",
                "failure_reason": "",
                "attempt_count": "",
                "last_attempt_utc": "",
            }
        )
        writer.writerow(
            {
                "symbol": "LEGEMPTY",
                "sector": "",
                "industry": "",
                "country": "",
                "quote_type": "",
                "sourced_date": today,
                "metadata_status": "",
                "failure_type": "",
                "failure_reason": "",
                "attempt_count": "",
                "last_attempt_utc": "",
            }
        )

    calls = []

    def _fake_fetch_with_retry(symbol: str, *, max_retries: int, retry_backoff_seconds: float):
        calls.append(symbol)
        return (
            {
                "sector": "Technology",
                "industry": "Software",
                "country": "United States",
                "quote_type": "EQUITY",
            },
            module.STATUS_SUCCESS,
            "",
            "",
            1,
        )

    monkeypatch.setattr(module, "_fetch_security_metadata_with_retry", _fake_fetch_with_retry)

    _path, stats = module.fetch_security_metadata_for_symbols(
        ["LEGGOOD", "LEGEMPTY", "MISSING1"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        smart_refresh=True,
        verbose=False,
        collect_stats=True,
    )

    assert calls == ["MISSING1"]
    assert stats["attempted"] == 1
