import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.cache import close_redis
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.routers import allocations, billing, clusters, providers, sync, recommendations
from app.services.factory import service_factory
from app.services.recommendations.rules._thresholds import WINDOW_DAYS, MIN_VALID_DAYS


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

logger.info(
    "Engine initialized: window_days=%d min_valid_days=%d",
    WINDOW_DAYS,
    MIN_VALID_DAYS,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting FinOps API (env=%s)", settings.env)
    start_scheduler()
    try:
        yield
    finally:
        logger.info("Shutting down FinOps API")
        shutdown_scheduler()
        await service_factory.aclose_all()
        await close_redis()
        await dispose_engine()


app = FastAPI(
    title="FinOps API",
    description="Multi-cluster cost observability and recommendations",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers.router, prefix="/api/v1", tags=["Providers"])
app.include_router(clusters.router, prefix="/api/v1", tags=["Clusters"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sync"])
app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])
app.include_router(allocations.router, prefix="/api/v1", tags=["Allocations"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}
