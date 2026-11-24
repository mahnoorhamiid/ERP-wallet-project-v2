# Architecture Brief: Digital Wallet Transaction Platform

**Subject:** Wallet-to-wallet transfer, a SadaPay/NayaPay-inspired academic prototype | **Data:** synthetic only | **Status:** prototype baseline `f987b32`

## 1. Purpose and selected journey

Pakistani digital-wallet customers expect immediate transfers over networks that regularly fail mid-request. The architectural problem is therefore not how to move a balance, but how to guarantee that every instruction has **exactly one financial effect and one explainable outcome** despite retries, partial failure and compliance intervention.

The selected journey is a **PKR wallet-to-wallet transfer**:

1. The customer submits a transfer with an `Idempotency-Key`.
2. The Gateway validates it, suppresses duplicates and issues a `transfer.initiated` event.
3. The Transaction Service screens it through Compliance: ALLOW, HOLD or REJECT.
4. On ALLOW, the sender is debited into a settlement clearing account.
5. The settlement rail is instructed. On confirmation, the receiver is credited.
6. On rejection, a reversing journal refunds the sender.
7. Reconciliation compares ledger and rail, and queues breaks for human resolution.

## 2. Scope

| In scope | Out of scope |
| :--- | :--- |
| P2P wallet transfer, double-entry ledger, compensation, compliance hold, reconciliation | Cards, bill payment, remittance, cash-in/out, lending |
| Synthetic wallets and a mock settlement rail | Live Raast/1LINK integration, real KYC, customer data |
| Bounded AI fraud-alert triage design | AI-initiated decisions, postings or releases |

## 3. Systems involved

| System | Responsibility | Status |
| :--- | :--- | :--- |
| API Gateway (FastAPI, 8000) | Validation, idempotency, correlation ID | Built; downstream call to Transaction Service stubbed |
| Transaction Service (FastAPI, 8001) | State machine, saga orchestration, ledger, recovery | Built |
| Compliance (FastAPI, 8002) | Threshold screening; hold above PKR 400,000 | Built as a mock |
| Settlement rail (FastAPI, 8004) | Simulates success, rejection and timeout | Built as a mock |
| Reconciliation (batch) | Ledger-to-rail comparison, exception queue | Built |
| AI triage | Advisory recommendation on alerts | Designed; no code in this baseline |
| Data store | System of record | SQLite demonstrated; PostgreSQL is the target |
| Docker Compose | Deployment and network isolation | Designed; no files in this baseline |

## 4. Constraints and assumptions

**Constraints:** Python and FastAPI; PKR only; integer paisa amounts; maximum PKR 1,000,000 per Gateway request; no real personal or financial data; AI must hold no money-movement authority.

**Assumptions:**
- The rail treats `transfer_id` as its own idempotency key and offers a status inquiry.
- Inter-service delivery is at-least-once, so every consumer must deduplicate.
- Clocks are UTC and reconciliation runs on a UTC business date.
- One platform operator owns both wallets. The "rail" stands in for an external settlement dependency.
- Identity is supplied by a trusted provider in production. The prototype only checks that a bearer token is present.

## 5. Critical controls

| ID | Control | Protects against | Status |
| :--- | :--- | :--- | :--- |
| C1 | Idempotency key plus canonical SHA-256 request hash | Double submission, key misuse | Built |
| C2 | Inbox deduplication on `event_id` | Duplicate event delivery | Built for sequential redelivery |
| C3 | Balanced, append-only double-entry journals | Lost or created money | Built in application code |
| C4 | Unique `(transfer_id, leg)` constraint | Double posting of a leg | Built, database-enforced |
| C5 | Whitelisted transitions with compare-and-set version | Illegal or concurrent state change | Built |
| C6 | Compensating reversal | Debit without settlement | Built; ambiguous outcomes need hardening |
| C7 | Fail-closed screening | Transfer without compliance decision | Built |
| C8 | Ledger-to-rail reconciliation | Undetected divergence | Built |
| C9 | Human decision on holds and AI advice | Unaccountable automation | Partial; officer identity not yet enforced |

## 6. Non-functional requirements

The figures below are **architecture targets**. They have not been load-tested.

| Quality | Target | Design response |
| :--- | :--- | :--- |
| Integrity | Zero unbalanced journals; zero duplicate legs | C3, C4 |
| Idempotency | Same key and body give one transfer within 24 h | C1, C2 (key-expiry enforcement outstanding) |
| Latency | p95 at or below 2 s end to end when dependencies are healthy | Short synchronous path; 2 s downstream timeouts |
| Availability | 99.9% monthly for transfer API | Stateless services, PostgreSQL HA in target state |
| Recoverability | Stuck DEBITED transfers detected within 60 s; RPO 0, RTO 15 min | Recovery loop, durable state, replicated database |
| Auditability | 100% of transitions attributable | State history, correlation ID, source event |
| Security | TLS/mTLS, least privilege, no real data | OAuth2/JWT and service identity in target state |
| Explainability | Every AI recommendation recorded with human outcome | Advisory-only contract, abstention below 0.70 |

## 7. Recommendation

The integrity core is sound and demonstrable. The platform is suitable for **controlled demonstration on synthetic data**. It is not suitable for live funds until the release gates in the Design Dossier (section 12) are closed.
