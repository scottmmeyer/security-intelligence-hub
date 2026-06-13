from __future__ import annotations

import csv
from dataclasses import replace
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pis.ingestion import ingest_portfolio_history, ingest_portfolio_history_file
from src.pis.service import PortfolioRegistrationResult, register_portfolio_snapshot_from_sih
from src.pis.storage import append_portfolio_history, build_portfolio_history_storage_paths
from src.portfolio.ingestion import ingest_portfolio
from src.portfolio.runner import _register_pis_snapshot_best_effort, run_analysis


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_pis_ingestion_creates_account_level_snapshots_and_cash_allocation() -> None:
    snapshots, positions, warnings = ingest_portfolio_history_file(
        Path("incoming/portfolio/Portfolio_Positions_May-29-2026.csv"),
        snapshot_date="2026-05-29",
    )

    assert len(snapshots) == 3
    assert {snapshot.account_id for snapshot in snapshots} == {"X20548022", "Z26346415", "Z35123695"}
    assert any(snapshot.cash_value > 0 for snapshot in snapshots)
    assert any(position.is_cash_equivalent for position in positions)
    assert any("zero-value position" in warning for warning in warnings)


def test_pis_ingestion_flags_duplicate_rows_and_zero_value_positions() -> None:
    content = """Account Number,Account Name,Symbol,Description,Quantity,Last Price,Current Value,Percent Of Account,Cost Basis Total,Type
123,Sample Account,SPAXX**,HELD IN MONEY MARKET,,,$100.00,50.00,,Cash,
123,Sample Account,ABC,ABC CORP,10,$10.00,$100.00,50.00,$80.00,Cash,
123,Sample Account,ABC,ABC CORP,0,$10.00,$0.00,0.00,$0.00,Cash,
"""

    snapshots, positions, warnings = ingest_portfolio_history(content, "sample.csv", "2026-05-29")

    assert len(snapshots) == 1
    assert len(positions) == 3
    assert any("duplicate symbol 'ABC'" in warning for warning in warnings)
    assert any("zero-value position 'ABC'" in warning for warning in warnings)


def test_pis_storage_is_append_only_and_idempotent(tmp_path: Path) -> None:
    snapshots, positions, _ = ingest_portfolio_history_file(
        Path("incoming/portfolio/Portfolio_Positions_May-29-2026.csv"),
        snapshot_date="2026-05-29",
    )
    snapshot = next(item for item in snapshots if item.account_id == "Z35123695")
    account_positions = [item for item in positions if item.snapshot_id == snapshot.snapshot_id]

    history_root = tmp_path / "data" / "history" / "pis"
    index_path = tmp_path / "data" / "history" / "pis_snapshot_index.csv"

    written_count = append_portfolio_history(
        snapshot=snapshot,
        positions=account_positions,
        history_root=history_root,
        index_path=index_path,
    )
    assert written_count == len(account_positions)

    storage_paths = build_portfolio_history_storage_paths(
        snapshot_date=snapshot.snapshot_date.isoformat(),
        account_id=snapshot.account_id,
        snapshot_id=snapshot.snapshot_id,
        history_root=history_root,
        index_path=index_path,
    )
    assert storage_paths.partition_dir.exists()
    assert len(_read_rows(storage_paths.snapshot_path)) == 1
    assert len(_read_rows(storage_paths.positions_path)) == len(account_positions)

    written_count_again = append_portfolio_history(
        snapshot=snapshot,
        positions=account_positions,
        history_root=history_root,
        index_path=index_path,
    )
    assert written_count_again == len(account_positions)
    assert len(_read_rows(index_path)) == 1


def test_pis_storage_rejects_mismatched_content_for_existing_partition(tmp_path: Path) -> None:
    snapshots, positions, _ = ingest_portfolio_history_file(
        Path("incoming/portfolio/Portfolio_Positions_May-29-2026.csv"),
        snapshot_date="2026-05-29",
    )
    snapshot = next(item for item in snapshots if item.account_id == "Z35123695")
    account_positions = [item for item in positions if item.snapshot_id == snapshot.snapshot_id]

    history_root = tmp_path / "data" / "history" / "pis"
    index_path = tmp_path / "data" / "history" / "pis_snapshot_index.csv"

    append_portfolio_history(
        snapshot=snapshot,
        positions=account_positions,
        history_root=history_root,
        index_path=index_path,
    )

    mutated_snapshot = replace(snapshot, portfolio_value=snapshot.portfolio_value + 1.0)

    with pytest.raises(ValueError, match="Immutable PIS partition protection"):
        append_portfolio_history(
            snapshot=mutated_snapshot,
            positions=account_positions,
            history_root=history_root,
            index_path=index_path,
        )


def test_pis_registration_uses_canonical_sih_portfolio_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    content = Path("incoming/portfolio/Portfolio_Positions_May-29-2026.csv").read_text(encoding="utf-8")
    sih_snapshot, sih_holdings = ingest_portfolio(content, "Portfolio_Positions_May-29-2026.csv", "2026-05-29")
    sih_snapshot = replace(sih_snapshot, ingestion_status="ACCEPTED", normalization_warnings=())

    captured: dict[str, object] = {}

    def fake_append_portfolio_history(*, snapshot, positions, history_root, index_path):
        captured["snapshot"] = snapshot
        captured["positions"] = list(positions)
        captured["history_root"] = history_root
        captured["index_path"] = index_path
        return len(list(positions))

    monkeypatch.setattr("src.pis.service.append_portfolio_history", fake_append_portfolio_history)

    result = register_portfolio_snapshot_from_sih(
        snapshot=sih_snapshot,
        holdings=sih_holdings,
        history_root=str(tmp_path / "data" / "history" / "pis"),
        index_path=str(tmp_path / "data" / "history" / "pis_snapshot_index.csv"),
    )

    assert result.registered is True
    assert captured["snapshot"].snapshot_id == sih_snapshot.portfolio_snapshot_id
    assert captured["snapshot"].account_name == sih_snapshot.account_name
    assert len(captured["positions"]) == len(sih_holdings)


def test_duplicate_registration_is_suppressed(tmp_path: Path) -> None:
    content = Path("incoming/portfolio/Portfolio_Positions_May-29-2026.csv").read_text(encoding="utf-8")
    sih_snapshot, sih_holdings = ingest_portfolio(content, "Portfolio_Positions_May-29-2026.csv", "2026-05-29")
    sih_snapshot = replace(sih_snapshot, ingestion_status="ACCEPTED", normalization_warnings=())
    history_root = tmp_path / "data" / "history" / "pis"
    index_path = tmp_path / "data" / "history" / "pis_snapshot_index.csv"

    first = register_portfolio_snapshot_from_sih(
        snapshot=sih_snapshot,
        holdings=sih_holdings,
        history_root=str(history_root),
        index_path=str(index_path),
    )
    second = register_portfolio_snapshot_from_sih(
        snapshot=sih_snapshot,
        holdings=sih_holdings,
        history_root=str(history_root),
        index_path=str(index_path),
    )

    assert first.registered is True
    assert second.registered is False
    assert second.duplicate is True


def test_pis_best_effort_helper_registers_and_survives_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    content = Path("incoming/portfolio/Portfolio_Positions_May-29-2026.csv").read_text(encoding="utf-8")
    sih_snapshot, sih_holdings = ingest_portfolio(content, "Portfolio_Positions_May-29-2026.csv", "2026-05-29")
    clean_snapshot = replace(sih_snapshot, ingestion_status="ACCEPTED", normalization_warnings=())

    captured: dict[str, object] = {}

    def fake_register_portfolio_snapshot_from_sih(*, snapshot, holdings, history_root="data/history/pis", index_path="data/history/pis/pis_snapshot_index.csv"):
        captured["snapshot"] = snapshot
        captured["holdings"] = list(holdings)
        return PortfolioRegistrationResult(
            snapshot_id=snapshot.portfolio_snapshot_id,
            registered=True,
            duplicate=False,
            position_count=len(captured["holdings"]),
            warning="",
        )

    monkeypatch.setattr("src.pis.service.register_portfolio_snapshot_from_sih", fake_register_portfolio_snapshot_from_sih)

    registration, warnings = _register_pis_snapshot_best_effort(snapshot=clean_snapshot, raw_holdings=sih_holdings)

    assert registration["status"] == "REGISTERED"
    assert captured["snapshot"].portfolio_snapshot_id == clean_snapshot.portfolio_snapshot_id
    assert len(captured["holdings"]) == len(sih_holdings)
    assert warnings == []

    def failing_register(*args, **kwargs):
        raise RuntimeError("PIS unavailable")

    monkeypatch.setattr("src.pis.service.register_portfolio_snapshot_from_sih", failing_register)

    registration_failed, warnings_failed = _register_pis_snapshot_best_effort(snapshot=clean_snapshot, raw_holdings=sih_holdings)

    assert registration_failed["status"] == "FAILED"
    assert any("PIS_SNAPSHOT_REGISTRATION_FAILED" in warning for warning in warnings_failed)


def test_failed_parse_creates_no_pis_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def fake_register(*args, **kwargs):
        called["value"] = True
        return None

    monkeypatch.setattr("src.pis.service.register_portfolio_snapshot_from_sih", fake_register)
    result = run_analysis("bad,data\n1,2\n", "broken.csv", "2026-05-29")

    assert result["status"] == "REJECTED"
    assert called["value"] is False
