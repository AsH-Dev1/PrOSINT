"""Company OSINT - employees, domains, technologies, LinkedIn, Crunchbase."""
import re, asyncio
from urllib.parse import quote
import httpx
from utils.cache import get_cached, set_cache, make_key

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"

async def _ddg_search(query: str) -> list[dict]:
    results = []
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent":UA,"Accept":"text/html"}, verify=False) as c:
            r = await c.get(f"https://html.duckduckgo.com/html/?q={quote(query)}")
            if r.status_code != 200: return results
            links = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.I|re.S)
            snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', r.text, re.I|re.S)
            for i, (raw, raw_t) in enumerate(links[:25]):
                m = re.search(r'uddg=([^&\'"]+)', raw)
                from urllib.parse import unquote
                url = unquote(m.group(1)) if m else ""
                if not url: continue
                title = re.sub(r'<[^>]+>', '', raw_t).strip()
                s = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                results.append({"title": title, "url": url, "snippet": s[:300]})
    except: pass
    return results


async def company_search(name: str) -> dict:
    name = name.strip()
    encoded = quote(name)
    result = {"company": name, "web_mentions": [], "social_search_urls": [], "info_links": []}

    # Web search
    queries = [f'"{name}" company', f'"{name}" employees linkedin', f'"{name}" crunchbase']
    for q in queries:
        result["web_mentions"].extend(await _ddg_search(q))

    # Social search URLs
    result["social_search_urls"] = [
        {"platform": "LinkedIn", "url": f"https://www.linkedin.com/company/{name.replace(' ','-').lower()}"},
        {"platform": "Glassdoor", "url": f"https://www.glassdoor.com/Search/results.htm?keyword={encoded}"},
        {"platform": "Crunchbase", "url": f"https://www.crunchbase.com/organization/{name.replace(' ','-').lower()}"},
        {"platform": "GitHub Org", "url": f"https://github.com/{name.replace(' ','').lower()}"},
        {"platform": "Twitter/X", "url": f"https://x.com/search?q={encoded}&f=user"},
        {"platform": "Instagram", "url": f"https://www.instagram.com/{name.replace(' ','').lower()}/"},
        {"platform": "YouTube", "url": f"https://www.youtube.com/results?search_query={encoded}"},
        {"platform": "TikTok", "url": f"https://www.tiktok.com/search?q={encoded}"},
    ]

    result["info_links"] = [
        {"name": "WHOIS Domain", "url": f"https://www.whois.com/whois/{name.replace(' ','').lower()}.com"},
        {"name": "OpenCorporates", "url": f"https://opencorporates.com/companies?q={encoded}"},
        {"name": "RocketReach", "url": f"https://rocketreach.co/{name.replace(' ','-').lower()}-profile_b5c71e1cf42e0b9a"},
        {"name": "BuiltWith", "url": f"https://builtwith.com/{name.replace(' ','').lower()}.com"},
        {"name": "Wappalyzer", "url": f"https://www.wappalyzer.com/lookup/{name.replace(' ','').lower()}.com"},
    ]

    result["total_sources"] = len(result["web_mentions"]) + len(result["social_search_urls"]) + len(result["info_links"])
    return result
