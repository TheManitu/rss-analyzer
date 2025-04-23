# api/app.py

import os, re, duckdb
from flask import Flask, render_template, request, jsonify, redirect, url_for
from config import DB_PATH, TOPIC_MAPPING, RSS_FEEDS
from ingestion.rss_ingest import RSSIngest
from storage.duckdb_storage import DuckDBStorage
from storage.topic_tracker import create_topic_table, update_topic, get_all_topics, print_topic_overview
from retrieval.hybrid_retrieval import HybridRetrieval
from filter.content_filter import ContentFilter
from ranking.cross_encoder_ranker import CrossEncoderRanker
from generation.llm_generator import LLMGenerator
from evaluation.quality_evaluator import QualityEvaluator
from logging_service.logger import EventLogger

BASE_DIR     = os.path.abspath(os.path.dirname(__file__) + "/..")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR   = os.path.join(BASE_DIR, "static")
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# Module
storage   = DuckDBStorage(db_path=DB_PATH)
ingestor  = RSSIngest(feeds=RSS_FEEDS, storage_client=storage)
retriever = HybridRetrieval(storage)
filterer  = ContentFilter(topic_mapping=TOPIC_MAPPING)
ranker    = CrossEncoderRanker()
generator = LLMGenerator()
evaluator = QualityEvaluator(threshold=1.0)
logger    = EventLogger()

@app.template_filter()
def first_words(s, num_words=250):
    if not s: return ""
    clean = re.sub(r"<.*?>", "", s)
    words = clean.split()
    return " ".join(words[:num_words]) + "…" if len(words)>num_words else clean

@app.template_filter()
def truncatewords(s, num_words=500):
    if not s: return ""
    words = s.split()
    return " ".join(words[:num_words]) + "…" if len(words)>num_words else s

def extract_topic_from_question(question: str) -> str:
    q = question.lower()
    for topic, data in TOPIC_MAPPING.items():
        for kw in data.get("keywords", []):
            if kw in q:
                return topic
    return "Allgemein"

@app.route("/", methods=["GET", "POST"])
def index():
    answer = ""
    sources = []
    if request.method == "POST":
        q = request.form.get("question","").strip()
        if q:
            topic = extract_topic_from_question(q)
            logger.log_question(q, topic)
            update_topic(topic, delta=1)

            # Retrieval + Ranking
            cands = retriever.retrieve(q)
            filt  = filterer.apply(cands, q)
            top   = ranker.rerank(q, filt)[:5]  # nur 5 verwenden

            # Generierung
            answer = generator.generate(q, top)
            eval_res = evaluator.evaluate(answer, top)
            if eval_res.get("flag"):
                app.logger.warning(f"Qualitätscheck niedrig: {eval_res['score']:.2f}")

            # Quellen für UI: title + link
            sources = [
                {"title": c["title"], "link": c["link"]}
                for c in top
            ]

    articles = storage.fetch_passages(time_filter=request.args.get("time_filter","14_days"))
    return render_template("index.html",
                           articles=articles,
                           answer=answer,
                           sources=sources)

@app.route("/search", methods=["POST"])
def api_search():
    data = request.get_json() or {}
    q = data.get("question","").strip()
    if not q:
        return jsonify({"answer":"Bitte Frage eingeben.","sources":[]}), 400

    topic = extract_topic_from_question(q)
    logger.log_question(q, topic)
    update_topic(topic, delta=1)

    cands = retriever.retrieve(q)
    filt  = filterer.apply(cands, q)
    top   = ranker.rerank(q, filt)[:5]

    answer = generator.generate(q, top)
    eval_res = evaluator.evaluate(answer, top)
    if eval_res.get("flag"):
        app.logger.warning(f"Qualitätscheck niedrig: {eval_res['score']:.2f}")

    sources = [
        {"title": c["title"], "link": c["link"]}
        for c in top
    ]
    return jsonify({"answer": answer, "sources": sources})

# Dashboard, Analytics, Audit unverändert …
@app.route("/dashboard")
def dashboard():
    topics = get_all_topics()
    return render_template("dashboard.html", topics=topics)

@app.route("/analytics")
def analytics():
    return render_template("analytics.html", questions=[])

@app.route("/audit")
def audit():
    con = duckdb.connect(DB_PATH, read_only=True)
    rows = con.execute(
        "SELECT article_id, event_type, timestamp "
        "FROM read_parquet('data/audit/article_history/*.parquet') "
        "ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    con.close()
    return render_template("audit.html", audit=rows)

@app.route("/redirect_to_dashboard")
def redirect_dash():
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    print_topic_overview()
    app.run(host="0.0.0.0", port=5000, debug=True)
