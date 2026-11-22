import json
import os
import re

def test_no_real_data_in_seed():
    """M4 Audit: Ensures the seed data does not contain real CNICs or phones."""
    seed_file = "data/seed/wallets.json"
    
    # 1. Make sure the file exists
    assert os.path.exists(seed_file), "Seed file is missing! Run scripts/seed.py first."
    
    with open(seed_file, "r") as f:
        data = json.load(f)
        
    wallets = data.get("wallets", [])
    assert len(wallets) > 0, "No wallets found in seed data."
    
    for wallet in wallets:
        # 2. Audit Names: Must be generic (Demo User X)
        assert "Demo User" in wallet["name"], f"Real-looking name found: {wallet['name']}"
        
        # 3. Audit Wallets: Must match the exact pattern W-[A-Z0-9]{3,12}
        assert re.match(r"^W-[A-Z0-9]{3,12}$", wallet["wallet_id"]), f"Invalid wallet ID: {wallet['wallet_id']}"
        
        # 4. Audit Phones: Must follow the pattern 03000000XXX (No real numbers)
        assert wallet["phone"].startswith("03000000"), f"Real-looking phone number found: {wallet['phone']}"

def test_no_real_data_in_codebase():
    """M4 Audit: Scans the code to ensure no one hardcoded real CNICs or personal data."""
    # A simple check to ensure no 13-digit CNIC numbers exist in the Python files
    for root, dirs, files in os.walk("."):
        if "venv" in root or ".git" in root or "site-packages" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # A real CNIC looks like 12345-1234567-1 (13 digits)
                    # We check for long strings of digits that might be real IDs
                    assert not re.search(r"\b\d{13}\b", content), f"Suspicious 13-digit number (potential CNIC) found in {path}"