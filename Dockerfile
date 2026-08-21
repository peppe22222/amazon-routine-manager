FROM python:3.11-slim

WORKDIR /app

# Installa pacchetti di sistema essenziali
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copia i requisiti e installa
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY backend /app/backend
COPY frontend /app/frontend

# Directory per i dati persistenti
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data

EXPOSE 8000

# Avvio del server
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
