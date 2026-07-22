import asyncio

from utils.report import Report


async def full_person_investigation(email: str, username: str | None = None) -> dict:
    from core import email as email_mod
    from core import username as username_mod

    email_results, username_results = await asyncio.gather(
        email_mod.full_email_intel(email),
        username_mod.full_username_intel(username or email.split("@")[0]),
        return_exceptions=True,
    )

    email_data = email_results if isinstance(email_results, dict) else {"error": str(email_results)}
    username_data = username_results if isinstance(username_results, dict) else {"error": str(username_results)}

    # Cross-reference findings
    cross_ref = _cross_reference(email_data, username_data)

    report = Report(email, "person")
    report.add_result("email", email_data)
    report.add_result("username", username_data)
    report.add_result("cross_reference", cross_ref)
    report_html = report.save_html()
    report_json = report.save_json()

    return {
        "email_intel": email_data,
        "username_intel": username_data,
        "cross_reference": cross_ref,
        "html_report": report_html,
        "json_report": report_json,
    }


def _cross_reference(email_data: dict, username_data: dict) -> dict:
    findings = []

    # Check if email is in breaches
    breaches = email_data.get("breaches", {})
    if isinstance(breaches, dict):
        if breaches.get("pwned"):
            findings.append({
                "type": "breach",
                "severity": "high",
                "detail": f"Email found in {breaches.get('breaches_count', 0)} data breaches",
                "platforms": [b.get("domain", "") for b in breaches.get("breaches", [])[:5]],
            })
        if breaches.get("sensitive_breaches", 0) > 0:
            findings.append({
                "type": "sensitive_data",
                "severity": "critical",
                "detail": f"Sensitive data exposed in {breaches.get('sensitive_breaches')} breaches",
            })

    # Check Gravatar
    gravatar = email_data.get("gravatar", {})
    if isinstance(gravatar, dict):
        if gravatar.get("has_gravatar"):
            gprofile = gravatar.get("profile", {})
            findings.append({
                "type": "gravatar",
                "severity": "info",
                "detail": "Gravatar profile found",
                "display_name": gprofile.get("display_name"),
                "location": gprofile.get("location"),
                "accounts": gprofile.get("accounts", []),
            })

    # Check social profiles
    if isinstance(username_data, dict):
        found = username_data.get("found", [])
        profiles_with_data = [f for f in found if f.get("profile_data") and any(f.get("profile_data", {}).values())]
        if profiles_with_data:
            names = []
            for p in profiles_with_data:
                pd = p.get("profile_data", {})
                site_name = p.get("name", p.get("site", "?"))
                if pd.get("name") or pd.get("display_name"):
                    names.append({"platform": site_name, "name": pd.get("name") or pd.get("display_name")})
            if names:
                findings.append({
                    "type": "identity_correlation",
                    "severity": "info",
                    "detail": "Correlated identities across platforms",
                    "names": names,
                })

    # MX provider for corporate emails
    mx = email_data.get("mx", {})
    if isinstance(mx, dict):
        providers = mx.get("mx_providers", [])
        if providers:
            findings.append({
                "type": "infrastructure",
                "severity": "info",
                "detail": f"Email hosted on: {', '.join(providers)}",
            })

    return {
        "findings_count": len(findings),
        "findings": findings,
        "risk_level": _determine_risk(findings),
    }


def _determine_risk(findings: list) -> str:
    levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    if not findings:
        return "unknown"
    max_level = max(levels.get(f.get("severity", "info"), 0) for f in findings)
    if max_level >= 4:
        return "critical"
    if max_level >= 3:
        return "high"
    if max_level >= 2:
        return "medium"
    return "low"
