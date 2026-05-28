from fastapi import APIRouter
from db import get_pool
import os

router = APIRouter()
YEAR = int(os.getenv("ACADEMIC_YEAR", "2026"))


@router.get("/classes")
async def classes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                c.id,
                c.standard,
                c.division,
                COALESCE(c.class_teacher, '—')                              AS teacher,
                COUNT(DISTINCT s.id)                                         AS student_count,
                ROUND(
                    100.0 * COUNT(a.id) FILTER (WHERE a.status = 'present')
                    / NULLIF(COUNT(a.id), 0)
                , 1)                                                         AS att_pct,
                ROUND(
                    AVG(100.0 * ts.marks_obtained / ts.total_marks)
                , 1)                                                         AS avg_score,
                COUNT(DISTINCT ml.id) FILTER (
                    WHERE ml.message_type = 'monthly_report'
                      AND ml.month_year  = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
                )                                                            AS reports_sent
            FROM classes c
            LEFT JOIN students s
                   ON s.class_id = c.id
                  AND s.is_deleted = FALSE
                  AND s.is_active  = TRUE
            LEFT JOIN attendance a
                   ON a.student_id = s.id
                  AND a.is_deleted = FALSE
                  AND DATE_TRUNC('month', a.date) = DATE_TRUNC('month', CURRENT_DATE)
            LEFT JOIN test_scores ts
                   ON ts.student_id = s.id
                  AND ts.is_deleted = FALSE
                  AND DATE_TRUNC('month', ts.test_date) = DATE_TRUNC('month', CURRENT_DATE)
            LEFT JOIN message_log ml
                   ON ml.student_id = s.id
            WHERE c.academic_year = $1
            GROUP BY c.id, c.standard, c.division, c.class_teacher
            ORDER BY avg_score DESC NULLS LAST
        """, YEAR)

    return [dict(r) for r in rows]
