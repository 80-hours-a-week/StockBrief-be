from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    EvidencePreviewContract,
    StockContractItem,
    StockDetailContractData,
    StockSearchContractData,
    StockSearchContractItem,
)
from app.orm import CompanyIdentifier, Stock
from app.services.candidate_service import CandidateService
from app.services.evidence_service import EvidenceService, contract_source_type
from app.services.response_helpers import pagination


class StockService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.candidates = CandidateService(session)
        self.evidence = EvidenceService(session)

    def search(
        self,
        *,
        q: str,
        market: str | None,
        limit: int,
        offset: int,
    ) -> StockSearchContractData:
        statement = select(Stock)
        if q:
            query = f"%{escape_like_query(q)}%"
            statement = statement.where(
                (Stock.ticker.like(query, escape="\\"))
                | (Stock.company_name.like(query, escape="\\"))
            )
        if market:
            statement = statement.where(Stock.market == market)

        total_statement = select(func.count()).select_from(statement.subquery())
        total = self.session.scalar(total_statement) or 0

        statement = statement.order_by(Stock.ticker.asc()).offset(offset).limit(limit)
        rows = self.session.scalars(statement).all()
        corp_codes = self.corp_codes([stock.ticker for stock in rows])

        return StockSearchContractData(
            items=[
                StockSearchContractItem(
                    ticker=stock.ticker,
                    name=stock.company_name,
                    market=stock.market,
                    sector=stock.sector,
                    corp_code=corp_codes.get(stock.ticker),
                    match_reason=match_reason(stock, q),
                )
                for stock in rows
            ],
            pagination=pagination(limit=limit, offset=offset, total=total),
        )

    def detail(self, ticker: str) -> StockDetailContractData:
        stock = self.candidates.stock_or_404(ticker)
        _, score = self.candidates.candidate_row(ticker)
        evidence = self.evidence.items(ticker)
        return StockDetailContractData(
            stock=self.contract_item(stock),
            price=self.candidates.latest_price_contract(ticker),
            score=self.candidates.stock_score_contract(score),
            brief=self.candidates.stock_brief_contract(stock=stock, score=score),
            evidence_preview=[
                EvidencePreviewContract(
                    id=item.id,
                    source_type=contract_source_type(item.type),
                    title=item.title,
                    source_name=item.source_name,
                    url=item.source_url,
                    published_at=item.published_at,
                )
                for item in evidence[:3]
            ],
        )

    def contract_item(self, stock: Stock) -> StockContractItem:
        return StockContractItem(
            ticker=stock.ticker,
            name=stock.company_name,
            market=stock.market,
            sector=stock.sector,
            corp_code=self.corp_code(stock.ticker),
        )

    def corp_code(self, ticker: str) -> str | None:
        identifier = self.session.scalars(
            select(CompanyIdentifier).where(
                CompanyIdentifier.ticker == ticker,
                CompanyIdentifier.provider == "OpenDART",
                CompanyIdentifier.identifier_type == "corp_code",
            )
        ).first()
        return identifier.identifier_value if identifier else None

    def corp_codes(self, tickers: list[str]) -> dict[str, str]:
        if not tickers:
            return {}
        rows = self.session.scalars(
            select(CompanyIdentifier).where(
                CompanyIdentifier.ticker.in_(tickers),
                CompanyIdentifier.provider == "OpenDART",
                CompanyIdentifier.identifier_type == "corp_code",
            )
        ).all()
        return {row.ticker: row.identifier_value for row in rows}


def escape_like_query(query: str) -> str:
    return query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def match_reason(stock: Stock, query: str) -> str:
    if not query:
        return "default"
    if query.casefold() in stock.ticker.casefold():
        return "ticker"
    if query.casefold() in stock.company_name.casefold():
        return "name"
    return "keyword"
