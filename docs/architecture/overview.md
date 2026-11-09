# Architecture overview

## Components
- **Frontend** – SPA for investigators. Talks only to the backend REST API.
- **Backend** – stateless FastAPI service. Owns users, alerts, cases, audit trail. Reads global models from
  a read-only registry volume. Hosts the assistant gateway so the Gemini API key never reaches the browser.
- **PostgreSQL** – platform data only. Contains no bank training data.
- **AI engine** – one Python package run in different roles: coordinator (`fraud_ai.federated.server`) or
  bank client (`fraud_ai.federated.client`, selected via `BANK_ID`).

## Data flows
1. **Training:** coordinator sends global parameters → each bank trains locally on its own data → returns
   updated parameters → coordinator aggregates (FedAvg initially) → global model written to the registry.
2. **Scoring:** each bank scores its own transactions with the global model, on the bank side.
3. **Investigation:** banks emit alert-level metadata (pseudonymised keys, score, feature attributions) to the
   platform API. Investigators see cross-bank patterns from this metadata, never raw training data.

## Design decisions to record as ADRs (docs/adr/)
- Flower for FL orchestration; FedAvg first, then FedProx for non-IID banks
- Pseudonymisation scheme for cross-bank entity linkage (keyed hash, key management)
- Alert schema contract between banks and platform
