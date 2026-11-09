.PHONY: up up-fl down logs migrate test test-backend test-ai test-frontend

up:            ; docker compose up --build
up-fl:         ; docker compose --profile federated up --build
down:          ; docker compose --profile federated down
logs:          ; docker compose logs -f
migrate:       ; docker compose exec backend alembic upgrade head

test: test-backend test-ai test-frontend
test-backend:  ; cd backend && python -m pytest
test-ai:       ; cd ai_engine && python -m pytest
test-frontend: ; cd frontend && npm test
