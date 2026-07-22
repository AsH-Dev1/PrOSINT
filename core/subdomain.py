import re
import json
from typing import Optional

import httpx

from utils.config import get_headers, REQUEST_TIMEOUT


async def crtsh_subdomains(domain: str) -> list[str]:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]

    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    subdomains = set()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers()) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for entry in data:
                    name = entry.get("name_value", entry.get("common_name", ""))
                    for n in name.split("\n"):
                        n = n.strip().lower().lstrip("*.")
                        if n and n.endswith(domain) and n != domain:
                            subdomains.add(n)
        except Exception:
            pass

    return sorted(subdomains)


async def alienvault_subdomains(domain: str) -> list[str]:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]

    url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
    subdomains = set()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers()) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for entry in data.get("passive_dns", []):
                    hostname = entry.get("hostname", "")
                    if hostname and hostname.endswith(domain) and hostname != domain:
                        subdomains.add(hostname.lower())
        except Exception:
            pass

    return sorted(subdomains)


async def rapiddns_subdomains(domain: str) -> list[str]:
    domain = domain.lower().strip().rstrip("/")
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]

    url = f"https://rapiddns.io/subdomain/{domain}?full=1"
    subdomains = set()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=get_headers()) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                from html.parser import HTMLParser

                class TDHandler(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.in_td = False
                        self.results = []

                    def handle_starttag(self, tag, attrs):
                        if tag == "td":
                            self.in_td = True

                    def handle_endtag(self, tag):
                        if tag == "td":
                            self.in_td = False

                    def handle_data(self, data):
                        if self.in_td and data.strip():
                            self.results.append(data.strip())

                handler = TDHandler()
                handler.feed(resp.text)
                for item in handler.results:
                    item = item.lower()
                    if item.endswith(domain) and item != domain:
                        subdomains.add(item)
        except Exception:
            pass

    return sorted(subdomains)


async def enumerate_subdomains(domain: str, sources: Optional[list[str]] = None) -> dict:
    if sources is None:
        sources = ["crtsh", "alienvault", "rapiddns"]

    all_subdomains = set()
    source_results = {}

    for source in sources:
        try:
            if source == "crtsh":
                subs = await crtsh_subdomains(domain)
            elif source == "alienvault":
                subs = await alienvault_subdomains(domain)
            elif source == "rapiddns":
                subs = await rapiddns_subdomains(domain)
            else:
                continue
            source_results[source] = {"count": len(subs), "subdomains": subs}
            all_subdomains.update(subs)
        except Exception as e:
            source_results[source] = {"count": 0, "error": str(e)}

    return {
        "domain": domain,
        "total_unique": len(all_subdomains),
        "subdomains": sorted(all_subdomains),
        "sources": source_results,
    }
