"""PII Reverse Search - Find all data linked to a CURP, SSN, phone, etc."""
import re, asyncio, random
from urllib.parse import quote, unquote
import httpx
from utils.cache import get_cached, set_cache, make_key

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"

# Patterns to detect PII types from input
PII_PATTERNS = {
    "curp": re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d{2}$', re.IGNORECASE),
    "ssn": re.compile(r'^\d{3}-\d{2}-\d{4}$'),
    "credit_card": re.compile(r'^[\d\s-]{13,19}$'),
    "phone": re.compile(r'^\+?\d{7,15}$'),
    "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
}


def detect_pii_type(value: str) -> str:
    """Auto-detect what type of PII the input is."""
    v = value.strip()
    if PII_PATTERNS["email"].match(v):
        return "email"
    if PII_PATTERNS["curp"].match(v):
        return "curp"
    if PII_PATTERNS["ssn"].match(v):
        return "ssn"
    if PII_PATTERNS["credit_card"].match(v):
        return "credit_card"
    if PII_PATTERNS["phone"].match(v):
        return "phone"
    return "unknown"


async def _ddg_search(query: str, max_results: int = 20) -> list[dict]:
    results = []
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": UA, "Accept": "text/html"}, verify=False) as c:
            r = await c.get(f"https://html.duckduckgo.com/html/?q={quote(query)}")
            if r.status_code != 200:
                return results
            links = re.findall(
                r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                r.text, re.IGNORECASE | re.DOTALL,
            )
            snippets = re.findall(
                r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                r.text, re.IGNORECASE | re.DOTALL,
            )
            for i, (raw, raw_title) in enumerate(links[:max_results]):
                clean = _extract_url(raw)
                if not clean: continue
                title = re.sub(r'<[^>]+>', '', raw_title).strip()
                s = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                results.append({"title": title, "url": clean, "snippet": s[:400], "source": "DuckDuckGo"})
    except: pass
    return results


def _extract_url(raw: str) -> str:
    m = re.search(r'uddg=([^&\'"]+)', raw)
    if m: return unquote(m.group(1))
    if raw.startswith("//"): return "https:" + raw
    if raw.startswith("http"): return raw
    return ""


async def _fetch_page(url: str, client: httpx.AsyncClient) -> dict:
    """Fetch a page and extract all PII-related data from it."""
    result = {"url": url, "emails": [], "names": [], "phones": [], "addresses": [],
               "other_ids": [], "raw_snippet": ""}
    try:
        r = await client.get(url, timeout=15, follow_redirects=True)
        if r.status_code != 200: return result
        text = r.text[:200000]
        result["raw_snippet"] = text[:800]

        # Extract emails
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        result["emails"] = list(set(e.lower() for e in emails if len(e) < 80))[:15]

        # Extract phone numbers
        phones = re.findall(r'\+?\d{1,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}', text)
        result["phones"] = list(set(p for p in phones if 7 < len(re.sub(r'[\s.-]', '', p)) < 16))[:10]

        # Extract potential names (Title Case patterns)
        names = re.findall(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})\b', text)
        result["names"] = list(set(n for n in names if len(n) > 6 and not any(w in n.lower() for w in
            ["the", "this", "that", "with", "from", "your", "what", "when", "where", "there",
             "their", "about", "would", "could", "should", "copyright", "reserved",
             "login", "register", "password", "username", "privacy", "terms", "policy"])))[:10]

        # Extract other IDs (CURP, SSN, passport-like)
        curps = re.findall(r'\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d{2}\b', text)
        ssns = re.findall(r'\b\d{3}-\d{2}-\d{4}\b', text)
        result["other_ids"] = list(set(curps + ssns))[:10]

        # Extract addresses (simple patterns)
        addresses = re.findall(
            r'\b\d{2,5}\s[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|blvd|boulevard|calle|carrera|diagonal|transversal|autopista|via|plaza)[\w\s,]*\b',
            text, re.IGNORECASE,
        )
        result["addresses"] = list(set(a.strip() for a in addresses if 10 < len(a) < 100))[:5]

    except: pass
    return result


async def reverse_pii_search(value: str) -> dict:
    """Search by PII value to find associated personal data."""
    value = value.strip()
    pii_type = detect_pii_type(value)

    result = {
        "target": value,
        "pii_type": pii_type,
        "web_results": [],
        "scraped_pages": [],
        "all_emails_found": [],
        "all_phones_found": [],
        "all_names_found": [],
        "all_ids_found": [],
    }

    # Web search for the exact value
    queries = [
        f'"{value}"',
        f'"{value}" site:pastebin.com OR site:justpaste.it OR site:ghostbin.com OR site:controlc.com',
        f'"{value}" site:reddit.com OR site:foroactivo.com OR site:forosdz.com',
    ]

    web_results = await asyncio.gather(*[_ddg_search(q) for q in queries])
    all_web = []
    seen_urls = set()
    for wr in web_results:
        for w in wr:
            if w["url"] not in seen_urls:
                seen_urls.add(w["url"])
                all_web.append(w)
    result["web_results"] = all_web[:30]

    # Scrape the most promising URLs for linked PII
    paste_urls = [w["url"] for w in all_web if any(s in w["url"] for s in
        ["pastebin.com", "justpaste.it", "controlc.com", "ghostbin.com", "rentry.co", "textbin.net", "zerobin.net"])][:10]

    if paste_urls:
        sem = asyncio.Semaphore(5)
        async def scrape_one(url):
            async with sem:
                async with httpx.AsyncClient(timeout=20, headers={"User-Agent": UA}, verify=False) as c:
                    return await _fetch_page(url, c)

        pages = await asyncio.gather(*[scrape_one(u) for u in paste_urls])

        for p in pages:
            if p.get("emails") or p.get("phones") or p.get("names"):
                result["scraped_pages"].append(p)
                result["all_emails_found"].extend(p["emails"])
                result["all_phones_found"].extend(p["phones"])
                result["all_names_found"].extend(p["names"])
                result["all_ids_found"].extend(p["other_ids"])

    result["all_emails_found"] = list(set(result["all_emails_found"]))[:30]
    result["all_phones_found"] = list(set(result["all_phones_found"]))[:20]
    result["all_names_found"] = list(set(result["all_names_found"]))[:20]
    result["all_ids_found"] = list(set(result["all_ids_found"]))[:20]
    result["sources_found"] = len(result["web_results"])
    result["scraped_sources"] = len(result["scraped_pages"])
    result["total_linked_data"] = (
        len(result["all_emails_found"]) + len(result["all_phones_found"]) +
        len(result["all_names_found"]) + len(result["all_ids_found"])
    )

    return result
