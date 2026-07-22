"""Leak search - scrape public breach data + paste site search."""
import re, asyncio, random
from urllib.parse import quote
import httpx
from utils.config import REQUEST_TIMEOUT
from utils.cache import get_cached, set_cache, make_key

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"


async def _search_psbdmp(email: str, client: httpx.AsyncClient) -> list[dict]:
    """Search psbdmp.ws for leaked passwords (free, no API key)."""
    results = []
    try:
        resp = await client.get(f"https://psbdmp.ws/api/v3/search/{email}", timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("data", [])[:20]:
                results.append({
                    "source": "Psbdmp",
                    "id": item.get("id"),
                    "date": item.get("date", ""),
                    "text_preview": str(item.get("text", ""))[:300],
                    "url": f"https://psbdmp.ws/{item.get('id')}" if item.get("id") else None,
                })
    except Exception:
        pass
    return results


async def _search_xposed(email: str, client: httpx.AsyncClient) -> list[dict]:
    """Search XposedOrNot for public breach data."""
    results = []
    try:
        resp = await client.get(f"https://api.xposedornot.com/v1/check-email/{email}", timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            breaches = data.get("Breaches", [])
            if isinstance(breaches, list):
                for b in breaches[:20]:
                    results.append({
                        "source": "XposedOrNot",
                        "breach": b,
                        "breaches_count": len(breaches),
                    })
    except Exception:
        pass
    return results


async def _search_holehe(email: str, client: httpx.AsyncClient) -> list[dict]:
    """Check if email is registered on various sites by checking sign-up pages."""
    results = []
    sites_to_check = [
        {"name": "Twitter/X", "url": f"https://api.x.com/i/users/email_available.json?email={quote(email)}"},
        {"name": "Spotify", "url": f"https://www.spotify.com/signup/validate?email={quote(email)}"},
        {"name": "Pinterest", "url": f"https://www.pinterest.com/resource/EmailExistsResource/get/?data=%7B%22options%22%3A%7B%22email%22%3A%22{quote(email)}%22%7D%7D"},
        {"name": "Imgur", "url": f"https://imgur.com/signin/ajax_email_available?email={quote(email)}"},
        {"name": "Patreon", "url": f"https://www.patreon.com/api/auth/check_email?email={quote(email)}"},
        {"name": "Flickr", "url": f"https://identity.flickr.com/checkemail?email={quote(email)}"},
        {"name": "Gravatar", "url": f"https://en.gravatar.com/{email_hash(email)}.json"},
        {"name": "GitHub", "url": f"https://api.github.com/search/users?q={quote(email)}+in:email"},
        {"name": "WordPress", "url": f"https://public-api.wordpress.com/rest/v1.1/users/{quote(email)}/auth-options"},
    ]

    for site in sites_to_check:
        try:
            resp = await client.get(site["url"], timeout=10)
            text = resp.text.lower()
            if any(w in text for w in ["taken", "registered", "exists", "already", "unavailable"]):
                results.append({"site": site["name"], "registered": True})
        except Exception:
            pass
    return results


def email_hash(email: str) -> str:
    import hashlib
    return hashlib.md5(email.encode()).hexdigest()


async def _search_breach_directory(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search for mentions in public breach directories via Google caching."""
    results = []
    search_query = f'"{query}" site:breachdirectory.org OR site:leak-lookup.com OR site:leakcheck.net'
    try:
        headers = {"User-Agent": UA}
        resp = await client.get(f"https://html.duckduckgo.com/html/?q={quote(search_query)}", headers=headers, timeout=15)
        if resp.status_code == 200:
            urls = re.findall(
                r'uddg=([^"&\s]+)',
                resp.text,
            )
            for u in list(set(urls))[:10]:
                u_decoded = httpx.URL(f"?uddg={u}").params.get("uddg", u)
                if u_decoded:
                    results.append({"source": "BreachDirectory", "url": u_decoded})
    except Exception:
        pass
    return results


async def search_leaks(target: str) -> dict:
    target = target.strip().lower()
    cache_key = make_key("leaks2", target)
    cached = get_cached(cache_key, ttl_hours=24)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        if "@" in target:
            psbdmp, xposed, holehe = await asyncio.gather(
                _search_psbdmp(target, client),
                _search_xposed(target, client),
                _search_holehe(target, client),
                return_exceptions=True,
            )
            psbdmp = psbdmp if isinstance(psbdmp, list) else []
            xposed = xposed if isinstance(xposed, list) else []
            holehe = holehe if isinstance(holehe, list) else []
        else:
            psbdmp, xposed, holehe = [], [], []

        breach_dirs = await _search_breach_directory(target, client)
        breach_dirs = breach_dirs if isinstance(breach_dirs, list) else []

    # Also generate manual search URLs for offline databases
    encoded = quote(target)
    leak_dbs = [
        {"name": "Dehashed", "url": f"https://dehashed.com/search?query={encoded}"},
        {"name": "SnusBase", "url": f"https://snusbase.com/search?term={encoded}"},
        {"name": "LeakCheck", "url": f"https://leakcheck.io/search?query={encoded}"},
        {"name": "IntelX", "url": f"https://intelx.io/?s={encoded}"},
    ]

    result = {
        "target": target,
        "leak_databases": leak_dbs,
        "psbdmp_results": psbdmp,
        "psbdmp_count": len(psbdmp),
        "xposed_results": xposed,
        "xposed_count": len(xposed),
        "holehe_sites": holehe,
        "holehe_registered": len(holehe),
        "breach_directory_findings": breach_dirs,
        "total_leak_hits": len(psbdmp) + len(xposed) + len(breach_dirs),
    }

    set_cache(cache_key, result)
    return result


async def search_documents(query: str) -> dict:
    query = query.strip()
    encoded = quote(query)
    cache_key = make_key("docs2", query.lower())
    cached = get_cached(cache_key, ttl_hours=24)
    if cached:
        return cached

    results = {"query": query, "findings": []}

    doc_searches = [
        f'site:docs.google.com "{query}"',
        f'site:pastebin.com "{query}"',
        f'site:scribd.com "{query}"',
        f'site:slideshare.net "{query}"',
        f'site:ghostbin.com "{query}"',
    ]

    headers = {"User-Agent": UA}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=headers) as client:
        for sq in doc_searches:
            try:
                resp = await client.get(f"https://html.duckduckgo.com/html/?q={quote(sq)}", timeout=15)
                if resp.status_code == 200:
                    links = re.findall(r'uddg=([^"&\s]+)', resp.text)
                    for raw in list(set(links))[:8]:
                        u = httpx.URL(f"?uddg={raw}").params.get("uddg", raw)
                        if u and u.startswith("http"):
                            results["findings"].append({"query": sq, "url": u})
            except Exception:
                continue

    results["total_findings"] = len(results["findings"])
    set_cache(cache_key, results)
    return results
