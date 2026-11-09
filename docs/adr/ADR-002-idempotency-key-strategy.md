# ADR 002: Idempotency Key Strategy

## Context
Customers may double-click "Send" or experience network timeouts and retry. Without protection, this results in double debits.

## Decision
The Gateway requires a unique `Idempotency-Key` header. We store this in the `gw_idempotency` table. If a request arrives with the same key and body, we return the stored response and add the `Idempotent-Replayed: true` header. If the key is used with a different body, we return `422 IDEMPOTENCY_KEY_REUSED`.

## Consequences
- Positive: Prevents double charges safely.
- Negative: Requires a database lookup on every POST request.