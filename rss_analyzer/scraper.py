# rss_analyzer/scraper.py
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
from rss_analyzer.database import create_table, insert_article

def clean_text(text):
    """Bereinigt den Text von überflüssigen Leerzeichen und HTML-Tags."""
    return re.sub(r'\s+', ' ', text).strip()

class SimpleTokenizer:
    def __init__(self, language):
        self.language = language
    def to_sentences(self, text):
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    def to_words(self, text):
        return re.findall(r'\w+', text, flags=re.UNICODE)

def generate_summary(text, max_words=300):
    """Erzeugt eine Zusammenfassung mithilfe des LexRankSummarizers."""
    parser = PlaintextParser.from_string(text, SimpleTokenizer("german"))
    summarizer = LexRankSummarizer()
    summary_sentences = summarizer(parser.document, 10)
    summary = " ".join(str(sentence) for sentence in summary_sentences)
    summary_words = summary.split()
    if len(summary_words) > max_words:
        summary = " ".join(summary_words[:max_words])
    return summary

def save_summary(title, summary):
    """Platzhalter zum Speichern der Zusammenfassung."""
    print(f"Zusammenfassung für '{title}' wurde erstellt und gespeichert.")

def fetch_full_article(link):
    MIN_WORDS = 100
    try:
        response = requests.get(link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return ""
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_tag = soup.find("main") or soup.find("article")
        if content_tag:
            for tag in content_tag(["aside", "iframe", "ins"]):
                tag.decompose()
            text1 = clean_text(content_tag.get_text(separator=" "))
            text1 = re.sub(r"(heise online|Logo|Anmelden|gratis testen|Mehr erfahren)", "", text1, flags=re.IGNORECASE)
            if len(text1.split()) >= MIN_WORDS:
                return text1
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        if paragraphs:
            text2 = clean_text(" ".join(paragraphs))
            text2 = re.sub(r"(heise online|Logo|Anmelden|gratis testen|Mehr erfahren)", "", text2, flags=re.IGNORECASE)
            if len(text2.split()) >= MIN_WORDS:
                return text2
        full_text = clean_text(soup.get_text(separator=" "))
        full_text = re.sub(r"(heise online|Logo|Anmelden|gratis testen|Mehr erfahren)", "", full_text, flags=re.IGNORECASE)
        return full_text if len(full_text.split()) >= MIN_WORDS else ""
    except Exception as e:
        print(f"Error fetching full article ({link}):", e)
    return ""

def summarize_article(content, title):
    if content is None:
        raise ValueError("Kein Inhalt für die Zusammenfassung übergeben.")
    word_count = len(content.split())
    if word_count <= 500:
        return None
    cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    try:
        summary = generate_summary(cleaned_content, max_words=300)
    except Exception as e:
        summary = ""
        paragraphs = cleaned_content.split("\n\n")
        for para in paragraphs:
            if para.strip():
                part_summary = generate_summary(para, max_words=100)
                summary += part_summary + " "
        summary_words = summary.split()
        if len(summary_words) > 350:
            summary = " ".join(summary_words[:300])
            last_period = summary.rfind(".")
            if last_period != -1:
                summary = summary[:last_period+1]
    summary_words = summary.split()
    if len(summary_words) > 350:
        trimmed_summary = " ".join(summary_words[:300])
        last_period = trimmed_summary.rfind(".")
        if last_period != -1:
            trimmed_summary = trimmed_summary[:last_period+1]
        summary = trimmed_summary
    save_summary(title, summary)
    return summary

def process_article(content, title):
    """Entscheidet, ob zusammengefasst werden soll."""
    word_count = len(content.split())
    try:
        lang = detect(content)
    except Exception as e:
        lang = "unknown"
    if word_count > 300 or lang == "en":
        print(f"Artikel '{title}' wird zusammengefasst: word_count={word_count}, lang={lang}")
        return summarize_article(content, title)
    else:
        return content

def fetch_and_store_feeds():
    """Liest alle RSS-Feeds ein und speichert Artikel (letzte 14 Tage) in die DB."""
    create_table()
    for url in RSS_FEEDS:
        print(f"Verarbeite Feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "Kein Titel")
            link = entry.get("link", "")
            description = clean_text(entry.get("summary", entry.get("description", "")).strip())
            if not description:
                description = "Beschreibung fehlt – klicken Sie auf den Artikel für mehr Informationen."
            full_content = fetch_full_article(link)
            if not full_content:
                print(f"Warnung: Kein vollständiger Artikeltext gefunden für {title}")
                full_content = description
            content = process_article(full_content, title)
            try:
                published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date()
            except Exception:
                published_dt = datetime.now(timezone.utc).date()
            text_to_search = (title + " " + description).lower()
            matched_topics = []
            for topic_name, data in TOPIC_MAPPING.items():
                for kw in data["keywords"]:
                    if kw in text_to_search:
                        matched_topics.append((topic_name, data["importance"]))
                        break
            if matched_topics:
                matched_topics = sorted(matched_topics, key=lambda x: x[1], reverse=True)
                chosen_topics = matched_topics[:2]
                topic_names = [t[0] for t in chosen_topics]
                importance = max(t[1] for t in chosen_topics)
            else:
                topic_names = ["Allgemein"]
                importance = 1
            topic_str = ", ".join(topic_names)
            relevance = importance
            if published_dt == datetime.now(timezone.utc).date():
                relevance += 1
            if published_dt >= (datetime.now(timezone.utc).date() - timedelta(days=14)):
                insert_article(title, link, description, content, published_dt, topic_str, importance, relevance)
                print(f"Gespeichert: {title}")
            else:
                print(f"Übersprungen (älter als 2 Wochen): {title}")

def test_output():
    """Gibt eine Testausgabe von 5 gespeicherten Artikeln aus."""
    from rss_analyzer.database import get_all_articles
    articles = get_all_articles(time_filter="today")
    for art in articles[:5]:
        print("Titel:", art["title"])
        print("Quelle:", art["link"])
        print("Veröffentlicht:", art["published"])
        print("Themen:", art["topic"])
        print("Wichtigkeit:", art["importance"])
        print("Relevanz:", art["relevance"])
        print("Content:", art["content"])
        print("-" * 80)

if __name__ == "__main__":
    fetch_and_store_feeds()
    print("\n--- Testausgabe der letzten 5 Artikel ---")
    test_output()
