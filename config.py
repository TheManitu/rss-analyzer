# config.py
import os

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "data", "rssfeed.duckdb")
DB_PATH    = os.getenv("DB_PATH", DEFAULT_DB)

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

# Mindestlänge für Artikel (für Cleanup)
MIN_ARTICLE_WORDS = int(os.getenv("MIN_ARTICLE_WORDS", 200))
MAX_ARTICLE_WORDS = int(os.getenv("MIN_ARTICLE_WORDS", 500))

# Anzahl paralleler Fetch‑Tasks
MAX_FETCH_WORKERS = int(os.getenv("MAX_FETCH_WORKERS", 10))

COOKIE_CONSENT_PHRASES = [
    "zustimmung", "cookie", "tracking", "privacy center",
    "datenschutzerklärung", "nutzung aller cookies", "widerruf"
]

TOPIC_MAPPING = {
    # … dein komplettes Mapping unverändert …
}

EXTRACTION_THRESHOLD      = float(os.getenv("EXTRACTION_THRESHOLD", 0.6))
HIGH_SIMILARITY_THRESHOLD = float(os.getenv("HIGH_SIMILARITY_THRESHOLD", 0.85))
LOW_SIMILARITY_THRESHOLD  = float(os.getenv("LOW_SIMILARITY_THRESHOLD", 0.5))

TOP_K_VECTORIZATION     = int(os.getenv("TOP_K_VECTORIZATION", 15))
TOP_K_BM25              = int(os.getenv("TOP_K_BM25", 15))
HYBRID_WEIGHT_SEMANTIC  = float(os.getenv("HYBRID_WEIGHT_SEMANTIC", 0.7))
HYBRID_WEIGHT_KEYWORD   = float(os.getenv("HYBRID_WEIGHT_KEYWORD", 0.3))

MIN_PASSTAGE_SCORE = float(os.getenv("MIN_PASSTAGE_SCORE", 0.6))
MAX_CONTEXTS       = int(os.getenv("MAX_CONTEXTS", 3))

EMBEDDING_MODEL      = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
LLM_MODEL_INITIAL   = os.getenv("LLM_MODEL_INITIAL", "llama2:7b")
LLM_MODEL_REFINE    = os.getenv("LLM_MODEL_REFINE", "llama2:7b")

KAFKA_BOOTSTRAP       = os.getenv("KAFKA_BOOTSTRAP", "rss-kafka-ingest:9092")
TOPIC_USER_QUESTIONS = os.getenv("TOPIC_USER_QUESTIONS", "UserQuestions")
