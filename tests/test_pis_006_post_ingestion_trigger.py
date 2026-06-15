"""Tests for PIS-006 post-ingestion refresh trigger.

Test matrix:
  A. registered=True  → refresh triggered exactly once
  B. duplicate=True   → refresh not triggered
  C. registration failure → refresh not triggered
  D. refresh exception    → analysis path unaffected (still returns pis_registration)
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import src.portfolio.runner as runner
from src.pis.service import PortfolioRegistrationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(*, registered: bool, duplicate: bool, warning: str = "") -> PortfolioRegistrationResult:
    return PortfolioRegistrationResult(
        snapshot_id="PSNAP-TEST-0001",
        registered=registered,
        duplicate=duplicate,
        position_count=10,
        warning=warning,
    )


# ---------------------------------------------------------------------------
# A. registered=True → refresh triggered exactly once
# ---------------------------------------------------------------------------

def test_refresh_triggered_on_new_registration(monkeypatch):
    """When a snapshot is successfully registered, background refresh starts exactly once."""

    started_threads: list[str] = []

    class _FakeThread:
        def __init__(self, target, daemon, name, **kwargs):
            self.name = name
            started_threads.append(name)

        def start(self):
            pass  # don't actually start the thread in tests

    monkeypatch.setattr("threading.Thread", _FakeThread)

    fake_result = _make_result(registered=True, duplicate=False)
    monkeypatch.setattr(
        "src.pis.service.register_portfolio_snapshot_from_sih",
        lambda **_: fake_result,
    )

    # Use a minimal mock snapshot (fields checked: ingestion_status, portfolio_snapshot_id)
    snapshot = MagicMock()
    snapshot.ingestion_status = "ACCEPTED"
    snapshot.portfolio_snapshot_id = "PSNAP-TEST-0001"

    pis_reg, warnings = runner._register_pis_snapshot_best_effort(
        snapshot=snapshot,
        raw_holdings=[],
    )

    assert pis_reg["status"] == "REGISTERED"
    assert pis_reg["registered"] is True
    assert len(started_threads) == 1
    assert started_threads[0] == "pis-post-ingestion-refresh"


# ---------------------------------------------------------------------------
# B. duplicate=True → refresh not triggered
# ---------------------------------------------------------------------------

def test_refresh_not_triggered_on_duplicate(monkeypatch):
    """When registration returns duplicate=True, no background refresh thread starts."""

    started_threads: list[str] = []

    class _FakeThread:
        def __init__(self, target, daemon, name, **kwargs):
            started_threads.append(name)

        def start(self):
            pass

    monkeypatch.setattr("threading.Thread", _FakeThread)

    fake_result = _make_result(registered=False, duplicate=True)
    monkeypatch.setattr(
        "src.pis.service.register_portfolio_snapshot_from_sih",
        lambda **_: fake_result,
    )

    snapshot = MagicMock()
    snapshot.ingestion_status = "ACCEPTED"
    snapshot.portfolio_snapshot_id = "PSNAP-TEST-0002"

    pis_reg, _ = runner._register_pis_snapshot_best_effort(
        snapshot=snapshot,
        raw_holdings=[],
    )

    assert pis_reg["status"] == "DUPLICATE"
    assert pis_reg["duplicate"] is True
    assert len(started_threads) == 0


# ---------------------------------------------------------------------------
# C. Registration failure → refresh not triggered
# ---------------------------------------------------------------------------

def test_refresh_not_triggered_on_registration_failure(monkeypatch):
    """When register_portfolio_snapshot_from_sih raises, refresh must not start."""

    started_threads: list[str] = []

    class _FakeThread:
        def __init__(self, target, daemon, name, **kwargs):
            started_threads.append(name)

        def start(self):
            pass

    monkeypatch.setattr("threading.Thread", _FakeThread)

    def _raise(**_):
        raise RuntimeError("simulated registration failure")

    monkeypatch.setattr(
        "src.pis.service.register_portfolio_snapshot_from_sih",
        _raise,
    )

    snapshot = MagicMock()
    snapshot.ingestion_status = "ACCEPTED"
    snapshot.portfolio_snapshot_id = "PSNAP-TEST-0003"

    pis_reg, warnings = runner._register_pis_snapshot_best_effort(
        snapshot=snapshot,
        raw_holdings=[],
    )

    # Registration failed → FAILED status, no refresh
    assert pis_reg["status"] == "FAILED"
    assert pis_reg["registered"] is False
    assert len(started_threads) == 0
    assert any("PIS_SNAPSHOT_REGISTRATION_FAILED" in w for w in warnings)


# ---------------------------------------------------------------------------
# D. Refresh exception → analysis path unaffected
# ---------------------------------------------------------------------------

def test_refresh_exception_does_not_affect_analysis(monkeypatch):
    """Even if trigger_startup_refresh raises inside the thread, registration succeeds."""

    # Patch threading.Thread to run the target immediately (synchronously) so we
    # can test the exception-swallowing behaviour without spawning a real thread.
    class _SyncThread:
        def __init__(self, target, daemon, name, **kwargs):
            self._target = target

        def start(self):
            self._target()  # run synchronously; should not raise

    monkeypatch.setattr("threading.Thread", _SyncThread)

    # trigger_startup_refresh raises
    def _bad_refresh(**_):
        raise RuntimeError("simulated refresh failure")

    monkeypatch.setattr(
        "src.pis.refresh_orchestrator.trigger_startup_refresh",
        _bad_refresh,
    )

    fake_result = _make_result(registered=True, duplicate=False)
    monkeypatch.setattr(
        "src.pis.service.register_portfolio_snapshot_from_sih",
        lambda **_: fake_result,
    )

    snapshot = MagicMock()
    snapshot.ingestion_status = "ACCEPTED"
    snapshot.portfolio_snapshot_id = "PSNAP-TEST-0004"

    # Must not raise, even though refresh throws
    pis_reg, warnings = runner._register_pis_snapshot_best_effort(
        snapshot=snapshot,
        raw_holdings=[],
    )

    assert pis_reg["status"] == "REGISTERED"
    assert pis_reg["registered"] is True
    # No warning about refresh failure (it is swallowed silently)
    assert not any("refresh" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# E. REJECTED snapshot → neither registration nor refresh occurs
# ---------------------------------------------------------------------------

def test_no_refresh_for_rejected_snapshot(monkeypatch):
    """REJECTED snapshots skip registration entirely; refresh must never start."""

    started_threads: list[str] = []

    class _FakeThread:
        def __init__(self, target, daemon, name, **kwargs):
            started_threads.append(name)

        def start(self):
            pass

    monkeypatch.setattr("threading.Thread", _FakeThread)

    snapshot = MagicMock()
    snapshot.ingestion_status = "REJECTED"
    snapshot.portfolio_snapshot_id = "PSNAP-TEST-0005"

    pis_reg, warnings = runner._register_pis_snapshot_best_effort(
        snapshot=snapshot,
        raw_holdings=[],
    )

    assert pis_reg["status"] == "SKIPPED"
    assert len(started_threads) == 0
