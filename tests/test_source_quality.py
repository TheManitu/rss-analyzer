from pipeline.source_quality import classify_source, credibility_label


def test_classify_official_openai_source():
    source = classify_source(
        "https://help.openai.com/en/articles/11909943-gpt-55-in-chatgpt",
        "GPT-5.5 in ChatGPT",
        "GPT-5.5 Instant in ChatGPT is the default for all logged-in users.",
    )

    assert source["source_type"] == "official"
    assert source["is_official"] is True
    assert source["is_speculative"] is False
    assert source["credibility_score"] == 1.0


def test_classify_rumor_source_as_unconfirmed():
    source = classify_source(
        "https://example.com/gpt-5-6-release-date",
        "GPT-5.6 release date leak",
        "A rumor says GPT-5.6 could launch in June with a larger context window.",
    )

    assert source["source_type"] == "speculative"
    assert source["is_official"] is False
    assert source["is_speculative"] is True
    assert credibility_label(source) == "unbestaetigte Quelle"


def test_classify_prediction_market_and_canary_log_as_unconfirmed():
    source = classify_source(
        "https://example.com/gpt-5-6",
        "GPT-5.6 canary log and prediction market odds",
        "Codex log signals are discussed, but there is no official confirmation.",
    )

    assert source["source_type"] == "speculative"
    assert source["is_speculative"] is True
