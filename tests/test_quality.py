import pandas as pd

from src.data_quality import validate_apod


def test_validate_apod_flags_missing_and_invalid():
    df = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "title": "Ok",
                "explanation": "Nice image",
                "media_type": "image",
                "url": "http://example.com/a",
                "hdurl": None,
                "thumbnail_url": None,
                "service_version": "v1",
                "copyright": "NASA",
                "fetched_at": None,
            },
            {
                "date": "not-a-date",
                "title": "Missing url",
                "explanation": "",
                "media_type": "weird",
                "url": None,
                "hdurl": None,
                "thumbnail_url": None,
                "service_version": "v1",
                "copyright": None,
                "fetched_at": None,
            },
            {
                "date": "2024-01-01",
                "title": "Duplicate date",
                "explanation": "",
                "media_type": "video",
                "url": "http://example.com/b",
                "hdurl": None,
                "thumbnail_url": None,
                "service_version": "v1",
                "copyright": None,
                "fetched_at": None,
            },
        ]
    )

    report = validate_apod(df)

    assert report["missing"]["url"] == 1
    assert report["invalid_dates"]["invalid_format_count"] == 1
    assert report["duplicates"]["by_date"] >= 2
    assert report["invalid_media_type"]["count"] == 1
    assert report["empty_strings"]["explanation"] >= 2