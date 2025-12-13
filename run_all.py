#!/usr/bin/env python
"""Simple orchestrator to run the main project steps sequentially.
- Fetch APOD data into SQLite
- Run data quality checks (JSON/MD)
- (Optional) Fetch Mars photos sample
- Run pytest
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(title: str, cmd: list[str]) -> int:
    print(f"\n=== {title} ===")
    print("Command:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print(f"{title} completed successfully.\n")
    else:
        print(f"{title} failed with code {result.returncode}.\n")
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NASA APOD pipeline steps sequentially.")
    parser.add_argument("--database", default=str(ROOT / "data" / "apod.db"), help="SQLite database path")
    parser.add_argument(
        "--skip-mars", action="store_true", help="Skip optional Mars photos fetch step (avoids empty results if no photos that day)."
    )
    parser.add_argument(
        "--mars-date", default=None, help="Earth date YYYY-MM-DD for Mars photos (optional; overrides --mars-sol)."
    )
    parser.add_argument(
        "--mars-sol", type=int, default=1000, help="Mars sol for photos when date is not provided (default: 1000 for Curiosity)."
    )
    parser.add_argument("--mars-rover", default="curiosity", help="Rover name: curiosity|perseverance|opportunity|spirit")
    parser.add_argument("--api-key", default=None, help="NASA API key; falls back to env/NASA_APOD_FALLBACK inside scripts.")
    args = parser.parse_args()

    steps: list[tuple[str, list[str]]] = []

    pipeline_cmd = [
        PYTHON,
        str(ROOT / "src" / "apod_pipeline.py"),
        "--database",
        args.database,
    ]
    if args.api_key:
        pipeline_cmd += ["--api-key", args.api_key]
    steps.append(("Fetch APOD", pipeline_cmd))

    dq_cmd = [
        PYTHON,
        str(ROOT / "src" / "data_quality.py"),
        "--database",
        args.database,
        "--report-json",
        str(ROOT / "data" / "data_quality_report.json"),
        "--report-md",
        str(ROOT / "data" / "data_quality_report.md"),
    ]
    steps.append(("Data Quality", dq_cmd))

    if not args.skip_mars:
        mars_cmd = [
            PYTHON,
            str(ROOT / "src" / "mars_photos.py"),
            "--rover",
            args.mars_rover,
            "--output",
            str(ROOT / "data" / "mars_photos.json"),
        ]
        if args.mars_date:
            mars_cmd += ["--date", args.mars_date]
        else:
            mars_cmd += ["--sol", str(args.mars_sol)]
        if args.api_key:
            mars_cmd += ["--api-key", args.api_key]
        steps.append(("Mars Photos (optional)", mars_cmd))

    steps.append(("Pytest", [PYTHON, "-m", "pytest", "-q"]))

    failures = 0
    for title, cmd in steps:
        code = run(title, cmd)
        if code != 0:
            failures += 1
            break

    if failures:
        sys.exit(1)
    print("All steps completed.")


if __name__ == "__main__":
    main()
