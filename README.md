# RSS Analyzer

RSS Analyzer ist eine lokale Research-App fuer aktuelle Tech- und AI-Quellen. Das System sammelt RSS-Artikel, bereinigt Scraping-Artefakte, bewertet Quellenqualitaet und beantwortet Nutzerfragen mit einer Retrieval-Augmented-Generation-Pipeline (RAG).

Der aktuelle Stand ist auf Demo-Qualitaet ausgerichtet: Die UI zeigt Artikel, Antworten und Quellen kompakt, unterscheidet offizielle Quellen von Drittquellen und vermeidet Antworten auf Basis lose verwandter Treffer.

## Aktueller Stand

- Moderne Reader-Oberflaeche mit Artikelstrom, Themenfilter, Zeitraumfilter und Antwort-/Quellenbereich.
- Light Mode und Dark Mode inklusive passender Scrollbars und lesbarer Ergebnis-Panels.
- RSS-Ingestion fuer Tech-, AI- und OpenAI-nahe Quellen, ergaenzt durch kuratierte Trusted Sources.
- Quellenbasierte Q&A ueber `/search` mit Antwort, Quellenliste, Snippets, Domain und Quellenbewertung.
- Quellenklassifizierung in `official`, `third_party`, `speculative` und `community`.
- Spezifische Fragen wie GPT-5.6, Iris oder andere Codenames muessen passende Quellen enthalten; ansonsten meldet das System klar, dass keine belastbare Quelle gefunden wurde.
- Scrape-Text wird bereinigt: HTML, Cookie-/Werbe-Boilerplate, kaputte Encoding-Zeichen und Markdown-Artefakte wie `##`, `**...**` oder `[Link](url)` werden entfernt.
- Ausgeklappte Artikel werden linksbuendig mit lesbaren Absatzumbruechen dargestellt.
- Fallback-Antworten bleiben quellenbasiert, falls kein lokales LLM erreichbar ist.

## Warum das Projekt interessant ist

Viele RSS-Reader koennen Artikel sammeln, aber sie beantworten keine Research-Fragen mit Quellenkontrolle. RSS Analyzer kombiniert deshalb vier Schritte:

1. Sammeln: Artikel aus RSS-Feeds, offiziellen Hilfeseiten und kuratierten Discovery-Quellen.
2. Bereinigen: Entfernung von Werbung, Navigation, kaputten Zeichen, Markdown-Resten und Duplicate Content.
3. Bewerten: Einstufung der Quellen nach Herkunft und Spekulationssignalen.
4. Antworten: RAG-Antworten mit Quellen, Snippets und Vertrauenshinweisen.

Das Ziel ist nicht, Geruechte als Fakten zu behandeln. Gerade bei unveroeffentlichten Modellen oder Codenames wird bewusst getrennt zwischen bestaetigten Informationen, Drittquellen und unbestaetigten Hinweisen.

## Beispielverhalten

### Frage zu einem belegten Thema

Frage:

```text
Was ist neu bei OpenAI?
```

Erwartetes Verhalten:

- Es werden relevante Quellen aus dem Artikelbestand gesucht.
- Offizielle OpenAI-Quellen werden hoeher gewichtet.
- Die Antwort nennt belegte Informationen und listet darunter Quellen mit Snippet und Bewertung.

### Frage zu GPT Iris

Frage:

```text
Was ist Chat GPT Iris?
```

Erwartetes Verhalten:

- `chat`, `gpt` und `openai` gelten als generische Kontextbegriffe.
- `iris` gilt als spezifischer Pflichtbegriff.
- Wenn keine Quelle `iris` belastbar belegt, antwortet das System nicht mit GPT-5.5-Ersatzquellen.

Beispielausgabe:

```text
Es wurden keine ausreichend relevanten Quellen gefunden, die die spezifischen Suchbegriffe (iris) belastbar belegen. Ich beantworte die Frage deshalb nicht mit nur lose verwandten GPT- oder OpenAI-Quellen.
```

## Architektur

```text
rss-analyzer/
├── api/                    Flask-App, RAG-Endpoints und UI-Routen
├── ingestion/              RSS- und Trusted-Source-Ingestion
├── pipeline/               Cleaning, Topics, Relevance, Segmentation, Summaries
├── retrieval/              PassageRetriever und ContentFilter
├── ranking/                Cross-Encoder-Ranking
├── generation/             Prompting, LLM-Anbindung und Fallback-Antworten
├── evaluation/             Antwortqualitaets-Evaluierung
├── storage/                DuckDB-Storage
├── templates/              Flask/Jinja-Templates
├── static/                 Frontend-JavaScript, CSS und Logo
├── tests/                  Regressionstests fuer Ingestion, RAG, UI und Textqualitaet
├── config.py               Feeds, Quellen, Retrieval- und Modellparameter
├── docker-compose.yml      Kafka, Ollama, API und Analytics-Services
└── requirements.txt
```

## Daten- und Quellenqualitaet

Die wichtigsten Qualitaetsregeln liegen in:

- `pipeline/text_quality.py`: HTML-Stripping, Boilerplate-Filter, Markdown-Bereinigung, Encoding-Reparatur.
- `pipeline/source_quality.py`: offizielle Quellen, Community-Quellen, Spekulationssignale und Vertrauenslabel.
- `retrieval/passage_retriever.py`: Retrieval, Topic-/Keyword-Filter und Pflichtbegriffe fuer spezifische Fragen.
- `api/rag.py`: Kontextaufbau, Quellenliste, Quellenbegruendung und No-Answer-Verhalten.

Spezifische Codenames oder Versionsbegriffe duerfen nicht durch allgemeine GPT-/OpenAI-Treffer ersetzt werden. Diese Regel verhindert Demo-Antworten, die zwar thematisch nah wirken, aber die eigentliche Frage nicht belegen.

## Schnellstart lokal

Voraussetzungen:

- Python 3.11 empfohlen
- Optional: Ollama fuer lokale LLM-Antworten
- Optional: Docker fuer den vollstaendigen Stack

Installation:

```powershell
git clone https://github.com/TheManitu/rss-analyzer.git
cd rss-analyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Schneller UI-Start ohne komplette Pipeline beim Start:

```powershell
$env:PORT='5001'
$env:SKIP_INGEST_ON_STARTUP='true'
$env:SKIP_KEYWORDS_ON_STARTUP='true'
$env:SKIP_TOPICS_ON_STARTUP='true'
$env:SKIP_RELEVANCE_ON_STARTUP='true'
$env:SKIP_SEGMENTATION_ON_STARTUP='true'
$env:SKIP_SUMMARIZATION_ON_STARTUP='true'
$env:SKIP_ANALYZER_ON_STARTUP='true'
$env:SKIP_DASHBOARD_ON_STARTUP='true'
python -m api.api
```

Dann im Browser:

```text
http://127.0.0.1:5001/
```

Standardstart mit Default-Port:

```powershell
python -m api.api
```

Dann:

```text
http://127.0.0.1:5000/
```

## Docker-Start

```powershell
docker compose up --build
```

Der Docker-Stack startet unter anderem:

- Flask-API
- Kafka und Zookeeper
- Ollama
- Spark-Analytics-Services

Wichtige Environment-Variablen:

```text
DB_PATH
PORT
OLLAMA_HOST
LLM_MODEL_INITIAL
LLM_MODEL_REFINE
RETRIEVAL_CANDIDATES
FINAL_CONTEXTS
ENABLE_DISCOVERY_FEEDS
SKIP_INGEST_ON_STARTUP
SKIP_KEYWORDS_ON_STARTUP
SKIP_TOPICS_ON_STARTUP
SKIP_RELEVANCE_ON_STARTUP
SKIP_SEGMENTATION_ON_STARTUP
SKIP_SUMMARIZATION_ON_STARTUP
SKIP_ANALYZER_ON_STARTUP
SKIP_DASHBOARD_ON_STARTUP
```

## Tests

Komplette Testsuite:

```powershell
python -m pytest tests/ -q
```

Der aktuelle Stand deckt unter anderem ab:

- Text- und Encoding-Qualitaet
- Markdown-Bereinigung aus Scrape-Texten
- Quellenklassifizierung
- GPT-5.6- und Iris-No-Answer-Verhalten
- Passage-Retrieval
- RAG-Antworten
- Frontend-Rendering und Layout-Regeln
- Trusted-Source-Ingestion

## Wichtige Endpoints

```text
GET  /                 Web-UI
POST /search           JSON-Q&A fuer das Frontend
POST /api/refresh      Pipeline-Aktualisierung aus der UI
GET  /rag              RAG-Blueprint-Index
POST /rag/search       RAG-Blueprint-Suche
```

Beispiel fuer `/search`:

```json
{
  "question": "Was ist neu bei OpenAI?"
}
```

Antwortschema:

```json
{
  "answer": "...",
  "sources": [
    {
      "title": "...",
      "link": "...",
      "snippet": "...",
      "domain": "...",
      "discussion": "...",
      "source_type": "official",
      "credibility_score": 1.0
    }
  ]
}
```

## Demo-Hinweise

Fuer eine gute Demo eignen sich Fragen, die entweder klar belegbar sind oder bewusst die No-Answer-Logik zeigen:

- `Was ist neu bei OpenAI?`
- `Welche aktuellen Hinweise gibt es zu GPT-5.6 und wie belastbar sind die Quellen?`
- `Was ist Chat GPT Iris?`

Die Demo sollte zeigen:

- Antworten werden mit Quellen erklaert.
- Quellen werden bewertet, nicht nur verlinkt.
- Unbestaetigte Hinweise werden nicht als Produktfakten dargestellt.
- Wenn keine Quelle passt, sagt das System das klar.

## Rollback und Betrieb

Die App nutzt DuckDB lokal. Fuer lokale Tests kann eine eigene DB gesetzt werden:

```powershell
$env:DB_PATH="$env:TEMP\rss_analyzer_live_test.duckdb"
```

Ein fehlerhafter Code-Stand kann per Git revert zurueckgenommen werden:

```powershell
git revert <commit>
```

Fuer Demo- oder Portfolio-Screenshots sollte die App mit einer vorbereiteten DuckDB und gesetzten Startup-Skip-Flags gestartet werden, damit die UI sofort reagiert.
