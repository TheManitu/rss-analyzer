# Dockerfile

FROM python:3.10-slim

# 1) System-Pakete
RUN apt-get update && apt-get install -y \
    build-essential git curl libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

# 2) CUDA-fähiges PyTorch & Faiss‐GPU
RUN pip install --no-cache-dir \
        torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 && \
    pip uninstall -y faiss-cpu && \
    pip install --no-cache-dir faiss-gpu

# 3) Restliche Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Spacy: Deutsch-Modell installieren
RUN python3 -m spacy download de_core_news_sm

# 4) NLTK-Modelle (falls genutzt)
RUN python3 - <<EOF
import nltk
nltk.download('punkt')
nltk.download('stopwords')
EOF

# 5) Quell-Code kopieren
COPY . .

# 6) Port freigeben
EXPOSE 5000

# 7) Startkommando
CMD ["python", "-u", "-m", "api.api"]
