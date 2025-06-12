FROM python:3.11-slim

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 5001
EXPOSE 5001

# Run the Authentication service using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:create_app()"]
