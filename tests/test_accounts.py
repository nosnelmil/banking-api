import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_connection
 
client = TestClient(app)
 
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyaWNoYSJ9.3KtM4et7OksbmSJqIA7r0d2hJtRv647HqkawMKpGlYc"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}
 
 
@pytest.fixture
def new_account_id():
    # Generates a fresh, unique account id for every test run, and removes
    # that row afterwards — so the suite can be run again and again without
    # failing on a 409 from leftover data created by the last run.
    account_id = f"test-{uuid.uuid4().hex[:8]}"
    yield account_id
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
    conn.commit()
    cur.close()
    conn.close()
 
 
def test_create_account_compliance(new_account_id):  # COMPLIANCE TEST
    response = client.post(
        "/accounts",
        headers=HEADERS,
        json={"id": new_account_id, "owner_name": "Test User", "balance": 50.0},
    )
    assert response.status_code == 201
 
 
def test_create_account_negative_bad_balance():  # NEGATIVE TEST
    response = client.post(
        "/accounts",
        headers=HEADERS,
        json={"id": f"test-{uuid.uuid4().hex[:8]}", "owner_name": "Test User", "balance": -10.0},
    )
    assert response.status_code == 422
 
 
def test_create_account_requires_auth():  # COMPLIANCE TEST — authentication
    response = client.post(
        "/accounts",
        json={"id": f"test-{uuid.uuid4().hex[:8]}", "owner_name": "Test User", "balance": 50.0},
    )
    assert response.status_code == 401
 
 
def test_create_account_duplicate_rejected(new_account_id):  # NEGATIVE TEST — duplicate
    payload = {"id": new_account_id, "owner_name": "Test User", "balance": 50.0}
    first = client.post("/accounts", headers=HEADERS, json=payload)
    assert first.status_code == 201
    second = client.post("/accounts", headers=HEADERS, json=payload)
    assert second.status_code == 409
 
 
def test_get_account_not_found():  # NEGATIVE TEST — missing account
    response = client.get("/accounts/does-not-exist", headers=HEADERS)
    assert response.status_code == 404
 
 
def test_v1_accounts_has_deprecation_headers():  # COMPLIANCE TEST — Module 12 versioning
    response = client.get("/v1/accounts", headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["Deprecation"] == "true"
    assert response.headers["Sunset"] == "2026-12-31"
 
 
def test_v2_accounts_has_account_tier():  # COMPLIANCE TEST — Module 12 versioning
    response = client.get("/v2/accounts", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert all("account_tier" in a for a in body)
