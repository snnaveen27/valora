import asyncio
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure env is loaded from project root
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / '.env')

from backend.services.apify_google_maps import ApifyGoogleMapsService

async def main():
    service = ApifyGoogleMapsService()
    print("APIFY_TOKEN_LOADED=", bool(service.api_token))

    localities = [
        "Koramangala",
        "Whitefield",
        "Electronic City",
        "HSR Layout",
        "Indiranagar",
    ]

    results = []
    for loc in localities:
        print(f"Fetching {loc}...")
        try:
            data = await service.fetch_location_data(loc)
            ok = isinstance(data, dict) and not data.get("error")
            print(f"  -> {'OK' if ok else 'ERROR'}")
            results.append({
                "location": loc,
                "ok": ok,
                "places_count": (data.get("places_count") if isinstance(data, dict) else None)
            })
        except Exception as e:
            print(f"  -> ERROR: {e}")
            results.append({"location": loc, "ok": False, "error": str(e)})
        await asyncio.sleep(1)

    # Print summary and the latest aggregate file path if present
    print("SUMMARY:")
    print(json.dumps(results, indent=2))
    data_dir = Path("data/location_intelligence")
    if data_dir.exists():
        aggs = sorted(data_dir.glob("bangalore_aggregate_*.json"), key=lambda p: p.stat().st_mtime)
        if aggs:
            print("AGGREGATE_FILE=", str(aggs[-1]))

if __name__ == "__main__":
    asyncio.run(main())
