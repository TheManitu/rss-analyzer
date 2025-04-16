# RSS Analyzer mit RAG

Dies ist ein Open-Source-Projekt zur Analyse von RSS-Feeds mit einer Retrieval-Augmented Generation (RAG) Pipeline. Das Ziel des Projekts ist es, News- und Tech-Feeds automatisch zu sammeln, zu analysieren und auf Basis der gesammelten Informationen präzise Antworten auf Benutzerfragen zu generieren. Das System ist modular aufgebaut, läuft lokal und verarbeitet ausschließlich RSS-Feed-Daten.

## Überblick

Der RSS Analyzer kombiniert klassische ETL-Techniken mit modernen NLP-Methoden. Zunächst werden RSS-Feeds aus verschiedenen Quellen eingelesen, bereinigt und in einer lokalen DuckDB-Datenbank gespeichert. Anschließend ermöglicht eine RAG-Pipeline, die auf Sentence-Transformer-Embeddings und FAISS basiert, die semantische Suche und Generierung von Antworten mithilfe eines KI-Modells. Die Webanwendung (basierend auf Flask) stellt eine benutzerfreundliche Oberfläche zur Verfügung, über die Fragen gestellt und Antworten zusammen mit den entsprechenden Quellen angezeigt werden.

## Hauptmerkmale

- **Automatisches Einlesen von RSS-Feeds:**  
  Das System sammelt regelmäßig Artikel von verschiedenen RSS-Feeds und speichert diese in einer lokalen DuckDB-Datenbank.

- **Datenbereinigung und -aufbereitung:**  
  Artikel werden bereinigt, zusammengefasst (bei langen Inhalten) und mit Metadaten wie Veröffentlichungsdatum, Themen und Wichtigkeit versehen.

- **Retrieval-Augmented Generation (RAG):**  
  Mittels semantischer Suche über FAISS und Sentence-Transformern werden relevante Artikel zu einer Benutzerfrage gefunden. Anschließend generiert ein KI-Modell eine präzise Antwort basierend auf diesen Quellen.

- **Modulare Architektur:**  
  Der Code ist klar in separate Module unterteilt, was die Wartung, Erweiterung und das Verständnis der einzelnen Komponenten erleichtert.

- **Lokaler Betrieb:**  
  Alle Funktionen laufen lokal, sodass keine externen Dienste (z. B. Cloud oder Docker) erforderlich sind – ideal für erste Data-Engineering-Projekte.

## Architektur und Technologien

- **Backend:**  
  - *Python 3.x* als Programmiersprache  
  - *Flask* als Web-Framework  
  - *DuckDB* als leichtgewichtige, spaltenorientierte Datenbank für die Speicherung von Artikeln

- **Data Engineering & NLP:**  
  - RSS-Feeds werden mit *feedparser* und *BeautifulSoup* eingelesen  
  - Textaufbereitung, Zusammenfassung und Spracherkennung mit *sumy*, *langdetect* und weiteren Bibliotheken  
  - Semantische Suche mit *Sentence-Transformers* und *FAISS*

- **Frontend:**  
  - HTML, CSS (unter Verwendung von Google Fonts für ein modernes Design) und JavaScript  
  - Dynamische Interaktion (z. B. Lade-Indikatoren, Suchabfragen) über asynchrone Fetch-Requests

## Ordnerstruktur

rss-analyzer/ ├── rss_analyzer/ # Haupt-Package │ ├── init.py # Initialisierung des Packages │ ├── config.py # Zentrale Konfiguration (z. B. DB-Pfad, RSS-URLs, Themen-Mapping) │ ├── database.py # Datenbankoperationen (Tabellenerstellung, Insert, Abfragen) │ ├── scraper.py # RSS-Feed-Einlesung, Bereinigung und Speicherung │ ├── rag.py # RAG-Pipeline (Embeddings, FAISS-Suche, KI-Antwort-Generierung) │ └── app.py # Flask-Webanwendung ├── templates/ # HTML-Templates │ └── index.html # Benutzeroberfläche (Suchseite, Anzeige der Artikel) ├── static/ # Statische Dateien (CSS, Favicon, etc.) │ └── style.css # Styling der Anwendung ├── tests/ # Unit-Tests für einzelne Komponenten │ ├── test_database.py
│ ├── test_scraper.py
│ └── test_rag.py ├── requirements.txt # Python-Abhängigkeiten └── README.md # Diese Projektbeschreibung


## Installation

1. **Repository klonen:**  
   Klone das Repository auf deinen lokalen Rechner:
   bash
  `git clone https://github.com/dein-benutzername/rss-analyzer.git
   cd rss-analyzer`

    Virtuelles Environment erstellen:
    Erstelle und aktiviere ein virtuelles Environment:

python -m venv venv
# Unter Windows:
venv\Scripts\activate
# Unter Unix/macOS:
source venv/bin/activate

# Abhängigkeiten installieren:
Installiere alle benötigten Pakete:

`pip install -r requirements.txt`

## Nutzung
# RSS-Feeds einlesen

Führe den Scraper aus, um die RSS-Feeds zu verarbeiten und Artikel in die Datenbank zu speichern:

`python -m rss_analyzer.scraper`

## Webanwendung starten

# Starte die Flask-Webanwendung:

`python -m rss_analyzer.app`

Öffne anschließend http://127.0.0.1:5000 in deinem Browser. Hier kannst du Fragen zur Informationssuche stellen und erhältst basierend auf den gesammelten Artikeln generierte Antworten sowie Quellverweise.

## Tests

Um die einzelnen Komponenten zu testen, führe Unit-Tests mit pytest im Ordner tests/ aus:

pytest tests/

Dadurch wird sichergestellt, dass alle Kernfunktionen (Datenbank, Scraper, RAG-Pipeline) wie erwartet funktionieren.
Erweiterungsmöglichkeiten

    Erweiterte Datenanalyse:
    Integration von Named Entity Recognition (NER), Sentiment-Analyse oder automatischer Themenklassifizierung.
    Optimierung der RAG-Pipeline:
    Verwendung von approximativen Indizes (z. B. HNSW) und Vorberechnung der Artikel-Embeddings für schnellere Suchanfragen.
    UI/UX-Verbesserungen:
    Verbesserung des Designs und der Benutzerfreundlichkeit, etwa durch zusätzliche Filteroptionen und responsive Design-Anpassungen.
    Inkrementelles Update der Datenbank:
    Anstatt die Tabelle bei jedem Run komplett neu zu erstellen, könnten nur neue Artikel eingefügt und alte entfernt werden.

## Fazit

Der RSS Analyzer mit RAG demonstriert den gesamten Workflow eines Data-Engineering-Projekts – von der Datenerfassung über die Verarbeitung und Analyse bis hin zur Bereitstellung einer interaktiven Benutzeroberfläche. Das Projekt zeigt, wie moderne Open-Source-Tools kombiniert werden können, um aus unstrukturierten RSS-Daten wertvolle, strukturierte Informationen und Antworten zu generieren.
