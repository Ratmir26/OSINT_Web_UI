import re
from ddgs import DDGS
from utils.web_scraper import safe_get, get_soup
from utils.helpers import format_phone_basic


def _ddgs_search(query: str, max_results=5) -> list[dict]:
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


def _parse_price(text: str) -> str:
    m = re.search(r'(\d[\d\s]*)\s*(?:₽|руб|руб\.)', text, re.I)
    if m:
        return m.group(1).strip().replace(" ", "") + " ₽"
    return ""


def _parse_avito_id(url: str) -> str:
    m = re.search(r'avito\.ru/(?:[\w-]+/)?(\d+)', url)
    if m:
        return m.group(1)
    return ""


def _parse_youla_id(url: str) -> str:
    m = re.search(r'youla\.ru/(?:[\w-]+/)?([\w-]+)', url)
    if m:
        return m.group(1)
    return ""


def search_avito(query: str, max_results=5) -> list[dict]:
    try:
        results = _ddgs_search(f"site:avito.ru {query}", max_results=max_results)
        items = []
        for r in results:
            item = {
                "title": r["title"],
                "price": _parse_price(r["snippet"]),
                "url": r["link"],
                "snippet": r["snippet"],
            }
            items.append(item)
        return items
    except Exception:
        return []


def search_yula(query: str, max_results=5) -> list[dict]:
    try:
        results = _ddgs_search(f"site:youla.ru {query}", max_results=max_results)
        items = []
        for r in results:
            item = {
                "title": r["title"],
                "price": _parse_price(r["snippet"]),
                "url": r["link"],
                "snippet": r["snippet"],
            }
            items.append(item)
        return items
    except Exception:
        return []


def search_by_phone(phone: str, max_results=5) -> dict:
    try:
        formatted = format_phone_basic(phone)
        phone_query = re.sub(r'\D', '', phone)
        avito_results = search_avito(phone_query, max_results=max_results)
        yula_results = search_yula(phone_query, max_results=max_results)
        return {
            "query": phone,
            "avito": avito_results,
            "yula": yula_results,
        }
    except Exception:
        return {
            "query": phone,
            "avito": [],
            "yula": [],
        }
