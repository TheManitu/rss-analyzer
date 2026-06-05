from pathlib import Path

from config import MAX_FEED_ENTRIES_PER_FEED, RSS_FEEDS


def test_refresh_uses_full_default_ingestion_feed_set():
    api_source = Path("api/api.py").read_text(encoding="utf-8")

    assert "RSSIngest(storage_client=storage).run()" in api_source
    assert "RSSIngest(feeds=RSS_FEEDS" not in api_source


def test_rss_feed_configuration_has_current_source_breadth():
    expected_feeds = {
        "https://research.google/blog/rss/",
        "https://blogs.nvidia.com/feed/",
        "https://www.microsoft.com/en-us/research/feed/",
        "https://www.artificialintelligence-news.com/feed/",
        "https://www.the-decoder.com/feed/",
        "https://www.golem.de/rss.php?feed=RSS2.0",
        "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
        "https://www.theregister.com/software/ai_ml/headlines.atom",
        "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss",
    }

    assert len(RSS_FEEDS) >= 25
    assert expected_feeds.issubset(set(RSS_FEEDS))


def test_ingestion_limits_each_feed_to_fresh_entries():
    ingest_source = Path("ingestion/rss_ingest.py").read_text(encoding="utf-8")

    assert MAX_FEED_ENTRIES_PER_FEED >= 10
    assert "feed.entries[:MAX_FEED_ENTRIES_PER_FEED]" in ingest_source
