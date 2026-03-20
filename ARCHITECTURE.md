# Expense Tracker — Architecture Document

## Overview

A simple expense tracking web application with a static HTML/JS frontend communicating with a FastAPI backend backed by a PostgreSQL database.

---

## Tech Stack

| Layer    | Technology                      |
|----------|---------------------------------|
| Frontend | Vanilla HTML, CSS, JavaScript   |
| Backend  | Python 3.9, FastAPI, Uvicorn    |
| Database | PostgreSQL (via psycopg2-binary) |
| Config   | python-dotenv (.env file)       |

---

## Project Structure

```
expense-tracker/
├── index.html          # Single-page frontend UI
├── style.css           # Frontend styles
├── script.js           # Frontend logic (fetch API calls, DOM rendering)
├── backend/
│   ├── main.py         # FastAPI app, route definitions, CORS config
│   ├── database.py     # DB connection factory and schema init
│   ├── requirements.txt
│   └── venv/           # Python virtual environment (not committed ideally)
└── README.md
```

---

## Architecture Diagram

```
Browser
  │
  │  Opens index.html / style.css / script.js (served as static files)
  │
  │  HTTP fetch() calls to http://127.0.0.1:8000
  ▼
FastAPI (Uvicorn)   ← backend/main.py
  │
  │  psycopg2 connections (one per request)
  ▼
PostgreSQL
  └── expenses table
```

---

## Data Model

### `expenses` table

| Column       | Type              | Notes                         |
|--------------|-------------------|-------------------------------|
| `id`         | SERIAL PRIMARY KEY |                               |
| `description`| TEXT NOT NULL      |                               |
| `amount`     | NUMERIC(10, 2)     |                               |
| `category`   | TEXT NOT NULL      | Unconstrained (any string)    |
| `created_at` | TIMESTAMPTZ        | Defaults to `NOW()`           |

Schema is created on startup via `init_db()` using `CREATE TABLE IF NOT EXISTS`.

---

## API Endpoints

| Method | Path                  | Description                     | Auth |
|--------|-----------------------|---------------------------------|------|
| GET    | `/expenses`           | Returns all expenses, newest first | None |
| POST   | `/expenses`           | Creates a new expense           | None |
| DELETE | `/expenses/{id}`      | Deletes expense by integer ID   | None |

### Request body (POST `/expenses`)
```json
{
  "description": "Coffee",
  "amount": 4.50,
  "category": "food"
}
```

---

## Frontend Behavior

- `loadExpenses()` — fetches all expenses from the API, applies client-side category filter, renders the list, and updates the total.
- Form submit — POSTs new expense then reloads the list.
- Delete button — DELETEs by ID then reloads the list.
- Filter select — triggers `loadExpenses()` on change.
- **Total is always calculated over all expenses**, regardless of the active filter.

---

## Configuration

The backend reads a single environment variable:

| Variable       | Description                                 |
|----------------|---------------------------------------------|
| `DATABASE_URL` | Full PostgreSQL connection string (required) |

Loaded from a `.env` file via `python-dotenv`.

---

## Bugs & Security Vulnerabilities

### Critical

#### 1. Stored XSS — `script.js:21-26`
`expense.description` and `expense.category` are injected directly into `innerHTML` without sanitization:
```js
li.innerHTML = `<span>${expense.description}</span> ...`
```
If the database contains a description like `<img src=x onerror=alert(1)>`, it executes in every visitor's browser. Any user or API caller who can write to the database can attack all other users.

**Fix:** Use `document.createElement` + `.textContent` for all user-supplied values, or sanitize before injection.

#### 2. Wildcard CORS — `main.py:10-15`
```python
allow_origins=["*"]
```
Any website on the internet can make cross-origin requests to this API. Combined with the lack of authentication, this means any third-party page can read, create, and delete all expenses on behalf of a user.

**Fix:** Restrict to the actual frontend origin (e.g., `["http://localhost:5500"]`).

---

### High

#### 3. Database connection leak on exception — `main.py` (all routes)
There is no `try/finally` around DB operations. If any `cur.execute()` raises an exception, `cur.close()` and `conn.close()` are never called, leaking the connection.

**Fix:** Wrap DB operations in `try/finally`, or use a context manager (`with conn`, `with cur`).

#### 4. No input validation on `category` — `main.py:23-26`
The `Expense` Pydantic model places no constraint on `category`. Clients can POST arbitrary strings (including very long ones or injection payloads).

**Fix:** Use `Literal["food", "transport", "entertainment", "other"]` or a `Field(..., pattern=...)` validator.

#### 5. No input validation on `description` — `main.py:23-26`
`description: str` has no max-length constraint. A client can POST megabytes of text per request, growing the database unboundedly.

**Fix:** Add `Field(..., max_length=500)` (or similar).

---

### Medium

#### 6. No error handling on fetch calls — `script.js`
All three `fetch()` calls (`loadExpenses`, form submit, `deleteExpense`) have no `try/catch`. A network error or non-2xx response is silently swallowed (or causes an unhandled Promise rejection), leaving the user with no feedback.

**Fix:** Wrap each `await fetch(...)` in `try/catch` and display a user-facing error message.

#### 7. Unhandled promise from `loadExpenses()` — `script.js:46`
After form submit, `loadExpenses()` is called without `await`:
```js
form.reset();
loadExpenses(); // Promise not awaited or caught
```
Any error thrown inside `loadExpenses()` is silently lost.

**Fix:** `await loadExpenses()` inside the `async` handler.

#### 8. No DB connection pooling — `main.py` / `database.py`
Every request opens a new raw psycopg2 connection and closes it after the query. This is expensive and won't scale — PostgreSQL has a hard cap on simultaneous connections.

**Fix:** Use `psycopg2.pool.ThreadedConnectionPool` or replace with SQLAlchemy + connection pool.

#### 9. `DATABASE_URL` not validated at startup — `database.py:9`
If `DATABASE_URL` is unset, `psycopg2.connect(None)` raises an obscure `TypeError`. There is no startup check or helpful error message.

**Fix:** Add an explicit guard: `if not os.getenv('DATABASE_URL'): raise RuntimeError(...)`.

---

### Low

#### 10. Total ignores active filter — `script.js:30`
```js
const total = expenses.reduce((sum, e) => sum + parseFloat(e.amount), 0);
```
`expenses` is the unfiltered list. When a category filter is active, the total still reflects all categories, which is likely confusing.

**Fix:** Either make this intentional ("grand total") and label it clearly, or compute the total from `visible`.

#### 11. Hardcoded API base URL — `script.js:1`
```js
const API = 'http://127.0.0.1:8000';
```
This breaks in any environment other than local development.

**Fix:** Derive the URL from `window.location.origin` or inject it at build time via an environment variable.

#### 12. Unused import — `database.py:2`
```python
from psycopg2.extras import DictCursor
```
`DictCursor` is imported but never used.

#### 13. Deprecated `@app.on_event("startup")` — `main.py:18`
This decorator is deprecated in FastAPI ≥ 0.93. The recommended replacement is the `lifespan` context manager.

#### 14. `venv/` committed to the repository
The `backend/venv/` directory is tracked in git. Virtual environments should be listed in `.gitignore` and not committed.

---

## Summary Table

| #  | Severity | Location          | Issue                                  |
|----|----------|-------------------|----------------------------------------|
| 1  | Critical | `script.js:21`    | Stored XSS via `innerHTML`             |
| 2  | Critical | `main.py:10`      | Wildcard CORS                          |
| 3  | High     | `main.py` routes  | DB connection leak (no try/finally)    |
| 4  | High     | `main.py:23`      | No category validation                 |
| 5  | High     | `main.py:23`      | No description length limit            |
| 6  | Medium   | `script.js`       | No fetch error handling                |
| 7  | Medium   | `script.js:46`    | Unawaited `loadExpenses()` promise     |
| 8  | Medium   | `database.py`     | No DB connection pooling               |
| 9  | Medium   | `database.py:9`   | Missing `DATABASE_URL` startup check   |
| 10 | Low      | `script.js:30`    | Total ignores active filter            |
| 11 | Low      | `script.js:1`     | Hardcoded localhost API URL            |
| 12 | Low      | `database.py:2`   | Unused `DictCursor` import             |
| 13 | Low      | `main.py:18`      | Deprecated `on_event` startup hook     |
| 14 | Low      | `backend/venv/`   | Virtual env committed to git           |
