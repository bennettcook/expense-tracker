from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2.extras
from database import get_connection, init_db

app = FastAPI()

# Allow your HTML frontend to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run table creation on startup
@app.on_event("startup")
def startup():
    init_db()

# Data shape for incoming expense data
class Expense(BaseModel):
    description: str
    amount: float
    category: str


@app.get("/expenses")
def get_expenses():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM expenses ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@app.post("/expenses", status_code=201)
def add_expense(expense: Expense):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO expenses (description, amount, category) VALUES (%s, %s, %s) RETURNING *",
        (expense.description, expense.amount, expense.category)
    )
    new_row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_row


@app.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    conn.commit()
    cur.close()
    conn.close()