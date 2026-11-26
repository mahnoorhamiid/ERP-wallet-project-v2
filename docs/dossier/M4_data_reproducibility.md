# M4: Data Environment & Reproducibility

## 1. Synthetic Data Generation
The project strictly forbids the use of real customer data. All data is synthetic and generated via the `scripts/seed.py` script.
- **Fixed Random Seed:** The generator uses a fixed random seed (`42`) to ensure absolute reproducibility. Every developer who runs the script gets the exact same dataset.
- **Data Patterns:** 
  - Names are strictly generic (e.g., `Demo User 1`).
  - Wallet IDs follow the regex `^W-[A-Z0-9]{3,12}$` (e.g., `W-DEMO01`).
  - Phone numbers follow the pattern `03000000XXX`.
- **No Real Data:** No real CNICs, personal phone numbers, or actual transaction records exist in the repository.

## 2. Automated Audit
To enforce the synthetic data rule at every handover and before the final freeze, an automated audit test exists at `tests/test_synthetic_data.py`.
- It reads `data/seed/wallets.json` and asserts that no names or phone numbers look realistic.
- It scans the entire Python codebase to ensure no 13-digit CNIC numbers are hardcoded anywhere.

## 3. Reproducibility & Time
- **Clock:** All services use `libs/common/clock.py::now()`. This ensures that if we need to freeze the clock for deterministic tests, we can do so without modifying individual services.
- **Database Portability:** The system uses SQLAlchemy exclusively. `DATABASE_URL` is an environment variable, allowing the system to run on SQLite (for pytest) or Postgres (for Docker Compose).
