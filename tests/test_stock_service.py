from app.orm import Stock
from app.services.stock_service import match_reason


def test_match_reason_matches_ticker_case_insensitively() -> None:
    stock = Stock(
        ticker="AAPL",
        company_name="Apple",
        company_name_en=None,
        market="NASDAQ",
        sector=None,
        industry=None,
        listing_date=None,
        is_active=True,
    )

    assert match_reason(stock, "aapl") == "ticker"
