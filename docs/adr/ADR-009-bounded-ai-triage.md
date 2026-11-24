# ADR-009: Bounded AI Triage with Human Authority

**Status:** Proposed for team ratification; design only at `f987b32` | **Date:** 2026-11-24

## Context
Fraud-alert queues benefit from prioritisation. Probabilistic output is nevertheless unsuitable as authority to release, reject or post funds.

## Options considered
1. **No AI:** lowest model risk, fully manual queue.
2. **Autonomous AI decision:** fastest, but unacceptable accountability and manipulation risk.
3. **Advisory AI:** prioritises and summarises; an authorised officer decides.

## Decision
Adopt option 3. The service receives a minimised synthetic alert and returns a priority, recommendation, confidence and rationale. It abstains below 0.70. It has no credentials, code path or network route to the Transaction Service or ledger. Only an authenticated officer may issue `hold.resolved`, and the Transaction Service re-validates that decision. AI failure leaves the alert in the manual queue.

## Consequences
- **Positive:** reduces queue effort while preserving accountability and a safe failure mode.
- **Negative:** automation bias, false confidence and review overhead.
- **Mitigation:** show evidence and uncertainty, record agreement and override, sample-review decisions, version model and prompt, retain a kill switch.

## Verification required before acceptance
Service code, import-isolation test, network-denial test, duplicate-alert test, abstention test, and rejection of unauthenticated or AI-originated `hold.resolved`. None of these is present in the baseline.
