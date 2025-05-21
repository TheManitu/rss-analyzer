# pipeline/relevance_scoring.py

import os
import logging
import json
import re
import requests

from storage.duckdb_storage import DuckDBStorage
from config import LLM_MODEL_INITIAL, OLLAMA_HOST

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RelevanceScorer:
    """
    Bewertet Artikel mit einem Relevanz-Score (1.0–10.0) via Ollama HTTP-API.
    Im run()-Durchgang werden nur 'abnormale' Scores (NULL, 1.0 oder >10.0) neu berechnet.
    """

    def __init__(self, db_path=None, model_name: str | None = None):
        self.storage = DuckDBStorage(db_path=db_path)
        self.model   = (model_name or LLM_MODEL_INITIAL).lower()
        self.host    = os.getenv("OLLAMA_HOST", OLLAMA_HOST).rstrip("/")

        logger.info(f"RelevanceScorer: Ollama host={self.host}, model='{self.model}'")

        # Fallback auf OpenAI-Stub falls nötig
        self.fallback_openai = False
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            tags = [m["name"].lower() for m in resp.json().get("models", [])]
            if not any(t == self.model or t.startswith(self.model) for t in tags):
                logger.warning(f"Modell '{self.model}' nicht gefunden, fallback auf OpenAI-Stub.")
                self.fallback_openai = True
        except Exception as e:
            logger.warning(f"Fehler bei /api/tags: {e}. Fallback auf OpenAI-Stub.")
            self.fallback_openai = True

    def _score_with_ollama(self, excerpt: str, topic: str) -> float:
        prompt = (
            f"Artikel-Thema: {topic}\n"
            f"Artikel-Auszug: {excerpt[:500]}...\n\n"
            "Bewerte die Wichtigkeit auf einer Skala von 1.0 (sehr gering) bis 10.0 (sehr hoch). "
            "Antworte **nur** mit der Zahl."
        )
        payload = {"model": self.model, "prompt": prompt, "max_tokens": 5, "do_sample": False}

        res = requests.post(f"{self.host}/api/generate", json=payload, timeout=60)
        res.raise_for_status()
        raw = res.text

        # 1) klassisches JSON
        try:
            obj = json.loads(raw)
            text = obj["choices"][0]["text"].strip()
            m = re.search(r"(\d+(?:\.\d+)?)", text)
            if m:
                val = float(m.group(1))
                return max(1.0, min(val, 10.0))
        except Exception:
            pass

        # 2) Streaming-Fallback: komplette response-Fragmente sammeln
        full = ""
        for line in raw.splitlines():
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "response" in o:
                full += o["response"]
            if o.get("done", False):
                break

        cleaned = full.strip()
        nums = re.findall(r"\d+\.\d+|\d+", cleaned)
        floats = [float(n) for n in nums]

        # 3) Trailing-Nummer, falls kein Prompt-Text wiederholt wird
        low = cleaned.lower()
        if not (low.startswith("die wichtigkeit") or low.startswith("bewerten sie")):
            m_end = re.search(r"(\d+(?:\.\d+)?)(?:\D*)$", cleaned)
            if m_end:
                cand = float(m_end.group(1))
                if 1.0 <= cand <= 10.0:
                    return cand

        # 4) Interior-Floats zwischen 1 und 10
        interior = [v for v in floats if 1.0 < v < 10.0]
        if interior:
            return interior[-1]

        # 5) Exakte 10.0 oder 1.0
        if 10.0 in floats:
            return 10.0
        if 1.0 in floats:
            return 1.0

        # 6) letzte Zahl clamped auf [1,10]
        if floats:
            last = floats[-1]
            return max(1.0, min(last, 10.0))

        # 7) letzter Ausweg
        return 1.0

    def _score_with_openai(self, excerpt: str, topic: str) -> float:
        # Fallback-Stub
        return 1.0

    def evaluate(self, excerpt: str, topic: str) -> float:
        if self.fallback_openai:
            return self._score_with_openai(excerpt, topic)
        try:
            return self._score_with_ollama(excerpt, topic)
        except Exception as e:
            logger.warning(f"Ollama-Scoring fehlgeschlagen ({e}), fallback auf OpenAI.")
            return self._score_with_openai(excerpt, topic)

    def run(self, time_filter: str = '14_days'):
        con = self.storage.connect()
        # Nur Artikel mit importance IS NULL, =1.0 oder >10.0
        rows = con.execute("""
            SELECT link, content, description, topic
              FROM articles
             WHERE importance IS NULL
                OR importance = 1.0
                OR importance > 10.0
        """).fetchall()
        con.close()

        total = len(rows)
        logger.info(f"RelevanceScorer: {total} Artikel mit abnormalem Score zum Re-Scoren")

        for idx, (link, content, desc, topic) in enumerate(rows, start=1):
            excerpt = (content or desc or "")[:500]
            score = self.evaluate(excerpt, topic or "Allgemein")

            db = self.storage.connect()
            db.execute(
                "UPDATE articles SET importance = ? WHERE link = ?",
                (score, link)
            )
            db.close()

            logger.info(f"[{idx}/{total}] {link} → {score:.2f}")

        logger.info("RelevanceScorer: Re-Scoring abgeschlossen.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    RelevanceScorer().run()
