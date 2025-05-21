# tests/test_passage_retriever.py

import pytest
from flask import Flask
from storage.duckdb_storage import DuckDBStorage
from retrieval.passage_retriever import PassageRetriever
from config import SYN_WEIGHT, TOPIC_THRESHOLD_FACTOR, TOPIC_TITLE_WEIGHT

@pytest.fixture
def app():
    """Minimal-Flask-App für current_app.config."""
    app = Flask(__name__)
    app.config['SYN_WEIGHT'] = SYN_WEIGHT
    app.config['TOPIC_THRESHOLD_FACTOR'] = TOPIC_THRESHOLD_FACTOR
    app.config['TOPIC_TITLE_WEIGHT'] = TOPIC_TITLE_WEIGHT
    return app

@pytest.fixture
def temp_storage(tmp_path):
    """Erzeuge eine temporäre DuckDB mit genau einem Kubernetes-Artikel."""
    db_file = tmp_path / "test.duckdb"
    storage = DuckDBStorage(db_path=str(db_file))
    con = storage.connect()
    con.execute("""
        INSERT INTO articles
          (title, link, description, content, summary, published, topic, importance)
        VALUES
          (
            'Test Kubernetes',
            'http://a',
            'Kurzbeschreibung',
            'Kubernetes ist ein Container-Orchestrator.',
            'Kubernetes ist …',
            CURRENT_DATE,
            'Cloud Computing & Infrastruktur',
            1.0
          )
    """)
    con.close()
    return storage

def test_retrieve_kubernetes(app, temp_storage):
    retriever = PassageRetriever(temp_storage)
    # Wichtig: App-Context aktivieren, damit extract_topic... current_app.config nutzt
    with app.app_context():
        results = retriever.retrieve("Kubernetes Features")
        assert results, "Erwartet mindestens eine Passage"
        for p in results:
            text = p['text'].lower()
            title = (p.get('title') or '').lower()
            assert 'kubernetes' in text or 'kubernetes' in title, \
                f"Passage oder Titel muss 'Kubernetes' enthalten, war: {p}"

