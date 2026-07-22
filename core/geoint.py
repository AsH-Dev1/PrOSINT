"""GeoInt - WiFi/BSSID lookup, reverse geocoding, OpenStreetMap enrichment."""
import re, asyncio
from urllib.parse import quote
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"


async def wifi_lookup(bssid: str) -> dict:
    """Look up WiFi BSSID on WiGLE.net (free, no API key)."""
    bssid = re.sub(r'[^a-fA-F0-9:]', '', bssid.strip())
    result = {"bssid": bssid, "found": False, "networks": []}
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA, "Accept": "text/html"}, verify=False) as c:
            r = await c.get(f"https://wigle.net/search?netid={bssid}")
            if r.status_code == 200:
                text = r.text
                lat = re.search(r'<td[^>]*>\s*Lat:\s*</td>\s*<td[^>]*>\s*([\d.-]+)\s*</td>', text)
                lon = re.search(r'<td[^>]*>\s*Lon:\s*</td>\s*<td[^>]*>\s*([\d.-]+)\s*</td>', text)
                if lat and lon:
                    result["found"] = True
                    result["coordinates"] = {"lat": float(lat.group(1)), "lon": float(lon.group(1))}
                    result["maps_url"] = f"https://www.google.com/maps?q={result['coordinates']['lat']},{result['coordinates']['lon']}"
    except: pass
    return result


async def reverse_geocode(lat: float, lon: float) -> dict:
    """Reverse geocode coordinates to address using OpenStreetMap Nominatim (free)."""
    result = {"lat": lat, "lon": lon}
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": f"PrOSINT/3.0", "Accept": "application/json"}, verify=False) as c:
            r = await c.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1")
            if r.status_code == 200:
                d = r.json()
                addr = d.get("address", {})
                result["display_name"] = d.get("display_name", "")
                result["address"] = {
                    "road": addr.get("road", ""),
                    "city": addr.get("city", addr.get("town", addr.get("village", ""))),
                    "state": addr.get("state", ""),
                    "country": addr.get("country", ""),
                    "postcode": addr.get("postcode", ""),
                }
    except: pass
    return result


async def ip_to_location(ip: str) -> dict:
    """Get IP location with reverse geocoding for address-level detail."""
    result = {"ip": ip}
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}, verify=False) as c:
        try:
            r = await c.get(f"http://ip-api.com/json/{ip}")
            if r.status_code == 200:
                d = r.json()
                if d.get("status") == "success":
                    lat, lon = d.get("lat"), d.get("lon")
                    result["city"] = d.get("city")
                    result["country"] = d.get("country")
                    result["isp"] = d.get("isp")
                    if lat and lon:
                        geo = await reverse_geocode(lat, lon)
                        result["address"] = geo.get("address", {})
                        result["display_name"] = geo.get("display_name", "")
                        result["maps_url"] = f"https://www.google.com/maps?q={lat},{lon}"
        except: pass
    return result
