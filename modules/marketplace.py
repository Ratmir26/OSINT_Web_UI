import json

import requests

from utils.web_scraper import safe_get, get_soup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
}


def search_wildberries(query: str, max_results=5) -> list[dict]:
    try:
        url = (
            "https://search.wb.ru/exactmatch/ru/common/v7/search"
            f"?query={requests.utils.quote(query)}&dest=123585493&resultset=catalog"
        )
        resp = safe_get(url)
        if not resp:
            return []

        data = resp.json()
        products = (data.get("data") or {}).get("products") or []
        results = []
        for product in products[:max_results]:
            pid = product.get("id")
            sizes = product.get("sizes") or []
            price = ""
            if sizes:
                price_info = sizes[0].get("price") or {}
                total = price_info.get("total")
                if total is not None:
                    price = f"{total / 100:.2f} ₽"

            rating = product.get("rating")
            if rating is not None:
                rating = float(rating)

            results.append({
                "name": product.get("name", ""),
                "price": price,
                "rating": rating,
                "reviews": product.get("feedbacks", 0),
                "url": f"https://www.wildberries.ru/catalog/{pid}/detail.aspx" if pid else "",
                "brand": product.get("brand", ""),
                "supplier": product.get("supplier", ""),
            })
        return results
    except Exception:
        return []


def search_ozon(query: str, max_results=5) -> list[dict]:
    try:
        url = (
            "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2"
            f"?url=/search/?text={requests.utils.quote(query)}"
        )
        resp = requests.post(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return _ozon_fallback(query, max_results)

        data = resp.json()
        products = _parse_ozon_json(data, max_results)
        if products:
            return products
        return _ozon_fallback(query, max_results)
    except Exception:
        return _ozon_fallback(query, max_results)


def _parse_ozon_json(data: dict, max_results: int) -> list[dict]:
    try:
        cells = (data.get("cells") or []) or (data.get("widgetStates") or {})
        results = []
        if isinstance(cells, dict):
            for key in sorted(cells.keys()):
                try:
                    widget = json.loads(cells[key])
                    items = _extract_ozon_items(widget)
                    results.extend(items)
                except Exception:
                    continue
        elif isinstance(cells, list):
            for cell in cells:
                try:
                    if isinstance(cell, str):
                        widget = json.loads(cell)
                    else:
                        widget = cell
                    items = _extract_ozon_items(widget)
                    results.extend(items)
                except Exception:
                    continue
        return results[:max_results]
    except Exception:
        return []


def _extract_ozon_items(widget: dict) -> list[dict]:
    items = []
    try:
        if "items" in widget:
            raw = widget["items"]
        elif "list" in widget:
            raw = widget["list"]
        else:
            return []

        for item in raw:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id") or item.get("cellTrackingInfo", {}).get("id")
            price_info = item.get("mainPrice") or item.get("price") or {}
            price = ""
            if isinstance(price_info, dict):
                val = price_info.get("value") or price_info.get("price")
                if val is not None:
                    if isinstance(val, (int, float)):
                        price = f"{float(val):.2f} ₽"
                    else:
                        price = str(val)
            elif isinstance(price_info, (int, float)):
                price = f"{float(price_info):.2f} ₽"

            rating = item.get("rating")
            if rating is None:
                rating = item.get("reviewRating")
            if rating is not None:
                try:
                    rating = float(rating)
                except (ValueError, TypeError):
                    rating = None

            reviews = item.get("reviewCount") or item.get("feedbacks") or item.get("reviews") or 0

            name = item.get("title") or item.get("name") or ""

            items.append({
                "name": name,
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "url": f"https://www.ozon.ru/product/{item_id}/" if item_id else "",
            })
    except Exception:
        pass
    return items


def _ozon_fallback(query: str, max_results: int) -> list[dict]:
    try:
        search_url = f"https://www.ozon.ru/search/?text={requests.utils.quote(query)}"
        soup = get_soup(search_url, timeout=15)
        if not soup:
            return []

        results = []
        product_cards = soup.select("[data-widget='searchResults'] [data-widget='searchResult']")
        if not product_cards:
            product_cards = soup.select("div[data-widget='searchResult']")
        if not product_cards:
            product_cards = soup.select("div.a3j, div.k2l, div[class*='tile']")

        for card in product_cards[:max_results]:
            try:
                link_el = card.find("a", href=True)
                name_el = card.find("a", class_="tile-hover-target") or card.find("a", href=True)
                price_el = card.select_one("[class*='price'], [class*='cost'], [data-widget='price']")
                rating_el = card.select_one("[class*='rating'], [class*='star']")

                name = ""
                link = ""
                if link_el:
                    href = link_el.get("href", "")
                    if href:
                        link = f"https://www.ozon.ru{href}" if href.startswith("/") else href
                        name = name_el.get_text(strip=True) if name_el else ""
                        if not name:
                            name = link_el.get("title", "") or link_el.get_text(strip=True)

                price_text = price_el.get_text(strip=True) if price_el else ""
                rating_text = rating_el.get_text(strip=True) if rating_el else ""

                item_id = None
                import re
                m = re.search(r"/product/(\d+)", link)
                if m:
                    item_id = m.group(1)

                results.append({
                    "name": name,
                    "price": price_text,
                    "rating": rating_text if rating_text else None,
                    "reviews": "",
                    "url": link,
                })
            except Exception:
                continue

        return results
    except Exception:
        return []


def search_marketplace(query: str) -> dict:
    wb_results = search_wildberries(query)
    ozon_results = search_ozon(query)
    return {
        "query": query,
        "wildberries": wb_results,
        "ozon": ozon_results,
    }
