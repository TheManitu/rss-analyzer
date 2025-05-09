# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -m nltk.downloader stopwords punkt averaged_perceptron_tagger


# Copy code
COPY . /app

# Optional: Erstelle das data‑Verzeichnis (wird gemountet)
RUN mkdir -p /app/data

# Standard‑Command ist in Compose definiert