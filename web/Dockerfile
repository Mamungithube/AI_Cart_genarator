FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies required for Pillow, font rendering, and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-core \
    curl \
    netcat-traditional \
    dos2unix \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create an unprivileged user for security
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser -s /bin/bash appuser

# Copy application source code
COPY . /app/

# Convert entrypoint line endings to LF (in case checked out on Windows) and make executable
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Create required directories and set proper ownership
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app /home/appuser

# Switch to unprivileged user
USER appuser

# Expose Django internal port
EXPOSE 8000

# Execute entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
