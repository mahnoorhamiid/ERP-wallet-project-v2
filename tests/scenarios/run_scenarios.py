"""Live demo of scenarios S02-S05 against the running services.

Needs Transaction (8001), Compliance (8002) and Rail (8004), and a seeded txn.db.
Run from anywhere: python tests/scenarios/run_scenarios.py
"""
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
TXN_URL = os.getenv("TXN_URL", "http://127.0.0.1:8001")
COMPLIANCE_URL = os.getenv("COMPLIANCE_URL", "http://127.0.0.1:8002")
RAIL_URL = os.getenv("RAIL_URL", "http://127.0.0.1:8004")
SERVICES = [  # app, URL, a path only that service has
    ("services.txn.main:app", TXN_URL, "/internal/v1/events"),
    ("services.compliance.main:app", COMPLIANCE_URL, "/internal/v1/screen"),
    ("services.rail_mock.main:app", RAIL_URL, "/rail/v1/settlements"),
]
SENDER, RECEIVER = "W-DEMO001", "W-DEMO002"
MIN_BALANCE = 2_000_000  # enough for S02-S04


def get_balance(wallet_id):
    r = httpx.get(f"{TXN_URL}/internal/v1/wallets/{wallet_id}/balance", timeout=10)
    r.raise_for_status()
    return r.json()["balance_minor"]


def post_event(payload):
    # Longer than the services' own timeouts to each other.
    r = httpx.post(f"{TXN_URL}/internal/v1/events", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def rail_admin(action, **params):
    httpx.post(f"{RAIL_URL}/rail/admin/{action}", params=params,
               timeout=10).raise_for_status()


def initiated(amount_minor):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "transfer.initiated",
        "correlation_id": str(uuid.uuid4()),
        "data": {
            "transfer_id": str(uuid.uuid4()),
            "sender_wallet_id": SENDER,
            "receiver_wallet_id": RECEIVER,
            "amount_minor": amount_minor,
            "currency": "PKR",
        },
    }


def s02_partial_failure_compensation():
    before = get_balance(SENDER)
    rail_admin("mode", mode="REJECT")
    try:
        result = post_event(initiated(1_000_000))
    finally:
        rail_admin("mode", mode="SUCCESS")
    after = get_balance(SENDER)

    print(f"Transfer state: {result['state']}")
    print(f"Balance before: {before}, after: {after}")
    return result["state"] == "REVERSED" and before == after


def s03_duplicate_event():
    event = initiated(500_000)
    before = get_balance(SENDER)
    first, second = post_event(event), post_event(event)
    change = before - get_balance(SENDER)

    print(f"First event state: {first['state']}")
    print(f"Second event status: {second.get('status')}")
    print(f"Balance change: {change} (should be exactly 500000)")
    return (first["state"] == "COMPLETED" and second.get("status") == "duplicate"
            and change == 500_000)


def s04_reconciliation_break():
    transfer = post_event(initiated(1_000_000))
    tid = transfer["transfer_id"]
    print(f"Transfer state: {transfer['state']}")
    rail_admin("inject-break", transfer_id=tid, kind="tamper_amount")

    print("Running reconciliation...")
    today = datetime.now(timezone.utc).date().isoformat()
    subprocess.run([sys.executable, "-m", "services.txn.recon", "--date", today],
                   cwd=ROOT, env={**os.environ, "RAIL_URL": RAIL_URL},
                   check=True, stdout=subprocess.DEVNULL)
    report = json.loads((ROOT / "reports" / f"recon_{today}.json").read_text())

    # Check this transfer specifically: earlier runs may have left other breaks.
    found = [d["type"] for d in report["details"] if d["transfer_id"] == tid]
    print(f"Break found for this transfer: {found}")
    return transfer["state"] == "COMPLETED" and found == ["AMOUNT_MISMATCH"]


def s05_compliance_hold():
    before = get_balance(SENDER)
    result = post_event(initiated(45_000_000))  # above the 40,000,000 hold limit
    after = get_balance(SENDER)

    print(f"Transfer state: {result['state']} (reason: {result.get('hold_reason_code')})")
    print(f"Balance before: {before}, after: {after}")
    return (result["state"] == "ON_HOLD"
            and result.get("hold_reason_code") == "LARGE_AMOUNT" and before == after)


SCENARIOS = [
    ("S02", "Partial Failure & Compensation", s02_partial_failure_compensation),
    ("S03", "Duplicate Event (Idempotency)", s03_duplicate_event),
    ("S04", "Reconciliation Break", s04_reconciliation_break),
    ("S05", "Compliance Hold", s05_compliance_hold),
]


def check_ready():
    """Return setup problems, each with the command that fixes it."""
    problems = []
    for app, url, path in SERVICES:
        port = url.rsplit(":", 1)[-1]
        start = f"    python -m uvicorn {app} --port {port}"
        try:
            paths = httpx.get(f"{url}/openapi.json", timeout=10).json().get("paths", {})
        except httpx.TransportError:
            problems.append(f"{url} is not reachable. Start it in a new terminal:\n{start}")
        except ValueError:
            problems.append(f"{url} is not one of our services. Free port {port}, then:\n{start}")
        else:
            if path not in paths:
                problems.append(f"{url} is running the wrong service. Stop it (Ctrl+C), "
                                f"then run:\n{start}")
    if not problems and (balance := get_balance(SENDER)) < MIN_BALANCE:
        problems.append(f"{SENDER} has {balance}, needs {MIN_BALANCE}. For a fresh "
                        "database: stop the services, move txn.db aside, then run\n"
                        "    python -m services.txn.seed")
    return problems


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if problems := check_ready():
        print("Cannot start the demo:\n")
        print("\n\n".join(problems))
        return 2

    passed = 0
    for code, title, scenario in SCENARIOS:
        print(f"\n--- SCENARIO {code}: {title} ---")
        try:
            ok = scenario()
        except (httpx.HTTPError, subprocess.CalledProcessError, KeyError) as e:
            print(f"Error: {e!r}")
            ok = False
        passed += ok
        print(f"{'✅' if ok else '❌'} {code} {'PASSED' if ok else 'FAILED'}")

    print(f"\n{passed} of {len(SCENARIOS)} scenarios passed.")
    return 0 if passed == len(SCENARIOS) else 1


if __name__ == "__main__":
    sys.exit(main())
