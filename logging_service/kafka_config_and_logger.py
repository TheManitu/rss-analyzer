# kafka_config_and_logger.py

"""
Definiert Kafka-Topics, JSON-Schemas (intern) und Funktionen zum Loggen
von UserQuestion- und ArticleViewed-Events.
"""

import json
from kafka import KafkaProducer
from datetime import datetime, timezone

# ----------------------------------------
#  Kafka-Konfiguration
# ----------------------------------------

KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC_USER_QUESTIONS    = "UserQuestions"
TOPIC_ARTICLE_VIEWS     = "ArticleViews"

# ----------------------------------------
#  JSON-Schema-Definitionen (nur zur Referenz)
# ----------------------------------------

USER_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "type":            {"enum": ["UserQuestion"]},
        "question":        {"type": "string"},
        "topic":           {"type": "string"},
        "n_candidates":    {"type": "integer"},
        "used_article_ids":{"type": "array", "items": {"type": "integer"}},
        "timestamp":       {"type": "string", "format": "date-time"}
    },
    "required": ["type", "question", "n_candidates", "timestamp"]
}

ARTICLE_VIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "type":      {"enum": ["ArticleViewed"]},
        "article_id":{"type": "integer"},
        "user_id":   {"type": "string"},
        "topic":     {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"}
    },
    "required": ["type", "article_id", "timestamp"]
}

# ----------------------------------------
#  Kafka Producer
# ----------------------------------------

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# ----------------------------------------
#  Event-Logging-Funktionen
# ----------------------------------------

def log_user_question(question: str, topic: str, n_candidates: int, used_article_ids: list):
    """
    Loggt ein UserQuestion-Event mit Anzahl Kandidaten und
    Liste der verwendeten Artikel-IDs.
    """
    event = {
        "type":             "UserQuestion",
        "question":         question,
        "topic":            topic,
        "n_candidates":     n_candidates,
        "used_article_ids": used_article_ids,
        "timestamp":        datetime.now(timezone.utc).isoformat()
    }
    # optional: jsonschema.validate(event, USER_QUESTION_SCHEMA)
    producer.send(TOPIC_USER_QUESTIONS, value=event)


def log_article_view(article_id: int, user_id: str = None, topic: str = None):
    """
    Loggt ein ArticleViewed-Event mit Artikel-ID, (optional) User und Topic.
    """
    event = {
        "type":       "ArticleViewed",
        "article_id": article_id,
        "user_id":    user_id,
        "topic":      topic,
        "timestamp":  datetime.now(timezone.utc).isoformat()
    }
    # optional: jsonschema.validate(event, ARTICLE_VIEW_SCHEMA)
    producer.send(TOPIC_ARTICLE_VIEWS, value=event)
