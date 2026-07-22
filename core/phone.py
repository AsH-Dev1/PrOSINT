"""Deep Phone OSINT v3 - carrier, 9 apps, VoIP detection, Truecaller, leaks, forums."""
import re, asyncio
from urllib.parse import quote, unquote
import phonenumbers
from phonenumbers import geocoder, carrier, timezone, PhoneNumberType
import httpx
from utils.config import REQUEST_TIMEOUT

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"

CARRIER_DB = {
    "52": {"55":"Telcel","56":"Movistar","81":"AT&T Mexico","33":"Movistar/AT&T","22":"Telcel","44":"Movistar","66":"Telcel","77":"Movistar","99":"Telcel","31":"Telcel","46":"Movistar"},
    "1": {"201":"Verizon","212":"T-Mobile","213":"T-Mobile","214":"AT&T","310":"Verizon","312":"AT&T","404":"AT&T","408":"T-Mobile","415":"Verizon","510":"AT&T","512":"T-Mobile","602":"T-Mobile","610":"Verizon","615":"AT&T","626":"T-Mobile","650":"T-Mobile","702":"T-Mobile","718":"Verizon","720":"T-Mobile","760":"Verizon","770":"AT&T","818":"T-Mobile","858":"Verizon","917":"Verizon"},
    "34": {"60":"Movistar","61":"Movistar","62":"Movistar","63":"Movistar","64":"Movistar","65":"Movistar","66":"Movistar","67":"Movistar","68":"Movistar","69":"Movistar","70":"Vodafone","71":"Vodafone","72":"Vodafone","73":"Vodafone","74":"Vodafone","75":"Vodafone","76":"Vodafone","77":"Vodafone","78":"Vodafone","79":"Vodafone","80":"Orange","81":"Orange","82":"Orange","83":"Orange","84":"Orange","85":"Orange","86":"Orange","87":"Orange","88":"Orange","89":"Orange"},
    "44": {"71":"EE","72":"EE","73":"EE","74":"EE","75":"EE","76":"Vodafone UK","77":"Vodafone UK","78":"Vodafone UK","79":"Vodafone UK","70":"O2"},
    "33": {"6":"Orange/SFR","7":"Free Mobile"},
    "49": {"15":"Telekom","16":"Vodafone DE","17":"O2/E-Plus"},
    "55": {"11":"Vivo","21":"Claro","31":"TIM","41":"Vivo","51":"TIM","61":"Oi","71":"Claro","81":"TIM"},
    "54": {"11":"Movistar","15":"Personal","911":"Claro"},
    "57": {"30":"Tigo","31":"Claro","32":"Claro","35":"Movistar","10":"Claro","11":"Tigo"},
    "56": {"9":"Entel","5":"Movistar Chile","7":"Claro Chile"},
    "51": {"9":"Movistar","8":"Claro","7":"Entel"},
    "91": {"70":"Jio","80":"Airtel","90":"Vodafone","97":"Jio","98":"Airtel","99":"Vodafone"},
    "86": {"13":"China Mobile","15":"China Mobile","18":"China Mobile","17":"China Telecom","18":"China Telecom","13":"China Unicom","15":"China Unicom"},
    "7": {"90":"MTS","91":"MegaFon","92":"Beeline","96":"Beeline","98":"Tele2","99":"MegaFon"},
    "81": {"80":"NTT Docomo","90":"SoftBank","70":"KDDI au"},
    "82": {"10":"SK Telecom","11":"KT","12":"LG U+"},
    "39": {"32":"TIM","33":"Vodafone IT","34":"WindTre","35":"Iliad"},
    "61": {"4":"Telstra","41":"Optus","42":"Vodafone AU"},
    "31": {"6":"KPN","65":"Vodafone NL","62":"T-Mobile NL"},
    "46": {"70":"Telia","72":"Tele2","73":"Telenor","76":"3 Sweden"},
    "47": {"40":"Telenor","41":"Telia","90":"Ice","94":"ice.net"},
    "351": {"91":"Vodafone PT","92":"MEO","93":"NOS"},
    "54": {"11":"Movistar","15":"Personal","91":"Claro"},
}

VOIP_RANGES = {
    "google_voice": [r'\b\d{3}-\d{3}-\d{4}\b.*google voice', 'google voice number', 'gv number'],
    "twilio": [r'twilio', r'\+\d{10,15}.*twilio'],
    "textnow": [r'textnow', r'text now', r'\+\d{10,15}.*textnow'],
    "burner": [r'burner phone', r'burner number', r'\+\d{10,15}.*burner'],
    "skype": [r'skype number', r'skype', r'\+\d{10,15}.*skype'],
}


def _detect_carrier_from_prefix(national: str, country_code) -> str:
    cc = str(country_code) if country_code else ""
    db = CARRIER_DB.get(cc, {})
    if not db: return ""
    clean = re.sub(r'[\s\-\(\)]', '', national or "")
    if not clean: return ""
    for pl in [3, 2]:
        p = clean[:pl]
        if p in db: return db[p]
    return db.get(clean[0], "")


async def _ddg_search(query: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent":UA,"Accept":"text/html"}, verify=False) as c:
            r = await c.get(f"https://html.duckduckgo.com/html/?q={quote(query)}")
            if r.status_code != 200: return []
            links = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.I|re.S)
            snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', r.text, re.I|re.S)
            results = []
            for i, (raw, raw_t) in enumerate(links[:25]):
                m = re.search(r'uddg=([^&\'"]+)', raw)
                url = unquote(m.group(1)) if m else ""
                if not url: continue
                title = re.sub(r'<[^>]+>', '', raw_t).strip()
                s = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                results.append({"title": title, "url": url, "snippet": s[:300]})
            return results
    except: return []


async def check_social_apps(phone: str) -> dict:
    clean = re.sub(r'[\s\-\(\)]', '', phone.strip())
    if not clean.startswith('+'): clean = '+' + clean

    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
    results = {"accounts": [], "linked_count": 0}

    async def _check(name, url, check_fn):
        try:
            async with httpx.AsyncClient(timeout=15, headers=headers, verify=False, follow_redirects=True) as c:
                return await check_fn(c, url, clean)
        except: return {"platform": name, "found": False, "detail": "Check failed"}

    async def _wa(c, url, ph): r = await c.get(f"https://wa.me/{ph}"); return {"platform":"WhatsApp","found":r.status_code==200 and len(r.text)>1000,"detail":"WhatsApp account active" if r.status_code==200 else "Not on WhatsApp","url":f"https://wa.me/{ph}"}
    async def _tg(c, url, ph): r = await c.get(f"https://t.me/{ph}"); t=r.text.lower(); return {"platform":"Telegram","found":r.status_code==200 and any(w in t for w in ["send message","chat","tgme"]),"detail":"Telegram account active" if r.status_code==200 else "Not on Telegram","url":f"https://t.me/{ph}"}
    async def _signal(c, url, ph): r = await c.get(f"https://signal.me/#p/{ph}"); return {"platform":"Signal","found":r.status_code==200,"detail":"Signal link available","url":f"https://signal.me/#p/{ph}"}
    async def _viber(c, url, ph): r = await c.get(f"https://invite.viber.com/?g2=AQB%2B{ph.replace('+','')}"); return {"platform":"Viber","found":r.status_code==200 and len(r.text)>500,"detail":"Viber account possible","url":f"https://invite.viber.com/?g2=AQB%2B{ph.replace('+','')}"}
    async def _fb(c, url, ph): r = await c.get(f"https://www.facebook.com/login/identify/?ctx=recover&search_query={ph}"); t=r.text.lower(); fnd=any(w in t for w in ["account found","choose an account","send code via sms","text you a code"]); return {"platform":"Facebook","found":fnd,"detail":"Linked to Facebook account" if fnd else "Check Facebook manually","url":f"https://www.facebook.com/login/identify/?ctx=recover&search_query={ph}"}
    async def _ig(c, url, ph): r = await c.get(f"https://www.instagram.com/accounts/account_recovery/"); t=r.text.lower(); csrf=re.search(r'csrf_token["\s:=]+["\']([^"\']+)',t); return {"platform":"Instagram","found":False,"detail":"Check Instagram recovery page","url":"https://www.instagram.com/accounts/password/reset/"}
    async def _amazon(c, url, ph): r = await c.get(f"https://www.amazon.com/ap/forgotpassword?openid.return_to=https%3A%2F%2Fwww.amazon.com"); return {"platform":"Amazon","found":r.status_code==200,"detail":"Amazon recovery page accessible","url":"https://www.amazon.com/ap/forgotpassword"}
    async def _snapchat(c, url, ph): r = await c.get(f"https://accounts.snapchat.com/accounts/password_reset_request?phone={ph}"); return {"platform":"Snapchat","found":r.status_code in (200,302),"detail":"Check Snapchat recovery","url":f"https://accounts.snapchat.com/accounts/password_reset_request?phone={ph}"}
    async def _cashapp(c, url, ph): u=ph.replace('+',''); r = await c.get(f"https://cash.app/${u}"); return {"platform":"Cash App","found":r.status_code==200 and len(r.text)>500 and "cash" in r.text.lower(),"detail":"Cash App tag possible","url":f"https://cash.app/${u}"}
    async def _truecaller(c, url, ph): r = await c.get(f"https://www.truecaller.com/search/{ph}"); t=r.text; name=re.search(r'<h1[^>]*>([^<]+)</h1>',t); spam=re.search(r'spam[^<]*<[^>]*>([^<]+)<',t,I); return {"platform":"Truecaller","found":r.status_code==200 and len(t)>500,"detail":"Name found" if name else "Check Truecaller manually","url":f"https://www.truecaller.com/search/{ph}"}

    checks = [
        ("WhatsApp", _wa), ("Telegram", _tg), ("Signal", _signal),
        ("Viber", _viber), ("Facebook", _fb), ("Instagram", _ig),
        ("Amazon", _amazon), ("Snapchat", _snapchat),
        ("Cash App", _cashapp), ("Truecaller", _truecaller),
    ]

    tasks = [asyncio.create_task(_check(n, "", f)) for n, f in checks]
    for t in asyncio.as_completed(tasks):
        r = await t
        results["accounts"].append(r)
    results["linked_count"] = sum(1 for a in results["accounts"] if a["found"])
    return results


async def deep_phone_intel(phone: str) -> dict:
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone.strip())
    if not phone_clean.startswith('+'): phone_clean = '+' + phone_clean

    basic = {"input": phone, "valid": False, "possible": False, "e164": None,
             "national": None, "international": None, "country": None,
             "country_code": None, "carrier": None, "timezone": [],
             "line_type": None, "region": None, "voip_provider": ""}
    try:
        p = phonenumbers.parse(phone)
        basic["possible"] = phonenumbers.is_possible_number(p)
        basic["valid"] = phonenumbers.is_valid_number(p)
        basic["e164"] = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164)
        basic["national"] = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.NATIONAL)
        basic["international"] = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        basic["country_code"] = p.country_code
        basic["country"] = geocoder.description_for_number(p, "en")
        basic["region"] = geocoder.region_code_for_number(p)
        try: basic["timezone"] = list(timezone.time_zones_for_number(p))
        except: pass
        lm = {PhoneNumberType.MOBILE: "Mobile", PhoneNumberType.FIXED_LINE: "Fixed Line",
              PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed/Mobile", PhoneNumberType.TOLL_FREE: "Toll Free",
              PhoneNumberType.PREMIUM_RATE: "Premium", PhoneNumberType.VOIP: "VoIP",
              PhoneNumberType.PERSONAL_NUMBER: "Personal", PhoneNumberType.PAGER: "Pager"}
        basic["line_type"] = lm.get(phonenumbers.number_type(p), "Unknown")
        try: cname = carrier.name_for_number(p, "en")
        except: cname = None
        if not cname or cname == "Unknown":
            cname = _detect_carrier_from_prefix(basic.get("national",""), basic.get("country_code"))
        basic["carrier"] = cname or "Unknown"
        # VoIP detection
        if basic.get("line_type") == "VoIP":
            nat = basic.get("national","")
            for provider, patterns in VOIP_RANGES.items():
                for pat in patterns:
                    if re.search(pat, nat, re.I):
                        basic["voip_provider"] = provider.replace("_"," ").title()
                        break
    except: pass

    if not basic.get("valid") and not basic.get("possible"):
        return {"error": "Invalid phone number", "basic": basic}

    social = await check_social_apps(phone)

    queries = [f'"{phone_clean}"', f'{phone_clean} site:pastebin.com OR site:justpaste.it', f'{phone_clean} site:reddit.com']
    all_web = []
    for q in queries:
        all_web.extend(await _ddg_search(q))
    seen = set()
    web = []
    for r in all_web:
        if r["url"] not in seen: seen.add(r["url"]); web.append(r)

    paste_mentions = [r for r in web if any(s in r.get("url","") for s in ["pastebin.com","justpaste.it","controlc.com","ghostbin.com"])]
    forum_mentions = [r for r in web if any(s in r.get("url","") for s in ["reddit.com","foro","forum","board"])]

    risks = []
    if basic.get("line_type") == "VoIP": risks.append({"level":"medium","detail":"VoIP number" + (f' ({basic.get("voip_provider")})' if basic.get("voip_provider") else "")})
    if basic.get("line_type") == "Toll Free": risks.append({"level":"low","detail":"Toll-free number"})
    if paste_mentions: risks.append({"level":"high","detail":f"Found in {len(paste_mentions)} paste/leak sites"})
    if forum_mentions: risks.append({"level":"medium","detail":f"Mentioned in {len(forum_mentions)} forums"})
    if len(web) > 5: risks.append({"level":"medium","detail":f"Published in {len(web)} web results"})
    linked = social.get("linked_count",0)
    if linked > 0: risks.append({"level":"info","detail":f"Linked to {linked} platforms"})

    return {"basic":basic,"social_media":social,"paste_sites":paste_mentions[:10],"paste_sites_count":len(paste_mentions),
            "forum_mentions":forum_mentions[:10],"forum_mentions_count":len(forum_mentions),
            "web_mentions":web[:15],"web_mentions_count":len(web),"risk_assessment":risks,"total_sources":len(web)}
