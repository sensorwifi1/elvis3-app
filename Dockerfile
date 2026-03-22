FROM python:3.11-slim

WORKDIR /app

# Kopiujemy najpierw listę bibliotek
COPY requirements.txt .

# Instalujemy biblioteki PLUS serwery produkcyjne (gunicorn i uvicorn)
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn

# Kopiujemy całą resztę aplikacji (to trwa najkrócej)
COPY . .

# Komenda startowa uruchamiająca aplikację na porcie 8080
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "main:app"]