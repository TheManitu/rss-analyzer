
# RSS Analyzer mit RAG

Dieses Open‑Source‑Projekt sammelt, bereinigt und analysiert RSS‑Feed‑Artikel lokal und stellt eine interaktive Web‑UI zur Verfügung. Es kombiniert klassische ETL‑Techniken mit einer Retrieval‑Augmented Generation (RAG)‑Pipeline.

## Kernfunktionen

-   **Robuste RSS‑Ingestion**
    
    -   Paralleles Fetching (aiohttp), Duplikat‑Check, HTML‑ und Cookie‑Bereinigung
        
    -   Volltext‑Scraping mit BeautifulSoup (nur ausgewählte Domains), Skip-Liste für problematische URLs
        
    -   Automatisches Entfernen kurzer Artikel (< 300 Wörter)
        
    -   Extractive Summaries (TextRank via Sumy) und regelbasierte Übersetzung (Apertium)
        
-   **Saubere Datenhaltung**
    
    -   DuckDB‑Storage mit automatischer Schema‑Migration (`content`, `summary`, `translation`)
        
    -   `clean_text()` entfernt HTML‑Tags und Entities
        
    -   Nachreinigung aller ausgelieferten Texte vor UI‑Darstellung
        
-   **RAG‑Pipeline**
    
    -   Semantische Suche: Sentence‑Transformer + FAISS
        
    -   Keyword‑Suche: BM25
        
    -   Hybrid‑Score‑Fusion und Auswahl der Top‑K Kontexte
        
-   **Prompt‑Templates**
    
    -   Maximal 5 Quellen pro Antwort
        
    -   Wichtigste Artikel: Vollständige Zusammenfassung (≤ 500 Wörter)
        
    -   Nebensätze: Kurzfassung (≤ 200 Zeichen)
        
    -   Ausgabe ausschließlich auf Deutsch
        
    -   Prompt‑Vorlagen im Verzeichnis `prompt_templates/`
        
-   **REST‑API (Flask)**
    
    -   Endpoint `/search`: liefert Top‑5 Kandidaten (`title`, `link`) als JSON für Frontend
        
    -   Antwortgenerierung mit LLM (Llama2 oder konfiguriertes Modell)
        
-   **Web‑UI**
    
    -   Indexseite mit Suchfeld, Antwort und klickbarer Quellenliste
        
    -   Unter der Antwort eine Leerzeile und `.sources-box` für Quellenlinks
        
    -   Template‑Filter `|striptags`, `first_words`, `truncatewords` in `app.py`
        
-   **Styling**
    
    -   `static/style.css` enthält `.sources-box`‑Styles sowie allgemeines Layout
        
    -   Moderne Typografie über Google Fonts
        

## Projektstruktur

```
rss-analyzer/
├── docker/                     # Docker‑Setup & Integrationsskripte
│   ├── docker-compose.yml      # Zookeeper, Kafka, Spark
│   └── integration/            # Kafka/Spark Test‑Tools
├── prompt_templates/           # Vorgaben für Sprachmodelle
│   └── *.tpl                   # Prompt‑Definitionen (max. 5 Quellen, Deutsch)
├── rss_analyzer/                # Haupt‑Package
│   ├── config.py               # Umgebungsparameter & Schwellwerte
│   ├── ingestion/              # RSS‑Ingest & Cleanup (async, clean_text)
│   │   └── rss_ingest.py
│   ├── storage/                # DuckDB‑Abstraktion + Migration + Cleanup
│   │   └── duckdb_storage.py
│   ├── retrieval/              # Hybride Suche (FAISS + BM25)
│   │   └── hybrid_retrieval.py
│   ├── ranking/                # Cross‑Encoder Reranking
│   │   └── cross_encoder_ranker.py
│   ├── generation/             # LLM‑Prompting & Antwortgenerierung
│   │   └── llm_generator.py
│   ├── evaluation/             # Qualitätsprüfung der generierten Antwort
│   │   └── quality_evaluator.py
│   ├── api/                    # REST‑API (Flask)
│   │   └── app.py
│   └── topic_tracker.py        # Themen‑Statistiken
├── templates/                  # Jinja2 Templates
│   └── index.html              # Suchoberfläche mit Quellenbox
├── static/                     # Frontend‑Assets
│   └── style.css               # Styles (u. a. `.sources-box`)
├── tests/                      # Unit‑Tests für alle Module
│   ├── test_ingest.py
│   ├── test_storage.py
│   └── test_rag.py
├── requirements.txt            # Python‑Dependencies
└── README.md                   # Projektbeschreibung
```

## Installation & Start

1.  **Klone das Repo**
    
    ```
    git clone https://github.com/<user>/rss-analyzer.git
    cd rss-analyzer
    ```
    
2.  **DB zurücksetzen** (entfernt alte, ungefilterte Artikel)
    
    ```
    rm -f data/rssfeed.duckdb
    ```
    
3.  **Dependencies installieren**
    
    ```
    pip install -r requirements.txt
    ```
    
4.  **Docker‑Services starten**
    
    ```
    cd docker
    docker-compose up -d --build
    ```
    
5.  **Web‑UI direkt lokal starten** (ohne Kafka/Spark)
    
    ```
    python -m rss_analyzer.api.app
    ```
    
    und öffne http://localhost:5000
    

## Tests

```
pytest tests/
```

## Weiterentwicklung

-   **Weitere Sprachpaare**: Apertium‑Plugins oder Offline‑Module einbinden
    
-   **Abstraktive Summaries**: LLM‑basierte Paraphrasierung
    
-   **UI‑Erweiterungen**: Filter, Sortierung, Dark Mode
    
-   **Performance**: Vorberechnete Embeddings, HNSW‑Index
    

----------

Mit dieser modularen Struktur und den neuen Clean‑&‑Summarize‑Funktionen bietet der RSS Analyzer zuverlässige, saubere Daten und eine responsive, deutschsprachige Recherche‑Oberfläche.
