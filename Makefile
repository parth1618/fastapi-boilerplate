.PHONY: help install dev test lint format typecheck security clean migrate run compose-up compose-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ═══════════════════════════════════════════════════════════
# SETUP & INSTALLATION
# ═══════════════════════════════════════════════════════════

install: ## Install dependencies
	poetry install --with dev

install-prod: ## Install production dependencies only
	poetry install --without dev

update: ## Update dependencies
	poetry update

# ═══════════════════════════════════════════════════════════
# DEVELOPMENT
# ═══════════════════════════════════════════════════════════

dev: ## Run dev server with hot reload
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-debug: ## Run dev server with debug logging
	LOG_LEVEL=DEBUG poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run: ## Run with gunicorn (production-like)
	poetry run gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --workers 4

# ═══════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════

test: ## Run tests
	poetry run pytest -v

test-cov: ## Run tests with coverage
	poetry run pytest -v --cov=app --cov-report=html --cov-report=term-missing

test-cov-xml: ## Run tests with XML coverage (for CI)
	poetry run pytest -v --cov=app --cov-report=xml

test-watch: ## Run tests in watch mode
	poetry run ptw -- -v

test-failed: ## Run only failed tests
	poetry run pytest --lf -v

test-markers: ## Show available test markers
	poetry run pytest --markers

# ═══════════════════════════════════════════════════════════
# CODE QUALITY
# ═══════════════════════════════════════════════════════════

lint: ## Lint with ruff
	poetry run ruff check .

lint-fix: ## Lint and fix with ruff
	poetry run ruff check . --fix

format: ## Format with ruff
	poetry run ruff format .

format-check: ## Check formatting without making changes
	poetry run ruff format . --check

typecheck: ## Type check with mypy
	poetry run mypy .

# ═══════════════════════════════════════════════════════════
# SECURITY
# ═══════════════════════════════════════════════════════════

security: ## Run all security checks
	@echo "Running Bandit security checks..."
	poetry run bandit -c pyproject.toml -r app/
	@echo "\nChecking for secrets..."
	poetry run detect-secrets scan --baseline .secrets.baseline

security-baseline: ## Update secrets baseline
	poetry run detect-secrets scan > .secrets.baseline

bandit: ## Run bandit security checks
	poetry run bandit -c pyproject.toml -r app/

safety: ## Check dependencies for vulnerabilities
	@echo "Safety check requires manual review of dependencies"
	@echo "Run: poetry show --outdated"
	poetry show --outdated

# ═══════════════════════════════════════════════════════════
# PRE-COMMIT
# ═══════════════════════════════════════════════════════════

precommit-install: ## Install pre-commit hooks
	poetry run pre-commit install --install-hooks
	poetry run pre-commit install --hook-type commit-msg

precommit-uninstall: ## Uninstall pre-commit hooks
	poetry run pre-commit uninstall
	poetry run pre-commit uninstall --hook-type commit-msg

precommit-run: ## Run pre-commit on all files
	rm -rf .mypy_cache || true
	poetry run pre-commit run --all-files

precommit-update: ## Update pre-commit hooks
	poetry run pre-commit autoupdate

# ═══════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════

migrate: ## Run Alembic migrations
	poetry run alembic upgrade head

migrate-down: ## Downgrade one migration
	poetry run alembic downgrade -1

migration: ## Create new migration (usage: make migration m="message")
	poetry run alembic revision --autogenerate -m "$(m)"

migration-history: ## Show migration history
	poetry run alembic history

migration-current: ## Show current migration
	poetry run alembic current

db-reset: ## Reset database (WARNING: destructive)
	poetry run alembic downgrade base
	poetry run alembic upgrade head

# ═══════════════════════════════════════════════════════════
# DOCKER
# ═══════════════════════════════════════════════════════════

compose-up: ## Start Docker Compose services
	docker-compose up -d --build

compose-down: ## Stop Docker Compose services
	docker-compose down

compose-logs: ## Show Docker Compose logs
	docker-compose logs -f

compose-ps: ## Show running containers
	docker-compose ps

compose-rebuild: ## Rebuild and restart services
	docker-compose down
	docker-compose up -d --build

docker-build: ## Build Docker image
	docker build -t fastapi-boilerplate:latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env fastapi-boilerplate:latest

# ═══════════════════════════════════════════════════════════
# CLEANING
# ═══════════════════════════════════════════════════════════

clean: ## Clean cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/ dist/ build/

clean-all: clean ## Clean everything including venv
	rm -rf .venv/

# ═══════════════════════════════════════════════════════════
# CI/CD SIMULATION
# ═══════════════════════════════════════════════════════════

ci: ## Run full CI pipeline locally
	@echo "=== Running CI Pipeline ==="
	@echo "\n[1/6] Installing dependencies..."
	@$(MAKE) install
	@echo "\n[2/6] Running linting..."
	@$(MAKE) lint
	@echo "\n[3/6] Running tests with coverage..."
	@$(MAKE) test-cov-xml
	@echo "\n[4/6] Running security checks..."
	@$(MAKE) security
	@echo "\n[5/6] Type checking..."
	@$(MAKE) typecheck
	@echo "\n[6/6] Building Docker image..."
	@$(MAKE) docker-build
	@echo "\n=== ✅ CI Pipeline Completed Successfully ==="

# ═══════════════════════════════════════════════════════════
# DOCUMENTATION
# ═══════════════════════════════════════════════════════════

docs-serve: ## Serve API documentation
	@echo "API Docs available at: http://localhost:8000/docs"
	@echo "ReDoc available at: http://localhost:8000/redoc"
	@$(MAKE) dev

# ═══════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════

shell: ## Open Python shell with app context
	poetry run python -i -c "from app.main import app; from app.db.session import get_db"

check-deps: ## Check for outdated dependencies
	poetry show --outdated

check-poetry: ## Validate poetry configuration
	poetry check

env-example: ## Generate .env.example from .env
	grep -v '^#' .env | sed 's/=.*/=/' > .env.example || true

backup-db: ## Backup database (for SQLite)
	@if [ -f "app.db" ]; then \
		cp app.db "app.db.backup.$$(date +%Y%m%d_%H%M%S)"; \
		echo "Database backed up"; \
	else \
		echo "No database file found"; \
	fi
