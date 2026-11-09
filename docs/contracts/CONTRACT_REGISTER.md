# Integration Contract Register

This document tracks all inter-component contracts in the system.

| Contract Name | Owner | Consumer | Version | Status | Sign-offs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST /v1/transfers` (REST) | M1 | Customer App | 1.0 | FROZEN | M1, M2, M3, M4 |
| `GET /v1/transfers/{id}` (REST) | M1 | Customer App | 1.0 | FROZEN | M1, M2, M3, M4 |
| `transfer.initiated` (Event) | M1 | M2 (Txn) | 1.0 | FROZEN | M1, M2, M3, M4 |
| `transfer.state_changed` (Event) | M2 | M3 (Compliance) | 1.0 | FROZEN | M1, M2, M3, M4 |
| `rail.settlement_confirmed` (Event) | M2 | M2 (Txn) | 1.0 | FROZEN | M1, M2, M3, M4 |
| `hold.resolved` (Event) | M3 | M2 (Txn) | 1.0 | FROZEN | M1, M2, M3, M4 |
| `POST /internal/v1/events` | M2 | M1, M3 | 1.0 | FROZEN | M1, M2, M3, M4 |
| `POST /internal/v1/screen` | M3 | M2 | 1.0 | FROZEN | M1, M2, M3, M4 |