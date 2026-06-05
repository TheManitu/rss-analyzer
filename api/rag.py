# api/rag.py

import logging
import uuid

from flask import Blueprint, current_app, jsonify, render_template, request, session

from api.filters import first_words, truncatewords
from api.utils import extract_topic_from_question, store_question_event
from config import FINAL_CONTEXTS
from logging_service.kafka_config_and_logger import log_answer_quality, log_user_question
from pipeline.source_quality import classify_source
from pipeline.text_quality import clean_article_text, is_useful_article_text, is_valid_source_link, snippet
from retrieval.passage_retriever import PassageRetriever
from storage.topic_tracker import create_topic_table, get_all_topics, update_topic


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api.rag")

rag_bp = Blueprint("rag", __name__)
rag_bp.add_app_template_filter(first_words, "first_words")
rag_bp.add_app_template_filter(truncatewords, "truncatewords")

NO_ANSWER = "Es wurden keine ausreichend relevanten und qualitativ verwertbaren Quellen zu dieser Frage gefunden."
SPECULATIVE_QUERY_TERMS = (
    "leak",
    "geleakt",
    "geleakte",
    "geleakten",
    "geruecht",
    "geruechte",
    "gerücht",
    "gerüchte",
    "rumor",
    "rumour",
    "unbestaetigt",
    "unbestätigt",
    "prediction market",
    "polymarket",
)


@rag_bp.before_app_request
def ensure_session_ids():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())


def _get_retriever():
    return getattr(current_app, "retriever", None) or PassageRetriever(current_app.storage)


def context_limit_for_question(question: str) -> int:
    lowered = (question or "").lower()
    if any(term in lowered for term in SPECULATIVE_QUERY_TERMS):
        return max(FINAL_CONTEXTS, 7)
    return FINAL_CONTEXTS


def _filter_and_rank(question: str, passages: list[dict]) -> list[dict]:
    filtered = passages or []
    filterer = getattr(current_app, "filterer", None)
    if filterer is not None:
        try:
            filtered = filterer.filter(question, filtered)
        except TypeError:
            filtered = filterer.filter(filtered)
        except Exception:
            logger.exception("ContentFilter fehlgeschlagen:")
            filtered = passages or []

    ranker = getattr(current_app, "ranker", None)
    if ranker is not None:
        try:
            return ranker.rank(question, filtered)
        except Exception:
            logger.exception("Ranker fehlgeschlagen:")
    return sorted(filtered, key=lambda item: item.get("score", 0), reverse=True)


def _article_row(link: str):
    con = None
    try:
        try:
            con = current_app.storage.connect(read_only=True)
        except TypeError:
            con = current_app.storage.connect()
        return con.execute(
            """
            SELECT title, summary, content, description
            FROM articles
            WHERE link = ?
            """,
            (link,),
        ).fetchone()
    except Exception:
        logger.exception("Artikelkontext konnte nicht geladen werden: %s", link)
        return None
    finally:
        if con is not None:
            con.close()


def build_contexts_from_passages(passages: list[dict], limit: int = FINAL_CONTEXTS) -> list[dict]:
    contexts = []
    seen = set()

    for passage in passages or []:
        link = (passage.get("link") or "").strip()
        if not link or link in seen or not is_valid_source_link(link):
            continue
        seen.add(link)

        row = _article_row(link)
        row_title = row[0] if row else None
        row_summary = row[1] if row else None
        row_content = row[2] if row else None
        row_description = row[3] if row else None

        title = clean_article_text(row_title or passage.get("title") or "Ohne Titel")
        summary = clean_article_text(
            row_summary
            or passage.get("summary")
            or passage.get("text")
            or passage.get("section_text")
            or row_content
            or row_description
            or ""
        )
        if not is_useful_article_text(summary, min_words=10):
            continue

        source_quality = classify_source(link, title, summary)
        contexts.append({
            "title": title,
            "summary": summary,
            "link": link,
            "score": passage.get("score", 0),
            **source_quality,
        })
        if len(contexts) >= limit * 2:
            break

    contexts.sort(
        key=lambda ctx: (
            ctx.get("credibility_score", 0),
            ctx.get("score", 0),
        ),
        reverse=True,
    )
    return contexts[:limit]


def sources_from_contexts(contexts: list[dict]) -> list[dict]:
    return [{
        "title": ctx["title"],
        "link": ctx["link"],
        "snippet": snippet(ctx["summary"], 220),
        "score": ctx.get("score", 0),
        "source_type": ctx.get("source_type"),
        "credibility_score": ctx.get("credibility_score", 0),
        "is_official": ctx.get("is_official", False),
        "is_speculative": ctx.get("is_speculative", False),
    } for ctx in contexts]


def answer_question(question: str) -> tuple[str, list[dict], list[dict], list[dict], str, dict]:
    topic = extract_topic_from_question(question)
    try:
        passages = _get_retriever().retrieve(question) or []
    except Exception:
        logger.exception("Fehler bei PassageRetriever:")
        passages = []

    ranked = _filter_and_rank(question, passages)
    contexts = build_contexts_from_passages(ranked, limit=context_limit_for_question(question))
    if not contexts:
        return NO_ANSWER, [], [], passages, topic, {"score": 0.0, "flag": True}

    try:
        answer = current_app.generator.generate(question, contexts=contexts)
    except Exception:
        logger.exception("LLM-Fehler:")
        answer = "Entschuldigung, aktuell kann keine quellenbasierte Antwort generiert werden."

    try:
        eval_res = current_app.evaluator.evaluate(answer, contexts)
    except Exception:
        logger.exception("Antwort-Evaluierung fehlgeschlagen:")
        eval_res = {"score": 0.0, "flag": True}

    return answer, sources_from_contexts(contexts), contexts, passages, topic, eval_res


def log_question_result(question: str, topic: str, passages: list[dict], contexts: list[dict], eval_res: dict):
    used_links = [ctx["link"] for ctx in contexts]
    try:
        log_user_question(question, topic, len(passages), used_links, session["user_id"], session["session_id"])
    except Exception:
        logger.exception("Question-Logging fehlgeschlagen:")
    try:
        store_question_event(question, topic, len(contexts))
    except Exception:
        logger.exception("Question-Event konnte nicht gespeichert werden:")
    try:
        update_topic(topic, delta=1)
    except Exception:
        logger.exception("Topic-Tracking fehlgeschlagen:")
    try:
        log_answer_quality(
            used_article_ids=used_links,
            quality_score=eval_res.get("score", 0.0),
            flag=eval_res.get("flag", True),
            user_id=session["user_id"],
            session_id=session["session_id"],
        )
    except Exception:
        logger.exception("Answer-Quality-Logging fehlgeschlagen:")


@rag_bp.route("/", methods=["GET", "POST"])
def index():
    create_topic_table()
    answer, sources = "", []
    time_filter = request.args.get("time_filter", "14_days")

    if request.method == "POST":
        q = request.form.get("question", "").strip()
        if not q:
            answer = "Bitte eine Frage eingeben."
        else:
            answer, sources, contexts, passages, topic, eval_res = answer_question(q)
            log_question_result(q, topic, passages, contexts, eval_res)

    try:
        top_articles = current_app.storage.get_all_articles(time_filter="today")
        articles = current_app.storage.get_all_articles(time_filter=time_filter)
        counts = {
            "today": len(current_app.storage.get_all_articles("today")),
            "3_days": len(current_app.storage.get_all_articles("3_days")),
            "7_days": len(current_app.storage.get_all_articles("7_days")),
            "14_days": len(current_app.storage.get_all_articles("14_days")),
        }
        topics = get_all_topics()
    except Exception:
        logger.exception("Fehler beim Laden der Uebersichtsdaten:")
        top_articles, articles, counts, topics = [], [], {}, []

    return render_template(
        "index.html",
        answer=answer,
        sources=sources,
        top_articles=top_articles,
        articles=articles,
        counts=counts,
        topics=topics,
        time_filter=time_filter,
    )


@rag_bp.route("/search", methods=["POST"])
def api_search():
    data = request.get_json() or {}
    q = data.get("question", "").strip()
    if not q:
        return jsonify(answer="Bitte eine Frage eingeben.", sources=[]), 400

    answer, sources, contexts, passages, topic, eval_res = answer_question(q)
    log_question_result(q, topic, passages, contexts, eval_res)
    return jsonify(answer=answer, sources=sources), 200
