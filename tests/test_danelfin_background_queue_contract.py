from __future__ import annotations

from pathlib import Path


_EXTENSION_BG = Path("tools/chrome_danelfin_capture_extension/background.js")


def _source() -> str:
    return _EXTENSION_BG.read_text(encoding="utf-8")


def test_queue_includes_required_pairs_in_order() -> None:
    src = _source()
    expected = [
        '["MU", "VRT"]',
        '["FHI", "DELL"]',
        '["CVE", "AEIS"]',
        '["CAH", "TSM"]',
        '["ATLC", "TSLA"]',
    ]
    indexes = [src.index(token) for token in expected]
    assert indexes == sorted(indexes)


def test_queue_uses_inactive_tabs_and_sequential_processing() -> None:
    src = _source()
    assert "active: false" in src
    assert "for (const pair of CAPTURE_QUEUE)" in src
    assert "await waitForTabComplete(created.id)" in src
    assert "await postCapture(response.capture.observations, false)" in src
    assert "await sleep(QUEUE_DELAY_MS);" in src
    assert "Promise.all(" not in src


def test_queue_stops_on_challenge_and_same_day_conflict() -> None:
    src = _source()
    assert "if (response.capture.challenge)" in src
    assert "throw new Error(stopReason);" in src
    assert "hasSameDayConflict(ingestBody)" in src
    assert "conflicts_with_existing_same_day_value" in src


def test_queue_blocks_concurrent_starts() -> None:
    src = _source()
    assert "let queueRunning = false;" in src
    assert "if (queueRunning)" in src
    assert "queueRunning = true;" in src
    assert "queueRunning = false;" in src
