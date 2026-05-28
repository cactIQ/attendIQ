from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db import get_pool
from datetime import date
import os, json

router = APIRouter()
YEAR = int(os.getenv("ACADEMIC_YEAR", "2026"))


class StudentUpdate(BaseModel):
    name:             Optional[str]  = None
    gender:           Optional[str]  = None
    date_of_birth:    Optional[str]  = None
    whatsapp_number:  Optional[str]  = None
    email:            Optional[str]  = None
    is_active:        Optional[bool] = None


@router.get("/students")
async def list_students(class_id: Optional[int] = None, search: Optional[str] = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                s.id, s.name, s.gender, s.roll_number,
                s.whatsapp_number, s.email, s.date_of_birth,
                s.joining_date, s.is_active,
                c.standard, c.division, c.class_teacher
            FROM students s
            JOIN classes c ON c.id = s.class_id
            WHERE s.is_deleted = FALSE
              AND ($1::int  IS NULL OR s.class_id = $1)
              AND ($2::text IS NULL OR s.name ILIKE '%' || $2 || '%')
            ORDER BY c.standard, c.division, s.roll_number
        """, class_id, search)
    return [
        {
            **dict(r),
            "date_of_birth": r["date_of_birth"].isoformat() if r["date_of_birth"] else None,
            "joining_date":  r["joining_date"].isoformat()  if r["joining_date"]  else None,
        }
        for r in rows
    ]


@router.get("/students/{student_id}")
async def get_student(student_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT s.*, c.standard, c.division, c.class_teacher
            FROM students s
            JOIN classes c ON c.id = s.class_id
            WHERE s.id = $1 AND s.is_deleted = FALSE
        """, student_id)
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    r = dict(row)
    r["date_of_birth"] = r["date_of_birth"].isoformat() if r["date_of_birth"] else None
    r["joining_date"]  = r["joining_date"].isoformat()  if r["joining_date"]  else None
    r["updated_at"]    = r["updated_at"].isoformat()    if r.get("updated_at") else None
    return r


@router.patch("/students/{student_id}")
async def update_student(student_id: str, body: StudentUpdate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM students WHERE id = $1 AND is_deleted = FALSE", student_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Student not found")

        updates = body.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Coerce types so asyncpg gets native Python objects
        if "date_of_birth" in updates:
            updates["date_of_birth"] = date.fromisoformat(updates["date_of_birth"]) if updates["date_of_birth"] else None

        # Build SET clause dynamically
        fields = list(updates.keys())
        values = list(updates.values())
        set_clause = ", ".join(f"{f} = ${i+2}" for i, f in enumerate(fields))

        await conn.execute(
            f"UPDATE students SET {set_clause} WHERE id = $1",
            student_id, *values
        )

        # Log to change_log
        old = {f: existing[f].isoformat() if hasattr(existing[f], 'isoformat') else existing[f] for f in fields if existing[f] is not None and f in dict(existing)}
        # Make new_values JSON-safe too
        updates_json = {k: v.isoformat() if isinstance(v, date) else v for k, v in updates.items()}
        await conn.execute("""
            INSERT INTO change_log (table_name, record_id, action, old_values, new_values, changed_by, note)
            VALUES ('students', $1, 'update', $2::jsonb, $3::jsonb, 'chat', 'Updated via dashboard')
        """, student_id, json.dumps(old), json.dumps(updates_json))

    return {"ok": True, "updated": fields}


@router.get("/classes-list")
async def classes_list():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, standard, division, class_teacher
            FROM classes
            WHERE academic_year = $1
            ORDER BY standard, division
        """, YEAR)
    return [dict(r) for r in rows]
