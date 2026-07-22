"""Breach Data Search v3 - multi-source public breach database scraping."""
import re, asyncio
from urllib.parse import quote, unquote
import httpx
from utils.cache import get_cached, set_cache, make_key

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"


async def _ddg_search(query: str) -> list[dict]:
    results = []
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": UA, "Accept": "text/html"}, verify=False) as c:
            r = await c.get(f"https://html.duckduckgo.com/html/?q={quote(query)}")
            if r.status_code != 200: return results
            links = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.I|re.S)
            for raw, raw_t in links[:20]:
                m = re.search(r'uddg=([^&\'"]+)', raw)
                url = unquote(m.group(1)) if m else ""
                if not url: continue
                title = re.sub(r'<[^>]+>', '', raw_t).strip()
                results.append({"title": title, "url": url})
    except: pass
    return results


async def search_breaches(target: str) -> dict:
    target = target.strip().lower()
    is_email = "@" in target
    encoded = quote(target)

    result = {"target": target, "target_type": "email" if is_email else "other", "findings": [], "manual_search_urls": []}

    # Psbdmp
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}, verify=False) as c:
            r = await c.get(f"https://psbdmp.ws/api/v3/search/{target}")
            if r.status_code == 200:
                data = r.json()
                for item in data.get("data", [])[:10]:
                    result["findings"].append({
                        "source": "Psbdmp", "date": item.get("date", ""),
                        "text_preview": str(item.get("text", ""))[:300],
                        "url": f"https://psbdmp.ws/{item.get('id')}" if item.get("id") else None,
                    })
    except: pass

    # XposedOrNot
    if is_email:
        try:
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}, verify=False) as c:
                r = await c.get(f"https://api.xposedornot.com/v1/check-email/{target}")
                if r.status_code == 200:
                    data = r.json()
                    for b in data.get("Breaches", [])[:10]:
                        result["findings"].append({"source": "XposedOrNot", "breach": b})
        except: pass

    # BreachDirectory scraping
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}, verify=False) as c:
            r = await c.get(f"https://breachdirectory.org/search?search={encoded}")
            if r.status_code == 200:
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r.text)
                for e in set(emails)[:10]:
                    result["findings"].append({"source": "BreachDirectory", "email_found": e})
    except: pass

    # Search for target on paste sites
    paste_results = await _ddg_search(f'"{target}" site:pastebin.com OR site:justpaste.it OR site:ghostbin.com')
    for p in paste_results[:10]:
        result["findings"].append({"source": "Paste Search", "url": p.get("url", ""), "title": p.get("title", "")[:100]})

    # Manual search URLs
    result["manual_search_urls"] = [
        {"name": "Dehashed", "url": f"https://dehashed.com/search?query={encoded}"},
        {"name": "SnusBase", "url": f"https://snusbase.com/search?term={encoded}"},
        {"name": "LeakCheck", "url": f"https://leakcheck.io/search?query={encoded}"},
        {"name": "IntelX", "url": f"https://intelx.io/?s={encoded}"},
        {"name": "BreachForums", "url": f"https://breachforums.st/search?q={encoded}"},
        {"name": "LeakPeek", "url": f"https://leakpeek.com/?search={encoded}"},
    ]

    result["total_findings"] = len(result["findings"])
    return result
