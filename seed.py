"""
M4 Data Environment: Synthetic Seed Generator.
Uses a fixed random seed (42) to ensure reproducibility. 
Never uses real data.
"""
import random
import json
import os


random.seed(42)

def generate_wallets(num_wallets=5):
    """Generates fake wallet IDs like W-DEMO01"""
    wallets = []
    for i in range(1, num_wallets + 1):
        
        wallet_id = f"W-DEMO{i:02d}"
        wallets.append({
            "wallet_id": wallet_id,
            "name": f"Demo User {i}",
            "phone": f"03000000{i:03d}", # Follows the exact phone pattern from the PDF
            "balance_minor": 100000000 # Start everyone with 1,000,000 PKR (in paisa)
        })
    return wallets

def main():
    print("Generating synthetic seed data...")
    
   
    data = {
        "wallets": generate_wallets()
    }

    
    os.makedirs("data/seed", exist_ok=True)
    
    
    output_path = "data/seed/wallets.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"✅ Success! Generated {len(data['wallets'])} wallets.")
    print(f"✅ Saved to {output_path}")

if __name__ == "__main__":
    main()