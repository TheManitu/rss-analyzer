import os

# Basis-Verzeichnisse und DB-Pfad
BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "data", "rssfeed.duckdb")
DB_PATH    = os.getenv("DB_PATH", DEFAULT_DB)

# RSS-Feeds (inkl. erweiterter KI/AI-Quellen)
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
    "https://huggingface.co/blog/feed.xml",
    "https://openai.com/blog/rss",
    "https://blog.google/technology/ai/rss/",
    "https://azure.microsoft.com/en-us/blog/topics/artificial-intelligence/feed/",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://medium.com/feed/topic/artificial-intelligence"
]

# Clean-Up-Schwellen
MIN_ARTICLE_WORDS = int(os.getenv("MIN_ARTICLE_WORDS", 200))
MAX_ARTICLE_WORDS = int(os.getenv("MAX_ARTICLE_WORDS", 500))
MAX_FETCH_WORKERS = int(os.getenv("MAX_FETCH_WORKERS", 10))

# Topic-Mapping: Stichwörter → Topic-Kategorie
TOPIC_MAPPING = {
    "Allgemein": {"keywords": []},

    "OpenAI und GPT-Modelle": {
        "keywords": [
            "openai", "gpt-3", "gpt-4", "chatgpt", "dall-e", "codex",
            "openai api", "open ai", "borts", "text-davinci"
        ]
    },
    "Anthropic & Claude": {
        "keywords": ["anthropic", "claude", "claude ai"]
    },
    "Google AI & Bard": {
        "keywords": ["google ai", "bard", "gemini", "lambda"]
    },
    "Meta AI & LLaMA": {
        "keywords": ["meta ai", "llama", "llama2", "fairseq"]
    },
    "Microsoft AI & Azure": {
        "keywords": ["microsoft", "azure ai", "copilot", "bing chat"]
    },
    "Amazon AWS AI": {
        "keywords": ["amazon", "aws ai", "sagemaker", "lex", "polly"]
    },

    "Apple Geräte & Dienste": {
        "keywords": ["apple", "iphone", "ipad", "macos", "app store", "siri"]
    },
    "Google Produkte": {
        "keywords": ["android", "chrome", "google home", "gmail", "youtube"]
    },
    "Meta & Soziale Medien": {
        "keywords": ["facebook", "instagram", "whatsapp", "threads", "tiktok"]
    },

    "Künstliche Intelligenz & Maschinelles Lernen": {
        "keywords": [
            "ki", "künstliche intelligenz", "maschinelles lernen",
            "deep learning", "neuronale netze", "transformer", "bert"
        ]
    },
    "Cloud Computing & Infrastruktur": {
        "keywords": [
            "cloud", "saas", "iaas", "paas", "infrastruktur",
            "docker", "kubernetes", "virtualisierung"
        ]
    },
    "Software- und Hardware-Entwicklungen": {
        "keywords": [
            "software", "firmware", "chip", "prozessor", "grafikkarte",
            "ssd", "ram", "motherboard"
        ]
    },
    "IT-Sicherheit & Cybersecurity": {
        "keywords": [
            "cybersecurity", "datenschutz", "hacker", "malware",
            "ransomware", "firewall", "zero day"
        ]
    },
    "IoT & Vernetzte Systeme": {
        "keywords": ["iot", "smart home", "sensor", "5g", "edge computing"]
    },
    "Robotik & autonome Systeme": {
        "keywords": ["robotik", "drohne", "autonom", "fahrzeug", "automatisierung"]
    },
    "Wissenschaftliche Forschung & Durchbrüche": {
        "keywords": [
            "forschung", "experiment", "paper", "studie", "publikation",
            "quantentechnologie", "biotech", "science"
        ]
    },
    "Markttrends & Finanzen": {
        "keywords": [
            "aktie", "ipo", "start-up", "venture", "finanz",
            "investment", "markttrend", "economie"
        ]
    },
    "Digitalisierung & Politik": {
        "keywords": [
            "politik", "gesetz", "regulierung", "digitalisierung",
            "compliance", "ethik", "zensur", "datenschutzerklärung"
        ]
    },
    "Politik": {
        "keywords": [
            "politik", "regierung", "wahl", "bundestag",
            "trump", "donald", "biden", "usa", "präsident",
            "election", "parlament", "kanzler", "regierungskrise"
        ]
    },
    "Wirtschaft": {
        "keywords": [
            "aktien", "markt", "bank", "finanzen",
            "wirtschaft", "inflation", "rezession", "unternehmen"
        ]
    },
    "Technologie": {
        "keywords": [
            "tech", "ki", "künstliche intelligenz", "cloud",
            "software", "hardware", "chip", "microprocessor"
        ]
    },
    "Wissenschaft": {
        "keywords": ["studie", "forschung", "universität", "wissenschaft"]
    },
    "Gesundheit": {
        "keywords": ["medizin", "gesundheit", "krankenhaus", "impfung"]
    },
}

# Score-Filter-Schwellen
EXTRACTION_THRESHOLD      = float(os.getenv("EXTRACTION_THRESHOLD", 0.6))
HIGH_SIMILARITY_THRESHOLD = float(os.getenv("HIGH_SIMILARITY_THRESHOLD", 0.85))
LOW_SIMILARITY_THRESHOLD  = float(os.getenv("LOW_SIMILARITY_THRESHOLD", 0.5))

# Hybrid-Fusionsgewichte (Embedding vs. BM25 vs. Importance)
HYBRID_WEIGHT_SEMANTIC  = float(os.getenv("HYBRID_WEIGHT_SEMANTIC", 0.5))
HYBRID_WEIGHT_KEYWORD   = float(os.getenv("HYBRID_WEIGHT_KEYWORD", 0.2))
IMPORTANCE_WEIGHT       = float(os.getenv("IMPORTANCE_WEIGHT", 0.3))

# Recency-Boost für neue Artikel
RECENCY_WEIGHT = float(os.getenv("RECENCY_WEIGHT", 0.2))

# Top-Kandidaten fürs Retrieval
RETRIEVAL_CANDIDATES = int(os.getenv("RETRIEVAL_CANDIDATES", 10))

# Mindestscore für Passage-Auswahl
MIN_PASSTAGE_SCORE = float(os.getenv("MIN_PASSTAGE_SCORE", 0.1))

# LLM-Modelle für Initial- und Refine-Schritte
EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
LLM_MODEL_INITIAL   = os.getenv("LLM_MODEL_INITIAL", "llama2:7b")
LLM_MODEL_REFINE    = os.getenv("LLM_MODEL_REFINE",  "llama2:7b")

# Anzahl finaler Kontexte fürs LLM
FINAL_CONTEXTS = int(os.getenv("FINAL_CONTEXTS", 5))
MAX_CONTEXTS   = FINAL_CONTEXTS

# Kafka-Konfiguration & Sonstiges
KAFKA_BOOTSTRAP       = os.getenv("KAFKA_BOOTSTRAP", "rss-kafka-ingest:9092")
TOPIC_USER_QUESTIONS = os.getenv("TOPIC_USER_QUESTIONS", "UserQuestions")
TOPIC_ARTICLE_VIEWS  = os.getenv("TOPIC_ARTICLE_VIEWS", "ArticleViews")
TOPIC_ANSWER_QUALITY = os.getenv("TOPIC_ANSWER_QUALITY", "AnswerQuality")

# Timeout für externe Aufrufe (in Sekunden)
TIMEOUT_SEC = int(os.getenv("TIMEOUT_SEC", 60))

# Gewichtungen für recalc_importance()
VIEWS_WEIGHT   = float(os.getenv("W_VIEWS",   0.4))
REFS_WEIGHT    = float(os.getenv("W_REFS",    0.5))
FLAG_WEIGHT    = float(os.getenv("W_FLAG",    0.1))
CONTENT_WEIGHT = float(os.getenv("W_CONTENT", 0.1))  # neuer Content-Metric-Anteil
