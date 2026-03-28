FROM python:3.11-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code:/code/server3
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=600

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching.
COPY server3/requirements.txt /code/server3/requirements.txt
RUN python -m pip install --no-cache-dir --retries 10 --prefer-binary -r /code/server3/requirements.txt

# Copy app code and shared package from workspace root build context.
COPY server3 /code/server3
COPY server3/.env /code/server3/.env
COPY shared_security /code/shared_security

# Create uploads directory
RUN mkdir -p /code/server3/uploads && chmod 755 /code/server3/uploads

WORKDIR /code/server3

EXPOSE 8080

# Longer startup period for Azure
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
	CMD curl -f http://127.0.0.1:${PORT:-8080}/healthz || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 120"]
