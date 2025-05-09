#!/usr/bin/env python3

import os, re, duckdb, time, nltk, argparse
from rake_nltk import Rake
from storage.duckdb_storage import DuckDBStorage
from config import DB_PATH

nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)

MAX_TEXT_LENGTH = 5000

def get_stopwords(langs=("english", "german")) -> set:
    stops = set()
    for lang in langs:
        stops |= set(nltk.corpus.stopwords.words(lang))
    return stops

def is_valid_phrase(phrase: str, stopwords: set, min_words: int, min_char_length: int) -> bool:
    words = phrase.split()
    if len(words) < min_words or all(len(w) < min_char_length for w in words):
        return False
    if all(w.lower() in stopwords for w in words):
        return False
    if not re.search(r"[A-Za-zÄÖÜäöüß]", phrase):
        return False
    if re.fullmatch(r"[\d\s\.,\-]+", phrase):
        return False
    if len(set(words)) == 1:
        return False

    joined = " ".join(words).lower()
    filler_patterns = [
        r"\bdieser beitrag\b",
        r"\bdieser artikel\b",
        r"\bin diesem artikel\b",
        r"\bbeispiel\b",
        r"\binformationen\b"
    ]
    if any(re.search(pat, joined) for pat in filler_patterns):
        return False

    if not any(len(w) > 5 and w.lower() not in stopwords for w in words):
        return False

    return True

def extract_and_store_keywords(start: int, end: int):
    db_path = DB_PATH
    storage = DuckDBStorage(db_path=db_path)
    stopwords = get_stopwords(("english", "german"))
    rake = Rake(stopwords=stopwords)
    rake.sentence_tokenizer = lambda text: text.split(".")

    con = duckdb.connect(db_path)
    all_links = [row[0] for row in con.execute("SELECT link FROM articles ORDER BY link").fetchall()]
    existing = {row[0] for row in con.execute("SELECT DISTINCT link FROM article_keywords").fetchall()}
    batch = all_links[start:end]
    total = len(all_links)

    print(f"🔍 Verarbeite Artikel {start+1}–{min(end, total)} von {total}...")

    for link in batch:
        if link in existing:
            print(f"[⏭] Keywords für {link} bereits vorhanden, übersprungen")
            continue

        row = con.execute("SELECT title, summary, content FROM articles WHERE link = ?", (link,)).fetchone()
        if not row:
            continue
        text = " ".join(filter(None, row)).strip()
        if not text:
            print(f"[!] Leerer Text für {link}, übersprungen")
            continue

        text = text[:MAX_TEXT_LENGTH]

        rake.extract_keywords_from_text(text)
        scored_phrases = rake.get_ranked_phrases_with_scores()
        keywords = []

        for score, phrase in scored_phrases:
            if score < 1.0:
                break
            if is_valid_phrase(phrase, stopwords, 2, 4):
                kw = phrase.strip().lower()
                if kw not in keywords:
                    keywords.append(kw)
            if len(keywords) >= 25:
                break

        if keywords:
            storage.upsert_article_keywords(link, keywords, conn=con)
            print(f"[+] {len(keywords)} Keywords für {link}")
        else:
            print(f"[!] Keine relevanten Keywords für {link}")

    con.close()
    print(f"✅ Batch {start}–{end} abgeschlossen.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    extract_and_store_keywords(start=args.start, end=args.end)
