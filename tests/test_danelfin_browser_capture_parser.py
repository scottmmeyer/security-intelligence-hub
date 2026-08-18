from __future__ import annotations

import pytest

from src.scoring.danelfin_browser_capture_parser import (
    extract_scores,
    extract_source_date,
    parse_pair_page,
    parse_single_stock_page,
)


def test_single_page_parser_extracts_symbol_score_and_date() -> None:
    text = "Overall AI Score 3 out of 10 Last update: 2026-08-15"
    parsed = parse_single_stock_page("https://danelfin.com/stock/MSFT", text)
    assert parsed.symbol == "MSFT"
    assert parsed.danelfin_raw == 3
    assert parsed.sourced_date == "2026-08-15"


def test_pair_page_parser_extracts_two_scores_and_shared_date() -> None:
    text = "MSFT 3 out of 10 NVDA 8 out of 10 Updated Aug 15, 2026"
    left, right = parse_pair_page("https://danelfin.com/stocks/msft-vs-nvda", text)
    assert left.symbol == "MSFT"
    assert left.danelfin_raw == 3
    assert left.sourced_date == "2026-08-15"
    assert right.symbol == "NVDA"
    assert right.danelfin_raw == 8
    assert right.sourced_date == "2026-08-15"


def test_pair_page_parser_accepts_canonical_slugged_redirect_url() -> None:
    text = "Micron 4 out of 10 Vertiv 7 out of 10 Last update: 2026-08-16"
    left, right = parse_pair_page(
        "https://danelfin.com/stocks/MU-micron-technology-vs-VRT-vertiv-compare",
        text,
        expected_symbols=("MU", "VRT"),
    )
    assert left.symbol == "MU"
    assert left.danelfin_raw == 4
    assert right.symbol == "VRT"
    assert right.danelfin_raw == 7
    assert left.sourced_date == "2026-08-16"
    assert right.sourced_date == "2026-08-16"


def test_pair_page_parser_uses_expected_symbols_when_slug_unknown() -> None:
    text = "Alpha 4 out of 10 Beta 9 out of 10 Last update: 2026-08-14"
    left, right = parse_pair_page(
        "https://danelfin.com/stocks/company-a-vs-company-b",
        text,
        expected_symbols=("MU", "VRT"),
    )
    assert left.symbol == "MU"
    assert left.danelfin_raw == 4
    assert right.symbol == "VRT"
    assert right.danelfin_raw == 9


def test_pair_page_parser_rejects_when_symbols_unavailable() -> None:
    text = "Alpha 4 out of 10 Beta 9 out of 10 Last update: 2026-08-14"
    with pytest.raises(ValueError, match="symbols unavailable"):
        parse_pair_page("https://danelfin.com/stocks/company-a-vs-company-b", text)


def test_missing_score_raises() -> None:
    with pytest.raises(ValueError, match="no Danelfin score"):
        parse_single_stock_page("https://danelfin.com/stock/MSFT", "Last update: 2026-08-15")


def test_malformed_pair_raises_when_fewer_than_two_scores() -> None:
    with pytest.raises(ValueError, match="at least two"):
        parse_pair_page("https://danelfin.com/stocks/msft-vs-nvda", "MSFT 3 out of 10")


def test_pair_page_rejects_when_only_one_symbol_is_available() -> None:
    text = "MSFT 3 out of 10 NVDA 8 out of 10 Last update: 2026-08-15"
    with pytest.raises(ValueError, match="symbols unavailable"):
        parse_pair_page(
            "https://danelfin.com/stocks/company-a-vs-company-b",
            text,
            expected_symbols=("MSFT", ""),
        )


def test_extract_scores_ignores_out_of_range_and_nonmatching() -> None:
    text = "11 out of 10 0 out of 10 7 out of 10 score=9"
    assert extract_scores(text) == [7]


def test_pair_page_extra_out_of_10_noise_does_not_prevent_capture() -> None:
    text = (
        "MSFT 3 out of 10 NVDA 8 out of 10 Fundamental 7 out of 10 "
        "Last update: 2026-08-15"
    )
    left, right = parse_pair_page("https://danelfin.com/stocks/msft-vs-nvda", text)
    assert left.symbol == "MSFT"
    assert right.symbol == "NVDA"
    assert left.danelfin_raw == 3
    assert right.danelfin_raw == 8


def test_extract_source_date_none_when_absent() -> None:
    assert extract_source_date("Overall AI Score 6 out of 10") is None


def test_extract_source_date_accepts_long_format() -> None:
    assert extract_source_date("Last update: Aug 15, 2026") == "2026-08-15"
