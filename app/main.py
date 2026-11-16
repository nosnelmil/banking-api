from fastapi import FastAPI, HTTPException
from app.models import Account
 
app = FastAPI(title="Accounts API")
accounts_db = []  # temporary in-memory list — replaced with Postgres in Module 5
 
# creating end point for the accounts api
@app.post("/accounts")
def create_account(account: Account):
    accounts_db.append(account)
    return account
 
# creating end point for the accounts id to get information api
@app.get("/accounts/{account_id}")
def get_account(account_id: str):
    for acc in accounts_db:
        if acc.id == account_id:
            return acc
    raise HTTPException(status_code=404, detail="Account not found")
