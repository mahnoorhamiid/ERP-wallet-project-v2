import httpx
import uuid
from services.txn.db import init_db, SessionLocal
from services.txn.models import Transfer, LedgerEntry
from sqlalchemy import select, func

TXN_URL = "http://127.0.0.1:8001"
RAIL_URL = "http://127.0.0.1:8004"

def get_balance(wallet_id):
    r = httpx.get(f"{TXN_URL}/internal/v1/wallets/{wallet_id}/balance")
    return r.json()["balance_minor"]

def post_event(payload):
    return httpx.post(f"{TXN_URL}/internal/v1/events", json=payload).json()

print("\n--- SCENARIO S02: Partial Failure & Compensation ---")
# Set Rail to REJECT mode
httpx.post(f"{RAIL_URL}/rail/admin/mode?mode=REJECT")
bal_before = get_balance("W-DEMO001")

# Send transfer
payload = {
    "event_id": str(uuid.uuid4()),
    "event_type": "transfer.initiated",
    "correlation_id": "corr-s02",
    "data": {
        "transfer_id": f"tx-s02-{uuid.uuid4().hex[:4]}",
        "sender_wallet_id": "W-DEMO001",
        "receiver_wallet_id": "W-DEMO002",
        "amount_minor": 1000000,
        "currency": "PKR"
    }
}
res = post_event(payload)
print(f"Transfer State: {res['state']}") 
# Expect: REVERSED

bal_after = get_balance("W-DEMO001")
print(f"Balance Before: {bal_before}, Balance After: {bal_after}")
if bal_before == bal_after and res['state'] == 'REVERSED':
    print("S02 PASSED: Funds were refunded (compensated) due to Rail Rejection.")
else:
    print("S02 FAILED")

# Reset Rail to SUCCESS
httpx.post(f"{RAIL_URL}/rail/admin/mode?mode=SUCCESS")


print("\n--- SCENARIO S03: Duplicate Event (Idempotency) ---")
payload = {
    "event_id": str(uuid.uuid4()),
    "event_type": "transfer.initiated",
    "correlation_id": "corr-s03",
    "data": {
        "transfer_id": f"tx-s03-{uuid.uuid4().hex[:4]}",
        "sender_wallet_id": "W-DEMO001",
        "receiver_wallet_id": "W-DEMO002",
        "amount_minor": 500000,
        "currency": "PKR"
    }
}
bal_before = get_balance("W-DEMO001")

res1 = post_event(payload)
res2 = post_event(payload) # Send the exact same event again

bal_after = get_balance("W-DEMO001")
print(f"First Event State: {res1['state']}")
print(f"Second Event State: {res2.get('status', res2.get('state'))}")
print(f"Balance change: {bal_before - bal_after} (Should be exactly 500000)")

if (bal_before - bal_after) == 500000 and res2.get('status') == 'duplicate':
    print("S03 PASSED: Duplicate event was blocked by Inbox deduplication.")
else:
    print("S03 FAILED")


print("\n--- SCENARIO S04: Reconciliation Break ---")
# 1. Create a successful transfer
payload = {
    "event_id": str(uuid.uuid4()),
    "event_type": "transfer.initiated",
    "correlation_id": "corr-s04",
    "data": {
        "transfer_id": f"tx-s04-{uuid.uuid4().hex[:4]}",
        "sender_wallet_id": "W-DEMO001",
        "receiver_wallet_id": "W-DEMO002",
        "amount_minor": 1000000,
        "currency": "PKR"
    }
}
res = post_event(payload)
tid = res['transfer_id']
print(f"Transfer State: {res['state']}")

# 2. Tamper with the rail
httpx.post(f"{RAIL_URL}/rail/admin/inject-break?transfer_id={tid}&kind=tamper_amount")

# 3. Run recon directly via Python import
import subprocess
import json
print("Running Reconciliation...")
recon_out = subprocess.check_output(["python", "-m", "services.txn.recon", "--date", "2026-11-10"]).decode("utf-8")
recon_json = json.loads(recon_out)

breaks = recon_json["by_type"].get("AMOUNT_MISMATCH", 0)
if breaks > 0:
    print("✅ S04 PASSED: Recon engine caught the AMOUNT_MISMATCH break.")
else:
    print("❌ S04 FAILED: Recon missed the break.")


print("\n--- SCENARIO S05: Compliance Hold ---")
bal_before = get_balance("W-DEMO001")
payload = {
    "event_id": str(uuid.uuid4()),
    "event_type": "transfer.initiated",
    "correlation_id": "corr-s05",
    "data": {
        "transfer_id": f"tx-s05-{uuid.uuid4().hex[:4]}",
        "sender_wallet_id": "W-DEMO001",
        "receiver_wallet_id": "W-DEMO002",
        "amount_minor": 45000000, # Over 40m limit, triggers HOLD
        "currency": "PKR"
    }
}
res = post_event(payload)
print(f"Transfer State: {res['state']} (Reason: {res.get('hold_reason_code')})")
bal_after = get_balance("W-DEMO001")

if res['state'] == 'ON_HOLD' and res.get('hold_reason_code') == 'LARGE_AMOUNT' and bal_before == bal_after:
    print("✅ S05 PASSED: Large transfer placed ON_HOLD without altering balance.")
else:
    print("❌ S05 FAILED")

print("\nAll tests complete! Check the output above for green checks.")
