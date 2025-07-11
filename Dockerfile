FROM python:3.12-slim

# Set Python environment variables for container optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install uv
RUN pip install uv

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy the application
COPY . .
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
