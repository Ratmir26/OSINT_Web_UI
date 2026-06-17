import re
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from utils.web_scraper import safe_get, get_soup


def _search_ddg(query: str) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    soup = get_soup(url)
    results = []
    if not soup:
        return results
    for item in soup.select("div.result"):
        title_el = item.select_one("h2 a")
        snippet_el = item.select_one("a.result__snippet")
        link = ""
        title = ""
        if title_el:
            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link.startswith("//"):
                link = "https:" + link
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if title or link:
            results.append({"title": title, "link": link, "snippet": snippet})
    return results


def search_telegram_username(username: str) -> dict:
    username = username.lstrip("@")
    url = f"https://t.me/{username}"
    resp = safe_get(url)
    exists = resp is not None

    title = ""
    description = ""
    photo = ""

    if exists and resp:
        soup = BeautifulSoup(resp.text, "lxml")
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        if og_title and og_title.get("content"):
            title = og_title["content"]
        if og_desc and og_desc.get("content"):
            description = og_desc["content"]
        if og_image and og_image.get("content"):
            photo = og_image["content"]

    result = {
        "query": username,
        "type": "username",
        "telegram_url": url if exists else "",
        "title": title,
        "description": description,
        "photo": photo,
        "exists": exists,
        "found_on_web": [],
    }

    web_results = _search_ddg(f"t.me {username} telegram")
    result["found_on_web"] = web_results

    return result


def search_telegram_phone(phone: str) -> dict:
    phone_clean = re.sub(r"[^\d+]", "", phone)

    results = _search_ddg(f"{phone} telegram")
    tme_results = _search_ddg(f"t.me {phone}")

    seen = set()
    merged = []
    for r in results + tme_results:
        key = r.get("link", r.get("title", ""))
        if key not in seen:
            seen.add(key)
            merged.append(r)

    return {
        "query": phone,
        "type": "phone",
        "telegram_url": "",
        "title": "",
        "description": "",
        "phone_clean": phone_clean,
        "found_on_web": merged,
    }


def search_telegram(query: str) -> dict:
    query = query.strip()
    phone_pattern = re.compile(
        r"^\+?\d{7,15}$"
        r"|^(\+?\d[\d\s\-\(\)]{6,20})$"
    )

    web_results = _search_ddg(f"{query} telegram")

    if query.startswith("@") or not re.match(r"^[\d\+\s\-\(\)]+$", query):
        result = search_telegram_username(query)
        existing_links = {r.get("link") for r in result["found_on_web"]}
        for r in web_results:
            if r.get("link") not in existing_links:
                result["found_on_web"].append(r)
        return result

    if phone_pattern.match(query) or re.sub(r"[\s\-\(\)]", "", query).isdigit():
        result = search_telegram_phone(query)
        existing_links = {r.get("link") for r in result["found_on_web"]}
        for r in web_results:
            if r.get("link") not in existing_links:
                result["found_on_web"].append(r)
        return result

    return {
        "query": query,
        "type": "unknown",
        "telegram_url": "",
        "title": "",
        "description": "",
        "found_on_web": web_results,
    }
