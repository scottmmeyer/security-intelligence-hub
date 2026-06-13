from __future__ import annotations

import csv
from pathlib import Path

from src.pis.storage import (
    pis_latest_snapshot_summary,
    pis_snapshot_history_health,
    pis_snapshot_inventory,
    pis_value_timeline,
)


_PASS_ACCOUNT_NAME = "General Brokerage, Joint WROS - TOD, Individual - TOD"


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _index_headers() -> list[str]:
    return [
        "snapshot_id",
        "snapshot_date",
        "account_id",
        "account_name",
        "position_count",
        "portfolio_value",
        "cash_value",
        "positions_path",
        "source_file",
        "created_at_utc",
    ]


def test_snapshot_inventory_loads(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PIS-1",
                "snapshot_date": "2026-05-21",
                "account_id": "A1",
                "account_name": _PASS_ACCOUNT_NAME,
                "position_count": "3",
                "portfolio_value": "1000",
                "cash_value": "100",
                "positions_path": "data/history/pis/pis_positions.csv",
                "source_file": "holdings.csv",
                "created_at_utc": "2026-05-21T12:00:00+00:00",
            }
        ],
    )

    rows = pis_snapshot_inventory(index_path=index_path)
    assert len(rows) == 1
    assert rows[0]["snapshot_id"] == "PIS-1"
    assert rows[0]["market_value"] == 1000.0


def test_latest_summary_loads(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    positions_path = tmp_path / "positions.csv"
    _write_csv(
        positions_path,
        ["symbol", "market_value"],
        [
            {"symbol": "MSFT", "market_value": "400"},
            {"symbol": "AAPL", "market_value": "300"},
            {"symbol": "CASH", "market_value": "200"},
        ],
    )
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PIS-2",
                "snapshot_date": "2026-05-22",
                "account_id": "A1",
                "account_name": _PASS_ACCOUNT_NAME,
                "position_count": "2",
                "portfolio_value": "700",
                "cash_value": "200",
                "positions_path": str(positions_path),
                "source_file": "holdings2.csv",
                "created_at_utc": "2026-05-22T12:00:00+00:00",
            }
        ],
    )

    latest = pis_latest_snapshot_summary(index_path=index_path, repo_root=tmp_path)
    assert latest["snapshot_date"] == "2026-05-22"
    assert latest["total_value"] == 700.0
    assert latest["cash"] == 200.0
    assert latest["largest_holdings"][0]["symbol"] == "MSFT"


def test_timeline_computes_change_vs_prior(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PIS-1",
                "snapshot_date": "2026-05-21",
                "account_id": "A1",
                "account_name": _PASS_ACCOUNT_NAME,
                "position_count": "3",
                "portfolio_value": "1000",
                "cash_value": "100",
                "positions_path": "x",
                "source_file": "a.csv",
                "created_at_utc": "2026-05-21T12:00:00+00:00",
            },
            {
                "snapshot_id": "PIS-2",
                "snapshot_date": "2026-05-22",
                "account_id": "A1",
                "account_name": _PASS_ACCOUNT_NAME,
                "position_count": "3",
                "portfolio_value": "1300",
                "cash_value": "120",
                "positions_path": "x",
                "source_file": "b.csv",
                "created_at_utc": "2026-05-22T12:00:00+00:00",
            },
        ],
    )

    timeline = pis_value_timeline(index_path=index_path)
    assert timeline[0]["snapshot_date"] == "2026-05-22"
    assert timeline[0]["change_vs_prior_snapshot"] == 300.0


def test_empty_state_graceful_defaults(tmp_path: Path) -> None:
    index_path = tmp_path / "missing.csv"

    assert pis_snapshot_inventory(index_path=index_path) == []
    assert pis_value_timeline(index_path=index_path) == []

    latest = pis_latest_snapshot_summary(index_path=index_path, repo_root=tmp_path)
    assert latest["snapshot_date"] == ""
    assert latest["largest_holdings"] == []

    health = pis_snapshot_history_health(index_path=index_path)
    assert health["snapshot_count"] == 0


def test_multiple_accounts_aggregate_in_timeline(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PIS-A",
                "snapshot_date": "2026-05-22",
                "account_id": "A1",
                "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
                "position_count": "2",
                "portfolio_value": "900",
                "cash_value": "80",
                "positions_path": "x",
                "source_file": "a.csv",
                "created_at_utc": "2026-05-22T12:00:00+00:00",
            },
            {
                "snapshot_id": "PIS-B",
                "snapshot_date": "2026-05-22",
                "account_id": "A2",
                "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
                "position_count": "4",
                "portfolio_value": "1100",
                "cash_value": "120",
                "positions_path": "x",
                "source_file": "b.csv",
                "created_at_utc": "2026-05-22T12:00:00+00:00",
            },
        ],
    )

    timeline = pis_value_timeline(index_path=index_path)
    assert timeline[0]["portfolio_value"] == 1100.0
    assert timeline[0]["positions"] == 4


def test_sih_pis_navigation_and_api_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]

    portfolio_html = (root / "ui" / "portfolio_alignment" / "index.html").read_text(encoding="utf-8")
    pis_html = (root / "ui" / "pis_dashboard" / "index.html").read_text(encoding="utf-8")
    pis_app = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert "/ui/pis_dashboard/" in portfolio_html
    assert "Security Intelligence Hub" in pis_html
    assert "/ui/portfolio_alignment/" in pis_html

    assert "/api/pis/summary" in pis_app
    assert "/api/pis/snapshots" in pis_app
    assert "/api/pis/latest" in pis_app
    assert "/api/pis/health" in pis_app
    assert "/api/pis/governance/latest" in pis_app
    assert "/api/pis/governance-summary" in pis_app
    assert "/api/pis/canonical/latest" in pis_app
    assert "/api/pis/canonical/history" in pis_app
    assert "/api/pis/canonical-summary" in pis_app
    assert "/api/pis/changes/latest" in pis_app
    assert "/api/pis/change-summary" in pis_app
    assert "/api/pis/lineage/latest" in pis_app
    assert "/api/pis/lineage-summary" in pis_app

    assert "Section 6: Snapshot Governance" in pis_html
    assert "governanceSummary" in pis_html
    assert "governanceTable" in pis_html
    assert "Section 7: Canonical Daily Portfolio State" in pis_html
    assert "canonicalSummary" in pis_html
    assert "canonicalTable" in pis_html

    assert "Change Detection Section 1" in pis_html
    assert "Change Detection Section 2" in pis_html
    assert "Change Detection Section 3" in pis_html
    assert "Change Detection Section 4" in pis_html
    assert "Change Detection Section 5" in pis_html
    assert "Change Detection Section 6" in pis_html
    assert "Lineage Section 1" in pis_html
    assert "Lineage Section 2" in pis_html
    assert "Lineage Section 3" in pis_html
    assert "Lineage Section 4" in pis_html


def test_dashboard_loading_shell_and_section_hooks_present() -> None:
    root = Path(__file__).resolve().parents[1]

    pis_html = (root / "ui" / "pis_dashboard" / "index.html").read_text(encoding="utf-8")

    assert "dashboardLoadingBanner" in pis_html
    assert "dashboardStatusPanel" in pis_html
    assert 'role="status"' in pis_html
    assert 'aria-live="polite"' in pis_html

    assert 'data-section-key="inventory"' in pis_html
    assert 'data-section-key="governance"' in pis_html
    assert 'data-section-key="canonical"' in pis_html
    assert 'data-section-key="lineageDetail"' in pis_html


def test_progressive_rendering_status_model_present_in_app() -> None:
    root = Path(__file__).resolve().parents[1]

    pis_app = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert 'const SLOW_THRESHOLD_MS = 5000;' in pis_app
    assert 'const STATUS_LOADING = "LOADING";' in pis_app
    assert 'const STATUS_LOADED = "LOADED";' in pis_app
    assert 'const STATUS_SLOW = "SLOW";' in pis_app
    assert 'const STATUS_FAILED = "FAILED";' in pis_app
    assert 'Portfolio Intelligence Dashboard' in pis_app
    assert 'Loading data...' in pis_app
    assert 'requestCache.set(path, loadJson(path));' in pis_app
    assert 'function runSectionTask(sectionKey, requestFactory, onSuccess)' in pis_app
    assert pis_app.count('runSectionTask(') >= 10


def test_lineage_loading_slow_and_failure_contract_present() -> None:
    root = Path(__file__).resolve().parents[1]

    pis_app = (root / "ui" / "pis_dashboard" / "app.js").read_text(encoding="utf-8")

    assert 'Loading lineage...' in pis_app
    assert 'Lineage data is taking longer than expected...' in pis_app
    assert 'Data unavailable' in pis_app
    assert 'Request timed out while waiting for the server.' in pis_app
    assert 'requestJson("/api/pis/lineage/latest")' in pis_app
    assert 'requestJson("/api/pis/lineage-summary")' in pis_app
    assert 'statuses.filter((status) => status === STATUS_LOADED || status === STATUS_FAILED).length' in pis_app
