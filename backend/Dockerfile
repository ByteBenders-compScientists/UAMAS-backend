FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# CMD ["gunicorn", "--timeout=300", "--graceful-timeout=30", "--workers=2", "--threads=2", "--keep-alive=5", "--bind", "0.0.0.0:5000", "app:app"]
CMD ["gunicorn", "-k", "gthread", "--timeout=300", "--workers=3", "--threads=4", "--bind", "0.0.0.0:5000", "app:app"]
