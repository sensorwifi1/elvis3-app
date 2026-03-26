FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV DATA_DIR=/data
VOLUME ["/data"]

EXPOSE 8080

# 1 worker — synchronous gunicorn, thread-safe for background WS loop
CMD ["gunicorn", "-w", "1", "--timeout", "120", "-b", "0.0.0.0:8080", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
