
from services.compliance.main import ScreenReq, screen

print("\nStarting Compliance Tests...\n")

# 1. Normal transaction (should ALLOW)
print("1. Testing normal transaction...")

req1 = ScreenReq(
    transfer_id="TEST001",
    sender_wallet_id="WALLET001",
    receiver_wallet_id="WALLET002",
    amount_minor=1000000,
    currency="PKR",
    correlation_id="CORR001",
    kyc_verified=True,
    aml_flag=False
)

result1 = screen(req1)
assert result1["decision"] == "ALLOW"
print("   PASS: Normal transaction approved.")


# 2. KYC failure (should HOLD)
print("2. Testing KYC failure...")

req2 = ScreenReq(
    transfer_id="TEST002",
    sender_wallet_id="WALLET001",
    receiver_wallet_id="WALLET002",
    amount_minor=1000000,
    currency="PKR",
    correlation_id="CORR002",
    kyc_verified=False,
    aml_flag=False
)

result2 = screen(req2)
assert result2["decision"] == "HOLD"
assert result2["reason_code"] == "KYC_NOT_VERIFIED"
print("   PASS: Unverified KYC transaction held.")


# 3. AML alert (should HOLD)
print("3. Testing AML alert...")

req3 = ScreenReq(
    transfer_id="TEST003",
    sender_wallet_id="WALLET001",
    receiver_wallet_id="WALLET002",
    amount_minor=1000000,
    currency="PKR",
    correlation_id="CORR003",
    kyc_verified=True,
    aml_flag=True
)

result3 = screen(req3)
assert result3["decision"] == "HOLD"
assert result3["reason_code"] == "AML_ALERT"
print("   PASS: AML flagged transaction held.")


# 4. Large transaction (should HOLD)
print("4. Testing large transaction...")

req4 = ScreenReq(
    transfer_id="TEST004",
    sender_wallet_id="WALLET001",
    receiver_wallet_id="WALLET002",
    amount_minor=50000000,
    currency="PKR",
    correlation_id="CORR004",
    kyc_verified=True,
    aml_flag=False
)

result4 = screen(req4)
assert result4["decision"] == "HOLD"
assert result4["reason_code"] == "LARGE_AMOUNT"
print("   PASS: Large transaction held.")


print("\nALL COMPLIANCE TESTS PASSED!")
