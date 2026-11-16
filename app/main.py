from typing import List
from datetime import date  
from psycopg2.extras import execute_values
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import JSONResponse
import uuid
from fastapi import APIRouter
from app.models import (
    Account,
    AccountUpdate,
    AccountStatusUpdate,
    AccountStatus,
    AccountType,
    Currency,
)
from app.db import get_connection   # your existing DB session dependency
import logging
logger = logging.getLogger("uvicorn.error")


from app.auth import verify_token
from fastapi.exceptions import RequestValidationError
from psycopg2 import IntegrityError

import asyncio

logger = logging.getLogger("uvicorn.error")


v1 = APIRouter(prefix="/v1")
v2 = APIRouter(prefix="/v2")


app = FastAPI(title="Accounts API")

@app.middleware("http")
async def add_deprecation_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/v1"):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "2026-12-31"
    return response

 
@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    request.state.trace_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Trace-Id"] = request.state.trace_id
    return response
 
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Something went wrong",
            "trace_id": request.state.trace_id,
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": exc.errors()[0]["msg"],
            "trace_id": request.state.trace_id,
        },
    )

@v1.get("/accounts")
def get_accounts(
    currency: Currency | None = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(verify_token),
):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, owner_name, balance, status,
               account_type, currency, created_at, updated_at
        FROM accounts
    """

    conditions = []
    params = []

    if currency:
        conditions.append("currency = %s")
        params.append(currency.value)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """

    params.extend([limit, offset])

    cur.execute(query, tuple(params))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "id": row[0],
            "owner_name": row[1],
            "balance": float(row[2]),
            "status": row[3],
            "account_type": row[4],
            "currency": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }
        for row in rows
    ]

@v2.get("/accounts")
def get_accounts_v2(user=Depends(verify_token)):
    result = get_accounts(
        currency=None,
        limit=10,
        offset=0,
    )
    for account in result:
        account["account_tier"] = "standard"
    return result


@app.post(
    "/accounts",
    status_code=201,
    responses={
        400: {
            "description": "Validation error",
            "headers": {
                "X-Trace-Id": {
                    "description": "Unique ID for this request",
                    "schema": {"type": "string"},
                }
            },
        },
        401: {"description": "Authentication required"},
        409: {
            "description": "Account already exists",
            "headers": {
                "X-Trace-Id": {
                    "description": "Unique ID for this request",
                    "schema": {"type": "string"},
                }
            },
        },
    },
)
def create_account(account: Account, user=Depends(verify_token)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO accounts
        (id, owner_name, balance, status, account_type, currency)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            account.id,
            account.owner_name,
            account.balance,
            account.status.value,
            account.account_type.value,
            account.currency.value,
        ),
    )
    conn.commit()
    conn.close()
    return account

@app.get(
    "/accounts/{account_id}",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "Account not found"},
    },
)
def get_account(account_id: str, user=Depends(verify_token)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, owner_name, balance FROM accounts WHERE id = %s",
        (account_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"id": row[0], "owner_name": row[1], "balance": float(row[2])}

@app.patch("/v1/accounts/{account_id}")
def update_account(
    account_id: str,
    account: AccountUpdate,
    user=Depends(verify_token),
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check whether account exists
        cur.execute(
            "SELECT id FROM accounts WHERE id = %s",
            (account_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Account not found",
            )
 
        # Build dynamic UPDATE
        updates = account.model_dump(exclude_unset=True)
        fields = []
        params = []
 
        if "balance" in updates:
            fields.append("balance = %s")
            params.append(updates["balance"])
 
        if "status" in updates:
            fields.append("status = %s")
            params.append(updates["status"].value)
 
        if "account_type" in updates:
            fields.append("account_type = %s")
            params.append(updates["account_type"].value)
 
        # Nothing was provided
        if not fields:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update",
            )
 
        # Always update updated_at
        fields.append("updated_at = CURRENT_TIMESTAMP")
 
        query = f"""
            UPDATE accounts
            SET {", ".join(fields)}
            WHERE id = %s
        """
        params.append(account_id)
        cur.execute(query, tuple(params))
        conn.commit()
 
        # Fetch updated account
        cur.execute(
            """
            SELECT
                id,
                owner_name,
                balance,
                status,
                account_type,
                currency,
                created_at,
                updated_at
            FROM accounts
            WHERE id = %s
            """,
            (account_id,),
        )
        row = cur.fetchone()
        return {
            "id": row[0],
            "owner_name": row[1],
            "balance": float(row[2]),
            "status": row[3],
            "account_type": row[4],
            "currency": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }
    finally:
        cur.close()
        conn.close()

@app.post(
    "/accounts/bulk",
    status_code=201,
    responses={
        400: {"description": "Empty list"},
        401: {"description": "Authentication required"},
        409: {"description": "One or more accounts already exist"},
    },
)
def create_accounts_bulk(accounts: List[Account], user=Depends(verify_token)):


    if not accounts:
        raise HTTPException(status_code=400, detail="Send at least one account")


    rows = [
        (
            a.id,
            a.owner_name,
            a.balance,
            a.status.value,
            a.account_type.value,
            a.currency.value,
        )
        for a in accounts
    ]


    conn = get_connection()
    cur = conn.cursor()


    try:
        execute_values(
            cur,
            """
            INSERT INTO accounts
                (id, owner_name, balance, status, account_type, currency)
            VALUES %s
            """,
            rows,
        )
        conn.commit()


        return {"created": len(rows)}


    except IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=409,
            detail="One or more accounts already exist. Nothing was saved.",
        )


    finally:
        cur.close()
        conn.close()


@app.get("/health/live")
def liveness():
    return {"status": "alive"}
 
@app.get("/health/ready")
def readiness(conn = Depends(get_connection)):
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
    except Exception as e:
        logger.error(f"DB check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "not ready", "database": "down"},
        )
    return {"status": "ready", "database": "up"}

@app.post("/accounts/{account_id}/verify")
async def verify_account(account_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM accounts WHERE id = %s",
        (account_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    # Simulate a slow external verification/KYC service
    await asyncio.sleep(2)
    return {
        "account_id": account_id,
        "verified": True
    }


app.include_router(v1)
app.include_router(v2)
