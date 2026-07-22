"""People Search v4 - WebMii scraping, directory scraping, real data extraction."""
import re, asyncio, json
from urllib.parse import quote, unquote
from utils.http_helper import fetch

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"


async def _webmii_search(name: str) -> list[dict]:
    """Scrape WebMii for person results."""
    results = []
    try:
        resp = await fetch(f"https://webmii.com/people?n={quote(name)}", timeout=15)
        if resp["status"] != 200: return results
        text = resp["text"]
        # WebMii shows people cards with name, score, links
        cards = re.findall(r'<div[^>]*class="[^"]*card[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', text, re.I|re.S)
        for card in cards:
            name_m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', card, re.I|re.S)
            score_m = re.search(r'(\d+\.?\d*)\s*/\s*10', card)
            if name_m:
                results.append({
                    "name": re.sub(r'<[^>]+>', '', name_m.group(2)).strip(),
                    "url": name_m.group(1) if name_m.group(1).startswith("http") else f"https://webmii.com{name_m.group(1)}",
                    "score": score_m.group(1) if score_m else "",
                    "source": "WebMii",
                })
        if not results:
            # Simpler extraction
            links = re.findall(r'<a[^>]*href="(/[^"]+/people/[^"]+)"[^>]*>(.*?)</a>', text, re.I|re.S)
            for href, link_text in links[:10]:
                name_clean = re.sub(r'<[^>]+>', '', link_text).strip()
                if len(name_clean) > 3:
                    results.append({"name": name_clean, "url": f"https://webmii.com{href}", "source": "WebMii"})
    except: pass
    return results[:10]


async def _pipl_search(name: str) -> list[dict]:
    """Try Pipl search scraping."""
    try:
        resp = await fetch(f"https://pipl.com/search/?q={quote(name)}", timeout=15)
        if resp["status"] != 200: return []
        text = resp["text"]
        results = []
        # Pipl shows structured person data
        names = re.findall(r'<span[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</span>', text, re.I|re.S)
        locations = re.findall(r'<span[^>]*class="[^"]*location[^"]*"[^>]*>(.*?)</span>', text, re.I|re.S)
        if names:
            for n in names[:5]:
                clean = re.sub(r'<[^>]+>', '', n).strip()
                if clean: results.append({"name": clean, "source": "Pipl"})
        return results
    except: return []


async def _thatsthem_scrape(name: str) -> list[dict]:
    """Scrape That'sThem for person data."""
    try:
        resp = await fetch(f"https://thatsthem.com/search?q={quote(name)}", timeout=15)
        if resp["status"] != 200: return []
        text = resp["text"]
        results = []
        # That'sThem shows name, age, phone, address, email in cards
        names = re.findall(r'<span[^>]*itemprop="name"[^>]*>(.*?)</span>', text, re.I)
        phones = re.findall(r'<span[^>]*itemprop="telephone"[^>]*>(.*?)</span>', text, re.I)
        addresses = re.findall(r'<span[^>]*itemprop="address"[^>]*>(.*?)</span>', text, re.I)
        for i, n in enumerate(names[:5]):
            entry = {"name": re.sub(r'<[^>]+>', '', n).strip(), "source": "ThatsThem"}
            if i < len(phones): entry["phone"] = re.sub(r'<[^>]+>', '', phones[i]).strip()
            if i < len(addresses): entry["address"] = re.sub(r'<[^>]+>', '', addresses[i]).strip()
            results.append(entry)
        return results
    except: return []


async def full_name_search(name: str) -> dict:
    name = name.strip()
    encoded = quote(name)
    result = {"name": name, "web_mentions": [], "social_search_urls": [], "people_directories": [], "dorks": [], "scraped_data": []}

    # Try real scraping from WebMii, That'sThem, Pipl
    scraped = await asyncio.gather(
        _webmii_search(name), _thatsthem_scrape(name), _pipl_search(name),
        return_exceptions=True,
    )
    for s in scraped:
        if isinstance(s, list) and s:
            result["scraped_data"].extend(s)

    # Social URLs
    result["social_search_urls"] = [
        {"platform": "Facebook", "url": f"https://www.facebook.com/search/people/?q={encoded}"},
        {"platform": "LinkedIn", "url": f"https://www.linkedin.com/search/results/people/?keywords={encoded}"},
        {"platform": "Twitter/X", "url": f"https://x.com/search?q={encoded}&f=user"},
        {"platform": "Instagram", "url": f"https://www.instagram.com/{name.replace(' ','').lower()}/"},
        {"platform": "GitHub", "url": f"https://github.com/search?q={encoded}&type=users"},
        {"platform": "YouTube", "url": f"https://www.youtube.com/results?search_query={encoded}"},
        {"platform": "TikTok", "url": f"https://www.tiktok.com/search/user?q={encoded}"},
        {"platform": "Reddit", "url": f"https://www.reddit.com/search/?q={encoded}&type=user"},
        {"platform": "Pinterest", "url": f"https://www.pinterest.com/search/users/?q={encoded}"},
        {"platform": "Taringa (LATAM)", "url": f"https://www.taringa.net/search/?q={encoded}"},
        {"platform": "VK (Rusia/Global)", "url": f"https://vk.com/search?c[per_page]=20&c[q]={encoded}&c[section]=people"},
        {"platform": "Badoo (LATAM)", "url": f"https://badoo.com/es/search?q={encoded}"},
    ]

    # Directories with WebMii as first option
    result["people_directories"] = [
        {"name": "WebMii (Global - RECOMENDADO)", "url": f"https://webmii.com/people?n={encoded}"},
        {"name": "Pipl (Global)", "url": f"https://pipl.com/search/?q={encoded}"},
        {"name": "ThatsThem (US)", "url": f"https://thatsthem.com/search?q={encoded}"},
        {"name": "Yasni (Global)", "url": f"https://www.yasni.com/{encoded}/search"},
        {"name": "PeekYou (Global)", "url": f"https://www.peekyou.com/_/{name.replace(' ','_')}"},
        {"name": "Directorio Telefonico MX", "url": f"https://www.directoriotelefonico.com.mx/buscar/{encoded}"},
        {"name": "Seccion Amarilla MX", "url": f"https://www.seccionamarilla.com.mx/search?q={encoded}"},
        {"name": "CompuTrabajo MX", "url": f"https://www.computrabajo.com.mx/candidatos?q={encoded}"},
        {"name": "OccMundial MX", "url": f"https://www.occ.com.mx/buscar-trabajo/?q={encoded}"},
        {"name": "Infocif MX", "url": f"https://infocif.mx/busqueda?q={encoded}"},
        {"name": "MercadoLibre MX", "url": f"https://listado.mercadolibre.com.mx/{encoded}"},
        {"name": "Whitepages (US)", "url": f"https://www.whitepages.com/name/{name.replace(' ', '-')}"},
        {"name": "TruePeopleSearch (US)", "url": f"https://www.truepeoplesearch.com/results?name={encoded}"},
        {"name": "FastPeopleSearch (US)", "url": f"https://www.fastpeoplesearch.com/name/{name.replace(' ', '-')}"},
        {"name": "Spokeo (US)", "url": f"https://www.spokeo.com/{name.replace(' ', '-')}"},
        {"name": "Nuwber (US)", "url": f"https://nuwber.com/search?name={encoded}"},
        {"name": "Yasni (Global)", "url": f"https://www.yasni.com/{encoded}/search"},
        {"name": "PeekYou (Global)", "url": f"https://www.peekyou.com/_/{name.replace(' ','_')}"},
        {"name": "Radaris (US)", "url": f"https://radaris.com/p/{name.replace(' ','+')}/"},
        {"name": "FamilyTreeNow (US)", "url": f"https://www.familytreenow.com/search/genealogy/results?first=&last={encoded}"},
        {"name": "ZabaSearch (US)", "url": f"https://www.zabasearch.com/people/{name.replace(' ','-')}/"},
    ]

    # Dorks
    result["dorks"] = [
        {"label": "CV/Resume", "url": f"https://www.google.com/search?q=%22{encoded}%22+filetype:pdf+resume+OR+cv+OR+curriculum"},
        {"label": "Social Media MX", "url": f"https://www.google.com/search?q=%22{encoded}%22+site:linkedin.com+OR+site:facebook.com+OR+site:instagram.com+OR+site:taringa.net"},
        {"label": "Mexican Gov Docs", "url": f"https://www.google.com/search?q=%22{encoded}%22+site:gob.mx+OR+site:ine.mx+OR+site:imss.gob.mx"},
        {"label": "Forums MX/LATAM", "url": f"https://www.google.com/search?q=%22{encoded}%22+site:reddit.com+OR+site:foroactivo.com+OR+site:taringa.net"},
        {"label": "Public Records MX", "url": f"https://www.google.com/search?q=%22{encoded}%22+(CURP+OR+telefono+OR+direccion+OR+RFC)"},
        {"label": "Leaks & Pastes", "url": f"https://www.google.com/search?q=%22{encoded}%22+site:pastebin.com+OR+site:justpaste.it"},
        {"label": "News MX", "url": f"https://www.google.com/search?q=%22{encoded}%22+site:eluniversal.com.mx+OR+site:milenio.com+OR+site:reforma.com&tbm=nws"},
    ]

    result["total_sources"] = len(result["scraped_data"]) + len(result["social_search_urls"]) + len(result["people_directories"]) + len(result["dorks"])
    return result
