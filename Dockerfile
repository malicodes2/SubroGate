# ==============================================================================
# Multi-Stage Dockerfile for SubroGate Enterprise Subrogation Console
# Combines React TypeScript Frontend and FastAPI Vertex AI Backend in a single
# high-performance, lightweight Google Cloud Run container.
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Compile React Frontend SPA
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install frontend dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Build production bundle
COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# STAGE 2: Python Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Environment configurations
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    SUBROGATE_ENV=production \
    SUBROGATE_HOST=0.0.0.0 \
    SUBROGATE_PORT=8080

# Install runtime utilities (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root security user
RUN groupadd -r subrogate && useradd -r -g subrogate -d /app -s /sbin/nologin subrogate

WORKDIR /app

# Install Python backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application backend codebase
COPY backend/ /app/backend/

# Copy compiled React frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Grant ownership to non-root user
RUN chown -R subrogate:subrogate /app

# Switch to non-root user
USER subrogate

# Expose dynamic Cloud Run container port
EXPOSE 8080

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT}/health || exit 1

# Launch application with exec to guarantee SIGTERM graceful shutdown handling
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
