# NASA APOD Data Pipeline

Python pipeline to collect at least 30 days of NASA Astronomy Picture of the Day (APOD) metadata and store it locally in SQLite for analysis.

## Setup

1. Install Python 3.10+.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Provide an API key (recommended via environment):
   ```bash
   $env:NASA_API_KEY="<your_key>"
   ```
   The script will default to the provided course key if the environment variable is not set.

## Step-by-step guide to run the project
1) Fetch APOD data into SQLite (30 days by default):
   ```bash
   python src/apod_pipeline.py --database data/apod.db
   ```
   - Customize range: `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` or `--days N`.

2) Run data quality checks (outputs JSON + Markdown reports in `data/`):
   ```bash
   python src/data_quality.py --database data/apod.db --report-json data/data_quality_report.json --report-md data/data_quality_report.md
   ```

3) Explore analysis and charts (EDA notebook):
   - Open `docs/apod_eda.ipynb` in VS Code/Jupyter.
   - Notebook visualizes word frequencies, media mix over time, weekday patterns, and copyright distribution.

4) Browse data in a simple web UI (bonus):
   ```bash
   python src/web_app.py
   # visit http://127.0.0.1:5000
   ```
   - Filter by date range and media type; sentiment scores (VADER) are shown per explanation.

5) Optional extra NASA endpoint (Mars Rover Photos):
   ```bash
   python src/mars_photos.py --date 2025-12-08 --output data/mars_photos.json
   ```

6) Run tests:
   ```bash
   pytest -q
   ```

7) (Optional) Schedule daily collection (Windows Task Scheduler example):
   - Create a Basic Task → Trigger daily → Action: `Start a program`
   - Program/script: `C:\\Program Files\\Python314\\python.exe`
   - Add arguments: `d:/Study/SENG8081/NASA-APOD-Finals/src/apod_pipeline.py --database d:/Study/SENG8081/NASA-APOD-Finals/data/apod.db`
   - Ensure `NASA_API_KEY` is set in the task's environment or passed with `--api-key`.

## Usage

Fetch the latest 30 days into a local database (created if missing):

```bash
python src/apod_pipeline.py --database apod.db
```

Custom date range:

```bash
python src/apod_pipeline.py --start-date 2024-10-01 --end-date 2024-10-31 --database apod.db
```

Or anchor a range to a start date (30 days by default):

```bash
python src/apod_pipeline.py --start-date 2024-10-01 --days 45 --database apod.db
```

### Options
- `--days` (default 30) sets the range length when only one or no boundary is supplied.
- `--start-date` / `--end-date` accept `YYYY-MM-DD` values.
- `--api-key` overrides the environment/default key.
- `--max-retries` and `--retry-wait` control basic retry behavior for rate limiting or transient errors.

## Data quality
- Run automated checks and emit reports to `data/`:
  ```bash
  python src/data_quality.py --database data/apod.db --report-json data/data_quality_report.json --report-md data/data_quality_report.md
  ```
- Checks: missing required fields (`date`, `title`, `media_type`, `url`), invalid/out-of-range dates, duplicate dates, invalid media types, and empty strings. Reports are generated in both JSON and Markdown.

## Analysis notebook
- Explore EDA and visualizations in `docs/apod_eda.ipynb` (word frequencies, media mix over time, weekday patterns, copyright distribution).
- Open in VS Code or Jupyter after ensuring `data/apod.db` exists.

## Bonus features implemented
- Simple Flask web interface (`src/web_app.py`) to browse APOD entries with filters and on-the-fly sentiment (VADER) for explanations.
- NLP sentiment analysis via VADER; visible in the web UI and available for further analysis in notebooks.
- Mars Rover Photos integration (`src/mars_photos.py`) to pull another NASA endpoint into `data/mars_photos.json`.
- Scheduling guidance for automated daily collection via Windows Task Scheduler.

## Database schema
Table `apod_entries`:

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

## What it does
- Calls the APOD API with a date range to stay within rate limits while collecting multiple days at once.
- Requests thumbnails for video entries so media is always represented.
- Creates an `apod_entries` table (if missing) and upserts records keyed by `date` with a small index on `media_type` to speed up queries.

## Notes
- The pipeline stores APOD metadata; if you want images locally you can extend the script to download the `url`/`hdurl` fields.
- The database defaults to `apod.db` in the repository root, but you can point to any writable path.
- Unit tests live in `tests/`; run `pytest` to execute the suite.
