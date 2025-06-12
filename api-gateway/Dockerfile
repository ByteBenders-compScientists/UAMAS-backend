FROM python:3.11-slim

# install system dependencies (if any)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy and install Python dependencies
COPY api-gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY api-gateway/ .

# expose port 8080
EXPOSE 8080

# run the API Gateway (using gunicorn for production)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
