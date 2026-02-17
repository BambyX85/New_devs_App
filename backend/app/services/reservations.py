from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional


def _format_currency(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

async def calculate_monthly_revenue(property_id: str, month: int, year: int, db_session=None) -> Decimal:
    """
    Calculates revenue for a specific month.
    """

    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)
        
    print(f"DEBUG: Querying revenue for {property_id} from {start_date} to {end_date}")

    # SQL Simulation (This would be executed against the actual DB)
    query = """
        SELECT SUM(total_amount) as total
        FROM reservations
        WHERE property_id = $1
        AND tenant_id = $2
        AND check_in_date >= $3
        AND check_in_date < $4
    """
    
    # In production this query executes against a database session.
    # result = await db.fetch_val(query, property_id, tenant_id, start_date, end_date)
    # return result or Decimal('0')
    
    return Decimal('0') # Placeholder for now until DB connection is finalized

async def calculate_total_revenue(
    property_id: str,
    tenant_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    # Import here to avoid circular imports
    from sqlalchemy import text
    from app.core.database_pool import db_pool

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise RuntimeError("Database pool not available")

    session = await db_pool.get_session()
    async with session:
        query = text("""
            WITH property_ctx AS (
                SELECT timezone
                FROM properties
                WHERE id = :property_id AND tenant_id = :tenant_id
            ),
            month_window AS (
                SELECT
                    CASE
                        WHEN CAST(:month AS INTEGER) IS NOT NULL AND CAST(:year AS INTEGER) IS NOT NULL
                            THEN make_timestamp(CAST(:year AS INTEGER), CAST(:month AS INTEGER), 1, 0, 0, 0)
                        ELSE (
                            SELECT date_trunc('month', timezone(pc.timezone, MAX(r.check_in_date)))
                            FROM reservations r
                            WHERE r.property_id = :property_id AND r.tenant_id = :tenant_id
                        )
                    END AS local_month_start,
                    pc.timezone AS property_timezone
                FROM property_ctx pc
            )
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN mw.local_month_start IS NOT NULL
                            AND timezone(mw.property_timezone, r.check_in_date) >= mw.local_month_start
                            AND timezone(mw.property_timezone, r.check_in_date) < (mw.local_month_start + INTERVAL '1 month')
                            THEN r.total_amount
                        ELSE 0
                    END
                ), 0) AS total_revenue,
                COALESCE(SUM(
                    CASE
                        WHEN mw.local_month_start IS NOT NULL
                            AND timezone(mw.property_timezone, r.check_in_date) >= (mw.local_month_start - INTERVAL '1 month')
                            AND timezone(mw.property_timezone, r.check_in_date) < mw.local_month_start
                            THEN r.total_amount
                        ELSE 0
                    END
                ), 0) AS previous_total_revenue,
                COUNT(
                    CASE
                        WHEN mw.local_month_start IS NOT NULL
                            AND timezone(mw.property_timezone, r.check_in_date) >= mw.local_month_start
                            AND timezone(mw.property_timezone, r.check_in_date) < (mw.local_month_start + INTERVAL '1 month')
                            THEN r.id
                    END
                ) AS reservation_count,
                mw.local_month_start
            FROM month_window mw
            LEFT JOIN reservations r
                ON r.property_id = :property_id
                AND r.tenant_id = :tenant_id
            GROUP BY mw.local_month_start
        """)

        result = await session.execute(
            query,
            {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "month": month,
                "year": year,
            },
        )
        row = result.fetchone()

        if row:
            total_revenue = Decimal(str(row.total_revenue))
            previous_total_revenue = Decimal(str(row.previous_total_revenue))
            trend_percentage = None
            if previous_total_revenue > 0:
                trend_percentage = float(
                    ((total_revenue - previous_total_revenue) / previous_total_revenue * Decimal("100"))
                    .quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                )
            report_month = (
                row.local_month_start.date().isoformat()
                if row.local_month_start is not None
                else None
            )
            return {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "total": _format_currency(total_revenue),
                "currency": "USD",
                "count": int(row.reservation_count or 0),
                "report_month": report_month,
                "trend_percentage": trend_percentage,
            }

        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": "0.00",
            "currency": "USD",
            "count": 0,
            "report_month": None,
            "trend_percentage": None,
        }
