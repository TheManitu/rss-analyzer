from ingestion import rss_ingest
from ingestion.rss_ingest import RSSIngest, normalize_feed_link
from storage import duckdb_storage
from storage.duckdb_storage import DuckDBStorage


class FeedEntry(dict):
    def __getattr__(self, name):
        return self[name]


class FakeResponse:
    text = """
    <html>
      <h1>GPT-5.5 in ChatGPT</h1>
      <article>
        <p>GPT-5.5 Instant in ChatGPT is the default model for logged-in users and improves info seeking, technical writing, translation, and everyday work.</p>
        <p>GPT-5.5 Thinking can reason on hard tasks, keep track of prior work, and provide a short preamble before it starts reasoning.</p>
        <p>GPT-5.5 Pro is the highest-capability option for long-running workflows, while official notes do not announce GPT-5.6.</p>
        <p>GPT-5.5 supports tools including web search, data analysis, image analysis, file analysis, image generation, memory, and custom instructions depending on mode.</p>
        <p>Official availability details describe Free, Plus, Go, Pro, Business, Enterprise, and Edu access patterns, including usage limits, context windows, and model picker behavior for paid tiers.</p>
        <p>The document explains that older conversations may continue on current GPT-5.5 equivalents and that legacy models can remain available for a limited period after newer launches.</p>
        <p>These details are useful for answering user questions because they separate confirmed product behavior from unconfirmed future model rumors.</p>
      </article>
    </html>
    """

    def raise_for_status(self):
        pass


def test_trusted_sources_are_ingested_as_openai_articles(tmp_path, monkeypatch):
    monkeypatch.setattr(rss_ingest, "create_topic_table", lambda: None)
    monkeypatch.setattr(rss_ingest, "update_topic", lambda *args, **kwargs: None)
    monkeypatch.setattr(rss_ingest.requests, "get", lambda *args, **kwargs: FakeResponse())

    storage = DuckDBStorage(db_path=str(tmp_path / "trusted.duckdb"))
    ingester = RSSIngest(
        feeds=[],
        storage_client=storage,
        trusted_sources=["https://help.openai.com/en/articles/11909943-gpt-5-5-in-chatgpt"],
    )

    assert ingester._ingest_trusted_sources() == 1

    articles = storage.get_all_articles()
    assert len(articles) == 1
    assert articles[0]["topic"] == "OpenAI & GPT-Modelle"
    assert articles[0]["importance"] == 10
    assert articles[0]["link"].startswith("https://help.openai.com/")


def test_bing_news_redirect_is_decoded_to_original_source():
    link = (
        "https://www.bing.com/news/apiclick.aspx?"
        "url=https%3a%2f%2fwww.geeky-gadgets.com%2fgpt-5-6-june-2026-release%2f"
        "&format=rss"
    )

    assert normalize_feed_link(link) == "https://www.geeky-gadgets.com/gpt-5-6-june-2026-release/"


def test_discovery_feed_articles_are_stored_as_openai_topic(tmp_path, monkeypatch):
    discovery_feed = "https://www.bing.com/news/search?q=%22GPT-5.6%22%20%22OpenAI%22&format=rss"
    original_url = "https://www.geeky-gadgets.com/gpt-5-6-june-2026-release/"
    redirect_url = (
        "https://www.bing.com/news/apiclick.aspx?"
        "url=https%3a%2f%2fwww.geeky-gadgets.com%2fgpt-5-6-june-2026-release%2f"
    )

    monkeypatch.setattr(rss_ingest, "create_topic_table", lambda: None)
    monkeypatch.setattr(rss_ingest, "update_topic", lambda *args, **kwargs: None)
    monkeypatch.setattr(duckdb_storage.IngestionFilter, "validate", lambda *args, **kwargs: (True, "OK"))
    monkeypatch.setattr(
        rss_ingest.feedparser,
        "parse",
        lambda url: type("Feed", (), {
            "entries": [
                FeedEntry(
                    title="What to Expect from OpenAI's GPT-5.6 Release",
                    link=redirect_url,
                    summary="OpenAI GPT-5.6 is discussed as an unconfirmed release topic.",
                    published_parsed=(2026, 6, 2, 12, 0, 0, 0, 0, 0),
                )
            ]
        })(),
    )

    async def fake_fetch_all(self, urls):
        assert urls == [original_url]
        return [FakeResponse.text]

    monkeypatch.setattr(RSSIngest, "_fetch_all", fake_fetch_all)

    storage = DuckDBStorage(db_path=str(tmp_path / "discovery.duckdb"))
    ingester = RSSIngest(
        feeds=[discovery_feed],
        discovery_feeds=[discovery_feed],
        trusted_sources=[],
        discovery_sources=[],
        storage_client=storage,
    )

    ingester.run()

    articles = storage.get_all_articles()
    assert len(articles) == 1
    assert articles[0]["link"] == original_url
    assert articles[0]["topic"] == "OpenAI & GPT-Modelle"
    assert articles[0]["importance"] == 4
