from fastapi import APIRouter
from db import get_pool

router = APIRouter()


@router.get("/alerts")
async def alerts():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                s.id            AS student_id,
                s.name          AS student_name,
                c.standard,
                c.division,
                COUNT(*)        AS absent_days,
                -- 'Sent' if any absence_alert was dispatched this month
                CASE WHEN MAX(ml.delivery_status) IS NOT NULL THEN 'Sent'
                     ELSE 'Pending'
                END             AS alert_status
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            JOIN classes  c ON c.id = s.class_id
            LEFT JOIN message_log ml
                   ON ml.student_id  = s.id
                  AND ml.message_type = 'absence_alert'
                  AND ml.month_year   = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
            WHERE a.status     = 'absent'
              AND DATE_TRUNC('month', a.date) = DATE_TRUNC('month', CURRENT_DATE)
              AND a.is_deleted = FALSE
              AND s.is_deleted = FALSE
              AND s.is_active  = TRUE
            GROUP BY s.id, s.name, c.standard, c.division
            HAVING COUNT(*) >= 3
            ORDER BY absent_days DESC
        """)

    return [dict(r) for r in rows]
