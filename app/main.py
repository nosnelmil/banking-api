from fastapi import FastAPI, HTTPException
from app.models import Account
 
 
from app.db import get_connection   #import this new line in main.py

import uuid
 
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException

import psycopg2


app = FastAPI(title="Accounts API")
accounts_db = []  # temporary in-memory list — replaced with Postgres in Module 5
 
#replace old create_account method with below one
@app.post("/accounts")
def create_account(account: Account):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO accounts (id, owner_name, balance) VALUES (%s, %s, %s)",
            (account.id, account.owner_name, account.balance),
        )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"Account with id {account.id} already exists",
        )
    conn.close()
    return account

 

#replace old get_account method with below one
@app.get("/accounts/{account_id}")
def get_account(account_id: str):
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
    return {"id": row[0], "owner_name": row[1], "balance": row[2]}


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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "request_error",
            "message": exc.detail,
            "trace_id": request.state.trace_id,
        },
    )
