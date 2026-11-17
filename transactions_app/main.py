import httpx
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from transactions_app.transaction_models import Transaction, TransactionType
from app.db import get_connection

app = FastAPI(title="Transactions API")
security = HTTPBearer()

# Temporary in-memory idempotency cache — same pattern as Module 20
idempotency_cache = {}

ACCOUNTS_API_URL = "http://localhost:8001"


def check_account_active(account_id: str, token: str):
    """
    Returns a tuple: (is_active: bool, account_data: dict | None)
    Raises HTTPException(404) if the account doesn't exist,
    and HTTPException(503) if the Accounts API can't be reached.
    """
    try:
        response = httpx.get(
            f"{ACCOUNTS_API_URL}/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=3.0
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Accounts service unavailable"
        )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Account not found")

    if response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail="Accounts service returned an unexpected response"
        )

    account_data = response.json()
    is_active = account_data.get("status", "").lower() == "active"
    return is_active, account_data


@app.post("/transactions", status_code=201)
def create_transaction(
    txn: Transaction,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    idempotency_key: str = Header(...)
):
    request_fingerprint = f"{txn.account_id}:{txn.type.value}:{txn.amount}"

    # 1. Check idempotency — including conflict detection
    if idempotency_key in idempotency_cache:
        cached = idempotency_cache[idempotency_key]
        if cached["request_fingerprint"] != request_fingerprint:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key already used with different request data"
            )
        return cached["result"]

    # 2. Extract token
    token = credentials.credentials

    # 3. Verify account exists and is active
    is_active, account_data = check_account_active(txn.account_id, token)
    if not is_active:
        raise HTTPException(
            status_code=409,
            detail="Account is not active"
        )

    # 4. Insufficient-funds check — withdrawals only
    if txn.type == TransactionType.withdrawal:
        balance = account_data.get("balance", 0)
        if txn.amount > balance:
            raise HTTPException(
                status_code=422,
                detail="Insufficient funds for this withdrawal"
            )
        # updating balance
    try:
        response = httpx.patch(
            f"{ACCOUNTS_API_URL}/accounts/{txn.account_id}/balance",
            json={
                "type": txn.type.value,
                "amount": str(txn.amount)
            },
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=3.0
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Accounts service unavailable"
        )

    if response.status_code != 200:
        if response.status_code in (404, 409, 422):
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "detail", "Balance update failed"
                )
            )

        raise HTTPException(
            status_code=503,
            detail="Accounts service failed to update balance"
        )

    # 5. Connect to database
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 6. Insert transaction
        cur.execute(
            """
            INSERT INTO transactions
            (id, account_id, type, amount, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                txn.id,
                txn.account_id,
                txn.type.value,
                txn.amount,
                txn.status
            )
        )

        # 7. Commit
        conn.commit()

        # 8. Store response for idempotency
        idempotency_cache[idempotency_key] = {
            "request_fingerprint": request_fingerprint,
            "result": txn
        }

        # 9. Return transaction
        return txn

    except HTTPException:
        raise

    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to create transaction")

    finally:
        cur.close()
        conn.close()


@app.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, account_id, type, amount, status, created_at
            FROM transactions
            WHERE id = %s
            """,
            (transaction_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {
            "id": row[0],
            "account_id": row[1],
            "type": row[2],
            "amount": float(row[3]),
            "status": row[4],
            "created_at": row[5]
        }
    finally:
        cur.close()
        conn.close()
