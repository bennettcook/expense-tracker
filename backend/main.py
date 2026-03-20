from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
import psycopg2.extras

from database import get_connection, init_db
from auth import router as auth_router, get_current_user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.on_event("startup")
def startup():
    init_db()


class Expense(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., gt=0)
    category: Literal["food", "transport", "entertainment", "other"]


@app.get("/expenses")
def get_expenses(user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM expenses WHERE user_id = %s ORDER BY created_at DESC",
            (user["id"],),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/expenses", status_code=201)
def add_expense(expense: Expense, user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO expenses (user_id, description, amount, category) VALUES (%s, %s, %s, %s) RETURNING *",
            (user["id"], expense.description, expense.amount, expense.category),
        )
        new_row = cur.fetchone()
        conn.commit()
        return new_row
    finally:
        cur.close()
        conn.close()


@app.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Scope delete to user's own expenses to prevent cross-user deletion
        cur.execute(
            "DELETE FROM expenses WHERE id = %s AND user_id = %s",
            (expense_id, user["id"]),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Expense not found")
        conn.commit()
    finally:
        cur.close()
        conn.close()
