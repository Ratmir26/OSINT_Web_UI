from ddgs import DDGS

from utils.web_scraper import safe_get, get_soup
from utils.helpers import extract_social_links


def _ddgs_search(query: str, max_results=10) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="ru-ru", max_results=max_results))
        parsed = []
        for r in results:
            parsed.append({
                "title": r.get("title", ""),
                "link": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
        return parsed
    except Exception:
        return []


def _parse_vk(soup) -> dict:
    data = {"name": "", "city": "", "status": ""}
    if not soup:
        return data
    name_el = soup.find("h2", class_="op_header")
    if name_el:
        data["name"] = name_el.get_text(strip=True)
    if not data["name"]:
        title = soup.find("title")
        if title:
            data["name"] = title.get_text(strip=True).split("|")[0].strip()
    text = soup.get_text(separator=" ", strip=True)
    for kw in ["город", "City"]:
        idx = text.lower().find(kw.lower())
        if idx != -1:
            chunk = text[idx : idx + 60]
            import re
            m = re.search(r"(?:город|City)\s*[:\-]?\s*(.{2,30}?)(?:[,.\n]|$)", chunk, re.I)
            if m:
                data["city"] = m.group(1).strip()
                break
    status_el = soup.find("div", class_="status_text")
    if status_el:
        data["status"] = status_el.get_text(strip=True)
    return data


def _parse_ok(soup) -> dict:
    data = {"name": "", "city": "", "status": ""}
    if not soup:
        return data
    h1 = soup.find("h1")
    if h1:
        data["name"] = h1.get_text(strip=True)
    if not data["name"]:
        title = soup.find("title")
        if title:
            data["name"] = title.get_text(strip=True).split("|")[0].strip()
    text = soup.get_text(separator=" ", strip=True)
    for kw in ["город", "City", "Город"]:
        idx = text.lower().find(kw.lower())
        if idx != -1:
            chunk = text[idx : idx + 60]
            import re
            m = re.search(r"(?:город|City)\s*[:\-]?\s*(.{2,30}?)(?:[,.\n]|$)", chunk, re.I)
            if m:
                data["city"] = m.group(1).strip()
                break
    return data


def _parse_facebook(soup) -> dict:
    data = {"name": "", "city": "", "status": ""}
    if not soup:
        return data
    title = soup.find("title")
    if title:
        data["name"] = title.get_text(strip=True).split("|")[0].strip()
    text = soup.get_text(separator=" ", strip=True)
    for kw in ["город", "City", "Lives in", "From"]:
        idx = text.lower().find(kw.lower())
        if idx != -1:
            chunk = text[idx : idx + 80]
            import re
            m = re.search(r"(?:Lives in|From|город|City)\s*[:\-]?\s*(.{2,40}?)(?:[,.\n]|$)", chunk, re.I)
            if m:
                data["city"] = m.group(1).strip()
                break
    return data


def search_name(full_name: str) -> dict:
    profiles = {
        "VK": {"url": "", "name": "", "info": ""},
        "OK": {"url": "", "name": "", "info": ""},
        "Facebook": {"url": "", "name": "", "info": ""},
        "Instagram": {"url": ""},
    }
    all_results = []
    sources = []

    queries = [
        f'"{full_name}" VK',
        f'"{full_name}" site:vk.com',
        f'"{full_name}" site:ok.ru',
        f'"{full_name}" site:facebook.com',
        f'"{full_name}" Instagram',
    ]

    for query in queries:
        try:
            results = _ddgs_search(query, max_results=10)
            for r in results:
                link = r.get("link", "")
                if link and not any(existing.get("link") == link for existing in all_results):
                    all_results.append(r)
        except Exception:
            continue

    for r in all_results:
        link = r.get("link", "")
        if not link:
            continue

        if "vk.com" in link and not profiles["VK"]["url"]:
            profiles["VK"]["url"] = link
            if "vk.com" not in sources:
                sources.append("vk.com")
            soup = get_soup(link, timeout=10)
            parsed = _parse_vk(soup)
            profiles["VK"]["name"] = parsed["name"]
            parts = []
            if parsed.get("city"):
                parts.append(f"город: {parsed['city']}")
            if parsed.get("status"):
                parts.append(f"статус: {parsed['status']}")
            profiles["VK"]["info"] = "; ".join(parts)

        elif "ok.ru" in link and not profiles["OK"]["url"]:
            profiles["OK"]["url"] = link
            if "ok.ru" not in sources:
                sources.append("ok.ru")
            soup = get_soup(link, timeout=10)
            parsed = _parse_ok(soup)
            profiles["OK"]["name"] = parsed["name"]
            parts = []
            if parsed.get("city"):
                parts.append(f"город: {parsed['city']}")
            if parsed.get("status"):
                parts.append(f"статус: {parsed['status']}")
            profiles["OK"]["info"] = "; ".join(parts)

        elif "facebook.com" in link and not profiles["Facebook"]["url"]:
            profiles["Facebook"]["url"] = link
            if "facebook.com" not in sources:
                sources.append("facebook.com")
            soup = get_soup(link, timeout=10)
            parsed = _parse_facebook(soup)
            profiles["Facebook"]["name"] = parsed["name"]
            parts = []
            if parsed.get("city"):
                parts.append(f"город: {parsed['city']}")
            if parsed.get("status"):
                parts.append(f"статус: {parsed['status']}")
            profiles["Facebook"]["info"] = "; ".join(parts)

        elif "instagram.com" in link and not profiles["Instagram"]["url"]:
            profiles["Instagram"]["url"] = link

    if "duckduckgo" not in sources:
        sources.insert(0, "duckduckgo")

    return {
        "full_name": full_name,
        "profiles": profiles,
        "search_results": all_results[:20],
        "sources": sources,
    }
