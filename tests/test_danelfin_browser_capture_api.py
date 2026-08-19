from __future__ import annotations

import csv
import json
import socket
import threading
import urllib.error
import urllib.request
import urllib.parse
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
    with run_outcome_ui._danelfin_diag_lock:
        run_outcome_ui._danelfin_diag_runs.clear()
    with run_outcome_ui._danelfin_prod_lock:
        run_outcome_ui._danelfin_prod_runs.clear()
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
    assert body["canonical_persistence_called"] is False

    rows = {row["symbol"]: row for row in body["captured_rows"]}
    assert rows["MSFT"]["danelfin_raw"] == "3"
    assert rows["MSFT"]["danelfin_score"] == "1.5000"
    assert rows["NVDA"]["danelfin_raw"] == "8"
    assert rows["NVDA"]["danelfin_score"] == "4.0000"

    assert body["latest_path"] is None
    assert body["provenance_path"] is None


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
    assert body["canonical_persistence_called"] is True
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


def test_browser_capture_diagnostic_queue_endpoint_emits_one_job(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue?symbol=NVDA",
            timeout=10,
        ) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert body["status"] == "ok"
    assert body["diagnostic"] is True
    assert body["dry_run"] is True
    assert body["job_count"] == 1
    assert body["symbols"] == ["NVDA"]
    job = body["jobs"][0]
    assert job["kind"] == "pair"
    assert job["symbols"][0] == "NVDA"
    assert job["dry_run"] is True
    assert job["diagnostic"] is True
    assert job["diagnostic_run_id"] == body["diagnostic_run_id"]


def test_diagnostic_pending_queue_reuses_prepared_run_without_creating_second_run(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue?symbol=NVDA&pair_symbol=ANIP",
            timeout=10,
        ) as resp:
            prepared = json.loads(resp.read().decode("utf-8"))

        prepared_run_id = str(prepared["diagnostic_run_id"])

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue/pending?symbol=NVDA",
            timeout=10,
        ) as resp:
            pending = json.loads(resp.read().decode("utf-8"))

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue/pending?id={urllib.parse.quote(prepared_run_id, safe='')}",
            timeout=10,
        ) as resp:
            pending_by_id = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert pending["status"] == "ok"
    assert pending["diagnostic"] is True
    assert pending["dry_run"] is True
    assert pending["job_count"] == 1
    assert pending["diagnostic_run_id"] == prepared_run_id
    assert pending["jobs"][0]["diagnostic_run_id"] == prepared_run_id
    assert pending_by_id["diagnostic_run_id"] == prepared_run_id

    with run_outcome_ui._danelfin_diag_lock:
        run_ids = list(run_outcome_ui._danelfin_diag_runs.keys())
    assert run_ids == [prepared_run_id]


def test_diagnostic_claim_is_atomic_and_prevents_double_claim(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue?symbol=NVDA&pair_symbol=ANIP",
            timeout=10,
        ) as resp:
            prepared = json.loads(resp.read().decode("utf-8"))

        run_id = str(prepared["diagnostic_run_id"])

        status_code, first_claim = _post_json(
            port,
            "/api/danelfin/browser-capture/diagnostic-queue/claim",
            {
                "diagnostic_run_id": run_id,
                "worker_id": "extension-worker-1",
            },
        )
        status_code_second, second_claim = _post_json(
            port,
            "/api/danelfin/browser-capture/diagnostic-queue/claim",
            {
                "diagnostic_run_id": run_id,
                "worker_id": "extension-worker-2",
            },
        )

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue/pending?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            pending_after_claim = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 200
    assert first_claim["status"] == "ok"
    assert first_claim["job_count"] == 1
    assert first_claim["diagnostic_run_id"] == run_id
    assert first_claim["jobs"][0]["diagnostic_run_id"] == run_id

    assert status_code_second == 200
    assert second_claim["status"] == "ok"
    assert second_claim["job_count"] == 0
    assert second_claim["diagnostic_run_id"] == run_id
    assert second_claim["jobs"] == []

    assert pending_after_claim["status"] == "ok"
    assert pending_after_claim["job_count"] == 0
    assert pending_after_claim["jobs"] == []


def test_diagnostic_pending_poll_does_not_claim_or_transition_state(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue?symbol=NVDA&pair_symbol=ANIP",
            timeout=10,
        ) as resp:
            prepared = json.loads(resp.read().decode("utf-8"))

        run_id = str(prepared["diagnostic_run_id"])

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue/pending?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            first_poll = json.loads(resp.read().decode("utf-8"))

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue/pending?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            second_poll = json.loads(resp.read().decode("utf-8"))

        with run_outcome_ui._danelfin_diag_lock:
            state = dict(run_outcome_ui._danelfin_diag_runs[run_id])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert first_poll["status"] == "ok"
    assert first_poll["job_count"] == 1
    assert second_poll["status"] == "ok"
    assert second_poll["job_count"] == 1
    assert first_poll["diagnostic_run_id"] == run_id
    assert second_poll["diagnostic_run_id"] == run_id

    assert state["state"] == "PREPARED"
    assert state["claimed_at"] is None
    assert state["worker_claimed"] is None


def test_diagnostic_run_attribution_events_and_capture_update_prepared_run(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue?symbol=NVDA&pair_symbol=ANIP",
            timeout=10,
        ) as resp:
            prepared = json.loads(resp.read().decode("utf-8"))
        run_id = str(prepared["diagnostic_run_id"])

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue/pending?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            fetched = json.loads(resp.read().decode("utf-8"))

        assert fetched["job_count"] == 1
        assert fetched["diagnostic_run_id"] == run_id

        for event in [
            "worker_started",
            "worker_claimed",
            "navigation_started",
            "navigation_completed",
            "capture_started",
            "capture_completed",
        ]:
            status_code, _ = _post_json(
                port,
                "/api/danelfin/browser-capture/diagnostic-status",
                {
                    "diagnostic_run_id": run_id,
                    "event": event,
                    "url": "https://danelfin.com/stocks/nvda-vs-anip",
                },
            )
            assert status_code == 200

        status_code, capture_body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": True,
                "diagnostic_run_id": run_id,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "operator_source": "PAIR_PAGE",
                "observations": [
                    {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
                    {"symbol": "ANIP", "danelfin_raw": 6, "sourced_date": "2026-08-15"},
                ],
            },
        )

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-status?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            status_body = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 200
    assert capture_body["diagnostic_run_id"] == run_id
    assert capture_body["dry_run"] is True
    assert capture_body["canonical_persistence_called"] is False

    diag = status_body["diagnostic"]
    assert diag["diagnostic_run_id"] == run_id
    assert diag["worker_started"]
    assert diag["worker_claimed"]
    assert diag["navigation_started"]
    assert diag["navigation_completed"]
    assert diag["capture_started"]
    assert diag["capture_completed"]
    assert diag["result_received"]
    assert diag["normalized"]
    assert diag["validation_passed"]

    with run_outcome_ui._danelfin_diag_lock:
        run_ids = list(run_outcome_ui._danelfin_diag_runs.keys())
    assert run_ids == [run_id]


def test_browser_capture_dry_run_never_calls_canonical_persistence(isolated_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def _should_not_run(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("canonical persistence should not be called in dry_run")

    monkeypatch.setattr(
        "src.scoring.danelfin_manual_import.import_manual_danelfin_observations",
        _should_not_run,
    )

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
                ],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert body["dry_run"] is True
    assert body["canonical_persistence_called"] is False
    assert called["value"] is False


def test_browser_capture_diagnostic_run_id_survives_and_updates_status(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue?symbol=NVDA",
            timeout=10,
        ) as resp:
            queue_body = json.loads(resp.read().decode("utf-8"))

        run_id = str(queue_body["diagnostic_run_id"])
        status_code, capture_body = _post_json(
            port,
            "/api/danelfin/browser-capture",
            {
                "dry_run": True,
                "diagnostic_run_id": run_id,
                "acquisition_method": "BROWSER_CAPTURE_DANELFIN_UI",
                "operator_source": "PAIR_PAGE",
                "observations": [
                    {"symbol": "NVDA", "danelfin_raw": 8, "sourced_date": "2026-08-15"},
                ],
            },
        )

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-status?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            status_body = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 200
    assert capture_body["diagnostic_run_id"] == run_id
    diag = status_body["diagnostic"]
    assert status_body["status"] == "ok"
    assert diag["result_received"]
    assert diag["normalized"]
    assert diag["validation_passed"]


def test_browser_capture_diagnostic_status_records_terminal_error(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/diagnostic-queue?symbol=NVDA",
            timeout=10,
        ) as resp:
            queue_body = json.loads(resp.read().decode("utf-8"))

        run_id = str(queue_body["diagnostic_run_id"])
        status, body = _post_json(
            port,
            "/api/danelfin/browser-capture/diagnostic-status",
            {
                "diagnostic_run_id": run_id,
                "event": "error",
                "error": "simulated worker failure",
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert body["status"] == "ok"
    assert body["diagnostic"]["error"]["message"] == "simulated worker failure"


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


def test_production_prepare_pending_and_claim_contract(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        status_prepare, prepared = _post_json(
            port,
            "/api/danelfin/browser-capture/production-queue/prepare",
            {"symbols": ["NVDA", "ANIP"], "source": "pytest"},
        )
        run_id = str(prepared["run_id"])

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/production-queue/pending?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            pending = json.loads(resp.read().decode("utf-8"))

        status_claim, claim = _post_json(
            port,
            "/api/danelfin/browser-capture/production-queue/claim",
            {"run_id": run_id, "worker_id": "extension-worker-1"},
        )
        status_claim_2, claim_second = _post_json(
            port,
            "/api/danelfin/browser-capture/production-queue/claim",
            {"run_id": run_id, "worker_id": "extension-worker-2"},
        )

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/production-status?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            status_payload = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_prepare == 200
    assert prepared["status"] == "ok"
    assert prepared["mode"] == "production"
    assert prepared["dry_run"] is False
    assert prepared["job_count"] == 1
    assert prepared["jobs"][0]["mode"] == "production"
    assert prepared["jobs"][0]["dry_run"] is False

    assert pending["status"] == "ok"
    assert pending["run_id"] == run_id
    assert pending["job_count"] == 1

    assert status_claim == 200
    assert claim["status"] == "ok"
    assert claim["run_id"] == run_id
    assert claim["job_count"] == 1

    assert status_claim_2 == 200
    assert claim_second["status"] == "ok"
    assert claim_second["job_count"] == 0

    run_state = status_payload["run"]
    assert run_state["run_id"] == run_id
    assert run_state["claimed_at"] is not None
    assert run_state["state"] == "RUNNING"


def test_production_status_tracks_terminal_error_event(isolated_repo: Path) -> None:
    server, thread, port = _start_server()
    try:
        _, prepared = _post_json(
            port,
            "/api/danelfin/browser-capture/production-queue/prepare",
            {"symbols": ["NVDA"], "source": "pytest"},
        )
        run_id = str(prepared["run_id"])

        status_event, _ = _post_json(
            port,
            "/api/danelfin/browser-capture/production-status",
            {"run_id": run_id, "event": "error", "error": "simulated timeout"},
        )

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/danelfin/browser-capture/production-status?id={urllib.parse.quote(run_id, safe='')}",
            timeout=10,
        ) as resp:
            status_payload = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_event == 200
    run_state = status_payload["run"]
    assert run_state["state"] == "ERROR"
    assert run_state["error"]["message"] == "simulated timeout"
