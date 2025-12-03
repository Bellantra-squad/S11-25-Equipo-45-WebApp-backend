# Use a specific version of Python slim image for better stability
FROM python:3.12-slim AS builder

# Build-time environment selector (local|production)
ARG BUILD_ENV=local

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/base.txt requirements/base.txt
COPY requirements/local.txt requirements/local.txt
COPY requirements/production.txt requirements/production.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && if [ "$BUILD_ENV" = "production" ]; then \
    pip install --no-cache-dir -r requirements/production.txt; \
    else \
    pip install --no-cache-dir -r requirements/local.txt; \
    fi

# Copy project files
COPY . .

# Make entrypoint executable (uses existing entrypoint.sh with ASGI + uvicorn worker)
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Command to run the application with ASGI support for WebSockets
CMD ["/app/entrypoint.sh"]
