"""Universal HTTP helper - tries httpx first, falls back to curl."""
import subprocess, re, asyncio

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

async def fetch(url: str, timeout: int = 15, headers: dict = None, follow_redirects: bool = True) -> dict:
    """Fetch a URL, trying httpx first then curl. Returns {status, text, url}"""
    hdrs = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"}
    if headers: hdrs.update(headers)
    
    # Try httpx first (fastest when it works)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout, headers=hdrs, verify=False, follow_redirects=follow_redirects) as c:
            r = await c.get(url)
            return {"status": r.status_code, "text": r.text, "url": str(r.url)}
    except Exception:
        pass
    
    # Fall back to curl subprocess
    try:
        cmd = ["curl", "-s", "--max-time", str(timeout), "-L" if follow_redirects else "",
               "-H", f"User-Agent: {hdrs['User-Agent']}",
               "-H", f"Accept: {hdrs['Accept']}"]
        cmd = [a for a in cmd if a]  # Remove empty strings
        if follow_redirects: cmd.append("-L")
        for k, v in hdrs.items():
            if k.lower() not in ("user-agent", "accept"):
                cmd.extend(["-H", f"{k}: {v}"])
        cmd.append(url)
        
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
        return {"status": 200 if proc.returncode == 0 else 500, "text": stdout.decode(errors="replace"), "url": url}
    except Exception:
        pass
    
    return {"status": 0, "text": "", "url": url}
