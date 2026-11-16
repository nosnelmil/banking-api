from fastmcp import FastMCP
import asyncio
import psycopg2
mcp = FastMCP("Bank Account Services")


@mcp.tool
async def verify_account(account_id: str) -> dict:
    """
    Verify whether a bank account exists in PostgreSQL.
    """
    print(f"Starting verification for account {account_id}")
    # Simulate external verification delay
    await asyncio.sleep(2)

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="banking",
        user="postgres",
        password="bankpass123"
    )
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, owner_name FROM accounts WHERE id = %s",
        (account_id,)
    )
    account = cursor.fetchone()

    cursor.close()
    conn.close()
    verified = account is not None
    print(f"Verification completed for account {account_id}")
    return {
        "account_id": account_id,
        "owner_name": account[1] if verified else None,
        "verified": verified
    }

if __name__ == "__main__":
    mcp.run()
