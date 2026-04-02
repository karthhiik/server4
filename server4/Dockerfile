FROM python:3.12-slim

WORKDIR /app

# System dependencies for WeasyPrint, Playwright, python-pptx
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright chromium for image/thumbnail rendering
RUN playwright install chromium && playwright install-deps chromium

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/cache /app/data/logs /app/data/exports

# Environment
ENV ENVIRONMENT=production \
    API_HOST=0.0.0.0 \
    API_PORT=8003 \
    DATA_PATH=/app/data \
    CACHE_PATH=/app/data/cache \
    LOGS_PATH=/app/data/logs

EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8003/health').raise_for_status()"

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "2"]
