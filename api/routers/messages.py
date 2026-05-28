from fastapi import APIRouter
from db import get_pool

router = APIRouter()


@router.get("/messages")
async def messages():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                ml.id,
                s.name              AS student_name,
                p.name              AS parent_name,
                p.relation,
                ml.message_type,
                ml.message_content,
                ml.whatsapp_number,
                ml.delivery_status,
                ml.failure_reason,
                ml.month_year,
                ml.triggered_by
            FROM message_log ml
            JOIN students s ON s.id = ml.student_id
            JOIN parents  p ON p.id = ml.parent_id
            WHERE ml.month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
            ORDER BY ml.id DESC
            LIMIT 30
        """)

    return [dict(r) for r in rows]
