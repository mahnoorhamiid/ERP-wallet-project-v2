from uuid import uuid4
from sqlalchemy import select, func
from libs.common.clock import now
from services.txn.models import LedgerAccount, LedgerJournal, LedgerEntry

class InsufficientFunds(Exception): ...
class InvalidJournal(Exception): ...

OPENING      = "CLEARING:OPENING"
SETTLEMENT   = "CLEARING:SETTLEMENT"
def wallet_acct(wid): return f"WALLET:{wid}"

def ensure_account(session, account_id, name, account_type, wallet_id=None):
    if session.get(LedgerAccount, account_id) is None:
        session.add(LedgerAccount(account_id=account_id, name=name,
                                  account_type=account_type, wallet_id=wallet_id))

def get_balance(session, wallet_id) -> int:
    acc = wallet_acct(wallet_id)
    q = select(LedgerEntry.direction, func.coalesce(func.sum(LedgerEntry.amount_minor), 0)) \
        .where(LedgerEntry.account_id == acc).group_by(LedgerEntry.direction)
    bal = 0
    for direction, total in session.execute(q):
        bal += total if direction == "CREDIT" else -total
    return bal

def post_journal(session, transfer_id, leg, source_event_id, correlation_id, entries,
                 reverses_journal_id=None):
    # idempotent: one journal per (transfer_id, leg)
    existing = session.execute(
        select(LedgerJournal).where(LedgerJournal.transfer_id == transfer_id,
                                    LedgerJournal.leg == leg)).scalar_one_or_none()
    if existing:
        return existing

    # validate I1 (balanced) and I4 (positive int, PKR)
    dr = sum(e["amount_minor"] for e in entries if e["direction"] == "DEBIT")
    cr = sum(e["amount_minor"] for e in entries if e["direction"] == "CREDIT")
    if dr != cr:
        raise InvalidJournal(f"unbalanced {dr} != {cr}")
    for e in entries:
        if not isinstance(e["amount_minor"], int) or e["amount_minor"] <= 0:
            raise InvalidJournal("amount must be positive int")
        if e.get("currency", "PKR") != "PKR":
            raise InvalidJournal("currency must be PKR")

    j = LedgerJournal(journal_id=str(uuid4()), transfer_id=transfer_id, leg=leg,
                      source_event_id=source_event_id, correlation_id=correlation_id,
                      reverses_journal_id=reverses_journal_id, posted_at=now())
    session.add(j); session.flush()
    for e in entries:
        session.add(LedgerEntry(entry_id=str(uuid4()), journal_id=j.journal_id,
                                account_id=e["account_id"], direction=e["direction"],
                                amount_minor=e["amount_minor"], currency="PKR"))
    return j

# --- posting rules (from PDF §3.3) ---
def post_opening_balance(session, wallet_id, amount_minor, event_id="seed"):
    ensure_account(session, OPENING, "Clearing Opening", "ASSET")
    ensure_account(session, wallet_acct(wallet_id), wallet_id, "LIABILITY", wallet_id)
    return post_journal(session, f"OPENING-{wallet_id}", "OPENING", event_id, event_id, [
        {"account_id": OPENING,               "direction": "DEBIT",  "amount_minor": amount_minor},
        {"account_id": wallet_acct(wallet_id),"direction": "CREDIT", "amount_minor": amount_minor},
    ])

def post_debit_leg(session, transfer, event_id):
    if get_balance(session, transfer.sender_wallet_id) < transfer.amount_minor:
        raise InsufficientFunds()
    return post_journal(session, transfer.transfer_id, "DEBIT_LEG", event_id,
                        transfer.correlation_id, [
        {"account_id": wallet_acct(transfer.sender_wallet_id), "direction": "DEBIT",
         "amount_minor": transfer.amount_minor},
        {"account_id": SETTLEMENT, "direction": "CREDIT",
         "amount_minor": transfer.amount_minor},
    ])

def post_credit_leg(session, transfer, event_id):
    return post_journal(session, transfer.transfer_id, "CREDIT_LEG", event_id,
                        transfer.correlation_id, [
        {"account_id": SETTLEMENT, "direction": "DEBIT",
         "amount_minor": transfer.amount_minor},
        {"account_id": wallet_acct(transfer.receiver_wallet_id), "direction": "CREDIT",
         "amount_minor": transfer.amount_minor},
    ])

def post_reversal_leg(session, transfer, debit_journal_id, event_id):
    return post_journal(session, transfer.transfer_id, "REVERSAL_LEG", event_id,
                        transfer.correlation_id, [
        {"account_id": SETTLEMENT, "direction": "DEBIT",
         "amount_minor": transfer.amount_minor},
        {"account_id": wallet_acct(transfer.sender_wallet_id), "direction": "CREDIT",
         "amount_minor": transfer.amount_minor},
    ], reverses_journal_id=debit_journal_id)