# M4: Bounded AI Design (Fraud-Alert Triage)

## 1. Purpose & Scope
The AI extension is designed to assist human compliance officers by triaging fraud alerts. It receives an alert from the M3 Compliance service and returns a **recommendation only** (priority and disposition). It strictly does not have the authority to approve, reject, or modify any transaction.

## 2. Bounded Behavior & Abstention
To ensure safety, the AI operates on a strict confidence threshold (`AI_ABSTAIN_THRESHOLD`, default 0.70). 
- If the model's calculated confidence is **above** the threshold, it recommends a disposition (e.g., `REVIEW_REJECT` or `REVIEW_RELEASE`).
- If the confidence falls **below** the threshold, the AI **abstains** (returns `ABSTAIN`). It refuses to guess, forcing the human officer to make the decision without AI bias.
- **Human-in-the-Loop:** Every AI recommendation is merely a suggestion. The final decision to release or reject funds is made exclusively by a human Compliance Officer.

## 3. Isolation & Security (The "No Path" Rule)
The project mandates that the AI has no network path and no code path to the Transaction Service or the Ledger.
- **Network Isolation:** In `docker-compose.yml`, the `ai-triage` service is placed exclusively on the `ai-network`. It has no access to the `wallet-network` (which hosts Postgres, Gateway, and Txn).
- **Code Isolation:** The `services/ai_triage/` module does not import any SQLAlchemy models, Postgres libraries, or `txn`/`gateway` code.
- **Automated Proof:** The test `test_ai_has_no_path_to_txn_or_ledger` (in `tests/test_ai_triage.py`) performs a static analysis to ensure no forbidden imports exist in the AI service.

## 4. Idempotency & Reliability
Because inter-service delivery is at-least-once, the AI service must handle duplicate alerts. 
- It uses its own isolated SQLite database (`ai_triage.db`).
- It dedupes on the `alert_id`. If an alert is received twice, it returns the exact same `recommendation_id` and response without re-running the model.
