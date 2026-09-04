from __future__ import annotations

from scripts.run_outcome_ui import _macro_market_confirmation_payload


def test_market_confirmation_includes_explicit_freshness_and_coverage_fields() -> None:
    payload = _macro_market_confirmation_payload()

    assert payload.get("availability") in {"AVAILABLE", "UNAVAILABLE"}
    assert payload.get("as_of") is not None
    assert payload.get("freshness") is not None
    assert payload.get("summary_recency") is not None

    evidence = payload.get("evidence_freshness") or {}
    assert evidence.get("status") in {"CURRENT", "MIXED", "STALE", "UNAVAILABLE"}
    assert "oldest_effective_date" in evidence
    assert "newest_effective_date" in evidence
    assert isinstance(evidence.get("component_effective_dates"), dict)

    coverage = payload.get("coverage") or {}
    assert coverage.get("state") in {
        "FULLY_EVALUATED",
        "PARTIALLY_EVALUATED",
        "NOT_EVALUATED",
        "UNAVAILABLE",
    }
    assert "evaluable_weight_pct" in coverage


def test_market_confirmation_effective_dates_do_not_exceed_as_of() -> None:
    payload = _macro_market_confirmation_payload()
    as_of = str(payload.get("as_of") or "")[:10]
    assert as_of

    evidence = payload.get("evidence_freshness") or {}
    comp = evidence.get("component_effective_dates") or {}
    for _, value in comp.items():
        if value:
            assert str(value)[:10] <= as_of

    oldest = evidence.get("oldest_effective_date")
    newest = evidence.get("newest_effective_date")
    if oldest:
        assert str(oldest)[:10] <= as_of
    if newest:
        assert str(newest)[:10] <= as_of


def test_market_confirmation_coverage_matches_existing_state_field() -> None:
    payload = _macro_market_confirmation_payload()
    coverage = payload.get("coverage") or {}
    assert coverage.get("state") == payload.get("portfolio_momentum_condition")
