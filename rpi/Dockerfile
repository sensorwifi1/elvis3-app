FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV DATA_DIR=/data
VOLUME ["/data"]

EXPOSE 8080

# gthread worker: wiele wątków na worker, jeden zawieszony recv() nie blokuje całego procesu
CMD ["gunicorn", "-w", "1", "--worker-class", "gthread", "--threads", "4", "--timeout", "60", "--keep-alive", "2", "-b", "0.0.0.0:8080", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
