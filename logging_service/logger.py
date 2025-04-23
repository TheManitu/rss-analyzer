"""
Zentrales Logging (Kafka) für Events aus allen Modulen.
"""
from kafka import KafkaProducer
import json
from config import KAFKA_BOOTSTRAP, TOPIC_USER_QUESTIONS, TOPIC_USER_QUESTIONS, TOPIC_USER_QUESTIONS

class EventLogger:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def log_question(self, question: str, topic: str = None):
        """
        Loggt eine User-Frage mit optionalem Thema.
        """
        event = {
            "type": "UserQuestion",
            "question": question,
            "topic": topic,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
        self.producer.send(TOPIC_USER_QUESTIONS, value=event)

    def log_article_view(self, article_id: int, user_id: str = None):
        """
        Loggt, wenn ein Artikel im Frontend angesehen wurde.
        """
        event = {
            "type": "ArticleViewed",
            "article_id": article_id,
            "user_id": user_id,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
        # Beispiel für ein eigenes Topic
        self.producer.send("ArticleViews", value=event)
