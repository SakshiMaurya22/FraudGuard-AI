# Federated AI – Privacy-Preserving Financial Fraud Detection & Investigation Platform

> **Disclaimer.** This is an **academic prototype**. It is **not** an official JPMorgan Chase
> product and is not affiliated with, endorsed by, or derived from any JPMorgan Chase system. It is
> *inspired by* publicly documented federated-learning research for financial crime detection, such
> as JPMorgan's Project AIKYA. All data is synthetic. Nothing here is production-ready or
> suitable for real financial decisions.

## What it does

Three simulated, independent institutions — **Bank Alpha**, **Bank Beta**, **Bank Gamma** — each
hold their own local transaction data. They jointly train a fraud-detection model with federated
learning (Flower + PyTorch). **Raw training records never reach the central coordinator**; only model
parameter updates do. Investigators use a web platform to review alerts, explore transaction graphs,
read model explanations, and ask an AI assistant (Gemini via the backend, with a rule-based fallback).

## Architecture

```
┌───────────────┐   REST/JWT   ┌──────────────┐        ┌────────────┐
│ React + TS UI │ ───────────► │   FastAPI    │ ─────► │ PostgreSQL │  users, alerts, cases,
│ (investigator)│              │   backend    │        └────────────┘  audit log, FL metrics
└───────────────┘              └──────┬───────┘
                                      │ read-only
                               ┌──────▼───────┐
                               │ model registry│◄──── writes global model ────┐
                               └──────────────┘                              │
                                                                  ┌──────────┴─────────┐
 ┌──────────────┐  parameters only  ┌──────────────────┐          │  Flower coordinator │
 │ Bank Alpha   │◄─────────────────►│                  │◄────────►│     (fl-server)     │
 │ local data ✔ │                   │   gRPC (Flower)  │          │ no access to data   │
 ├──────────────┤                   │                  │          └────────────────────┘
 │ Bank Beta    │◄─────────────────►│                  │
 ├──────────────┤                   │                  │
 │ Bank Gamma   │◄─────────────────►│                  │
 └──────────────┘                   └──────────────────┘
 Each bank scores its own transactions locally and sends only alert-level metadata
 (pseudonymised entity hashes, score, explanation) to the platform.
```

The privacy boundary is enforced at three levels: Docker volume mounts (each client mounts only its own
data, read-only; the coordinator mounts none), code guards (`fraud_ai/utils/privacy.py`), and tests.

Details: [`docs/architecture/overview.md`](docs/architecture/overview.md) ·
[`docs/security/privacy-model.md`](docs/security/privacy-model.md)

## Tech stack

| Area | Tools |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router, Axios, TanStack Query, Recharts, Lucide, Cytoscape.js |
| Backend | Python, FastAPI, SQLAlchemy 2, Pydantic v2, PostgreSQL, Alembic, JWT (PyJWT) |
| AI/ML | PyTorch, Flower, scikit-learn, XGBoost, NetworkX, Captum, Pandas, NumPy |
| Assistant | Google Gemini (server-side only) with rule-based fallback |
| Testing | Pytest, Vitest + Testing Library |
| Deployment | Docker, Docker Compose |

## Project layout

```
backend/      FastAPI app (core, db, models, schemas, api/v1, services, repositories) + Alembic + tests
ai_engine/    fraud_ai package (data, federated, models, graph, explainability, evaluation) + tests
              data/banks/{alpha,beta,gamma}/  isolated local data (gitignored)
frontend/     React app (api, components, pages, hooks, types, lib, routes, tests)
database/     init SQL and seeds
scripts/      helper scripts          config/   shared configuration
docs/         architecture, api, ml, security, ADRs
tests/        cross-service integration and e2e tests
```

## Quick start

```bash
cp .env.example .env              # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build         # postgres + backend (:8000) + frontend (:5173)
# open http://localhost:5173/status   and   http://localhost:8000/docs
docker compose --profile federated up --build   # adds the coordinator and 3 bank clients (Phase 3+)
```

Run tests locally:

```bash
make test-backend     # cd backend && pip install -r requirements-dev.txt
make test-ai          # cd ai_engine && pip install -r requirements-dev.txt
make test-frontend    # cd frontend && npm install
```

## Implementation status

Only what is checked below exists. Nothing is simulated or hardcoded.

- [x] **Phase 1 – Foundation:** folder structure, Docker Compose with per-bank isolation, settings with
      production safety checks, JWT/bcrypt primitives, DB session, Alembic wiring, health endpoints, privacy
      guards, frontend shell with API status page, unit/integration tests, CI
- [ ] **Phase 2 – Auth & data model:** users/roles, alerts, cases, audit log, migrations, auth endpoints
- [ ] **Phase 3 – Data & federated learning:** synthetic data generator with distinct per-bank distributions,
      local PyTorch model, Flower server/clients, centralized and local-only baselines (XGBoost) for comparison
- [ ] **Phase 4 – Evaluation:** PR-AUC/recall at fixed FPR per bank, federated vs local vs pooled comparison
- [ ] **Phase 5 – Investigation:** NetworkX graph analytics, Captum explanations, alerts and cases UI, Cytoscape graph
- [ ] **Phase 6 – Assistant:** Gemini gateway grounded on case data, rule-based fallback
- [ ] **Phase 7 – Hardening:** update clipping + differential-privacy noise, secure aggregation study, RBAC audit

## Known limitations (by design of the prototype)

- Federated learning does not by itself guarantee privacy: model updates can leak information
  (membership inference, gradient inversion). Mitigations are planned in Phase 7 and will be measured, not assumed.
- All banks run on one machine; network, latency and trust assumptions are simulated.
- Data is synthetic, so reported metrics say nothing about real-world fraud performance.
