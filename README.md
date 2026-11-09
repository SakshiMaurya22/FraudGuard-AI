# FraudGuard AI – Federated AI Fraud Detection Platform

> **Academic prototype disclaimer:** This project is an academic prototype inspired by publicly documented research in federated learning for financial crime detection. It is not affiliated with, endorsed by, or derived from JPMorgan Chase. All data is synthetic, and the platform is not intended for production financial decisions.

## Overview

FraudGuard AI is a privacy-focused financial fraud detection and investigation platform built around federated learning.

It uses three simulated independent institutions:

- Bank Alpha
- Bank Beta
- Bank Gamma

Each institution keeps its transaction data locally. The federated learning approach allows institutions to collaboratively train a fraud detection model by sharing model parameter updates rather than raw transaction records.

The platform also provides an investigator-facing web application for reviewing alerts, managing investigations, and exploring fraud-related information.

## Architecture

- **Frontend:** React and TypeScript
- **Backend:** FastAPI
- **Database:** PostgreSQL
- **Machine Learning:** PyTorch and Flower
- **AI Assistant:** Google Gemini integration with a rule-based fallback

The intended architecture separates bank-level training data from the central coordinator. Only model updates are exchanged during federated training.

## Tech Stack

| Area | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL, Alembic |
| AI/ML | PyTorch, Flower, scikit-learn, XGBoost |
| Assistant | Google Gemini |
| Testing | Pytest, Vitest |
| Deployment | Docker, Docker Compose |

## Project Structure

```text
backend/       FastAPI application and database integration
ai_engine/     Federated learning and fraud detection modules
frontend/      React and TypeScript application
database/      Database initialization and seed files
scripts/       Helper scripts
config/        Shared configuration
docs/          Architecture and project documentation
tests/         Integration and end-to-end tests
```

## Core Concepts

1. **Federated Learning:** Collaborative model training across simulated banks.
2. **Privacy Preservation:** Raw bank transaction data is intended to remain local.
3. **Fraud Detection:** Machine learning models for identifying potentially fraudulent transactions.
4. **Investigation Platform:** A web interface for investigators to review alerts and related information.
5. **AI Assistance:** Gemini integration with a rule-based fallback.

## Academic Project Limitations

- The institutions and transaction data are simulated.
- Federated learning does not automatically guarantee complete privacy.
- Model updates can potentially leak information.
- Real-world performance and production security have not been established.

## Project Status

This repository contains the current implementation of an evolving academic project. Some planned components may be incomplete or require additional configuration.

## Disclaimer

FraudGuard AI is an independent academic project. It is not an official product of any bank or financial institution.