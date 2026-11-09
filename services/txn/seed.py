import json
from services.txn.db import SessionLocal, init_db
from services.txn import ledger

def load_seed(session, data):
    for w in data["wallets"]:
        ledger.post_opening_balance(session, w["wallet_id"], w["opening_balance_minor"])

if __name__ == "__main__":
    init_db()
    with open("data/seed/wallets.json") as f:
        data = json.load(f)
    with SessionLocal() as s:
        load_seed(s, data); s.commit()
