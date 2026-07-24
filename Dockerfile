# ── Stage 1: Base & Dependencies ───────────────────────────────────────
FROM python:3.11-slim as builder

# Set environment variables for Poetry
ENV POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (creates .venv in /app)
RUN poetry install --only main --no-root

# Install the Spacy model required by Presidio
RUN poetry run python -m spacy download en_core_web_lg


# ── Stage 2: Runtime ───────────────────────────────────────────────────
FROM python:3.11-slim as runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy virtual environment and spacy models from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY ./app ./app
COPY ./migrations ./migrations
COPY alembic.ini ./

# Expose port
EXPOSE 8000

# Run migrations and start the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
