from fastapi import FastAPI, HTTPException
from app.models import Account
 
app = FastAPI(title="Accounts API")
accounts_db = []  # temporary in-memory list — replaced with Postgres in Module 5
 
from app.db import get_connection   #import this new line in main.py
 
#replace old create_account method with below one
@app.post("/accounts")
def create_account(account: Account):
    conn = get_connection()
    cur = conn.cursor()  # a cursor runs SQL commands over the connection
    cur.execute(
        "INSERT INTO accounts (id, owner_name, balance) VALUES (%s, %s, %s)",  # %s placeholders prevent SQL injection
        (account.id, account.owner_name, account.balance),
    )
    conn.commit()  # actually save the change — without this, nothing persists
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

