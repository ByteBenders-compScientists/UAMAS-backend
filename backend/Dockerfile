FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

EXPOSE 5002
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "app:app"]
