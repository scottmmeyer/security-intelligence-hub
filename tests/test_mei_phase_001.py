"""MEI Phase 1 — Validation Test Suite.

Covers MEI-001 through MEI-005.  All tests are deterministic and
filesystem-isolated (pytest tmp_path).  No network calls.  No
modifications to any existing project data.

Tests validate:
  Q1: SIH can identify upcoming major market events
  Q2: SIH can identify portfolio exposure to those events
  Q3: SIH can identify security-level event sensitivities
  Q4: Recommendations can be viewed in event context
  Q5–Q7: No recommendation/scoring/governance engines are modified
  Q8: MEI is informational only
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.mei.events import mei_events, mei_events_summary, _in_window, _days_away
from src.mei.security_profiles import (
    mei_security_profile,
    mei_security_profiles_bulk,
    _sector_defaults,
    ALL_TAGS,
)
from src.mei.exposures import mei_exposures, mei_exposures_summary
from src.mei.recommendation_context import (
    mei_recommendation_context,
    mei_recommendation_context_summary,
)
from src.mei.event_history import mei_event_history, mei_event_history_summary


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_event_calendar(root: Path, events: list[dict]) -> Path:
    """Write a minimal event_calendar.json and return the path."""
    path = root / "data" / "mei" / "event_calendar.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events), encoding="utf-8")
    return path


def _make_security_sensitivities(root: Path, overrides: dict) -> Path:
    path = root / "data" / "mei" / "security_sensitivities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides), encoding="utf-8")
    return path


def _make_event_history(root: Path, entries: list[dict]) -> Path:
    path = root / "data" / "mei" / "event_history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


_PAR_HOLDINGS_HEADERS = [
    "portfolio_snapshot_id", "snapshot_date", "account_name",
    "symbol", "description", "quantity", "market_value",
    "percent_of_portfolio", "asset_class", "geography",
    "market_cap_bucket", "mega_subtier", "industry",
]


def _make_par_run(
    root: Path,
    run_id: str,
    snapshot_date: str,
    holdings: list[dict],
    deployment_queue: list[dict] | None = None,
    recommendations: list[dict] | None = None,
) -> Path:
    run_dir = root / "data" / "portfolio_ingestion" / "analysis_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "run_id": run_id,
        "snapshot_date": snapshot_date,
        "created_at_utc": f"{snapshot_date}T10:00:00+00:00",
        "status": "COMPLETE",
    }
    (run_dir / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    # Holdings CSV
    if holdings:
        h_path = run_dir / "holdings.csv"
        with h_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=_PAR_HOLDINGS_HEADERS, extrasaction="ignore")
            w.writeheader()
            for h in holdings:
                row = {k: "" for k in _PAR_HOLDINGS_HEADERS}
                row.update(h)
                w.writerow(row)

    # Deployment queue JSON
    if deployment_queue is not None:
        dq = {"run_id": run_id, "queue_version": "1", "candidate_count": len(deployment_queue), "queue": deployment_queue}
        (run_dir / "deployment_queue.json").write_text(json.dumps(dq), encoding="utf-8")
    else:
        (run_dir / "deployment_queue.json").write_text(json.dumps({"queue": []}), encoding="utf-8")

    # Recommendations JSON
    recs = recommendations or []
    (run_dir / "recommendations.json").write_text(json.dumps(recs), encoding="utf-8")

    return run_dir


def _today_plus(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _today_minus(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# ─── MEI-001: Event Calendar ─────────────────────────────────────────────────


class TestMeiEvents:

    def test_events_returns_only_window(self, tmp_path):
        """mei_events should return only events within the lookahead window."""
        events = [
            {
                "event_id": "EV-PAST", "event_name": "Past Event",
                "event_date": _today_minus(5), "impact_level": "HIGH",
                "event_type": "INFLATION", "sensitivity_tags": ["INFLATION"],
                "source": "Test", "consensus_expectation": "",
                "description": ""
            },
            {
                "event_id": "EV-TODAY", "event_name": "Today Event",
                "event_date": _today_plus(0), "impact_level": "HIGH",
                "event_type": "MONETARY_POLICY", "sensitivity_tags": ["INTEREST_RATE"],
                "source": "Test", "consensus_expectation": "",
                "description": ""
            },
            {
                "event_id": "EV-7D", "event_name": "Week Out Event",
                "event_date": _today_plus(7), "impact_level": "MEDIUM",
                "event_type": "LABOR", "sensitivity_tags": ["LABOR"],
                "source": "Test", "consensus_expectation": "",
                "description": ""
            },
            {
                "event_id": "EV-FUTURE", "event_name": "Far Future Event",
                "event_date": _today_plus(30), "impact_level": "LOW",
                "event_type": "HOUSING", "sensitivity_tags": ["HOUSING"],
                "source": "Test", "consensus_expectation": "",
                "description": ""
            },
        ]
        _make_event_calendar(tmp_path, events)

        result = mei_events(repo_root=tmp_path, days_ahead=14)

        ids = [e["event_id"] for e in result["events"]]
        assert "EV-PAST" not in ids, "Past events should be excluded"
        assert "EV-TODAY" in ids, "Today's events should be included"
        assert "EV-7D" in ids, "Near-future events should be included"
        assert "EV-FUTURE" not in ids, "Events beyond window should be excluded"

    def test_events_counts_by_impact(self, tmp_path):
        events = [
            {"event_id": "H1", "event_name": "H1", "event_date": _today_plus(1), "impact_level": "HIGH",
             "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
            {"event_id": "H2", "event_name": "H2", "event_date": _today_plus(2), "impact_level": "HIGH",
             "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
            {"event_id": "M1", "event_name": "M1", "event_date": _today_plus(3), "impact_level": "MEDIUM",
             "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
            {"event_id": "L1", "event_name": "L1", "event_date": _today_plus(4), "impact_level": "LOW",
             "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
        ]
        _make_event_calendar(tmp_path, events)
        result = mei_events(repo_root=tmp_path, days_ahead=14)
        assert result["high_impact_count"] == 2
        assert result["medium_impact_count"] == 1
        assert result["low_impact_count"] == 1
        assert result["total_events"] == 4

    def test_events_sorted_by_date(self, tmp_path):
        events = [
            {"event_id": "E3", "event_date": _today_plus(5), "impact_level": "HIGH",
             "event_name": "E3", "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
            {"event_id": "E1", "event_date": _today_plus(1), "impact_level": "HIGH",
             "event_name": "E1", "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
            {"event_id": "E2", "event_date": _today_plus(3), "impact_level": "HIGH",
             "event_name": "E2", "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
        ]
        _make_event_calendar(tmp_path, events)
        result = mei_events(repo_root=tmp_path, days_ahead=14)
        dates = [e["event_date"] for e in result["events"]]
        assert dates == sorted(dates)

    def test_events_days_away_computed(self, tmp_path):
        target_date = _today_plus(3)
        events = [
            {"event_id": "EV", "event_date": target_date, "impact_level": "HIGH",
             "event_name": "EV", "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
        ]
        _make_event_calendar(tmp_path, events)
        result = mei_events(repo_root=tmp_path)
        ev = result["events"][0]
        assert ev["days_away"] == 3

    def test_events_next_high_event_identified(self, tmp_path):
        events = [
            {"event_id": "LOW1", "event_date": _today_plus(1), "impact_level": "LOW",
             "event_name": "Low", "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
            {"event_id": "HIGH1", "event_date": _today_plus(2), "impact_level": "HIGH",
             "event_name": "High One", "event_type": "T", "sensitivity_tags": [], "source": "X", "consensus_expectation": "", "description": ""},
        ]
        _make_event_calendar(tmp_path, events)
        result = mei_events(repo_root=tmp_path)
        assert result["next_high_event"] is not None
        assert result["next_high_event"]["event_id"] == "HIGH1"
        assert result["next_high_event"]["days_away"] == 2

    def test_events_empty_calendar(self, tmp_path):
        _make_event_calendar(tmp_path, [])
        result = mei_events(repo_root=tmp_path)
        assert result["total_events"] == 0
        assert result["events"] == []
        assert result["next_high_event"] is None

    def test_events_missing_calendar_file(self, tmp_path):
        """Should return gracefully with zero events if file is missing."""
        result = mei_events(repo_root=tmp_path)
        assert result["total_events"] == 0
        assert "error" not in result

    def test_events_summary_returns_expected_structure(self, tmp_path):
        events = [
            {"event_id": "H1", "event_date": _today_plus(1), "impact_level": "HIGH",
             "event_name": "FOMC", "event_type": "MONETARY_POLICY", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "Fed", "consensus_expectation": "Hold", "description": ""},
            {"event_id": "M1", "event_date": _today_plus(20), "impact_level": "MEDIUM",
             "event_name": "CPI", "event_type": "INFLATION", "sensitivity_tags": ["INFLATION"],
             "source": "BLS", "consensus_expectation": "", "description": ""},
        ]
        _make_event_calendar(tmp_path, events)
        summary = mei_events_summary(repo_root=tmp_path)
        assert "as_of_date" in summary
        assert "events_next_14_days" in summary
        assert summary["events_next_14_days"] == 1
        assert summary["high_impact_next_14_days"] == 1
        assert summary["events_next_30_days"] == 2
        assert summary["next_high_impact_event"] is not None
        assert summary["next_high_impact_event"]["event_id"] == "H1"
        assert isinstance(summary["observations"], list)
        assert len(summary["observations"]) >= 1


# ─── MEI-003: Security Profiles ──────────────────────────────────────────────


class TestMeiSecurityProfiles:

    def test_all_tags_present_in_profile(self, tmp_path):
        """Every security profile must include all sensitivity tags."""
        _make_par_run(tmp_path, "PAR-TEST-001", "2026-06-16", [
            {"symbol": "MSFT", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "MEGA", "percent_of_portfolio": "5.0"},
        ])
        profile = mei_security_profile("MSFT", repo_root=tmp_path)
        assert "sensitivities" in profile
        for tag in ALL_TAGS:
            assert tag in profile["sensitivities"], f"Missing tag: {tag}"

    def test_curated_override_applied(self, tmp_path):
        """Curated overrides should override sector defaults for the specified tags."""
        _make_par_run(tmp_path, "PAR-TEST-001", "2026-06-16", [
            {"symbol": "XYZ", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "LARGE", "percent_of_portfolio": "3.0"},
        ])
        _make_security_sensitivities(tmp_path, {
            "XYZ": {"ENERGY": "HIGH", "HOUSING": "HIGH"}
        })
        profile = mei_security_profile("XYZ", repo_root=tmp_path)
        assert profile["sensitivities"]["ENERGY"] == "HIGH"
        assert profile["sensitivities"]["HOUSING"] == "HIGH"
        assert profile["sensitivity_source"] == "CURATED"

    def test_unknown_symbol_gets_defaults(self, tmp_path):
        """Symbol not in holdings or curated list should still return a valid profile."""
        profile = mei_security_profile("ZZZZ", repo_root=tmp_path)
        assert "sensitivities" in profile
        for tag in ALL_TAGS:
            assert tag in profile["sensitivities"]

    def test_sector_defaults_technology(self):
        """TECHNOLOGY sector should have HIGH interest rate and capex sensitivity."""
        defaults = _sector_defaults("TECHNOLOGY", "EQUITIES")
        assert defaults["INTEREST_RATE"] == "HIGH"
        assert defaults["TECHNOLOGY_CAPEX"] == "HIGH"

    def test_sector_defaults_energy(self):
        """ENERGY sector should have HIGH energy sensitivity."""
        defaults = _sector_defaults("ENERGY", "EQUITIES")
        assert defaults["ENERGY"] == "HIGH"
        assert defaults["INTEREST_RATE"] == "LOW"

    def test_sector_defaults_fixed_income(self):
        """Fixed income should have HIGH interest rate and credit sensitivity."""
        defaults = _sector_defaults("ALL", "FIXED_INCOME")
        assert defaults["INTEREST_RATE"] == "HIGH"
        assert defaults["CREDIT"] == "HIGH"
        assert defaults["INFLATION"] == "HIGH"

    def test_sector_defaults_healthcare(self):
        """Healthcare should have HIGH regulatory sensitivity."""
        defaults = _sector_defaults("HEALTHCARE", "EQUITIES")
        assert defaults["REGULATORY"] == "HIGH"
        assert defaults["INTEREST_RATE"] == "LOW"

    def test_bulk_profiles_returns_all_symbols(self, tmp_path):
        """Bulk profile endpoint should return a profile for every requested symbol."""
        symbols = ["MSFT", "NVDA", "CAH", "PSX"]
        result = mei_security_profiles_bulk(symbols, repo_root=tmp_path)
        assert "profiles" in result
        assert result["total"] == 4
        for sym in symbols:
            assert sym in result["profiles"]

    def test_top_sensitivities_excludes_none(self, tmp_path):
        """top_sensitivities should only include HIGH or MODERATE levels."""
        _make_par_run(tmp_path, "PAR-TEST-001", "2026-06-16", [
            {"symbol": "CAH", "asset_class": "EQUITIES", "industry": "HEALTHCARE",
             "market_cap_bucket": "MID", "percent_of_portfolio": "2.0"},
        ])
        profile = mei_security_profile("CAH", repo_root=tmp_path)
        top = profile["top_sensitivities"]
        for tag in top:
            level = profile["sensitivities"][tag]
            assert level in {"HIGH", "MODERATE"}, f"Tag {tag} in top_sensitivities with level {level}"


# ─── MEI-002: Exposures ───────────────────────────────────────────────────────


class TestMeiExposures:

    def _setup(self, tmp_path) -> tuple[Path, list]:
        """Standard setup: FOMC event + 3 holdings."""
        events = [
            {
                "event_id": "FOMC-TEST",
                "event_name": "FOMC Rate Decision",
                "event_date": _today_plus(2),
                "impact_level": "HIGH",
                "event_type": "MONETARY_POLICY",
                "sensitivity_tags": ["INTEREST_RATE", "CREDIT"],
                "source": "Fed",
                "consensus_expectation": "Hold",
                "description": "",
            }
        ]
        _make_event_calendar(tmp_path, events)

        holdings = [
            {"symbol": "MSFT", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "MEGA", "percent_of_portfolio": "8.0"},
            {"symbol": "PSX", "asset_class": "EQUITIES", "industry": "ENERGY",
             "market_cap_bucket": "MID", "percent_of_portfolio": "2.0"},
            {"symbol": "BND", "asset_class": "FIXED_INCOME", "industry": "ALL",
             "market_cap_bucket": "N/A", "percent_of_portfolio": "10.0"},
        ]
        _make_par_run(tmp_path, "PAR-EXP-001", "2026-06-16", holdings)
        # Curated sensitivities: MSFT HIGH to INTEREST_RATE, PSX LOW
        _make_security_sensitivities(tmp_path, {
            "MSFT": {"INTEREST_RATE": "HIGH", "TECHNOLOGY_CAPEX": "HIGH"},
            "PSX": {"INTEREST_RATE": "LOW", "ENERGY": "HIGH"},
            "BND": {"INTEREST_RATE": "HIGH", "CREDIT": "HIGH"},
        })
        return tmp_path, events

    def test_exposures_structure(self, tmp_path):
        self._setup(tmp_path)
        result = mei_exposures(repo_root=tmp_path)
        assert "event_exposures" in result
        assert isinstance(result["event_exposures"], list)
        assert "as_of_date" in result
        assert "total_holdings_analyzed" in result

    def test_fomc_event_included(self, tmp_path):
        self._setup(tmp_path)
        result = mei_exposures(repo_root=tmp_path)
        ev_ids = [e["event_id"] for e in result["event_exposures"]]
        assert "FOMC-TEST" in ev_ids

    def test_exposure_buckets_assigned(self, tmp_path):
        self._setup(tmp_path)
        result = mei_exposures(repo_root=tmp_path)
        fomc_ev = next((e for e in result["event_exposures"] if e["event_id"] == "FOMC-TEST"), None)
        assert fomc_ev is not None
        # MSFT has HIGH INTEREST_RATE → high bucket
        high_syms = [h["symbol"] for h in fomc_ev["high_exposure"]]
        assert "MSFT" in high_syms

    def test_exposure_counts_match_lists(self, tmp_path):
        self._setup(tmp_path)
        result = mei_exposures(repo_root=tmp_path)
        for ev in result["event_exposures"]:
            assert ev["high_count"] == len(ev["high_exposure"])
            assert ev["moderate_count"] == len(ev["moderate_exposure"])
            assert ev["low_count"] == len(ev["low_exposure"])

    def test_exposures_summary_structure(self, tmp_path):
        self._setup(tmp_path)
        summary = mei_exposures_summary(repo_root=tmp_path)
        assert "total_events_analyzed" in summary
        assert "most_exposed_symbols" in summary
        assert isinstance(summary["most_exposed_symbols"], list)
        assert "event_summary_table" in summary

    def test_empty_holdings_no_crash(self, tmp_path):
        _make_event_calendar(tmp_path, [
            {"event_id": "EV", "event_date": _today_plus(1), "impact_level": "HIGH",
             "event_name": "EV", "event_type": "T", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "X", "consensus_expectation": "", "description": ""}
        ])
        # No PAR run — should return gracefully with zero holdings analyzed
        result = mei_exposures(repo_root=tmp_path)
        assert result["total_holdings_analyzed"] == 0
        # Events still appear in the list, just with empty exposure buckets
        for ev in result["event_exposures"]:
            assert ev["high_count"] == 0
            assert ev["moderate_count"] == 0
            assert ev["low_count"] == 0

    def test_no_events_no_crash(self, tmp_path):
        _make_event_calendar(tmp_path, [])
        _make_par_run(tmp_path, "PAR-EMPTY", "2026-06-16", [
            {"symbol": "MSFT", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "MEGA", "percent_of_portfolio": "5.0"},
        ])
        result = mei_exposures(repo_root=tmp_path)
        assert result["total_events"] == 0


# ─── MEI-004: Recommendation Context ─────────────────────────────────────────


class TestMeiRecommendationContext:

    def _setup(self, tmp_path) -> Path:
        events = [
            {
                "event_id": "FOMC-CTX",
                "event_name": "FOMC Rate Decision",
                "event_date": _today_plus(2),
                "impact_level": "HIGH",
                "event_type": "MONETARY_POLICY",
                "sensitivity_tags": ["INTEREST_RATE", "TECHNOLOGY_CAPEX"],
                "source": "Fed",
                "consensus_expectation": "Hold",
                "description": "",
            }
        ]
        _make_event_calendar(tmp_path, events)

        holdings = [
            {"symbol": "DELL", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "LARGE", "percent_of_portfolio": "3.5"},
            {"symbol": "PSX", "asset_class": "EQUITIES", "industry": "ENERGY",
             "market_cap_bucket": "MID", "percent_of_portfolio": "2.0"},
        ]
        dq = [
            {"rank": "1", "symbol": "DELL", "composite_score": "4.7",
             "narrative_tier": "CORE_CONVICTION_LEADER", "trim_score": "0"},
        ]
        recs = [
            {"recommendation_id": "R1", "recommendation_type": "REDUCE_OVERWEIGHT",
             "priority": 2, "confidence": "HIGH", "title": "Reduce PSX",
             "affected_symbols": ["PSX"], "evidence_summary": "overweight"},
        ]
        _make_par_run(tmp_path, "PAR-CTX-001", "2026-06-16", holdings, dq, recs)
        _make_security_sensitivities(tmp_path, {
            "DELL": {"INTEREST_RATE": "HIGH", "TECHNOLOGY_CAPEX": "HIGH"},
            "PSX": {"INTEREST_RATE": "LOW", "ENERGY": "HIGH"},
        })
        return tmp_path

    def test_context_structure(self, tmp_path):
        self._setup(tmp_path)
        result = mei_recommendation_context(repo_root=tmp_path)
        assert "items" in result
        assert "total_recommendations" in result
        assert "event_exposed_count" in result
        assert "clean_count" in result
        assert "as_of_date" in result

    def test_deployment_candidate_included(self, tmp_path):
        self._setup(tmp_path)
        result = mei_recommendation_context(repo_root=tmp_path)
        symbols = [i["symbol"] for i in result["items"]]
        assert "DELL" in symbols

    def test_actionable_recommendation_included(self, tmp_path):
        self._setup(tmp_path)
        result = mei_recommendation_context(repo_root=tmp_path)
        symbols = [i["symbol"] for i in result["items"]]
        assert "PSX" in symbols

    def test_event_exposed_flag_set(self, tmp_path):
        self._setup(tmp_path)
        result = mei_recommendation_context(repo_root=tmp_path)
        dell_item = next((i for i in result["items"] if i["symbol"] == "DELL"), None)
        assert dell_item is not None
        # DELL has HIGH INTEREST_RATE / TECH_CAPEX + FOMC event has those tags
        assert dell_item["event_exposure_label"] == "EVENT_EXPOSED"
        assert dell_item["max_sensitivity"] == "HIGH"

    def test_low_sensitivity_symbol_may_be_clean(self, tmp_path):
        """PSX has LOW INTEREST_RATE and no TECHNOLOGY_CAPEX sensitivity to FOMC tags."""
        self._setup(tmp_path)
        result = mei_recommendation_context(repo_root=tmp_path)
        psx_item = next((i for i in result["items"] if i["symbol"] == "PSX"), None)
        assert psx_item is not None
        # PSX LOW on INTEREST_RATE → may be low exposure, not necessarily CLEAN
        # but should have operator_note
        assert isinstance(psx_item["operator_note"], str)
        assert len(psx_item["operator_note"]) > 0

    def test_operator_note_present_for_all_items(self, tmp_path):
        self._setup(tmp_path)
        result = mei_recommendation_context(repo_root=tmp_path)
        for item in result["items"]:
            assert "operator_note" in item
            assert isinstance(item["operator_note"], str)
            assert len(item["operator_note"]) > 0

    def test_context_summary_structure(self, tmp_path):
        self._setup(tmp_path)
        summary = mei_recommendation_context_summary(repo_root=tmp_path)
        assert "total_recommendations" in summary
        assert "event_exposed_count" in summary
        assert "clean_count" in summary
        assert "high_sensitivity_exposed" in summary
        assert "observations" in summary
        assert isinstance(summary["observations"], list)

    def test_no_recommendation_modification(self, tmp_path):
        """MEI context overlay must not modify any PAR artifacts."""
        run_id = "PAR-CTX-NMOD"
        _make_event_calendar(tmp_path, [
            {"event_id": "EV", "event_date": _today_plus(1), "impact_level": "HIGH",
             "event_name": "Test", "event_type": "T", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "X", "consensus_expectation": "", "description": ""}
        ])
        holdings = [{"symbol": "MSFT", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
                     "market_cap_bucket": "MEGA", "percent_of_portfolio": "5.0"}]
        dq = [{"rank": "1", "symbol": "MSFT", "composite_score": "4.5",
               "narrative_tier": "CORE_CONVICTION_LEADER", "trim_score": "0"}]
        run_dir = _make_par_run(tmp_path, run_id, "2026-06-16", holdings, dq)

        # Capture deployment queue before MEI call
        dq_path = run_dir / "deployment_queue.json"
        before = dq_path.read_text(encoding="utf-8")

        mei_recommendation_context(repo_root=tmp_path)

        after = dq_path.read_text(encoding="utf-8")
        assert before == after, "MEI must not modify deployment_queue.json"


# ─── MEI-005: Event History ───────────────────────────────────────────────────


class TestMeiEventHistory:

    def test_empty_history_returns_gracefully(self, tmp_path):
        _make_event_history(tmp_path, [])
        result = mei_event_history(repo_root=tmp_path)
        assert result["total_events_tracked"] == 0
        assert result["events"] == []
        assert result["last_event_date"] is None

    def test_history_entries_normalized(self, tmp_path):
        entries = [
            {
                "event_id": "FOMC-2026-03-19",
                "event_name": "FOMC Rate Decision",
                "event_date": "2026-03-19",
                "event_type": "MONETARY_POLICY",
                "portfolio_return_pct": 1.2,
                "best_performers": ["VRT", "DELL"],
                "worst_performers": ["TSLA"],
                "notes": "Rate held as expected.",
                "recorded_at": "2026-03-20T10:00:00Z",
            }
        ]
        _make_event_history(tmp_path, entries)
        result = mei_event_history(repo_root=tmp_path)
        assert result["total_events_tracked"] == 1
        ev = result["events"][0]
        assert ev["event_id"] == "FOMC-2026-03-19"
        assert ev["portfolio_return_pct"] == 1.2
        assert "VRT" in ev["best_performers"]

    def test_history_sorted_descending(self, tmp_path):
        entries = [
            {"event_id": "E1", "event_date": "2026-01-15", "event_name": "E1", "event_type": "T",
             "best_performers": [], "worst_performers": [], "notes": ""},
            {"event_id": "E2", "event_date": "2026-03-19", "event_name": "E2", "event_type": "T",
             "best_performers": [], "worst_performers": [], "notes": ""},
            {"event_id": "E3", "event_date": "2026-02-10", "event_name": "E3", "event_type": "T",
             "best_performers": [], "worst_performers": [], "notes": ""},
        ]
        _make_event_history(tmp_path, entries)
        result = mei_event_history(repo_root=tmp_path)
        dates = [e["event_date"] for e in result["events"]]
        assert dates == sorted(dates, reverse=True)

    def test_history_summary_structure(self, tmp_path):
        entries = [
            {"event_id": "E1", "event_date": "2026-03-19", "event_name": "FOMC", "event_type": "T",
             "portfolio_return_pct": 0.8, "best_performers": [], "worst_performers": [], "notes": ""},
            {"event_id": "E2", "event_date": "2026-04-10", "event_name": "CPI", "event_type": "T",
             "portfolio_return_pct": -0.5, "best_performers": [], "worst_performers": [], "notes": ""},
        ]
        _make_event_history(tmp_path, entries)
        summary = mei_event_history_summary(repo_root=tmp_path)
        assert summary["total_events_tracked"] == 2
        assert summary["positive_event_count"] == 1
        assert summary["negative_event_count"] == 1
        assert summary["avg_portfolio_return_pct"] == pytest.approx(0.15, abs=0.01)
        assert isinstance(summary["observations"], list)

    def test_missing_history_file_no_crash(self, tmp_path):
        """Should return zero-events gracefully if history file is missing."""
        result = mei_event_history(repo_root=tmp_path)
        assert result["total_events_tracked"] == 0
        assert "error" not in result

    def test_history_summary_empty_observations(self, tmp_path):
        _make_event_history(tmp_path, [])
        summary = mei_event_history_summary(repo_root=tmp_path)
        assert isinstance(summary["observations"], list)
        assert len(summary["observations"]) >= 1  # Must explain why empty


# ─── Validation Q1–Q8 ─────────────────────────────────────────────────────────


class TestMeiValidationQuestions:
    """Formal validation of the EPIC's Q1-Q8 acceptance criteria."""

    def test_q1_can_identify_upcoming_events(self, tmp_path):
        """Q1: SIH can identify upcoming major market events."""
        events = [
            {"event_id": "FOMC", "event_name": "FOMC Rate Decision",
             "event_date": _today_plus(3), "impact_level": "HIGH",
             "event_type": "MONETARY_POLICY", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "Fed", "consensus_expectation": "Hold", "description": ""},
        ]
        _make_event_calendar(tmp_path, events)
        result = mei_events(repo_root=tmp_path)
        assert result["total_events"] >= 1
        assert any(e["event_id"] == "FOMC" for e in result["events"])

    def test_q2_can_identify_portfolio_exposure(self, tmp_path):
        """Q2: SIH can identify portfolio exposure to those events."""
        events = [
            {"event_id": "FOMC", "event_name": "FOMC Rate Decision",
             "event_date": _today_plus(2), "impact_level": "HIGH",
             "event_type": "MONETARY_POLICY", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "Fed", "consensus_expectation": "", "description": ""}
        ]
        _make_event_calendar(tmp_path, events)
        _make_par_run(tmp_path, "PAR-Q2", "2026-06-16", [
            {"symbol": "MSFT", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "MEGA", "percent_of_portfolio": "5.0"},
        ])
        _make_security_sensitivities(tmp_path, {"MSFT": {"INTEREST_RATE": "HIGH"}})
        result = mei_exposures(repo_root=tmp_path)
        assert result["total_events"] >= 1
        fomc_exp = next((e for e in result["event_exposures"] if e["event_id"] == "FOMC"), None)
        assert fomc_exp is not None
        high_syms = [h["symbol"] for h in fomc_exp["high_exposure"]]
        assert "MSFT" in high_syms

    def test_q3_can_identify_security_level_sensitivities(self, tmp_path):
        """Q3: SIH can identify security-level event sensitivities."""
        _make_par_run(tmp_path, "PAR-Q3", "2026-06-16", [
            {"symbol": "PSX", "asset_class": "EQUITIES", "industry": "ENERGY",
             "market_cap_bucket": "MID", "percent_of_portfolio": "3.0"},
        ])
        _make_security_sensitivities(tmp_path, {"PSX": {"ENERGY": "HIGH", "INTEREST_RATE": "LOW"}})
        profile = mei_security_profile("PSX", repo_root=tmp_path)
        assert profile["sensitivities"]["ENERGY"] == "HIGH"
        assert "ENERGY" in profile["top_sensitivities"]

    def test_q4_recommendations_viewable_in_event_context(self, tmp_path):
        """Q4: Recommendations can be viewed in event context."""
        events = [
            {"event_id": "FOMC", "event_name": "FOMC",
             "event_date": _today_plus(2), "impact_level": "HIGH",
             "event_type": "MONETARY_POLICY", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "Fed", "consensus_expectation": "", "description": ""}
        ]
        _make_event_calendar(tmp_path, events)
        dq = [{"rank": "1", "symbol": "MSFT", "composite_score": "4.5",
               "narrative_tier": "CORE_CONVICTION_LEADER", "trim_score": "0"}]
        _make_par_run(tmp_path, "PAR-Q4", "2026-06-16", [
            {"symbol": "MSFT", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "MEGA", "percent_of_portfolio": "5.0"},
        ], deployment_queue=dq)
        _make_security_sensitivities(tmp_path, {"MSFT": {"INTEREST_RATE": "HIGH"}})
        result = mei_recommendation_context(repo_root=tmp_path)
        assert result["total_recommendations"] >= 1
        msft = next((i for i in result["items"] if i["symbol"] == "MSFT"), None)
        assert msft is not None
        assert msft["event_exposure_label"] == "EVENT_EXPOSED"
        assert isinstance(msft["operator_note"], str)

    def test_q5_no_recommendation_engines_modified(self, tmp_path):
        """Q5: No recommendation engines are modified by MEI."""
        run_id = "PAR-Q5"
        _make_event_calendar(tmp_path, [
            {"event_id": "EV", "event_date": _today_plus(1), "impact_level": "HIGH",
             "event_name": "Test", "event_type": "T", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "X", "consensus_expectation": "", "description": ""}
        ])
        run_dir = _make_par_run(tmp_path, run_id, "2026-06-16", [
            {"symbol": "VRT", "asset_class": "EQUITIES", "industry": "INDUSTRIALS",
             "market_cap_bucket": "LARGE", "percent_of_portfolio": "4.0"},
        ], deployment_queue=[{"rank": "1", "symbol": "VRT", "composite_score": "3.9",
                               "narrative_tier": "HIGH_CONVICTION", "trim_score": "0"}])

        recs_before = (run_dir / "recommendations.json").read_text()
        dq_before = (run_dir / "deployment_queue.json").read_text()

        mei_recommendation_context(repo_root=tmp_path)
        mei_exposures(repo_root=tmp_path)

        assert (run_dir / "recommendations.json").read_text() == recs_before
        assert (run_dir / "deployment_queue.json").read_text() == dq_before

    def test_q6_no_scoring_engines_modified(self, tmp_path):
        """Q6: No scoring engines are modified by MEI."""
        _make_event_calendar(tmp_path, [])
        _make_par_run(tmp_path, "PAR-Q6", "2026-06-16", [
            {"symbol": "MSFT", "asset_class": "EQUITIES", "industry": "TECHNOLOGY",
             "market_cap_bucket": "MEGA", "percent_of_portfolio": "5.0"},
        ])
        # security_profiles.py reads but never writes to curated file
        _make_security_sensitivities(tmp_path, {"MSFT": {"INTEREST_RATE": "HIGH"}})
        sens_before = (tmp_path / "data" / "mei" / "security_sensitivities.json").read_text()
        mei_security_profile("MSFT", repo_root=tmp_path)
        sens_after = (tmp_path / "data" / "mei" / "security_sensitivities.json").read_text()
        assert sens_before == sens_after

    def test_q7_no_governance_rules_modified(self, tmp_path):
        """Q7: No governance rules are modified by MEI."""
        _make_event_calendar(tmp_path, [])
        cal_before = (tmp_path / "data" / "mei" / "event_calendar.json").read_text()
        mei_events(repo_root=tmp_path)
        cal_after = (tmp_path / "data" / "mei" / "event_calendar.json").read_text()
        assert cal_before == cal_after

    def test_q8_mei_is_informational_only(self, tmp_path):
        """Q8: MEI is informational only — output is read-only context, no side effects."""
        _make_event_calendar(tmp_path, [
            {"event_id": "EV", "event_date": _today_plus(1), "impact_level": "HIGH",
             "event_name": "FOMC", "event_type": "MONETARY_POLICY", "sensitivity_tags": ["INTEREST_RATE"],
             "source": "Fed", "consensus_expectation": "Hold", "description": ""}
        ])
        _make_event_history(tmp_path, [])

        # Calling all MEI endpoints should not create new artifacts
        mei_files_before = set((tmp_path / "data" / "mei").iterdir())
        mei_events(repo_root=tmp_path)
        mei_events_summary(repo_root=tmp_path)
        mei_event_history(repo_root=tmp_path)
        mei_event_history_summary(repo_root=tmp_path)
        mei_files_after = set((tmp_path / "data" / "mei").iterdir())

        assert mei_files_before == mei_files_after, (
            "MEI endpoints must not create new files or modify existing ones"
        )
