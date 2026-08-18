from __future__ import annotations

import csv
import json
import socket
import threading
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

import pytest

import scripts.run_outcome_ui as run_outcome_ui


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server() -> tuple[object, threading.Thread, int]:
    port = _free_port()
    server = run_outcome_ui._ThreadingTCPServer(("127.0.0.1", port), run_outcome_ui._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, port


def _post_json(port: int, path: str, payload: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": "chrome-extension://test-extension"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "danelfin_raw", "danelfin_score", "sourced_date"])
        writer.writeheader()
        writer.writerows(rows)


def _write_holdings_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["symbol", "asset_class", "security_type", "operational_state"],
        )
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture()
def isolated_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    signals_dir = repo / "data" / "signals" / "danelfin"
    _write_csv(
        signals_dir / "latest_danelfin.csv",
        [
            {"symbol": "MSFT", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-17"},
            {"symbol": "NVDA", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-17"},
        ],
    )
    (signals_dir / "latest_danelfin.provenance.json").write_text('{"symbols": {}}', encoding="utf-8")

    monkeypatch.setattr(run_outcome_ui, "_REPO_ROOT", repo)
    monkeypatch.setitem(run_outcome_ui._SIGNAL_FILES, "danelfin", signals_dir / "latest_danelfin.csv")
    return repo


def test_browser_capture_endpoint_accepts_two_observations_dry_run(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": True,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "operator_source": "PAIR_PAGE",
                "observations": [
                    {"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"},
                    {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
                ],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert body["status"] == "ok"
    assert body["dry_run"] is True
    assert body["applied_count"] == 2
    assert body["operator_source"] == "PAIR_PAGE"
    assert body["acquisition_method"] == "BROWSER_CAPTURE_DANELFIN_UI"

    rows = {row["symbol"]: row for row in body["captured_rows"]}
    assert rows["MSFT"]["danelfin_raw"] == "3"
    assert rows["MSFT"]["danelfin_score"] == "1.5000"
    assert rows["NVDA"]["danelfin_raw"] == "8"
    assert rows["NVDA"]["danelfin_score"] == "4.0000"

    latest_path = Path(body["latest_path"])
    assert latest_path.exists()
    with latest_path.open("r", encoding="utf-8", newline="") as handle:
        file_rows = {row["symbol"]: row for row in csv.DictReader(handle)}
    assert file_rows["MSFT"]["danelfin_score"] == "1.5000"
    assert file_rows["NVDA"]["danelfin_score"] == "4.0000"

    provenance_path = Path(body["provenance_path"])
    assert provenance_path.exists()
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["symbols"]["MSFT"]["acquisition_method"] == "BROWSER_CAPTURE_DANELFIN_UI"
    assert provenance["symbols"]["MSFT"]["operator_source"] == "PAIR_PAGE"


def test_browser_capture_endpoint_accepts_production_mode_and_writes_canonical_cache(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": False,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "operator_source": "PAIR_PAGE",
                "observations": [
                    {"symbol": "MU", "danelfin_raw": 4, "sourced_date": "2026-08-16"},
                    {"symbol": "VRT", "danelfin_raw": 7, "sourced_date": "2026-08-16"},
                ],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert body["dry_run"] is False
    assert Path(body["latest_path"]).resolve() == (isolated_repo / "data" / "signals" / "danelfin" / "latest_danelfin.csv").resolve()
    assert body["applied_count"] == 2

    latest_text = (isolated_repo / "data" / "signals" / "danelfin" / "latest_danelfin.csv").read_text(encoding="utf-8")
    assert "MU,4,2.0000,2026-08-16" in latest_text
    assert "VRT,7,3.5000,2026-08-16" in latest_text

    prov = json.loads((isolated_repo / "data" / "signals" / "danelfin" / "latest_danelfin.provenance.json").read_text(encoding="utf-8"))
    assert prov["symbols"]["MU"]["acquisition_method"] == "BROWSER_CAPTURE_DANELFIN_UI"
    assert prov["symbols"]["MU"]["operator_source"] == "PAIR_PAGE"
    assert prov["symbols"]["VRT"]["acquisition_method"] == "BROWSER_CAPTURE_DANELFIN_UI"
    assert prov["symbols"]["VRT"]["operator_source"] == "PAIR_PAGE"


def test_browser_capture_endpoint_rejects_malformed_score(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": True,
                "observations": [{"symbol": "MSFT", "danelfin_raw": 11, "sourced_date": "2026-08-15"}],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 422
    assert "between 1 and 10" in body["error"]


def test_browser_capture_endpoint_rejects_duplicate_symbol(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": True,
                "observations": [
                    {"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"},
                    {"symbol": "MSFT", "danelfin_raw": 4, "sourced_date": "2026-08-15"},
                ],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 422
    assert "duplicate symbol" in body["error"]


def test_browser_capture_endpoint_rejects_invalid_date(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": True,
                "observations": [{"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "not-a-date"}],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 422
    assert "Invalid Danelfin source date" in body["error"]


def test_browser_capture_dry_run_does_not_modify_production_cache(isolated_repo: Path) -> None:
    prod_latest = isolated_repo / "data" / "signals" / "danelfin" / "latest_danelfin.csv"
    before = prod_latest.read_text(encoding="utf-8") if prod_latest.exists() else ""

    server, thread, port = _start_server()
    try:
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": True,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "operator_source": "PAIR_PAGE",
                "observations": [
                    {"symbol": "MSFT", "danelfin_raw": 3, "sourced_date": "2026-08-15"},
                    {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
                ],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    after = prod_latest.read_text(encoding="utf-8") if prod_latest.exists() else ""
    assert status == 200
    assert body["dry_run"] is True
    assert before == after


def test_browser_capture_production_mode_does_not_trigger_analyze_side_effects(isolated_repo: Path) -> None:
    analysis_runs_dir = isolated_repo / "data" / "portfolio_ingestion" / "analysis_runs"
    assert not analysis_runs_dir.exists()

    server, thread, port = _start_server()
    try:
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": False,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "operator_source": "PAIR_PAGE",
                "observations": [
                    {"symbol": "MU", "danelfin_raw": 4, "sourced_date": "2026-08-16"},
                    {"symbol": "VRT", "danelfin_raw": 7, "sourced_date": "2026-08-16"},
                ],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert body["dry_run"] is False
    assert not analysis_runs_dir.exists()


def test_danelfin_capture_queue_endpoint_builds_deterministic_jobs(isolated_repo: Path) -> None:
    analysis_runs_dir = isolated_repo / "data" / "portfolio_ingestion" / "analysis_runs"
    base_universe = isolated_repo / "data" / "current" / "base_equity_universe.csv"
    _write_holdings_csv(
        analysis_runs_dir / "PAR-20260817-TESTQUEUE" / "holdings.csv",
        [
            {"symbol": "AAA", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "BBB", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "CCC", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "DDD", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "EEE", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "CCC", "asset_class": "EQUITIES", "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION"},
        ],
    )
    base_universe.parent.mkdir(parents=True, exist_ok=True)
    base_universe.write_text(
        "symbol,starmine_ess_text,starmine_ess_raw_score\nAAA,BULLISH,8.5\nBBB,BULLISH,8.5\nCCC,BULLISH,8.5\nDDD,BULLISH,8.5\nEEE,BULLISH,8.5\n",
        encoding="utf-8",
    )
    _write_csv(
        isolated_repo / "data" / "signals" / "danelfin" / "latest_danelfin.csv",
        [
            {"symbol": "AAA", "danelfin_raw": "9", "danelfin_score": "4.5000", "sourced_date": "2026-08-18"},
            {"symbol": "BBB", "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": "2026-08-18"},
            {"symbol": "CCC", "danelfin_raw": "5", "danelfin_score": "2.5000", "sourced_date": "2026-08-13"},
            {"symbol": "EEE", "danelfin_raw": "", "danelfin_score": "", "sourced_date": "2026-08-18"},
        ],
    )

    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/danelfin/browser-capture/queue", timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert body["status"] == "ok"
    assert body["provider"] == "danelfin"
    assert body["symbols"] == ["CCC", "DDD", "EEE"]
    assert body["symbol_count"] == 3
    assert body["job_count"] == 2
    assert body["pair_count"] == 1
    assert body["single_count"] == 1

    jobs = body["jobs"]
    assert jobs[0]["kind"] == "pair"
    assert jobs[0]["symbols"] == ["CCC", "DDD"]
    assert jobs[0]["operator_source"] == "PAIR_PAGE"
    assert jobs[0]["url"] == "https://danelfin.com/stocks/ccc-vs-ddd"
    assert jobs[1]["kind"] == "single"
    assert jobs[1]["symbols"] == ["EEE"]
    assert jobs[1]["operator_source"] == "STOCK_PAGE"
    assert jobs[1]["url"] == "https://danelfin.com/stock/eee"
