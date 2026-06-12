from app.models import PaginationResponse


def pagination(*, limit: int, offset: int, total: int) -> PaginationResponse:
    return PaginationResponse(
        limit=limit,
        offset=offset,
        total=total,
        has_more=offset + limit < total,
    )
