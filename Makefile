COMPOSE := docker compose -f infra/docker-compose.yml --env-file .env
PY := uv run --directory backend

.PHONY: dev up down test lint typecheck eval-smoke eval-full tables figures reproduce demo-data

dev:
	$(COMPOSE) up -d postgres redis

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

test:
	$(PY) pytest
	npm --prefix frontend test

lint:
	$(PY) ruff check .
	$(PY) ruff format --check .

typecheck:
	$(PY) mypy

# The evaluation targets below are wired up in Phase 7.
eval-smoke eval-full tables figures reproduce demo-data:
	@echo "$@ is not implemented yet (Phase 7)" && exit 1
