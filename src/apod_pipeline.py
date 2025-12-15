"""
so here what i'm doing is to download NASA Astronomy Picture of the Day (APOD) entries for a date range
and i'm storing them in a local SQLite database.

my notes:
- "SQLite" is a single-file database (here: `data/apod.db`).
- "Upsert" means: insert a new row, or update the existing row if that date already exists.
- The NASA API can rate-limit requests. If I hit a rate limit, I should wait and retry.
"""

import argparse
import datetime as dt
import logging
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from src.config import get_env

API_URL = "https://api.nasa.gov/planetary/apod"
DEFAULT_API_KEY = get_env("NASA_API_KEY", "DEMO_KEY")
logger = logging.getLogger(__name__)


def parse_date(value: str) -> dt.date:
    try:
        return dt.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}', expected YYYY-MM-DD") from exc


def resolve_date_range(days: int, start: Optional[dt.date], end: Optional[dt.date]) -> Tuple[dt.date, dt.date]:
    today = dt.date.today()
    if days <= 0:
        raise argparse.ArgumentTypeError("--days must be positive")

    if start and end:
        pass
    elif start and not end:
        end = start + dt.timedelta(days=days - 1)
    elif end and not start:
        start = end - dt.timedelta(days=days - 1)
    else:
        end = today
        start = today - dt.timedelta(days=days - 1)

    if end > today:
        end = today
    if start > end:
        raise argparse.ArgumentTypeError("start date must be on or before end date")
    return start, end


def fetch_apod_range(
    start_date: dt.date,
    end_date: dt.date,
    api_key: str,
    thumbs: bool = True,
    retries: int = 3,
    retry_wait: int = 5,
) -> List[Dict[str, Any]]:
    params = {
        "api_key": api_key,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    if thumbs:
        params["thumbs"] = "true"

    payload: Any = None
    last_error: Optional[BaseException] = None

    for attempt in range(retries + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=30)
        except requests.RequestException as exc:  # network issue
            last_error = exc
            logger.warning("Request failed (attempt %s/%s): %s", attempt + 1, retries + 1, exc)
            if attempt == retries:
                raise
            time.sleep(retry_wait)
            continue

        if response.status_code == 429 and attempt < retries:
            wait_seconds = int(response.headers.get("Retry-After", retry_wait))
            logger.warning("Rate limited by NASA API, retrying in %s seconds", wait_seconds)
            time.sleep(wait_seconds)
            continue

        if response.status_code >= 500 and attempt < retries:
            logger.warning(
                "NASA API returned %s (attempt %s/%s), retrying in %s seconds",
                response.status_code,
                attempt + 1,
                retries + 1,
                retry_wait,
            )
            time.sleep(retry_wait)
            continue

        try:
            payload = response.json()
        except ValueError as exc:
            snippet = response.text[:200]
            raise RuntimeError(f"Non-JSON response from NASA API: {snippet}") from exc

        if response.status_code != 200:
            message = payload if isinstance(payload, dict) else response.text
            raise RuntimeError(f"NASA API returned {response.status_code}: {message}")
        break
    else:
        raise RuntimeError(f"Failed to fetch NASA APOD after {retries + 1} attempts: {last_error}")

    entries = payload if isinstance(payload, list) else [payload]
    normalized: List[Dict[str, Any]] = []
    for entry in entries:
        date_value = entry.get("date")
        title = entry.get("title")
        if not date_value or not title:
            logger.debug("Skipping entry missing date or title: %s", entry)
            continue
        normalized.append(
            {
                "date": date_value,
                "title": title,
                "explanation": entry.get("explanation"),
                "media_type": entry.get("media_type"),
                "url": entry.get("url"),
                "hdurl": entry.get("hdurl"),
                "thumbnail_url": entry.get("thumbnail_url"),
                "service_version": entry.get("service_version"),
                "copyright": entry.get("copyright"),
            }
        )
    return normalized


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS apod_entries (
            date TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            explanation TEXT,
            media_type TEXT,
            url TEXT,
            hdurl TEXT,
            thumbnail_url TEXT,
            service_version TEXT,
            copyright TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apod_media_type ON apod_entries (media_type);
        """
    )


def persist_entries(db_path: str, entries: Iterable[Dict[str, Any]]) -> int:
    entries = list(entries)
    if not entries:
        return 0

    with sqlite3.connect(db_path) as connection:
        ensure_schema(connection)
        connection.executemany(
            """
            INSERT INTO apod_entries (
                date, title, explanation, media_type, url, hdurl, thumbnail_url, service_version, copyright
            )
            VALUES (
                :date, :title, :explanation, :media_type, :url, :hdurl, :thumbnail_url, :service_version, :copyright
            )
            ON CONFLICT(date) DO UPDATE SET
                title=excluded.title,
                explanation=excluded.explanation,
                media_type=excluded.media_type,
                url=excluded.url,
                hdurl=excluded.hdurl,
                thumbnail_url=excluded.thumbnail_url,
                service_version=excluded.service_version,
                copyright=excluded.copyright,
                fetched_at=CURRENT_TIMESTAMP;
            """,
            entries,
        )
        connection.commit()
    return len(entries)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Fetch NASA APOD entries for a date range and upsert them into a SQLite database. "
            "Defaults to the most recent 30 days if no dates are provided."
        )
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to fetch when start/end dates are not provided (default: 30).",
    )
    parser.add_argument("--start-date", type=parse_date, help="YYYY-MM-DD start date.")
    parser.add_argument("--end-date", type=parse_date, help="YYYY-MM-DD end date.")
    parser.add_argument(
        "--database",
        default="apod.db",
        help="SQLite database file path (will be created if missing).",
    )
    parser.add_argument(
        "--api-key",
        default=DEFAULT_API_KEY,
        help="NASA API key. Defaults to env var NASA_API_KEY (falls back to DEMO_KEY if not set).",
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Retry attempts on transient failures.")
    parser.add_argument("--retry-wait", type=int, default=5, help="Seconds to wait between retries.")
    args = parser.parse_args()

    start_date, end_date = resolve_date_range(args.days, args.start_date, args.end_date)
    logger.info("Fetching APOD entries from %s to %s", start_date, end_date)

    entries = fetch_apod_range(
        start_date=start_date,
        end_date=end_date,
        api_key=args.api_key,
        thumbs=True,
        retries=args.max_retries,
        retry_wait=args.retry_wait,
    )
    stored = persist_entries(args.database, entries)
    logger.info("Stored %s entries into %s", stored, args.database)


if __name__ == "__main__":
    main()
