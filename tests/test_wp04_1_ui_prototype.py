from __future__ import annotations

from pathlib import Path


def test_ui_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "ui" / "outcome_visualization" / "index.html").exists()
    assert (root / "ui" / "outcome_visualization" / "app.js").exists()
    assert (root / "ui" / "outcome_visualization" / "README.md").exists()


def test_runner_script_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts" / "run_outcome_ui.py").exists()


def test_empty_state_message_is_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")
    assert (
        "Replay contracts exist, but no performance points are available for this filter window."
    ) in app_js


def test_ui_point_in_time_and_status_fallback_logic_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")

    assert "drawPointInTimeChart" in app_js
    assert "insufficient_history" in app_js
    assert "unavailable" in app_js
    assert "initialized" in app_js
    assert "pending" in app_js


def test_ui_replay_availability_contract_support_present() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")
    index_html = (root / "ui" / "outcome_visualization" / "index.html").read_text(encoding="utf-8")

    assert "replay_availability.csv" in app_js
    assert "replay_matrix.csv" in app_js
    assert "availabilityMeta" in index_html


def test_readme_documents_input_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "ui" / "outcome_visualization" / "README.md").read_text(encoding="utf-8")

    assert "data/current/replay_performance_series.csv" in readme
    assert "data/current/replay_inputs.csv" in readme
    assert "data/current/analytical_universe.csv" in readme


def test_no_heavy_frontend_tooling_introduced() -> None:
    root = Path(__file__).resolve().parents[1]

    assert not (root / "ui" / "outcome_visualization" / "package.json").exists()
    assert not (root / "ui" / "outcome_visualization" / "node_modules").exists()


def test_portfolio_alignment_ui_shows_exposure_split() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "Direct" in app_js
    assert "ETF-derived" in app_js
    assert "Effective" in app_js
    assert "Hyper Mega exposure:" in app_js
