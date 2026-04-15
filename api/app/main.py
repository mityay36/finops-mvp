from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import allocations, recommendations, billing

app = FastAPI(
    title="FinOps MVP API",
    description="Unified Cost API: OpenCost + YC Billing + Recommendations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(allocations.router, prefix="/api/v1", tags=["Allocations"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
