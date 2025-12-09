import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List

import requests

API_URL = "https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos"
DEFAULT_API_KEY = "1r44g8KrnaLuckayDcinAftBK4LRR9C4Di7zG2za"


def fetch_mars_photos(date: dt.date, api_key: str) -> List[Dict[str, Any]]:
    params = {"earth_date": date.isoformat(), "api_key": api_key}
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("photos", [])
    return [
        {
            "id": item.get("id"),
            "img_src": item.get("img_src"),
            "earth_date": item.get("earth_date"),
            "rover": item.get("rover", {}).get("name"),
            "camera": item.get("camera", {}).get("full_name"),
        }
        for item in data
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Mars rover photos for a given Earth date.")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Earth date YYYY-MM-DD (default: today)")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="NASA API key")
    parser.add_argument("--output", default="data/mars_photos.json", help="Output JSON path")
    args = parser.parse_args()

    target_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
    photos = fetch_mars_photos(target_date, args.api_key)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(photos, indent=2), encoding="utf-8")
    print(f"Saved {len(photos)} photos to {out_path}")


if __name__ == "__main__":
    main()
