#!/usr/bin/env python3
import sys, asyncio, json, re
from pathlib import Path
import typer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import domain as domain_mod
from core import subdomain as subdomain_mod
from core import network as network_mod
from core import email as email_mod
from core import username as username_mod
from core import phone as phone_mod
from core import metadata as metadata_mod
from core import web as web_mod
from core import face as face_mod
from core import person as person_mod
from core import people as people_mod
from core import pii as pii_mod
from core import dorks as dorks_mod
from core import harvester as harvester_mod
from core import accounts as accounts_mod
from core import leaks as leaks_mod
from core import company as company_mod
from core import crypto as crypto_mod
from core import twitter_intel as twitter_mod
from core import telegram_intel as telegram_mod
from core import breaches as breaches_mod
from core import geoint as geoint_mod
from core import pipeline as pipeline_mod
from core.graph_engine import GraphEngine

from utils.output import (
    print_banner, print_success, print_error, print_info,
    print_warning, print_section, print_table, print_json,
    print_results, create_progress,
)
from utils.report import Report

app = typer.Typer(name="prosint", help="PrOSINT v2.0 - Deep OSINT", add_completion=False)


@app.callback()
def callback():
    print_banner()


@app.command()
def domain(target: str = typer.Argument(..., help="Domain"), json_output: bool = typer.Option(False, "--json", "-j")):
    """WHOIS + DNS enumeration."""
    async def run():
        whois, dns = await asyncio.gather(domain_mod.whois_lookup(target), domain_mod.dns_enum(target))
        print_results(whois, "WHOIS"); print_results(dns, "DNS")
        if json_output: print_json({"whois": whois, "dns": dns})
    asyncio.run(run())


@app.command()
def subdomain(target: str = typer.Argument(..., help="Domain"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Subdomain enumeration."""
    async def run():
        r = await subdomain_mod.enumerate_subdomains(target)
        print_info(f"Found {r['total_unique']} unique subdomains.")
        for s in r["sources"]:
            print(f"  {s}: {r['sources'][s].get('count', 0)}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def network(target: str = typer.Argument(..., help="IP"), ports: bool = typer.Option(False, "--ports", "-p"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Full IP intelligence."""
    async def run():
        r = await network_mod.full_network_intel(target, scan_ports=ports)
        geo = r.get("geolocation", {})
        if geo: print_results(geo, "Geolocation"); print_info(f"Maps: {geo.get('maps_url', 'N/A')}")
        risk = r.get("risk_summary", [])
        for ri in risk: print_warning(ri["type"]) if ri["level"] in ("critical","high") else print_info(ri["type"])
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def email(target: str = typer.Argument(..., help="Email"), accounts: bool = typer.Option(False, "--accounts", "-a"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Email investigation."""
    async def run():
        r = await email_mod.full_email_intel(target)
        v = r.get("validation", {})
        if not v.get("valid_format"): print_error("Invalid email"); return
        print_info(f"Score: {v.get('score', 0)}")
        g = r.get("gravatar", {})
        if g.get("has_gravatar"): print_success("Gravatar found!"); print_results(g.get("profile", {}), "Gravatar")
        b = r.get("breaches", {})
        if b.get("pwned"): print_warning(f"PWNED in {b.get('breaches_count', 0)} breaches!")
        if accounts:
            acc = await accounts_mod.discover_linked_accounts(target)
            print_info(f"Linked accounts: {acc['accounts_found']}")
            for a in acc.get("accounts", []): print(f"  + {a['platform']}")
            r["linked_accounts"] = acc
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def username(target: str = typer.Argument(..., help="Username"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Search username across 90+ platforms with aggressive detection."""
    async def run():
        r = await username_mod.full_username_intel(target)
        print_info(f"Found on {r['found_count']}/{r['sites_checked']} platforms.")
        for f in r.get("found", []):
            pd = f.get("profile_data", {})
            extra = f" -> {pd.get('display_name','')}" if pd.get("display_name") else ""
            print(f"  + {f.get('name', '?')}: {f.get('url','')[:60]}{extra[:80]}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def phone(target: str = typer.Argument(..., help="Phone"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Deep phone OSINT: social media links, web mentions, paste sites, forums."""
    async def run():
        r = await phone_mod.deep_phone_intel(target)
        basic = r.get("basic", {})
        print_results(basic, "Phone Analysis")
        wc = r.get("web_mentions_count", 0)
        if wc: print_warning(f"Found in {wc} web results!")
        pc = r.get("paste_sites_count", 0)
        if pc: print_warning(f"Number appears in {pc} paste/leak sites!")
        fc = r.get("forum_mentions_count", 0)
        if fc: print_info(f"Mentioned in {fc} forums/social media posts")
        social = r.get("social_media", {})
        for a in social.get("accounts", []):
            if a.get("found"): print_success(f"  {a['platform']}: {a.get('note', 'Linked')} -> {a.get('url','')}")
        for ri in r.get("risk_assessment", []): print_warning(ri["detail"]) if ri["level"] == "high" else print_info(ri["detail"])
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def metadata(target: str = typer.Argument(..., help="File"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Metadata extraction."""
    async def run():
        r = await metadata_mod.extract_metadata(target)
        if r.get("error"): print_error(r["error"]); return
        print_table("Metadata", [{"Key": k, "Value": str(v)[:200]} for k, v in r.items()])
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def web(target: str = typer.Argument(..., help="URL"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Web analysis."""
    async def run():
        tech, wayback = await asyncio.gather(web_mod.wappalyzer_scan(target), web_mod.wayback_snapshots(target))
        print_info(f"Tech: {', '.join(tech.get('technologies', []))}")
        print_info(f"Wayback: {len(wayback) if isinstance(wayback, list) else 0} snapshots")
        if json_output: print_json({"technologies": tech, "wayback": wayback})
    asyncio.run(run())


@app.command()
def face(target: str = typer.Argument(..., help="Image file"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Face detection + reverse search."""
    async def run():
        r = await face_mod.face_search(target)
        print_info(f"Faces: {r.get('faces_detected', 0)}")
        rs = r.get("reverse_search", {})
        for img in rs.get("results", [])[:10]: print(f"  {img.get('url','')[:100]}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def person(email_addr: str = typer.Argument(..., help="Email"), username_target: str = typer.Option(None, "--username", "-u"), graph: bool = typer.Option(False, "--graph"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Person investigation."""
    async def run():
        uname = username_target or email_addr.split("@")[0]
        r = await person_mod.full_person_investigation(email_addr, uname)
        cross = r.get("cross_reference", {})
        print_section(f"Risk: {cross.get('risk_level', 'unknown').upper()}")
        for f in cross.get("findings", []): print_info(f"  {f['detail']}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def search(name: str = typer.Argument(..., help="Full name"), country: str = typer.Option("", "--country", "-c"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Search person by name."""
    async def run():
        r = await people_mod.full_name_search(name)
        print_info(f"Sources: {r.get('total_sources', 0)}")
        for w in r.get("web_mentions", [])[:5]: print(f"  {w.get('title','')[:80]}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def dorks(name: str = typer.Argument(..., help="Target name"), category: str = typer.Option(None, "--category", "-c"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Execute Google Dorks and extract real results."""
    async def run():
        r = await dorks_mod.execute_dork(name, category)
        print_info(f"Found {r['total_results']} results across {r['dorks_executed']} dorks.")
        for cat, data in r.get("results_by_category", {}).items():
            print_section(f"{data['label']} ({data['results_count']})")
            for res in data["results"][:5]:
                print(f"  {res['title'][:80]}")
                if res.get("url"): print(f"    [dim]{res['url'][:100]}[/dim]")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def harvest(domain: str = typer.Argument(..., help="Domain"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Harvest emails, hosts, and names from search engines."""
    async def run():
        r = await harvester_mod.harvest(domain)
        print_info(f"Emails: {r['emails_count']} | Hosts: {r['hosts_count']} | Names: {r['names_count']}")
        print_section(f"Emails ({r['emails_count']})")
        for e in r.get("emails", [])[:30]: print(f"  {e}")
        print_section(f"Names ({r['names_count']})")
        for n in r.get("names", [])[:20]: print(f"  {n}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def leaks(target: str = typer.Argument(..., help="Email or username"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Search breach databases and paste sites."""
    async def run():
        r = await leaks_mod.search_leaks(target)
        print_section(f"Leak Databases ({len(r['leak_databases'])})")
        for db in r["leak_databases"]: print(f"  {db['name']}: {db['url']}")
        pastes = r.get("paste_findings", [])
        if pastes:
            print_warning(f"Pastes found: {len(pastes)}")
            for p in pastes[:10]: print(f"  {p['url']}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def docs(query: str = typer.Argument(..., help="Search query"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Search documents and pastes across the web."""
    async def run():
        r = await leaks_mod.search_documents(query)
        print_info(f"Documents found: {r.get('total_findings', 0)}")
        for f in r.get("findings", [])[:15]:
            print(f"  [{f['source']}] {f['url'][:100]}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def discord(
    username: str = typer.Argument(..., help="Username to search on Discord platforms"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Look up Discord user profiles, IDs, badges, linked accounts."""
    async def run():
        r = await people_mod.search_discord_username(username)
        print_info(f"Sites checked: {len(r['sites'])}")
        for s in r["sites"]:
            if s["found"]:
                print_success(f"  {s['name']}: found")
                if s.get("ids_found"):
                    for uid in s["ids_found"]: print(f"    ID: {uid}")
        if r.get("profiles_found"):
            for p in r["profiles_found"]:
                profile = p.get("profile", {})
                if profile.get("username"):
                    print_section(f"Profile: {profile.get('username')}#{profile.get('discriminator', '0')}")
                if profile.get("display_name"):
                    print(f"  Display: {profile['display_name']}")
                if p.get("badges"):
                    print(f"  Badges: {', '.join(p['badges'])}")
                if p.get("linked_accounts"):
                    print(f"  Linked: {', '.join(p['linked_accounts'])}")
        if r.get("possible_ids"):
            print_info(f"Discord IDs: {', '.join(r['possible_ids'][:5])}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def pii(
    target: str = typer.Argument(..., help="CURP, SSN, phone, email or ID to reverse-search"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Reverse PII search - input a CURP/SSN/phone to find linked personal data."""
    async def run():
        pii_type = pii_mod.detect_pii_type(target)
        print_info(f"Detected type: {pii_type}")
        r = await pii_mod.reverse_pii_search(target)
        print_info(f"Sources found: {r['sources_found']} | Linked data: {r['total_linked_data']}")
        if r.get("all_emails_found"):
            print_section(f"Emails ({len(r['all_emails_found'])})")
            for e in r["all_emails_found"][:15]: print(f"  {e}")
        if r.get("all_phones_found"):
            print_section(f"Phones ({len(r['all_phones_found'])})")
            for p in r["all_phones_found"][:10]: print(f"  {p}")
        if r.get("all_names_found"):
            print_section(f"Names ({len(r['all_names_found'])})")
            for n in r["all_names_found"][:10]: print(f"  {n}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def company(
    name: str = typer.Argument(..., help="Company name to investigate"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Company OSINT: employees, domains, technologies, LinkedIn, Crunchbase."""
    async def run():
        r = await company_mod.company_search(name)
        wm = r.get("web_mentions", [])
        print_info(f"Web mentions: {len(wm)} | Social: {len(r.get('social_search_urls',[]))} | Info links: {len(r.get('info_links',[]))}")
        if wm:
            print_section("Web Results")
            for w in wm[:8]: print(f"  {w.get('title','?')[:80]}\n    {w.get('url','')[:100]}")
        print_section("Search Links")
        for s in r.get("social_search_urls", []): print(f"  {s['platform']}: {s['url']}")
        for s in r.get("info_links", []): print(f"  {s['name']}: {s['url']}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def compare(
    img1: str = typer.Argument(..., help="First image"),
    img2: str = typer.Argument(..., help="Second image"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Compare two faces to check if they're the same person."""
    async def run():
        r = await face_mod.compare_faces(img1, img2)
        if r.get("error"): print_error(r["error"]); return
        if r["match"]: print_success(f"MATCH! Distance: {r['distance']} (threshold: {r['threshold']})")
        else: print_warning(f"No match. Distance: {r['distance']} (threshold: {r['threshold']})")
        print_info(f"Model: {r.get('model','unknown')}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def crypto(
    address: str = typer.Argument(..., help="BTC or ETH wallet address"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Crypto wallet lookup: balance, transactions, explorers, OFAC sanctions."""
    async def run():
        r = await crypto_mod.crypto_lookup(address)
        print_info(f"Type: {r.get('type', 'Unknown')}")
        tx = r.get("transactions", {})
        if tx.get("final_balance") is not None: print_info(f"Balance: {tx['final_balance']} BTC ({tx.get('n_tx',0)} txs)")
        if tx.get("balance") is not None: print_info(f"Balance: {tx['balance']} ETH")
        for e in r.get("explorers", []): print(f"  {e['name']}: {e['url']}")
        print_info(f"OFAC Sanctions: {r.get('sanctions_check','')}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def twitter(
    username: str = typer.Argument(..., help="Twitter/X username"),
    timeline: bool = typer.Option(False, "--timeline", "-t", help="Fetch recent tweets"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Twitter/X profile lookup: followers, bio, verified, recent tweets."""
    async def run():
        r = await twitter_mod.twitter_lookup(username)
        if r.get("error"): print_warning(r["error"]); return
        p = r.get("profile", {})
        print_results(p, f"Twitter: {username}")
        if timeline:
            tweets = await twitter_mod.twitter_timeline(username)
            print_info(f"Recent tweets: {len(tweets)}")
            for t in tweets[:10]:
                print(f"  [{t.get('date','?')}] {t.get('content','')[:100]}")
                if t.get("url"): print(f"    {t['url']}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def telegram_lookup(
    target: str = typer.Argument(..., help="Telegram username or phone"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Telegram profile lookup: bio, avatar, members, recent messages."""
    async def run():
        r = await telegram_mod.telegram_web_lookup(target)
        if r.get("found"): print_success("Profile found!")
        p = r.get("profile", {})
        if p.get("display_name"): print_info(f"Name: {p['display_name']}")
        if p.get("bio"): print_info(f"Bio: {p['bio'][:200]}")
        if p.get("members"): print_info(f"Members: {p['members']}")
        msgs = r.get("recent_messages", [])
        if msgs: print_section(f"Recent Messages ({len(msgs)})")
        for m in msgs[:5]: print(f"  {m[:120]}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def breaches_lookup(
    target: str = typer.Argument(..., help="Email to search in breach databases"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Multi-source breach search: Psbdmp, XposedOrNot, BreachDirectory, paste sites."""
    async def run():
        r = await breaches_mod.search_breaches(target)
        print_info(f"Findings: {r['total_findings']}")
        for f in r.get("findings", [])[:15]:
            src = f.get("source","?")
            if f.get("breach"): print_warning(f"  [{src}] {f['breach']}")
            elif f.get("url"): print(f"  [{src}] {f.get('url','')[:80]}")
        print_section("Manual Search URLs")
        for db in r.get("manual_search_urls", []): print(f"  {db['name']}: {db['url']}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def geoint(
    target: str = typer.Argument(..., help="IP address, BSSID (WiFi), or lat,lon coordinates"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Geolocation intelligence: IP to address, WiFi BSSID lookup, reverse geocoding."""
    target = target.strip()
    async def run():
        if re.match(r'^[\d.-]+,[\d.-]+$', target):
            lat, lon = target.split(",")
            r = await geoint_mod.reverse_geocode(float(lat), float(lon))
            print_info(f"Address: {r.get('display_name','Unknown')}")
        elif re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', target):
            r = await geoint_mod.wifi_lookup(target)
            if r.get("found"): print_success(f"Found at: {r['coordinates']} -> {r.get('maps_url','')}")
            else: print_warning("Not found on WiGLE")
        else:
            r = await geoint_mod.ip_to_location(target)
            print_info(f"Location: {r.get('display_name',r.get('city','?'))}")
            print_info(f"ISP: {r.get('isp','?')}")
            if r.get("maps_url"): print_info(f"Maps: {r['maps_url']}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def investigate(
    target: str = typer.Argument(..., help="Any target: email, domain, IP, phone, or name"),
    depth: int = typer.Option(2, "--depth", "-d", help="Recursive depth (1-5)"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Deep graph investigation with recursive entity discovery and database storage."""
    async def run():
        r = await pipeline_mod.deep_investigation(target, depth=depth)
        print_section(f"Graph: {r['target_type']} ({r['total_entities']} entities, {r['total_edges']} edges)")
        for n in r.get("graph",{}).get("nodes",[])[:12]:
            print(f"  [{n['type']}] {n['value'][:60]}")
        edges = r.get("graph",{}).get("edges",[])
        if edges: print_section(f"Relationships ({len(edges)})")
        for e in edges[:10]:
            print(f"  {e.get('relationship','?')} ({e.get('confidence',0):.0%})")
        print_info(f"Case: {r['investigation_id']} | CLI: prosint cases / prosint graph-view {r['investigation_id']}")
        if json_output: print_json(r)
    asyncio.run(run())


@app.command()
def cases(json_output: bool = typer.Option(False, "--json", "-j")):
    """List all saved graph investigations."""
    from core.graph_engine import GraphEngine
    g = GraphEngine()
    cases_list = g.list_investigations()
    g.close()
    if not cases_list: print_info("No saved investigations."); return
    for c in cases_list[:20]:
        print(f"  [{c.get('id','?')[:8]}] {c.get('name','?')[:50]} | {c.get('entity_count',0)} entities")
    if json_output: print_json(cases_list)


@app.command()
def graph_view(case_id: str = typer.Argument(..., help="Investigation ID"), depth: int = typer.Option(2, "--depth", "-d"), json_output: bool = typer.Option(False, "--json", "-j")):
    """View entity graph for a saved case."""
    from core.graph_engine import GraphEngine
    g = GraphEngine(case_id)
    graph = g.find_neighbors(case_id, depth=depth)
    g.close()
    print_info(f"Nodes: {graph['total_nodes']} | Edges: {graph['total_edges']}")
    for n in graph.get("nodes",[])[:15]: print(f"  [{n['type']}] {n['value'][:60]}")
    if json_output: print_json(graph)


@app.command()
def full(target: str = typer.Argument(..., help="Domain or email"), json_output: bool = typer.Option(False, "--json", "-j")):
    """Full investigation."""
    async def run():
        if "@" in target:
            r = await person_mod.full_person_investigation(target)
            print_info(f"Risk: {r.get('cross_reference',{}).get('risk_level','unknown')}")
        else:
            whois, dns, subs, harvest_r = await asyncio.gather(
                domain_mod.whois_lookup(target), domain_mod.dns_enum(target),
                subdomain_mod.enumerate_subdomains(target), harvester_mod.harvest(target),
            )
            print_info(f"Subdomains: {subs['total_unique']} | Emails: {harvest_r['emails_count']} | Hosts: {harvest_r['hosts_count']}")
            if json_output: print_json({"whois": whois, "dns": dns, "subdomains": subs, "harvest": harvest_r})
    asyncio.run(run())


@app.command()
def webui(host: str = typer.Option("127.0.0.1", "--host", "-h"), port: int = typer.Option(8000, "--port", "-p"), reload: bool = typer.Option(False, "--reload", "-r")):
    """Start PrOSINT Web UI."""
    import uvicorn
    from web.app import app as fastapi_app
    print_success(f"PrOSINT v2.0: http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    app()
