# Base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Poetry/Pip configuration
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Set work directory
WORKDIR /app

# Install system dependencies
# WeasyPrint needs: libpango-1.0-0 libpangoft2-1.0-0 libopenjp2-7
# Postgres needs: libpq-dev (often included or needed for building psycopg2)
# General build: build-essential
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libopenjp2-7 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install \
    "Django>=5.0" \
    daphne \
    psycopg2-binary \
    google-cloud-aiplatform \
    google-cloud-storage \
    python-dotenv \
    weasyprint \
    markdown

# Copy project
COPY . /app/

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
