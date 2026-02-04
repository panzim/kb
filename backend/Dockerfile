# Use a slim Python image
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1. Copy the workspace configuration and lockfile
COPY pyproject.toml uv.lock ./
# 2. Copy the relevant sub-projects
COPY backend/ ./backend/

# 3. Synchronize dependencies 
# use --package backend to focus the install
RUN uv sync --frozen --no-dev --package backend

# Final Stage
FROM python:3.14-slim
WORKDIR /app

# Copy the venv from the builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend

# Create directories for mounts and set permissions
RUN mkdir -p /app/db /app/logs && chmod 777 /app/db /app/logs

# Ensure the venv is used
ENV PATH="/app/.venv/bin:$PATH"

# Set the working directory to the backend for your script
WORKDIR /app/backend

# Use your specific serve script
CMD ["sh", "serve.sh"]
