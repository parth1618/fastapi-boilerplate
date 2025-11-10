# Multi-stage production Dockerfile with security hardening
# Stage 1: Builder - Install dependencies and build
FROM python:3.11-slim AS builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  POETRY_VERSION=1.8.4 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_IN_PROJECT=1 \
  POETRY_VIRTUALENVS_CREATE=1 \
  POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  # Build essentials
  gcc \
  g++ \
  make \
  # PostgreSQL client
  postgresql-client \
  libpq-dev \
  # Required for some Python packages
  git \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies
# --without dev: Don't install dev dependencies
# --no-root: Don't install the project itself yet
RUN poetry install --without dev --no-root --no-interaction --no-ansi \
  && rm -rf ${POETRY_CACHE_DIR}

# ================================
# Stage 2: Runtime - Production image
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PATH="/app/.venv/bin:$PATH" \
  # Security: Drop privileges
  APP_USER=appuser \
  APP_GROUP=appuser \
  APP_HOME=/app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
  # PostgreSQL client for database operations
  postgresql-client \
  # Health check utility
  curl \
  # Timezone data
  tzdata \
  # CA certificates for HTTPS
  ca-certificates \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

# Create non-root user and group
RUN groupadd -r ${APP_GROUP} && \
  useradd -r -g ${APP_GROUP} -d ${APP_HOME} -s /sbin/nologin \
  -c "Application user" ${APP_USER}

# Set working directory
WORKDIR ${APP_HOME}

# Copy virtual environment from builder
COPY --from=builder --chown=${APP_USER}:${APP_GROUP} /app/.venv ./.venv

# Copy application code
COPY --chown=${APP_USER}:${APP_GROUP} . .

# Create necessary directories
RUN mkdir -p logs uploads \
  && chown -R ${APP_USER}:${APP_GROUP} logs uploads

# Switch to non-root user
USER ${APP_USER}

# Expose application port
EXPOSE 8000

# Health check
# Check every 30s, timeout 10s, start checking after 40s, retry 3 times
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command: Run with gunicorn
CMD ["gunicorn", \
  "-k", "uvicorn.workers.UvicornWorker", \
  "app.main:app", \
  "--bind", "0.0.0.0:8000", \
  "--workers", "4", \
  "--worker-class", "uvicorn.workers.UvicornWorker", \
  "--timeout", "120", \
  "--keepalive", "5", \
  "--access-logfile", "-", \
  "--error-logfile", "-", \
  "--log-level", "info"]

# ================================
# Stage 3: Development image (optional)
FROM runtime AS development

# Switch back to root for installing dev dependencies
USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  vim \
  && rm -rf /var/lib/apt/lists/*

# Copy dev dependencies
COPY --from=builder /app/.venv /app/.venv

# Install additional dev dependencies
RUN . .venv/bin/activate && \
  pip install --no-cache-dir \
  debugpy \
  ipython

# Switch back to app user
USER ${APP_USER}

# Override CMD for development (with reload)
CMD ["uvicorn", "app.main:app", \
  "--host", "0.0.0.0", \
  "--port", "8000", \
  "--reload", \
  "--log-level", "debug"]

# ================================
# Build Arguments and Environment Variables
# ================================
# Build with: docker build --target runtime -t myapp:prod .
#
# Environment variables to set at runtime:
# - DATABASE_URL
# - REDIS_URL
# - JWT_SECRET_KEY
# - ENVIRONMENT (production|staging|development)
# - LOG_LEVEL
# - OTEL_EXPORTER_OTLP_ENDPOINT
