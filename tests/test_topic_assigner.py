from pipeline.topic_assignment import TopicAssigner


def test_topic_assigner_uses_rule_matches(tmp_path):
    assigner = TopicAssigner(db_path=str(tmp_path / "topics.duckdb"))

    cases = [
        (
            {"title": "Deep Learning Trends", "content": "Neuronale Netze, KI und LLMs verbessern Modelle."},
            "Künstliche Intelligenz & Maschinelles Lernen",
        ),
        (
            {"title": "AWS SageMaker Update", "content": "AWS AI, SageMaker, Polly und Bedrock erhalten neue Funktionen."},
            "Amazon AWS AI",
        ),
        (
            {"title": "Unbekanntes Thema", "content": "Lorem ipsum dolor sit amet ohne klare technische Signale."},
            "Allgemein",
        ),
    ]

    for article, expected in cases:
        assert assigner.assign_topic(article["title"], article["content"]) == expected
