import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")
USER_AGENT = os.getenv("USER_AGENT", "PrOSINT/1.0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "24"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "10"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))


def get_headers():
    return {"User-Agent": USER_AGENT}
