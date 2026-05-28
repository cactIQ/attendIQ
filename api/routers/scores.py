from fastapi import APIRouter, Query
from typing import Optional
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
                s.class_id,
                c.standard,
                c.division,
                ts.subject,
                ts.test_name,
                ts.marks_obtained,
                ts.total_marks,
                TRIM(ts.grade) AS grade,
                ts.test_date
            FROM test_scores ts
            JOIN students s ON s.id = ts.student_id
            JOIN classes  c ON c.id = s.class_id
            WHERE ts.is_deleted = FALSE
              AND s.is_deleted  = FALSE
              AND DATE_TRUNC('month', ts.test_date) = DATE_TRUNC('month', CURRENT_DATE)
            ORDER BY ts.student_id, ts.subject, ts.test_date DESC
            LIMIT 100
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


@router.get("/scores/all")
async def all_scores(
    class_id:  Optional[int] = Query(None),
    subject:   Optional[str] = Query(None),
    test_name: Optional[str] = Query(None),
    grade:     Optional[str] = Query(None),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                s.id            AS student_id,
                s.name          AS student_name,
                s.roll_number,
                s.class_id,
                c.standard,
                c.division,
                ts.subject,
                ts.test_name,
                ts.test_date,
                ts.marks_obtained,
                ts.total_marks,
                TRIM(ts.grade) AS grade,
                ts.imported_from
            FROM test_scores ts
            JOIN students s ON s.id = ts.student_id
            JOIN classes  c ON c.id = s.class_id
            WHERE ts.is_deleted = FALSE
              AND s.is_deleted  = FALSE
              AND ($1::int  IS NULL OR s.class_id = $1)
              AND ($2::text IS NULL OR ts.subject  = $2)
              AND ($3::text IS NULL OR ts.test_name = $3)
              AND ($4::text IS NULL OR ts.grade    = $4)
            ORDER BY ts.test_date DESC, c.standard, c.division, s.roll_number
            LIMIT 500
        """, class_id, subject, test_name, grade)

    return [
        {
            **dict(r),
            "marks_obtained": float(r["marks_obtained"]),
            "total_marks":    float(r["total_marks"]),
            "test_date":      r["test_date"].isoformat(),
        }
        for r in rows
    ]


@router.get("/scores/filters")
async def score_filters():
    """Returns distinct subjects and test names for populating dropdowns."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        subjects   = await conn.fetch("SELECT DISTINCT subject   FROM test_scores WHERE is_deleted=FALSE ORDER BY subject")
        test_names = await conn.fetch("SELECT DISTINCT test_name FROM test_scores WHERE is_deleted=FALSE ORDER BY test_name")
    return {
        "subjects":   [r["subject"]   for r in subjects],
        "test_names": [r["test_name"] for r in test_names],
    }
