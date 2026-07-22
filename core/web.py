import re
from urllib.parse import urlparse

import httpx

from utils.config import get_headers, REQUEST_TIMEOUT
from utils.cache import get_cached, set_cache, make_key


async def unshorten_url(url: str) -> dict:
    url = url.strip()
    result = {"original": url}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers()) as client:
        try:
            resp = await client.head(url, follow_redirects=True)
            final_url = str(resp.url)
            result["resolved"] = final_url
            result["redirected"] = final_url != url
            result["hops"] = len(resp.history)
            result["status"] = resp.status_code
        except Exception as e:
            result["error"] = str(e)

    return result


async def wayback_urls(domain: str) -> list[dict]:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]

    cache_key = make_key("wayback", domain)
    cached = get_cached(cache_key)
    if cached:
        return cached

    url = f"https://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&fl=timestamp,original,statuscode,mimetype&collapse=urlkey&limit=200"
    results = []

    async with httpx.AsyncClient(timeout=60, headers=get_headers()) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                lines = resp.json()
                for line in lines[1:]:
                    if len(line) >= 4:
                        results.append({
                            "timestamp": line[0],
                            "url": line[1],
                            "status": line[2],
                            "mimetype": line[3] if len(line) > 3 else "",
                        })
        except Exception:
            pass

    set_cache(cache_key, results)
    return results


async def wayback_snapshots(url: str, limit: int = 50) -> list[dict]:
    query_url = f"https://web.archive.org/cdx/search/cdx?url={url}&output=json&fl=timestamp,original,statuscode&limit={limit}"
    results = []

    async with httpx.AsyncClient(timeout=60, headers=get_headers()) as client:
        try:
            resp = await client.get(query_url)
            if resp.status_code == 200:
                lines = resp.json()
                for line in lines[1:]:
                    if len(line) >= 3:
                        timestamp = line[0]
                        results.append({
                            "timestamp": timestamp,
                            "url": line[1],
                            "status": line[2],
                            "archive_url": f"https://web.archive.org/web/{timestamp}/{line[1]}",
                        })
        except Exception:
            pass

    return results


WAPP_TECHS = [
    ("jQuery", r'jquery[.-]?(\d+\.\d+\.\d+)?\.js'),
    ("Bootstrap", r'bootstrap[.-]?(\d+\.\d+\.\d+)?\.(js|css)'),
    ("React", r'react[.-]?(\d+\.\d+\.\d+)?\.(js|production\.min\.js|development\.js)'),
    ("Vue.js", r'vue[.-]?(\d+\.\d+\.\d+)?\.(js|min\.js)'),
    ("Angular", r'angular[.-]?(\d+\.\d+\.\d+)?\.js'),
    ("WordPress", r'wp-content|wp-includes|wordpress'),
    ("Drupal", r'drupal\.js|sites/default|/misc/drupal'),
    ("Joomla", r'joomla|/media/jui/'),
    ("Laravel", r'laravel_session'),
    ("Django", r'csrftoken|django\.__debug'),
    ("Ruby on Rails", r'_rails_|rails-ujs'),
    ("Express", r'x-powered-by:\s*Express'),
    ("PHP", r'\.php|PHPSESSID'),
    ("Nginx", r'nginx'),
    ("Apache", r'apache'),
    ("Cloudflare", r'cloudflare|__cfduid'),
    ("Google Analytics", r'google-analytics\.com|gtag\('),
    ("Font Awesome", r'font-?awesome'),
    ("Google Fonts", r'fonts\.googleapis\.com'),
    ("reCAPTCHA", r'recaptcha'),
    ("Stripe", r'stripe\.com|js\.stripe'),
    ("Tailwind CSS", r'tailwindcss|tailwind\.min\.css'),
    ("Alpine.js", r'alpine[.-]?\d'),
    ("Next.js", r'__NEXT_|_next/static'),
    ("Nuxt.js", r'__NUXT_|/_nuxt/'),
]


async def wappalyzer_scan(url: str) -> dict:
    url = url.strip()
    if not url.startswith("http"):
        url = f"https://{url}"

    result = {"url": url, "technologies": [], "headers": {}}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers(), verify=False) as client:
        try:
            resp = await client.get(url, follow_redirects=True)
            body = resp.text.lower()
            headers_text = "\n".join(f"{k}: {v}" for k, v in resp.headers.items()).lower()

            combined = body + " " + headers_text

            for tech, pattern in WAPP_TECHS:
                if re.search(pattern, combined, re.IGNORECASE):
                    result["technologies"].append(tech)

            result["status_code"] = resp.status_code
            result["final_url"] = str(resp.url)
            result["headers"] = dict(resp.headers)
            result["title"] = _extract_title(resp.text)
        except Exception as e:
            result["error"] = str(e)

    return result


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""
