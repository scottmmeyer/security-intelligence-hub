from __future__ import annotations

import pytest

from src.portfolio.ingestion import IngestionError, detect_format, ingest_portfolio


def _fidelity_csv(
    *,
    header_line: str,
    row_line: str,
    preamble_non_empty_lines: int = 0,
) -> str:
    preamble = "\n".join(f"preamble line {i+1}" for i in range(preamble_non_empty_lines))
    if preamble:
        return f"{preamble}\n{header_line}\n{row_line}\n"
    return f"{header_line}\n{row_line}\n"


def test_fidelity_header_matching_is_case_insensitive() -> None:
    headers = [
        "account name/number",
        "symbol",
        "description",
        "quantity",
        "last price",
        "current value",
    ]
    assert detect_format(headers) == "FIDELITY_CSV"


def test_fidelity_header_matching_tolerates_outer_whitespace() -> None:
    headers = [
        "  Account Name/Number  ",
        "  Symbol ",
        " Description  ",
        " Quantity ",
        " Last Price ",
        " Current Value  ",
    ]
    assert detect_format(headers) == "FIDELITY_CSV"


def test_fidelity_header_matching_tolerates_internal_whitespace_variants() -> None:
    headers = [
        "Account   Name/Number",
        "Symbol",
        "Description",
        "Quantity",
        "Last   Price",
        "Current   Value",
    ]
    assert detect_format(headers) == "FIDELITY_CSV"


def test_fidelity_column_lookup_uses_normalized_lowercase_keys() -> None:
    content = _fidelity_csv(
        header_line=(
            "  account name/number  , symbol , DESCRIPTION , quantity , last price , current value , "
            " percent of account , cost basis total "
        ),
        row_line=" Individual TOD X20-548022 , mu , Micron Technology , 10 , 100 , 1000 , 25.0 , 800 ",
    )

    snapshot, holdings = ingest_portfolio(content, "fidelity.csv", "2026-07-13")

    assert snapshot.source_format == "FIDELITY_CSV"
    assert len(holdings) == 1
    assert holdings[0].symbol == "MU"
    assert holdings[0].description == "Micron Technology"
    assert holdings[0].quantity == 10
    assert holdings[0].market_value == 1000


def test_header_line_detection_is_case_insensitive() -> None:
    content = _fidelity_csv(
        preamble_non_empty_lines=3,
        header_line=(
            "account name/number,symbol,description,quantity,last price,current value,percent of account,cost basis total"
        ),
        row_line="Individual TOD X20-548022,MU,Micron Technology,10,100,1000,25.0,800",
    )

    snapshot, holdings = ingest_portfolio(content, "fidelity.csv", "2026-07-13")

    assert snapshot.source_format == "FIDELITY_CSV"
    assert len(holdings) == 1
    assert holdings[0].symbol == "MU"


def test_long_preamble_header_after_twenty_rows_is_accepted_up_to_two_hundred() -> None:
    content = _fidelity_csv(
        preamble_non_empty_lines=30,
        header_line=(
            "Account Name/Number,Symbol,Description,Quantity,Last Price,Current Value,Percent Of Account,Cost Basis Total"
        ),
        row_line="Individual TOD X20-548022,MU,Micron Technology,10,100,1000,25.0,800",
    )

    snapshot, holdings = ingest_portfolio(content, "fidelity.csv", "2026-07-13")

    assert snapshot.source_format == "FIDELITY_CSV"
    assert len(holdings) == 1


def test_preamble_scan_fails_safely_when_header_after_two_hundred_non_empty_rows() -> None:
    content = _fidelity_csv(
        preamble_non_empty_lines=205,
        header_line=(
            "Account Name/Number,Symbol,Description,Quantity,Last Price,Current Value,Percent Of Account,Cost Basis Total"
        ),
        row_line="Individual TOD X20-548022,MU,Micron Technology,10,100,1000,25.0,800",
    )

    with pytest.raises(IngestionError, match="Cannot determine portfolio format"):
        ingest_portfolio(content, "fidelity.csv", "2026-07-13")


def test_existing_normal_fidelity_csv_still_parses() -> None:
    content = _fidelity_csv(
        header_line=(
            "Account Name/Number,Symbol,Description,Quantity,Last Price,Current Value,Percent Of Account,Cost Basis Total"
        ),
        row_line="Individual TOD X20-548022,MU,Micron Technology,10,100,1000,25.0,800",
    )

    snapshot, holdings = ingest_portfolio(content, "fidelity.csv", "2026-07-13")

    assert snapshot.source_format == "FIDELITY_CSV"
    assert snapshot.ingestion_status in {"ACCEPTED", "PARTIAL"}
    assert len(holdings) == 1
    assert holdings[0].symbol == "MU"
