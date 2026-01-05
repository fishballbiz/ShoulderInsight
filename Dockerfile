# Base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Set work directory
WORKDIR /app

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install \
    "Django>=5.0" \
    daphne \
    google-genai \
    weasyprint \
    whitenoise \
    opencv-python-headless \
    numpy

# Copy project
COPY . /app/

# Create required directories
RUN mkdir -p /media/uploads

# Collect static files at build time
RUN python manage.py collectstatic --noinput

# Default port (Cloud Run uses PORT env var)
ENV PORT=8080
EXPOSE 8080

# Default command (create session dir at runtime, then start server)
CMD mkdir -p /tmp/django_sessions && daphne -b 0.0.0.0 -p $PORT config.asgi:application
