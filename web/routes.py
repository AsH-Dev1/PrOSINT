import sys, asyncio, tempfile, os, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from core import domain as domain_mod, subdomain as subdomain_mod
from core import network as network_mod, email as email_mod
from core import username as username_mod, phone as phone_mod
from core import metadata as metadata_mod, web as web_mod
from core import face as face_mod, person as person_mod
from core import people as people_mod, dorks as dorks_mod
from core import harvester as harvester_mod
from core import accounts as accounts_mod, leaks as leaks_mod
from core import pii as pii_mod
from core import company as company_mod
from core import crypto as crypto_mod
from core import twitter_intel as twitter_mod
from core import telegram_intel as telegram_mod
from core import breaches as breaches_mod
from core import geoint as geoint_mod
from core import pipeline as pipeline_mod
from core.graph_engine import GraphEngine
from utils.report import Report, REPORT_DIR

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
router = APIRouter(prefix="/api")
pages_router = APIRouter()


@pages_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@pages_router.get("/report/{report_id}", response_class=HTMLResponse)
async def view_report(request: Request, report_id: str):
    fp = REPORT_DIR / report_id
    return FileResponse(fp) if fp.exists() else HTMLResponse("<h1>Not found</h1>", status_code=404)

# DOMAIN
@router.post("/domain")
async def api_domain(target: str = Form(...)):
    w, d = await asyncio.gather(domain_mod.whois_lookup(target), domain_mod.dns_enum(target))
    return {"whois": w, "dns": d}

@router.post("/subdomain")
async def api_subdomain(target: str = Form(...)):
    return await subdomain_mod.enumerate_subdomains(target)

@router.post("/network")
async def api_network(target: str = Form(...), ports: bool = Form(False)):
    return await network_mod.full_network_intel(target, scan_ports=ports)

@router.post("/email")
async def api_email(target: str = Form(...), accounts: bool = Form(False)):
    r = await email_mod.full_email_intel(target)
    if accounts:
        r["linked_accounts"] = await accounts_mod.discover_linked_accounts(target)
    return r

@router.post("/username")
async def api_username(target: str = Form(...)):
    return await username_mod.full_username_intel(target)

@router.post("/phone")
async def api_phone(target: str = Form(...)):
    return await phone_mod.deep_phone_intel(target)

@router.post("/metadata")
async def api_metadata(file: UploadFile = File(...)):
    s = Path(file.filename or "upload").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=s) as t:
        t.write(await file.read()); tp = t.name
    try: return await metadata_mod.extract_metadata(tp)
    finally: os.unlink(tp)

@router.post("/web")
async def api_web(target: str = Form(...)):
    tech, wb = await asyncio.gather(web_mod.wappalyzer_scan(target), web_mod.wayback_snapshots(target))
    return {"technologies": tech, "wayback": wb}

@router.post("/face")
async def api_face(file: UploadFile = File(...)):
    s = Path(file.filename or "upload").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=s) as t:
        t.write(await file.read()); tp = t.name
    try: return await face_mod.face_search(tp)
    finally: os.unlink(tp)

@router.post("/person")
async def api_person(email_addr: str = Form(...), username_target: str = Form("")):
    u = username_target or email_addr.split("@")[0]
    return await person_mod.full_person_investigation(email_addr, u)

@router.post("/search")
async def api_search(name: str = Form(...)):
    return await people_mod.full_name_search(name)

@router.post("/dorks")
async def api_dorks(name: str = Form(...), category: str = Form("")):
    return await dorks_mod.execute_dork(name, category if category else None)

@router.post("/harvest")
async def api_harvest(target: str = Form(...)):
    return await harvester_mod.harvest(target)

@router.post("/leaks")
async def api_leaks(target: str = Form(...)):
    return await leaks_mod.search_leaks(target)

@router.post("/docs")
async def api_docs(query: str = Form(...)):
    return await leaks_mod.search_documents(query)


@router.post("/discord")
async def api_discord(target: str = Form(...)):
    return await people_mod.search_discord_username(target)


@router.post("/pii")
async def api_pii(target: str = Form(...)):
    return await pii_mod.reverse_pii_search(target)


@router.post("/company")
async def api_company(name: str = Form(...)):
    return await company_mod.company_search(name)


@router.post("/crypto")
async def api_crypto(address: str = Form(...)):
    return await crypto_mod.crypto_lookup(address)


@router.post("/twitter")
async def api_twitter(username: str = Form(...), timeline: bool = Form(False)):
    r = await twitter_mod.twitter_lookup(username)
    if timeline: r["recent_tweets"] = await twitter_mod.twitter_timeline(username)
    return r


@router.post("/telegram")
async def api_telegram(target: str = Form(...)):
    return await telegram_mod.telegram_web_lookup(target)


@router.post("/breaches")
async def api_breaches(target: str = Form(...)):
    return await breaches_mod.search_breaches(target)


@router.post("/geoint")
async def api_geoint(target: str = Form(...)):
    target = target.strip()
    if re.match(r'^[\d.-]+,[\d.-]+$', target):
        lat, lon = target.split(",")
        return await geoint_mod.reverse_geocode(float(lat), float(lon))
    elif re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', target):
        return await geoint_mod.wifi_lookup(target)
    return await geoint_mod.ip_to_location(target)


@router.post("/investigate")
async def api_investigate(target: str = Form(...), depth: int = Form(2)):
    return await pipeline_mod.deep_investigation(target, depth=depth)


@router.get("/cases")
async def api_cases():
    g = GraphEngine()
    cases = g.list_investigations()
    g.close()
    return cases


@router.get("/graph/{case_id}")
async def api_graph(case_id: str, depth: int = 2):
    g = GraphEngine(case_id)
    graph = g.find_neighbors(case_id, depth=depth)
    g.close()
    return graph


@router.post("/full")
async def api_full(target: str = Form(...)):
    if "@" in target:
        return await person_mod.full_person_investigation(target)
    w, d, s, h = await asyncio.gather(
        domain_mod.whois_lookup(target), domain_mod.dns_enum(target),
        subdomain_mod.enumerate_subdomains(target), harvester_mod.harvest(target),
    )
    return {"whois": w, "dns": d, "subdomains": s, "harvest": h}
