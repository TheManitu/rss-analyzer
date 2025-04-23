# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . /app

# Optional: Erstelle das data‑Verzeichnis (wird gemountet)
RUN mkdir -p /app/data

# Standard‑Command ist in Compose definiert