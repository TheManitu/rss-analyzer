# ingestion/rss_ingest.py

import logging
import warnings
from bs4 import MarkupResemblesLocatorWarning
# unterdrückt die Warnung, wenn BeautifulSoup pure URLs sieht
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

import asyncio
import aiohttp
import subprocess
import re
import requests

from html import unescape
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urlparse

import feedparser
from bs4 import BeautifulSoup

from config import (
    RSS_FEEDS,
    DB_PATH,
    MIN_ARTICLE_WORDS,
    MAX_FETCH_WORKERS,
    MAX_FEED_ENTRIES_PER_FEED,
    TRUSTED_SOURCE_URLS,
    DISCOVERY_RSS_FEEDS,
    DISCOVERY_SOURCE_URLS,
)
from storage.duckdb_storage import DuckDBStorage
from storage.topic_tracker import create_topic_table, update_topic
from pipeline.text_quality import clean_article_text, is_useful_article_text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SKIP_SCRAPE_DOMAINS = {
    'huggingface.co/blog',
    # ggf. weitere Domains …
}


def clean_text(text: str) -> str:
    """Entfernt HTML-Tags, HTML-Entities und normalisiert Whitespace."""
    return clean_article_text(text or "")


def normalize_feed_link(link: str) -> str:
    """Return the original article URL for RSS search-result redirect links."""
    value = (link or "").strip()
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.endswith("bing.com") and "apiclick" in parsed.path:
        target = parse_qs(parsed.query).get("url", [""])[0]
        if target:
            return unquote(target)
    return value


def reader_url(url: str) -> str:
    return f"https://r.jina.ai/http://r.jina.ai/http://{url}"


def fetch_url_text(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return resp.text
    except Exception:
        resp = requests.get(reader_url(url), timeout=max(timeout, 25), headers=headers)
        resp.raise_for_status()
        return resp.text


def extract_article_text(html: str) -> str:
    """Extract the likely article body while avoiding common page chrome."""
    if "<" not in (html or "") and "Title:" in (html or "")[:200]:
        lines = [
            line for line in (html or "").splitlines()
            if not line.startswith(("Title:", "URL Source:", "Markdown Content:"))
        ]
        return clean_article_text("\n".join(lines))

    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button", "noscript", "svg", "iframe"]):
        tag.decompose()

    candidates = soup.select("article, main, [role='main'], .article, .post, .entry-content")
    root = max(candidates, key=lambda node: len(node.get_text(" ", strip=True)), default=soup)
    parts = []
    for node in root.find_all(["p", "li", "h2", "h3"]):
        text = clean_article_text(node.get_text(" ", strip=True))
        if len(text.split()) >= 5:
            parts.append(text)
    return clean_article_text("\n".join(parts) or root.get_text(" ", strip=True))


def extract_title(html: str, fallback: str) -> str:
    if "<" not in (html or "") and "Title:" in (html or "")[:200]:
        for line in (html or "").splitlines():
            if line.startswith("Title:"):
                return clean_text(line.replace("Title:", "", 1).strip()) or fallback
    soup = BeautifulSoup(html or "", "html.parser")
    for selector in ("h1", "title"):
        node = soup.select_one(selector)
        if node:
            title = clean_text(node.get_text(" ", strip=True))
            if title:
                return title
    return fallback


def summarize(text: str, sentences: int = 3) -> str:
    """Extraktive Zusammenfassung via Sumy, Fallback auf naive Satz-Trennung."""
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.text_rank import TextRankSummarizer

        parser = PlaintextParser.from_string(text, Tokenizer("german"))
        summarizer = TextRankSummarizer()
        summary = summarizer(parser.document, sentences)
        return " ".join(str(s) for s in summary)
    except Exception:
        parts = re.split(r'(?<=[\.!?])\s+', text)
        return " ".join(parts[:sentences])


def translate_de_en(text: str) -> str:
    """Regelbasierte Deutsch→Englisch-Übersetzung mit Apertium."""
    try:
        proc = subprocess.run(
            ["apertium", "-u", "de-en"],
            input=text,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() or ""
    except Exception:
        return ""


class RSSIngest:
    """
    Lädt alle RSS_FEEDS, scrapt Einträge (mit Fallbacks), 
    wirft keine Exceptions, filtert nur < MIN_ARTICLE_WORDS.
    """

    def __init__(
        self,
        feeds=None,
        storage_client=None,
        trusted_sources=None,
        discovery_sources=None,
        discovery_feeds=None,
    ):
        self.discovery_feeds = DISCOVERY_RSS_FEEDS if discovery_feeds is None else discovery_feeds
        self.feeds   = (RSS_FEEDS + self.discovery_feeds) if feeds is None else feeds
        self.storage = storage_client or DuckDBStorage(db_path=DB_PATH)
        self.trusted_sources = trusted_sources if trusted_sources is not None else TRUSTED_SOURCE_URLS
        self.discovery_sources = discovery_sources if discovery_sources is not None else DISCOVERY_SOURCE_URLS
        create_topic_table()
        self.existing = set(self.storage.get_all_links())

    async def _fetch(self, session, url):
        try:
            async with session.get(url, timeout=10,
                                   headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception:
            logger.warning(f"Fetch fehlgeschlagen für {url}")
        return None

    async def _fetch_all(self, urls):
        connector = aiohttp.TCPConnector(limit_per_host=MAX_FETCH_WORKERS)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self._fetch(session, u) for u in urls]
            return await asyncio.gather(*tasks)

    def _ingest_source_urls(self, urls: list[str], topic: str, importance: int, label: str) -> int:
        saved = 0
        for url in urls:
            if not url or url in self.existing:
                continue
            try:
                html = fetch_url_text(url)
                title = extract_title(html, url)
                content = extract_article_text(html)
                if not is_useful_article_text(content, min_words=MIN_ARTICLE_WORDS):
                    logger.info(f"Verwerfe {label} {url}: Textqualitaet nicht ausreichend")
                    continue
                summary = summarize(content)
                if self.storage.insert_article(
                    title=title,
                    link=url,
                    description=summary,
                    content=content,
                    summary=summary,
                    translation="",
                    published=datetime.now(timezone.utc).date(),
                    topic=topic,
                    importance=importance,
                    relevance=0
                ):
                    update_topic(topic, delta=1)
                    self.existing.add(url)
                    saved += 1
            except Exception as exc:
                logger.warning(f"{label} {url} konnte nicht geladen werden: {exc}")
        return saved

    def _ingest_trusted_sources(self) -> int:
        return self._ingest_source_urls(
            self.trusted_sources,
            topic="OpenAI & GPT-Modelle",
            importance=10,
            label="Trusted Source",
        )

    def _ingest_discovery_sources(self) -> int:
        return self._ingest_source_urls(
            self.discovery_sources,
            topic="OpenAI & GPT-Modelle",
            importance=4,
            label="Discovery Source",
        )

    def run(self):
        saved = 0
        to_scrape = []
        meta      = []

        logger.info("Starte RSS-Ingestion…")
        # 1) Feed-Parsing
        for feed_url in self.feeds:
            is_discovery_feed = feed_url in self.discovery_feeds
            try:
                logger.info(f"Lese Feed {feed_url}")
                feed = feedparser.parse(feed_url)
            except Exception as e:
                logger.error(f"Feedparser-Error {feed_url}: {e}")
                continue

            for entry in feed.entries[:MAX_FEED_ENTRIES_PER_FEED]:
                link = normalize_feed_link(entry.get("link", ""))
                if not link or link in self.existing:
                    continue

                title    = clean_text(entry.get("title", ""))
                raw_desc = entry.get("summary", "") or entry.get("description", "")
                desc     = clean_text(raw_desc)
                topic = "OpenAI & GPT-Modelle" if is_discovery_feed else "Allgemein"
                importance = 4 if is_discovery_feed else 0
                try:
                    published = datetime(*entry.published_parsed[:6],
                                         tzinfo=timezone.utc).date()
                except Exception:
                    published = datetime.now(timezone.utc).date()

                # entscheiden: RSS-only vs. Fulltext-Scrape
                if any(dom in link for dom in SKIP_SCRAPE_DOMAINS):
                    # sofort speichern
                    content = desc
                    should_scrape = False
                else:
                    to_scrape.append(link)
                    meta.append((title, link, desc, published, topic, importance))
                    should_scrape = True

                if not should_scrape:
                    try:
                        summ = summarize(content)
                        trans = translate_de_en(content)
                        self.storage.insert_article(
                            title=title,
                            link=link,
                            description=desc,
                            content=content,
                            summary=summ,
                            translation=trans,
                            published=published,
                            topic=topic,
                            importance=importance,
                            relevance=0
                        )
                        update_topic(topic, delta=1)
                        saved += 1
                        self.existing.add(link)
                    except Exception as e:
                        logger.error(f"Speichern RSS-only {link} fehlgeschlagen: {e}")

        # 2) Volltext-Scraping
        htmls = asyncio.get_event_loop().run_until_complete(
            self._fetch_all(to_scrape)
        )
        for (title, link, desc, published, topic, importance), html in zip(meta, htmls):
            try:
                if html:
                    content = extract_article_text(html)
                else:
                    content = desc

                # Filter: nur Artikel mit ausreichender Länge behalten
                word_count = len(content.split())
                if word_count < MIN_ARTICLE_WORDS:
                    logger.info(f"Verwerfe {link}: nur {word_count} Wörter")
                    continue
                if not is_useful_article_text(content, min_words=MIN_ARTICLE_WORDS):
                    logger.info(f"Verwerfe {link}: Textqualitaet nicht ausreichend")
                    continue

                summ = summarize(content)
                trans = translate_de_en(content)

                self.storage.insert_article(
                    title=title,
                    link=link,
                    description=desc,
                    content=content,
                    summary=summ,
                    translation=trans,
                    published=published,
                    topic=topic,
                    importance=importance,
                    relevance=0
                )
                update_topic(topic, delta=1)
                saved += 1
                self.existing.add(link)

            except Exception as e:
                logger.error(f"Fehler bei Artikel {link}: {e}")
                # weiter mit nächstem Eintrag

        saved += self._ingest_trusted_sources()
        saved += self._ingest_discovery_sources()
        logger.info(f"Ingestion abgeschlossen: {saved} Artikel gespeichert.")
