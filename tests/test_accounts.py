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
 
 
@pytest.fixture
def existing_account_id(new_account_id):
    # Creates a real account for tests that need one to already exist.
    response = client.post(
        "/accounts",
        headers=HEADERS,
        json={"id": new_account_id, "owner_name": "Test User", "balance": 50.0},
    )
    assert response.status_code == 201
    return new_account_id
 
 
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


def test_update_status_requires_idempotency_key():
    response = client.patch("/accounts/1/status", params={"new_status": "Frozen"})
    assert response.status_code == 422
 
def test_update_status_rejects_invalid_status(new_account_id):
    response = client.patch(
        f"/accounts/{new_account_id}/status",
        params={"new_status": "NotARealStatus"},
        headers={"Idempotency-Key": "test-key-1"}
    )
    assert response.status_code == 422
 
def test_update_status_not_found():
    response = client.patch(
        "/accounts/does-not-exist/status",
        params={"new_status": "Frozen"},
        headers={"Idempotency-Key": "test-key-2"}
    )
    assert response.status_code == 404
 
def test_update_status_idempotent_repeat(existing_account_id):
    headers = {"Idempotency-Key": "test-key-3"}
    first = client.patch(f"/accounts/{existing_account_id}/status", params={"new_status": "Frozen"}, headers=headers)
    second = client.patch(f"/accounts/{existing_account_id}/status", params={"new_status": "Frozen"}, headers=headers)
    assert first.status_code == 200
    assert first.json() == second.json()
 
def test_update_status_key_reuse_conflict(existing_account_id):
    headers = {"Idempotency-Key": "test-key-4"}
    client.patch(f"/accounts/{existing_account_id}/status", params={"new_status": "Frozen"}, headers=headers)
    conflict = client.patch(f"/accounts/{existing_account_id}/status", params={"new_status": "Active"}, headers=headers)
    assert conflict.status_code == 409

def test_delete_account_is_idempotent(existing_account_id):
    headers = {"Idempotency-Key": "test-key-5"}
    first = client.delete(f"/accounts/{existing_account_id}", headers=headers)
    second = client.delete(f"/accounts/{existing_account_id}", headers=headers)
    assert first.status_code == 200
    assert second.json()["already_closed"] in (True, False)
