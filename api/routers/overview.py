from fastapi import APIRouter, Query
from typing import Optional
from db import get_pool
import os

router = APIRouter()
YEAR = int(os.getenv("ACADEMIC_YEAR", "2026"))


@router.get("/overview")
async def overview(class_id: Optional[int] = Query(None)):
    pool = await get_pool()
    async with pool.acquire() as conn:

        active_students = await conn.fetchval("""
            SELECT COUNT(*)
            FROM students
            WHERE is_active = TRUE AND is_deleted = FALSE
              AND ($1::int IS NULL OR class_id = $1)
        """, class_id)

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
              AND ($1::int IS NULL OR s.class_id = $1)
        """, class_id)

        avg_score = await conn.fetchval("""
            SELECT ROUND(AVG(100.0 * ts.marks_obtained / ts.total_marks), 1)
            FROM test_scores ts
            JOIN students s ON s.id = ts.student_id
            WHERE DATE_TRUNC('month', ts.test_date) = DATE_TRUNC('month', CURRENT_DATE)
              AND ts.is_deleted = FALSE
              AND s.is_deleted = FALSE
              AND ($1::int IS NULL OR s.class_id = $1)
        """, class_id)

        msg = await conn.fetchrow("""
            SELECT
                COUNT(*)                                                        AS total,
                COUNT(*) FILTER (WHERE delivery_status IN ('delivered','read')) AS delivered,
                COUNT(*) FILTER (WHERE delivery_status = 'failed')              AS failed
            FROM message_log ml
            JOIN students s ON s.id = ml.student_id
            WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
              AND ($1::int IS NULL OR s.class_id = $1)
        """, class_id)

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


@router.get("/attendance/trend")
async def attendance_trend(class_id: Optional[int] = Query(None)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', a.date), 'Mon')                          AS month,
                DATE_TRUNC('month', a.date)                                           AS month_date,
                ROUND(100.0 * COUNT(*) FILTER (WHERE a.status = 'present') / NULLIF(COUNT(*),0), 1) AS present_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE a.status = 'late')    / NULLIF(COUNT(*),0), 1) AS late_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE a.status = 'absent')  / NULLIF(COUNT(*),0), 1) AS absent_pct
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE a.is_deleted = FALSE
              AND s.is_deleted = FALSE
              AND a.date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '4 months'
              AND ($1::int IS NULL OR s.class_id = $1)
            GROUP BY DATE_TRUNC('month', a.date)
            ORDER BY DATE_TRUNC('month', a.date)
        """, class_id)

    return [
        {
            "month":       r["month"],
            "present_pct": float(r["present_pct"] or 0),
            "late_pct":    float(r["late_pct"]    or 0),
            "absent_pct":  float(r["absent_pct"]  or 0),
        }
        for r in rows
    ]
