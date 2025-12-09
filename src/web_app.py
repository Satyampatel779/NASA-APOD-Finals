from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, render_template_string, request
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "apod.db"

app = Flask(__name__)
_sentiment = SentimentIntensityAnalyzer()

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>NASA APOD Browser</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 1.5rem; }
    header { margin-bottom: 1rem; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .meta { color: #555; font-size: 0.9rem; }
    .title { font-weight: 600; }
    .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 6px; background: #eef; margin-left: 0.5rem; }
    .sent { font-size: 0.85rem; color: #333; }
    form { margin-bottom: 1rem; }
    input, select { padding: 0.35rem; }
  </style>
</head>
<body>
<header>
  <h1>NASA APOD Browser</h1>
  <form method="get">
    <label>Date range: <input type="date" name="start" value="{{ start }}"> to <input type="date" name="end" value="{{ end }}"></label>
    <label>Media: 
      <select name="media">
        <option value="">All</option>
        <option value="image" {% if media=='image' %}selected{% endif %}>Images</option>
        <option value="video" {% if media=='video' %}selected{% endif %}>Videos</option>
      </select>
    </label>
    <button type="submit">Apply</button>
  </form>
</header>
<section>
  {% for row in rows %}
  <div class="card">
    <div class="meta">{{ row['date'] }} • {{ row['media_type'] }}{% if row['copyright'] %} • © {{ row['copyright'] }}{% endif %}</div>
    <div class="title">{{ row['title'] }}</div>
    <p>{{ row['explanation'][:240] }}{% if row['explanation'] and row['explanation']|length > 240 %}...{% endif %}</p>
    {% if row['url'] %}<div><a href="{{ row['url'] }}" target="_blank">Open media</a></div>{% endif %}
    <div class="sent">Sentiment (compound): {{ "%.3f"|format(row['sentiment']) }}</div>
  </div>
  {% endfor %}
  {% if not rows %}<p>No entries found for the selected filters.</p>{% endif %}
</section>
</body>
</html>
"""


def fetch_rows(start: str | None, end: str | None, media: str | None) -> List[Dict[str, Any]]:
    query = "SELECT * FROM apod_entries WHERE 1=1"
    params: List[Any] = []
    if start:
        query += " AND date >= ?"
        params.append(start)
    if end:
        query += " AND date <= ?"
        params.append(end)
    if media:
        query += " AND media_type = ?"
        params.append(media)
    query += " ORDER BY date DESC LIMIT 100"

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(query, params).fetchall()
    results: List[Dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        text = data.get("explanation") or ""
        data["sentiment"] = _sentiment.polarity_scores(text).get("compound", 0.0)
        results.append(data)
    return results


@app.route("/")
def index():
    start = request.args.get("start")
    end = request.args.get("end")
    media = request.args.get("media") or None
    rows = fetch_rows(start, end, media)
    return render_template_string(PAGE, rows=rows, start=start or "", end=end or "", media=media or "")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
