# generation/llm_generator.py

import os
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from ollama import chat
from config import (
    LLM_MODEL_INITIAL,
    LLM_MODEL_REFINE,
    TIMEOUT_SEC,
    MERGE_SUMMARY_WORD_LIMIT
)
from generation.prompt_template import build_merge_prompt, build_answer_prompt

# Logging vorbereiten
LOG_DIR = os.getenv("LLM_CHAT_LOG_DIR", "/app/logs")
os.makedirs(LOG_DIR, exist_ok=True)
fh = logging.FileHandler(os.path.join(LOG_DIR, "llm_chat.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
chat_logger = logging.getLogger("llm_chat")
chat_logger.setLevel(logging.INFO)
chat_logger.addHandler(fh)

SYSTEM_PROMPT = (
    "Du bist ein fachkundiger Assistent. Antworte ausschließlich auf Basis "
    "der bereitgestellten Artikelsummaries. Erfinde keine zusätzlichen Quellen "
    "oder Fakten. Antworte direkt und selbstbewusst. Wenn Informationen fehlen, "
    "gib kurz an, dass keine ausreichenden Daten vorliegen."
)


class LLMGenerator:
    """
    1) Merge aller Kontext-Summaries zu einer Meta-Summary (bis MERGE_SUMMARY_WORD_LIMIT Wörter)
    2) Antwort nur auf Basis dieser Meta-Summary erstellen
    """

    def __init__(self,
                 initial_model: str = LLM_MODEL_INITIAL,
                 refine_model:  str = LLM_MODEL_REFINE,
                 timeout_sec:   int = TIMEOUT_SEC):
        self.initial_model = initial_model
        self.refine_model  = refine_model
        self.timeout       = timeout_sec

    def _call_with_timeout(self, model: str, messages: list) -> any:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(chat, model=model, messages=messages)
            try:
                return future.result(timeout=self.timeout)
            except TimeoutError:
                chat_logger.error(f"LLM-Aufruf nach {self.timeout}s abgebrochen")
            except Exception as e:
                chat_logger.error(f"LLM-Verbindung oder Fehler: {e}")
        return None

    def _merge_summaries(self, contexts: list[dict]) -> str:
        prompt = build_merge_prompt(contexts, MERGE_SUMMARY_WORD_LIMIT)
        chat_logger.info(f"→ MERGE PROMPT:\n{prompt}")
        resp = self._call_with_timeout(self.refine_model, [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ])
        if resp and hasattr(resp, "message"):
            merged = resp.message.content.strip()
            chat_logger.info(f"[DEBUG] Merged ({len(merged.split())} Wörter)")
            return merged

        # Fallback: rohe Verkettung, gekürzt
        all_text = " ".join(ctx["summary"] for ctx in contexts)
        words    = all_text.split()
        if len(words) > MERGE_SUMMARY_WORD_LIMIT:
            fallback = " ".join(words[:MERGE_SUMMARY_WORD_LIMIT]) + "…"
        else:
            fallback = all_text
        chat_logger.warning(f"Merge-Fallback ({len(fallback.split())} Wörter)")
        return fallback

    def generate(self, question: str, contexts: list[dict]) -> str:
        # 1) Meta-Summary
        merged_summary = self._merge_summaries(contexts)

        # 2) Antwort-Prompt
        prompt = build_answer_prompt(question, contexts, merged_summary)
        chat_logger.info(f"→ ANSWER PROMPT:\n{prompt}")
        resp = self._call_with_timeout(self.initial_model, [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ])
        if resp and hasattr(resp, "message"):
            answer = resp.message.content.strip()
            chat_logger.info(f"← ANSWER RESP:\n{answer}")
            return answer

        # Fallback: Meta-Summary als Antwort
        chat_logger.warning("Antwort-Fallback: Meta-Summary")
        return merged_summary


# Alias
generate = LLMGenerator
