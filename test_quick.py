import sqlite3
from services.txn.db import SessionLocal, init_db
from services.txn.models import Transfer, StateHistory
from services.txn.state_machine import transition, IllegalTransition
from libs.common.clock import now
from libs.common.outbox import init_outbox
import uuid

# 1. Ensure SQLAlchemy tables exist
init_db()

# 2. Ensure YOUR outbox table exists (using raw sqlite)
conn = sqlite3.connect("txn.db")
init_outbox(conn)
conn.close()

# 3. Open SQLAlchemy session
session = SessionLocal()
transfer_id = str(uuid.uuid4())

print("1. Creating fake transfer...")
t = Transfer(
    transfer_id=transfer_id, sender_wallet_id="W-TEST-1", receiver_wallet_id="W-TEST-2",
    amount_minor=10000, currency="PKR", state="INITIATED", version=0,
    correlation_id=str(uuid.uuid4()), created_at=now(), updated_at=now()
)
session.add(t)
session.commit()

print("2. Testing legal transition (INITIATED -> SCREENING)...")
transition(session, transfer_id, "SCREENING", None, event_id="evt-123")
session.commit()

t_check = session.get(Transfer, transfer_id)
assert t_check.state == "SCREENING"
assert t_check.version == 1
print("   ✅ Legal transition passed.")

print("3. Testing illegal transition (SCREENING -> COMPLETED)...")
try:
    transition(session, transfer_id, "COMPLETED", "SETTLED", event_id="evt-124")
    print("   ❌ FAILED: Did not raise IllegalTransition!")
except IllegalTransition as e:
    print(f"   ✅ Illegal transition blocked successfully: {e}")

session.close()
print("\n🎉 All Quick Tests Passed! You can delete test_quick.py now.")