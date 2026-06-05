from retrieval.content_filter import ContentFilter


def test_content_filter_keeps_only_deduped_quality_passages():
    candidates = [
        {
            "title": "OpenAI API Update",
            "link": "https://example.com/openai",
            "text": "OpenAI beschreibt ein neues API-Update mit besseren Tools, klaren Sicherheitsfunktionen und Auswirkungen fuer Entwicklerteams.",
            "score": 0.9,
        },
        {
            "title": "Duplicate",
            "link": "https://example.com/openai",
            "text": "OpenAI beschreibt ein neues API-Update mit besseren Tools.",
            "score": 0.4,
        },
        {
            "title": "Ad",
            "link": "https://example.com/ad",
            "text": "Advertisement. Sign up. Accept cookies. Privacy policy.",
            "score": 0.8,
        },
        {
            "title": "Invalid Link",
            "link": "javascript:alert(1)",
            "text": "Ein ansonsten langer Text wird wegen der ungueltigen Quelle verworfen.",
            "score": 0.7,
        },
    ]

    filtered = ContentFilter(min_words=10).apply(candidates, "Was ist neu bei OpenAI?")

    assert len(filtered) == 1
    assert filtered[0]["link"] == "https://example.com/openai"
