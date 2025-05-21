#!/usr/bin/env python3
# pipeline/keyword_extraction_langaware.py

import os
import argparse
import yaml
from langdetect import detect
import spacy
import yake

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

from storage.duckdb_storage import DuckDBStorage

# === CONFIG ===
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
MMR_DIVERSITY   = 0.7

def load_synonyms(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def apply_synonyms(kw_list: list[str], synonyms: dict) -> list[str]:
    normalized = []
    for kw in kw_list:
        for base, forms in synonyms.items():
            if kw.lower() in [f.lower() for f in forms] + [base.lower()]:
                kw = base
                break
        normalized.append(kw)
    return list(dict.fromkeys(normalized))


class LanguageAwareKeywordExtractor:
    """
    Extrahiert Unigram-Keywords, priorisiert dabei Begriffe aus dem Titel.
    """
    def __init__(self,
                 db_path: str = None,
                 top_n:   int = 15,
                 synonyms_path: str = None):
        self.db_path   = db_path    or os.getenv("DB_PATH")
        self.top_n     = top_n
        self.synonyms  = load_synonyms(synonyms_path) if synonyms_path else {}

        # Modelle nur einmal laden
        self.sbert     = SentenceTransformer(DEFAULT_MODEL)
        self.kb        = KeyBERT(model=self.sbert)
        self.spacy_de  = spacy.load("de_core_news_sm")
        self.yake_de   = yake.KeywordExtractor(
            lan="de", n=1, dedupLim=0.9, top=self.top_n*2
        )

    def extract(self, title: str, text: str) -> list[str]:
        lang = detect(text or title or "en")

        # 1) Keywords aus Titel (Unigram, MMR)
        stop_words = (
            list(self.spacy_de.Defaults.stop_words)
            if lang == "de" else "english"
        )
        try:
            title_kws = [
                kw for kw,_ in self.kb.extract_keywords(
                    title,
                    keyphrase_ngram_range=(1,1),
                    stop_words=stop_words,
                    top_n=self.top_n,
                    use_mmr=True,
                    diversity=MMR_DIVERSITY
                )
            ]
        except Exception:
            title_kws = []

        # 2) NER aus Text (DE)
        ents = []
        if lang == "de":
            doc = self.spacy_de(text)
            ents = [
                ent.text for ent in doc.ents
                if ent.label_ in ("PER","ORG","LOC","PRODUCT")
            ]

        # 3) KeyBERT aus Text (Unigram, MMR)
        try:
            kb_raw = [
                kw for kw,_ in self.kb.extract_keywords(
                    text,
                    keyphrase_ngram_range=(1,1),
                    stop_words=stop_words,
                    top_n=self.top_n*2,
                    use_mmr=True,
                    diversity=MMR_DIVERSITY
                )
            ]
        except Exception:
            kb_raw = []

        # 4) YAKE-Fallback (DE)
        yake_raw = []
        if lang == "de":
            yake_raw = [kw for kw,_ in self.yake_de.extract_keywords(text)]

        # 5) Merge in Reihenfolge: Titel → NER → KeyBERT → YAKE
        merged = []
        for term in title_kws + ents + kb_raw + yake_raw:
            if " " in term:  # nur Unigrams
                continue
            if term.lower() not in [m.lower() for m in merged]:
                merged.append(term)
            if len(merged) >= self.top_n:
                break

        # 6) Synonym-Mapping & final trim
        if self.synonyms:
            merged = apply_synonyms(merged, self.synonyms)

        return merged[:self.top_n]

    def run(self, time_filter: str = "14_days"):
        db       = DuckDBStorage(db_path=self.db_path)
        articles = db.get_all_articles(time_filter)
        total    = len(articles)

        for idx, art in enumerate(articles, start=1):
            link  = art["link"]
            title = art.get("title", "")
            text  = art.get("content") or art.get("description") or ""
            kws   = self.extract(title, text)
            db.update_keywords(link, kws)
            print(f"[LangAwareKW {idx}/{total}] {link}: {kws}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db",       help="DuckDB-Pfad (überschreibt ENV DB_PATH)")
    p.add_argument("--top_n",    type=int, default=5)
    p.add_argument("--synonyms", help="Pfad zur YAML-Synonyms-Datei")
    args = p.parse_args()

    LanguageAwareKeywordExtractor(
        db_path=args.db,
        top_n=args.top_n,
        synonyms_path=args.synonyms
    ).run()
