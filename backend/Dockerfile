# syntax=docker/dockerfile:1

# 1. Set the base version. 3.12-slim is the best choice for stability.
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files and buffering logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 2. Install system dependencies needed for psycopg2 (PostgreSQL)
# These must be installed before 'pip install'
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# 4. Install Python dependencies
# We copy pyproject.toml separately to leverage Docker caching
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# 5. Copy the rest of the application code
COPY . .

# 6. Switch to the non-privileged user
USER appuser

# 7. Expose the port and start the application
EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.config.py", "app.main:app"]