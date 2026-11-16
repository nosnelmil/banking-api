# Accounts API — Responsibility Map
 
## Infrastructure Team owns:
- The Linux VM, Docker, and the Postgres container itself
- Network routing between the Windows and Linux VMs
- VM scaling and uptime
 
## API Team owns:
- The OpenAPI contract
- Request validation and business logic (e.g. balance >= 0)
- Error messages and status codes
- Authentication logic (verifying the token's claims)
