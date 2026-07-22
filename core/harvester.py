"""Harvester v3 - 6 search engines, GitHub code search, DNSDumpster, HackerTarget."""
import re, asyncio, random
from urllib.parse import quote
import httpx
from utils.config import REQUEST_TIMEOUT
from utils.cache import get_cached, set_cache, make_key

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
HOST_RE = re.compile(r"([a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}")

async def _search_engine(query: str, engine: str, client: httpx.AsyncClient) -> tuple[set, set]:
    engines = {
        "google": f"https://www.google.com/search?q={quote(query)}&num=50&hl=en",
        "bing": f"https://www.bing.com/search?q={quote(query)}&count=30",
        "ddg": f"https://html.duckduckgo.com/html/?q={quote(query)}",
        "yahoo": f"https://search.yahoo.com/search?p={quote(query)}&n=30",
        "yandex": f"https://yandex.com/search/?text={quote(query)}",
        "baidu": f"https://www.baidu.com/s?wd={quote(query)}&rn=30",
    }
    url = engines.get(engine)
    if not url: return set(), set()
    emails, hosts = set(), set()
    try:
        r = await client.get(url, timeout=20, headers={"User-Agent": UA, "Accept": "text/html"})
        if r.status_code != 200: return emails, hosts
        text = r.text
        for e in EMAIL_RE.findall(text):
            e = e.lower()
            if len(e) < 50 and "." in e.split("@")[-1]: emails.add(e)
        for h in HOST_RE.findall(text):
            h = h[0].lower() if isinstance(h, tuple) else h.lower()
            if "." in h and 4 < len(h) < 100: hosts.add(h)
    except: pass
    return emails, hosts


async def _crt_sh(domain: str, client: httpx.AsyncClient) -> set:
    emails = set()
    try:
        r = await client.get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=15)
        if r.status_code == 200:
            for e in r.json():
                for v in [e.get("name_value",""), e.get("common_name","")]:
                    emails.update(EMAIL_RE.findall(v.lower()))
    except: pass
    return emails


async def _github_code_search(domain: str, client: httpx.AsyncClient) -> set:
    emails = set()
    try:
        r = await client.get(f"https://github.com/search?q={quote(domain)}&type=code", timeout=15, headers={"User-Agent": UA})
        if r.status_code == 200:
            emails.update(EMAIL_RE.findall(r.text.lower()))
    except: pass
    return emails


async def _dnsdumpster(domain: str, client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get("https://dnsdumpster.com/", timeout=10, headers={"User-Agent": UA})
        csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
        if not csrf: return {"available": False}
        token = csrf.group(1)
        cookies = r.cookies
        r2 = await client.post("https://dnsdumpster.com/", data={"csrfmiddlewaretoken": token, "targetip": domain}, cookies=cookies, headers={"User-Agent": UA, "Referer": "https://dnsdumpster.com/"}, timeout=20)
        if r2.status_code == 200:
            hosts = list(set(re.findall(r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r2.text)))
            return {"available": True, "hosts": hosts[:50], "url": f"https://dnsdumpster.com/"}
    except: pass
    return {"available": False}


async def _hackertarget(domain: str, client: httpx.AsyncClient) -> dict:
    results = {}
    try:
        r = await client.get(f"https://api.hackertarget.com/hostsearch/?q={domain}", timeout=15)
        if r.status_code == 200 and "error" not in r.text.lower():
            hosts = [l.split(",")[0] for l in r.text.strip().split("\n") if "," in l]
            results["hosts"] = hosts[:100]
        r2 = await client.get(f"https://api.hackertarget.com/reverseiplookup/?q={domain}", timeout=15)
        if r2.status_code == 200 and "error" not in r2.text.lower():
            results["reverse_ips"] = [l.strip() for l in r2.text.strip().split("\n") if l.strip()][:50]
    except: pass
    return results if results else {"available": False}


async def harvest(domain: str) -> dict:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain).split("/")[0]

    cache_key = make_key("harvest3", domain)
    if cached := get_cached(cache_key, ttl_hours=6): return cached

    all_emails, all_hosts = set(), set()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=False) as c:
        # Search engines
        queries = [f"@{domain}", f"{domain} email", f"site:{domain}"]
        engines = ["google", "bing", "ddg", "yahoo", "yandex"]
        tasks = [_crt_sh(domain, c), _github_code_search(domain, c)]
        for q in queries[:2]:
            for eng in engines[:3]:
                tasks.append(_search_engine(q, eng, c))
        dns_task = _dnsdumpster(domain, c)
        ht_task = _hackertarget(domain, c)
        tasks.append(dns_task); tasks.append(ht_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, tuple) and len(r) == 2:
                all_emails.update(r[0]); all_hosts.update(r[1])
            elif isinstance(r, set): all_emails.update(r)

    dns_data = dns_task if isinstance(dns_task, dict) else {}
    ht_data = ht_task if isinstance(ht_task, dict) else {}

    result = {"domain": domain, "emails": sorted(all_emails), "emails_count": len(all_emails),
              "hosts": sorted(all_hosts)[:100], "hosts_count": len(all_hosts),
              "dnsdumpster": dns_data, "hackertarget": ht_data}
    set_cache(cache_key, result)
    return result
