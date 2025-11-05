.PHONY: help install dev test lint format typecheck clean migrate run compose-up compose-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install --with dev

dev: ## Run dev server
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	poetry run pytest -v

lint: ## Lint with ruff
	poetry run ruff check .

format: ## Format with ruff
	poetry run ruff format .

typecheck: ## Type check with mypy
	poetry run mypy .

clean: ## Clean cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache

migrate: ## Run Alembic migrations
	poetry run alembic upgrade head

migration: ## Create new migration (usage: make migration m="message")
	poetry run alembic revision --autogenerate -m "$(m)"

run: ## Run with gunicorn
	poetry run gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000

compose-up: ## Start Docker Compose
	docker-compose up -d --build

compose-down: ## Stop Docker Compose
	docker-compose down

compose-logs: ## Show Docker Compose logs
	docker-compose logs -f

precommit-install: ## Install pre-commit hooks
	poetry run pre-commit install

precommit-run: ## Run pre-commit on all files
	poetry run pre-commit run --all-files