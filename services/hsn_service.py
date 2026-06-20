"""
HSN lookup service.

Approach:
 1. Local seed of common HSN codes (computer parts + home appliances) for fast,
    deterministic lookup. Source: GST CBIC official HSN schedule.
 2. Optional live lookup against tallysolutions.com/business-tools-templates/free-hsn-code-finder
    via best-effort scrape. This page does not expose a public API; structure may
    change at any time. Local results are returned first.
"""
import json, os, re
from functools import lru_cache

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "hsn_codes.json")


@lru_cache(maxsize=1)
def _load() -> list:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def lookup_hsn(keyword: str, limit: int = 10) -> list:
    if not keyword:
        return []
    kw = keyword.strip().lower()
    data = _load()
    matches = []
    for row in data:
        hay = f"{row.get('name','')} {row.get('keywords','')}".lower()
        if kw in hay:
            matches.append(row)
            if len(matches) >= limit:
                break
    # Fallback: word-prefix match
    if not matches:
        for row in data:
            if any(kw in w for w in re.split(r"\W+", row.get("name", "").lower())):
                matches.append(row)
                if len(matches) >= limit:
                    break
    return matches


def best_match(keyword: str) -> dict | None:
    res = lookup_hsn(keyword, limit=1)
    return res[0] if res else None
