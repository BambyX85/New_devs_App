from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")

    from sqlalchemy import text
    from app.core.database_pool import db_pool

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise HTTPException(status_code=500, detail="Database unavailable")

    session = await db_pool.get_session()
    async with session:
        result = await session.execute(
            text("""
                SELECT id, name
                FROM properties
                WHERE tenant_id = :tenant_id
                ORDER BY name
            """),
            {"tenant_id": tenant_id},
        )
        rows = result.fetchall()

    return {
        "properties": [{"id": row.id, "name": row.name} for row in rows]
    }

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=1900, le=2100),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    if (month is None) != (year is None):
        raise HTTPException(
            status_code=422,
            detail="month and year must be provided together",
        )

    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")

    from sqlalchemy import text
    from app.core.database_pool import db_pool

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise HTTPException(status_code=500, detail="Database unavailable")

    session = await db_pool.get_session()
    async with session:
        property_exists = await session.execute(
            text("SELECT 1 FROM properties WHERE id = :property_id AND tenant_id = :tenant_id"),
            {"property_id": property_id, "tenant_id": tenant_id},
        )
        if property_exists.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Property not found for tenant")

    revenue_data = await get_revenue_summary(property_id, tenant_id, month=month, year=year)

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": revenue_data['total'],
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count'],
        "report_month": revenue_data.get("report_month"),
        "trend_percentage": revenue_data.get("trend_percentage"),
    }
