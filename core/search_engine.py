"""Search Engine helper - use curl subprocess when httpx is blocked."""
import subprocess, re, asyncio
from urllib.parse import quote, unquote
from html import unescape as html_unescape


async def curl_search(query: str, timeout: int = 10) -> list[dict]:
    """Search using curl subprocess (works when Python httpx is blocked)."""
    results = []
    engines = [
        ("ddg", f"https://lite.duckduckgo.com/lite/?q={quote(query)}"),
        ("google", f"https://www.google.com/search?q={quote(query)}&num=20&hl=en"),
    ]
    
    for engine, url in engines:
        if results: break
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl", "-s", "--max-time", str(timeout), "-L",
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "-H", "Accept: text/html",
                url,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            text = stdout.decode(errors="replace")
            
            if not text or len(text) < 500:
                continue
            
            # DDG Lite extraction
            links = re.findall(r'<a[^>]*rel="nofollow"[^>]*href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', text, re.I|re.S)
            
            # Google extraction
            if not links:
                links = re.findall(r'<a[^>]*href="(/url\?q=([^"&]+)[^"]*)"[^>]*>\s*<h3[^>]*>(.*?)</h3>', text, re.I|re.S)
                links = [(m[1], m[2]) for m in links]
            
            # Google fallback 
            if not links:
                g_links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>\s*<h3[^>]*>(.*?)</h3>', text, re.I|re.S)
                links = [(l[0], l[1]) for l in g_links if "google" not in l[0].lower()]
            
            # Generic fallback
            if not links:
                all_links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>\s*([^<]{10,200})\s*</a>', text, re.I|re.S)
                links = [(l[0], l[1]) for l in all_links if "google" not in l[0].lower() and "duckduckgo" not in l[0].lower()][:20]
            
            for raw_url, raw_title in links:
                clean_url = raw_url
                m = re.search(r'uddg=([^&\'"]+)', raw_url)
                if m: clean_url = unquote(m.group(1))
                clean_url = clean_url or raw_url
                if not clean_url.startswith("http"): continue
                title = html_unescape(re.sub(r'<[^>]+>', '', raw_title).strip())
                if not title or len(title) < 3: continue
                results.append({"title": title[:200], "url": clean_url, "snippet": "", "source": f"{engine} via curl"})
                
        except asyncio.TimeoutError:
            continue
        except Exception:
            continue
    
    return results[:20]
