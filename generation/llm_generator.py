# generation/llm_generator.py

import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from ollama import chat
from config import LLM_MODEL_INITIAL, LLM_MODEL_REFINE
from generation.prompt_template import (
    build_initial_prompt,
    build_refine_prompt,
    build_finalize_prompt
)

# Logging vorbereiten
LOG_DIR = os.getenv("LLM_CHAT_LOG_DIR", "/app/logs")
os.makedirs(LOG_DIR, exist_ok=True)
fh = logging.FileHandler(os.path.join(LOG_DIR, "llm_chat.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
chat_logger = logging.getLogger("llm_chat")
chat_logger.setLevel(logging.INFO)
chat_logger.addHandler(fh)

SYSTEM_PROMPT = (
    "Du bist ein fachkundiger Assistent. Antworte ausschließlich auf Basis der bereitgestellten Artikelsummaries. "
    "Erfinde keine zusätzlichen Quellen oder Fakten. "
    "Antworte direkt und selbstbewusst. Wenn die bereitgestellten Informationen nicht ausreichen, "
    "gib kurz an, dass keine Informationen vorliegen, statt Vermutungen anzustellen."
)

class LLMGenerator:
    def __init__(self, initial_model=LLM_MODEL_INITIAL, refine_model=LLM_MODEL_REFINE, timeout_sec=30):
        self.initial_model = initial_model
        self.refine_model  = refine_model
        self.timeout       = timeout_sec

    def _call_with_timeout(self, model: str, messages: list) -> any:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(chat, model=model, messages=messages)
            try:
                return future.result(timeout=self.timeout)
            except TimeoutError:
                chat_logger.error(f"LLM call timed out after {self.timeout}s")
                raise
            except Exception as e:
                chat_logger.exception("Fehler bei Initialantwort")
                return "Entschuldigung, die Antwort konnte aktuell nicht generiert werden."

    def generate(self, question: str, contexts: list) -> str:
        # Schritt 1: Initial
        p1 = build_initial_prompt(question, contexts)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": p1}]
        chat_logger.info(f"→ INIT PROMPT:\n{p1}")
        try:
            r1 = self._call_with_timeout(self.initial_model, msgs)
            a1 = r1.message.content.strip()
            chat_logger.info(f"← INIT RESP:\n{a1}")
        except Exception:
            return "Entschuldigung, die Antwort konnte derzeit nicht generiert werden."

        # Schritt 2: Refine
        p2 = build_refine_prompt(question, contexts, a1)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": p2}]
        chat_logger.info(f"→ REFINE PROMPT:\n{p2}")
        try:
            r2 = self._call_with_timeout(self.refine_model, msgs)
            a2 = r2.message.content.strip()
            chat_logger.info(f"← REFINE RESP:\n{a2}")
        except Exception:
            return a1  # fallback

        # Schritt 3: Finalisieren
        p3 = build_finalize_prompt(question, contexts, a2)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": p3}]
        chat_logger.info(f"→ FINAL PROMPT:\n{p3}")
        try:
            r3 = self._call_with_timeout(self.refine_model, msgs)
            final = r3.message.content.strip()
            chat_logger.info(f"← FINAL RESP:\n{final}")
        except Exception:
            return a2  # fallback

        return final
