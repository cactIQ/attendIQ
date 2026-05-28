from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from db import get_pool

router = APIRouter()


@router.get("/messages")
async def messages(month: Optional[str] = Query(None), msg_type: Optional[str] = Query(None), status: Optional[str] = Query(None)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                ml.id,
                ml.student_id,
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
            WHERE ml.month_year     = COALESCE($1, TO_CHAR(CURRENT_DATE, 'YYYY-MM'))
              AND ($2::text IS NULL OR ml.message_type    = $2)
              AND ($3::text IS NULL OR ml.delivery_status = $3)
            ORDER BY ml.id DESC
            LIMIT 200
        """, month, msg_type, status)
    return [dict(r) for r in rows]


@router.get("/messages/stats")
async def message_stats(month: Optional[str] = Query(None)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*)                                                        AS total,
                COUNT(*) FILTER (WHERE delivery_status = 'sent')                AS sent,
                COUNT(*) FILTER (WHERE delivery_status = 'delivered')           AS delivered,
                COUNT(*) FILTER (WHERE delivery_status = 'read')                AS read,
                COUNT(*) FILTER (WHERE delivery_status = 'failed')              AS failed,
                COUNT(*) FILTER (WHERE delivery_status = 'pending')             AS pending
            FROM message_log
            WHERE month_year = COALESCE($1, TO_CHAR(CURRENT_DATE, 'YYYY-MM'))
        """, month)
    return dict(row)


class SendMessage(BaseModel):
    student_id:      str
    parent_id:       int
    message_type:    str
    message_content: str
    whatsapp_number: str


@router.post("/messages/send")
async def send_message(body: SendMessage):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verify student + parent exist
        student = await conn.fetchrow("SELECT id FROM students WHERE id=$1 AND is_deleted=FALSE", body.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        parent = await conn.fetchrow("SELECT id, whatsapp_number FROM parents WHERE id=$1 AND is_deleted=FALSE", body.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent not found")

        from datetime import date
        month_year = date.today().strftime("%Y-%m")

        row = await conn.fetchrow("""
            INSERT INTO message_log
                (student_id, parent_id, message_type, message_content, whatsapp_number, delivery_status, month_year, triggered_by)
            VALUES ($1, $2, $3, $4, $5, 'pending', $6, 'chat')
            RETURNING id
        """, body.student_id, body.parent_id, body.message_type, body.message_content, body.whatsapp_number, month_year)

    return {"ok": True, "message_id": row["id"], "status": "pending"}


@router.get("/messages/parents/{student_id}")
async def get_parents(student_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, relation, whatsapp_number, is_primary
            FROM parents
            WHERE student_id=$1 AND is_deleted=FALSE
            ORDER BY is_primary DESC
        """, student_id)
    return [dict(r) for r in rows]
