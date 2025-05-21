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

from html import unescape
from datetime import datetime, timezone

import feedparser
from bs4 import BeautifulSoup

from config import RSS_FEEDS, DB_PATH, MIN_ARTICLE_WORDS, MAX_FETCH_WORKERS
from storage.duckdb_storage import DuckDBStorage
from storage.topic_tracker import create_topic_table, update_topic

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SKIP_SCRAPE_DOMAINS = {
    'huggingface.co/blog',
    # ggf. weitere Domains …
}


def clean_text(text: str) -> str:
    """Entfernt HTML-Tags, HTML-Entities und normalisiert Whitespace."""
    soup = BeautifulSoup(text or '', 'html.parser')
    raw = soup.get_text(separator=' ')
    no_tags = re.sub(r'<[^>]+>', '', raw)
    return re.sub(r'\s+', ' ', unescape(no_tags)).strip()


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

    def __init__(self, feeds=None, storage_client=None):
        self.feeds   = feeds or RSS_FEEDS
        self.storage = storage_client or DuckDBStorage(db_path=DB_PATH)
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

    def run(self):
        saved = 0
        to_scrape = []
        meta      = []

        logger.info("Starte RSS-Ingestion…")
        # 1) Feed-Parsing
        for feed_url in self.feeds:
            try:
                logger.info(f"Lese Feed {feed_url}")
                feed = feedparser.parse(feed_url)
            except Exception as e:
                logger.error(f"Feedparser-Error {feed_url}: {e}")
                continue

            for entry in feed.entries:
                link = entry.get("link", "").strip()
                if not link or link in self.existing:
                    continue

                title    = clean_text(entry.get("title", ""))
                raw_desc = entry.get("summary", "") or entry.get("description", "")
                desc     = clean_text(raw_desc)
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
                    meta.append((title, link, desc, published))
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
                            topic="Allgemein",
                            importance=0,
                            relevance=0
                        )
                        update_topic("Allgemein", delta=1)
                        saved += 1
                        self.existing.add(link)
                    except Exception as e:
                        logger.error(f"Speichern RSS-only {link} fehlgeschlagen: {e}")

        # 2) Volltext-Scraping
        htmls = asyncio.get_event_loop().run_until_complete(
            self._fetch_all(to_scrape)
        )
        for (title, link, desc, published), html in zip(meta, htmls):
            try:
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    for tag in soup(["script", "style", "nav", "header", "footer"]):
                        tag.decompose()
                    paras = [p.get_text() for p in soup.find_all("p")]
                    content = clean_text(" ".join(paras))
                else:
                    content = desc

                # Filter: nur Artikel mit ausreichender Länge behalten
                word_count = len(content.split())
                if word_count < MIN_ARTICLE_WORDS:
                    logger.info(f"Verwerfe {link}: nur {word_count} Wörter")
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
                    topic="Allgemein",
                    importance=0,
                    relevance=0
                )
                update_topic("Allgemein", delta=1)
                saved += 1
                self.existing.add(link)

            except Exception as e:
                logger.error(f"Fehler bei Artikel {link}: {e}")
                # weiter mit nächstem Eintrag

        logger.info(f"Ingestion abgeschlossen: {saved} Artikel gespeichert.")
