FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# System dependencies for WeasyPrint, Playwright, python-pptx
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --prefer-binary --retries 10 --timeout 1000 -r requirements.txt

# Install Playwright chromium for image/thumbnail rendering
RUN playwright install chromium && playwright install-deps chromium

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/cache /app/data/embeddings /app/data/research /app/data/logs /app/data/exports \
    && useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app /ms-playwright

# Environment
ENV ENVIRONMENT=production \
    API_HOST=0.0.0.0 \
    API_PORT=8080 \
    PORT=8080 \
    WEBSITES_PORT=8080 \
    DATA_PATH=/app/data \
    EMBEDDINGS_PATH=/app/data/embeddings \
    CACHE_PATH=/app/data/cache \
    RESEARCH_PATH=/app/data/research \
    LOGS_PATH=/app/data/logs

EXPOSE 8080

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os, httpx; httpx.get(f'http://127.0.0.1:{os.getenv(\"PORT\", os.getenv(\"API_PORT\", \"8080\"))}/health', timeout=5).raise_for_status()"

# Run with uvicorn. Shell form lets Azure App Service inject PORT.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${WEB_CONCURRENCY:-2}"]
