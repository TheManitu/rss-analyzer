#!/usr/bin/env python3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
from langdetect import detect
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer

from rss_analyzer.config import RSS_FEEDS, TOPIC_MAPPING
from rss_analyzer.database import create_table, insert_article, get_all_articles
from rss_analyzer.topic_db import create_topic_table, update_topic

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

class SimpleTokenizer:
    def __init__(self, language):
        self.language = language
    def to_sentences(self, text):
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    def to_words(self, text):
        return re.findall(r'\w+', text)

def generate_summary(text, max_words=300):
    parser = PlaintextParser.from_string(text, SimpleTokenizer("german"))
    summarizer = LexRankSummarizer()
    summary_sentences = summarizer(parser.document, 10)
    summary = " ".join(str(sentence) for sentence in summary_sentences)
    return " ".join(summary.split()[:max_words])

def is_cookie_consent_text(text):
    """
    Prüft, ob der übergebene Text typische Cookie-Consent-Phrasen enthält.
    Diese Phrasen sollen unerwünschte Informationen (z. B. bei golem.de) erkennen.
    """
    consent_phrases = [
        "zustimmung", "cookie", "tracking", "privacy center",
        "datenschutzerklärung", "nutzung aller cookies", "widerruf"
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in consent_phrases)

def fetch_full_article(link):
    MIN_WORDS = 100
    try:
        response = requests.get(link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return ""
        soup = BeautifulSoup(response.content, "html.parser")
        # Entferne Tags, die nicht zum Artikelinhalt gehören.
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Versuche, den Inhalt aus <main> oder <article> zu extrahieren.
        content_tag = soup.find("main") or soup.find("article")
        if content_tag:
            for tag in content_tag(["aside", "iframe", "ins"]):
                tag.decompose()
            text1 = clean_text(content_tag.get_text(separator=" "))
            # Falls der Text ausreichend lang ist und nicht hauptsächlich Cookie-Consent-Informationen enthält:
            if len(text1.split()) >= MIN_WORDS and not is_cookie_consent_text(text1):
                return text1
            else:
                # Falls offensichtlich Cookie-Consent-Text detektiert wird, verwende alternativ alle <p>-Tags.
                paragraphs = soup.find_all("p")
                filtered_paragraphs = []
                for p in paragraphs:
                    p_text = clean_text(p.get_text())
                    if not is_cookie_consent_text(p_text):
                        filtered_paragraphs.append(p_text)
                text2 = clean_text(" ".join(filtered_paragraphs))
                if len(text2.split()) >= MIN_WORDS:
                    return text2
        # Fallback: alle <p>-Tags
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        text3 = clean_text(" ".join(paragraphs))
        return text3 if len(text3.split()) >= MIN_WORDS else ""
    except Exception as e:
        print(f"❌ Fehler beim Artikelabruf ({link}):", e)
        return ""

def process_article(content, title):
    word_count = len(content.split())
    try:
        lang = detect(content)
    except Exception:
        lang = "unknown"
    if word_count > 300 or lang == "en":
        return generate_summary(content)
    return content

def fetch_and_store_feeds():
    create_table()
    create_topic_table()
    saved_count = 0
    for url in RSS_FEEDS:
        print(f"🌐 Verarbeite Feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "Kein Titel")
            link = entry.get("link", "")
            description = clean_text(entry.get("summary", entry.get("description", "")))
            if not description:
                description = "Beschreibung fehlt."
            full_content = fetch_full_article(link)
            if not full_content:
                full_content = description
            content = process_article(full_content, title)
            try:
                published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date()
            except Exception:
                published_dt = datetime.now(timezone.utc).date()

            text_to_search = (title + " " + description).lower()
            matched_topics = [(name, d["importance"]) for name, d in TOPIC_MAPPING.items()
                              if any(kw in text_to_search for kw in d["keywords"])]
            if matched_topics:
                matched_topics.sort(key=lambda x: x[1], reverse=True)
                topic_names = [t[0] for t in matched_topics[:2]]
                importance = max(t[1] for t in matched_topics)
            else:
                topic_names = ["Allgemein"]
                importance = 1
            topic_str = ", ".join(topic_names)
            relevance = importance + (1 if published_dt == datetime.now(timezone.utc).date() else 0)

            if published_dt >= (datetime.now(timezone.utc).date() - timedelta(days=14)):
                insert_article(title, link, description, content, published_dt, topic_str, importance, relevance)
                for t in topic_names:
                    update_topic(t, delta=1)
                saved_count += 1
    print(f"\n✅ {saved_count} neue Artikel gespeichert.")

def show_summary():
    print("\n🗂️  Vorschau der gespeicherten Artikel:")
    articles = get_all_articles(time_filter="today")
    for a in articles[:5]:
        print(f"• {a['title']} ({a['published']}) – Thema: {a['topic']}")

if __name__ == "__main__":
    fetch_and_store_feeds()
    show_summary()
