"""Free Shodan alternatives + enhanced IP intelligence."""
import re, socket, asyncio
from urllib.parse import quote
import httpx
from utils.config import REQUEST_TIMEOUT, SHODAN_API_KEY
from utils.cache import get_cached, set_cache, make_key

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"
COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017]
SERVICE_MAP = {21:"FTP",22:"SSH",23:"Telnet",25:"SMTP",53:"DNS",80:"HTTP",110:"POP3",135:"MSRPC",139:"NetBIOS",143:"IMAP",443:"HTTPS",445:"SMB",993:"IMAPS",995:"POP3S",3306:"MySQL",3389:"RDP",5432:"PostgreSQL",5900:"VNC",6379:"Redis",8080:"HTTP-Alt",8443:"HTTPS-Alt",27017:"MongoDB"}


async def check_port(ip: str, port: int, timeout: float = 1.0) -> dict:
    try:
        _, w = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
        w.close(); await w.wait_closed()
        return {"port": port, "open": True, "service": SERVICE_MAP.get(port, "unknown")}
    except: return {"port": port, "open": False, "service": SERVICE_MAP.get(port, "unknown")}

async def port_scan(ip: str, ports: list[int] | None = None) -> list[dict]:
    if ports is None: ports = COMMON_PORTS
    results = await asyncio.gather(*[check_port(ip, p) for p in ports])
    return [r for r in results if r["open"]]

async def ip_geolocation(ip: str) -> dict:
    async with httpx.AsyncClient(timeout=10, verify=False) as c:
        try:
            r = await c.get(f"http://ip-api.com/json/{ip}?fields=66846719", headers={"User-Agent": UA})
            if r.status_code == 200:
                d = r.json()
                if d.get("status") == "success":
                    geo = {"ip": d.get("query"), "country": d.get("country"), "country_code": d.get("countryCode"),
                           "region": d.get("regionName"), "city": d.get("city"), "zip": d.get("zip"),
                           "lat": d.get("lat"), "lon": d.get("lon"), "isp": d.get("isp"), "org": d.get("org"),
                           "asn": f"AS{d.get('as','').split()[0]}" if d.get("as") else None,
                           "timezone": d.get("timezone"), "is_proxy": d.get("proxy", False),
                           "is_hosting": d.get("hosting", False), "is_mobile": d.get("mobile", False)}
                    if geo.get("lat") and geo.get("lon"):
                        geo["maps_url"] = f"https://www.google.com/maps?q={geo['lat']},{geo['lon']}"
                    return geo
        except: pass
    return {}

async def shodan_lookup(ip: str) -> dict:
    if not SHODAN_API_KEY: return {"available": False, "reason": "No API key in .env"}
    cache_key = make_key("shodan", ip)
    if cached := get_cached(cache_key): return cached
    async with httpx.AsyncClient(timeout=15) as c:
        try:
            r = await c.get(f"https://api.shodan.io/shodan/host/{ip}?key={SHODAN_API_KEY}")
            if r.status_code == 200:
                d = r.json()
                res = {"available": True, "ip": d.get("ip_str"), "org": d.get("org"), "isp": d.get("isp"),
                       "asn": d.get("asn"), "os": d.get("os"), "ports": d.get("ports",[]),
                       "hostnames": d.get("hostnames",[]), "domains": d.get("domains",[]),
                       "country": d.get("country_name"), "city": d.get("city"),
                       "vulns": list(d.get("vulns",[])), "tags": list(d.get("tags",[]))}
                set_cache(cache_key, res); return res
        except: pass
    return {"available": False}

async def censys_lookup(ip: str) -> dict:
    """Censys search (free, no API key)."""
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": UA, "Accept": "text/html"}, verify=False, follow_redirects=True) as c:
        try:
            r = await c.get(f"https://search.censys.io/search?resource=hosts&q={ip}&per_page=5")
            if r.status_code == 200 and "Censys" in r.text:
                text = r.text
                services = re.findall(r'<span[^>]*>\s*(\d+/\w+)\s*</span>', text)
                os_m = re.search(r'<strong[^>]*>\s*([Ww]indows|[Ll]inux|[Dd]ebian|[Uu]buntu|[Cc]ent[Oo][Ss]|[Rr]ed\s*[Hh]at|[Mm]ac\s*[Oo][Ss][^<]+)</strong>', text)
                return {"available": True, "services": services[:10], "os": os_m.group(1).strip() if os_m else None,
                        "url": f"https://search.censys.io/hosts/{ip}"}
        except: pass
    return {"available": False, "url": f"https://search.censys.io/hosts/{ip}"}


async def securitytrails_lookup(domain_or_ip: str) -> dict:
    """SecurityTrails free DNS lookup."""
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": UA, "Accept": "text/html"}, verify=False, follow_redirects=True) as c:
        try:
            r = await c.get(f"https://securitytrails.com/domain/{domain_or_ip}")
            if r.status_code == 200 and "SecurityTrails" in r.text:
                text = r.text
                related = re.findall(r'<span[^>]*>\s*([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})\s*</span>', text)
                return {"available": True, "related_domains": list(set(related))[:20],
                        "url": f"https://securitytrails.com/domain/{domain_or_ip}"}
        except: pass
    return {"available": False, "url": f"https://securitytrails.com/domain/{domain_or_ip}"}

async def abuseipdb_check(ip: str) -> dict:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}, verify=False) as c:
        try:
            r = await c.get(f"https://www.abuseipdb.com/check/{ip}")
            if r.status_code == 200:
                t = r.text
                m = re.search(r'was reported\s*<b>(\d+)</b>\s*times?', t)
                m2 = re.search(r'confidence[^"]*"[^"]*"[^"]*<b>(\d+)%</b>', t)
                return {"reports": int(m.group(1)) if m else 0,
                        "confidence": int(m2.group(1)) if m2 else None,
                        "url": f"https://www.abuseipdb.com/check/{ip}"}
        except: pass
    return {"reports": 0}

async def reverse_ip_lookup(ip: str) -> list[str]:
    results = []
    async with httpx.AsyncClient(timeout=15, verify=False) as c:
        try:
            r = await c.get(f"https://api.hackertarget.com/reverseiplookup/?q={ip}")
            if r.status_code == 200 and "error" not in r.text.lower():
                results = [l.strip() for l in r.text.strip().split("\n") if l.strip() and "." in l]
        except: pass
    return sorted(set(results))

async def reverse_dns(ip: str) -> str:
    try: return socket.gethostbyaddr(ip)[0]
    except: return ""

async def full_network_intel(ip: str, scan_ports: bool = False) -> dict:
    geo, shodan, censys, strails, abuse, rev, rdns = await asyncio.gather(
        ip_geolocation(ip), shodan_lookup(ip), censys_lookup(ip),
        securitytrails_lookup(ip), abuseipdb_check(ip),
        reverse_ip_lookup(ip), reverse_dns(ip),
        return_exceptions=True,
    )
    results = {
        "ip": ip,
        "geolocation": geo if isinstance(geo, dict) else {},
        "shodan": shodan if isinstance(shodan, dict) else {},
        "censys": censys if isinstance(censys, dict) else {},
        "securitytrails": strails if isinstance(strails, dict) else {},
        "abuseipdb": abuse if isinstance(abuse, dict) else {},
        "reverse_ip": rev if isinstance(rev, list) else [],
        "reverse_dns": rdns if isinstance(rdns, str) else "",
    }
    if scan_ports: results["open_ports"] = await port_scan(ip)

    risk = []
    geo_d = results.get("geolocation", {})
    if isinstance(geo_d, dict):
        if geo_d.get("is_proxy"): risk.append({"level": "high", "type": "Proxy/VPN detected"})
        if geo_d.get("is_hosting"): risk.append({"level": "medium", "type": "Hosting/Data center IP"})
    abuse_d = results.get("abuseipdb", {})
    if isinstance(abuse_d, dict) and (abuse_d.get("reports") or 0) > 0:
        risk.append({"level": "high", "type": f"Reported {abuse_d.get('reports')} times on AbuseIPDB"})
    shodan_d = results.get("shodan", {})
    if isinstance(shodan_d, dict) and shodan_d.get("available") and shodan_d.get("vulns"):
        risk.append({"level": "critical", "type": f"{len(shodan_d['vulns'])} known CVEs"})
    results["risk_summary"] = risk
    return results
