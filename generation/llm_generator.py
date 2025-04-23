import os
import logging

# 1) Logging‑Verzeichnis und Logger einrichten
LOG_DIR  = os.getenv("LLM_CHAT_LOG_DIR", "/app/logs")
LOG_FILE = os.path.join(LOG_DIR, "llm_chat.log")
os.makedirs(LOG_DIR, exist_ok=True)

chat_logger = logging.getLogger("llm_chat")
chat_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
))
chat_logger.addHandler(file_handler)

# 2) Ollama‑Client importieren
import os
os.environ.setdefault("OLLAMA_URL", os.getenv("OLLAMA_URL","http://ollama:11434"))
from ollama import chat

from config import LLM_MODEL_INITIAL, LLM_MODEL_REFINE
from generation.prompt_template import (
    build_initial_prompt,
    build_refine_prompt,
    build_finalize_prompt
)

class LLMGenerator:
    def __init__(self, initial_model=LLM_MODEL_INITIAL, refine_model=LLM_MODEL_REFINE):
        self.initial_model = initial_model
        self.refine_model  = refine_model

    def generate(self, question: str, contexts: list) -> str:
        # --- Schritt 1: Initialer Prompt
        prompt1 = build_initial_prompt(question, contexts)
        chat_logger.info(f"→ INITIAL PROMPT:\n{prompt1}")

        resp1 = chat(model=self.initial_model, messages=[{'role':'user','content':prompt1}])
        answer1 = resp1.message.content.strip()
        chat_logger.info(f"← INITIAL RESPONSE:\n{answer1}")

        # --- Schritt 2: Refinement Prompt
        prompt2 = build_refine_prompt(question, contexts, answer1)
        chat_logger.info(f"→ REFINEMENT PROMPT:\n{prompt2}")

        resp2 = chat(model=self.refine_model, messages=[{'role':'user','content':prompt2}])
        answer2 = resp2.message.content.strip()
        chat_logger.info(f"← REFINEMENT RESPONSE:\n{answer2}")

        # --- Schritt 3: Finalisierungs Prompt
        prompt3 = build_finalize_prompt(question, answer2)
        chat_logger.info(f"→ FINALIZE PROMPT:\n{prompt3}")

        resp3 = chat(model=self.refine_model, messages=[{'role':'user','content':prompt3}])
        final_answer = resp3.message.content.strip()
        chat_logger.info(f"← FINAL RESPONSE:\n{final_answer}")

        return final_answer
