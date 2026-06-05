# config.py

import os
from topic_config import TOPIC_MAPPING, TOPIC_SYNONYMS

# Basis-Verzeichnisse und DB-Pfad
BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "data", "rssfeed.duckdb")
DB_PATH    = os.getenv("DB_PATH", DEFAULT_DB)

# RSS-Feeds
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
    "https://medium.com/feed/topic/artificial-intelligence",
    # Zusaetzliche, am 03.06.2026 verifizierte aktuelle AI-/Tech-Feeds.
    "https://research.google/blog/rss/",
    "https://blogs.nvidia.com/feed/",
    "https://www.microsoft.com/en-us/research/feed/",
    "https://www.artificialintelligence-news.com/feed/",
    "https://www.the-decoder.com/feed/",
    "https://www.golem.de/rss.php?feed=RSS2.0",
    "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
    "https://www.theregister.com/software/ai_ml/headlines.atom",
    "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss",
    "https://simonwillison.net/atom/everything/",
    "https://venturebeat.com/category/ai/feed/"
]

# Offizielle Quellen, die keine RSS-Feeds sind, aber fuer aktuelle
# Produkt-/Modellfragen als hochwertige Kontextquellen dienen.
TRUSTED_SOURCE_URLS = [
    "https://help.openai.com/en/articles/6825453-chatgpt-release-notes",
    "https://help.openai.com/en/articles/9624314-model-release-notes",
    "https://help.openai.com/en/articles/11909943-gpt-5-5-in-chatgpt",
]

# Fragegetriebene Discovery-Feeds fuer aktuelle OpenAI-/Modellthemen.
# Bing News RSS funktioniert ohne API-Key und liefert die Original-URL im
# Redirect-Parameter; die Ingestion dekodiert diese URL vor dem Speichern.
ENABLE_DISCOVERY_FEEDS = os.getenv("ENABLE_DISCOVERY_FEEDS", "true").lower() in ("1", "true", "yes")
DISCOVERY_RSS_FEEDS = [
    "https://www.bing.com/news/search?q=%22GPT-5.6%22%20%22OpenAI%22&format=rss",
    "https://www.bing.com/news/search?q=%22ChatGPT%205.6%22%20%22OpenAI%22&format=rss",
    "https://www.bing.com/news/search?q=%22GPT-5.6%22%20%22release%20date%22&format=rss",
] if ENABLE_DISCOVERY_FEEDS else []

# Kuratierte Zusatzquellen fuer die aktuelle GPT-5.6-Frage. Diese Quellen
# werden nicht als offiziell behandelt; source_quality markiert Leaks,
# Prediction-Markets und Geruechte als unbestaetigt.
DISCOVERY_SOURCE_URLS = [
    "https://tokenmix.ai/blog/gpt-5-6-release-date-leaks-2026",
    "https://chatforest.com/reviews/openai-gpt-5-6-canary-leak-release-date-prediction-markets-2026/",
    "https://dev.to/tokenmixai/gpt-56-is-real-a-codex-log-says-so-everything-else-is-made-up-1ep1",
    "https://wavespeed.ai/blog/posts/gpt-5-6-canary-leak-what-we-know/",
    "https://www.predictionmarketnetwork.com/article/openai-releases-gpt-55-amid-market-speculation-over-next-ver-210007-20260527",
]

# Clean-Up-Schwellen
MIN_ARTICLE_WORDS      = int(os.getenv("MIN_ARTICLE_WORDS",      150))
MAX_PUNCT_RATIO        = float(os.getenv("MAX_PUNCT_RATIO",       0.30))
MAX_FETCH_WORKERS      = int(os.getenv("MAX_FETCH_WORKERS",       10))
MAX_FEED_ENTRIES_PER_FEED = int(os.getenv("MAX_FEED_ENTRIES_PER_FEED", 12))

# Sprach- und Blacklist-Filter
ALLOWED_LANGUAGES      = os.getenv("ALLOWED_LANGUAGES", "de,en").split(",")
BLACKLIST_PATTERNS     = [
    r"Jetzt abonnieren",
    r"(?:Dies ist ein Teaser)",
    r"Weiterlesen",
    r"Sign up",
    r"Enthält Blacklist-Muster"
]

# Topic-Blacklist
BLOCKED_TOPICS         = os.getenv("BLOCKED_TOPICS", "kaufempfehlung,produkttest").split(",")
TOPIC_ALLOW_PREFIX     = os.getenv("TOPIC_ALLOW_PREFIX", "gaming")

# Hybrid- & Recency-Gewichte
HYBRID_WEIGHT_SEMANTIC = float(os.getenv("HYBRID_WEIGHT_SEMANTIC", 0.6))
IMPORTANCE_WEIGHT      = float(os.getenv("IMPORTANCE_WEIGHT",      0.3))
RECENCY_WEIGHT         = float(os.getenv("RECENCY_WEIGHT",         0.1))

# Retrieval-Parameter
RETRIEVAL_CANDIDATES   = int(os.getenv("RETRIEVAL_CANDIDATES",   10))
MIN_PASSTAGE_SCORE     = float(os.getenv("MIN_PASSTAGE_SCORE",     0.1))
SYN_WEIGHT             = float(os.getenv("SYN_WEIGHT",             2.0))

# Modell-Konfigurationen
EMBEDDING_MODEL        = os.getenv("EMBEDDING_MODEL",        "sentence-transformers/all-MiniLM-L6-v2")
CROSS_ENCODER_MODEL    = os.getenv("CROSS_ENCODER_MODEL",    "cross-encoder/ms-marco-MiniLM-L-6-v2")
KEYWORD_MODEL          = os.getenv("KEYWORD_MODEL",          EMBEDDING_MODEL)
SEGMENTER_MODEL        = os.getenv("SEGMENTER_MODEL",        EMBEDDING_MODEL)

# Offenes LLM-Modell für Start & Zusammenfassung
LLM_MODEL_INITIAL      = os.getenv("LLM_MODEL_INITIAL",      "mistral-openorca")
LLM_MODEL_REFINE       = os.getenv("LLM_MODEL_REFINE",       "mistral-openorca")
OLLAMA_HOST            = os.getenv("OLLAMA_HOST",            "http://ollama:11434")

# Zusammenfassungs-Parameter
SUMMARY_MIN_LENGTH     = int(os.getenv("SUMMARY_MIN_LENGTH",     50))
SUMMARY_MAX_LENGTH     = int(os.getenv("SUMMARY_MAX_LENGTH",    500))
SUMMARY_TEMPERATURE    = float(os.getenv("SUMMARY_TEMPERATURE",  0.0))
SUMMARY_BATCH_SIZE     = int(os.getenv("SUMMARY_BATCH_SIZE",    10))
SUMMARY_MAX_TOKENS     = int(os.getenv("SUMMARY_MAX_TOKENS",   1024))

# Merge Summary
MERGE_SUMMARY_WORD_LIMIT = int(os.getenv("MERGE_SUMMARY_WORD_LIMIT", 500))

# RAG-Pipeline-Parameter
FINAL_CONTEXTS             = int(os.getenv("FINAL_CONTEXTS",             5))
SUMMARY_BOOST              = float(os.getenv("SUMMARY_BOOST",              1.2))
RECENCY_MAX_DAYS           = int(os.getenv("RECENCY_MAX_DAYS",           14))
USE_STRICT_KEYWORD_FILTER  = os.getenv("USE_STRICT_KEYWORD_FILTER", "false").lower() in ("1","true","yes")

# Topic-Parameter
TOPIC_THRESHOLD_FACTOR = float(os.getenv("TOPIC_THRESHOLD_FACTOR", 1.2))
TOPIC_TITLE_WEIGHT     = float(os.getenv("TOPIC_TITLE_WEIGHT",     1.0))
TOPIC_EMB_MODEL        = os.getenv("TOPIC_EMB_MODEL",            EMBEDDING_MODEL)
TOPIC_EMB_WEIGHT       = float(os.getenv("TOPIC_EMB_WEIGHT",       0.5))
TOPIC_EMB_THRESHOLD    = float(os.getenv("TOPIC_EMB_THRESHOLD",    0.3))

# Kafka & Timeouts
KAFKA_BOOTSTRAP        = os.getenv("KAFKA_BOOTSTRAP",        "kafka:9092")
TIMEOUT_SEC            = int(os.getenv("TIMEOUT_SEC",              60))
