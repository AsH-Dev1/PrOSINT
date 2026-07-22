import json
from pathlib import Path
from datetime import datetime, timedelta

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_key(*parts):
    return "-".join(str(p).replace("/", "_").replace(" ", "_") for p in parts)


def _cache_path(key):
    return CACHE_DIR / f"{key}.json"


def get_cached(key, ttl_hours=24):
    path = _cache_path(key)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
        cached_at = datetime.fromisoformat(data["_cached_at"])
        if datetime.now() - cached_at > timedelta(hours=ttl_hours):
            path.unlink(missing_ok=True)
            return None
        return data["value"]
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def set_cache(key, value):
    path = _cache_path(key)
    data = {"_cached_at": datetime.now().isoformat(), "value": value}
    path.write_text(json.dumps(data, ensure_ascii=False, default=str))


def make_key(*parts):
    return _cache_key(*parts)
