# api/filters.py

import re

def first_words(s: str, num_words: int = 250) -> str:
    if not s:
        return ""
    # HTML-Tags entfernen
    clean = re.sub(r"<.*?>", "", s)
    words = clean.split()
    return " ".join(words[:num_words]) + ("…" if len(words) > num_words else "")

def truncatewords(s: str, num_words: int = 500) -> str:
    if not s:
        return ""
    words = s.split()
    return " ".join(words[:num_words]) + ("…" if len(words) > num_words else "")
