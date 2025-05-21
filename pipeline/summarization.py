# pipeline/summarization.py

import logging
import asyncio
import aiohttp
import sys
from storage.duckdb_storage import DuckDBStorage
from config import (
    OLLAMA_HOST,
    LLM_MODEL_REFINE,
    SUMMARY_MIN_LENGTH,
    SUMMARY_MAX_LENGTH,
    SUMMARY_TEMPERATURE,
    SUMMARY_BATCH_SIZE
)

# --- Logger initialisieren ---
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger = logging.getLogger("summarizer")
logger.setLevel(logging.INFO)
logger.addHandler(handler)


class Summarizer:
    """
    Zwei-Phasen-Summarizer für maximale Qualität:
      1) Chunk-Level Summaries: Kernaussagen aus Textteilen
      2) Finaler Refine-Schritt: Kombiniere Teil-Summaries
    Fortschrittsanzeige und Ausgabe der vollständigen Zusammenfassungen.
    Optionales Reset aller vorhandenen Summaries.
    """
    def __init__(self, db_path: str | None = None):
        self.storage = DuckDBStorage(db_path=db_path)
        self.ollama_url = f"{OLLAMA_HOST}/api/generate"
        self.sem = asyncio.Semaphore(SUMMARY_BATCH_SIZE)

    def _build_prompt(self, text: str) -> str:
        return (
            "Fasse folgenden Text prägnant zusammen und nenne die "
            "Kernaussagen, Take-aways sowie deren Relevanz:\n\n" + text
        )

    def _build_refine_prompt(self, part_summaries: list[str]) -> str:
        combined = "\n\n".join(part_summaries)
        return (
            "Du hast mehrere Teilsummaries eines Artikels erstellt. "
            "Fasse sie jetzt zu einer einheitlichen, detaillierten Gesamt-Zusammenfassung "
            "zusammen, die alle wichtigen Punkte enthält:\n\n" + combined
        )

    def _chunk_text(self, text: str) -> list[str]:
        # Splittet nach Absätzen, sammelt so lange bis SUMMARY_MAX_LENGTH Wörter erreicht
        paras = [p.strip() for p in text.split("\n") if p.strip()]
        chunks, current = [], ""
        for p in paras:
            # Zähle Wörter im potenziellen Chunk
            if len((current + " " + p).split()) <= SUMMARY_MAX_LENGTH:
                current = f"{current} {p}".strip() if current else p
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)
        return chunks

    async def _call_api(self, session: aiohttp.ClientSession, prompt: str) -> str:
        # Wir verzichten auf max_tokens, um volle Länge zu bekommen
        payload = {
            "model": LLM_MODEL_REFINE,
            "prompt": prompt,
            "temperature": SUMMARY_TEMPERATURE,
            "stream": False
        }
        async with session.post(self.ollama_url, json=payload, timeout=120) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("response", "").strip()

    def _fallback_snippet(self, text: str) -> str:
        # Wenn Summary fehlt oder zu kurz, nimm die ersten SUMMARY_MIN_LENGTH Wörter
        words = text.split()
        snippet = " ".join(words[:SUMMARY_MIN_LENGTH])
        return snippet + ("…" if len(words) > SUMMARY_MIN_LENGTH else "")

    async def _process_article(self, session, link: str, content: str) -> tuple[str, str]:
        # Phase 1: Chunk-Level Summaries
        chunks = self._chunk_text(content or "")
        part_summaries: list[str] = []
        for chunk in chunks:
            prompt = self._build_prompt(chunk)
            try:
                summ = await self._call_api(session, prompt)
                if not summ or len(summ.split()) < SUMMARY_MIN_LENGTH:
                    raise ValueError("Teil-Summary zu kurz oder leer")
            except Exception:
                # Fallback: Snippet aus Original-Chunk
                summ = self._fallback_snippet(chunk)
            part_summaries.append(summ)
        logger.info(f"-> {link}: {len(part_summaries)} Teil-Summaries erstellt")

        # Phase 2: Gesamt-Summary verfeinern
        refine_prompt = self._build_refine_prompt(part_summaries)
        try:
            final_summary = await self._call_api(session, refine_prompt)
            if not final_summary or len(final_summary.split()) < SUMMARY_MIN_LENGTH:
                raise ValueError("Final-Summary zu kurz oder leer")
        except Exception:
            # Fallback: Einfache Konkatenation der Part-Summaries
            final_summary = "\n\n".join(part_summaries)
        return link, final_summary

    def run(self, reset: bool = False):
        if reset:
            logger.info("Reset: Lösche alle vorhandenen Summaries …")
            self.storage.execute("UPDATE articles SET summary = '';")

        # Lade alle Artikel ohne Summary
        con = self.storage.connect()
        rows = con.execute(
            "SELECT link, content FROM articles WHERE summary IS NULL OR summary = ''"
        ).fetchall()
        con.close()

        total = len(rows)
        logger.info(f"Starte Zusammenfassung von {total} Artikeln …")
        if total == 0:
            logger.info("Keine Artikel zum Zusammenfassen.")
            return

        async def worker():
            async with aiohttp.ClientSession() as session:
                async def sem_task(link, content):
                    async with self.sem:
                        return await self._process_article(session, link, content)

                tasks = [
                    asyncio.create_task(sem_task(link, content))
                    for link, content in rows
                ]

                count = 0
                for fut in asyncio.as_completed(tasks):
                    link, summary = await fut
                    count += 1
                    remaining = total - count

                    # Summary in DB speichern
                    con2 = self.storage.connect()
                    con2.execute(
                        "UPDATE articles SET summary = ? WHERE link = ?",
                        (summary, link)
                    )
                    con2.close()

                    # Fortschritt und komplette Summary ausgeben
                    logger.info(f"[{count}/{total}] {link} abgeschlossen (verbleibend: {remaining})")
                    logger.info("Zusammenfassung:\n" + summary)

        try:
            asyncio.run(worker())
        except KeyboardInterrupt:
            logger.warning("Summarizer durch Benutzer beendet.")
            return

        logger.info("=== Alle Artikel sind zusammengefasst ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Artikel-Zusammenfassungen erstellen")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Alle vorhandenen Summaries zurücksetzen und komplett neu generieren"
    )
    args = parser.parse_args()

    Summarizer().run(reset=args.reset)
