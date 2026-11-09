# ADR 001: API-First with OpenAPI 3.1

## Context
We need a clear contract between the mobile app and the backend Gateway. Any drift in the contract will cause client crashes.

## Decision
We will use an API-first approach. The FastAPI application generates an OpenAPI 3.1 schema via `scripts/export_openapi.py`. The OpenAPI YAML file is committed to the repository and treated as the single source of truth.

## Consequences
- Positive: Client code can be auto-generated. Contract tests prevent accidental breaking changes.
- Negative: Developers must remember to run the export script after any endpoint changes.