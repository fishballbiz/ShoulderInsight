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
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (pinned versions)
RUN pip install \
    Django==6.0.2 \
    daphne==4.2.1 \
    google-genai==1.64.0 \
    weasyprint==68.1 \
    whitenoise==6.11.0 \
    opencv-python-headless==4.13.0.92 \
    numpy==2.4.2

# Copy project
COPY . /app/

# Create required directories and non-root user
RUN mkdir -p /media/uploads /tmp/django_sessions \
    && useradd -r -s /bin/false appuser \
    && chown -R appuser:appuser /app /media /tmp/staticfiles /tmp/django_sessions

# Collect static files at build time
RUN python manage.py collectstatic --noinput

# Switch to non-root user
USER appuser

# Default port (Cloud Run uses PORT env var)
ENV PORT=8080
EXPOSE 8080

CMD daphne -b 0.0.0.0 -p $PORT config.asgi:application
