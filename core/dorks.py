"""Google Dorks - Execute real queries via DuckDuckGo with clean URL extraction."""
import re, asyncio, random
from urllib.parse import quote, unquote
import httpx
from utils.cache import get_cached, set_cache, make_key

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
]

DORK_TEMPLATES = {
    "resume_cv": {"label": "CV / Resume", "query": '"{name}" filetype:pdf (resume OR cv OR curriculum)'},
    "social_media": {"label": "Social Media", "query": '"{name}" (site:linkedin.com OR site:facebook.com OR site:twitter.com OR site:x.com OR site:instagram.com)'},
    "forums": {"label": "Forums & Communities", "query": '"{name}" (site:reddit.com OR site:news.ycombinator.com OR site:stackoverflow.com OR site:github.com)'},
    "public_records": {"label": "Public Records", "query": '"{name}" (phone OR address OR birthday OR born OR location)'},
    "publications": {"label": "Publications & Docs", "query": '"{name}" (site:docs.google.com OR site:slideshare.net OR site:scribd.com OR site:academia.edu)'},
    "news_blogs": {"label": "News & Blogs", "query": '"{name}" (site:medium.com OR site:substack.com OR site:dev.to OR site:blogspot.com)'},
    "paste_leaks": {"label": "Pastes & Leaks", "query": '"{name}" (site:pastebin.com OR site:justpaste.it OR site:controlc.com)'},
    "email_discovery": {"label": "Email Discovery", "query": '"{name}" (@gmail.com OR @yahoo.com OR @hotmail.com OR @outlook.com OR @protonmail.com)'},
    "github_code": {"label": "Code & Commits", "query": '"{name}" site:github.com (commits OR pull OR issues OR gist OR code)'},
    "linkedin": {"label": "LinkedIn Profiles", "query": '"{name}" site:linkedin.com/in'},
}


async def _search_ddg(query: str, max_results: int = 30) -> list[dict]:
    """Search DuckDuckGo with quick timeout."""
    results = []
    headers = {"User-Agent": random.choice(UA_LIST), "Accept": "text/html", "Accept-Language": "en-US"}
    
    try:
        async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True, verify=False) as c:
            resp = await c.get(f"https://lite.duckduckgo.com/lite/?q={quote(query)}")
            if resp.status_code != 200: return results
            text = resp.text
            links = re.findall(r'<a[^>]*rel="nofollow"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', text, re.I|re.S)
            snippets = re.findall(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', text, re.I|re.S)
            
            for i, (raw_url, raw_title) in enumerate(links[:max_results]):
                clean_url = raw_url
                m = re.search(r'uddg=([^&\'"]+)', raw_url)
                if m: clean_url = unquote(m.group(1))
                if not clean_url or not clean_url.startswith("http"): continue
                if "duckduckgo.com" in clean_url: continue
                title = re.sub(r'<[^>]+>', '', raw_title).strip() or "Untitled"
                s = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                results.append({"title": title[:200], "url": clean_url, "snippet": s[:400], "source": "DuckDuckGo"})
    except asyncio.TimeoutError:
        pass
    except Exception:
        pass
    
    return results


def _extract_clean_url(raw: str) -> str:
    """Extract the real URL from DDG's encoded href."""
    # DDG encodes hrefs as //duckduckgo.com/l/?uddg=REAL_URL&rut=...
    # or just as regular URLs
    m = re.search(r'uddg=([^&\'"]+)', raw)
    if m:
        return unquote(m.group(1))
    # It might also be a direct URL
    raw = raw.strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    if raw.startswith("http"):
        return raw
    return ""


async def execute_dork(name: str, category: str | None = None) -> dict:
    if category and category in DORK_TEMPLATES:
        templates = {category: DORK_TEMPLATES[category]}
    else:
        templates = DORK_TEMPLATES

    all_results = {}
    total = 0

    async def _process_dork(cat, cfg):
        query = cfg["query"].replace("{name}", name)
        from core.search_engine import curl_search
        try:
            results = await asyncio.wait_for(curl_search(query, timeout=10), timeout=12)
        except (asyncio.TimeoutError, Exception):
            results = []
        return cat, {
            "label": cfg["label"],
            "query": query,
            "results_count": len(results),
            "results": results[:15],
        }

    tasks = [_process_dork(cat, cfg) for cat, cfg in templates.items()]
    batch_results = await asyncio.gather(*tasks)

    for cat, data in batch_results:
        all_results[cat] = data
        total += data["results_count"]

    return {
        "target": name,
        "dorks_executed": len(templates),
        "total_results": total,
        "results_by_category": all_results,
    }
