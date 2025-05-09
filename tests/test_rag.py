import pytest
from flask import Flask
from api.rag import rag_bp

@pytest.fixture
def client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'

    # Dummy mocks (müssen ggf. angepasst werden)
    app.storage = type('MockStorage', (), {
        'get_all_articles': lambda self, **kwargs: [],
        'fetch_passages': lambda self, **kwargs: [],
        'get_article_keywords': lambda self, link: [],
    })()

    app.generator = type('MockGen', (), {'generate': lambda self, q, c: "Antwort"})()
    app.evaluator = type('MockEval', (), {'evaluate': lambda self, a, c: {"score": 1.0, "flag": False}})()
    app.retriever = type('MockRet', (), {'retrieve': lambda self, q: []})()
    app.filterer = type('MockFilt', (), {'apply': lambda self, c, q: c})()
    app.ranker = type('MockRank', (), {'rerank': lambda self, q, c: c})()

    app.register_blueprint(rag_bp)
    
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_index_get(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Quellen" in res.data or b"Antwort" in res.data


def test_index_post_no_question(client):
    res = client.post("/", data={"question": ""})
    assert res.status_code == 200
    assert b"Bitte eine Frage eingeben" in res.data


def test_search_post_valid(client):
    import json
    res = client.post("/search", data=json.dumps({"question": "Was gibt es Neues?"}),
                      content_type='application/json')
    assert res.status_code == 200
    data = res.get_json()
    assert "answer" in data
    assert "sources" in data


def test_search_post_empty(client):
    import json
    res = client.post("/search", data=json.dumps({"question": ""}),
                      content_type='application/json')
    assert res.status_code == 400


def test_search_post_invalid_json(client):
    res = client.post("/search", data="nicht-json",
                      content_type='application/json')
    assert res.status_code == 400
