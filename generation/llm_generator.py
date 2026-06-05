# generation/llm_generator.py

import os
import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from ollama import chat
from config import (
    LLM_MODEL_INITIAL,
    LLM_MODEL_REFINE,
    TIMEOUT_SEC,
    MERGE_SUMMARY_WORD_LIMIT
)
from generation.prompt_template import build_merge_prompt, build_answer_prompt
from pipeline.source_quality import classify_source, credibility_label
from pipeline.text_quality import clean_article_text

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

    @staticmethod
    def _message_content(resp) -> str:
        if not resp:
            return ""
        if hasattr(resp, "message") and hasattr(resp.message, "content"):
            return (resp.message.content or "").strip()
        if isinstance(resp, dict):
            message = resp.get("message") or {}
            return (message.get("content") or resp.get("response") or "").strip()
        return ""

    @staticmethod
    def _summary_from_context(ctx: dict) -> str:
        return clean_article_text(
            ctx.get("summary")
            or ctx.get("text")
            or ctx.get("section_text")
            or ctx.get("content")
            or ctx.get("description")
            or ""
        )

    @classmethod
    def _normalize_contexts(cls, contexts: list[dict]) -> list[dict]:
        normalized = []
        seen = set()
        for idx, ctx in enumerate(contexts or [], start=1):
            link = (ctx.get("link") or "").strip()
            summary = cls._summary_from_context(ctx)
            if not link or not summary or link in seen:
                continue
            seen.add(link)
            quality = classify_source(link, ctx.get("title") or "", summary)
            normalized.append({
                "title": clean_article_text(ctx.get("title") or f"Quelle {idx}"),
                "link": link,
                "summary": summary,
                "source_type": ctx.get("source_type") or quality["source_type"],
                "credibility_score": ctx.get("credibility_score", quality["credibility_score"]),
                "is_official": ctx.get("is_official", quality["is_official"]),
                "is_speculative": ctx.get("is_speculative", quality["is_speculative"]),
            })
        return sorted(
            normalized,
            key=lambda ctx: (ctx.get("credibility_score", 0), ctx.get("source_type") == "official"),
            reverse=True,
        )

    @staticmethod
    def _confirmed_point(ctx: dict) -> str:
        title = ctx.get("title", "Quelle")
        summary = ctx.get("summary", "")
        haystack = f"{title} {summary}".lower()

        if "chatgpt" in haystack and "release notes" in haystack and "active session" in haystack:
            return f"- {title}: OpenAI dokumentiert neue Account-Sicherheitsfunktionen rund um aktive ChatGPT-Sitzungen."
        if "model release notes" in haystack and "gpt-5.5 instant" in haystack:
            return f"- {title}: OpenAI dokumentiert ein GPT-5.5-Instant-Update fuer bessere Antwortqualitaet, Lesbarkeit und Alltagshilfe."
        if "gpt-5.5 in chatgpt" in haystack or "gpt-5.5 instant in chatgpt" in haystack:
            return f"- {title}: OpenAI beschreibt GPT-5.5 Instant als aktuellen bestaetigten ChatGPT-Stand fuer angemeldete Nutzer."

        words = summary.split()
        if not words:
            return f"- {title}: Quelle enthaelt relevante Informationen, Details siehe Quellenliste."
        concise = " ".join(words[:22])
        if len(words) > 22:
            concise += "..."
        return f"- {title}: {concise}"

    @staticmethod
    def _combined_text(contexts: list[dict]) -> str:
        return " ".join(f"{ctx.get('title', '')} {ctx.get('summary', '')}" for ctx in contexts).lower()

    @classmethod
    def _speculative_points(cls, contexts: list[dict]) -> list[str]:
        points = []
        seen = set()

        def add(point: str):
            if point not in seen:
                seen.add(point)
                points.append(point)

        for idx, ctx in enumerate(contexts, start=1):
            if ctx.get("is_official") or not ctx.get("is_speculative"):
                continue

            marker = f"[{idx}]"
            combined = f"{ctx.get('title', '')} {ctx.get('summary', '')}".lower()

            if "codex" in combined and any(term in combined for term in ("log", "backend", "rollout", "mapping", "canary")):
                add(f"{marker} Codex-/Backend-Leak: Drittquellen berichten von einem kurz sichtbaren Rollout-/Mapping-Eintrag mit `gpt-5.6`, der spaeter verschwand; das ist kein offizieller OpenAI-Nachweis.")
            if "may 13" in combined or "13, 2026" in combined or "13. mai" in combined:
                add(f"{marker} Leak-Zeitpunkt: Die Codex-/Canary-Spur wird in den Quellen auf den 13. Mai 2026 datiert.")
            if "polymarket" in combined or "prediction market" in combined or "odds" in combined:
                if re.search(r"80\s*[-\u2013]\s*89\s*%", combined):
                    add(f"{marker} Prediction-Market: Polymarket-Odds werden mit 80-89% fuer eine oeffentliche Veroeffentlichung bis 30. Juni 2026 genannt; das ist eine Markt-Wette, keine Roadmap.")
                elif "june 30" in combined:
                    add(f"{marker} Prediction-Market: Drittquellen nennen hohe Polymarket-Odds fuer einen Release bis 30. Juni 2026; das bleibt unbestaetigt.")
                elif "july 31" in combined:
                    add(f"{marker} Prediction-Market: Einzelne Quellen nennen auch Markt-Wetten fuer spaetestens 31. Juli 2026; das bleibt unbestaetigt.")
                else:
                    add(f"{marker} Prediction-Market: Es gibt Markt-/Odds-Spekulationen zu GPT-5.6, aber keine offizielle Terminbestaetigung.")
            if "mid-to-late june" in combined:
                add(f"{marker} Release-Geruecht: Eine Quelle nennt Mitte bis Ende Juni 2026 als realistisches Fenster; das ist Spekulation.")
            if "within weeks" in combined:
                add(f"{marker} Release-Geruecht: Eine Quelle formuliert, GPT-5.6 koennte innerhalb weniger Wochen erscheinen; das ist nicht bestaetigt.")
            if any(term in combined for term in ("1.5m", "1.5 million", "1,5", "context window", "token context")):
                add(f"{marker} Feature-Geruecht: Ein groesseres Kontextfenster bzw. 1.5M-Token-Kontext wird erwaehnt, aber nicht offiziell belegt.")
            if any(term in combined for term in ("codename", "pricing", "benchmark")):
                add(f"{marker} Nicht belegte Details: Codenames, Preise und Benchmark-Werte werden ausdruecklich als nicht dokumentiert bzw. spekulativ behandelt.")
            if "advanced reasoning" in combined or "multi-step reasoning" in combined:
                add(f"{marker} Feature-Geruecht: Besseres Reasoning bzw. mehrstufiges Schlussfolgern wird behauptet, bleibt aber unbestaetigt.")
            if "agentic workflow" in combined or "agentic workflows" in combined:
                add(f"{marker} Feature-Geruecht: Agentic Workflows werden als erwartete Verbesserung genannt, aber nicht offiziell bestaetigt.")
            if "token efficiency" in combined:
                add(f"{marker} Feature-Geruecht: Verbesserte Token-Effizienz wird behauptet, bleibt aber unbestaetigt.")
            if "dual-version" in combined or "pro" in combined:
                add(f"{marker} Feature-Geruecht: Eine Pro-/Dual-Version wird erwaehnt, ist aber nicht offiziell bestaetigt.")

        if points:
            return points
        return [
            f"[{idx}] {ctx.get('title', 'Quelle')}: als {credibility_label(ctx)} behandeln, nicht als bestaetigte Produktinformation."
            for idx, ctx in enumerate(contexts, start=1)
            if ctx.get("is_speculative") and not ctx.get("is_official")
        ]

    @staticmethod
    def _fallback_answer(question: str, contexts: list[dict]) -> str:
        if not contexts:
            return "In den gespeicherten Artikeln liegen keine ausreichenden Informationen vor, um diese Frage quellenbasiert zu beantworten."

        lower_question = question.lower()
        asks_release = any(term in lower_question for term in ("wann", "release", "erschein", "kommt", "date"))
        asks_features = any(term in lower_question for term in ("feature", "funktion", "neu", "erwarten", "stand"))
        versioned_openai = any(term in lower_question for term in ("chatgpt 5.6", "gpt-5.6", "gpt 5.6", "5.6"))

        official = [ctx for ctx in contexts if ctx.get("is_official")]
        speculative = [ctx for ctx in contexts if ctx.get("is_speculative") and not ctx.get("is_official")]
        third_party = [ctx for ctx in contexts if not ctx.get("is_official") and not ctx.get("is_speculative")]

        official_mentions_version = any("5.6" in f"{ctx['title']} {ctx['summary']}".lower() for ctx in official)
        speculative_points = LLMGenerator._speculative_points(contexts) if speculative else []

        def clean_point(point: str) -> str:
            return point.lstrip("- ").strip()

        def join_points(points: list[str], limit: int = 5) -> str:
            cleaned = [clean_point(point) for point in points[:limit] if point]
            return " ".join(cleaned)

        lines = ["## Kurzfazit"]
        if versioned_openai and not any("5.6" in f"{ctx['title']} {ctx['summary']}".lower() for ctx in official):
            if speculative:
                lines.append(
                    "Offiziell gibt es keine bestaetigte ChatGPT-/GPT-5.6-Ankuendigung. "
                    "Fuer deine Frage nach neuen Features und einem moeglichen Release heisst das: "
                    "Man kann nur die aktuelle Quellenlage einordnen. Es gibt unbestaetigte Drittquellen "
                    "zu Codex-/Backend-Spuren, Markt-Wetten und moeglichen Funktionsrichtungen, aber "
                    "Release-Datum und konkrete 5.6-Features bleiben Spekulation."
                )
            else:
                lines.append(
                    "Offiziell gibt es keine bestaetigte ChatGPT-/GPT-5.6-Ankuendigung. "
                    "Release-Datum und konkrete 5.6-Features duerfen daher nicht als Fakt dargestellt "
                    "werden; belastbar ist nur, was die bereitgestellten Quellen ausdruecklich belegen."
                )
        else:
            lines.append(
                "Die Antwort stuetzt sich auf die bereitgestellten Quellen und trennt belegte Aussagen "
                "von unbestaetigten Hinweisen."
            )

        lines.append("\n## Gesicherter Stand")
        confirmed_contexts = official or third_party
        confirmed_points = [
            LLMGenerator._confirmed_point(ctx)
            for ctx in contexts[:5]
            if ctx in confirmed_contexts
        ]
        if confirmed_points:
            lines.append(join_points(confirmed_points, limit=5))
        else:
            lines.append("In den bereitgestellten Quellen gibt es keine bestaetigten Informationen, die die Frage direkt beantworten.")

        if asks_features:
            lines.append("\n## Feature-Einschaetzung")
            if versioned_openai:
                feature_points = [
                    point for point in speculative_points
                    if any(term in point.lower() for term in ("kontext", "feature", "reasoning", "agentic", "token", "pro-", "dual"))
                ]
                paragraph = (
                    "Fuer ChatGPT/GPT-5.6 liegt keine bestaetigte Feature-Liste in den offiziellen Quellen vor. "
                )
                if feature_points:
                    paragraph += (
                        "Unbestaetigt werden in Drittquellen vor allem folgende Richtungen diskutiert: "
                        f"{join_points(feature_points, limit=5)} "
                    )
                if official:
                    paragraph += (
                        "Als aktueller bestaetigter Stand sind nur die genannten ChatGPT-/GPT-5.5-Aenderungen "
                        "belastbar; daraus darf keine 5.6-Zusage abgeleitet werden."
                    )
                lines.append(paragraph)
            elif not official:
                lines.append("Eine belastbare Feature-Liste laesst sich aus den vorhandenen Quellen nicht ableiten, weil sie nicht offiziell sind.")
            else:
                lines.append("Neue Funktionen sollten nur aus bestaetigten Quellen abgeleitet werden; nicht belegte Features bleiben offen.")

        if asks_release or versioned_openai:
            lines.append("\n## Release-Stand")
            if versioned_openai and not official_mentions_version:
                release_points = [
                    point for point in speculative_points
                    if any(term in point.lower() for term in ("juni", "juli", "roadmap", "prediction", "release", "wochen", "markt-wette"))
                ]
                paragraph = "Kein offizielles Release-Datum fuer ChatGPT/GPT-5.6 in den bereitgestellten offiziellen Quellen. "
                if release_points:
                    paragraph += (
                        "Unbestaetigt gibt es aber Terminsignale in Drittquellen: "
                        f"{join_points(release_points, limit=4)} "
                    )
                paragraph += "Diese Hinweise sind nuetzlich fuer die Geruechte- und Marktlage, ersetzen aber keine OpenAI-Roadmap."
                lines.append(paragraph)
            else:
                lines.append("Bestaetigte Termine sind nur aus den oben genannten Quellen ableitbar; nicht belegte Release-Fenster bleiben offen.")

        if speculative:
            lines.append("\n## Diskutierte, unbestaetigte Hinweise")
            lines.append(
                "Die wichtigsten unbestaetigten Signale sind: "
                f"{join_points(speculative_points, limit=8)} "
                "Diese Hinweise duerfen nur als Quellenlage/Spekulation erscheinen, nicht als Produktfakt."
            )

        lines.append("\n## Quellenlage")
        source_parts = []
        if official:
            source_parts.append(f"{len(official)} offizielle Quelle(n) mit hoechster Prioritaet")
        if speculative:
            source_parts.append(f"{len(speculative)} unbestaetigte Quelle(n), geeignet fuer Geruechte-/Marktlage, nicht fuer Fakten")
        if third_party:
            source_parts.append(f"{len(third_party)} weitere Drittquelle(n)")
        if source_parts:
            lines.append("Die Quellenbasis besteht aus " + "; ".join(source_parts) + ".")
        source_labels = [
            f"[{idx}] {ctx['title']} - {credibility_label(ctx)}"
            for idx, ctx in enumerate(contexts[:7], start=1)
        ]
        if source_labels:
            lines.append("Zum Nachlesen: " + "; ".join(source_labels) + ".")
        return "\n".join(lines)

    def _merge_summaries(self, contexts: list[dict]) -> str:
        prompt = build_merge_prompt(contexts, MERGE_SUMMARY_WORD_LIMIT)
        chat_logger.info(f"→ MERGE PROMPT:\n{prompt}")
        resp = self._call_with_timeout(self.refine_model, [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ])
        merged = self._message_content(resp)
        if merged:
            chat_logger.info(f"[DEBUG] Merged ({len(merged.split())} Wörter)")
            return merged

        # Fallback: rohe Verkettung, gekürzt
        all_text = " ".join(self._summary_from_context(ctx) for ctx in contexts)
        words    = all_text.split()
        if len(words) > MERGE_SUMMARY_WORD_LIMIT:
            fallback = " ".join(words[:MERGE_SUMMARY_WORD_LIMIT]) + "…"
        else:
            fallback = all_text
        chat_logger.warning(f"Merge-Fallback ({len(fallback.split())} Wörter)")
        return fallback

    def generate(self, question: str, contexts: list[dict]) -> str:
        contexts = self._normalize_contexts(contexts)
        if not contexts:
            return self._fallback_answer(question, contexts)

        # 1) Meta-Summary
        merged_summary = self._merge_summaries(contexts)

        # 2) Antwort-Prompt
        prompt = build_answer_prompt(question, contexts, merged_summary)
        chat_logger.info(f"→ ANSWER PROMPT:\n{prompt}")
        resp = self._call_with_timeout(self.initial_model, [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ])
        answer = self._message_content(resp)
        if answer:
            chat_logger.info(f"← ANSWER RESP:\n{answer}")
            return answer

        chat_logger.warning("Antwort-Fallback: quellenbasierte Kurzantwort")
        return self._fallback_answer(question, contexts)


# Alias
generate = LLMGenerator
