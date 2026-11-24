# ADR-005: Synchronous Decision Path with Asynchronous Recovery

**Status:** Proposed for team ratification | **Date:** 2026-11-24 | **Related:** ADR-004, ADR-006

## Context
Customers need an immediate, definitive outcome where possible. Screening and rail settlement are remote calls that can be slow, reject, or fail after taking effect. A fully synchronous design couples availability to every dependency. A fully asynchronous one makes ordinary transfers harder to understand and test.

## Options considered
1. **Fully synchronous:** simple and immediate, but fragile when a response is lost.
2. **Fully asynchronous:** resilient and decoupled, but eventually consistent throughout and dependent on a broker.
3. **Hybrid:** synchronous screening, debit and rail attempt; durable state, with recovery and notifications handled asynchronously.

## Decision
Adopt option 3. Remote calls have bounded timeouts (2 s). The debit commits before the rail is called, so no ledger transaction spans that call. Transfers left in `DEBITED` are handled by a background recovery loop. State changes are written to an outbox for later delivery.

## Consequences
- **Positive:** immediate result on the normal path, recoverable state after failure, no broker for the prototype.
- **Negative:** a worst-case request spans several timeouts; `DEBITED` is visible as an intermediate state.
- **Hardening required:** an ambiguous rail result must remain `DEBITED` until a definitive inquiry. The current code compensates on any non-`SETTLED` inquiry after an exception, and recovery re-submits the settlement before inquiring.
- **Not yet built:** Gateway-to-Transaction call and the running outbox dispatcher.

## Verification
Rail `REJECT` and timeout modes both end `REVERSED` with zero net balance change. A late settlement arriving after reversal is not covered.
