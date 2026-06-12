from fastapi import APIRouter

from app.routes import candidates, chat, evidence, meta, stocks

router = APIRouter()
router.include_router(meta.router)
router.include_router(candidates.router)
router.include_router(evidence.router)
router.include_router(stocks.router)
router.include_router(chat.router)
