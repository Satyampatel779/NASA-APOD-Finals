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

## What it does
- Calls the APOD API with a date range to stay within rate limits while collecting multiple days at once.
- Requests thumbnails for video entries so media is always represented.
- Creates an `apod_entries` table (if missing) and upserts records keyed by `date` with a small index on `media_type` to speed up queries.

## Notes
- The pipeline stores APOD metadata; if you want images locally you can extend the script to download the `url`/`hdurl` fields.
- The database defaults to `apod.db` in the repository root, but you can point to any writable path.
