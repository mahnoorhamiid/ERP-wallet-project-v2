import argparse
import csv
import json
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from services.txn.db import SessionLocal, init_db
from services.txn.models import Transfer, LedgerJournal, ReconException
from libs.common.clock import now
import httpx

RAIL_URL = os.getenv("RAIL_URL", "http://127.0.0.1:8004")

def run_recon(date: str):
    init_db()
    run_id = str(uuid.uuid4())
    s = SessionLocal()
    try:
        # 1) Get all DEBIT_LEG journals posted on this date
        start_date = datetime.fromisoformat(date + "T00:00:00+00:00")
        end_date = datetime.fromisoformat(date + "T23:59:59+00:00")
        
        journals = s.execute(select(LedgerJournal).where(
            LedgerJournal.leg == "DEBIT_LEG",
            LedgerJournal.posted_at >= start_date,
            LedgerJournal.posted_at <= end_date,
        )).scalars().all()
        
        ledger_map = {j.transfer_id: s.get(Transfer, j.transfer_id) for j in journals}

        # 2) Get rail report
        rail = httpx.get(f"{RAIL_URL}/rail/v1/reports/settlements", params={"date": date}, timeout=5.0).json()["rows"]
        rail_map = {r["transfer_id"]: r for r in rail}

        breaks = []
        matched = 0
        matched_value = 0
        
        for tid, t in ledger_map.items():
            r = rail_map.get(tid)
            
            # If transfer is COMPLETED, it must exist on the rail and be SETTLED
            if t.state == "COMPLETED":
                if not r: 
                    breaks.append((tid, "MISSING_AT_RAIL", t, None))
                elif r.get("amount_minor") != t.amount_minor:
                    breaks.append((tid, "AMOUNT_MISMATCH", t, r))
                elif r["status"] != "SETTLED": 
                    breaks.append((tid, "STATUS_MISMATCH", t, r))
                else: 
                    matched += 1
                    matched_value += t.amount_minor
                    
            # If transfer is REVERSED, it shouldn't be SETTLED on the rail
            elif t.state == "REVERSED":
                if r and r["status"] == "SETTLED":
                    breaks.append((tid, "STATUS_MISMATCH", t, r))
                else: 
                    matched += 1

        # Check for rail settlements that aren't in our ledger
        for tid, r in rail_map.items():
            if tid not in ledger_map:
                breaks.append((tid, "MISSING_IN_LEDGER", None, r))

        # 3) Write reports
        os.makedirs("reports", exist_ok=True)
        summary = {"date": date, "run_id": run_id, "total_ledger": len(ledger_map),
                   "total_rail": len(rail_map), "matched": matched, "breaks": len(breaks),
                   "matched_value_minor": matched_value, "by_type": {}}
                   
        for _, btype, *_ in breaks:
            summary["by_type"][btype] = summary["by_type"].get(btype, 0) + 1
            
        with open(f"reports/recon_{date}.json", "w") as f:
            json.dump({"summary": summary, "details": [{"transfer_id": t, "type": b} for t, b, *_ in breaks]}, f, indent=2)
            
        with open(f"reports/recon_{date}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["transfer_id", "type"])
            for t, b, *_ in breaks: 
                w.writerow([t, b])

        # 4) Save exceptions to DB
        for tid, btype, t, r in breaks:
            exists = s.execute(select(ReconException).where(
                ReconException.transfer_id == tid, ReconException.type == btype,
                ReconException.status == "OPEN")).scalar_one_or_none()
            if not exists:
                s.add(ReconException(exception_id=str(uuid.uuid4()), run_id=run_id,
                    transfer_id=tid, type=btype,
                    expected_json={"state": t.state if t else None},
                    actual_json=r or {}, status="OPEN", created_at=now()))
        s.commit()
        return summary
    finally:
        s.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    print(json.dumps(run_recon(p.parse_args().date), indent=2))