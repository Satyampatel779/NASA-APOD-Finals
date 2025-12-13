"""Data quality checks for the APOD SQLite table.

This script reads the `apod_entries` table and produces a small report that answers
simple questions like:
- Are any required fields missing?
- Do any dates look invalid or out of range?
- Did duplicate days sneak in?
- Are there unexpected media_type values?

Outputs:
- A JSON report (easy for programs to read)
- A Markdown report (easy for humans to read)
"""

import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

APOD_EPOCH = dt.date(1995, 6, 16)
ALLOWED_MEDIA_TYPES = {"image", "video", "other"}


def _load_dataframe(db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    with sqlite3.connect(db_path) as con:
        return pd.read_sql_query("SELECT * FROM apod_entries", con)


def _parse_date_safe(raw: str) -> Optional[dt.date]:
    try:
        return dt.datetime.strptime(raw, "%Y-%m-%d").date()
    except Exception:
        return None


def validate_apod(df: pd.DataFrame) -> Dict[str, any]:
    report: Dict[str, any] = {
        "total_rows": int(df.shape[0]),
        "missing": {},
        "invalid_dates": {},
        "duplicates": {},
        "invalid_media_type": {},
        "empty_strings": {},
    }

    required_fields = ["date", "title", "media_type", "url"]
    for field in required_fields:
        missing_rows = df[df[field].isna()].shape[0]
        report["missing"][field] = int(missing_rows)

    # dates
    parsed_dates: List[Optional[dt.date]] = [_parse_date_safe(x) for x in df["date"].fillna("")]
    invalid_format_idx = [i for i, d in enumerate(parsed_dates) if d is None]
    today = dt.date.today()
    out_of_range_idx = [
        i for i, d in enumerate(parsed_dates) if d is not None and (d < APOD_EPOCH or d > today)
    ]
    report["invalid_dates"] = {
        "invalid_format_count": len(invalid_format_idx),
        "out_of_range_count": len(out_of_range_idx),
    }

    # duplicates by date
    dup_dates = df[df.duplicated(subset=["date"], keep=False)]["date"].tolist()
    report["duplicates"] = {"by_date": len(dup_dates), "unique_dates": len(set(dup_dates))}

    # media type validation
    invalid_media = df[~df["media_type"].isin(ALLOWED_MEDIA_TYPES)]
    report["invalid_media_type"] = {
        "count": int(invalid_media.shape[0]),
        "samples": invalid_media[["date", "media_type"]].head(5).to_dict(orient="records"),
    }

    # empty string checks (after stripping)
    for field in ["title", "explanation", "url"]:
        empties = df[df[field].fillna("").str.strip() == ""]
        report["empty_strings"][field] = int(empties.shape[0])

    return report


def save_report(report: Dict[str, any], json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def save_markdown(report: Dict[str, any], md_path: Path) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# APOD Data Quality Report", ""]
    lines.append(f"Total rows: {report.get('total_rows', 0)}")
    lines.append("")

    lines.append("## Missing Required Fields")
    for field, count in report.get("missing", {}).items():
        lines.append(f"- {field}: {count}")
    lines.append("")

    lines.append("## Invalid Dates")
    inv = report.get("invalid_dates", {})
    lines.append(f"- Invalid format: {inv.get('invalid_format_count', 0)}")
    lines.append(f"- Out of range: {inv.get('out_of_range_count', 0)}")
    lines.append("")

    lines.append("## Duplicate Dates")
    dup = report.get("duplicates", {})
    lines.append(f"- Duplicate rows: {dup.get('by_date', 0)}")
    lines.append(f"- Unique duplicated dates: {dup.get('unique_dates', 0)}")
    lines.append("")

    lines.append("## Invalid Media Types")
    inv_media = report.get("invalid_media_type", {})
    lines.append(f"- Count: {inv_media.get('count', 0)}")
    samples = inv_media.get("samples", [])
    if samples:
        lines.append("- Samples:")
        for sample in samples:
            lines.append(f"  - {sample}")
    lines.append("")

    lines.append("## Empty Strings")
    for field, count in report.get("empty_strings", {}).items():
        lines.append(f"- {field}: {count}")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run data quality checks on the APOD SQLite table and write JSON/Markdown reports."
    )
    parser.add_argument("--database", default="data/apod.db", help="Path to SQLite database.")
    parser.add_argument("--report-json", default="data/data_quality_report.json", help="Path to JSON report output.")
    parser.add_argument("--report-md", default="data/data_quality_report.md", help="Path to Markdown summary.")
    args = parser.parse_args()

    db_path = Path(args.database)
    df = _load_dataframe(db_path)
    report = validate_apod(df)
    save_report(report, Path(args.report_json))
    save_markdown(report, Path(args.report_md))


if __name__ == "__main__":
    main()
