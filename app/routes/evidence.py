from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.models import StockEvidenceContractResponse
from app.routes.common import COMMON_ERROR_RESPONSES, request_id
from app.services.candidate_service import CandidateService
from app.services.evidence_service import EvidenceService

router = APIRouter()


@router.get(
    "/stocks/{ticker}/evidence",
    response_model=StockEvidenceContractResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def get_stock_evidence(
    request: Request,
    ticker: str,
    source_type: str | None = Query(default=None, pattern="^(NEWS|DISCLOSURE|SCORE|CHUNK)$"),
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> StockEvidenceContractResponse:
    CandidateService(session).stock_or_404(ticker)
    return StockEvidenceContractResponse(
        data=EvidenceService(session).contract_data(
            ticker=ticker,
            source_type=source_type,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        ),
        message="근거 목록을 반환했습니다.",
        request_id=request_id(request),
    )
