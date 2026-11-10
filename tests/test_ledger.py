from services.txn.db import SessionLocal, init_db
from services.txn import ledger
from services.txn.models import Transfer
from libs.common.clock import now
import uuid

init_db()
session = SessionLocal()

# 1. Give wallet A 5000 paisa
print("1. Seeding wallet W-A with 5000...")
ledger.post_opening_balance(session, "W-A", 5000)
session.commit()
assert ledger.get_balance(session, "W-A") == 5000
print("   ✅ Balance is 5000")

# 2. Try to send 6000 (should fail)
print("2. Trying to send 6000 (Insufficient funds)...")
t_fail = Transfer(transfer_id=str(uuid.uuid4()), sender_wallet_id="W-A", receiver_wallet_id="W-B",
                  amount_minor=6000, currency="PKR", state="DEBITED", version=0,
                  correlation_id="corr-1", created_at=now(), updated_at=now())
session.add(t_fail)
session.flush()
try:
    ledger.post_debit_leg(session, t_fail, "evt-1")
    print("   ❌ FAILED: Should have raised InsufficientFunds")
except ledger.InsufficientFunds:
    print("   ✅ InsufficientFunds raised correctly")
    session.rollback()

# 3. Send 2000 (should succeed)
print("3. Sending 2000 from A to B...")

t_ok = Transfer(transfer_id=str(uuid.uuid4()), sender_wallet_id="W-A", receiver_wallet_id="W-B",
                amount_minor=2000, currency="PKR", state="DEBITED", version=0,
                correlation_id="corr-2", created_at=now(), updated_at=now())
session.add(t_ok)
session.flush()

ledger.post_debit_leg(session, t_ok, "evt-2")
ledger.post_credit_leg(session, t_ok, "evt-3")
session.commit()

assert ledger.get_balance(session, "W-A") == 3000
assert ledger.get_balance(session, "W-B") == 2000
print("   ✅ Money moved! A has 3000, B has 2000.")

session.close()
print("\n🎉 Ledger Tests Passed!")