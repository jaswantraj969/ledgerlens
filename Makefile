COMPOSE := docker compose -f infra/docker-compose.yml --env-file .env
PY := uv run --directory backend

.PHONY: dev up down test lint typecheck ci eval-smoke eval-full tables figures reproduce demo-data

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

# Local mirror of .github/workflows/ci.yml; see the script header for what it does not prove.
ci:
	bash -c 'set -o pipefail; bash scripts/ci_local.sh 2>&1 | tee docs/progress/logs/ci-local.txt'

# The evaluation targets below are wired up in Phase 7.
eval-smoke eval-full tables figures reproduce demo-data:
	@echo "$@ is not implemented yet (Phase 7)" && exit 1
