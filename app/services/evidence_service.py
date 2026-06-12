from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    StockEvidenceContractData,
    StockEvidenceContractItem,
    StockEvidenceItemResponse,
)
from app.orm import EvidenceChunk, FinancialStatement, PriceMetric, SourceDocument
from app.services.response_helpers import pagination


class EvidenceService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def contract_data(
        self,
        *,
        ticker: str,
        source_type: str | None,
        from_date: date | None,
        to_date: date | None,
        limit: int,
        offset: int,
    ) -> StockEvidenceContractData:
        requested_types = contract_source_type_filter(source_type)
        evidence = self.items(ticker, requested_types)
        evidence = filter_evidence_dates(evidence, from_date=from_date, to_date=to_date)
        limited = evidence[offset : offset + limit]
        return StockEvidenceContractData(
            ticker=ticker,
            items=[stock_evidence_contract_item(item) for item in limited],
            pagination=pagination(limit=limit, offset=offset, total=len(evidence)),
        )

    def items(
        self,
        ticker: str,
        requested_types: set[str] | None = None,
    ) -> list[StockEvidenceItemResponse]:
        requested = requested_types or parse_evidence_types(None)
        items: list[StockEvidenceItemResponse] = []
        if "financial" in requested:
            items.extend(self._financial_evidence(ticker))
        if "disclosure" in requested or "news" in requested:
            items.extend(self._chunk_evidence(ticker, requested))
        if "price" in requested:
            items.extend(self._price_evidence(ticker))
        return sorted(
            items,
            key=lambda item: (item.as_of_date is None, item.as_of_date, item.id),
            reverse=True,
        )

    def _financial_evidence(self, ticker: str) -> list[StockEvidenceItemResponse]:
        financials = self.session.scalars(
            select(FinancialStatement)
            .where(FinancialStatement.ticker == ticker)
            .order_by(FinancialStatement.period_end_date.desc())
        ).all()
        items = []
        for row in financials:
            source = (
                self.session.get(SourceDocument, row.source_document_id)
                if row.source_document_id
                else None
            )
            items.append(
                StockEvidenceItemResponse(
                    id=f"financial_{ticker}_{row.fiscal_year}_{row.fiscal_period}",
                    type="financial",
                    title=f"{row.fiscal_year} {row.fiscal_period} 재무 mock 근거",
                    summary="재무제표 mock 데이터의 주요 수치가 검토 근거로 사용됩니다.",
                    source_name=source.source_name if source else "FINANCIAL_MOCK",
                    source_url=source.source_url if source else None,
                    source_identifier=(
                        source.external_id
                        if source
                        else f"{ticker}-{row.fiscal_year}-{row.fiscal_period}"
                    ),
                    published_at=source.published_at if source else None,
                    as_of_date=row.period_end_date,
                    data_status="available",
                )
            )
        return items

    def _chunk_evidence(
        self,
        ticker: str,
        requested_types: set[str],
    ) -> list[StockEvidenceItemResponse]:
        chunks = self.session.scalars(
            select(EvidenceChunk)
            .where(EvidenceChunk.ticker == ticker)
            .order_by(EvidenceChunk.fetched_at.desc())
        ).all()
        items = []
        for chunk in chunks:
            source = self.session.get(SourceDocument, chunk.source_document_id)
            evidence_type = source_type_to_evidence_type(source.source_type if source else "")
            if evidence_type not in requested_types:
                continue
            items.append(
                StockEvidenceItemResponse(
                    id=chunk.evidence_id,
                    type=evidence_type,
                    title=source.title if source else f"{ticker} 근거 데이터",
                    summary=chunk.chunk_text,
                    source_name=source.source_name if source else "UNKNOWN_SOURCE",
                    source_url=chunk.source_url or (source.source_url if source else None),
                    source_identifier=(
                        source.external_id if source else str(chunk.source_document_id)
                    ),
                    published_at=(
                        chunk.published_at or (source.published_at if source else None)
                    ),
                    as_of_date=(chunk.published_at.date() if chunk.published_at else None),
                    data_status="available",
                )
            )
        return items

    def _price_evidence(self, ticker: str) -> list[StockEvidenceItemResponse]:
        prices = self.session.scalars(
            select(PriceMetric)
            .where(PriceMetric.ticker == ticker)
            .order_by(PriceMetric.trade_date.desc())
        ).all()
        return [
            StockEvidenceItemResponse(
                id=f"price_{ticker}_{row.trade_date.isoformat()}",
                type="price",
                title=f"{row.trade_date.isoformat()} 가격 지표 fallback mock",
                summary="가격과 유동성 fallback mock 데이터가 검토 근거로 사용됩니다.",
                source_name=row.source,
                source_url=None,
                source_identifier=f"{row.source}:{ticker}:{row.trade_date.isoformat()}",
                published_at=None,
                as_of_date=row.trade_date,
                data_status="fallback" if "FALLBACK" in row.source else "available",
            )
            for row in prices
        ]


def parse_evidence_types(types: str | None) -> set[str]:
    allowed = {"financial", "news", "disclosure", "price"}
    if not types:
        return allowed
    parsed = {item.strip() for item in types.split(",") if item.strip()}
    invalid = parsed - allowed
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported evidence types: {', '.join(sorted(invalid))}.",
        )
    return parsed


def contract_source_type(value: str) -> str:
    mapping = {
        "news": "NEWS",
        "disclosure": "DISCLOSURE",
        "financial": "SCORE",
        "price": "SCORE",
    }
    return mapping.get(value, "CHUNK")


def contract_source_type_filter(source_type: str | None) -> set[str]:
    if source_type is None:
        return parse_evidence_types(None)
    mapping = {
        "NEWS": {"news"},
        "DISCLOSURE": {"disclosure"},
        "SCORE": {"financial", "price"},
        "CHUNK": {"news", "disclosure"},
    }
    return mapping[source_type]


def filter_evidence_dates(
    evidence: list[StockEvidenceItemResponse],
    *,
    from_date: date | None,
    to_date: date | None,
) -> list[StockEvidenceItemResponse]:
    if from_date is None and to_date is None:
        return evidence
    filtered = []
    for item in evidence:
        item_date = item.as_of_date or (item.published_at.date() if item.published_at else None)
        if item_date is None:
            continue
        if from_date and item_date < from_date:
            continue
        if to_date and item_date > to_date:
            continue
        filtered.append(item)
    return filtered


def stock_evidence_contract_item(
    item: StockEvidenceItemResponse,
) -> StockEvidenceContractItem:
    metadata = {
        "data_status": item.data_status,
    }
    if item.source_identifier:
        metadata["source_identifier"] = item.source_identifier
    if item.as_of_date:
        metadata["as_of_date"] = item.as_of_date.isoformat()
    return StockEvidenceContractItem(
        id=item.id,
        source_type=contract_source_type(item.type),
        title=item.title,
        source_name=item.source_name,
        url=item.source_url,
        published_at=item.published_at,
        snippet=item.summary,
        metadata=metadata,
    )


def source_type_to_evidence_type(source_type: str) -> str:
    if source_type == "news":
        return "news"
    if source_type == "disclosure":
        return "disclosure"
    if source_type == "financial":
        return "financial"
    if source_type == "price":
        return "price"
    return "disclosure"


def optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float_value(value)


def float_value(value: object) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)
