"""Telegram Intelligence - user lookup, group info via Telethon or web scraping."""
import re, asyncio
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"


async def telegram_web_lookup(username_or_phone: str) -> dict:
    target = username_or_phone.strip().lstrip("@")
    result = {"target": target, "found": False, "profile": {}, "groups": []}
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}

    async with httpx.AsyncClient(timeout=15, headers=headers, verify=False, follow_redirects=True) as c:
        try:
            r = await c.get(f"https://t.me/{target}")
            if r.status_code == 200:
                text = r.text
                result["found"] = True
                title = re.search(r'<meta property="og:title" content="([^"]+)"', text)
                desc = re.search(r'<meta property="og:description" content="([^"]+)"', text)
                img = re.search(r'<meta property="og:image" content="([^"]+)"', text)
                if title: result["profile"]["display_name"] = title.group(1)
                if desc: result["profile"]["bio"] = desc.group(1)[:500]
                if img: result["profile"]["avatar"] = img.group(1)
                members = re.search(r'<div class="tgme_page_extra">([^<]+)</div>', text)
                if members: result["profile"]["members"] = members.group(1).strip()
        except: pass

    # Check for public groups
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers, verify=False) as c:
            r = await c.get(f"https://t.me/s/{target}")
            if r.status_code == 200 and r.text:
                msgs = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', r.text, re.S)
                result["recent_messages"] = [re.sub(r'<[^>]+>', '', m).strip()[:200] for m in msgs[:5]]
    except: pass

    return result
