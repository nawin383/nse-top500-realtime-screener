"""v1 routers aggregation."""
from fastapi import APIRouter
from .stocks import router as stocks_r
from .market import router as market_r
from .screener import router as screener_r
from .webhooks import router as webhooks_r

router = APIRouter()
router.include_router(market_r, tags=["v1-market"])
router.include_router(stocks_r, tags=["v1-stocks"])
router.include_router(screener_r, tags=["v1-screener"])
router.include_router(webhooks_r, tags=["v1-webhooks"])
