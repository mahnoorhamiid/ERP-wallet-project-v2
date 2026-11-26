# M4: Bounded AI Design (Fraud-Alert Triage)

## 1. Purpose & Scope
The AI extension is designed to assist human compliance officers by triaging fraud alerts. It receives an alert from the M3 Compliance service and returns a recommendation only (priority and disposition). It does not have the authority to approve, reject, or modify any transaction.

## 2. Bounded Behavior & Abstention
To ensure safety, the AI operates on a strict confidence threshold. 
- If the model's confidence is above the threshold, it recommends a disposition.
- If the confidence falls below the threshold, the AI abstains (returns ABSTAIN). It refuses to guess, forcing the human officer to make the decision without AI bias.
- Human-in-the-Loop: Every AI recommendation is merely a suggestion. The final decision is made by a human Compliance Officer.

## 3. Isolation & Security
The AI has no network path and no code path to the Transaction Service or the Ledger.
- Network Isolation: In the Docker environment, the ai-triage service is placed exclusively on the ai-network. It has no access to the wallet-network.
- Code Isolation: The AI module does not import any database models or transaction code.
- Automated Proof: A static analysis test ensures no forbidden imports exist.

## 4. Idempotency & Reliability
Because inter-service delivery is at-least-once, the AI service handles duplicate alerts. It uses an isolated SQLite database and dedupes on the alert_id. If an alert is received twice, it returns the exact same recommendation.
