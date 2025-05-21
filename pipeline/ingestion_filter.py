# pipeline/ingestion_filter.py
import re
from langdetect import detect, DetectorFactory
from typing import Tuple

from config import (
    MIN_ARTICLE_WORDS,
    MAX_PUNCT_RATIO,
    ALLOWED_LANGUAGES,
    BLACKLIST_PATTERNS,
    BLOCKED_TOPICS,
    TOPIC_ALLOW_PREFIX
)
import logging

logger = logging.getLogger(__name__)
# Langdetect determinism
DetectorFactory.seed = 0

class IngestionFilter:
    """
    Filtert Artikel bereits bei der Ingestion nach definierten Kriterien:
      - Mindestwortzahl
      - Maximaler Sonderzeichenanteil
      - Zugelassene Sprachen
      - Blacklist-Textmuster
      - Unerwünschte Topics
    """

    @staticmethod
    def is_short(text: str) -> bool:
        words = len(text.split())
        return words < MIN_ARTICLE_WORDS

    @staticmethod
    def is_weird_format(text: str) -> bool:
        if not text:
            return True
        non_alnum = sum(1 for c in text if not c.isalnum() and not c.isspace())
        total = len(text)
        ratio = non_alnum / total if total else 1.0
        return ratio > MAX_PUNCT_RATIO

    @staticmethod
    def detect_language(text: str) -> str:
        try:
            lang = detect(text)
            return lang
        except Exception:
            return ""

    @staticmethod
    def has_blacklist_pattern(text: str) -> bool:
        for pattern in BLACKLIST_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        return False

    @staticmethod
    def is_blocked_topic(topic: str) -> bool:
        lt = (topic or "").lower()
        for blocked in BLOCKED_TOPICS:
            if blocked in lt:
                # Allow Gaming as exception
                if TOPIC_ALLOW_PREFIX and lt.startswith(TOPIC_ALLOW_PREFIX.lower()):
                    return False
                return True
        return False

    @classmethod
    def validate(cls, title: str, content: str, topic: str) -> Tuple[bool, str]:
        """
        Validiert einen Artikel und gibt (is_valid, reason) zurück.
        """
        # 1) Wortzahl
        if cls.is_short(content):
            return False, f"Wortzahl < {MIN_ARTICLE_WORDS}"
        # 2) Format-Check
        if cls.is_weird_format(content):
            return False, f"Sonderzeichenanteil > {MAX_PUNCT_RATIO * 100:.0f}%"
        # 3) Sprache
        lang = cls.detect_language(content)
        if lang not in ALLOWED_LANGUAGES:
            return False, f"Sprache '{lang}' nicht in {ALLOWED_LANGUAGES}"
        # 4) Blacklist-Muster
        if cls.has_blacklist_pattern(content):
            return False, "Enthält Blacklist-Muster"
        # 5) Topic-Blacklist
        if cls.is_blocked_topic(topic):
            return False, f"Unerwünschtes Topic '{topic}'"
        return True, "OK"
