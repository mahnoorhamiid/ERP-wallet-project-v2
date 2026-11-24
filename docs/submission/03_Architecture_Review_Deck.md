# Architecture Review Deck: Digital Wallet Transaction Platform

**Format:** 10 slides, approximately 15 minutes. "On slide" is the visible content; "Say" is the presenter script.

---

## Slide 1. One instruction, one financial effect

**On slide**
- Digital wallet architecture: wallet-to-wallet transfer
- Decision sought: approve a controlled synthetic pilot
- Team: [names] | Date: [date] | Baseline: `f987b32`

**Visual:** one customer request ending in a balanced pair of postings.

**Say:** We are asking the board for one decision: whether this architecture may proceed to a controlled pilot on synthetic data. We will show what protects customers' money, what is proven, and what still prevents live use.

---

## Slide 2. Uncertain networks turn retries into financial risk

**On slide**
- Customers retry when no response arrives
- Services fail between debit and settlement
- Institutions must explain every rupee
- Priorities: integrity, recoverability, auditability

**Visual:** timeline of request, lost response and retry.

**Say:** A slow transfer is an inconvenience. A duplicate debit is a loss of trust and a potential regulatory issue. The business case is fewer disputes, controlled exceptions and defensible evidence.

---

## Slide 3. Responsibilities are separated around a single financial authority

**On slide**

| Component | Authority |
| :--- | :--- |
| Gateway | Accept and deduplicate requests |
| Compliance | Allow, hold or reject |
| Transaction Service | Change state and post journals |
| Rail | Confirm settlement |
| Reconciliation | Detect divergence |
| AI triage (design) | Advise only |

**Visual:** C4 container diagram. Solid lines for built, dashed for planned.

**Say:** Only the Transaction Service can post to the ledger. In this baseline the Gateway's downstream call is stubbed, Docker and PostgreSQL are planned, and AI is design only. The demonstration states this explicitly.

---

## Slide 4. Debit and credit are separated so uncertainty stays visible

**On slide**
- INITIATED → SCREENING → DEBITED → COMPLETED
- Exceptions: ON_HOLD, FAILED, REJECTED
- Recovery: DEBITED → COMPENSATING → REVERSED
- Illegal transitions are rejected

**Visual:** state diagram, normal path highlighted.

**Say:** Funds in flight sit in a settlement clearing account. We do not hold a ledger transaction open while waiting for the rail, and every state change is recorded.

---

## Slide 5. Independent controls stop duplicate and unbalanced postings

**On slide**
- Idempotency key plus body hash
- Event inbox
- Balanced journals in integer paisa
- Unique transfer and leg
- Version compare-and-set

**Visual:** five gates between request and ledger.

**Say:** In our test run, resending an event debited the sender only once and no journal was unbalanced. These controls still need concurrency testing, particularly wallet locking to prevent simultaneous overspending.

---

## Slide 6. Partial failure ends in compensation and evidence

**On slide**

| Event | Observed outcome |
| :--- | :--- |
| Client times out, resends | Recorded result; no second debit |
| Rail rejects | REVERSED; net change 0 |
| Rail times out, not settled | REVERSED; flagged for reconciliation |
| Rail record altered | AMOUNT_MISMATCH exception |

**Visual:** debit and reversing journal pair.

**Say:** Compensation adds a new journal instead of rewriting history. One case is not yet safe: if the rail settles late, after we reversed, we could lose funds. That is a release blocker.

---

## Slide 7. Controls are layered; security is still prototype-grade

**On slide**

| Area | Today | Required |
| :--- | :--- | :--- |
| Identity | Token presence | Verified JWT and wallet ownership |
| Internal calls | Open on localhost | mTLS and authorisation |
| Compliance | Threshold rule | Rules, maker-checker, officer identity |
| Audit | State history | Tamper-evident retention |
| AI | Design, advisory | Isolation proof, human decision record |

**Visual:** today/required two-column map.

**Say:** AI will never hold money-movement permission. Today, however, the hold-resolution endpoint does not authenticate an officer, so human approval is a design commitment until that is fixed.

---

## Slide 8. Five risks determine release readiness

**On slide**

| Risk | Rating | Treatment |
| :--- | :--- | :--- |
| Settlement after reversal | Critical | Hold until definitive inquiry |
| Rejected callback completes transfer | Critical | Check callback status |
| Unauthenticated internal commands | Critical | mTLS, authorisation |
| Concurrent overspend | High | Wallet row lock, race tests |
| Non-atomic event handling | High | One transaction for inbox and effects |

**Visual:** likelihood-impact matrix.

**Say:** We found these by exercising and inspecting the baseline. Ratings are engineering judgement. Each has an owner to assign and a testable exit criterion in the dossier.

---

## Slide 9. Release depends on evidence, not dates

**On slide**
- **Gate 1, integrity:** critical defects closed; concurrency tests pass
- **Gate 2, integration:** Gateway, outbox and PostgreSQL end to end
- **Gate 3, security:** identity, mTLS, officer approval
- **Gate 4, operations:** load, failover, monitoring, runbooks
- **Gate 5, AI:** isolation, abstention and override tests

**Visual:** five-stage gate roadmap with current position before Gate 1.

**Say:** The gates are sequential in terms of money risk. AI comes last because the platform must be safe without it.

---

## Slide 10. Recommendation: Go for demonstration, No-Go for live funds

**On slide**

| Use | Decision |
| :--- | :--- |
| Academic demonstration, synthetic data | **GO** |
| Controlled synthetic pilot | **CONDITIONAL GO** after Gates 1 and 2 |
| Real customers or funds | **NO-GO** until all gates pass |

- Ask: approve the architecture direction and Gate 1 work

**Visual:** three decision bars.

**Say:** We recommend approving the direction because the ledger, state model and recovery pattern are coherent and demonstrable. We recommend against live use because the remaining gaps affect money. Approval today commits to closing Gate 1, not to production.
