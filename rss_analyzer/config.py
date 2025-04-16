# rss_analyzer/config.py

# Pfad zur DuckDB-Datenbankdatei (in einem persistierenden Ordner)
DB_PATH = "data/rssfeed.duckdb"

# RSS-Feed-URLs
RSS_FEEDS = [
    "https://www.heise.de/rss/heise.rdf",
    "https://www.wired.com/feed/category/tech/latest/rss",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.technologyreview.com/feed/",
    "https://aibusiness.com/rss",
    "https://openai.com/research/rss",
    "https://towardsdatascience.com/feed",
    "https://ai.googleblog.com/feeds/posts/default",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.engadget.com/rss.xml",
    "https://deepmind.com/blog/feed/basic/",
    "https://huggingface.co/blog/feed.xml"
]

# Mindestanzahl Wörter, die ein Artikel haben muss
MIN_ARTICLE_WORDS = 100

# Liste typischer Consent-Phrasen
COOKIE_CONSENT_PHRASES = [
    "zustimmung", "cookie", "tracking", "privacy center",
    "datenschutzerklärung", "nutzung aller cookies", "widerruf"
]

# Mapping für Themenfelder inkl. Schlüsselwörter und Wichtigkeit
TOPIC_MAPPING = {
    "Künstliche Intelligenz und maschinelles Lernen": {
         "keywords": ["ki", "künstliche intelligenz", "maschinelles lernen", "deep learning", "neuronale netze"],
         "importance": 10
    },
    "Datenwissenschaft und Big Data": {
         "keywords": ["datenwissenschaft", "big data", "datenanalyse", "statistische modellierung", "datengetrieben"],
         "importance": 8
    },
    "IT-Sicherheit und Cybersecurity": {
         "keywords": ["it-sicherheit", "cybersecurity", "datenschutz", "hackerangriffe", "sicherheitsbedrohungen"],
         "importance": 9
    },
    "Technologische Innovationen und Zukunftstechnologien": {
         "keywords": ["technologische innovationen", "zukunftstechnologien", "disruptive innovationen", "neue technologie"],
         "importance": 8
    },
    "Software- und Hardware-Entwicklungen": {
         "keywords": ["softwareentwicklung", "hardware", "betriebssystem", "softwarelösungen"],
         "importance": 7
    },
    "Wissenschaftliche Forschung und technologische Durchbrüche": {
         "keywords": ["forschung", "wissenschaftliche studie", "technologische durchbrüche", "forschungsergebnisse"],
         "importance": 9
    },
    "Digitalisierung und IT-Infrastruktur": {
         "keywords": ["digitalisierung", "it-infrastruktur", "digitale transformation", "digitales geschäftsmodell"],
         "importance": 7
    },
    "Cloud Computing und IT-Dienste": {
         "keywords": ["cloud computing", "it-dienste", "virtualisierung", "cloud-services"],
         "importance": 7
    },
    "Internet of Things (IoT) und vernetzte Systeme": {
         "keywords": ["internet of things", "iot", "vernetzte systeme", "smart home"],
         "importance": 6
    },
    "Robotik und autonome Systeme": {
         "keywords": ["robotik", "autonome systeme", "autonome fahrzeuge"],
         "importance": 6
    },
    "Technologiepolitik und ethische Fragestellungen": {
         "keywords": ["technologiepolitik", "ethische fragestellungen", "regulierung", "datenschutz", "gesellschaftliche verantwortung"],
         "importance": 5
    },
    "Forschung und Entwicklungen bei führenden Technologieunternehmen": {
         "keywords": ["google", "openai", "mit technology review", "technologieunternehmen"],
         "importance": 9
    },
    "Technologische Geschäftsmodelle und Start-ups": {
         "keywords": ["start-up", "geschäftsmodell", "unternehmensmodell", "tech-start-up"],
         "importance": 5
    },
    "Medien, Kommunikation und digitale Kultur": {
         "keywords": ["medien", "kommunikation", "digitale kultur", "social media"],
         "importance": 4
    },
    "Markttrends und wirtschaftliche Aspekte der Tech-Branche": {
         "keywords": ["markttrends", "wirtschaft", "investitionen", "tech branche", "ökonomisch"],
         "importance": 5
    }
}

# Konfiguration für die RAG-Pipeline
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Zentrale Schwellenwerte zur Extraktion relevanter Informationen
EXTRACTION_THRESHOLD = 0.6      # Standardwert in extract_relevant_passages (z. B. 0.6)
HIGH_SIMILARITY_THRESHOLD = 0.85   # z. B. in der Passage-Auswahl: Score >= 0.85
LOW_SIMILARITY_THRESHOLD = 0.5    # z. B. als Fallback, wenn kein Absatz den hohen Score erreicht
