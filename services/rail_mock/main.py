from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
import os, uuid, asyncio

app = FastAPI()
MODE = {"mode": "SUCCESS"}
STORE: dict[str, dict] = {}

class SettleReq(BaseModel):
    transfer_id: str; amount_minor: int; currency: str
    sender_wallet_id: str; receiver_wallet_id: str
    callback_url: str; correlation_id: str

def _mode(h: str | None):
    if os.getenv("RAIL_ALLOW_HEADER_OVERRIDE") == "1" and h:
        return h
    return MODE["mode"]

@app.post("/rail/admin/mode")
def set_mode(mode: str):
    MODE["mode"] = mode
    return MODE

@app.post("/rail/v1/settlements")
async def settle(req: SettleReq, x_mock_rail_mode: str | None = Header(None)):
    if req.transfer_id in STORE:
        return STORE[req.transfer_id]     # idempotent per transfer_id
    
    m = _mode(x_mock_rail_mode)
    if m == "TIMEOUT_NOT_SETTLED":
        await asyncio.sleep(10)
        raise HTTPException(504, "timeout")
        
    ref = f"RAIL-{uuid.uuid4()}"
    
    if m == "REJECT":
        STORE[req.transfer_id] = {"rail_reference": ref, "status": "REJECTED",
            "amount_minor": req.amount_minor,
            "reason_code": "RAIL_REJECT", "settled_at": None}
    elif m == "TIMEOUT_BUT_SETTLED":
        STORE[req.transfer_id] = {"rail_reference": ref, "status": "PENDING",
            "amount_minor": req.amount_minor,
            "reason_code": None, "settled_at": None}
        await asyncio.sleep(10)
        raise HTTPException(504, "timeout")
    else:
        STORE[req.transfer_id] = {"rail_reference": ref, "status": "SETTLED",
            "amount_minor": req.amount_minor,
            "reason_code": None,
            "settled_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
            
    return STORE[req.transfer_id]

@app.get("/rail/v1/settlements/{transfer_id}")
def inquiry(transfer_id: str):
    return STORE.get(transfer_id, {"status": "NOT_FOUND"})

@app.get("/rail/v1/reports/settlements")
def report(date: str):
    rows = []
    for tid, r in STORE.items():
        if r.get("settled_at") and r["settled_at"].startswith(date):
            rows.append({"transfer_id": tid, **r})
    return {"date": date, "rows": rows}
@app.post("/rail/admin/inject-break")
def inject(transfer_id: str, kind: str):
    if kind == "delete_row":
        STORE.pop(transfer_id, None)
    elif kind == "tamper_amount":
        if transfer_id in STORE:
            STORE[transfer_id]["amount_minor"] = 999
    return {"ok": True}