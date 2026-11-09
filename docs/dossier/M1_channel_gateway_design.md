# M1 Channel & Gateway Design

## API Resource Model
- `POST /v1/transfers`: Initiates a wallet-to-wallet transfer.
- `GET /v1/transfers/{id}`: Retrieves transfer status.
- `GET /v1/wallets/{id}/balance`: Retrieves wallet balance.

## Error Catalogue
- `400 MISSING_IDEMPOTENCY_KEY`: Header is absent.
- `422 SAME_WALLET`: Sender and receiver are identical.
- `422 INVALID_AMOUNT`: Amount is <= 0 or > 1,000,000 PKR.
- `422 UNSUPPORTED_CURRENCY`: Currency is not PKR.
- `503 DOWNSTREAM_UNAVAILABLE`: Txn service is down.

## Correlation ID Rules
Every request receives an `X-Correlation-ID` header. If none is provided, the Gateway generates a UUID v4. This ID is passed to all downstream services.