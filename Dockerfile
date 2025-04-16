# Dockerfile
FROM python:3.9-slim

# Verhindert das Erstellen von Bytecode und sorgt für unbuffered Output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installiere notwendige Systempakete inkl. cron und supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    wget \
    cron \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Setze das Arbeitsverzeichnis
WORKDIR /app

# Kopiere requirements.txt und installiere Python-Abhängigkeiten (Caching maximieren)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Kopiere den gesamten Projektinhalt
COPY . /app/

# Setze PYTHONPATH (optional, falls erforderlich)
ENV PYTHONPATH="/app"

# Mache das Entry-Point-Script ausführbar
RUN chmod +x /app/entrypoint.sh

# Exponiere den Flask-Port
EXPOSE 5000

# Starte das Entry-Point-Script
ENTRYPOINT ["/app/entrypoint.sh"]
