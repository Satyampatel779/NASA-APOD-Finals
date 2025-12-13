"""Generate a few static PNG charts from the APOD SQLite database.

This script is optional. It produces the same core visuals as the notebook, but writes
them to `docs/` as image files so they can be viewed without opening Jupyter.

Outputs:
- `docs/media_by_date.png`
- `docs/weekday_distribution.png`
- `docs/word_frequency.png`
"""

import sqlite3
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "apod.db"
OUT_DIR = ROOT / "docs"
OUT_DIR.mkdir(exist_ok=True)


def load_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql_query("SELECT * FROM apod_entries", con)
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["weekday"] = df["date_dt"].dt.day_name()
    return df.dropna(subset=["date_dt"])


def plot_media_over_time(df: pd.DataFrame) -> None:
    media_by_date = df.groupby("date_dt")["media_type"].value_counts().unstack(fill_value=0)
    media_by_date.sort_index(inplace=True)
    ax = media_by_date.plot(kind="bar", stacked=True, figsize=(12, 4), color=["#4c72b0", "#dd8452", "#55a868"])
    ax.set_title("Media Type Distribution by Date")
    ax.set_xlabel("Date")
    ax.set_ylabel("Count")
    plt.xticks(rotation=75)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "media_by_date.png", dpi=150)
    plt.close()


def plot_weekday_distribution(df: pd.DataFrame) -> None:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    counts = df["weekday"].value_counts().reindex(order, fill_value=0)
    plt.figure(figsize=(7, 4))
    sns.barplot(x=counts.index, y=counts.values, palette="viridis")
    plt.title("APOD Posts by Weekday")
    plt.xlabel("Weekday")
    plt.ylabel("Count")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "weekday_distribution.png", dpi=150)
    plt.close()


def plot_top_words(df: pd.DataFrame) -> None:
    def extract_words(text: str) -> list[str]:
        return re.findall(r"[A-Za-z]{4,}", text.lower()) if isinstance(text, str) else []

    all_words = df["explanation"].dropna().apply(extract_words)
    freq = pd.Series([w for words in all_words for w in words]).value_counts()
    top_words = freq.head(20)
    plt.figure(figsize=(10, 5))
    sns.barplot(x=top_words.values, y=top_words.index, color="steelblue")
    plt.title("Top Words in APOD Explanations (>=4 letters)")
    plt.xlabel("Count")
    plt.ylabel("Word")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "word_frequency.png", dpi=150)
    plt.close()


def main() -> None:
    df = load_data()
    plot_media_over_time(df)
    plot_weekday_distribution(df)
    plot_top_words(df)
    print("Saved plots to", OUT_DIR)


if __name__ == "__main__":
    main()
