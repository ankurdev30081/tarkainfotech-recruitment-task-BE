import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def create_category(client, name="Food"):
    return client.post("/categories", json={"name": name}).json()


# ---------- Categories ----------

def test_create_category(client):
    res = client.post("/categories", json={"name": "Food"})
    assert res.status_code == 201
    assert res.json() == {"id": 1, "name": "Food"}


def test_create_category_trims_name(client):
    res = client.post("/categories", json={"name": "  Travel  "})
    assert res.json()["name"] == "Travel"


def test_duplicate_category_rejected(client):
    create_category(client, "Food")
    res = client.post("/categories", json={"name": "food"})
    assert res.status_code == 409
    assert res.json()["detail"] == "Category already exists"


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}, {}])
def test_invalid_category_name(client, body):
    assert client.post("/categories", json=body).status_code == 422


def test_list_categories_with_total_expenses(client):
    food = create_category(client, "Food")
    create_category(client, "Travel")
    for title in ["Lunch", "Dinner", "Snack"]:
        client.post("/expenses", json={"title": title, "amount": 10, "category_id": food["id"]})

    res = client.get("/categories")
    assert res.status_code == 200
    assert res.json() == [
        {"id": 1, "name": "Food", "total_expenses": 3},
        {"id": 2, "name": "Travel", "total_expenses": 0},
    ]


# ---------- Expenses ----------

def test_create_expense(client):
    cat = create_category(client)
    res = client.post("/expenses", json={"title": "Lunch", "amount": 250.5, "category_id": cat["id"]})
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == 1
    assert data["title"] == "Lunch"
    assert data["amount"] == 250.5
    assert data["category_id"] == cat["id"]
    assert "created_at" in data


def test_expense_requires_existing_category(client):
    res = client.post("/expenses", json={"title": "Lunch", "amount": 10, "category_id": 999})
    assert res.status_code == 400
    assert res.json()["detail"] == "Category does not exist"


@pytest.mark.parametrize(
    "body",
    [
        {"title": "", "amount": 10},
        {"title": "   ", "amount": 10},
        {"title": "Lunch", "amount": 0},
        {"title": "Lunch", "amount": -5},
        {"title": "Lunch", "amount": "abc"},
        {"amount": 10},
    ],
)
def test_invalid_expense_input(client, body):
    cat = create_category(client)
    res = client.post("/expenses", json={**body, "category_id": cat["id"]})
    assert res.status_code == 422


def test_list_expenses_includes_category_name(client):
    cat = create_category(client, "Food")
    client.post("/expenses", json={"title": "Lunch", "amount": 250.5, "category_id": cat["id"]})

    res = client.get("/expenses")
    assert res.status_code == 200
    [expense] = res.json()
    assert expense["title"] == "Lunch"
    assert expense["amount"] == 250.5
    assert expense["category"] == "Food"
    assert "created_at" in expense


def test_list_expenses_empty(client):
    assert client.get("/expenses").json() == []


# ---------- Summary ----------

def test_summary_empty(client):
    assert client.get("/summary").json() == {"total": 0, "count": 0, "average": 0}


def test_summary(client):
    cat = create_category(client)
    client.post("/expenses", json={"title": "Lunch", "amount": 250.5, "category_id": cat["id"]})
    client.post("/expenses", json={"title": "Dinner", "amount": 180, "category_id": cat["id"]})

    assert client.get("/summary").json() == {"total": 430.5, "count": 2, "average": 215.25}


# ---------- Docs ----------

def test_openapi_docs_available(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/categories", "/expenses", "/summary"} <= set(paths)
