from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.models import StockDetailContractResponse, StockSearchContractResponse
from app.routes.common import COMMON_ERROR_RESPONSES, request_id
from app.services.stock_service import StockService

router = APIRouter()


@router.get(
    "/stocks/search",
    response_model=StockSearchContractResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def search_stocks(
    request: Request,
    q: str = Query(default="", max_length=100),
    market: str | None = Query(default=None, pattern="^(KOSPI|KOSDAQ)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> StockSearchContractResponse:
    return StockSearchContractResponse(
        data=StockService(session).search(
            q=q,
            market=market,
            limit=limit,
            offset=offset,
        ),
        message="종목 검색 결과를 반환했습니다.",
        request_id=request_id(request),
    )


@router.get(
    "/stocks/{ticker}",
    response_model=StockDetailContractResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def get_stock(
    request: Request,
    ticker: str,
    session: Session = Depends(get_db_session),
) -> StockDetailContractResponse:
    return StockDetailContractResponse(
        data=StockService(session).detail(ticker),
        message="종목 상세 정보를 반환했습니다.",
        request_id=request_id(request),
    )
