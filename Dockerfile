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

# Create an entrypoint script to run migrations before starting the server
RUN echo '#!/bin/bash\n\
    set -e\n\
    \n\
    # Wait for database to be ready\n\
    echo "Waiting for database..."\n\
    sleep 5\n\
    \n\
    # Run migrations\n\
    echo "Running migrations..."\n\
    python manage.py migrate --noinput || true\n\
    \n\
    # Collect static files if in production\n\
    if [ "$BUILD_ENV" = "production" ]; then\n\
    echo "Collecting static files..."\n\
    python manage.py collectstatic --noinput || true\n\
    fi\n\
    \n\
    # Start server\n\
    echo "Starting server..."\n\
    exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT\n' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Command to run the application
CMD ["/app/entrypoint.sh"]
