from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select, text
from services.txn.db import init_db, SessionLocal
from services.txn import models, ledger
from libs.common.clock import now
import httpx
import os
import uuid
import sqlite3
from libs.common.outbox import init_outbox

COMPLIANCE_URL = os.getenv("COMPLIANCE_URL", "http://127.0.0.1:8002")
RAIL_URL = os.getenv("RAIL_URL", "http://127.0.0.1:8004")

@asynccontextmanager
async def lifespan(app):
    init_db()
    
    # Initialize the raw SQLite outbox table
    conn = sqlite3.connect("txn.db")
    init_outbox(conn)
    conn.close()
    
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
    if not t: raise HTTPException(404, "TRANSFER_NOT_FOUND")
    return snapshot(t)

@app.get("/internal/v1/wallets/{wallet_id}/balance")
def get_balance(wallet_id: str, s=Depends(db)):
    return {"wallet_id": wallet_id, "balance_minor": ledger.get_balance(s, wallet_id), "currency": "PKR"}

# ==========================================
# PART 2: EVENT INGESTION & ORCHESTRATION
# ==========================================

@app.post("/internal/v1/events")
def ingest_event(envelope: dict, s=Depends(db)):
    event_id = envelope["event_id"]
    existing = s.get(models.Inbox, event_id)
    if existing: return {"status": "duplicate", "snapshot": existing.result_snapshot}

    etype = envelope["event_type"]
    
    if etype == "transfer.initiated":
        snap = _handle_initiated(s, envelope)
    elif etype == "rail.settlement_confirmed":
        snap = _handle_settlement(s, envelope)
    elif etype == "hold.resolved":
        snap = _handle_hold(s, envelope)
    else:
        raise HTTPException(422, "UNKNOWN_EVENT_TYPE")

    s.add(models.Inbox(event_id=event_id, event_type=etype, processed_at=now(), result_snapshot=snap))
    s.commit()
    return snap

def _handle_initiated(s, env):
    from services.txn.state_machine import transition
    d = env["data"]; corr = env["correlation_id"]; eid = env["event_id"]
    
    t = models.Transfer(transfer_id=d["transfer_id"], sender_wallet_id=d["sender_wallet_id"],
        receiver_wallet_id=d["receiver_wallet_id"], amount_minor=d["amount_minor"], currency=d["currency"],
        state="INITIATED", version=0, correlation_id=corr, created_at=now(), updated_at=now())
    s.add(t); s.flush()

    if ledger.get_balance(s, t.sender_wallet_id) < 0:
        transition(s, t.transfer_id, "FAILED", "WALLET_NOT_FOUND", eid); s.commit()
        return snapshot(s.get(models.Transfer, t.transfer_id))
        
    transition(s, t.transfer_id, "SCREENING", None, eid)

    try:
        r = httpx.post(f"{COMPLIANCE_URL}/internal/v1/screen", json={
            "transfer_id": t.transfer_id, "sender_wallet_id": t.sender_wallet_id,
            "receiver_wallet_id": t.receiver_wallet_id, "amount_minor": t.amount_minor,
            "currency": t.currency, "correlation_id": corr}, timeout=2.0)
        r.raise_for_status()
        decision = r.json()["decision"]
    except Exception:
        transition(s, t.transfer_id, "FAILED", "SCREENING_UNAVAILABLE", eid); s.commit()
        return snapshot(s.get(models.Transfer, t.transfer_id))

    if decision == "REJECT":
        transition(s, t.transfer_id, "REJECTED", "REJECT", eid); s.commit()
        return snapshot(s.get(models.Transfer, t.transfer_id))
    if decision == "HOLD":
        transition(s, t.transfer_id, "ON_HOLD", "HOLD", eid); s.commit()
        return snapshot(s.get(models.Transfer, t.transfer_id))

    try:
        ledger.post_debit_leg(s, t, eid)
        transition(s, t.transfer_id, "DEBITED", "ALLOW", eid)
        s.commit()
    except ledger.InsufficientFunds:
        s.rollback()
        transition(s, t.transfer_id, "FAILED", "INSUFFICIENT_FUNDS", eid); s.commit()
        return snapshot(s.get(models.Transfer, t.transfer_id))

    return _call_rail_and_settle(s, t, eid)

def _call_rail_and_settle(s, t, eid):
    from services.txn.state_machine import transition
    try:
        r = httpx.post(f"{RAIL_URL}/rail/v1/settlements", json={
            "transfer_id": t.transfer_id, "amount_minor": t.amount_minor, "currency": t.currency,
            "sender_wallet_id": t.sender_wallet_id, "receiver_wallet_id": t.receiver_wallet_id,
            "callback_url": "http://127.0.0.1:8001/internal/v1/events", "correlation_id": t.correlation_id}, timeout=2.0)
        r.raise_for_status()
        status = r.json()["status"]
    except Exception:
        try:
            q = httpx.get(f"{RAIL_URL}/rail/v1/settlements/{t.transfer_id}", timeout=2.0).json()
            status = q["status"]
        except Exception:
            status = "UNKNOWN"
        if status != "SETTLED": return _compensate(s, t, eid, set_recon=True)

    if status == "SETTLED":
        ledger.post_credit_leg(s, t, eid)
        transition(s, t.transfer_id, "COMPLETED", "SETTLED", eid)
        s.commit()
        return snapshot(s.get(models.Transfer, t.transfer_id))
    else:
        return _compensate(s, t, eid)

def _compensate(s, t, eid, set_recon=False):
    from services.txn.state_machine import transition
    dj = s.execute(select(models.LedgerJournal).where(
        models.LedgerJournal.transfer_id == t.transfer_id, models.LedgerJournal.leg == "DEBIT_LEG")).scalar_one()
    transition(s, t.transfer_id, "COMPENSATING", "REJECTED", eid)
    ledger.post_reversal_leg(s, t, dj.journal_id, eid)
    transition(s, t.transfer_id, "REVERSED", "REVERSAL_POSTED", eid)
    if set_recon: s.get(models.Transfer, t.transfer_id).recon_flag = True
    s.commit()
    return snapshot(s.get(models.Transfer, t.transfer_id))

def _handle_settlement(s, env):
    from services.txn.state_machine import transition
    d = env["data"]; t = s.get(models.Transfer, d["transfer_id"])
    if not t: raise HTTPException(404, "TRANSFER_NOT_FOUND")
    if t.state == "COMPLETED": return snapshot(t)
    if t.state == "DEBITED" and d["amount_minor"] == t.amount_minor:
        ledger.post_credit_leg(s, t, env["event_id"])
        transition(s, t.transfer_id, "COMPLETED", "SETTLED", env["event_id"])
        s.commit(); return snapshot(s.get(models.Transfer, t.transfer_id))
    return snapshot(t)

def _handle_hold(s, env):
    from services.txn.state_machine import transition
    d = env["data"]; t = s.get(models.Transfer, d["transfer_id"])
    if t.state != "ON_HOLD": return snapshot(t)
    if d["decision"] == "RELEASE":
        try:
            ledger.post_debit_leg(s, t, env["event_id"])
            transition(s, t.transfer_id, "DEBITED", "RELEASE", env["event_id"])
            s.commit()
            return _call_rail_and_settle(s, t, env["event_id"])
        except ledger.InsufficientFunds:
            s.rollback()
            transition(s, t.transfer_id, "FAILED", "INSUFFICIENT_FUNDS", env["event_id"])
    else:
        transition(s, t.transfer_id, "REJECTED", "REJECT", env["event_id"])
    s.commit()
    return snapshot(s.get(models.Transfer, t.transfer_id))