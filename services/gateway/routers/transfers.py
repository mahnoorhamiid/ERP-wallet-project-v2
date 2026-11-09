"""POST /v1/transfers and GET /v1/transfers/{id}."""
import os
import re
import uuid
import sqlite3
import json
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from libs.common.correlation import get_correlation_id
from libs.common.clock import now
from libs.common.events import EventEnvelope, EventType, TransferInitiatedData
from services.gateway.idempotency import begin, complete, hash_request, is_stale

router = APIRouter()
IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
MAX_TRANSFER_MINOR = 100_000_000

class TransferRequest(BaseModel):
    sender_wallet_id: str = Field(pattern=r"^W-[A-Z0-9]{3,12}$")
    receiver_wallet_id: str = Field(pattern=r"^W-[A-Z0-9]{3,12}$")
    amount_minor: int
    currency: str = "PKR"
    reference: str | None = Field(default=None, max_length=140)

class TransferResponse(BaseModel):
    transfer_id: str
    status: str
    sender_wallet_id: str
    receiver_wallet_id: str
    amount_minor: int
    currency: str
    failure_reason: str | None = None
    hold_reason_code: str | None = None
    correlation_id: str
    created_at: str
    updated_at: str

def _error(code: str, message: str, status: int) -> HTTPException:
    return HTTPException(status_code=status, detail={
        "code": code, "message": message,
        "correlation_id": get_correlation_id(),
    })

@router.post("/v1/transfers", status_code=201)
async def create_transfer(
    body: TransferRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    authorization: str | None = Header(default=None),
):
    # 1. header checks
    if not idempotency_key:
        raise _error("MISSING_IDEMPOTENCY_KEY", "Idempotency-Key header required", 400)
    if not IDEMPOTENCY_RE.match(idempotency_key):
        raise _error("VALIDATION_ERROR", "Bad Idempotency-Key format", 422)
    if not authorization or not authorization.startswith("Bearer "):
        raise _error("UNAUTHORIZED", "Bearer token required", 401)

    client_id = "demo-client"  # TODO: replace with JWT sub later

    # 2. body validation beyond Pydantic
    if body.sender_wallet_id == body.receiver_wallet_id:
        raise _error("SAME_WALLET", "Sender and receiver must differ", 422)
    if body.amount_minor <= 0 or body.amount_minor > MAX_TRANSFER_MINOR:
        raise _error("INVALID_AMOUNT", "Amount out of range", 422)
    if body.currency != "PKR":
        raise _error("UNSUPPORTED_CURRENCY", "Only PKR supported", 422)

    # 3. hash
    rh = hash_request(body.model_dump())
    
    # Get sqlite3 connection from app.state
    conn = request.app.state.db_conn
    try:
        row, is_new = begin(conn, client_id, idempotency_key, rh)

        if not is_new:
            if row["request_hash"] != rh:
                raise _error("IDEMPOTENCY_KEY_REUSED", "Same key, different body", 422)
            if row["state"] == "COMPLETED":
                # replay
                from fastapi.responses import JSONResponse
                body_dict = json.loads(row["response_body"]) if isinstance(row["response_body"], str) else row["response_body"]
                return JSONResponse(
                    content=body_dict, status_code=row["response_code"],
                    headers={"Idempotent-Replayed": "true"},
                )
            if not is_stale(row):
                raise _error("REQUEST_IN_PROGRESS", "Retry after 1s", 409)
            # stale: reuse stored IDs, re-send
            transfer_id = row["transfer_id"]
            event_id = row["event_id"]
        else:
            transfer_id = str(uuid.uuid4())
            event_id = str(uuid.uuid4())
            # update row with generated IDs
            conn.execute("UPDATE gw_idempotency SET transfer_id=?, event_id=? WHERE client_id=? AND idempotency_key=?", (transfer_id, event_id, client_id, idempotency_key))
            conn.commit()

        # 4. build event
        envelope = EventEnvelope(
            event_id=uuid.UUID(event_id),
            event_type=EventType.TRANSFER_INITIATED,
            occurred_at=now(),
            producer="gateway",
            correlation_id=uuid.UUID(get_correlation_id()),
            data=TransferInitiatedData(
                transfer_id=uuid.UUID(transfer_id),
                idempotency_key=idempotency_key,
                sender_wallet_id=body.sender_wallet_id,
                receiver_wallet_id=body.receiver_wallet_id,
                amount_minor=body.amount_minor,
                currency="PKR",
                reference=body.reference,
                channel="customer_app",
            ).model_dump(mode="json"),
        )

        # 5. call txn (STUBBED FOR NOW)
        # In the real chain, this will be an HTTP call to M2's service.
        # For now, we fake a successful DEBITED snapshot.
        snapshot = {
            "transfer_id": transfer_id,
            "state": "DEBITED",
            "failure_reason": None,
            "hold_reason_code": None,
        }

        # 6. store response
        response_body = {
            "transfer_id": snapshot["transfer_id"],
            "status": snapshot["state"],
            "sender_wallet_id": body.sender_wallet_id,
            "receiver_wallet_id": body.receiver_wallet_id,
            "amount_minor": body.amount_minor,
            "currency": "PKR",
            "failure_reason": snapshot.get("failure_reason"),
            "hold_reason_code": snapshot.get("hold_reason_code"),
            "correlation_id": get_correlation_id(),
            "created_at": now().isoformat().replace("+00:00", "Z"),
            "updated_at": now().isoformat().replace("+00:00", "Z"),
        }
        
        complete(conn, client_id, idempotency_key, 201, response_body)
        return response_body
        
    finally:
        pass  # connection stays open for app lifespan