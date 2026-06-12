from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import HealthResponse, ServicePolicyResponse
from app.routes.common import COMMON_ERROR_RESPONSES, PROHIBITED_OUTPUTS

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.app_env,
        time=datetime.now(timezone.utc),
    )


@router.get(
    "/meta/service-policy",
    response_model=ServicePolicyResponse,
    responses=COMMON_ERROR_RESPONSES,
)
def service_policy() -> ServicePolicyResponse:
    return ServicePolicyResponse(
        product_type="evidence_based_stock_candidate_recommendation",
        recommendation_type="review_candidate_not_buy_sell_advice",
        prohibited_outputs=PROHIBITED_OUTPUTS,
        mvp_auth="guest_first",
    )
