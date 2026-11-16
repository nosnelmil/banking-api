from fastmcp import FastMCP
import asyncio
 
mcp = FastMCP("Bank Account Services")
 
@mcp.tool
async def verify_account(account_id: str) -> dict:
    """
    Verify a bank account using an external verification service.
    """
    print(f"Starting verification for account {account_id}")
    # Simulate slow external KYC service
    await asyncio.sleep(2)
    print(f"Verification completed for account {account_id}")

    return {
        "account_id": account_id,
        "verified": True
    }
 
if __name__ == "__main__":
    mcp.run()
