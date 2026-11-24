# ADR-008: Durable Relational Idempotency Store

**Status:** Proposed for team ratification | **Date:** 2026-11-24 | **Refines:** ADR-002

## Context
An idempotency record is part of a financial control. Losing it during a restart or eviction could allow a retry to create a second transfer.

## Options considered
1. **In-process memory:** lost on restart and not shared between instances.
2. **Redis with TTL:** fast shared store; safe use depends on persistence and eviction configuration.
3. **Relational table:** durable, constrained and auditable; adds a database write per request.

## Decision
Use option 3, keyed by `(client_id, idempotency_key)`. Store the SHA-256 of canonical JSON, state, transfer and event identifiers, and response. The prototype uses SQLite (`gateway.db`); the target is PostgreSQL. Records carry a 24-hour expiry. Matching completed requests replay with `Idempotent-Replayed: true`; a different body returns 422; a fresh in-progress request returns 409; one older than 30 s resumes with its original identifiers. The Transaction Service separately deduplicates on `event_id`.

## Consequences
- **Positive:** survives restart; primary key prevents duplicate records; replay is deterministic.
- **Negative:** write latency and retention management.
- **Hardening required:** generate identifiers in the initial insert; convert concurrent primary-key conflicts into 409 rather than an unhandled error; enforce expiry; derive `client_id` from the verified JWT subject; make inbox and business effects atomic downstream.

## Verification
Three store unit tests pass. The retry scenario passes once a stray command is removed from its test file. The Gateway returned the same transfer ID on replay and 422 on body change.
