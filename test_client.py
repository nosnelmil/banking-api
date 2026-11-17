import httpx
import time
 
LINUX_VM_IP = "localhost"  # replace with your actual Linux VM’s IP, e.g. 13.233.137.96
 
def call_account(account_id: str, token: str, retries: int = 2):
    for attempt in range(retries + 1):  # try once, then retry up to `retries` more times
        try:
            response = httpx.get(
                f"http://{LINUX_VM_IP}:8001/v1/accounts/{account_id}",
                headers={"Authorization": f"Bearer {token}"},  # forward the caller’s identity
                timeout=3.0,  # give up waiting after 3 seconds
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)  # wait longer after each failed attempt (backoff)
    raise Exception("All retries failed")
