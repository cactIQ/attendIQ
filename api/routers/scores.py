from fastapi import APIRouter
from db import get_pool

router = APIRouter()


@router.get("/scores")
async def scores():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Latest score per student per subject this month
        rows = await conn.fetch("""
            SELECT DISTINCT ON (ts.student_id, ts.subject)
                s.id            AS student_id,
                s.name          AS student_name,
                ts.subject,
                ts.test_name,
                ts.marks_obtained,
                ts.total_marks,
                ts.grade,
                ts.test_date
            FROM test_scores ts
            JOIN students s ON s.id = ts.student_id
            WHERE ts.is_deleted = FALSE
              AND s.is_deleted  = FALSE
              AND DATE_TRUNC('month', ts.test_date) = DATE_TRUNC('month', CURRENT_DATE)
            ORDER BY ts.student_id, ts.subject, ts.test_date DESC
            LIMIT 20
        """)

    return [
        {
            **dict(r),
            "marks_obtained": float(r["marks_obtained"]),
            "total_marks":    float(r["total_marks"]),
            "test_date":      r["test_date"].isoformat(),
        }
        for r in rows
    ]
