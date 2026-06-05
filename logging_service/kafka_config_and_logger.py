# logging_service/kafka_config_and_logger.py

import os
import json
import logging
from datetime import datetime, timezone
import atexit

try:
    from kafka import KafkaProducer
    from kafka.errors import NoBrokersAvailable
    from kafka.admin import KafkaAdminClient, NewTopic
except Exception:  # pragma: no cover - optional runtime dependency guard
    KafkaProducer = None
    KafkaAdminClient = None
    NewTopic = None

    class NoBrokersAvailable(Exception):
        pass

# -----------------------------------------------------------------------------
# Kafka-Konfiguration (anpassbar via ENV)
# -----------------------------------------------------------------------------
_BOOTSTRAP_ENV       = os.getenv("KAFKA_BOOTSTRAP_SERVERS") or os.getenv("KAFKA_BOOTSTRAP") or ""
BOOTSTRAP_SERVERS    = [server for server in _BOOTSTRAP_ENV.split(",") if server]
KAFKA_ENABLED        = os.getenv(
    "ENABLE_KAFKA_LOGGING",
    "true" if BOOTSTRAP_SERVERS else "false"
).lower() in ("1", "true", "yes")
TOPIC_USER_QUESTIONS = os.getenv("TOPIC_USER_QUESTIONS", "UserQuestions")
TOPIC_ARTICLE_VIEWS  = os.getenv("TOPIC_ARTICLE_VIEWS",  "ArticleViews")
TOPIC_ANSWER_QUALITY = os.getenv("TOPIC_ANSWER_QUALITY", "AnswerQuality")
PARTITIONS           = int(os.getenv("KAFKA_TOPIC_PARTITIONS", "1"))
REPLICATION_FACTOR   = int(os.getenv("KAFKA_TOPIC_REPLICATION_FACTOR", "1"))

# -----------------------------------------------------------------------------
# Topics initialisieren
# -----------------------------------------------------------------------------
def ensure_topics():
    if not KAFKA_ENABLED or not BOOTSTRAP_SERVERS:
        logging.debug("Kafka-Logging nicht konfiguriert; Topic-Setup uebersprungen.")
        return
    if KafkaAdminClient is None:
        logging.debug("Kafka-Paket nicht installiert; Topic-Setup uebersprungen.")
        return
    try:
        admin    = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS)
        existing = set(admin.list_topics())
        needed   = [TOPIC_USER_QUESTIONS, TOPIC_ARTICLE_VIEWS, TOPIC_ANSWER_QUALITY]
        new_topics = [
            NewTopic(name=tn, num_partitions=PARTITIONS, replication_factor=REPLICATION_FACTOR)
            for tn in needed if tn not in existing
        ]
        if new_topics:
            admin.create_topics(new_topics=new_topics)
            logging.info(f"Created Kafka topics: {[t.name for t in new_topics]}")
        admin.close()
    except Exception as e:
        logging.warning(f"Could not ensure Kafka topics: {e}")

# Topic-Setup ist opt-in, damit lokale UI/API-Starts ohne Kafka nicht am Import rauschen.
if os.getenv("ENABLE_KAFKA_TOPIC_SETUP", "false").lower() in ("1", "true", "yes"):
    ensure_topics()

# -----------------------------------------------------------------------------
# Lazy-initialisierter KafkaProducer
# -----------------------------------------------------------------------------
_producer = None

def _get_producer():
    global _producer
    if not KAFKA_ENABLED or not BOOTSTRAP_SERVERS:
        logging.debug("Kafka-Logging nicht konfiguriert; Event wird verworfen.")
        return None
    if KafkaProducer is None:
        logging.debug("Kafka-Paket nicht installiert; Events werden verworfen.")
        return None
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=5,
                linger_ms=100
            )
            logging.info(f"KafkaProducer connected to {BOOTSTRAP_SERVERS}")
            atexit.register(_producer.flush)
            atexit.register(_producer.close)
        except NoBrokersAvailable:
            logging.warning("Kafka brokers not available; events will be dropped.")
            _producer = None
    return _producer

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# -----------------------------------------------------------------------------
# Event-Logging-Funktionen
# -----------------------------------------------------------------------------
def log_user_question(question: str,
                      topic: str,
                      n_candidates: int,
                      used_article_ids: list,
                      user_id: str = None,
                      session_id: str = None):
    event = {
        "event_type":       "UserQuestion",
        "timestamp":        _now_iso(),
        "user_id":          user_id,
        "session_id":       session_id,
        "question":         question,
        "topic":            topic,
        "n_candidates":     n_candidates,
        "used_article_ids": used_article_ids
    }
    producer = _get_producer()
    if producer:
        try:
            producer.send(TOPIC_USER_QUESTIONS, value=event)
        except Exception as e:
            logging.error(f"Error sending UserQuestion event: {e}")
    else:
        logging.debug("Dropped UserQuestion event (no Kafka producer)")

def log_article_view(article_id: str,
                     topic: str = None,
                     user_id: str = None,
                     session_id: str = None):
    event = {
        "event_type":  "ArticleViewed",
        "timestamp":   _now_iso(),
        "user_id":     user_id,
        "session_id":  session_id,
        "article_id":  article_id,
        "topic":       topic
    }
    producer = _get_producer()
    if producer:
        try:
            producer.send(TOPIC_ARTICLE_VIEWS, value=event)
        except Exception as e:
            logging.error(f"Error sending ArticleViewed event: {e}")
    else:
        logging.debug("Dropped ArticleViewed event (no Kafka producer)")

def log_answer_quality(used_article_ids: list,
                       quality_score: float,
                       flag: bool,
                       user_id: str = None,
                       session_id: str = None):
    event = {
        "event_type":       "AnswerQuality",
        "timestamp":        _now_iso(),
        "user_id":          user_id,
        "session_id":       session_id,
        "used_article_ids": used_article_ids,
        "quality_score":    quality_score,
        "flag":             flag
    }
    producer = _get_producer()
    if producer:
        try:
            producer.send(TOPIC_ANSWER_QUALITY, value=event)
        except Exception as e:
            logging.error(f"Error sending AnswerQuality event: {e}")
    else:
        logging.debug("Dropped AnswerQuality event (no Kafka producer)")
