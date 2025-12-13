import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List

import requests

from src.config import get_env

DEFAULT_API_KEY = get_env("NASA_API_KEY", "DEMO_KEY")
DEFAULT_ROVER = "curiosity"


def fetch_mars_photos(
    api_key: str,
    rover: str,
    earth_date: dt.date | None = None,
    sol: int | None = None,
) -> List[Dict[str, Any]]:
    base_url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos"
    params: Dict[str, Any] = {"api_key": api_key}
    if earth_date:
        params["earth_date"] = earth_date.isoformat()
    if sol is not None:
        params["sol"] = sol

    try:
        resp = requests.get(base_url, params=params, timeout=30)
        if resp.status_code == 404:
            # No photos for that date/sol or rover; return empty instead of raising
            return []
        resp.raise_for_status()
    except requests.HTTPError as exc:
        snippet = resp.text[:200] if "resp" in locals() else str(exc)
        raise RuntimeError(f"NASA Mars API error {getattr(resp, 'status_code', '?')}: {snippet}") from exc

    data = resp.json().get("photos", [])
    return [
        {
            "id": item.get("id"),
            "img_src": item.get("img_src"),
            "earth_date": item.get("earth_date"),
            "sol": item.get("sol"),
            "rover": item.get("rover", {}).get("name"),
            "camera": item.get("camera", {}).get("full_name"),
        }
        for item in data
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Mars rover photos for a given Earth date or sol.")
    parser.add_argument("--date", help="Earth date YYYY-MM-DD (optional if --sol is set)")
    parser.add_argument("--sol", type=int, help="Martian sol (mission day) integer")
    parser.add_argument("--rover", default=DEFAULT_ROVER, help="Rover name: curiosity|opportunity|spirit|perseverance")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="NASA API key")
    parser.add_argument("--output", default="data/mars_photos.json", help="Output JSON path")
    args = parser.parse_args()

    if not args.date and args.sol is None:
        args.date = dt.date.today().isoformat()

    earth_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
    photos = fetch_mars_photos(
        api_key=args.api_key,
        rover=args.rover,
        earth_date=earth_date,
        sol=args.sol,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(photos, indent=2), encoding="utf-8")
    print(f"Saved {len(photos)} photos to {out_path} (rover={args.rover}, date={args.date}, sol={args.sol})")


if __name__ == "__main__":
    main()
