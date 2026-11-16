from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import uuid
from app.models import Account
from app.db import get_connection
from app.auth import verify_token
from fastapi.exceptions import RequestValidationError 

app = FastAPI(title="Accounts API")
 
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
        "INSERT INTO accounts (id, owner_name, balance) VALUES (%s, %s, %s)",
        (account.id, account.owner_name, account.balance),
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
 
@app.get("/health/live")
def liveness():
    return {"status": "alive"}
 
@app.get("/health/ready")
def readiness():
    return {"status": "ready"}
