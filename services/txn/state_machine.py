from sqlalchemy import update
from libs.common.clock import now
from libs.common.outbox import enqueue
from services.txn.models import Transfer, StateHistory
import uuid

class IllegalTransition(Exception): ...

TRANSITIONS = {
    ("INITIATED", "SCREENING"):     None,
    ("INITIATED", "FAILED"):        ("WALLET_NOT_FOUND", "WALLET_INACTIVE"),
    ("SCREENING", "DEBITED"):       "ALLOW",
    ("SCREENING", "ON_HOLD"):       "HOLD",
    ("SCREENING", "REJECTED"):      "REJECT",
    ("SCREENING", "FAILED"):        ("INSUFFICIENT_FUNDS", "SCREENING_UNAVAILABLE"),
    ("ON_HOLD", "DEBITED"):         "RELEASE",
    ("ON_HOLD", "REJECTED"):        "REJECT",
    ("ON_HOLD", "FAILED"):          "INSUFFICIENT_FUNDS",
    ("DEBITED", "COMPLETED"):       "SETTLED",
    ("DEBITED", "COMPENSATING"):    ("REJECTED", "TIMEOUT_UNCONFIRMED"),
    ("COMPENSATING", "REVERSED"):   "REVERSAL_POSTED",
}
TERMINAL = {"COMPLETED", "REVERSED", "REJECTED", "FAILED"}

def transition(session, transfer_id: str, to_state: str, reason: str | None, event_id: str) -> Transfer:
    for _ in range(3):
        t = session.get(Transfer, transfer_id)
        if t is None:
            raise IllegalTransition(f"transfer {transfer_id} not found")
        
        from_state = t.state
        key = (from_state, to_state)
        if key not in TRANSITIONS:
            raise IllegalTransition(f"illegal {from_state}->{to_state}")
        
        allowed = TRANSITIONS[key]
        if isinstance(allowed, tuple) and reason not in allowed:
            raise IllegalTransition(f"reason {reason} not allowed for {from_state}->{to_state}")
        if isinstance(allowed, str) and allowed != reason:
            raise IllegalTransition(f"reason must be {allowed}, got {reason}")

        res = session.execute(
            update(Transfer)
            .where(Transfer.transfer_id == transfer_id,
                   Transfer.state == from_state,
                   Transfer.version == t.version)
            .values(state=to_state, version=t.version + 1, updated_at=now(),
                    failure_reason=reason if to_state == "FAILED" else t.failure_reason)
        )
        if res.rowcount == 1:
            break
        session.expire_all()
    else:
        raise IllegalTransition("compare-and-set failed after 3 retries")

    session.add(StateHistory(transfer_id=transfer_id, from_state=from_state,
                             to_state=to_state, reason=reason, event_id=event_id,
                             occurred_at=now()))
    
    envelope = {
        "event_type": "transfer.state_changed",
        "event_version": "1.0",
        "occurred_at": now().isoformat().replace("+00:00", "Z"),
        "producer": "txn",
        "correlation_id": t.correlation_id,
        "data": {"transfer_id": transfer_id, "from_state": from_state,
                 "to_state": to_state, "reason_code": reason, "journal_ids": []},
    }
    
    raw_conn = session.connection().connection.dbapi_connection
    enqueue(raw_conn, event_id=str(uuid.uuid4()), target_url="http://compliance:8002/internal/v1/events", payload=envelope)
    
    return session.get(Transfer, transfer_id)