import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .database import get_db, init_db
from .schemas import (
    Category,
    CategoryCreate,
    CategoryWithTotal,
    Expense,
    ExpenseCreate,
    ExpenseWithCategory,
    Summary,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Advanced Expense Tracker API",
    description="Manage categories and expenses with category-wise grouping.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

Db = sqlite3.Connection


@app.post(
    "/categories",
    response_model=Category,
    status_code=status.HTTP_201_CREATED,
    tags=["Categories"],
    responses={409: {"description": "Category already exists"}},
)
def create_category(payload: CategoryCreate, db: Db = Depends(get_db)):
    try:
        with db:
            cur = db.execute("INSERT INTO categories (name) VALUES (?)", (payload.name,))
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Category already exists")
    return Category(id=cur.lastrowid, name=payload.name)


@app.get("/categories", response_model=list[CategoryWithTotal], tags=["Categories"])
def list_categories(db: Db = Depends(get_db)):
    rows = db.execute(
        """
        SELECT c.id, c.name, COUNT(e.id) AS total_expenses
        FROM categories c
        LEFT JOIN expenses e ON e.category_id = c.id
        GROUP BY c.id
        ORDER BY c.name
        """
    ).fetchall()
    return [dict(row) for row in rows]


@app.post(
    "/expenses",
    response_model=Expense,
    status_code=status.HTTP_201_CREATED,
    tags=["Expenses"],
    responses={400: {"description": "Category does not exist"}},
)
def create_expense(payload: ExpenseCreate, db: Db = Depends(get_db)):
    if not db.execute("SELECT 1 FROM categories WHERE id = ?", (payload.category_id,)).fetchone():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category does not exist")

    created_at = datetime.now().replace(microsecond=0)
    with db:
        cur = db.execute(
            "INSERT INTO expenses (title, amount, category_id, created_at) VALUES (?, ?, ?, ?)",
            (payload.title, payload.amount, payload.category_id, created_at.isoformat()),
        )
    return Expense(id=cur.lastrowid, created_at=created_at, **payload.model_dump())


@app.get("/expenses", response_model=list[ExpenseWithCategory], tags=["Expenses"])
def list_expenses(db: Db = Depends(get_db)):
    rows = db.execute(
        """
        SELECT e.id, e.title, e.amount, c.name AS category, e.created_at
        FROM expenses e
        JOIN categories c ON c.id = e.category_id
        ORDER BY e.created_at DESC, e.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


@app.get("/summary", response_model=Summary, tags=["Summary"])
def get_summary(db: Db = Depends(get_db)):
    total, count = db.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM expenses").fetchone()
    average = round(total / count, 2) if count else 0
    return Summary(total=round(total, 2), count=count, average=average)
