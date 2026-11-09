import requests
import json

url = "http://127.0.0.1:8000/v1/transfers"
headers = {
    "Content-Type": "application/json",
    "Idempotency-Key": "my-super-key-123",
    "Authorization": "Bearer fake-token"
}
body = {
    "sender_wallet_id": "W-ALICE01",
    "receiver_wallet_id": "W-BOB0001",
    "amount_minor": 100000,
    "currency": "PKR"
}

print("--- SENDING FIRST REQUEST ---")
res1 = requests.post(url, headers=headers, json=body)
print("Status:", res1.status_code)
print("Transfer ID:", res1.json().get("transfer_id"))
print("Replayed Header:", res1.headers.get("Idempotent-Replayed"))

print("\n--- SENDING SECOND REQUEST (SAME KEY) ---")
res2 = requests.post(url, headers=headers, json=body)
print("Status:", res2.status_code)
print("Transfer ID:", res2.json().get("transfer_id"))
print("Replayed Header:", res2.headers.get("Idempotent-Replayed"))

if res1.json().get("transfer_id") == res2.json().get("transfer_id") and res2.headers.get("Idempotent-Replayed") == "true":
    print("\n[SUCCESS] Idempotency is working perfectly!")
else:
    print("\n[FAILED] Something is wrong.")
