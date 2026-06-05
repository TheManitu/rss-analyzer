# tests/test_passage_retriever.py

import pytest
from flask import Flask
from storage.duckdb_storage import DuckDBStorage
from retrieval.passage_retriever import PassageRetriever, _diverse_by_link
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
            'Kubernetes ist ein Container-Orchestrator fuer Cloud-Anwendungen. Es verwaltet Pods, Deployments, Services und skaliert Workloads in Clustern. Neue Kubernetes Features verbessern Sicherheit, Automatisierung und Infrastruktur-Betrieb.',
            'Kubernetes verwaltet Container, Pods, Deployments und Services in Cloud-Clustern. Neue Features verbessern Sicherheit, Automatisierung und Infrastruktur-Betrieb.',
            CURRENT_DATE,
            'Allgemein',
            1.0
          ),
          (
            'Elektroauto Kosten',
            'http://b',
            'Kurzbeschreibung',
            'Elektroautos verursachen im Sommer unterschiedliche Kosten je nach Stromtarif, Verbrauch, Ladepunkt und Fahrprofil. Der Artikel vergleicht mehrere Modelle und erklaert Preisunterschiede.',
            'Elektroautos haben je nach Stromtarif, Verbrauch und Ladepunkt sehr unterschiedliche Kosten. Der Artikel erklaert Preisunterschiede fuer Autofahrer.',
            CURRENT_DATE,
            'Allgemein',
            10.0
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


def test_retrieve_versioned_model_name(app, tmp_path):
    db_file = tmp_path / "versioned.duckdb"
    storage = DuckDBStorage(db_path=str(db_file))
    con = storage.connect()
    con.execute("""
        INSERT INTO articles
          (title, link, description, content, summary, published, topic, importance)
        VALUES
          (
            'GPT-5.6 Geruechte und offizieller Stand',
            'https://example.com/gpt-5-6',
            'Kurzbeschreibung',
            'GPT-5.6 wird in diesem Artikel als unbestaetigtes Thema diskutiert. Der Text trennt Geruechte von offiziellen OpenAI-Informationen und nennt keine bestaetigte Veroeffentlichung.',
            'GPT-5.6 ist laut Artikel unbestaetigt. Es gibt keine offizielle Veroeffentlichung und keine bestaetigten Features.',
            CURRENT_DATE,
            'OpenAI & GPT-Modelle',
            1.0
          ),
          (
            'Elektroauto Kosten',
            'https://example.com/cars',
            'Kurzbeschreibung',
            'Elektroautos verursachen im Sommer unterschiedliche Kosten je nach Stromtarif, Verbrauch, Ladepunkt und Fahrprofil.',
            'Elektroautos haben je nach Stromtarif unterschiedliche Kosten.',
            CURRENT_DATE,
            'Allgemein',
            10.0
          )
    """)
    con.close()

    retriever = PassageRetriever(storage)
    with app.app_context():
        results = retriever.retrieve("Was gibt es Neues zu GPT-5.6?")

    assert results
    assert results[0]["link"] == "https://example.com/gpt-5-6"


def test_diverse_by_link_prefers_unique_sources():
    results = [
        {"link": "https://example.com/a", "score": 1.0},
        {"link": "https://example.com/a", "score": 0.9},
        {"link": "https://example.com/b", "score": 0.8},
    ]

    diverse = _diverse_by_link(results, 2)

    assert [item["link"] for item in diverse] == [
        "https://example.com/a",
        "https://example.com/b",
    ]

