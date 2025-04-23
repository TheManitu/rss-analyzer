#!/usr/bin/env python3
# ingestion/rss_ingest.py
import asyncio
import aiohttp
import subprocess
import shlex
import re

from html import unescape
from datetime import datetime, timezone
import feedparser
from bs4 import BeautifulSoup

from config import RSS_FEEDS, DB_PATH, MIN_ARTICLE_WORDS, MAX_FETCH_WORKERS
from storage.duckdb_storage import DuckDBStorage
from storage.topic_tracker import create_topic_table, update_topic

# Domains, für die nur die RSS-Summary genutzt wird (kein Fulltext-Scrape)
SKIP_SCRAPE_DOMAINS = [
    'huggingface.co/blog',
    # hier weitere Domains ergänzen, falls nötig
]

def clean_text(text: str) -> str:
    """
    Entfernt HTML-Tags, HTML-Entities und normalisiert Whitespace.
    """
    # HTML parsen und reinen Text holen
    soup = BeautifulSoup(text or '', 'html.parser')
    raw = soup.get_text(separator=' ')
    # Entferne fallbackweise alle <...> Reste
    no_tags = re.sub(r'<[^>]+>', '', raw)
    # Entities unescapen (z.B. &amp; -> &)
    unesc = unescape(no_tags)
    # Whitespace konsolidieren
    return re.sub(r'\s+', ' ', unesc).strip()


def summarize(text: str, sentences: int = 5) -> str:
    """
    Extraktive Zusammenfassung via Sumy (TextRank). Fällt bei Fehlern auf Satz-Splitting zurück.
    """
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
    """
    Übersetzt deutsch->englisch regelbasiert via Apertium.
    """
    cmd = f"echo {shlex.quote(text)} | apertium -u de-en"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip() or ""

class RSSIngest:
    def __init__(self, feeds=None, storage_client=None):
        self.feeds = feeds or RSS_FEEDS
        self.storage = storage_client or DuckDBStorage(db_path=DB_PATH)
        create_topic_table()
        # Einmaliger Duplikat-Check: bereits gespeicherte Links
        self.existing_links = set(self.storage.get_all_links())

    async def fetch_content(self, session, url):
        try:
            async with session.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception:
            return None

    async def fetch_all(self, urls):
        connector = aiohttp.TCPConnector(limit_per_host=MAX_FETCH_WORKERS)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_content(session, u) for u in urls]
            return await asyncio.gather(*tasks)

    def delete_short_articles(self, min_words: int = MIN_ARTICLE_WORDS):
        """
        Löscht Artikel mit zu wenig Content (nur bei gescrapten Artikeln, nicht bei RSS-Feeds).
        """
        # Baue WHERE-Klausel: kurze Content-Artikel, aber NICHT aus Skip-Domains
        exclude = " OR ".join([f"link LIKE '%{d}%'" for d in SKIP_SCRAPE_DOMAINS])
        clause = f"array_length(split(content, ' '), 1) < {min_words}"
        if exclude:
            clause += f" AND NOT ({exclude})"
        self.storage.execute(f"""
          DELETE FROM articles
          WHERE {clause}
        """)
        print(f"🗑️ Artikel mit <{min_words} Wörtern gelöscht (außer RSS-only Feeds)")

    def run(self):
        saved = 0
        to_fetch = []      # URLs für Fulltext-Scraping
        meta = []          # Metadaten dazu
        direct = []        # RSS-only Artikel

        print("🌐 Scanne Feeds auf neue Artikel…")
        for url in self.feeds:
            print(f"  → Feed: {url}")
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = clean_text(entry.get("title", ""))
                link = entry.get("link", "").strip()
                if link in self.existing_links:
                    continue
                raw_desc = entry.get("summary", entry.get("description", ""))
                desc = clean_text(raw_desc)
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date()
                except Exception:
                    published = datetime.now(timezone.utc).date()
                if any(domain in link for domain in SKIP_SCRAPE_DOMAINS):
                    direct.append((title, link, desc, published))
                else:
                    to_fetch.append(link)
                    meta.append((title, link, desc, published))

        # 1) RSS-only Artikel speichern (ohne Längencheck)
        for title, link, desc, published in direct:
            summ = summarize(desc)
            trans = translate_de_en(desc)
            self.storage.insert_article(
                title=title,
                link=link,
                description=desc,
                content=desc,
                summary=summ,
                translation=trans,
                published=published,
                topic=None,
                importance=0,
                relevance=0,
            )
            update_topic("Allgemein", delta=1)
            saved += 1

        # 2) Volltext-Scraping und Speichern
        htmls = asyncio.get_event_loop().run_until_complete(self.fetch_all(to_fetch))
        for (title, link, desc, published), html in zip(meta, htmls):
            content = desc
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                for tag in soup(["script","style","nav","footer","header"]):
                    tag.decompose()
                paras = [p.get_text() for p in soup.find_all("p")]
                content = clean_text(" ".join(paras))
            if len(content.split()) < MIN_ARTICLE_WORDS:
                print(f"⚠️ Artikel zu kurz ({len(content.split())} Wörter): {link}")
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
                topic=None,
                importance=0,
                relevance=0,
            )
            update_topic("Allgemein", delta=1)
            saved += 1

        # 3) Cleanup of too-short scrapes
        self.delete_short_articles(min_words=MIN_ARTICLE_WORDS)

        print(f"\n✅ {saved} neue Artikel verarbeitet und gespeichert.")


def main():
    RSSIngest().run()

if __name__ == "__main__":
    main()
