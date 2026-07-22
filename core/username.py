"""Username search - aggressive detection across 90+ platforms."""
import json, re, asyncio, random
from pathlib import Path
import httpx
from utils.config import MAX_CONCURRENT

SITES_FILE = Path(__file__).resolve().parent.parent / "data" / "sites.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

ERROR_PHRASES = re.compile(
    r"not found|doesn't exist|page not found|no such user|unknown user|"
    r"couldn't find|sorry.*(?:couldn't|we can't)|does not exist|"
    r"this account doesn't|profile not found|user not found|"
    r"page isn't available|page cannot be found|the page you were looking for doesn't|"
    r"there's nothing here|whoops.*gone|blog has been removed"
)

LOGIN_REDIRECTS = [
    "/login", "/signin", "/accounts/login", "/auth", "login?next=",
    "authwall", "i/flow/login", "sign_in",
]


def _load_sites() -> list[dict]:
    try:
        return [s for s in json.loads(SITES_FILE.read_text()) if isinstance(s, dict) and "url" in s]
    except: return []


async def _check_site(username: str, cfg: dict, client: httpx.AsyncClient) -> dict:
    name = cfg.get("name", "?")
    url_tpl = cfg.get("url", "")
    check_url = (cfg.get("check_url") or url_tpl).replace("{username}", username)
    profile_url = url_tpl.replace("{username}", username)
    is_api = cfg.get("api", False)
    site_ua = cfg.get("headers", {}).get("User-Agent", UA)

    if not check_url:
        return {"name": name, "url": profile_url, "found": False, "profile_data": {}}

    headers = {
        "User-Agent": site_ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = await client.get(check_url, headers=headers, follow_redirects=False, timeout=20)
        status = resp.status_code

        # Follow redirects manually to detect login pages
        if status in (301, 302, 303, 307, 308):
            location = resp.headers.get("location", "")
            if not location:
                return {"name": name, "url": profile_url, "found": False}
            loc_lower = location.lower()
            for login_path in LOGIN_REDIRECTS:
                if login_path in loc_lower:
                    return {"name": name, "url": profile_url, "found": False}
            # Follow the redirect
            resp = await client.get(location, headers=headers, follow_redirects=True, timeout=20)
            status = resp.status_code

        if status in (404, 410, 503):
            return {"name": name, "url": profile_url, "found": False}

        text = resp.text[:300000]
        final_url = str(resp.url).lower()
        text_lower = text.lower()

        # Check error page
        if ERROR_PHRASES.search(text_lower):
            return {"name": name, "url": profile_url, "found": False}

        # Check login redirect again
        for login_path in LOGIN_REDIRECTS:
            if login_path in final_url:
                return {"name": name, "url": profile_url, "found": False}

        # API sites
        if is_api and status == 200:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    if data.get("message") and "not found" in str(data.get("message", "")).lower():
                        return {"name": name, "url": profile_url, "found": False}
                    if data.get("error"):
                        return {"name": name, "url": profile_url, "found": False}
                    # For API responses, also check username presence
                    api_text = json.dumps(data).lower()
                    if username.lower() in api_text:
                        return {"name": name, "url": profile_url, "found": True,
                                "profile_data": _extract_api_fields(data, cfg)}
                    # Some APIs return user data without username in text
                    if len(str(data)) > 100:
                        return {"name": name, "url": profile_url, "found": True,
                                "profile_data": _extract_api_fields(data, cfg)}
            except:
                pass

        # For all other 200 responses: if the page isn't clearly an error,
        # and is substantial enough, check if username appears anywhere
        if status == 200 and len(text) > 500:
            if username.lower() in text_lower:
                return {"name": name, "url": profile_url, "found": True,
                        "profile_data": _scrape_meta(text, name)}
            # Still mark as found if no error patterns matched and page is big enough
            # (Many sites have the username in JavaScript, which requires rendering)
            if len(text) > 10000:
                return {"name": name, "url": profile_url, "found": True,
                        "profile_data": _scrape_meta(text, name)}

    except (asyncio.TimeoutError, httpx.ConnectError, httpx.ReadError):
        pass
    except Exception:
        pass

    return {"name": name, "url": profile_url, "found": False, "profile_data": {}}


def _is_bad_url(url: str) -> bool:
    """Reject template tags, javascript, data URIs, and other non-URLs."""
    if not url or len(url) < 5: return True
    bad_patterns = ["<%", "%>", "javascript:", "data:image", "{{", "}}"]
    return any(p in url for p in bad_patterns)


def _extract_api_fields(data: dict, cfg: dict) -> dict:
    out = {}
    for dest, src in (cfg.get("profile_fields") or {}).items():
        if "/" in str(src):
            parts = src.split("/"); val = data
            try:
                for p in parts:
                    val = val[int(p) if p.isdigit() else p] if isinstance(val, (list, dict)) else None
                out[dest] = val
            except: pass
        else:
            v = data.get(src)
            if v: out[dest] = v
    return out


def _scrape_meta(html: str, site_name: str) -> dict:
    data = {}
    og_title = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
    if og_title:
        t = og_title.group(1).strip()
        if 3 < len(t) < 120: data["display_name"] = t
    else:
        title_tag = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_tag:
            t = title_tag.group(1).strip()
            t = re.sub(r'\s*[-–|•]\s*[A-Z].*$', '', t)
            if 3 < len(t) < 100: data["display_name"] = t

    og_desc = re.search(r'<meta[^>]*(?:property=["\']og:description|name=["\']description)["\'][^>]*content=["\']([^"\']{10,400})', html, re.IGNORECASE)
    if og_desc: data["description"] = og_desc.group(1)[:300]

    for pat in [r'"location"\s*:\s*"([^"]+)"', r'"city"\s*:\s*"([^"]+)"', r'"country"\s*:\s*"([^"]+)"']:
        m = re.search(pat, html, re.IGNORECASE)
        if m: data["location"] = m.group(1); break

    avatar = re.search(r'<img[^>]*src=["\']([^"\']*(?:avatar|profile_pic|profile-pic|og:image)[^"\']*)["\']', html, re.IGNORECASE)
    if avatar and not _is_bad_url(avatar.group(1)): data["avatar"] = avatar.group(1)
    else:
        og_img = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
        if og_img:
            img = og_img.group(1)
            if "logo" not in img.lower() and "icon" not in img.lower() and not _is_bad_url(img): data["avatar"] = img

    return data


async def search_username(username: str) -> dict:
    username = username.strip().lstrip("@")
    uname_lower = username.lower()
    sites = _load_sites()

    if not sites:
        return {"username": username, "sites_checked": 0, "found_count": 0, "found": [], "not_found": []}

    sem = asyncio.Semaphore(min(MAX_CONCURRENT or 10, 12))
    timeout_config = httpx.Timeout(25.0, connect=12.0)

    async def check_one(cfg):
        async with sem:
            await asyncio.sleep(random.uniform(0.02, 0.15))
            return await _check_site(uname_lower, cfg, client)

    async with httpx.AsyncClient(
        timeout=timeout_config, follow_redirects=False, verify=False,
        limits=httpx.Limits(max_connections=25, max_keepalive_connections=10),
    ) as client:
        results = await asyncio.gather(*[check_one(s) for s in sites], return_exceptions=True)

    found = []
    errors = 0
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            errors += 1
        elif r.get("found"):
            found.append(r)

    return {
        "username": username,
        "sites_checked": len(sites),
        "found_count": len(found),
        "found": found,
        "errors": errors,
    }


async def full_username_intel(username: str) -> dict:
    r = await search_username(username)
    providers = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com", "proton.me", "icloud.com"]
    r["email_hints"] = [f"{username}@{p}" for p in providers]
    r["summary"] = {
        "profile_links": [{"platform": f["name"], "url": f.get("url","")} for f in r.get("found",[]) if f.get("url")],
        "names": [{"platform": f["name"], "name": f.get("profile_data",{}).get("display_name","")} for f in r.get("found",[]) if f.get("profile_data",{}).get("display_name")],
        "locations": [{"platform": f["name"], "location": f.get("profile_data",{}).get("location","")} for f in r.get("found",[]) if f.get("profile_data",{}).get("location")],
    }
    return r
