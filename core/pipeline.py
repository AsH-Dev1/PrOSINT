"""Recursive Transform Engine v4 - robust graph investigation."""
import asyncio, re
from datetime import datetime, timezone
from core.graph_engine import GraphEngine

TRANSFORM_MAP = {
    "Email":    ["email_intel", "username_discovery"],
    "Username": ["platform_search"],
    "Phone":    ["phone_intel", "social_check"],
    "Domain":   ["domain_intel", "subdomain_enum"],
    "IP":       ["geo_intel"],
    "Person":   ["people_search", "social_links"],
}
MAX_DEPTH = 3
MAX_ENTITIES = 100


async def deep_investigation(target: str, depth: int = 2) -> dict:
    engine = GraphEngine()
    engine.create_investigation(f"Investigation: {target[:40]}", target)
    root_type, root_value = _classify(target)
    root_id = engine.add_entity(root_type, root_value, {"original_target": target})

    visited = set()
    queue = [(root_id, 0)]
    total = 1

    while queue and total < MAX_ENTITIES:
        eid, cur_depth = queue.pop(0)
        if eid in visited or cur_depth > depth:
            continue
        visited.add(eid)

        row = engine.db.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
        if not row: continue
        etype = row["type"] if isinstance(row, dict) else row[1]
        evalue = row["value"] if isinstance(row, dict) else row[2]

        transforms = TRANSFORM_MAP.get(etype, ["people_search"])
        for tname in transforms:
            if total >= MAX_ENTITIES: break
            try:
                new_entities = await _run_transform(tname, evalue, etype, engine)
                for ne in new_entities:
                    if total >= MAX_ENTITIES: break
                    ne_id = engine.add_entity(ne["type"], ne["value"], ne.get("props",{}), ne.get("conf",0.8))
                    engine.add_edge(eid, ne_id, ne.get("rel","LINKED_TO"), ne.get("conf",0.5), ne.get("ev",""))
                    if ne_id not in visited and cur_depth < depth:
                        queue.append((ne_id, cur_depth + 1))
                    total += 1
            except Exception as e:
                pass

    graph = engine.find_neighbors(root_id, depth=depth)
    cases = engine.list_investigations()
    engine.close()

    return {"investigation_id": engine.investigation_id, "target": target,
            "target_type": root_type, "depth": depth,
            "total_entities": graph["total_nodes"], "total_edges": graph["total_edges"],
            "graph": graph, "investigations": cases[:10]}


def _classify(target: str) -> tuple:
    t = target.strip()
    if "@" in t: return ("Email", t.lower())
    if re.match(r'^\+?\d{7,15}$', re.sub(r'[\s\-\(\)]','', t)): return ("Phone", t)
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', t): return ("IP", t)
    if "." in t and " " not in t and "@" not in t: return ("Domain", t.lower())
    return ("Person", t)


async def _run_transform(name: str, value: str, etype: str, engine) -> list[dict]:
    result = []

    if name == "email_intel":
        from core import email as m
        data = await m.full_email_intel(value)
        v = data.get("validation", {})
        if v.get("valid_format"):
            result.append({"type":"Email","value":value,"props":v,"rel":"OWNS","conf":1.0})
        g = data.get("gravatar", {})
        if g.get("has_gravatar") and g.get("profile"):
            gp = g["profile"]
            dn = gp.get("display_name","")
            if dn:
                result.append({"type":"Person","value":dn,"props":gp,"rel":"LINKED_TO","conf":0.6,"ev":"Gravatar profile"})
            loc = gp.get("location","")
            if loc:
                result.append({"type":"Location","value":loc,"props":{"source":"gravatar"},"rel":"LOCATED_AT","conf":0.5})
        b = data.get("breaches", {})
        if b.get("pwned"):
            for breach in b.get("breaches", [])[:5]:
                result.append({"type":"Breach","value":breach.get("name","?"),"props":breach,"rel":"BREACHED_IN","conf":0.9,"ev":breach.get("domain","")})

    elif name == "username_discovery":
        username = value.split("@")[0]
        from core import username as m
        data = await m.search_username(username)
        for f in data.get("found", [])[:15]:
            sn = f.get("name", "?")
            pd = f.get("profile_data", {})
            result.append({"type":"SocialProfile","value":f"{sn}:{username}",
                          "props":{"platform":sn,"url":f.get("url",""),"display_name":pd.get("display_name",""),"location":pd.get("location","")},
                          "rel":"FOUND_ON","conf":0.7,"ev":f.get("url","")})
            if pd.get("location"):
                result.append({"type":"Location","value":pd["location"],
                              "props":{"platform":sn},"rel":"LOCATED_AT","conf":0.5})

    elif name == "platform_search":
        from core import username as m
        data = await m.search_username(value)
        for f in data.get("found", [])[:15]:
            sn = f.get("name", "?")
            pd = f.get("profile_data", {})
            result.append({"type":"SocialProfile","value":f"{sn}:{value}",
                          "props":{"platform":sn,"url":f.get("url",""),"display_name":pd.get("display_name",""),"location":pd.get("location","")},
                          "rel":"FOUND_ON","conf":0.7,"ev":f.get("url","")})

    elif name == "phone_intel":
        from core import phone as m
        data = await m.deep_phone_intel(value)
        basic = data.get("basic", {})
        if basic.get("country"):
            result.append({"type":"Location","value":basic["country"],
                          "props":{"region":basic.get("region",""),"carrier":basic.get("carrier","")},
                          "rel":"LOCATED_AT","conf":0.8})

    elif name == "social_check":
        from core import phone as m
        data = await m.check_social_apps(value)
        for a in data.get("accounts", [])[:5]:
            if a.get("found"):
                result.append({"type":"SocialProfile","value":f"{a['platform']}:{value}",
                              "props":{"platform":a["platform"],"detail":a.get("detail","")},
                              "rel":"LINKED_TO","conf":0.5,"ev":a.get("detail","")})

    elif name == "domain_intel":
        from core import domain as m
        whois = await m.whois_lookup(value)
        if whois.get("registrar"):
            result.append({"type":"Company","value":whois.get("registrar",""),"props":whois,"rel":"OWNS","conf":0.8})

    elif name == "subdomain_enum":
        from core import subdomain as m
        data = await m.enumerate_subdomains(value)
        for sub in data.get("subdomains", [])[:8]:
            result.append({"type":"Domain","value":sub,"rel":"BELONGS_TO","conf":0.7})

    elif name == "geo_intel":
        from core import network as m
        geo = await m.ip_geolocation(value)
        if geo.get("city"):
            result.append({"type":"Location","value":f"{geo.get('city')}, {geo.get('country')}","props":geo,"rel":"LOCATED_AT","conf":0.9})

    elif name == "people_search":
        from core import people as m
        from core import username as uname_mod
        data = await m.full_name_search(value)
        scraped = data.get("scraped_data", [])
        for s in scraped[:8]:
            if s.get("name"):
                result.append({"type":"Person","value":s["name"],"props":s,"rel":"MATCHES","conf":0.4,"ev":s.get("source","")})
        # Also try username search from the name
        parts = value.lower().replace("  "," ").split()
        if parts:
            usernames = [parts[0], "".join(parts), f"{parts[0]}{parts[-1][0] if len(parts)>1 else ''}",
                        f"{parts[0]}.{parts[-1] if len(parts)>1 else parts[0]}",
                        f"{parts[0]}_{parts[-1] if len(parts)>1 else parts[0]}"]
            for uname in usernames[:3]:
                try:
                    u_data = await uname_mod.search_username(uname)
                    for f in u_data.get("found", [])[:5]:
                        sn = f.get("name", "?")
                        result.append({"type":"SocialProfile","value":f"{sn}:{uname}",
                                      "props":{"platform":sn,"url":f.get("url",""),"display_name":f.get("profile_data",{}).get("display_name","")},
                                      "rel":"FOUND_ON","conf":0.5,"ev":f.get("url","")})
                except: pass

    elif name == "social_links":
        from core import people as m
        data = await m.full_name_search(value)
        for s in data.get("social_search_urls", [])[:6]:
            result.append({"type":"SocialProfile","value":f"Search:{s['platform']}",
                          "props":{"platform":s["platform"],"url":s["url"]},"rel":"LINKED_TO","conf":0.3})

    return result
