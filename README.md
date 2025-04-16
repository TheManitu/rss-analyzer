# RSS Analyzer mit RAG

Dies ist ein Open-Source-Projekt zur Analyse von RSS-Feeds mittels einer Retrieval-Augmented Generation (RAG) Pipeline. Ziel ist es, News- und Tech-Feeds automatisch zu sammeln, zu analysieren und auf Basis der gesammelten Informationen präzise Antworten auf Benutzerfragen zu generieren. Das System verwendet moderne Technologien zur semantischen Suche, Verarbeitung und Analyse von RSS-Daten – und alle Komponenten laufen in Docker-Containern.

## Überblick

Der RSS Analyzer kombiniert klassische ETL-Techniken mit fortschrittlichen NLP-Methoden. Zunächst werden RSS-Feeds aus verschiedenen Quellen eingelesen, bereinigt und in einer lokalen DuckDB-Datenbank gespeichert. Anschließend ermöglicht eine RAG-Pipeline – basierend auf Sentence-Transformer-Embeddings, FAISS und zusätzlichen themenspezifischen Filtern – die semantische Suche und Generierung von Antworten mithilfe eines KI-Modells.

Neu in dieser Version ist der Einsatz von Kafka und Spark:
- **Kafka** dient als zentraler Nachrichtenbus: Jede vom Benutzer gestellte Frage sowie Ereignisse aus der Artikelanzeige (z. B. gelesene Artikel) werden als Kafka‑Nachrichten publiziert. Dadurch kannst Du das Nutzerverhalten in Echtzeit analysieren.
- **Spark** wird eingesetzt, um diese Nachrichten zu aggregieren und zu analysieren – beispielsweise um häufig gestellte Fragen, Leseverhalten oder Trends zu ermitteln. Diese aggregierten Daten werden über das Analytics-Dashboard visualisiert.
- Zusätzlich wird der Scraper automatisch zu definierten Zeiten (z. B. per Cron‑Job innerhalb des Containers) ausgeführt, um die Artikel regelmäßig zu aktualisieren.

Die Webanwendung (Flask‑basiert) stellt eine benutzerfreundliche Oberfläche zur Verfügung, über die Fragen eingegeben, Antworten generiert und Dashboards zur Analyse aufgerufen werden können.

## Projektstruktur

Die empfohlene Struktur des Projekts (funktioniert ausschließlich in Docker) sieht wie folgt aus:



  

rss-analyzer/ ├── docker/
│ ├── docker-compose.yml # Docker Compose-Konfiguration (inklusive Zookeeper, Kafka, Spark, und des RAG-App-Services) │ └── integration/ # Integrationstools │ ├── create_topic_send_data.py # Kafka Producer zum Senden von Testnachrichten │ └── spark_read_from_topic_and_show.py # Spark-Job zum Lesen von Kafka-Daten ├── rss_analyzer/ # Haupt-Package der Anwendung │ ├── init.py │ ├── config.py # Zentrale Konfiguration (DB-Pfad, RSS-URLs, Themen-Mapping, Schwellenwerte etc.) │ ├── database.py # Datenbankoperationen (Tabellenerstellung, Insert, Abfragen) │ ├── scraper.py # RSS-Feed-Einlesung, Bereinigung und Speicherung │ ├── rag.py # RAG-Pipeline (Embeddings, FAISS-Suche, themenspezifische Filter, Kafka/Spark-Integration) │ └── app.py # Flask-Webanwendung (inklusive Dashboard- und Analytics-Routen) ├── templates/ # HTML-Templates │ ├── index.html # Benutzeroberfläche (Suchseite, Anzeige der Artikel) │ ├── dashboard.html # Dashboard zur Übersicht der Themen und Artikel │ └── analytics.html # Analytics-Dashboard zur Anzeige aggregierter Nutzungsdaten ├── static/ # Statische Dateien (CSS, Bilder, Favicon etc.) │ └── style.css # Styling der Anwendung ├── requirements.txt # Python-Abhängigkeiten └── README.md # Projektbeschreibung und Anleitungen

  
  
  


## Hauptmerkmale

- **Automatisches Einlesen von RSS-Feeds:**  
  Das System sammelt regelmäßig Artikel von verschiedenen RSS-Feeds und speichert diese in einer persistierenden DuckDB-Datenbank.

- **Datenaufbereitung und -bereinigung:**  
  Artikel werden bereinigt, ggf. zusammengefasst und mit wichtigen Metadaten wie Veröffentlichungsdatum, Themen und Wichtigkeit versehen.

- **Retrieval-Augmented Generation (RAG):**  
  Die RAG-Pipeline nutzt semantische Suche (mit Sentence-Transformer-Embeddings und FAISS), kombiniert mit themenspezifischen Filtern und zusätzlichen Score‑Thresholds, um die bestpassenden Artikel als Quellen zu wählen und eine präzise KI-Antwort zu generieren – maximal 5 qualitativ hochwertige Quellen werden verwendet.

- **Kafka-Integration:**  
  Jede vom Benutzer gestellte Frage wird per Kafka an den Topic „UserQuestions“ gesendet, sodass das Nutzerverhalten erfasst werden kann.

- **Spark-Analyse:**  
  Mittels Spark (z. B. über einen separaten Spark-Job) werden die Kafka-Nachrichten in Echtzeit aggregiert, um Trends, häufig gestellte Fragen und Leseverhalten zu analysieren.

- **Dashboard & Analytics:**  
  Über das Dashboard (unter `/dashboard`) und das Analytics-Dashboard (unter `/analytics`) erhältst Du Einblicke in die Themenabdeckung, Artikelveröffentlichungen und Nutzerinteraktionen.

- **Automatischer Scraper:**  
  Der Scraper wird über ein externes Shell-/Batch-Skript (z. B. `run_scraper.sh` bzw. `run_scraper.bat`) zu definierten Zeiten automatisch gestartet, sodass die Artikeldaten stets aktuell bleiben.

## Installation & Betrieb (ausschließlich via Docker)

Da alle Komponenten jetzt in Docker-Containern betrieben werden, erfolgt die Installation und Ausführung ausschließlich über Docker. Lokale Installationsanweisungen außerhalb von Docker entfallen.

### 1. Repository klonen
  

## Installation

  

### 1. **Repository klonen:**

Klone das Repository auf deinen lokalen Rechner:

`git clone  https://github.com/dein-benutzername/rss-analyzer.git`

`cd rss-analyzer`

  

### 2. Docker-Setup starten

Wechsle in den Ordner und  builde und starte die Container:

`docker-compose build`
`docker-compose up -d`
  

### 3. Scraper automatisieren

Das Projekt enthält ein Skript (z. B. run_scraper.sh für Unix/WSL oder run_scraper.bat für Windows), das zum automatischen Start des Scrapers genutzt werden kann. Diese Skripte können in Deinem Docker-Container (über Cron oder einen Task Scheduler) verwendet werden, um den Scraper zu definierten Zeiten auszuführen.
  

### 4. 4. Zugriff auf die Anwendung und Dashboards

    Hauptseite:
    Öffne im Browser http://127.0.0.1:5000 – hier kannst Du Deine Fragen eingeben und die generierten Antworten inkl. Quellen ansehen.

    Dashboard:
    Rufe http://127.0.0.1:5000/dashboard auf, um eine Übersicht der Themen, Artikelanzahl, Status und letzte Aktualisierungen zu sehen.

    Analytics:
    Rufe http://127.0.0.1:5000/analytics auf, um aggregierte Daten zu häufig gestellten Fragen und Nutzerverhalten anzuzeigen (mittels Dummy-Daten oder aggregierten Spark-Ergebnissen).

  

### 5. Integrationstools nutzen:

  

### Tests

Führe die Unit-Tests im Ordner tests/ aus, um sicherzustellen, dass alle Komponenten (Datenbank, Scraper, RAG-Pipeline) wie erwartet funktionieren:
  

`pytest tests/`

  

### Erweiterungsmöglichkeiten

    Erweiterte Datenanalyse:
    Integration von Named Entity Recognition (NER), Sentiment-Analyse oder automatischer Themenklassifizierung.

    Optimierung der RAG-Pipeline:
    Verwendung von approximativen Indizes (z. B. HNSW) und Vorberechnung der Artikel-Embeddings für schnellere Suchanfragen.

    Echtzeitanalyse:
    Erweiterung der Kafka-/Spark-Integration, um detaillierte Nutzungs- und Aggregationsdaten zu sammeln.

    Automatisierung des Scrapers:
    Einrichtung von Cron-/Task Schedulern, um den Scraper regelmäßig (z. B. täglich um 03:00 Uhr) zu starten.

  


# Tests

  

Um die einzelnen Komponenten zu testen, führe Unit-Tests mit pytest im Ordner tests/ aus:

  

`pytest tests/`



## Fazit

Der RSS Analyzer mit RAG demonstriert den gesamten Workflow eines modernen Data-Engineering-Projekts – von der Datenerfassung über die Verarbeitung und Analyse bis hin zur Bereitstellung einer interaktiven Webanwendung und eines Dashboards für Analysen. Durch die Integration von Kafka, Spark und einem automatisierten Scraper-System erhältst Du wertvolle Einsichten in das Nutzerverhalten und kannst gezielt Optimierungen vornehmen.
