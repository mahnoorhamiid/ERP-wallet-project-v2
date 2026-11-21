
import logging
import json
from datetime import datetime, timezone
from fastapi import FastAPI
from pydantic import BaseModel, Field

# Observability: basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compliance")

def write_audit_log(transfer_id, decision, reason_code):
    record = {
        "transfer_id": transfer_id,
        "decision": decision,
        "reason_code": reason_code,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        with open("compliance_audit.jsonl", "a") as file:
            file.write(json.dumps(record) + "\n")

    except OSError:
        logger.exception(
            "Failed to write audit log for transfer %s",
            transfer_id
        )
        raise



app = FastAPI(title="Digital Wallet Compliance Service")


class ScreenReq(BaseModel):
    transfer_id: str
    sender_wallet_id: str
    receiver_wallet_id: str
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3,max_length=3)
    correlation_id: str
    kyc_verified: bool = False 
    aml_flag: bool = False


@app.get("/health")
def health():
    return {"status": "healthy", "service": "compliance"}


@app.post("/internal/v1/screen")
def screen(req: ScreenReq):

    logger.info(
        "Screening transfer %s, correlation %s",
        req.transfer_id,
        req.correlation_id
    )

    # KYC check
    if not req.kyc_verified:
        logger.warning("KYC verification failed")
        write_audit_log(req.transfer_id, "HOLD", "KYC_NOT_VERIFIED")
        return {
            "decision": "HOLD",
            "reason_code": "KYC_NOT_VERIFIED"
        }

    # AML check
    if req.aml_flag:
        logger.warning("AML risk flag detected")
        write_audit_log(req.transfer_id, "HOLD", "AML_ALERT")
        return {
            "decision": "HOLD",
            "reason_code": "AML_ALERT"
        }

    # Transaction amount check
    if req.amount_minor > 40000000:
        logger.warning("Large transaction held for review")
        write_audit_log(req.transfer_id, "HOLD", "LARGE_AMOUNT")
        return {
            "decision": "HOLD",
            "reason_code": "LARGE_AMOUNT"
        }

    logger.info("Transfer approved: %s", req.transfer_id)
    write_audit_log(req.transfer_id, "ALLOW", None)

    return {
        "decision": "ALLOW",
        "reason_code": None
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "compliance"
    }