import re
import hashlib
import asyncio
import dns.resolver
import httpx

from utils.config import get_headers, HIBP_API_KEY, REQUEST_TIMEOUT
from utils.cache import get_cached, set_cache, make_key

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "yopmail.com", "throwaway.email", "sharklasers.com", "trashmail.com",
    "maildrop.cc", "getnada.com", "dispostable.com", "mailnesia.com",
    "temp-mail.org", "fakeinbox.com", "mohmal.com", "moakt.com",
}

ROLE_PREFIXES = {
    "admin", "info", "support", "sales", "contact", "help", "noreply",
    "no-reply", "webmaster", "postmaster", "abuse", "hostmaster", "root",
    "mailer-daemon", "bounce", "security", "privacy", "dmarc", "dmarcian",
}


def validate(email: str) -> dict:
    email = email.strip().lower()
    result = {
        "email": email, "valid_format": False, "disposable": False,
        "role_account": False, "free_provider": False, "score": 0,
    }

    if not EMAIL_RE.match(email):
        return result

    result["valid_format"] = True
    local, domain = email.split("@", 1)
    result["local_part"] = local
    result["domain"] = domain
    result["score"] += 1

    if local.lower() in ROLE_PREFIXES:
        result["role_account"] = True
        result["score"] -= 1

    if domain in DISPOSABLE_DOMAINS:
        result["disposable"] = True
        result["score"] -= 3

    free_providers = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                      "live.com", "aol.com", "protonmail.com", "proton.me",
                      "icloud.com", "me.com", "mail.com", "zoho.com", "yandex.com"}
    result["free_provider"] = domain in free_providers

    local_patterns = {
        "numeric": bool(re.match(r"^\d+$", local)),
        "common_words": bool(re.match(r"^(test|demo|example|sample|temporary|fake|spam)$", local)),
        "dots_separated": "." in local,
    }
    result["local_patterns"] = local_patterns

    if local_patterns["numeric"]:
        result["score"] -= 1
    if local_patterns["common_words"]:
        result["score"] -= 2
    if len(local) <= 2:
        result["score"] -= 1

    return result


async def mx_check(email: str) -> dict:
    email = email.strip().lower()
    domain = email.split("@")[-1]

    result = {"domain": domain, "has_mx": False, "mx_records": [], "can_receive": False}
    try:
        answers = dns.resolver.resolve(domain, "MX")
        result["has_mx"] = True
        result["mx_records"] = sorted(
            [{"priority": r.preference, "server": str(r.exchange).rstrip(".")} for r in answers],
            key=lambda x: x["priority"],
        )

        mx_domains = set()
        for mx in result["mx_records"]:
            mx_domains.add(mx["server"].lower())
        result["mx_providers"] = _detect_mx_provider(mx_domains)
        result["can_receive"] = True

    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        try:
            dns.resolver.resolve(domain, "A")
            result["can_receive"] = True
        except Exception:
            pass
    except Exception:
        pass

    return result


def _detect_mx_provider(mx_domains: set) -> list[str]:
    providers = []
    checks = {
        "Google Workspace": lambda d: "google" in d or "googlemail" in d,
        "Microsoft 365": lambda d: "outlook.com" in d or "protection.outlook.com" in d,
        "ProtonMail": lambda d: "protonmail" in d,
        "Zoho": lambda d: "zoho" in d,
        "Fastmail": lambda d: "fastmail" in d,
        "Cloudflare Email": lambda d: "cloudflare" in d,
        "MXRoute": lambda d: "mxroute" in d,
        "Namecheap": lambda d: "namecheap" in d,
    }
    for name, check in checks.items():
        if any(check(d) for d in mx_domains):
            providers.append(name)
    return providers


async def hibp_breaches(email: str) -> dict:
    email = email.strip().lower()

    if not HIBP_API_KEY:
        return {"available": False, "pwned": False, "reason": "No HIBP_API_KEY configured"}

    cache_key = make_key("hibp", email)
    cached = get_cached(cache_key, ttl_hours=168)
    if cached:
        return cached

    headers = get_headers()
    headers["hibp-api-key"] = HIBP_API_KEY
    headers["user-agent"] = "PrOSINT"

    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                breaches = resp.json()
                result = {
                    "available": True,
                    "email": email,
                    "pwned": True,
                    "breaches_count": len(breaches),
                    "breaches": [{
                        "name": b.get("Name"),
                        "domain": b.get("Domain"),
                        "date": b.get("BreachDate"),
                        "added": b.get("AddedDate"),
                        "data_classes": b.get("DataClasses", []),
                        "description": b.get("Description", "")[:300],
                        "pwn_count": b.get("PwnCount"),
                        "verified": b.get("IsVerified"),
                        "sensitive": b.get("IsSensitive"),
                    } for b in breaches],
                }

                sensitive = sum(1 for b in result["breaches"] if b.get("sensitive"))
                result["sensitive_breaches"] = sensitive

                all_classes = set()
                for b in result["breaches"]:
                    all_classes.update(b.get("data_classes", []))
                result["all_compromised_data"] = sorted(all_classes)

            elif resp.status_code == 404:
                result = {"available": True, "email": email, "pwned": False,
                          "breaches_count": 0, "breaches": []}
            elif resp.status_code == 401:
                result = {"available": False, "pwned": False, "reason": "Invalid HIBP API key"}
            else:
                result = {"available": False, "pwned": False, "reason": f"HIBP returned {resp.status_code}"}
        except Exception as e:
            result = {"available": False, "pwned": False, "reason": str(e)}

    set_cache(cache_key, result)
    return result


async def gravatar_lookup(email: str) -> dict:
    email = email.strip().lower()
    h = hashlib.md5(email.encode()).hexdigest()

    result = {"email": email, "hash": h, "has_gravatar": False}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers()) as client:
        for size in [2048, 200]:
            url = f"https://www.gravatar.com/avatar/{h}?d=404&s={size}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    result["has_gravatar"] = True
                    result["avatar_url"] = f"https://www.gravatar.com/avatar/{h}?d=404&s={size}"
                    break
            except Exception:
                continue

        try:
            profile_url = f"https://www.gravatar.com/{h}.json"
            resp = await client.get(profile_url)
            if resp.status_code == 200:
                data = resp.json()
                entry = data.get("entry", [{}])[0]
                result["has_profile"] = True
                result["profile"] = {
                    "display_name": entry.get("displayName"),
                    "preferred_username": entry.get("preferredUsername"),
                    "about": entry.get("aboutMe", "")[:500],
                    "location": entry.get("currentLocation"),
                    "urls": [u.get("value") for u in entry.get("urls", [])],
                    "accounts": [{
                        "domain": a.get("domain"),
                        "display": a.get("display"),
                        "url": a.get("url"),
                    } for a in entry.get("accounts", [])],
                    "emails": [e.get("value") for e in entry.get("emails", [])],
                }
            else:
                result["has_profile"] = False
        except Exception:
            result["has_profile"] = False

    return result


async def emailrep_lookup(email: str) -> dict:
    email = email.strip().lower()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers()) as client:
        try:
            resp = await client.get(f"https://emailrep.io/{email}")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "reputation": data.get("reputation"),
                    "suspicious": data.get("suspicious"),
                    "references": data.get("references"),
                    "details": {
                        "blacklisted": data.get("details", {}).get("blacklisted"),
                        "malicious_activity": data.get("details", {}).get("malicious_activity"),
                        "credentials_leaked": data.get("details", {}).get("credentials_leaked"),
                        "spam": data.get("details", {}).get("spam"),
                        "domain_reputation": data.get("details", {}).get("domain_reputation"),
                        "last_seen": data.get("details", {}).get("last_seen"),
                        "sources": data.get("details", {}).get("sources", []),
                    },
                }
        except Exception:
            pass
    return {}


async def full_email_intel(email: str) -> dict:
    fmt = validate(email)

    results = {
        "email": email,
        "validation": fmt,
    }

    if not fmt["valid_format"]:
        results["error"] = "Invalid email format"
        return results

    mx, breaches, gravatar, reputation = await asyncio.gather(
        mx_check(email), hibp_breaches(email), gravatar_lookup(email), emailrep_lookup(email),
        return_exceptions=True,
    )

    results["mx"] = mx if isinstance(mx, dict) else {}
    results["breaches"] = breaches if isinstance(breaches, dict) else {}
    results["gravatar"] = gravatar if isinstance(gravatar, dict) else {}
    results["reputation"] = reputation if isinstance(reputation, dict) else {}

    return results
