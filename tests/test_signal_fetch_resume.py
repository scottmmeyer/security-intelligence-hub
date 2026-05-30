import csv
from datetime import date

import pytest

from src.scoring import fetch_danelfin_scores as danelfin_module
from src.scoring import fetch_yahoo_supplemental as yahoo_module
from src.scoring import fetch_zacks_scores as zacks_module


def _read_rows(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize(
    ("module", "fetch_attr", "fetcher_name", "expected_latest_name", "fake_impl", "value_field"),
    [
        (
            zacks_module,
            "fetch_zacks_data",
            "fetch_zacks_scores_for_symbols",
            "latest_zacks.csv",
            lambda symbol, delay_min=0, delay_max=0: (1.0, 5.0, 1.2, 123.0, 15.0),
            "zacks_rank",
        ),
        (
            yahoo_module,
            "fetch_yahoo_supplemental",
            "fetch_yahoo_supplemental_for_symbols",
            "latest_yahoo_supplemental.csv",
            lambda symbol: {
                "price_target": 101.0,
                "abr": 1.7,
                "eps_growth_5yr": 12.0,
                "current_price": 100.0,
            },
            "price_target",
        ),
        (
            danelfin_module,
            "fetch_danelfin_score",
            "fetch_danelfin_scores_for_symbols",
            "latest_danelfin.csv",
            lambda symbol: (8, 4.0),
            "danelfin_raw",
        ),
    ],
)
def test_signal_fetchers_resume_from_today_checkpoint(
    tmp_path,
    monkeypatch,
    module,
    fetch_attr,
    fetcher_name,
    expected_latest_name,
    fake_impl,
    value_field,
):
    calls = []

    def wrapper(*args, **kwargs):
        calls.append(args[0])
        return fake_impl(*args, **kwargs)

    monkeypatch.setattr(module, fetch_attr, wrapper)

    fetcher = getattr(module, fetcher_name)
    fetcher(["AAA"], output_dir=tmp_path, delay_min=0, delay_max=0, verbose=False)
    fetcher(["AAA", "BBB"], output_dir=tmp_path, delay_min=0, delay_max=0, verbose=False)

    today = date.today().isoformat()
    dated_files = list(tmp_path.glob(f"{today}_*.csv"))
    assert len(dated_files) == 1

    dated_rows = _read_rows(dated_files[0])
    latest_rows = _read_rows(tmp_path / expected_latest_name)

    assert calls == ["AAA", "BBB"]
    assert [row["symbol"] for row in dated_rows] == ["AAA", "BBB"]
    assert [row["symbol"] for row in latest_rows] == ["AAA", "BBB"]
    assert all(row[value_field] for row in dated_rows)