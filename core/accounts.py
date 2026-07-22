"""Email-to-accounts discovery - reliable checks only."""
import re, asyncio, hashlib, random
import httpx
from utils.config import REQUEST_TIMEOUT
from utils.cache import get_cached, set_cache, make_key

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"


async def discover_linked_accounts(email: str) -> dict:
    email = email.strip().lower()
    if "@" not in email: return {"error": "Invalid email", "accounts_found": 0, "accounts": []}

    sem = asyncio.Semaphore(5)
    h = hashlib.md5(email.encode()).hexdigest()

    async def check_one(name, fn):
        async with sem:
            try: return {"platform": name, "registered": await fn()}
            except: return {"platform": name, "registered": False}

    async def _gh():
        headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
        async with httpx.AsyncClient(timeout=10, headers=headers) as c:
            r = await c.get(f"https://api.github.com/search/users?q={email}+in:email&per_page=1")
            return r.status_code == 200 and r.json().get("total_count", 0) > 0

    async def _gl():
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}) as c:
            r = await c.get(f"https://gitlab.com/api/v4/users?search={email}")
            return r.status_code == 200 and len(r.json()) > 0

    async def _gravatar():
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}) as c:
            r = await c.get(f"https://en.gravatar.com/{h}.json")
            return r.status_code == 200 and len(r.text) > 20

    async def _wp():
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}) as c:
            r = await c.get(f"https://public-api.wordpress.com/rest/v1.1/users/{email}/auth-options")
            text = r.text.lower()
            return r.status_code == 200 and "password_authentication" in text and "email_verified" in text

    async def _docker():
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}) as c:
            r = await c.get(f"https://hub.docker.com/v2/users/{email}/")
            return r.status_code == 200 and "id" in r.text and len(r.text) > 50

    async def _devto():
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}) as c:
            r = await c.get(f"https://dev.to/api/users/by_username?url={email.split('@')[0]}")
            return r.status_code == 200 and isinstance(r.json(), dict) and r.json().get("id")

    checks = [
        ("GitHub", _gh), ("GitLab", _gl), ("Gravatar", _gravatar),
        ("WordPress", _wp), ("Docker Hub", _docker), ("Dev.to", _devto),
    ]

    results = await asyncio.gather(*[check_one(n, f) for n, f in checks])
    accounts = [r for r in results if r["registered"]]

    return {
        "email": email, "platforms_checked": len(checks),
        "accounts_found": len(accounts), "accounts": accounts,
    }


async def check_messaging_apps(phone: str) -> dict:
    phone_clean = re.sub(r"[^\d+]", "", phone.strip())
    if not phone_clean.startswith("+"): phone_clean = "+" + phone_clean

    apps = [
        ("WhatsApp", f"https://wa.me/{phone_clean}", "chat with|continue to chat|send message"),
        ("Telegram", f"https://t.me/{phone_clean}", "send message|chat|view"),
        ("Signal", f"https://signal.me/#p/{phone_clean}", "signal|message"),
    ]

    results = []
    headers = {"User-Agent": UA}
    async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True, verify=False) as c:
        for name, url, check in apps:
            try:
                r = await c.get(url)
                likely = any(w in r.text.lower() for w in check.split("|"))
                results.append({"app": name, "likely_active": likely or r.status_code == 200, "url": url})
            except: pass

    return {"phone": phone_clean, "apps_found": len(results), "apps": results}
