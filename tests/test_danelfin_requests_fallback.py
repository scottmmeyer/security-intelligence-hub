from __future__ import annotations

from datetime import date

import requests

from src.scoring import fetch_danelfin_scores as danelfin


class _Resp:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_http_403_classifies_blocked(monkeypatch) -> None:
    monkeypatch.setattr(danelfin.requests, "get", lambda *args, **kwargs: _Resp(403, "forbidden"))
    result = danelfin.fetch_danelfin_score_detailed("NVDA")
    assert result.status == "BLOCKED_403_OR_CHALLENGE"


def test_challenge_html_classifies_blocked(monkeypatch) -> None:
    monkeypatch.setattr(
        danelfin.requests,
        "get",
        lambda *args, **kwargs: _Resp(200, "<html><title>Just a moment</title>Checking your browser</html>"),
    )
    result = danelfin.fetch_danelfin_score_detailed("NVDA")
    assert result.status == "BLOCKED_403_OR_CHALLENGE"


def test_success_path_does_not_request_browser_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        danelfin.requests,
        "get",
        lambda *args, **kwargs: _Resp(200, '<div aria-label="8 out of 10"></div>'),
    )

    called: list[list[str]] = []

    def _fallback(symbols: list[str], *, verbose: bool) -> dict[str, object]:
        called.append(list(symbols))
        return {"browser_fallback_requested": 0}

    monkeypatch.setattr(danelfin, "_request_browser_fallback_for_blocked_symbols", _fallback)

    _, stats = danelfin.fetch_danelfin_scores_for_symbols(
        ["NVDA"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        verbose=False,
        collect_stats=True,
    )

    assert stats["requests_success"] == 1
    assert stats["requests_blocked"] == 0
    assert called == [[]]


def test_no_primary_fields_does_not_request_browser_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(danelfin.requests, "get", lambda *args, **kwargs: _Resp(200, "<html>plain page</html>"))

    called: list[list[str]] = []

    def _fallback(symbols: list[str], *, verbose: bool) -> dict[str, object]:
        called.append(list(symbols))
        return {"browser_fallback_requested": 0}

    monkeypatch.setattr(danelfin, "_request_browser_fallback_for_blocked_symbols", _fallback)

    _, stats = danelfin.fetch_danelfin_scores_for_symbols(
        ["NVDA"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        verbose=False,
        collect_stats=True,
    )

    assert stats["requests_no_primary_fields"] == 1
    assert stats["requests_blocked"] == 0
    assert called == [[]]


def test_network_error_does_not_request_browser_fallback(tmp_path, monkeypatch) -> None:
    def _raise_timeout(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(danelfin.requests, "get", _raise_timeout)

    called: list[list[str]] = []

    def _fallback(symbols: list[str], *, verbose: bool) -> dict[str, object]:
        called.append(list(symbols))
        return {"browser_fallback_requested": 0}

    monkeypatch.setattr(danelfin, "_request_browser_fallback_for_blocked_symbols", _fallback)

    _, stats = danelfin.fetch_danelfin_scores_for_symbols(
        ["NVDA"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        verbose=False,
        collect_stats=True,
    )

    assert stats["requests_network_error"] == 1
    assert stats["requests_blocked"] == 0
    assert called == [[]]


def test_blocked_request_invokes_single_production_prepare(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(danelfin.requests, "get", lambda *args, **kwargs: _Resp(403, "forbidden"))

    fallback_calls: list[list[str]] = []

    def _fallback(symbols: list[str], *, verbose: bool) -> dict[str, object]:
        fallback_calls.append(list(symbols))
        today = date.today().isoformat()
        rows = [{"symbol": sym, "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": today} for sym in symbols]
        danelfin._write_csv(tmp_path / f"{today}_danelfin.csv", rows)
        danelfin._write_csv(tmp_path / "latest_danelfin.csv", rows)
        return {
            "browser_fallback_requested": 1,
            "browser_jobs_prepared": 1,
            "browser_jobs_claimed": 1,
            "browser_jobs_completed": 1,
            "browser_jobs_failed": 0,
            "browser_primary_fields_success": 1,
        }

    monkeypatch.setattr(danelfin, "_request_browser_fallback_for_blocked_symbols", _fallback)

    _, stats = danelfin.fetch_danelfin_scores_for_symbols(
        ["NVDA"],
        output_dir=tmp_path,
        delay_min=0,
        delay_max=0,
        verbose=False,
        collect_stats=True,
    )

    assert fallback_calls == [["NVDA"]]
    assert stats["requests_blocked"] == 1
    assert stats["browser_fallback_requested"] == 1
    assert stats["browser_jobs_prepared"] == 1
    assert stats["browser_jobs_claimed"] == 1
    assert stats["browser_jobs_completed"] == 1


def test_provider_ordering_unchanged() -> None:
    from scripts import refresh_signals as rs

    assert rs._ALL_PROVIDERS == ("zacks", "danelfin", "yahoo", "fmp")


# =========================================================================
# Regression tests for acquisition observability fix (explicit zero semantics)
# =========================================================================


def test_observability_explicit_zero_requests_attempted_preserved(tmp_path, monkeypatch) -> None:
    """Test A: requests_attempted=0 is preserved, not overwritten by attempted_count fallback."""
    from scripts import refresh_signals as rs

    # Simulate checkpoint-resumed fetch stats: 0 actual HTTP requests despite symbols submitted.
    fetch_stats = {
        "requested": 63,
        "attempted": 63,  # symbols submitted
        "requests_attempted": 0,  # NO HTTP REQUESTS (0, not missing)
        "requests_success": 0,
        "requests_blocked": 0,
        "requests_no_primary_fields": 0,
        "requests_network_error": 0,
        "skipped_checkpoint": 63,  # all checkpointed
        "skipped_already_covered": 0,
        "retried_failed_checkpoint": 0,
        "browser_fallback_requested": 0,
        "browser_jobs_prepared": 0,
        "browser_jobs_claimed": 0,
        "browser_jobs_completed": 0,
        "browser_jobs_failed": 0,
        "browser_primary_fields_success": 0,
    }

    metrics = rs._compute_provider_metrics(
        provider="danelfin",
        mode="portfolio_signals",
        submitted_symbols=["SYM1"] * 63,  # 63 submitted
        coverage_before={},
        coverage_after={},
        runtime_sec=0.1,
        fetch_stats=fetch_stats,
    )

    # Key assertion: requests_attempted must remain 0, not become 63
    assert metrics["requests_attempted"] == 0, f"Expected 0, got {metrics['requests_attempted']}"
    assert metrics["requested_count"] == 63
    assert metrics["attempted_count"] == 63


def test_observability_explicit_zero_requests_blocked_preserved(tmp_path, monkeypatch) -> None:
    """Test B: requests_blocked=0 remains 0 when no blocks occur."""
    from scripts import refresh_signals as rs

    fetch_stats = {
        "requested": 0,
        "attempted": 0,
        "requests_attempted": 0,
        "requests_success": 0,
        "requests_blocked": 0,  # Explicit zero
        "requests_no_primary_fields": 0,
        "requests_network_error": 0,
        "browser_fallback_requested": 0,
        "skipped_checkpoint": 100,
        "skipped_already_covered": 0,
        "retried_failed_checkpoint": 0,
        "browser_jobs_prepared": 0,
        "browser_jobs_claimed": 0,
        "browser_jobs_completed": 0,
        "browser_jobs_failed": 0,
        "browser_primary_fields_success": 0,
    }

    metrics = rs._compute_provider_metrics(
        provider="danelfin",
        mode="skip_compliant",
        submitted_symbols=[],
        coverage_before={},
        coverage_after={},
        runtime_sec=0.1,
        fetch_stats=fetch_stats,
    )

    assert metrics["requests_blocked"] == 0, f"Expected 0, got {metrics['requests_blocked']}"
    assert metrics["browser_fallback_requested"] == 0


def test_observability_missing_metric_uses_compatibility_fallback(tmp_path, monkeypatch) -> None:
    """Test D: Missing acquisition metrics still use compatibility fallback."""
    from scripts import refresh_signals as rs

    # Old provider code might not include requests_attempted in fetch_stats
    fetch_stats_missing = {
        # "requests_attempted": key missing intentionally
        "requested": 50,
        "attempted": 50,
        "requests_success": 25,
        "requests_blocked": 5,
        "requests_no_primary_fields": 5,
        "requests_network_error": 5,
        "skipped_checkpoint": 10,
        "skipped_already_covered": 10,
        "retried_failed_checkpoint": 0,
        "browser_fallback_requested": 0,
        "browser_jobs_prepared": 0,
        "browser_jobs_claimed": 0,
        "browser_jobs_completed": 0,
        "browser_jobs_failed": 0,
        "browser_primary_fields_success": 0,
    }

    metrics = rs._compute_provider_metrics(
        provider="danelfin",
        mode="coverage_repair",
        submitted_symbols=["SYM1"] * 50,
        coverage_before={},
        coverage_after={},
        runtime_sec=0.1,
        fetch_stats=fetch_stats_missing,
    )

    # When requests_attempted is missing, should fall back to attempted_count
    assert metrics["requests_attempted"] == 50, f"Expected fallback to 50, got {metrics['requests_attempted']}"


def test_observability_limited_nvda_fallback_metrics_truthful(tmp_path, monkeypatch) -> None:
    """Test F: Limited fallback metrics remain truthful for 403 cases."""
    from scripts import refresh_signals as rs

    # Known single-symbol production fallback: NVDA with 403 -> fallback prepared/claimed.
    fetch_stats_nvda_fallback = {
        "requested": 1,
        "attempted": 1,
        "requests_attempted": 1,  # One HTTP request attempted
        "requests_success": 0,
        "requests_blocked": 1,  # Blocked by 403
        "requests_no_primary_fields": 0,
        "requests_network_error": 0,
        "skipped_checkpoint": 0,
        "skipped_already_covered": 0,
        "retried_failed_checkpoint": 0,
        "browser_fallback_requested": 1,  # Fallback requested
        "browser_jobs_prepared": 1,  # Job prepared
        "browser_jobs_claimed": 1,  # Job claimed
        "browser_jobs_completed": 1,  # Job completed
        "browser_jobs_failed": 0,
        "browser_primary_fields_success": 1,  # Success from fallback
    }

    metrics = rs._compute_provider_metrics(
        provider="danelfin",
        mode="research_refresh",
        submitted_symbols=["NVDA"],
        coverage_before={},
        coverage_after={},
        runtime_sec=0.5,
        fetch_stats=fetch_stats_nvda_fallback,
    )

    assert metrics["requests_attempted"] == 1
    assert metrics["requests_blocked"] == 1
    assert metrics["browser_fallback_requested"] == 1
    assert metrics["browser_jobs_prepared"] == 1
    assert metrics["browser_jobs_claimed"] == 1
    assert metrics["browser_primary_fields_success"] == 1


def test_observability_checkpoint_resume_no_fake_requests(tmp_path, monkeypatch) -> None:
    """Test E: Checkpoint-resumed run doesn't report fake HTTP request attempts."""
    from scripts import refresh_signals as rs

    # All 63 symbols from checkpoint, zero HTTP requests made
    fetch_stats_checkpoint = {
        "requested": 63,  # submitted from checkpoint
        "attempted": 63,  # submitted count
        "requests_attempted": 0,  # NO HTTP REQUESTS
        "requests_success": 0,
        "requests_blocked": 0,
        "requests_no_primary_fields": 0,
        "requests_network_error": 0,
        "skipped_checkpoint": 63,  # all were checkpointed
        "skipped_already_covered": 0,
        "retried_failed_checkpoint": 0,
        "browser_fallback_requested": 0,  # No fallback needed
        "browser_jobs_prepared": 0,
        "browser_jobs_claimed": 0,
        "browser_jobs_completed": 0,
        "browser_jobs_failed": 0,
        "browser_primary_fields_success": 0,
    }

    metrics = rs._compute_provider_metrics(
        provider="danelfin",
        mode="portfolio_signals",
        submitted_symbols=["SYM1"] * 63,
        coverage_before={},
        coverage_after={},
        runtime_sec=0.4,
        fetch_stats=fetch_stats_checkpoint,
    )

    # Assertions: all must be 0, not inflated by fallback
    assert metrics["requests_attempted"] == 0, "requests_attempted must not be inflated"
    assert metrics["requests_success"] == 0
    assert metrics["requests_blocked"] == 0
    assert metrics["browser_fallback_requested"] == 0
    assert metrics["browser_jobs_prepared"] == 0
    assert metrics["attempted_count"] == 63, "attempted_count can differ from requests_attempted"
