FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Minimal OS deps (no ODBC — app communicates with API over HTTP only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY pyproject.toml ./
COPY src/ ./src/

# Install app dependencies (streamlit, httpx, plotly — no pyodbc)
RUN uv sync --extra app

# Copy app source
COPY app/ ./app/

ENV PATH="/app/.venv/bin:$PATH"

# Default API URL for Docker Compose networking (overridable via environment)
ENV API_BASE_URL="http://api:8000/api/v1"

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "app/Home.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
