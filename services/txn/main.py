from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select, text
from services.txn.db import init_db, SessionLocal
from services.txn import models, ledger
from libs.common.clock import now
import uuid

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

def db():
    s = SessionLocal()
    try: 
        yield s
    finally: 
        s.close()

@app.get("/health")
def health(): 
    return {"status": "ok"}

@app.get("/ready")
def ready(s=Depends(db)):
    s.execute(text("SELECT 1"))
    return {"status": "ready"}

def snapshot(t):
    return {"transfer_id": t.transfer_id, "state": t.state,
            "failure_reason": t.failure_reason, "hold_reason_code": t.hold_reason_code,
            "amount_minor": t.amount_minor, "currency": t.currency,
            "sender_wallet_id": t.sender_wallet_id, "receiver_wallet_id": t.receiver_wallet_id,
            "correlation_id": t.correlation_id,
            "created_at": t.created_at.isoformat(), "updated_at": t.updated_at.isoformat()}

@app.get("/internal/v1/transfers/{transfer_id}")
def get_transfer(transfer_id: str, s=Depends(db)):
    t = s.get(models.Transfer, transfer_id)
    if not t: 
        raise HTTPException(404, "TRANSFER_NOT_FOUND")
    return snapshot(t)

@app.get("/internal/v1/wallets/{wallet_id}/balance")
def get_balance(wallet_id: str, s=Depends(db)):
    return {"wallet_id": wallet_id, "balance_minor": ledger.get_balance(s, wallet_id),
            "currency": "PKR"}