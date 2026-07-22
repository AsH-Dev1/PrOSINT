import re
import socket
from datetime import datetime

import dns.resolver
import httpx

from utils.config import get_headers, REQUEST_TIMEOUT


async def whois_lookup(domain: str) -> dict:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]

    result = {
        "domain": domain,
        "queried_at": datetime.utcnow().isoformat(),
    }

    try:
        import whois
        w = whois.whois(domain)
        result["registrar"] = w.registrar
        result["creation_date"] = _parse_date(w.creation_date)
        result["expiration_date"] = _parse_date(w.expiration_date)
        result["name_servers"] = [str(n).lower() for n in (w.name_servers or [])]
        result["status"] = str(w.status) if w.status else None
        result["emails"] = w.emails
    except Exception as e:
        result["whois_error"] = str(e)

    return result


def _parse_date(val):
    if val is None:
        return None
    if isinstance(val, list):
        return str(val[0])
    return str(val)


async def dns_enum(domain: str) -> dict:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]

    records = {}
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]

    for rtype in record_types:
        try:
            answers = dns.resolver.resolve(domain, rtype)
            records[rtype] = [str(a.to_text()) for a in answers]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            records[rtype] = []
        except dns.exception.DNSException:
            records[rtype] = []
        except Exception:
            records[rtype] = []

    return {"domain": domain, "dns_records": records}


async def reverse_ip(ip: str) -> list:
    ip = ip.strip()
    results = []

    # Use HackerTarget API (free, no key needed)
    urls = [
        f"https://api.hackertarget.com/reverseiplookup/?q={ip}",
        f"https://api.viewdns.info/reverseip/?host={ip}&apikey=free&output=json",
    ]

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers()) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    text = resp.text
                    if "error" not in text.lower() and "invalid" not in text.lower():
                        for line in text.strip().split("\n"):
                            line = line.strip()
                            if line and not line.startswith("{"):
                                results.append(line)
                        if results:
                            break
            except Exception:
                continue

    return list(set(results))


async def resolve_domain_to_ip(domain: str) -> str:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return ""
