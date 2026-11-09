# M1 Idempotency & Retry Design

## The Algorithm
1. Check the `gw_idempotency` table for the client ID and key.
2. If not found, insert as `IN_PROGRESS` and process the request.
3. If found and `COMPLETED`, return the stored response.
4. If found and `IN_PROGRESS` (age < 30s), return `409 REQUEST_IN_PROGRESS`.
5. If found and `IN_PROGRESS` (age > 30s), treat as a crashed attempt and retry.

## Client Actions on Failure
- **Timeout:** Retry with the same Idempotency-Key.
- **503 Service Unavailable:** Wait 2 seconds and retry with the same key.
- **409 Conflict:** Wait 1 second and retry with the same key.