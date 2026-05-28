from fastapi import APIRouter
from db import get_pool
import os

router = APIRouter()
YEAR = int(os.getenv("ACADEMIC_YEAR", "2026"))


@router.get("/overview")
async def overview():
    pool = await get_pool()
    async with pool.acquire() as conn:

        active_students = await conn.fetchval("""
            SELECT COUNT(*)
            FROM students
            WHERE is_active = TRUE AND is_deleted = FALSE
        """)

        att_pct = await conn.fetchval("""
            SELECT ROUND(
                100.0 * COUNT(*) FILTER (WHERE a.status = 'present')
                / NULLIF(COUNT(*), 0)
            , 1)
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE DATE_TRUNC('month', a.date) = DATE_TRUNC('month', CURRENT_DATE)
              AND a.is_deleted = FALSE
              AND s.is_deleted = FALSE
        """)

        avg_score = await conn.fetchval("""
            SELECT ROUND(AVG(100.0 * ts.marks_obtained / ts.total_marks), 1)
            FROM test_scores ts
            JOIN students s ON s.id = ts.student_id
            WHERE DATE_TRUNC('month', ts.test_date) = DATE_TRUNC('month', CURRENT_DATE)
              AND ts.is_deleted = FALSE
              AND s.is_deleted = FALSE
        """)

        msg = await conn.fetchrow("""
            SELECT
                COUNT(*)                                                      AS total,
                COUNT(*) FILTER (WHERE delivery_status IN ('delivered','read')) AS delivered,
                COUNT(*) FILTER (WHERE delivery_status = 'failed')            AS failed
            FROM message_log
            WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
        """)

    return {
        "active_students": active_students or 0,
        "avg_attendance":  float(att_pct  or 0),
        "avg_score":       float(avg_score or 0),
        "messages": {
            "total":     msg["total"],
            "delivered": msg["delivered"],
            "failed":    msg["failed"],
        },
    }
