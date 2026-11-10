from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ScreenReq(BaseModel):
    transfer_id: str
    sender_wallet_id: str
    receiver_wallet_id: str
    amount_minor: int
    currency: str
    correlation_id: str

@app.post("/internal/v1/screen")
def screen(req: ScreenReq):
    # If amount is over 400,000 PKR, hold for review
    if req.amount_minor > 40000000:
        return {"decision": "HOLD", "reason_code": "LARGE_AMOUNT"}
    return {"decision": "ALLOW", "reason_code": None}