import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root and .env
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / '.env')

from backend.services.apify_google_maps import ApifyGoogleMapsService

async def main():
    svc = ApifyGoogleMapsService()
    print("APIFY_TOKEN_LOADED=", bool(svc.api_token))
    result = await svc.fetch_all_bangalore_locations()
    print("RESULT_KEYS=", list(result.keys()) if isinstance(result, dict) else type(result))
    out_dir = project_root / 'data' / 'location_intelligence'
    print("OUTPUT_DIR=", str(out_dir))
    if out_dir.exists():
        files = sorted([str(p) for p in out_dir.glob('*.json')])
        print("FILES=", files)

if __name__ == '__main__':
    asyncio.run(main())
