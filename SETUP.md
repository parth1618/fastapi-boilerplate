# FastAPI Boilerplate - Complete Setup Guide

This comprehensive guide will walk you through setting up the FastAPI boilerplate from scratch to a fully functional development environment.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start with Docker](#quick-start-with-docker)
3. [Local Development Setup](#local-development-setup)
4. [Database Setup](#database-setup)
5. [Environment Configuration](#environment-configuration)
6. [Development Workflow](#development-workflow)
7. [Testing Setup](#testing-setup)
8. [IDE Configuration](#ide-configuration)
9. [Troubleshooting](#troubleshooting)
10. [Production Deployment](#production-deployment)

---

## Prerequisites

Ensure you have the following installed on your system:

### Required Software

| Software | Version | Installation |
|----------|---------|--------------|
| **Python** | 3.11+ | [Download](https://www.python.org/downloads/) |
| **Docker** | Latest | [Download](https://docs.docker.com/get-docker/) |
| **Docker Compose** | Latest | Included with Docker Desktop |
| **Poetry** | 1.8.0+ | `curl -sSL https://install.python-poetry.org \| python3 -` |
| **Git** | Latest | [Download](https://git-scm.com/downloads) |

### Optional but Recommended

- **PostgreSQL** 16+ (for local development without Docker)
- **Redis** 7+ (for local development without Docker)
- **Make** (for using Makefile commands)

### Verify Installation

```bash
# Check Python version
python --version  # Should be 3.11 or higher

# Check Docker
docker --version
docker-compose --version

# Check Poetry
poetry --version

# Check Git
git --version
```

---

## Quick Start with Docker

This is the **recommended** approach for getting started quickly.

### Step 1: Clone the Repository

```bash
git clone https://github.com/parth1618/fastapi-boilerplate.git
cd fastapi-boilerplate
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if needed (default values work for Docker)
nano .env  # or use your preferred editor
```

### Step 3: Start All Services

```bash
# Start PostgreSQL, Redis, Jaeger, OpenTelemetry Collector, and Prometheus
make compose-up

# Or manually:
docker-compose up -d
```

This command will:
- ✅ Pull required Docker images
- ✅ Start PostgreSQL database
- ✅ Start Redis cache
- ✅ Start Jaeger for distributed tracing
- ✅ Start OpenTelemetry Collector
- ✅ Start Prometheus for metrics
- ✅ Create network connections

### Step 4: Verify Services

```bash
# Check all services are running
docker-compose ps

# Expected output should show all services as "Up"
```

### Step 5: Run Database Migrations

```bash
# Install dependencies first
make install

# Run migrations to create database tables
make migrate

# Or manually:
poetry run alembic upgrade head
```

### Step 6: Initialize Database

```bash
# Create default admin user
poetry run python -m app.db.init_db
```

### Step 7: Start Development Server

```bash
# Start the FastAPI application
make dev

# Or manually:
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 8: Verify Installation

Open your browser and navigate to:

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Jaeger UI**: http://localhost:16686
- **Prometheus**: http://localhost:9091

Test the API:

```bash
# Health check
curl http://localhost:8000/health

# Should return JSON with status information
```

### Step 9: Test Authentication

```bash
# Login with default admin credentials
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# Should return access_token and refresh_token
```

---

## Local Development Setup

For development without Docker (requires local PostgreSQL and Redis).

### Step 1: Clone Repository

```bash
git clone https://github.com/parth1618/fastapi-boilerplate.git
cd fastapi-boilerplate
```

### Step 2: Install Poetry

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH (Linux/Mac)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For Mac with zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Install Dependencies

```bash
# Install all dependencies including dev dependencies
make install

# Or manually:
poetry install --with dev

# Verify installation
poetry run python --version
```

### Step 4: Install PostgreSQL Locally

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS (using Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Create Database:**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE appdb;
CREATE USER postgres WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE appdb TO postgres;
\q
```

### Step 5: Install Redis Locally

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**Verify Redis:**
```bash
redis-cli ping
# Should return: PONG
```

### Step 6: Configure Environment

```bash
# Copy environment template
cp .env.example .env
```

Edit `.env` with your local settings:

```env
# Environment
ENVIRONMENT=development
DEBUG=true

# Database (Local)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/appdb

# Redis (Local)
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# OpenTelemetry (disable for local dev if not using)
OTEL_ENABLED=false
```

### Step 7: Run Migrations

```bash
# Run database migrations
make migrate

# Or manually:
poetry run alembic upgrade head
```

### Step 8: Initialize Database

```bash
# Create default admin user
poetry run python -m app.db.init_db
```

### Step 9: Start Development Server

```bash
# Start FastAPI with auto-reload
make dev

# Or manually:
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Database Setup

### Creating Migrations

```bash
# Auto-generate migration from model changes
make migration m="add_user_profile_fields"

# Or manually:
poetry run alembic revision --autogenerate -m "add_user_profile_fields"
```

### Applying Migrations

```bash
# Apply all pending migrations
make migrate

# Or manually:
poetry run alembic upgrade head
```

### Migration Management

```bash
# View migration history
poetry run alembic history

# Rollback last migration
poetry run alembic downgrade -1

# Rollback to specific version
poetry run alembic downgrade <revision_id>

# View current migration version
poetry run alembic current
```

### Reset Database (⚠️ Destructive)

```bash
# Stop services
docker-compose down -v

# Restart and re-migrate
docker-compose up -d postgres redis
make migrate
poetry run python -m app.db.init_db
```

---

## Environment Configuration

### Required Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | ✅ |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | ✅ |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | - | ✅ |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` | ❌ |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` | ❌ |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` | ❌ |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application environment | `development` |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (json/text) | `json` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `RATE_LIMIT_PER_MINUTE` | Requests per minute | `100` |
| `OTEL_ENABLED` | Enable OpenTelemetry | `false` |
| `METRICS_ENABLED` | Enable Prometheus metrics | `true` |
| `CACHE_ENABLED` | Enable Redis caching | `true` |

### Generating Secret Keys

```python
# Generate a secure JWT secret key
import secrets
print(secrets.token_urlsafe(32))
```

Or use command line:

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Development Workflow

### Daily Development Flow

```bash
# 1. Start services
make compose-up  # or make dev for local

# 2. Create a feature branch
git checkout -b feature/my-new-feature

# 3. Make code changes
# Edit files in app/

# 4. Run tests frequently
make test

# 5. Check code quality
make lint
make format
make typecheck

# 6. Commit changes (pre-commit hooks will run)
git add .
git commit -m "feat: add new feature"

# 7. Push changes
git push origin feature/my-new-feature
```

### Making Code Changes

**Adding a New Endpoint:**

1. Create endpoint file in `app/api/v1/endpoints/`
2. Add service logic in `app/services/`
3. Create schemas in `app/schemas/`
4. Write tests in `tests/api/`
5. Update router in `app/api/v1/router.py`

**Adding a New Model:**

1. Create model in `app/models/`
2. Import in `app/models/__init__.py`
3. Create migration: `make migration m="add_new_model"`
4. Apply migration: `make migrate`
5. Create corresponding schemas

### Code Quality Checks

```bash
# Lint code with Ruff
make lint

# Auto-format code
make format

# Type check with MyPy
make typecheck

# Run all checks
make lint && make format && make typecheck
```

---

## Testing Setup

### Running Tests

```bash
# Run all tests
make test

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/api/test_auth.py -v

# Run specific test function
poetry run pytest tests/api/test_auth.py::test_register_user -v

# Run tests with coverage
poetry run pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Writing Tests

Tests are located in the `tests/` directory and use pytest with async support.

**Example Test:**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio()
async def test_create_user(client: AsyncClient) -> None:
    """Test user creation endpoint."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123",
            "full_name": "Test User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

### Test Configuration

Tests use an in-memory SQLite database by default (configured in `tests/conftest.py`).

---

## IDE Configuration

### Visual Studio Code

**Recommended Extensions:**

Create `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "ms-azuretools.vscode-docker",
    "github.copilot",
    "ms-python.black-formatter"
  ]
}
```

**Settings:**

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true,
      "source.fixAll": true
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.rulers": [100],
  "files.trimTrailingWhitespace": true
}
```

### PyCharm / IntelliJ IDEA

1. **Open Project**: File → Open → Select project directory
2. **Configure Interpreter**:
   - File → Settings → Project → Python Interpreter
   - Add Interpreter → Poetry Environment
   - Select existing Poetry environment
3. **Enable Ruff**:
   - Settings → Tools → External Tools → Add
   - Program: `poetry`
   - Arguments: `run ruff check $FilePath$`
4. **Configure Tests**:
   - Settings → Tools → Python Integrated Tools
   - Default test runner: pytest

---

## Troubleshooting

### Common Issues and Solutions

#### Port Already in Use

**Problem:** Port 8000 is already in use

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
poetry run uvicorn app.main:app --reload --port 8001
```

#### Database Connection Error

**Problem:** Cannot connect to PostgreSQL

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U postgres -d appdb

# Restart PostgreSQL
docker-compose restart postgres
```

#### Redis Connection Error

**Problem:** Cannot connect to Redis

**Solution:**
```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

#### Migration Errors

**Problem:** Alembic migration fails

**Solution:**
```bash
# View migration history
poetry run alembic history

# Rollback to previous version
poetry run alembic downgrade -1

# Reset database (⚠️ deletes all data)
docker-compose down -v
docker-compose up -d postgres redis
make migrate
```

#### Poetry Lock File Issues

**Problem:** poetry.lock is out of sync

**Solution:**
```bash
# Update lock file
poetry lock --no-update

# Or regenerate
rm poetry.lock
poetry install
```

#### Import Errors

**Problem:** Module not found errors

**Solution:**
```bash
# Ensure you're in the Poetry environment
poetry shell

# Reinstall dependencies
poetry install

# Check Python path
poetry run python -c "import sys; print(sys.path)"
```

#### Docker Build Failures

**Problem:** Docker build fails

**Solution:**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check Dockerfile syntax
docker build -t test .
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Change `JWT_SECRET_KEY` to a strong random value
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Update `DATABASE_URL` to production database
- [ ] Update `REDIS_URL` to production Redis
- [ ] Configure `CORS_ORIGINS` for your frontend domain
- [ ] Enable HTTPS/TLS
- [ ] Set up database backups
- [ ] Configure monitoring and alerting
- [ ] Review security settings
- [ ] Set up logging aggregation

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=<generate-strong-key>
DATABASE_URL=postgresql+asyncpg://user:pass@prod-host:5432/db
REDIS_URL=redis://prod-redis:6379/0
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
LOG_FORMAT=json
RATE_LIMIT_PER_MINUTE=60
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

### Docker Production Build

```bash
# Build production image
docker build -t fastapi-boilerplate:v1.0.0 .

# Tag for registry
docker tag fastapi-boilerplate:v1.0.0 registry.example.com/fastapi-boilerplate:v1.0.0

# Push to registry
docker push registry.example.com/fastapi-boilerplate:v1.0.0
```

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      containers:
      - name: app
        image: fastapi-boilerplate:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: jwt-secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## Post-Setup Steps

### 1. Install Pre-commit Hooks

```bash
make precommit-install

# Test pre-commit
make precommit-run
```

### 2. Create Your First API Endpoint

See the project structure and examples in `app/api/v1/endpoints/`

### 3. Configure Monitoring

- Access Jaeger UI: http://localhost:16686
- Access Prometheus: http://localhost:9091
- Configure alerting rules

### 4. Set Up CI/CD

The project includes GitHub Actions workflows in `.github/workflows/ci.yml`

### 5. Read Documentation

- Review README.md for project overview
- Check CONTRIBUTING.md for contribution guidelines
- Explore API docs at `/docs`

---

## Getting Help

### Resources

- **Documentation**: README.md, API docs at `/docs`
- **GitHub Issues**: [Report bugs](https://github.com/parth1618/fastapi-boilerplate/issues)
- **Discussions**: [Ask questions](https://github.com/parth1618/fastapi-boilerplate/discussions)

### Community Support

- Stack Overflow: Tag with `fastapi`
- FastAPI Discord: [Join server](https://discord.gg/fastapi)
- Reddit: r/FastAPI

---

## Next Steps

1. **Customize Models**: Add your domain models in `app/models/`
2. **Add Endpoints**: Create new API endpoints in `app/api/v1/endpoints/`
3. **Write Tests**: Add comprehensive tests in `tests/`
4. **Configure CI/CD**: Customize GitHub Actions workflows
5. **Deploy**: Follow production deployment guide

---

## Appendix

### Useful Commands Reference

```bash
# Development
make dev              # Start dev server
make install          # Install dependencies
make migrate          # Run migrations
make migration m=""   # Create migration

# Testing
make test             # Run tests
make test-cov         # Run with coverage

# Code Quality
make lint             # Lint code
make format           # Format code
make typecheck        # Type check
make clean            # Clean cache

# Docker
make compose-up       # Start services
make compose-down     # Stop services
make compose-logs     # View logs

# Database
make migrate          # Apply migrations
make migration        # Create migration
```

### Directory Structure Reference

```
fastapi-boilerplate/
├── app/                    # Application code
│   ├── api/               # API endpoints
│   ├── core/              # Core config & security
│   ├── db/                # Database setup
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── middleware/        # Custom middleware
│   ├── dependencies/      # FastAPI dependencies
│   └── utils/             # Utility functions
├── tests/                 # Test suite
├── migrations/            # Alembic migrations
├── .github/workflows/     # CI/CD pipelines
└── docker-compose.yml     # Docker services
```

---

**Setup Version**: 1.0.0
**Last Updated**: November 5, 2025
**Maintained By**: FastAPI Boilerplate Team