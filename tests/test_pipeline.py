import argparse
import datetime as dt
import sqlite3
from pathlib import Path

import pytest

from src import apod_pipeline as pipeline


def test_resolve_date_range_with_start_only():
    start = dt.date(2024, 1, 1)
    expected_end = start + dt.timedelta(days=29)
    resolved_start, resolved_end = pipeline.resolve_date_range(days=30, start=start, end=None)
    assert resolved_start == start
    assert resolved_end == expected_end


def test_resolve_date_range_invalid_order():
    start = dt.date(2024, 1, 5)
    end = dt.date(2024, 1, 1)
    with pytest.raises(argparse.ArgumentTypeError):
        pipeline.resolve_date_range(days=5, start=start, end=end)


def test_persist_entries_upserts(tmp_path: Path):
    db_path = tmp_path / "apod.db"
    entries = [
        {
            "date": "2024-01-01",
            "title": "First",
            "explanation": "One",
            "media_type": "image",
            "url": "http://example.com/1",
            "hdurl": None,
            "thumbnail_url": None,
            "service_version": "v1",
            "copyright": None,
        }
    ]
    # initial insert
    inserted = pipeline.persist_entries(str(db_path), entries)
    assert inserted == 1

    # upsert with new title same date
    entries[0]["title"] = "First-updated"
    inserted = pipeline.persist_entries(str(db_path), entries)
    assert inserted == 1

    with sqlite3.connect(db_path) as con:
        title = con.execute("SELECT title FROM apod_entries WHERE date='2024-01-01'").fetchone()[0]
    assert title == "First-updated"