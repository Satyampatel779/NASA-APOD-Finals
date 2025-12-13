# NASA APOD Data Pipeline

I built this project to collect, validate, analyze, and visualize NASA Astronomy Picture of the Day (APOD) data locally in SQLite. After the API calls finish, everything important runs offline from a single database file, so it is easy to review and grade end-to-end.

## Quick start (Windows PowerShell)
```pwsh
# 1) Install deps
python -m pip install -r requirements.txt

# 2) Set your API key (replace with your own) or create a .env file
$env:NASA_API_KEY="<your_key>"
# alternatively: create a .env file at the repo root with
# NASA_API_KEY=<your_key>

# 3) Run the main pipeline (30 days by default)
python src/apod_pipeline.py --database data/apod.db

# 4) Run quality checks
python src/data_quality.py --database data/apod.db --report-json data/data_quality_report.json --report-md data/data_quality_report.md

# 5) Generate plots (PNG in docs/)
python docs/generate_plots.py

# 6) NLP entities/keyphrases (fallback to regex if spaCy model missing)
python src/nlp_analysis.py --database data/apod.db --model en_core_web_sm --top 25

# 7) Launch the web UI
python src/web_app.py   # open http://127.0.0.1:5000

# 8) Run tests
pytest -q
```

## What each piece does
- `src/apod_pipeline.py`: Fetch APOD entries for a date range and upsert into SQLite with retries and thumbnails.
- `src/data_quality.py`: Check missing fields, invalid/out-of-range dates, duplicates, media-type issues, and empty strings; outputs JSON/Markdown reports in `data/`.
- `docs/apod_eda.ipynb`: EDA notebook (quality summary + media mix + posting patterns + text/HD visuals).
- `docs/generate_plots.py`: Produces PNGs in `docs/` (`media_by_date.png`, `weekday_distribution.png`, `word_frequency.png`).
- `src/nlp_analysis.py`: NLP on explanations—sentiment via VADER (shown in the UI) and entities/keyphrases via spaCy; falls back to regex heuristics if the spaCy model is unavailable.
- `src/web_app.py`: Flask UI to browse APOD entries with filters and inline sentiment scores.
- `src/mars_photos.py`: Bonus script to fetch Mars Rover photos by Earth date or sol; saves JSON in `data/`.
- `run_all.py`: Orchestrator to run fetch → quality → (optional Mars) → tests in one go.

## Installation notes
- Python 3.10+ recommended. This repo has been exercised with Python 3.14; spaCy can be sensitive to Python/model versions, so `src/nlp_analysis.py` includes a regex fallback.
- Install deps: `python -m pip install -r requirements.txt`
- If you want full spaCy entities, install the model: `python -m spacy download en_core_web_sm` (optional; fallback is automatic if it fails).

## Running the pipeline (detailed)
1) Fetch data
   ```pwsh
   python src/apod_pipeline.py --database data/apod.db --days 30
   # or set explicit dates:
   python src/apod_pipeline.py --start-date 2024-11-01 --end-date 2024-11-30 --database data/apod.db
   ```

2) Data quality
   ```pwsh
   python src/data_quality.py --database data/apod.db --report-json data/data_quality_report.json --report-md data/data_quality_report.md
   ```

3) Analysis / visualization
   - Notebook: open `docs/apod_eda.ipynb` in VS Code/Jupyter (requires `data/apod.db`).
   - Static PNGs: `python docs/generate_plots.py` (writes to `docs/`).

4) NLP
   ```pwsh
   python src/nlp_analysis.py --database data/apod.db --model en_core_web_sm --top 25
   ```
   Outputs: `data/nlp_entities.json`, `data/nlp_keyphrases.json`. If the model is missing or incompatible, the script falls back to regex-based extraction.

5) Web UI
   ```pwsh
   python src/web_app.py
   # then open http://127.0.0.1:5000
   ```
   Filter by date and media type; sentiment (VADER) is shown per explanation.

6) Mars Rover bonus
   ```pwsh
   python src/mars_photos.py --rover perseverance --date 2022-02-18 --output data/mars_photos.json
   # or use sol instead of date:
   python src/mars_photos.py --rover curiosity --sol 1000 --output data/mars_photos.json
   ```

7) Tests
   ```pwsh
   pytest -q
   ```

8) Scheduling (optional, Windows Task Scheduler)
   - Program: `C:\Program Files\Python314\python.exe`
   - Args: `d:/Study/SENG8081/NASA-APOD-Finals/src/apod_pipeline.py --database d:/Study/SENG8081/NASA-APOD-Finals/data/apod.db`
   - Ensure `NASA_API_KEY` is set in the task or pass `--api-key <key>`.

## Data artifacts
- `data/apod.db`: SQLite database with APOD metadata.
- `data/data_quality_report.json|md`: Quality summaries.
- `data/apod_entries.csv`: CSV export of the APOD table.
- `docs/media_by_date.png`, `weekday_distribution.png`, `word_frequency.png`: Generated charts.
- `data/nlp_entities.json`, `data/nlp_keyphrases.json`: NLP outputs.
- `data/mars_photos.json` (if you run the Mars script).
- `data/schema.txt`: Table definition and index.

## Database schema (apod_entries)
- `date` TEXT PRIMARY KEY
- `title` TEXT NOT NULL
- `explanation` TEXT
- `media_type` TEXT
- `url` TEXT
- `hdurl` TEXT
- `thumbnail_url` TEXT
- `service_version` TEXT
- `copyright` TEXT
- `fetched_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
Index: `idx_apod_media_type` on `media_type`.

## Design notes
- I request date ranges to respect API limits while reducing call volume.
- I upsert by `date` to keep the latest metadata without duplicates.
- I ask for video thumbnails so every record has a representative media link.
- Quality checks guard against missing fields, bad dates, and malformed media types.

## Troubleshooting
- Missing spaCy model or Python 3.14 incompatibility: the NLP script falls back to regex heuristics; install `en_core_web_sm` if you need richer entities.
- Empty Mars photos: some dates/sols have zero results; the script now returns an empty JSON instead of failing.
- API key: set `NASA_API_KEY` or pass `--api-key` to `apod_pipeline.py` and `mars_photos.py`.
