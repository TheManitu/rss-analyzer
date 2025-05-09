# app/api/api.py

import os
import logging
from flask import Flask, render_template, send_from_directory, session
from prometheus_client import Counter, Gauge, Histogram

from ingestion.rss_ingest import RSSIngest
from storage.duckdb_storage import DuckDBStorage
from storage.topic_tracker import create_topic_table, update_topic, get_all_topics
from retrieval.passage_retriever import PassageRetriever
from retrieval.content_filter import ContentFilter
from ranking.cross_encoder_ranker import CrossEncoderRanker
from generation.llm_generator import LLMGenerator
from evaluation.quality_evaluator import QualityEvaluator

from api.rag import rag_bp
from api.metrics import metrics_bp  # falls ihr Metrics-Blueprint nutzt
from api.filters import first_words, truncatewords

from config import (
    RSS_FEEDS,
    TOPIC_MAPPING,
    LLM_MODEL_INITIAL,
    LLM_MODEL_REFINE,
    FINAL_CONTEXTS
)

def create_app():
    # Basis-Pfade
    base_dir      = os.path.abspath(os.path.dirname(__file__))
    templates_dir = os.path.join(base_dir, '..', 'templates')
    static_dir    = os.path.join(base_dir, '..', 'static')

    app = Flask(
        __name__,
        template_folder=templates_dir,
        static_folder=static_dir
    )
    app.secret_key = os.getenv("FLASK_SECRET", "change_me")

    # Expose key config vars to Flask config
    app.config["LLM_MODEL_INITIAL"] = LLM_MODEL_INITIAL   # Default "llama2:7b" :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}
    app.config["LLM_MODEL_REFINE"]  = LLM_MODEL_REFINE
    app.config["FINAL_CONTEXTS"]     = FINAL_CONTEXTS

    # Topic-Tabelle sicherstellen
    create_topic_table()

    # Storage & Ingestor
    app.storage  = DuckDBStorage()
    app.ingestor = RSSIngest(feeds=RSS_FEEDS, storage_client=app.storage)

    # RAG-Pipeline-Komponenten
    app.retriever = PassageRetriever(app.storage)
    app.filterer  = ContentFilter(topic_mapping=TOPIC_MAPPING)
    app.ranker    = CrossEncoderRanker()
    app.generator = LLMGenerator()
    app.evaluator = QualityEvaluator(threshold=0.5)

    # Prometheus-Metriken
    app.Q_COUNT    = Counter("rss_questions_total", "Total number of questions processed")
    app.ZERO_CAND  = Gauge("rss_zero_candidate_ratio", "Ratio of zero-candidate questions")
    app.DB_LATENCY = Histogram("duckdb_query_seconds", "DuckDB query latency in seconds")

    # Jinja-Filter
    app.add_template_filter(first_words,   "first_words")
    app.add_template_filter(truncatewords, "truncatewords")

    # Blueprints
    app.register_blueprint(rag_bp)
    app.register_blueprint(metrics_bp)

    # Favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico')

    # Zusatz-Routen
    @app.route('/audit')
    def audit():
        audit = app.storage.execute("SELECT link, topic, timestamp FROM question_events")
        return render_template('audit.html', audit=audit)

    @app.route('/analytics')
    def analytics():
        # Beispiel: Top-5 Fragen aus question_events
        con = app.storage.connect(read_only=True)
        top_q = con.execute("""
            SELECT question, COUNT(*) AS cnt
            FROM question_events
            GROUP BY question
            ORDER BY cnt DESC
            LIMIT 5
        """).fetchall()
        hourly = con.execute("""
            SELECT EXTRACT(hour FROM timestamp) AS hr, COUNT(*) AS cnt
            FROM question_events
            GROUP BY hr
            ORDER BY hr
        """).fetchall()
        top_views = con.execute("""
            SELECT link, view_count
            FROM article_metrics
            ORDER BY view_count DESC
            LIMIT 5
        """).fetchall()
        con.close()
        return render_template(
            'analytics.html',
            questions_total=app.Q_COUNT._value.get(),  # aktueller Zählerstand
            top_questions=top_q,
            questions_by_hour=hourly,
            top_article_views=top_views
        )

    @app.route('/dashboard')
    def dashboard():
        topics = get_all_topics()
        return render_template('dashboard.html', topics=topics)

    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    create_app().run(host="0.0.0.0", port=5000, debug=True)
