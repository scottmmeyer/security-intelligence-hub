from __future__ import annotations

from pathlib import Path


def test_copilot_instructions_define_incoming_routing_contract() -> None:
    path = Path(__file__).resolve().parents[1] / ".github" / "copilot-instructions.md"
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "process the incoming folder" in lowered
    assert "scripts/_run_intake.py" in text
    assert "scripts/process_incoming_portfolio.py" in text
    assert "incoming/ess/starmine" in text
    assert "incoming/ess/non_starmine_zacks" in text

    assert "do not use:" in lowered
    assert "for ess files" in lowered
    assert "mixed incoming content" in lowered
    assert "support / unknown files" in lowered
