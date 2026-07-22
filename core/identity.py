"""Identity Resolution v4 - fuzzy matching, entity clustering, confidence scoring."""
import re
from difflib import SequenceMatcher


def name_similarity(name1: str, name2: str) -> float:
    """Compare two names using multiple strategies."""
    if not name1 or not name2: return 0.0
    n1, n2 = name1.lower().strip(), name2.lower().strip()
    if n1 == n2: return 1.0

    # Token-based comparison
    tokens1 = set(n1.split())
    tokens2 = set(n2.split())
    if tokens1 == tokens2: return 0.95
    jaccard = len(tokens1 & tokens2) / max(len(tokens1 | tokens2), 1)
    ratio = SequenceMatcher(None, n1, n2).ratio()

    # If one name is contained in the other (e.g., "John" vs "John Smith")
    if n1 in n2 or n2 in n1:
        return max(0.7, (jaccard + ratio) / 2)

    return max(ratio, jaccard)


def username_similarity(u1: str, u2: str) -> float:
    """Compare usernames accounting for common variations."""
    if not u1 or not u2: return 0.0
    a, b = u1.lower().strip().lstrip("@"), u2.lower().strip().lstrip("@")
    if a == b: return 1.0
    if a.replace("_","").replace("-","").replace(".","") == b.replace("_","").replace("-","").replace(".",""):
        return 0.85
    if a in b or b in a: return 0.6
    return SequenceMatcher(None, a, b).ratio()


def email_to_username(email: str) -> list[str]:
    """Generate likely usernames from an email."""
    if "@" not in email: return []
    local = email.split("@")[0].lower()
    variants = [local]
    # Remove common patterns
    for sep in [".", "_", "-"]:
        if sep in local:
            variants.append(local.replace(sep, ""))
            variants.extend(local.split(sep))
    # Add first initial variants
    parts = re.split(r'[._\-]', local)
    if len(parts) >= 2:
        variants.append(parts[0][0] + parts[1])
        variants.append(parts[0] + parts[1][0])
    return list(set(v for v in variants if len(v) >= 2))


def cluster_identities(profiles: list[dict]) -> list[list[dict]]:
    """Group profiles that likely belong to the same person."""
    if not profiles: return []
    clusters = [[profiles[0]]]
    for profile in profiles[1:]:
        matched = False
        for cluster in clusters:
            for member in cluster:
                score = _profile_similarity(profile, member)
                if score > 0.5:
                    cluster.append(profile)
                    matched = True
                    break
            if matched: break
        if not matched:
            clusters.append([profile])
    return clusters


def _profile_similarity(p1: dict, p2: dict) -> float:
    scores = []
    n1 = p1.get("display_name", p1.get("name", ""))
    n2 = p2.get("display_name", p2.get("name", ""))
    if n1 and n2: scores.append(name_similarity(n1, n2))
    u1 = p1.get("username", "")
    u2 = p2.get("username", "")
    if u1 and u2: scores.append(username_similarity(u1, u2))
    loc1 = p1.get("location", "")
    loc2 = p2.get("location", "")
    if loc1 and loc2 and loc1.lower() == loc2.lower(): scores.append(1.0)
    elif loc1 and loc2: scores.append(0.3)
    if not scores: return 0.0
    return sum(scores) / len(scores)


def generate_email_variants(name: str, domain: str = "gmail.com") -> list[str]:
    """Generate common email patterns for a person name."""
    name = name.lower().strip()
    parts = name.split()
    if len(parts) < 2: return [f"{name}@{domain}"]
    first, last = parts[0], parts[-1]
    variants = [
        f"{first}.{last}@{domain}", f"{first}{last}@{domain}",
        f"{first}_{last}@{domain}", f"{first}{last[0]}@{domain}",
        f"{first[0]}{last}@{domain}", f"{last}.{first}@{domain}",
        f"{last}{first}@{domain}", f"{first}-{last}@{domain}",
    ]
    return variants
