from fastapi import APIRouter, Query
from app.services.yc_billing import yc_billing

router = APIRouter()

@router.get("/billing/actual")
async def get_actual_billing(days: int = Query(30, ge=1, le=90)):
    """
    Фактические расходы из YC Billing CSV экспорта в Object Storage.
    Дополняет OpenCost данные реальными списаниями от YC.
    """
    return yc_billing.get_actual_costs(days=days)
