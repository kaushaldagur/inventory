import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


os.environ["DATABASE_URL"] = "sqlite:////tmp/test_inventory.db"
os.environ["JWT_SECRET"] = "test-secret"
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.user_service import create_user_account  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def register_user(client, email="user@example.com", password="password123", full_name="Test User"):
    db = SessionLocal()
    try:
        create_user_account(db, full_name=full_name, email=email, password=password)
    finally:
        db.close()
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    data = response.json()
    return data["access_token"], data["user"]


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_product(client, token, sku="SKU-1", quantity=10, price=25.50):
    response = client.post(
        "/products",
        headers=auth_headers(token),
        json={
            "name": "Desk Lamp",
            "sku": sku,
            "price": price,
            "quantity_in_stock": quantity,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_customer(client, token, email="customer@example.com"):
    response = client.post(
        "/customers",
        headers=auth_headers(token),
        json={
            "full_name": "Avery Morgan",
            "email": email,
            "phone_number": "555-0101",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_product_sku_must_be_unique_per_user(client):
    token_a, _ = register_user(client, email="a@example.com")
    token_b, _ = register_user(client, email="b@example.com")

    create_product(client, token_a, sku="SHARED-SKU")

    duplicate = client.post(
        "/products",
        headers=auth_headers(token_a),
        json={"name": "Dup", "sku": "SHARED-SKU", "price": 1, "quantity_in_stock": 1},
    )
    assert duplicate.status_code == 409

    other_user_same_sku = client.post(
        "/products",
        headers=auth_headers(token_b),
        json={"name": "Allowed", "sku": "SHARED-SKU", "price": 1, "quantity_in_stock": 1},
    )
    assert other_user_same_sku.status_code == 201


def test_users_cannot_see_each_others_data(client):
    token_a, _ = register_user(client, email="owner-a@example.com")
    token_b, _ = register_user(client, email="owner-b@example.com")

    product_a = create_product(client, token_a, sku="A-SKU")
    create_product(client, token_b, sku="B-SKU")

    list_a = client.get("/products", headers=auth_headers(token_a)).json()
    list_b = client.get("/products", headers=auth_headers(token_b)).json()

    assert len(list_a) == 1
    assert list_a[0]["sku"] == "A-SKU"
    assert len(list_b) == 1
    assert list_b[0]["sku"] == "B-SKU"

    assert client.get(f"/products/{product_a['id']}", headers=auth_headers(token_b)).status_code == 404


def test_product_management_crud_endpoints_and_required_fields(client):
    token, _ = register_user(client)

    create_response = client.post(
        "/products",
        headers=auth_headers(token),
        json={
            "name": "Wireless Mouse",
            "sku": "MOUSE-1",
            "price": 29.99,
            "quantity_in_stock": 12,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    product_id = created["id"]

    list_response = client.get("/products", headers=auth_headers(token))
    assert list_response.status_code == 200
    assert any(product["id"] == product_id for product in list_response.json())

    detail_response = client.get(f"/products/{product_id}", headers=auth_headers(token))
    assert detail_response.status_code == 200

    update_response = client.put(
        f"/products/{product_id}",
        headers=auth_headers(token),
        json={
            "name": "Wireless Mouse Pro",
            "sku": "MOUSE-1-PRO",
            "price": 39.99,
            "quantity_in_stock": 9,
        },
    )
    assert update_response.status_code == 200

    delete_response = client.delete(f"/products/{product_id}", headers=auth_headers(token))
    assert delete_response.status_code == 204
    assert client.get(f"/products/{product_id}", headers=auth_headers(token)).status_code == 404


def test_customer_email_must_be_unique_per_user(client):
    token, _ = register_user(client)
    create_customer(client, token, email="unique@example.com")

    response = client.post(
        "/customers",
        headers=auth_headers(token),
        json={
            "full_name": "Second Customer",
            "email": "unique@example.com",
            "phone_number": "555-0102",
        },
    )
    assert response.status_code == 409


def test_customer_management_crud_endpoints_and_required_fields(client):
    token, _ = register_user(client)

    create_response = client.post(
        "/customers",
        headers=auth_headers(token),
        json={
            "full_name": "Jordan Lee",
            "email": "jordan@example.com",
            "phone_number": "555-2020",
        },
    )
    assert create_response.status_code == 201
    customer_id = create_response.json()["id"]

    assert client.get("/customers", headers=auth_headers(token)).status_code == 200
    assert client.get(f"/customers/{customer_id}", headers=auth_headers(token)).status_code == 200
    assert client.delete(f"/customers/{customer_id}", headers=auth_headers(token)).status_code == 204


def test_product_quantity_cannot_be_negative(client):
    token, _ = register_user(client)
    response = client.post(
        "/products",
        headers=auth_headers(token),
        json={"name": "Invalid", "sku": "NEG-1", "price": 10, "quantity_in_stock": -1},
    )
    assert response.status_code == 422


def test_order_rejects_insufficient_inventory(client):
    token, _ = register_user(client)
    product = create_product(client, token, quantity=2)
    customer = create_customer(client, token)

    response = client.post(
        "/orders",
        headers=auth_headers(token),
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": 3}],
        },
    )
    assert response.status_code == 409
    assert client.get(f"/products/{product['id']}", headers=auth_headers(token)).json()["quantity_in_stock"] == 2


def test_order_reduces_stock_and_calculates_total_in_backend(client):
    token, _ = register_user(client)
    product = create_product(client, token, quantity=10, price=19.99)
    customer = create_customer(client, token)

    response = client.post(
        "/orders",
        headers=auth_headers(token),
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": 3}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total_amount"] == "59.97"
    assert client.get(f"/products/{product['id']}", headers=auth_headers(token)).json()["quantity_in_stock"] == 7


def test_order_management_endpoints_and_required_fields(client):
    token, _ = register_user(client)
    product = create_product(client, token, sku="ORDER-SKU-1", quantity=10, price=12.50)
    customer = create_customer(client, token, email="orders@example.com")

    create_response = client.post(
        "/orders",
        headers=auth_headers(token),
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": 4}],
        },
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["id"]

    assert client.get("/orders", headers=auth_headers(token)).status_code == 200
    assert client.get(f"/orders/{order_id}", headers=auth_headers(token)).status_code == 200
    assert client.get(f"/products/{product['id']}", headers=auth_headers(token)).json()["quantity_in_stock"] == 6
    assert client.delete(f"/orders/{order_id}", headers=auth_headers(token)).status_code == 204


def test_login_after_admin_created_user(client):
    db = SessionLocal()
    try:
        create_user_account(
            db,
            full_name="Test User",
            email="testuser@example.com",
            password="strongpassword",
        )
    finally:
        db.close()

    login_response = client.post(
        "/auth/login",
        json={"email": "testuser@example.com", "password": "strongpassword"},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert "access_token" in body
    assert body["user"]["email"] == "testuser@example.com"


def test_protected_routes_require_auth(client):
    assert client.get("/products").status_code == 401


def test_order_payload_is_validated_before_processing(client):
    token, _ = register_user(client)
    product = create_product(client, token, quantity=10)
    customer = create_customer(client, token)

    response = client.post(
        "/orders",
        headers=auth_headers(token),
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": 0}],
        },
    )
    assert response.status_code == 422
