import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))


def init_db():
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                amount      NUMERIC(10, 2) NOT NULL,
                category    TEXT NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Migration: add user_id to pre-existing expenses tables that lack the column
        cur.execute("""
            ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
        """)

        conn.commit()
        cur.close()
    finally:
        conn.close()
