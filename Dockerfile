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
    weasyprint

# Copy project
COPY . /app/

# Expose port
EXPOSE 8000

# Default command
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
