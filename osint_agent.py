#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import requests
from datetime import datetime
from urllib.parse import quote_plus
from dotenv import load_dotenv
from ddgs import DDGS

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def log(msg: str, level="INFO"):
    colors = {"INFO": "\033[94m", "OK": "\033[92m", "WARN": "\033[93m", "ERR": "\033[91m", "RESET": "\033[0m"}
    c = colors.get(level, colors["INFO"])
    r = colors["RESET"]
    print(f"{c}[{level}]{r} {msg}")


def safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        sanitized = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        print(sanitized.encode('cp1251', errors='replace').decode('cp1251'))


def safe_get(url: str, timeout=15, retries=2) -> requests.Response | None:
    for attempt in range(retries + 1):
        try:
            resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp
            log(f"HTTP {resp.status_code} для {url}", "WARN")
        except Exception as e:
            log(f"Ошибка (попытка {attempt+1}): {e}", "ERR")
        time.sleep(1)
    return None


def extract_phones(text: str) -> list[str]:
    patterns = [
        r'\+996\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}',
        r'\+7\s?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
        r'8\s?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
    ]
    phones = []
    for pat in patterns:
        matches = re.findall(pat, text)
        for m in matches:
            cleaned = re.sub(r'\s+', ' ', m).strip()
            if cleaned and cleaned not in phones:
                phones.append(cleaned)
    return phones


def extract_emails(text: str) -> list[str]:
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    return list(dict.fromkeys([e for e in emails if not e.endswith(('.png', '.jpg', '.gif'))]))


def extract_social_links(text: str) -> dict[str, str]:
    socials = {}
    patterns = {
        "Instagram": r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+',
        "Telegram": r'https?://(?:t\.me|telegram\.me)/[a-zA-Z0-9_]+',
        "WhatsApp": r'https?://wa\.me/\d+',
        "YouTube": r'https?://(?:www\.)?youtube\.com/(?:c/|channel/|@)[a-zA-Z0-9_-]+',
        "Facebook": r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9.]+',
        "VK": r'https?://(?:www\.)?vk\.com/[a-zA-Z0-9_]+',
        "TikTok": r'https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9_.]+',
    }
    for name, pat in patterns.items():
        matches = re.findall(pat, text)
        if matches:
            socials[name] = matches[0]
    return socials


def web_search(query: str, max_results=10) -> list[dict]:
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
        log(f"DuckDuckGo: найдено {len(parsed)} результатов по '{query}'", "OK")
        return parsed
    except Exception as e:
        log(f"Ошибка DuckDuckGo: {e}", "ERR")
        return []


def search_2gis(query: str) -> dict | None:
    log("Поиск в 2GIS...", "INFO")
    try:
        search_url = f"https://catalog.api.2gis.com/3.0/items?q={quote_plus(query)}&region_id=207&key=rurbbn3446"
        resp = SESSION.get(search_url, timeout=15)
        if resp.status_code != 200:
            log(f"2GIS API: HTTP {resp.status_code}", "WARN")
            return search_2gis_via_web(query)

        data = resp.json()
        items = data.get("result", {}).get("items", [])
        if not items:
            log("2GIS API: результатов нет, пробую парсинг сайта", "WARN")
            return search_2gis_via_web(query)

        item = items[0]
        org_id = item.get("id", "")
        details_url = f"https://catalog.api.2gis.com/3.0/items/byid?id={org_id}&key=rurbbn3446"
        det_resp = SESSION.get(details_url, timeout=15)
        det_data = det_resp.json()
        detail = det_data.get("result", {}).get("items", [{}])[0]

        result = {
            "name": detail.get("name", ""),
            "address": detail.get("address_name", ""),
            "rating": detail.get("reviews", {}).get("general_rating", ""),
            "reviews_count": detail.get("reviews", {}).get("general_count", ""),
            "phones": [],
            "website": "",
            "schedule": detail.get("schedule", {}),
        }
        contact_groups = detail.get("contact_groups", [])
        if contact_groups:
            for contact in contact_groups[0].get("contacts", []):
                if contact.get("type") == "phone":
                    result["phones"].append(contact.get("value", ""))
                elif contact.get("type") == "website":
                    result["website"] = contact.get("value", "")

        log(f"2GIS: {result['name']} — {result['address']}", "OK")
        return result
    except Exception as e:
        log(f"2GIS API ошибка: {e}, пробую парсинг сайта", "WARN")
        return search_2gis_via_web(query)


def search_2gis_via_web(query: str) -> dict | None:
    log("2GIS: парсинг сайта...", "INFO")
    try:
        gis_results = web_search(f"{query} site:2gis.ru", max_results=5)
        target_url = ""
        for r in gis_results:
            link = r.get("link", "")
            if "2gis.ru" in link and "/search/" not in link and "2gis.ru" in link:
                target_url = link
                break

        if not target_url:
            for r in gis_results:
                link = r.get("link", "")
                if "2gis.ru" in link:
                    target_url = link
                    break

        if not target_url:
            log("2GIS: страница не найдена через поиск", "WARN")
            return None

        resp = safe_get(target_url, timeout=20)
        if not resp:
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(separator=" ", strip=True)

        name = ""
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)

        address = ""
        addr_meta = soup.find("meta", {"itemprop": "address"})
        if addr_meta:
            address = addr_meta.get("content", "")

        if not address:
            match = re.search(r'(?:ул\.|улица|пр\.|проспект|пер\.|переулок|микрорайон|мкр)[^.]*', text)
            if match:
                address = match.group(0).strip()

        phones = extract_phones(text)
        emails = extract_emails(text)
        socials = extract_social_links(text)

        log(f"2GIS (web): {name or query}", "OK")
        return {
            "name": name or query,
            "address": address,
            "rating": "",
            "reviews_count": "",
            "phones": phones,
            "website": "",
            "schedule": {},
            "emails": emails,
            "socials": socials,
            "source_url": target_url,
        }
    except Exception as e:
        log(f"2GIS парсинг ошибка: {e}", "ERR")
        return None


def search_yandex_maps(query: str) -> dict | None:
    log("Поиск в Яндекс.Картах...", "INFO")
    try:
        yndx_results = web_search(f"{query} Яндекс Карты", max_results=5)
        target_url = ""
        for r in yndx_results:
            link = r.get("link", "")
            if "yandex.ru/maps/org/" in link or "yandex.by/maps/org/" in link or "yandex.kz/maps/org/" in link:
                target_url = link
                break

        if not target_url:
            for r in yndx_results:
                link = r.get("link", "")
                if "yandex" in link and "maps" in link:
                    target_url = link
                    break

        if not target_url:
            log("Яндекс.Карты: страница не найдена", "WARN")
            return None

        resp = safe_get(target_url, timeout=20)
        if not resp:
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(separator=" ", strip=True)

        name = ""
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title:
            name = og_title.get("content", "")

        if not name:
            h1 = soup.find("h1")
            if h1:
                name = h1.get_text(strip=True)

        address = ""
        og_desc = soup.find("meta", {"property": "og:description"})
        if og_desc:
            address = og_desc.get("content", "")

        if not address:
            match = re.search(r'(?:ул\.|улица|пр\.|проспект|пер\.|переулок|микрорайон|мкр)[^.]*', text)
            if match:
                address = match.group(0).strip()

        phones = extract_phones(text)

        hours = ""
        hours_match = re.search(r'(?:круглосуточно|ежедневно|пн-|пн–|будни|график)[^.]*\.', text, re.I)
        if hours_match:
            hours = hours_match.group(0).strip()

        rating = ""
        rating_match = re.search(r'(\d[,.]\d)\s*★?', text)
        if rating_match:
            rating = rating_match.group(1)

        log(f"Яндекс.Карты: {name or query}", "OK")
        return {
            "name": name or query,
            "address": address,
            "rating": rating,
            "phones": phones,
            "hours": hours,
            "categories": [],
            "features": [],
            "url": target_url,
        }
    except Exception as e:
        log(f"Яндекс.Карты ошибка: {e}", "ERR")
        return None


def scrape_webpage(url: str) -> dict:
    log(f"Анализ страницы: {url}", "INFO")
    data = {"phones": [], "emails": [], "socials": {}, "text": ""}
    resp = safe_get(url, timeout=20)
    if not resp:
        return data

    text = resp.text
    data["text"] = text[:5000]
    data["phones"] = extract_phones(text)
    data["emails"] = extract_emails(text)
    data["socials"] = extract_social_links(text)
    log(f"Найдено: {len(data['phones'])} тел., {len(data['emails'])} email, {len(data['socials'])} соцсетей", "OK")
    return data


def search_social_profiles(name: str) -> dict[str, str]:
    log("Поиск соцсетей...", "INFO")
    profiles = {}

    platforms = ["Instagram", "Telegram", "VK", "TikTok", "Facebook", "YouTube", "WhatsApp"]
    for platform in platforms:
        try:
            results = web_search(f'"{name}" {platform}', max_results=5)
            for r in results:
                link = r.get("link", "")
                if platform == "Instagram" and "instagram.com" in link and "/p/" not in link:
                    profiles["Instagram"] = link
                    break
                elif platform == "Telegram" and ("t.me" in link or "telegram.me" in link):
                    profiles["Telegram"] = link
                    break
                elif platform == "VK" and "vk.com" in link:
                    profiles["VK"] = link
                    break
                elif platform == "TikTok" and "tiktok.com" in link:
                    profiles["TikTok"] = link
                    break
                elif platform == "Facebook" and "facebook.com" in link:
                    profiles["Facebook"] = link
                    break
                elif platform == "YouTube" and "youtube.com" in link:
                    profiles["YouTube"] = link
                    break
                elif platform == "WhatsApp" and "wa.me" in link:
                    profiles["WhatsApp"] = link
                    break
        except Exception as e:
            log(f"Поиск {platform}: {e}", "ERR")
            continue

    return profiles


def generate_report(target: str, data: dict) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    lines = [
        f"# OSINT Досье: {target}",
        f"",
        f"**Дата сбора:** {now}",
        f"**Источники:** DuckDuckGo, 2GIS, Яндекс.Карты, Веб-скрапинг",
        f"",
        f"---",
        f"",
    ]

    web_results = data.get("web", [])
    if web_results:
        lines.extend([
            f"## Поиск в интернете",
            f"",
        ])
        for r in web_results[:10]:
            title = r.get("title", "")
            link = r.get("link", "")
            snippet = r.get("snippet", "")
            lines.append(f"- [{title}]({link})")
            if snippet:
                lines.append(f"  > {snippet[:200]}")
        lines.append("")

    gis = data.get("2gis", {})
    if gis:
        lines.extend([
            f"## 2GIS Данные",
            f"",
            f"- **Название:** {gis.get('name', '—')}",
            f"- **Адрес:** {gis.get('address', '—')}",
            f"- **Рейтинг:** {gis.get('rating', '—')}",
            f"- **Телефоны:** {', '.join(gis.get('phones', [])) if gis.get('phones') else '—'}",
            f"- **Сайт:** {gis.get('website', '—')}",
        ])
        if gis.get("emails"):
            lines.append(f"- **Email:** {', '.join(gis['emails'])}")
        if gis.get("socials"):
            for sname, surl in gis["socials"].items():
                lines.append(f"- **{sname}:** [{surl}]({surl})")
        if gis.get("source_url"):
            lines.append(f"- **Источник:** [{gis['source_url']}]({gis['source_url']})")
        lines.append("")

    yndx = data.get("yandex", {})
    if yndx:
        lines.extend([
            f"## Яндекс.Карты",
            f"",
            f"- **Название:** {yndx.get('name', '—')}",
            f"- **Адрес:** {yndx.get('address', '—')}",
            f"- **Телефоны:** {', '.join(yndx.get('phones', [])) if yndx.get('phones') else '—'}",
            f"- **Часы работы:** {yndx.get('hours', '—')}",
            f"- **Рейтинг:** {yndx.get('rating', '—')}",
        ])
        if yndx.get("url"):
            lines.append(f"- **Ссылка:** [{yndx['url']}]({yndx['url']})")
        lines.append("")

    web = data.get("webpage", {})
    if web:
        lines.extend([
            f"## Контакты (с сайта)",
            f"",
            f"- **Телефоны:** {', '.join(web.get('phones', [])) if web.get('phones') else '—'}",
            f"- **Email:** {', '.join(web.get('emails', [])) if web.get('emails') else '—'}",
            f"",
        ])
        if web.get("socials"):
            lines.append(f"### Соцсети (найденные на сайте)")
            lines.append("")
            for name, url in web["socials"].items():
                lines.append(f"- **{name}:** [{url}]({url})")
            lines.append("")

    soc = data.get("socials", {})
    if soc:
        lines.extend([
            f"## Социальные сети",
            f"",
        ])
        for name, url in soc.items():
            lines.append(f"- **{name}:** [{url}]({url})")
        lines.append("")

    lines.extend([
        f"---",
        f"",
        f"*Сгенерировано OSINT Agent*",
    ])

    return "\n".join(lines)


def run_osint(target: str, return_data: bool = False):
    log("=" * 60, "INFO")
    log(f"Запуск OSINT-агента для: {target}", "INFO")
    log("=" * 60, "INFO")

    data = {}

    log("\n[1/5] Поиск в интернете (DuckDuckGo)...", "INFO")
    web_results = web_search(target, max_results=10)
    data["web"] = web_results

    log("\n[2/5] Поиск в 2GIS...", "INFO")
    gis_data = search_2gis(target)
    if gis_data:
        data["2gis"] = gis_data

    log("\n[3/5] Поиск в Яндекс.Картах...", "INFO")
    yndx_data = search_yandex_maps(target)
    if yndx_data:
        data["yandex"] = yndx_data

    log("\n[4/5] Анализ веб-сайта...", "INFO")
    website_url = ""
    if gis_data and gis_data.get("website"):
        website_url = gis_data["website"]

    if not website_url and web_results:
        skip_domains = ["wikipedia.org", "tripadvisor", "otvet.mail.ru", "irecommend",
                        "restaurantguru", "zoon.ru", "chibbis.ru", "dostavka.today",
                        "lunch.catery.ru", "eda.yandex.ru"]
        for r in web_results:
            link = r.get("link", "")
            if any(domain in link for domain in skip_domains):
                continue
            website_url = link
            break

    if not website_url and web_results:
        website_url = web_results[0].get("link", "")

    if website_url:
        web_data = scrape_webpage(website_url)
        if not web_data.get("phones") and not web_data.get("emails") and not web_data.get("socials"):
            for r in web_results:
                link = r.get("link", "")
                if link == website_url:
                    continue
                skip_domains = ["wikipedia.org", "tripadvisor", "otvet.mail.ru"]
                if any(domain in link for domain in skip_domains):
                    continue
                log(f"Первая страница пуста, пробую: {link}", "INFO")
                web_data = scrape_webpage(link)
                if web_data.get("phones") or web_data.get("emails") or web_data.get("socials"):
                    website_url = link
                    break
        data["webpage"] = web_data
        data["website_url"] = website_url

    log("\n[5/5] Поиск социальных профилей...", "INFO")
    socials = search_social_profiles(target)
    data["socials"] = socials

    log("\n" + "=" * 60, "INFO")
    log("Генерация отчёта...", "INFO")
    report = generate_report(target, data)

    safe_name = re.sub(r'[^\w\s-]', '', target).strip().replace(' ', '_')
    results_dir = os.path.join(os.path.dirname(__file__), "data", "results")
    os.makedirs(results_dir, exist_ok=True)

    filename = f"report_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    filepath = os.path.join(results_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    json_path = filepath.replace(".md", "_raw.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log(f"Отчёт сохранён: {filepath}", "OK")
    log(f"JSON данные: {json_path}", "OK")
    log(f"\n{'=' * 60}", "INFO")

    safe_print("\n" + report)
    if return_data:
        return data
    return filepath
