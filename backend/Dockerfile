# Builder Stage
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1. Copy the workspace configuration and lockfile
COPY pyproject.toml uv.lock ./
# 2. Copy the relevant sub-project
COPY backend/ ./backend/

# Pre-load tockenizer model
ENV HF_HOME=/app/hf.cache
RUN uv run backend/pre-load.py

# 3. Synchronize dependencies
RUN uv sync --frozen --no-dev --package backend


# Final Stage
FROM python:3.13-slim
WORKDIR /app

# Copy the venv from the builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend
COPY --from=builder /app/hf.cache /app/hf.cache

# Create directories for mounts and set permissions
RUN mkdir -p /app/backend/db /app/backend/logs \
  && chmod 777 /app/backend/db /app/backend/logs

# Ensure the venv is used
ENV PATH="/app/.venv/bin:$PATH"
ENV HF_HOME=/app/hf.cache
ENV HF_HUB_OFFLINE=1

# Set the working directory to the backend for your script
WORKDIR /app/backend

# Use your specific serve script
CMD ["sh", "serve.sh"]
