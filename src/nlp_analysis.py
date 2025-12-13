"""NLP analysis for APOD explanations.

This script reads `date`, `title`, and `explanation` from the `apod_entries` table and
produces two small JSON files:

- `data/nlp_entities.json`: most common detected "entities"
- `data/nlp_keyphrases.json`: most common keyphrase-style terms

If spaCy is available, the script uses spaCy's NER and noun chunks.
If spaCy cannot be imported or the model cannot be loaded, the script falls back to
simple regex heuristics so the project still runs in a limited environment.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import List

import pandas as pd

try:
    import spacy
except Exception:  # spaCy not available or incompatible with Python version
    spacy = None

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "apod.db"
DEFAULT_ENTITIES = ["PERSON", "NORP", "FAC", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "WORK_OF_ART", "LAW", "LANGUAGE"]


def load_nlp(model: str):
    if spacy is None:
        return None
    try:
        return spacy.load(model)
    except Exception:
        return None


def load_data(db_path: Path) -> pd.DataFrame:
    import sqlite3

    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query("SELECT date, title, explanation FROM apod_entries", con)
    df["explanation"] = df["explanation"].fillna("")
    return df


def extract_entities(texts: List[str], nlp, labels: List[str]) -> Counter:
    if nlp is None:
        # Fallback: simple capitalized-token heuristic as pseudo-entities
        counts: Counter = Counter()
        for text in texts:
            for token in re.findall(r"\b[A-Z][A-Za-z]{3,}\b", text):
                counts[token] += 1
        return counts
    counts: Counter = Counter()
    for doc in nlp.pipe(texts, batch_size=32, disable=["tagger", "lemmatizer", "textcat"]):
        for ent in doc.ents:
            if ent.label_ in labels:
                counts[ent.text] += 1
    return counts


def extract_keyphrases(texts: List[str], nlp) -> Counter:
    if nlp is None:
        counts: Counter = Counter()
        for text in texts:
            # simple 1-3 word lowercase phrases of 4+ letters
            for phrase in re.findall(r"\b([a-z]{4,}(?:\s+[a-z]{4,}){0,2})\b", text.lower()):
                counts[phrase.strip()] += 1
        return counts
    counts: Counter = Counter()
    for doc in nlp.pipe(texts, batch_size=32, disable=["ner", "textcat"]):
        for chunk in doc.noun_chunks:
            phrase = chunk.text.strip().lower()
            if len(phrase) >= 4:
                counts[phrase] += 1
    return counts


def save_top(counter: Counter, top_n: int, path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [{"text": text, "count": count} for text, count in counter.most_common(top_n)]
    path.write_text(json.dumps({label: data}, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze APOD explanation text and write top entities/keyphrases to JSON (spaCy optional; regex fallback)."
    )
    parser.add_argument("--database", default=str(DB_PATH), help="Path to SQLite database")
    parser.add_argument("--model", default="en_core_web_sm", help="spaCy model name")
    parser.add_argument("--top", type=int, default=25, help="Top N items to keep")
    parser.add_argument("--entities-out", default=str(ROOT / "data" / "nlp_entities.json"), help="Entities JSON output")
    parser.add_argument("--phrases-out", default=str(ROOT / "data" / "nlp_keyphrases.json"), help="Keyphrases JSON output")
    args = parser.parse_args()

    nlp = load_nlp(args.model)
    df = load_data(Path(args.database))
    texts = df["explanation"].tolist()

    ent_counts = extract_entities(texts, nlp, DEFAULT_ENTITIES)
    phrase_counts = extract_keyphrases(texts, nlp)

    save_top(ent_counts, args.top, Path(args.entities_out), label="entities")
    save_top(phrase_counts, args.top, Path(args.phrases_out), label="keyphrases")
    print(f"Saved entities to {args.entities_out} and keyphrases to {args.phrases_out}")


if __name__ == "__main__":
    main()
