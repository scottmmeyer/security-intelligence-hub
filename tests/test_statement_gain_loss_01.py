from __future__ import annotations

import inspect
import json
import socket
import threading
from contextlib import closing
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.request
from unittest.mock import patch
import sys
import types
import pytest

from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer
from scripts.ingest_statement_gain_loss import main as ingest_main
from src.portfolio.statements import statement_gain_loss as sgl
from src.portfolio.statements.statement_gain_loss import (
    StatementParsingError,
    build_snapshot_from_sources,
    load_statement_source,
)


FIXTURE = Path("tests/fixtures/statement_gain_loss/fidelity_statement_2026_06_combined.txt")


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _fetch_json(path: str, patchers: list | None = None) -> dict:
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with ExitStack() as stack:
            for p in patchers or []:
                stack.enter_context(p)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                assert resp.status == 200
                return json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _snapshot():
    src = load_statement_source(source_path=FIXTURE)
    return build_snapshot_from_sources(
        [src],
        statement_date="2026-06-30",
        statement_period_start="2026-06-01",
        statement_period_end="2026-06-30",
        main_statement_account_numbers={"X20-548022", "Z35-123695"},
    )


def _snapshot_without_explicit_dates(source_path: Path | None = None):
    src = load_statement_source(source_path=source_path or FIXTURE)
    return build_snapshot_from_sources(
        [src],
        main_statement_account_numbers={"X20-548022", "Z35-123695"},
    )


def test_parse_main_portfolio_statement_summary_values() -> None:
    snap = _snapshot()
    p = snap.portfolio_summary
    assert p is not None
    assert p.ending_value == 488629.07
    assert p.total_including_other_holdings == 491972.75
    assert p.beginning_value_ytd == 370160.68
    assert p.additions_ytd == 116090.53
    assert p.subtractions_ytd == -137018.74
    assert p.fees_ytd == -222.25
    assert p.transfers_between_fidelity_accounts_ytd == 50916.98
    assert p.change_in_investment_value_ytd == 88479.62
    assert p.taxable_income_ytd == 3122.91
    assert p.dividends_ytd == 3088.33
    assert p.long_term_capital_gains_income_ytd == 34.58


def test_parse_x20_realized_gain_loss_values() -> None:
    snap = _snapshot()
    x20 = next(a for a in snap.accounts if a.account_number == "X20-548022")
    assert x20.ending_value == 4.61
    assert x20.change_in_investment_value_ytd == 9898.90
    assert x20.realized_short_term_net_ytd == -860.90
    assert x20.realized_short_term_gain_ytd == 117.74
    assert x20.realized_short_term_loss_ytd == -1813.40
    assert x20.realized_short_term_disallowed_loss_ytd == 834.76
    assert x20.realized_long_term_net_ytd == -53337.12
    assert x20.realized_long_term_gain_ytd == 47.73
    assert x20.realized_long_term_loss_ytd == -71382.52
    assert x20.realized_long_term_disallowed_loss_ytd == 17997.67
    assert x20.realized_net_gain_loss_ytd == -54198.02


def test_parse_z35_realized_gain_loss_values() -> None:
    snap = _snapshot()
    z35 = next(a for a in snap.accounts if a.account_number == "Z35-123695")
    assert z35.ending_value == 488624.46
    assert z35.change_in_investment_value_ytd == 78580.72
    assert z35.realized_short_term_net_ytd == 766.62
    assert z35.realized_short_term_gain_ytd == 8944.78
    assert z35.realized_short_term_loss_ytd == -8178.16
    assert z35.realized_long_term_net_ytd == 13643.16
    assert z35.realized_long_term_gain_ytd == 14214.32
    assert z35.realized_long_term_loss_ytd == -571.16
    assert z35.realized_net_gain_loss_ytd == 14409.78


def test_parse_z26_joint_realized_gain_loss_values() -> None:
    snap = _snapshot()
    z26 = next(a for a in snap.accounts if a.account_number == "Z26-346415")
    assert z26.ending_value == 0.00
    assert z26.beginning_value_ytd == 56756.19
    assert z26.change_in_investment_value_ytd == 6741.76
    assert z26.realized_short_term_net_ytd == 1598.94
    assert z26.realized_short_term_gain_ytd == 1606.26
    assert z26.realized_short_term_loss_ytd == -7.32
    assert z26.realized_long_term_net_ytd == 167.16
    assert z26.realized_long_term_gain_ytd == 804.77
    assert z26.realized_long_term_loss_ytd == -637.61
    assert z26.realized_net_gain_loss_ytd == 1766.10


def test_account_metadata_overrides_apply_authoritatively() -> None:
    snap = _snapshot()
    x20 = next(a for a in snap.accounts if a.account_number == "X20-548022")
    z35 = next(a for a in snap.accounts if a.account_number == "Z35-123695")
    z26 = next(a for a in snap.accounts if a.account_number == "Z26-346415")

    assert x20.account_type == "Individual TOD"
    assert x20.account_name == "Individual TOD"
    assert z35.account_type == "Individual TOD"
    assert z35.account_name == "Individual TOD"
    assert z26.account_type == "Joint WROS TOD"
    assert z26.account_name == "Joint WROS TOD"


def test_content_month_name_date_detection_without_explicit_overrides() -> None:
    snap = _snapshot_without_explicit_dates()
    assert snap.statement_period_start == "2026-06-01"
    assert snap.statement_period_end == "2026-06-30"
    assert snap.statement_date == "2026-06-30"


def test_filename_fallback_date_detection_when_content_missing() -> None:
    with TemporaryDirectory() as tmp:
        src_path = Path(tmp) / "Statement06302026.txt"
        src_path.write_text(
            "Account X20-548022, Individual TOD\n"
            "Ending Account Value: $4.61\n"
            "YTD net realized gain/loss: -$54,198.02\n",
            encoding="utf-8",
        )
        snap = _snapshot_without_explicit_dates(src_path)

    assert snap.statement_date == "2026-06-30"
    assert snap.statement_period_start == "2026-06-30"
    assert snap.statement_period_end == "2026-06-30"


def test_content_date_overrides_conflicting_filename_date() -> None:
    with TemporaryDirectory() as tmp:
        src_path = Path(tmp) / "Statement05312026.txt"
        src_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        snap = _snapshot_without_explicit_dates(src_path)

    assert snap.statement_date == "2026-06-30"
    assert "Content-derived statement date overrides filename-derived date." in snap.warnings


def test_no_date_detected_raises_structured_failure() -> None:
    with TemporaryDirectory() as tmp:
        src_path = Path(tmp) / "statement_unknown.txt"
        src_path.write_text("Account X20-548022, Individual TOD\n", encoding="utf-8")
        src = load_statement_source(source_path=src_path)
        with pytest.raises(StatementParsingError) as exc:
            build_snapshot_from_sources([src])

    assert exc.value.reason == "statement_date_unresolved"
    assert exc.value.details["source_file"].endswith("statement_unknown.txt")


def test_provenance_classification_fixture_and_manual_text() -> None:
    fixture_src = load_statement_source(source_path=FIXTURE)
    inline_src = load_statement_source(text="Account X20-548022, Individual TOD")
    assert fixture_src.source_provenance == "fixture-text"
    assert inline_src.source_provenance == "manual-text-extract"


def test_pdf_ocr_unavailable_returns_structured_failure() -> None:
    class _DummyPage:
        def extract_text(self):
            return None

    class _DummyReader:
        def __init__(self, _path: str):
            self.pages = [_DummyPage()]

    with TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "Statement06302026.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        fake_pypdf = types.SimpleNamespace(PdfReader=_DummyReader)
        with patch.dict(sys.modules, {"pypdf": fake_pypdf}):
            with pytest.raises(StatementParsingError) as exc:
                load_statement_source(source_path=pdf)

    assert exc.value.reason == "ocr_unavailable"
    assert exc.value.details["source_provenance"] == "ocr-unavailable"


def test_combined_realized_net_gain_loss_all_three_accounts() -> None:
    snap = _snapshot()
    assert snap.derived_totals["combined_realized_net_gain_loss_ytd_all_accounts"] == -38022.14


def test_combined_realized_net_gain_loss_main_statement_accounts_only() -> None:
    snap = _snapshot()
    assert snap.derived_totals["combined_realized_net_gain_loss_ytd_main_statement_accounts"] == -39788.24


def test_ytd_change_in_investment_value_values() -> None:
    snap = _snapshot()
    assert snap.portfolio_summary is not None
    assert snap.portfolio_summary.change_in_investment_value_ytd == 88479.62
    x20 = next(a for a in snap.accounts if a.account_number == "X20-548022")
    z35 = next(a for a in snap.accounts if a.account_number == "Z35-123695")
    z26 = next(a for a in snap.accounts if a.account_number == "Z26-346415")
    assert x20.change_in_investment_value_ytd == 9898.90
    assert z35.change_in_investment_value_ytd == 78580.72
    assert z26.change_in_investment_value_ytd == 6741.76


def test_missing_statement_artifact_returns_unavailable_contract() -> None:
    with TemporaryDirectory() as tmp:
        payload = _fetch_json(
            "/api/statement-gain-loss/latest",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", Path(tmp))],
        )

    assert payload["status"] == "unavailable"
    assert payload["statement_date"] is None
    assert payload["statement_period"]["start"] is None
    assert payload["statement_period"]["end"] is None
    assert payload["scoring_impact"] == "none"


def _write_statement_artifact_payload(path: Path) -> dict:
    payload = {
        "statement_period": {"start": "2026-06-01", "end": "2026-06-30"},
        "statement_date": "2026-06-30",
        "source_files": ["data/incoming/fidelity_statements/Statement06302026.pdf"],
        "source_provenance": [
            {
                "source_file": "data/incoming/fidelity_statements/Statement06302026.pdf",
                "source_provenance": "pdf-text-extracted",
            }
        ],
        "extraction_timestamp_utc": "2026-07-01T00:00:00+00:00",
        "portfolio_summary": {
            "change_in_investment_value_ytd": 88479.62,
        },
        "accounts": [
            {
                "account_number": "X20-548022",
                "realized_net_gain_loss_ytd": -54198.02,
                "change_in_investment_value_ytd": 9898.90,
                "ending_value": 4.61,
            }
        ],
        "derived_totals": {
            "combined_realized_net_gain_loss_ytd_all_accounts": -38022.14,
        },
        "warnings": [],
        "scoring_impact": "none",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_statement_endpoint_available_uses_latest_pointer_and_includes_provenance_summary() -> None:
    with TemporaryDirectory() as tmp:
        repo = Path(tmp)
        latest = repo / "artifacts" / "statement_gain_loss" / "latest.json"
        _write_statement_artifact_payload(latest)
        payload = _fetch_json(
            "/api/statement-gain-loss/latest",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", repo)],
        )

    assert payload["status"] == "available"
    assert payload["statement_date"] == "2026-06-30"
    assert payload["source_provenance_summary"]["source_count"] == 1
    assert payload["source_provenance_summary"]["provenance_types"] == ["pdf-text-extracted"]
    assert payload["scoring_impact"] == "none"


def test_statement_endpoint_history_fallback_resolves_latest_dated_artifact() -> None:
    with TemporaryDirectory() as tmp:
        repo = Path(tmp)
        dated = repo / "artifacts" / "statement_gain_loss" / "2026-06-30" / "STATEMENT_GAIN_LOSS_2026-06-30.json"
        _write_statement_artifact_payload(dated)
        history = repo / "artifacts" / "statement_gain_loss" / "history" / "statement_gain_loss_index.json"
        history.parent.mkdir(parents=True, exist_ok=True)
        history.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "statement_date": "2026-06-30",
                            "json_artifact_path": str(dated),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        payload = _fetch_json(
            "/api/statement-gain-loss/latest",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", repo)],
        )

    assert payload["status"] == "available"
    assert payload["statement_date"] == "2026-06-30"
    assert payload["source_provenance_summary"]["provenance_types"] == ["pdf-text-extracted"]
    assert payload["scoring_impact"] == "none"


def test_non_statement_route_behavior_unchanged_operator_tax_state() -> None:
    with TemporaryDirectory() as tmp:
        payload = _fetch_json(
            "/api/operator/tax-state",
            patchers=[patch("scripts.run_outcome_ui._REPO_ROOT", Path(tmp))],
        )

    assert payload == {}


def test_statement_pipeline_reports_no_scoring_impact() -> None:
    snap = _snapshot()
    assert snap.scoring_impact == "none"
    source = inspect.getsource(sgl)
    assert "src.scoring" not in source


def _write_minimal_statement(path: Path, account_line: str, ending: str, net_realized: str) -> None:
    path.write_text(
        "Statement period: 2026-06-01 to 2026-06-30\n"
        f"{account_line}\n"
        f"Ending Account Value: {ending}\n"
        f"YTD net realized gain/loss: {net_realized}\n",
        encoding="utf-8",
    )


def test_incoming_grouping_writes_date_keyed_artifacts_and_latest_pointer() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        incoming = root / "incoming"
        output = root / "artifacts"
        raw_archive = root / "raw"
        incoming.mkdir(parents=True, exist_ok=True)

        _write_minimal_statement(
            incoming / "Statement06302026_A.txt",
            "Account X20-548022, Individual TOD",
            "$4.61",
            "-$54,198.02",
        )
        _write_minimal_statement(
            incoming / "Statement06302026_B.txt",
            "Account Z35-123695, Individual TOD",
            "$488,624.46",
            "$14,409.78",
        )

        rc = ingest_main(
            [
                "--incoming-dir",
                str(incoming),
                "--output-root",
                str(output),
                "--raw-archive-root",
                str(raw_archive),
            ]
        )
        assert rc == 0

        dated_json = output / "2026-06-30" / "STATEMENT_GAIN_LOSS_2026-06-30.json"
        dated_md = output / "2026-06-30" / "STATEMENT_GAIN_LOSS_2026-06-30.md"
        latest_json = output / "latest.json"
        latest_md = output / "latest.md"
        history = output / "history" / "statement_gain_loss_index.json"

        assert dated_json.exists()
        assert dated_md.exists()
        assert latest_json.exists()
        assert latest_md.exists()
        assert history.exists()

        payload = json.loads(dated_json.read_text(encoding="utf-8"))
        assert payload["statement_date"] == "2026-06-30"
        assert len(payload["accounts"]) == 2
        assert "source_provenance" in payload
        assert sorted(item["source_provenance"] for item in payload["source_provenance"]) == [
            "manual-text-extract",
            "manual-text-extract",
        ]

        history_payload = json.loads(history.read_text(encoding="utf-8"))
        assert len(history_payload["entries"]) == 1
        assert history_payload["entries"][0]["statement_date"] == "2026-06-30"
        assert len(history_payload["entries"][0]["source_provenance"]) == 2


def test_history_index_upsert_is_idempotent_for_same_statement_date() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        incoming = root / "incoming"
        output = root / "artifacts"
        raw_archive = root / "raw"
        incoming.mkdir(parents=True, exist_ok=True)

        statement_a = incoming / "Statement06302026_A.txt"
        _write_minimal_statement(
            statement_a,
            "Account X20-548022, Individual TOD",
            "$4.61",
            "-$54,198.02",
        )

        rc1 = ingest_main(
            [
                "--incoming-dir",
                str(incoming),
                "--output-root",
                str(output),
                "--raw-archive-root",
                str(raw_archive),
            ]
        )
        assert rc1 == 0

        # Update source and ingest again for same statement date.
        _write_minimal_statement(
            statement_a,
            "Account X20-548022, Individual TOD",
            "$10.00",
            "-$54,198.02",
        )
        rc2 = ingest_main(
            [
                "--incoming-dir",
                str(incoming),
                "--output-root",
                str(output),
                "--raw-archive-root",
                str(raw_archive),
            ]
        )
        assert rc2 == 0

        history = output / "history" / "statement_gain_loss_index.json"
        history_payload = json.loads(history.read_text(encoding="utf-8"))
        assert len(history_payload["entries"]) == 1
        assert history_payload["entries"][0]["statement_date"] == "2026-06-30"


def test_dry_run_reports_but_writes_nothing() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        incoming = root / "incoming"
        output = root / "artifacts"
        raw_archive = root / "raw"
        incoming.mkdir(parents=True, exist_ok=True)

        _write_minimal_statement(
            incoming / "Statement06302026_A.txt",
            "Account X20-548022, Individual TOD",
            "$4.61",
            "-$54,198.02",
        )

        rc = ingest_main(
            [
                "--incoming-dir",
                str(incoming),
                "--output-root",
                str(output),
                "--raw-archive-root",
                str(raw_archive),
                "--dry-run",
            ]
        )
        assert rc == 0
        assert not output.exists()
        assert not raw_archive.exists()


def test_raw_archive_default_is_copy_not_move() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        incoming = root / "incoming"
        output = root / "artifacts"
        raw_archive = root / "raw"
        incoming.mkdir(parents=True, exist_ok=True)

        source = incoming / "Statement06302026_A.txt"
        _write_minimal_statement(
            source,
            "Account X20-548022, Individual TOD",
            "$4.61",
            "-$54,198.02",
        )

        rc = ingest_main(
            [
                "--incoming-dir",
                str(incoming),
                "--output-root",
                str(output),
                "--raw-archive-root",
                str(raw_archive),
            ]
        )
        assert rc == 0
        assert source.exists()
        assert (raw_archive / "2026-06-30" / source.name).exists()
