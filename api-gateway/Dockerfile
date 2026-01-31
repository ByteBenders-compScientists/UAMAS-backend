FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libffi-dev libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["gunicorn", "--workers=3", "--threads=2", "--bind", "0.0.0.0:8080", "app:app"]
