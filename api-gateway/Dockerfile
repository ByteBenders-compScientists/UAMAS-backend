FROM python:3.11-slim AS base

# Set workdir
WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libffi-dev libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Use Gunicorn for better concurrency handling in production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
