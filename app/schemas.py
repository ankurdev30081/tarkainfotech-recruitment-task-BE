from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CategoryCreate(BaseModel):
    name: NonEmptyStr = Field(examples=["Food"])


class Category(BaseModel):
    id: int
    name: str


class CategoryWithTotal(Category):
    total_expenses: int


class ExpenseCreate(BaseModel):
    title: NonEmptyStr = Field(examples=["Lunch"])
    amount: float = Field(gt=0, examples=[250.5])
    category_id: int = Field(examples=[1])


class Expense(BaseModel):
    id: int
    title: str
    amount: float
    category_id: int
    created_at: datetime


class ExpenseWithCategory(BaseModel):
    id: int
    title: str
    amount: float
    category: str
    created_at: datetime


class Summary(BaseModel):
    total: float
    count: int
    average: float
